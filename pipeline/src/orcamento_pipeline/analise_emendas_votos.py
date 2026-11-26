"""Análise: as emendas seguem os votos? Emendas individuais e Pix pagas de 2023 a 2026 × votos de cada
deputado federal em cada município (2022) × população, e a variação dos votos em 2026.

    uv run analise-emendas-votos                # baixa o que faltar das fontes e roda tudo
    uv run analise-emendas-votos --do-espelho   # pega os insumos já reduzidos no espelho e só roda a análise
    uv run analise-emendas-votos --publicar     # envia insumos e resultados ao espelho (precisa da chave do B2)

O texto da análise, com método e limites, está em analises/emendas-votos/README.md.

Fontes (cache em data/raw):
- Emendas pagas: data/publico/emendas-pagamentos.parquet (`uv run explorador-emendas`), do qual sai o recorte
  insumos/emendas-portal.parquet.
- Saúde de 2019–24: o Portal da Transparência registra boa parte dessas emendas como pagas ao Banco do
  Brasil, em Brasília, sem a cidade. O Fundo Nacional de Saúde publica cada proposta, com o fundo de saúde de
  destino, o município e o parlamentar: uma planilha por UF e ano (consultafns.saude.gov.br, API pública
  recursos/proposta/planilha). Cada planilha leva minutos; baixam três por vez.
- Votos: TSE, votação por candidato e município (cdn.tse.jus.br, uns 1,4 GB os três): deputado federal em 2018,
  2022 e 2026; deputado estadual em 2022 e 2026 (para as dobradinhas).
- Prefeitos: TSE, candidatos de 2024 (consulta_cand): partido, coligação e resultado de quem disputou a prefeitura.
- População: IBGE, Censo 2022 (tabela 4709).
- Deputados: Câmara, dados abertos, legislatura 57 (o mesmo cache do mapa das emendas).

Saída em data/analises/emendas-votos/:
- insumos/  emendas-portal.parquet (o recorte do Portal), fns-propostas.parquet, votos-deputado-federal.parquet,
            votos-deputado-estadual.parquet, prefeitos-2024.csv, populacao-2022.csv, deputados.csv: o que vai ao
            espelho, para refazer sem baixar as fontes
No espelho, tudo fica em analises/emendas-votos/<versão>/, a versão vinda do conteúdo dos insumos; o
repositório aponta a versão que o texto cita em analises/emendas-votos/espelho.json (gravado por --publicar).
- painel.parquet         deputado × município do estado dele: emenda (2023–26 e 2019–22), votos de 2018, 2022 e 2026,
                         população, prefeito eleito em 2024 e votos dos parceiros estaduais
- resultados.json        os números da análise (os que o texto cita)
- preco-por-deputado.csv R$ de emenda por voto de cada deputado
- dobradinhas.csv        os pares deputado federal × deputado estadual que a análise trata como parceiros
"""

from __future__ import annotations

import argparse
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
PONTEIRO = c.RAIZ / "analises" / "emendas-votos" / "espelho.json"   # a versão dos dados que o texto cita
ARQUIVOS_INSUMOS = ("emendas-portal.parquet", "fns-propostas.parquet", "votos-deputado-federal.parquet",
                    "votos-deputado-estadual.parquet", "prefeitos-2024.csv", "populacao-2022.csv", "deputados.csv")
ARQUIVOS_RESULTADOS = ("painel.parquet", "resultados.json", "preco-por-deputado.csv", "dobradinhas.csv")

ANOS_EMENDA = (2023, 2026)
ANOS_ANTES = (2019, 2022)        # o mandato anterior: a emenda que veio antes da eleição de 2022
ANOS_FNS = (2019, 2020, 2021, 2022, 2023, 2024)   # a partir de 2025 o Portal já registra o fundo municipal
BB = "00000000000191"            # Banco do Brasil: o favorecido sem cidade
DF = "5300108"                   # Brasília: o pagamento vai a entidades com sede lá
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
TSE_CANDIDATOS = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ano}.zip"
FNS = "https://consultafns.saude.gov.br/recursos/proposta/planilha"
IBGE = "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93?localidades=N6[all]"
# Reserva para os poucos municípios cujo nome no TSE difere do IBGE (repositório público sem licença:
# só consultado, nunca copiado para cá).
TSE_IBGE_RESERVA = "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv"
# Títulos e partículas ignorados ao casar o nome do deputado com o nome de urna.
# O partido do deputado é o de 2022. Fusões até 2024 e federações, para comparar com o do prefeito de 2024.
FUSOES = {"PTB": "PRD", "PATRIOTA": "PRD", "PSC": "PODE", "PROS": "SOLIDARIEDADE", "PMN": "MOBILIZA"}
FEDERACOES = {"PT": "PT+PCdoB+PV", "PC do B": "PT+PCdoB+PV", "PV": "PT+PCdoB+PV", "PSDB": "PSDB+CIDADANIA",
              "CIDADANIA": "PSDB+CIDADANIA", "PSOL": "PSOL+REDE", "REDE": "PSOL+REDE"}
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


def deputados() -> list[tuple[str, str, str, bool]]:
    """(nome, uf, partido, veterano) dos deputados da legislatura 57; veterano = esteve na 56 (2019–23).
    Do mesmo cache que o mapa das emendas usa."""
    from .emendas_mapa import baixar_json

    def legislatura(leg: int) -> list[dict]:
        pag, url, saida = 1, f"https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={leg}&itens=100", []
        while url:
            doc = baixar_json(url, f"camara-{leg}-{pag}.json")
            saida += doc["dados"]
            url = next((l["href"] for l in doc["links"] if l["rel"] == "next"), None)
            pag += 1
        return saida

    l56 = {(chave(d["nome"]), d["siglaUf"]) for d in legislatura(56)}
    saida = {(d["nome"], d["siglaUf"]): d.get("siglaPartido") or "" for d in legislatura(57)}
    return [(n, uf, p, (chave(n), uf) in l56) for (n, uf), p in sorted(saida.items())]


def csvs_do_tse(zip_: Path, pasta: Path) -> Path:
    """Extrai os CSVs por UF (não o do Brasil inteiro) de um zip do TSE para uma pasta temporária."""
    pasta.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_) as z:
        for nome in z.namelist():
            if re.search(r"_[A-Z]{2}\.csv$", nome) and not nome.endswith("_BR.csv") and not (pasta / nome).exists():
                z.extract(nome, pasta)
    return pasta


def casar_municipios(con: duckdb.DuckDBPyConnection, rotulo: str, ibge_por_nome: dict[tuple[str, str], str]) -> None:
    """Município do TSE → IBGE pelo nome; a reserva só para o que não casar. Lê a tabela temporária `tse`
    (uf, cd, mun) e grava `tse_ibge` (uf, cd, ibge)."""
    nomes = {(uf, cd): chave(mun) for uf, cd, mun in con.sql("SELECT DISTINCT uf, cd, mun FROM tse").fetchall()}
    faltam = {k for k, kmun in nomes.items() if (k[0], kmun) not in ibge_por_nome}
    reserva: dict[tuple[str, int], str] = {}
    if faltam:
        txt = baixar(TSE_IBGE_RESERVA, RAW / "tse" / "municipios_brasileiros_tse.csv").read_text(encoding="utf-8")
        for linha in txt.splitlines()[1:]:
            cod_tse, uf, _, _, ibge = linha.split(",")
            reserva[(uf, int(cod_tse))] = ibge
        print(f"  TSE {rotulo}: {len(faltam)} municípios com nome diferente do IBGE, casados pela tabela de reserva: "
              f"{sorted(nomes[k] + '/' + k[0] for k in faltam)}", flush=True)
    pares = [(uf, cd, ibge_por_nome.get((uf, k)) or reserva.get((uf, cd))) for (uf, cd), k in nomes.items()]
    # A grafia do TSE passa a valer também para as outras fontes (o FNS usa a mesma grafia antiga).
    for (uf, cd, ibge), k in zip(pares, nomes.values()):
        if ibge:
            ibge_por_nome.setdefault((uf, k), ibge)
    con.sql("CREATE OR REPLACE TEMP TABLE tse_ibge(uf VARCHAR, cd INT, ibge VARCHAR)")
    con.executemany("INSERT INTO tse_ibge VALUES (?, ?, ?)", pares)


