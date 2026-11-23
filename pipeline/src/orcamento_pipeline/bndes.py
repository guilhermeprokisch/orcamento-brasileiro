"""BNDES e estatais (/bndes): quem pega empréstimo do BNDES, com que juro, quanto custa o subsídio e o que entra e sai
das estatais federais.

    uv run bndes                     # baixa tudo (~1,3 GB do BNDES e ~1,3 GB do cadastro de CNPJ, lidos e apagados)
    uv run bndes --receita 2026-11   # o mês do cadastro de CNPJ (padrão: o último)
    uv run bndes --sem-baixar        # só copia as cópias versionadas para o site (publicação automática)

Fontes:

- BNDES, dados abertos, "Operações de financiamento": um CSV com as operações diretas e indiretas não automáticas
  (20 MB, CNPJ completo, a cidade do projeto) e outro com as indiretas automáticas (1,2 GB, o documento mascarado,
  `**.*99.999/9999-**`, a cidade do cliente). Os dois desde 2002, com o valor contratado, o custo financeiro (TJLP,
  TLP, Selic, taxa fixa…), o produto, o programa e o setor. O servidor às vezes corta o download no meio sem erro:
  confere o tamanho e retoma.
- BNDES, "Estatísticas de desembolsos" por porte (com pessoa física à parte): o que saiu de fato em cada mês. O crédito
  rural das pessoas físicas quase não está nos arquivos de operação, então entra só por aqui, somado.
- Receita Federal, cadastro de CNPJ (arquivos Empresas): a natureza jurídica, para não nomear empresário individual nem
  MEI, e o nome de empresa que identifica cada cliente das indiretas (nome igual e os 5 dígitos visíveis da raiz).
- Ministério do Planejamento, Orçamento de Subsídios da União (anexo, Tabela 1): o custo estimado dos subsídios
  financeiros e creditícios por programa.
- Tesouro Nacional, Resultado do Tesouro Nacional (série histórica, Tabela 2.2): os dividendos que cada estatal pagou
  à União e o que o Tesouro pagou de equalização do Plano Safra.
- Ministério da Gestão, dados abertos das estatais (SEST): a subvenção do Tesouro a cada estatal dependente (DRE).
- Benefícios fiscais por empresa (data/publico/beneficios-fiscais-empresas.parquet, de beneficios_fiscais.py), quando
  existir: o benefício que cada empresa declarou, para a ligação com /impostos/empresas.

Privacidade:

- Nas indiretas há pessoas físicas pelo nome, e às vezes um CPF dentro do nome (empresário individual). Só aparece
  pelo nome quem bate com uma empresa do cadastro de CNPJ e não é pessoa: nem empresário individual ou MEI (natureza
  213-5) nem do grupo 4 das naturezas, o das pessoas físicas com CNPJ (produtor rural, 412-0); nas diretas, a raiz do
  CNPJ também passa pela natureza. Todo o resto entra só nos totais. Nenhuma saída guarda o
  documento das indiretas: guarda a raiz achada no cadastro.

Saídas (site/public/data/bndes/, com cópia em pipeline/referencia/ para a publicação automática):

- resumo.json: a página /bndes (série, juros, setores, os maiores, o custo, as estatais).
- cidades.json: por cidade (código IBGE), o ano fechado mais recente, para a página da cidade.
- empresas.json: por raiz de CNPJ, o total desde 2020 e a parte com juro abaixo do de mercado, para a busca de /bndes
  e a ficha de /impostos/empresas.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import statistics
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import openpyxl

from .cidades import RAIZ
from .divida_ativa import URL_RECEITA, _baixar as _baixar_receita, e_pessoa, ultimo_mes_receita
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA = RAIZ / "data" / "raw" / "bndes"
SAIDA = RAIZ / "site" / "public" / "data" / "bndes"
REFERENCIA = RAIZ / "pipeline" / "referencia"
ARQUIVOS = {"resumo.json": "bndes.json", "cidades.json": "bndes-cidades.json", "empresas.json": "bndes-empresas.json"}
BENEFICIOS = RAIZ / "data" / "publico" / "beneficios-fiscais-empresas.parquet"

CKAN_BNDES = "https://dadosabertos.bndes.gov.br/api/3/action/package_show?id="
CKAN_TESOURO = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id="
RTN_PACOTE = "ab56485b-9c40-4efb-8563-9ce3e1973c4b"
OSU_PAGINA = "https://www.gov.br/planejamento/pt-br/assuntos/avaliacao-de-politicas-publicas/orcamento-de-subsidios-da-uniao"
SEST = "https://www.gov.br/gestao/pt-br/assuntos/estatais/transparencia/"
FONTE = ("BNDES, operações contratadas e desembolsos (dados abertos); Receita Federal, cadastro de CNPJ; Ministério do "
         "Planejamento, Orçamento de Subsídios da União; Tesouro Nacional, Resultado do Tesouro Nacional; Ministério da "
         "Gestão, dados das estatais (SEST)")
PRIMEIRO_ANO_EMPRESAS = 2020
CPF_NO_NOME = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{11}")

# O custo financeiro de cada operação, em quatro faixas para a página. O BNDES soma o spread dele por cima.
# - abaixo: TJLP (fixada pelo governo abaixo do custo do Tesouro, trocada pela TLP em 2018), taxa fixa e TR (as linhas com
#   dinheiro de fundo, como Fundo Clima, FUST e FNDCT, ou com equalização do Tesouro, como Pronaf e Brasil Soberano);
# - tlp: segue o juro do título do Tesouro corrigido pela inflação (NTN-B), sem desconto do Tesouro;
# - mercado: Selic, CDI, IPCA, dólar ou cesta de moedas;
# - doacao: o apoio não reembolsável (Fundo Amazônia, Fundo Social), que não volta.
FAIXAS = ("abaixo", "tlp", "mercado", "doacao")


def faixa_de_juro(custo: str, modalidade: str) -> str:
    c, m = (custo or "").upper().strip(), (modalidade or "").upper()
    if m.startswith("NÃO REEMB") or m.startswith("NAO REEMB"):
        return "doacao"
    if c in ("TJLP", "TAXA FIXA") or c.startswith("TAXA REFERENCIAL"):
        return "abaixo"
    if c == "TLP":
        return "tlp"
    return "mercado"


SQL_FAIXA = """CASE WHEN upper(modalidade) LIKE 'N_O REEMB%' THEN 'doacao'
    WHEN upper(trim(custo)) IN ('TJLP', 'TAXA FIXA') OR upper(trim(custo)) LIKE 'TAXA REFERENCIAL%' THEN 'abaixo'
    WHEN upper(trim(custo)) = 'TLP' THEN 'tlp' ELSE 'mercado' END"""

SETORES = {"INFRAESTRUTURA": "infra", "INFRA-ESTRUTURA": "infra", "INDUSTRIA": "industria", "INDÚSTRIA": "industria",
           "COMERCIO/SERVICOS": "comercio", "COMÉRCIO/SERVIÇOS": "comercio", "AGROPECUÁRIA": "agro", "AGROPECUARIA": "agro"}
NOMES_SETOR = {"infra": "Estradas, aeroportos, portos, energia e saneamento", "industria": "Indústria",
               "comercio": "Comércio e serviços", "agro": "Agropecuária"}

# "Para quê", a partir do programa (instrumento financeiro) e do produto. A primeira regra que casa vale.
PARA_QUE = [
    (r"FUNDO AMAZ", "Fundo Amazônia (doação)"), (r"N[ÃA]O REEMBOLS", "Doação"),
    (r"RODOVIAS E FERROVIAS", "Rodovias e ferrovias"), (r"RODOVI", "Rodovias"), (r"AEROPORT", "Aeroportos"), (r"MARINHA MERCANTE", "Barcos e estaleiros (Marinha Mercante)"),
    (r"FERROVI|HIDROVI", "Ferrovias e hidrovias"), (r"PORTO|TERMINA", "Portos"), (r"SANEAMENTO|\bAGUA\b|ESGOTO", "Saneamento"),
    (r"MOBILIDADE|TRILHOS|BRT", "Transporte urbano"), (r"FUNDO CLIMA", "Fundo Clima"),
    (r"ENERGIA|SOLAR|E[ÓO]LICA|BIOMASSA|HIDREL|TRANSMISS|G[ÁA]S", "Energia"), (r"INOVA", "Inovação"),
    (r"SOBERANO", "Brasil Soberano (exportadoras)"), (r"[ÔO]NIBUS E CAMINH", "Ônibus e caminhões"),
    (r"PRONAF|RURAL|ARMAZ|AGRO|ABC|PRODECOOP|PCA", "Agropecuária"),
    (r"PEQUENAS E M[ÉE]DIAS|GIRO", "Capital de giro"), (r"EXPORT|EXIM|PR[ÉE]-EMBARQUE", "Exportação"),
    (r"DEB[ÊE]NTURE", "Debêntures"), (r"FUST|TELECOM", "Telecomunicações"), (r"SA[ÚU]DE", "Saúde"),
    (r"EDUCA", "Educação"), (r"PMAT|GEST[ÃA]O P[ÚU]BLICA|ESTADO|MUNIC", "Gestão pública e obras"),
    (r"MATERIAIS INDUSTRIALIZADOS|BK |M[ÁA]QUINAS|FINAME", "Máquinas e equipamentos"),
    (r"CAPACIDADE PRODUTIVA", "Ampliação de fábricas e serviços"),
]


def para_que(instrumento: str, produto: str, subsetor: str = "") -> str:
    """Pelo programa e pelo produto; nas debêntures e no que não casar, pelo setor da empresa (CNAE)."""
    def casar(texto: str) -> str:
        for padrao, nome in PARA_QUE:
            if re.search(padrao, texto.upper()):
                return nome
        return "Outros"
    p = casar(f"{instrumento or ''} {produto or ''}")
    if p in ("Debêntures", "Outros") and subsetor:
        q = casar(subsetor)
        if q not in ("Outros", "Gestão pública e obras"):
            return q
    return p


def normalizar_nome(nome: str) -> str:
    """Para comparar o nome do BNDES (cortado em 55 letras) com a razão social da Receita: sem acento, pontuação nem
    o número entre parênteses que o BNDES às vezes põe no fim, e só as 30 primeiras letras."""
    s = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\(\d+\)\s*$", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s).strip()
    return s[:30].strip()


def digitos_visiveis(doc: str) -> str:
    """'**.*16.560/0001-**' → '16560' (os 5 dígitos da raiz que o BNDES mostra: do 4º ao 8º)."""
    d = re.sub(r"[^0-9*]", "", doc or "")
    return d[3:8] if len(d) == 14 and "*" not in d[3:8] else ""


def raiz_no_nome(nome: str) -> str:
    """O BNDES às vezes põe a raiz do CNPJ no fim do nome: 'BOM JESUS AGROPECUARIA LTDA (08895796)'."""
    m = re.search(r"\((\d{8})\)\s*$", nome or "")
    return m.group(1) if m else ""


def pode_nomear(nome: str, natureza: str | None) -> bool:
    """A mesma regra da dívida ativa e dos benefícios fiscais (divida_ativa.e_pessoa), com a natureza obrigatória:
    nas indiretas, quem não foi achado no cadastro de CNPJ não aparece pelo nome."""
    return bool(natureza) and not e_pessoa(natureza) and not CPF_NO_NOME.search(nome or "")


# ---------------------------------------------------------------- downloads

def _abrir(url: str, cab: dict | None = None, timeout: int = 300):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(cab or {})})
    return urllib.request.urlopen(req, timeout=timeout, context=CONTEXTO_TLS)


def _json(url: str) -> dict:
    with _abrir(url, timeout=60) as r:
        return json.load(r)


def baixar(url: str, destino: Path, tamanho: int | None = None) -> Path:
    """Baixa com retomada (Range) até ter o tamanho esperado; não baixa de novo se já está inteiro."""
    if destino.exists() and (tamanho is None or destino.stat().st_size == tamanho):
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_name(destino.name + ".part")
    for tentativa in range(12):
        ja = parte.stat().st_size if parte.exists() else 0
        if tamanho and ja >= tamanho:
            break
        try:
            with _abrir(url, {"Range": f"bytes={ja}-"} if ja else None, timeout=600) as r, parte.open("ab" if ja else "wb") as f:
                if ja and r.status != 206:
                    f.truncate(0)
                shutil.copyfileobj(r, f, 8 << 20)
            if tamanho is None or parte.stat().st_size >= tamanho:
                break
            print(f"    {destino.name}: veio {parte.stat().st_size / 1e6:,.0f} de {tamanho / 1e6:,.0f} MB; retomando", flush=True)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 416):
                raise
            print(f"    {destino.name}: {e}; tentando de novo", flush=True)
            time.sleep(10 * (tentativa + 1))
    if tamanho and parte.stat().st_size != tamanho:
        raise RuntimeError(f"{url}: veio com {parte.stat().st_size} bytes, esperava {tamanho}")
    parte.rename(destino)
    return destino


def recurso_bndes(pacote: str, padrao: str) -> tuple[str, int | None]:
    for r in _json(CKAN_BNDES + pacote)["result"]["resources"]:
        if re.search(padrao, r["url"]):
            return r["url"], r.get("size")
    raise RuntimeError(f"BNDES: {pacote} sem recurso {padrao}")


def utf8(origem: Path) -> Path:
    """Os CSVs do BNDES vêm em Windows-1252, com um ou outro byte inválido; o DuckDB quer UTF-8."""
    destino = origem.with_suffix(".utf8.csv")
    if destino.exists() and destino.stat().st_mtime >= origem.stat().st_mtime:
        return destino
    with origem.open("rb") as e, destino.open("w", encoding="utf-8", newline="") as s:
        for bloco in iter(lambda: e.read(16 << 20), b""):
            s.write(bloco.decode("cp1252", errors="replace"))
    return destino


# ---------------------------------------------------------------- 1. as operações

def tabela(con: duckdb.DuckDBPyConnection, nome: str, colunas: list[str], linhas: list[list]) -> None:
    """Uma tabela temporária de texto a partir de listas do Python (por um CSV: o executemany é lento e não aceita vazio)."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(colunas)
        w.writerows(linhas)
    tipos = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in colunas) + "}"
    con.execute(f"CREATE OR REPLACE TEMP TABLE {nome} AS SELECT * FROM read_csv('{f.name}', header=true, columns={tipos}, quote='\"', escape='\"')")
    Path(f.name).unlink()


