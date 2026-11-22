"""Servidores civis do Executivo federal que recebem acima do teto, somados por órgão.

    uv run supersalarios-federal               # baixa os meses que faltam (12 meses) e monta o arquivo do site
    uv run supersalarios-federal --sem-baixar  # só copia pipeline/referencia/supersalarios-federal.json

Fonte: Portal da Transparência (CGU), download de dados dos servidores, um zip por mês:
- {AAAAMM}_Servidores_SIAPE.zip (~80 MB): Remuneracao.csv (uma linha por servidor ativo, com salário-base,
  abate-teto, 13º, férias, "outras remunerações eventuais" e verbas indenizatórias) e Cadastro.csv (o órgão
  onde cada servidor trabalha, o de exercício);
- {AAAAMM}_Honorarios_Advocaticios.zip e {AAAAMM}_Honorarios_Jetons.zip: os honorários de sucumbência
  pagos aos advogados públicos e os jetons de conselhos de estatais. Saem com um mês de atraso: o arquivo
  de outubro traz os pagamentos de setembro.
Depois de alguns downloads seguidos, o Portal passa a pedir captcha: aí o comando para e monta a saída com os
meses que já estão no cache; rodando de novo outro dia, ele completa os que faltam.
Os arquivos têm nome e CPF parcial de cada servidor. Aqui eles são lidos linha a linha de dentro do zip,
juntados pelo código do servidor no Portal e somados por órgão; o zip é apagado depois. O cache em
data/raw/supersalarios-federal/{AAAA-MM}.json.gz guarda só as somas de cada órgão no mês.

Para cada servidor e mês, as camadas da "escada" (cada uma soma uma parte ao que vem antes):
salário-base menos o abate-teto; + pagamentos eventuais; + honorários e jetons; + verbas indenizatórias
(auxílio-alimentação, creche, transporte). Ficam fora o 13º e as férias. Passa do teto quem tem o total
acima do subsídio de ministro do STF do mês.

Saída em site/public/data/indicadores/supersalarios-federal.json, com cópia em pipeline/referencia/.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import shutil
import statistics
import time
import urllib.error
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from .cidades import RAIZ
from .supersalarios import DEGRAU, DEGRAUS, FAIXAS, MINIMO, _get, teto

BASE = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/servidores"
PASTA = RAIZ / "data" / "raw" / "supersalarios-federal"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios-federal.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios-federal.json"
FONTE = "Portal da Transparência (CGU), remuneração dos servidores civis do Poder Executivo federal (SIAPE)"
MESES = 12
PAUSA = 20   # segundos antes de cada download

GRUPOS = ["base", "eventuais", "honorarios", "indenizacoes"]
NOMES_GRUPOS = {
    "base": "Salário, menos o corte pelo teto",
    "eventuais": "Pagamentos eventuais (substituições, gratificações, bônus)",
    "honorarios": "Honorários de sucumbência e jetons",
    "indenizacoes": "Verbas indenizatórias (auxílio-alimentação, creche, transporte)",
}


def _num(s: str | None) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return 0.0


def _linhas(zf: zipfile.ZipFile, fim: str):
    nome = next((n for n in zf.namelist() if n.endswith(fim)), None)
    if nome is None:
        return
    with zf.open(nome) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="cp1252", newline=""), delimiter=";")


class Bloqueado(Exception):
    """O Portal passou a pedir captcha (proteção contra robôs). Não se contorna: para e tenta outro dia."""


def _zip(nome: str, pasta: Path) -> zipfile.ZipFile | None:
    """Baixa um arquivo do Portal, com uma pausa antes (o servidor bloqueia quem baixa muito seguido). None se
    ainda não saiu."""
    arq = pasta / nome
    time.sleep(PAUSA)
    try:
        arq.write_bytes(_get(f"{BASE}/{nome}", timeout=600))
    except urllib.error.HTTPError as erro:
        if erro.code in (403, 404):
            return None   # ainda não publicado
        if erro.code in (405, 429) or erro.headers.get("x-amzn-waf-action"):
            raise Bloqueado(f"{nome}: o Portal respondeu {erro.code} ({erro.headers.get('x-amzn-waf-action') or 'limite'})") from erro
        raise
    return zipfile.ZipFile(arq)


def _pagos(zf: zipfile.ZipFile | None, fim: str) -> dict[str, float]:
    soma: dict[str, float] = defaultdict(float)
    if zf:
        for r in _linhas(zf, fim):
            soma[r.get("Id_SERVIDOR_PORTAL") or ""] += _num(r.get("VALOR"))
    return soma


def somar_mes(ano: int, mes: int) -> dict | None:
    """As somas de um mês por órgão de exercício. Devolve None se o mês (ou os honorários dele) não saiu."""
    seguinte = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    tmp = PASTA / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        hon = _zip("%d%02d_Honorarios_Advocaticios.zip" % seguinte, tmp)
        if hon is None:
            return None
        jet = _zip("%d%02d_Honorarios_Jetons.zip" % seguinte, tmp)
        siape = _zip(f"{ano}{mes:02d}_Servidores_SIAPE.zip", tmp)
        if siape is None:
            return None
        honorarios = _pagos(hon, "HonorariosAdvocaticios.csv")
        jetons = _pagos(jet, "(Jetons).csv")
        orgao: dict[str, tuple[str, str]] = {}
        for r in _linhas(siape, "_Cadastro.csv"):
            i, cod, nome = r.get("Id_SERVIDOR_PORTAL") or "", r.get("COD_ORG_EXERCICIO") or "", (r.get("ORG_EXERCICIO") or "").strip()
            # Quem tem cargo e função aparece duas vezes: fica o primeiro órgão com nome.
            if i not in orgao or (orgao[i][1].lower().startswith("sem informa") and not nome.lower().startswith("sem informa")):
                orgao[i] = (cod, nome)
        t = teto(ano, mes)
        por: dict[str, dict] = {}
        for r in _linhas(siape, "_Remuneracao.csv"):
            i = r.get("Id_SERVIDOR_PORTAL") or ""
            base = _num(r.get("REMUNERAÇÃO BÁSICA BRUTA (R$)")) + _num(r.get("ABATE-TETO (R$)"))
            partes = {
                "base": base,
                "eventuais": _num(r.get("OUTRAS REMUNERAÇÕES EVENTUAIS (R$)")),
                "honorarios": honorarios.get(i, 0.0) + jetons.get(i, 0.0),
                "indenizacoes": _num(r.get("TOTAL DE VERBAS INDENIZATÓRIAS (R$)(*)")),
            }
            total = sum(partes.values())
            if total <= 0:
                continue
            cod, nome = orgao.get(i, ("", "Sem informação"))
            o = por.setdefault(cod or nome, {"nome": nome, "servidores": 0, "acima": 0, "excesso": 0.0, "totais": [],
                                             "grupos": {g: 0.0 for g in GRUPOS}, "camadas": [[0, 0.0] for _ in GRUPOS],
                                             "hist": [0] * (DEGRAUS + 1)})
            o["servidores"] += 1
            o["totais"].append(total)
            soma = 0.0
            for k, g in enumerate(GRUPOS):
                soma += partes[g]
                o["grupos"][g] += partes[g]
                if soma > t:
                    o["camadas"][k][0] += 1
                    o["camadas"][k][1] += soma - t
            if total > t:
                o["acima"] += 1
                o["excesso"] += total - t
                o["hist"][min(DEGRAUS, int((total - t - 0.005) // DEGRAU))] += 1
        for o in por.values():
            totais = o.pop("totais")
            o["mediana"] = round(statistics.median(totais), 2)
            o["pago"] = round(sum(totais), 2)
            o["excesso"] = round(o["excesso"], 2)
            o["grupos"] = {g: round(v, 2) for g, v in o["grupos"].items()}
            o["camadas"] = [[n, round(v, 2)] for n, v in o["camadas"]]
        return {"teto": t, "orgaos": por}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def meses_recentes(hoje: date) -> list[tuple[int, int]]:
    """Do mês passado para trás, os candidatos (o mais recente pode ainda não ter saído)."""
    a, m = hoje.year, hoje.month
    saida = []
    for _ in range(MESES + 3):
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
        saida.append((a, m))
    return saida


def resumir(meses: list[dict], cod: str) -> dict | None:
    xs = [x["orgaos"][cod] for x in meses if cod in x["orgaos"]]
    if not xs:
        return None
    n = len(xs)
    servidores = sum(x["servidores"] for x in xs)
    acima = sum(x["acima"] for x in xs)
    poucos = acima / n < MINIMO
    limites = [f // DEGRAU for f in FAIXAS]
    faixas = [0.0] * (len(FAIXAS) + 1)
    for x in xs:
        for i, c in enumerate(x["hist"]):
            faixas[sum(1 for lim in limites if i >= lim)] += c / n
    return {
        "nome": xs[-1]["nome"], "meses": n,
        "servidores": round(servidores / n),
        "acima": None if poucos else round(acima / n),
        "parte": None if poucos else round(acima / servidores, 4),
        "excesso": None if poucos else round(sum(x["excesso"] for x in xs)),
        "pago": round(sum(x["pago"] for x in xs)),
        "mediana": round(statistics.median([x["mediana"] for x in xs])),
        "grupos": {g: round(sum(x["grupos"][g] for x in xs)) for g in GRUPOS},
        "camadas": [[round(sum(x["camadas"][k][0] for x in xs) / n), round(sum(x["camadas"][k][1] for x in xs))] for k in range(len(GRUPOS))],
        "faixas": None if poucos else [round(f) if f >= MINIMO else None for f in faixas],
    }


def montar(meses: dict[str, dict]) -> dict:
    ordem = sorted(meses)
    lista = [meses[m] for m in ordem]
    cods = sorted({c for x in lista for c in x["orgaos"]})
    orgaos = {c: r for c in cods if (r := resumir(lista, c))}
    serie = {}
    for m in ordem:
        os_ = meses[m]["orgaos"].values()
        serie[m] = [sum(o["servidores"] for o in os_), sum(o["acima"] for o in os_), round(sum(o["excesso"] for o in os_))]
    return {
        "fonte": FONTE, "url": "https://portaldatransparencia.gov.br/download-de-dados/servidores",
        "gerado": date.today().isoformat(), "de": ordem[0], "ate": ordem[-1], "meses": len(ordem),
        "grupos": [[g, NOMES_GRUPOS[g]] for g in GRUPOS], "faixas": FAIXAS, "orgaos": orgaos, "serie": serie,
    }


def gravar(doc: dict) -> None:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    os_ = doc["orgaos"].values()
    serv = sum(o["servidores"] for o in os_)
    acima = sum(o["acima"] or 0 for o in os_)
    exc = sum(o["excesso"] or 0 for o in os_)
    print(f"{doc['de']} a {doc['ate']}: {serv} servidores num mês típico, {acima} acima do teto ({acima / serv:.1%}), "
          f"R$ {exc / 1e9:.2f} bi acima do teto em {doc['meses']} meses")
    for c, o in sorted(doc["orgaos"].items(), key=lambda i: -(i[1]["excesso"] or 0))[:12]:
        print(f"    {o['nome'][:50]:50s} {o['acima'] or 0:6d} de {o['servidores']:6d}  R$ {(o['excesso'] or 0) / 1e6:7.1f} mi")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")


def main() -> None:
    p = argparse.ArgumentParser(prog="supersalarios-federal", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está em data/raw, sem baixar")
    args = p.parse_args()
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    PASTA.mkdir(parents=True, exist_ok=True)
    meses: dict[str, dict] = {}
    for a, m in meses_recentes(date.today()):
        if len(meses) == MESES:
            break
        chave = f"{a}-{m:02d}"
        cache = PASTA / f"{chave}.json.gz"
        if cache.exists():
            meses[chave] = json.loads(gzip.decompress(cache.read_bytes()))
            continue
        if args.so_cache:
            continue
        print(f"  {chave}: baixando", flush=True)
        try:
            x = somar_mes(a, m)
        except Bloqueado as erro:
            print(f"  {erro}. Parando os downloads; a saída fica com os {len(meses)} meses do cache. Rode de novo outro dia.", flush=True)
            break
        if x is None:
            print(f"  {chave}: ainda não publicado (ou sem os honorários)", flush=True)
            continue
        cache.write_bytes(gzip.compress(json.dumps(x, ensure_ascii=False, separators=(",", ":")).encode()))
        os_ = x["orgaos"].values()
        print(f"  {chave}: {sum(o['servidores'] for o in os_)} servidores, {sum(o['acima'] for o in os_)} acima do teto", flush=True)
        meses[chave] = x
    if not meses:
        if REFERENCIA.exists():   # sem nenhum mês novo nem cache: fica a cópia de referência
            shutil.copyfile(REFERENCIA, SAIDA)
            print(f"nenhum mês baixado; copiado {REFERENCIA.relative_to(RAIZ)}")
            return
        raise SystemExit("nenhum mês")
    gravar(montar(meses))
