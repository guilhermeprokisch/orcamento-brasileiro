"""Emendas dos deputados estaduais: o que cada um indicou no orçamento do estado, para qual cidade e quanto foi pago.

    uv run emendas-estaduais                 # baixa os estados de novo e grava a cópia de referência
    uv run emendas-estaduais --uf MG ES      # só alguns (os outros ficam como estavam na cópia de referência)
    uv run emendas-estaduais --sem-baixar    # só copia a cópia de referência para o site (a publicação diária)

Cada estado publica de um jeito (docs/levantamento-emendas-estaduais.md). Aqui entram os que têm arquivo aberto com o
deputado e a cidade:
- MG: CSV das indicações (dados.mg.gov.br), com o código IBGE, o tipo de quem recebe e o pago;
- ES: CSV por ano (dados.es.gov.br), com o código IBGE de 6 dígitos e o pago;
- AC: a planilha que a página de emendas da Seplan lê, com o município pelo nome e o pago;
- PA: a API que a página de emendas do portal do estado chama, com o município pelo nome e o pago;
- RJ: a base das emendas impositivas e o relatório de execução (Seplag), com o município pelo nome;
- DF: a API do portal da transparência do DF (o DF é uma cidade só);
- MS: CSV por ano (dados.ms.gov.br), com o município pelo nome e só o valor indicado.
- SC: o painel Power BI da Secretaria da Fazenda (2023 em diante), com o código IBGE, o tipo de quem recebe e o pago;
- PE: as tabelas de 2026 dos dados abertos (dados.pe.gov.br), por forma de execução; antes de 2026 não há o autor;
- AL: o JSON que a página de emendas do portal chama, só 2026;
- MA: a exportação CSV do portal, só 2026;
- SE: a API do portal (2022 a 2025) e o painel de monitoramento que o portal indica (2026 em diante);
- SP: os painéis Power BI do portal da transparência (um por ano, 2023 a 2025), com o município pelo nome e o estágio
  de cada emenda (o pago é o valor das que estão como "Pagas").

Nada de CPF: as colunas de documento do credor não são lidas, e os nomes de quem recebe não são guardados, só o total
por cidade, separado entre a prefeitura, entidades e o estado. O deputado é ligado à página dele em /politicos pelo
nome, com a mesma regra de politicos_estaduais.ligar_assembleia, sobre os eleitos de 2022 (pipeline/referencia/politicos.json).

Saída em site/public/data/indicadores/emendas-estaduais.json (e a cópia em pipeline/referencia/):
    {"gerado", "anos", "estados": {uf: {nome, fonte, url, anos, pago, pix, nota}},
     "mun": {ibge: {ano: {v, i, p, g, pix, n, aut, areas}}},
     "uf": {uf: {ano: {v, i, p, semCidade, n}}},
     "deputados": {chave tse: {ano: {v, i, p, n, pix, g, est, cid, nc, areas}}}}
    v = o valor que a página mostra: o pago, onde o estado publica, ou o indicado; i = indicado; p = pago (ou null);
    g = [prefeitura, entidades, estado e outros] (ou null, onde o estado não diz quem recebe); pix = transferência
    especial; aut = [[nome, valor, chave tse ou null], ...]; cid = [[ibge, valor], ...].
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import shutil
import ssl
import sys
import time
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import cidades as c
from . import powerbi
from .fontes import CONTEXTO_TLS
from .politicos import em_ordem, nome_proprio, sem_acento
from .politicos_estaduais import chave_nome, ligar_assembleia
from .rfb import casador

PASTA = c.RAIZ / "data" / "raw" / "emendas-estaduais"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "emendas-estaduais.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "emendas-estaduais.json"
POLITICOS = c.RAIZ / "pipeline" / "referencia" / "politicos.json"
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
UA = "Mozilla/5.0 (orcamento-brasileiro; dados abertos)"
PRIMEIRO_ANO = 2023          # a legislatura eleita em 2022, a mesma de /politicos
IBGE_DF = 53                  # o DF, como a página dele o chama (o código do estado)
MAX_AUTORES, MAX_AREAS, MAX_CIDADES = 5, 4, 8

ESTADOS = {
    "MG": {"nome": "Minas Gerais", "fonte": "Governo de Minas Gerais, dados abertos: emendas estaduais, indicações",
           "url": "https://dados.mg.gov.br/dataset/portal_emendas_estaduais", "pago": True, "pix": True},
    "ES": {"nome": "Espírito Santo", "fonte": "Secretaria da Fazenda do Espírito Santo, dados abertos: emendas parlamentares do estado",
           "url": "https://dados.es.gov.br/dataset/portal-da-transparencia-emendas-parlamentares-do-estado", "pago": True, "pix": False},
    "AC": {"nome": "Acre", "fonte": "Secretaria de Planejamento do Acre, portal de emendas estaduais",
           "url": "https://seplan.ac.gov.br/gestao-estrategica-de-recursos/convenios/portal-de-emendas-estaduais/", "pago": True, "pix": True},
    "PA": {"nome": "Pará", "fonte": "Portal da Transparência do Pará: emendas parlamentares estaduais",
           "url": "https://www.sistemas.pa.gov.br/portaltransparencia/emendas-parlamentares-estaduais", "pago": True, "pix": False},
    "RJ": {"nome": "Rio de Janeiro", "fonte": "Secretaria de Planejamento do Rio de Janeiro: emendas impositivas e relatório de execução",
           "url": "https://www.redeplan.planejamento.rj.gov.br/demaisprocessos/emendas.html", "pago": True, "pix": True},
    "DF": {"nome": "Distrito Federal", "fonte": "Portal da Transparência do Distrito Federal: emendas parlamentares",
           "url": "https://www.transparencia.df.gov.br/#/despesas/emendas-parlamentares", "pago": True, "pix": False},
    "SC": {"nome": "Santa Catarina", "fonte": "Secretaria da Fazenda de Santa Catarina, painel de emendas parlamentares estaduais",
           "url": "https://www.sef.sc.gov.br/transparencias/emendas-parlamentares-estaduais", "pago": True, "pix": True},
    "SP": {"nome": "São Paulo", "fonte": "Portal da Transparência de São Paulo, painéis de emendas impositivas",
           "url": "https://www.transparencia.sp.gov.br/home/emendasparlamentares", "pago": True, "pix": False},
    "PE": {"nome": "Pernambuco", "fonte": "Governo de Pernambuco, dados abertos: emendas parlamentares estaduais",
           "url": "https://dados.pe.gov.br/dataset/emendasparlamentaresestaduais", "pago": True, "pix": True},
    "AL": {"nome": "Alagoas", "fonte": "Portal da Transparência de Alagoas: emendas parlamentares estaduais",
           "url": "https://transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais/", "pago": True, "pix": True},
    "MA": {"nome": "Maranhão", "fonte": "Portal da Transparência do Maranhão: emendas estaduais",
           "url": "https://www.transparencia.ma.gov.br/app/v2/emendasestaduais", "pago": True, "pix": False},
    "SE": {"nome": "Sergipe", "fonte": "Portal da Transparência de Sergipe e Painel de Monitoramento das Emendas Parlamentares Estaduais",
           "url": "https://www.transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais", "pago": True, "pix": True},
    "MS": {"nome": "Mato Grosso do Sul", "fonte": "Governo de Mato Grosso do Sul, dados abertos: emendas parlamentares",
           "url": "https://www.dados.ms.gov.br/dataset/emendas-parlamentares", "pago": False, "pix": False},
}
# O que vale dizer de cada estado, além do que os dados mostram.
NOTAS = {
    "ES": "Até 2026 as emendas do Espírito Santo não eram obrigatórias: o governo podia não pagar, e pagou bem menos do que foi indicado.",
    "RJ": "Em 2024 o relatório de execução não separa as emendas; só há o valor indicado.",
    "DF": "O pago inclui o que foi pago no ano de emendas de anos anteriores.",
    "SP": ("São Paulo publica o estágio de cada emenda, não o valor pago: conta como pago o valor das emendas que estão como "
           "pagas. O painel de 2026 ainda não existe. A lei paulista prevê a transferência especial, mas o painel não a separa."),
    "PE": "Pernambuco só publica as emendas com o deputado a partir de 2026.",
    "AL": "Alagoas só publica as emendas a partir de 2026.",
    "MA": "O Maranhão só publica as emendas a partir de 2026. A transferência especial existe na lei, mas os dados não a separam.",
    "SE": "Em 2025, o portal de Sergipe só traz o pago de parte das emendas; para esse ano, o valor é o indicado.",
    "MS": "Mato Grosso do Sul publica só o valor indicado de cada emenda, não quanto já foi pago.",
}


@dataclass
class Linha:
    uf: str
    ano: int
    autor: str                 # como o estado escreve
    coletiva: bool             # bloco, bancada, comissão ou mais de um deputado
    ibge: int | None           # None: o estado inteiro ou sem cidade
    grupo: int | None          # 0 prefeitura, 1 entidades, 2 estado e outros; None: o estado não diz
    area: str
    pix: bool
    indicado: float
    pago: float | None


# ---------------------------------------------------------------- ajudantes

def numero(s) -> float:
    """ "R$ 1.234,56", "1234,5", "300.000", "100000" e números → float."""
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s or "").replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    if not s or s in ("-", "—"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def conserta(s: str) -> str:
    """Texto UTF-8 lido duas vezes ("SaÃºde" → "Saúde")."""
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def texto(b: bytes) -> str:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return conserta(b.decode(enc))
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1")


def baixar(url: str, destino: Path, forcar: bool, headers: dict | None = None, contexto: ssl.SSLContext = CONTEXTO_TLS,
           dados: bytes | None = None) -> bytes:
    if destino.exists() and not forcar:
        return destino.read_bytes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = urllib.parse.quote(url, safe=":/?=&%#+,")
    pedido = urllib.request.Request(url, data=dados, headers={"User-Agent": UA, **(headers or {})})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(pedido, timeout=300, context=contexto) as r:
                b = r.read()
            destino.write_bytes(b)
            return b
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError("inalcançável")


def ler_csv(b: bytes, sep: str | None = None) -> list[dict]:
    t = texto(b)
    if sep is None:
        primeira = t.split("\n", 1)[0]
        sep = ";" if primeira.count(";") >= primeira.count(",") else ","
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(t), delimiter=sep)]


def ler_csv_remendado(b: bytes, sep: str) -> list[dict]:
    """CSV com quebra de linha dentro de campos sem aspas (PE): junta as linhas físicas até ter todas as colunas."""
    linhas = texto(b).splitlines()
    cab = next(csv.reader([linhas[0]], delimiter=sep))
    saida, buf = [], ""
    for l in linhas[1:]:
        buf = f"{buf} {l}" if buf else l
        cols = next(csv.reader([buf], delimiter=sep), [])
        if len(cols) < len(cab):
            continue
        saida.append({k.strip(): (v or "").strip() for k, v in zip(cab, cols)})
        buf = ""
    return saida


def area(s: str) -> str:
    s = re.sub(r"^\s*\d+\s*-\s*", "", s or "").strip()
    return nome_proprio(s, pessoa=True) if s else "Não informado"


MUNICIPAL = re.compile(r"\b(MUNICIPIO|MUNICIPAL|PREFEITURA|FUNDO MUNICIPAL|CAMARA MUNICIPAL)\b")
ESTADUAL = re.compile(r"\b(ESTADO D[OAE]|SECRETARIA DE ESTADO|SECRETARIA ESTADUAL|FUNDO ESTADUAL|GOVERNO D[OAE]|"
                      r"UNIVERSIDADE (FEDERAL|ESTADUAL)|INSTITUTO FEDERAL|POLICIA|BOMBEIROS|TRIBUNAL|DEFENSORIA|"
                      r"MINISTERIO PUBLICO|DEPARTAMENTO ESTADUAL|CONSORCIO|AUTARQUIA|FUNDACAO ESTADUAL)\b")


def grupo_pelo_nome(nome: str) -> int:
    n = sem_acento(nome or "").upper()
    if ESTADUAL.search(n):
        return 2
    if MUNICIPAL.search(n):
        return 0
    return 1


# ---------------------------------------------------------------- os estados

def ler_mg(forcar: bool) -> list[Linha]:
    url = ("https://dados.mg.gov.br/dataset/portal_emendas_estaduais/resource/d85d9a92-dd8e-473d-bcb4-a4f3d13309b1/"
           "download/vw_sg_v2_ep_indic_recursos_tw.csv")
    tipos = {"MUNICÍPIO": 0, "FUNDO MUNICIPAL DE SAÚDE": 0, "ORGANIZAÇÃO DA SOCIEDADE CIVIL": 1, "CAIXA ESCOLAR": 1,
             "SERVIÇOS SOCIAIS AUTÔNOMOS": 1, "CONSÓRCIO PÚBLICO": 2, "ÓRGÃOS OU ENTIDADES PÚBLICAS": 2, "UNIDADE ADMINISTRATIVA": 2}
    saida = []
    for r in ler_csv(baixar(url, PASTA / "MG" / "indicacoes.csv", forcar), ";"):
        if r["status_indicacao"].startswith("REPROVADO"):
            continue
        ibge = r["municipio_ibge"].split(",")[0].split(".")[0]
        pix = r["tipo_indicacao"] == "TRANSFERÊNCIA ESPECIAL"
        saida.append(Linha("MG", int(r["ano_exercicio"]), r["responsavel"], r["classificacao_resp_descricao"] != "PARLAMENTAR ESTADUAL",
                           int(ibge) if ibge.isdigit() else None, tipos.get(r["beneficiario_tipo"], 0 if pix else None),
                           "Transferência especial" if pix else area(r["funcao_descricao"]), pix,
                           numero(r["valor_indicacao"]), numero(r["valor_pago"])))
    return saida


def ckan_recursos(base: str, pacote: str) -> list[dict]:
    b = baixar(f"{base}/api/3/action/package_show?id={pacote}", PASTA / "_ckan" / f"{pacote}.json", True)
    return json.loads(b)["result"]["resources"]


def ler_es(forcar: bool, ibge6: dict[str, int]) -> list[Linha]:
    saida = []
    for rec in ckan_recursos("https://dados.es.gov.br", "portal-da-transparencia-emendas-parlamentares-do-estado"):
        m = re.search(r"emendas-estaduais-(\d{4})\.csv$", rec["url"].lower())
        if not m:
            continue
        ano = int(m.group(1))
        linhas = ler_csv(baixar(rec["url"], PASTA / "ES" / f"{ano}.csv", forcar or ano >= dt.date.today().year - 1), ";")
        por_emenda = Counter(r["NumeroEmenda"] for r in linhas)
        for r in linhas:
            # CpfCnpjNis e Favorecido não são lidos: só a modalidade diz para quem foi.
            mod = r["CodigoModalidade"]
            g = 0 if mod.startswith("4") else 1 if mod.startswith(("5", "6")) else 2
            autor = re.sub(r"^Dep(\.|utad[oa])\s*(ª|a\b)?\s*", "", r["NomeAutor"]).strip()
            saida.append(Linha("ES", int(r["AnoEmenda"] or ano), autor, bool(re.search(r"bancada|comiss|bloco", autor, re.I)),
                               ibge6.get(r["CodigoMunicipio"].zfill(6)), g, area(r["Funcao"]), False,
                               numero(r["ValorPrevisto"]) / por_emenda[r["NumeroEmenda"]], numero(r["ValorPago"])))
    return saida


def ler_ac(forcar: bool, ibge_de) -> list[Linha]:
    url = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vRzbV0AT43iRHZEQ4ovc5jbywcxI2De6p_dYftLPkuV3ZsiemRCdhjbhHE8pk_f_FnzHi9rM67PqyYh/"
           "pub?gid=1271042240&single=true&output=csv")
    saida = []
    for r in ler_csv(baixar(url, PASTA / "AC" / "emendas.csv", forcar), ","):
        if not r.get("Ano", "").isdigit():
            continue
        mod = r.get("Descrição Modalidade Aplicacao Estadual", "")
        mun = r.get("Municípios", "")
        ibge = None if not mun or "estado" in mun.lower() else ibge_de(mun, "AC")
        pix = "especial" in mod.lower()
        g = 0 if "munic" in mod.lower() else grupo_pelo_nome(r.get("Nome Entidade Beneficiada", ""))
        saida.append(Linha("AC", int(r["Ano"]), r["Parlamentar"], False, ibge, g,
                           "Transferência especial" if pix else area(r.get("Área Temática", "")), pix,
                           numero(r.get("Valor Emenda")), numero(r.get("Pago"))))
    return saida


def chave_api_pa() -> str:
    """A chave pública que a própria página manda no cabeçalho X-API-KEY (fica no JavaScript dela)."""
    base = "https://www.sistemas.pa.gov.br/portaltransparencia/"
    def get(u: str) -> str:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60, context=CONTEXTO_TLS).read().decode("utf-8", "replace")
    html = get(base + "emendas-parlamentares-estaduais")
    indice = re.search(r"assets/index\.[0-9a-f]+\.js", html).group(0)
    js = get(base + indice)
    rota = re.search(r'path:"/emendas-parlamentares-estaduais"[^}]*?import\("\./([^"]+)"\)', js).group(1)
    js = get(base + "assets/" + rota)
    servico = re.search(r'import\("\./(publicEmendasService[^"]+)"\)', js).group(1)
    js = get(base + "assets/" + servico)
    var = re.search(r'"X-API-KEY":(\w+)', js).group(1)
    return re.search(rf'\b{var}="([^"]+)"', js).group(1)


def ler_pa(forcar: bool, ibge_de) -> list[Linha]:
    api = "https://api.emendas.seplad.pa.gov.br/api/v1/transparencia/emendas"
    cab = {"X-API-KEY": chave_api_pa(), "Accept": "application/json"}
    anos = json.loads(baixar(api + "/opcoes", PASTA / "PA" / "opcoes.json", True, cab))
    anos = [int(a) for a in (anos.get("anos") or anos.get("data", {}).get("anos") or [])]
    saida = []
    for ano in sorted(a for a in anos if a >= PRIMEIRO_ANO):
        doc = json.loads(baixar(f"{api}?ano={ano}", PASTA / "PA" / f"{ano}.json", forcar or ano >= dt.date.today().year - 1, cab))
        for r in doc["data"]:
            if r.get("cancelada") in (True, "true", "Sim", "S"):
                continue
            mun = r.get("municipios") or ""
            mun = mun[0] if isinstance(mun, list) and len(mun) == 1 else mun if isinstance(mun, str) else ""
            ibge = None if not mun or mun.lower().startswith("divers") else ibge_de(mun, "PA")
            saida.append(Linha("PA", int(r.get("ano") or ano), r.get("parlamentar") or "", False, ibge, None,
                               area(r.get("funcao_governo") or ""), False, numero(r.get("valor")), numero(r.get("pago"))))
    return saida


def pagos_relatorio_rj(t: str) -> dict[str, float]:
    """O pago de cada emenda (pelo código) no relatório de execução do RJ."""
    # Relatório com a emenda numa linha e os empenhos embaixo; às vezes com uma linha "<código> Total".
    soma: dict[str, float] = defaultdict(float)
    total: dict[str, float] = {}
    atual = None
    for cols in csv.reader(io.StringIO(t), delimiter=";"):
        cols = [x.strip() for x in cols]
        if len(cols) < 12:
            continue
        m = re.fullmatch(r"(\d{8,})(\s+Total)?", cols[8])
        if m and m.group(2):
            total[m.group(1)] = numero(cols[-1])
            continue
        if m:                                          # a linha da emenda (com o pago, quando não há empenhos embaixo)
            atual = m.group(1)
            soma[atual] += numero(cols[-1])
        elif not cols[8] and re.match(r"20\d\dNE", cols[9]) and atual:   # um empenho da emenda de cima
            soma[atual] += numero(cols[-1])
        else:
            atual = None
    return {**soma, **total}


def ler_rj(forcar: bool, ibge_de) -> list[Linha]:
    pagina = "https://www.redeplan.planejamento.rj.gov.br/demaisprocessos/emendas.html"
    html = texto(baixar(pagina, PASTA / "RJ" / "emendas.html", True))
    links = sorted({urllib.parse.urljoin(pagina, h) for h in re.findall(r'href="([^"]+\.csv)"', html)})
    hoje = dt.date.today().year

    def ano_de(u: str) -> int | None:
        nome = urllib.parse.unquote(u.rsplit("/", 1)[-1])
        m = re.search(r"(20\d\d)(?!\d)", re.sub(r"\d{2}\d{2}(20\d\d)", "", nome)) or re.search(r"/(20\d\d)/", u)
        return int(m.group(1)) if m else None

    def data_de(u: str) -> str:
        m = re.search(r"(\d{2})(\d{2})(20\d\d)", urllib.parse.unquote(u))
        return f"{m.group(3)}{m.group(2)}{m.group(1)}" if m else ""

    def periodo(u: str) -> int:
        n = urllib.parse.unquote(u).lower()
        m = re.search(r"(\d)\s*(º|_)?\s*(bi|quadri)", n)
        k = int(m.group(1)) if m else 0
        return k * (2 if "bi" in (m.group(3) if m else "") else 4)   # em meses: o relatório mais recente do ano

    saida = []
    for ano in range(2024, hoje + 1):
        bases = [u for u in links if "base" in u.lower() and ano_de(u) == ano]
        if not bases:
            continue
        # O ano pode ter mais de uma base (a do começo do ano e as fases de detalhamento): fica a de maior valor.
        candidatas = []
        for i, u in enumerate(sorted(bases, key=data_de)):
            ls = ler_csv(baixar(u, PASTA / "RJ" / f"base-{ano}-{i}.csv", forcar or ano >= hoje - 1), ";")
            candidatas.append((sum(numero(r.get("Valor")) for r in ls), ls))
        linhas = max(candidatas, key=lambda x: x[0])[1]
        pago: dict[str, float] = {}
        execs = [u for u in links if "xecu" in u.lower() and ano_de(u) == ano]
        if execs:
            rel = max(execs, key=periodo)
            b = baixar(rel, PASTA / "RJ" / f"execucao-{ano}.csv", forcar or ano >= hoje - 1)
            pago = pagos_relatorio_rj(texto(b))
        for r in linhas:
            ident = (r.get("Identificador") or "").strip()
            mun = r.get("Município", "")
            ibge = None if not mun or mun.lower() in ("estado", "estadual") else ibge_de(mun, "RJ")
            mod = r.get("Modalidade", "")
            pix = "especial" in mod.lower()
            benef = r.get("Beneficiário", "")
            g = (0 if pix or "fundo a fundo" in mod.lower() else grupo_pelo_nome(benef)) if benef or pix else None
            saida.append(Linha("RJ", ano, r.get("Autor", ""), False, ibge, g,
                               "Transferência especial" if pix else area(r.get("Função", "")), pix,
                               numero(r.get("Valor")), pago.get(ident, 0.0) if pago else None))
    return saida


def autor_df(nome: str) -> tuple[str, bool]:
    """ "ARLETE AVELAR SAMPAIO - ARLETE SAMPAIO" é uma pessoa (o nome civil e o político); "AGACIEL MAIA - HERMETO" são
    dois deputados, uma emenda em grupo."""
    partes = [p.strip() for p in nome.split(" - ") if p.strip()]
    if re.search(r"bancada|comiss|bloco|mesa", nome, re.I):
        return nome, True
    if len(partes) <= 1:
        return nome, False
    ts = [set(chave_nome(p).split("-")) for p in partes]
    if len(partes) == 2 and (ts[0] <= ts[1] or ts[1] <= ts[0] or len(ts[0] & ts[1]) >= 2):
        return min(partes, key=len), False
    return nome, True


def ler_df(forcar: bool) -> list[Linha]:
    api = "https://www.transparencia.df.gov.br/api/despesa/emendas-parlamentares"
    cab = {"x-client-id": str(uuid.uuid4()), "Accept": "application/json"}
    anos = json.loads(baixar(api + "/anos", PASTA / "DF" / "anos.json", True, cab))
    hoje = dt.date.today().year
    saida = []
    for ano in sorted(a for a in anos if a >= PRIMEIRO_ANO):
        pagina, itens = 0, []
        while True:
            doc = json.loads(baixar(f"{api}?anoExercicio={ano}&page={pagina}&size=500",
                                    PASTA / "DF" / f"{ano}-{pagina}.json", forcar or ano >= hoje - 1, cab))
            itens += doc.get("content", [])
            if doc.get("last", True) or pagina > 100:
                break
            pagina += 1
        for r in itens:
            autor, coletiva = autor_df(r.get("nomeAutor") or "")
            saida.append(Linha("DF", int(r.get("anoExercicio") or ano), autor, coletiva,
                               IBGE_DF, None, area(r.get("nomeFuncao") or ""), False,
                               numero(r.get("dotacaoInicial")), numero(r.get("valorEmpenhoPago"))))
    return saida


# MS não publica a função: a área sai do órgão que executa a emenda.
AREAS_MS = [("SAUDE", "Saúde"), ("EDUCACAO", "Educação"), ("UNIVERSIDADE", "Educação"), ("ASSISTENCIA SOCIAL", "Assistência social"),
            ("DESPORTO", "Esporte e lazer"), ("ESPORTE", "Esporte e lazer"), ("CULTURA", "Cultura"), ("AGRARIO", "Agricultura"),
            ("CIDADANIA", "Direitos da cidadania"), ("SEGURANCA", "Segurança pública"), ("MEIO AMBIENTE", "Meio ambiente")]


def area_ms(orgao: str) -> str:
    o = sem_acento(orgao).upper()
    return next((a for k, a in AREAS_MS if k in o), area(re.sub(r"\s+-\s+\w+$", "", orgao)))


def ler_ms(forcar: bool, ibge_de) -> list[Linha]:
    saida = []
    for rec in ckan_recursos("https://www.dados.ms.gov.br", "emendas-parlamentares"):
        m = re.search(r"(20\d\d)", rec["name"])
        if rec.get("format", "").upper() != "CSV" or not m:
            continue
        ano = int(m.group(1))
        for r in ler_csv(baixar(rec["url"], PASTA / "MS" / f"{ano}.csv", forcar or ano >= dt.date.today().year - 1), ";"):
            nomes = [n.strip() for n in re.split(r",|;| e ", r.get("Nomes(s) Político(s)") or r.get("Deputado(s)") or "") if n.strip()]
            mun = re.sub(r"\s*-\s*MS$", "", r.get("Município", "")).strip()
            ibge = ibge_de(mun, "MS") if mun else None
            orgao = area_ms(r.get("Órgão", ""))
            saida.append(Linha("MS", ano, nomes[0] if len(nomes) == 1 else ", ".join(nomes), len(nomes) != 1, ibge,
                               grupo_pelo_nome(r.get("Beneficiário(a)", "")), orgao, False, numero(r.get("Valor Emenda")), None))
    return saida


# Os painéis Power BI: SC tem um só, de 2023 em diante; SP, um por ano (a chave do de 2026 entra aqui quando sair).
PAINEL_SC = "cd153507-3216-4721-9c42-b900a95507d9"
PAINEIS_SP = {2023: "f7243798-e16d-47bf-a76d-587c0fc94501", 2024: "7ae99f38-6898-461b-8d93-aeee788c318a",
              2025: "c53a54e7-9c63-4d84-be1a-5111bf2756d8"}
AREAS_SC = {"FUNDO SOCIAL": "Fundo Social", "SED": "Educação", "SES": "Saúde", "SIE": "Infraestrutura", "SAR": "Agricultura",
            "SSP": "Segurança pública"}
FUNCOES = {"SAUDE": "Saúde", "EDUCACAO": "Educação", "ADMINISTRACAO": "Administração", "ASSISTENCIA SOCIAL": "Assistência social",
           "SEGURANCA PUBLICA": "Segurança pública", "ENCARGOS ESPECIAIS": "Encargos especiais", "CULTURA": "Cultura",
           "DESPORTO E LAZER": "Esporte e lazer", "ESPORTE": "Esporte e lazer", "AGRICULTURA": "Agricultura", "URBANISMO": "Urbanismo",
           "SANEAMENTO": "Saneamento", "TRANSPORTE": "Transporte", "HABITACAO": "Habitação", "DIREITOS DA CIDADANIA": "Direitos da cidadania",
           "TURISMO": "Turismo", "GESTAO AMBIENTAL": "Meio ambiente", "MEIO AMBIENTE": "Meio ambiente", "TRABALHO": "Trabalho"}


def num(v) -> float:
    return v if isinstance(v, (int, float)) else numero(str(v).replace(".", ",")) if v else 0.0


def area_sp(funcao: str | None, orgao: str | None) -> str:
    """ "10 - SAUDE" (ou "04 - ADMINISTRACAO; 06 - ...", fica a primeira); sem função, o órgão que processou."""
    for s in (funcao, orgao):
        if not s:
            continue
        s = sem_acento(re.sub(r"^\s*\d+\s*-\s*", "", s.split(";")[0])).upper().strip()
        return next((v for k, v in FUNCOES.items() if s.startswith(k)), nome_proprio(s, pessoa=True))
    return "Não informado"


def guardar_json(dados, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def ler_sc(forcar: bool) -> list[Linha]:
    """Só as colunas da emenda: o documento de quem recebe, o banco e a conta, que o painel também carrega, não são lidos."""
    destino = PASTA / "SC" / "cadastro.json"
    if forcar or not destino.exists():
        m = powerbi.modelo(PAINEL_SC)
        cols = ["num_ano", "num_emenda_parlamentar", "nom_parlamentar", "nom_tipo_beneficiario", "Código IBGE", "val_emenda_parlamentar",
                "Pagamentos", "Modalidade Final", "Unidade Orçamentária", "dsc_situacao"]
        guardar_json(powerbi.consultar(PAINEL_SC, m, "CadastroEmendasParlamentares", cols), destino)
    tipos = {"Prefeituras / Municípios": 0, "Fundos": 0, "Órgão da Administração Direta Municipal": 0,
             "Entidade Privada Sem Fins Lucrativos": 1, "APAE": 1}
    saida = []
    for r in json.loads(destino.read_text(encoding="utf-8")):
        if r.get("dsc_situacao") == "Inativo" or not r.get("num_ano"):
            continue
        pix = (r.get("Modalidade Final") or "").startswith("Município")
        ibge = r.get("Código IBGE")
        autor = r.get("nom_parlamentar") or ""
        saida.append(Linha("SC", int(r["num_ano"]), autor, autor.lower().startswith(("bancada", "comiss", "mesa")), int(ibge) if ibge else None,
                           tipos.get(r.get("nom_tipo_beneficiario"), 2), "Transferência especial" if pix else
                           AREAS_SC.get(r.get("Unidade Orçamentária") or "", "Não informado"), pix,
                           num(r.get("val_emenda_parlamentar")), num(r.get("Pagamentos"))))
    return saida


def ler_sp(forcar: bool, ibge_de) -> list[Linha]:
    hoje = dt.date.today().year
    saida = []
    for ano, k in sorted(PAINEIS_SP.items()):
        destino = PASTA / "SP" / f"{ano}.json"
        if forcar or ano >= hoje - 1 or not destino.exists():
            m = powerbi.modelo(k)
            tabela = next(t for t, cols in powerbi.esquema(k, m).items() if "PARLAMENTAR" in cols)
            cols = ["CÓDIGO", "ANO", "MUNICÍPIO", "PARLAMENTAR", "BENEFICIÁRIO", "FUNÇÃO DE GOVERNO", "ÓRGÃO PROCESSADOR", "ESTÁGIO",
                    "VALOR DECISÃO", "Primeira Fase Substituídas"]
            guardar_json(powerbi.consultar(k, m, tabela, cols), destino)
        for r in json.loads(destino.read_text(encoding="utf-8")):
            # A emenda impedida na 1ª fase foi trocada por outra, que também está na lista: contar as duas dobraria o indicado.
            if r.get("Primeira Fase Substituídas") == "Sim":
                continue
            mun = (r.get("MUNICÍPIO") or "").strip()
            ibge = ibge_de(mun, "SP") if mun and not mun.upper().startswith(("ESTADO", "DIVERSOS", "VARIOS", "VÁRIOS")) else None
            v = num(r.get("VALOR DECISÃO"))
            autor = r.get("PARLAMENTAR") or ""
            saida.append(Linha("SP", int(r.get("ANO") or ano), autor, autor.lower().startswith(("bancada", "comiss", "mesa")), ibge,
                               grupo_pelo_nome(r.get("BENEFICIÁRIO") or ""), area_sp(r.get("FUNÇÃO DE GOVERNO"), r.get("ÓRGÃO PROCESSADOR")),
                               False, v, v if r.get("ESTÁGIO") == "Pagas" else 0.0))
    return saida


def ler_pe(forcar: bool, ibge_de) -> list[Linha]:
    """2026: uma linha por empenho (ou por emenda sem empenho); o orçamento da emenda se repete em cada linha dela."""
    base = "https://dados.pe.gov.br/dataset/7c721673-6f32-467b-853f-297ec1399705/resource/"
    tabelas = {"pix": "2ad1df94-50cb-4612-ba1b-51c7e11377a2/download/tabela_completa_pix.csv",
               "direta": "fbadd887-5110-406c-887a-2427c3cac8b1/download/tabela_completa_direta.csv",
               "gtv": "8a102499-016e-4b02-8714-fcb2757cfe2f/download/tabela_completa_gtv.csv"}
    saida = []
    for nome, caminho in tabelas.items():
        vistas = set()
        linhas = []
        for r in ler_csv_remendado(baixar(base + caminho, PASTA / "PE" / f"{nome}.csv", True), ";"):
            chave = tuple(r.values())
            if chave in vistas:              # a mesma linha repetida no arquivo
                continue
            vistas.add(chave)
            linhas.append(r)
        por_emenda = Counter((r["autor"], r["codigo_alepe"]) for r in linhas)
        for r in linhas:
            mun = r.get("municipio", "")
            ibge = ibge_de(mun, "PE") if mun and not mun.upper().startswith(("ESTADO", "PERNAMBUCO", "DIVERSOS")) else None
            g = 0 if nome == "pix" else 2 if nome == "direta" else grupo_pelo_nome(r.get("beneficiario", ""))
            saida.append(Linha("PE", int(r["ano"]), r["autor"], False, ibge, g,
                               "Transferência especial" if nome == "pix" else area(r.get("tematica", "")), nome == "pix",
                               numero(r.get("orcamento_atual")) / por_emenda[(r["autor"], r["codigo_alepe"])], numero(r.get("valor_pago"))))
    return saida


AREAS_AL = {"FES": "Saúde", "SEADES": "Assistência social", "SELAJ": "Esporte e lazer", "SECTI": "Ciência e tecnologia",
            "SECULT": "Cultura", "SEDUC": "Educação", "SETEQ": "Trabalho", "SEDICS": "Direitos da cidadania"}


def ler_al(forcar: bool, ibge_de) -> list[Linha]:
    url = "https://transparencia.al.gov.br/despesa/json-emendas-parlamentares/?limit=1000&offset={}"
    rows, offset = [], 0
    while True:
        d = json.loads(baixar(url.format(offset), PASTA / "AL" / f"{offset}.json", True))
        rows += d["rows"]
        offset += 1000
        if offset >= d["total"] or not d["rows"]:
            break
    saida = []
    for r in rows:
        forma = r.get("forma_repasse") or ""
        pix = forma.lower().startswith("transfer")
        mun = r.get("municipio") or ""
        orgao = (r.get("orgao_entidade_executora") or "").split(" - ")[-1].strip()
        ar = "Transferência especial" if pix else "Saúde" if "SESAU" in forma else AREAS_AL.get(orgao, "Não informado")
        benef = r.get("beneficiario") or ""
        g = 0 if pix else grupo_pelo_nome(benef) if benef else None
        saida.append(Linha("AL", int(r.get("ano") or 0), r.get("parlamentar") or "", False, ibge_de(mun, "AL") if mun else None, g, ar, pix,
                           numero(r.get("valor_dotacao_atualizado")), numero(r.get("valor_pago"))))
    return saida


def ler_ma(forcar: bool, ibge_de) -> list[Linha]:
    url = "https://www.transparencia.ma.gov.br/app/v2/emendasestaduais/export?ano={}&formato=csv"
    saida = []
    ano = dt.date.today().year
    linhas = ler_csv(baixar(url.format(ano), PASTA / "MA" / f"{ano}.csv", True), ",")
    for r in linhas:
        mod = r.get("Modalidade", "")
        g = 0 if mod.startswith(("40", "41")) else 1 if mod.startswith("50") else 2
        mun = r.get("Localizador de Gasto", "")
        ibge = ibge_de(mun, "MA") if mun and not mun.upper().startswith(("ESTADO", "MARANH", "DIVERSOS")) else None
        saida.append(Linha("MA", int(r.get("Exercício") or ano), r.get("Parlamentar", ""), False, ibge, g, area(r.get("Função", "")), False,
                           numero(r.get("Valor Solicitado")), numero(r.get("Valor Pago"))))
    # O portal devolve 2026 para qualquer ano pedido: só fica o ano que o arquivo diz.
    return saida


# SE (2022 a 2025) só dá a sigla do órgão que processa a emenda; as que não temos certeza ficam em "Outros".
AREAS_SE = {"SAÚDE": "Saúde", "SES": "Saúde", "FES": "Saúde", "SEASIC": "Assistência social", "SEASC": "Assistência social",
            "FUNCAP": "Cultura", "SEAGRI": "Agricultura", "EMDAGRO": "Agricultura", "CODERSE": "Agricultura",
            "SEEL": "Esporte e lazer", "SEED": "Educação", "SEDUC": "Educação", "SEDURBI": "Urbanismo", "PM": "Segurança pública",
            "SSP": "Segurança pública", "CBM": "Segurança pública", "SEJUC": "Segurança pública", "SEMAC": "Meio ambiente",
            "SETUR": "Turismo", "SPM": "Direitos da cidadania"}


def ler_se(forcar: bool, ibge_de) -> list[Linha]:
    api = "https://api.transparencia.se.gov.br/api/emendas-estaduais"
    hoje = dt.date.today().year
    saida = []
    for ano in sorted(a for a in json.loads(baixar(api + "/anos", PASTA / "SE" / "anos.json", True)) if a >= PRIMEIRO_ANO):
        pagina, rows = 1, []
        while True:
            d = json.loads(baixar(f"{api}?ano={ano}&page={pagina}&limit=100", PASTA / "SE" / f"{ano}-{pagina}.json", forcar or ano >= hoje - 1))
            rows += d["data"]
            if pagina >= d.get("totalPages", 1):
                break
            pagina += 1
        for r in rows:
            mun = (r.get("localidade") or "").strip()
            ibge = ibge_de(mun, "SE") if mun and not mun.upper().startswith(("ESTADO", "SERGIPE", "DIVERSOS")) else None
            ex = r.get("executor") or ""
            pago = (r.get("valorPago") or "").strip()
            orgao = re.sub(r"^\d+\s*-\s*", "", (r.get("orgaoProcessador") or "")).strip().upper()
            saida.append(Linha("SE", int(r.get("exercicio") or ano), r.get("parlamentar") or "", False, ibge,
                               grupo_pelo_nome(ex) if ex else None, AREAS_SE.get(orgao, "Outros"), False,
                               numero(r.get("valorIndicado")), numero(pago) if pago else None))
    # 2026 em diante: o painel de monitoramento (a plataforma que o portal indica), com a exportação completa.
    d = json.loads(baixar("https://sergipeemendasparlamentares.plataformatarget.com.br/api/emendas/export?", PASTA / "SE" / "painel.json", True))
    for r in (d["data"] if isinstance(d, dict) else d):
        n = r.get("n_emenda") or ""
        m = re.search(r"\.(20\d\d)-", n)
        ano = int(m.group(1)) if m else hoje
        inst = (r.get("tipo_instrumento") or "").upper()
        pix = inst.startswith("TRANSFER")
        mun = r.get("municipio") or ""
        ibge = ibge_de(mun, "SE") if mun and "indispon" not in mun.lower() and not mun.upper().startswith(("ESTADO", "SERGIPE")) else None
        benef = r.get("beneficiario") or ""
        g = 0 if pix or "FUNDO A FUNDO" in inst else 2 if "DIRETA" in inst else grupo_pelo_nome(benef) if benef else None
        saida.append(Linha("SE", ano, r.get("autor") or "", False, ibge, g,
                           "Transferência especial" if pix else area(r.get("area") or r.get("cd_funcao") or ""), pix,
                           float(r.get("valor") or 0), float(r.get("pagamento") or 0) + float(r.get("restoapagar_pago") or 0)))
    return saida


# ---------------------------------------------------------------- montagem

def eleitos() -> list[dict]:
    doc = json.loads(POLITICOS.read_text(encoding="utf-8"))
    return [{"chave": p["chave"], "uf": p["uf"], "urna": p["tse"]["urna"], "completo": p["tse"].get("completo"), "cargo": p["tse"]["cargo"]}
            for p in doc["politicos"] if p.get("casa") == "assembleia" and p.get("tse")]


# Os nomes que a regra de nomes não liga sozinha: (uf, chave_nome do autor) → o nome de urna no TSE. Conferidos à mão
# em 23/11/2026 (mesma pessoa, grafia diferente).
APELIDOS = {
    ("ES", "alcantaro-filho"): "Alcântaro",
    ("MG", "celinho-sinttrocel"): "Celinho Sintrocel",
    ("MG", "grego-fundacao"): "Grego",
    ("PA", "flavio-igor-pantoja"): "Flavio Higor Pantoja",
    ("MA", "ariston"): "Ariston Gonçalo",
    ("MA", "andreia-m-rezende"): "Andreia Martins Rezende",
    ("SE", "garibalde-mendonca"): "Garibalde",
    ("SE", "carminha-paiva"): "Carminha",
    ("SE", "luizao-donatrampi"): "Luizao Dona Trampi",
    ("SE", "dr-samuel"): "Dr. Samuel Carvalho",
    ("SE", "paulo-junior"): "Paulo Jr",
    ("SE", "lidiane-lucena"): "Dra Lidiane Lucena",
    ("SE", "george-passos"): "Georgeo Passos",
    ("SE", "ibrain-monteiro"): "Ibrain de Valmir",
    ("SP", "teonilio-barba"): "Barba",
    ("SP", "fabiana-bolsonaro"): "Fabiana B.",
}


def ligar(linhas: list[Linha]) -> dict[tuple[str, str], str]:
    """(uf, autor) → chave do eleito no TSE."""
    def nome_tse(l: Linha) -> str:
        return APELIDOS.get((l.uf, chave_nome(l.autor)), l.autor)
    autores: dict[str, set] = defaultdict(set)
    volta: dict[tuple[str, str], str] = {}
    for l in linhas:
        if not l.coletiva and l.autor:
            k = f"{l.uf}-{chave_nome(nome_tse(l))}"
            autores[l.uf].add((k, nome_tse(l)))
            volta[(l.uf, l.autor)] = k
    todos = eleitos()
    ligacao = ligar_assembleia(todos, autores)
    dono = {k: ch for ch, ks in ligacao.items() for k in ks}
    # O mesmo deputado com duas grafias em anos diferentes ("Julio Garcia" e "Julio Cesar Garcia"): a regra acima liga
    # só uma. A outra liga se for igual, palavra por palavra, ao nome de urna ou ao nome completo de um eleito só.
    exatos: dict[str, set[str]] = defaultdict(set)
    for e in todos:
        for n in (e["urna"], e.get("completo")):
            if n:
                exatos[f"{e['uf']}-{chave_nome(n)}"].add(e["chave"])
    for nomes in autores.values():
        for k, _ in nomes:
            if k not in dono and len(exatos.get(k, ())) == 1:
                dono[k] = next(iter(exatos[k]))
    for uf, nomes in sorted(autores.items()):
        chaves = {k for k, _ in nomes}
        sem = sorted({n for k, n in nomes if k not in dono})
        print(f"{uf}: {len(chaves & set(dono))} de {len(chaves)} autores ligados ao TSE; sem ligação (suplentes e a "
              f"legislatura anterior): {', '.join(sem[:12]) or 'nenhum'}{'…' if len(sem) > 12 else ''}", flush=True)
    return {a: dono[k] for a, k in volta.items() if k in dono}


def nome_autor(l: Linha) -> str:
    n = nome_proprio(l.autor, pessoa=True)
    return re.sub(r"^Bloco\b", "Bloco", n)


def montar(linhas: list[Linha], ligacao: dict, meta: dict[str, dict]) -> dict:
    hoje = dt.date.today().year
    linhas = [l for l in linhas if PRIMEIRO_ANO <= l.ano <= hoje and (l.indicado or l.pago)]
    tem_pago = {uf: m["pago"] for uf, m in meta.items()}

    # Num ano em que o estado não publica o pago (RJ em 2024), o valor é o indicado.
    # Também quando menos da metade das linhas do ano tem o pago (SE em 2025): o pago parcial daria a impressão de que
    # quase nada foi pago.
    com_pago, total = Counter(), Counter()
    for l in linhas:
        total[(l.uf, l.ano)] += 1
        com_pago[(l.uf, l.ano)] += l.pago is not None
    sem_pago_no_ano = {k for k, n in total.items() if com_pago[k] < n / 2}

    def valor(l: Linha) -> float:
        return (l.pago or 0.0) if tem_pago[l.uf] and (l.uf, l.ano) not in sem_pago_no_ano else l.indicado

    def novo():
        return {"v": 0.0, "i": 0.0, "p": 0.0, "temP": False, "g": [0.0, 0.0, 0.0], "gNulo": False, "pix": 0.0, "n": 0,
                "aut": Counter(), "areas": Counter(), "cid": Counter(), "est": 0.0}

    mun: dict[int, dict[int, dict]] = defaultdict(lambda: defaultdict(novo))
    ufs: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(novo))
    deps: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(novo))
    nomes_aut: dict[tuple, str] = {}
    for l in linhas:
        v = valor(l)
        chave = None if l.coletiva else ligacao.get((l.uf, l.autor))
        quem = chave or ("coletiva" if l.coletiva else nome_autor(l))
        nomes_aut[(l.uf, quem)] = nome_autor(l)
        alvos = [ufs[l.uf][l.ano]]
        if l.ibge:
            alvos.append(mun[l.ibge][l.ano])
        if chave:
            alvos.append(deps[chave][l.ano])
        for a in alvos:
            a["v"] += v
            a["i"] += l.indicado
            a["p"] += l.pago or 0.0
            a["temP"] |= l.pago is not None
            a["n"] += 1
            a["pix"] += v if l.pix else 0.0
            if l.grupo is None:
                a["gNulo"] = True
            else:
                a["g"][l.grupo] += v
            a["areas"][l.area] += v
        ufs[l.uf][l.ano]["est"] += 0.0 if l.ibge else v
        if l.ibge:
            mun[l.ibge][l.ano]["aut"][(l.uf, quem)] += v
        if chave:
            d = deps[chave][l.ano]
            if l.ibge:
                d["cid"][l.ibge] += v
            else:
                d["est"] += v

    def r(x: float) -> int:
        return round(x)

    def fechar(a: dict, uf: str, ano: int) -> dict:
        o = {"v": r(a["v"]), "i": r(a["i"]), "p": r(a["p"]) if tem_pago[uf] and a["temP"] and (uf, ano) not in sem_pago_no_ano else None,
             "n": a["n"]}
        if a["pix"]:
            o["pix"] = r(a["pix"])
        if not a["gNulo"] and a["v"]:
            o["g"] = [r(x) for x in a["g"]]
        o["areas"] = [[k, r(v)] for k, v in em_ordem(a["areas"])[:MAX_AREAS] if v > 0]
        return o

    uf_do_mun = {}
    for l in linhas:
        if l.ibge:
            uf_do_mun[l.ibge] = l.uf
    saida_mun = {}
    for ibge, anos in mun.items():
        uf = uf_do_mun[ibge]
        saida_mun[str(ibge)] = {}
        for ano, a in sorted(anos.items()):
            o = fechar(a, uf, ano)
            # [nome, valor, chave tse]: o nome como o estado escreve; a página troca pelo de /politicos quando há chave.
            # As emendas de bloco, bancada ou de mais de um deputado vêm juntas, com o nome "coletiva".
            o["aut"] = [["coletiva" if k[1] == "coletiva" else nomes_aut[k], r(v), k[1] if k[1].startswith("tse-") else None]
                        for k, v in sorted(a["aut"].items(), key=lambda kv: (-kv[1], str(kv[0])))[:MAX_AUTORES] if v > 0]
            o["nAut"] = sum(1 for (_, q), v in a["aut"].items() if v > 0 and q != "coletiva")
            saida_mun[str(ibge)][str(ano)] = o
    saida_uf = {uf: {str(ano): dict(fechar(a, uf, ano), semCidade=r(a["est"])) for ano, a in sorted(anos.items())} for uf, anos in ufs.items()}
    saida_dep = {}
    for chave, anos in deps.items():
        uf = next(u for (u, q) in nomes_aut if q == chave)
        saida_dep[chave] = {}
        for ano, a in sorted(anos.items()):
            o = fechar(a, uf, ano)
            o["est"] = r(a["est"])
            o["cid"] = [[ib, r(v)] for ib, v in em_ordem(a["cid"])[:MAX_CIDADES] if v > 0]
            o["nc"] = sum(1 for v in a["cid"].values() if v > 0)
            saida_dep[chave][str(ano)] = o
    anos = sorted({l.ano for l in linhas})
    estados = {}
    for uf, m in meta.items():
        anos_uf = sorted({l.ano for l in linhas if l.uf == uf})
        if anos_uf:
            estados[uf] = {**m, "anos": anos_uf, "nota": NOTAS.get(uf)}
    return {"gerado": dt.date.today().isoformat(), "anos": anos, "estados": estados,
            "mun": saida_mun, "uf": saida_uf, "deputados": saida_dep}


def juntar(novo: dict, velho: dict, lidos: set[str]) -> dict:
    """Os estados não lidos agora (fora do --uf, ou que falharam) ficam como estavam na cópia de referência."""
    sigla = {str(k): s for k, s in c.SIGLAS.items()}
    uf_dep = {e["chave"]: e["uf"] for e in eleitos()}
    def manter(uf: str | None) -> bool:
        return bool(uf) and uf not in lidos
    for k, v in velho.get("mun", {}).items():
        if manter("DF" if k == str(IBGE_DF) else sigla.get(k[:2])):
            novo["mun"].setdefault(k, v)
    for k, v in velho.get("uf", {}).items():
        if manter(k):
            novo["uf"].setdefault(k, v)
    for k, v in velho.get("deputados", {}).items():
        if manter(uf_dep.get(k)):
            novo["deputados"].setdefault(k, v)
    for k, v in velho.get("estados", {}).items():
        if manter(k):
            novo["estados"].setdefault(k, v)
    novo["anos"] = sorted(set(novo["anos"]) | {a for e in novo["estados"].values() for a in e["anos"]})
    return novo


def _gravar(doc: dict, *destinos: Path) -> None:
    t = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(t, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(prog="emendas-estaduais", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--uf", nargs="+", choices=sorted(ESTADOS), help="só estes estados (os outros vêm da cópia de referência)")
    p.add_argument("--sem-baixar", action="store_true", help="só copia a cópia de referência para o site")
    p.add_argument("--forcar", action="store_true", help="baixa de novo os anos fechados")
    args = p.parse_args()

    if args.sem_baixar:
        if not REFERENCIA.exists():
            sys.exit(f"sem cópia de referência em {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(c.RAIZ)} → {SAIDA.relative_to(c.RAIZ)}")
        return

    nomes = json.loads(NOMES.read_text(encoding="utf-8"))["mun"]
    ibge6 = {k[:6]: int(k) for k in nomes}
    ibge_de_txt = casador()
    def ibge_de(nome: str, uf: str) -> int | None:
        k = ibge_de_txt(nome, uf)
        return int(k) if k else None

    leitores = {"MG": lambda f: ler_mg(f), "ES": lambda f: ler_es(f, ibge6), "AC": lambda f: ler_ac(f, ibge_de),
                "PA": lambda f: ler_pa(f, ibge_de), "RJ": lambda f: ler_rj(f, ibge_de), "DF": lambda f: ler_df(f),
                "MS": lambda f: ler_ms(f, ibge_de), "SC": lambda f: ler_sc(f), "SP": lambda f: ler_sp(f, ibge_de),
                "PE": lambda f: ler_pe(f, ibge_de), "AL": lambda f: ler_al(f, ibge_de), "MA": lambda f: ler_ma(f, ibge_de),
                "SE": lambda f: ler_se(f, ibge_de)}
    escolhidos = args.uf or sorted(ESTADOS)
    linhas: list[Linha] = []
    falhou = []
    for uf in escolhidos:
        print(f"lendo {uf}…", flush=True)
        try:
            ls = leitores[uf](args.forcar)
        except Exception as e:
            print(f"  {uf} falhou: {e!r}", flush=True)
            falhou.append(uf)
            continue
        sem = sum(1 for l in ls if not l.ibge)
        print(f"  {len(ls)} linhas; {sem} sem cidade; anos {sorted({l.ano for l in ls})}", flush=True)
        linhas += ls

    lidos = {u for u in escolhidos if u not in falhou}
    doc = montar(linhas, ligar(linhas), {uf: ESTADOS[uf] for uf in lidos})
    if lidos != set(ESTADOS) and REFERENCIA.exists():
        doc = juntar(doc, json.loads(REFERENCIA.read_text(encoding="utf-8")), lidos)
        print(f"  {', '.join(sorted(set(ESTADOS) - lidos))}: ficam como estavam na cópia de referência", flush=True)
    ultimo = max(a for a in doc["anos"] if a < dt.date.today().year)
    print(f"\n{'UF':<3} {'ano':>4} {'linhas':>7} {'indicado':>10} {'pago':>10} {'sem cidade':>11}  (R$ mi, {ultimo})")
    for uf in sorted(doc["uf"]):
        a = doc["uf"][uf].get(str(ultimo))
        if a:
            pg = f"{a['p'] / 1e6:>10.1f}" if a["p"] is not None else f"{'—':>10}"
            print(f"{uf:<3} {ultimo:>4} {a['n']:>7} {a['i'] / 1e6:>10.1f} {pg} {a['semCidade'] / 1e6:>11.1f}")
    print(f"{len(doc['mun'])} cidades; {len(doc['deputados'])} deputados ligados às páginas de /politicos")
    _gravar(doc, SAIDA, REFERENCIA)
    print(f"gravado {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)}")
    if falhou:
        sys.exit(1)


if __name__ == "__main__":
    main()
