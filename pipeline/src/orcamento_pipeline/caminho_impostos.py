"""O caminho dos impostos: quem cobra cada imposto, o que é repassado a outro governo e quem fica com o
dinheiro no fim (página /impostos; levantamento em docs/levantamento-caminho-impostos.md).

    uv run caminho-impostos               # monta o ano de ANO a partir dos caches e das planilhas do Tesouro
    uv run caminho-impostos --sem-baixar  # só copia pipeline/referencia/caminho-impostos.json (publicação)

Fontes (todas de um ano fechado, que não muda mais):
- União: Resultado do Tesouro Nacional (RTN), série histórica, aba 2.2 (R$ milhões correntes): a arrecadação
  por tributo e o total de cada repasse por repartição de receita (o lado de quem manda o dinheiro).
  A planilha vem do mesmo endereço que contas_federal.py usa (data/raw/tesouro/rtn/).
- Estados e prefeituras: Declaração de Contas Anuais (DCA), Anexo I-C, do SICONFI, no cache que o FINBRA e o mapa
  já mantêm (data/raw/siconfi/dca-ic/{ano}.json.gz). Dá o que cada governo cobrou de cada imposto e o que recebeu
  de cada repasse (o lado de quem recebe), com as deduções para o Fundeb. Prefeituras sem a DCA do ano entram
  com a do ano anterior (são ~50 cidades pequenas, menos de 1% do total).
- Benefícios fiscais da União: Demonstrativo dos Gastos Tributários da Receita Federal (ver GASTOS_TRIBUTARIOS).

Regra para não contar duas vezes: cada real aparece uma vez só na coluna "o que se paga" (o imposto, no governo
que o cobra). Um repasse é uma ligação entre dois governos, não um imposto novo. No fim, o que cada governo fica é
o que cobrou, menos o que repassou, mais o que recebeu, e a soma do que todos ficam é igual à soma do que se pagou.
O programa confere essa conta e confere cada repasse pelos dois lados (quem manda e quem recebe).

Saída em site/public/data/impostos/caminho.json, com cópia versionada em pipeline/referencia/caminho-impostos.json:
    {"ano": 2025, "fonte": …, "nos": [{"id", "nome", "coluna": 0|1|2, "esfera"}],
     "fluxos": [{"de", "para", "valor" (R$ bi), "tipo", "nome", "id"}],
     "governos": {"uniao"|"estados"|"prefeituras": {"cobra", "repassa", "recebe", "fica"}},
     "deixa": {…benefícios fiscais…}, "conferencia": [{"nome", "manda", "recebe"}], "populacao": …}
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone

import openpyxl

from . import cidades as c
from . import contas_federal as cf

ANO = 2025
SAIDA = c.RAIZ / "site" / "public" / "data" / "impostos" / "caminho.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "caminho-impostos.json"
PASTA_DCA = c.PASTA_BRUTO / "dca-ic"

BRUTA = "Receitas Brutas Realizadas"
DED_FUNDEB = "Deduções - FUNDEB"
DED_OUTRAS = "Outras Deduções da Receita"
TOTAL = "RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)"


# ── DCA (estados e prefeituras) ──────────────────────────────────────────────────────────────────

def _codigo(conta: str) -> str:
    m = re.match(r"\s*([\d.]+)\s*-", conta or "")
    return m.group(1) if m else (conta or "").strip()


def ler_dca(ano: int) -> dict[str, dict[tuple[str, str], float]]:
    """{ibge: {(código da conta, coluna): valor em R$}} do Anexo I-C, para estados (2 dígitos) e municípios.

    Município sem a DCA do ano entra com a do ano anterior (se tiver); quantos e quanto pesam vai em "faltam".
    """
    def carregar(a: int) -> dict[str, list[dict]]:
        return json.loads(gzip.decompress((PASTA_DCA / f"{a}.json.gz").read_bytes()))

    brutos = carregar(ano)
    try:
        antes = carregar(ano - 1)
    except FileNotFoundError:
        antes = {}
    entes = json.loads((c.PASTA_BRUTO / "entes.json").read_text(encoding="utf-8"))
    municipios = {str(e["cod_ibge"]): e for e in entes if e["esfera"] == "M" and e["cod_ibge"] != 5300108}
    faltam = [k for k in municipios if not brutos.get(k)]
    do_ano_anterior = [k for k in faltam if antes.get(k)]
    for k in do_ano_anterior:
        brutos[k] = antes[k]
    saida: dict[str, dict[tuple[str, str], float]] = {}
    for ibge, linhas in brutos.items():
        if not linhas or (len(ibge) != 2 and ibge not in municipios):
            continue
        d: dict[tuple[str, str], float] = defaultdict(float)
        for l in linhas:
            d[(_codigo(l["conta"]), l["coluna"])] += float(l["valor"] or 0)
        saida[ibge] = d
    ler_dca.faltam = {  # type: ignore[attr-defined]
        "sem_dca": len(faltam), "com_ano_anterior": len(do_ano_anterior),
        "populacao_sem_nenhuma": sum(municipios[k]["populacao"] for k in faltam if k not in do_ano_anterior),
    }
    return saida


def somar(dca: dict, esfera: str, conta: str, coluna: str = BRUTA, uf: str | None = None) -> float:
    """Soma de uma conta numa esfera ('E' estados e DF, 'M' municípios), em R$ bilhões."""
    t = 0.0
    for ibge, d in dca.items():
        if (len(ibge) == 2) != (esfera == "E"):
            continue
        if uf and ibge[:2] != uf:
            continue
        t += d.get((conta, coluna), 0.0)
    return t / 1e9


def liquida(dca: dict, esfera: str, conta: str) -> float:
    """Arrecadação de um imposto sem as restituições ("outras deduções"); as deduções do Fundeb e das cotas das
    prefeituras não saem daqui, porque são repasses e entram como ligação."""
    return somar(dca, esfera, conta) - abs(somar(dca, esfera, conta, DED_OUTRAS))


def fundeb_liquido(dca: dict) -> dict:
    """O Fundeb por estado: quanto o governo estadual e as prefeituras põem (dedução de 20% de impostos e
    repasses) e tiram (pelo número de alunos). O que o estado põe a mais do que tira vai, no fim, para as
    prefeituras do mesmo estado. A complementação da União fica de fora (é conta 1.7.1.5, um repasse à parte)."""
    por_uf = {}
    for uf in sorted(k for k in dca if len(k) == 2):
        cs = abs(dca[uf].get((TOTAL, DED_FUNDEB), 0.0)) / 1e9
        rs = dca[uf].get(("1.7.5.1.00.0.0", BRUTA), 0.0) / 1e9
        cm = abs(somar(dca, "M", TOTAL, DED_FUNDEB, uf=uf))
        rm = somar(dca, "M", "1.7.5.1.00.0.0", uf=uf)
        por_uf[uf] = {"estado_poe": cs, "estado_tira": rs, "prefeituras_poem": cm, "prefeituras_tiram": rm}
    return por_uf


def itr_receita_federal(ano: int) -> float | None:
    """ITR arrecadado no ano (R$ bi), da arrecadação por estado da Receita Federal que o mapa já baixa
    (data/raw/receita-federal/arrecadacao-estado.csv). O RTN não separa o ITR das outras receitas."""
    import csv
    try:
        texto = (c.RAIZ / "data" / "raw" / "receita-federal" / "arrecadacao-estado.csv").read_bytes().decode("latin-1")
    except OSError:
        return None
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    col = next((i for i, h in enumerate(linhas[0]) if "TERRITORIAL RURAL" in h.upper()), None)
    if col is None:
        return None
    total = 0.0
    for l in linhas[1:]:
        if l and l[0] == str(ano) and col < len(l) and l[col]:
            total += float(l[col].replace(".", "").replace(",", "."))
    return total / 1e9 or None


# ── RTN (União) ──────────────────────────────────────────────────────────────────────────────────

def ler_rtn_22(xlsx: bytes, ano: int) -> dict[str, float]:
    """Linhas da aba 2.2 do RTN no ano, em R$ bilhões, pelo rótulo normalizado (sem o número da linha)."""
    wb = openpyxl.load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    linhas = list(wb["2.2"].iter_rows(values_only=True))
    cab = next(l for l in linhas if cf._normal(l[0]) == "discriminacao")
    col = next(i for i, a in enumerate(cab) if str(a or "").strip() == str(ano))
    saida = {}
    for l in linhas:
        rot = cf._normal(l[0])
        if rot and isinstance(l[col], (int, float)):
            saida.setdefault(rot, l[col] / 1000)
    return saida


def rtn(linhas: dict[str, float], inicio: str) -> float:
    achados = [v for k, v in linhas.items() if k.startswith(inicio)]
    if not achados:
        raise ValueError(f"RTN, aba 2.2: linha '{inicio}' não encontrada")
    return achados[0]


# ── Montagem ─────────────────────────────────────────────────────────────────────────────────────

# Colunas do diagrama: 0 = o que se paga (o imposto), 1 = quem cobra, 2 = quem fica com o dinheiro no fim.
GOVERNOS = [("uniao", "União"), ("estados", "Estados e DF"), ("prefeituras", "Prefeituras")]


def montar(dca: dict, r: dict[str, float], ano: int) -> dict:
    E = lambda conta: somar(dca, "E", conta)
    M = lambda conta: somar(dca, "M", conta)
    EL = lambda conta: liquida(dca, "E", conta)
    ML = lambda conta: liquida(dca, "M", conta)

    # ── O que se paga, por quem cobra ──
    # União (RTN, aba 2.2). A contribuição dos servidores federais à previdência deles fica de fora, como a dos
    # servidores de estados e prefeituras: é o regime próprio, que não passa por repartição nenhuma.
    uniao = {
        "ir": rtn(r, "1.1.03 imposto sobre a renda"),
        "inss": rtn(r, "1.3 arrecadacao liquida para o rgps"),
        "cofins": rtn(r, "1.1.05 cofins") + rtn(r, "1.1.06 pis/pasep"),
        "csll": rtn(r, "1.1.07 csll"),
        "importacao": rtn(r, "1.1.01 imposto sobre a importacao"),
        "ipi": rtn(r, "1.1.02 ipi"),
        "iof": rtn(r, "1.1.04 iof"),
        "outros-federais": rtn(r, "1.1.09 cide") + rtn(r, "1.1.10 outras receitas administradas")
                           + rtn(r, "1.4.6 contribuicao do salario educacao"),
        "royalties": rtn(r, "1.4.4 receitas de exploracao de recursos naturais"),
    }
    # Estados e DF (DCA, sem as restituições). O DF cobra também ISS, IPTU e ITBI e entra aqui.
    estados = {
        "icms": EL("1.1.1.4.50.1.0") + EL("1.1.1.4.50.2.0"),   # com o adicional do fundo de combate à pobreza
        "ipva": EL("1.1.1.2.51.0.0"),
        "itcmd": EL("1.1.1.2.52.0.0"),
        "ir": EL("1.1.1.3.03.0.0"),                              # IR retido dos próprios servidores
        "iss": EL("1.1.1.4.51.1.0"),
        "iptu": EL("1.1.1.2.50.0.0") + EL("1.1.1.2.53.0.0"),     # IPTU e ITBI do DF
        "taxas": EL("1.1.2.0.00.0.0") + EL("1.2.4.0.00.0.0"),
    }
    prefeituras = {
        "iss": ML("1.1.1.4.51.1.0"),
        "iptu": ML("1.1.1.2.50.0.0"),
        "itbi": ML("1.1.1.2.53.0.0"),
        "ir": ML("1.1.1.3.03.0.0"),
        "taxas": ML("1.1.2.0.00.0.0") + ML("1.2.4.0.00.0.0"),  # com a contribuição de iluminação pública
    }
    cobra = {"uniao": uniao, "estados": estados, "prefeituras": prefeituras}

    # ── Repasses ──
    # União → estados e prefeituras: o valor que quem recebe declarou (DCA, bruto, antes da retenção do Fundeb),
    # menos nos royalties, que o governo do Rio de Janeiro não registra como repasse na DCA: ali vale o total que o
    # Tesouro mandou (RTN 2.4), tirando o que as prefeituras declararam.
    royalties_total = rtn(r, "2.4 transferencias de exploracao de recursos naturais")
    royalties_pref = M("1.7.1.2.00.0.0")
    fundeb = fundeb_liquido(dca)
    fundeb_e_para_m = sum(v["estado_poe"] - v["estado_tira"] for v in fundeb.values())
    obrig_ue = {
        "fpe": E("1.7.1.1.50.0.0"),
        "ipi-exportacao": E("1.7.1.1.53.0.0"),
        "royalties": royalties_total - royalties_pref,
        "salario-educacao": E("1.7.1.4.50.0.0"),
        "fundeb-uniao": E("1.7.1.5.00.0.0"),
        "outros-obrigatorios": E("1.7.1.1.54.0.0") + E("1.7.1.1.55.0.0") + E("1.7.1.9.58.0.0") + E("1.7.1.9.62.0.0"),
    }
    obrig_um = {
        "fpm": M("1.7.1.1.51.0.0"),
        "itr": M("1.7.1.1.52.0.0"),
        "royalties": royalties_pref,
        "salario-educacao": M("1.7.1.4.50.0.0"),
        "fundeb-uniao": M("1.7.1.5.00.0.0"),
        "outros-obrigatorios": M("1.7.1.1.54.0.0") + M("1.7.1.1.55.0.0") + M("1.7.1.9.58.0.0") + M("1.7.1.9.62.0.0"),
    }
    # Programas: tudo o mais que a União mandou (SUS, merenda, assistência social, convênios, emendas), que não é
    # divisão de imposto. É o total das contas 1.7.1 e 2.4.1 menos os repasses obrigatórios acima.
    prog_ue = E("1.7.1.0.00.0.0") + E("2.4.1.0.00.0.0") - sum(v for k, v in obrig_ue.items() if k != "royalties") - E("1.7.1.2.00.0.0")
    prog_um = M("1.7.1.0.00.0.0") + M("2.4.1.0.00.0.0") - sum(obrig_um.values())
    obrig_em = {
        "cota-icms": M("1.7.2.1.50.0.0"),
        "cota-ipva": M("1.7.2.1.51.0.0"),
        "cota-ipi": M("1.7.2.1.52.0.0") + M("1.7.2.1.53.0.0") + M("1.7.2.1.98.0.0") + M("1.7.2.2.00.0.0"),
        "fundeb": fundeb_e_para_m,
    }
    prog_em = M("1.7.2.0.00.0.0") + M("2.4.2.0.00.0.0") - (M("1.7.2.1.00.0.0") + M("1.7.2.2.00.0.0"))

    # O que há dentro dos programas, pelo que quem recebe declarou; "outros" fecha a conta com o total acima.
    def detalhar(total: float, partes: list[tuple[str, float]]) -> list[dict]:
        itens = [(n, v) for n, v in partes if v > 0.05]
        resto = total - sum(v for _, v in itens)
        if resto > 0.05:
            itens.append(("Outros (precatórios do antigo Fundef, segurança pública, cultura…)", resto))
        return [{"nome": n, "valor": round(v, 1)} for n, v in sorted(itens, key=lambda x: -x[1])]

    def da_uniao(X) -> list[tuple[str, float]]:
        return [
            ("Saúde (SUS)", X("1.7.1.3.00.0.0") + X("2.4.1.1.00.0.0") + X("1.7.1.7.50.0.0") + X("2.4.1.4.50.0.0")),
            ("Educação (merenda, transporte escolar, dinheiro direto na escola)",
             X("1.7.1.4.00.0.0") - X("1.7.1.4.50.0.0") + X("2.4.1.2.00.0.0")),
            ("Assistência social", X("1.7.1.6.00.0.0")),
            ("Emendas parlamentares sem destino definido (transferência especial)", X("1.7.1.9.57.0.0") + X("2.4.1.9.51.0.0")),
            ("Convênios", X("1.7.1.7.00.0.0") - X("1.7.1.7.50.0.0") + X("2.4.1.4.00.0.0") - X("2.4.1.4.50.0.0")),
        ]
    programas = {
        "c-uniao>f-estados": detalhar(prog_ue, da_uniao(E)),
        "c-uniao>f-prefeituras": detalhar(prog_um, da_uniao(M)),
        "c-estados>f-prefeituras": detalhar(prog_em, [
            ("Saúde (SUS)", M("1.7.2.3.00.0.0") + M("2.4.2.1.00.0.0")),
            ("Convênios", M("1.7.2.4.00.0.0") + M("2.4.2.2.00.0.0")),
        ]),
    }
    fundos = rtn(r, "2.2.1 repasse total")

    nomes_repasse = {
        "fpe": "Fundo de Participação dos Estados (FPE)", "fpm": "Fundo de Participação dos Municípios (FPM)",
        "ipi-exportacao": "IPI-exportação", "itr": "Metade do ITR", "royalties": "Royalties",
        "salario-educacao": "Salário-educação", "fundeb-uniao": "Fundeb: a parte da União",
        "outros-obrigatorios": "Outros repasses obrigatórios", "cota-icms": "Um quarto do ICMS",
        "cota-ipva": "Metade do IPVA", "cota-ipi": "Parte do IPI-exportação e dos royalties do estado",
        "fundeb": "Fundeb: o que o estado põe a mais", "programas": "Programas (SUS, escola, convênios, emendas)",
        "fundos": "Fundos regionais (FNE, FNO, FCO)",
    }
    fluxos: list[dict] = []

    def ligar(de: str, para: str, valor: float, tipo: str, chave: str, nome: str) -> None:
        if valor > 0.05:
            fluxos.append({"id": f"{de}>{para}:{chave}", "de": de, "para": para, "valor": round(valor, 1),
                           "tipo": tipo, "chave": chave, "nome": nome})

    nomes_imposto = {
        "ir": "Imposto de renda", "inss": "Contribuição ao INSS", "cofins": "Cofins e PIS", "csll": "CSLL",
        "importacao": "Imposto de importação", "ipi": "IPI", "iof": "IOF",
        "outros-federais": "Outros tributos federais", "royalties": "Royalties do petróleo e da mineração",
        "icms": "ICMS", "ipva": "IPVA", "itcmd": "Imposto sobre heranças e doações (ITCMD)",
        "iss": "ISS", "iptu": "IPTU", "itbi": "ITBI", "taxas": "Taxas e iluminação pública",
    }
    for gov, impostos in cobra.items():
        for imp, v in impostos.items():
            ligar(f"t-{imp}", f"c-{gov}", v, "imposto", imp, nomes_imposto[imp])
    for chave, v in obrig_ue.items():
        ligar("c-uniao", "f-estados", v, "obrigatorio", chave, nomes_repasse[chave])
    ligar("c-uniao", "f-estados", prog_ue, "programa", "programas", nomes_repasse["programas"])
    for chave, v in obrig_um.items():
        ligar("c-uniao", "f-prefeituras", v, "obrigatorio", chave, nomes_repasse[chave])
    ligar("c-uniao", "f-prefeituras", prog_um, "programa", "programas", nomes_repasse["programas"])
    ligar("c-uniao", "f-fundos", fundos, "obrigatorio", "fundos", nomes_repasse["fundos"])
    for chave, v in obrig_em.items():
        ligar("c-estados", "f-prefeituras", v, "obrigatorio", chave, nomes_repasse[chave])
    ligar("c-estados", "f-prefeituras", prog_em, "programa", "programas", nomes_repasse["programas"])

    # O que fica: o que cada governo cobrou menos o que mandou adiante.
    governos = {}
    for gov, _ in GOVERNOS:
        cobrou = sum(cobra[gov].values())
        repassa = sum(f["valor"] for f in fluxos if f["de"] == f"c-{gov}")
        recebe = sum(f["valor"] for f in fluxos if f["para"] == f"f-{gov}" and f["de"] != f"c-{gov}")
        ligar(f"c-{gov}", f"f-{gov}", cobrou - repassa, "fica", "fica", "Fica com quem cobrou")
        governos[gov] = {"cobra": round(cobrou, 1), "repassa": round(repassa, 1), "recebe": round(recebe, 1),
                         "fica": round(cobrou - repassa + recebe, 1)}

    nos = [{"id": f"t-{k}", "nome": v, "coluna": 0} for k, v in nomes_imposto.items()
           if any(f["de"] == f"t-{k}" for f in fluxos)]
    nos += [{"id": f"c-{g}", "nome": n, "coluna": 1, "esfera": g} for g, n in GOVERNOS]
    nos += [{"id": f"f-{g}", "nome": n, "coluna": 2, "esfera": g} for g, n in GOVERNOS]
    nos += [{"id": "f-fundos", "nome": "Fundos regionais", "coluna": 2, "esfera": "fundos"}]

    conferir(fluxos, governos)
    # O que há dentro dos nós que juntam vários tributos (para o painel dizer quais são).
    itr = itr_receita_federal(ano)
    outras_rfb = rtn(r, "1.1.10 outras receitas administradas")
    composicao = {
        "outros-federais": [x for x in [
            {"nome": "Salário-educação (das empresas, para a educação básica)", "valor": round(rtn(r, "1.4.6 contribuicao do salario educacao"), 1)},
            {"nome": "ITR (imposto das terras rurais)", "valor": round(itr, 1)} if itr else None,
            {"nome": "CIDE dos combustíveis", "valor": round(rtn(r, "1.1.09 cide"), 1)},
            {"nome": "Outras receitas da Receita Federal (taxas, contribuições menores, multas)", "valor": round(outras_rfb - (itr or 0), 1)},
        ] if x],
        "taxas": [
            {"nome": "Taxas dos estados e do DF (licenças, fiscalização, cartórios, Justiça)", "valor": round(EL("1.1.2.0.00.0.0"), 1)},
            {"nome": "Taxas das prefeituras (licenças, coleta de lixo)", "valor": round(ML("1.1.2.0.00.0.0"), 1)},
            {"nome": "Contribuição de iluminação pública (na conta de luz)", "valor": round(ML("1.2.4.0.00.0.0") + EL("1.2.4.0.00.0.0"), 1)},
        ],
        "cofins": [{"nome": "Cofins", "valor": round(rtn(r, "1.1.05 cofins"), 1)}, {"nome": "PIS/Pasep", "valor": round(rtn(r, "1.1.06 pis/pasep"), 1)}],
        "ir": [{"nome": "Pessoas físicas (declaração anual)", "valor": round(rtn(r, "1.1.03.1 i.r. pessoa fisica"), 1)},
               {"nome": "Empresas", "valor": round(rtn(r, "1.1.03.2 i.r. pessoa juridica"), 1)},
               {"nome": "Descontado na fonte (salários, aplicações, remessas)", "valor": round(rtn(r, "1.1.03.3 i.r. retido na fonte"), 1)},
               {"nome": "Descontado dos servidores dos estados (fica com eles)", "valor": round(EL("1.1.1.3.03.0.0"), 1)},
               {"nome": "Descontado dos servidores das prefeituras (fica com elas)", "valor": round(ML("1.1.1.3.03.0.0"), 1)}],
        "iptu": [{"nome": "IPTU das prefeituras", "valor": round(ML("1.1.1.2.50.0.0"), 1)},
                 {"nome": "IPTU e ITBI do Distrito Federal", "valor": round(EL("1.1.1.2.50.0.0") + EL("1.1.1.2.53.0.0"), 1)}],
    }
    return {"nos": nos, "fluxos": fluxos, "governos": governos, "programas": programas, "composicao": composicao,
            "fundeb": {"por_uf": {uf: {k: round(x, 2) for k, x in v.items()} for uf, v in fundeb.items()},
                       "estados_poem": round(sum(v["estado_poe"] for v in fundeb.values()), 1),
                       "estados_tiram": round(sum(v["estado_tira"] for v in fundeb.values()), 1),
                       "prefeituras_poem": round(sum(v["prefeituras_poem"] for v in fundeb.values()), 1),
                       "prefeituras_tiram": round(sum(v["prefeituras_tiram"] for v in fundeb.values()), 1),
                       # De onde vem o que os estados põem no fundo (a dedução de 20% de cada conta), R$ bi.
                       "deducao_estados": {k: round(abs(somar(dca, "E", conta, DED_FUNDEB)), 1) for k, conta in [
                           ("icms", "1.1.1.4.50.0.0"), ("ipva", "1.1.1.2.51.0.0"), ("itcmd", "1.1.1.2.52.0.0"),
                           ("fpe", "1.7.1.1.50.0.0"), ("ipi", "1.7.1.1.53.0.0")]}}}


def conferir(fluxos: list[dict], governos: dict) -> None:
    """As pontas fecham: em cada nó do meio, o que entra é o que sai; e o que se pagou é o que todos ficam."""
    entra, sai = defaultdict(float), defaultdict(float)
    for f in fluxos:
        sai[f["de"]] += f["valor"]
        entra[f["para"]] += f["valor"]
    for g, _ in GOVERNOS:
        no = f"c-{g}"
        if abs(entra[no] - sai[no]) > 0.5:
            raise ValueError(f"{no}: entra {entra[no]:.1f}, sai {sai[no]:.1f}")
    pago = sum(v for k, v in sai.items() if k.startswith("t-"))
    fica = sum(v for k, v in entra.items() if k.startswith("f-"))
    if abs(pago - fica) > 0.5:
        raise ValueError(f"pago {pago:.1f} ≠ fica {fica:.1f}")


# ── O que deixa de entrar ────────────────────────────────────────────────────────────────────────

# Receita Federal, Demonstrativo dos Gastos Tributários, "bases efetivas" de 2023 com a série 2021 a 2026 (publicado em
# agosto de 2026): é a estimativa mais nova para 2025 (o efetivo vai até 2023; 2024 a 2026 são projeção). O do PLOA
# 2025 dava R$ 544 bi; este, R$ 569 bi. Quadro XXVI: por tributo e por benefício, R$ 1,00.
URL_DGT = ("https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/renuncia/"
           "gastos-tributarios-bases-efetivas/dgt-bases-efetivas-2023-serie-2021-a-2026-quadros.xlsx")
PAGINA_DGT = ("https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/renuncia/"
              "gastos-tributarios-bases-efetivas")
PASTA_DGT = c.RAIZ / "data" / "raw" / "receita-federal" / "dgt"
# Tributo do quadro → imposto do diagrama.
TRIBUTO_DGT = [("Imposto sobre Importação", "importacao"), ("Imposto sobre a Renda", "ir"),
               ("Imposto sobre Produtos Industrializados", "ipi"), ("Imposto sobre Operações Financeiras", "iof"),
               ("Contribuição Social para o PIS", "cofins"), ("Contribuição Social sobre o Lucro", "csll"),
               ("Contribuição para o Financiamento da Seguridade", "cofins"), ("Contribuição para a Previdência", "inss"),
               ("Contribuição de Intervenção", "outros-federais"), ("Adicional ao Frete", "outros-federais"),
               ("Contribuição para o Desenvolvimento da Indústria", "outros-federais"),
               ("Imposto sobre Propriedade Territorial", "outros-federais")]
# Nomes do quadro → nome simples (os outros ficam como estão).
NOMES_DGT = {"Simples Nacional": "Simples Nacional (impostos menores para pequenas empresas)",
             "Entidades sem Fins Lucrativos - Imunes / Isentas": "Entidades sem fins lucrativos",
             "Despesas Médicas": "Deduções de despesas médicas no imposto de renda",
             "Desoneração da Folha de Salários": "Desoneração da folha de salários",
             "Entidades Filantrópicas": "Entidades filantrópicas (previdência)",
             "Microempreendedor Individual - MEI": "Microempreendedor individual (MEI)",
             "Agricultura e Agroindústria - Desoneração Cesta Básica": "Cesta básica",
             "Aposentadoria por Moléstia Grave ou Acidente": "Aposentadoria de quem tem doença grave (sem imposto de renda)",
             "Exportação da Produção Rural": "Exportação da produção rural",
             "Aposentadoria de Declarante com 65 Anos ou Mais": "Parte isenta da aposentadoria depois dos 65 anos",
             "Assistência Médica, Odontológica e Farmacêutica a Empregados": "Plano de saúde que a empresa paga ao empregado"}

# Estados: Tesouro Nacional, Boletim de Finanças dos Entes Subnacionais 2025 (fevereiro de 2026), com os dados que os
# estados informam no Programa de Acompanhamento Fiscal. A renúncia de ICMS projetada pelos próprios estados para
# 2025 (planilha de tabelas, aba "Gráfico 12": R$ 183,06 bi por tempo determinado e R$ 75,20 bi por tempo
# indeterminado), sem o Paraná e o Maranhão. Em 2024 foram R$ 258,9 bi, 22,8% do ICMS. Não há valores por estado.
ICMS_RENUNCIA = {"total": 258.3, "ano_referencia": 2025, "sem": ["PR", "MA"], "em_2024": 258.9,
                 "fonte": "Tesouro Nacional, Boletim de Finanças dos Entes Subnacionais 2025 (projeção dos estados)",
                 "url": "https://www.tesourotransparente.gov.br/publicacoes/boletim-de-financas-dos-entes-subnacionais"}
# A série do mesmo gráfico 12 (tempo determinado + indeterminado, R$ bi): 2023 e 2024 informados, 2025 e 2026 projetados.
ICMS_SERIE = [{"ano": 2023, "valor": 218.1, "efetivo": True}, {"ano": 2024, "valor": 259.0, "efetivo": True},
              {"ano": 2025, "valor": 258.3, "efetivo": False}, {"ano": 2026, "valor": 283.2, "efetivo": False}]


def gastos_tributarios(ano: int) -> dict:
    """Benefícios fiscais da União no ano (total, por imposto do diagrama e os maiores) e a renúncia de ICMS."""
    arq = PASTA_DGT / URL_DGT.rsplit("/", 1)[-1]
    if not arq.exists():
        print(f"  baixando {arq.name}", flush=True)
        PASTA_DGT.mkdir(parents=True, exist_ok=True)
        arq.write_bytes(cf._get(URL_DGT, timeout=300))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(arq, read_only=True, data_only=True)
    linhas = list(wb["Q XXVI"].iter_rows(values_only=True))
    cab = next(l for l in linhas if any(str(x).strip() == str(ano) for x in l if x is not None))
    col = next(i for i, x in enumerate(cab) if str(x).strip() == str(ano))
    por_tributo: dict[str, float] = defaultdict(float)
    itens: dict[str, float] = defaultdict(float)
    itens_por: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    atual = ""
    total = None
    tributo = None
    for l in linhas[linhas.index(cab) + 1:]:
        nome = str(l[0] or "").strip()
        v = l[col] if isinstance(l[col], (int, float)) else None
        if not nome or v is None:
            continue
        if nome == "TOTAL":
            total = v / 1e9
            break
        achado = next((k for pref, k in TRIBUTO_DGT if nome.startswith(pref)), None)
        if achado and tributo != nome:
            tributo = nome
            por_tributo[achado] += v / 1e9
            atual = achado
        else:
            itens[nome] += v / 1e9
            if tributo:
                itens_por[atual][nome] += v / 1e9
    if total is None or abs(sum(por_tributo.values()) - total) > 0.01 * total:
        raise ValueError(f"DGT {ano}: os tributos ({sum(por_tributo.values()):.1f}) não somam o total ({total})")
    maiores = sorted(itens.items(), key=lambda x: -x[1])[:10]
    # A série do quadro: o total e o total em % do PIB de cada ano; a linha de cima diz o que é efetivo e o que é projeção.
    anos_col = {int(str(x).strip()): i for i, x in enumerate(cab) if re.fullmatch(r"\d{4}", str(x or "").strip())}
    acima = linhas[linhas.index(cab) - 1]
    marca, efetivo_col = None, {}
    for i, x in enumerate(acima):
        if x:
            marca = str(x).strip().upper()
        efetivo_col[i] = marca == "EFETIVO"
    linha_total = next(l for l in linhas if str(l[0] or "").strip() == "TOTAL")
    linha_pib = next((l for l in linhas if str(l[0] or "").strip().upper().replace(" ", "") == "GT/PIB"), None)
    serie = [{"ano": a, "valor": round(linha_total[i] / 1e9, 1), "efetivo": efetivo_col.get(i, False),
              "pib": round(linha_pib[i] * 100, 2) if linha_pib and isinstance(linha_pib[i], (int, float)) else None}
             for a, i in sorted(anos_col.items()) if isinstance(linha_total[i], (int, float))]
    maiores_por = {k: [{"nome": NOMES_DGT.get(n, n), "valor": round(v, 1)} for n, v in sorted(d.items(), key=lambda x: -x[1])[:5] if v >= 0.5]
                   for k, d in itens_por.items()}
    return {
        "uniao": {"total": round(total, 1), "ano": ano, "estimativa": "projeção das bases efetivas de 2023",
                  "fonte": "Receita Federal, Demonstrativo dos Gastos Tributários (bases efetivas 2023, série 2021 a 2026)",
                  "url": URL_DGT, "pagina": PAGINA_DGT,
                  "por_imposto": {k: round(v, 1) for k, v in sorted(por_tributo.items(), key=lambda x: -x[1])},
                  "itens": [{"nome": NOMES_DGT.get(n, n), "valor": round(v, 1)} for n, v in maiores],
                  "itens_por_imposto": maiores_por, "serie": serie},
        "estados": {**ICMS_RENUNCIA, "serie": ICMS_SERIE},
    }


def conferencia(dca: dict, r: dict[str, float], doc: dict) -> list[dict]:
    """Cada repasse contado pelos dois lados: o que quem manda diz ter mandado e o que quem recebe declarou."""
    def fluxo(de: str, para: str, chave: str) -> float:
        return sum(f["valor"] for f in doc["fluxos"] if f["de"] == de and f["para"] == para and f["chave"] == chave)

    def sem_df(conta: str, parte: float) -> float:
        d = dca["53"]
        df = (d.get((conta, BRUTA), 0.0) - abs(d.get((conta, DED_OUTRAS), 0.0))) / 1e9
        return parte * (liquida(dca, "E", conta) - df)

    fpm_fpe = sum(fluxo("c-uniao", p, k) for p, k in
                  [("f-estados", "fpe"), ("f-prefeituras", "fpm"), ("f-estados", "ipi-exportacao")])
    fundeb = doc["fundeb"]
    linhas = [
        ("FPE, FPM e IPI-exportação", "Tesouro (RTN 2.1)", rtn(r, "2.1 fpm / fpe / ipi ee"), fpm_fpe),
        ("Salário-educação", "Tesouro (RTN 2.3)", rtn(r, "2.3 transferencia de contribuicao do salario educacao"),
         fluxo("c-uniao", "f-estados", "salario-educacao") + fluxo("c-uniao", "f-prefeituras", "salario-educacao")),
        ("Fundeb: a parte da União", "Tesouro (RTN 4.3.10)", rtn(r, "4.3.10 fundeb"),
         fluxo("c-uniao", "f-estados", "fundeb-uniao") + fluxo("c-uniao", "f-prefeituras", "fundeb-uniao")),
        ("Royalties", "Tesouro (RTN 2.4)", rtn(r, "2.4 transferencias de exploracao de recursos naturais"),
         somar(dca, "E", "1.7.1.2.00.0.0") + somar(dca, "M", "1.7.1.2.00.0.0")),
        # O Rio de Janeiro lança os royalties dele em "demais receitas patrimoniais" (1.3.9), não como repasse.
        ("Royalties, com o que o Rio lança como receita própria", "Tesouro (RTN 2.4)",
         rtn(r, "2.4 transferencias de exploracao de recursos naturais"),
         somar(dca, "E", "1.7.1.2.00.0.0") + somar(dca, "M", "1.7.1.2.00.0.0") + dca["33"].get(("1.3.9.0.00.0.0", BRUTA), 0.0) / 1e9),
        ("Um quarto do ICMS", "25% do ICMS dos estados (sem o DF)", sem_df("1.1.1.4.50.1.0", 0.25),
         fluxo("c-estados", "f-prefeituras", "cota-icms")),
        ("Metade do IPVA", "50% do IPVA dos estados (sem o DF)", sem_df("1.1.1.2.51.0.0", 0.5),
         fluxo("c-estados", "f-prefeituras", "cota-ipva")),
        ("Fundeb: o que entra e o que sai do fundo", "estados e prefeituras põem",
         fundeb["estados_poem"] + fundeb["prefeituras_poem"], fundeb["estados_tiram"] + fundeb["prefeituras_tiram"]),
    ]
    return [{"nome": n, "lado_manda": quem, "manda": round(a, 1), "recebe": round(b, 1)} for n, quem, a, b in linhas]


def populacao(ano: int) -> float | None:
    """Moradores do país no ano (milhões), da cópia de referência do comando populacao, se existir."""
    try:
        doc = json.loads((c.RAIZ / "pipeline" / "referencia" / "populacao.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    do_ano = doc.get("anos", {}).get(str(ano)) or {}
    total = sum(v for k, v in do_ano.items() if len(k) == 2)   # os 26 estados e o DF
    return round(total / 1e6, 1) if total else None


def resumo(doc: dict) -> str:
    g = doc["governos"]
    pago = sum(f["valor"] for f in doc["fluxos"] if f["tipo"] == "imposto")
    linhas = [f"{doc['ano']}: R$ {pago:,.0f} bi pagos"]
    for k, n in GOVERNOS:
        linhas.append(f"  {n:13} cobra {g[k]['cobra']:7.1f}  repassa {g[k]['repassa']:6.1f}  recebe {g[k]['recebe']:6.1f}"
                      f"  fica {g[k]['fica']:7.1f}  ({g[k]['cobra'] / pago:.0%} → {g[k]['fica'] / pago:.0%})")
    for c_ in doc["conferencia"]:
        dif = (c_["recebe"] - c_["manda"]) / c_["manda"] if c_["manda"] else 0
        linhas.append(f"  confere {c_['nome']:42} {c_['manda']:7.1f} x {c_['recebe']:7.1f}  ({dif:+.1%})")
    return "\n".join(linhas)


def copiar_referencia() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REFERENCIA, SAIDA)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia de {REFERENCIA.relative_to(c.RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ano", type=int, default=ANO)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return
    try:
        xlsx, url, nome = cf.baixar_rtn()
        r = ler_rtn_22(xlsx, args.ano)
        dca = ler_dca(args.ano)
    except (OSError, ValueError, KeyError, StopIteration) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: faltou uma fonte ({erro}); usando a cópia versionada", flush=True)
            copiar_referencia()
            return
        raise
    doc = {"ano": args.ano, "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "fonte": {"rtn": {"url": url, "arquivo": nome, "pagina": cf.PAGINA_RTN},
                     "dca": "SICONFI, Declaração de Contas Anuais, Anexo I-C (receitas orçamentárias)",
                     "faltam": ler_dca.faltam},  # type: ignore[attr-defined]
           "populacao": populacao(args.ano), **montar(dca, r, args.ano)}
    doc["conferencia"] = conferencia(dca, r, doc)
    doc["deixa"] = gastos_tributarios(args.ano)
    print(resumo(doc), flush=True)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
