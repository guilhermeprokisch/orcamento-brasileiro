"""Confere o que o Portal da Transparência diz ter mandado às prefeituras com o que elas declaram.

    uv run conciliar 2025

Duas fontes contam o mesmo dinheiro de jeitos diferentes: o Portal (federal.py) registra o que
a União pagou; a prestação de contas anual (DCA, Anexo I-C) registra o que a prefeitura diz ter
recebido. Este comando soma as duas por programa, em todos os municípios que têm os dois lados,
e mostra o total e a dispersão da razão Portal/declarado.

O que a comparação de 2025 mostrou (detalhes em docs/conciliacao-federal.md):
- SUS, royalties e assistência social batem;
- o FPM do Portal é o declarado já sem os 20% retidos para o FUNDEB e sem as três parcelas
  extras de 1% (julho, setembro e dezembro), que não aparecem no arquivo do Portal;
- o FUNDEB do Portal é a complementação da União mais a parte do fundo formada por tributos
  federais; a parte formada por ICMS e IPVA chega às prefeituras sem passar pelo Portal.

Lê os caches já existentes (não consulta a API): data/raw/siconfi/dca-ic/{ano}.json.gz e
site/public/data/mapa/federal-{ano}.json.
"""

from __future__ import annotations

import argparse
import json

from . import cidades as c
from .federal import COLUNAS, SAIDA

# Contas da receita (classificação de 2022 em diante) de cada programa.
FPM = "1.7.1.1.51.0.0"
CONTAS = {
    "saude": ("1.7.1.3.00.0.0", "2.4.1.1.00.0.0"),
    "royalties": ("1.7.1.2.00.0.0",),
    "assistencia": ("1.7.1.6.00.0.0",),
    "complementacao": ("1.7.1.5.00.0.0",),
    "fundeb": ("1.7.5.1.00.0.0",),
    "uniao": ("1.7.1.0.00.0.0", "2.4.1.0.00.0.0"),
}


def declarado(itens: list[dict]) -> dict[str, float] | None:
    """Repasses da União declarados por uma prefeitura, por programa (líquidos de deduções)."""
    bruto: dict[str, float] = {}
    deducao: dict[str, float] = {}
    for i in itens:
        cod = " ".join((i["conta"] or "").split()).split(" ")[0]
        if not cod[:1].isdigit():
            continue
        v = float(i["valor"] or 0)
        if "Brutas" in i["coluna"] or "Realizadas" == i["coluna"]:
            bruto[cod] = v
        else:
            deducao[cod] = deducao.get(cod, 0.0) + abs(v)
    liq = lambda *cods: sum(bruto.get(k, 0.0) - deducao.get(k, 0.0) for k in cods)
    d = {k: liq(*cods) for k, cods in CONTAS.items()}
    if d["uniao"] <= 0:
        return None
    d["fpm"], d["fpm_bruto"] = liq(FPM), bruto.get(FPM, 0.0)
    # Educação (FNDE), convênios, transferências especiais e o que mais vier da União.
    d["demais"] = d["uniao"] - d["fpm"] - d["saude"] - d["royalties"] - d["assistencia"] - d["complementacao"]
    return d


def do_portal(valores: list[int]) -> dict[str, float]:
    p = dict(zip(COLUNAS, valores))
    return {"fpm": p["fpm"], "saude": p["saude"], "royalties": p["royalties"], "assistencia": p["assistencia"],
            "fundeb": p["fundeb"], "demais": p["educacao"] + p["outros"]}


# (rótulo, valor do Portal, valor declarado)
COMPARACOES = [
    ("FPM x declarado bruto", lambda p, d: p["fpm"], lambda p, d: d["fpm_bruto"]),
    ("FPM x declarado sem a retenção do FUNDEB", lambda p, d: p["fpm"], lambda p, d: d["fpm"]),
    ("SUS", lambda p, d: p["saude"], lambda p, d: d["saude"]),
    ("Royalties e compensações", lambda p, d: p["royalties"], lambda p, d: d["royalties"]),
    ("Assistência social (FNAS)", lambda p, d: p["assistencia"], lambda p, d: d["assistencia"]),
    ("Educação e outros repasses", lambda p, d: p["demais"], lambda p, d: d["demais"]),
    ("FUNDEB x complementação da União", lambda p, d: p["fundeb"], lambda p, d: d["complementacao"]),
    ("FUNDEB x complementação + fundo", lambda p, d: p["fundeb"], lambda p, d: d["complementacao"] + d["fundeb"]),
]


def comparar(ano: int) -> tuple[int, list[dict]]:
    """(municípios com os dois lados, uma linha por comparação)."""
    federal = json.loads((SAIDA / f"federal-{ano}.json").read_text())["mun"]
    cache = c.CacheAno(ano, anexo="dca-ic")
    pares = []
    for ibge, valores in federal.items():
        d = declarado(cache.obter(int(ibge)) or [])
        if d:
            pares.append((do_portal(valores), d))
    linhas = []
    for rotulo, portal, decl in COMPARACOES:
        razoes = sorted(portal(p, d) / decl(p, d) for p, d in pares if decl(p, d) > 1e5)
        q = lambda x: razoes[int(x * (len(razoes) - 1))] if razoes else float("nan")
        tp, td = sum(portal(p, d) for p, d in pares), sum(decl(p, d) for p, d in pares)
        linhas.append({"rotulo": rotulo, "portal": tp, "declarado": td, "razao": tp / td if td else float("nan"),
                       "p10": q(0.1), "mediana": q(0.5), "p90": q(0.9),
                       "perto": sum(1 for r in razoes if abs(r - 1) <= 0.05) / len(razoes) if razoes else 0.0})
    return len(pares), linhas


def main() -> None:
    p = argparse.ArgumentParser(prog="conciliar", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    args = p.parse_args()
    n, linhas = comparar(args.ano)
    print(f"{n} municípios com os dois lados em {args.ano}. Razão = Portal / declarado.\n")
    print("| Comparação | Portal (R$ bi) | Declarado (R$ bi) | Razão | p10 | Mediana | p90 | Cidades a ±5% |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for l in linhas:
        print(f"| {l['rotulo']} | {l['portal'] / 1e9:.1f} | {l['declarado'] / 1e9:.1f} | {l['razao']:.2f} | "
              f"{l['p10']:.2f} | {l['mediana']:.2f} | {l['p90']:.2f} | {l['perto']:.0%} |")


if __name__ == "__main__":
    main()
