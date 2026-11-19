"""Gasto dos estados e municípios por função e subfunção (SICONFI, Tesouro Nacional).

    uv run cidades                    # os dois últimos exercícios fechados
    uv run cidades --so-estados       # só os 26 estados e o DF (54 consultas)
    uv run cidades --anos 2024 2025
    uv run cidades --limite 50        # só os 50 primeiros municípios (para testar)
    uv run cidades --max-chamadas 3000  # para depois de 3.000 consultas novas

Fonte: Declaração de Contas Anuais (DCA), Anexo I-E, que cada prefeitura entrega
ao Tesouro até 30 de abril do ano seguinte (os estados, até 31 de maio). A API do SICONFI só responde um ente
por vez, então são ~5.570 chamadas por ano. As respostas de cada ano ficam
num único arquivo, data/raw/siconfi/dca-ie/{ano}.json.gz (ver CacheAno);
respostas vazias (prefeitura que ainda não entregou) são consultadas de novo
a cada execução. A API bloqueia
acima do limite documentado de 1 requisição por segundo (HTTP 429), então as chamadas seguem esse ritmo.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import statistics
import time
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from .fontes import CONTEXTO_TLS, USER_AGENT

RAIZ = Path(__file__).resolve().parents[3]
PASTA_BRUTO = RAIZ / "data" / "raw" / "siconfi"
SAIDA = RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
SAIDA_ESTADOS = RAIZ / "site" / "public" / "data" / "cidades" / "estados.json"

URL_API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
ANEXO = "DCA-Anexo I-E"
COL_EMPENHADO = "Despesas Empenhadas"
COL_PAGO = "Despesas Pagas"
CONTA_TOTAL = "Despesas Exceto Intraorçamentárias"
IBGE_DF = 53
PRIMEIRO_ANO = 2014  # a DCA de 2013 vem vazia na API

# Faixas de população para comparar cada cidade com as de porte parecido.
FAIXAS = [
    (5_000, "até 5 mil habitantes"),
    (10_000, "de 5 a 10 mil habitantes"),
    (20_000, "de 10 a 20 mil habitantes"),
    (50_000, "de 20 a 50 mil habitantes"),
    (100_000, "de 50 a 100 mil habitantes"),
    (500_000, "de 100 a 500 mil habitantes"),
    (None, "mais de 500 mil habitantes"),
]


class Ritmo:
    """Espaça as chamadas entre todas as threads e pausa todas juntas num 429.

    A documentação da API (https://apidatalake.tesouro.gov.br/docs/siconfi/) fixa o limite em
    1 requisição por segundo. Acima disso, um firewall responde 429 (sem Retry-After) por
    alguns minutos.
    """

    def __init__(self, por_segundo: float) -> None:
        self.intervalo = 1 / por_segundo
        self.proxima = 0.0
        self.trava = threading.Lock()

    def esperar(self) -> None:
        with self.trava:
            agora = time.monotonic()
            vez = max(agora, self.proxima)
            self.proxima = vez + self.intervalo
        time.sleep(max(0.0, vez - agora))

    def pausar(self, segundos: float) -> None:
        with self.trava:
            self.proxima = max(self.proxima, time.monotonic() + segundos)


RITMO = Ritmo(1)


def _get(caminho: str, params: dict) -> dict:
    url = URL_API + caminho + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    bloqueios = 0
    for tentativa in range(8):
        RITMO.esperar()
        try:
            with urllib.request.urlopen(req, timeout=90, context=CONTEXTO_TLS) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code != 429 or bloqueios == 4:
                if tentativa >= 3:
                    raise
                time.sleep(2 ** tentativa)
                continue
            bloqueios += 1
            pausa = 60 * 2 ** (bloqueios - 1)
            print(f"  429 da API; pausando {pausa}s", flush=True)
            RITMO.pausar(pausa)
        except Exception:
            if tentativa >= 3:
                raise
            time.sleep(2 ** tentativa)
    raise RuntimeError(f"{caminho}: muitas tentativas")


def baixar_entes(forcar: bool = False) -> list[dict]:
    """Todos os entes do SICONFI (União, estados, DF e municípios), com nome, UF e população."""
    PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
    cache = PASTA_BRUTO / "entes.json"
    if cache.exists() and not forcar:
        return json.loads(cache.read_text(encoding="utf-8"))
    itens = _get("entes", {})["items"]
    cache.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    return itens


class Orcamento:
    """Limite de chamadas novas por execução: o cache cresce aos poucos no CI."""

    def __init__(self, maximo: int | None) -> None:
        self.restantes = maximo
        self.trava = threading.Lock()

    def gastar(self) -> bool:
        with self.trava:
            if self.restantes is None:
                return True
            if self.restantes <= 0:
                return False
            self.restantes -= 1
            return True


CHAMADAS = Orcamento(None)


CAMPOS_CACHE = ("coluna", "conta", "valor", "populacao")


def compactar(itens: list[dict]) -> list[dict]:
    """Só as colunas e campos que `resumir` usa: o cache fica com ~1/5 do tamanho."""
    return [{k: i.get(k) for k in CAMPOS_CACHE} for i in itens if i.get("coluna") in (COL_EMPENHADO, COL_PAGO)]


class CacheAno:
    """Respostas da DCA de um exercício num único arquivo: data/raw/siconfi/dca-ie/{ano}.json.gz.

    Um arquivo por ano (e não um por ente) porque o cache pode morar num disco de
    rede (WebDAV), onde milhares de arquivos pequenos sobem muito devagar. Fica em
    memória durante a execução e é regravado a cada 200 respostas novas e no fim,
    sempre num temporário trocado de nome: uma queda não deixa o arquivo pela metade.
    """

    SALVAR_A_CADA = 200

    def __init__(self, ano: int, anexo: str = "dca-ie", filtro: Callable[[list[dict]], list[dict]] | None = None) -> None:
        # `anexo`: pasta do cache (dca-ie = despesa por função; dca-ic = receitas, vindas do FINBRA).
        self.filtro = filtro or compactar
        self.arq = PASTA_BRUTO / anexo / f"{ano}.json.gz"
        self.trava = threading.Lock()
        self.novos = 0
        self.dados: dict[str, list[dict]] = {}
        try:
            self.dados = json.loads(gzip.decompress(self.arq.read_bytes()))
        except FileNotFoundError:
            pass
        except (OSError, ValueError, EOFError) as e:
            print(f"  aviso: {self.arq.name} ilegível ({e}); começando o ano do zero", flush=True)
        # Formato antigo (um arquivo por ente em dca-ie/{ano}/): incorpora e passa a gravar no novo.
        antiga = self.arq.parent / str(ano)
        if antiga.is_dir():
            for arq in antiga.glob("*.json"):
                if arq.stem not in self.dados or not self.dados[arq.stem]:
                    try:
                        self.dados[arq.stem] = compactar(json.loads(arq.read_text(encoding="utf-8")))
                        self.novos += 1
                    except (OSError, ValueError):
                        pass

    def obter(self, ibge: int) -> list[dict] | None:
        return self.dados.get(str(ibge))

    def guardar(self, ibge: int, itens: list[dict]) -> None:
        with self.trava:
            self.dados[str(ibge)] = self.filtro(itens)
            self.novos += 1
            if self.novos % self.SALVAR_A_CADA == 0:
                self._gravar()

    def salvar(self) -> None:
        with self.trava:
            if self.novos:
                self._gravar()

    def _gravar(self) -> None:
        self.arq.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.arq.with_name(self.arq.name + ".tmp")
        tmp.write_bytes(gzip.compress(json.dumps(self.dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
        os.replace(tmp, self.arq)


def baixar_dca(cache: CacheAno, ano: int, ibge: int, consultar: bool = True, anexo: str = ANEXO) -> list[dict] | None:
    """Linhas de um anexo da DCA de um ente (por padrão o I-E, despesa por função).

    None se a chamada falhar, o limite acabar ou `consultar` for falso. O `cache` tem que ser
    o do mesmo anexo.
    """
    itens = cache.obter(ibge)
    if itens or not consultar:
        return itens
    if not CHAMADAS.gastar():
        return None
    try:
        d = _get("dca", {"an_exercicio": ano, "no_anexo": anexo, "id_ente": ibge})
    except Exception:
        return None
    if d.get("hasMore"):
        raise RuntimeError(f"DCA {ano}/{ibge}: resposta paginada, não esperada")
    cache.guardar(ibge, d["items"])
    return d["items"]


def _separar(conta: str) -> tuple[str, str]:
    """"10.301 - Atenção Básica" -> ("10.301", "Atenção Básica"); "FU10 - Demais…" -> ("10.FU", …)."""
    cod, _, nome = conta.partition(" - ")
    cod = cod.strip()
    if cod.startswith("FU"):
        cod = f"{cod[2:]}.FU"
    return cod, " ".join(nome.split())


def _so_letras(s: str) -> str:
    """Só as letras, em minúsculas e sem acento: compara rótulos que variam de grafia entre anos."""
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower())


def resumir(itens: list[dict]) -> dict | None:
    """Agrupa as linhas da DCA em total, funções e subfunções (empenhado e pago)."""
    total = {"emp": 0.0, "pago": 0.0}
    funcoes: dict[str, list[float]] = {}
    subfuncoes: dict[str, float] = {}
    nomes: dict[str, str] = {}
    pop = None
    achou_total = False
    for i in itens:
        col = i["coluna"]
        if col not in (COL_EMPENHADO, COL_PAGO):
            continue
        pop = pop or i.get("populacao")
        v = float(i["valor"] or 0)
        conta = " ".join(i["conta"].split())
        # A grafia do total muda com o ano: "Despesas (Exceto Intraorçamentárias)" até ~2016,
        # "Despesas (Exceto Intra-Orçamentárias)" em 2013. Compara só as letras.
        rotulo = _so_letras(conta)
        if rotulo == _so_letras(CONTA_TOTAL):
            total["emp" if col == COL_EMPENHADO else "pago"] = v
            achou_total = True
            continue
        if rotulo == _so_letras("Despesas Intraorçamentárias") or " - " not in conta:
            continue
        cod, nome = _separar(conta)
        nomes[cod] = nome
        if "." in cod:
            if col == COL_EMPENHADO:
                subfuncoes[cod] = subfuncoes.get(cod, 0.0) + v
        else:
            par = funcoes.setdefault(cod, [0.0, 0.0])
            par[0 if col == COL_EMPENHADO else 1] += v
    if not achou_total or total["emp"] <= 0:
        return None
    return {"total": total, "funcoes": funcoes, "subfuncoes": subfuncoes, "nomes": nomes, "pop": pop}


def faixa_de(pop: int) -> int:
    for idx, (ate, _) in enumerate(FAIXAS):
        if ate is None or pop <= ate:
            return idx
    return len(FAIXAS) - 1


# Código IBGE do estado (dois dígitos) -> sigla. Na lista do SICONFI os estados vêm com UF "BR".
SIGLAS = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE",
    24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
}


def baixar_lote(entes: list[dict], anos: list[int], paralelo: int, rotulo: str,
                so_cache: set[int] = frozenset()) -> tuple[dict[int, dict[int, dict]], set[int]]:
    """resumos[ano][ibge] (ausente se o ente não entregou) e os entes com alguma consulta pendente.

    Anos em `so_cache` (histórico importado do FINBRA) são lidos só do cache, sem consultar a API.
    """
    resumos: dict[int, dict[int, dict]] = {}
    pendentes: set[int] = set()
    for ano in anos:
        consultar = ano not in so_cache
        print(f"{'baixando' if consultar else 'lendo do cache'} DCA {ano} de {len(entes)} {rotulo}…", flush=True)
        t0 = time.time()
        cache = CacheAno(ano)
        try:
            with ThreadPoolExecutor(paralelo) as ex:
                brutos = list(ex.map(lambda e: baixar_dca(cache, ano, e["cod_ibge"], consultar), entes))
        finally:
            cache.salvar()
        resumos[ano] = {}
        for e, itens in zip(entes, brutos):
            if itens is None:
                if consultar:
                    pendentes.add(e["cod_ibge"])
                continue
            r = resumir(itens)
            if r:
                resumos[ano][e["cod_ibge"]] = r
        print(f"  {len(resumos[ano])} com dados ({time.time() - t0:.0f}s)", flush=True)
    return resumos, pendentes


def montar(entes: list[dict], anos: list[int], resumos: dict[int, dict[int, dict]], pendentes: set[int],
           faixa: Callable[[int], int], rotulos_faixas: list[str], identificar: Callable[[dict], dict]) -> dict:
    """Documento para o site: nomes, medianas per capita por faixa e um registro por ente.

    `identificar(ente)` devolve {nome, uf, capital}; o DF fica fora das medianas
    porque acumula funções de estado e de município. Entes sem dados e com
    consulta pendente ficam de fora: não dá para dizer que não entregaram.
    """
    nomes: dict[str, str] = {}
    for ano in anos:
        for r in resumos[ano].values():
            nomes.update(r["nomes"])
    funcoes = {c: n for c, n in sorted(nomes.items()) if "." not in c}
    subfuncoes = {c: (n if not c.endswith(".FU") else "Demais subfunções") for c, n in sorted(nomes.items()) if "." in c}

    medianas: dict[str, list[dict[str, float]]] = {}
    for ano in anos:
        grupos: list[dict[str, list[float]]] = [{} for _ in rotulos_faixas]
        for ibge, r in resumos[ano].items():
            if not r["pop"] or ibge == IBGE_DF:
                continue
            g = grupos[faixa(r["pop"])]
            g.setdefault("total", []).append(r["total"]["emp"] / r["pop"])
            for f in funcoes:
                g.setdefault(f, []).append(r["funcoes"].get(f, [0.0])[0] / r["pop"])
        medianas[str(ano)] = [
            {k: round(statistics.median(v), 2) for k, v in g.items()} | {"n": len(g.get("total", []))}
            for g in grupos
        ]

    registros = []
    for e in entes:
        ibge = e["cod_ibge"]
        base = {"ibge": ibge} | identificar(e)
        ano = next((a for a in reversed(anos) if ibge in resumos[a]), None)
        if ano is None and ibge in pendentes:
            continue
        if ano is None:
            registros.append(base | {"pop": e["populacao"], "ano": None})
            continue
        r = resumos[ano][ibge]
        pop = r["pop"] or e["populacao"]
        registros.append(base | {
            "pop": pop,
            "faixa": faixa(pop),
            "ano": ano,
            "total": [round(r["total"]["emp"]), round(r["total"]["pago"])],
            "f": {c: [round(v[0]), round(v[1])] for c, v in r["funcoes"].items() if v[0] or v[1]},
            "s": {c: round(v) for c, v in r["subfuncoes"].items() if v},
            "hist": {str(a): round(resumos[a][ibge]["total"]["emp"]) for a in anos if ibge in resumos[a]},
        })

    return {
        "gerado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "SICONFI/Tesouro Nacional, DCA Anexo I-E",
        "anos": anos,
        "funcoes": funcoes,
        "subfuncoes": subfuncoes,
        "faixas": rotulos_faixas,
        "medianas": medianas,
        "cidades": registros,
    }


def _gravar(doc: dict, saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    com = sum(1 for c in doc["cidades"] if c["ano"])
    print(f"  {com} de {len(doc['cidades'])} com DCA -> {saida.relative_to(RAIZ)} ({saida.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    hoje = date.today()
    p = argparse.ArgumentParser(prog="cidades", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # A DCA de um ano chega até abril do seguinte: antes de maio, o último ano fechado ainda está incompleto.
    ultimo = hoje.year - 1 if hoje.month >= 5 else hoje.year - 2
    p.add_argument("--anos", type=int, nargs="+", default=[ultimo - 1, ultimo])
    p.add_argument("--anos-estados", type=int, nargs="+", default=list(range(PRIMEIRO_ANO, ultimo + 1)),
                   help="os estados são só 27 consultas por ano: vão desde 2014 por padrão")
    p.add_argument("--limite", type=int, default=None, help="só os N primeiros municípios (teste)")
    p.add_argument("--so-estados", action="store_true", help="só os 26 estados e o DF")
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--por-segundo", type=float, default=1, help="ritmo máximo de chamadas à API (o limite documentado é 1/s)")
    p.add_argument("--max-chamadas", type=int, default=None,
                   help="para depois de N chamadas novas (o resto fica para a próxima execução)")
    args = p.parse_args()
    RITMO.intervalo = 1 / args.por_segundo
    CHAMADAS.restantes = args.max_chamadas

    todos = sorted(baixar_entes(forcar=args.max_chamadas != 0), key=lambda e: e["cod_ibge"])  # --max-chamadas 0: só o cache
    anos = sorted(args.anos)

    # Estados e DF: 27 consultas por ano.
    estados = [e for e in todos if e["esfera"] in ("E", "D")]
    anos_estados = sorted(set(args.anos_estados) | set(anos))
    resumos, pendentes = baixar_lote(estados, anos_estados, args.paralelo, "estados")
    doc = montar(estados, anos_estados, resumos, pendentes, lambda _pop: 0, ["estados"],
                 lambda e: {"nome": e["ente"], "uf": SIGLAS[e["cod_ibge"]], "capital": False})
    _gravar(doc, SAIDA_ESTADOS)

    if not args.so_estados:
        municipios = [e for e in todos if e["esfera"] in ("M", "D")]
        if args.limite:
            municipios = municipios[: args.limite]
        # Histórico: anos anteriores que já estão no cache (importados com `uv run finbra`) entram
        # só a partir do cache; a API é consultada apenas para os anos de `--anos`.
        historico = {int(p.name[:4]) for p in (PASTA_BRUTO / "dca-ie").glob("*.json.gz")
                     if p.name[:4].isdigit() and int(p.name[:4]) < min(anos)}
        anos_mun = sorted(set(anos) | historico)
        resumos, p_mun = baixar_lote(municipios, anos_mun, args.paralelo, "municípios", so_cache=historico)
        pendentes |= p_mun

        def identificar(e: dict) -> dict:
            if e["cod_ibge"] == IBGE_DF:
                return {"nome": "Brasília (Distrito Federal)", "uf": "DF", "capital": True}
            return {"nome": e["ente"], "uf": e["uf"], "capital": e["capital"].strip() == "1"}

        doc = montar(municipios, anos_mun, resumos, p_mun, faixa_de, [r for _, r in FAIXAS], identificar)
        _gravar(doc, SAIDA)

    print(f"{len(pendentes)} entes com consultas que falharam ou ficaram para a próxima execução")


if __name__ == "__main__":
    main()
