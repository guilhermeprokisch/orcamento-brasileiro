"""Para quem as prefeituras do Paraná pagaram: os empenhos e os pagamentos que as 399 cidades mandam ao TCE-PR (SIM-AM).

    uv run pagamentos --uf PR                          # baixa o pacote de 2025 (1,4 GB) e resume as 399 cidades
    uv run pagamentos --uf PR --municipio Curitiba     # só uma cidade; junta-se às que já estão no arquivo

Fonte: o Portal Informação para Todos (PIT) do TCE-PR, um ZIP por ano com tudo o que os municípios
mandam ao tribunal (https://pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip), sem cadastro nem
captcha. Dentro, nove ZIPs por município ("{ano}_{código IBGE sem o dígito}_Despesa.zip", "…_Receita.zip",
…). Só o de despesa interessa; ele traz XMLs em UTF-8, um elemento por registro, às vezes divididos em
partes ("EmpenhoPagamento_1.xml", "_2.xml"):

- Empenho: cada empenho do ano, com a entidade (prefeitura, Câmara, fundos, autarquias, previdência e os
  consórcios sediados na cidade), a natureza (cdGrupoNatureza, cdModalidade, cdElemento) e o credor
  (sgDocCredor "CNPJ" ou "CPF", nrDocCredor, nmCredor). O CPF já vem mascarado pelo tribunal
  ("***.744.***-**") e nunca é guardado;
- EmpenhoPagamento: cada pagamento (vlOperacao, dtOperacao), ligado ao empenho pelo idEmpenho. Alguns
  campos do fim vêm com os nomes trocados (vlPagamentoBruto="BANCO"); vlOperacao e dtOperacao estão certos;
- EmpenhoPagamentoEstorno: os estornos de pagamento (vlEstorno, dtEstorno).

**O pago é a soma dos pagamentos feitos no ano, menos os estornos do ano, dos empenhos do próprio ano.**
O arquivo também traz pagamentos de empenhos de anos anteriores (restos a pagar) e, dos empenhos de
2025, o que se pagou em 2026: os dois ficam de fora, como no "pago" da prestação de contas ao Tesouro
(DCA). Conferido em Abatiá: R$ 45.131.900, igual à DCA de 2025. O campo vlPagamento do próprio empenho
não serve: inclui o que se pagou no ano seguinte.

Os consórcios de municípios (entidades com "consórcio" ou "associação intermunicipal" no nome) ficam de
fora: o arquivo põe cada um na cidade-sede, e o dinheiro é de várias cidades. (Em Laranjeiras do Sul, a
Associação Intermunicipal de Saúde do Centro Oeste pagou R$ 18,7 mi; sem ela, a cidade bate com a DCA.) Daí em diante, as mesmas regras da Paraíba (pagamentos.py)
e do resumo de AC e SC (pagamentos_qlik.resumir): operações internas (modalidade 91) fora do total;
folha, previdência, dívida e bancos e outros órgãos públicos à parte dos fornecedores; pessoas físicas só
no total e na contagem.

Saída em site/public/data/indicadores/pagamentos-pr.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba. A publicação automática só copia (`pagamentos --sem-baixar`).
"""

from __future__ import annotations

import io
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida
from .fontes import CONTEXTO_TLS, USER_AGENT
from .pagamentos_mg import FOLHA_NOME, limpar_nome

FONTE = "Tribunal de Contas do Estado do Paraná (TCE-PR), Portal Informação para Todos (PIT), dados do SIM-AM"
URL = "https://pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip"
PASTA = c.RAIZ / "data" / "raw" / "tce-pr"
NOME_ZIP = re.compile(r"^(\d{4})_(\d{6})_Despesa\.zip$")
CONSORCIO = re.compile(r"CONSORCIO|ASSOCIACAO INTERMUNICIPAL")


def baixar(ano: int, refazer: bool = False) -> Path:
    arq = PASTA / f"{ano}_PIT_TodosArquivos.zip"
    if arq.exists() and not refazer:
        return arq
    PASTA.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".parte")
    print(f"baixando {URL.format(ano=ano)} (cerca de 1,4 GB)", flush=True)
    req = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as resp, tmp.open("wb") as f:
        while bloco := resp.read(1 << 20):
            f.write(bloco)
    tmp.rename(arq)
    return arq


REFERENCIA = re.compile(rb"&#(x[0-9a-fA-F]+|\d+);")


def _sem_controle(m: re.Match) -> bytes:
    """Alguns históricos trazem caracteres de controle ("&#x1;"), que o XML não aceita: viram espaço."""
    v = m.group(1)
    n = int(v[1:], 16) if v[:1] in (b"x", b"X") else int(v)
    return b" " if n < 32 and n not in (9, 10, 13) else m.group(0)


def registros(z: zipfile.ZipFile, tabela: str):
    """Os atributos de cada <tabela .../> do XML (ou das partes dele, "_1.xml", "_2.xml"…), um de cada vez."""
    partes = re.compile(rf"_{tabela}(_\d+)?\.xml$")
    for nome in sorted(n for n in z.namelist() if partes.search(n)):
        texto = REFERENCIA.sub(_sem_controle, z.read(nome))
        for _, el in ET.iterparse(io.BytesIO(texto)):
            if el.tag == tabela:
                yield el.attrib
                el.clear()


