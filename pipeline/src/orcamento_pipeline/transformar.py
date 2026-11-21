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


def fatores_ipca(indice: dict[str, float], anos: list[int]) -> dict:
    """Fatores para levar valores de cada ano a reais do último ano completo.

    Usa a média anual do número-índice (média dos meses disponíveis, no caso
    do ano corrente). valor_real = valor_nominal × fator[ano].
    """
    medias, meses = {}, {}
    for ano in anos:
        vs = [v for k, v in indice.items() if k.startswith(str(ano))]
        if vs:
            medias[ano] = sum(vs) / len(vs)
            meses[ano] = len(vs)
    completos = [a for a, n in meses.items() if n == 12]
    if not completos:
        raise RuntimeError("IPCA sem nenhum ano completo")
    base = max(completos)
    ultimo_mes = max(indice)
    return {
        "base": base,
        "metodo": "média anual do IPCA (número-índice); ano corrente: média dos meses disponíveis",
        "fonte": "IBGE, SIDRA tabela 1737",
        "ultimo_mes": f"{ultimo_mes[:4]}-{ultimo_mes[4:]}",
        "fatores": {str(a): round(medias[base] / m, 6) for a, m in medias.items()},
    }


def nome_oficial(nomes_siop: dict[int, dict], dim: str, ano: int, cod: str) -> str | None:
    """Nome do SIOP para o código: do mesmo ano ou, se faltar, do ano mais próximo (até 2 anos)."""
    for delta in (0, -1, 1, -2, 2):
        nome = nomes_siop.get(ano + delta, {}).get(dim, {}).get(cod)
        if nome:
            return nome
    return None


# Tipo de despesa pelo identificador de resultado primário (RP) do SIOP: código no JSON → nome no site.
TIPOS = {
    "obr": "Obrigatória",
    "esc": "Escolha do governo",
    "eme": "Emendas parlamentares",
    "fin": "Financeira (dívida)",
}
# RP 0 financeira; 1 obrigatória; 2 discricionária e 3 PAC (discricionária); 6 a 9 emendas individuais,
# de bancada, de comissão e de relator. Outros códigos, se aparecerem, contam como escolha do governo.
TIPO_DO_RP = {"0": "fin", "1": "obr", "2": "esc", "3": "esc", "6": "eme", "7": "eme", "8": "eme", "9": "eme"}
# Valor do Portal → valor do SIOP usado para repartir uma linha entre os tipos.
MEDIDA_SIOP = {"inicial": "inicial", "atualizado": "atualizado", "empenhado": "empenhado", "realizado": "pago"}


