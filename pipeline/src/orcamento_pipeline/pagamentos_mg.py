"""Para quem as prefeituras de Minas Gerais pagaram: os empenhos que as 853 cidades mandam ao TCE-MG (SICOM).

    uv run pagamentos --uf MG                          # lê data/raw/tce-mg/2025-empenho.zip (ou ~/Downloads)
    uv run pagamentos --uf MG --municipio Contagem     # só uma cidade; junta-se às que já estão no arquivo

Fonte: os dados abertos do TCE-MG (https://dadosabertos.tce.mg.gov.br, Jurisdicionado → Downloads), o
pacote "Empenhos" de cada ano (2025: 585 MB). **Não dá para baixar por programa**: o site gera uma chave
com um captcha invisível ao abrir a página, e sem ela tudo responde 401. O arquivo é baixado à mão, no
navegador, uma vez por ano (o site salva como "{ano}-empenho.zip"), e posto em data/raw/tce-mg/ ou deixado
na pasta Downloads.

O pacote é um ZIP com um ZIP por município ("SICOM.{ano}.{código IBGE}.empenho.zip"), cada um com CSVs
separados por ";", em UTF-8. Três deles bastam, ligados pelo "seq_empenho":

- empenho.csv: um empenho por linha, com o órgão (prefeitura, Câmara, fundos, autarquias, previdência) e
  a natureza da despesa ("3.3.90.39.99 - ...": grupo, modalidade e elemento);
- credorEmpenho.csv: o credor de cada empenho (num_doc_credor, nom_credor). O CNPJ vem inteiro; o CPF vem
  cortado (só 6 dígitos) e nunca é guardado;
- empenhoFonte.csv: o **movimento de cada mês** por fonte de recursos: empenhado, reforço e anulação,
  liquidado, pago e "outras baixas", cada um com a sua anulação.

**O pago é o pagamento mais as "outras baixas"**, as duas descontadas das anulações. As outras baixas são
as retenções (imposto de renda, INSS, consignados) que a prefeitura desconta do credor e repassa a quem
de direito: o credor recebeu aquilo, e a prestação de contas ao Tesouro (DCA) também conta como pago.
Conferido em Belo Horizonte: pagamento R$ 12,0 bi, outras baixas R$ 6,7 bi; sem as operações internas
(modalidade 91, R$ 1,2 bi), R$ 17,575 bi, igual à DCA de 2025. Só os empenhos do próprio ano estão no
pacote; o que se pagou de restos a pagar fica de fora, como no "pago" da DCA.

Conferido com a DCA de 2025 (pago, com ou sem as operações internas, a mais próxima): das 853 cidades,
829 batem a menos de 5% e 795 a menos de 1%; Belo Horizonte e Uberlândia batem no real. Os maiores
desvios são diferença entre as duas fontes, não de leitura: o pacote tem os doze meses, mas o próprio
liquidado é a metade da DCA em Entre Folhas (−49%) e Água Boa (−41%) e bem maior em São Francisco do
Glória (+54%) e Caparaó (+46%).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir): operações internas fora do total; folha, previdência, dívida e bancos e outros
órgãos públicos à parte dos fornecedores; pessoas físicas só no total e na contagem.

Saída em site/public/data/indicadores/pagamentos-mg.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba. A publicação automática só copia (`pagamentos --sem-baixar`).
"""

from __future__ import annotations

import csv
import io
import re
import time
import zipfile
from pathlib import Path

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida

FONTE = "Tribunal de Contas do Estado de Minas Gerais (TCE-MG), dados abertos do SICOM, pacote de empenhos"
PASTA = c.RAIZ / "data" / "raw" / "tce-mg"
DOWNLOADS = Path.home() / "Downloads"
NOME_ZIP = re.compile(r"SICOM\.(\d{4})\.(\d{7})\.empenho\.zip$")
NATUREZA = re.compile(r"^\s*(\d)\.(\d)\.(\d{2})\.(\d{2})")
# Credores sem CPF nem CNPJ que são a folha.
FOLHA_NOME = re.compile(r"FOLHA|SERVIDOR|FUNCIONA|FOPAG|\bPESSOAL\b|INATIVOS|APOSENTAD|PENSIONIST|SALARI|REMUNERA")


def pacote(ano: int) -> Path:
    """O ZIP do ano: em data/raw/tce-mg/ ou, senão, na pasta Downloads (onde o navegador salva)."""
    for pasta in (PASTA, DOWNLOADS):
        arq = pasta / f"{ano}-empenho.zip"
        if arq.exists():
            return arq
    raise SystemExit(
        f"falta o pacote de empenhos de {ano} do TCE-MG. Baixe à mão em https://dadosabertos.tce.mg.gov.br "
        f"(Jurisdicionado → Downloads, exercício {ano}, linha 'Empenhos') e ponha em {PASTA.relative_to(c.RAIZ)}/ "
        "ou deixe na pasta Downloads; o site não deixa baixar por programa (captcha)."
    )


