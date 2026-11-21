"""Para quem as prefeituras do Rio Grande do Sul pagaram: os empenhos que as 497 cidades mandam ao TCE-RS (SIAPC).

    uv run pagamentos --uf RS                              # baixa o arquivo de 2025 (1,35 GB) e resume as 497 cidades
    uv run pagamentos --uf RS --municipio "Porto Alegre"   # só uma cidade; junta-se às que já estão no arquivo

Fonte: os dados abertos do TCE-RS, "Despesa orçamentária por empenhos", um ZIP por ano
(https://dados.tce.rs.gov.br/dados/municipal/empenhos/{ano}.csv.zip), sem cadastro nem captcha. **O site
só responde do Brasil**: a carga é feita à mão, daqui, e a publicação automática só copia o resultado.

Dentro, um CSV em UTF-8 separado por vírgulas (2025: 14,7 GB, 27 milhões de linhas), lido direto do ZIP,
linha a linha. Cada linha é uma operação ("tipo_operacao": E de empenho, L de liquidação, P de
pagamento) de um empenho, com o órgão (cd_orgao: prefeitura, Câmara, autarquias, fundações, empresas
públicas dependentes e consórcios), a natureza ("cd_elemento", 3.3.90.39: categoria, grupo, modalidade e
elemento) e o credor (nm_credor, tp_pessoa PF ou PJ, cnpj_cpf). **O CPF vem inteiro**: só serve, na
memória, para contar pessoas, e nunca é gravado. As linhas vêm agrupadas por órgão, então o arquivo é
somado um órgão de cada vez (cerca de 5 minutos).

O município de cada órgão vem do cadastro de órgãos auditados do tribunal
(https://dados.tce.rs.gov.br/dados/auxiliar/orgaos_auditados_rs.csv), com o código do IBGE. Entram todos
os órgãos municipais menos os consórcios e as associações de municípios, que o cadastro põe na
cidade-sede. A empresa de transporte de Porto Alegre (EPTC), empresa pública que depende do orçamento da
cidade, entra: a prestação de contas ao Tesouro (DCA) também a conta.

**O pago é a soma dos pagamentos feitos no ano dos empenhos do próprio ano** (os estornos vêm como
pagamentos negativos). O arquivo também traz os restos a pagar de anos anteriores pagos no ano, que
ficam de fora, como no "pago" da DCA. Conferido com a DCA de 2025: Porto Alegre (R$ 9.631.957.261),
Caxias do Sul e Agudo batem ao real.

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir): operações internas (modalidade 91) fora do total; folha, previdência, dívida e
bancos e outros órgãos públicos à parte dos fornecedores; pessoas físicas só no total e na contagem.

Saída em site/public/data/indicadores/pagamentos-rs.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba. A publicação automática só copia (`pagamentos --sem-baixar`).
"""

from __future__ import annotations

import csv
import io
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida
from .fontes import CONTEXTO_TLS, USER_AGENT
from .pagamentos_mg import FOLHA_NOME, limpar_nome
from .pagamentos_pr import mei

FONTE = "Tribunal de Contas do Estado do Rio Grande do Sul (TCE-RS), dados abertos, despesa orçamentária por empenhos"
URL = "https://dados.tce.rs.gov.br/dados/municipal/empenhos/{ano}.csv.zip"
URL_ORGAOS = "https://dados.tce.rs.gov.br/dados/auxiliar/orgaos_auditados_rs.csv"
PASTA = c.RAIZ / "data" / "raw" / "tce-rs"
# Órgãos municipais que não são de uma cidade só.
FORA = {"CONSÓRCIO ADMINISTRATIVO", "ASSOCIAÇÃO"}


def baixar(url: str, arq: Path, refazer: bool = False) -> Path:
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


def orgaos(arq: Path) -> dict[str, tuple[str, str]]:
    """{cd_orgao: (código IBGE, setor)} dos órgãos municipais do cadastro do tribunal."""
    with arq.open(encoding="utf-8-sig", newline="") as f:
        return {l["CD_ORGAO"]: (l["CD_MUNICIPIO_IBGE"], l["SETOR_GOVERNAMENTAL"]) for l in csv.DictReader(f) if l["ESFERA"] == "MUNICIPAL"}


def num(s: str) -> float:
    return float(s) if s else 0.0


def ler_csv(arq: Path):
    with zipfile.ZipFile(arq) as z, z.open(next(n for n in z.namelist() if n.lower().endswith(".csv"))) as bruto:
        yield from csv.reader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""))