def votos_tse(con: duckdb.DuckDBPyConnection, ano: int, ibge_por_nome: dict[tuple[str, str], str], estaduais: bool) -> None:
    """Votos válidos de cada candidato a deputado federal, por município (somadas as zonas), na tabela votos;
    com `estaduais`, também os de deputado estadual, na tabela votos_est."""
    zip_ = baixar(TSE.format(ano=ano), RAW / "tse" / f"votacao_candidato_munzona_{ano}.zip", timeout=3600)
    pasta = csvs_do_tse(zip_, RAW / "tse" / f"_csv_{ano}")
    cargos = "'6', '7'" if estaduais else "'6'"   # 6 = deputado federal, 7 = deputado estadual
    con.sql(f"""CREATE OR REPLACE TEMP TABLE tse AS
                SELECT CD_CARGO::INT cargo, SG_UF uf, CD_MUNICIPIO::INT cd, NM_MUNICIPIO mun, SQ_CANDIDATO sq, NM_CANDIDATO nome,
                       NM_URNA_CANDIDATO urna, SG_PARTIDO partido, DS_SIT_TOT_TURNO situacao, sum(QT_VOTOS_NOMINAIS_VALIDOS::BIGINT) votos
                FROM read_csv('{pasta}/*.csv', delim=';', encoding='latin-1', header=true, all_varchar=true)
                WHERE CD_CARGO IN ({cargos}) GROUP BY ALL""")
    shutil.rmtree(pasta)
    casar_municipios(con, str(ano), ibge_por_nome)
    for cargo, tabela in ((6, "votos"), (7, "votos_est")):
        con.sql(f"""INSERT INTO {tabela} SELECT {ano}, t.uf, m.ibge, sq, nome, urna, partido, situacao, votos
                    FROM tse t LEFT JOIN tse_ibge m USING (uf, cd) WHERE cargo = {cargo}""")


def prefeitos_2024(con: duckdb.DuckDBPyConnection, ibge_por_nome: dict[tuple[str, str], str]) -> None:
    """Quem disputou a prefeitura em 2024: partido, coligação e resultado, na tabela prefeitos. Do arquivo de
    candidatos do TSE saem só essas colunas; CPF, título e e-mail não são lidos."""
    zip_ = baixar(TSE_CANDIDATOS.format(ano=2024), RAW / "tse" / "consulta_cand_2024.zip", timeout=3600)
    pasta = csvs_do_tse(zip_, RAW / "tse" / "_csv_cand_2024")
    con.sql(f"""CREATE OR REPLACE TEMP TABLE tse AS
                SELECT SG_UF uf, SG_UE::INT cd, NM_UE mun, NR_TURNO::INT turno, SG_PARTIDO partido,
                       DS_COMPOSICAO_COLIGACAO coligacao, DS_SIT_TOT_TURNO resultado
                FROM read_csv('{pasta}/*.csv', delim=';', encoding='latin-1', header=true, all_varchar=true)
                WHERE CD_CARGO = '11' AND CD_TIPO_ELEICAO = '2'""")   # prefeito, eleição ordinária
    shutil.rmtree(pasta)
    casar_municipios(con, "2024 (prefeitos)", ibge_por_nome)
    con.sql("""CREATE TABLE prefeitos AS SELECT t.uf, m.ibge, turno, partido, coligacao, resultado
               FROM tse t JOIN tse_ibge m USING (uf, cd) WHERE m.ibge IS NOT NULL""")


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

    con.sql("CREATE TABLE dep(nome VARCHAR, uf VARCHAR, partido VARCHAR, veterano BOOLEAN)")
    con.executemany("INSERT INTO dep VALUES (?, ?, ?, ?)", deputados())
    con.sql(f"COPY dep TO '{INSUMOS / 'deputados.csv'}' (HEADER)")

    for tabela in ("votos", "votos_est"):
        con.sql(f"""CREATE TABLE {tabela}(ano INT, uf VARCHAR, ibge VARCHAR, sq VARCHAR, nome VARCHAR, urna VARCHAR,
                                         partido VARCHAR, situacao VARCHAR, votos BIGINT)""")
    for ano in (2018, 2022, 2026):
        print(f"TSE {ano}", flush=True)
        votos_tse(con, ano, por_nome, estaduais=ano != 2018)
    sem = con.sql("SELECT count(*) FROM votos WHERE ibge IS NULL").fetchall()[0][0]
    print(f"  votos sem município IBGE: {sem} linhas", flush=True)
    # ORDER BY ALL em tudo o que vai para os insumos: sem empates na ordem, os arquivos saem iguais byte a byte
    # a cada rodada, e a versão (o hash deles) só muda quando os dados mudam.
    con.sql(f"COPY (SELECT ano, uf, sq, ibge, nome, urna, partido, situacao, votos FROM votos ORDER BY ALL) TO '{INSUMOS / 'votos-deputado-federal.parquet'}'")
    con.sql(f"""COPY (SELECT ano, uf, sq, ibge, nome, urna, partido, situacao, votos FROM votos_est WHERE ibge IS NOT NULL ORDER BY ALL)
                TO '{INSUMOS / 'votos-deputado-estadual.parquet'}'""")
    print("TSE 2024 (prefeitos)", flush=True)
    prefeitos_2024(con, por_nome)
    con.sql(f"COPY (SELECT * FROM prefeitos ORDER BY ALL) TO '{INSUMOS / 'prefeitos-2024.csv'}' (HEADER)")

    con.sql("""CREATE TABLE fns(proposta VARCHAR, ano INT, uf VARCHAR, ibge VARCHAR, municipio VARCHAR, entidade VARCHAR,
                                tipo VARCHAR, parlamentar VARCHAR, partido VARCHAR, pago DOUBLE)""")
    con.executemany("INSERT INTO fns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", propostas_fns(por_nome))
    print(con.sql("SELECT ano, count(*) linhas, round(sum(pago) / 1e9, 2) bi_pagos, count(*) FILTER (ibge IS NULL) sem_ibge FROM fns GROUP BY 1 ORDER BY 1"))
    con.sql(f"COPY (SELECT ano, uf, proposta, ibge, municipio, entidade, tipo, parlamentar, partido, pago FROM fns ORDER BY ALL) TO '{INSUMOS / 'fns-propostas.parquet'}'")

    # O recorte do Portal que a análise usa, congelado junto dos outros insumos (o parquet geral do explorador
    # é refeito a cada publicação).
    a0, a1 = ANOS_ANTES[0], ANOS_EMENDA[1]
    con.sql(f"""COPY (SELECT emenda, ano, mes, autor, tipo, favorecido, codigo, grupo, uf, municipio, ibge, area, valor
                      FROM '{PAGAMENTOS}' WHERE tipo IN ('Individual', 'Pix') AND ano BETWEEN {a0} AND {a1}
                      ORDER BY ALL) TO '{INSUMOS / 'emendas-portal.parquet'}'""")


def versao_insumos() -> str:
    """Versão = conteúdo dos insumos: dados novos vão para outra pasta no espelho, e o cache nunca mistura."""
    from .fichas_emendas import versao
    return versao(*(INSUMOS / n for n in ARQUIVOS_INSUMOS))


def insumos_do_espelho() -> None:
    """Baixa os insumos da versão que o repositório aponta (analises/emendas-votos/espelho.json)."""
    v = json.loads(PONTEIRO.read_text(encoding="utf-8"))["versao"]
    for nome in ARQUIVOS_INSUMOS:
        print(f"espelho {v}: {nome}", flush=True)
        if (INSUMOS / nome).exists():
            (INSUMOS / nome).unlink()
        baixar(f"{ESPELHO}/{PREFIXO}/{v}/insumos/{nome}", INSUMOS / nome)
    if versao_insumos() != v:
        sys.exit(f"os insumos baixados não batem com a versão {v} do espelho.json")


