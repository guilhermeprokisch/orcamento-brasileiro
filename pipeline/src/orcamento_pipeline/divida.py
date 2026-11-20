"""Dívida dos governos estaduais e das prefeituras (Relatório de Gestão Fiscal, Anexo 2).

    uv run divida                    # estados, de 2015 até o último ano fechado
    uv run divida --anos 2024 2025
    uv run divida --prefeituras      # prefeituras, o último ano fechado (~5.570 consultas, 1h30 ou mais)

Fonte: RGF Anexo 02, "Demonstrativo da Dívida Consolidada Líquida", que o Poder Executivo de cada
estado entrega ao Tesouro a cada quadrimestre (API do SICONFI, a mesma de cidades.py, com o mesmo
limite de uma consulta por segundo). Fica o fim do ano (3º quadrimestre):
- dívida consolidada (DC): tudo o que o estado deve a prazo maior que um ano;
- dívida consolidada líquida (DCL): a DC menos o que o estado tem em caixa e aplicações;
- receita corrente líquida ajustada (RCL): a base dos limites da Lei de Responsabilidade Fiscal.
O limite para os estados é de duas vezes a RCL e, para as prefeituras, de 1,2 vez (Resolução
40/2001 do Senado); o de alerta, 90% disso (art. 59 da LRF). Prefeituras de cidades com menos de
50 mil habitantes podem entregar o RGF por semestre: para elas o semestre é consultado primeiro. Os percentuais são calculados aqui, a partir dos valores, porque o
rótulo das linhas muda de um ano para outro.

Cache em data/raw/siconfi/rgf-a02/{ano}.json.gz (prefeituras: rgf-a02-mun/). Saída em
site/public/data/estados/divida.json (prefeituras: site/public/data/cidades/divida.json, com cópia
versionada em pipeline/referencia/divida-prefeituras.json, porque a primeira carga é longa):
    {"fonte": …, "anos": {"2025": {"33": [DC, DCL, RCL ajustada]}}}
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date

from . import cidades as c

SAIDA = c.RAIZ / "site" / "public" / "data" / "estados" / "divida.json"
SAIDA_MUN = c.RAIZ / "site" / "public" / "data" / "cidades" / "divida.json"
REFERENCIA_MUN = c.RAIZ / "pipeline" / "referencia" / "divida-prefeituras.json"
POPULACAO = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
PRIMEIRO_ANO = 2015
FONTE = "Tesouro Nacional, Relatório de Gestão Fiscal dos estados (Anexo 2, dívida consolidada líquida), 3º quadrimestre"
FONTE_MUN = "Tesouro Nacional, Relatório de Gestão Fiscal das prefeituras (Anexo 2, dívida consolidada líquida), fim do ano"


def baixar(cache: c.CacheAno, ano: int, ibge: int, esfera: str = "E", semestre_primeiro: bool = False) -> list[dict] | None:
    """As linhas do Anexo 2 do fim do ano; [] se o ente não entregou; None se a consulta falhou.

    Um estado sem resposta ([] no cache) é consultado de novo a cada execução, porque pode entregar atrasado.
    Uma prefeitura sem resposta não é: para procurar as que entregaram depois, apague
    data/raw/siconfi/rgf-a02-mun/{ano}.json.gz antes de rodar `uv run divida --prefeituras`."""
    if (itens := cache.obter(ibge)) is not None and (itens or esfera == "M"):
        return itens
    periodos = (("S", 2), ("Q", 3)) if semestre_primeiro else (("Q", 3), ("S", 2))
    for periodicidade, periodo in periodos:
        if not c.CHAMADAS.gastar():
            return None
        try:
            d = c._get("rgf", {"an_exercicio": ano, "in_periodicidade": periodicidade, "nr_periodo": periodo,
                               "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 02", "co_esfera": esfera,
                               "co_poder": "E", "id_ente": ibge})
        except Exception as erro:   # a API às vezes falha; fica para a próxima execução
            print(f"  {ibge}/{ano}: {erro}", flush=True)
            return None
        itens = [{k: i.get(k) for k in ("coluna", "conta", "valor")} for i in d.get("items", []) if FIM.search(i.get("coluna") or "")]
        if itens:
            cache.guardar(ibge, itens)
            return itens
    cache.guardar(ibge, [])
    return []


# A coluna do fim do ano: "Até o 3º Quadrimestre" (ou o 2º semestre, para quem entrega por semestre).
FIM = re.compile(r"(3º|3°|3o)\s*quadrimestre|(2º|2°|2o)\s*semestre", re.I)


def filtro_rgf(itens: list[dict]) -> list[dict]:
    """O que o cache guarda de cada resposta. Sem ele, o CacheAno usaria o filtro da DCA (só as colunas de
    despesa empenhada e paga), que não existem no RGF: o cache gravava listas vazias."""
    return [{k: i.get(k) for k in ("coluna", "conta", "valor")} for i in itens]


def resumir(itens: list[dict]) -> list[float] | None:
    """[DC, DCL, RCL ajustada] no fim do ano."""
    fim = [i for i in itens if FIM.search(i["coluna"])]
    valores: dict[str, float] = {}
    for i in fim:
        conta = c._so_letras(i["conta"])
        if conta.startswith("dividaconsolidadaliquida"):
            valores.setdefault("dcl", float(i["valor"] or 0))
        elif conta.startswith("dividaconsolidada"):
            valores.setdefault("dc", float(i["valor"] or 0))
        elif conta.startswith("receitacorrenteliquidaajustada"):
            valores.setdefault("rcl_aj", float(i["valor"] or 0))
        elif conta.startswith("receitacorrenteliquida"):
            valores.setdefault("rcl", float(i["valor"] or 0))
    rcl = valores.get("rcl_aj") or valores.get("rcl")
    if "dcl" not in valores or not rcl:
        return None
    return [round(valores.get("dc", 0)), round(valores["dcl"]), round(rcl)]


def main() -> None:
    hoje = date.today()
    # O RGF do 3º quadrimestre é entregue até 30 de janeiro: a partir de março o ano anterior está completo.
    ultimo = hoje.year - 1 if hoje.month >= 3 else hoje.year - 2
    p = argparse.ArgumentParser(prog="divida", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+", default=list(range(PRIMEIRO_ANO, ultimo + 1)))
    p.add_argument("--max-chamadas", type=int, default=None, help="para depois de N consultas novas à API")
    p.add_argument("--prefeituras", action="store_true", help="as prefeituras em vez dos estados (padrão: só o último ano fechado)")
    args = p.parse_args()
    c.CHAMADAS.restantes = args.max_chamadas
    if args.prefeituras:
        prefeituras(args.anos if args.anos != list(range(PRIMEIRO_ANO, ultimo + 1)) else [ultimo])
        return

    anos: dict[str, dict[str, list[float]]] = {}
    pendentes = 0
    for ano in sorted(args.anos):
        cache = c.CacheAno(ano, anexo="rgf-a02", filtro=filtro_rgf)
        try:
            for ibge in sorted(c.SIGLAS):
                itens = baixar(cache, ano, ibge)
                if itens is None:
                    pendentes += 1
                    continue
                if itens and (r := resumir(itens)):
                    anos.setdefault(str(ano), {})[str(ibge)] = r
        finally:
            cache.salvar()
        print(f"{ano}: {len(anos.get(str(ano), {}))} estados", flush=True)

    # Junta ao que já existe: um ano que falhou agora não apaga o que foi baixado antes.
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")).get("anos", {}) if SAIDA.exists() else {}
    for ano, estados in anterior.items():
        for ibge, v in estados.items():
            anos.setdefault(ano, {}).setdefault(ibge, v)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"fonte": FONTE, "anos": dict(sorted(anos.items()))}, separators=(",", ":")), encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)}" + (f" ({pendentes} consultas ficaram para a próxima execução)" if pendentes else ""))


def prefeituras(anos_pedidos: list[int]) -> None:
    pop = {str(x["ibge"]): x["pop"] for x in json.loads(POPULACAO.read_text(encoding="utf-8"))["cidades"]}
    # Brasília não tem prefeitura: o Distrito Federal entra com os estados.
    entes = sorted((int(k) for k in pop if len(k) == 7 and not k.startswith("53")), key=lambda k: -pop[str(k)])
    origem = REFERENCIA_MUN if REFERENCIA_MUN.exists() else SAIDA_MUN
    anos: dict[str, dict[str, list[float]]] = json.loads(origem.read_text(encoding="utf-8")).get("anos", {}) if origem.exists() else {}
    pendentes = 0
    for ano in sorted(anos_pedidos):
        cache = c.CacheAno(ano, anexo="rgf-a02-mun", filtro=filtro_rgf)
        doano = anos.setdefault(str(ano), {})
        try:
            for i, ibge in enumerate(entes):
                if str(ibge) in doano:
                    continue
                itens = baixar(cache, ano, ibge, esfera="M", semestre_primeiro=pop[str(ibge)] < 50_000)
                if itens is None:
                    pendentes += 1
                    continue
                if itens and (r := resumir(itens)):
                    doano[str(ibge)] = r
                if (i + 1) % 250 == 0:
                    print(f"  {ano}: {i + 1} de {len(entes)} consultadas, {len(doano)} com dados", flush=True)
                    gravar_mun(anos)
        finally:
            cache.salvar()
            gravar_mun(anos)
        print(f"{ano}: {len(doano)} prefeituras", flush=True)
    print(f"saída: {SAIDA_MUN.relative_to(c.RAIZ)} e {REFERENCIA_MUN.relative_to(c.RAIZ)}"
          + (f" ({pendentes} consultas ficaram para a próxima execução)" if pendentes else ""))


def gravar_mun(anos: dict) -> None:
    texto = json.dumps({"fonte": FONTE_MUN, "anos": {a: dict(sorted(v.items())) for a, v in sorted(anos.items())}}, separators=(",", ":"))
    for destino in (SAIDA_MUN, REFERENCIA_MUN):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
