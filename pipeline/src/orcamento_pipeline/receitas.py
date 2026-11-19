"""Leitura das receitas da DCA (Anexo I-C): total líquido, origem e tributos próprios.

A classificação das receitas mudou duas vezes no período:

- 2013-2017: códigos x.x.x.x.xx.xx.xx; transferências em 1.7.2.x (União .1, estados .2,
  multigovernamentais/FUNDEB .4) e convênios em 1.7.6.x e 2.4.7.x; total "Total Receitas",
  que inclui as intraorçamentárias (categorias 7 e 8).
- 2018-2021: códigos x.x.x.x.xx.x.x; União em 1.7.1.0 e 2.4.1.0, estados em 1.7.2.0 e
  2.4.2.0, FUNDEB em 1.7.5.0.
- 2022 em diante: mesmos códigos de topo, com outro detalhamento abaixo deles; desde 2020
  o total vem como "RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)".

Os tributos (IPTU, ISS…) e as cotas de ICMS e IPVA são achados pelo nome da conta,
porque os códigos deles mudam a cada era.
"""

from __future__ import annotations

from .cidades import _so_letras

# Ordem dos valores devolvidos por `receita` (e gravados nos arquivos do mapa).
CAMPOS = ["receita", "propria", "uniao", "estado", "fundeb", "credito",
          "iptu", "iss", "itbi", "irrf", "taxas", "cosip", "outros_tributos", "cota_icms", "cota_ipva"]

TOTAL_SEM_INTRA = _so_letras("RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)")


def receita(itens: list[dict]) -> list[float] | None:
    """Valores de `CAMPOS` para um ente num ano, ou None se não houver total de receita.

    Receita e origem são líquidas (brutas menos deduções) e sem intraorçamentárias.
    Tributos e cotas são brutos. `propria` é o que sobra depois de União, estado, FUNDEB
    e empréstimos.
    """
    liq: dict[str, float] = {}
    bruta: dict[str, float] = {}  # nome da conta (só letras) -> maior valor bruto com esse nome
    antigo = False
    for i in itens:
        conta = " ".join((i["conta"] or "").split())
        v = float(i["valor"] or 0)
        realizada = "Realizadas" in i["coluna"]
        if conta[:1].isdigit():
            chave = conta.split(" ")[0]
            antigo = antigo or (chave.count(".") == 6 and len(chave.split(".")[-1]) == 2)
            if realizada and not chave.startswith(("7.", "8.")):
                nome = _so_letras(conta[len(chave):])
                bruta[nome] = max(bruta.get(nome, 0.0), v)
                if chave.startswith("1.1.0.0.00"):
                    bruta["_tributaria"] = v
        else:
            chave = _so_letras(conta)
        # Deduções vêm positivas no FINBRA e nos anos recentes da API, e negativas nos anos
        # antigos da API: subtrai sempre o valor absoluto.
        liq[chave] = liq.get(chave, 0.0) + (v if realizada else -abs(v))

    def soma(*codigos: str) -> float:
        return sum(liq.get(k, 0.0) for k in codigos)

    total = liq.get(TOTAL_SEM_INTRA)
    if total is None:
        total = liq.get("totalreceitas")
        if total is not None:
            zeros = "00.00.00" if antigo else "00.0.0"
            total -= soma(f"7.0.0.0.{zeros}", f"8.0.0.0.{zeros}")
    if not total or total <= 0:
        return None

    if antigo:
        uniao = soma("1.7.2.1.00.00.00", "1.7.6.1.00.00.00", "2.4.2.1.00.00.00", "2.4.7.1.00.00.00")
        estado = soma("1.7.2.2.00.00.00", "1.7.6.2.00.00.00", "2.4.2.2.00.00.00", "2.4.7.2.00.00.00")
        fundeb = soma("1.7.2.4.00.00.00")
        credito = soma("2.1.0.0.00.00.00")
    else:
        uniao = soma("1.7.1.0.00.0.0", "2.4.1.0.00.0.0")
        estado = soma("1.7.2.0.00.0.0", "2.4.2.0.00.0.0")
        fundeb = soma("1.7.5.0.00.0.0")
        credito = soma("2.1.0.0.00.0.0")

    def nomeado(*nomes: str, exato: bool = False) -> float:
        return max((v for n, v in bruta.items() if (n in nomes if exato else n.startswith(nomes))), default=0.0)

    iptu = nomeado("impostosobreapropriedadepredial")
    iss = nomeado("impostosobreservicosdequalquernatureza")
    itbi = max((v for n, v in bruta.items()
                if n.startswith(("impostosobretransmissao", "impostossobretransmissao")) and "intervivos" in n), default=0.0)
    irrf = nomeado("impostosobrearendaretidonafonte", "impostoderendaretidonasfontes",
                   "impostosobrearendaeproventosdequalquernatureza")
    taxas = nomeado("taxas", exato=True)
    cosip = nomeado("contribuicaoparaocusteiodoservicodeiluminacao", "contribuicaoparacusteiodoservicodeiluminacao")
    outros = max(0.0, bruta.get("_tributaria", 0.0) - iptu - iss - itbi - irrf - taxas)
    cota_icms = nomeado("cotapartedoicms", exato=True)
    cota_ipva = nomeado("cotapartedoipva", exato=True)
    return [total, total - uniao - estado - fundeb - credito, uniao, estado, fundeb, credito,
            iptu, iss, itbi, irrf, taxas, cosip, outros, cota_icms, cota_ipva]