def ler_operacoes(con: duckdb.DuckDBPyConnection, diretas: Path, indiretas: Path) -> None:
    """Junta os dois arquivos numa tabela op, com a faixa de juro, o setor e o "para quê"."""
    num = lambda c: f"TRY_CAST(replace(replace({c}, '.', ''), ',', '.') AS DOUBLE)"  # noqa: E731
    ler = lambda p: f"read_csv('{p}', delim=';', header=true, all_varchar=true, quote='\"')"  # noqa: E731
    con.execute(f"""CREATE OR REPLACE TABLE op AS
        SELECT 'direta' AS forma, TRY_CAST(data_da_contratacao AS DATE) AS data, trim(cliente) AS cliente,
               substr(regexp_replace(cnpj, '[^0-9]', '', 'g'), 1, 8) AS raiz, '' AS vis,
               nullif(nullif(trim(municipio_codigo), '0'), '9999999') AS ibge, trim(uf) AS uf,
               {num('valor_contratado_reais')} AS valor, trim(custo_financeiro) AS custo, modalidade_de_apoio AS modalidade,
               trim(produto) AS produto, trim(instrumento_financeiro) AS instrumento, upper(trim(setor_bndes)) AS setor_bndes,
               trim(natureza_do_cliente) AS natureza, trim(subsetor_cnae_nome) AS subsetor
          FROM {ler(diretas)}
        UNION ALL
        SELECT 'indireta', TRY_CAST(data_da_contratacao AS DATE), trim(cliente),
               regexp_extract(trim(cliente), '\\((\\d{{8}})\\)\\s*$', 1),
               CASE WHEN regexp_matches(cpf_cnpj, '^[*][*][.][*][0-9]{{2}}[.][0-9]{{3}}/') THEN substr(regexp_replace(cpf_cnpj, '[^0-9*]', '', 'g'), 4, 5) ELSE '' END,
               nullif(nullif(trim(municipio_codigo), '0'), '9999999'), trim(uf),
               {num('valor_da_operacao_em_reais')}, trim(custo_financeiro), modalidade_de_apoio,
               trim(produto), trim(instrumento_financeiro), upper(trim(setor_bndes)), trim(natureza_do_cliente),
               trim(subsetor_cnae_nome)
          FROM {ler(indiretas)}""")
    con.execute("DELETE FROM op WHERE data IS NULL OR valor IS NULL")
    # Antes de 2011 o BNDES trocava o nome da pessoa física pelo nome do banco: não é cliente, só total.
    con.execute("""ALTER TABLE op ADD COLUMN ano INTEGER; ALTER TABLE op ADD COLUMN faixa VARCHAR;
                   ALTER TABLE op ADD COLUMN setor VARCHAR; ALTER TABLE op ADD COLUMN para VARCHAR;""")
    casos = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in SETORES.items())
    con.execute(f"""UPDATE op SET ano = year(data), faixa = {SQL_FAIXA}, setor = coalesce(CASE setor_bndes {casos} END, 'comercio')""")
    # "Para quê": calculado em Python para cada par (programa, produto), que são poucos.
    pares = con.execute("SELECT DISTINCT instrumento, produto, subsetor FROM op").fetchall()
    tabela(con, "pq", ["instrumento", "produto", "subsetor", "para"], [[i, p, ss, para_que(i, p, ss)] for i, p, ss in pares])
    con.execute("""UPDATE op SET para = pq.para FROM pq
                    WHERE op.instrumento IS NOT DISTINCT FROM pq.instrumento AND op.produto IS NOT DISTINCT FROM pq.produto
                      AND op.subsetor IS NOT DISTINCT FROM pq.subsetor""")
    # Diretas: a raiz vem do CNPJ; indiretas: a raiz no nome só vale se bater com os dígitos visíveis.
    con.execute("UPDATE op SET raiz = '' WHERE forma = 'indireta' AND (raiz = '' OR substr(raiz, 4, 5) <> vis)")