# ---------------------------------------------------------------- painel

def casar_deputados(con: duckdb.DuckDBPyConnection) -> None:
    """Cada deputado do cadastro ↔ um candidato do TSE de 2022 no mesmo estado (nome de urna ou civil)."""
    cand: dict[str, list] = {}
    for uf, sq, urna, nome, sit, v in con.sql("SELECT uf, sq, urna, nome, situacao, sum(votos) FROM votos WHERE ano = 2022 GROUP BY ALL").fetchall():
        cand.setdefault(uf, []).append((sq, chave(urna), chave(nome), sit, v))
    pares, sem_par = [], []
    for nome, uf, veterano in con.sql("SELECT nome, uf, veterano FROM dep").fetchall():
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
            pares.append((k, uf, melhor[3], bool(veterano)))
        else:
            sem_par.append(f"{nome} ({uf})")
    con.sql("CREATE OR REPLACE TABLE casados(k VARCHAR, uf VARCHAR, sq VARCHAR, veterano BOOLEAN)")
    con.executemany("INSERT INTO casados VALUES (?, ?, ?, ?)", pares)
    print(f"deputados casados com o TSE: {len(pares)}; sem par: {len(sem_par)} {sem_par}", flush=True)


def bloco(partido: str) -> str:
    """Partido de 2022 ou de 2024 → o partido (ou a federação) em que ele estava em 2024."""
    p = FUSOES.get(partido, partido)
    return FEDERACOES.get(p, p)


def blocos_da_coligacao(coligacao: str) -> set[str]:
    """'PP / MDB / Federação PSDB CIDADANIA (45-PSDB / 23-CIDADANIA)' → os partidos, já como blocos."""
    pedacos = [re.sub(r"^\d+-", "", x.strip()) for x in re.split(r"/|\(|\)", str(coligacao))]
    return {bloco(x) for x in pedacos if x and not x.startswith("Federa") and x != "#NULO"}


def marcar_prefeitos(con: duckdb.DuckDBPyConnection) -> None:
    """Tabelas por município: o bloco do prefeito eleito em 2024, os blocos da coligação dele e os que disputaram."""
    eleitos, coligados, disputaram = {}, set(), set()
    for ibge, turno, partido, coligacao, resultado in con.sql(
            "SELECT ibge, turno, partido, coligacao, resultado FROM prefeitos ORDER BY ibge, turno").fetchall():
        if turno == 1:
            disputaram.add((ibge, bloco(partido)))
        if resultado == "ELEITO":   # o do 2º turno, quando houve, vem depois e fica
            eleitos[ibge] = (bloco(partido), blocos_da_coligacao(coligacao))
    for ibge, (b, col) in eleitos.items():
        coligados |= {(ibge, x) for x in col if x != b}
    con.sql("CREATE TABLE pref_eleito(ibge VARCHAR, bloco VARCHAR); CREATE TABLE pref_colig(ibge VARCHAR, bloco VARCHAR); "
            "CREATE TABLE pref_disputou(ibge VARCHAR, bloco VARCHAR)")
    con.executemany("INSERT INTO pref_eleito VALUES (?, ?)", [(i, b) for i, (b, _) in eleitos.items()])
    con.executemany("INSERT INTO pref_colig VALUES (?, ?)", sorted(coligados))
    con.executemany("INSERT INTO pref_disputou VALUES (?, ?)", sorted(disputaram))
    con.sql("CREATE TABLE dep_bloco(sq VARCHAR, bloco VARCHAR)")
    con.executemany("INSERT INTO dep_bloco VALUES (?, ?)", [(sq, bloco(p)) for sq, p in con.sql(
        "SELECT sq, any_value(partido) FROM votos WHERE ano = 2022 AND sq IN (SELECT sq FROM casados) GROUP BY sq").fetchall()])


def achar_dobradinhas(con: duckdb.DuckDBPyConnection) -> None:
    """Parceiro de um deputado federal = candidato a estadual em 2022, com 3 mil votos ou mais, cuja fatia dos votos de
    cada cidade tem correlação de 0,6 ou mais com a do federal, e de 0,5 ou mais mesmo sem as três cidades que mais
    pesam (para não pegar quem só é da mesma cidade). Grava a tabela dobradinhas e o arquivo dobradinhas.csv.
    sq_est26 é a candidatura do mesmo parceiro a estadual em 2026 (mesmo nome civil, mesmo estado, par único)."""
    pares = []
    fed = con.sql("SELECT uf, sq, ibge, votos::DOUBLE votos, validos::DOUBLE validos FROM painel ORDER BY uf, sq, ibge").fetchnumpy()
    est = con.sql("""SELECT uf, sq, ibge, votos::DOUBLE votos FROM votos_est WHERE ano = 2022 AND uf <> 'DF' AND sq IN
                     (SELECT sq FROM votos_est WHERE ano = 2022 GROUP BY sq HAVING sum(votos) >= 3000)""").fetchnumpy()
    tot = con.sql("SELECT ibge, sum(votos)::DOUBLE v FROM votos_est WHERE ano = 2022 GROUP BY 1").fetchnumpy()
    total_est = dict(zip(tot["ibge"], tot["v"]))
    for uf in sorted(set(fed["uf"])):
        f = fed["uf"] == uf
        muns, im = np.unique(fed["ibge"][f], return_inverse=True)
        deps, idp = np.unique(fed["sq"][f], return_inverse=True)
        F = np.zeros((len(muns), len(deps)))
        F[im, idp] = np.where(fed["validos"][f] > 0, fed["votos"][f] / np.maximum(fed["validos"][f], 1), 0)
        e = (est["uf"] == uf) & np.isin(est["ibge"], muns)
        cands, ic = np.unique(est["sq"][e], return_inverse=True)
        S = np.zeros((len(muns), len(cands)))
        S[np.searchsorted(muns, est["ibge"][e]), ic] = est["votos"][e]
        S /= np.maximum(np.array([total_est.get(m, 0) for m in muns], float), 1)[:, None]
        zf, zs = (F - F.mean(0)) / np.maximum(F.std(0), 1e-12), (S - S.mean(0)) / np.maximum(S.std(0), 1e-12)
        corr = zf.T @ zs / len(muns)
        for i, j in zip(*np.where(corr >= 0.6)):
            x, y = F[:, i], S[:, j]
            resto = np.argsort(-(x - x.mean()) * (y - y.mean()))[3:]
            if len(resto) > 2 and x[resto].std() > 0 and y[resto].std() > 0:
                sem3 = float(np.corrcoef(x[resto], y[resto])[0, 1])
                if sem3 >= 0.5:
                    pares.append((uf, str(deps[i]), str(cands[j]), round(float(corr[i, j]), 2), round(sem3, 2)))
    con.sql("CREATE TABLE pares_dob(uf VARCHAR, sq VARCHAR, sq_est VARCHAR, correlacao DOUBLE, correlacao_sem_3_cidades DOUBLE)")
    con.executemany("INSERT INTO pares_dob VALUES (?, ?, ?, ?, ?)", pares)
    con.sql("""CREATE TABLE dobradinhas AS
        WITH e22 AS (SELECT sq, any_value(uf) uf, any_value(nome) nome, any_value(urna) urna, any_value(partido) partido
                     FROM votos_est WHERE ano = 2022 AND sq IN (SELECT sq_est FROM pares_dob) GROUP BY sq),
        e26 AS (SELECT uf, chave(nome) kn, any_value(sq) sq FROM (SELECT DISTINCT uf, nome, sq FROM votos_est WHERE ano = 2026)
                GROUP BY ALL HAVING count(*) = 1),
        f22 AS (SELECT sq, any_value(urna) urna, any_value(partido) partido FROM votos WHERE ano = 2022 GROUP BY sq)
        SELECT p.uf, p.sq, f22.urna deputado, f22.partido, p.sq_est, e22.urna estadual, e22.partido partido_estadual,
               p.correlacao, p.correlacao_sem_3_cidades, e26.sq sq_est26
        FROM pares_dob p JOIN e22 ON e22.sq = p.sq_est JOIN f22 ON f22.sq = p.sq
        LEFT JOIN e26 ON e26.uf = e22.uf AND e26.kn = chave(e22.nome)""")
    con.sql(f"COPY (SELECT * FROM dobradinhas ORDER BY correlacao DESC, uf, deputado, estadual) TO '{SAIDA / 'dobradinhas.csv'}' (HEADER)")
    n, nd = con.sql("SELECT count(*), count(DISTINCT sq) FROM dobradinhas").fetchall()[0]
    print(f"dobradinhas: {n} pares, {nd} deputados com parceiro", flush=True)


