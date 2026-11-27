"""Para quem vai o dinheiro da saúde (e da educação) de cada prefeitura: quanto passa para entidades
sem fins lucrativos (Santas Casas, hospitais filantrópicos, organizações sociais), quanto para
empresas, quanto é folha própria, pessoal terceirizado, repasse a outros governos e o resto.

    uv run saude-entidades                  # último ano fechado; ~3 h na primeira vez (1 consulta por segundo)
    uv run saude-entidades --uf SP --limite 20   # um teste curto
    uv run saude-entidades --sem-baixar     # só copia pipeline/referencia/saude-entidades.json (publicação)

Fonte: a Matriz de Saldos Contábeis (MSC) que cada prefeitura manda todo mês ao Tesouro (SICONFI,
API aberta em apidatalake.tesouro.gov.br, msc_orcamentaria). A de dezembro, classe 6 (execução da
despesa), traz cada conta com a função (10 = saúde, 12 = educação), a subfunção e a natureza da
despesa completa: grupo (pessoal, custeio, investimento), modalidade de aplicação (quem recebe: a
própria prefeitura, outro governo, entidade sem fins lucrativos, empresa) e elemento. Nenhum
relatório anual (DCA, RREO) cruza a função com a modalidade; a MSC cruza.

Conta "liquidada" = 6.2.2.1.3.03 (liquidado a pagar) + 6.2.2.1.3.04 (liquidado e pago). Em São Carlos
(SP), 2025, a soma dá R$ 460,0 mi na saúde, e a DCA (Anexo I-E, "Despesas Liquidadas") R$ 459,9 mi;
a diferença é a despesa intraorçamentária (modalidade 91), que aqui fica de fora. O módulo compara
com a DCA de cada cidade quando ela está no cache (data/raw/siconfi/dca-ie/) e tira da saída as que
não batem (em 2025, 116 de 4.756; em algumas a MSC traz um décimo da saúde, em outras o triplo).

Grupos de destino (o que cada um costuma ser):
- entidades: modalidade 50, "transferências a instituições privadas sem fins lucrativos", menos o
  elemento 85. Santas Casas e hospitais filantrópicos contratados ou conveniados, APAEs, entidades
  que tocam creches. Não diz qual entidade: o nome está nos pagamentos por credor (pagamentos.py),
  que só existem para alguns estados, e na lista de hospitais (unidades_saude.py).
- organizações sociais: modalidade 50, elemento 85 ("contrato de gestão"), OSs que administram
  hospitais, UPAs e postos. Muitas prefeituras lançam o contrato de gestão no elemento 39 da
  modalidade 50: aí ele aparece em "entidades".
- empresas: modalidades 60 e 67 (instituições privadas com fins lucrativos, PPP).
- terceirizados: elemento 34 (pessoal decorrente de contratos de terceirização) e 37 (locação de mão
  de obra), em qualquer modalidade direta: médicos por empresa, cooperativa, limpeza, vigilância.
- folha: grupo 1 (pessoal e encargos), sem o elemento 34.
- outros governos: modalidades de transferência ou aplicação em outro ente e consórcios
  (20–46, 70–76, 93–95).
- prefeitura: o resto da aplicação direta (90 e afins): remédios, material, serviços contratados
  (exames, aluguel, sistemas), obras e equipamentos.

Cache por ente em data/raw/siconfi/msc-liquidado/{ano}.json.gz ([função, subfunção, natureza de 6
dígitos (grupo, modalidade, elemento), valor], só o liquidado). Saída em
site/public/data/indicadores/saude-entidades.json, com cópia em pipeline/referencia/:
    {"fonte", "ano", "grupos": [rótulos], "brasil": {"10": [...], "12": [...]},
     "mun": {ibge: {"10": [liquidado, entidades, organizações sociais, empresas, terceirizados, folha,
                           outros governos, prefeitura], "12": [...]}}}
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from . import cidades as c

SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "saude-entidades.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "saude-entidades.json"
CONTAS_LIQUIDADO = {"622130300", "622130400"}
FUNCOES = ("10", "12")
GRUPOS = ["entidades sem fins lucrativos", "organizações sociais (contrato de gestão)", "empresas",
          "pessoal terceirizado", "folha própria", "outros governos e consórcios", "a própria prefeitura"]
OUTROS_GOVERNOS = {f"{m:02d}" for m in [*range(20, 47), *range(70, 77), 93, 94, 95]}
FONTE = ("Tesouro Nacional, SICONFI: Matriz de Saldos Contábeis (MSC) de dezembro, despesa liquidada "
         "por função e modalidade de aplicação")


def grupo_de(natureza6: str) -> int | None:
    """Índice em GRUPOS a partir de grupo (1 dígito), modalidade (2) e elemento (2). None = intraorçamentária."""
    grupo, mod, elem = natureza6[0], natureza6[1:3], natureza6[3:5]
    if mod == "91":
        return None
    if mod == "50":
        return 1 if elem == "85" else 0
    if mod in ("60", "67"):
        return 2
    if mod in OUTROS_GOVERNOS:
        return 5
    if elem in ("34", "37"):
        return 3
    if grupo == "1":
        return 4
    return 6


def compactar(itens: list[dict]) -> list[list]:
    """Linhas da MSC -> [função, subfunção, natureza de 6 dígitos, valor liquidado], somadas."""
    soma: dict[tuple[str, str, str], float] = defaultdict(float)
    for r in itens:
        if r.get("conta_contabil") not in CONTAS_LIQUIDADO or not r.get("funcao") or not r.get("natureza_despesa"):
            continue
        n = r["natureza_despesa"]
        # Nas contas de execução, a movimentação do ano vem a débito; um crédito é estorno.
        v = r["valor"] if r.get("natureza_conta") == "D" else -r["valor"]
        soma[(str(r["funcao"]).zfill(2), str(r.get("subfuncao") or "").zfill(3), n[1:6])] += v
    return [[f, s, n, round(v, 2)] for (f, s, n), v in soma.items() if abs(v) >= 0.005]


def baixar_msc(cache: c.CacheAno, ano: int, ibge: int, consultar: bool) -> list[list] | None:
    """Linhas compactadas do ente; [] se ele não mandou a MSC de dezembro; None se a consulta falhou."""
    if str(ibge) in cache.dados:
        return cache.dados[str(ibge)]
    if not consultar:
        return None
    itens: list[dict] = []
    offset = 0
    try:
        while True:
            d = c._get("msc_orcamentaria", {"id_ente": ibge, "an_referencia": ano, "me_referencia": 12,
                                            "co_tipo_matriz": "MSCE", "classe_conta": 6, "id_tv": "period_change",
                                            "offset": offset})
            itens += d["items"]
            if not d.get("hasMore"):
                break
            offset += d["limit"]
    except Exception as e:
        print(f"  {ibge}: {e}", flush=True)
        return None
    cache.guardar(ibge, itens)
    return cache.dados[str(ibge)]


def resumir(linhas: list[list]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for f in FUNCOES:
        v = [0.0] * len(GRUPOS)
        for fun, _, nat, valor in linhas:
            if fun == f and (g := grupo_de(nat)) is not None:
                v[g] += valor
        if sum(v) > 0:
            out[f] = [round(sum(v))] + [round(x) for x in v]
    return out


def conferir_dca(ano: int, resumos: dict[int, dict]) -> set[int]:
    """Confere o total da saúde com a DCA (Anexo I-E) das cidades que estão no cache: o liquidado tem que
    ficar entre o pago e o empenhado (o cache da DCA guarda só essas duas colunas), com 2% de folga."""
    dca = c.CacheAno(ano)
    longe = comparadas = 0
    fora: set[int] = set()
    for ibge, r in resumos.items():
        itens = dca.obter(ibge)
        if not itens or "10" not in r:
            continue
        col = {x["coluna"]: x["valor"] for x in itens if x["conta"].startswith("10 - ")}
        emp, pago = col.get("Despesas Empenhadas"), col.get("Despesas Pagas")
        if not emp or pago is None:
            continue
        comparadas += 1
        if not (0.98 * pago <= r["10"][0] <= 1.02 * emp):
            longe += 1
            fora.add(ibge)
            if longe <= 10:
                print(f"  {ibge}: saúde liquidada na MSC {r['10'][0] / 1e6:.1f} mi; "
                      f"na DCA, paga {pago / 1e6:.1f} mi e empenhada {emp / 1e6:.1f} mi", flush=True)
    print(f"conferência com a DCA: {comparadas - longe} de {comparadas} cidades batem; as outras ficam de fora", flush=True)
    return fora


def gravar(doc: dict) -> int:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return len(texto)


def main() -> None:
    p = argparse.ArgumentParser(prog="saude-entidades", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=date.today().year - 1)
    p.add_argument("--uf", help="só as cidades de um estado (teste)")
    p.add_argument("--limite", type=int, help="no máximo N cidades (teste)")
    p.add_argument("--paralelo", type=int, default=3)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a referência para o site")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está no cache, sem consultar")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA.exists():
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia da referência)")
        return

    entes = [e for e in c.baixar_entes() if e.get("esfera") == "M"]
    if args.uf:
        entes = [e for e in entes if e.get("uf") == args.uf.upper()]
    # Os maiores primeiro: se a carga parar no meio, as cidades com mais gente já estão prontas.
    entes.sort(key=lambda e: -(e.get("populacao") or 0))
    if args.limite:
        entes = entes[: args.limite]
    cache = c.CacheAno(args.ano, anexo="msc-liquidado", filtro=compactar)
    faltam = sum(str(e["cod_ibge"]) not in cache.dados for e in entes)
    print(f"MSC {args.ano}: {len(entes)} cidades, {faltam} a consultar", flush=True)
    t0 = time.time()
    feitas = 0

    def um(e: dict):
        nonlocal feitas
        r = baixar_msc(cache, args.ano, e["cod_ibge"], not args.so_cache)
        feitas += 1
        if feitas % 100 == 0:
            print(f"  {feitas}/{len(entes)} ({time.time() - t0:.0f}s)", flush=True)
        return r

    try:
        with ThreadPoolExecutor(args.paralelo) as ex:
            brutos = list(ex.map(um, entes))
    finally:
        cache.salvar()

    resumos: dict[int, dict] = {}
    for e, linhas in zip(entes, brutos):
        if linhas:
            r = resumir(linhas)
            if r:
                resumos[e["cod_ibge"]] = r
    sem = sum(1 for b in brutos if b == [])
    falhas = sum(1 for b in brutos if b is None)
    print(f"{len(resumos)} cidades com dados; {sem} sem a MSC de dezembro; {falhas} consultas falharam", flush=True)
    # Onde a MSC não bate com a DCA, uma das duas está errada e não dá para saber qual: a cidade sai.
    for ibge in conferir_dca(args.ano, resumos):
        del resumos[ibge]

    brasil = {f: [sum(r[f][i] for r in resumos.values() if f in r) for i in range(len(GRUPOS) + 1)] for f in FUNCOES}
    for f, nome in (("10", "saúde"), ("12", "educação")):
        t = brasil[f][0] or 1
        partes = ", ".join(f"{g} {100 * v / t:.0f}%" for g, v in zip(GRUPOS, brasil[f][1:]))
        print(f"{nome}: R$ {t / 1e9:.1f} bi liquidados; {partes}", flush=True)
    doc = {"fonte": FONTE, "ano": args.ano, "grupos": GRUPOS, "brasil": brasil,
           "mun": {str(k): v for k, v in sorted(resumos.items())}}
    tam = gravar(doc)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({tam / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
