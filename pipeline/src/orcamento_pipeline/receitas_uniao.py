"""Receitas do governo federal (de onde vem o dinheiro da União), para a página /receitas.

    uv run receitas-uniao                # baixa o que falta e grava o JSON do site e a referência
    uv run receitas-uniao --forcar       # baixa de novo todos os anos
    uv run receitas-uniao --sem-baixar   # só copia pipeline/referencia/receitas-uniao.json para o site (CI)

Fonte: "Receitas" nos dados abertos do Portal da Transparência (CGU), um zip por ano desde 2014
(https://portaldatransparencia.gov.br/download-de-dados/receitas), com o valor previsto (atualizado) e o
realizado de cada receita, por órgão e unidade que arrecada. A receita vem classificada em quatro níveis
da natureza da receita: categoria (corrente, de capital), origem (impostos, contribuições, operações de
crédito…), espécie e detalhamento (IRPJ, Cofins…). O detalhamento junta o tributo e a parcela (principal,
multas e juros, dívida ativa): aqui eles viram dois níveis, "item" e "parcela".

O refinanciamento da dívida (títulos vendidos para pagar títulos que vencem) é marcado em cada linha:
são as operações de crédito cujo detalhamento fala em refinanciamento ("TIT.RESP.TN-REFIN.DIV.PUB…").

Para conferir, cada ano fechado guarda também o total oficial do Relatório Resumido da Execução
Orçamentária da União (RREO, Anexo 1, 6º bimestre), pela API do SICONFI. Até 2019 o Portal bate com ele
(diferença menor que 0,1%); de 2020 em diante o Portal fica de 1% a 3% abaixo, por lançamentos que não
aparecem no arquivo (ver docs/receitas-uniao.md).

Saída: site/public/data/receitas/uniao.json, com cópia em pipeline/referencia/receitas-uniao.json:
    {"gerado_em", "fonte", "colunas": [origem, especie, item, parcela, orgao, categoria, refin, previsto, realizado],
     "dims": {dimensão: {código: nome}},
     "anos": [{"ano", "ate": última data com lançamento, "parcial", "oficial": {...} | null, "linhas": [...]}]}
Os zips ficam em data/raw/receitas-uniao/.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import time
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

URL = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/receitas/{ano}_Receitas.zip"
PASTA = c.RAIZ / "data" / "raw" / "receitas-uniao"
SAIDA = c.RAIZ / "site" / "public" / "data" / "receitas" / "uniao.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "receitas-uniao.json"
PRIMEIRO_ANO = 2014
FONTE = "Controladoria-Geral da União, Portal da Transparência: receitas públicas"
COLUNAS = ["origem", "especie", "item", "parcela", "orgao", "categoria", "refin", "previsto", "realizado"]
DIAS_ATUALIZAR = 7   # o ano corrente e o anterior são baixados de novo depois disso

CATEGORIAS = {
    "receitascorrentes": ("c", "Receitas correntes"),
    "receitasdecapital": ("k", "Receitas de capital"),
    "receitascorrentesintraorcamentarias": ("ci", "Receitas correntes intraorçamentárias"),
    "receitasdecapitalintraorcamentarias": ("ki", "Receitas de capital intraorçamentárias"),
}

# Origem da receita: código curto e nome em português simples.
ORIGENS = {
    "impostostaxasecontribuicoesdemelhoria": ("impostos", "Impostos e taxas"),
    "contribuicoes": ("contribuicoes", "Contribuições"),
    "receitapatrimonial": ("patrimonial", "Receita patrimonial"),
    "receitaagropecuaria": ("agropecuaria", "Receita agropecuária"),
    "receitaindustrial": ("industrial", "Receita industrial"),
    "receitadeservicos": ("servicos", "Receita de serviços"),
    "transferenciascorrentes": ("transf-correntes", "Transferências correntes"),
    "outrasreceitascorrentes": ("outras-correntes", "Outras receitas correntes"),
    "operacoesdecredito": ("credito", "Operações de crédito"),
    "alienacaodebens": ("alienacao", "Venda de bens"),
    "amortizacoesdeemprestimos": ("amortizacoes", "Empréstimos devolvidos"),
    "transferenciasdecapital": ("transf-capital", "Transferências de capital"),
    "outrasreceitasdecapital": ("outras-capital", "Outras receitas de capital"),
}

# Espécies que o arquivo corta em 45 letras: o nome inteiro (chave: só letras do nome cortado).
ESPECIES = {
    "transferenciasdosestadosedodistritofed": "Transferências dos estados e do Distrito Federal",
    "transferenciasdosmunicipiosedesuasent": "Transferências dos municípios",
    "contribuicoesparaentidadesprivadasdese": "Contribuições para entidades privadas de serviço social",
    "receitasdecorrentesdecompensacoesaoreg": "Compensações ao regime geral de previdência",
    "receitasdecorrentesdeaportesperiodicosp": "Aportes periódicos para compensações ao regime geral de previdência",
    "receitatitulosdotesouronacionalresgatad": "Títulos do Tesouro resgatados",
    "transferenciasprovenientesdedepositona": "Transferências de depósitos não identificados",
    "transferenciasdeoutrasinstituicoespub": "Transferências de outras instituições públicas",
    "receitadividaativaprovenientedeamortiza": "Dívida ativa de empréstimos devolvidos",
    "bensdireitosevaloresincorporadosaopatr": "Bens, direitos e valores incorporados ao patrimônio público",
    "delegacaodeservicospublicosmediantec": "Concessões e permissões de serviços públicos",
    "exploracaodopatrimonioimobiliariodoe": "Exploração do patrimônio imobiliário do Estado",
    "servicoseatividadesreferentesanavegac": "Serviços de navegação e transporte",
    "indenizacoesrestituicoeseressarciment": "Indenizações, restituições e ressarcimentos",
    "multasadministrativascontratuaisejudicia": "Multas administrativas, contratuais e judiciais",
}

# Parcela de cada receita, pelo fim do detalhamento. A ordem decide quando há mais de uma marca.
PARCELAS = [
    ("divida-ativa", "Dívida ativa (cobrança de atrasados)", re.compile(r"D[IÍ]V\.?\s*A|D[IÍ]VIDA\s*ATIV|D\.A\.")),
    ("parcelamento", "Parcelamentos", re.compile(r"PARCEL")),
    ("multas", "Multas e juros", re.compile(r"^(MUL|MULTAS?|JUROS)\b|MUL\.\s*JU|MULTAS?\s+E\s+JUROS")),
    ("principal", "Valor principal", re.compile(r"^PRI(N|NC|NCIPAL|NCIPA)?\.?$|^PRINC")),
]
PARCELA_PADRAO = ("principal", "Valor principal")
INTRA = re.compile(r"^(IN|INT|INTR|INTRA|REC\.?\s*INTRA.*)$")

# Siglas e abreviações do SIAFI nos detalhamentos (maiúsculas, sem acento) -> por extenso. Cada
# abreviação termina em ponto ou no fim da palavra ("(?![A-Z])"), para não casar dentro de outra.
_F = r"(?:\.|(?![A-Z]))"
ABREVIACOES = [
    (rf"\bTIT{_F}\s*RESP{_F}\s*(DO\s*)?(T\.?\s*N{_F}|TES{_F}\s*NAC{_F})", "Títulos do Tesouro"),
    (rf"\bTITULOS DE RESPONS{_F}\s*TES{_F}\s*NAC{_F}", "Títulos do Tesouro"),
    (rf"\bREFIN(AN|ANC)?{_F}\s*(DA\s*)?DIV(IDA)?{_F}\s*PUB(LICA)?{_F}\s*(FED(ERAL)?{_F})?", "refinanciamento da dívida"),
    (rf"\bEXC{_F}\s*REF{_F}\s*DIV{_F}\s*PUB{_F}", "exceto refinanciamento"),
    (rf"\bMERC{_F}\s*INT(ERNO)?{_F}", "mercado interno"),
    (rf"\bMERC{_F}\s*EXT(ERNO)?{_F}", "mercado externo"),
    (rf"\bOP{_F}\s*(DE\s*)?CREDITO", "operações de crédito"),
    (rf"\bCONT(R|RIB)?{_F}\s*PREV(ID)?{_F}", "contribuição previdenciária"),
    (rf"\bCONTR(IB)?{_F}", "contribuição"),
    (rf"\b(N(Ã|A)O|Ñ)\s*OPT(ANTES)?{_F}\s*SIMP(LES)?{_F}\s*NAC{_F}", "fora do Simples"),
    (rf"\bOPT(ANTES)?{_F}\s*SIMP(LES)?{_F}\s*NAC{_F}", "do Simples"),
    (r"\bCONTRIBUINTES\b", ""),
    (r"\bS/\s*", "sobre "), (r"\bP/\s*", "para "), (r"\bC/\s*", "com "),
    (rf"\bSERV{_F}", "serviço"), (rf"\bADMINISTRAT{_F}", "administrativos"),
    (rf"\bCOMPENS{_F}\s*FINANC{_F}", "compensação financeira"), (rf"\bEXPL{_F}", "exploração"),
    (rf"\bREC{_F}\s*HIDRICOS", "recursos hídricos"), (rf"\bEMPREG{_F}", "empregador"),
    (rf"\bDEM{_F}", "demais"), (rf"\bREMUN(ER)?{_F}", "remuneração"), (rf"\bDISPONIB{_F}", "disponibilidades"),
    (rf"\bESP{_F}", "especial"), (rf"\bPETR(O)?{_F}", "petróleo"), (rf"\bPLAT{_F}", "plataforma"),
    (rf"\bROY(AL)?{_F}", "royalties"), (rf"\bPART{_F}", "participação"), (rf"\bEXC(ED)?{_F}", "excedente"),
    (rf"\bAMORT{_F}", "amortização"), (rf"\bEMPREST{_F}", "empréstimos"), (rf"\bEST{_F}", "estados"),
    (rf"\bMUN{_F}", "municípios"), (rf"\bLEGISL{_F}", "legislação"), (rf"\bRES{_F}", "resultado"),
    (r"\bBACEN\b", "Banco Central"), (rf"\bDESENV{_F}", "desenvolvimento"), (rf"\bPROG{_F}", "programas"),
    (rf"\bFIN{_F}", "financiamento"), (rf"\bSEG{_F}", "seguridade"), (rf"\bRECEITA{_F}", "receita"),
]
# Palavras comuns sem acento no SIAFI.
ACENTOS = {
    "LIQUIDA": "líquida", "OPERACOES": "operações", "OPERACAO": "operação", "IMPORTACAO": "importação",
    "EXPORTACAO": "exportação", "PREVIDENCIARIA": "previdenciária", "CONTRIBUICAO": "contribuição",
    "CONTRIBUICOES": "contribuições", "COMPENSACAO": "compensação", "COMPENSACOES": "compensações",
    "CONCESSAO": "concessão", "CESSAO": "cessão", "EDUCACAO": "educação", "ARRECADACAO": "arrecadação",
    "APLICACOES": "aplicações", "PUBLICA": "pública", "PUBLICO": "público", "PUBLICOS": "públicos",
    "DIVIDA": "dívida", "TITULOS": "títulos", "CREDITO": "crédito", "SALARIO": "salário", "PETROLEO": "petróleo",
    "SERVICOS": "serviços", "SERVICO": "serviço", "ECONOMICO": "econômico", "PROPRIO": "próprio", "UNIAO": "União",
    "FISCALIZACAO": "fiscalização", "INSPECAO": "inspeção", "HIDRAULICA": "hidráulica", "ENERGIA": "energia",
    "EMPRESTIMOS": "empréstimos", "AMORTIZACAO": "amortização", "AMORTIZACOES": "amortizações",
    "MUNICIPIOS": "municípios", "PREVIDENCIA": "previdência", "TELECOMUNICACOES": "telecomunicações",
    "RESTITUICOES": "restituições", "INDENIZACOES": "indenizações", "ALIENACAO": "venda", "INTANGIVEIS": "intangíveis",
    "IMOVEIS": "imóveis", "MOVEIS": "móveis", "VARIACAO": "variação", "CAMBIAL": "cambial", "DEPOSITOS": "depósitos",
    "BANCARIOS": "bancários", "ESPECIFICA": "específica", "AGENCIA": "agência", "NACIONAL": "nacional",
    "PERIODICOS": "periódicos", "DECORRENTES": "decorrentes", "PATRIMONIO": "patrimônio", "TRANSITO": "trânsito",
}

# Nomes simples para os itens que mais pesam (chave: só letras e números, sem acento).
_TIT_REFIN = "Títulos vendidos para pagar a dívida que vence"
_TIT_NOVOS = "Títulos vendidos para cobrir o déficit e outras despesas"
NOMES_ITENS = {
    # dívida (operações de crédito)
    "titresptnrefindivpubfedmercint": _TIT_REFIN, "titresptnrefinancdividapublicafederal": _TIT_REFIN,
    "titresptnrefindivpubfedint": _TIT_REFIN,
    "titresptnrefindivpubfedmercext": _TIT_REFIN + " (no exterior)",
    "titresprefinandividapublicafederal": _TIT_REFIN + " (no exterior)",
    "titresptnmercintexcrefdivpub": _TIT_NOVOS, "titulosderesponstesnacmercint": _TIT_NOVOS,
    "titrespdotesnacoutrasaplicacoes": _TIT_NOVOS,
    "titresptnmercextexcrefdivpub": _TIT_NOVOS + " (no exterior)", "titulosderesponstesnacmercext": _TIT_NOVOS + " (no exterior)",
    "titulostesouronacionaloutrasaplicacoes": _TIT_NOVOS + " (no exterior)",
    "opdecreditocontratuaismercexterno": "Empréstimos de bancos e organismos internacionais",
    "operacoesdecreditosexternascontratuais": "Empréstimos de bancos e organismos internacionais",
    # imposto de renda
    "irpjliquidadeincentivos": "Imposto de renda das empresas (IRPJ)",
    "pessoasjuridicasliquidadeincentivos": "Imposto de renda das empresas (IRPJ)",
    "irrftrabalho": "Imposto de renda descontado do salário", "retidonasfontestrabalho": "Imposto de renda descontado do salário",
    "irrfcapital": "Imposto de renda sobre aplicações financeiras", "retidonasfontescapital": "Imposto de renda sobre aplicações financeiras",
    "irrfremessaaoexterior": "Imposto de renda sobre dinheiro enviado ao exterior",
    "retidonasfontesremessaaoexterior": "Imposto de renda sobre dinheiro enviado ao exterior",
    "irrfoutrosrendimentos": "Imposto de renda descontado de outros rendimentos",
    "retidonasfontesoutrosrendimentos": "Imposto de renda descontado de outros rendimentos",
    "irpf": "Imposto de renda das pessoas físicas (declaração)", "pessoasfisicas": "Imposto de renda das pessoas físicas (declaração)",
    # outros impostos
    "impostosobreaimportacao": "Imposto de importação", "recdoprincipaldoimpostosaimport": "Imposto de importação",
    "iofdemaisoperacoes": "IOF (imposto sobre operações financeiras)",
    "ipioutrosprodutos": "IPI (outros produtos)", "ipivinculadosaimportacao": "IPI na importação",
    "ipiautomoveis": "IPI dos automóveis", "ipifumo": "IPI do cigarro", "ipibebidas": "IPI das bebidas",
    "taxasinspecaocontroleefiscalizacao": "Taxas de fiscalização",
    # contribuições
    "contrprevempregadornoptsimpnac": "Contribuição das empresas ao INSS",
    "contribdeempresassseguradosassalariados": "Contribuição das empresas ao INSS",
    "contprevidempregadoroptsimpnac": "Contribuição das empresas do Simples ao INSS",
    "contribuicoesporgps": "Contribuições ao INSS (todas)",
    "contribprevidenciariadosegurado": "Contribuição ao INSS descontada do salário",
    "contribuicoesdoseguradoassalariado": "Contribuição ao INSS descontada do salário",
    "cofinssfaturamentonaooptsimpnac": "Cofins", "cofinssobreofaturamento": "Cofins", "cofins": "Cofins",
    "recdoprincipaldacontrpfinsegsocial": "Cofins",
    "cofinssfaturamentooptsimpnac": "Cofins das empresas do Simples",
    "csllcontribuintesnaooptsimpnac": "Contribuição sobre o lucro (CSLL)",
    "csllcontribuintesnoptsimpnac": "Contribuição sobre o lucro (CSLL)",
    "contribsocialsobrelucroliqcsll": "Contribuição sobre o lucro (CSLL)",
    "recdoprincipaldacontribslucropj": "Contribuição sobre o lucro (CSLL)",
    "csllcontribuintesoptsimplesnac": "Contribuição sobre o lucro (CSLL) do Simples",
    "contribpispasepnaooptsimpnac": "PIS/Pasep", "contribpispasepnoptantessimpnac": "PIS/Pasep",
    "contribuicaoparaopispasep": "PIS/Pasep", "recdoprincipaldascontrpopispasep": "PIS/Pasep",
    "contribpispasepsobrefaturamento": "PIS/Pasep",
    "contribsocialdosalarioeducacao": "Salário-educação", "contribuicaodosalarioeducacao": "Salário-educação",
    "cideremessasaoexterior": "Cide sobre remessas ao exterior", "cidecombustiveis": "Cide dos combustíveis",
    "cotapartedoafrmm": "Adicional ao frete da Marinha Mercante (AFRMM)",
    "cpssspatronalservidorcivil": "Contribuição da União à previdência dos servidores",
    "contribpatronalservcivilativo": "Contribuição da União à previdência dos servidores",
    "contribpatrdeservativocivprpps": "Contribuição da União à previdência dos servidores",
    "cpsssservidorcivilativo": "Contribuição dos servidores à própria previdência",
    "contrpcustpensmilitforcasarmadas": "Contribuição dos militares para as pensões",
    "simples": "Simples Nacional",
    # patrimônio, Banco Central, empréstimos
    "remunerdisponibilidadestesnacional": "Rendimento do dinheiro do Tesouro no Banco Central",
    "remunerdisponibilidadesdotesouro": "Rendimento do dinheiro do Tesouro no Banco Central",
    "remuneracaodasdisponibilidadesdotesouro": "Rendimento do dinheiro do Tesouro no Banco Central",
    "resultadodobacendemaisoperacoes": "Lucro do Banco Central",
    "resultadodobancocentraldemaisoperacoes": "Lucro do Banco Central",
    "resbacenopcreservederivcambiais": "Lucro do Banco Central com reservas e câmbio",
    "pesppetroplatcomant31212psal": "Participação especial do petróleo",
    "roypetrplatpartilhacomap31212": "Royalties do petróleo (partilha do pré-sal)",
    "roypetroplatcomantes31212psal": "Royalties do petróleo",
    "royexcpetroplatcmant31212psal": "Royalties do petróleo (parcela excedente)",
    "compensfinancexplrecursosminerais": "Royalties da mineração (CFEM)",
    "concusopotencialenergiahidraulica": "Concessões de usinas hidrelétricas",
    "competrogasnateoutroscontrpart": "Venda do petróleo da União (partilha)",
    "dividendos": "Dividendos das estatais", "dividendosuniao": "Dividendos das estatais",
    "jurossobreocapitalproprio": "Juros sobre capital próprio das estatais",
    "remuneracaodedepositosbancarios": "Rendimento de depósitos bancários",
    "remuneracaodedepbancariosgeral": "Rendimento de depósitos bancários",
    "retornodeopjureencfinanceiros": "Juros de empréstimos concedidos pela União",
    "jurosdeemprestimos": "Juros de empréstimos concedidos pela União",
    "remunsrepassepprogdesenveconomico": "Juros dos repasses ao BNDES e outros programas",
    "amortizacaodeemprestimoscontratuais": "Devolução de empréstimos feitos pela União (BNDES e outros)",
    "amortizacaodeemprestimosestmun": "Devolução de empréstimos feitos a estados e municípios",
    "amortizacaodeemprestimosestadosmunicipios": "Devolução de empréstimos feitos a estados e municípios",
    "multasprevistasemlegislespecifica": "Multas previstas em lei",
    "restitdespprimariasexanteriores": "Devolução de despesas de anos anteriores",
    "amortizacaodeemprestimosestemun": "Devolução de empréstimos feitos a estados e municípios",
    "contribuicaodoservidorcivilativo": "Contribuição dos servidores à própria previdência",
    "contribdoservidorcivilinativo": "Contribuição dos servidores aposentados à previdência",
    "concservgertransmdistrenerelet": "Concessões de energia elétrica",
    "contribpispasepoptantessimpnac": "PIS/Pasep das empresas do Simples",
    "recpispasepnaoreclsup20anos": "Cotas do PIS/Pasep não sacadas em 20 anos",
    "aportesfundocompsbeneffiscfcbfpr": "Aportes ao fundo de compensação de benefícios fiscais",
    "amortizacaodefinanciamentosemgeral": "Devolução de financiamentos concedidos pela União",
    "royexcpetroplatcomapartir31212": "Royalties do petróleo (parcela excedente)",
    "royalpetroplatcomapartir31212": "Royalties do petróleo",
    "roypetroplatcomantes31212demais": "Royalties do petróleo",
    "royexcpetroplatcomant31212dem": "Royalties do petróleo (parcela excedente)",
    "pesppetroplatcomant31212demais": "Participação especial do petróleo",
    "impostosobreaexportacao": "Imposto de exportação",
    "partuniaoemreclotprognnumericos": "Parte da União nas loterias",
    "contribsloteriasprognostnumericos": "Contribuição sobre as loterias",
    "servicosdenavegacaoaerea": "Tarifas de navegação aérea",
    "cessaodiroperacpagtosexeceleg": "Venda do direito de pagar os servidores (folha) a bancos",
    "multasprevistasnoctb": "Multas de trânsito (rodovias federais)",
    "amortizacaodefinanciamentodofies": "Devolução de financiamentos do Fies",
    "itrmunicipiosconveniados": "Imposto territorial rural (ITR)",
    "cidecombustiveiscomercializacao": "Cide dos combustíveis",
    "delegpexplorinfraestaeroportuaria": "Concessões de aeroportos",
    "delegpprestservtranspferroviario": "Concessões de ferrovias",
    "alienacaodebensintangiveis": "Venda de direitos (bens intangíveis)",
    "bonusasscontrpartilhaproducaouniao": "Bônus de assinatura de contratos de petróleo",
    "bonusasscontrpartilhaprodestmun": "Bônus de assinatura de contratos de petróleo (parte de estados e municípios)",
    "bonusassinatdecontratodeconcessao": "Bônus de assinatura de concessões",
    "variacaocambial": "Ganho com variação do câmbio",
    "csll": "Contribuição sobre o lucro (CSLL)",
    "cofinssfaturamento": "Cofins",
}


def so_letras(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def codigo(*partes: str) -> str:
    return hashlib.md5("|".join(so_letras(p) for p in partes).encode()).hexdigest()[:6]


def numero(s: str) -> float:
    s = (s or "").strip()
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def separar_parcela(detalhe: str) -> tuple[str, str]:
    """'IRPJ-LIQUIDA DE INCENTIVOS-MULTAS E JUROS' -> ('IRPJ-LIQUIDA DE INCENTIVOS', 'multas')."""
    partes = [p.strip() for p in re.split(r"\s*-\s*", " ".join(detalhe.split())) if p.strip()]
    achadas = set()
    while len(partes) > 1:
        fim = partes[-1].upper()
        if INTRA.match(fim):
            partes.pop()
            continue
        marca = next((cod for cod, _, rx in PARCELAS if rx.search(fim)), None)
        if not marca:
            break
        achadas.add(marca)
        partes.pop()
    parcela = next((cod for cod, _, _ in PARCELAS if cod in achadas), PARCELA_PADRAO[0])
    return "-".join(partes) or detalhe, parcela


def nome_item(base: str) -> str:
    """Nome legível de um detalhamento do SIAFI (maiúsculas, abreviado)."""
    chave = so_letras(base)
    if chave in NOMES_ITENS:
        return NOMES_ITENS[chave]
    t = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode().upper()
    for padrao, troca in ABREVIACOES:
        t = re.sub(padrao, f" {troca} ", t)
    t = re.sub(r"\.(?=[A-Z])", ". ", t)   # "OPER.COM" -> "OPER. COM"
    t = re.sub(r"\s*-\s*", " – ", t)
    t = re.sub(r"\s+", " ", t).strip(" .–")
    # Siglas (até 5 letras, sem vogal ou conhecidas) ficam em maiúsculas; o resto em minúsculas.
    siglas = {"IR", "IRPJ", "IRPF", "IRRF", "IPI", "IOF", "ITR", "CSLL", "PIS", "PASEP", "COFINS", "CIDE", "INSS", "FGTS",
              "RPPS", "RGPS", "BNDES", "BACEN", "TDA", "CFEM", "ANP", "ANATEL", "ANEEL", "CPMF", "SUS", "FUNDAF", "FIES",
              "FAT", "CTB", "PGPM", "DPVAT", "PND", "FCVS", "CVM", "SUSEP", "ANS", "ANVISA", "ANTT", "ANAC", "ANTAQ"}
    palavras = []
    for p in t.split(" "):
        limpa = re.sub(r"[^A-Z]", "", p)
        if re.search(r"[a-zà-ÿ]", p):          # já veio por extenso de ABREVIACOES
            palavras.append(p)
        elif limpa in ACENTOS and limpa == p.strip(".,;:()"):
            palavras.append(p.replace(limpa, ACENTOS[limpa]))
        elif limpa in siglas or (2 <= len(limpa) <= 4 and not re.search(r"[AEIOU]", limpa)):
            palavras.append(p)
        else:
            palavras.append(p.lower())
    t = " ".join(palavras)
    return t[:1].upper() + t[1:]


def baixar(ano: int, forcar: bool) -> bool:
    PASTA.mkdir(parents=True, exist_ok=True)
    destino = PASTA / f"{ano}_Receitas.zip"
    hoje = dt.date.today()
    if destino.exists() and not forcar:
        idade = (time.time() - destino.stat().st_mtime) / 86400
        if ano < hoje.year - 1 or idade < DIAS_ATUALIZAR:
            return True
    req = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
            dados = resp.read()
    except Exception as erro:
        print(f"  {ano}: não baixou ({erro})", flush=True)
        return destino.exists()
    if not dados.startswith(b"PK"):
        print(f"  {ano}: a resposta não é um zip (captcha?)", flush=True)
        return destino.exists()
    tmp = destino.with_suffix(".tmp")
    tmp.write_bytes(dados)
    tmp.replace(destino)
    print(f"  {ano}: {len(dados) / 1e6:.1f} MB", flush=True)
    return True


def oficial(ano: int) -> dict | None:
    """Totais do RREO da União (Anexo 1, 6º bimestre) pela API do SICONFI, com cache."""
    if ano < 2015 or ano >= dt.date.today().year:
        return None
    cache = PASTA / f"rreo-{ano}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        itens = c._get("rreo", {"an_exercicio": ano, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
                                "no_anexo": "RREO-Anexo 01", "id_ente": 1})["items"]
    except Exception as erro:
        print(f"  RREO {ano}: {erro}", flush=True)
        return None
    valor = {}
    for i in itens:
        chave = {"Até o Bimestre (c)": "realizado", "PREVISÃO INICIAL": "previsto_inicial",
                 "PREVISÃO ATUALIZADA (a)": "previsto_atualizado"}.get(i["coluna"])
        if chave and i["cod_conta"] == "TotalReceitas" and i["valor"] is not None:
            valor.setdefault(chave, round(i["valor"]))
    if "realizado" not in valor:
        return None
    doc = {"fonte": f"RREO da União, 6º bimestre de {ano} (Anexo 1, total das receitas)", **valor}
    cache.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return doc


def ler(ano: int, dims: dict, nomes_vistos: dict) -> dict:
    """Agrega o CSV do ano em linhas (origem, espécie, item, parcela, órgão, categoria, refin)."""
    soma: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0.0])
    ate = ""
    with zipfile.ZipFile(PASTA / f"{ano}_Receitas.zip") as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as f:
            leitor = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
            for r in leitor:
                cat_k = so_letras(r["CATEGORIA ECONÔMICA"])
                orig_k = so_letras(r["ORIGEM RECEITA"])
                if cat_k not in CATEGORIAS or orig_k not in ORIGENS:
                    # "Sem informação" e "a classificar": valores ínfimos, entram como "outras".
                    cat = CATEGORIAS.get(cat_k, ("x", "Sem classificação"))
                    orig = ORIGENS.get(orig_k, ("outras", "Sem classificação"))
                else:
                    cat, orig = CATEGORIAS[cat_k], ORIGENS[orig_k]
                especie = " ".join(r["ESPÉCIE RECEITA"].split()) or "Sem informação"
                especie_nome = ESPECIES.get(so_letras(especie), especie[:1].upper() + especie[1:].lower()
                                            if especie.isupper() else especie[:1].upper() + especie[1:])
                detalhe = " ".join(r["DETALHAMENTO"].split()) or "Sem informação"
                base, parcela = separar_parcela(detalhe)
                cod_esp = codigo(orig[0], especie)
                cod_item = codigo(orig[0], especie, base)
                refin = int(orig[0] == "credito" and "REFIN" in detalhe.upper() and "EXC" not in detalhe.upper())
                orgao = (r["CÓDIGO ÓRGÃO SUPERIOR"] or "-").strip()
                dims["categoria"][cat[0]] = cat[1]
                dims["origem"][orig[0]] = orig[1]
                dims["especie"][cod_esp] = especie_nome
                nomes_vistos[cod_item][base] += 1
                dims["orgao"][orgao] = " ".join((r["NOME ÓRGÃO SUPERIOR"] or "Sem informação").split())
                v = soma[(orig[0], cod_esp, cod_item, parcela, orgao, cat[0], refin)]
                v[0] += numero(r["VALOR PREVISTO ATUALIZADO"])
                v[1] += numero(r["VALOR REALIZADO"])
                data = r["DATA LANÇAMENTO"] or ""
                if re.fullmatch(r"\d\d/\d\d/\d{4}", data):
                    iso = f"{data[6:]}-{data[3:5]}-{data[:2]}"
                    ate = max(ate, iso)
    linhas = [[*k, round(v[0]), round(v[1])] for k, v in sorted(soma.items()) if round(v[0]) or round(v[1])]
    return {"ano": ano, "ate": ate or None, "linhas": linhas}


def gerar(forcar: bool) -> dict:
    hoje = dt.date.today()
    dims: dict[str, dict[str, str]] = {d: {} for d in ("origem", "especie", "item", "parcela", "orgao", "categoria")}
    dims["parcela"] = {cod: nome for cod, nome, _ in PARCELAS}
    nomes_vistos: dict[str, Counter] = defaultdict(Counter)
    anos = []
    for ano in range(PRIMEIRO_ANO, hoje.year + 1):
        if not baixar(ano, forcar):
            continue
        doc = ler(ano, dims, nomes_vistos)
        doc["parcial"] = ano == hoje.year
        doc["oficial"] = oficial(ano)
        anos.append(doc)
        tot = sum(l[-1] for l in doc["linhas"])
        refin = sum(l[-1] for l in doc["linhas"] if l[6])
        of = doc["oficial"]
        conf = f"; RREO R$ {of['realizado'] / 1e9:,.1f} bi ({tot / of['realizado'] - 1:+.1%})" if of else ""
        print(f"{ano}: {len(doc['linhas'])} linhas, R$ {tot / 1e9:,.1f} bi (refinanciamento R$ {refin / 1e9:,.1f} bi){conf}",
              flush=True)
    # Nome de cada item: a grafia mais frequente (de preferência com acento), passada a limpo.
    for cod, cont in nomes_vistos.items():
        grafia = max(cont, key=lambda g: (cont[g], bool(re.search(r"[À-ÿ]", g))))
        dims["item"][cod] = nome_item(grafia)
    # Órgãos: nome do ano mais recente já ficou (o dicionário é sobrescrito em ordem de ano).
    return {
        "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "fonte": FONTE,
        "url": "https://portaldatransparencia.gov.br/download-de-dados/receitas",
        "colunas": COLUNAS,
        "dims": {d: dict(sorted(v.items())) for d, v in dims.items()},
        "anos": anos,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--forcar", action="store_true", help="baixar de novo todos os anos")
    p.add_argument("--sem-baixar", action="store_true", help="só copiar a referência versionada para o site (publicação automática)")
    args = p.parse_args()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    if args.sem_baixar:
        if REFERENCIA.exists():
            SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia de {REFERENCIA.relative_to(c.RAIZ)})")
        return
    doc = gerar(args.forcar)
    if not doc["anos"]:
        raise SystemExit("nenhum ano baixado")
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for alvo in (SAIDA, REFERENCIA):
        alvo.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({len(texto) / 1e3:,.0f} KB)")


if __name__ == "__main__":
    main()