def identificar(con: duckdb.DuckDBPyConnection, mes: str) -> None:
    """Acha a raiz e a natureza jurídica de cada cliente no cadastro de CNPJ da Receita (arquivos Empresas, um por
    vez, apagados depois). Indiretas: nome normalizado igual e os 5 dígitos visíveis iguais. Cache em data/raw/bndes."""
    clientes = con.execute("""SELECT DISTINCT vis, cliente FROM op
                               WHERE forma = 'indireta' AND raiz = '' AND vis <> '' AND ano >= 2011""").fetchall()
    tabela(con, "nomes", ["vis", "cliente", "nome"], [[v, c, normalizar_nome(c)] for v, c in clientes])
    raizes = {r for (r,) in con.execute("SELECT DISTINCT raiz FROM op WHERE raiz <> ''").fetchall()}
    chaves = {(v, n) for v, n in con.execute("SELECT DISTINCT vis, nome FROM nomes").fetchall()}
    cache = PASTA / f"cadastro-{mes}.csv"
    achados: dict[tuple[str, str], str] = {}
    natureza: dict[str, str] = {}
    if cache.exists():
        with cache.open(encoding="utf-8") as f:
            for tipo, a, b, c in csv.reader(f, delimiter=";"):
                if tipo == "n":
                    natureza[a] = b
                else:
                    achados[(a, b)] = c
    else:
        tmp = PASTA / "cnpj-tmp"
        repetidas: set[tuple[str, str]] = set()
        for i in range(10):
            arq = _baixar_receita(f"{URL_RECEITA}{mes}/Empresas{i}.zip", tmp / f"Empresas{i}.zip", receita=True)
            with zipfile.ZipFile(arq) as z:
                for membro in z.namelist():
                    for r in csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";"):
                        if len(r) < 3:
                            continue
                        raiz = r[0]
                        k = (raiz[3:8], normalizar_nome(r[1]))
                        if k in chaves:
                            if k in achados and achados[k] != raiz:
                                repetidas.add(k)
                            achados[k] = raiz
                            natureza[raiz] = r[2]
                        if raiz in raizes:
                            natureza[raiz] = r[2]
            arq.unlink()
            print(f"    Empresas{i}: {len(achados):,} clientes das indiretas achados; natureza de {len(natureza):,} raízes", flush=True)
        for k in repetidas:   # dois CNPJs com o mesmo começo de nome e os mesmos dígitos: não dá para saber qual
            achados.pop(k, None)
        PASTA.mkdir(parents=True, exist_ok=True)
        with cache.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerows(["n", k, v, ""] for k, v in sorted(natureza.items()))
            w.writerows(["c", k[0], k[1], v] for k, v in sorted(achados.items()))
    tabela(con, "achados", ["vis", "nome", "raiz"], [[k[0], k[1], v] for k, v in achados.items()])
    con.execute("""UPDATE op SET raiz = x.raiz FROM (SELECT n.vis, n.cliente, a.raiz FROM nomes n JOIN achados a USING (vis, nome)) x
                    WHERE op.forma = 'indireta' AND op.raiz = '' AND op.vis = x.vis AND op.cliente = x.cliente""")
    tabela(con, "nat", ["raiz", "natureza_rfb"], [list(x) for x in natureza.items()])
    marcar_nomeaveis(con)


