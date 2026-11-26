"""Benefícios fiscais por empresa (/impostos/empresas): quem deixou de pagar imposto federal, quanto e com o quê.

    uv run beneficios-fiscais                    # baixa a Dirbi e o cadastro de CNPJ; cruza com a PGFN e os contratos
    uv run beneficios-fiscais --trimestre 2026_trimestre_03 --receita 2026-11
    uv run beneficios-fiscais --sem-baixar       # só copia o resumo versionado para o site (publicação automática)

Fontes:

- Receita Federal, Dirbi (Declaração de Incentivos, Renúncias, Benefícios e Imunidades de Natureza Tributária,
  IN RFB 2.198/2024): desde 2024 as empresas fora do Simples que usam benefício federal declaram todo mês quanto
  deixaram de pagar, benefício por benefício (os 173 códigos do Anexo Único) e tributo por tributo. A Receita publica
  um zip por ano numa pasta pública da nuvem dela (lida por WebDAV, como o cadastro de CNPJ), com o CNPJ da matriz,
  o nome, o município e a UF da matriz, o CNAE, o mês, o código e o valor. Quem conseguiu na Justiça esconder o nome
  aparece como "Restrição Judicial (n)", com o CNPJ em asteriscos.
- Receita Federal, cadastro de CNPJ (arquivos Empresas e Cnaes do mês): a natureza jurídica de cada empresa, para
  não nomear empresário individual nem MEI, e o nome da atividade de cada CNAE.
- PGFN, dívida ativa da União (os zips do trimestre que divida_ativa.py já baixa): quanto cada empresa deve e
  quanto está em cobrança, só pelo devedor principal.
- PNCP, contratos do ano (data/publico/contratos-{ano}-por-cnpj.parquet, de explorador_contratos.py) e pagamentos de
  emendas a empresas (data/publico/emendas-pagamentos-por-cnpj.parquet, de explorador_emendas.py), quando existirem.

Regras de privacidade (as mesmas da dívida ativa):

- Os arquivos não trazem CPF. Quem tem CNPJ mas é pessoa entra nos totais, nunca pelo nome, e fica fora dos arquivos
  por empresa: empresário individual e MEI (natureza 213-5) e o grupo 4 das naturezas, o das pessoas físicas
  (produtor rural, empresa individual imobiliária, candidato…). Um nome com um número de 11 dígitos (um CPF) também.
- As empresas com restrição judicial já vêm sem nome nem CNPJ e aparecem assim.

Saídas:

- data/publico/beneficios-fiscais-empresas.parquet: uma linha por empresa (raiz do CNPJ), com o total de cada ano, o
  benefício maior, a dívida com a União e os contratos; a busca e a ficha consultam no bucket público (espelho.py
  envia data/publico/ para explorador/).
- data/publico/beneficios-fiscais-por-cnpj.parquet: empresa, ano, código do benefício e valor, ordenado pela raiz,
  para a ficha de cada empresa.
- site/public/data/beneficios-fiscais/resumo.json: os números, os grupos e as maiores do ano fechado mais recente,
  com cópia em pipeline/referencia/beneficios-fiscais.json para a publicação automática (--sem-baixar).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import duckdb

from .cidades import RAIZ
from .divida_ativa import (PASTA as PASTA_PGFN, S as SIT, TIPOS as TIPOS_PGFN, URL_RECEITA,
                           _abrir, _baixar, _pode_nomear, arquivos_pgfn, e_pessoa, situacao, ultimo_mes_receita, ultimo_trimestre)

PASTA = RAIZ / "data" / "raw" / "receita-federal"
PASTA_DIRBI = PASTA / "dirbi"
PUBLICO = RAIZ / "data" / "publico"
SAIDA_EMPRESAS = PUBLICO / "beneficios-fiscais-empresas.parquet"
SAIDA_DETALHE = PUBLICO / "beneficios-fiscais-por-cnpj.parquet"
SAIDA = RAIZ / "site" / "public" / "data" / "beneficios-fiscais" / "resumo.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "beneficios-fiscais.json"
URL_BUCKET = "https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/explorador"
# Pasta pública da Dirbi na nuvem da Receita (dados.gov.br, conjunto "Renúncias Fiscais de Tributos Federais").
URL_DIRBI = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
TOKEN_DIRBI = "QsZYAHeegq65LxC"
PRIMEIRO_ANO = 2024
FONTE = ("Receita Federal, Dirbi (benefícios fiscais declarados pelas empresas) e cadastro de CNPJ; PGFN, dívida ativa "
         "da União; PNCP, contratos")
# Quem paga as emendas em nome do governo aparece como "favorecido" sem ser: o Banco do Brasil e a Caixa.
AGENTES_PAGADORES = {"00000000", "00360305"}

# O nome de cada código do Anexo Único da IN RFB 2.198/2024, como a Receita escreve no cabeçalho da planilha
# "Acumulado - CNPJ, Benefício, Ano" (a mesma pasta da Dirbi).
CODIGOS = {
    1: "PERSE", 2: "RECAP", 3: "REIDI", 4: "REPORTO", 5: "ÓLEO BUNKER", 6: "PROD. FARMACÊUTICOS - CMED",
    7: "DESONERAÇÃO DA FOLHA", 8: "PADIS", 9: "CARNE BOVINA, OVINA E CAPRINA - Exportação",
    10: "CARNE BOVINA, OVINA E CAPRINA - Industrialização", 11: "CAFÉ NÃO TORRADO", 12: "CAFÉ TORRADO E SEUS EXTRATOS",
    13: "LARANJA", 14: "SOJA", 15: "CARNE SUÍNA E AVÍCOLA", 16: "PRODUTOS AGROPECUÁRIOS GERAIS", 17: "REIQ - Redução Alíquotas",
    18: "REIQ - Créditos", 19: "REIQ - Créditos Adicionais", 20: "SUDAM / SUDENE - Redução 75%",
    21: "SUDAM / SUDENE - Reinvestimento 30%", 22: "ADUBOS E FERTILIZANTES", 23: "DEFENSIVOS AGROPECUÁRIOS", 24: "AERONAVES",
    25: "AERONAVES - Partes e Peças", 26: "PROD. FARMACÊUTICOS - Medicam. Doses", 27: "PRODUTOS QUÍMICOS - Cap. 29",
    28: "ZFM - Importação de Matérias Primas", 29: "SUBVENÇÕES INVESTIMENTOS", 30: "IT - Despesa Operacional",
    31: "IT - Redução IPI", 32: "IT - Depreciação Acelerada Ano Aquisição", 33: "IT - Amortização Acelerada de Intangíveis",
    34: "IT - Universidades", 35: "IT - Transf. Micro e Peq. Empresas", 36: "IT - Transf. Inventor Independente",
    37: "IT - Dispêndios - Adic. 60 a 80%", 38: "IT - Patentes e Cultivares - Adic. 20%", 39: "IT - Instituições Científicas",
    40: "IT - Depreciação Acelerada de Projetos", 41: "IT - Amortização Acelerada Inst. Fixas", 42: "IT - Subvenções União",
    43: "IT - Informática e Automação", 44: "ZFM - Importação para Elaboração de Matérias-Primas",
    45: "ZFM - Máquinas para Imobilizado", 46: "ZFM - Alíquotas 0,65% e 3%", 47: "ZFM - Alíquotas - Lucro Real",
    48: "ZFM - Alíquotas - Lucro Presumido e Simples", 49: "ZFM - Compras Nacionais Destinadas à ZFM",
    50: "ZFM - Venda de Matérias-Primas", 51: "ZFM - Pneumáticos para Bicicletas", 52: "ZFM - TI e Comunicação",
    53: "ZFM - Industrializados para Consumo Interno", 54: "ZFM - Industrializados para Território Nacional",
    55: "ZFM - Quadriciclos e Triciclos", 56: "ZFM - Entrada de Produtos Nacionais", 57: "ZFM - Entrada de Produtos Estrangeiros",
    58: "ZFM - Coeficiente de Redução - Geral", 59: "ZFM - Coeficiente de Redução - 88%", 60: "ZFM - Coeficiente de Redução - 5 pp",
    61: "TRANSPORTE AÉREO", 62: "TRANSPORTE RODOVIÁRIO", 63: "SEMENTES E MUDAS", 64: "CORRETIVO DE SOLO",
    65: "FEIJÕES, ARROZ, FARINHAS E SÊMOLAS", 66: "INOCULANTES AGRÍCOLAS", 67: "VACINAS VETERINÁRIAS",
    68: "FARINHAS A BASE DE MILHO", 69: "PINTOS DE UM DIA", 70: "LEITE FLUIDO", 71: "LEITE EM PÓ INTEGRAL",
    72: "LEITE EM PÓ SEMIDESNATADO", 73: "QUEIJOS", 74: "SORO DE LEITE", 75: "FARINHA DE TRIGO", 76: "TRIGO",
    77: "PRÉ MISTURAS PARA PÃO", 78: "MASSAS ALIMENTÍCIAS", 79: "CARNES", 80: "PEIXES", 81: "CAFÉ - Redução de Alíquota",
    82: "AÇÚCAR", 83: "ÓLEOS VEGETAIS", 84: "MANTEIGA", 85: "MARGARINA", 86: "SABÃO DE TOUCADOR",
    87: "PRODUTOS DE HIGIENE BUCAL", 88: "PAPEL HIGIÊNICO", 89: "MAIS LEITE SAUDÁVEL - PJ Habilitadas",
    90: "LEITE IN NATURA - PJ Não Habilitadas ao PMLS", 91: "MÁQUINAS PARA PRODUZIR PAPÉIS",
    92: "RET INCORPORAÇÕES - 1% - Faixa Urbano 1 - PMCMV", 93: "RET CONSTRUÇÕES - 1% - Faixa Urbano 1 - PMCMV", 94: "REPES",
    95: "RETID", 96: "RECINE", 97: "CÂMARA DE COMERC. DE ENERGIA ELÉTRICA", 98: "REPETRO-INDUSTRIALIZAÇÃO",
    99: "REPETRO-PERMANENTE", 100: "REPETRO-TEMPORÁRIO", 101: "CARVÃO MINERAL", 102: "GÁS NATURAL - PPT",
    103: "GÁS NATURAL LIQUEFEITO", 104: "PRODS. QUÍMICOS INTERMED. DE SÍNTESE", 105: "PRODS. HOSPITAIS, CLÍNICAS E CONSULT.",
    106: "PRODS. FARMAC. - Opoterápicos", 107: "PRODS. FARMAC. - Anti-Soros e Vacinas", 108: "PRODS. FARMAC. - Antitoxinas",
    109: "PRODS. FARMAC. - Medicam. não Apresentados em Doses", 110: "PRODS. FARMAC. - Curativos",
    111: "PRODS. FARMAC. - Opacificantes e Reagentes", 112: "PRODS. FARMAC. - Contraceptivos",
    113: "CINEMA, ÁUDIO E RADIODIFUSÃO", 114: "PROJETORES EXIBIÇÃO CINEMATOGRÁFICA", 115: "PRODUTOS HORTÍCULAS E FRUTAS",
    116: "OVOS", 117: "SÊMENS E EMBRIÕES", 118: "LIVROS", 119: "PREPARAÇÕES NÃO-ALCOÓLICAS PARA ELABORAÇÃO DE BEBIDAS",
    120: "AEROGERADORES", 121: "EMBARCAÇÕES - PARTES E PEÇAS - REB - Red. Alíq.",
    122: "AERONAVES E EMBARCAÇÕES - PARTES E PEÇAS - Isenção", 123: "MATERIAL DE DEFESA, SUAS PARTES E PEÇAS",
    124: "SERVIÇOS DE CONTROLE DE PRODUÇÃO", 125: "TRENS DE ALTA VELOCIDADE", 126: "TRANSP. COLET. PASSAGEIROS - Municipal",
    127: "TRANSP. COLET. PASSAGEIROS - Região Metropolitana, Intermunicipal, Interestadual e Internacional",
    128: "ÁGUA MINERAL", 129: "BIODIESEL - Combustível Social", 130: "EIZOF", 131: "CADEIRAS DE RODAS",
    132: "APARELHOS ORTOPÉDICOS", 133: "PRÓTESES", 134: "ALMOFADAS ANTIESCARAS", 135: "IMPRESSORAS, COPIADORAS E FAX BRAILLE",
    136: "MÁQUINAS DE ESCREVER EM BRAILLE", 137: "CADEIRAS DE RODAS - Partes e Acessórios", 138: "APARELHOS PARA AUDIÇÃO DE SURDOS",
    139: "OCLUSORES INTERAURICULARES", 140: "ACESSÓRIOS PARA AUDIÇÃO DE SURDOS", 141: "CALCULADORAS COM SINTETIZADOR DE VOZ",
    142: "TECLADOS PARA PESSOAS COM DEFICIÊNCIA", 143: "MOUSE PARA PESSOAS COM DEFICIÊNCIA", 144: "LINHAS BRAILLE",
    145: "SCANNERS COM SINTETIZADOR DE VOZ", 146: "DUPLICADORES BRAILLE", 147: "ACIONADORES DE PRESSÃO PARA MOBILIDADE REDUZIDA",
    148: "LUPAS ELETRÔNICAS PARA DEFICIÊNCIA VISUAL", 149: "IMPLANTES COCLEARES", 150: "PRÓTESES OCULARES",
    151: "SOFTWARES CONVERSORES DE TEXTO EM VOZ SINTETIZADA", 152: "APARELHOS CONVERSORES DE TEXTO EM BRAILLE",
    153: "NEUROESTIMULADORES PARA PARKINSON", 154: "HEDGE - OPERAÇÕES DE COBERTURA", 155: "VEÍCULOS BLINDADOS DE COMBATE",
    156: "DOAÇÕES A INST. FINANC. PÚBL. PARA CONS. AMBIENTAL", 157: "PROGR. ESTÍMULO À SOLICIT. DE DOC. FISCAL",
    158: "VINHOS DE UVAS FRESCAS", 159: "CARNE SUÍNA E AVÍCOLA - Adquiridas de PJ", 160: "EMPRESA CIDADÃ", 161: "PRONAC",
    162: "PAT - PROGR. ALIMENT. TRABALHADOR", 163: "HORÁRIO ELEITORAL GRATUITO", 164: "PROUNI - IRPJ e CSLL",
    165: "PROUNI - PIS/Pasep e Cofins", 166: "INCENTIVO AO DESPORTO", 167: "FUNDOS DA CRIANÇA/ADOLESCENTE", 168: "FUNDOS DO IDOSO",
    169: "DEPRECIAÇÃO ACELERADA - Lei 14.871/24", 170: "ZPE - Máquinas, Aparelhos, Instrumentos e Equipamentos",
    171: "ZPE - Matérias-Primas, Produtos Intermediários e Materiais de Embalagem", 172: "ZPE - Serviços",
    173: "BENS DE INFORMÁTICA E COMUNICAÇÃO",
}

# Grupos para a página. "tipo": "empresa" quando é preciso projeto, habilitação ou estar num lugar (o benefício é da
# empresa); "produto" quando a lei zera o imposto de um produto (quem declara é quem vende, mas parte vai para o
# preço); "setor" para a desoneração da folha, que vale para setores inteiros.
GRUPOS = [
    ("cesta", "Cesta básica e alimentos", "carne, café, leite, queijo, óleo, arroz e feijão", "produto",
     [9, 10, 11, 12, 13, 14, 15, 16, 65, *range(68, 91), 115, 116, 158, 159]),
    ("agro", "Insumos do agro", "adubo, defensivo, semente", "produto", [22, 23, 63, 64, 66, 67, 117]),
    ("zfm", "Zona Franca de Manaus", "e áreas de livre comércio", "empresa", [28, *range(44, 61), 130]),
    ("sudene", "Sudam e Sudene", "imposto de renda menor no Norte e no Nordeste", "empresa", [20, 21]),
    ("inovacao", "Inovação", "Lei do Bem e lei de informática", "empresa", [8, *range(30, 44), 173]),
    ("folha", "Desoneração da folha", "INSS menor para setores inteiros", "setor", [7]),
    ("saude", "Remédios e saúde", "medicamentos, vacinas, próteses", "produto", [6, 26, *range(105, 113), *range(131, 154)]),
    ("infra", "Infraestrutura e energia", "Reidi, Repetro, Recap, Reporto, gás", "empresa", [2, 3, 4, 5, 97, *range(98, 104), 120, 129, 169]),
    ("subvencao", "Subvenção para investimento", "incentivo de ICMS que sai da conta do imposto de renda", "empresa", [29]),
    ("perse", "Perse", "eventos e turismo, até março de 2025", "empresa", [1]),
    ("doacoes", "Doações e programas", "Rouanet, PAT, fundos, Prouni, Empresa Cidadã", "empresa", [156, *range(160, 169)]),
]
GRUPO_DO_CODIGO = {k: g[0] for g in GRUPOS for k in g[4]}
OUTROS = ("outros", "Outros de produto", "aviões e peças, químicos, transporte, construção", "produto")

SIGLAS = {"perse": "Perse", "recap": "Recap", "reidi": "Reidi", "reporto": "Reporto", "cmed": "CMED", "padis": "Padis",
          "reiq": "Reiq", "pmcmv": "Minha Casa Minha Vida", "ret": "RET", "pj": "PJ", "repes": "Repes", "retid": "Retid",
          "recine": "Recine", "ppt": "PPT", "eizof": "EIZOF", "pat": "PAT", "pronac": "Pronac (Lei Rouanet)",
          "prouni": "Prouni", "zpe": "ZPE", "pis/pasep": "PIS/Pasep", "sudam": "Sudam", "sudene": "Sudene", "reb": "REB",
          "pmls": "PMLS", "cofins": "Cofins", "irpj": "IRPJ", "csll": "CSLL", "ipi": "IPI", "ti": "TI", "zfm": "Zona Franca",
          "repetro-industrialização": "Repetro-Industrialização", "repetro-permanente": "Repetro-Permanente",
          "repetro-temporário": "Repetro-Temporário", "braille": "Braille", "parkinson": "Parkinson"}
PREFIXOS = [("ZFM - ", "Zona Franca: "), ("IT - ", "Lei do Bem: "), ("SUDAM / SUDENE - ", "Sudam e Sudene: "),
            ("PROD. FARMACÊUTICOS - ", "Remédios: "), ("PRODS. FARMAC. - ", "Remédios: "), ("REIQ - ", "Reiq: "),
            ("ZPE - ", "ZPE: "), ("PROUNI - ", "Prouni: ")]
NOME_PROPRIO = {43: "Lei de informática", 29: "Subvenção para investimento", 7: "Desoneração da folha",
                161: "Pronac (Lei Rouanet)", 162: "PAT (alimentação do trabalhador)", 1: "Perse"}


def nome_beneficio(cod: int) -> str:
    """'ZFM - TI e Comunicação' → 'Zona Franca: TI e comunicação'."""
    if cod in NOME_PROPRIO:
        return NOME_PROPRIO[cod]
    s = CODIGOS.get(cod, f"Código {cod}")
    prefixo = ""
    for de, para in PREFIXOS:
        if s.startswith(de):
            prefixo, s = para, s[len(de):]
            break
    palavras = [SIGLAS.get(p.lower(), p.lower()) for p in s.split()]
    texto = " ".join(palavras)
    texto = texto[:1].upper() + texto[1:]
    return prefixo + (texto[:1].lower() + texto[1:] if prefixo and not texto[:2].isupper() else texto)


# ---------------------------------------------------------------- 1. a Dirbi

def anos_dirbi() -> list[int]:
    with _abrir(URL_DIRBI, metodo="PROPFIND", cab={"Depth": "1", "Authorization": _auth(TOKEN_DIRBI)}) as r:
        return sorted({int(a) for a in re.findall(r"renuncia-por-regime-(\d{4})\.zip", r.read().decode())})


def _auth(token: str) -> str:
    import base64
    return "Basic " + base64.b64encode(f"{token}:".encode()).decode()


def baixar_dirbi(ano: int) -> Path:
    destino = PASTA_DIRBI / f"renuncia-por-regime-{ano}.zip"
    if destino.exists():
        return destino
    # _baixar autentica com o token do cadastro de CNPJ; a Dirbi é outra pasta, com outro token.
    import urllib.request
    from .fontes import CONTEXTO_TLS, USER_AGENT
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_name(destino.name + ".part")
    req = urllib.request.Request(f"{URL_DIRBI}renuncia-por-regime-{ano}.zip",
                                 headers={"User-Agent": USER_AGENT, "Authorization": _auth(TOKEN_DIRBI)})
    with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as r, parte.open("wb") as f:
        while bloco := r.read(8 << 20):
            f.write(bloco)
    if not zipfile.is_zipfile(parte):
        raise RuntimeError(f"Dirbi {ano}: a resposta não é um zip")
    parte.rename(destino)
    return destino


def ler_dirbi(con: duckdb.DuckDBPyConnection, arquivos: dict[int, Path]) -> None:
    """Tabela d: uma linha por empresa (chave), ano e código, com o valor; e m: os meses de cada ano."""
    partes = []
    with tempfile.TemporaryDirectory(dir=PASTA) as tmp:
        for ano, arq in arquivos.items():
            with zipfile.ZipFile(arq) as z:
                membro = next(n for n in z.namelist() if n.lower().endswith(".csv"))
                csv_ = Path(tmp) / f"{ano}.csv"
                with z.open(membro) as src, csv_.open("wb") as dst:
                    while bloco := src.read(8 << 20):
                        dst.write(bloco)
            print(f"  Dirbi {ano}: {csv_.stat().st_size / 1e6:.0f} MB", flush=True)
            # Colunas pela posição: o cabeçalho tem acentos e às vezes BOM.
            con.execute(f"""CREATE OR REPLACE TABLE bruto_{ano} AS SELECT * FROM read_csv('{csv_}', header=true, delim=',', quote='"',
                all_varchar=true, columns={{'cnpj':'VARCHAR','nome':'VARCHAR','municipio':'VARCHAR','uf':'VARCHAR','cnae':'VARCHAR',
                'mes':'VARCHAR','ano':'VARCHAR','cod':'VARCHAR','tributo':'VARCHAR','valor':'VARCHAR'}})""")
            partes.append(f"SELECT * FROM bruto_{ano}")
        con.execute(f"""CREATE OR REPLACE TABLE linhas AS
            SELECT CASE WHEN cnpj LIKE '%*%' THEN 'rj' || regexp_extract(nome, '\\((\\d+)\\)', 1)
                        ELSE substr(regexp_replace(cnpj, '\\D', '', 'g'), 1, 8) END AS chave,
                   trim(nome) AS nome, trim(municipio) AS municipio, trim(uf) AS uf, lpad(trim(cnae), 7, '0') AS cnae,
                   TRY_CAST(mes AS INTEGER) AS mes, TRY_CAST(ano AS INTEGER) AS ano, TRY_CAST(cod AS INTEGER) AS cod,
                   TRY_CAST(replace(replace(valor, '.', ''), ',', '.') AS DOUBLE) AS valor
              FROM ({' UNION ALL '.join(partes)}) WHERE TRY_CAST(ano AS INTEGER) IS NOT NULL""")
        for ano in arquivos:
            con.execute(f"DROP TABLE bruto_{ano}")
    con.execute("""CREATE OR REPLACE TABLE d AS SELECT chave, ano, cod, sum(valor) AS valor FROM linhas
                   WHERE valor IS NOT NULL AND valor > 0 GROUP BY ALL""")
    con.execute("CREATE OR REPLACE TABLE m AS SELECT ano, count(DISTINCT mes) AS meses, max(mes) AS ultimo FROM linhas GROUP BY ano")
    # Nome, lugar e CNAE: os da linha mais recente de cada empresa.
    con.execute("""CREATE OR REPLACE TABLE cad AS SELECT chave, arg_max(nome, ano * 100 + mes) AS nome,
                   arg_max(municipio, ano * 100 + mes) AS municipio, arg_max(uf, ano * 100 + mes) AS uf,
                   arg_max(cnae, ano * 100 + mes) AS cnae FROM linhas GROUP BY chave""")
    con.execute("DROP TABLE linhas")


# ---------------------------------------------------------------- 2. o cadastro de CNPJ

def natureza_e_cnaes(raizes: set[str], mes: str) -> tuple[dict[str, str], dict[str, str]]:
    """A natureza jurídica de cada raiz (arquivos Empresas, ~1,3 GB, baixados um por vez e apagados) e o nome de cada
    CNAE. Fica em cache em data/raw/receita-federal/ (só as raízes pedidas)."""
    cache, cache_cnae = PASTA / f"natureza-{mes}.csv", PASTA / f"cnaes-{mes}.csv"
    nat: dict[str, str] = {}
    if cache.exists():
        with cache.open(encoding="utf-8") as f:
            nat = {r[0]: r[1] for r in csv.reader(f, delimiter=";")}
    faltam = raizes - set(nat)
    if faltam and len(faltam) > len(raizes) * 0.02:   # um cache de outro conjunto de raízes: lê de novo
        tmp = PASTA / "cnpj-tmp"
        for i in range(10):
            arq = _baixar(f"{URL_RECEITA}{mes}/Empresas{i}.zip", tmp / f"Empresas{i}.zip", receita=True)
            with zipfile.ZipFile(arq) as z:
                for membro in z.namelist():
                    for r in csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";"):
                        if r and r[0] in faltam:
                            nat[r[0]] = r[2]
            arq.unlink()
            print(f"    Empresas{i}: {len(nat):,} raízes com natureza", flush=True)
        with cache.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter=";").writerows(sorted(nat.items()))
    cnaes: dict[str, str] = {}
    if not cache_cnae.exists():
        arq = _baixar(f"{URL_RECEITA}{mes}/Cnaes.zip", PASTA / "cnpj-tmp" / "Cnaes.zip", receita=True)
        with zipfile.ZipFile(arq) as z, cache_cnae.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            for membro in z.namelist():
                for r in csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";"):
                    if r and r[0].isdigit():
                        w.writerow([r[0].zfill(7), r[1]])
        arq.unlink()
    with cache_cnae.open(encoding="utf-8") as f:
        cnaes = {r[0]: r[1] for r in csv.reader(f, delimiter=";")}
    return nat, cnaes


# ---------------------------------------------------------------- 3. dívida ativa, contratos e emendas

def divida(raizes: set[str], tri: str | None) -> tuple[dict[str, list[float]], str]:
    """Raiz → [total, em cobrança, parcelada, garantida, suspensa], só o devedor principal e só empresas."""
    if tri is None:
        locais = sorted((p for p in PASTA_PGFN.glob("*_trimestre_*") if p.is_dir() and
                         all(any((p / f"{n}.zip").exists() for n in nomes) for nomes in TIPOS_PGFN.values())), reverse=True)
        tri = locais[0].name if locais else ultimo_trimestre()
    arqs = arquivos_pgfn(tri) if not (PASTA_PGFN / tri).exists() else {
        t: next(PASTA_PGFN / tri / f"{n}.zip" for n in nomes if (PASTA_PGFN / tri / f"{n}.zip").exists())
        for t, nomes in TIPOS_PGFN.items()}
    soma: dict[str, list[float]] = defaultdict(lambda: [0.0] * 5)
    posicao = ""
    for arq in arqs.values():
        with zipfile.ZipFile(arq) as z:
            for membro in z.namelist():
                if m := re.search(r"_(\d{6})\.csv$", membro):
                    posicao = max(posicao, m.group(1))
                leitor = csv.reader(io.TextIOWrapper(z.open(membro), encoding="latin-1", newline=""), delimiter=";")
                cab = next(leitor)
                i_doc, i_pessoa, i_dev, i_sit, i_aj, i_val = (cab.index(c) for c in (
                    "CPF_CNPJ", "TIPO_PESSOA", "TIPO_DEVEDOR", "TIPO_SITUACAO_INSCRICAO", "INDICADOR_AJUIZADO", "VALOR_CONSOLIDADO"))
                for l in leitor:
                    if len(l) <= i_val or not l[i_pessoa].startswith("Pessoa jur") or l[i_dev].upper() != "PRINCIPAL":
                        continue
                    d = re.sub(r"\D", "", l[i_doc])
                    if len(d) != 14 or d[:8] not in raizes:
                        continue
                    v = float(l[i_val] or 0)
                    s = situacao(l[i_sit], l[i_aj])
                    x = soma[d[:8]]
                    x[0] += v
                    x[{SIT["justica"]: 1, SIT["cobranca"]: 1, SIT["parcelada"]: 2, SIT["garantida"]: 3, SIT["suspensa"]: 4}.get(s, 1)] += v
            print(f"    PGFN {arq.name}: {len(soma):,} empresas com dívida até aqui", flush=True)
    return dict(soma), f"{posicao[4:]}/{posicao[:4]}" if posicao else tri


def contratos_e_emendas(con: duckdb.DuckDBPyConnection, ano: int) -> tuple[int | None, bool]:
    """Tabelas ct (raiz, n, valor dos contratos do ano) e em (raiz, valor pago com emendas desde PRIMEIRO_ANO)."""
    arq = PUBLICO / f"contratos-{ano}-por-cnpj.parquet"
    tem_ct = arq.exists()
    if tem_ct:
        con.execute(f"""CREATE OR REPLACE TABLE ct AS SELECT substr(cnpj, 1, 8) AS chave, count(*)::INTEGER AS n_contratos,
                        sum(valor) AS contratos FROM read_parquet('{arq}') WHERE pessoa = 'PJ' AND cnpj <> '' GROUP BY 1""")
    else:
        print(f"  sem {arq.relative_to(RAIZ)}: os contratos ficam de fora", flush=True)
        con.execute("CREATE OR REPLACE TABLE ct (chave VARCHAR, n_contratos INTEGER, contratos DOUBLE)")
    arq = PUBLICO / "emendas-pagamentos-por-cnpj.parquet"
    if arq.exists():
        fora = ", ".join(f"'{r}'" for r in AGENTES_PAGADORES)
        con.execute(f"""CREATE OR REPLACE TABLE em AS SELECT substr(codigo, 1, 8) AS chave, sum(valor) AS emendas
                        FROM read_parquet('{arq}') WHERE length(codigo) = 14 AND ano >= {PRIMEIRO_ANO}
                        AND substr(codigo, 1, 8) NOT IN ({fora}) GROUP BY 1""")
    else:
        con.execute("CREATE OR REPLACE TABLE em (chave VARCHAR, emendas DOUBLE)")
    return (ano if tem_ct else None), arq.exists()


# ---------------------------------------------------------------- 4. as saídas

def _inserir(con: duckdb.DuckDBPyConnection, sql: str, linhas: list) -> None:
    if linhas:   # o executemany do DuckDB recusa uma lista vazia
        con.executemany(sql, linhas)


def montar(con: duckdb.DuckDBPyConnection, nat: dict[str, str], cnaes: dict[str, str], div: dict[str, list[float]],
           posicao_pgfn: str, ano_contratos: int | None) -> tuple[dict, set[str], int]:
    meses = {a: (n, u) for a, n, u in con.execute("SELECT ano, meses, ultimo FROM m ORDER BY ano").fetchall()}
    anos = sorted(meses)
    fechados = [a for a in anos if meses[a][0] == 12]
    ano = max(fechados) if fechados else max(anos)

    # Quem não pode aparecer pelo nome (empresário individual, MEI, CPF no nome): fica só nos totais.
    cad = {k: (nome, mun, uf, cnae) for k, nome, mun, uf, cnae in con.execute("SELECT chave, nome, municipio, uf, cnae FROM cad").fetchall()}
    ocultas = {k for k, (nome, *_r) in cad.items() if not k.startswith("rj") and not _pode_nomear(nome, nat.get(k, ""))}
    con.execute("CREATE OR REPLACE TEMP TABLE ocultas (chave VARCHAR)")
    _inserir(con, "INSERT INTO ocultas VALUES (?)", [[k] for k in ocultas])
    con.execute("CREATE OR REPLACE TEMP TABLE grupo_cod (cod INTEGER, grupo VARCHAR)")
    _inserir(con, "INSERT INTO grupo_cod VALUES (?, ?)", [[k, g] for k, g in GRUPO_DO_CODIGO.items()])
    con.execute("""CREATE OR REPLACE TABLE dg AS SELECT d.*, coalesce(g.grupo, 'outros') AS grupo FROM d LEFT JOIN grupo_cod g USING (cod)""")

    tipo_do_grupo = {g[0]: g[3] for g in GRUPOS} | {OUTROS[0]: OUTROS[3]}
    # Por empresa, no ano principal: total, grupo maior e benefício maior.
    por_emp: dict[str, dict] = {}
    for chave, cod, grupo, v in con.execute(f"SELECT chave, cod, grupo, valor FROM dg WHERE ano = {ano}").fetchall():
        e = por_emp.setdefault(chave, {"total": 0.0, "grupos": defaultdict(float), "cods": defaultdict(float)})
        e["total"] += v
        e["grupos"][grupo] += v
        e["cods"][cod] += v
    total = sum(e["total"] for e in por_emp.values())
    ordem = sorted(por_emp, key=lambda k: -por_emp[k]["total"])
    posicao = {k: i + 1 for i, k in enumerate(ordem)}
    n = len(ordem)
    valores = [por_emp[k]["total"] for k in ordem]
    soma_ate = lambda q: sum(valores[:q])  # noqa: E731
    um_pct = max(1, round(n / 100))
    metade = valores[n // 2:]

    def principal(k: str) -> tuple[str, int]:
        e = por_emp[k]
        return max(e["grupos"], key=e["grupos"].get), max(e["cods"], key=e["cods"].get)

    def item(k: str) -> dict:
        nome, mun, uf, cnae = cad[k]
        g, cod = principal(k)
        x = div.get(k)
        return {"pos": posicao[k], "raiz": "" if k.startswith("rj") else k, "nome": nome, "municipio": mun, "uf": uf,
                "setor": cnaes.get(cnae, ""), "grupo": g, "tipo": tipo_do_grupo[g], "beneficio": nome_beneficio(cod),
                "valor": round(por_emp[k]["total"]), "cobranca": round(x[1]) if x and x[1] >= 1e5 else 0,
                "restricao": k.startswith("rj")}

    nomeaveis = [k for k in ordem if k not in ocultas]
    contratos = dict(con.execute("SELECT chave, contratos FROM ct").fetchall())

    grupos = []
    for gid, gnome, gsub, gtipo, *_ in [*GRUPOS, OUTROS]:
        membros = sorted(((k, e["grupos"][gid]) for k, e in por_emp.items() if e["grupos"].get(gid)), key=lambda x: -x[1])
        v = sum(x[1] for x in membros)
        if not v:
            continue
        maiores = [{"raiz": "" if k.startswith("rj") else k, "nome": cad[k][0], "valor": round(x)} for k, x in membros if k not in ocultas][:10]
        grupos.append({"id": gid, "nome": gnome, "sub": gsub, "tipo": gtipo, "valor": round(v), "empresas": len(membros),
                       "top10": round(sum(x[1] for x in membros[:10]) / v, 3), "maiores": maiores})
    grupos.sort(key=lambda g: -g["valor"])
    tipos = defaultdict(float)
    for g in grupos:
        tipos[g["tipo"]] += g["valor"]

    uf = defaultdict(lambda: [0.0, 0])
    for k in ordem:
        u = uf[cad[k][2] or "?"]
        u[0] += por_emp[k]["total"]
        u[1] += 1

    devem = [k for k in ordem if div.get(k, [0, 0])[1] > 0]
    com_ct = [k for k in ordem if contratos.get(k)]
    tres = [k for k in devem if contratos.get(k)]
    por_ano = {a: con.execute(f"SELECT sum(valor), count(DISTINCT chave) FROM d WHERE ano = {a}").fetchone() for a in anos}

    return {
        "fonte": FONTE, "ano": ano, "pgfn": posicao_pgfn, "contratosAno": ano_contratos,
        "empresasArquivo": f"{URL_BUCKET}/{SAIDA_EMPRESAS.name}", "porCnpj": f"{URL_BUCKET}/{SAIDA_DETALHE.name}",
        "anos": [{"ano": a, "valor": round(por_ano[a][0]), "empresas": por_ano[a][1], "meses": meses[a][0], "ultimoMes": meses[a][1]} for a in anos],
        "total": round(total), "empresas": n, "mediana": round(statistics.median(valores)) if valores else 0,
        "concentracao": {"top10": round(soma_ate(10)), "top100": round(soma_ate(100)), "top1pct": round(soma_ate(um_pct)), "n1pct": um_pct,
                         "bilhao": [sum(1 for v in valores if v >= 1e9), round(sum(v for v in valores if v >= 1e9))],
                         "metadeBaixo": [len(metade), round(sum(metade))]},
        "tipos": {k: round(v) for k, v in tipos.items()},
        "grupos": grupos,
        "maiores": [item(k) for k in nomeaveis[:100]],
        "uf": sorted(([u, round(v[0]), v[1]] for u, v in uf.items()), key=lambda x: -x[1]),
        "cruzamentos": {
            "devem": [len(devem), round(sum(por_emp[k]["total"] for k in devem)), round(sum(div[k][1] for k in devem))],
            "contratos": [len(com_ct), round(sum(contratos[k] for k in com_ct)), round(sum(por_emp[k]["total"] for k in com_ct))],
            "tres": [len(tres), round(sum(por_emp[k]["total"] for k in tres))],
        },
        "restricao": [sum(1 for k in ordem if k.startswith("rj")), round(sum(por_emp[k]["total"] for k in ordem if k.startswith("rj")))],
        "ocultas": [sum(1 for k in ordem if k in ocultas), round(sum(por_emp[k]["total"] for k in ordem if k in ocultas))],
    }, ocultas, ano


def gravar_parquets(con: duckdb.DuckDBPyConnection, ocultas: set[str], cnaes: dict[str, str], div: dict[str, list[float]], ano: int) -> None:
    anos = [a for (a,) in con.execute("SELECT DISTINCT ano FROM d ORDER BY ano").fetchall()]
    con.execute("CREATE OR REPLACE TEMP TABLE setor (cnae VARCHAR, setor VARCHAR)")
    _inserir(con, "INSERT INTO setor VALUES (?, ?)", list(cnaes.items()))
    con.execute("CREATE OR REPLACE TEMP TABLE div (chave VARCHAR, divida DOUBLE, cobranca DOUBLE, parcelada DOUBLE, garantida DOUBLE, suspensa DOUBLE)")
    _inserir(con, "INSERT INTO div VALUES (?, ?, ?, ?, ?, ?)", [[k, *v] for k, v in div.items()])
    con.execute("CREATE OR REPLACE TEMP TABLE nomes_cod (cod INTEGER, beneficio VARCHAR)")
    _inserir(con, "INSERT INTO nomes_cod VALUES (?, ?)", [[k, nome_beneficio(k)] for k in CODIGOS])
    colunas = ", ".join(f"sum(valor) FILTER (ano = {a}) AS v{a}" for a in anos)
    con.execute(f"""CREATE OR REPLACE TEMP TABLE emp AS
        WITH t AS (SELECT chave, {colunas} FROM dg GROUP BY chave),
             p AS (SELECT chave, arg_max(cod, valor) AS cod, arg_max(grupo, valor) AS grupo FROM
                   (SELECT chave, cod, any_value(grupo) AS grupo, sum(valor) AS valor FROM dg WHERE ano = {ano} GROUP BY ALL) GROUP BY chave)
        SELECT CASE WHEN c.chave LIKE 'rj%' THEN '' ELSE c.chave END AS raiz, c.chave, c.nome, c.municipio, c.uf, c.cnae,
               s.setor, t.* EXCLUDE (chave), p.grupo, n.beneficio, div.divida, div.cobranca,
               ct.n_contratos, ct.contratos, em.emendas
          FROM cad c JOIN t USING (chave) LEFT JOIN p USING (chave) LEFT JOIN nomes_cod n ON n.cod = p.cod
          LEFT JOIN setor s USING (cnae) LEFT JOIN div USING (chave) LEFT JOIN ct USING (chave) LEFT JOIN em USING (chave)
         WHERE c.chave NOT IN (SELECT chave FROM ocultas)""")
    PUBLICO.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY (SELECT * FROM emp ORDER BY chave) TO '{SAIDA_EMPRESAS}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 20000)")
    con.execute(f"""COPY (SELECT d.chave, d.ano, d.cod, n.beneficio, d.grupo, d.valor FROM dg d JOIN nomes_cod n USING (cod)
                    WHERE d.chave NOT IN (SELECT chave FROM ocultas) ORDER BY d.chave, d.ano, d.valor DESC)
                    TO '{SAIDA_DETALHE}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 20000)""")
    print(f"saída: {SAIDA_EMPRESAS.relative_to(RAIZ)} ({SAIDA_EMPRESAS.stat().st_size / 1e6:.1f} MB) e "
          f"{SAIDA_DETALHE.relative_to(RAIZ)} ({SAIDA_DETALHE.stat().st_size / 1e6:.1f} MB)", flush=True)


