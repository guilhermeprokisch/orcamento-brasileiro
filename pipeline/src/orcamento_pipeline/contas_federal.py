"""As contas fecham? Resultado primário e nominal do setor público e do governo central, e quanto do gasto
federal é obrigatório por lei (página /contas).

    uv run contas-federal               # baixa as séries do Banco Central e a série histórica do Tesouro
    uv run contas-federal --sem-baixar  # só copia pipeline/referencia/contas-federal.json (publicação)

Fontes:
- Banco Central, necessidade de financiamento do setor público (NFSP) sem desvalorização cambial, em % do PIB,
  acumulada em 12 meses (SGS, api.bcb.gov.br, sem chave). A NFSP é positiva quando falta dinheiro (déficit);
  aqui o sinal é invertido: positivo é superávit, negativo é déficit.
    5793 / 5727 / 5760  setor público consolidado: primário, nominal e juros nominais
    5783 / 5717 / 5750  governo federal e Banco Central (o "governo central"): primário, nominal e juros
    4382                PIB acumulado em 12 meses, R$ milhões (para passar de % do PIB a reais)
  O valor de dezembro é o do ano; o último mês publicado entra à parte, como "12 meses até".
- Tesouro Nacional, Resultado do Tesouro Nacional (RTN), série histórica, aba 2.1 (anual, R$ milhões
  correntes). O endereço da planilha muda todo mês; vem da API do portal Tesouro Transparente (CKAN).
  Linhas usadas: 2 (repasses obrigatórios a estados e municípios), 4 (despesa total), 4.1 (benefícios
  previdenciários), 4.2 (pessoal), 4.3 (outras despesas obrigatórias), 4.4.1 (obrigatórias com controle de
  fluxo: Bolsa Família, parte da saúde…) e 4.4.2 (discricionárias). A separação começa em 2008.

Saída em site/public/data/federal/contas.json, com cópia versionada em pipeline/referencia/contas-federal.json
(usada com --sem-baixar ou se o download falhar):
    {"fonte": …, "anos": [2002, …],
     "spc": {"primario": [% do PIB], "nominal": […], "juros": […]},
     "central": {"primario": […], "nominal": […], "juros": […]},
     "pib": [R$ bi], "doze": {"ate": "2026-09", "pib": R$ bi, "spc": [primário, nominal, juros], "central": […]},
     "rtn": {"url": …, "titulo": …, "anos": [2008, …], "repasses": [R$ bi], "total": […], "previdencia": […],
             "pessoal": […], "outras": […], "controle": […], "discricionarias": […]}}
As listas seguem "anos" (ou "rtn.anos"); null onde falta o dado.
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
from datetime import datetime, timezone

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json&dataInicial=01/01/{ano}&dataFinal=31/12/2099"
CKAN_RTN = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id=ab56485b-9c40-4efb-8563-9ce3e1973c4b"
PAGINA_RTN = "https://www.tesourotransparente.gov.br/ckan/dataset/resultado-do-tesouro-nacional"
SAIDA = c.RAIZ / "site" / "public" / "data" / "federal" / "contas.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "contas-federal.json"
PASTA_BRUTO = c.RAIZ / "data" / "raw" / "tesouro" / "rtn"
PRIMEIRO_ANO = 2002
FONTE = ("Banco Central, NFSP sem desvalorização cambial (SGS 5793, 5727, 5760, 5783, 5717, 5750 e 4382); "
         "Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, tabela 2.1)")

SERIES = {"spc": {"primario": 5793, "nominal": 5727, "juros": 5760},
          "central": {"primario": 5783, "nominal": 5717, "juros": 5750}}
PIB12 = 4382

# Linhas da aba 2.1 do RTN: início do rótulo (sem acento, minúsculo, espaços simples) → chave.
LINHAS_RTN = {"2. transf. por reparticao de receita": "repasses", "4. despesa total": "total",
              "4.1 beneficios previdenciarios": "previdencia", "4.2 pessoal e encargos sociais": "pessoal",
              "4.3 outras despesas obrigatorias": "outras", "4.4.1 obrigatorias com controle de fluxo": "controle",
              "4.4.2 despesas discricionarias": "discricionarias"}
PRIMEIRO_ANO_RTN = 2008


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=CONTEXTO_TLS) as resp:
        return resp.read()


def _normal(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t.replace("-", " ")).strip()


# ── Banco Central ────────────────────────────────────────────────────────────────────────────────

def sgs(serie: int) -> dict[str, float]:
    """Série mensal do SGS como {'2026-09': valor}."""
    dados = json.loads(_get(SGS.format(serie=serie, ano=PRIMEIRO_ANO)))
    saida = {}
    for p in dados:
        _, m, a = p["data"].split("/")
        if p.get("valor") not in (None, ""):
            saida[f"{a}-{m}"] = float(p["valor"])
    if not saida:
        raise ValueError(f"série {serie} do SGS veio vazia")
    return saida


def montar_bc(bc: dict[int, dict[str, float]]) -> dict:
    """Valores de dezembro de cada ano (sinal invertido: superávit positivo) e os 12 meses até o último mês."""
    ultimo_dez = max(int(m[:4]) for m in bc[5793] if m.endswith("-12"))
    anos = list(range(PRIMEIRO_ANO, ultimo_dez + 1))
    r = lambda v: None if v is None else round(-v, 2)
    saida: dict = {"anos": anos}
    for esfera, series in SERIES.items():
        saida[esfera] = {k: [r(bc[s].get(f"{a}-12")) for a in anos] for k, s in series.items()}
    saida["pib"] = [round(v / 1000, 1) if (v := bc[PIB12].get(f"{a}-12")) is not None else None for a in anos]
    ate = min(max(bc[s]) for ser in SERIES.values() for s in ser.values())
    if not ate.endswith("-12") and int(ate[:4]) > ultimo_dez:
        saida["doze"] = {"ate": ate, "pib": round(bc[PIB12][ate] / 1000, 1) if ate in bc[PIB12] else None,
                         **{e: [r(bc[s].get(ate)) for s in ser.values()] for e, ser in SERIES.items()}}
    return saida


# ── Tesouro: Resultado do Tesouro Nacional ───────────────────────────────────────────────────────

def baixar_rtn() -> tuple[bytes, str, str]:
    """(planilha, endereço, nome do arquivo) da série histórica mensal mais recente do RTN."""
    pacote = json.loads(_get(CKAN_RTN))["result"]
    recurso = next(r for r in pacote["resources"]
                   if (r.get("format") or "").upper() == "XLSX" and "rie hist" in (r.get("name") or "").lower())
    url = recurso["url"]
    nome = url.rsplit("/", 1)[-1]
    cache = PASTA_BRUTO / nome
    if cache.exists():
        return cache.read_bytes(), url, nome
    print(f"  baixando {nome}", flush=True)
    dados = _get(url, timeout=300)
    PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(dados)
    return dados, url, nome


def ler_rtn(xlsx: bytes) -> dict:
    """As linhas de LINHAS_RTN da aba 2.1, em R$ bilhões, de PRIMEIRO_ANO_RTN ao último ano da planilha."""
    wb = openpyxl.load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    linhas = list(wb["2.1"].iter_rows(values_only=True))
    cab = next(l for l in linhas if _normal(l[0]) == "discriminacao")
    colunas = {int(a): i for i, a in enumerate(cab) if re.fullmatch(r"\d{4}", str(a or "").strip())}
    anos = [a for a in sorted(colunas) if a >= PRIMEIRO_ANO_RTN]
    saida: dict = {"anos": anos}
    for l in linhas:
        rotulo = _normal(l[0])
        for inicio, chave in LINHAS_RTN.items():
            if rotulo.startswith(inicio) and chave not in saida:
                saida[chave] = [round(l[colunas[a]] / 1000, 1) if isinstance(l[colunas[a]], (int, float)) else None
                                for a in anos]
    falta = [k for k in LINHAS_RTN.values() if k not in saida]
    if falta:
        raise ValueError(f"RTN, aba 2.1: linhas não encontradas: {falta}")
    # Confere: as partes somam a despesa total.
    for j, a in enumerate(anos):
        partes = sum(saida[k][j] or 0 for k in ("previdencia", "pessoal", "outras", "controle", "discricionarias"))
        if saida["total"][j] and abs(partes - saida["total"][j]) > 0.01 * saida["total"][j]:
            raise ValueError(f"RTN {a}: as partes ({partes}) não somam a despesa total ({saida['total'][j]})")
    return saida


# ── Montagem ─────────────────────────────────────────────────────────────────────────────────────

def resumo(doc: dict) -> str:
    a = doc["anos"][-1]
    spc, cen = doc["spc"], doc["central"]
    rtn = doc["rtn"]
    j = len(rtn["anos"]) - 1
    livre = rtn["discricionarias"][j] / rtn["total"][j]
    return (f"{a}: setor público primário {spc['primario'][-1]}% do PIB, nominal {spc['nominal'][-1]}%; "
            f"governo central primário {cen['primario'][-1]}%, nominal {cen['nominal'][-1]}%\n"
            f"  RTN {rtn['anos'][j]}: despesa R$ {rtn['total'][j]} bi, discricionárias R$ {rtn['discricionarias'][j]} bi ({livre:.1%})"
            + (f"\n  12 meses até {doc['doze']['ate']}: {doc['doze']}" if "doze" in doc else ""))


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
    anterior = json.loads(REFERENCIA.read_text(encoding="utf-8")) if REFERENCIA.exists() else None
    try:
        bc = {s: sgs(s) for ser in SERIES.values() for s in ser.values()} | {PIB12: sgs(PIB12)}
        doc = {"fonte": FONTE, "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), **montar_bc(bc)}
    except (urllib.error.URLError, OSError, ValueError, KeyError) as erro:
        if anterior:
            print(f"  aviso: Banco Central falhou ({erro}); usando a cópia versionada", flush=True)
            copiar_referencia()
            return
        raise
    try:
        xlsx, url, nome = baixar_rtn()
        doc["rtn"] = {"url": url, "pagina": PAGINA_RTN, "arquivo": nome, **ler_rtn(xlsx)}
    except (urllib.error.URLError, OSError, ValueError, KeyError, StopIteration) as erro:
        if not (anterior and "rtn" in anterior):
            raise
        print(f"  aviso: RTN falhou ({erro}); mantendo o da cópia versionada", flush=True)
        doc["rtn"] = anterior["rtn"]
    print(resumo(doc), flush=True)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