def montar_painel() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.create_function("chave", chave, ["VARCHAR"], "VARCHAR")
    con.sql(f"CREATE TABLE votos AS SELECT * FROM '{INSUMOS / 'votos-deputado-federal.parquet'}'")
    con.sql(f"CREATE TABLE votos_est AS SELECT * FROM '{INSUMOS / 'votos-deputado-estadual.parquet'}'")
    con.sql(f"CREATE TABLE prefeitos AS SELECT * FROM read_csv('{INSUMOS / 'prefeitos-2024.csv'}', types={{'ibge': 'VARCHAR'}})")
    con.sql(f"CREATE TABLE fns AS SELECT * FROM '{INSUMOS / 'fns-propostas.parquet'}'")
    con.sql(f"CREATE TABLE pop AS SELECT * FROM read_csv('{INSUMOS / 'populacao-2022.csv'}', types={{'ibge': 'VARCHAR'}})")
    con.sql(f"CREATE TABLE dep AS SELECT * FROM read_csv('{INSUMOS / 'deputados.csv'}')")
    casar_deputados(con)
    marcar_prefeitos(con)
    a0, a1 = ANOS_EMENDA
    b0, b1 = ANOS_ANTES
    fns_anos = ", ".join(map(str, ANOS_FNS))
    # Portal, menos o que o FNS cobre melhor (toda a saúde individual até 2024, e o que foi ao BB);
    # mais o FNS. Brasília fica fora: lá o pagamento vai a entidades com sede na capital.
    # `estadual`: pago a governo ou fundo estadual. Aparece no município da sede (a capital), mas pode ser
    # gasto em qualquer cidade do estado. No FNS, pelo nome da entidade.
    con.sql(f"""CREATE TABLE emendas AS
        WITH portal AS (
            SELECT chave(autor) k, ibge, ano, valor, CASE WHEN tipo = 'Pix' THEN valor ELSE 0 END pix, 0.0 fns,
                   CASE WHEN grupo = 'Governo estadual' THEN valor ELSE 0 END est
            FROM '{INSUMOS / "emendas-portal.parquet"}'
            WHERE tipo IN ('Individual', 'Pix') AND ano BETWEEN {b0} AND {a1}
              AND NOT (coalesce(codigo, '') = '{BB}' OR (tipo = 'Individual' AND area = 'Saúde' AND ano IN ({fns_anos})))
              AND coalesce(ibge, '') NOT IN ('', '{DF}')),
        saude AS (SELECT chave(parlamentar) k, ibge, ano, pago valor, 0.0 pix, pago fns,
                         CASE WHEN entidade NOT ILIKE '%MUNIC%' AND (entidade ILIKE '%ESTAD%' OR entidade ILIKE 'FUNDO ESPECIAL DE SAUDE%')
                              THEN pago ELSE 0 END est
                  FROM fns WHERE ano IN ({fns_anos}) AND ibge IS NOT NULL AND ibge <> '{DF}' AND pago > 0)
        SELECT k, ibge, ano, sum(valor) valor, sum(pix) pix, sum(fns) fns, sum(est) est
        FROM (SELECT * FROM portal UNION ALL SELECT * FROM saude) GROUP BY ALL""")
    # A candidatura do mesmo deputado em 2018 e em 2026: mesmo nome civil, mesmo estado, par único.
    for ano in (2018, 2026):
        con.sql(f"""CREATE TABLE ponte{ano} AS
            SELECT a.sq, b.sq sq_outro
            FROM (SELECT sq, uf, chave(nome) kn FROM (SELECT DISTINCT sq, uf, nome FROM votos WHERE ano = 2022 AND sq IN (SELECT sq FROM casados))) a
            JOIN (SELECT sq, uf, chave(nome) kn FROM (SELECT DISTINCT sq, uf, nome FROM votos WHERE ano = {ano})) b USING (uf, kn)
            QUALIFY count(*) OVER (PARTITION BY a.sq) = 1 AND count(*) OVER (PARTITION BY b.sq) = 1""")
    anos, antes = range(a0, a1 + 1), range(b0, b1 + 1)
    por_ano = ", ".join(f"sum(e.valor) FILTER (e.ano = {a}) e{a}" for a in list(antes) + list(anos))
    con.sql(f"""CREATE TABLE painel AS
        WITH d AS (SELECT sq, any_value(uf) uf, bool_or(veterano) veterano FROM casados GROUP BY sq),
        em AS (SELECT c.sq, e.ibge, sum(e.valor) FILTER (e.ano >= {a0}) emenda, sum(e.pix) FILTER (e.ano >= {a0}) pix,
                      sum(e.fns) FILTER (e.ano >= {a0}) fns, sum(e.est) FILTER (e.ano >= {a0}) est,
                      sum(e.valor) FILTER (e.ano <= {b1}) emenda_antes, {por_ano}
               FROM emendas e JOIN casados c USING (k) GROUP BY ALL),
        v22 AS (SELECT sq, ibge, sum(votos) votos FROM votos WHERE ano = 2022 GROUP BY ALL),
        val AS (SELECT ibge, sum(votos) validos FROM votos WHERE ano = 2022 GROUP BY 1),
        v18 AS (SELECT p.sq, v.ibge, sum(v.votos) votos18 FROM votos v JOIN ponte2018 p ON p.sq_outro = v.sq WHERE v.ano = 2018 GROUP BY ALL),
        v26 AS (SELECT p.sq, v.ibge, sum(v.votos) votos26 FROM votos v JOIN ponte2026 p ON p.sq_outro = v.sq WHERE v.ano = 2026 GROUP BY ALL)
        SELECT d.sq, d.uf, d.veterano, p.ibge, p.populacao, coalesce(val.validos, 0) validos, coalesce(v22.votos, 0) votos,
               CASE WHEN d.sq IN (SELECT sq FROM ponte2018) THEN coalesce(v18.votos18, 0) END votos18,
               CASE WHEN d.sq IN (SELECT sq FROM ponte2026) THEN coalesce(v26.votos26, 0) END votos26,
               coalesce(em.emenda, 0) emenda, coalesce(em.pix, 0) pix, coalesce(em.fns, 0) fns, coalesce(em.est, 0) est,
               {", ".join(f"coalesce(em.e{a}, 0) e{a}" for a in anos)},
               coalesce(em.emenda_antes, 0) emenda_antes, {", ".join(f"coalesce(em.e{a}, 0) e{a}" for a in antes)},
               -- prefeito eleito em 2024 (NULL onde o TSE não traz eleito na eleição ordinária)
               CASE WHEN pe.ibge IS NOT NULL THEN (pe.bloco = b.bloco)::INT END prefeito_do_partido,
               CASE WHEN pe.ibge IS NOT NULL THEN (pc.ibge IS NOT NULL)::INT END partido_na_coligacao,
               CASE WHEN pe.ibge IS NOT NULL THEN (pd.ibge IS NOT NULL AND pe.bloco <> b.bloco)::INT END partido_disputou_e_perdeu
        FROM d JOIN pop p ON p.uf = d.uf LEFT JOIN dep_bloco b ON b.sq = d.sq
        LEFT JOIN v22 ON v22.sq = d.sq AND v22.ibge = p.ibge LEFT JOIN val ON val.ibge = p.ibge
        LEFT JOIN em ON em.sq = d.sq AND em.ibge = p.ibge
        LEFT JOIN v18 ON v18.sq = d.sq AND v18.ibge = p.ibge LEFT JOIN v26 ON v26.sq = d.sq AND v26.ibge = p.ibge
        LEFT JOIN pref_eleito pe ON pe.ibge = p.ibge
        LEFT JOIN pref_colig pc ON pc.ibge = p.ibge AND pc.bloco = b.bloco
        LEFT JOIN pref_disputou pd ON pd.ibge = p.ibge AND pd.bloco = b.bloco
        WHERE d.uf <> 'DF'""")
    # Só deputados com emenda e voto no estado; concorreu em 2026 = teve algum voto em 2026.
    con.sql("""CREATE OR REPLACE TABLE painel AS SELECT *,
                 sum(emenda) OVER w em_tot, sum(votos) OVER w vot_tot, sum(populacao) OVER w pop_tot,
                 sum(votos26) OVER w v26_tot FROM painel WINDOW w AS (PARTITION BY sq)""")
    con.sql("DELETE FROM painel WHERE em_tot = 0 OR vot_tot = 0")
    # Dobradinhas: os votos dos parceiros estaduais em cada cidade. `parceiros22` soma todos os parceiros;
    # `parceiros22_ambos` e `parceiros26` só os que concorreram de novo a estadual em 2026 (NULL se nenhum concorreu).
    achar_dobradinhas(con)
    con.sql("""CREATE OR REPLACE TABLE painel AS
        WITH tem AS (SELECT sq, count(sq_est26) n26 FROM dobradinhas GROUP BY sq),
        v AS (SELECT d.sq, e.ibge, sum(e.votos) parceiros22, sum(e.votos) FILTER (d.sq_est26 IS NOT NULL) ambos
              FROM dobradinhas d JOIN votos_est e ON e.sq = d.sq_est AND e.ano = 2022 GROUP BY ALL),
        w AS (SELECT d.sq, e.ibge, sum(e.votos) parceiros26 FROM dobradinhas d JOIN votos_est e ON e.sq = d.sq_est26 AND e.ano = 2026 GROUP BY ALL),
        t AS (SELECT ibge, sum(votos) estaduais22 FROM votos_est WHERE ano = 2022 GROUP BY 1)
        SELECT p.*, coalesce(t.estaduais22, 0) estaduais22,
               CASE WHEN tem.sq IS NOT NULL THEN coalesce(v.parceiros22, 0) END parceiros22,
               CASE WHEN tem.n26 > 0 THEN coalesce(v.ambos, 0) END parceiros22_ambos,
               CASE WHEN tem.n26 > 0 THEN coalesce(w.parceiros26, 0) END parceiros26
        FROM painel p LEFT JOIN tem USING (sq) LEFT JOIN v ON v.sq = p.sq AND v.ibge = p.ibge
        LEFT JOIN w ON w.sq = p.sq AND w.ibge = p.ibge LEFT JOIN t ON t.ibge = p.ibge""")
    con.sql(f"COPY (SELECT * EXCLUDE (em_tot, vot_tot, pop_tot, v26_tot) FROM painel ORDER BY sq, ibge) TO '{SAIDA / 'painel.parquet'}'")
    return con


