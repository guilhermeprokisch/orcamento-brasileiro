"""Dívida ativa da União: o que empresas e pessoas devem ao governo federal e não pagaram.

    uv run divida-ativa                       # último trimestre da PGFN e último cadastro de CNPJ
    uv run divida-ativa --trimestre 2026_trimestre_03 --receita 2026-11
    uv run divida-ativa --sem-baixar          # só copia pipeline/referencia/divida-ativa.json

Fontes:

- PGFN, dados abertos da dívida ativa (https://dadosabertos.pgfn.gov.br/): um zip por tipo e por
  trimestre, com uma linha por inscrição: devedor (CPF mascarado ou CNPJ), UF, situação da inscrição,
  se está na Justiça e o valor consolidado. Tipos: não previdenciária (impostos e multas, ~1,4 GB;
  desde 2026 o arquivo se chama "Sistema_SIDA"), previdenciária (contribuições ao INSS, ~80 MB) e FGTS
  (~20 MB). A lista não traz o município.
- Receita Federal, cadastro de CNPJ (Estabelecimentos e Empresas, ~6,7 GB por mês): a cidade de cada
  CNPJ devedor, se a empresa está ativa e a natureza jurídica. Cada arquivo é baixado, lido e apagado.

Regras de privacidade (inegociáveis):

- CPF nunca é guardado, nem parte dele. As pessoas físicas entram só no total e na contagem, por UF
  (a lista não diz a cidade delas); a contagem usa um hash em memória, que não sai do programa.
- Empresas aparecem pelo nome e CNPJ, com a situação da dívida. Quem tem CNPJ mas é pessoa entra nos totais,
  nunca pelo nome: o empresário individual (natureza 213-5, que inclui o MEI) e todo o grupo 4 da tabela de
  naturezas da Receita, o das pessoas físicas (produtor rural, 412-0; empresa individual imobiliária, 401-4;
  candidato a cargo eletivo, 409-0; e os outros). Um nome com um número de 11 dígitos (CPF) também não sai.

O município é o do estabelecimento devedor (o CNPJ completo); sem ele, o da matriz. CNPJ que não está
no cadastro (empresas muito antigas) conta só no estado.

Saída: site/public/data/divida-ativa/divida-ativa.json, com cópia em pipeline/referencia/. Os downloads
são grandes e a PGFN às vezes só responde do Brasil: a publicação usa --sem-baixar.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from array import array
from collections import defaultdict
from pathlib import Path

from .cidades import RAIZ
from .federal import siafi_para_ibge
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA = RAIZ / "data" / "raw" / "pgfn"
SAIDA = RAIZ / "site" / "public" / "data" / "divida-ativa" / "divida-ativa.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "divida-ativa.json"
URL_PGFN = "https://dadosabertos.pgfn.gov.br/"
# Cadastro de CNPJ da Receita: pasta compartilhada no Nextcloud, lida por WebDAV público.
URL_RECEITA = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
TOKEN_RECEITA = "YggdBLfdninEJX9"
FONTE = ("PGFN, dados abertos da dívida ativa da União; Receita Federal, cadastro de CNPJ "
         "(cidade, natureza jurídica e situação de cada empresa)")

# Tipo de dívida → nomes possíveis do arquivo (o não previdenciário mudou de nome em 2026).
TIPOS = {
    "nao_prev": ("Dados_abertos_Sistema_SIDA", "Dados_abertos_Nao_Previdenciario"),
    "prev": ("Dados_abertos_Previdenciario",),
    "fgts": ("Dados_abertos_FGTS",),
}
T = list(TIPOS)
# Situação da inscrição, em cinco grupos para o site.
SITUACOES = ["justica", "cobranca", "parcelada", "garantida", "suspensa"]
S = {s: i for i, s in enumerate(SITUACOES)}
NAO_ATIVA = {"01", "03", "04", "08"}  # nula, suspensa, inapta, baixada (02 é ativa)
EMPRESARIO_INDIVIDUAL = "2135"
CPF_NO_NOME = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
MAIORES_CIDADE = 10
MAIORES_BRASIL = 20


def situacao(tipo: str, ajuizado: str) -> int | None:
    if tipo == "Em cobrança":
        return S["justica"] if ajuizado == "SIM" else S["cobranca"]
    return {"Benefício Fiscal": S["parcelada"], "Em negociação": S["parcelada"], "Garantia": S["garantida"],
            "Suspenso por decisão judicial": S["suspensa"]}.get(tipo)


# ---------------------------------------------------------------- downloads

def _abrir(url: str, receita: bool = False, metodo: str = "GET", cab: dict | None = None):
    h = {"User-Agent": USER_AGENT, **(cab or {})}
    if receita:
        import base64
        h["Authorization"] = "Basic " + base64.b64encode(f"{TOKEN_RECEITA}:".encode()).decode()
    req = urllib.request.Request(url, headers=h, method=metodo)
    return urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS)


def _baixar(url: str, destino: Path, receita: bool = False) -> Path:
    """Baixa para destino (com .part e retomada); não baixa de novo se já existe."""
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_name(destino.name + ".part")
    for tentativa in range(6):
        ja = parte.stat().st_size if parte.exists() else 0
        try:
            with _abrir(url, receita, cab={"Range": f"bytes={ja}-"} if ja else None) as r, parte.open("ab" if ja else "wb") as f:
                if ja and r.status != 206:
                    f.truncate(0)
                shutil.copyfileobj(r, f, 8 << 20)
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 416):
                raise
            print(f"    {destino.name}: {e}; tentando de novo", flush=True)
            time.sleep(10 * (tentativa + 1))
    else:
        raise RuntimeError(f"{url}: não baixou")
    if not zipfile.is_zipfile(parte):
        raise RuntimeError(f"{url}: a resposta não é um zip")
    parte.rename(destino)
    return destino


def ultimo_trimestre() -> str:
    """O trimestre mais recente com os três arquivos publicados."""
    with _abrir(URL_PGFN) as r:
        pastas = sorted(set(re.findall(r'href="(\d{4}_trimestre_\d{2})/"', r.read().decode("latin-1"))), reverse=True)
    for tri in pastas:
        with _abrir(URL_PGFN + tri + "/") as r:
            html = r.read().decode("latin-1")
        if all(any(f"{n}.zip" in html for n in nomes) for nomes in TIPOS.values()):
            return tri
    raise RuntimeError("nenhum trimestre completo na PGFN")


def ultimo_mes_receita() -> str:
    with _abrir(URL_RECEITA, receita=True, metodo="PROPFIND", cab={"Depth": "1"}) as r:
        return max(re.findall(r"/webdav/(\d{4}-\d{2})/", r.read().decode()))


def arquivos_pgfn(tri: str) -> dict[str, Path]:
    pasta = PASTA / tri
    with _abrir(URL_PGFN + tri + "/") as r:
        html = r.read().decode("latin-1")
    saida = {}
    for tipo, nomes in TIPOS.items():
        nome = next(n for n in nomes if f"{n}.zip" in html)
        print(f"  {tri}/{nome}.zip", flush=True)
        saida[tipo] = _baixar(f"{URL_PGFN}{tri}/{nome}.zip", pasta / f"{nome}.zip")
    return saida


# ---------------------------------------------------------------- 1. a lista da PGFN

class Devedores:
    """As empresas devedoras (uma linha por CNPJ), em colunas compactas, e os totais das pessoas."""

    def __init__(self) -> None:
        self.indice: dict[int, int] = {}
        self.cols = [array("d") for _ in range(len(T) + len(SITUACOES))]
        self.nome: list[str] = []
        self.uf: list[str] = []
        self.pf_valor: dict[str, float] = defaultdict(float)
        self.pf_quem: dict[str, set[int]] = defaultdict(set)  # hash em memória, nunca gravado
        self.pf_tipos = [0.0] * len(T)
        self.pf_situacoes = [0.0] * len(SITUACOES)
        self.posicao = ""
        self.ignorados: dict[str, float] = defaultdict(float)

    def ler(self, tipo: str, arq: Path) -> None:
        t = T.index(tipo)
        cols, indice = self.cols, self.indice
        with zipfile.ZipFile(arq) as z:
            for membro in z.namelist():
                if m := re.search(r"_(\d{6})\.csv$", membro):
                    self.posicao = max(self.posicao, m.group(1))
                leitor = csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";")
                cab = next(leitor)
                i_doc, i_pessoa, i_dev, i_nome, i_uf = (cab.index(c) for c in
                                                         ("CPF_CNPJ", "TIPO_PESSOA", "TIPO_DEVEDOR", "NOME_DEVEDOR", "UF_DEVEDOR"))
                i_sit, i_aj, i_val = (cab.index(c) for c in ("TIPO_SITUACAO_INSCRICAO", "INDICADOR_AJUIZADO", "VALOR_CONSOLIDADO"))
                for l in leitor:
                    v = float(l[i_val] or 0)
                    if l[i_dev].upper() != "PRINCIPAL":  # "Principal" ou "PRINCIPAL", conforme o arquivo
                        self.ignorados["corresponsável"] += v  # o mesmo débito de novo, em nome de outro
                        continue
                    s = situacao(l[i_sit], l[i_aj])
                    if s is None:
                        self.ignorados[f"situação {l[i_sit]}"] += v
                        s = S["cobranca"]
                    uf = l[i_uf]
                    if l[i_pessoa] == "Pessoa física":
                        # Pessoa: só o valor e a contagem, pela UF. O hash junta CPF mascarado e nome e
                        # fica só na memória deste programa.
                        self.pf_valor[uf] += v
                        self.pf_tipos[t] += v
                        self.pf_situacoes[s] += v
                        self.pf_quem[uf].add(hash((l[i_doc], l[i_nome])))
                        continue
                    d = re.sub(r"\D", "", l[i_doc])
                    if len(d) != 14:
                        self.ignorados["CNPJ inválido"] += v
                        continue
                    k = indice.get(cnpj := int(d))
                    if k is None:
                        k = indice[cnpj] = len(self.nome)
                        for c in cols:
                            c.append(0.0)
                        self.nome.append(l[i_nome].strip())
                        self.uf.append(uf)
                    cols[t][k] += v
                    cols[len(T) + s][k] += v
                print(f"    {membro}: {len(self.nome):,} empresas até aqui", flush=True)


# ---------------------------------------------------------------- 2. o cadastro de CNPJ

def cadastro(dev: Devedores, mes: str, pasta: Path) -> tuple[array, array, dict[int, str]]:
    """Para cada empresa devedora: o município (código SIAFI), se está ativa e a natureza jurídica.

    O resultado fica em cache (cadastro-{mes}.csv, só os CNPJs devedores); os arquivos da Receita são
    baixados um por vez e apagados depois de lidos (~6,7 GB, uns 35 minutos)."""
    n = len(dev.nome)
    municipio = array("H", bytes(2 * n))
    ativa = array("b", [-1]) * n  # -1: não achada; 0: fechada ou inativa; 1: ativa
    natureza: dict[int, str] = {}
    cache = pasta / f"cadastro-{mes}.csv"
    if cache.exists():
        with cache.open(encoding="utf-8") as f:
            for cnpj, mun, at, nat in csv.reader(f, delimiter=";"):
                if (k := dev.indice.get(int(cnpj))) is not None:
                    municipio[k], ativa[k] = int(mun), int(at)
                if nat:
                    natureza[int(cnpj) // 1_000_000] = nat
        return municipio, ativa, natureza

    # Cada arquivo da Receita vira uma parte pequena em cadastro-{mes}/ (só os devedores), para uma falha no
    # meio não obrigar a baixar tudo de novo.
    partes = pasta / f"cadastro-{mes}"
    partes.mkdir(parents=True, exist_ok=True)
    basicos = {c // 1_000_000 for c in dev.indice}
    tmp = RAIZ / "data" / "raw" / "receita-federal" / "cnpj-tmp"
    for prefixo in ("Estabelecimentos", "Empresas"):
        for i in range(10):
            parte = partes / f"{prefixo}{i}.csv"
            if parte.exists():
                continue
            arq = _baixar(f"{URL_RECEITA}{mes}/{prefixo}{i}.zip", tmp / f"{prefixo}{i}.zip", receita=True)
            achadas = 0
            with zipfile.ZipFile(arq) as z, (parte.with_suffix(".part")).open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, delimiter=";")
                for membro in z.namelist():
                    leitor = csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";")
                    for r in leitor:
                        # CNPJ com letras (o alfanumérico, desde julho de 2026): é empresa nova, que ainda não
                        # aparece na lista da PGFN.
                        if not r[0].isdigit() or int(r[0]) not in basicos:
                            continue
                        if prefixo == "Empresas":
                            w.writerow(["n", r[0], r[2]])
                            achadas += 1
                            continue
                        mun, at = int(r[20] or 0), int(r[5] not in NAO_ATIVA)
                        if r[1] == "0001":
                            w.writerow(["m", r[0], mun, at])
                        if (r[0] + r[1] + r[2]).isdigit() and int(r[0] + r[1] + r[2]) in dev.indice:
                            w.writerow(["e", r[0] + r[1] + r[2], mun, at])
                            achadas += 1
            parte.with_suffix(".part").rename(parte)
            arq.unlink()
            print(f"    {prefixo}{i}: {achadas:,} devedores", flush=True)
    matriz: dict[int, tuple[int, int]] = {}
    for parte in sorted(partes.glob("*.csv")):
        with parte.open(encoding="utf-8") as f:
            for r in csv.reader(f, delimiter=";"):
                if r[0] == "n":
                    natureza[int(r[1])] = r[2]
                elif r[0] == "m":
                    matriz[int(r[1])] = (int(r[2]), int(r[3]))
                elif (k := dev.indice.get(int(r[1]))) is not None:
                    municipio[k], ativa[k] = int(r[2]), int(r[3])
    # CNPJ de filial que não está mais no cadastro: vale a cidade da matriz.
    for cnpj, k in dev.indice.items():
        if ativa[k] == -1 and (m := matriz.get(cnpj // 1_000_000)):
            municipio[k], ativa[k] = m
    with cache.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        for cnpj, k in dev.indice.items():
            w.writerow([cnpj, municipio[k], ativa[k], natureza.get(cnpj // 1_000_000, "")])
    shutil.rmtree(partes)
    return municipio, ativa, natureza


# ---------------------------------------------------------------- 3. somas

def _cnpj(c: int) -> str:
    d = f"{c:014d}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def e_pessoa(nat: str) -> bool:
    """Natureza jurídica de quem tem CNPJ mas é uma pessoa: o empresário individual e o MEI (213-5) e o grupo 4 da
    tabela da Receita, "pessoas físicas" (produtor rural, empresa individual imobiliária, candidato, leiloeiro…)."""
    return nat == EMPRESARIO_INDIVIDUAL or nat.startswith("4")


def _pode_nomear(nome: str, nat: str) -> bool:
    return not e_pessoa(nat) and not CPF_NO_NOME.search(nome) and not re.search(r"\d{11}", nome)


def montar(dev: Devedores, municipio: array, ativa: array, natureza: dict[int, str], tri: str, mes: str) -> dict:
    siafi = siafi_para_ibge()
    nt, ns = len(T), len(SITUACOES)
    vazio = lambda: {"t": [0.0] * nt, "s": [0.0] * ns, "pub": 0.0, "fech": 0.0, "ind": 0.0,  # noqa: E731
                     "emp": defaultdict(lambda: [0.0, [0.0] * ns, "", "", 0, 0.0])}
    mun: dict = defaultdict(vazio)
    brasil = vazio()
    uf_sem: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    uf_pj: dict[str, float] = defaultdict(float)
    sem_mun = 0
    for cnpj, k in dev.indice.items():
        t = [dev.cols[j][k] for j in range(nt)]
        s = [dev.cols[nt + j][k] for j in range(ns)]
        v = sum(t)
        if v <= 0:
            continue
        b = cnpj // 1_000_000
        nat = natureza.get(b, "")
        ibge = siafi.get(f"{municipio[k]:04d}") if municipio[k] else None
        alvos = [brasil] + ([mun[ibge]] if ibge else [])
        if not ibge:
            sem_mun += 1
            uf_sem[dev.uf[k]][0] += v
            uf_sem[dev.uf[k]][1] += 1
        uf_pj[dev.uf[k]] += v
        for a in alvos:
            for j in range(nt):
                a["t"][j] += t[j]
            for j in range(ns):
                a["s"][j] += s[j]
            if nat.startswith("1"):
                a["pub"] += v
            if e_pessoa(nat):
                a["ind"] += v
            if ativa[k] == 0:
                a["fech"] += v
            e = a["emp"][b]
            e[0] += v
            for j in range(ns):
                e[1][j] += s[j]
            if v > e[5]:  # o nome e o CNPJ do estabelecimento que mais deve
                e[2], e[3], e[4], e[5] = dev.nome[k], cnpj, ibge or 0, v

    def maiores(emp: dict, n: int, com_cidade: bool) -> list:
        lista = []
        for b, (v, s, nome, cnpj, ibge, _) in sorted(emp.items(), key=lambda x: -x[1][0]):
            if not _pode_nomear(nome, natureza.get(b, "")):
                continue
            item = [nome, _cnpj(cnpj), round(v), max(range(ns), key=lambda j: s[j])]
            if com_cidade:
                item.append(_chave(ibge) if ibge else None)
            lista.append(item)
            if len(lista) == n:
                break
        return lista

    def resumo(a: dict) -> dict:
        return {"total": round(sum(a["t"])), "tipos": [round(x) for x in a["t"]], "situacoes": [round(x) for x in a["s"]],
                "empresas": len(a["emp"]), "publico": round(a["pub"]), "fechadas": round(a["fech"]),
                "individuais": round(a["ind"])}

    saida = {}
    for ibge, a in sorted(mun.items()):
        r = resumo(a)
        saida[_chave(ibge)] = [r["total"], r["tipos"], r["situacoes"], r["empresas"], r["publico"], r["fechadas"],
                               maiores(a["emp"], MAIORES_CIDADE, False)]
    pf_total = sum(dev.pf_valor.values())
    pf_n = sum(len(x) for x in dev.pf_quem.values())
    b = resumo(brasil)
    ufs = sorted(set(uf_pj) | set(dev.pf_valor))
    return {
        "trimestre": tri, "posicao": f"{dev.posicao[4:]}/{dev.posicao[:4]}", "receita": mes, "fonte": FONTE,
        "tipos": T, "situacoes": SITUACOES,
        "colunas": ["total", "tipos", "situacoes", "empresas", "publico", "fechadas", "maiores"],
        "maiores_colunas": ["nome", "cnpj", "valor", "situacao"],
        "brasil": {
            **b, "total": b["total"] + round(pf_total), "empresas_valor": b["total"],
            # Tipos e situações do país contam empresas e pessoas.
            "tipos": [round(x + y) for x, y in zip(brasil["t"], dev.pf_tipos)],
            "situacoes": [round(x + y) for x, y in zip(brasil["s"], dev.pf_situacoes)],
            "pessoas": [round(pf_total), pf_n], "sem_cidade": [round(sum(x[0] for x in uf_sem.values())), sem_mun],
            "cidades": len(saida), "maiores": maiores(brasil["emp"], MAIORES_BRASIL, True),
        },
        # UF: [dívida das empresas, dívida das pessoas, nº de pessoas, empresas sem cidade (valor, nº)]
        "uf": {u: [round(uf_pj[u]), round(dev.pf_valor[u]), len(dev.pf_quem[u]), round(uf_sem[u][0]), uf_sem[u][1]]
               for u in ufs if u and len(u) == 2},
        "mun": saida,
    }


def _chave(ibge: str) -> str:
    return "53" if ibge == "5300108" else ibge  # o site chama o Distrito Federal de 53


# ---------------------------------------------------------------- main

def copiar_referencia() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REFERENCIA, SAIDA)
    print(f"saída: {SAIDA.relative_to(RAIZ)} (cópia de {REFERENCIA.relative_to(RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(prog="divida-ativa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--trimestre", help="ex.: 2026_trimestre_03 (padrão: o último completo)")
    p.add_argument("--receita", help="mês do cadastro de CNPJ, ex.: 2026-11 (padrão: o último)")
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return
    try:
        tri = args.trimestre or ultimo_trimestre()
        mes = args.receita or ultimo_mes_receita()
        print(f"PGFN {tri}; cadastro de CNPJ {mes}", flush=True)
        arqs = arquivos_pgfn(tri)
    except Exception as erro:  # noqa: BLE001 — qualquer falha de download cai na cópia versionada
        if REFERENCIA.exists():
            print(f"  aviso: download falhou ({erro}); usando a cópia versionada", flush=True)
            copiar_referencia()
            return
        raise
    dev = Devedores()
    for tipo, arq in arqs.items():
        dev.ler(tipo, arq)
    for motivo, v in dev.ignorados.items():
        print(f"  fora da soma: {motivo}, R$ {v / 1e9:.2f} bi")
    municipio, ativa, natureza = cadastro(dev, mes, PASTA / tri)
    doc = montar(dev, municipio, ativa, natureza, tri, mes)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    b = doc["brasil"]
    bi = lambda v: f"R$ {v / 1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    print(f"posição {doc['posicao']}: estoque {bi(b['total'])}; empresas {bi(b['empresas_valor'])} ({b['empresas']:,} CNPJs), "
          f"pessoas {bi(b['pessoas'][0])} ({b['pessoas'][1]:,}); sem cidade {bi(b['sem_cidade'][0])} ({b['sem_cidade'][1]:,})")
    print("  tipos: " + ", ".join(f"{t} {bi(v)}" for t, v in zip(T, b["tipos"])))
    print("  situações: " + ", ".join(f"{s} {bi(v)}" for s, v in zip(SITUACOES, b["situacoes"])))
    print(f"  órgãos públicos {bi(b['publico'])}; empresas fechadas ou inativas {bi(b['fechadas'])}; "
          f"pessoas com CNPJ {bi(b['individuais'])}; {b['cidades']} cidades")
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
