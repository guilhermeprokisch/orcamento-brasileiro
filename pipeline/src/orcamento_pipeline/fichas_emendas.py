"""Fichas prontas da busca de emendas (/emendas/buscar): as contas de cada página feitas uma vez só.

    uv run explorador-emendas --so-fichas    # refaz as fichas a partir dos Parquets já gravados

Cada ficha da busca (uma emenda, um parlamentar, uma entidade, uma cidade ou um estado) fazia as contas no
navegador com o DuckDB, a cada visita: uns 3 s só para ligar o motor, mais a leitura dos dados. Aqui as mesmas
contas saem prontas em arquivos JSON pequenos, que a página só lê. O DuckDB fica para a busca por texto.

Saída em data/publico/fichas/<versão>/ (o espelho manda para explorador/fichas/ no bucket):
- emenda/<8 primeiros dígitos>.json  as emendas de um ano e autor: {código: ficha}
- autor/<nome sem acento>.json       {nome: ficha}, com todos os anos
- entidade/<6º ao 8º caractere do CNPJ>.json   {CNPJ: ficha}
- lugar/<código IBGE da cidade, ou o código de 2 dígitos do estado>.json

A versão vem do conteúdo dos Parquets: dados novos, pasta nova, e o cache da Cloudflare nunca mistura fichas
de duas cargas. As contas são as mesmas das consultas de site/src/pages/emendas/buscar.astro; quem mudar uma
muda a outra.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

import duckdb

# Código IBGE de 2 dígitos de cada estado (a página do estado é ?ente=33, por exemplo).
UF_CODIGO = {"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17", "MA": "21", "PI": "22",
             "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29", "MG": "31", "ES": "32",
             "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53"}


# A lista de emendas de uma entidade guarda as 500 maiores: o Banco do Brasil recebeu de 24 mil emendas, e a
# lista inteira faria um arquivo de 3 MB. A página diz quando a lista foi cortada.
MAX_EMENDAS_ENTIDADE = 500


def slug(s: str) -> str:
    """O nome do arquivo de um parlamentar; a página calcula igual (sem acento, minúsculas, hífens)."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "sem-nome"


def grupo_cnpj(codigo: str) -> str:
    """O arquivo de uma entidade: do 6º ao 8º caractere do código (no CNPJ, o fim da raiz, que se espalha por
    igual; o começo não: muitos começam com 000), só letras e números. A página calcula igual."""
    return re.sub(r"[^0-9A-Za-z]", "_", codigo[5:8]) or "_"


