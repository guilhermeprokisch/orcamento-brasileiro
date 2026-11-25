"""Análise: as emendas seguem os votos? Emendas individuais e Pix pagas de 2023 a 2026 × votos de cada
deputado federal em cada município (2022) × população, e a variação dos votos em 2026.

    uv run analise-emendas-votos                # baixa o que faltar das fontes e roda tudo
    uv run analise-emendas-votos --do-espelho   # pega os insumos já reduzidos no espelho e só roda a análise
    uv run analise-emendas-votos --publicar     # envia insumos e resultados ao espelho (precisa da chave do B2)

O texto da análise, com método e limites, está em analises/emendas-votos/README.md.

Fontes (cache em data/raw):
- Emendas pagas: data/publico/emendas-pagamentos.parquet (`uv run explorador-emendas`; no espelho em
  explorador/emendas-pagamentos.parquet).
- Saúde de 2023–24: o Portal da Transparência registra boa parte dessas emendas como pagas ao Banco do
  Brasil, em Brasília, sem a cidade. O Fundo Nacional de Saúde publica cada proposta, com o fundo de saúde de
  destino, o município e o parlamentar: uma planilha por UF e ano (consultafns.saude.gov.br, API pública
  recursos/proposta/planilha). Cada planilha leva minutos; baixam três por vez.
- Votos: TSE, votação por candidato e município, 2022 e 2026 (cdn.tse.jus.br, uns 1 GB os dois).
- População: IBGE, Censo 2022 (tabela 4709).
- Deputados: Câmara, dados abertos, legislatura 57 (o mesmo cache do mapa das emendas).

Saída em data/analises/emendas-votos/:
- insumos/  votos-deputado-federal.parquet, fns-propostas.parquet, populacao-2022.csv, deputados.csv
            (o que vai ao espelho, para quem quiser refazer sem baixar as fontes)
- painel.parquet         deputado × município do estado dele: emenda, votos de 2022 e de 2026, população
- resultados.json        os números da análise (os que o texto cita)
- preco-por-deputado.csv R$ de emenda por voto de cada deputado
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import numpy as np

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

SAIDA = c.RAIZ / "data" / "analises" / "emendas-votos"
INSUMOS = SAIDA / "insumos"
RAW = c.RAIZ / "data" / "raw"
PAGAMENTOS = c.RAIZ / "data" / "publico" / "emendas-pagamentos.parquet"
BUCKET = "orcamento-brasileiro-dados"
ESPELHO = f"https://dados.orcamentobrasileiro.com.br/file/{BUCKET}"
PREFIXO = "analises/emendas-votos"

ANOS_EMENDA = (2023, 2026)
ANOS_FNS = (2023, 2024)          # a partir de 2025 o Portal já registra o fundo municipal
BB = "00000000000191"            # Banco do Brasil: o favorecido sem cidade
DF = "5300108"                   # Brasília: o pagamento vai a entidades com sede lá
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
FNS = "https://consultafns.saude.gov.br/recursos/proposta/planilha"
IBGE = "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93?localidades=N6[all]"
# Reserva para os poucos municípios cujo nome no TSE difere do IBGE (repositório público sem licença:
# só consultado, nunca copiado para cá).
TSE_IBGE_RESERVA = "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv"
# Títulos e partículas ignorados ao casar o nome do deputado com o nome de urna.
TITULOS = set("dr dra pr pra pastor pastora delegado delegada coronel capitao general sargento cabo professor professora prof "
              "junior jr filho neto da de do das dos e missionario irmao tenente major subtenente bispo padre doutor doutora "
              "enfermeira enfermeiro".split())


# ---------------------------------------------------------------- utilidades

def chave(nome: str) -> str:
    """Nome comparável: sem acento, sem pontuação, minúsculo, sem o "Dep."/"Sen." do começo."""
    n = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z ]", " ", n)).strip().lower()
    return re.sub(r"^(dep|sen|deputad[oa]|senador[a]?) ", "", n)


def tokens(k: str) -> set[str]:
    return {t for t in k.split() if t not in TITULOS and len(t) > 1}


def baixar(url: str, destino: Path, dados: bytes | None = None, timeout: int = 900) -> Path:
    """Baixa para o cache (uma vez só); POST quando `dados` vem preenchido."""
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    cab = {"User-Agent": USER_AGENT} | ({"Content-Type": "application/json"} if dados else {})
    req = urllib.request.Request(url, data=dados, headers=cab)
    parte = destino.with_suffix(destino.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout, context=CONTEXTO_TLS) as r, open(parte, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    parte.rename(destino)
    return destino


def reais(x) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(s) if s else 0.0


# ---------------------------------------------------------------- insumos

def municipios_ibge() -> list[tuple[str, str, str, int]]:
    """(ibge, nome, uf, população do Censo 2022)."""
    doc = json.loads(baixar(IBGE, RAW / "ibge" / "censo-2022-populacao-municipios.json").read_text(encoding="utf-8"))
    linhas = []
    for s in doc[0]["resultados"][0]["series"]:
        nome, uf = s["localidade"]["nome"].rsplit(" - ", 1)
        linhas.append((s["localidade"]["id"], nome, uf, int(s["serie"]["2022"])))
    return linhas


def deputados() -> list[tuple[str, str, str]]:
    """(nome, uf, partido) dos deputados da legislatura 57, do mesmo cache que o mapa das emendas usa."""
    from .emendas_mapa import baixar_json
    pag, url, saida = 1, "https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura=57&itens=100", {}
    while url:
        doc = baixar_json(url, f"camara-57-{pag}.json")
        for d in doc["dados"]:
            saida[(d["nome"], d["siglaUf"])] = d.get("siglaPartido") or ""
        url = next((l["href"] for l in doc["links"] if l["rel"] == "next"), None)
        pag += 1
    return [(n, uf, p) for (n, uf), p in sorted(saida.items())]


def votos_tse(con: duckdb.DuckDBPyConnection, ano: int, ibge_por_nome: dict[tuple[str, str], str]) -> None:
    """Votos válidos de cada candidato a deputado federal, por município (somadas as zonas), na tabela votos."""
    zip_ = baixar(TSE.format(ano=ano), RAW / "tse" / f"votacao_candidato_munzona_{ano}.zip", timeout=3600)
    pasta = RAW / "tse" / f"_csv_{ano}"
    pasta.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_) as z:
        for nome in z.namelist():
            if re.search(r"_[A-Z]{2}\.csv$", nome) and not nome.endswith("_BR.csv") and not (pasta / nome).exists():
                z.extract(nome, pasta)
    con.sql(f"""CREATE OR REPLACE TEMP TABLE tse AS
                SELECT SG_UF uf, CD_MUNICIPIO::INT cd, NM_MUNICIPIO mun, SQ_CANDIDATO sq, NM_CANDIDATO nome, NM_URNA_CANDIDATO urna,
                       SG_PARTIDO partido, DS_SIT_TOT_TURNO situacao, sum(QT_VOTOS_NOMINAIS_VALIDOS::BIGINT) votos
                FROM read_csv('{pasta}/*.csv', delim=';', encoding='latin-1', header=true, all_varchar=true)
                WHERE CD_CARGO = '6' GROUP BY ALL""")
    shutil.rmtree(pasta)
    # Município do TSE → IBGE pelo nome; a reserva só para o que não casar.
    nomes = {(uf, cd): chave(mun) for uf, cd, mun in con.sql("SELECT DISTINCT uf, cd, mun FROM tse").fetchall()}
    faltam = {k for k, kmun in nomes.items() if (k[0], kmun) not in ibge_por_nome}
    reserva: dict[tuple[str, int], str] = {}
    if faltam:
        txt = baixar(TSE_IBGE_RESERVA, RAW / "tse" / "municipios_brasileiros_tse.csv").read_text(encoding="utf-8")
        for linha in txt.splitlines()[1:]:
            cod_tse, uf, _, _, ibge = linha.split(",")
            reserva[(uf, int(cod_tse))] = ibge
        print(f"  TSE {ano}: {len(faltam)} municípios com nome diferente do IBGE, casados pela tabela de reserva: "
              f"{sorted(nomes[k] + '/' + k[0] for k in faltam)}", flush=True)
    pares = [(uf, cd, ibge_por_nome.get((uf, k)) or reserva.get((uf, cd))) for (uf, cd), k in nomes.items()]
    # A grafia do TSE passa a valer também para as outras fontes (o FNS usa a mesma grafia antiga).
    for (uf, cd, ibge), k in zip(pares, nomes.values()):
        if ibge:
            ibge_por_nome.setdefault((uf, k), ibge)
    con.sql("CREATE OR REPLACE TEMP TABLE tse_ibge(uf VARCHAR, cd INT, ibge VARCHAR)")
    con.executemany("INSERT INTO tse_ibge VALUES (?, ?, ?)", pares)
    con.sql(f"""INSERT INTO votos SELECT {ano}, t.uf, m.ibge, sq, nome, urna, partido, situacao, votos
                FROM tse t LEFT JOIN tse_ibge m USING (uf, cd)""")


def planilhas_fns() -> list[Path]:
    pasta = RAW / "fns" / "propostas-individuais"
    pedidos = [(uf, ano) for ano in ANOS_FNS for uf in UFS]

    def um(p):
        uf, ano = p
        corpo = json.dumps({"sgUf": uf, "ano": str(ano), "tpEmenda": "INDIVIDUAL"}).encode()
        arq = baixar(FNS, pasta / f"{uf}_{ano}.xlsx", dados=corpo)
        print(f"  FNS {uf} {ano}: {arq.stat().st_size // 1024} KB", flush=True)
        return arq

    faltam = [p for p in pedidos if not (pasta / f"{p[0]}_{p[1]}.xlsx").exists()]
    if faltam:
        print(f"FNS: {len(faltam)} planilhas a baixar (minutos cada, três por vez)", flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(um, faltam))
    return [pasta / f"{uf}_{ano}.xlsx" for uf, ano in pedidos]


def propostas_fns(ibge_por_nome: dict[tuple[str, str], str]) -> list[tuple]:
    """Cada linha: proposta × parlamentar, com o valor pago proporcional ao que ele indicou."""
    from openpyxl import load_workbook
    linhas = []
    for arq in planilhas_fns():
        ws = load_workbook(arq, read_only=True).active
        ws.reset_dimensions()   # a planilha do FNS declara só a primeira célula; sem isto, só sai o cabeçalho
        it = ws.iter_rows(values_only=True)
        cab = [chave(h).replace(" ", "_") for h in next(it)]
        for r in it:
            d = dict(zip(cab, r))
            if not d.get("no_proposta"):
                continue
            vprop, vpago, vind = reais(d["valor_proposta"]), reais(d["valor_pago"]), reais(d["valor_ind_objeto"])
            pago = vind * vpago / vprop if vprop else 0.0
            uf = d["uf"]
            linhas.append((d["no_proposta"], int(d["ano"]), uf, ibge_por_nome.get((uf, chave(d["municipio"]))),
                           d["municipio"], d["entidade"], d["tipo"], d["apelido"], d["partido"], pago))
    return linhas


def montar_insumos() -> None:
    INSUMOS.mkdir(parents=True, exist_ok=True)
    mun = municipios_ibge()
    por_nome = {(uf, chave(nome)): ibge for ibge, nome, uf, _ in mun}
    # Grafias do FNS que nem o IBGE nem o TSE usam.
    por_nome |= {("SE", "gracho cardoso"): "2802601", ("MT", "poxoreo"): "5107008", ("BA", "muquem de sao francisco"): "2922250"}
    con = duckdb.connect()
    con.sql("CREATE TABLE pop(ibge VARCHAR, municipio VARCHAR, uf VARCHAR, populacao BIGINT)")
    con.executemany("INSERT INTO pop VALUES (?, ?, ?, ?)", mun)
    con.sql(f"COPY pop TO '{INSUMOS / 'populacao-2022.csv'}' (HEADER)")

    con.sql("CREATE TABLE dep(nome VARCHAR, uf VARCHAR, partido VARCHAR)")
    con.executemany("INSERT INTO dep VALUES (?, ?, ?)", deputados())
    con.sql(f"COPY dep TO '{INSUMOS / 'deputados.csv'}' (HEADER)")

    con.sql("""CREATE TABLE votos(ano INT, uf VARCHAR, ibge VARCHAR, sq VARCHAR, nome VARCHAR, urna VARCHAR,
                                  partido VARCHAR, situacao VARCHAR, votos BIGINT)""")
    for ano in (2022, 2026):
        print(f"TSE {ano}", flush=True)
        votos_tse(con, ano, por_nome)
    sem = con.sql("SELECT count(*) FROM votos WHERE ibge IS NULL").fetchall()[0][0]
    print(f"  votos sem município IBGE: {sem} linhas", flush=True)
    con.sql(f"COPY (SELECT * FROM votos ORDER BY ano, uf, sq, ibge) TO '{INSUMOS / 'votos-deputado-federal.parquet'}'")

    con.sql("""CREATE TABLE fns(proposta VARCHAR, ano INT, uf VARCHAR, ibge VARCHAR, municipio VARCHAR, entidade VARCHAR,
                                tipo VARCHAR, parlamentar VARCHAR, partido VARCHAR, pago DOUBLE)""")
    con.executemany("INSERT INTO fns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", propostas_fns(por_nome))
    print(con.sql("SELECT ano, count(*) linhas, round(sum(pago) / 1e9, 2) bi_pagos, count(*) FILTER (ibge IS NULL) sem_ibge FROM fns GROUP BY 1 ORDER BY 1"))
    con.sql(f"COPY (SELECT * FROM fns ORDER BY ano, uf, proposta) TO '{INSUMOS / 'fns-propostas.parquet'}'")


def insumos_do_espelho() -> None:
    for nome in ("votos-deputado-federal.parquet", "fns-propostas.parquet", "populacao-2022.csv", "deputados.csv"):
        print(f"espelho: {nome}", flush=True)
        baixar(f"{ESPELHO}/{PREFIXO}/insumos/{nome}", INSUMOS / nome)
    if not PAGAMENTOS.exists():
        print("espelho: emendas-pagamentos.parquet", flush=True)
        baixar(f"{ESPELHO}/explorador/emendas-pagamentos.parquet", PAGAMENTOS)


# ---------------------------------------------------------------- painel

def casar_deputados(con: duckdb.DuckDBPyConnection) -> None:
    """Cada deputado do cadastro ↔ um candidato do TSE de 2022 no mesmo estado (nome de urna ou civil)."""
    cand: dict[str, list] = {}
    for uf, sq, urna, nome, sit, v in con.sql("SELECT uf, sq, urna, nome, situacao, sum(votos) FROM votos WHERE ano = 2022 GROUP BY ALL").fetchall():
        cand.setdefault(uf, []).append((sq, chave(urna), chave(nome), sit, v))
    pares, sem_par = [], []
    for nome, uf in con.sql("SELECT nome, uf FROM dep").fetchall():
        k, tk, melhor = chave(nome), tokens(chave(nome)), None
        for sq, ku, kn, sit, v in cand.get(uf, []):
            if k in (ku, kn):
                s = 3
            elif tokens(ku) and (tokens(ku) <= tk or tk <= tokens(ku)):
                s = 2
            elif tk and tk <= tokens(kn):
                s = 1
            else:
                continue
            candidato = (s, sit != "NÃO ELEITO", v, sq)
            melhor = max(melhor, candidato) if melhor else candidato
        if melhor and melhor[1]:
            pares.append((k, uf, melhor[3]))
        else:
            sem_par.append(f"{nome} ({uf})")
    con.sql("CREATE OR REPLACE TABLE casados(k VARCHAR, uf VARCHAR, sq VARCHAR)")
    con.executemany("INSERT INTO casados VALUES (?, ?, ?)", pares)
    print(f"deputados casados com o TSE: {len(pares)}; sem par: {len(sem_par)} {sem_par}", flush=True)


def montar_painel() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.create_function("chave", chave, ["VARCHAR"], "VARCHAR")
    con.sql(f"CREATE TABLE votos AS SELECT * FROM '{INSUMOS / 'votos-deputado-federal.parquet'}'")
    con.sql(f"CREATE TABLE fns AS SELECT * FROM '{INSUMOS / 'fns-propostas.parquet'}'")
    con.sql(f"CREATE TABLE pop AS SELECT * FROM read_csv('{INSUMOS / 'populacao-2022.csv'}', types={{'ibge': 'VARCHAR'}})")
    con.sql(f"CREATE TABLE dep AS SELECT * FROM read_csv('{INSUMOS / 'deputados.csv'}')")
    casar_deputados(con)
    a0, a1 = ANOS_EMENDA
    fns_anos = ", ".join(map(str, ANOS_FNS))
    # Portal, menos o que o FNS cobre melhor (toda a saúde individual de 2023–24, e o que foi ao BB);
    # mais o FNS. Brasília fica fora: lá o pagamento vai a entidades com sede na capital.
    con.sql(f"""CREATE TABLE emendas AS
        WITH portal AS (
            SELECT chave(autor) k, ibge, valor, CASE WHEN tipo = 'Pix' THEN valor ELSE 0 END pix, 0.0 fns
            FROM '{PAGAMENTOS}'
            WHERE tipo IN ('Individual', 'Pix') AND ano BETWEEN {a0} AND {a1}
              AND NOT (coalesce(codigo, '') = '{BB}' OR (tipo = 'Individual' AND area = 'Saúde' AND ano IN ({fns_anos})))
              AND coalesce(ibge, '') NOT IN ('', '{DF}')),
        saude AS (SELECT chave(parlamentar) k, ibge, pago valor, 0.0 pix, pago fns FROM fns
                  WHERE ano IN ({fns_anos}) AND ibge IS NOT NULL AND ibge <> '{DF}' AND pago > 0)
        SELECT k, ibge, sum(valor) valor, sum(pix) pix, sum(fns) fns FROM (SELECT * FROM portal UNION ALL SELECT * FROM saude) GROUP BY ALL""")
    con.sql("""CREATE TABLE painel AS
        WITH d AS (SELECT DISTINCT sq, uf FROM casados),
        em AS (SELECT c.sq, e.ibge, sum(e.valor) emenda, sum(e.pix) pix, sum(e.fns) fns FROM emendas e JOIN casados c USING (k) GROUP BY ALL),
        v22 AS (SELECT sq, ibge, sum(votos) votos FROM votos WHERE ano = 2022 GROUP BY ALL),
        val AS (SELECT ibge, sum(votos) validos FROM votos WHERE ano = 2022 GROUP BY 1),
        ponte AS (SELECT DISTINCT sq, uf, nome FROM votos WHERE ano = 2022),
        v26 AS (SELECT p.sq, v.ibge, sum(v.votos) votos26 FROM votos v JOIN ponte p ON p.uf = v.uf AND p.nome = v.nome
                WHERE v.ano = 2026 GROUP BY ALL)
        SELECT d.sq, d.uf, p.ibge, p.populacao, coalesce(val.validos, 0) validos, coalesce(v22.votos, 0) votos,
               v26.votos26, coalesce(em.emenda, 0) emenda, coalesce(em.pix, 0) pix, coalesce(em.fns, 0) fns
        FROM d JOIN pop p ON p.uf = d.uf
        LEFT JOIN v22 ON v22.sq = d.sq AND v22.ibge = p.ibge LEFT JOIN val ON val.ibge = p.ibge
        LEFT JOIN em ON em.sq = d.sq AND em.ibge = p.ibge LEFT JOIN v26 ON v26.sq = d.sq AND v26.ibge = p.ibge
        WHERE d.uf <> 'DF'""")
    # Só deputados com emenda e voto no estado; concorreu em 2026 = teve algum voto em 2026.
    con.sql("""CREATE OR REPLACE TABLE painel AS SELECT *,
                 sum(emenda) OVER w em_tot, sum(votos) OVER w vot_tot, sum(populacao) OVER w pop_tot,
                 sum(votos26) OVER w v26_tot FROM painel WINDOW w AS (PARTITION BY sq)""")
    con.sql("DELETE FROM painel WHERE em_tot = 0 OR vot_tot = 0")
    con.sql(f"COPY (SELECT * EXCLUDE (em_tot, vot_tot, pop_tot, v26_tot) FROM painel ORDER BY sq, ibge) TO '{SAIDA / 'painel.parquet'}'")
    return con


# ---------------------------------------------------------------- estimativas

def ppml(y: np.ndarray, X: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Poisson com efeito fixo de grupo (verossimilhança concentrada); erros agrupados por grupo."""
    G = g.max() + 1
    Y = np.bincount(g, y, G)
    n_g = np.bincount(g, minlength=G)
    b = np.zeros(X.shape[1])
    for _ in range(100):
        eta = X @ b
        eta -= (np.bincount(g, eta, G) / n_g)[g]
        e = np.exp(eta)
        p = e / np.bincount(g, e, G)[g]
        mu = Y[g] * p
        px = np.stack([np.bincount(g, p * X[:, j], G) for j in range(X.shape[1])], 1)
        Xc = X - px[g]
        H = (Xc * mu[:, None]).T @ Xc
        passo = np.linalg.solve(H, (X * (y - mu)[:, None]).sum(0))
        b += passo
        if np.abs(passo).max() < 1e-9:
            break
    s = Xc * (y - mu)[:, None]
    sg = np.stack([np.bincount(g, s[:, j], G) for j in range(X.shape[1])], 1)
    Hi = np.linalg.inv(H)
    return b, np.sqrt(np.diag(Hi @ (sg.T @ sg) @ Hi))


