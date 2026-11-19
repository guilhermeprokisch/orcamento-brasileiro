"""Dados do mapa: despesa, receita, tributos e áreas de gasto de cada município e estado, por ano.

    uv run mapa                 # todos os anos que estão no cache (2013 em diante)
    uv run mapa --anos 2024 2025

Lê os caches da DCA em data/raw/siconfi/ (despesa por função, dca-ie, e receitas, dca-ic),
preenchidos por `uv run cidades` (API) e `uv run finbra` (arquivos em lote). As receitas dos
estados não vêm no FINBRA de municípios: são buscadas na API (27 consultas por ano) e ficam
no mesmo cache.

Saídas em site/public/data/mapa/:
- anos/{ano}.json   {"mun": {ibge: registro}, "uf": {id: registro}}
- areas/{ano}.json  gasto por função (28 áreas) de cada ente
- contas/{ano}.json despesa por natureza e balanço patrimonial de cada município
                    ({ibge: {"n": contas.NATUREZA, "b": contas.BALANCO}}), dos anexos I-D e I-AB
- nomes.json        nomes de municípios, estados e áreas
- serie.json        despesa e receita de cada ente em todos os anos
- ipca.json         fatores para corrigir pela inflação
- rfb.json          arrecadação federal por estado e ano (Receita Federal)
- municipios.geojson, estados.geojson  malhas do IBGE, simplificadas

Cada registro é uma lista: população, despesa, saúde, educação, segurança, pago e, quando há
receita, os valores de `receitas.CAMPOS`, na mesma ordem. A página do mapa (site/public/mapa/)
depende dessa ordem: mudar aqui exige mudar o objeto `I` de lá.
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT, baixar_ipca
from .contas import balanco, natureza
from .receitas import receita
from .transformar import fatores_ipca

SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa"
PASTA_IPCA = c.RAIZ / "data" / "raw" / "ipca"
ARQ_RFB = c.RAIZ / "data" / "raw" / "receita-federal" / "arrecadacao-estado.csv"
URL_RFB = "https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv"
URL_MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
             "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao={nivel}")
MALHAS = {"municipio": "municipios.geojson", "UF": "estados.geojson"}
ANEXO_RECEITA = "DCA-Anexo I-C"
CAMPOS_CACHE_RECEITA = ("coluna", "conta", "cod_conta", "valor", "populacao")
FUNCOES_DESTAQUE = ("10", "12", "06")  # saúde, educação, segurança pública


def filtro_receita(itens: list[dict]) -> list[dict]:
    return [{k: i.get(k) for k in CAMPOS_CACHE_RECEITA} for i in itens]


def registro(itens_despesa: list[dict] | None, itens_receita: list[dict] | None) -> tuple[list[int] | None, dict | None]:
    """(registro do mapa, resumo da despesa) de um ente num ano."""
    d = c.resumir(itens_despesa) if itens_despesa else None
    if not d or not d["pop"]:
        return None, None
    f = d["funcoes"]
    r = [d["pop"], d["total"]["emp"]] + [f.get(k, [0.0])[0] for k in FUNCOES_DESTAQUE] + [d["total"]["pago"]]
    rec = receita(itens_receita) if itens_receita else None
    return [round(x) for x in r + (rec or [])], d


def arrecadacao_federal(anos: list[int]) -> dict:
    """Total arrecadado pela Receita Federal em cada estado e ano. Baixa o CSV se não houver cache."""
    if not ARQ_RFB.exists():
        ARQ_RFB.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL_RFB, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
            ARQ_RFB.write_bytes(resp.read())
    total: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with ARQ_RFB.open(encoding="latin-1", newline="") as arq:
        linhas = csv.reader(arq, delimiter=";")
        next(linhas)
        for l in linhas:
            if len(l) < 4 or not l[0].strip().isdigit():
                continue
            ano, uf = int(l[0]), l[2].strip()
            for v in l[3:]:
                v = v.strip().replace(".", "").replace(",", ".")
                try:
                    total[ano][uf] += float(v)
                except ValueError:
                    pass
    return {"fonte": "Receita Federal, arrecadação por estado",
            "anos": {str(a): {u: round(v) for u, v in total[a].items()} for a in anos if a in total}}


def malhas() -> None:
    """Malhas de municípios e estados (IBGE, qualidade mínima), com 3 casas decimais e só o código."""
    def arredondar(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 3), round(coords[1], 3)]
        return [arredondar(x) for x in coords]

    for nivel, nome in MALHAS.items():
        bruto = c.RAIZ / "data" / "raw" / "ibge" / f"malha-{nivel}.json"
        if not bruto.exists():
            bruto.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(URL_MALHA.format(nivel=nivel), headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
                bruto.write_bytes(resp.read())
        geo = json.loads(bruto.read_text(encoding="utf-8"))
        for f in geo["features"]:
            f["geometry"]["coordinates"] = arredondar(f["geometry"]["coordinates"])
            f["properties"] = {"id": f["properties"]["codarea"]}
        (SAIDA / nome).write_text(json.dumps(geo, separators=(",", ":")))


def ipca(anos: list[int]) -> dict:
    try:
        indice = baixar_ipca(PASTA_IPCA)
    except Exception as e:  # sem rede: usa o último arquivo baixado
        print(f"  aviso: IPCA indisponível ({e}); usando o cache", flush=True)
        linhas = json.loads((PASTA_IPCA / "ipca_1737.json").read_text(encoding="utf-8"))
        indice = {}
        for l in linhas[1:]:
            try:
                indice[l["D3C"]] = float(l["V"])
            except ValueError:
                continue
    return fatores_ipca(indice, anos)


def main() -> None:
    hoje = date.today()
    ultimo = hoje.year - 1 if hoje.month >= 5 else hoje.year - 2
    p = argparse.ArgumentParser(prog="mapa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+", default=list(range(2013, ultimo + 1)))
    p.add_argument("--max-chamadas", type=int, default=None, help="limite de consultas à API (receitas dos estados)")
    args = p.parse_args()
    c.CHAMADAS.restantes = args.max_chamadas
    anos = sorted(args.anos)

    entes = c.baixar_entes()
    nomes: dict[str, dict] = {"mun": {}, "uf": {}, "areas": {}}
    for e in entes:
        if e["esfera"] == "M":
            nomes["mun"][str(e["cod_ibge"])] = [e["ente"], e["uf"]]
        elif e["esfera"] in ("E", "D"):
            nomes["uf"][str(e["cod_ibge"])] = [e["ente"], c.SIGLAS[e["cod_ibge"]]]

    (SAIDA / "anos").mkdir(parents=True, exist_ok=True)
    (SAIDA / "areas").mkdir(parents=True, exist_ok=True)
    (SAIDA / "contas").mkdir(parents=True, exist_ok=True)
    serie: dict = {"anos": anos, "mun": {}, "uf": {}}
    for n, ano in enumerate(anos):
        despesa = c.CacheAno(ano)
        receitas = c.CacheAno(ano, anexo="dca-ic", filtro=filtro_receita)
        if ano >= c.PRIMEIRO_ANO:  # receitas dos estados: API
            for uf in nomes["uf"]:
                c.baixar_dca(receitas, ano, int(uf), anexo=ANEXO_RECEITA)
            receitas.salvar()
        doc: dict = {"mun": {}, "uf": {}}
        areas: dict = {"mun": {}, "uf": {}}
        for esfera in ("mun", "uf"):
            for ibge in nomes[esfera]:
                r, d = registro(despesa.obter(int(ibge)), receitas.obter(int(ibge)))
                if not r:
                    continue
                doc[esfera][ibge] = r
                areas[esfera][ibge] = {k: round(v[0]) for k, v in d["funcoes"].items() if v[0] > 0}
                for k in d["funcoes"]:
                    nomes["areas"][k] = d["nomes"][k]
                s = serie[esfera].setdefault(ibge, [[None] * len(anos), [None] * len(anos)])
                s[0][n] = r[1]
                s[1][n] = r[6] if len(r) > 6 else None
        (SAIDA / "anos" / f"{ano}.json").write_text(json.dumps(doc, separators=(",", ":")))
        (SAIDA / "areas" / f"{ano}.json").write_text(json.dumps(areas, separators=(",", ":")))
        # Despesa por natureza e balanço patrimonial (só municípios; vêm dos arquivos do FINBRA).
        por_natureza = c.CacheAno(ano, anexo="dca-id", filtro=filtro_receita)
        patrimonio = c.CacheAno(ano, anexo="dca-iab", filtro=filtro_receita)
        contas: dict = {}
        for ibge in doc["mun"]:
            n = natureza(por_natureza.obter(int(ibge)) or [])
            b = balanco(patrimonio.obter(int(ibge)) or [])
            if n or b:
                contas[ibge] = {k: v for k, v in (("n", n), ("b", b)) if v}
        (SAIDA / "contas" / f"{ano}.json").write_text(json.dumps(contas, separators=(",", ":")))
        print(f"{ano}: {len(doc['mun'])} municípios ({sum(1 for r in doc['mun'].values() if len(r) > 6)} com receita), "
              f"{len(doc['uf'])} estados ({sum(1 for r in doc['uf'].values() if len(r) > 6)} com receita); "
              f"natureza {sum(1 for x in contas.values() if 'n' in x)}, balanço {sum(1 for x in contas.values() if 'b' in x)}", flush=True)

    nomes["areas"] = dict(sorted(nomes["areas"].items()))
    (SAIDA / "nomes.json").write_text(json.dumps(nomes, ensure_ascii=False, separators=(",", ":")))
    (SAIDA / "serie.json").write_text(json.dumps(serie, separators=(",", ":")))
    (SAIDA / "ipca.json").write_text(json.dumps(ipca(anos)))
    (SAIDA / "rfb.json").write_text(json.dumps(arrecadacao_federal(anos), separators=(",", ":")))
    malhas()
    print(f"saída: {SAIDA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