def marcar_nomeaveis(con: duckdb.DuckDBPyConnection) -> None:
    """chave: a raiz de quem pode aparecer pelo nome; '' para o resto (pessoas, MEI, quem não foi achado)."""
    con.execute("ALTER TABLE op ADD COLUMN IF NOT EXISTS chave VARCHAR")
    # As naturezas de pessoa saem da mesma regra da dívida ativa (e_pessoa), não de uma cópia dela em SQL.
    naturezas = [n for (n,) in con.execute("SELECT DISTINCT natureza_rfb FROM nat WHERE natureza_rfb IS NOT NULL").fetchall()]
    tabela(con, "pessoa", ["natureza_rfb"], [[n] for n in naturezas if e_pessoa(n)])
    con.execute(f"""UPDATE op SET chave = CASE WHEN op.raiz <> '' AND n.natureza_rfb IS NOT NULL
                                                  AND n.natureza_rfb NOT IN (SELECT natureza_rfb FROM pessoa)
                                                  AND NOT regexp_matches(op.cliente, '{CPF_NO_NOME.pattern}') THEN op.raiz
                                             WHEN op.forma = 'direta' AND op.raiz <> '' AND n.natureza_rfb IS NULL
                                                  AND op.natureza NOT ILIKE 'PRIVADA%' THEN op.raiz
                                             ELSE '' END
                     FROM (SELECT DISTINCT o.raiz, nat.natureza_rfb FROM op o LEFT JOIN nat USING (raiz)) n
                    WHERE n.raiz = op.raiz""")
    con.execute("UPDATE op SET chave = '' WHERE chave IS NULL")