def mqo_dois_efeitos(y: np.ndarray, X: np.ndarray, g1: np.ndarray, g2: np.ndarray, it: int = 60) -> tuple[np.ndarray, np.ndarray]:
    """Mínimos quadrados com efeito fixo de deputado e de município (projeções alternadas); erros por deputado."""
    Z = np.column_stack([y, X]).astype(float)
    n1, n2 = np.bincount(g1), np.bincount(g2)
    for _ in range(it):
        Z -= np.stack([np.bincount(g1, Z[:, j]) / n1 for j in range(Z.shape[1])], 1)[g1]
        Z -= np.stack([np.bincount(g2, Z[:, j]) / n2 for j in range(Z.shape[1])], 1)[g2]
    yy, XX = Z[:, 0], Z[:, 1:]
    XtXi = np.linalg.inv(XX.T @ XX)
    b = XtXi @ XX.T @ yy
    e = yy - XX @ b
    sg = np.stack([np.bincount(g1, XX[:, j] * e) for j in range(XX.shape[1])], 1)
    return b, np.sqrt(np.diag(XtXi @ (sg.T @ sg) @ XtXi))


def grupos(*cols: np.ndarray) -> np.ndarray:
    return np.unique(np.column_stack(cols) if len(cols) > 1 else cols[0], axis=0, return_inverse=True)[1].ravel()