def num(s: str | None) -> float:
    return float(s) if s else 0.0


def empenhos(z: zipfile.ZipFile, ano: int) -> tuple[dict[str, list], dict]:
    """{idEmpenho: [entidade, grupo, modalidade, elemento, tipo do documento, documento, nome, empenhado, pago]}
    dos empenhos do ano de um município, e o que ficou de fora (consórcios, restos a pagar, o pago no ano seguinte)."""
    emp, fora = {}, Counter()
    for e in registros(z, "Empenho"):
        if e.get("nrAnoEmpenho") != str(ano):
            continue
        emp[e["idEmpenho"]] = [e.get("nmEntidade", ""), e.get("cdGrupoNatureza", ""), e.get("cdModalidade", ""),
                               e.get("cdElemento", ""), (e.get("sgDocCredor") or "").strip(), e.get("nrDocCredor", ""),
                               e.get("nmCredor", ""), num(e.get("vlEmpenho")), 0.0]
    for tabela, campo, data, sinal in (("EmpenhoPagamento", "vlOperacao", "dtOperacao", 1),
                                       ("EmpenhoPagamentoEstorno", "vlEstorno", "dtEstorno", -1)):
        for p in registros(z, tabela):
            v = sinal * num(p.get(campo))
            e = emp.get(p.get("idEmpenho", ""))
            if not e:
                fora["restos a pagar"] += v
            elif (p.get(data) or "")[:4] != str(ano):
                fora["pago no ano seguinte"] += v
            else:
                e[8] += v
    for k in [k for k, e in emp.items() if CONSORCIO.search(pb._sem_acento(e[0]))]:
        fora["consórcios"] += emp.pop(k)[8]
    return emp, fora


def mei(nome: str) -> bool:
    """O nome traz um CPF ou começa pela raiz do CNPJ ("12.345.678 FULANA DE TAL"): é um microempreendedor."""
    return bool(pagamentos_saida.CPF_NO_NOME.search(nome or "") or pb.MEI.search(nome or ""))


def linha(chave: str, e: list) -> pq.Linha:
    entidade, grupo, modalidade, elemento, tipo_doc, doc_bruto, nome_bruto, empenhado, pago = e
    nome = limpar_nome(nome_bruto)
    doc = re.sub(r"\D", "", doc_bruto or "")
    if tipo_doc == "CNPJ" and pb.cnpj_valido(doc.zfill(14)):
        # Microempreendedor com o CPF no nome (o nome do MEI é o da pessoa): conta como pessoa física.
        pessoa_fisica, doc = mei(nome_bruto), doc.zfill(14)
    elif tipo_doc == "CPF" or len(doc) == 11:
        # O CPF vem mascarado ("***.744.***-**"): com o nome, só serve, na memória, para contar pessoas.
        pessoa_fisica, doc = True, f"PF {doc_bruto.strip()} {nome}"
    else:
        pessoa_fisica, doc = None, ""
        if FOLHA_NOME.search(pb._sem_acento(nome)):
            grupo = "1"
    if pagamentos_saida.FOLHA_NOME.search(pb._sem_acento(nome)):
        grupo = "1"
    return pq.Linha(chave=chave, unidade=entidade, doc=doc, nome=nome, pessoa_fisica=pessoa_fisica, grupo=grupo,
                    modalidade=(modalidade or "").zfill(2), elemento=(elemento or "").zfill(2), empenhado=empenhado, pago=pago)


def rodar(ano: int, so: list[str] | None, pausa: float = 0.0, refazer: bool = False) -> None:
    arq = baixar(ano, refazer)
    print(f"lendo {arq}", flush=True)
    entes = {str(e["cod_ibge"]): e["ente"] for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "PR"}
    por_seis = {ibge[:6]: ibge for ibge in entes}
    pedidos = {pb._chave(n) for n in so} if so else None
    resultado, fora, fora_do_cadastro = {}, Counter(), []
    t0 = time.time()
    with zipfile.ZipFile(arq) as externo:
        for nome_zip in sorted(externo.namelist()):
            m = NOME_ZIP.match(nome_zip)
            if not m or int(m.group(1)) != ano:
                continue
            ibge = por_seis.get(m.group(2))
            if not ibge:
                fora_do_cadastro.append(m.group(2))
                continue
            if pedidos and pb._chave(entes[ibge]) not in pedidos:
                continue
            with zipfile.ZipFile(io.BytesIO(externo.read(nome_zip))) as z:
                brutos, fora_cidade = empenhos(z, ano)
            fora.update(fora_cidade)
            resumo, _ = pq.resumir(linha(k, e) for k, e in brutos.items())
            resultado[ibge] = resumo
            if len(resultado) % 50 == 0 or pedidos:
                print(f"  {len(resultado)} cidades ({time.time() - t0:.0f} s); {entes[ibge]}: {pq.br(len(brutos))} empenhos, "
                      f"pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi", flush=True)
    if fora_do_cadastro:
        print(f"  códigos fora do cadastro do PR (ficaram de fora): {fora_do_cadastro}")
    if not resultado:
        raise SystemExit("nenhuma cidade lida")
    for motivo, v in fora.most_common():
        print(f"  fora do total ({motivo}): R$ {pq.br(v / 1e6, 1)} mi")
    pagamentos_saida.gravar("PR", FONTE, ano, resultado, so)