def copiar_referencia() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(RAIZ)} (cópia de {REFERENCIA.relative_to(RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(prog="beneficios-fiscais", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--trimestre", help="trimestre da PGFN, ex.: 2026_trimestre_03 (padrão: o último já baixado, senão o último publicado)")
    p.add_argument("--receita", help="mês do cadastro de CNPJ, ex.: 2026-11 (padrão: o último)")
    p.add_argument("--sem-baixar", action="store_true", help="só copia o resumo versionado para o site")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA.exists():
            copiar_referencia()
        return

    anos = [a for a in anos_dirbi() if a >= PRIMEIRO_ANO]
    print(f"Dirbi: {', '.join(map(str, anos))}", flush=True)
    arquivos = {a: baixar_dirbi(a) for a in anos}
    con = duckdb.connect()
    ler_dirbi(con, arquivos)
    raizes = {k for (k,) in con.execute("SELECT chave FROM cad WHERE chave NOT LIKE 'rj%'").fetchall()}
    print(f"  {len(raizes):,} empresas", flush=True)

    mes = args.receita or ultimo_mes_receita()
    nat, cnaes = natureza_e_cnaes(raizes, mes)
    print(f"  cadastro de CNPJ {mes}: natureza de {len(nat):,} empresas; {sum(1 for v in nat.values() if e_pessoa(v)):,} "
          "pessoas com CNPJ (empresário individual, MEI, produtor rural…)", flush=True)
    div, posicao_pgfn = divida(raizes, args.trimestre)
    ultimo_fechado = con.execute("SELECT max(ano) FROM m WHERE meses = 12").fetchone()[0] or max(anos)
    ano_ct, _ = contratos_e_emendas(con, ultimo_fechado)

    doc, ocultas, ano = montar(con, nat, cnaes, div, posicao_pgfn, ano_ct)
    gravar_parquets(con, ocultas, cnaes, div, ano)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    bi = lambda v: f"R$ {v / 1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    print(f"{ano}: {bi(doc['total'])} de {doc['empresas']:,} empresas; as 100 maiores com "
          f"{doc['concentracao']['top100'] / doc['total']:.0%}; {doc['ocultas'][0]:,} sem nome (pessoas com CNPJ) com "
          f"{bi(doc['ocultas'][1])}; {doc['restricao'][0]} com restrição judicial ({bi(doc['restricao'][1])})")
    c = doc["cruzamentos"]
    print(f"  devem à União (em cobrança, PGFN {posicao_pgfn}): {c['devem'][0]:,} empresas, {bi(c['devem'][1])} de benefício, "
          f"{bi(c['devem'][2])} em cobrança; com contrato em {ano_ct}: {c['contratos'][0]:,}")
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