def num(s: str) -> float:
    return float(s) if s else 0.0


def ler_csv(z: zipfile.ZipFile, sufixo: str):
    nome = next(n for n in z.namelist() if n.endswith(sufixo))
    with z.open(nome) as bruto:
        # Os CSVs não usam aspas, mas algumas descrições trazem uma aspa solta: com QUOTE_NONE ela é só um caractere
        # (senão o leitor junta linhas até achar a próxima aspa).
        texto = io.TextIOWrapper(bruto, encoding="utf-8", errors="replace", newline="")
        yield from csv.DictReader(texto, delimiter=";", quoting=csv.QUOTE_NONE)


def empenhos(z: zipfile.ZipFile) -> dict[str, list]:
    """{seq_empenho: [órgão, número, natureza, doc, nome, empenhado, pago]} de um município."""
    emp = {l["seq_empenho"]: [l["cod_orgao"], l["num_empenho"], l["dsc_naturezadespesa"], "", "", 0.0, 0.0]
           for l in ler_csv(z, ".empenho.empenho.csv")}
    for l in ler_csv(z, ".empenho.credorEmpenho.csv"):
        if e := emp.get(l["seq_empenho"]):
            e[3], e[4] = l["num_doc_credor"], l["nom_credor"]
    for l in ler_csv(z, ".empenho.empenhoFonte.csv"):
        if e := emp.get(l["seq_empenho"]):
            e[5] += num(l["vlr_empenho"]) + num(l["vlr_reforco_emp"]) - num(l["vlr_anulacao_emp"])
            e[6] += (num(l["vlr_pagamento"]) - num(l["vlr_anu_pagamento"])
                     + num(l["vlr_outras_baixas"]) - num(l["vlr_anu_outras_baixas"]))
    return emp


def limpar_nome(nome: str) -> str:
    """Tira do nome o CPF que alguns microempreendedores (MEI) têm na razão social ("FULANA CPF 123.456.789 - 00")."""
    nome = pagamentos_saida.CPF_NO_NOME.sub(" ", nome or "")
    nome = re.sub(r"\bCPF\b[\s:.\-]*", " ", nome)
    return " ".join(nome.split()).strip(" -")


def linha(seq: str, e: list) -> pq.Linha:
    orgao, numero, natureza, doc_bruto, nome, empenhado, pago = e
    nome = limpar_nome(nome)
    m = NATUREZA.match(natureza or "")
    grupo, modalidade, elemento = (m.group(2), m.group(3), m.group(4)) if m else ("", "", "")
    doc = re.sub(r"\D", "", doc_bruto or "")
    if len(doc) == 14 and pb.cnpj_valido(doc):
        pessoa_fisica = False
    elif len(doc) in (6, 11):
        # CPF (o TCE-MG publica só 6 dígitos): só serve, na memória, para contar pessoas.
        pessoa_fisica, doc = True, f"PF {doc} {nome}"
    else:
        pessoa_fisica, doc = None, ""
        if FOLHA_NOME.search(pb._sem_acento(nome)):
            grupo = "1"
    return pq.Linha(chave=seq, unidade=f"Órgão {orgao}", doc=doc, nome=nome, pessoa_fisica=pessoa_fisica,
                    grupo=grupo, modalidade=modalidade, elemento=elemento, empenhado=empenhado, pago=pago)


def rodar(ano: int, so: list[str] | None, pausa: float = 0.0, refazer: bool = False) -> None:
    arq = pacote(ano)
    print(f"lendo {arq}", flush=True)
    entes = {str(e["cod_ibge"]): e["ente"] for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "MG"}
    pedidos = {pb._chave(n) for n in so} if so else None
    resultado, fora_do_cadastro = {}, []
    t0 = time.time()
    with zipfile.ZipFile(arq) as externo:
        for nome_zip in sorted(externo.namelist()):
            m = NOME_ZIP.search(nome_zip)
            if not m or int(m.group(1)) != ano:
                continue
            ibge = m.group(2)
            cidade = entes.get(ibge)
            if not cidade:
                fora_do_cadastro.append(ibge)
                continue
            if pedidos and pb._chave(cidade) not in pedidos:
                continue
            with zipfile.ZipFile(io.BytesIO(externo.read(nome_zip))) as z:
                brutos = empenhos(z)
            resumo, _ = pq.resumir(linha(k, e) for k, e in brutos.items())
            resultado[ibge] = resumo
            if len(resultado) % 50 == 0 or pedidos:
                print(f"  {len(resultado)} cidades ({time.time() - t0:.0f} s); {cidade}: {pq.br(len(brutos))} empenhos, "
                      f"pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi", flush=True)
    if fora_do_cadastro:
        print(f"  códigos do IBGE fora do cadastro de MG (ficaram de fora): {fora_do_cadastro}")
    if not resultado:
        raise SystemExit("nenhuma cidade lida")
    pagamentos_saida.gravar("MG", FONTE, ano, resultado, so)