def estimar(con: duckdb.DuckDBPyConnection) -> dict:
    r: dict = {}
    q = lambda sql: con.sql(sql).fetchall()
    [(n_dep, n_pares, bi, bi_fns)] = q("SELECT count(DISTINCT sq), count(*), sum(emenda) / 1e9, sum(fns) / 1e9 FROM painel")
    r["painel"] = {"deputados": n_dep, "pares": n_pares, "emendas_bi": round(bi, 2), "das_quais_fns_bi": round(bi_fns, 2)}

    # 1. Elasticidades (PPML, efeito fixo de deputado)
    sq, emenda, votos, pop, validos = (np.array(x) for x in zip(*q("SELECT sq, emenda, votos, populacao, validos FROM painel")))
    g = grupos(sq)
    y = emenda.astype(float) / 1e6
    lv, z, lp, lval = np.log1p(votos.astype(float)), (votos == 0).astype(float), np.log(pop.astype(float)), np.log1p(validos.astype(float))
    modelos = {"so_votos": ([lv, z], ["votos", "zero_voto"]), "so_populacao": ([lp], ["populacao"]),
               "votos_e_populacao": ([lv, z, lp], ["votos", "zero_voto", "populacao"]),
               "votos_e_eleitorado": ([lv, z, lval], ["votos", "zero_voto", "votos_validos"])}
    r["elasticidades"] = {}
    for nome, (cols, rot) in modelos.items():
        b, ep = ppml(y, np.column_stack(cols), g)
        r["elasticidades"][nome] = {k: {"coef": round(float(bi_), 3), "ep": round(float(ei), 3)} for k, bi_, ei in zip(rot, b, ep)}

    # 2. Concentração e margem extensiva
    con.sql("""CREATE OR REPLACE TABLE p2 AS SELECT *, emenda / em_tot s_em, votos / vot_tot s_vot, populacao / pop_tot s_pop,
                 row_number() OVER (PARTITION BY sq ORDER BY votos DESC, ibge) posicao,
                 CASE WHEN validos > 0 THEN votos / validos ELSE 0 END dominio FROM painel""")
    r["concentracao"] = {f"top{k}": dict(zip(("emendas", "votos", "populacao"), map(lambda x: round(x, 3), q(
        f"SELECT sum(emenda) FILTER (posicao <= {k}) / sum(emenda), sum(votos) FILTER (posicao <= {k}) / sum(votos), "
        f"sum(populacao) FILTER (posicao <= {k}) / sum(populacao) FROM p2")[0]))) for k in (1, 5, 10, 20)}
    [(p0, p1, sh0, base_sem)] = q("""SELECT avg((emenda > 0)::INT) FILTER (votos = 0), avg((emenda > 0)::INT) FILTER (votos > 0),
                                          sum(emenda) FILTER (votos = 0) / sum(emenda), avg((emenda = 0)::INT) FILTER (s_vot >= 0.01) FROM p2""")
    r["margem"] = {"chance_receber_sem_voto": round(p0, 3), "chance_receber_com_voto": round(p1, 3),
                   "fatia_emendas_sem_voto": round(sh0, 4), "municipios_base_sem_emenda": round(base_sem, 3)}
    r["correlacao_dentro_do_deputado"] = dict(zip(("votos_mediana", "populacao_mediana", "fatia_deputados_votos_maior"), map(lambda x: round(x, 3), q(
        """SELECT median(rv), median(rp), avg((rv > rp)::INT) FROM
           (SELECT sq, corr(s_em, s_vot) rv, corr(s_em, s_pop) rp FROM p2 GROUP BY sq)""")[0])))

    # 3. Tabelas por faixa
    def faixas(expr: str, cortes: list[float], rotulos: list[str], onde: str = "TRUE") -> list[dict]:
        caso = " ".join(f"WHEN {expr} <= {c_} THEN {i}" for i, c_ in enumerate(cortes)) + f" ELSE {len(cortes)}"
        linhas = q(f"""SELECT CASE {caso} END f, count(*), avg((emenda > 0)::INT), sum(emenda), sum(votos), sum(populacao)
                       FROM p2 WHERE {onde} GROUP BY 1 ORDER BY 1""")
        return [{"faixa": rotulos[f], "pares": n, "chance_receber": round(p, 3), "emenda": round(e), "votos": int(v),
                 "reais_por_voto": round(e / v) if v else None, "reais_por_habitante": round(e / h, 2)} for f, n, p, e, v, h in linhas]
    r["por_fatia_dos_votos"] = faixas("s_vot", [0, 1e-4, 5e-4, 1e-3, 2.5e-3, 5e-3, 1e-2, 2e-2, 5e-2],
        ["0", "até 0,01%", "0,01–0,05%", "0,05–0,1%", "0,1–0,25%", "0,25–0,5%", "0,5–1%", "1–2%", "2–5%", "mais de 5%"])
    r["por_dominio_local"] = faixas("dominio", [0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5],
        ["menos de 1%", "1–3%", "3–5%", "5–10%", "10–20%", "20–30%", "30–50%", "mais de 50%"], "votos > 0")
    r["por_porte"] = faixas("populacao", [5e3, 1e4, 2e4, 5e4, 1e5, 5e5],
        ["até 5 mil", "5–10 mil", "10–20 mil", "20–50 mil", "50–100 mil", "100–500 mil", "mais de 500 mil"], "votos > 0")

    # 4. Preço médio do voto por deputado (mecânico: a cota é igual, os votos não)
    con.sql(f"""COPY (SELECT sq, any_value(uf) uf, round(any_value(em_tot)) emenda, any_value(vot_tot) votos,
                      round(any_value(em_tot) / any_value(vot_tot), 2) reais_por_voto FROM painel GROUP BY sq ORDER BY reais_por_voto)
                TO '{SAIDA / 'preco-por-deputado.csv'}' (HEADER)""")
    r["preco_por_deputado"] = dict(zip(("mediana", "p10", "p90"), map(round, q(
        "SELECT median(x), quantile_cont(x, 0.1), quantile_cont(x, 0.9) FROM (SELECT any_value(em_tot) / any_value(vot_tot) x FROM painel GROUP BY sq)")[0])))

    # 5. Votos em 2026 (quem concorreu de novo no mesmo estado)
    [(conc,)] = q("SELECT count(DISTINCT sq) FROM painel WHERE v26_tot > 0")
    d = q("SELECT sq, ibge, emenda, votos, coalesce(votos26, 0) FROM painel WHERE v26_tot > 0")
    sq6, ib6, em6, v22, v26 = (np.array(x) for x in zip(*d))
    em6, v22, v26 = em6.astype(float), v22.astype(float), v26.astype(float)
    dlog, le, lv22 = np.log1p(v26) - np.log1p(v22), np.log1p(em6 / 1e3), np.log1p(v22)
    g1, g2 = grupos(sq6), grupos(ib6)
    b, ep = mqo_dois_efeitos(dlog, np.column_stack([le, lv22]), g1, g2)
    m = v22 >= 50
    b50, ep50 = mqo_dois_efeitos(dlog[m], np.column_stack([le[m], lv22[m]]), grupos(sq6[m]), grupos(ib6[m]))
    r["votos_2026"] = {"deputados_que_concorreram": conc,
                       "elasticidade_votos_a_emenda": {"coef": round(float(b[0]), 3), "ep": round(float(ep[0]), 3)},
                       "elasticidade_com_50_votos_ou_mais": {"coef": round(float(b50[0]), 3), "ep": round(float(ep50[0]), 3)}}
    quartis = q("""WITH b AS (SELECT *, emenda / votos rpv FROM painel WHERE v26_tot > 0 AND votos >= 50),
                   r AS (SELECT *, CASE WHEN emenda = 0 THEN 'sem emenda'
                         ELSE 'Q' || least(4, 1 + floor(4 * (percent_rank() OVER (PARTITION BY sq, emenda > 0 ORDER BY rpv))))::INT END grupo FROM b)
                   SELECT grupo, count(*), sum(votos), sum(coalesce(votos26, 0)), sum(emenda) FROM r GROUP BY 1 ORDER BY 1""")
    r["votos_2026"]["por_quartil_de_reais_por_voto"] = [
        {"grupo": gr, "municipios": n, "votos_2022": int(a), "votos_2026": int(b_), "variacao": round(b_ / a - 1, 3),
         "reais_por_voto_2022": round(e / a) if a else 0} for gr, n, a, b_, e in quartis]
    return r


