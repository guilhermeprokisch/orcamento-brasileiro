"""Gasto com pessoal dos governos estaduais e das prefeituras (Relatório de Gestão Fiscal, Anexo 1).

    uv run pessoal                    # estados, de 2015 até o último ano fechado
    uv run pessoal --anos 2024 2025
    uv run pessoal --prefeituras      # prefeituras, o último ano fechado (~5.570 consultas, 1h30 ou mais)
    uv run pessoal --prefeituras --max-chamadas 0   # só copia a referência (publicação automática)

Fonte: RGF Anexo 01, "Demonstrativo da Despesa com Pessoal", do Poder Executivo (API do SICONFI, uma
consulta por segundo, como em divida.py). Fica o fim do ano (3º quadrimestre ou 2º semestre), com os
12 meses somados:
- despesa total com pessoal (DTP): a conta da Lei de Responsabilidade Fiscal, que deixa de fora, entre
  outras coisas, as aposentadorias pagas pelo fundo de previdência dos servidores;
- receita corrente líquida ajustada (RCL): a base do limite;
- despesa bruta com pessoal, dividida em servidores ativos e aposentados e pensionistas.
O limite do Executivo é 54% da RCL nas prefeituras e 49% nos estados (art. 20 da LRF); o prudencial,
95% dele (art. 22) e o de alerta, 90% (art. 59).

Cache em data/raw/siconfi/rgf-a01/{ano}.json.gz (prefeituras: rgf-a01-mun/). Saída em
site/public/data/estados/pessoal.json (prefeituras: site/public/data/cidades/pessoal.json, com cópia
versionada em pipeline/referencia/pessoal-prefeituras.json, porque a primeira carga é longa):
    {"fonte": …, "anos": {"2025": {"33": [DTP, RCL ajustada, bruta, ativos, aposentados e pensionistas]}}}
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date

from . import cidades as c

SAIDA = c.RAIZ / "site" / "public" / "data" / "estados" / "pessoal.json"
SAIDA_MUN = c.RAIZ / "site" / "public" / "data" / "cidades" / "pessoal.json"
REFERENCIA_MUN = c.RAIZ / "pipeline" / "referencia" / "pessoal-prefeituras.json"
POPULACAO = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
PRIMEIRO_ANO = 2015
FONTE = "Tesouro Nacional, Relatório de Gestão Fiscal dos estados (Anexo 1, despesa com pessoal do Poder Executivo), 3º quadrimestre"
FONTE_MUN = "Tesouro Nacional, Relatório de Gestão Fiscal das prefeituras (Anexo 1, despesa com pessoal do Poder Executivo), fim do ano"

# As duas colunas que interessam: o total dos 12 meses (a despesa) e "Valor" (RCL, DTP e limites).
COLUNAS = re.compile(r"^(valor|total \(últimos 12 meses\))", re.I)


def filtro_rgf(itens: list[dict]) -> list[dict]:
    """O que o cache guarda de cada resposta. Sem ele, o CacheAno usaria o filtro da DCA (só as colunas de
    despesa empenhada e paga), que não existem no RGF: o cache gravava listas vazias."""
    return [{k: i.get(k) for k in ("coluna", "conta", "valor")} for i in itens]


def baixar(cache: c.CacheAno, ano: int, ibge: int, esfera: str = "E", semestre_primeiro: bool = False) -> list[dict] | None:
    """As linhas do Anexo 1 do fim do ano; [] se o ente não entregou; None se a consulta falhou.

    Um estado sem resposta ([] no cache) é consultado de novo a cada execução, porque pode entregar atrasado.
    Uma prefeitura sem resposta não é: para procurar as que entregaram depois, apague
    data/raw/siconfi/rgf-a01-mun/{ano}.json.gz antes de rodar `uv run pessoal --prefeituras`."""
    if (itens := cache.obter(ibge)) is not None and (itens or esfera == "M"):
        return itens
    periodos = (("S", 2), ("Q", 3)) if semestre_primeiro else (("Q", 3), ("S", 2))
    for periodicidade, periodo in periodos:
        if not c.CHAMADAS.gastar():
            return None
        try:
            d = c._get("rgf", {"an_exercicio": ano, "in_periodicidade": periodicidade, "nr_periodo": periodo,
                               "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 01", "co_esfera": esfera,
                               "co_poder": "E", "id_ente": ibge})
        except Exception as erro:   # a API às vezes falha; fica para a próxima execução
            print(f"  {ibge}/{ano}: {erro}", flush=True)
            return None
        itens = [{k: i.get(k) for k in ("coluna", "conta", "valor")} for i in d.get("items", []) if COLUNAS.search(i.get("coluna") or "")]
        if itens:
            cache.guardar(ibge, itens)
            return itens
    cache.guardar(ibge, [])
    return []


def resumir(itens: list[dict]) -> list[int] | None:
    """[DTP, RCL ajustada, despesa bruta, ativos, aposentados e pensionistas] no fim do ano."""
    v: dict[str, float] = {}
    for i in itens:
        conta, total = c._so_letras(i["conta"]), (i["coluna"] or "").lower().startswith("total")
        valor = float(i["valor"] or 0)
        if total:
            if conta.startswith("despesabrutacompessoal"):
                v.setdefault("bruta", valor)
            elif conta.startswith("pessoalativo"):
                v.setdefault("ativos", valor)
            elif conta.startswith("pessoalinativo"):
                v.setdefault("inativos", valor)
        elif conta.startswith("despesatotalcompessoal"):
            v.setdefault("dtp", valor)
        elif "receitacorrenteliquidaajustada" in conta:
            v.setdefault("rcl_aj", valor)
        elif conta.startswith("receitacorrenteliquida"):
            v.setdefault("rcl", valor)
    rcl = v.get("rcl_aj") or v.get("rcl")
    if not v.get("dtp") or not rcl:
        return None
    return [round(v["dtp"]), round(rcl), round(v.get("bruta", 0)), round(v.get("ativos", 0)), round(v.get("inativos", 0))]


def main() -> None:
    hoje = date.today()
    # O RGF do fim do ano é entregue até 30 de janeiro: a partir de março o ano anterior está completo.
    ultimo = hoje.year - 1 if hoje.month >= 3 else hoje.year - 2
    p = argparse.ArgumentParser(prog="pessoal", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+", default=list(range(PRIMEIRO_ANO, ultimo + 1)))
    p.add_argument("--max-chamadas", type=int, default=None, help="para depois de N consultas novas à API")
    p.add_argument("--prefeituras", action="store_true", help="as prefeituras em vez dos estados (padrão: só o último ano fechado)")
    args = p.parse_args()
    c.CHAMADAS.restantes = args.max_chamadas
    if args.prefeituras:
        prefeituras(args.anos if args.anos != list(range(PRIMEIRO_ANO, ultimo + 1)) else [ultimo])
        return

    anos: dict[str, dict[str, list[int]]] = {}
    pendentes = 0
    for ano in sorted(args.anos):
        cache = c.CacheAno(ano, anexo="rgf-a01", filtro=filtro_rgf)
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
    anos: dict[str, dict[str, list[int]]] = json.loads(origem.read_text(encoding="utf-8")).get("anos", {}) if origem.exists() else {}
    pendentes = 0
    for ano in sorted(anos_pedidos):
        cache = c.CacheAno(ano, anexo="rgf-a01-mun", filtro=filtro_rgf)
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
