"""Para quem as prefeituras de São Paulo pagaram: o interior pelo TCE-SP e a capital pelo TCM-SP.

    uv run pagamentos --uf SP               # as 645 cidades, 2025 (baixa cerca de 2,3 GB; leva uns minutos)
    uv run pagamentos --uf SP --refazer     # baixa os arquivos de novo

Duas fontes, porque a capital tem o seu próprio tribunal de contas:

- **644 cidades do interior e do litoral: TCE-SP (Audesp).** Um ZIP por ano com todas as prefeituras
  (https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ano}.zip, 2,1 GB em
  2025), com um CSV separado por ";" em que cada linha é uma fase de um empenho (empenhado, liquidado ou
  pago, com o valor e o mês), o órgão (prefeitura, Câmara, autarquias, fundações, instituto de
  previdência), o credor (nome e CPF/CNPJ) e a classificação da despesa. O CSV é lido direto do ZIP,
  linha a linha, e o ZIP é apagado no fim (são muitos GB).
- **A capital: TCM-SP.** Um CSV por ano com todos os empenhos da cidade de São Paulo
  (https://iris.tcm.sp.gov.br/assets/data/empenho/Empenho{ano}.csv, 180 MB em 2025; documentação em
  https://observatorio.tcm.sp.gov.br/Pagina/67782), uma linha por empenho, com o credor (CPF_CNPJ e
  Razão Social), a classificação e os valores empenhado, liquidado e pago no próprio ano (o que fica para
  o ano seguinte, restos a pagar, vem em colunas à parte e não entra). Entram a prefeitura, a Câmara, o
  Tribunal de Contas do Município, os fundos (inclusive os da previdência, FUNPREV e FUNFIN), as
  autarquias, as fundações e as empresas da prefeitura que dependem do orçamento dela (COHAB, SP
  Urbanismo, SPCine). O arquivo vem em CP850 (a codificação do DOS), com o cabeçalho estragado: as
  colunas são lidas pela posição, conferida antes da carga.

**Os dois servidores só respondem do Brasil** (como os de AC, SC e PE). A carga é feita à mão, de um
computador no Brasil, e fica em pipeline/referencia/pagamentos-sp.json; a publicação automática só copia
(`pagamentos --sem-baixar`).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py): só o pago no ano conta; operações entre
unidades do município (modalidade 91) ficam fora do total; folha, previdência, dívida e bancos e outros
órgãos públicos à parte dos fornecedores; consórcios fora; pessoas físicas só no total e na contagem.
**O CPF é descartado na leitura**: da pessoa física só se guarda, na memória, um número embaralhado
(hash) para contar quantas pessoas são, e nem o nome nem o número vão para o arquivo. O CNPJ só é
guardado para pessoa jurídica.

Conferido com o que as prefeituras declararam ao Tesouro (DCA 2025, pago com ou sem as operações internas,
a mais próxima): das 643 cidades com DCA de 2025, 640 batem a menos de 5% e 636 a menos de 1%; a capital fica
0,005% abaixo (R$ 105.881 mi contra 105.887 mi). Destoam Ibirarema (+5,9%), Guaraci (+12,9%) e Rio das Pedras
(+13%), todas acima: o serviço de água (em Ibirarema e Rio das Pedras) ou o fundo de previdência
(Guaraci) pagou boa parte da diferença, e parecem ter ficado fora da conta mandada ao Tesouro.
Brotas e Sarutaiá só têm a DCA de 2024.

Saída em site/public/data/indicadores/pagamentos-sp.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba.
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
import zipfile
from collections import Counter, defaultdict

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as qlik
from .fontes import CONTEXTO_TLS, USER_AGENT

URL_TCE = "https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ano}.zip"
URL_TCM = "https://iris.tcm.sp.gov.br/assets/data/empenho/Empenho{ano}.csv"
PASTA_TCE = c.RAIZ / "data" / "raw" / "tce-sp"
PASTA_TCM = c.RAIZ / "data" / "raw" / "tcm-sp"
FONTE = "Tribunal de Contas do Estado de São Paulo (TCE-SP), dados abertos de despesas dos municípios"
FONTE_CAPITAL = "Tribunal de Contas do Município de São Paulo (TCM-SP), dados abertos de empenhos da prefeitura"
CAPITAL = "3550308"
csv.field_size_limit(1 << 30)


def baixar(url: str, arq, refazer: bool = False):
    if arq.exists() and not refazer:
        return arq
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".parte")
    print(f"baixando {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as resp, tmp.open("wb") as f:
        while bloco := resp.read(1 << 20):
            f.write(bloco)
    tmp.rename(arq)
    return arq


# Credores que os arquivos de SP trazem com nomes que as regras da Paraíba não reconhecem. Só valem para quem
# teria virado fornecedor ou pessoa física: um "FOLHA DE PAGAMENTO" com o CNPJ da própria prefeitura (em Santo
# André, R$ 65 mi em 2025), o serviço de água da própria cidade, FGTS, Pasep (FAT), associações de municípios.
FOLHA_NOME = re.compile(r"FOLHA (DE )?(PAG|PGT)|^FOLHA D[OA] |[(-] ?FOLHA\b|(EM|CONFORME) FOLHA|^PENS(AO|OES) (JUDICIA|ALIMENT)"
                        r"|FUNDO DE GARANTIA|\bFGTS\b|F\.G\.T\.S")
PREVIDENCIA_SP = re.compile(r"I\.N\.S\.S")
ORGAO_SP = re.compile(r"^SAAE\b|SERVI[CÇ]O AUT[OÔ]NOMO|^SERV\.? AUT|^MUNICIPIO\b|FUNDO DE AMPARO AO TRABALHADOR|^FUNDO DESENV"
                      r"|CONSORCIO DE MUNICIPIOS|UNIAO DOS MUNICIPIOS|\bUMMES\b|\bCOMAM\b|ASSOCIACAO DOS MUNICIPIOS")
# O arquivo do TCE-SP traz alguns nomes já estragados (o "ç" virou "ï¿½"): prefere-se outra grafia do mesmo
# fornecedor ou, sem nenhuma, a razão social do cadastro de CNPJ (pagamentos_qlik.completar_nomes).
ESTRAGADO = re.compile("ï¿½|\ufffd")


def tipo_do_credor(l: qlik.Linha) -> int:
    t = qlik.tipo_do_credor(l)
    if t in (pb.EMPRESA, pb.PESSOA):
        nome = pb._sem_acento(l.nome)
        if PREVIDENCIA_SP.search(nome):
            return pb.PREVIDENCIA
        if FOLHA_NOME.search(nome):
            return pb.FOLHA
        if ORGAO_SP.search(nome):
            return pb.ORGAO
    return t


def nome_limpo(nomes: Counter) -> str:
    limpos = Counter({n: q for n, q in nomes.items() if not ESTRAGADO.search(n)})
    return qlik.nome_mais_comum(limpos)


class Acumulador:
    """Os empenhos de um município, somados como em pagamentos_qlik.resumir, mas linha a linha."""

    def __init__(self):
        self.pago = self.empenhado = self.intra = self.consorcios = 0.0
        self.tipos = [0.0] * len(pb.TIPOS)
        self.pessoas: set[int] = set()
        self.pagos: set[int] = set()   # empenhos com pagamento
        self.linhas = 0
        self.empresas = defaultdict(lambda: [Counter(), Counter(), 0.0, set()])

    def somar(self, l: qlik.Linha, doc_pessoa: str = "") -> None:
        """Uma linha com o empenhado e/ou o pago de um empenho (no TCE-SP, cada fase vem numa linha; um
        empenho pago em várias vezes conta uma vez só, pela chave). `doc_pessoa` (o CPF, ou o código que o
        tribunal põe no lugar dele) só serve para contar pessoas: vira um hash na memória e é jogado fora."""
        if pb.CONSORCIO_UG.match(l.unidade):
            self.consorcios += l.pago
            return
        if l.modalidade == "91":
            self.intra += l.pago
            return
        self.empenhado += l.empenhado
        if not l.pago:
            return
        t = tipo_do_credor(l)
        self.linhas += 1
        chave = hash(l.chave) if l.chave else self.linhas
        self.pago += l.pago
        self.pagos.add(chave)
        self.tipos[t] += l.pago
        if t == pb.PESSOA:
            self.pessoas.add(hash(doc_pessoa or l.doc or l.nome))
        elif t == pb.EMPRESA:
            e = self.empresas[l.doc[:8]]   # filiais da mesma empresa juntas, pela raiz do CNPJ
            e[0][l.nome] += 1
            e[1][l.doc] += l.pago
            e[2] += l.pago
            e[3].add(chave)

    def resumo(self) -> dict:
        empresas = sorted(self.empresas.values(), key=lambda e: -e[2])
        return {
            "pago": round(self.pago), "empenhado": round(self.empenhado), "n": len(self.pagos),
            "tipos": [round(v) for v in self.tipos], "intra": round(self.intra),
            "pessoas": len(self.pessoas), "empresas": len(self.empresas),
            "credores": [[nome_limpo(e[0]), e[1].most_common(1)[0][0], round(e[2]), len(e[3])] for e in empresas[:pb.MAIORES]],
        }


# ---------------------------------------------------------------------------------------- capital (TCM-SP)

# Posição das colunas no CSV do TCM-SP. O cabeçalho vem com os acentos estragados; por isso a carga
# confere estes nomes sem acento (só as letras ASCII) antes de ler.
COLUNAS_TCM = {
    "exercicio": (2, "Exerc"), "sigla": (5, "Sigla da empresa"), "empresa": (6, "Descri"),
    "grupo": (23, "digo do grupo de natureza da despesa"), "modalidade": (25, "digo da modalidade de aplica"),
    "elemento": (27, "digo do elemento de despesa"), "doc": (36, "CPF_CNPJ"), "nome": (37, "Raz"),
    "empenhado": (38, "Valor do empenho"), "cancelado": (39, "Cancelado"), "pago": (41, "Pago"),
}


def linhas_tcm(arq):
    with arq.open(encoding="cp850", newline="") as f:
        r = csv.reader(f)
        cab = next(r)
        for nome, (i, texto) in COLUNAS_TCM.items():
            if texto not in cab[i]:
                raise SystemExit(f"TCM-SP: a coluna {i} deveria ser {texto!r} e é {cab[i]!r}; o arquivo mudou")
        n = len(cab)
        for l in r:
            # Algumas observações trazem uma vírgula a mais; as colunas usadas vêm antes delas.
            if len(l) < n:
                raise SystemExit(f"TCM-SP: linha com {len(l)} colunas em vez de {n}: {l[:3]}")
            yield l


def resumir_tcm(arq, ano: int) -> tuple[dict, dict]:
    m = Acumulador()
    fora = {"linhas": 0, "outro_ano": 0, "unidades": Counter()}
    col = {k: i for k, (i, _) in COLUNAS_TCM.items()}
    for l in linhas_tcm(arq):
        fora["linhas"] += 1
        if l[col["exercicio"]] != str(ano):
            fora["outro_ano"] += 1
            continue
        doc = re.sub(r"\D", "", l[col["doc"]])
        pessoa = len(doc) == 11
        # Empenhado como na DCA: o valor do empenho menos o que foi cancelado.
        empenhado = float(l[col["empenhado"]] or 0) - float(l[col["cancelado"]] or 0)
        pago = float(l[col["pago"]] or 0)
        unidade = l[col["empresa"]]
        fora["unidades"][unidade] += pago
        m.somar(qlik.Linha(
            chave="", unidade=unidade, doc="" if pessoa else doc.zfill(14), nome=" ".join(l[col["nome"]].split()),
            pessoa_fisica=pessoa, grupo=l[col["grupo"]].strip(), modalidade=l[col["modalidade"]].strip().zfill(2),
            elemento=l[col["elemento"]].strip().zfill(2), empenhado=empenhado, pago=pago,
        ), doc_pessoa=doc if pessoa else "")
    return m.resumo(), fora


# ---------------------------------------------------------------------------------------- interior (TCE-SP)

COLUNAS_TCE = ["ano_exercicio", "codigo_municipio_ibge", "ds_orgao", "tp_despesa", "nr_empenho", "tp_identificador_despesa",
               "nr_identificador_despesa", "ds_despesa", "vl_despesa", "ds_elemento"]
# Fases de cada empenho: o empenhado é o empenho mais os reforços, menos as anulações.
EMPENHADO = {"Empenhado": 1, "Reforço": 1, "Anulação": -1}
PAGO = "Valor Pago"
FASES = {*EMPENHADO, PAGO, "Valor Liquidado"}


def linhas_tce(arq):
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            r = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
            cab = next(r)
            if faltam := [k for k in COLUNAS_TCE if k not in cab]:
                raise SystemExit(f"TCE-SP: faltam as colunas {faltam} no arquivo; ele mudou")
            yield {k: cab.index(k) for k in COLUNAS_TCE}, len(cab)
            yield from r


def resumir_tce(arq, ano: int, ibges: set[str]) -> tuple[dict, dict]:
    mun: dict[str, Acumulador] = defaultdict(Acumulador)
    fora = {"linhas": 0, "tortas": 0, "outro_ano": Counter(), "sem_ibge": Counter(), "fases": Counter(), "negativo": Counter(),
            "unidades": Counter(), "identificador": Counter()}
    it = linhas_tce(arq)
    col, n = next(it)
    i_ano, i_ibge, i_orgao, i_fase, i_emp, i_tipo, i_doc, i_nome, i_valor, i_elem = (col[k] for k in COLUNAS_TCE)
    for l in it:
        fora["linhas"] += 1
        if len(l) != n:
            fora["tortas"] += 1
            continue
        fase = l[i_fase]
        v = pb.valor(l[i_valor])
        fora["fases"][fase] += v
        if v < 0:
            fora["negativo"][fase] += 1
        if fase not in FASES:
            continue
        if fase == "Valor Liquidado":
            continue
        # "22-2025": o número do empenho traz o ano. Pagamento de empenho de outro ano (restos a pagar) não entra,
        # como no "pago" da prestação de contas ao Tesouro.
        if l[i_ano] != str(ano) or not l[i_emp].strip().endswith(f"-{ano}"):
            fora["outro_ano"][fase] += v
            continue
        ibge = l[i_ibge].strip()
        if ibge not in ibges:
            fora["sem_ibge"][ibge] += v
            continue
        tipo = l[i_tipo]
        pessoa = "FÍSICA" in tipo
        doc = re.sub(r"\D", "", l[i_doc]) if "CNPJ" in tipo else ""
        fora["identificador"][tipo] += 1
        elem = re.sub(r"\D", "", l[i_elem].split(" - ")[0])   # "33903905 - SERVIÇOS…": categoria, grupo, modalidade, elemento, item
        orgao = " ".join(l[i_orgao].split())
        pago = v if fase == PAGO else 0.0
        if pago:
            fora["unidades"][orgao.upper()] += pago
        mun[ibge].somar(qlik.Linha(
            chave=f"{orgao}|{l[i_emp].strip()}", unidade=orgao, doc=doc.zfill(14) if doc else "", nome=" ".join(l[i_nome].split()),
            pessoa_fisica=pessoa, grupo=elem[1:2], modalidade=elem[2:4], elemento=elem[4:6],
            empenhado=EMPENHADO.get(fase, 0) * v, pago=pago,
        ), doc_pessoa=l[i_doc] if pessoa else "")
        if fora["linhas"] % 2_000_000 == 0:
            print(f"  {qlik.br(fora['linhas'])} linhas", flush=True)
    return {ibge: m.resumo() for ibge, m in mun.items()}, fora


# ---------------------------------------------------------------------------------------- carga

ENTRA = ("a prefeitura, a Câmara e, onde existem, as autarquias (como o serviço de água e esgoto), as fundações, "
         "as empresas que dependem do orçamento da prefeitura e o instituto de previdência")
ENTRA_CAPITAL = ("a prefeitura, a Câmara, o Tribunal de Contas do Município, as autarquias (como o Hospital do Servidor), "
                 "as fundações, as empresas que dependem do orçamento da prefeitura (como a COHAB e a SP Urbanismo) "
                 "e os fundos da previdência")


def rodar(ano: int, refazer: bool = False, manter: bool = False) -> None:
    ibges = {str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "SP"}

    arq_tcm = baixar(URL_TCM.format(ano=ano), PASTA_TCM / f"Empenho{ano}.csv", refazer)
    capital, fora_tcm = resumir_tcm(arq_tcm, ano)
    capital.update(fonte=FONTE_CAPITAL, entra=ENTRA_CAPITAL)
    print(f"capital (TCM-SP): {qlik.br(fora_tcm['linhas'])} empenhos, pago R$ {qlik.br(capital['pago'] / 1e9, 2)} bi"
          f" (mais R$ {qlik.br(capital['intra'] / 1e9, 2)} bi entre unidades)", flush=True)
    if fora_tcm["outro_ano"]:
        print(f"  empenhos de outro ano (fora): {fora_tcm['outro_ano']}")

    arq_tce = baixar(URL_TCE.format(ano=ano), PASTA_TCE / f"despesas-{ano}.zip", refazer)
    print(f"lendo {arq_tce.name} (o CSV dentro tem uns 15 GB; leva alguns minutos)", flush=True)
    mun, fora = resumir_tce(arq_tce, ano, ibges - {CAPITAL})
    print(f"interior (TCE-SP): {qlik.br(fora['linhas'])} linhas, {len(mun)} municípios, pago R$ "
          f"{qlik.br(sum(m['pago'] for m in mun.values()) / 1e9, 2)} bi")
    print(f"  por fase (R$ bi): { {k: round(v / 1e9, 2) for k, v in fora['fases'].items()} }")
    for chave in ("tortas", "outro_ano", "sem_ibge", "negativo", "identificador"):
        if fora[chave]:
            print(f"  {chave}: {fora[chave] if chave != 'sem_ibge' else dict(fora[chave].most_common(5))}")
    consorcios = sum(1 for u in fora["unidades"] if pb.CONSORCIO_UG.match(u))
    print(f"  {len(fora['unidades'])} unidades com pagamento ({consorcios} consórcios, fora do total)")
    if faltam := sorted(ibges - set(mun) - {CAPITAL}):
        print(f"  cidades sem nenhum pagamento no arquivo: {faltam}")

    mun[CAPITAL] = capital
    if sem_nome := qlik.completar_nomes(mun):
        print(f"  {sem_nome} fornecedores sem nome nem no cadastro de CNPJ: aparecem pelo CNPJ")
    destino, referencia = qlik.saida("SP")
    doc = {"fonte": FONTE, "ano": ano, "uf": "SP", "tipos": pb.TIPOS, "entra": ENTRA, "mun": dict(sorted(mun.items()))}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for arq in (destino, referencia):
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(texto, encoding="utf-8")
    print(f"saída: {destino.relative_to(c.RAIZ)} ({len(mun)} municípios, {len(texto) / 1e3:.0f} KB) e {referencia.relative_to(c.RAIZ)}")
    if not manter:
        arq_tce.unlink()   # 2 GB: o resumo já está guardado (rodar(ano, manter=True) guarda o ZIP para ler de novo)
        print(f"  apagado {arq_tce.relative_to(c.RAIZ)} (2 GB; o resumo já está gravado)")
