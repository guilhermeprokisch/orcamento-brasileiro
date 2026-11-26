"""Preço pago comparado: o mesmo remédio comprado por cidades e estados diferentes, e quantas empresas disputaram.

    uv run precos                 # baixa as compras de 2025 e 2026 e monta (uns 30 min na primeira vez)
    uv run precos --sem-baixar    # só copia pipeline/referencia/precos*.json para o site (CI)
    uv run precos --sem-rs        # sem o LicitaCon do RS (dois zips de ~280 MB)

O levantamento das fontes e as regras da comparação estão em docs/levantamento-preco-pago.md. Em resumo:

- **Compras.gov.br, pesquisa de preço** (a base do Painel de Preços): cada compra de um código CATMAT, com a unidade
  padronizada, a quantidade, o preço unitário, o fornecedor e o código IBGE da cidade do órgão. Só tem quem compra pelo
  sistema federal (governo federal, parte dos estados e umas 150 a 400 prefeituras por remédio).
- **LicitaCon, do TCE-RS**: todos os órgãos do Rio Grande do Sul, com a descrição livre do item (casada com a lista
  abaixo pela descrição), o preço homologado e todas as propostas de cada item. Para as prefeituras do RS, o preço vem
  daqui (e não do Compras.gov.br, para não contar a mesma compra duas vezes), e daqui vem a conta das licitações com uma
  empresa só, só nos órgãos que informam ao TCE as propostas perdedoras.

A comparação: mesmo código, mesma unidade (comprimido, cápsula ou ampola), mesmo ano (pela data da compra). A
referência é a mediana das compras de quantidade parecida (o ano de cada remédio dividido em três grupos: pequenas,
médias e grandes). Acima de 30 vezes ou abaixo de 1/30 da mediana do ano é erro de unidade (o preço da caixa no lugar do
comprimido) e fica de fora. Um remédio só tem mediana com 20 compras de 10 compradores diferentes no ano. Uma compra é
"mais cara" quando passa de 2 vezes a mediana das parecidas e dá pelo menos R$ 1.000 a mais se a quantidade toda for
comprada.

Nunca guarda CPF: do fornecedor fica só o nome de pessoa jurídica (CNPJ com 14 dígitos, e não MEI, cujo nome é o da
pessoa). Do LicitaCon, o documento de quem propôs só é contado, nunca guardado.

Saídas (com cópia em pipeline/referencia/):
    site/public/data/indicadores/precos.json   por cidade e por estado:
        {"anos", "remedios": {codigo: nome}, "mun": {ibge: ente}, "uf": {codigo: ente}}
        ente = {"n": compras comparadas, "r": remédios diferentes, "caras": [[codigo, ano, data, preço, mediana das
                parecidas, quantidade, a mais, modalidade, comprador, fornecedor, link], ...] (as 12 de mais reais a mais),
                "n_caras": quantas passam do dobro e de R$ 1.000 a mais, "n_dobro": quantas passam do dobro,
                "baratas": quantas pagaram a mediana ou menos, "rs": {disputa do RS, só nas prefeituras gaúchas}}
    site/public/data/precos/remedios.json      a página nacional: por remédio e ano, a mediana, a faixa, as medianas por
                                               quantidade e por região e todas as compras
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import io
import json
import re
import shutil
import statistics as st
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA = c.RAIZ / "data" / "raw" / "precos"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "precos.json"
SAIDA_NACIONAL = c.RAIZ / "site" / "public" / "data" / "precos" / "remedios.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "precos.json"
REFERENCIA_NACIONAL = c.RAIZ / "pipeline" / "referencia" / "precos-remedios.json"
MUNICIPIOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
URL_PESQUISA = "https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
URL_LICITACON = "https://dados.tce.rs.gov.br/dados/licitacon/licitacao/ano/{ano}.csv.zip"
LINK_COMPRASGOV = "https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/acompanhamento-compra?compra={}"

# Os remédios comparados: código CATMAT, nome no site, forma ("comprimido", "cápsula", "ampola") e, para casar a
# descrição livre do LicitaCon, o princípio ativo e a dosagem (regex sobre o texto em maiúsculas e sem acento).
# Lista fechada, conferida no catálogo em 23/11/2026: só a dosagem e a forma mais comuns na farmácia básica.
REMEDIOS: list[tuple[int, str, str, str, str]] = [
    (268856, "Losartana 50 mg", "comprimido", r"LOSARTAN", r"50"),
    (287473, "Losartana 100 mg", "comprimido", r"LOSARTAN", r"100"),
    (267690, "Metformina 500 mg", "comprimido", r"METFORMIN", r"500"),
    (267691, "Metformina 850 mg", "comprimido", r"METFORMIN", r"850"),
    (267747, "Sinvastatina 20 mg", "comprimido", r"SINVASTATIN", r"20"),
    (267745, "Sinvastatina 40 mg", "comprimido", r"SINVASTATIN", r"40"),
    (267674, "Hidroclorotiazida 25 mg", "comprimido", r"HIDROCLOROTIAZID", r"25"),
    (267613, "Captopril 25 mg", "comprimido", r"CAPTOPRIL", r"25"),
    (267651, "Enalapril 10 mg", "comprimido", r"ENALAPRIL", r"10"),
    (267652, "Enalapril 20 mg", "comprimido", r"ENALAPRIL", r"20"),
    (272434, "Anlodipino 5 mg", "comprimido", r"ANLODIPIN", r"5"),
    (267517, "Atenolol 50 mg", "comprimido", r"ATENOLOL", r"50"),
    (267772, "Propranolol 40 mg", "comprimido", r"PROPRANOLOL", r"40"),
    (267567, "Carvedilol 25 mg", "comprimido", r"CARVEDILOL", r"25"),
    (267729, "Nifedipino 20 mg", "comprimido", r"NIFEDIPIN", r"20"),
    (267663, "Furosemida 40 mg", "comprimido", r"FUROSEMID", r"40"),
    (267653, "Espironolactona 25 mg", "comprimido", r"ESPIRONOLACTON", r"25"),
    (267502, "AAS 100 mg", "comprimido", r"ACIDO ACETILSALICILICO|\bAAS\b", r"100"),
    (267671, "Glibenclamida 5 mg", "comprimido", r"GLIBENCLAMID", r"5"),
    (268123, "Levotiroxina 50 mcg", "comprimido", r"LEVOTIROXIN", r"50\s*(MCG|UG|µG)"),
    (267712, "Omeprazol 20 mg", "cápsula", r"OMEPRAZOL", r"20"),
    (267713, "Omeprazol 40 mg", "cápsula", r"OMEPRAZOL", r"40"),
    (273009, "Fluoxetina 20 mg", "cápsula", r"FLUOXETIN", r"20"),
    (272365, "Sertralina 50 mg", "comprimido", r"SERTRALIN", r"50"),
    (267512, "Amitriptilina 25 mg", "comprimido", r"AMITRIPTILIN", r"25"),
    (270119, "Clonazepam 2 mg", "comprimido", r"CLONAZEPAM", r"2"),
    (267197, "Diazepam 10 mg", "comprimido", r"DIAZEPAM", r"10"),
    (267618, "Carbamazepina 200 mg", "comprimido", r"CARBAMAZEPIN", r"200"),
    (267660, "Fenobarbital 100 mg", "comprimido", r"FENOBARBITAL", r"100"),
    (268149, "Risperidona 2 mg", "comprimido", r"RISPERIDON", r"2"),
    (267669, "Haloperidol 5 mg", "comprimido", r"HALOPERIDOL", r"5"),
    (267743, "Prednisona 20 mg", "comprimido", r"PREDNISONA", r"20"),
    (267676, "Ibuprofeno 600 mg", "comprimido", r"IBUPROFEN", r"600"),
    (267778, "Paracetamol 500 mg", "comprimido", r"PARACETAMOL", r"500"),
    (267203, "Dipirona 500 mg", "comprimido", r"DIPIRONA", r"500"),
    (271089, "Amoxicilina 500 mg", "cápsula", r"AMOXICILIN", r"500"),
    (267140, "Azitromicina 500 mg", "comprimido", r"AZITROMICIN", r"500"),
    (267625, "Cefalexina 500 mg", "cápsula", r"CEFALEXIN", r"500"),
    (267632, "Ciprofloxacino 500 mg", "comprimido", r"CIPROFLOXACIN", r"500"),
    (267717, "Metronidazol 250 mg", "comprimido", r"METRONIDAZOL", r"250"),
    (267506, "Albendazol 400 mg", "comprimido", r"ALBENDAZOL", r"400"),
    (273466, "Loratadina 10 mg", "comprimido", r"LORATADIN", r"10"),
    (267503, "Ácido fólico 5 mg", "comprimido", r"ACIDO FOLICO", r"5"),
    (268252, "Dipirona injetável 500 mg/ml", "ampola", r"DIPIRONA", r"500\s*MG\s*/\s*ML"),
    (271003, "Diclofenaco injetável 25 mg/ml", "ampola", r"DICLOFENAC", r"25\s*MG\s*/\s*ML"),
]
NOME = {r[0]: r[1] for r in REMEDIOS}
FORMA = {r[0]: r[2] for r in REMEDIOS}

# Unidades aceitas por forma. Comprimido e cápsula andam juntos: o mesmo código CATMAT às vezes é vendido nas duas
# formas, pelo mesmo preço (amoxicilina 500 mg: 169 compras em cápsula, 106 em comprimido em 2026).
UNIDADES_COMPRASGOV = {"comprimido": {"COMPR", "CAPS", "DRG"}, "cápsula": {"COMPR", "CAPS", "DRG"}, "ampola": {"AM", "AMP"}}
UNIDADES_LIVRES = {
    "solido": re.compile(r"^(CP|CPR|CPS|COM|COMP|COMPR|COMPRIM|COMPRIMIDOS?|CAP|CAPS|CAPSULAS?|CMP|DRG|DRAGEAS?|UN|UND|UNID|UNIDADES?|UNIT|UNITARIO)\.?$"),
    "ampola": re.compile(r"^(AMP|AMPOLAS?|AM|UN|UND|UNID|UNIDADES?|UNIT|UNITARIO)\.?$"),
}
# Na descrição livre, o item que leva outro princípio ativo junto, ou outra forma, não é o mesmo remédio.
OUTRO = re.compile(r"\+|\bASSOC|\bCOM\s+[A-Z]{5,}INA\b|HIDROCLOROTIAZ.*(LOSARTAN|CAPTOPRIL|ENALAPRIL)|(LOSARTAN|CAPTOPRIL|ENALAPRIL).*HIDROCLOROTIAZ|"
                   r"CLAVUL|SULBACT|CODEIN|CAFEIN|ESCOPOLAMIN|ORFENADRIN|GLIBENCL.*METFORMIN|METFORMIN.*(GLIBENCL|GLIMEPIR|SITAGLIP|VILDAGLIP|DAPAGLI|EMPAGLI|"
                   r"LINAGLIP|SAXAGLIP|ALOGLIP|GLICLAZ)|ANLODIPINO.*LOSARTAN|LOSARTAN.*ANLODIPIN|GOTAS|SUSP|XAROPE|SOLUCAO|INFANTIL|PEDIATR|"
                   r"PROLONGAD|LIBERACAO|RETARD|\bXR\b|\bAP\b|\bSR\b|\bCR\b|EFERVESC|MASTIGAV|DISPERSIV|SUBLINGU|VAGINAL|CREME|POMADA|GEL\b|COLIRIO|"
                   r"SUPOSIT|TOPIC|MANIPUL|VETERIN|PO PARA|\bCLAV|MAGNESI|TAMPONAD|JUDICIAL|\bMUPS\b")
OUTRO_INJETAVEL = re.compile(r"\+|\bASSOC|ESCOPOLAMIN|ORFENADRIN|ADIFENIN|PROMETAZIN|COMPRIMID|GOTAS|ORAL\b|VETERIN")

ANO_ATUAL = dt.date.today().year
ANOS = [ANO_ATUAL - 1, ANO_ATUAL]
ERRO_DE_UNIDADE = 30   # vezes a mediana do ano: acima disso (ou abaixo de 1/30) é o preço da caixa, ou digitação
MAIS_CARA = 2.0        # vezes a mediana das compras parecidas
A_MAIS_MINIMO = 1000   # reais, se comprar a quantidade toda
MIN_COMPRAS, MIN_COMPRADORES = 20, 10
MODALIDADE = {5: "pregão", 6: "dispensa", 7: "inexigibilidade", 1: "convite", 2: "tomada de preços", 3: "concorrência"}
MEI = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}\s")
# Compradores com código de cidade que não são a prefeitura: entram na mediana nacional, mas não na página da cidade.
NAO_E_PREFEITURA = re.compile(r"CONSORC|CONS\.|C[AÂ]MARA MUN|ZOOBOT|PARQUES|CONSELHO|UNIVERSIDADE|FACULDADE|INSTITUTO FEDERAL", re.I)
REGIAO = {u: r for r, us in {"Norte": "AC AM AP PA RO RR TO", "Nordeste": "AL BA CE MA PB PE PI RN SE", "Centro-Oeste": "DF GO MS MT",
                             "Sudeste": "ES MG RJ SP", "Sul": "PR RS SC"}.items() for u in us.split()}
UF_CODIGO = {s: k for k, s in c.SIGLAS.items()}
# O nome de algumas UASGs começa com o código do sistema: "MBA-PREFEITURA MUNICIPAL DE DOM BASILIO", "EPA - SECRETARIA…".
PREFIXO_UASG = re.compile(r"^[MEC](%s)\s*-\s*" % "|".join(c.SIGLAS.values()))


def sem_acento(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", (s or "").upper()) if unicodedata.category(ch) != "Mn")


def bonito(s: str) -> str:
    """"FUNDO MUNICIPAL DE SAUDE DE MARABA - PA" → "Fundo Municipal de Saude de Maraba - PA" (siglas de 2 letras ficam)."""
    s = re.sub(r"\s+", " ", s or "").strip()
    if s != s.upper():
        return s
    pequenas = {"de", "da", "do", "das", "dos", "e", "em", "para", "a", "o"}
    out = []
    for i, p in enumerate(s.lower().split(" ")):
        if len(p) == 2 and p.isalpha() and p.upper() in c.SIGLAS.values():
            out.append(p.upper())
        elif i > 0 and p in pequenas:
            out.append(p)
        elif p in ("ltda", "ltda.", "s/a", "s.a.", "me", "epp", "eireli"):
            out.append(p.upper() if p not in ("ltda", "ltda.") else p.capitalize())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out)


# ---------------------------------------------------------------------------------------------------------------------
# Compras.gov.br


def _get_json(url: str, tentativas: int = 6) -> dict:
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=240, context=CONTEXTO_TLS) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError):
            # Até o 400 ("Bad Request") é passageiro nessa API: a mesma consulta responde minutos depois.
            time.sleep(10 * (t + 1))
    raise RuntimeError(f"sem resposta: {url}")


def baixar_codigo(codigo: int, ano: int) -> list[dict]:
    """Todas as compras do código no ano. O ano passado fica guardado; o atual é baixado de novo depois de 6 dias."""
    arq = PASTA / "comprasgov" / f"{codigo}-{ano}.json.gz"
    if arq.exists() and (ano < ANO_ATUAL or time.time() - arq.stat().st_mtime < 6 * 86400):
        return json.loads(gzip.decompress(arq.read_bytes()))
    fim = f"{ano}-12-31" if ano < ANO_ATUAL else dt.date.today().isoformat()
    linhas, p = [], 1
    while True:
        q = urllib.parse.urlencode({"pagina": p, "tamanhoPagina": 500, "tipo": "codigoItemCatalogo", "codigo": codigo,
                                    "dataCompraInicio": f"{ano}-01-01", "dataCompraFim": fim})
        d = _get_json(f"{URL_PESQUISA}?{q}")
        linhas += d.get("resultado") or []
        if not d.get("paginasRestantes"):
            break
        p += 1
    campos = ("idCompra", "dataCompra", "modalidade", "quantidade", "precoUnitario", "siglaUnidadeFornecimento", "niFornecedor",
              "nomeFornecedor", "codigoUasg", "nomeUasg", "estado", "codigoMunicipio", "municipio", "esfera")
    linhas = [{k: x.get(k) for k in campos} for x in linhas]
    for x in linhas:   # nunca o CPF: o documento do fornecedor só fica se for CNPJ
        if len(re.sub(r"\D", "", x.get("niFornecedor") or "")) != 14:
            x["niFornecedor"], x["nomeFornecedor"] = "", ""
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_bytes(gzip.compress(json.dumps(linhas, ensure_ascii=False).encode()))
    return linhas


def compras_comprasgov() -> list[dict]:
    """As compras do Compras.gov.br no formato comum: uma por item comprado."""
    pedidos = [(cod, ano) for cod, *_ in REMEDIOS for ano in ANOS]
    with ThreadPoolExecutor(4) as ex:
        brutos = list(ex.map(lambda p: (p, baixar_codigo(*p)), pedidos))
    saida = []
    for (cod, ano), linhas in brutos:
        aceitas = UNIDADES_COMPRASGOV[FORMA[cod]]
        for x in linhas:
            if (x.get("dataCompra") or "")[:4] != str(ano) or not x.get("precoUnitario") or not x.get("quantidade"):
                continue
            if x.get("siglaUnidadeFornecimento") not in aceitas:
                continue
            esfera = x.get("esfera")
            ibge = x.get("codigoMunicipio")
            fornecedor = x.get("nomeFornecedor") or ""
            saida.append({
                "codigo": cod, "ano": ano, "data": x["dataCompra"][:10], "preco": float(x["precoUnitario"]), "qtd": float(x["quantidade"]),
                "esfera": esfera, "uf": x.get("estado") or "", "ibge": int(ibge) if ibge else None,
                "comprador": bonito(PREFIXO_UASG.sub("", x.get("nomeUasg") or "")), "id_comprador": f"uasg:{x.get('codigoUasg')}",
                "fornecedor": "" if MEI.match(fornecedor) else bonito(fornecedor),
                "modalidade": MODALIDADE.get(x.get("modalidade"), "outra"), "link": LINK_COMPRASGOV.format(x.get("idCompra")),
                "fonte": "c",
            })
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# PNCP (pregões de todas as plataformas, baixados pelo precos_pncp.py)

LINK_PNCP = "https://pncp.gov.br/app/editais/{}/{}/{}"
# No pregão o preço final não pode passar do estimado. Muito acima dele, o homologado é o preço da caixa e o estimado,
# o do comprimido (Pains-MG, 2026: losartana estimada a R$ 0,04, homologada a R$ 30,41).
ACIMA_DO_ESTIMADO = 3


GENERICO_ORGAO = {"MUNICIPIO", "PREFEITURA", "MUNICIPAL", "FUNDO", "SAUDE", "SECRETARIA", "ESTADO", "GOVERNO", "CAMARA",
                  "CONSORCIO", "INTERMUNICIPAL", "PUBLICA", "PUBLICO"}


def nome_pncp(unidade: str, orgao: str, cidade: str = "") -> str:
    """O nome do comprador no PNCP: a unidade ("Secretaria de Saúde", "Unidade Única") muitas vezes não diz a cidade;
    nesse caso o órgão vai entre parênteses, ou a cidade, quando nem o órgão a diz ("Fundo Municipal de Saúde")."""
    palavras = lambda t: {w for w in re.findall(r"[A-Z]{3,}", sem_acento(t).upper()) if w not in GENERICO_ORGAO}
    nome = bonito(unidade.strip() or orgao)
    for extra in (orgao, cidade):
        chaves = palavras(extra)
        if chaves:
            return nome if chaves & palavras(nome) else f"{nome} ({bonito(extra) if extra == orgao else extra})"
    return nome


def compras_pncp(sem_rs: bool) -> tuple[list[dict], int]:
    """As compras do PNCP no formato comum, menos as que já vêm de outra fonte: as feitas no Compras.gov.br (estão na
    pesquisa de preço) e, com o LicitaCon, as das prefeituras do RS. Devolve também quantas foram tiradas por passar do
    estimado."""
    from .precos_pncp import compras_guardadas   # aqui, e não no topo: precos_pncp importa deste módulo

    cidades = {str(m["ibge"]): m["nome"] for m in json.loads(MUNICIPIOS.read_text(encoding="utf-8"))["cidades"]} if MUNICIPIOS.exists() else {}
    saida, acima = [], 0
    for x in compras_guardadas():
        if x.get("plataforma") == "Compras.gov.br" or (not sem_rs and x.get("esfera") == "M" and x.get("uf") == "RS"):
            continue
        esfera = "E" if x.get("esfera") == "D" else x.get("esfera")
        comprador = nome_pncp(x.get("unidade") or "", x.get("orgao") or "", cidades.get(str(x.get("ibge") or ""), ""))
        for i in x["itens"]:
            if casar(i["descricao"], i.get("unidade") or "") != i["codigo"]:   # a regra do casamento pode ter mudado
                continue
            res = [r for r in i["resultados"] if r.get("preco")]
            if not res:
                continue
            r = min(res, key=lambda r: r.get("ordem") or 1)   # no registro de preço, o primeiro colocado
            preco = float(r["preco"])
            qtd = float(r.get("qtd") or i.get("qtd") or 0)
            data = r.get("data") or x.get("publicacao") or ""
            if not qtd or data[:4] not in {str(a) for a in ANOS}:
                continue
            if i.get("estimado") and preco > ACIMA_DO_ESTIMADO * float(i["estimado"]):
                acima += 1
                continue
            fornecedor = r.get("fornecedor") or ""
            saida.append({
                "codigo": i["codigo"], "ano": int(data[:4]), "data": data, "preco": preco, "qtd": qtd, "esfera": esfera, "uf": x.get("uf") or "",
                "ibge": int(x["ibge"]) if esfera == "M" and str(x.get("ibge") or "").isdigit() else None,
                "comprador": comprador, "id_comprador": f"pncp:{x['cnpj']}:{x.get('unidade')}",
                "fornecedor": "" if MEI.match(fornecedor) else bonito(fornecedor),
                "modalidade": "pregão", "link": LINK_PNCP.format(x["cnpj"], x["ano"], x["seq"]), "fonte": "p",
            })
    return saida, acima


# ---------------------------------------------------------------------------------------------------------------------
# LicitaCon (TCE-RS)


def baixar_licitacon(ano: int) -> Path:
    arq = PASTA / "licitacon" / f"{ano}.csv.zip"
    if arq.exists() and (ano < ANO_ATUAL - 1 or time.time() - arq.stat().st_mtime < 6 * 86400):
        return arq
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    req = urllib.request.Request(URL_LICITACON.format(ano=ano), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=1800, context=CONTEXTO_TLS) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(arq)
    return arq


def _num(s: str | None) -> float:
    """Número do LicitaCon; vazio ou estragado ("#################") vira 0."""
    try:
        return float(s or 0)
    except ValueError:
        return 0.0


def _ler(z: zipfile.ZipFile, nome: str):
    return csv.DictReader(io.TextIOWrapper(z.open(nome), encoding="utf-8-sig", errors="replace"))


def casar(descricao: str, unidade: str) -> int | None:
    """O código da lista para uma descrição livre ("LOSARTANA POTÁSSICA 50MG COMPRIMIDO"), ou None."""
    t = sem_acento(descricao)
    u = sem_acento(unidade).strip()
    for cod, _, forma, ativo, dose in REMEDIOS:
        if not re.search(r"\b(?:%s)" % ativo, t):   # "OMEPRAZOL" não pode casar "ESOMEPRAZOL"
            continue
        injetavel = forma == "ampola"
        if injetavel:
            if not re.search(r"INJET|AMP", t) or OUTRO_INJETAVEL.search(t) or not re.search(r"\b%s\b" % dose, t):
                continue
            if not UNIDADES_LIVRES["ampola"].match(u):
                continue
        else:
            if re.search(r"INJET|AMPOL|FRASCO|LIOFIL|MG\s*/\s*ML|\bCX\b|CAIXA|BLISTER|\bC/\s*\d", t) or OUTRO.search(t):
                continue
            # a dosagem do item: o número antes de "MG" (ou "MCG") tem de ser o da lista, e não pode haver outra dosagem
            doses = re.findall(r"(\d+(?:[.,]\d+)?)\s*(MG|MCG|UG|µG|G)\b", t)
            alvo = float(re.match(r"\d+", dose).group())
            if not doses or any(float(d.replace(",", ".")) != alvo for d, _ in doses):
                continue
            if "MCG" in dose and not any(un in ("MCG", "UG", "µG") for _, un in doses):
                continue
            if "MCG" not in dose and not all(un == "MG" for _, un in doses):
                continue
            if not UNIDADES_LIVRES["solido"].match(u):
                continue
        return cod
    return None


def _ibge_rs() -> dict[str, int]:
    """Nome da cidade (sem acento) → código IBGE, para as prefeituras do RS ("PM DE SELBACH")."""
    doc = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    return {sem_acento(x["nome"]): x["ibge"] for x in doc["cidades"] if x["uf"] == "RS"}


def ler_licitacon(ano: int, arq: Path, ibge_rs: dict[str, int]) -> tuple[list[dict], dict[int, dict]]:
    """As compras dos remédios da lista (no formato comum) e a disputa nos pregões de remédio das prefeituras."""
    z = zipfile.ZipFile(arq)
    chave = lambda r: (r["CD_ORGAO"], r["NR_LICITACAO"], r["ANO_LICITACAO"], r["CD_TIPO_MODALIDADE"])
    lic, orgao_ibge = {}, {}
    for r in _ler(z, "licitacao.csv"):
        nome = sem_acento(r["NM_ORGAO"])
        m = re.match(r"^PM DE (.+)$", nome)
        if m and m.group(1).strip() in ibge_rs:
            orgao_ibge[r["CD_ORGAO"]] = ibge_rs[m.group(1).strip()]
        lic[chave(r)] = {"orgao": r["CD_ORGAO"], "nome": r["NM_ORGAO"], "mod": r["CD_TIPO_MODALIDADE"], "objeto": r["DS_OBJETO"] or "",
                         "homologacao": (r["DT_HOMOLOGACAO"] or "")[:10], "link": r["LINK_LICITACON_CIDADAO"] or "",
                         "valor": _num(r["VL_HOMOLOGADO"])}
    pregao = {"PCE", "PRP", "PRE"}
    # Propostas por item: só contadas (o documento pode ser um CPF e não é guardado).
    propostas: dict[tuple, set[int]] = defaultdict(set)
    for r in _ler(z, "item_prop.csv"):
        k = chave(r)
        if k in lic and lic[k]["mod"] in pregao:
            propostas[k + (r["NR_LOTE"], r["NR_ITEM"])].add(hash(r["NR_DOCUMENTO"]))
    # Um órgão "informa as perdedoras" quando mostra mais de uma empresa em pelo menos metade dos itens dos seus pregões.
    por_orgao = defaultdict(lambda: [0, 0])
    for k, v in propostas.items():
        por_orgao[k[0]][0] += 1
        por_orgao[k[0]][1] += len(v) > 1
    informa = {o for o, (n, mais) in por_orgao.items() if n >= 20 and mais / n >= 0.5}

    compras, pregoes_remedio, vencedores = [], set(), {}
    leitor = csv.reader(io.TextIOWrapper(z.open("item.csv"), encoding="utf-8-sig", errors="replace"))
    cab = next(leitor)
    col = {n: cab.index(n) for n in ("CD_ORGAO", "NR_LICITACAO", "ANO_LICITACAO", "CD_TIPO_MODALIDADE", "NR_LOTE", "NR_ITEM", "DS_ITEM",
                                     "QT_ITENS", "SG_UNIDADE_MEDIDA", "VL_UNITARIO_HOMOLOGADO")}
    # O vencedor vem num de dois pares de colunas TP_DOCUMENTO/NR_DOCUMENTO (nunca nos dois); só o CNPJ é lido.
    docs = [(i, i + 1) for i, n in enumerate(cab) if n == "TP_DOCUMENTO" and i + 1 < len(cab) and cab[i + 1] == "NR_DOCUMENTO"]
    for linha in leitor:
        if len(linha) < len(cab):
            continue
        k = tuple(linha[col[n]] for n in ("CD_ORGAO", "NR_LICITACAO", "ANO_LICITACAO", "CD_TIPO_MODALIDADE"))
        if k not in lic:
            continue
        cod = casar(linha[col["DS_ITEM"]], linha[col["SG_UNIDADE_MEDIDA"]])
        if cod is None:
            continue
        L = lic[k]
        pregoes_remedio.add(k)
        preco, qtd = _num(linha[col["VL_UNITARIO_HOMOLOGADO"]]), _num(linha[col["QT_ITENS"]])
        data = L["homologacao"]
        if not preco or not qtd or data[:4] != str(ano) or L["orgao"] not in orgao_ibge:
            continue
        cnpj = next((re.sub(r"\D", "", linha[j]) for i, j in docs if linha[i] == "J"), "")
        if cnpj:
            vencedores[cnpj] = ""
        compras.append({
            "codigo": cod, "ano": ano, "data": data, "preco": preco, "qtd": qtd, "esfera": "M", "uf": "RS",
            "ibge": orgao_ibge[L["orgao"]], "comprador": "Prefeitura de " + bonito(re.sub(r"^PM DE ", "", L["nome"].upper())),
            "id_comprador": f"tcers:{L['orgao']}", "fornecedor": cnpj,
            "modalidade": {"PCE": "pregão", "PRP": "pregão", "PRE": "pregão", "PRD": "dispensa", "PRI": "inexigibilidade"}.get(L["mod"], "outra"),
            "link": L["link"], "fonte": "rs",
        })
    # O nome das empresas vencedoras (só CNPJ; o arquivo de pessoas também tem pessoas físicas, que não são lidas).
    if vencedores:
        for r in _ler(z, "pessoas.csv"):
            if r.get("TP_DOCUMENTO") != "J":
                continue
            d = re.sub(r"\D", "", r.get("NR_DOCUMENTO") or "")
            if d in vencedores:
                vencedores[d] = r.get("NM_PESSOA") or ""
    for x in compras:
        nome = vencedores.get(x["fornecedor"], "") if x["fornecedor"] else ""
        x["fornecedor"] = "" if MEI.match(nome) else bonito(nome)

    # A disputa: pregões de remédio das prefeituras homologados no ano (o objeto fala em medicamento e algum item é da
    # lista). Conta todos os itens do pregão, não só os da lista.
    alvo = {k for k in pregoes_remedio if lic[k]["mod"] in pregao and lic[k]["orgao"] in orgao_ibge
            and re.search("MEDICAMENT", sem_acento(lic[k]["objeto"])) and lic[k]["homologacao"][:4] == str(ano)}
    por_pregao = defaultdict(list)
    for kk, v in propostas.items():
        if kk[:4] in alvo:
            por_pregao[kk[:4]].append(len(v))
    disputa: dict[int, dict] = {}
    for k in alvo:
        L, ns = lic[k], por_pregao.get(k, [])
        if not ns:
            continue
        d = disputa.setdefault(orgao_ibge[L["orgao"]], {"ano": ano, "informa": L["orgao"] in informa, "pregoes": 0, "itens": 0, "um": 0, "so_um": []})
        um = sum(1 for n in ns if n == 1)
        d["pregoes"] += 1
        d["itens"] += len(ns)
        d["um"] += um
        if um == len(ns):
            d["so_um"].append([re.sub(r"\s+", " ", L["objeto"]).strip()[:160], L["homologacao"], len(ns), round(L["valor"], 2), L["link"]])
    for d in disputa.values():
        d["n_so_um"] = len(d["so_um"])
        d["so_um"] = sorted(d["so_um"], key=lambda x: -x[3])[:3]
    return compras, disputa


# ---------------------------------------------------------------------------------------------------------------------
# A comparação


def _quantil(v: list[float], p: float) -> float:
    v = sorted(v)
    i = (len(v) - 1) * p
    a = int(i)
    return v[a] + (v[min(a + 1, len(v) - 1)] - v[a]) * (i - a)


def comparar(compras: list[dict]) -> tuple[dict, list[dict]]:
    """Para cada remédio e ano: a mediana, a faixa e as medianas das compras parecidas. Marca cada compra com a razão."""
    grupos = defaultdict(list)
    for x in compras:
        grupos[(x["codigo"], x["ano"])].append(x)
    resumo, aceitas = {}, []
    for (cod, ano), xs in grupos.items():
        m0 = st.median(x["preco"] for x in xs)
        bons = [x for x in xs if m0 / ERRO_DE_UNIDADE <= x["preco"] <= m0 * ERRO_DE_UNIDADE]
        compradores = {x["id_comprador"] for x in bons}
        if len(bons) < MIN_COMPRAS or len(compradores) < MIN_COMPRADORES:
            continue
        qs = [x["qtd"] for x in bons]
        t1, t2 = _quantil(qs, 1 / 3), _quantil(qs, 2 / 3)
        grupo = lambda q: 0 if q <= t1 else 1 if q <= t2 else 2
        med_grupo = [st.median([x["preco"] for x in bons if grupo(x["qtd"]) == g] or [m0]) for g in range(3)]
        regioes = defaultdict(list)
        for x in bons:
            regioes[REGIAO.get(x["uf"], "")].append(x["preco"])
        precos = [x["preco"] for x in bons]
        resumo[(cod, ano)] = {
            "n": len(bons), "compradores": len(compradores), "fora": len(xs) - len(bons),
            "mediana": round(st.median(precos), 4), "faixa": [round(_quantil(precos, 0.25), 4), round(_quantil(precos, 0.75), 4)],
            "grupos": [[round(t1), round(med_grupo[0], 4)], [round(t2), round(med_grupo[1], 4)], [None, round(med_grupo[2], 4)]],
            "regioes": {r: [len(v), round(st.median(v), 4)] for r, v in sorted(regioes.items()) if r and len(v) >= 5},
        }
        for x in bons:
            ref = med_grupo[grupo(x["qtd"])]
            x["ref"] = ref
            x["razao"] = x["preco"] / ref
            x["a_mais"] = max(0.0, (x["preco"] - ref) * x["qtd"])
            aceitas.append(x)
    return resumo, aceitas


def por_ente(aceitas: list[dict]) -> tuple[dict, dict]:
    mun, uf = defaultdict(list), defaultdict(list)
    for x in aceitas:
        if x["esfera"] == "M" and x["ibge"] and not NAO_E_PREFEITURA.search(x["comprador"]):
            mun[str(x["ibge"])].append(x)
        elif x["esfera"] == "E" and x["uf"] in UF_CODIGO:
            uf[str(UF_CODIGO[x["uf"]])].append(x)
        elif x["esfera"] == "M" and x["ibge"] == 5300108:   # Distrito Federal (esfera "E" ou "M" conforme o órgão)
            uf["53"].append(x)

    def montar(xs: list[dict]) -> dict:
        caras = sorted((x for x in xs if x["razao"] >= MAIS_CARA and x["a_mais"] >= A_MAIS_MINIMO), key=lambda x: -x["a_mais"])
        return {
            "n": len(xs), "r": len({x["codigo"] for x in xs}),
            "baratas": sum(1 for x in xs if x["razao"] <= 1),
            "caras": [[x["codigo"], x["ano"], x["data"], round(x["preco"], 4), round(x["ref"], 4), round(x["qtd"]), round(x["a_mais"]),
                       x["modalidade"], x["comprador"], x["fornecedor"], x["link"]] for x in caras[:12]],
            "n_caras": len(caras),
            "n_dobro": sum(1 for x in xs if x["razao"] >= MAIS_CARA),
        }
    return {k: montar(v) for k, v in mun.items()}, {k: montar(v) for k, v in uf.items()}


def montar(compras: list[dict], disputa: dict[int, dict]) -> tuple[dict, dict]:
    resumo, aceitas = comparar(compras)
    mun, uf = por_ente(aceitas)
    for ibge, d in disputa.items():
        mun.setdefault(str(ibge), {"n": 0, "r": 0, "baratas": 0, "caras": [], "n_caras": 0, "n_dobro": 0})["rs"] = d
    hoje = dt.date.today().isoformat()
    doc = {
        "fonte": "Compras.gov.br (pesquisa de preço), PNCP e LicitaCon (TCE-RS)", "gerado": hoje, "anos": ANOS,
        "regras": {"mais_cara": MAIS_CARA, "a_mais": A_MAIS_MINIMO, "erro": ERRO_DE_UNIDADE},
        "remedios": {str(cod): [nome, forma] for cod, nome, forma, *_ in REMEDIOS},
        "mun": dict(sorted(mun.items())), "uf": dict(sorted(uf.items())),
    }
    por_cod = defaultdict(list)
    for x in aceitas:
        por_cod[(x["codigo"], x["ano"])].append(x)
    nacional = {"gerado": hoje, "anos": ANOS, "remedios": []}
    for cod, nome, forma, *_ in REMEDIOS:
        anos = {}
        for ano in ANOS:
            r = resumo.get((cod, ano))
            if not r:
                continue
            xs = sorted(por_cod[(cod, ano)], key=lambda x: -x["razao"])
            r["compras"] = [[x["comprador"], x["uf"], x["esfera"], x["ibge"] if x["esfera"] == "M" else None, x["data"], round(x["preco"], 4),
                             round(x["qtd"]), round(x["razao"], 2), x["modalidade"], x["link"]] for x in xs]
            anos[str(ano)] = r
        if anos:
            nacional["remedios"].append({"codigo": cod, "nome": nome, "forma": forma, "anos": anos})
    return doc, nacional


def _gravar(doc: dict, *destinos: Path) -> None:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(texto, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(prog="precos", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia as versões guardadas em pipeline/referencia")
    p.add_argument("--sem-rs", action="store_true", help="sem o LicitaCon do RS")
    args = p.parse_args()
    if args.sem_baixar:
        for ref, saida in ((REFERENCIA, SAIDA), (REFERENCIA_NACIONAL, SAIDA_NACIONAL)):
            if not ref.exists():
                raise SystemExit(f"falta {ref}")
            saida.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ref, saida)
            print(f"copiado {ref.relative_to(c.RAIZ)}")
        return

    compras = compras_comprasgov()
    print(f"Compras.gov.br: {len(compras)} compras de {len(REMEDIOS)} remédios em {ANOS}")
    pncp, acima = compras_pncp(args.sem_rs)
    compras += pncp
    print(f"PNCP (outras plataformas): {len(pncp)} compras; {acima} tiradas por passar de {ACIMA_DO_ESTIMADO} vezes o preço estimado")
    disputa: dict[int, dict] = {}
    if not args.sem_rs:
        ibge_rs = _ibge_rs()
        # As prefeituras do RS vêm do LicitaCon, que tem todas (as que compram pelo Compras.gov.br também).
        compras = [x for x in compras if not (x["esfera"] == "M" and x["uf"] == "RS")]
        for ano in ANOS:
            rs, disp = ler_licitacon(ano, baixar_licitacon(ano), ibge_rs)
            compras += rs
            if ano == ANO_ATUAL:   # a disputa mostrada é a do ano atual
                disputa = disp
            print(f"LicitaCon {ano}: {len(rs)} compras de prefeituras do RS casadas com a lista; {len(disp)} prefeituras com pregão de remédio")
    doc, nacional = montar(compras, disputa)
    _gravar(doc, SAIDA, REFERENCIA)
    _gravar(nacional, SAIDA_NACIONAL, REFERENCIA_NACIONAL)
    caras = sum(e["n_caras"] for e in doc["mun"].values())
    print(f"{len(nacional['remedios'])} remédios com mediana; {len(doc['mun'])} cidades e {len(doc['uf'])} estados com compra comparada; "
          f"{caras} compras de prefeitura acima de {MAIS_CARA:g} vezes a mediana das parecidas")
    for r in nacional["remedios"][:8]:
        a = r["anos"].get(str(ANO_ATUAL)) or next(iter(r["anos"].values()))
        print(f"  {r['nome']:32s} mediana R$ {a['mediana']:.4f}  faixa {a['faixa'][0]:.4f}-{a['faixa'][1]:.4f}  {a['n']} compras de {a['compradores']}")
    print(f"gravado em {SAIDA.relative_to(c.RAIZ)} e {SAIDA_NACIONAL.relative_to(c.RAIZ)} (cópias em pipeline/referencia)")


if __name__ == "__main__":
    main()
