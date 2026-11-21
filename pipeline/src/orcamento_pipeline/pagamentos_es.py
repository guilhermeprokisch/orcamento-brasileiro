"""Para quem as prefeituras do Espírito Santo pagaram: os empenhos que o TCE-ES publica no dados.es.gov.br.

    uv run pagamentos --uf ES                 # baixa os arquivos de 2025 (cerca de 145 MB) e resume as 78 prefeituras
    uv run pagamentos --uf ES --refazer       # baixa de novo, mesmo se já existirem

Fonte: o conjunto "Empenhos dos municípios capixabas" (https://dados.es.gov.br/dataset/tcees-empenho),
com o que as prefeituras mandam ao Tribunal de Contas pelo CidadES, a prestação de contas mensal. Sem
cadastro. Cada ano vem em alguns ZIPs (2025: cinco; dezembro, sozinho, ocupa os dois últimos, cada um com
metade das linhas), cada um com um CSV separado por ";", em Windows-1252. Uma linha por empenho, mês e
fonte de recursos, com o **movimento do mês**: empenhado, liquidado e pago no mês (negativo quando há
anulação ou estorno), e à parte o que se pagou de restos a pagar de anos anteriores. Os ZIPs são lidos
direto, linha a linha, e o resumo soma os meses de cada empenho.

Entram todas as unidades gestoras do município: prefeitura, Câmara, fundos, autarquias (como os serviços
de água e esgoto), empresas dependentes e o instituto de previdência. O município vem pelo nome
("EsferaAdministrativa"). Consórcios, se aparecerem como unidade, ficam de fora.

O "pago" é a soma da coluna "Paga" dos empenhos do próprio ano; os restos a pagar ficam de fora, como no
"pago" da prestação de contas ao Tesouro (DCA).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir). O tribunal diz como o credor se identifica: CNPJ, CPF ou uma "inscrição
genérica" / "identificação especial", usada quase sempre para a folha ("FOLHA DE PAGAMENTO", "DIVERSOS
SERVIDORES"), que vai para "folha" pelo grupo da despesa ou pelo nome. **O CPF não vem**: o campo
chega vazio para pessoa física; o nome só serve, na memória, para contar pessoas, e nunca é gravado.

**Só responde do Brasil?** Não foi conferido; por segurança, como nos outros estados, a carga é feita
daqui e fica em pipeline/referencia/pagamentos-es.json, e a publicação automática só copia
(`pagamentos --sem-baixar`). Ler os 3 GB de CSV leva cerca de dois minutos.

Saída em site/public/data/indicadores/pagamentos-es.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida
from .fontes import CONTEXTO_TLS, USER_AGENT

CONJUNTO = "https://dados.es.gov.br/api/3/action/package_show?id=tcees-empenho"
FONTE = "Tribunal de Contas do Estado do Espírito Santo (TCE-ES), dados abertos de empenhos dos municípios (CidadES)"
PASTA = c.RAIZ / "data" / "raw" / "tce-es"

CONSORCIO = re.compile(r"(?i)cons[oó]rcio")
# Credores sem CPF nem CNPJ (inscrição genérica, identificação especial) que são a folha.
FOLHA_NOME = re.compile(r"FOLHA|SERVIDOR|FUNCIONA|FOPAG|\bPESSOAL\b|INATIVOS|APOSENTAD|PENSIONIST|SALARI|REMUNERA")


def arquivos(ano: int) -> list[tuple[str, str, int]]:
    """[(nome, endereço, tamanho)] dos ZIPs do ano, pela lista do portal."""
    req = urllib.request.Request(CONJUNTO, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as r:
        recursos = json.load(r)["result"]["resources"]
    padrao = re.compile(rf"^municipios-despesas-empenhos-\d+-{ano}$")
    achados = [(x["name"], x["url"], int(x.get("size") or 0)) for x in recursos if padrao.match(x.get("name") or "")]
    if not achados:
        raise SystemExit(f"o TCE-ES não tem os empenhos de {ano} no dados.es.gov.br")
    return sorted(achados)


def baixar(ano: int, refazer: bool = False) -> list:
    PASTA.mkdir(parents=True, exist_ok=True)
    locais = []
    for nome, url, tamanho in arquivos(ano):
        arq = PASTA / f"{nome}.zip"
        locais.append(arq)
        if arq.exists() and not refazer and (not tamanho or arq.stat().st_size == tamanho):
            continue
        print(f"baixando {url}", flush=True)
        tmp = arq.with_name(arq.name + ".parte")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=900, context=CONTEXTO_TLS) as resp, tmp.open("wb") as f:
            while bloco := resp.read(1 << 20):
                f.write(bloco)
        tmp.rename(arq)
    return locais


def linhas(arq):
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="cp1252", newline=""), delimiter=";")


def juntar(arqs, ano: int) -> tuple[dict, Counter]:
    """Soma os meses de cada empenho do ano: {município: {empenho: [atributos..., empenhado, pago]}}."""
    mun: dict[str, dict] = defaultdict(dict)
    fora: Counter = Counter()
    t0 = time.time()
    for arq in arqs:
        for i, l in enumerate(linhas(arq), 1):
            if l["AnoEmpenho"] != str(ano):
                continue   # restos a pagar de anos anteriores: o "Paga" deles é zero, e o que se pagou vem em RPPPago
            chave = (l["CodigoUnidadeGestora"], l["NumeroEmpenho"])
            e = mun[l["EsferaAdministrativa"]].get(chave)
            if e is None:
                e = mun[l["EsferaAdministrativa"]][chave] = [l["UnidadeGestora"], "", "", "", l["CodigoGrupoNatureza"],
                                                              l["CodigoModalidade"], l["CodigoElemento"], 0.0, 0.0]
            if l["NomeCredorFornecedor"].strip():
                e[1], e[2], e[3] = l["NomeCredorFornecedor"], l["CodigoCredorFornecedor"], l["NomeIdentificacao"]
            e[7] += pb.valor(l["Empenhada"])
            e[8] += pb.valor(l["Paga"])
        fora["linhas"] += i
        print(f"  {arq.name}: {pq.br(i)} linhas ({time.time() - t0:.0f} s)", flush=True)
    return mun, fora


def linha(chave: tuple, e: list) -> pq.Linha:
    unidade, nome, codigo, ident, grupo, modalidade, elemento, empenhado, pago = e
    nome = " ".join(nome.split())
    ident = pb._sem_acento(ident)
    doc = re.sub(r"\D", "", codigo or "")
    if ident == "CPF":
        pessoa_fisica, doc = True, f"PF {nome}"   # o CPF não vem; o nome só serve para contar pessoas, na memória
    elif ident == "CNPJ":
        pessoa_fisica, doc = False, doc.zfill(14)
    else:
        # Inscrição genérica ou identificação especial: quase sempre a folha. Às vezes traz um CNPJ de verdade
        # (Banco do Brasil, por exemplo); senão, fica sem documento.
        pessoa_fisica, doc = (False, doc) if pb.cnpj_valido(doc) else (None, "")
        if FOLHA_NOME.search(pb._sem_acento(nome)):
            grupo = "1"
    if CONSORCIO.search(unidade):
        unidade = "Consórcio " + unidade
    return pq.Linha(chave="/".join(chave), unidade=unidade, doc=doc, nome=nome, pessoa_fisica=pessoa_fisica,
                    grupo=grupo.strip(), modalidade=modalidade.strip().zfill(2), elemento=elemento.strip().zfill(2),
                    empenhado=empenhado, pago=pago)


def rodar(ano: int, so: list[str] | None, pausa: float, refazer: bool = False) -> None:
    arqs = baixar(ano, refazer)
    ibge_por_nome = {pb._chave(e["ente"]): str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "ES"}
    brutos, fora = juntar(arqs, ano)
    pedidos = {pb._chave(n) for n in so} if so else None
    resultado, sem_ibge = {}, []
    for nome, empenhos in sorted(brutos.items()):
        if pedidos and pb._chave(nome) not in pedidos:
            continue
        ibge = ibge_por_nome.get(pb._chave(nome))
        if not ibge:
            sem_ibge.append(nome)
            continue
        resumo, fora_m = pq.resumir(linha(k, e) for k, e in empenhos.items())
        resultado[ibge] = resumo
        consorcio = f", consórcios R$ {pq.br(fora_m['consorcios'] / 1e6, 1)} mi fora" if fora_m["consorcios"] else ""
        print(f"  {nome}: {pq.br(len(empenhos))} empenhos, pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi{consorcio}")
    if sem_ibge:
        print(f"  sem código do IBGE (ficaram de fora): {sem_ibge}")
    print(f"ES {ano}: {pq.br(fora['linhas'])} linhas lidas")
    pagamentos_saida.gravar("ES", FONTE, ano, resultado, so)