# ---------------------------------------------------------------- 2. desembolsos, subsídios e estatais

def desembolsos() -> list[list]:
    url, tam = recurso_bndes("desembolsos", r"por-porte-de-empresa-pf-e-pj")
    arq = baixar(url, PASTA / "desembolsos-pf-pj.csv", tam)
    por_ano: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    with arq.open(encoding="cp1252", errors="replace") as f:
        for r in csv.DictReader(f, delimiter=";"):
            v = [float((r[k] or "0").replace(",", ".")) * 1e6 for k in ("pessoa_fisica", "micro", "pequena", "media", "grande")]
            a = por_ano[int(r["ano"])]
            a[0] += sum(v)
            a[1] += v[0]
    return [[ano, round(t), round(pf)] for ano, (t, pf) in sorted(por_ano.items()) if ano >= 2002]


def _anos_do_cabecalho(linha: tuple) -> dict[int, int]:
    return {int(c): j for j, c in enumerate(linha) if isinstance(c, (int, float)) and 1990 < c < 2100}


def subsidios_osu() -> dict:
    """Orçamento de Subsídios da União, Tabela 1 do anexo mais recente: R$ mil por programa e tipo."""
    with _abrir(OSU_PAGINA, timeout=60) as r:
        html = r.read().decode("utf-8", errors="replace")
    links = sorted(set(re.findall(r'href="([^"]*osu_(\d{4})-anex[^"]*\.xlsx/@@download/file)"', html)), key=lambda x: x[1])
    if not links:
        raise RuntimeError("OSU: nenhum anexo na página")
    href, edicao = links[-1]
    arq = baixar(href if href.startswith("http") else "https://www.gov.br" + href, PASTA / f"osu-{edicao}.xlsx")
    ws = openpyxl.load_workbook(arq, read_only=True, data_only=True)["Tab_1"]
    linhas = list(ws.iter_rows(values_only=True))
    cab = next(i for i, r in enumerate(linhas) if any(str(c).strip() == "Discriminação" for c in r if c))
    col = _anos_do_cabecalho(linhas[cab])
    anos = sorted(col)[-3:]
    tipos: dict[str, list[float]] = {}
    programas: dict[str, list[list]] = {"financeiros": [], "crediticios": []}
    atual = None
    for r in linhas[cab + 1:]:
        nome = next((str(c).strip() for c in r if isinstance(c, str) and c.strip()), "")
        if not nome:
            continue
        vals = [float(r[col[a]] or 0) * 1e3 if col[a] < len(r) and isinstance(r[col[a]], (int, float)) else 0.0 for a in anos]
        if nome.startswith("Benefícios Financeiros"):
            atual, tipos["financeiros"] = "financeiros", vals
        elif nome.startswith("Benefícios Creditícios"):
            atual, tipos["crediticios"] = "crediticios", vals
        elif nome.startswith("Benefícios Tributários"):
            atual, tipos["tributarios"] = None, vals
        elif nome == "TOTAL":
            tipos["total"] = vals
            break
        elif atual:
            programas[atual].append([nome, *[round(v) for v in vals]])
    for k in programas:
        programas[k].sort(key=lambda p: -p[-1])
    return {"edicao": int(edicao), "anos": anos, "tipos": {k: [round(v) for v in vs] for k, vs in tipos.items()}, **programas}


