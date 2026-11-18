"""Linha de comando do pipeline.

    uv run orcamento                 # 2014 até o ano corrente
    uv run orcamento --anos 2024 2025
    uv run orcamento --forcar        # baixa de novo mesmo se já existir
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb

from .fontes import baixar_orcamento_despesa
from .transformar import carregar, exportar_explorer, exportar_parquet

RAIZ = Path(__file__).resolve().parents[3]
PASTA_BRUTO = RAIZ / "data" / "raw" / "orcamento-despesa"
PARQUET = RAIZ / "data" / "out" / "orcamento_despesa.parquet"
PASTA_EXPLORER = RAIZ / "site" / "public" / "data" / "explorer"

PRIMEIRO_ANO = 2014


def main() -> None:
    hoje = date.today()
    p = argparse.ArgumentParser(prog="orcamento", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+",
                   default=list(range(PRIMEIRO_ANO, hoje.year + 1)))
    p.add_argument("--forcar", action="store_true",
                   help="baixa de novo todos os anos (o ano corrente é sempre baixado de novo)")
    args = p.parse_args()

    csvs = []
    for ano in sorted(args.anos):
        forcar = args.forcar or ano == hoje.year
        print(f"baixando {ano}{' (de novo)' if forcar else ''}…", flush=True)
        csvs.append(baixar_orcamento_despesa(ano, PASTA_BRUTO, forcar=forcar))

    con = duckdb.connect()
    carregar(con, csvs)
    exportar_parquet(con, PARQUET)
    resumo = exportar_explorer(con, PASTA_EXPLORER)

    bi = 1e9
    print(f"\n{'ano':>4}  {'linhas':>7}  {'atualizado':>12}  {'empenhado':>12}  {'realizado':>12}  (R$ bi)")
    for r in resumo:
        print(f"{r['ano']:>4}  {r['linhas']:>7}  {r['atualizado']/bi:>12.1f}  "
              f"{r['empenhado']/bi:>12.1f}  {r['realizado']/bi:>12.1f}")
    print(f"\nparquet: {PARQUET.relative_to(RAIZ)}\nexplorer: {PASTA_EXPLORER.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
