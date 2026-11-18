"""Limpa os CSVs brutos e gera os arquivos que o site consome."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

# Nomes das 26 colunas do CSV, na ordem em que aparecem.
COLUNAS_CSV = [
    "ano",
    "orgao_superior_cod", "orgao_superior",
    "orgao_cod", "orgao",
    "uo_cod", "uo",
    "funcao_cod", "funcao",
    "subfuncao_cod", "subfuncao",
    "programa_cod", "programa",
    "acao_cod", "acao",
    "categoria_cod", "categoria",
    "gnd_cod", "gnd",
    "elemento_cod", "elemento",
    "inicial", "atualizado", "empenhado", "realizado",
    "pct_realizado",
]

VALORES = ["inicial", "atualizado", "empenhado", "realizado"]

# Dimensões que vão para o Explorer: (nome no JSON, coluna de código, coluna de nome).
DIMENSOES = [
    ("orgao", "orgao_superior_cod", "orgao_superior"),
    ("uo", "uo_cod", "uo"),
    ("funcao", "funcao_cod", "funcao"),
    ("subfuncao", "subfuncao_cod", "subfuncao"),
    ("programa", "programa_cod", "programa"),
    ("acao", "acao_cod", "acao"),
    ("gnd", "gnd_cod", "gnd"),
]


def _numero(col: str) -> str:
    # "1.234.567,89" -> 1234567.89
    return f"TRY_CAST(replace(replace({col}, '.', ''), ',', '.') AS DECIMAL(18,2)) AS {col}"


def carregar(con: duckdb.DuckDBPyConnection, csvs: list[Path]) -> None:
    """Cria a tabela `despesa` com todos os anos, já tipada."""
    arquivos = [str(p) for p in csvs]
    texto = [c for c in COLUNAS_CSV if c not in VALORES and c not in ("ano", "pct_realizado")]
    con.execute(
        f"""
        CREATE OR REPLACE TABLE despesa AS
        SELECT
            CAST(ano AS INTEGER) AS ano,
            {", ".join(f"trim({c}) AS {c}" for c in texto)},
            {", ".join(_numero(v) for v in VALORES)}
        FROM read_csv(
            $arquivos,
            delim = ';', quote = '"', header = true, encoding = 'latin-1',
            names = $nomes, all_varchar = true
        )
        """,
        {"arquivos": arquivos, "nomes": COLUNAS_CSV},
    )
    ruins = con.execute(
        f"SELECT count(*) FROM despesa WHERE {' OR '.join(f'{v} IS NULL' for v in VALORES)}"
    ).fetchone()[0]
    if ruins:
        raise RuntimeError(f"{ruins} linhas com valor que não virou número")


def exportar_parquet(con: duckdb.DuckDBPyConnection, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY (SELECT * FROM despesa ORDER BY ano, orgao_superior_cod, uo_cod, acao_cod) "
        f"TO '{destino}' (FORMAT parquet, COMPRESSION zstd)"
    )


def exportar_explorer(con: duckdb.DuckDBPyConnection, pasta: Path) -> list[dict]:
    """Um JSON compacto por ano, agregado até o nível de ação × GND (sem elemento).

    Formato: dicionários código→nome por dimensão, e linhas como listas na
    ordem de `colunas`. Valores em reais inteiros. O site faz o agrupamento.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    gerado_em = datetime.now(timezone.utc).isoformat(timespec="seconds")
    resumo = []

    anos = [r[0] for r in con.execute("SELECT DISTINCT ano FROM despesa ORDER BY ano").fetchall()]
    for ano in anos:
        dims = {}
        for nome, cod, rotulo in DIMENSOES:
            pares = con.execute(
                f"SELECT {cod}, max({rotulo}) FROM despesa WHERE ano = ? GROUP BY 1 ORDER BY 1",
                [ano],
            ).fetchall()
            dims[nome] = {c: n for c, n in pares}

        codigos = [cod for _, cod, _ in DIMENSOES]
        linhas = con.execute(
            f"""
            SELECT {", ".join(codigos)},
                   {", ".join(f"CAST(round(sum({v})) AS BIGINT)" for v in VALORES)}
            FROM despesa WHERE ano = ?
            GROUP BY ALL
            HAVING {" OR ".join(f"sum({v}) <> 0" for v in VALORES)}
            ORDER BY ALL
            """,
            [ano],
        ).fetchall()

        totais = dict(zip(VALORES, (sum(l[len(codigos) + i] for l in linhas) for i in range(len(VALORES)))))
        doc = {
            "ano": ano,
            "gerado_em": gerado_em,
            "fonte": "Portal da Transparência (CGU) — Orçamento da Despesa",
            "colunas": [n for n, _, _ in DIMENSOES] + VALORES,
            "dims": dims,
            "linhas": [list(l) for l in linhas],
        }
        (pasta / f"{ano}.json").write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        resumo.append({"ano": ano, "linhas": len(linhas), **totais})

    (pasta / "anos.json").write_text(
        json.dumps({"gerado_em": gerado_em, "anos": resumo}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return resumo