def resultado_tesouro() -> dict:
    """Tabela 2.2 (anual, R$ milhões) da série histórica do RTN: dividendos por estatal e a equalização do Plano Safra."""
    res = next(r for r in _json(CKAN_TESOURO + RTN_PACOTE)["result"]["resources"]
               if r["url"].endswith(".xlsx") and "série histórica" in r["name"].lower())
    arq = baixar(res["url"], PASTA / "rtn.xlsx")
    ws = openpyxl.load_workbook(arq, read_only=True, data_only=True)["2.2"]
    linhas = list(ws.iter_rows(values_only=True))
    cab = next(i for i, r in enumerate(linhas) if r and str(r[0] or "").strip() == "Discriminação")
    col = _anos_do_cabecalho(linhas[cab])
    anos = [a for a in sorted(col) if a >= 2010]
    def serie(r: tuple) -> list[int]:
        return [round(float(r[col[a]] or 0) * 1e6) for a in anos]
    dividendos: dict[str, list[int]] = {}
    safra: dict[str, list[int]] = {}
    for r in linhas[cab + 1:]:
        rotulo = str(r[0] or "").strip()
        m = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", rotulo)
        if not m:
            continue
        cod, nome = m.group(1), re.sub(r"\s+\d+/$", "", m.group(2)).strip()
        if cod == "1.4.2":
            dividendos["total"] = serie(r)
        elif cod.startswith("1.4.2.") and cod.count(".") == 3:
            dividendos[nome] = serie(r)
        elif re.fullmatch(r"4\.\d\.15\.1\.[1-4]", cod):   # custeio, investimento, preços e Pronaf (a fonte escreve 4.1.15.1.2)
            safra[nome] = serie(r)
    return {"anos": anos, "dividendos": dividendos, "safra": safra}


def estatais_dependentes() -> dict:
    """SEST: a subvenção do Tesouro na DRE de cada estatal (anual até 2024; o 4º trimestre, acumulado, depois)."""
    ident = baixar(SEST + "sestidentificacao.zip", PASTA / "sest-identificacao.zip")
    dados = baixar(SEST + "sestdadosfinanceiros.zip", PASTA / "sest-dadosfinanceiros.zip")
    nomes: dict[str, tuple[str, str, bool]] = {}
    with zipfile.ZipFile(ident) as z:
        membro = next(n for n in z.namelist() if n.endswith("empresas-ativas.csv"))
        for r in csv.DictReader(io.TextIOWrapper(z.open(membro), encoding="latin-1"), delimiter=";"):
            nomes[r["codigo_siest"]] = (r["sigla"], r["nome"], r["dependencia"].startswith("Dependente"))
    valores: dict[tuple[str, int, str], float] = defaultdict(float)
    with zipfile.ZipFile(dados) as z:
        membro = next(n for n in z.namelist() if n.endswith("demonstracoes.csv"))
        for r in csv.DictReader(io.TextIOWrapper(z.open(membro), encoding="latin-1"), delimiter=";"):
            if r["demonstrativo"] == "DRE" and r["rubrica_codigo"] in ("407000", "260100000"):
                valores[(r["codigo_siest"], int(r["exercicio"]), r["periodicidade"])] += float(r["valor"].replace(".", "").replace(",", ".") or 0)
    # Por ano, o período mais completo que houver: o anual, senão o último trimestre publicado.
    ordem = ["Anual", "4º Trimestre", "3º Trimestre", "2º Trimestre", "1º Trimestre"]
    escolhido: dict[int, str] = {}
    for _, ano, per in valores:
        if ano not in escolhido or ordem.index(per) < ordem.index(escolhido[ano]):
            escolhido[ano] = per
    anos = sorted(a for a in escolhido if a >= 2016)
    emp: dict[str, list[int]] = defaultdict(lambda: [0] * len(anos))
    for (cod, ano, per), v in valores.items():
        if ano in anos and per == escolhido[ano]:
            emp[cod][anos.index(ano)] += round(v)
    lista = []
    for cod, vs in emp.items():
        sigla, nome, dep = nomes.get(cod, (cod, cod, False))
        if any(vs):
            lista.append([sigla, nome, dep, *vs])
    lista.sort(key=lambda x: -x[-1])
    return {"anos": anos, "periodo": {str(a): escolhido[a] for a in anos}, "empresas": lista,
            "dependentes": sum(1 for v in nomes.values() if v[2])}


# ---------------------------------------------------------------- 3. montar as saídas

