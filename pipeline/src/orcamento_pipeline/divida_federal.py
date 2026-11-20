"""Dívida pública federal: quanto é, quem empresta, de que tipo, quando vence e quanto custa.

    uv run divida-federal               # baixa o último Relatório Mensal da Dívida e as séries do Banco Central
    uv run divida-federal --sem-baixar  # só copia pipeline/referencia/divida-federal.json (publicação)

Fontes (ver docs/divida-federal.md):
- Tesouro Nacional, anexo do Relatório Mensal da Dívida (RMD), uma planilha com a história mês a mês.
  A página da publicação sempre redireciona para a edição mais recente; nela, o link "Anexo RMD_…zip".
  Abas usadas (dívida pública federal em poder do público, a DPF, em R$ bilhões):
    2.4  composição por indexador (prefixado, índice de preços, taxa flutuante, câmbio, demais)
    2.7  detentores dos títulos da dívida interna (DPMFi): bancos, fundos, previdência, estrangeiros…
    3.1  quanto vence em até 12 meses
    3.7  prazo médio (anos), linha "DPF"
    4.2  custo médio acumulado em 12 meses (% ao ano), linha "DPF"
- Banco Central, séries do SGS (api.bcb.gov.br, sem chave):
    13761  dívida bruta do governo geral (DBGG), R$ milhões
    13762  DBGG, % do PIB
    4607   juros nominais do Governo Federal, fluxo do mês, R$ milhões (NFSP sem desvalorização cambial)
    5751   os mesmos juros, acumulados em 12 meses, % do PIB
    4382   PIB acumulado em 12 meses, R$ milhões (para pôr a DPF em % do PIB)

Cache do anexo em data/raw/tesouro/rmd/. Saída em site/public/data/federal/divida.json, com cópia
versionada em pipeline/referencia/divida-federal.json (usada com --sem-baixar ou se o download falhar):
    {"fonte": …, "rmd": {"mes": "2026-09", "url": …}, "meses": ["2014-01", …],
     "dpf": [R$ bi], "pib12": [R$ bi], "dbgg": [R$ bi], "dbgg_pib": [%],
     "indexador": {"prefixado": [R$ bi], …}, "detentores": {"bancos": [R$ bi], …},
     "vence_12m": [R$ bi], "prazo_medio": [anos], "custo_medio": [% a.a.],
     "juros": {"2025": [R$ bi, % do PIB], …}, "juros_12m": {"ate": "2026-09", "valor": R$ bi, "pib": %}}
As listas mensais seguem "meses" (de janeiro de 2014 ao mês do último RMD); null onde falta o dado.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import unicodedata
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

PAGINA_RMD = "https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd"
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json&dataInicial=01/01/{ano}&dataFinal=31/12/2099"
PASTA_BRUTO = c.RAIZ / "data" / "raw" / "tesouro" / "rmd"
SAIDA = c.RAIZ / "site" / "public" / "data" / "federal" / "divida.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "divida-federal.json"
PRIMEIRO_ANO = 2014
FONTE = ("Tesouro Nacional, Relatório Mensal da Dívida (anexo); Banco Central, séries 13761, 13762, 4607, 5751 "
         "e 4382 do SGS")

MESES_PT = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9,
            "out": 10, "nov": 11, "dez": 12}
NOMES_MES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro"]

# Rótulo da coluna (sem acento, minúsculo, sem as notas de rodapé) → chave no JSON.
INDEXADORES = {"prefixado": "prefixado", "indice precos": "inflacao", "taxa flutuante": "selic",
               "cambio": "cambio", "demais": "demais", "total": "total"}
DETENTORES = {"instituicoes financeiras": "bancos", "fundos de investimento": "fundos", "previdencia": "previdencia",
              "nao-residentes": "estrangeiros", "tesouro direto": "tesouro_direto", "governo": "governo",
              "seguradoras": "seguradoras", "outros": "outros", "total": "total"}


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=CONTEXTO_TLS) as resp:
        return resp.read()


def _normal(s: object) -> str:
    """'Instituições Financeiras 1' → 'instituicoes financeiras'."""
    t = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+\d+$", "", re.sub(r"\s+", " ", t).strip())


def _mes(v: object) -> str | None:
    """Uma data da planilha (datetime, 'Set/26' ou 'mar/18*', com a marca de dado corrigido) como '2026-09'."""
    if isinstance(v, (datetime, date)):
        return f"{v.year}-{v.month:02d}"
    if isinstance(v, str) and (m := re.fullmatch(r"\s*([A-Za-zç]{3})/(\d{2})\*?\s*", v)) and m.group(1).lower() in MESES_PT:
        return f"{2000 + int(m.group(2))}-{MESES_PT[m.group(1).lower()]:02d}"
    return None


def _num(v: object) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


# ── Tesouro: anexo do RMD ────────────────────────────────────────────────────────────────────────

def baixar_anexo() -> tuple[bytes, str, str]:
    """(planilha .xlsx, nome do arquivo, endereço da edição) do RMD mais recente."""
    pagina = urllib.request.urlopen(urllib.request.Request(PAGINA_RMD, headers={"User-Agent": USER_AGENT}),
                                    timeout=120, context=CONTEXTO_TLS)
    url_edicao, html = pagina.geturl(), pagina.read().decode("utf-8", "replace")
    achado = re.search(r'href="(https://thot-arquivos\.tesouro\.gov\.br/publicacao-anexo/\d+)"[^>]*title="(Anexo[^"]*\.(?:zip|xlsx))"', html, re.I)
    if not achado:
        raise ValueError(f"link do anexo não encontrado em {url_edicao}")
    url, nome = achado.groups()
    cache = PASTA_BRUTO / nome
    if cache.exists():
        dados = cache.read_bytes()
    else:
        print(f"  baixando {nome}", flush=True)
        dados = _get(url, timeout=300)
        PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(dados)
    if nome.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            planilha = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
            dados = z.read(planilha)
    return dados, nome, url_edicao


def serie_longa(ws, rotulos: dict[str, str]) -> dict[str, dict[str, float]]:
    """Aba com um mês por linha e, para cada rótulo do cabeçalho, uma coluna de valor (e outra de %).

    Lê só o primeiro bloco (na aba 3.1, o da DPF; os blocos seguintes são da DPMFi e da DPFe)."""
    colunas: dict[str, int] = {}
    saida: dict[str, dict[str, float]] = {}
    for linha in ws.iter_rows(values_only=True):
        if not colunas:
            if _normal(linha[0]) == "mes":
                colunas = {rotulos[_normal(v)]: i for i, v in enumerate(linha) if _normal(v) in rotulos}
            continue
        mes = _mes(linha[0])
        if mes is None:
            if saida:
                break
            continue
        if int(mes[:4]) >= PRIMEIRO_ANO:
            saida[mes] = {k: v for k, i in colunas.items() if (v := _num(linha[i])) is not None}
    if not saida:
        raise ValueError(f"aba {ws.title}: nenhuma linha de dados")
    return saida


def serie_larga(ws, rotulo: str) -> dict[str, float]:
    """Aba com um mês por coluna ('Set/26' no cabeçalho): os valores da linha cujo rótulo é `rotulo`."""
    cabecalho: list[str | None] = []
    for linha in ws.iter_rows(values_only=True):
        meses = [_mes(v) for v in linha]
        if sum(m is not None for m in meses) > 12:
            cabecalho = meses
        elif cabecalho and _normal(linha[0]) == rotulo.lower():
            return {m: v for m, x in zip(cabecalho, linha) if m and int(m[:4]) >= PRIMEIRO_ANO and (v := _num(x)) is not None}
    raise ValueError(f"aba {ws.title}: linha {rotulo!r} não encontrada")


def ler_anexo(xlsx: bytes) -> dict:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    venc = serie_longa(wb["3.1"], {"ate 12 meses": "ate12", "total": "total"})
    return {
        "indexador": serie_longa(wb["2.4"], INDEXADORES),
        "detentores": serie_longa(wb["2.7"], DETENTORES),
        "vence_12m": {m: v["ate12"] for m, v in venc.items() if "ate12" in v},
        "prazo_medio": serie_larga(wb["3.7"], "DPF"),
        "custo_medio": serie_larga(wb["4.2"], "DPF"),
    }


# ── Banco Central: SGS ───────────────────────────────────────────────────────────────────────────

def sgs(serie: int) -> dict[str, float]:
    """Série mensal do SGS como {'2026-09': valor}."""
    dados = json.loads(_get(SGS.format(serie=serie, ano=PRIMEIRO_ANO)))
    saida = {}
    for p in dados:
        d, m, a = p["data"].split("/")
        if p.get("valor") not in (None, ""):
            saida[f"{a}-{m}"] = float(p["valor"])
    if not saida:
        raise ValueError(f"série {serie} do SGS veio vazia")
    return saida


# ── Montagem ─────────────────────────────────────────────────────────────────────────────────────

def montar(anexo: dict, bc: dict[int, dict[str, float]], nome: str, url: str) -> dict:
    ultimo = max(anexo["indexador"])
    a0, m0 = PRIMEIRO_ANO, 1
    meses = []
    while (a0, m0) <= (int(ultimo[:4]), int(ultimo[5:])):
        meses.append(f"{a0}-{m0:02d}")
        a0, m0 = (a0 + 1, 1) if m0 == 12 else (a0, m0 + 1)

    r = lambda v, n=2: None if v is None else round(v, n)
    lista = lambda d, n=2: [r(d.get(m), n) for m in meses]
    dpf = {m: v["total"] for m, v in anexo["indexador"].items() if "total" in v}
    mi = lambda serie: {m: v / 1000 for m, v in bc[serie].items()}  # R$ milhões → bilhões

    juros_mes = mi(4607)
    juros: dict[str, list] = {}
    for ano in range(PRIMEIRO_ANO, int(ultimo[:4]) + 1):
        doze = [juros_mes.get(f"{ano}-{m:02d}") for m in range(1, 13)]
        if all(v is not None for v in doze):
            juros[str(ano)] = [round(sum(doze), 1), r(bc[5751].get(f"{ano}-12"))]
    fim_juros = max(juros_mes)
    a, m = int(fim_juros[:4]), int(fim_juros[5:])
    ultimos12 = [juros_mes.get(f"{a - (k > m - 1)}-{(m - 1 - k) % 12 + 1:02d}") for k in range(12)]

    return {
        "fonte": FONTE,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rmd": {"mes": ultimo, "arquivo": nome, "url": url,
                "titulo": f"Relatório Mensal da Dívida de {NOMES_MES[int(ultimo[5:]) - 1]} de {ultimo[:4]}"},
        "meses": meses,
        "dpf": lista(dpf),
        "pib12": lista(mi(4382), 1),
        "dbgg": lista(mi(13761), 1),
        "dbgg_pib": lista(bc[13762]),
        "indexador": {k: lista({mm: v.get(k) for mm, v in anexo["indexador"].items()})
                      for k in INDEXADORES.values() if k != "total"},
        "detentores": {k: lista({mm: v.get(k) for mm, v in anexo["detentores"].items()})
                       for k in DETENTORES.values()},
        "vence_12m": lista(anexo["vence_12m"]),
        "prazo_medio": lista(anexo["prazo_medio"]),
        "custo_medio": lista(anexo["custo_medio"]),
        "juros": juros,
        "juros_12m": {"ate": fim_juros, "valor": round(sum(ultimos12), 1) if None not in ultimos12 else None,
                      "pib": r(bc[5751].get(fim_juros))},
    }


def resumo(doc: dict) -> str:
    i = len(doc["meses"]) - 1
    while doc["dpf"][i] is None:
        i -= 1
    det = doc["detentores"]
    tot = det["total"][i]
    fatias = ", ".join(f"{k} {det[k][i] / tot:.1%}" for k in det if k != "total" and det[k][i] is not None)
    return (f"{doc['meses'][i]}: DPF R$ {doc['dpf'][i]:,.2f} bi ({doc['dpf'][i] / doc['pib12'][i]:.1%} do PIB); "
            f"vence em 12 meses {doc['vence_12m'][i] / doc['dpf'][i]:.2%}; prazo médio {doc['prazo_medio'][i]} anos; "
            f"custo médio {doc['custo_medio'][i]}% a.a.; DBGG {doc['dbgg_pib'][i]}% do PIB\n  detentores: {fatias}\n"
            f"  juros (governo federal, 12 meses até {doc['juros_12m']['ate']}): R$ {doc['juros_12m']['valor']} bi, "
            f"{doc['juros_12m']['pib']}% do PIB")


def copiar_referencia() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REFERENCIA, SAIDA)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia de {REFERENCIA.relative_to(c.RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return
    try:
        xlsx, nome, url = baixar_anexo()
        anexo = ler_anexo(xlsx)
        bc = {s: sgs(s) for s in (13761, 13762, 4607, 5751, 4382)}
    except (urllib.error.URLError, OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: download falhou ({erro}); usando a cópia versionada", flush=True)
            copiar_referencia()
            return
        raise
    doc = montar(anexo, bc, nome, url)
    print(resumo(doc), flush=True)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
