"""Quanto cada governo aplicou em saúde e em educação frente ao mínimo da Constituição.

    uv run minimos                         # estados e DF, os anos fechados desde 2019
    uv run minimos --prefeituras           # prefeituras, o último ano fechado (~5.570 consultas, 1h30 ou mais)
    uv run minimos --prefeituras --anos 2023 2024
    uv run minimos --prefeituras --max-chamadas 0   # só copia a referência (publicação automática)

A Constituição manda aplicar uma parte da receita de impostos (e das transferências que vêm deles):
- saúde: 15% nas prefeituras (LC 141/2012, art. 7º) e 12% nos estados (art. 6º);
- educação (manutenção e desenvolvimento do ensino): 25% nos dois (CF, art. 212).

O número usado é o que o próprio governo declarou e apurou, não um cálculo nosso. Ele está no
RREO Anexo 14, "Demonstrativo Simplificado", do 6º bimestre (o ano inteiro), na coluna
"% Aplicado Até o Bimestre". Os anexos completos de saúde (12) e de educação (8) não estão na API
do SICONFI, porque são gerados pelo SIOPS e pelo SIOPE; o Anexo 14 repete o resultado dos dois.
Uma consulta por ente e por ano, a 1 por segundo (ver cidades.Ritmo).

Em 2020 e 2021 a Emenda Constitucional 119/2022 livrou de punição quem não aplicou os 25% em educação
por causa da pandemia, com a condição de completar a diferença até 2023. O arquivo guarda o número
desses anos; quem mostra o aviso decide como tratá-los.

Cache em data/raw/siconfi/rreo-a14/{ano}.json.gz. Saídas:
- site/public/data/estados/minimos.json
- site/public/data/cidades/minimos.json, com cópia versionada em pipeline/referencia/minimos-prefeituras.json,
  porque a primeira carga é longa (como em pessoal.py)
    {"fonte": …, "campos": [...], "anos": {"2025": {"3550308": [23.85, 15, 25.17, 25]}}}
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from . import cidades as c

SAIDA = c.RAIZ / "site" / "public" / "data" / "estados" / "minimos.json"
SAIDA_MUN = c.RAIZ / "site" / "public" / "data" / "cidades" / "minimos.json"
REFERENCIA_MUN = c.RAIZ / "pipeline" / "referencia" / "minimos-prefeituras.json"
POPULACAO = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
PASTA = "rreo-a14"
ANEXO = "RREO-Anexo 14"
PRIMEIRO_ANO = 2019
LIMITE_SIMPLIFICADO = 50_000  # habitantes: abaixo disso a prefeitura costuma entregar o "RREO Simplificado"
FONTE = ("Tesouro Nacional, Relatório Resumido de Execução Orçamentária (Anexo 14, demonstrativo simplificado), "
         "6º bimestre: percentual aplicado em saúde e em educação, como declarado pelo governo")
CAMPOS = ["saude", "saude_min", "educacao", "educacao_min"]

# Prefixo do identificador da conta -> área. As duas linhas do Anexo 14 com o percentual oficial.
CONTAS = {
    "AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude": "saude",
    "MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimento": "educacao",
}
APLICADO, MINIMO = "% Aplicado Até o Bimestre", "% Mínimo a Aplicar no Exercício"

# --atrasadas: consultar de novo as prefeituras que o cache marca como sem resposta ([]).
ATRASADAS = False


def _area(cod_conta: str | None) -> str | None:
    return next((a for prefixo, a in CONTAS.items() if (cod_conta or "").startswith(prefixo)), None)


def filtro(itens: list[dict]) -> list[dict]:
    """O cache guarda só as duas linhas de percentual (o anexo tem ~100)."""
    return [{k: i.get(k) for k in ("cod_conta", "coluna", "valor")} for i in itens
            if _area(i.get("cod_conta")) and i.get("coluna") in (APLICADO, MINIMO)]


def baixar(cache: c.CacheAno, ano: int, ibge: int, simplificado_primeiro: bool = False) -> list[dict] | None:
    """As linhas de percentual do 6º bimestre; [] se o ente não entregou; None se a consulta falhou."""
    if (itens := cache.obter(ibge)) is not None and (itens or (ibge > 99 and not ATRASADAS)):
        return itens
    tipos = ("RREO Simplificado", "RREO") if simplificado_primeiro else ("RREO", "RREO Simplificado")
    for tipo in tipos:
        if not c.CHAMADAS.gastar():
            return None
        try:
            d = c._get("rreo", {"an_exercicio": ano, "nr_periodo": 6, "co_tipo_demonstrativo": tipo,
                                "no_anexo": ANEXO, "id_ente": ibge})
        except Exception as erro:   # a API às vezes falha; fica para a próxima execução
            print(f"  {ibge}/{ano}: {erro}", flush=True)
            return None
        if itens := filtro(d.get("items", [])):
            cache.guardar(ibge, itens)
            return itens
    cache.guardar(ibge, [])
    return []


def resumir(itens: list[dict]) -> list[float | None] | None:
    """[saúde aplicada, mínimo de saúde, educação aplicada, mínimo de educação], em %."""
    v: dict[str, float] = {}
    for i in itens:
        area = _area(i["cod_conta"])
        chave = area if i["coluna"] == APLICADO else f"{area}_min"
        if i["valor"] is not None:
            v.setdefault(chave, round(float(i["valor"]), 2))
    if "saude" not in v and "educacao" not in v:
        return None
    return [v.get(k) for k in CAMPOS]


def ultimo_ano_fechado(hoje: date) -> int:
    # O RREO do 6º bimestre é entregue até 30 de janeiro: a partir de março o ano anterior está completo.
    return hoje.year - 1 if hoje.month >= 3 else hoje.year - 2


def gravar(destinos, fonte: str, anos: dict) -> None:
    texto = json.dumps({"fonte": fonte, "campos": CAMPOS,
                        "anos": {a: dict(sorted(v.items())) for a, v in sorted(anos.items())}}, separators=(",", ":"))
    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")


def estados(anos_pedidos: list[int]) -> None:
    anos: dict[str, dict] = json.loads(SAIDA.read_text(encoding="utf-8")).get("anos", {}) if SAIDA.exists() else {}
    for ano in sorted(anos_pedidos):
        cache = c.CacheAno(ano, anexo=PASTA, filtro=filtro)
        doano = anos.setdefault(str(ano), {})
        try:
            for ibge in sorted(c.SIGLAS):
                itens = baixar(cache, ano, ibge)
                if itens and (r := resumir(itens)):
                    doano[str(ibge)] = r
        finally:
            cache.salvar()
        print(f"{ano}: {len(doano)} estados", flush=True)
    gravar([SAIDA], FONTE, anos)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)}")


def prefeituras(anos_pedidos: list[int]) -> None:
    pop = {str(x["ibge"]): x["pop"] for x in json.loads(POPULACAO.read_text(encoding="utf-8"))["cidades"]}
    # Brasília não tem prefeitura: o Distrito Federal entra com os estados.
    entes = sorted((int(k) for k in pop if len(k) == 7 and not k.startswith("53")), key=lambda k: -pop[str(k)])
    origem = REFERENCIA_MUN if REFERENCIA_MUN.exists() else SAIDA_MUN
    anos: dict[str, dict] = json.loads(origem.read_text(encoding="utf-8")).get("anos", {}) if origem.exists() else {}
    pendentes = 0
    for ano in sorted(anos_pedidos):
        cache = c.CacheAno(ano, anexo=PASTA, filtro=filtro)
        doano = anos.setdefault(str(ano), {})
        try:
            for i, ibge in enumerate(entes):
                if str(ibge) in doano:
                    continue
                itens = baixar(cache, ano, ibge, simplificado_primeiro=pop[str(ibge)] < LIMITE_SIMPLIFICADO)
                if itens is None:
                    pendentes += 1
                    continue
                if itens and (r := resumir(itens)):
                    doano[str(ibge)] = r
                if (i + 1) % 250 == 0:
                    print(f"  {ano}: {i + 1} de {len(entes)} consultadas, {len(doano)} com dados", flush=True)
                    gravar((SAIDA_MUN, REFERENCIA_MUN), FONTE, anos)
        finally:
            cache.salvar()
            gravar((SAIDA_MUN, REFERENCIA_MUN), FONTE, anos)
        print(f"{ano}: {len(doano)} prefeituras", flush=True)
    print(f"saída: {SAIDA_MUN.relative_to(c.RAIZ)} e {REFERENCIA_MUN.relative_to(c.RAIZ)}"
          + (f" ({pendentes} consultas ficaram para a próxima execução)" if pendentes else ""))


def main() -> None:
    ultimo = ultimo_ano_fechado(date.today())
    p = argparse.ArgumentParser(prog="minimos", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+", default=None)
    p.add_argument("--max-chamadas", type=int, default=None, help="para depois de N consultas novas à API")
    p.add_argument("--prefeituras", action="store_true", help="as prefeituras em vez dos estados (padrão: só o último ano fechado)")
    p.add_argument("--atrasadas", action="store_true", help="com --prefeituras: consulta de novo as que ainda não tinham entregado")
    args = p.parse_args()
    global ATRASADAS
    ATRASADAS = args.atrasadas
    c.CHAMADAS.restantes = args.max_chamadas
    if args.prefeituras:
        prefeituras(args.anos or [ultimo])
    else:
        estados(args.anos or list(range(PRIMEIRO_ANO, ultimo + 1)))


if __name__ == "__main__":
    main()