# ---------------------------------------------------------------- estimativas

def ppml(y: np.ndarray, X: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Poisson com efeito fixo de grupo (verossimilhança concentrada, com busca de passo); erros agrupados por grupo."""
    X = X - X.mean(0)
    G = g.max() + 1
    Y = np.bincount(g, y, G)

    def partes(b):
        eta = X @ b
        m = np.full(G, -np.inf)
        np.maximum.at(m, g, eta)
        e = np.exp(eta - m[g])
        S = np.bincount(g, e, G)
        return e / S[g], np.sum(y * (eta - m[g] - np.log(S[g])))

    b = np.zeros(X.shape[1])
    p, ll = partes(b)
    for _ in range(300):
        mu = Y[g] * p
        px = np.stack([np.bincount(g, p * X[:, j], G) for j in range(X.shape[1])], 1)
        Xc = X - px[g]
        H = (Xc * mu[:, None]).T @ Xc
        passo = np.linalg.solve(H + 1e-9 * np.eye(len(b)), (X * (y - mu)[:, None]).sum(0))
        t = 1.0
        while True:
            p2, ll2 = partes(b + t * passo)
            if ll2 >= ll - 1e-12 or t < 1e-6:
                break
            t /= 2
        b, p, ll = b + t * passo, p2, ll2
        if np.abs(t * passo).max() < 1e-9:
            break
    mu = Y[g] * p
    px = np.stack([np.bincount(g, p * X[:, j], G) for j in range(X.shape[1])], 1)
    Xc = X - px[g]
    H = (Xc * mu[:, None]).T @ Xc
    s = Xc * (y - mu)[:, None]
    sg = np.stack([np.bincount(g, s[:, j], G) for j in range(X.shape[1])], 1)
    Hi = np.linalg.inv(H)
    return b, np.sqrt(np.diag(Hi @ (sg.T @ sg) @ Hi))


def ppml_dois_efeitos(y: np.ndarray, X: np.ndarray, g1: np.ndarray, g2: np.ndarray,
                      agrupar: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, int]:
    """Poisson com efeito fixo de deputado (g1) e de município (g2), por IRLS com projeções alternadas
    ponderadas (o método do ppmlhdfe). Tira antes os grupos só com zero, que não informam nada.
    Erros agrupados por `agrupar` (por g1, o deputado, se não vier). Devolve também o número de observações usadas."""
    agrupar = g1 if agrupar is None else agrupar
    ok = np.ones(len(y), bool)
    while True:   # grupos só com zero saem; tirar uns pode zerar outros
        antes = ok.sum()
        for g in (g1, g2):
            soma = np.bincount(g[ok], y[ok], g.max() + 1)
            ok &= soma[g] > 0
        if ok.sum() == antes:
            break
    y, X = y[ok], X[ok]
    g1, g2, agrupar = grupos(g1[ok]), grupos(g2[ok]), grupos(agrupar[ok])
    k = X.shape[1]

    def tirar_medias(M: np.ndarray, w: np.ndarray) -> np.ndarray:
        M = M.copy()
        w1, w2 = np.bincount(g1, w), np.bincount(g2, w)
        for _ in range(500):
            M0 = M.copy()
            M -= np.stack([np.bincount(g1, w * M[:, j]) / w1 for j in range(M.shape[1])], 1)[g1]
            M -= np.stack([np.bincount(g2, w * M[:, j]) / w2 for j in range(M.shape[1])], 1)[g2]
            if np.abs(M - M0).max() < 1e-10:
                break
        return M

    mu = (y + y.mean()) / 2
    eta = np.log(mu)
    desvio = np.inf
    for _ in range(100):
        z = eta + (y - mu) / mu
        M = tirar_medias(np.column_stack([z, X]), mu)
        zd, Xd = M[:, 0], M[:, 1:]
        XtWX = (Xd * mu[:, None]).T @ Xd
        b = np.linalg.solve(XtWX, (Xd * mu[:, None]).T @ zd)
        resid = zd - Xd @ b
        eta = z - resid
        mu = np.exp(eta)
        novo = 2 * np.sum(np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))
        if abs(novo - desvio) / max(abs(novo), 1) < 1e-10:
            break
        desvio = novo
    s = Xd * (mu * resid)[:, None]
    sg = np.stack([np.bincount(agrupar, s[:, j]) for j in range(k)], 1)
    Hi = np.linalg.inv(XtWX)
    return b, np.sqrt(np.diag(Hi @ (sg.T @ sg) @ Hi)), int(ok.sum())


def grupos(*cols: np.ndarray) -> np.ndarray:
    return np.unique(np.column_stack(cols) if len(cols) > 1 else cols[0], axis=0, return_inverse=True)[1].ravel()


CAPITAIS = set("1100205 1200401 1302603 1400100 1501402 1600303 1721000 2111300 2211001 2304400 2408102 2507507 2611606 "
               "2704302 2800308 2927408 3106200 3205309 3304557 3550308 4106902 4205407 4314902 5002704 5103403 5208707".split())


def coef(rotulos, b, ep) -> dict:
    return {k: {"coef": round(float(bi), 3), "ep": round(float(ei), 3)} for k, bi, ei in zip(rotulos, b, ep)}


def estimar(con: duckdb.DuckDBPyConnection) -> dict:
    r: dict = {}
    q = lambda sql: con.sql(sql).fetchall()
    [(n_dep, n_pares, bi, bi_fns, bi_est)] = q("SELECT count(DISTINCT sq), count(*), sum(emenda) / 1e9, sum(fns) / 1e9, sum(est) / 1e9 FROM painel")
    r["painel"] = {"deputados": n_dep, "pares": n_pares, "emendas_bi": round(bi, 2), "das_quais_fns_bi": round(bi_fns, 2),
                   "pagas_a_governo_estadual_bi": round(bi_est, 2)}
    # O FNS confere com o Portal? Emendas individuais de saúde, por ano: o que o FNS diz que pagou, o que o Portal
    # registra, e quanto disso o Portal mostra como pago ao Banco do Brasil, sem a cidade.
    r["fns_x_portal_bi"] = {str(ano): {"fns": round(f, 2), "portal_saude": round(p, 2), "portal_pago_ao_banco_do_brasil": round(bb, 2)}
                            for ano, f, p, bb in q(f"""
        SELECT f.ano, f.bi, p.bi, p.bb FROM (SELECT ano, sum(pago) / 1e9 bi FROM fns GROUP BY 1) f
        JOIN (SELECT ano, sum(valor) / 1e9 bi, sum(valor) FILTER (coalesce(codigo, '') = '{BB}') / 1e9 bb
              FROM '{INSUMOS / "emendas-portal.parquet"}' WHERE tipo = 'Individual' AND area = 'Saúde' GROUP BY 1) p USING (ano)
        ORDER BY 1""")}
    a0, a1 = ANOS_EMENDA
    anos = list(range(a0, a1 + 1))
    antes = list(range(ANOS_ANTES[0], ANOS_ANTES[1] + 1))
    cols = (["sq", "ibge", "veterano", "emenda", "est", "votos", "populacao", "validos", "votos26", "v26_tot"] + [f"e{a}" for a in anos]
            + ["votos18", "emenda_antes"] + [f"e{a}" for a in antes]
            + ["prefeito_do_partido", "partido_na_coligacao", "partido_disputou_e_perdeu", "estaduais22", "parceiros22", "parceiros22_ambos", "parceiros26"])
    # as colunas que podem faltar (o deputado não concorreu em 2018, a cidade não tem prefeito no arquivo, o deputado
    # não tem parceiro) ganham uma marca à parte, porque abaixo o que falta vira zero
    marcas = {"tem18": "votos18", "tem_pref": "prefeito_do_partido", "tem_par": "parceiros22", "tem_par26": "parceiros26"}
    sel = cols + [f"({v} IS NOT NULL)::INT {k}" for k, v in marcas.items()]
    d = dict(zip(cols + list(marcas), (np.array(x) for x in zip(*q(f"SELECT {', '.join(sel)} FROM painel ORDER BY sq, ibge")))))
    for k in cols[3:] + list(marcas):
        d[k] = np.array([0 if v is None else v for v in d[k]], float)
    g = grupos(d["sq"])
    votos, pop, validos = d["votos"], d["populacao"], d["validos"]
    lv, z, lp, lval = np.log1p(votos), (votos == 0).astype(float), np.log(pop), np.log1p(validos)
    dom = np.where(validos > 0, votos / np.where(validos > 0, validos, 1), 0)
    ldom = np.where(votos > 0, np.log(np.maximum(dom, 1e-9)), 0)
    vet = d["veterano"].astype(bool)
    cap = np.isin(d["ibge"], list(CAPITAIS))

    def modelo(yv, colunas, rotulos, m=None):
        m = np.ones(len(yv), bool) if m is None else m
        # só deputados que mandaram alguma emenda nesse recorte
        tem = np.bincount(grupos(d["sq"][m]), yv[m]) > 0
        mm = m.copy()
        mm[m] = tem[grupos(d["sq"][m])]
        b, ep = ppml(yv[mm] / 1e6, np.column_stack([c[mm] for c in colunas]), grupos(d["sq"][mm]))
        return coef(rotulos, b, ep) | {"deputados": int(len(np.unique(d["sq"][mm]))), "emendas_bi": round(float(yv[mm].sum() / 1e9), 2)}

    V, RV = [lv, z, lp], ["votos", "zero_voto", "populacao"]
    em = d["emenda"]
    # 1. Para onde vai a emenda: elasticidades (PPML, efeito fixo de deputado)
    r["elasticidades"] = {
        "so_votos": modelo(em, [lv, z], ["votos", "zero_voto"]),
        "so_populacao": modelo(em, [lp], ["populacao"]),
        "votos_e_populacao": modelo(em, V, RV),
        "votos_e_eleitorado": modelo(em, [lv, z, lval], ["votos", "zero_voto", "votos_validos"]),
        # votos = tamanho da cidade × força do deputado nela
        "tamanho_e_forca_local": modelo(em, [lval, ldom, z], ["votos_validos", "fatia_local", "zero_voto"]),
    }
    r["robustez"] = {
        "sem_pagamentos_estaduais": modelo(em - d["est"], V, RV),
        "sem_capitais": modelo(em, V, RV, ~cap),
        "veteranos": modelo(em, V, RV, vet),
        "novatos": modelo(em, V, RV, ~vet),
        "veteranos_por_ano_de_pagamento": {str(a): modelo(d[f"e{a}"], V, RV, vet) for a in anos},
        "novatos_por_ano_de_pagamento": {str(a): modelo(d[f"e{a}"], V, RV, ~vet) for a in anos if d[f"e{a}"][~vet].sum() > 3e8},
    }

    # 2. O "dono do município": emenda por faixa da fatia local, entre cidades do mesmo tamanho (1–3% = 1)
    cortes = [0, .01, .03, .05, .1, .2, .3, .5]
    rot = ["zero voto", "menos de 1%", "1–3%", "3–5%", "5–10%", "10–20%", "20–30%", "30–50%", "mais de 50%"]
    faixa = np.where(votos == 0, 0, 1 + np.searchsorted(cortes[1:], dom, side="left"))
    faixa = np.minimum(faixa, len(rot) - 1)
    dummies = [(faixa == i).astype(float) for i in range(len(rot)) if i != 2]
    b, ep = ppml(em / 1e6, np.column_stack([lval] + dummies), g)
    mult = dict(zip([x for i, x in enumerate(rot) if i != 2], b[1:]))
    r["dono_do_municipio"] = [
        {"fatia_local": x, "multiplicador": 1.0 if i == 2 else round(float(np.exp(mult[x])), 2),
         "chance_receber": round(float((em[faixa == i] > 0).mean()), 3), "pares": int((faixa == i).sum()),
         "emendas_bi": round(float(em[faixa == i].sum() / 1e9), 2)} for i, x in enumerate(rot)]

    # 3. Distância das proporções e espalhamento
    con.sql("""CREATE OR REPLACE TABLE p2 AS SELECT *, emenda / em_tot s_em, votos / vot_tot s_vot, populacao / pop_tot s_pop,
                 row_number() OVER (PARTITION BY sq ORDER BY votos DESC, ibge) posicao FROM painel""")
    r["proporcionalidade"] = dict(zip(("emenda_mudaria_de_cidade_para_seguir_votos", "para_seguir_populacao"), map(lambda x: round(x, 3), q(
        """SELECT median(dv), median(dp) FROM (SELECT sq, sum(abs(s_em - s_vot)) / 2 dv, sum(abs(s_em - s_pop)) / 2 dp FROM p2 GROUP BY sq)""")[0])))
    [(rec, tot, fat)] = q("SELECT median(n), median(t), median(n / t) FROM (SELECT sq, count(*) FILTER (emenda > 0) n, count(*) t FROM p2 GROUP BY sq)")
    r["espalhamento"] = {"municipios_que_recebem_mediana": rec, "municipios_do_estado_mediana": tot, "fatia_mediana": round(fat, 3)}
    r["concentracao"] = {f"top{k}": dict(zip(("emendas", "votos", "populacao"), map(lambda x: round(x, 3), q(
        f"SELECT sum(emenda) FILTER (posicao <= {k}) / sum(emenda), sum(votos) FILTER (posicao <= {k}) / sum(votos), "
        f"sum(populacao) FILTER (posicao <= {k}) / sum(populacao) FROM p2")[0]))) for k in (1, 5, 10, 20)}
    [(p0, p1, sh0, base_sem)] = q("""SELECT avg((emenda > 0)::INT) FILTER (votos = 0), avg((emenda > 0)::INT) FILTER (votos > 0),
                                          sum(emenda) FILTER (votos = 0) / sum(emenda), avg((emenda = 0)::INT) FILTER (s_vot >= 0.01) FROM p2""")
    r["margem"] = {"chance_receber_sem_voto": round(p0, 3), "chance_receber_com_voto": round(p1, 3),
                   "fatia_emendas_sem_voto": round(sh0, 4), "municipios_base_sem_emenda": round(base_sem, 3)}

    # 4. Preço médio do voto por deputado: mecânico (a cota é igual, os votos não); só para consulta
    con.sql(f"""COPY (SELECT sq, any_value(uf) uf, round(any_value(em_tot)) emenda, any_value(vot_tot) votos,
                      round(any_value(em_tot) / any_value(vot_tot), 2) reais_por_voto FROM painel GROUP BY sq ORDER BY reais_por_voto)
                TO '{SAIDA / 'preco-por-deputado.csv'}' (HEADER)""")

    # 5. Votos de 2026 de quem concorreu de novo no mesmo estado. Associação, não efeito: ver o texto.
    c26 = d["v26_tot"] > 0
    v26 = d["votos26"]
    recebeu = em > 0
    s = lambda m: float(v26[m].sum() / votos[m].sum() - 1)
    r["votos_2026"] = {
        "deputados": int(len(np.unique(d["sq"][c26]))),
        "variacao_com_emenda": round(s(c26 & recebeu), 3), "variacao_sem_emenda": round(s(c26 & ~recebeu), 3),
        "fatia_dos_votos_em_cidades_com_emenda": {"2022": round(float(votos[c26 & recebeu].sum() / votos[c26].sum()), 3),
                                                  "2026": round(float(v26[c26 & recebeu].sum() / v26[c26].sum()), 3)},
        "por_votos_de_2022": [],
    }
    for ini_, fim_, nome in ((1, 10, "1 a 10"), (11, 50, "11 a 50"), (51, 200, "51 a 200"), (201, 1000, "201 a 1.000"),
                             (1001, 5000, "1.001 a 5.000"), (5001, 1e9, "mais de 5.000")):
        f = c26 & (votos >= ini_) & (votos <= fim_)
        r["votos_2026"]["por_votos_de_2022"].append({"faixa": nome, "pares_com_emenda": int((f & recebeu).sum()),
            "pares_sem_emenda": int((f & ~recebeu).sum()), "com_emenda": round(s(f & recebeu), 3), "sem_emenda": round(s(f & ~recebeu), 3)})
    # Poisson com efeito fixo de deputado e de município, controlando os votos de 2022 (corrige a volta à média):
    # votos 2026 ~ recebeu + log(emenda) centrado entre quem recebeu + log(votos 2022)
    m = c26 & (votos > 0)
    lem = np.zeros(len(em))
    lem[recebeu] = np.log(em[recebeu])
    lem[recebeu & m] -= lem[recebeu & m].mean()
    b, ep, n = ppml_dois_efeitos(v26[m], np.column_stack([recebeu[m].astype(float), lem[m], np.log(votos[m])]), g[m], grupos(d["ibge"])[m])
    r["votos_2026"]["associacao"] = coef(["recebeu", "log_emenda", "log_votos_2022"], b, ep) | {
        "pares": n, "recebeu_em_porcentagem": round(float(np.exp(b[0]) - 1), 3)}
    rec_ano = [(d[f"e{a}"] > 0).astype(float) for a in anos]
    b, ep, n = ppml_dois_efeitos(v26[m], np.column_stack([x[m] for x in rec_ano] + [np.log(votos[m])]), g[m], grupos(d["ibge"])[m])
    r["votos_2026"]["associacao_por_ano_de_pagamento"] = {
        str(a): {"coef": round(float(bi), 3), "ep": round(float(ei), 3), "em_porcentagem": round(float(np.exp(bi) - 1), 3)}
        for a, bi, ei in zip(anos, b, ep)}

    # ---- Os testes que tentam separar "a emenda traz o voto" de "a emenda acompanha a aliança". Associação, sempre.
    gi = grupos(d["ibge"])
    pct = lambda x: round(float(np.exp(x) - 1), 3)

    def recebeu_e_valor(m, valor=em):
        """Recebeu (0/1) e log do valor, centrado entre quem recebeu dentro do recorte m."""
        rec = valor > 0
        le = np.zeros(len(valor))
        le[rec] = np.log(valor[rec])
        le[rec & m] -= le[rec & m].mean()
        return rec.astype(float), le

    def dois(yv, colunas, rotulos, m, em_pct=()):
        """Poisson com efeito fixo de deputado e de município, no recorte m."""
        b, ep, n = ppml_dois_efeitos(yv[m], np.column_stack([c_[m] for c_ in colunas]), g[m], gi[m])
        saida = coef(rotulos, b, ep) | {"pares": n, "deputados": int(len(np.unique(d["sq"][m])))}
        for k in em_pct:
            saida[k]["em_porcentagem"] = pct(saida[k]["coef"])
        return saida

    def um(yv, colunas, rotulos, m, em_pct=()):
        saida = modelo(yv, colunas, rotulos, m)
        for k in em_pct:
            saida[k]["em_porcentagem"] = pct(saida[k]["coef"])
        return saida

    lv22 = np.log(np.maximum(votos, 1))

    # 6. Votos de 2018: a base antiga explica? E o ciclo anterior: emenda paga antes × depois da eleição de 2022.
    tem18, v18 = d["tem18"] > 0, d["votos18"]
    l18, z18, lv18 = np.log1p(v18), (v18 == 0).astype(float), np.log(np.maximum(v18, 1))
    m = c26 & tem18 & (votos > 0)
    R, L = recebeu_e_valor(m)
    rot3 = ["recebeu", "log_emenda", "log_votos_2022"]
    antes_em = d["emenda_antes"]
    rec_antes, rec_depois = (antes_em > 0).astype(float), recebeu.astype(float)
    mv = tem18 & vet & (v18 > 0)
    mn = tem18 & ~vet
    r["votos_2018"] = {
        "deputados_com_candidatura_em_2018": int(len(np.unique(d["sq"][tem18]))),
        "votos_2026_sem_controlar_2018": dois(v26, [R, L, lv22], rot3, m, ["recebeu"]),
        "votos_2026_controlando_2018": dois(v26, [R, L, lv22, l18, z18], rot3 + ["log_votos_2018", "zero_voto_2018"], m, ["recebeu"]),
        "destino_da_emenda_dados_2022_e_2018": um(em, [lv, z, l18, z18, lp], ["votos_2022", "zero_voto_2022", "votos_2018", "zero_voto_2018", "populacao"], tem18),
        # veteranos, votos de 2022 dados os de 2018: a emenda paga no próprio mandato (2019–22) e a paga depois (2023–26)
        "ciclo_anterior": {
            "emenda_2019_22_no_painel_bi": round(float(antes_em[vet].sum() / 1e9), 2),
            "so_a_paga_antes_da_eleicao": dois(votos, [rec_antes, lv18], ["recebeu_2019_22", "log_votos_2018"], mv, ["recebeu_2019_22"]),
            "so_a_paga_depois_da_eleicao": dois(votos, [rec_depois, lv18], ["recebeu_2023_26", "log_votos_2018"], mv, ["recebeu_2023_26"]),
            "as_duas_juntas": dois(votos, [rec_antes, rec_depois, lv18], ["recebeu_2019_22", "recebeu_2023_26", "log_votos_2018"], mv,
                                   ["recebeu_2019_22", "recebeu_2023_26"]),
            "por_ano_de_pagamento": dois(votos, [(d[f"e{a}"] > 0).astype(float) for a in antes] + [lv18],
                                         [str(a) for a in antes] + ["log_votos_2018"], mv, [str(a) for a in antes]),
        },
        # quem concorreu em 2018 sem mandato não tinha emenda: a de 2023–26 foi para onde ele tinha crescido?
        "novatos_sem_mandato_em_2018": um(votos, [rec_depois, l18, z18, lval], ["recebeu_2023_26", "votos_2018", "zero_voto_2018", "votos_validos"],
                                          mn, ["recebeu_2023_26"]) if mn.any() else None,
    }

    # 7. Prefeitos eleitos em 2024: o dinheiro acompanha o prefeito? O partido do prefeito explica o voto?
    tp = d["tem_pref"] > 0
    pref, colig, perdeu = d["prefeito_do_partido"], d["partido_na_coligacao"], d["partido_disputou_e_perdeu"]
    e2324, e2526 = d["e2023"] + d["e2024"], d["e2025"] + d["e2026"]
    rotp = ["prefeito_do_partido", "partido_na_coligacao", "partido_disputou_e_perdeu"]
    # onde o partido do deputado disputou a prefeitura: emenda depois da posse × antes, ganhou × perdeu,
    # cada par deputado–cidade comparado consigo mesmo (efeitos fixos de par e de deputado × período)
    qd = tp & ((pref > 0) | (perdeu > 0))
    n = int(qd.sum())
    b, ep, nobs = ppml_dois_efeitos(np.concatenate([e2324[qd], e2526[qd]]) / 1e6, np.concatenate([np.zeros(n), pref[qd]])[:, None],
                                    np.concatenate([np.arange(n), np.arange(n)]), np.concatenate([g[qd], g[qd] + g.max() + 1]),
                                    agrupar=np.concatenate([g[qd], g[qd]]))
    m = c26 & tp & (votos > 0)
    R, L = recebeu_e_valor(m)
    r["prefeitos_2024"] = {
        "pares": int(tp.sum()),
        "fatia_dos_pares": {k: round(float(x[tp].mean()), 3) for k, x in zip(rotp, (pref, colig, perdeu))},
        "destino_da_emenda_2023_24": um(e2324, [pref, colig, perdeu, lv, z, lp], rotp + RV, tp, rotp),
        "destino_da_emenda_2025_26": um(e2526, [pref, colig, perdeu, lv, z, lp], rotp + RV, tp, rotp),
        "ganhar_a_prefeitura_depois_x_antes": {"coef": round(float(b[0]), 3), "ep": round(float(ep[0]), 3), "em_porcentagem": pct(b[0]),
                                               "observacoes": nobs, "pares_onde_o_partido_disputou": n},
        "votos_2026": {
            "so_emenda": dois(v26, [R, L, lv22], rot3, m, ["recebeu"]),
            "so_prefeito": dois(v26, [pref, colig, perdeu, lv22], rotp + ["log_votos_2022"], m, rotp),
            "emenda_e_prefeito": dois(v26, [R, L, pref, colig, perdeu, lv22], rot3[:2] + rotp + ["log_votos_2022"], m, ["recebeu"] + rotp),
        },
    }

    # 8. Dobradinhas com deputado estadual: o grupo local explica o voto? O ganho é do deputado ou do grupo?
    tpar, tpar26 = d["tem_par"] > 0, d["tem_par26"] > 0
    forte = (d["parceiros22"] / np.maximum(d["estaduais22"], 1) >= 0.10).astype(float)
    p22, p26 = d["parceiros22_ambos"], d["parceiros26"]
    m = c26 & tpar26 & (votos > 0)
    R, L = recebeu_e_valor(m)
    mp = c26 & tpar26 & (p22 > 0)
    Rp, Lp = recebeu_e_valor(mp)
    [(n_pares, n_dep, mesmo, voltou)] = q("""SELECT count(*), count(DISTINCT sq), avg((partido = partido_estadual)::INT), avg((sq_est26 IS NOT NULL)::INT) FROM dobradinhas""")
    r["dobradinhas"] = {
        "pares_federal_estadual": n_pares, "deputados_com_parceiro": n_dep, "fatia_do_mesmo_partido": round(mesmo, 3),
        "fatia_dos_parceiros_que_concorreram_em_2026": round(voltou, 3),
        "destino_da_emenda": um(em, [forte, lv, z, lp], ["parceiros_com_10_por_cento_ou_mais_da_cidade"] + RV, tpar,
                                ["parceiros_com_10_por_cento_ou_mais_da_cidade"]),
        "votos_2026": {
            "so_emenda": dois(v26, [R, L, lv22], rot3, m, ["recebeu"]),
            "controlando_parceiros_em_2022": dois(v26, [R, L, lv22, np.log1p(p22)], rot3 + ["log_votos_dos_parceiros_2022"], m, ["recebeu"]),
            "controlando_parceiros_em_2022_e_2026": dois(v26, [R, L, lv22, np.log1p(p22), np.log1p(p26)],
                                                         rot3 + ["log_votos_dos_parceiros_2022", "log_votos_dos_parceiros_2026"], m, ["recebeu"]),
        },
        # o voto dos parceiros em 2026, dado o deles em 2022: foi melhor onde o federal mandou emenda?
        "votos_dos_parceiros_2026": dois(p26, [Rp, Lp, np.log(np.maximum(p22, 1))], ["recebeu", "log_emenda", "log_votos_dos_parceiros_2022"], mp, ["recebeu"]),
        "votos_dos_parceiros_2026_dados_os_do_deputado": dois(p26, [Rp, Lp, np.log(np.maximum(p22, 1)), lv, z],
            ["recebeu", "log_emenda", "log_votos_dos_parceiros_2022", "log_votos_do_deputado_2022", "zero_voto_do_deputado"], mp, ["recebeu"]),
    }
    return r


# ---------------------------------------------------------------- publicação

def publicar() -> None:
    """Envia insumos e resultados para analises/emendas-votos/<versão>/ e grava o ponteiro no repositório."""
    v = versao_insumos()
    comando = ["b2"] if shutil.which("b2") else ["uvx", "--from", "b2", "b2"]
    subprocess.run(comando + ["sync", "--compare-versions", "size", "--exclude-regex", r"(\.part|\.DS_Store)$",
                              str(SAIDA), f"b2://{BUCKET}/{PREFIXO}/{v}"], check=True)
    base = f"{ESPELHO}/{PREFIXO}/{v}"
    PONTEIRO.write_text(json.dumps({"versao": v, "base": base,
                                    "insumos": [f"insumos/{n}" for n in ARQUIVOS_INSUMOS],
                                    "resultados": list(ARQUIVOS_RESULTADOS)},
                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # A página do site (site/src/lib/analises.ts) lê os números desta cópia, que vai no commit com o ponteiro.
    shutil.copyfile(SAIDA / "resultados.json", PONTEIRO.parent / "resultados.json")
    print(f"publicado em {base}/ ; ponteiro e resultados.json em {PONTEIRO.parent.relative_to(c.RAIZ)}/ (vão no commit)")


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
