"""A verba dos deputados estaduais (verba de gabinete, indenizatória ou de desempenho, conforme o estado), nas
Assembleias que publicam o gasto nota a nota, com o CNPJ, em arquivo ou API aberta. Usado por politicos.py.

Por ora: SP (ALESP), MG (ALMG), GO (ALEGO), MS (ALEMS), PE (Alepe) e CE (Alece). O levantamento de todas as 27
Casas está em docs/levantamento-parlamentar.md, seção 9.

Cada linha normalizada é (uf, dep, nome, ano, mes, cat, forn, doc, valor):
- dep: o id do deputado na Assembleia, ou o nome quando a Casa não dá id (MS e CE);
- doc: o CNPJ (14 dígitos), "PF" para pessoa física ou "" quando a fonte não diz. **O CPF nunca é lido**: quando o
  documento tem 11 dígitos, só fica a marca "PF", e o nome do fornecedor pessoa física também não é guardado.

Cache em data/raw/assembleias/<uf>/<ano>.csv (já normalizado, sem CPF e sem nome de pessoa física). Os anos fechados
não são baixados de novo; o ano corrente e o anterior, sim.
"""

from __future__ import annotations

import concurrent.futures as cf
import csv
import datetime as dt
import io
import json
import re
import ssl
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from .cidades import RAIZ

PASTA = RAIZ / "data" / "raw" / "assembleias"
UA = "Mozilla/5.0 (orcamento-brasileiro; dados abertos)"
PRIMEIRO_ANO = 2023
COLUNAS = ["uf", "dep", "nome", "ano", "mes", "cat", "forn", "doc", "v"]
UFS = ("SP", "MG", "GO", "MS", "PE", "CE")

# O que cada Casa chama de verba, para a página.
NOME_VERBA = {"SP": "verba de gabinete", "MG": "verba indenizatória", "GO": "verba indenizatória",
              "MS": "cota parlamentar", "PE": "verba indenizatória", "CE": "verba de desempenho parlamentar"}

# A ALESP manda o certificado sem o intermediário (Let's Encrypt YE1): a cadeia vai junto, pública, sem desligar a
# verificação.
URL_LE_YE1 = "https://letsencrypt.org/certs/gen-y/int-ye1.pem"

MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
         "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


# ---------------------------------------------------------------- utilidades

def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def ano_corrente() -> int:
    return dt.date.today().year


def anos() -> list[int]:
    return list(range(PRIMEIRO_ANO, ano_corrente() + 1))


_ctx_alesp: ssl.SSLContext | None = None


def _contexto(url: str) -> ssl.SSLContext | None:
    global _ctx_alesp
    if "al.sp.gov.br" not in url:
        return None
    if _ctx_alesp is None:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(urllib.request.Request(URL_LE_YE1, headers={"User-Agent": UA}), timeout=60) as r:
            ctx.load_verify_locations(cadata=r.read().decode("ascii"))
        _ctx_alesp = ctx
    return _ctx_alesp