def separar_por_tipo(linhas: list[list], rp: dict) -> tuple[list[list], int]:
    """Acrescenta o tipo de despesa a cada linha (orgao, uo, funcao, subfuncao, programa, acao, gnd, valores…).

    A chave UO × função × subfunção × programa × ação × GND é a mesma no Portal e no SIOP. Quando ela tem
    um tipo só, a linha recebe esse tipo; quando tem mais de um (uma ação com gasto próprio e emendas, por
    exemplo), a linha é repartida na proporção do SIOP, valor a valor (o pago do SIOP reparte o realizado).
    Linhas sem par no SIOP ficam com tipo "sem". Devolve (linhas novas, quantas ficaram sem tipo).
    """
    cols = rp["colunas"]
    i_rp = cols.index("rp")
    i_med = {m: cols.index(MEDIDA_SIOP[m]) for m in VALORES}
    por_chave: dict[tuple, dict[str, dict[str, float]]] = {}
    for l in rp["linhas"]:
        tipos = por_chave.setdefault(tuple(l[:6]), {})
        t = tipos.setdefault(TIPO_DO_RP.get(l[i_rp], "esc"), dict.fromkeys(VALORES, 0.0))
        for m, i in i_med.items():
            t[m] += l[i]

    saida, sem = [], 0
    for l in linhas:
        tipos = por_chave.get(tuple(l[1:7]))
        if not tipos:
            saida.append(l[:7] + ["sem"] + l[7:])
            sem += 1
            continue
        if len(tipos) == 1:
            saida.append(l[:7] + [next(iter(tipos))] + l[7:])
            continue
        nomes = sorted(tipos)
        partes = {t: [] for t in nomes}
        for j, m in enumerate(VALORES):
            # Proporção pela mesma medida; se ela não servir (zero ou sinais trocados), pela dotação atualizada,
            # depois pela inicial; sem nenhuma, tudo vai para o tipo com mais dotação.
            for med in (m, "atualizado", "inicial", "empenhado", "realizado"):
                pesos = [tipos[t][med] for t in nomes]
                if sum(pesos) > 0 and min(pesos) >= 0:
                    break
            else:
                maior = max(nomes, key=lambda t: abs(tipos[t]["atualizado"]))
                pesos = [1.0 if t == maior else 0.0 for t in nomes]
            # Valores inteiros: o último tipo fica com o resto, para a soma bater com a linha original.
            total, soma = l[7 + j], sum(pesos)
            fatias = [round(total * p / soma) for p in pesos[:-1]]
            fatias.append(total - sum(fatias))
            for t, v in zip(nomes, fatias):
                partes[t].append(v)
        for t in nomes:
            if any(partes[t]):
                saida.append(l[:7] + [t] + partes[t])
    return saida, sem


def exportar_explorer(
    con: duckdb.DuckDBPyConnection,
    pasta: Path,
    ipca: dict | None = None,
    nomes_siop: dict[int, dict] | None = None,
    rp_siop: dict[int, dict] | None = None,
) -> list[dict]:
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

        # Troca os nomes em maiúsculas e sem acento pelos oficiais do SIOP.
        trocados = 0
        for dim in ("uo", "programa", "acao"):
            for c in dims[dim]:
                oficial = nome_oficial(nomes_siop or {}, dim, ano, c)
                if oficial:
                    dims[dim][c] = oficial
                    trocados += 1
        total_nomes = sum(len(dims[d]) for d in ("uo", "programa", "acao"))

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
        colunas = [n for n, _, _ in DIMENSOES]
        fonte = "Portal da Transparência (CGU) — Orçamento da Despesa"
        linhas = [list(l) for l in linhas]
        com_tipo = None
        # Tipo de despesa (obrigatória, escolha do governo, emendas, financeira), do SIOP. Sem o SIOP
        # do ano, o arquivo sai como antes, sem a coluna, e o site esconde essa divisão.
        if (rp_siop or {}).get(ano):
            linhas, _ = separar_por_tipo(linhas, rp_siop[ano])
            colunas.append("tipo")
            dims["tipo"] = {c: n for c, n in TIPOS.items()}
            if any(l[7] == "sem" for l in linhas):
                dims["tipo"]["sem"] = "Sem informação"
            fonte += "; tipo de despesa: SIOP (identificador de resultado primário)"
            i_at = len(colunas) + VALORES.index("atualizado")
            com_tipo = round(sum(abs(l[i_at]) for l in linhas if l[7] != "sem") / max(1, sum(abs(l[i_at]) for l in linhas)), 4)
        doc = {
            "ano": ano,
            "gerado_em": gerado_em,
            "fonte": fonte,
            "colunas": colunas + VALORES,
            "dims": dims,
            "linhas": linhas,
        }
        (pasta / f"{ano}.json").write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        resumo.append({"ano": ano, "linhas": len(linhas), **totais,
                       "nomes_oficiais": round(trocados / max(1, total_nomes), 4),
                       **({"com_tipo": com_tipo} if com_tipo is not None else {})})

    (pasta / "anos.json").write_text(
        json.dumps({"gerado_em": gerado_em, "anos": resumo, "ipca": ipca}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return resumo
