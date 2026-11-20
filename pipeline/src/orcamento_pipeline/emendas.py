"""Emendas parlamentares que chegaram a cada cidade e estado (CGU, Portal da Transparência).

    uv run emendas

Fonte: o arquivo único "Emendas Parlamentares" dos dados abertos da CGU (um zip com vários CSV).
Usa dois deles:
- EmendasParlamentares_PorFavorecido.csv: cada pagamento de uma emenda, com o autor, o mês e a
  cidade de quem recebeu. É o que dá a cidade: no arquivo principal, a maior parte do dinheiro
  tem como lugar "MÚLTIPLO". Os nomes de quem recebeu não são guardados: só o total por cidade,
  separado entre a prefeitura (o município e os fundos municipais), entidades e empresas, e
  órgãos do estado e outros.
- EmendasParlamentares.csv: a área (função) de cada emenda, ligada pelo código da emenda.

Saída em site/public/data/indicadores/emendas.json:
    {"fonte", "anos": [...],
     "mun": {ibge: {ano: [total, prefeitura, entidades e empresas, estado e outros]}},
     "uf":  {código: {ano: [...]}},                  # soma das cidades do estado
     "autores": {ibge|código: {ano: [[autor, valor], ...]}},   # os 5 maiores, nos dois últimos anos (na cidade, sem os órgãos estaduais e federais)
     "areas":   {ibge|código: {ano: [[área, valor], ...]}}}    # as 3 maiores, nos dois últimos anos
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile
from collections import defaultdict

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT
from .rfb import casador

URL = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/emendas-parlamentares/EmendasParlamentares.zip"
PASTA = c.RAIZ / "data" / "raw" / "cgu" / "emendas"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "emendas.json"
FONTE = "Controladoria-Geral da União, Portal da Transparência: emendas parlamentares, pagamentos por favorecido"
PRIMEIRO_ANO = 2016
UF_SIGLA = {s: str(k) for k, s in c.SIGLAS.items()}


def numero(s: str) -> float:
    return float((s or "0").replace(".", "").replace(",", ".") or 0)


def grupo(natureza: str) -> int:
    """1 prefeitura, 2 entidades e empresas, 3 estado e outros (o índice em [total, ...])."""
    n = natureza.lower()
    if "municipal" in n or n.startswith("município") or n.startswith("municipio"):
        return 1
    if "estad" in n or "distrito federal" in n or "federal" in n or "autarquia" in n or "empresa pública" in n:
        return 3
    return 2


def linhas(z: zipfile.ZipFile, nome: str):
    with z.open(nome) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA / "EmendasParlamentares.zip"
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as resp:
        arquivo.write_bytes(resp.read())
    z = zipfile.ZipFile(arquivo)

    area_da_emenda = {r["Código da Emenda"]: r["Nome Função"] for r in linhas(z, "EmendasParlamentares.csv")}
    ibge_de = casador()
    mun: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0.0]))
    por_autor: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    por_area: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    sem_cidade = 0.0
    for r in linhas(z, "EmendasParlamentares_PorFavorecido.csv"):
        ano = r["Ano/Mês"][:4]
        if not ano.isdigit() or int(ano) < PRIMEIRO_ANO:
            continue
        v = numero(r["Valor Recebido"])
        uf, cidade = r["UF Favorecido"].strip(), r["Município Favorecido"].strip()
        ibge = ibge_de(cidade, uf) if cidade and uf else None
        if not ibge:
            sem_cidade += v
            continue
        g = grupo(r["Natureza Jurídica"])
        for chave in (ibge, ibge[:2]):
            t = mun[chave][ano]
            t[0] += v
            t[g] += v
            # Órgãos estaduais e federais ficam quase sempre na capital e atendem o estado inteiro: entram
            # nos autores e áreas do estado, não nos da cidade onde têm sede.
            if g == 3 and len(chave) == 7:
                continue
            por_autor[chave][ano][r["Nome do Autor da Emenda"].strip() or "Sem informação"] += v
            por_area[chave][ano][area_da_emenda.get(r["Código da Emenda"], "") or "Sem informação"] += v

    anos = sorted({a for x in mun.values() for a in x})
    recentes = anos[-2:]
    topo = lambda d, n: [[k, round(v)] for k, v in sorted(d.items(), key=lambda x: -x[1])[:n] if v > 0]
    doc = {
        "fonte": FONTE, "anos": [int(a) for a in anos],
        "mun": {k: {a: [round(x) for x in t] for a, t in sorted(v.items())} for k, v in sorted(mun.items()) if len(k) == 7},
        "uf": {k: {a: [round(x) for x in t] for a, t in sorted(v.items())} for k, v in sorted(mun.items()) if len(k) == 2},
        "autores": {k: {a: topo(v[a], 5) for a in recentes if a in v} for k, v in por_autor.items()},
        "areas": {k: {a: topo(v[a], 3) for a in recentes if a in v} for k, v in por_area.items()},
    }
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(texto, encoding="utf-8")
    total = {a: sum(v.get(a, [0])[0] for k, v in doc["uf"].items()) for a in doc["anos"] for a in [str(a)]}
    print("total por ano (R$ bi): " + ", ".join(f"{a} {t / 1e9:.1f}" for a, t in total.items()), flush=True)
    print(f"{len(doc['mun'])} cidades; sem cidade reconhecida: R$ {sem_cidade / 1e6:.0f} mi")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
