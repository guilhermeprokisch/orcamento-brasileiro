"""Dinheiro federal que chega a cada município num ano (Portal da Transparência).

    uv run federal 2025                              # repasses + benefícios já somados
    uv run federal 2025 --beneficios ~/Downloads     # soma antes os zips de Bolsa Família e BPC

Junta três coisas em site/public/data/mapa/federal-{ano}.json:

- Repasses ("Transferências", ~2,5 MB por mês, baixados aqui): por município, separados
  por programa (FPM, SUS, FUNDEB, royalties, educação, assistência, outros) quando vão para
  a prefeitura, e somados quando vão para outras entidades da cidade.
- Bolsa Família e BPC: os arquivos do Portal têm uma linha por beneficiário (nome, CPF, NIS)
  e somam ~6,5 GB por ano. O servidor bloqueia downloads automáticos em série com CAPTCHA,
  então os zips são baixados à mão e lidos com `--beneficios`. Só a soma por município é
  gravada, em pipeline/referencia/beneficios/ (versionada: refazer exige baixar tudo de novo).
  Nenhum dado pessoal sai do zip.

O Portal identifica o município pelo código SIAFI; a tabela do Tesouro (tabmun.csv) dá o
código do IBGE.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA_BRUTO = RAIZ / "data" / "raw" / "portal-transparencia"
PASTA_BENEFICIOS = RAIZ / "pipeline" / "referencia" / "beneficios"
SAIDA = RAIZ / "site" / "public" / "data" / "mapa"
URL_TRANSFERENCIAS = ("https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/"
                      "transferencias/{am}_Transferencias.zip")
URL_TABMUN = ("https://www.tesourotransparente.gov.br/ckan/dataset/abb968cb-3710-4f85-89cf-875c91b9c7f6/"
              "resource/eebb3bc6-9eea-4496-8bcf-304f33155282/download/tabmun.csv")

# Ordem das colunas de cada município no arquivo de saída.
PROGRAMAS = ["fpm", "saude", "fundeb", "royalties", "educacao", "assistencia", "outros"]
COLUNAS = PROGRAMAS + ["entidades", "bolsa_familia", "bpc"]
BENEFICIOS = {"novo-bolsa-familia": "NovoBolsaFamilia", "bpc": "BPC"}


def _baixar(url: str, destino: Path) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
            dados = resp.read()
        if not dados.startswith(b"PK") and destino.suffix == ".zip":
            raise RuntimeError(f"{url}: a resposta não é um zip (o Portal pode estar pedindo CAPTCHA)")
        destino.write_bytes(dados)
    return destino


def siafi_para_ibge() -> dict[str, str]:
    arq = _baixar(URL_TABMUN, RAIZ / "data" / "raw" / "tesouro" / "tabmun.csv")
    mapa = {}
    for linha in arq.read_text(encoding="latin-1").splitlines():
        p = linha.split(";")
        if len(p) >= 5:
            mapa[p[0].strip().zfill(4)] = p[4].strip()
    return mapa


def _programa(l: dict) -> str:
    cidada = (l["LINGUAGEM CIDADÃ"] or "").upper()
    acao = (l["NOME AÇÃO"] or "").upper()
    if cidada.startswith(("FPM", "FPE")):
        return "fpm"  # nos estados, o fundo de participação é o FPE
    if "FUNDEB" in cidada or "FUNDEB" in acao:
        return "fundeb"
    if any(t in cidada for t in ("ROYALT", "CFEM", "CFURH", "COMPENSA")) or "ROYALT" in acao or "COMPENSACAO FINANCEIRA" in acao:
        return "royalties"
    return {"10": "saude", "12": "educacao", "08": "assistencia"}.get(l["CÓDIGO FUNÇÃO"].strip(), "outros")


def repasses(ano: int, siafi: dict[str, str]) -> tuple[dict, dict]:
    """(por município, por estado) dos repasses da União no ano."""
    mun: dict = defaultdict(lambda: {"pref": defaultdict(float), "ent": 0.0})
    uf: dict = defaultdict(lambda: defaultdict(float))
    for mes in range(1, 13):
        am = f"{ano}{mes:02d}"
        arq = _baixar(URL_TRANSFERENCIAS.format(am=am), PASTA_BRUTO / "transferencias" / f"{am}_Transferencias.zip")
        with zipfile.ZipFile(arq) as z:
            texto = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1", newline="")
            for l in csv.DictReader(texto, delimiter=";"):
                v = float(l["VALOR TRANSFERIDO"].replace(".", "").replace(",", "."))
                tipo, nome = l["TIPO FAVORECIDO"], l["NOME FAVORECIDO"].upper()
                # "Administração Pública" genérica são os fundos de saúde e de assistência:
                # fundo municipal conta como prefeitura; fundo estadual, como governo do estado.
                fundo_estadual = tipo == "Administração Pública" and any(t in nome for t in ("ESTADUAL", "ESTADO", "DISTRITO FEDERAL"))
                if tipo.startswith("Administração Pública Estadual") or fundo_estadual:
                    uf[l["UF"]][_programa(l)] += v
                    continue
                cod = l["CÓDIGO MUNICÍPIO SIAFI"].strip()
                ibge = siafi.get(cod.zfill(4)) if cod else None
                if not ibge:
                    continue
                if tipo in ("Administração Pública Municipal", "Administração Pública"):
                    mun[ibge]["pref"][_programa(l)] += v
                else:
                    mun[ibge]["ent"] += v
        print(f"  repasses {am}", flush=True)
    return mun, uf


def somar_beneficios(pasta: Path, ano: int) -> None:
    """Soma por município cada zip de Bolsa Família/BPC da pasta e grava "siafi;valor;parcelas"."""
    PASTA_BENEFICIOS.mkdir(parents=True, exist_ok=True)
    for prog, sufixo in BENEFICIOS.items():
        for arq in sorted(pasta.glob(f"{ano}??_{sufixo}*.zip")):
            alvo = PASTA_BENEFICIOS / f"{prog}-{arq.name[:6]}.csv"
            if alvo.exists():
                continue
            soma: dict[bytes, float] = defaultdict(float)
            parcelas: dict[bytes, int] = defaultdict(int)
            with zipfile.ZipFile(arq) as z, z.open(z.namelist()[0]) as linhas:
                next(linhas)
                for linha in linhas:
                    # O município é a 4ª coluna e o valor é a última: não depende dos nomes no meio.
                    cod = linha.split(b";", 4)[3].strip(b'"')
                    v = linha.rsplit(b";", 1)[1].strip(b'"\r\n').replace(b".", b"").replace(b",", b".")
                    soma[cod] += float(v or 0)
                    parcelas[cod] += 1
            alvo.write_text("".join(f"{k.decode('latin-1')};{soma[k]:.2f};{parcelas[k]}\n" for k in sorted(soma)))
            print(f"  {prog} {arq.name[:6]}: {len(soma)} municípios, R$ {sum(soma.values()) / 1e9:.2f} bi", flush=True)


def ler_beneficios(ano: int, siafi: dict[str, str]) -> tuple[dict, dict]:
    """({programa: {ibge: valor}}, {programa: [meses com dados]})."""
    valores: dict = {p: defaultdict(float) for p in BENEFICIOS}
    meses: dict = {}
    for prog in BENEFICIOS:
        arqs = sorted(PASTA_BENEFICIOS.glob(f"{prog}-{ano}??.csv"))
        meses[prog] = [a.stem[-2:] for a in arqs]
        for a in arqs:
            for linha in a.read_text().splitlines():
                cod, v, _parcelas = linha.split(";")
                ibge = siafi.get(cod.zfill(4)) if cod else None
                if ibge:
                    valores[prog][ibge] += float(v)
    return valores, meses


def main() -> None:
    p = argparse.ArgumentParser(prog="federal", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    p.add_argument("--beneficios", type=Path, help="pasta com os zips de Bolsa Família e BPC baixados à mão")
    args = p.parse_args()

    siafi = siafi_para_ibge()
    if args.beneficios:
        somar_beneficios(args.beneficios.expanduser(), args.ano)
    mun, uf = repasses(args.ano, siafi)
    ben, meses = ler_beneficios(args.ano, siafi)
    faltam = {p: 12 - len(m) for p, m in meses.items() if len(m) < 12}
    if faltam:
        print(f"  aviso: benefícios incompletos (meses que faltam: {faltam}); o mapa projeta o ano a partir dos meses que há")

    saida = {}
    for ibge in set(mun) | set(ben["novo-bolsa-familia"]) | set(ben["bpc"]):
        r = mun.get(ibge, {"pref": {}, "ent": 0.0})
        saida[ibge] = [round(r["pref"].get(c, 0)) for c in PROGRAMAS] + [
            round(r["ent"]), round(ben["novo-bolsa-familia"].get(ibge, 0)), round(ben["bpc"].get(ibge, 0))]
    doc = {"ano": args.ano, "fonte": "Portal da Transparência (CGU)", "colunas": COLUNAS, "meses_beneficios": meses,
           "mun": saida, "uf": {k: {c: round(v.get(c, 0)) for c in PROGRAMAS} for k, v in uf.items() if k}}
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"federal-{args.ano}.json").write_text(json.dumps(doc, separators=(",", ":")))
    totais = {c: round(sum(v[i] for v in saida.values()) / 1e9, 1) for i, c in enumerate(COLUNAS)}
    print(f"{len(saida)} municípios; R$ bi: {totais}")


if __name__ == "__main__":
    main()