def _bi(v: float) -> str:
    return f"R$ {v / 1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def montar(con: duckdb.DuckDBPyConnection, desemb: list, osu: dict | None, rtn: dict | None, sest: dict | None) -> tuple[dict, dict, dict]:
    ultima = con.execute("SELECT max(data) FROM op").fetchone()[0]
    ano = ultima.year - 1 if ultima.month < 12 else ultima.year
    f = ", ".join(f"round(sum(valor) FILTER (faixa = '{x}')) AS {x}" for x in FAIXAS)
    serie = con.execute(f"""SELECT ano, round(sum(valor) FILTER (forma = 'direta')), round(sum(valor) FILTER (forma = 'indireta')), {f}
                            FROM op GROUP BY ano ORDER BY ano""").fetchall()
    serie = [[int(x or 0) for x in r] for r in serie]
    setores = con.execute(f"SELECT setor, round(sum(valor)) v FROM op WHERE ano = {ano} GROUP BY 1 ORDER BY v DESC, setor").fetchall()
    programas = con.execute(f"""SELECT para, round(sum(valor)) v FROM op WHERE ano = {ano} AND faixa = 'abaixo'
                                GROUP BY 1 ORDER BY v DESC, para LIMIT 8""").fetchall()

    # Os clientes que podem aparecer pelo nome, agregados pela raiz.
    con.execute(f"""CREATE OR REPLACE TEMP TABLE cli AS
        SELECT chave, ano, first(cliente ORDER BY valor DESC, cliente) AS nome, first(uf ORDER BY valor DESC, uf) AS uf, first(para ORDER BY valor DESC, para) AS para,
               sum(valor) AS valor, sum(valor) FILTER (faixa = 'abaixo') AS abaixo,
               {", ".join(f"sum(valor) FILTER (faixa = '{x}') AS v_{x}" for x in FAIXAS)},
               bool_or(forma = 'direta') AS direta, count(*) AS n
          FROM op WHERE chave <> '' GROUP BY chave, ano""")
    beneficio: dict[str, list] = {}
    if BENEFICIOS.exists():
        colunas = {c for (c,) in con.execute(f"SELECT name FROM parquet_schema('{BENEFICIOS}')").fetchall()}
        anos_ben = sorted(int(c[1:]) for c in colunas if re.fullmatch(r"v\d{4}", c))
        ano_ben = max((a for a in anos_ben if a <= ano), default=None)
        if ano_ben:
            antes = f"coalesce(v{ano_ben - 1}, 0)" if ano_ben - 1 in anos_ben else "0"
            for raiz, v, b, dois in con.execute(f"""SELECT raiz, v{ano_ben}, beneficio, coalesce(v{ano_ben}, 0) + {antes}
                                                   FROM '{BENEFICIOS}' WHERE raiz <> ''""").fetchall():
                beneficio[raiz] = [round(v or 0), b, round(dois)]
    def principal(chave: str, a: int) -> str:
        vs = con.execute(f"SELECT {', '.join(f'coalesce(v_{x}, 0)' for x in FAIXAS)}, valor FROM cli WHERE chave = ? AND ano = ?",
                         [chave, a]).fetchone()
        fx = max(range(4), key=lambda i: vs[i])
        return FAIXAS[fx] if vs[fx] >= 0.8 * vs[4] else "misto"
    maiores = []
    for chave, nome, uf, para, valor, abaixo in con.execute(
            f"SELECT chave, nome, uf, para, valor, coalesce(abaixo, 0) FROM cli WHERE ano = {ano} ORDER BY valor DESC, chave LIMIT 100").fetchall():
        b = beneficio.get(chave)
        maiores.append([nome_limpo(nome), chave, uf, para, principal(chave, ano), round(valor), round(abaixo), b[0] if b else None])
    sem_nome = con.execute(f"SELECT count(DISTINCT cliente), round(sum(valor)) FROM op WHERE ano = {ano} AND chave = ''").fetchone()
    sem_cidade = con.execute(f"SELECT round(sum(valor)) FROM op WHERE ano = {ano} AND ibge IS NULL").fetchone()[0] or 0
    diretas_ano = con.execute(f"SELECT round(sum(valor)) FROM op WHERE ano = {ano} AND forma = 'direta'").fetchone()[0] or 0

    # Ligação com os benefícios fiscais: empresas privadas com empréstimo direto nos dois últimos anos fechados.
    cruz = None
    if beneficio:
        linhas = con.execute(f"""SELECT chave, sum(valor) FROM op WHERE forma = 'direta' AND chave <> '' AND natureza ILIKE 'PRIVADA%'
                                 AND ano BETWEEN {ano - 1} AND {ano} GROUP BY 1""").fetchall()
        com = [(k, v) for k, v in linhas if beneficio.get(k, [0, "", 0])[2] > 0]
        cruz = {"anos": [ano - 1, ano], "empresas": len(linhas), "com_beneficio": len(com),
                "valor": round(sum(v for _, v in linhas)), "valor_com_beneficio": round(sum(v for _, v in com))}

    # Por cidade, o ano fechado.
    mun: dict[str, list] = {}
    por_cidade = con.execute(f"""SELECT ibge, count(*), round(sum(valor)), {", ".join(f"round(coalesce(sum(valor) FILTER (faixa = '{x}'), 0))" for x in FAIXAS)},
                                        count(DISTINCT cliente), round(coalesce(sum(valor) FILTER (forma = 'indireta'), 0)),
                                        round(coalesce(sum(valor) FILTER (para IN ('Máquinas e equipamentos', 'Ônibus e caminhões')), 0))
                                   FROM op WHERE ano = {ano} AND ibge IS NOT NULL GROUP BY ibge ORDER BY ibge""").fetchall()
    top = defaultdict(list)
    for ibge, chave, nome, valor, para in con.execute(f"""
            SELECT ibge, chave, first(cliente ORDER BY valor DESC, cliente), sum(valor) v, first(para ORDER BY valor DESC, para) FROM op
             WHERE ano = {ano} AND ibge IS NOT NULL AND chave <> '' GROUP BY ibge, chave
            QUALIFY row_number() OVER (PARTITION BY ibge ORDER BY v DESC, chave) <= 5 ORDER BY ibge, v DESC, chave""").fetchall():
        top[ibge].append([nome_limpo(nome), chave, round(valor), para])
    for ibge, n, total, *resto in por_cidade:
        faixas, (clientes, indireta, maquinas) = [int(x) for x in resto[:4]], resto[4:]
        mun["53" if ibge == "5300108" else ibge] = [n, int(total), faixas, clientes, int(indireta), int(maquinas), top.get(ibge, [])]
    totais = [v[1] for v in mun.values()]

    # Por empresa, desde 2020: a busca de /bndes e a ficha de /impostos/empresas.
    empresas = {}
    for chave, nome, uf, valor, abaixo, ult, direta in con.execute(f"""
            SELECT chave, first(nome ORDER BY valor DESC, nome), first(uf ORDER BY valor DESC, uf), sum(valor), coalesce(sum(abaixo), 0), max(ano), bool_or(direta)
              FROM cli WHERE ano >= {PRIMEIRO_ANO_EMPRESAS} GROUP BY chave HAVING sum(valor) >= 1e6 ORDER BY chave""").fetchall():
        empresas[chave] = [nome_limpo(nome), uf, round(valor), round(abaixo), ult, 1 if direta else 0]

    resumo = {
        "gerado": date.today().isoformat(), "fonte": FONTE, "ultima": ultima.isoformat(), "ano": ano,
        "serie": serie, "desembolso": desemb,
        "setores": [[k, NOMES_SETOR.get(k, k), int(v)] for k, v in setores],
        "programas_abaixo": [[k, int(v)] for k, v in programas],
        "maiores": maiores, "sem_nome": [sem_nome[0], int(sem_nome[1] or 0)],
        "diretas": int(diretas_ano), "sem_cidade": int(sem_cidade),
        "cidades": {"n": len(mun), "mediana": round(statistics.median(totais)) if totais else 0},
        "cruzamento": cruz,
        "osu": osu, "rtn": rtn, "sest": sest,
    }
    cidades = {"ano": ano, "fonte": FONTE, "mun": mun}
    doc_emp = {"desde": PRIMEIRO_ANO_EMPRESAS, "ate": ultima.isoformat(), "empresas": empresas}
    return resumo, cidades, doc_emp