# ---------------------------------------------------------------- publicação

def publicar() -> None:
    comando = ["b2"] if shutil.which("b2") else ["uvx", "--from", "b2", "b2"]
    for sub in ("insumos", ""):
        origem = SAIDA / sub if sub else SAIDA
        destino = f"b2://{BUCKET}/{PREFIXO}" + (f"/{sub}" if sub else "")
        args = ["sync", "--compare-versions", "size", "--exclude-regex", r"(\.part|\.DS_Store)$"]
        if not sub:
            args += ["--exclude-dir-regex", "insumos"]
        subprocess.run(comando + args + [str(origem), destino], check=True)
    print(f"publicado em {ESPELHO}/{PREFIXO}/")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--do-espelho", action="store_true", help="usa os insumos já reduzidos do espelho, sem baixar as fontes")
    ap.add_argument("--publicar", action="store_true", help="só envia data/analises/emendas-votos ao espelho")
    a = ap.parse_args()
    if a.publicar:
        return publicar()
    SAIDA.mkdir(parents=True, exist_ok=True)
    if a.do_espelho:
        insumos_do_espelho()
    else:
        if not PAGAMENTOS.exists():
            sys.exit(f"falta {PAGAMENTOS.relative_to(c.RAIZ)}: rode `uv run explorador-emendas` ou use --do-espelho")
        montar_insumos()
    con = montar_painel()
    r = estimar(con)
    (SAIDA / "resultados.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"\nsaída em {SAIDA.relative_to(c.RAIZ)}/")


if __name__ == "__main__":
    main()