def abrir(url: str, tentativas: int = 4, timeout: int = 120) -> bytes:
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/csv, */*"})
            with urllib.request.urlopen(req, timeout=timeout, context=_contexto(url)) as r:
                return r.read()
        except Exception as e:   # noqa: BLE001 — rede instável: tenta de novo e, no fim, levanta
            if i == tentativas - 1:
                raise
            print(f"  {url}: {e}; tentando de novo", flush=True)
            time.sleep(4 * (i + 1))
    raise RuntimeError("inalcançável")


def jabrir(url: str, **kw):
    return json.loads(abrir(url, **kw))


def so_digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def documento(s) -> str:
    """CNPJ com 14 dígitos; "PF" para CPF (com ou sem máscara); "" para o resto. O CPF não sai daqui."""
    bruto = str(s or "")
    d = so_digitos(bruto)
    if len(d) == 14:
        return d
    if len(d) == 11 or "*" in bruto:
        return "PF"
    return ""


def valor(s) -> float:
    """"R$ 1.234,56", "1234,56", "1234.56" ou número."""
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s or "").replace("R$", "").strip()
    if not t:
        return 0.0
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


CPF_NO_NOME = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{11}")


def fornecedor(forn, doc: str) -> str:
    """O nome do fornecedor, como guardado: vazio para pessoa física; "MEI" quando o nome traz um CPF colado (o
    microempreendedor costuma vir "FULANO DE TAL 12345678900"): nem o nome nem o CPF ficam."""
    if doc == "PF":
        return ""
    f = " ".join(str(forn or "").split())
    return "MEI" if CPF_NO_NOME.search(f) else f


def linha(uf, dep, nome, ano, mes, cat, forn, doc, v) -> list:
    doc = documento(doc) if doc not in ("PF", "") else doc
    return [uf, str(dep), " ".join(str(nome or "").split()), int(ano), int(mes), " ".join(str(cat or "").split()),
            fornecedor(forn, doc), doc, round(valor(v), 2)]


# As categorias de cada Casa, num nome curto comum. A ordem importa: a primeira regra que bate vale.
CATEGORIAS = [
    (r"beneficio (alimentacao|refeicao)|vale.(alimentacao|refeicao)", "Vale-alimentação e refeição"),
    (r"combust", "Combustível"),
    (r"divulga|publicidade|propaganda", "Divulgação do mandato"),
    (r"consultor|assessoria|tecnicos profissionais|pesquisa", "Consultorias e assessorias"),
    (r"locacao de veiculo|veiculo|transporte|fretamento", "Carro e transporte"),
    (r"pedagio|estacionamento|taxi", "Táxi, pedágio e estacionamento"),
    (r"passage|hospedagem|alimentacao|locomocao|viage|diaria", "Viagens, hospedagem e alimentação"),
    (r"moradia", "Moradia"),
    (r"^manutencao|condominio", "Escritório e manutenção"),
    (r"grafic|copia|impress", "Gráfica e cópias"),
    (r"material|expediente|consumo", "Material de escritório"),
    (r"software|equipamento|bens moveis|informatica|assinatura|periodico|publicac", "Equipamentos, software e assinaturas"),
    (r"servicos? de utilidade|serv\.? ?util|energia|agua", "Telefone, luz e água"),
    (r"telefon|internet|comunicacao|postais|correio|dados", "Telefone, internet e correio"),
    (r"imove|imovel|aluguel|condominio|manutencao|escritorio", "Escritório e manutenção"),
    (r"seguranca", "Segurança"),
    (r"evento|curso", "Eventos e cursos"),
]


def categoria(texto: str) -> str:
    t = sem_acento(texto or "").lower()
    t = re.sub(r"^[a-z]\s*-\s*", "", t)        # "A - COMBUSTÍVEIS" (ALESP)
    t = re.sub(r"^\d+\s*-\s*", "", t)          # "02 - COMUNICAÇÃO" (ALEGO)
    for padrao, nome in CATEGORIAS:
        if re.search(padrao, t):
            return nome
    return "Outros"


# ---------------------------------------------------------------- SP: ALESP

URL_SP = "https://www3.al.sp.gov.br/repositorio/dados-abertos/output/json/{arq}.json"


def sp(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    """Um arquivo com 2002 até hoje (~160 MB). Só as colunas sem dado pessoal; o `cpf` não é lido."""
    bruto = json.loads(abrir(URL_SP.format(arq="despesas"), timeout=600))
    por_ano: dict[int, list] = {a: [] for a in anos_}
    for x in bruto.get("despesas", []):
        a = int(x.get("ano") or 0)
        if a not in por_ano:
            continue
        pf = (x.get("tipoFornecedor") or "").upper() == "PF"
        doc = "PF" if pf else documento(x.get("cnpj"))
        por_ano[a].append(linha("SP", x.get("matricula"), x.get("deputado"), a, x.get("mes"), x.get("tipo"),
                                x.get("fornecedor"), doc, valor(x.get("valor"))))
    del bruto
    deps: dict[str, dict] = {}
    lista = json.loads(abrir(URL_SP.format(arq="deputados")))
    lista = lista.get("deputados", lista) if isinstance(lista, dict) else lista
    if isinstance(lista, dict):
        lista = next(iter(lista.values()))
    gabinete = {}
    for d in lista:
        foto = d.get("fotoGrande") or ""
        arq = foto.rsplit("/", 1)[-1]
        deps[str(d.get("matricula"))] = {
            "nome": d.get("nomeDeputado"), "partido": d.get("siglaPartido"),
            # Só o formato antigo da foto tem endereço conhecido (repositorio/deputadoPortal/fotos/<arquivo>).
            "foto": f"https://www.al.sp.gov.br/repositorio/deputadoPortal/fotos/{arq}" if re.match(r"^\d{8}-\d{6}-id=", arq) else None,
            "atual": d.get("situacaoMandatoAtual") == "EXE",
        }
        if d.get("idGabinete"):
            gabinete[str(d["idGabinete"])] = str(d.get("matricula"))
    # Assessores: quantas pessoas em cada "GABINETE DEP. X" (a unidade tem o mesmo id do gabinete). Nomes não ficam.
    lot = json.loads(abrir(URL_SP.format(arq="lotacoes"), timeout=300))
    lot = next(iter(lot.values())) if isinstance(lot, dict) else lot
    conta = Counter(str(x.get("idUA")) for x in lot if "GABINETE DEP" in (x.get("nomeUA") or "").upper())
    del lot
    for ua, n in conta.items():
        if ua in gabinete and gabinete[ua] in deps:
            deps[gabinete[ua]]["assessores"] = n
    return por_ano, deps


# ---------------------------------------------------------------- MG: ALMG

URL_MG = "https://dadosabertos.almg.gov.br/api/v2"


def mg(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    """A API, deputado a deputado e mês a mês (o CSV em lote fica num caminho que o robots.txt bloqueia)."""
    deps: dict[str, dict] = {}
    for caminho in ("deputados/em_exercicio", "deputados/que_exerceram_mandato", "deputados/que_se_afastaram",
                    "deputados/que_renunciaram", "deputados/que_perderam_mandato"):
        try:
            for d in jabrir(f"{URL_MG}/{caminho}?formato=json").get("list", []):
                deps.setdefault(str(d["id"]), {"nome": d.get("nome"), "partido": d.get("partido"),
                                               "foto": f"https://www.almg.gov.br/export/sites/portal/a-assembleia/deputados/fotos/{d['id']}.jpg",
                                               "atual": caminho.endswith("em_exercicio")})
        except Exception as e:   # noqa: BLE001
            print(f"  ALMG {caminho}: {e}", flush=True)

    def um(id_: str, a: int, m: int):
        try:
            d = jabrir(f"{URL_MG}/prestacao_contas/verbas_indenizatorias/deputados/{id_}/{a}/{m}?formato=json", tentativas=3)
        except Exception as e:   # noqa: BLE001
            print(f"  ALMG {id_} {a}/{m}: {e}", flush=True)
            return []
        out = []
        for grupo in d.get("list", []):
            cat = grupo.get("descTipoDespesa")
            for n in grupo.get("listaDetalheVerba") or []:
                out.append(linha("MG", id_, deps[id_]["nome"], a, m, cat, n.get("nomeEmitente"), documento(n.get("cpfCnpj")),
                                 valor(n.get("valorReembolsado"))))
        return out

    pedidos = []
    for id_ in deps:
        try:
            d = jabrir(f"{URL_MG}/prestacao_contas/verbas_indenizatorias/deputados/{id_}/datas?formato=json")
            datas = d.get("listaFechamentoVerba") or d.get("list") or []
        except Exception as e:   # noqa: BLE001
            print(f"  ALMG datas {id_}: {e}", flush=True)
            continue
        for x in datas:
            ref = (x.get("dataReferencia") or {}).get("$", "") if isinstance(x.get("dataReferencia"), dict) else str(x.get("dataReferencia") or x)
            mm = re.match(r"(\d{4})-(\d{2})", ref)
            if mm and int(mm.group(1)) in anos_:
                pedidos.append((id_, int(mm.group(1)), int(mm.group(2))))
    por_ano: dict[int, list] = {a: [] for a in anos_}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for (id_, a, m), linhas in zip(pedidos, ex.map(lambda p: um(*p), pedidos)):
            por_ano[a] += linhas
    return por_ano, deps


# ---------------------------------------------------------------- GO: ALEGO

URL_GO = "https://transparencia.al.go.leg.br/api/transparencia/verbas_indenizatorias"


def go(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    periodos = {p["ano"]: sorted(p["meses"]) for p in jabrir(f"{URL_GO}/periodos")}
    deps: dict[str, dict] = {}
    pedidos = []
    for a in anos_:
        for m in periodos.get(a, []):
            for d in jabrir(f"{URL_GO}/deputados?ano={a}&mes={m}"):
                pedidos.append((str(d["id"]), a, m))
                deps.setdefault(str(d["id"]), {"nome": d.get("nome")})

    def um(id_: str, a: int, m: int):
        try:
            d = jabrir(f"{URL_GO}/exibir?ano={a}&mes={m}&deputado_id={id_}", tentativas=3)
        except Exception as e:   # noqa: BLE001
            print(f"  ALEGO {id_} {a}/{m}: {e}", flush=True)
            return None, []
        out = []
        for g in d.get("grupos") or []:
            for sg in g.get("subgrupos") or []:
                for l in sg.get("lancamentos") or []:
                    f = l.get("fornecedor") or {}
                    out.append(linha("GO", id_, (d.get("deputado") or {}).get("nome"), a, m, g.get("descricao"),
                                     f.get("nome"), documento(f.get("cnpj_cpf")), valor(f.get("valor_indenizado"))))
        return d.get("deputado") or {}, out

    por_ano: dict[int, list] = {a: [] for a in anos_}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for (id_, a, m), (info, linhas) in zip(pedidos, ex.map(lambda p: um(*p), pedidos)):
            por_ano[a] += linhas
            if info:
                deps[id_].update({"nome": info.get("nome") or deps[id_]["nome"], "partido": info.get("partido"),
                                  "foto": info.get("foto")})
    return por_ano, deps


# ---------------------------------------------------------------- MS: ALEMS

URL_MS = "https://transparencia2.al.ms.gov.br/ceap/notas/exportar-csv?ano={ano}"


def ms(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    """Um CSV por ano, com 5 linhas de título antes da tabela. Sem id do deputado: a chave é o nome."""
    por_ano: dict[int, list] = {}
    for a in anos_:
        texto = abrir(URL_MS.format(ano=a), timeout=300).decode("utf-8-sig", "replace")
        linhas_ = texto.splitlines()
        ini = next(i for i, l in enumerate(linhas_) if l.startswith("Deputado;"))
        out = []
        for r in csv.DictReader(io.StringIO("\n".join(linhas_[ini:])), delimiter=";"):
            m = MESES.get(sem_acento(r.get("Mês") or "").lower())
            if not m:
                continue
            nome = re.sub(r"^dep\.?\s+", "", (r.get("Deputado") or "").strip(), flags=re.I)
            out.append(linha("MS", nome.upper(), nome, a, m, r.get("Categoria"), r.get("Fornecedor"),
                             documento(r.get("CPF/CNPJ")), valor(r.get("Valor (R$)"))))
        por_ano[a] = out
    return por_ano, {}


# ---------------------------------------------------------------- PE: Alepe

URL_PE = "https://www.alepe.pe.gov.br/servicos/transparencia"


def pe(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    deps = {}
    for d in jabrir(f"{URL_PE}/dep/deputados.php?leg=-16"):
        foto = d.get("foto") or ""
        deps[str(d["id"])] = {"nome": d.get("nome"), "partido": d.get("partido"),
                              "foto": f"https://www.alepe.pe.gov.br{foto}" if foto else None}

    # A nota traz só o número da rubrica; o nome vem da tabela de rubricas de cada ano.
    rubricas: dict[int, dict[int, str]] = {}
    for a in anos_:
        try:
            rubricas[a] = {int(r["numero_categoria"]): r["nome_categoria"]
                           for r in jabrir(f"{URL_PE}/adm/verbaindenizatoria-rubricas.php?ano={a}")}
        except Exception as e:   # noqa: BLE001
            print(f"  Alepe rubricas {a}: {e}", flush=True)
            rubricas[a] = {}

    def um(id_: str, a: int):
        out = []
        try:
            meses = jabrir(f"{URL_PE}/adm/verbaindenizatoria-dep-meses.php?dep={id_}&ano={a}", tentativas=3)
        except Exception as e:   # noqa: BLE001
            print(f"  Alepe {id_} {a}: {e}", flush=True)
            return out
        for mx in meses or []:
            m = mx.get("mes") if isinstance(mx, dict) else mx
            m = int(so_digitos(m) or 0) or MESES.get(sem_acento(str(m)).lower())
            if not m:
                continue
            try:
                docs = jabrir(f"{URL_PE}/adm/verbaindenizatoria.php?dep={id_}&ano={a}&mes={m}", tentativas=3)
                for doc in docs or []:
                    for n in jabrir(f"{URL_PE}/adm/verbaindenizatorianotas.php?docid={doc['docid']}", tentativas=3) or []:
                        rub = rubricas[a].get(int(so_digitos(n.get("rubrica")) or 0), str(n.get("rubrica")))
                        out.append(linha("PE", id_, deps[id_]["nome"], a, m, rub, n.get("empresa"),
                                         documento(n.get("cnpj")), valor(n.get("valor"))))
            except Exception as e:   # noqa: BLE001
                print(f"  Alepe {id_} {a}/{m}: {e}", flush=True)
        return out

    por_ano: dict[int, list] = {a: [] for a in anos_}
    pedidos = [(i, a) for i in deps for a in anos_]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for (id_, a), linhas in zip(pedidos, ex.map(lambda p: um(*p), pedidos)):
            por_ano[a] += linhas
    # Assessores: a contagem por lotação ("GAB.DEP. X"), de um período fixo que a Alepe publica.
    try:
        texto = abrir("https://dadosabertos.alepe.pe.gov.br/api/v1/lotacoes/?formato=csv").decode("utf-8-sig", "replace")
        por_nome = {_chave(d["nome"]): i for i, d in deps.items()}
        conta: Counter[str] = Counter()
        for r in csv.DictReader(io.StringIO(texto)):
            lot = (r.get("nome_lotacao") or "").upper()
            if lot.startswith("GAB.DEP."):
                i = por_nome.get(_chave(lot.removeprefix("GAB.DEP.")))
                if i:
                    conta[i] += int(r.get("total") or 0)
        for i, n in conta.items():
            deps[i]["assessores"] = n
    except Exception as e:   # noqa: BLE001
        print(f"  Alepe lotações: {e}", flush=True)
    return por_ano, deps


# ---------------------------------------------------------------- CE: Alece

URL_CE = "https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar/csv?mes={mes:02d}&ano={ano}"


def ce(anos_: list[int]) -> tuple[dict[int, list], dict[str, dict]]:
    """Um CSV por mês com todos os deputados. É por empenho (inclui contratos da Casa, como telefone), não por nota."""
    hoje = dt.date.today()
    por_ano: dict[int, list] = {}
    for a in anos_:
        out = []
        for m in range(1, 13):
            if (a, m) > (hoje.year, hoje.month):
                break
            try:
                texto = abrir(URL_CE.format(mes=m, ano=a), tentativas=3).decode("utf-8-sig", "replace")
            except Exception as e:   # noqa: BLE001
                print(f"  Alece {a}/{m}: {e}", flush=True)
                continue
            linhas_ = texto.splitlines()
            ini = next((i for i, l in enumerate(linhas_) if l.startswith("DEPUTADO;")), None)
            if ini is None:
                continue
            for r in csv.DictReader(io.StringIO("\n".join(linhas_[ini:])), delimiter=";"):
                nome = re.sub(r"^dep\.?\s+", "", (r.get("DEPUTADO") or "").strip(), flags=re.I)
                if not nome:
                    continue
                out.append(linha("CE", nome.upper(), nome, a, m, r.get("DESCRICAO"), r.get("CREDOR"),
                                 documento(r.get("CNPJ")), valor(r.get("VALOR"))))
        por_ano[a] = out
    return por_ano, {}


def categoria_ce(descricao: str) -> str:
    """A Alece não dá a categoria, só a descrição do empenho."""
    return categoria(descricao)


# ---------------------------------------------------------------- juntar

LEITORES = {"SP": sp, "MG": mg, "GO": go, "MS": ms, "PE": pe, "CE": ce}


def _chave(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(s or "").lower()).strip("-")


def carregar(ufs: tuple[str, ...] = UFS, baixar: bool = True) -> tuple[list[list], dict[str, dict]]:
    """Todas as linhas desde 2023 e os deputados de cada Casa ("<uf>-<dep>" → nome, partido, foto, assessores).
    Uma Casa que falha não derruba as outras: fica o cache. baixar=False só lê o cache."""
    todas: list[list] = []
    deputados: dict[str, dict] = {}
    for uf in ufs:
        pasta = PASTA / uf.lower()
        pasta.mkdir(parents=True, exist_ok=True)
        faltam = [a for a in anos() if a >= ano_corrente() - 1 or not (pasta / f"{a}.csv").exists()] if baixar else []
        info_arq = pasta / "deputados.json"
        try:
            t = time.time()
            novos, deps = LEITORES[uf](faltam) if faltam else ({}, {})
            for a, linhas_ in novos.items():
                if linhas_ or not (pasta / f"{a}.csv").exists():
                    with (pasta / f"{a}.csv").open("w", encoding="utf-8", newline="") as f:
                        w = csv.writer(f)
                        w.writerow(COLUNAS)
                        w.writerows(linhas_)
            if deps:
                info_arq.write_text(json.dumps(deps, ensure_ascii=False), encoding="utf-8")
            print(f"{uf}: {sum(len(x) for x in novos.values()):,} notas de {faltam} em {time.time() - t:.0f} s", flush=True)
        except Exception as e:   # noqa: BLE001 — a Casa fora do ar não impede a carga
            print(f"{uf}: falhou ({e}); fica o que já estava no cache", flush=True)
        for a in anos():
            arq = pasta / f"{a}.csv"
            if arq.exists():
                with arq.open(encoding="utf-8", newline="") as f:
                    for r in csv.DictReader(f):
                        todas.append([r["uf"], r["dep"], r["nome"], int(r["ano"]), int(r["mes"]), r["cat"], r["forn"],
                                      r["doc"], float(r["v"])])
        if info_arq.exists():
            for dep, d in json.loads(info_arq.read_text(encoding="utf-8")).items():
                deputados[f"{uf}-{dep}"] = d
    return todas, deputados