SIGLAS = {"SA", "S/A", "LTDA", "ME", "EPP", "EIRELI", "BRF", "CCR", "EPR", "BRK"}
PEQUENAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "EM", "PARA", "A", "O"}


def nome_limpo(nome: str) -> str:
    """'CONCESSIONARIA ROTA DO OESTE S.A.' → 'Concessionaria Rota do Oeste S.A.'; tira a raiz que o BNDES põe no fim."""
    cortado = len((nome or "").rstrip()) >= 55   # o BNDES corta o nome em 55 letras
    s = re.sub(r"\s*\(\d+\)\s*$", "", re.sub(r"\s+", " ", nome or "")).strip()
    if s != s.upper():
        return s + ("…" if cortado else "")
    partes = []
    for i, p in enumerate(s.split(" ")):
        if p.rstrip(".") in ("S.A", "S/A", "SA", "S/A."):
            partes.append("S.A.")
        elif p in SIGLAS:
            partes.append("Ltda" if p == "LTDA" else p)
        elif i > 0 and p in PEQUENAS:
            partes.append(p.lower())
        else:
            partes.append(p.capitalize())
    return " ".join(partes) + ("…" if cortado else "")


# ---------------------------------------------------------------- main

def gravar(nome: str, doc: dict) -> None:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA / nome, REFERENCIA / ARQUIVOS[nome]):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {(SAIDA / nome).relative_to(RAIZ)} ({len(texto) / 1e3:,.0f} KB) e pipeline/referencia/{ARQUIVOS[nome]}")


def copiar_referencia() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, ref in ARQUIVOS.items():
        if (REFERENCIA / ref).exists():
            shutil.copyfile(REFERENCIA / ref, SAIDA / nome)
            print(f"saída: {(SAIDA / nome).relative_to(RAIZ)} (cópia de pipeline/referencia/{ref})")


def _tentar(nome: str, f):
    try:
        return f()
    except Exception as e:   # uma fonte fora do ar não derruba as outras; a página esconde a parte que faltar
        print(f"  {nome}: falhou ({e}); a parte fica de fora", flush=True)
        return None


def main() -> None:
    p = argparse.ArgumentParser(prog="bndes", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--receita", help="mês do cadastro de CNPJ, ex.: 2026-11 (padrão: o último)")
    p.add_argument("--sem-baixar", action="store_true", help="só copia as cópias versionadas para o site")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return

    print("BNDES: operações", flush=True)
    arqs = {}
    for nome, padrao in (("diretas", r"nao-automaticas\.csv$"), ("indiretas", r"indiretas-automaticas\.csv$")):
        url, tam = recurso_bndes("operacoes-financiamento", padrao)
        arqs[nome] = utf8(baixar(url, PASTA / f"operacoes-{nome}.csv", tam))
    con = duckdb.connect()
    ler_operacoes(con, arqs["diretas"], arqs["indiretas"])
    print(f"  {con.execute('SELECT count(*) FROM op').fetchone()[0]:,} operações", flush=True)
    mes = args.receita or ultimo_mes_receita()
    print(f"Receita: cadastro de CNPJ {mes}", flush=True)
    identificar(con, mes)
    desemb = desembolsos()
    osu = _tentar("Orçamento de Subsídios", subsidios_osu)
    rtn = _tentar("Resultado do Tesouro", resultado_tesouro)
    sest = _tentar("SEST", estatais_dependentes)
    resumo, cidades, empresas = montar(con, desemb, osu, rtn, sest)
    for nome, doc in (("resumo.json", resumo), ("cidades.json", cidades), ("empresas.json", empresas)):
        gravar(nome, doc)
    a = resumo["ano"]
    s = next(r for r in resumo["serie"] if r[0] == a)
    print(f"{a}: {_bi(s[1] + s[2])} contratados ({_bi(s[1])} diretos); abaixo do mercado {_bi(s[3])}, TLP {_bi(s[4])}, "
          f"mercado {_bi(s[5])}, doação {_bi(s[6])}; {resumo['cidades']['n']:,} cidades; {len(empresas['empresas']):,} empresas "
          f"desde {PRIMEIRO_ANO_EMPRESAS}; sem nome: {resumo['sem_nome'][0]:,} clientes, {_bi(resumo['sem_nome'][1])}")


if __name__ == "__main__":
    main()
