"""Download dos arquivos brutos do Portal da Transparência."""

from __future__ import annotations

import shutil
import ssl
import urllib.request
import zipfile
from pathlib import Path

import certifi

# Lista de certificados da Mozilla: a do sistema pode não ter raízes usadas
# por sites do governo (ex.: GlobalSign Root R46 no SIOP).
CONTEXTO_TLS = ssl.create_default_context(cafile=certifi.where())

# Orçamento da despesa: um zip por exercício (2014 em diante), com um CSV
# em latin-1, separado por ";", no nível órgão × UO × função × programa × ação × elemento.
URL_ORCAMENTO_DESPESA = (
    "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/"
    "orcamento-despesa/{ano}_OrcamentoDespesa.zip"
)

USER_AGENT = "orcamento-br-pipeline/0.1"

# SIOP (Sistema Integrado de Planejamento e Orçamento): nomes oficiais, com
# acentos e grafia correta, de ações, programas e unidades orçamentárias.
URL_SIOP_SPARQL = "https://www1.siop.planejamento.gov.br/sparql/"
TIPOS_SIOP = {"acao": "Acao", "programa": "Programa", "uo": "UnidadeOrcamentaria"}


def baixar_nomes_siop(ano: int, destino: Path, forcar: bool = False) -> dict[str, dict[str, str]]:
    """Devolve {"acao"|"programa"|"uo": {código: nome}} do exercício, via SPARQL.

    Guarda o resultado em destino/{ano}.json; só consulta de novo se `forcar`.
    """
    import json
    import urllib.parse

    destino.mkdir(parents=True, exist_ok=True)
    cache = destino / f"{ano}.json"
    if cache.exists() and not forcar:
        return json.loads(cache.read_text(encoding="utf-8"))

    nomes: dict[str, dict[str, str]] = {}
    for chave, tipo in TIPOS_SIOP.items():
        prefixo = f"http://orcamento.dados.gov.br/id/{ano}/{tipo}/"
        consulta = (
            "PREFIX loa: <http://vocab.e.gov.br/2013/09/loa#> "
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
            f"SELECT ?cod ?nome WHERE {{ ?x a loa:{tipo} ; loa:codigo ?cod ; rdfs:label ?nome . "
            f'FILTER(STRSTARTS(STR(?x), "{prefixo}")) }}'
        )
        url = URL_SIOP_SPARQL + "?" + urllib.parse.urlencode({"query": consulta})
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
        )
        with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
            linhas = json.load(resp)["results"]["bindings"]
        # O endpoint corta em 10.000 linhas; um ano tem bem menos que isso.
        if len(linhas) >= 10_000:
            raise RuntimeError(f"SIOP {ano}/{tipo}: resultado truncado em {len(linhas)} linhas")
        nomes[chave] = {l["cod"]["value"].strip(): " ".join(l["nome"]["value"].split()) for l in linhas}

    cache.write_text(json.dumps(nomes, ensure_ascii=False), encoding="utf-8")
    return nomes


# IPCA, número-índice mensal (base dez/1993 = 100), tabela 1737 do SIDRA/IBGE.
URL_IPCA = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all/d/v2266%2013"


def baixar_ipca(destino: Path) -> dict[str, float]:
    """Baixa o IPCA (número-índice) e devolve {"AAAAMM": índice}. Sempre baixa de novo."""
    import json

    destino.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL_IPCA, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as resp:
        linhas = json.load(resp)
    (destino / "ipca_1737.json").write_text(json.dumps(linhas), encoding="utf-8")
    # A primeira linha é o cabeçalho; meses sem valor vêm como "..." ou "-".
    indice = {}
    for l in linhas[1:]:
        try:
            indice[l["D3C"]] = float(l["V"])
        except ValueError:
            continue
    if not indice:
        raise RuntimeError("IPCA veio vazio do SIDRA")
    return indice


def baixar_orcamento_despesa(ano: int, destino: Path, forcar: bool = False) -> Path:
    """Baixa e extrai o CSV do orçamento da despesa de um exercício.

    Retorna o caminho do CSV. Não baixa de novo se o CSV já existir, a menos
    que `forcar` seja verdadeiro (o ano corrente muda todo dia).
    """
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{ano}_OrcamentoDespesa.csv"
    if csv.exists() and not forcar:
        return csv

    url = URL_ORCAMENTO_DESPESA.format(ano=ano)
    zip_path = destino / f"{ano}_OrcamentoDespesa.zip"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as resp, zip_path.open("wb") as out:
        shutil.copyfileobj(resp, out)

    with zipfile.ZipFile(zip_path) as zf:
        membros = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if len(membros) != 1:
            raise RuntimeError(f"{zip_path.name}: esperava 1 CSV, encontrei {membros}")
        # Extrai pelo nome esperado, nunca pelo caminho que vem dentro do zip.
        with zf.open(membros[0]) as src, csv.open("wb") as out:
            shutil.copyfileobj(src, out)

    zip_path.unlink()
    return csv