def orgaos_do_arquivo(linhas, ano: int):
    """(cd_orgao, nome do órgão, empenhos, restos) para cada órgão do CSV, que vem agrupado por órgão:
    empenhos = {nr_empenho: [elemento, tp_pessoa, documento, nome, empenhado, pago]} dos empenhos do ano, e
    restos = o que se pagou no ano de empenhos de anos anteriores (restos a pagar, fora do total).
    Só o órgão da vez fica na memória."""
    linhas = iter(linhas)
    col = {k: i for i, k in enumerate(next(linhas))}
    a = str(ano)
    i_org, i_nome_org, i_tipo, i_ano, i_dt, i_nr = (col[k] for k in ("cd_orgao", "nome_orgao", "tipo_operacao", "ano_empenho", "dt_operacao", "nr_empenho"))
    i_el, i_tp, i_doc, i_nome, i_ve, i_vp = (col[k] for k in ("cd_elemento", "tp_pessoa", "cnpj_cpf", "nm_credor", "vl_empenho", "vl_pagamento"))
    atual, nome_org, emp, restos, vistos = None, "", {}, 0.0, set()
    for l in linhas:
        if l[i_org] != atual:
            if atual is not None:
                yield atual, nome_org, emp, restos
            if l[i_org] in vistos:
                raise SystemExit(f"o órgão {l[i_org]} aparece em dois trechos do arquivo: a leitura por órgão não serve mais")
            atual, nome_org, emp, restos = l[i_org], l[i_nome_org], {}, 0.0
            vistos.add(atual)
        tipo = l[i_tipo]
        if l[i_ano] != a:
            if tipo == "P" and l[i_dt][:4] == a:
                restos += num(l[i_vp])
            continue
        e = emp.get(l[i_nr])
        if e is None:
            e = emp[l[i_nr]] = [l[i_el], l[i_tp], l[i_doc], l[i_nome], 0.0, 0.0]
        if tipo == "E":
            e[4] += num(l[i_ve])
        elif tipo == "P" and l[i_dt][:4] == a:
            e[5] += num(l[i_vp])
    if atual is not None:
        yield atual, nome_org, emp, restos


def linha(chave: str, unidade: str, e: list) -> pq.Linha:
    elemento, tp_pessoa, doc, nome_bruto, empenhado, pago = e
    partes = (elemento or "").split(".")
    grupo, modalidade, elemento = (partes[1], partes[2], partes[3]) if len(partes) >= 4 else ("", "", "")
    nome = limpar_nome(nome_bruto)
    doc = "".join(ch for ch in doc or "" if ch.isdigit())
    if tp_pessoa == "PJ" and pb.cnpj_valido(doc.zfill(14)):
        # Microempreendedor com o CPF no nome (o nome do MEI é o da pessoa): conta como pessoa física.
        pessoa_fisica, doc = mei(nome_bruto), doc.zfill(14)
    elif tp_pessoa == "PF" or len(doc) == 11:
        # O CPF vem inteiro: só fica na memória, para contar pessoas, e nunca é gravado.
        pessoa_fisica, doc = True, f"PF {doc} {nome}"
    else:
        pessoa_fisica, doc = None, ""
        if FOLHA_NOME.search(pb._sem_acento(nome)):
            grupo = "1"
    if pagamentos_saida.FOLHA_NOME.search(pb._sem_acento(nome)):
        grupo = "1"
    return pq.Linha(chave=chave, unidade=unidade, doc=doc, nome=nome, pessoa_fisica=pessoa_fisica, grupo=grupo,
                    modalidade=modalidade, elemento=elemento, empenhado=empenhado, pago=pago)


def rodar(ano: int, so: list[str] | None, pausa: float = 0.0, refazer: bool = False) -> None:
    arq = baixar(URL.format(ano=ano), PASTA / f"{ano}.csv.zip", refazer)
    cadastro = orgaos(baixar(URL_ORGAOS, PASTA / "orgaos_auditados_rs.csv", refazer))
    entes = {str(e["cod_ibge"]): e["ente"] for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "RS"}
    pedidos = {pb._chave(n) for n in so} if so else None
    print(f"lendo {arq}", flush=True)
    acumulado: dict[str, pq.Resumo] = defaultdict(pq.Resumo)
    fora, sem_cadastro = Counter(), []
    t0 = time.time()
    for n, (cd, nome_orgao, emp, restos) in enumerate(orgaos_do_arquivo(ler_csv(arq), ano), 1):
        ibge, setor = cadastro.get(cd, ("", ""))
        if ibge not in entes:
            sem_cadastro.append(f"{cd} {nome_orgao}")
            continue
        if pedidos and pb._chave(entes[ibge]) not in pedidos:
            continue
        fora["restos a pagar"] += restos
        if setor in FORA:
            fora["consórcios e associações"] += sum(e[5] for e in emp.values())
            continue
        for nr, e in emp.items():
            acumulado[ibge].somar(linha(f"{cd}/{nr}", nome_orgao, e))
        if n % 100 == 0:
            print(f"  {n} órgãos ({time.time() - t0:.0f} s)", flush=True)
    if sem_cadastro:
        print(f"  órgãos sem município no cadastro (ficaram de fora): {sem_cadastro}")
    resultado = {ibge: r.fechar() for ibge, r in sorted(acumulado.items())}
    if not resultado:
        raise SystemExit("nenhuma cidade lida")
    for motivo, v in fora.most_common():
        print(f"  fora do total ({motivo}): R$ {pq.br(v / 1e6, 1)} mi")
    pagamentos_saida.gravar("RS", FONTE, ano, resultado, so)
