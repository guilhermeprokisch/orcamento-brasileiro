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
Saída: site/public/data/mapa/parcial.json.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from . import cidades as c

ANEXO = "RREO-Anexo 01"
PASTA = "rreo-a01"
SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa" / "parcial.json"
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

    doc: dict = {"ano": ano, "bimestre": bim, "ate": MESES[bim - 1], "meses": 2 * bim, "campos": CAMPOS, "uf": {}, "mun": {}}
    for esfera, lista in grupos.items():
        consultar = esfera == "uf" or args.municipios
        consultar_anterior = esfera == "uf" or (args.municipios and args.ano_anterior)
        for n, e in enumerate(lista, 1):
            ibge, tipos = e["cod_ibge"], tipos_para(esfera, e.get("populacao") or 0)
            r = resumir(baixar(atual, ano, bim, ibge, tipos) if consultar else atual.obter(ibge))
            if consultar and n % 500 == 0:
                print(f"  {esfera}: {n}/{len(lista)}", flush=True)
            if not r:
                continue
            antes = resumir(baixar(anterior, ano - 1, bim, ibge, tipos) if consultar_anterior else anterior.obter(ibge)) or {}
            r["receita_ano_anterior"], r["empenhado_ano_anterior"] = antes.get("receita", 0), antes.get("empenhado", 0)
            doc[esfera][str(ibge)] = [round(r.get(k, 0)) for k in CAMPOS]
        atual.salvar()
        anterior.salvar()

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"{ano}, até {doc['ate']}: {len(doc['uf'])} estados e {len(doc['mun'])} municípios com o relatório entregue")


if __name__ == "__main__":
    main()
