"""O ano em andamento: receita e despesa acumuladas até o último bimestre fechado.

    uv run rreo                                  # estados
    uv run rreo --municipios                     # também os municípios (uma consulta por município: ~1h40)
    uv run rreo --municipios --ano-anterior      # e o mesmo bimestre do ano anterior deles (outro tanto)

A prestação de contas anual (DCA) só chega no ano seguinte. Durante o ano, estados e
municípios entregam a cada dois meses o Relatório Resumido de Execução Orçamentária
(RREO). O Anexo 01 traz a receita prevista e a arrecadada, o orçamento (dotação) e a
despesa empenhada, liquidada e paga, acumuladas desde janeiro.

O bimestre de referência é o último cujo prazo de entrega (30 dias depois do fim do
bimestre) já passou, o mesmo para todos os entes, para os números serem comparáveis.
Quem não entregou esse bimestre fica de fora. O mesmo bimestre do ano anterior também
é baixado, para comparar o ritmo (nos municípios, só com `--ano-anterior`).

Municípios com menos de 50 mil habitantes costumam entregar o "RREO Simplificado", com as
mesmas contas: a consulta começa pelo tipo mais provável para o porte e tenta o outro se
vier vazio.

Cache em data/raw/siconfi/rreo-a01/{ano}-b{bimestre}.json.gz (ver cidades.CacheAno).

Saídas em site/public/data/mapa/:
- parcial.json        receita e despesa frente ao previsto, para as páginas de estado e cidade
- andamento.json      qual é o ano em andamento e até que mês vão os números
- anos/{ano}.json, contas/{ano}.json, areas/{ano}.json
                      o mesmo ano nos formatos da página /mapa (ver mapa.py), marcado como parcial.
                      O registro para no item "crédito": o relatório não detalha tributos nem áreas.
                      Se o ano já tem a prestação de contas anual, esses arquivos não são tocados.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from . import cidades as c

ANEXO = "RREO-Anexo 01"
PASTA = "rreo-a01"
PASTA_SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa"
SAIDA = PASTA_SAIDA / "parcial.json"
MESES = ["fevereiro", "abril", "junho", "agosto", "outubro", "dezembro"]
PRAZO_DIAS = 30
LIMITE_SIMPLIFICADO = 50_000  # habitantes

# (identificador da conta, coluna) -> campo. Valores acumulados no ano, sem intraorçamentárias.
RECEITA, DESPESA = "ReceitasExcetoIntraOrcamentarias", "DespesasExcetoIntraOrcamentarias"
VALORES = {
    (RECEITA, "PREVISÃO ATUALIZADA (a)"): "receita_prevista",
    (RECEITA, "Até o Bimestre (c)"): "receita",
    (DESPESA, "DOTAÇÃO ATUALIZADA (e)"): "dotacao",
    (DESPESA, "DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)"): "empenhado",
    (DESPESA, "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)"): "liquidado",
    (DESPESA, "DESPESAS PAGAS ATÉ O BIMESTRE (j)"): "pago",
}
REALIZADO, EMPENHADO, PAGO = "Até o Bimestre (c)", "DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)", "DESPESAS PAGAS ATÉ O BIMESTRE (j)"
# De onde veio a receita (contas do Anexo 01 somadas em cada item do registro do mapa).
ORIGENS = {
    "uniao": ("TransferenciasCorrentesDaUniaoEDeSuasEntidades", "TransferenciasDeCapitalDaUniaoEDeSuasEntidades"),
    "estado": ("TransferenciasCorrentesDosEstadosEDoDistritoFederalEDeSuasEntidades",
               "TransferenciasDeCapitalDosEstadosEDoDistritoFederalEDeSuasEntidades"),
    "fundeb": ("TransferenciasCorrentesDeOutrasInstituicoesPublicas",),  # na prática, o FUNDEB
    "credito": ("ReceitasDeOperacoesDeCredito",),
}
# Despesa por natureza, na ordem de contas.NATUREZA (os restos a pagar só existem no fim do ano).
GRUPOS = ("PessoalEEncargosSociais", "JurosEEncargosDaDivida", "OutrasDespesasCorrentes", "Investimentos",
          "InversoesFinanceiras", "AmortizacaoDaDivida")
# Ordem dos valores de cada ente no arquivo de saída.
CAMPOS = ["pop", *VALORES.values(), "receita_ano_anterior", "empenhado_ano_anterior"]
COLUNAS = {col for _, col in VALORES}
CAMPOS_CACHE = ("cod_conta", "coluna", "valor", "populacao")


def filtro(itens: list[dict]) -> list[dict]:
    """Só as colunas acumuladas: o relatório tem também o bimestre isolado, saldos e percentuais."""
    return [{k: i.get(k) for k in CAMPOS_CACHE} for i in itens if i.get("coluna") in COLUNAS]


def bimestre_de_referencia(hoje: date) -> tuple[int, int]:
    """(ano, bimestre) do último RREO cujo prazo de entrega já passou."""
    ano, bim = hoje.year, 6
    while True:
        fim = date(ano + (bim == 6), 1 if bim == 6 else 2 * bim + 1, 1) - timedelta(days=1)
        if fim + timedelta(days=PRAZO_DIAS) < hoje:
            return ano, bim
        ano, bim = (ano - 1, 6) if bim == 1 else (ano, bim - 1)


def tipos_para(esfera: str, populacao: int) -> tuple[str, ...]:
    """Tipos de demonstrativo a tentar, do mais provável para o menos."""
    if esfera != "mun":
        return ("RREO",)
    return ("RREO Simplificado", "RREO") if populacao < LIMITE_SIMPLIFICADO else ("RREO", "RREO Simplificado")


def baixar(cache: c.CacheAno, ano: int, bimestre: int, ibge: int, tipos: tuple[str, ...] = ("RREO",)) -> list[dict] | None:
    """Linhas do Anexo 01 de um ente. None se a chamada falhar ou o limite de consultas acabar."""
    itens = cache.obter(ibge)
    if itens:
        return itens
    for tipo in tipos:
        if not c.CHAMADAS.gastar():
            return None
        try:
            d = c._get("rreo", {"an_exercicio": ano, "nr_periodo": bimestre, "co_tipo_demonstrativo": tipo,
                                "no_anexo": ANEXO, "id_ente": ibge})
        except Exception:
            return None
        itens = d["items"]
        if itens:
            break
    cache.guardar(ibge, itens)
    return itens


def resumir(itens: list[dict] | None) -> dict | None:
    """{campo: valor} de um ente, ou None se o relatório não traz receita nem despesa."""
    v: dict[str, float] = {}
    for i in itens or []:
        campo = VALORES.get((i.get("cod_conta"), i.get("coluna")))
        if campo:
            v[campo] = float(i["valor"] or 0)
            v["pop"] = i.get("populacao") or v.get("pop", 0)
    return v if v.get("receita") and v.get("empenhado") else None


def para_o_mapa(itens: list[dict] | None) -> tuple[list[int], list[int], list[int]] | None:
    """(registro, despesa por natureza, [receita prevista, dotação]) de um ente, nos formatos do mapa.

    O registro segue mapa.py até "crédito": população, despesa, três áreas (zeradas: o Anexo 01
    não tem o gasto por área), pago, receita, própria, União, estado, FUNDEB e empréstimos.
    """
    r = resumir(itens)
    if not r:
        return None
    v = {(i["cod_conta"], i["coluna"]): float(i["valor"] or 0) for i in itens or []}
    origem = {k: sum(v.get((conta, REALIZADO), 0.0) for conta in contas) for k, contas in ORIGENS.items()}
    registro = [r.get("pop", 0), r["empenhado"], 0, 0, 0, r.get("pago", 0), r["receita"], r["receita"] - sum(origem.values()),
                origem["uniao"], origem["estado"], origem["fundeb"], origem["credito"]]
    natureza = [v.get((g, EMPENHADO), 0.0) for g in GRUPOS] + [0, 0]
    return [round(x) for x in registro], [round(x) for x in natureza], [round(r.get("receita_prevista", 0)), round(r.get("dotacao", 0))]


def gravar_para_o_mapa(meta: dict, entes: dict[str, dict[str, list[dict] | None]]) -> bool:
    """Grava o ano em andamento nos formatos do mapa. Falso se o ano já tem a prestação anual."""
    ano = meta["ano"]
    arq_ano, arq_meta = PASTA_SAIDA / "anos" / f"{ano}.json", PASTA_SAIDA / "andamento.json"
    if arq_ano.exists() and "parcial" not in json.loads(arq_ano.read_text()):
        arq_meta.unlink(missing_ok=True)  # o ano fechou: o mapa passa a usar a prestação anual
        return False
    doc: dict = {"parcial": meta, "mun": {}, "uf": {}}
    contas: dict = {}
    for esfera, por_ente in entes.items():
        for ibge, itens in por_ente.items():
            m = para_o_mapa(itens)
            if m:
                doc[esfera][ibge], contas[ibge] = m[0], {"n": m[1], "p": m[2]}
    for pasta, conteudo in (("anos", doc), ("contas", contas), ("areas", {"mun": {}, "uf": {}})):
        (PASTA_SAIDA / pasta).mkdir(parents=True, exist_ok=True)
        (PASTA_SAIDA / pasta / f"{ano}.json").write_text(json.dumps(conteudo, separators=(",", ":")))
    arq_meta.write_text(json.dumps(meta))
    return True


def main() -> None:
    p = argparse.ArgumentParser(prog="rreo", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--municipios", action="store_true", help="consulta também os municípios que faltam no cache")
    p.add_argument("--ano-anterior", action="store_true", help="com --municipios: consulta também o mesmo bimestre do ano anterior")
    p.add_argument("--bimestre", help="AAAA-N (padrão: o último com prazo de entrega vencido)")
    p.add_argument("--max-chamadas", type=int, default=None, help="limite de consultas à API nesta execução")
    args = p.parse_args()
    c.CHAMADAS.restantes = args.max_chamadas
    ano, bim = map(int, args.bimestre.split("-")) if args.bimestre else bimestre_de_referencia(date.today())

    entes = c.baixar_entes()
    grupos = {"uf": [e for e in entes if e["esfera"] in ("E", "D")], "mun": [e for e in entes if e["esfera"] == "M"]}
    atual = c.CacheAno(f"{ano}-b{bim}", anexo=PASTA, filtro=filtro)
    anterior = c.CacheAno(f"{ano - 1}-b{bim}", anexo=PASTA, filtro=filtro)

    meta = {"ano": ano, "bimestre": bim, "ate": MESES[bim - 1], "meses": 2 * bim}
    doc: dict = {**meta, "campos": CAMPOS, "uf": {}, "mun": {}}
    brutos: dict = {"uf": {}, "mun": {}}
    for esfera, lista in grupos.items():
        consultar = esfera == "uf" or args.municipios
        consultar_anterior = esfera == "uf" or (args.municipios and args.ano_anterior)
        for n, e in enumerate(lista, 1):
            ibge, tipos = e["cod_ibge"], tipos_para(esfera, e.get("populacao") or 0)
            itens = baixar(atual, ano, bim, ibge, tipos) if consultar else atual.obter(ibge)
            r = resumir(itens)
            if consultar and n % 500 == 0:
                print(f"  {esfera}: {n}/{len(lista)}", flush=True)
            if not r:
                continue
            antes = resumir(baixar(anterior, ano - 1, bim, ibge, tipos) if consultar_anterior else anterior.obter(ibge)) or {}
            r["receita_ano_anterior"], r["empenhado_ano_anterior"] = antes.get("receita", 0), antes.get("empenhado", 0)
            doc[esfera][str(ibge)] = [round(r.get(k, 0)) for k in CAMPOS]
            brutos[esfera][str(ibge)] = itens
        atual.salvar()
        anterior.salvar()

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(doc, separators=(",", ":")))
    no_mapa = gravar_para_o_mapa(meta, brutos)
    print(f"{ano}, até {doc['ate']}: {len(doc['uf'])} estados e {len(doc['mun'])} municípios com o relatório entregue"
          + ("" if no_mapa else "; o mapa já tem a prestação anual desse ano"))


if __name__ == "__main__":
    main()