def versao(*arquivos: Path) -> str:
    h = hashlib.sha1()
    for a in arquivos:
        with open(a, "rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                h.update(bloco)
    return h.hexdigest()[:10]


def gerar(pagamentos: Path, textos: Path, pasta: Path) -> str:
    """Grava as fichas em pasta/<versão>/ e devolve a versão. Apaga as versões antigas da pasta local."""
    v = versao(pagamentos, textos)
    destino = pasta / v
    if pasta.exists():
        for antiga in pasta.iterdir():
            if antiga.is_dir() and antiga.name != v:
                shutil.rmtree(antiga)
    if destino.exists():
        shutil.rmtree(destino)
    con = duckdb.connect()
    con.execute(f"CREATE TABLE p AS SELECT * FROM read_parquet('{pagamentos}')")
    con.execute(f"CREATE TABLE t AS SELECT * FROM read_parquet('{textos}')")

    def linhas(sql: str):
        cur = con.execute(sql)
        nomes = [d[0] for d in cur.description]
        return [dict(zip(nomes, r)) for r in cur.fetchall()]

    def separar(sql: str, *chaves: str, n: int = 0, por: str = ""):
        """Agrupa o resultado pelas colunas-chave (que saem de cada linha); com n, só as n maiores por grupo."""
        if n:
            sql = f"SELECT * FROM ({sql}) QUALIFY row_number() OVER (PARTITION BY {por} ORDER BY valor DESC) <= {n}"
        g = defaultdict(list)
        for r in linhas(sql):
            g[tuple(r.pop(k) for k in chaves)].append(r)
        if n:
            for lista in g.values():
                lista.sort(key=lambda r: -(r["valor"] or 0))
        return g

    V = "CAST(round(sum(valor)) AS BIGINT) AS valor"
    AREA = "coalesce(nullif(area, ''), 'Sem área')"
    SEMINFO = "'Sem informação'"
    contagem = {}

    # --- Emendas ---------------------------------------------------------------------------------------------
    COD = r"regexp_matches(emenda, '^\d{6,}')"
    resumo = separar(f"""SELECT emenda, any_value(autor) AS autor, any_value(tipo) AS tipo, min(ano)::INTEGER AS de, max(ano)::INTEGER AS ate,
        {V}, count(DISTINCT coalesce(nullif(codigo, ''), favorecido))::INTEGER AS quem FROM p WHERE {COD} GROUP BY emenda""", "emenda")
    quem = separar(f"""SELECT emenda, favorecido, codigo, grupo, municipio, uf, ibge, {V} FROM p WHERE {COD}
        GROUP BY ALL""", "emenda", n=15, por="emenda")
    area = separar(f"SELECT emenda, {AREA} AS area, {V} FROM p WHERE {COD} GROUP BY ALL", "emenda", n=6, por="emenda")
    anos = separar(f"SELECT emenda, ano, {V} FROM p WHERE {COD} GROUP BY ALL ORDER BY emenda, ano", "emenda")
    txt = separar(f"""SELECT emenda, fonte, ano, autor, beneficiario, codigo, uf, municipio, objeto, CAST(round(valor) AS BIGINT) AS valor
        FROM t WHERE {COD}""", "emenda", n=20, por="emenda")
    arquivos = defaultdict(dict)
    for (e,) in set(resumo) | set(txt):
        s = (resumo.get((e,)) or [{"autor": None, "tipo": None, "de": None, "ate": None, "valor": 0, "quem": 0}])[0]
        arquivos[e[:8]][e] = {"s": s, "quem": quem.get((e,), []), "area": area.get((e,), []), "anos": anos.get((e,), []),
                              "textos": txt.get((e,), [])}
    contagem["emenda"] = gravar(destino / "emenda", arquivos)

    # --- Parlamentares (e bancadas, comissões, relator): um arquivo com todos os anos -------------------------
    s_ano = separar(f"""SELECT autor, ano, count(DISTINCT emenda)::INTEGER AS emendas, {V},
        count(DISTINCT coalesce(nullif(ibge, ''), municipio || uf))::INTEGER AS lugares,
        CAST(round(sum(CASE WHEN tipo = 'Pix' THEN valor ELSE 0 END)) AS BIGINT) AS pix, any_value(tipo) AS tipo FROM p GROUP BY ALL""", "autor", "ano")
    onde = separar(f"SELECT autor, ano, municipio, uf, ibge, {V} FROM p GROUP BY ALL", "autor", "ano", n=10, por="autor, ano")
    quem_g = separar(f"SELECT autor, ano, grupo, {V} FROM p GROUP BY ALL ORDER BY autor, ano, valor DESC", "autor", "ano")
    area_a = separar(f"SELECT autor, ano, {AREA} AS area, {V} FROM p GROUP BY ALL", "autor", "ano", n=6, por="autor, ano")
    ent = separar(f"""SELECT autor, ano, favorecido, codigo, {V} FROM p WHERE grupo IN ('Entidade sem fins lucrativos', 'Empresa')
        GROUP BY ALL""", "autor", "ano", n=8, por="autor, ano")
    pix = separar(f"""SELECT autor, ano, beneficiario, objeto, CAST(round(valor) AS BIGINT) AS valor FROM t WHERE fonte = 'Plano de emenda Pix'""", "autor", "ano", n=10, por="autor, ano")
    em_a = separar(f"""SELECT autor, ano, emenda, any_value(tipo) AS tipo, mode(favorecido) AS favorecido, count(DISTINCT favorecido)::INTEGER AS n, {V}
        FROM p WHERE emenda <> {SEMINFO} GROUP BY ALL""", "autor", "ano", n=10, por="autor, ano")
    autores = defaultdict(dict)
    for (a, ano), (s,) in s_ano.items():
        k = (a, ano)
        autores[a][str(ano)] = {"s": s, "onde": onde.get(k, []), "quem": quem_g.get(k, []), "area": area_a.get(k, []),
                                "ent": ent.get(k, []), "pix": pix.get(k, []), "emendas": em_a.get(k, [])}
    arquivos = defaultdict(dict)
    for a, por_ano in autores.items():
        arquivos[slug(a)][a] = {"anos": sorted(int(x) for x in por_ano), "porAno": por_ano}
    contagem["autor"] = gravar(destino / "autor", arquivos)

    # --- Entidades (quem recebeu, pelo CNPJ) --------------------------------------------------------------------
    s_e = separar(f"""SELECT codigo, mode(favorecido) AS nome, any_value(municipio) AS municipio, any_value(uf) AS uf, {V},
        count(DISTINCT emenda)::INTEGER AS emendas FROM p WHERE codigo <> '' GROUP BY codigo""", "codigo")
    anos_e = separar(f"SELECT codigo, ano, {V} FROM p WHERE codigo <> '' GROUP BY ALL ORDER BY codigo, ano", "codigo")
    aut_e = separar(f"SELECT codigo, autor, {V} FROM p WHERE codigo <> '' GROUP BY ALL", "codigo", n=10, por="codigo")
    txt_e = separar(f"""SELECT codigo, fonte, ano, autor, objeto, CAST(round(valor) AS BIGINT) AS valor, emenda FROM t WHERE codigo <> ''""", "codigo", n=15, por="codigo")
    em_e = separar(f"""SELECT codigo, emenda, any_value(autor) AS autor, any_value(tipo) AS tipo, min(ano)::INTEGER AS de, max(ano)::INTEGER AS ate,
        mode(coalesce(nullif(area, ''), '')) AS area, {V} FROM p WHERE codigo <> '' AND emenda <> {SEMINFO} GROUP BY ALL ORDER BY codigo, valor DESC""", "codigo")
    sem_e = {k: r[0]["valor"] for k, r in separar(f"SELECT codigo, {V} FROM p WHERE codigo <> '' AND emenda = {SEMINFO} GROUP BY codigo", "codigo").items()}
    arquivos = defaultdict(dict)
    for (c,), (s,) in s_e.items():
        k = (c,)
        arquivos[grupo_cnpj(c)][c] = {"s": s, "anos": anos_e.get(k, []), "autores": aut_e.get(k, []), "textos": txt_e.get(k, []),
                                      "emendas": em_e.get(k, [])[:MAX_EMENDAS_ENTIDADE], "sem": sem_e.get(k, 0)}
    contagem["entidade"] = gravar(destino / "entidade", arquivos)

    # --- Lugares: cada cidade (pelo código IBGE) e cada estado (pela UF), com todos os anos -------------------
    con.execute("""CREATE TABLE l AS SELECT ibge AS ente, * FROM p WHERE ibge <> ''
        UNION ALL SELECT uf AS ente, * FROM p WHERE uf <> '' AND uf <> '-1'""")
    s_l = separar(f"""SELECT ente, ano, any_value(municipio) AS municipio, any_value(uf) AS uf, {V}, count(DISTINCT emenda)::INTEGER AS emendas
        FROM l GROUP BY ALL""", "ente", "ano")
    aut_l = separar(f"SELECT ente, ano, autor, {V} FROM l GROUP BY ALL", "ente", "ano", n=10, por="ente, ano")
    quem_l = separar(f"SELECT ente, ano, favorecido, codigo, grupo, {V} FROM l GROUP BY ALL", "ente", "ano", n=10, por="ente, ano")
    area_l = separar(f"SELECT ente, ano, {AREA} AS area, {V} FROM l GROUP BY ALL", "ente", "ano", n=6, por="ente, ano")
    em_l = separar(f"""SELECT ente, ano, emenda, any_value(autor) AS autor, mode(favorecido) AS favorecido, {V} FROM l WHERE emenda <> {SEMINFO}
        GROUP BY ALL""", "ente", "ano", n=10, por="ente, ano")
    lugares = defaultdict(dict)
    for (ente, ano), (s,) in s_l.items():
        k = (ente, ano)
        lugares[UF_CODIGO.get(ente, ente)][str(ano)] = {"s": s, "autores": aut_l.get(k, []), "quem": quem_l.get(k, []),
                                                         "area": area_l.get(k, []), "emendas": em_l.get(k, [])}
    destino_l = destino / "lugar"
    destino_l.mkdir(parents=True, exist_ok=True)
    for ente, por_ano in lugares.items():
        if not re.fullmatch(r"\d{2}|\d{7}", ente):
            continue
        (destino_l / f"{ente}.json").write_text(json.dumps({"anos": sorted(int(x) for x in por_ano), "porAno": por_ano},
                                                           ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    contagem["lugar"] = len(list(destino_l.iterdir()))

    total = sum(f.stat().st_size for f in destino.rglob("*.json"))
    print(f"fichas {v}: " + ", ".join(f"{n} de {k}" for k, n in contagem.items()) + f"; {total / 1e6:.0f} MB em data/publico/fichas/{v}")
    return v


def gravar(pasta: Path, arquivos: dict[str, dict]) -> int:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in arquivos.items():
        (pasta / f"{nome}.json").write_text(json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(arquivos)
