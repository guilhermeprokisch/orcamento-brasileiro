"""A página de cada político eleito (/politicos): o que custa e para onde manda dinheiro. Por ora, deputados federais e
senadores; o formato já tem lugar para os outros cargos (cada seção sem fonte diz o que falta).

    uv run politicos                  # baixa a cota, o gabinete e as emendas do ano; o TSE vem da cópia de referência
    uv run politicos --tse            # refaz também a parte das eleições (TSE 2018 e 2022, uns 2 GB, à mão)
    uv run politicos --sem-baixar     # só copia pipeline/referencia/politicos.json para o site

Fontes (levantamento em docs/levantamento-parlamentar.md):
- Câmara: a cota parlamentar (CEAP), um arquivo por ano (camara.leg.br/cotas/Ano-AAAA.csv.zip); a verba de gabinete,
  na página de cada deputado (camara.leg.br/deputados/{id}/verba-gabinete?ano=AAAA); os secretários parlamentares de
  hoje, no arquivo de funcionários dos dados abertos.
- Senado: a cota (CEAPS) na API de dados administrativos; a lista da legislatura (estado, partido, foto); os
  servidores de cada gabinete e escritório de apoio.
- CGU: as emendas pagas, do Parquet do explorador de emendas (data/publico/emendas-pagamentos.parquet, ou a cópia
  pública no bucket).
- TSE: candidaturas, bens declarados, receitas de campanha e votos de 2022 (e de 2018, para os senadores eleitos
  naquele ano).
- Receita Federal: a natureza jurídica dos fornecedores, para separar o empresário individual e o MEI.

Dados pessoais:
- O CPF nunca é guardado. A cota da Câmara traz o do deputado; o TSE, o do candidato. Os dois são casados só na
  memória (uma tabela temporária, apagada em seguida) e o que sai é o par "id da Câmara ↔ candidatura no TSE".
- Fornecedor pessoa física, empresário individual e MEI (natureza 213-5, ou o CPF no nome): só somados, sem nome.
- Doador de campanha pessoa física: só somado. Partido aparece com o nome.
- Bens: só o tipo e o valor, somados. A descrição de cada bem (texto livre, às vezes com endereço) não entra.
- Assessores: só a contagem por gabinete; nenhum nome.

Saída: site/public/data/politicos/politicos.json, com cópia em pipeline/referencia/politicos.json.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import html
import io
import json
import re
import shutil
import statistics
import time
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from .cidades import RAIZ

PASTA = RAIZ / "data" / "raw" / "politicos"
PASTA_TSE = RAIZ / "data" / "raw" / "tse"
PASTA_RECEITA = RAIZ / "data" / "raw" / "receita-federal"
SAIDA = RAIZ / "site" / "public" / "data" / "politicos" / "politicos.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "politicos.json"
EMENDAS_LOCAL = RAIZ / "data" / "publico" / "emendas-pagamentos.parquet"
EMENDAS_URL = "https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/explorador/emendas-pagamentos.parquet"

PRIMEIRO_ANO = 2023          # a legislatura atual
UA = "Mozilla/5.0 (orcamento-brasileiro; dados abertos)"

URL_COTA_CAMARA = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
URL_COTA_SENADO = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"
URL_SENADORES = "https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/57"
URL_FUNCIONARIOS_CAMARA = "https://dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv"
URL_DEPUTADOS = "https://dadosabertos.camara.leg.br/arquivos/deputados/csv/deputados.csv"
URL_SERVIDORES_SENADO = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/servidores/servidores"
URL_VERBA = "https://www.camara.leg.br/deputados/{id}/verba-gabinete?ano={ano}"
URL_TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele/{conjunto}/{conjunto}_{ano}.zip"
URL_TSE_CONTAS = "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip"

# Subsídio mensal de deputado federal e senador (Decreto Legislativo 172/2022): (desde, valor).
SUBSIDIO = [("2023-01", 39293.32), ("2023-04", 41650.92), ("2024-02", 44008.52), ("2025-02", 46366.19)]

# Teto mensal da cota da Câmara por estado: (desde, tabela). Ato da Mesa 270/2023 (anexo I) e Ato da Mesa 244/2026
# (IPCA de fev/2023 a dez/2025; tabela na página da Câmara para a imprensa).
TETO_CAMARA = [
    ("2023-02", {"AC": 50426.26, "AL": 46737.90, "AM": 49363.92, "AP": 49168.58, "BA": 44804.65, "CE": 48245.57,
                 "DF": 36582.46, "ES": 43217.71, "GO": 41300.86, "MA": 47945.49, "MG": 41886.51, "MS": 46336.64,
                 "MT": 45221.83, "PA": 48021.25, "PB": 47826.36, "PE": 47470.60, "PI": 46765.57, "PR": 44665.66,
                 "RJ": 41553.77, "RN": 48525.79, "RO": 49466.29, "RR": 51406.33, "RS": 46669.70, "SC": 45671.58,
                 "SE": 45933.06, "SP": 42837.33, "TO": 45297.41}),
    ("2026-02", {"AC": 57359.87, "AL": 53164.36, "AM": 56151.46, "AP": 55929.26, "BA": 50965.29, "CE": 54879.34,
                 "DF": 41612.55, "ES": 49160.15, "GO": 46979.73, "MA": 54537.99, "MG": 47645.91, "MS": 52707.93,
                 "MT": 51439.83, "PA": 54624.17, "PB": 54402.48, "PE": 53997.81, "PI": 53195.84, "PR": 50807.19,
                 "RJ": 47267.41, "RN": 55198.09, "RO": 56267.90, "RR": 58474.70, "RS": 53086.78, "SC": 51951.42,
                 "SE": 52248.86, "SP": 48727.46, "TO": 51525.80}),
]
MAX_SECRETARIOS = 25

UFS = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
       "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais",
       "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
       "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia",
       "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
       "TO": "Tocantins"}

# As categorias da cota, em nomes curtos. A chave é o começo do texto da fonte, sem acento e em minúsculas.
CATEGORIAS_CAMARA = [
    ("divulgacao", "Divulgação do mandato"), ("locacao ou fretamento de veiculos", "Aluguel de carro"),
    ("locacao ou fretamento de aeronaves", "Aluguel de avião"), ("locacao ou fretamento de embarcacoes", "Aluguel de barco"),
    ("manutencao de escritorio", "Escritório"), ("passage", "Passagens"), ("combustiveis", "Combustível"),
    ("hospedagem", "Hospedagem"), ("telefonia", "Telefone"), ("fornecimento de alimentacao", "Alimentação"),
    ("servico de seguranca", "Segurança"), ("servico de taxi", "Táxi, pedágio e estacionamento"),
    ("consultorias", "Consultorias"), ("complementacao do auxilio-moradia", "Complemento do auxílio-moradia"),
]
CATEGORIAS_SENADO = [
    ("locomocao", "Locomoção, hospedagem e combustível"), ("divulgacao", "Divulgação do mandato"),
    ("contratacao de consultorias", "Consultorias e assessorias"), ("passagens", "Passagens"),
    ("aluguel de imoveis", "Aluguel do escritório"), ("aquisicao de material", "Material de escritório"),
    ("servicos de seguranca", "Segurança"),
]

EMPRESARIO_INDIVIDUAL = "2135"
# Naturezas jurídicas que são uma pessoa só, com o nome dela: empresário individual e MEI (213-5), EIRELI (230-5 e
# 231-3) e sociedade unipessoal de advocacia (232-1). Entram somadas, sem nome. A sociedade limitada de um sócio só
# (206-2) não se distingue das outras limitadas sem o quadro de sócios: aparece com o nome, como empresa.
EMPRESA_DE_UMA_PESSOA = {EMPRESARIO_INDIVIDUAL, "2305", "2313", "2321"}
CPF_NO_NOME = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
MAX_FORNECEDORES = 8
MAX_LUGARES = 5
MAX_AREAS = 4
MESES_MINIMOS = 6     # para entrar na mediana do estado


# ---------------------------------------------------------------- utilidades

def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def slug(s: str) -> str:
    """O mesmo slug de fichas_emendas.slug (e da página das emendas): sem acento, minúsculas, hífens."""
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s).lower()).strip("-") or "sem-nome"


PEQUENAS = {"de", "da", "do", "das", "dos", "e"}


def nome_proprio(s: str, pessoa: bool = False) -> str:
    """"PLÍNIO VALÉRIO" → "Plínio Valério"; nomes já em caixa mista ficam como estão. Um nome curto em maiúsculas é
    sigla de empresa ("TAM", "GOL"), a não ser que seja de pessoa (pessoa=True: "ZEMA" → "Zema")."""
    s = " ".join((s or "").split())
    if s != s.upper() or (len(s) <= 4 and not pessoa):
        return s
    return " ".join(p.lower() if i and p.lower() in PEQUENAS else p.capitalize() for i, p in enumerate(s.split()))


def limpa_nome_empresa(s: str) -> str:
    """Tira do nome qualquer número que pareça CPF (o MEI costuma vir "FULANO DE TAL 12345678900")."""
    s = CPF_NO_NOME.sub("", s or "")
    s = re.sub(r"\d{11}", "", s)
    return " ".join(s.split()).strip(" -.,")


def categoria(texto: str, tabela: list[tuple[str, str]]) -> str:
    t = sem_acento(texto or "").lower().strip()
    for chave, nome in tabela:
        if t.startswith(chave):
            return nome
    return "Outros"


def tipo_fornecedor(doc: str, nome: str, natureza: dict[str, str]) -> str:
    """"empresa", "pessoa_empresa" (empresário individual e MEI) ou "pessoa" (CPF, ou documento mascarado)."""
    d = re.sub(r"\D", "", doc or "")
    if "*" in (doc or "") or len(d) == 11:
        return "pessoa"
    if len(d) != 14:
        return "outro"
    if natureza.get(d[:8]) in EMPRESA_DE_UMA_PESSOA or CPF_NO_NOME.search(nome or "") or re.search(r"\d{11}", nome or ""):
        return "pessoa_empresa"
    return "empresa"


def formata_cnpj(d: str) -> str:
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else d


def subsidio(mes: str) -> float:
    return [v for desde, v in SUBSIDIO if desde <= mes][-1]


def teto_camara(uf: str, mes: str) -> float | None:
    tabelas = [t for desde, t in TETO_CAMARA if desde <= mes]
    return tabelas[-1].get(uf) if tabelas else TETO_CAMARA[0][1].get(uf)


def abrir(url: str, tentativas: int = 6, timeout: int = 120, json_: bool = False):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Accept": "application/json"} if json_ else {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:   # noqa: BLE001 — rede instável: tenta de novo e, no fim, levanta
            if i == tentativas - 1:
                raise
            print(f"  {url}: {e}; tentando de novo", flush=True)
            time.sleep(5 * (i + 1))


def baixar(url: str, destino: Path, refazer: bool = False) -> Path:
    """Baixa para destino, a menos que já exista (refazer=True baixa de novo, para o ano corrente)."""
    if destino.exists() and not refazer:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r, tmp.open("wb") as f:
                shutil.copyfileobj(r, f, 8 << 20)
            tmp.replace(destino)
            return destino
        except Exception as e:   # noqa: BLE001
            if i == 3:
                raise
            print(f"  {url}: {e}; tentando de novo", flush=True)
            time.sleep(10 * (i + 1))
    return destino


def ano_corrente() -> int:
    return dt.date.today().year


def anos() -> list[int]:
    return list(range(PRIMEIRO_ANO, ano_corrente() + 1))


# ---------------------------------------------------------------- 1. cota da Câmara e do Senado

def carregar_cota_camara(con: duckdb.DuckDBPyConnection) -> None:
    """Tabela cam (sem o CPF do deputado) e a temporária cam_cpf (id → CPF), que só serve ao casamento com o TSE."""
    partes = []
    for ano in anos():
        z = PASTA / "camara" / f"Ano-{ano}.csv.zip"
        try:
            baixar(URL_COTA_CAMARA.format(ano=ano), z, refazer=ano >= ano_corrente() - 1)
        except Exception as e:   # noqa: BLE001
            if not z.exists():
                raise
            print(f"  cota da Câmara {ano}: {e}; fica a cópia baixada antes", flush=True)
        pasta = PASTA / "camara" / f"Ano-{ano}"
        with zipfile.ZipFile(z) as zf:
            nome = next(n for n in zf.namelist() if n.endswith(".csv"))
            zf.extract(nome, pasta)
        partes.append(pasta / nome)
    arqs = ", ".join(f"'{p}'" for p in partes)
    con.execute(f"""CREATE OR REPLACE TABLE cam_bruto AS SELECT * FROM read_csv([{arqs}], delim=';', header=true,
                    all_varchar=true, union_by_name=true)""")
    # O complemento do auxílio-moradia vem negativo em vlrLiquido, com o valor pago em vlrDocumento: usamos este.
    con.execute("""CREATE OR REPLACE TABLE cam AS SELECT ideCadastro AS id, txNomeParlamentar AS nome, sgUF AS uf,
                     sgPartido AS partido, txtDescricao AS cat, txtFornecedor AS forn,
                     regexp_replace(coalesce(txtCNPJCPF, ''), '[^0-9]', '', 'g') AS doc,
                     CASE WHEN txtDescricao ILIKE 'COMPLEMENTA%' THEN abs(TRY_CAST(vlrDocumento AS DOUBLE))
                          ELSE TRY_CAST(vlrLiquido AS DOUBLE) END AS v,
                     TRY_CAST(numAno AS INTEGER) AS ano, TRY_CAST(numMes AS INTEGER) AS mes
                   FROM cam_bruto WHERE coalesce(ideCadastro, '') <> '' AND sgUF <> 'NA'""")
    con.execute("""CREATE OR REPLACE TEMP TABLE cam_cpf AS SELECT DISTINCT ideCadastro AS id,
                     regexp_replace(cpf, '[^0-9]', '', 'g') AS cpf FROM cam_bruto
                   WHERE coalesce(ideCadastro, '') <> '' AND length(regexp_replace(cpf, '[^0-9]', '', 'g')) = 11""")
    con.execute("DROP TABLE cam_bruto")
    for p in partes:
        p.unlink(missing_ok=True)
    n = con.execute("SELECT count(*), count(DISTINCT id), sum(v) FROM cam").fetchone()
    print(f"cota da Câmara: {n[0]:,} notas, {n[1]} deputados, R$ {n[2] / 1e6:,.1f} mi", flush=True)


def carregar_cota_senado(con: duckdb.DuckDBPyConnection) -> None:
    arqs = []
    for ano in anos():
        destino = PASTA / "senado" / f"ceaps-{ano}.json"
        if not destino.exists() or ano >= ano_corrente() - 1:
            destino.parent.mkdir(parents=True, exist_ok=True)
            try:
                bruto = abrir(URL_COTA_SENADO.format(ano=ano), json_=True, timeout=300)
                json.loads(bruto)   # a API às vezes corta a resposta: só grava se o JSON estiver inteiro
                destino.write_bytes(bruto)
            except Exception as e:   # noqa: BLE001
                if not destino.exists():
                    raise
                print(f"  cota do Senado {ano}: {e}; fica a cópia baixada antes", flush=True)
        arqs.append(f"'{destino}'")
    con.execute(f"""CREATE OR REPLACE TABLE sen AS SELECT codSenador::VARCHAR AS id, nomeSenador AS nome,
                     tipoDespesa AS cat, fornecedor AS forn, coalesce(cpfCnpj, '') AS doc_bruto,
                     regexp_replace(coalesce(cpfCnpj, ''), '[^0-9]', '', 'g') AS doc,
                     valorReembolsado::DOUBLE AS v, ano::INTEGER AS ano, mes::INTEGER AS mes
                   FROM read_json([{", ".join(arqs)}], format='array', union_by_name=true)""")
    n = con.execute("SELECT count(*), count(DISTINCT id), sum(v) FROM sen").fetchone()
    print(f"cota do Senado: {n[0]:,} notas, {n[1]} senadores, R$ {n[2] / 1e6:,.1f} mi", flush=True)


def senadores() -> dict[str, dict]:
    """Código do senador → nome, nome completo, estado, partido, sexo e foto (legislatura 57, com os suplentes)."""
    lista = []
    for leg in ("56", "57"):   # a 56 só para quem saiu em janeiro de 2023; a 57 sobrescreve
        d = json.loads(abrir(URL_SENADORES.replace("/57", f"/{leg}"), json_=True))
        lista += d["ListaParlamentarLegislatura"]["Parlamentares"]["Parlamentar"]
    saida = {}
    for p in lista:
        i = p["IdentificacaoParlamentar"]
        mandatos = p.get("Mandatos", {}).get("Mandato") or []
        if isinstance(mandatos, dict):
            mandatos = [mandatos]
        uf = i.get("UfParlamentar") or next((m.get("UfParlamentar") for m in mandatos if m.get("UfParlamentar")), None)
        saida[i["CodigoParlamentar"]] = {
            "nome": i.get("NomeParlamentar"), "completo": i.get("NomeCompletoParlamentar"), "uf": uf,
            "partido": i.get("SiglaPartidoParlamentar"), "sexo": i.get("SexoParlamentar"),
            "foto": (i.get("UrlFotoParlamentar") or "").replace("http://", "https://"),
            "titular": any(m.get("DescricaoParticipacao") == "Titular" for m in mandatos),
        }
    return saida


# ---------------------------------------------------------------- 2. natureza jurídica dos fornecedores

def natureza_fornecedores(raizes: set[str], completa: bool) -> dict[str, str]:
    """Raiz do CNPJ → natureza jurídica. Cache em data/raw/receita-federal/natureza-politicos.csv. Com completa=True,
    as raízes que faltam são procuradas nos arquivos Empresas da Receita (~1,3 GB, um por vez, apagados depois); sem,
    a raiz que falta fica sem natureza (e o nome com CPF ainda a marca como pessoa)."""
    cache = PASTA_RECEITA / "natureza-politicos.csv"
    nat: dict[str, str] = {}
    if cache.exists():
        with cache.open(encoding="utf-8") as f:
            nat = {r[0]: r[1] for r in csv.reader(f, delimiter=";") if len(r) == 2}
    # Aproveita o cache de outros passos (benefícios fiscais, dívida ativa), que tem o mesmo formato.
    for outro in PASTA_RECEITA.glob("natureza-20*.csv"):
        with outro.open(encoding="utf-8") as f:
            for r in csv.reader(f, delimiter=";"):
                if len(r) == 2 and r[0] in raizes:
                    nat.setdefault(r[0], r[1])
    faltam = raizes - set(nat)
    print(f"natureza jurídica: {len(raizes) - len(faltam):,} de {len(raizes):,} fornecedores no cache", flush=True)
    if faltam and completa:
        from .divida_ativa import URL_RECEITA, _baixar, ultimo_mes_receita
        tmp = PASTA_RECEITA / "cnpj-tmp"
        try:
            mes = ultimo_mes_receita()
            for i in range(10):
                arq = _baixar(f"{URL_RECEITA}{mes}/Empresas{i}.zip", tmp / f"Empresas{i}.zip", receita=True)
                with zipfile.ZipFile(arq) as z:
                    for membro in z.namelist():
                        for r in csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";"):
                            if r and r[0] in faltam:
                                nat[r[0]] = r[2]
                arq.unlink()
                print(f"  Empresas{i}: {len(nat):,} raízes com natureza", flush=True)
        except Exception as e:   # noqa: BLE001 — a Receita fora do ar não impede a carga: segue com o cache
            print(f"natureza jurídica: a Receita falhou ({e}); segue com o que já estava no cache", flush=True)
            shutil.rmtree(tmp, ignore_errors=True)
    PASTA_RECEITA.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";").writerows(sorted((k, v) for k, v in nat.items() if k in raizes))
    return nat


# ---------------------------------------------------------------- 3. gabinete

def verba_gabinete(ids: list[str]) -> dict[tuple[str, int], dict]:
    """(id, ano) → {"gasto", "disponivel", "meses"}, lido da página de cada deputado. Anos fechados ficam em cache."""
    pasta = PASTA / "verba-gabinete"
    pasta.mkdir(parents=True, exist_ok=True)

    def um(id_: str, ano: int):
        arq = pasta / f"{id_}-{ano}.json"
        if arq.exists() and ano < ano_corrente():
            return (id_, ano), json.loads(arq.read_text(encoding="utf-8"))
        try:
            t = abrir(URL_VERBA.format(id=id_, ano=ano), tentativas=3, timeout=60).decode("utf-8", "replace")
        except Exception as e:   # noqa: BLE001
            print(f"  verba de gabinete {id_}/{ano}: {e}", flush=True)
            return (id_, ano), None
        m = re.search(r"<table.*?</table>", t, re.S)
        meses = []
        for linha in re.findall(r"<tr.*?</tr>", m.group(0) if m else "", re.S):
            cel = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)]
            if len(cel) >= 3 and cel[0].isdigit():
                num = lambda s: float(s.replace(".", "").replace(",", ".")) if re.match(r"^[\d.]+,\d{2}$", s) else 0.0
                meses.append([int(cel[0]), num(cel[1]), num(cel[2])])
        r = {"meses": len([x for x in meses if x[2] > 0]), "disponivel": round(sum(x[1] for x in meses), 2),
             "gasto": round(sum(x[2] for x in meses), 2)}
        arq.write_text(json.dumps(r), encoding="utf-8")
        return (id_, ano), r

    pedidos = [(i, a) for i in ids for a in anos()]
    saida = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for k, r in ex.map(lambda p: um(*p), pedidos):
            if r and r["gasto"] > 0:
                saida[k] = r
    print(f"verba de gabinete: {len(saida):,} deputado-anos com gasto", flush=True)
    return saida


def assessores_camara(nomes: dict[str, str]) -> dict[str, int]:
    """id do deputado → secretários parlamentares hoje. A lotação é "GAB. 4/848 - TABATA AMARAL"; casa pelo slug do nome."""
    arq = baixar(URL_FUNCIONARIOS_CAMARA, PASTA / "camara" / "funcionarios.csv", refazer=True)
    conta: Counter[str] = Counter()
    with arq.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r.get("grupo") == "Secretário Parlamentar" and " - " in (r.get("lotacao") or ""):
                conta[slug(r["lotacao"].split(" - ", 1)[1])] += 1
    por_slug: dict[str, list[str]] = defaultdict(list)
    for id_, nome in nomes.items():
        por_slug[slug(nome)].append(id_)
    saida = {}
    for s, n in conta.items():
        if len(por_slug.get(s, [])) == 1:
            saida[por_slug[s][0]] = n
    arq.unlink(missing_ok=True)   # tem nomes de servidores: não fica no disco
    print(f"assessores da Câmara: {len(saida)} gabinetes casados de {len(conta)}", flush=True)
    return saida


def assessores_senado(sens: dict[str, dict]) -> dict[str, int]:
    """código do senador → servidores ativos no gabinete e nos escritórios de apoio dele."""
    lista = json.loads(abrir(URL_SERVIDORES_SENADO, json_=True, timeout=300))
    conta: Counter[str] = Counter()
    for s in lista:
        lot = ((s.get("lotacao") or {}).get("nome") or "").strip()
        if s.get("situacao") != "ATIVO" or s.get("vinculo") == "PARLAMENTAR":
            continue
        m = re.match(r"^(?:Gabinete|Escrit[óo]rio de Apoio.*?)\s+d[oa] Senador[a]?\s+(.+)$", lot)
        if m:
            conta[slug(m.group(1))] += 1
    por_slug: dict[str, list[str]] = defaultdict(list)
    for cod, s in sens.items():
        por_slug[slug(s["nome"] or "")].append(cod)
    saida = {por_slug[k][0]: n for k, n in conta.items() if len(por_slug.get(k, [])) == 1}
    print(f"assessores do Senado: {len(saida)} gabinetes casados de {len(conta)}", flush=True)
    return saida


# ---------------------------------------------------------------- 4. emendas

def emendas(con: duckdb.DuckDBPyConnection) -> dict[str, dict[int, dict]]:
    """autor (como no explorador) → ano → resumo das emendas individuais pagas. O ranking é entre os parlamentares."""
    if EMENDAS_LOCAL.exists():
        fonte = f"'{EMENDAS_LOCAL}'"
    else:
        con.execute("INSTALL httpfs; LOAD httpfs")
        fonte = f"'{EMENDAS_URL}'"
    con.execute(f"""CREATE OR REPLACE TABLE em AS SELECT autor, ano, tipo, municipio, uf, ibge,
                      coalesce(nullif(area, ''), 'Sem área') AS area, valor
                    FROM read_parquet({fonte})
                    WHERE ano >= {PRIMEIRO_ANO} AND autor IS NOT NULL
                      AND NOT regexp_matches(autor, '^(Bancada|Comissão|Relator)')""")
    saida: dict[str, dict[int, dict]] = defaultdict(dict)
    tot = con.execute("""SELECT autor, ano, sum(valor) AS v,
                           count(DISTINCT coalesce(nullif(ibge, ''), municipio || uf))::INTEGER AS lugares,
                           sum(CASE WHEN tipo = 'Pix' THEN valor ELSE 0 END) AS pix,
                           rank() OVER (PARTITION BY ano ORDER BY sum(valor) DESC)::INTEGER AS posicao,
                           count(*) OVER (PARTITION BY ano)::INTEGER AS de
                         FROM em GROUP BY autor, ano""").fetchall()
    for autor, ano, v, lugares, pix, posicao, de in tot:
        saida[autor][ano] = {"total": round(v), "lugares": lugares, "pix": round(pix), "posicao": posicao, "de": de,
                             "onde": [], "area": []}
    for autor, ano, mun, uf, ibge, v in con.execute(f"""
            SELECT autor, ano, municipio, uf, ibge, v FROM (
              SELECT autor, ano, any_value(municipio) AS municipio, any_value(uf) AS uf, nullif(ibge, '') AS ibge,
                     sum(valor) AS v, row_number() OVER (PARTITION BY autor, ano ORDER BY sum(valor) DESC) AS n
              FROM em GROUP BY autor, ano, coalesce(nullif(ibge, ''), municipio || uf), nullif(ibge, ''))
            WHERE n <= {MAX_LUGARES} ORDER BY autor, ano, v DESC""").fetchall():
        saida[autor][ano]["onde"].append([mun or "Sem lugar", uf or "", ibge, round(v)])
    for autor, ano, area, v in con.execute(f"""
            SELECT autor, ano, area, v FROM (
              SELECT autor, ano, area, sum(valor) AS v, row_number() OVER (PARTITION BY autor, ano ORDER BY sum(valor) DESC) AS n
              FROM em GROUP BY autor, ano, area) WHERE n <= {MAX_AREAS} ORDER BY autor, ano, v DESC""").fetchall():
        saida[autor][ano]["area"].append([area, round(v)])
    print(f"emendas: {len(saida):,} autores individuais desde {PRIMEIRO_ANO}", flush=True)
    return saida


# ---------------------------------------------------------------- 5. TSE

def _tse_zip(conjunto: str, ano: int) -> Path:
    return baixar(URL_TSE.format(conjunto=conjunto, ano=ano), PASTA_TSE / f"{conjunto}_{ano}.zip")


def _csv_do_zip(z: Path, membro: str, destino: Path) -> Path:
    """Extrai um CSV do TSE já em UTF-8 (o DuckDB recusa alguns bytes do Latin-1 deles)."""
    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / membro
    with zipfile.ZipFile(z) as zf, zf.open(membro) as ent, saida.open("w", encoding="utf-8", newline="") as sai:
        for linha in io.TextIOWrapper(ent, encoding="latin-1", newline=""):
            sai.write(linha)
    return saida


CARGOS_TSE = ("DEPUTADO FEDERAL", "SENADOR", "1º SUPLENTE", "2º SUPLENTE")
# Os cargos que só têm a página pelo TSE (por ora): eleitos de 2022 para o estado.
CARGOS_ESTADUAIS = ("GOVERNADOR", "DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")
CASA_DO_CARGO = {"GOVERNADOR": "governo", "DEPUTADO ESTADUAL": "assembleia", "DEPUTADO DISTRITAL": "assembleia"}
MAX_CIDADES_VOTOS = 5


def tse(con: duckdb.DuckDBPyConnection, sens: dict[str, dict]) -> dict[str, dict]:
    """chave do político → a candidatura que o levou ao cargo, com votos, bens e receitas.
    - "camara-<id>": deputados federais, casados pelo CPF (só na memória);
    - "senado-<cod>": senadores, pelo nome completo e o estado;
    - "tse-<SQ_CANDIDATO>": governadores, deputados estaduais e distritais eleitos em 2022, que (por ora) só têm a
      página pelo TSE. A chave é o número da candidatura no TSE, nunca o CPF. Esses levam também o nome completo
      (para ligar à página da Câmara ou do Senado da mesma pessoa) e as cidades onde tiveram mais votos."""
    tmp = PASTA_TSE / "tmp"
    cand_partes = []
    for ano in (2018, 2022):
        z = _tse_zip("consulta_cand", ano)
        arq = _csv_do_zip(z, f"consulta_cand_{ano}_BRASIL.csv", tmp)
        cargos = CARGOS_TSE + (CARGOS_ESTADUAIS if ano == 2022 else ())
        cand_partes.append(f"""SELECT {ano} AS eleicao, SQ_CANDIDATO AS sq, SG_UF AS uf, DS_CARGO AS cargo,
              NM_CANDIDATO AS completo, NM_URNA_CANDIDATO AS urna, regexp_replace(NR_CPF_CANDIDATO, '[^0-9]', '', 'g') AS cpf,
              SG_PARTIDO AS partido, DS_GENERO AS genero, DS_SIT_TOT_TURNO AS situacao, TRY_CAST(NR_TURNO AS INTEGER) AS turno
            FROM read_csv('{arq}', delim=';', header=true, all_varchar=true)
            WHERE DS_CARGO IN {cargos}""")
    con.execute(f"CREATE OR REPLACE TEMP TABLE cand AS {' UNION ALL '.join(cand_partes)}")
    # Câmara: pelo CPF; o par sai sem ele.
    # Um CPF pode ter mais de uma linha (candidatura substituída, recurso): fica a que se elegeu, senão a mais votada
    # na totalização (a de situação final), senão a primeira.
    con.execute("""CREATE OR REPLACE TEMP TABLE par AS
                   SELECT 'camara-' || c.id AS chave,
                          arg_max(k.sq, (k.situacao ILIKE 'ELEITO%')::INTEGER * 2 + (k.situacao ILIKE 'SUPLENTE%')::INTEGER) AS sq,
                          2022 AS eleicao
                   FROM cam_cpf c JOIN cand k ON k.cpf = c.cpf AND k.cargo = 'DEPUTADO FEDERAL' AND k.eleicao = 2022
                   GROUP BY 1""")
    con.execute("DROP TABLE cam_cpf")
    con.execute("ALTER TABLE cand DROP COLUMN cpf")
    # Senado: nome completo e estado; senão, nome parlamentar e nome de urna.
    linhas = con.execute(f"""SELECT sq, eleicao, uf, cargo, completo, urna FROM cand
                            WHERE cargo <> 'DEPUTADO FEDERAL' AND cargo NOT IN {CARGOS_ESTADUAIS}
                              AND (situacao ILIKE 'ELEITO%' OR cargo LIKE '%SUPLENTE')""").fetchall()
    por_completo, por_urna = defaultdict(list), defaultdict(list)
    for sq, eleicao, uf, cargo, completo, urna in linhas:
        por_completo[(slug(completo), uf)].append((eleicao, sq))
        por_urna[(slug(urna), uf)].append((eleicao, sq))
    pares_sen = []
    for cod, s in sens.items():
        achados = por_completo.get((slug(s["completo"] or ""), s["uf"])) or por_urna.get((slug(s["nome"] or ""), s["uf"]))
        if achados:
            eleicao, sq = max(achados)
            pares_sen.append((f"senado-{cod}", sq, eleicao))
    if pares_sen:
        con.executemany("INSERT INTO par VALUES (?, ?, ?)", pares_sen)
    print(f"TSE: {con.execute('SELECT count(*) FROM par').fetchone()[0]} políticos casados com a candidatura", flush=True)
    # Governadores e deputados estaduais e distritais eleitos em 2022: a página é a candidatura.
    con.execute(f"""INSERT INTO par SELECT DISTINCT 'tse-' || sq, sq, 2022 FROM cand
                    WHERE eleicao = 2022 AND cargo IN {CARGOS_ESTADUAIS} AND situacao ILIKE 'ELEITO%'""")
    for cargo, n in con.execute("""SELECT k.cargo, count(DISTINCT p.sq) FROM par p JOIN cand k USING (sq)
                                   WHERE p.chave LIKE 'tse-%' GROUP BY 1 ORDER BY 1""").fetchall():
        print(f"TSE: {n} eleitos para {cargo.lower()} em 2022", flush=True)

    sqs = {sq for (sq,) in con.execute("SELECT sq FROM par").fetchall()}
    # Bens: só o tipo e o valor.
    bens: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "tipos": Counter()})
    for ano in (2018, 2022):
        arq = _csv_do_zip(_tse_zip("bem_candidato", ano), f"bem_candidato_{ano}_BRASIL.csv", tmp)
        for sq, tipo_, v in con.execute(f"""SELECT SQ_CANDIDATO, DS_TIPO_BEM_CANDIDATO,
                    TRY_CAST(replace(VR_BEM_CANDIDATO, ',', '.') AS DOUBLE)
                FROM read_csv('{arq}', delim=';', header=true, all_varchar=true)""").fetchall():
            if sq in sqs and v:
                bens[sq]["total"] += v
                bens[sq]["tipos"][nome_bem(tipo_)] += v
    # Receitas: por origem; partidos pelo nome; pessoa física só somada.
    receitas: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "origens": Counter(), "partidos": Counter(), "pf": [0, 0.0]})
    for ano in (2018, 2022):
        z = baixar(URL_TSE_CONTAS.format(ano=ano), PASTA_TSE / f"prestacao_de_contas_eleitorais_candidatos_{ano}.zip")
        arq = _csv_do_zip(z, f"receitas_candidatos_{ano}_BRASIL.csv", tmp)
        con.execute(f"CREATE OR REPLACE TEMP TABLE alvo AS SELECT unnest(?::VARCHAR[]) AS sq", [list(sqs)])
        for sq, fonte, origem, doc, doador, v in con.execute(f"""
                SELECT r.SQ_CANDIDATO, r.DS_FONTE_RECEITA, r.DS_ORIGEM_RECEITA,
                       regexp_replace(r.NR_CPF_CNPJ_DOADOR, '[^0-9]', '', 'g'),
                       CASE WHEN r.SG_PARTIDO_DOADOR NOT LIKE '#NULO%' AND r.DS_ESFERA_PARTIDARIA_DOADOR NOT LIKE '#NULO%'
                            THEN r.SG_PARTIDO_DOADOR || ', direção ' || CASE WHEN r.DS_ESFERA_PARTIDARIA_DOADOR ILIKE '%estadual%' THEN 'estadual' ELSE lower(r.DS_ESFERA_PARTIDARIA_DOADOR) END
                            ELSE r.NM_DOADOR END,
                       TRY_CAST(replace(r.VR_RECEITA, ',', '.') AS DOUBLE)
                FROM read_csv('{arq}', delim=';', header=true, all_varchar=true) r
                JOIN alvo a ON a.sq = r.SQ_CANDIDATO""").fetchall():
            if not v:
                continue
            g = grupo_receita(fonte, origem)
            rc = receitas[sq]
            rc["total"] += v
            rc["origens"][g] += v
            if g == "Pessoas físicas":
                rc["pf"][0] += 1
                rc["pf"][1] += v
            elif "partido" in (origem or "").lower() and len(doc) == 14:
                rc["partidos"][doador if "," in (doador or "") else nome_proprio(doador)] += v
        arq.unlink(missing_ok=True)
    # Votos: a soma das zonas, no primeiro turno (e no segundo, para governador). Para os cargos estaduais, também
    # as cidades com mais votos e a parte dos votos que veio de cada uma.
    votos: Counter[str] = Counter()
    votos2: Counter[str] = Counter()
    cidades: dict[str, Counter] = defaultdict(Counter)
    estaduais = {sq for (sq,) in con.execute("SELECT sq FROM par WHERE chave LIKE 'tse-%'").fetchall()}
    cargos_votos = ", ".join(f"'{c}'" for c in ("DEPUTADO FEDERAL", "SENADOR") + CARGOS_ESTADUAIS)
    for ano in (2018, 2022):
        z = _tse_zip("votacao_candidato_munzona", ano)
        with zipfile.ZipFile(z) as zf:
            # Um arquivo por estado. O _BRASIL.csv repete todos os estados juntos (somar os dois dobra os votos) e
            # o _BR.csv tem a votação para presidente: os dois ficam de fora.
            membros = arquivos_de_votos(zf.namelist())
        for membro in membros:
            arq = _csv_do_zip(z, membro, tmp)
            for sq, turno, cod, mun, uf, v in con.execute(f"""SELECT SQ_CANDIDATO, NR_TURNO, CD_MUNICIPIO, any_value(NM_MUNICIPIO),
                        any_value(SG_UF), sum(TRY_CAST(QT_VOTOS_NOMINAIS AS BIGINT))
                    FROM read_csv('{arq}', delim=';', header=true, all_varchar=true)
                    WHERE upper(DS_CARGO) IN ({cargos_votos})
                    GROUP BY 1, 2, 3""").fetchall():
                if sq not in sqs:
                    continue
                if turno == "1":
                    votos[sq] += int(v or 0)
                    if sq in estaduais:
                        cidades[sq][(cod, mun, uf)] += int(v or 0)
                else:
                    votos2[sq] += int(v or 0)
            arq.unlink(missing_ok=True)
    saida = {}
    for chave, sq, eleicao in con.execute("""SELECT p.chave, p.sq, p.eleicao FROM par p""").fetchall():
        k = con.execute("SELECT cargo, uf, partido, genero, situacao, urna, completo FROM cand WHERE sq = ? ORDER BY turno DESC LIMIT 1", [sq]).fetchone()
        b, r = bens.get(sq), receitas.get(sq)
        saida[chave] = {
            "eleicao": eleicao, "cargo": k[0].title().replace("º Suplente", "º suplente"), "uf": k[1], "partido": k[2],
            "genero": k[3], "situacao": situacao_tse(k[4]), "urna": nome_proprio(k[5], pessoa=True), "votos": votos.get(sq),
            "bens": {"total": round(b["total"]), "tipos": [[t, round(v)] for t, v in b["tipos"].most_common(5)]} if b else None,
            "receitas": {"total": round(r["total"]), "origens": [[o, round(v)] for o, v in r["origens"].most_common()],
                         "partidos": [[p, round(v)] for p, v in r["partidos"].most_common(3)],
                         "pf": [r["pf"][0], round(r["pf"][1])]} if r else None,
        }
        if chave.startswith("tse-"):
            e = saida[chave]
            e["sq"] = sq
            e["completo"] = k[6]   # o nome completo, que o TSE publica: liga à página da Câmara ou do Senado
            if votos2.get(sq):
                e["votos2"] = votos2[sq]
            tot = votos.get(sq) or 0
            e["cidades"] = [[nome_proprio(mun), uf, cod, v, round(v / tot, 4) if tot else 0]
                            for (cod, mun, uf), v in cidades[sq].most_common(MAX_CIDADES_VOTOS)]
            e["nCidades"] = sum(1 for v in cidades[sq].values() if v > 0)
    # A posição de cada eleito estadual entre os eleitos do mesmo cargo e estado, pelos votos do 1º turno.
    grupos: dict[tuple, list] = defaultdict(list)
    for chave, e in saida.items():
        if chave.startswith("tse-") and e["cargo"] != "Governador":
            grupos[(e["cargo"], e["uf"])].append(e)
    for lista in grupos.values():
        lista.sort(key=lambda e: -(e["votos"] or 0))
        for i, e in enumerate(lista):
            e["posicao"] = [i + 1, len(lista)]
    shutil.rmtree(tmp, ignore_errors=True)
    return saida


def arquivos_de_votos(nomes: list[str]) -> list[str]:
    """Os CSVs de votação por estado (votacao_candidato_munzona_AAAA_SP.csv), sem o _BR e o _BRASIL."""
    return [n for n in nomes if re.search(r"_[A-Z]{2}\.csv$", n) and not n.endswith("_BR.csv")]


def nome_bem(t: str) -> str:
    t = (t or "").strip()
    s = sem_acento(t).lower()
    if "quota" in s or "participac" in s or re.search(r"\bacoes\b", s):
        return "Participação em empresas"
    if s.startswith(("casa", "apartamento", "terreno", "predio", "sala", "loja", "outros bens imoveis", "galpao", "construcao",
                     "terra nua", "benfeitoria")) or "imovel" in s or "rural" in s:
        return "Imóveis"
    if "veiculo" in s or "aeronave" in s or "embarcac" in s:
        return "Veículos"
    if ("deposito" in s or "poupanca" in s or "aplicac" in s or "fundo" in s or "dinheiro" in s or "titulo" in s
            or "renda fixa" in s or "previdencia" in s or "vgbl" in s or "pgbl" in s or "investimento" in s
            or s.startswith("ouro") or "cripto" in s):
        return "Dinheiro e aplicações"
    if "credito" in s or "emprestimo" in s:
        return "Créditos a receber"
    return "Outros bens"


def grupo_receita(fonte: str | None, origem: str | None) -> str:
    f, o = sem_acento(fonte or "").lower(), sem_acento(origem or "").lower()
    if "fundo especial" in f:
        return "Fundo eleitoral"
    if "fundo partidario" in f:
        return "Fundo partidário"
    if "pessoas fisicas" in o or "financiamento coletivo" in o:
        return "Pessoas físicas"
    if "proprios" in o:
        return "Recursos próprios"
    if "partido" in o:
        return "Partido (outros recursos)"
    if "outros candidatos" in o:
        return "Outros candidatos"
    return "Outras origens"


def situacao_tse(s: str) -> str:
    return {"ELEITO": "eleito", "ELEITO POR QP": "eleito por QP", "ELEITO POR MÉDIA": "eleito por média",
            "SUPLENTE": "suplente", "NÃO ELEITO": "não eleito"}.get((s or "").upper(), (s or "").lower())


# ---------------------------------------------------------------- 6. montagem

def resumo_cota(con, tabela: str, id_: str, ano: int, cats: list[tuple[str, str]], nat: dict[str, str]) -> dict | None:
    linhas = con.execute(f"SELECT cat, forn, doc{', doc_bruto' if tabela == 'sen' else ''}, v, mes FROM {tabela} WHERE id = ? AND ano = ?", [id_, ano]).fetchall()
    if not linhas:
        return None
    por_cat: Counter[str] = Counter()
    por_mes = [0.0] * 12
    empresas: dict[str, list] = {}
    nomes_emp: dict[str, Counter] = defaultdict(Counter)
    cat_emp: dict[str, Counter] = defaultdict(Counter)
    grupos = {"pessoa_empresa": [set(), 0.0], "pessoa": [0, 0.0], "outro": [0, 0.0]}
    for linha in linhas:
        cat, forn, doc = linha[0], linha[1], linha[2]
        bruto = linha[3] if tabela == "sen" else doc
        v, mes = linha[-2], linha[-1]
        if v is None:
            continue
        c = categoria(cat, cats)
        por_cat[c] += v
        if mes and 1 <= mes <= 12:
            por_mes[mes - 1] += v
        tipo_ = tipo_fornecedor(bruto, forn, nat)
        if tipo_ == "empresa":
            empresas[doc] = empresas.get(doc, 0.0) + v
            nomes_emp[doc][limpa_nome_empresa(forn)] += 1
            cat_emp[doc][c] += v
        elif tipo_ == "pessoa_empresa":
            grupos["pessoa_empresa"][0].add(doc)
            grupos["pessoa_empresa"][1] += v
        else:
            grupos[tipo_][0] += 1
            grupos[tipo_][1] += v
    total = sum(por_cat.values())
    meses = sum(1 for x in por_mes if abs(x) > 0.005)
    maiores = sorted(empresas.items(), key=lambda kv: -kv[1])[:MAX_FORNECEDORES]
    return {
        "total": round(total), "meses": meses, "porMes": round(total / meses) if meses else 0,
        "categorias": [[c, round(v)] for c, v in por_cat.most_common() if round(v)],
        "mes": [round(x) for x in por_mes],
        "fornecedores": [[nome_proprio(nomes_emp[d].most_common(1)[0][0]), formata_cnpj(d),
                          cat_emp[d].most_common(1)[0][0], round(v)] for d, v in maiores],
        "pessoaEmpresa": [len(grupos["pessoa_empresa"][0]), round(grupos["pessoa_empresa"][1])],
        "pessoas": [grupos["pessoa"][0], round(grupos["pessoa"][1])],
        "semDocumento": round(grupos["outro"][1]),
    }


def salario_do_ano(ano: int, meses: int) -> int:
    """Aproximado: os meses com despesa na cota como meses no cargo, o subsídio de cada mês, mais 13º e 1/3 de férias
    proporcionais."""
    if not meses:
        return 0
    ate = 12 if ano < ano_corrente() else dt.date.today().month
    valores = [subsidio(f"{ano}-{m:02d}") for m in range(1, ate + 1)][-meses:]
    base = sum(valores)
    return round(base + (valores[-1] * (1 + 1 / 3)) * meses / 12)


def nomes_civis_camara() -> dict[str, str]:
    """id do deputado → nome civil (o arquivo de deputados dos dados abertos; a coluna de CPF vem vazia e não é lida)."""
    arq = baixar(URL_DEPUTADOS, PASTA / "camara" / "deputados.csv", refazer=True)
    saida = {}
    with arq.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            id_ = (r.get("uri") or "").rstrip("/").rsplit("/", 1)[-1]
            if id_ and r.get("nomeCivil"):
                saida[id_] = r["nomeCivil"]
    return saida


def periodo(p: dict) -> tuple[int, int] | None:
    """(primeiro, último) mês com despesa na cota, como AAAAMM."""
    meses = [int(a) * 100 + i + 1 for a, x in p["anos"].items() for i, v in enumerate((x.get("cota") or {}).get("mes", [])) if abs(v) > 0]
    return (min(meses), max(meses)) if meses else None


MES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_periodo(per: tuple[int, int] | None) -> str | None:
    """"jan/2023", "fev/2023 a out/2026"."""
    if not per:
        return None
    f = lambda m: f"{MES_CURTO[m % 100 - 1]}/{m // 100}"
    return f(per[0]) if per[0] == per[1] else f"{f(per[0])} a {f(per[1])}"


def ligar_mesma_pessoa(politicos: list[dict], completos: dict[str, str]) -> None:
    """Quem passou pelas duas Casas (deputado até janeiro de 2023 e senador depois, ou o contrário) tem uma página
    por cargo. Aqui as páginas da mesma pessoa se ligam: mesmo estado e mesmo nome completo (o nome civil na Câmara,
    o nome completo no Senado). Dois deputados com o mesmo nome parlamentar (pai e filho, por exemplo) não se juntam:
    só pessoas de Casas diferentes. Cada página ganha "outros" (os outros cargos) e "atual" (se é o cargo mais
    recente); a lista mostra só a atual."""
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for p in politicos:
        p["atual"] = True
        p["outros"] = []
        completo = completos.get(p["chave"])
        if completo:
            grupos[(p["uf"], slug(completo))].append(p)
    for membros in grupos.values():
        if len({m["casa"] for m in membros}) < 2:
            continue
        membros.sort(key=lambda m: (periodo(m) or (0, 0))[1])
        atual = membros[-1]
        if any(m["feminino"] for m in membros):   # o gênero vem do TSE ou do Senado; a página antiga pode não ter
            for m in membros:
                m["feminino"] = True
                m["cargo"] = {"Deputado federal": "Deputada federal", "Senador": "Senadora"}.get(m["cargo"], m["cargo"])
        for m in membros:
            m["atual"] = m is atual
            if m is not atual:
                # A página do cargo antigo fica com os anos desse cargo e sem as emendas, que são da pessoa e já
                # estão na página atual (o autor é o mesmo nas duas).
                m["anos"] = {a: {k: v for k, v in x.items() if k != "emendas"} for a, x in m["anos"].items() if x.get("cota")}
                m["autor"] = None
            m["outros"] = [{"chave": o["chave"], "cargo": o["cargo"], "periodo": rotulo_periodo(periodo(o)), "atual": o is atual}
                           for o in membros if o is not m]
    n = sum(1 for p in politicos if not p["atual"])
    print(f"mesma pessoa em duas Casas: {n} páginas de cargo antigo ligadas à atual", flush=True)


def montar(con, tse_dados: dict, com_verba: bool, completa: bool) -> dict:
    sens = senadores()
    # Nome, estado e partido mais recentes de cada deputado.
    deps = {id_: {"nome": n, "uf": uf, "partido": p} for id_, n, uf, p in con.execute("""
        SELECT id, arg_max(nome, ano * 100 + mes), arg_max(uf, ano * 100 + mes), arg_max(partido, ano * 100 + mes)
        FROM cam GROUP BY id""").fetchall()}
    sen_ids = [r[0] for r in con.execute("SELECT DISTINCT id FROM sen").fetchall()]

    raizes = {d[:8] for (d,) in con.execute("SELECT DISTINCT doc FROM cam WHERE length(doc) = 14 UNION SELECT DISTINCT doc FROM sen WHERE length(doc) = 14").fetchall()}
    nat = natureza_fornecedores(raizes, completa)
    verba = verba_gabinete(sorted(deps)) if com_verba else {}
    ass_cam = assessores_camara({i: d["nome"] for i, d in deps.items()})
    ass_sen = assessores_senado(sens)
    em = emendas(con)
    autores_por_slug: dict[str, str] = {slug(a): a for a in em}

    politicos = []
    for casa, ids in (("camara", sorted(deps)), ("senado", sorted(sen_ids))):
        for id_ in ids:
            chave = f"{casa}-{id_}"
            t = tse_dados.get(chave)
            if casa == "camara":
                d = deps[id_]
                nome, uf, partido = d["nome"], d["uf"], d["partido"]
                foto = f"https://www.camara.leg.br/internet/deputado/bandep/{id_}.jpg"
                feminino = (t or {}).get("genero") == "FEMININO"
                cargo = "Deputada federal" if feminino else "Deputado federal"
            else:
                s = sens.get(id_) or {}
                nome_cota = con.execute("SELECT any_value(nome) FROM sen WHERE id = ?", [id_]).fetchone()[0]
                nome = s.get("nome") or nome_proprio(nome_cota)
                uf, partido, foto = s.get("uf") or (t or {}).get("uf"), s.get("partido"), s.get("foto")
                feminino = s.get("sexo") == "Feminino"
                cargo = "Senadora" if feminino else "Senador"
            if not uf:
                print(f"  sem estado: {casa} {id_} {nome}; fica fora", flush=True)
                continue
            # O autor nas emendas: pelo nome parlamentar, pelo nome de urna e, no Senado, pelo nome que a cota usa.
            autor = None
            for candidato in (nome, (t or {}).get("urna"), nome_proprio(con.execute(f"SELECT any_value(nome) FROM {'cam' if casa == 'camara' else 'sen'} WHERE id = ?", [id_]).fetchone()[0])):
                if candidato and slug(candidato) in autores_por_slug:
                    autor = autores_por_slug[slug(candidato)]
                    break
            por_ano = {}
            for ano in anos():
                cota = resumo_cota(con, "cam" if casa == "camara" else "sen", id_, ano,
                                   CATEGORIAS_CAMARA if casa == "camara" else CATEGORIAS_SENADO, nat)
                e = em.get(autor, {}).get(ano) if autor else None
                if not cota and not e:
                    continue
                item: dict = {}
                if cota:
                    item["cota"] = cota
                    item["salario"] = salario_do_ano(ano, cota["meses"])
                    if casa == "camara":
                        tetos = [teto_camara(uf, f"{ano}-{m + 1:02d}") for m, x in enumerate(cota["mes"]) if abs(x) > 0.005]
                        item["cota"]["teto"] = round(sum(t_ for t_ in tetos if t_))
                if (id_, ano) in verba:
                    item["gabinete"] = verba[(id_, ano)]
                if e:
                    item["emendas"] = e
                por_ano[str(ano)] = item
            if not por_ano:
                continue
            politicos.append({
                "chave": chave, "casa": casa, "id": id_, "nome": nome, "uf": uf, "partido": partido, "cargo": cargo,
                "feminino": feminino, "foto": foto, "autor": autor, "tse": t,
                "assessores": (ass_cam if casa == "camara" else ass_sen).get(id_),
                "anos": por_ano,
            })

    completos = {f"camara-{i}": n for i, n in nomes_civis_camara().items()}
    completos.update({f"senado-{c}": s["completo"] for c, s in sens.items() if s.get("completo")})
    ligar_mesma_pessoa(politicos, completos)

    # Endereço: /politicos/<uf>/<nome>. Se o nome repete no estado, o cargo atual de quem passou pelas duas Casas
    # fica com o endereço limpo e o antigo ganha o cargo no fim; se ainda repetir (dois deputados com o mesmo nome),
    # o id.
    usados: Counter[str] = Counter((p["uf"], slug(p["nome"])) for p in politicos)
    limpos: Counter[str] = Counter((p["uf"], slug(p["nome"])) for p in politicos if p["atual"] and p["outros"])
    for p in politicos:
        s = slug(p["nome"])
        if usados[(p["uf"], s)] > 1 and not (p["atual"] and p["outros"] and limpos[(p["uf"], s)] == 1):
            s = f"{s}-{'deputado' if p['casa'] == 'camara' else 'senador'}"
        p["slug"] = s
    repetidos = Counter((p["uf"], p["slug"]) for p in politicos)
    for p in politicos:
        if repetidos[(p["uf"], p["slug"])] > 1:
            p["slug"] = f"{p['slug']}-{p['id']}"
    por_chave = {p["chave"]: p for p in politicos}
    for p in politicos:
        for o in p["outros"]:
            o["slug"] = por_chave[o["chave"]]["slug"]
    # Endereços que já foram ao ar e mudaram: a página nova responde também pelo antigo (redirecionamento).
    anteriores = {}
    if REFERENCIA.exists():
        for q in json.loads(REFERENCIA.read_text(encoding="utf-8")).get("politicos", []):
            anteriores[q["chave"]] = [q.get("slug")] + q.get("slugsAntigos", [])
    for p in politicos:
        antigos = [s_ for s_ in anteriores.get(p["chave"], []) if s_ and s_ != p["slug"]]
        p["slugsAntigos"] = sorted(set(antigos) - {q["slug"] for q in politicos if q["uf"] == p["uf"]})

    # Comparação: mediana do gasto por mês dos colegas da mesma Casa e do mesmo estado (com 6 meses ou mais).
    for ano in anos():
        grupos: dict[tuple, list] = defaultdict(list)
        for p in politicos:
            c = p["anos"].get(str(ano), {}).get("cota")
            if c and c["meses"] >= MESES_MINIMOS:
                grupos[(p["casa"], p["uf"])].append((p, c["porMes"], c["total"]))
        for (casa, uf), lista in grupos.items():
            valores = sorted(v for _, v, _ in lista)
            mediana = statistics.median(valores)
            for p, v, total in lista:
                c = p["anos"][str(ano)]["cota"]
                c["comparacao"] = {"mediana": round(mediana), "n": len(lista), "colegas": valores if casa == "camara" else None}
                if casa == "senado":
                    c["comparacao"]["pares"] = sorted(([q["nome"], q["slug"], t_] for q, _, t_ in lista), key=lambda x: -x[2])
    politicos.sort(key=lambda p: (p["uf"], sem_acento(p["nome"]).lower()))
    return {
        "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anos": [str(a) for a in anos()],
        "subsidio": SUBSIDIO,
        "maxSecretarios": MAX_SECRETARIOS,
        "ufs": UFS,
        "fontes": {
            "camara": "Câmara dos Deputados: cota parlamentar (CEAP), verba de gabinete e funcionários (dados abertos)",
            "senado": "Senado Federal: cota parlamentar (CEAPS), senadores e servidores (dados abertos)",
            "emendas": "Controladoria-Geral da União, Portal da Transparência: emendas parlamentares pagas",
            "tse": "Tribunal Superior Eleitoral: candidaturas, bens, receitas de campanha e votos (dados abertos)",
        },
        "politicos": politicos,
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="politicos", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--tse", action="store_true", help="refaz a parte das eleições (TSE, uns 2 GB de download)")
    p.add_argument("--sem-verba", action="store_true", help="não lê a verba de gabinete da Câmara (513 páginas por ano)")
    p.add_argument("--natureza", action="store_true", help="procura na Receita a natureza jurídica dos fornecedores novos (~1,3 GB)")
    args = p.parse_args()

    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return

    con = duckdb.connect()
    carregar_cota_camara(con)
    carregar_cota_senado(con)
    cache_tse = PASTA / "tse.json"   # a parte do TSE já montada (sem CPF), para não refazer a cada execução
    if args.tse:
        tse_dados = tse(con, senadores())
        cache_tse.write_text(json.dumps(tse_dados, ensure_ascii=False), encoding="utf-8")
    else:
        if cache_tse.exists():
            tse_dados = json.loads(cache_tse.read_text(encoding="utf-8"))
        else:
            anterior = json.loads(REFERENCIA.read_text(encoding="utf-8")) if REFERENCIA.exists() else {"politicos": []}
            tse_dados = {q["chave"]: q.get("tse") for q in anterior["politicos"] if q.get("tse")}
        con.execute("DROP TABLE IF EXISTS cam_cpf")
    dados = montar(con, tse_dados, com_verba=not args.sem_verba, completa=args.natureza)
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}: {len(dados['politicos'])} políticos, "
          f"{len(texto) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
