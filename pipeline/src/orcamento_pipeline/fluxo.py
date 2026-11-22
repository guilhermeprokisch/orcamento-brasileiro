"""O caminho do dinheiro dentro do ano: empenhado → liquidado → pago, e os restos a pagar.

    uv run fluxo 2025                   # todos os meses publicados de 2025
    uv run fluxo 2025 --meses 1 2 3     # só esses meses
    uv run fluxo 2025 --forcar          # baixa os zips de novo

Por que este comando existe
---------------------------
O orçamento anual (comando `orcamento`) é uma foto do exercício: dotação e empenho. Mas
o governo gasta em três etapas, e elas podem cair em anos diferentes:

    empenhado   reservou o dinheiro e assumiu o compromisso
    liquidado   a obra foi entregue, o serviço prestado, o benefício reconhecido
    pago        o dinheiro saiu do caixa

O que fica empenhado e não é pago vira **restos a pagar** e é arrastado para os anos
seguintes. Em despesa obrigatória isso quase não acontece — aposentadoria é paga no mês.
Em investimento é a regra: a obra é empenhada em dezembro e quitada dois ou três anos
depois. Então "o governo investiu X" medido pelo empenho mostra um governo mais ativo do
que ele foi, e é esse o número que o debate público usa.

O site já diz **quanto** está amarrado (`/contas`, "Quanto está amarrado") e qual a divisão
por tipo em cada recorte do Explorer (`FaixaTipo`). O que faltava era o **quando**: a saída
deste comando é a série mês a mês das três etapas, separada por tipo de despesa, que é o
que permite mostrar o empenho concentrado em dezembro e a conta velha sendo quitada.

Como cada linha é classificada
------------------------------
O arquivo mensal do Portal não traz o resultado primário, mas traz a chave
UO × função × subfunção × programa × ação × GND — a mesma do SIOP. O cache
`data/raw/siop/rp-{ano}.json` (do comando `orcamento`) dá o RP de cada chave, e daí o tipo,
com o mesmo `TIPO_DO_RP` que o Explorer usa. Chave com mais de um tipo é repartida na
proporção da **dotação atualizada** do SIOP; é mais grosseiro que o `separar_por_tipo` do
`transformar.py`, que reparte cada medida pela sua equivalente, porque o SIOP não tem
equivalente de liquidado nem de restos a pagar. Chave sem par no SIOP vira tipo "sem", e o
comando imprime quanto isso representa: enquanto for pequeno, a série se sustenta.

Cuidados
--------
- "Pago" é pagamento de empenho do próprio exercício; "restos a pagar pagos" é desembolso de
  compromisso de anos anteriores. As duas colunas NÃO se sobrepõem: somam-se para dar o
  desembolso do mês. Quem somar as duas como se fosse gasto do ano conta duas vezes.
- Os valores de cada mês são fluxo do mês, não acumulado do ano.
- São ~7 MB por mês zipado (~60 MB de CSV, ~70 mil linhas). Os zips ficam na mesma pasta que
  o `gasto-federal` já usa, então rodar os dois não baixa nada duas vezes.
- O mês mais recente sai com algumas semanas de atraso, e o Portal às vezes responde com
  CAPTCHA em vez do zip (`_baixar` quebra com aviso claro nesse caso).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from datetime import date

from .cidades import RAIZ
from .fontes import baixar_rp_siop
# Reaproveita o baixador e a pasta de cache do gasto-federal, que já lê estes mesmos zips.
from .gasto_federal import PASTA_EXECUCAO, URL_EXECUCAO, _baixar
from .transformar import TIPO_DO_RP, TIPOS

PASTA_SIOP = RAIZ / "data" / "raw" / "siop"
SAIDA = RAIZ / "site" / "public" / "data" / "federal" / "fluxo-{ano}.json"

# Colunas do CSV mensal que interessam: as seis da chave do SIOP, o grupo de despesa e os valores.
CHAVE = ["Código Unidade Orçamentária", "Código Função", "Código Subfução",
         "Código Programa Orçamentário", "Código Ação", "Código Grupo de Despesa"]
ETAPAS = {
    "empenhado": "Valor Empenhado (R$)",
    "liquidado": "Valor Liquidado (R$)",
    "pago": "Valor Pago (R$)",
    "rap_inscritos": "Valor Restos a Pagar Inscritos (R$)",
    "rap_cancelados": "Valor Restos a Pagar Cancelado (R$)",
    "rap_pagos": "Valor Restos a Pagar Pagos (R$)",
}
# Subfunções de refinanciamento da dívida (rolagem: troca título velho por novo), as mesmas
# que o Explorer tira por padrão.
SUBFUNCOES_REFINANCIAMENTO = {"841", "842"}
GRUPOS = {"1": "pessoal", "2": "juros", "3": "custeio", "4": "investimento",
          "5": "inversoes", "6": "amortizacao"}
FONTE = "Portal da Transparência (CGU), execução da despesa; SIOP, resultado primário"


def _num(s: str) -> float:
    # "1.234.567,89" -> 1234567.89
    s = (s or "0").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def tipos_por_chave(ano: int) -> dict[tuple, dict[str, float]]:
    """{chave do SIOP: {tipo: dotação atualizada}}, do cache `rp-{ano}.json`."""
    rp = baixar_rp_siop(ano, PASTA_SIOP)
    i_rp = rp["colunas"].index("rp")
    i_at = rp["colunas"].index("atualizado")
    por_chave: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for l in rp["linhas"]:
        tipo = TIPO_DO_RP.get(l[i_rp], "esc")
        por_chave[tuple(l[:6])][tipo] += float(l[i_at])
    return por_chave


def somar(ano: int, meses: list[int], por_chave: dict, forcar: bool) -> tuple[dict, dict, float, float]:
    """Soma as etapas por mês × tipo e por mês × grupo de despesa.

    Devolve (por tipo, por grupo, total empenhado, empenhado sem par no SIOP).
    """
    tipo_mes: dict[str, dict[str, dict[str, float]]] = {}
    grupo_mes: dict[str, dict[str, dict[str, float]]] = {}
    total = sem = 0.0
    for mes in meses:
        am = f"{ano}{mes:02d}"
        arq = PASTA_EXECUCAO / f"{am}_Despesas.zip"
        if forcar:
            arq.unlink(missing_ok=True)
        try:
            _baixar(URL_EXECUCAO.format(am=am), arq, zip_=True)
        except Exception as e:  # mês ainda não publicado, ou CAPTCHA
            print(f"  {ano}/{mes:02d} fora: {e}", flush=True)
            continue

        comp = f"{ano}-{mes:02d}"
        porTipo = tipo_mes.setdefault(comp, {})
        porGrupo = grupo_mes.setdefault(comp, {})
        with zipfile.ZipFile(arq) as z:
            texto = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1", newline="")
            for l in csv.DictReader(texto, delimiter=";"):
                if l["Código Subfução"] in SUBFUNCOES_REFINANCIAMENTO:
                    continue
                vals = {k: _num(l[c]) for k, c in ETAPAS.items()}
                if not any(vals.values()):
                    continue
                total += vals["empenhado"]

                grupo = GRUPOS.get(l["Código Grupo de Despesa"], "outros")
                alvo = porGrupo.setdefault(grupo, dict.fromkeys(ETAPAS, 0.0))
                for k, v in vals.items():
                    alvo[k] += v

                tipos = por_chave.get(tuple(l[c] for c in CHAVE))
                if not tipos:
                    sem += vals["empenhado"]
                    fatias = {"sem": 1.0}
                else:
                    soma = sum(tipos.values())
                    # Dotação zerada (crédito só no meio do ano): fica com o tipo de maior dotação.
                    fatias = ({t: v / soma for t, v in tipos.items()} if soma > 0
                              else {max(tipos, key=lambda t: abs(tipos[t])): 1.0})
                for t, peso in fatias.items():
                    alvo = porTipo.setdefault(t, dict.fromkeys(ETAPAS, 0.0))
                    for k, v in vals.items():
                        alvo[k] += v * peso
        print(f"  {ano}/{mes:02d} ok", flush=True)
    return tipo_mes, grupo_mes, total, sem


def main() -> None:
    hoje = date.today()
    p = argparse.ArgumentParser(prog="fluxo", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int, nargs="?", default=hoje.year)
    p.add_argument("--meses", type=int, nargs="+", default=list(range(1, 13)))
    p.add_argument("--forcar", action="store_true", help="baixa os zips de novo")
    args = p.parse_args()

    print(f"resultado primário de {args.ano} (SIOP)…", flush=True)
    por_chave = tipos_por_chave(args.ano)

    print("meses:", flush=True)
    tipo_mes, grupo_mes, total, sem = somar(args.ano, sorted(args.meses), por_chave, args.forcar)
    if not tipo_mes:
        raise SystemExit("nenhum mês disponível")

    saida = SAIDA.with_name(SAIDA.name.format(ano=args.ano))
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({
        "ano": args.ano,
        "fonte": FONTE,
        "atualizado_em": hoje.isoformat(),
        "sem_refinanciamento": True,
        "observacao": ("'pago' é pagamento de empenho do próprio exercício; 'rap_pagos' é "
                       "desembolso de anos anteriores. As duas colunas somam-se, não se sobrepõem."),
        "tipos": TIPOS | {"sem": "Sem par no SIOP"},
        "por_tipo": tipo_mes,
        "por_grupo": grupo_mes,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    bi = 1e9
    print(f"\n{'mês':>8}  {'empenhado':>11}  {'liquidado':>11}  {'pago':>11}  "
          f"{'RAP inscr.':>11}  {'RAP pagos':>11}   (R$ bi, todos os tipos)")
    for comp in sorted(tipo_mes):
        s = {k: sum(t[k] for t in tipo_mes[comp].values()) for k in ETAPAS}
        print(f"{comp:>8}  {s['empenhado']/bi:>11.1f}  {s['liquidado']/bi:>11.1f}  "
              f"{s['pago']/bi:>11.1f}  {s['rap_inscritos']/bi:>11.1f}  {s['rap_pagos']/bi:>11.1f}")

    print(f"\n{'tipo':>22}  {'empenhado':>11}  {'pago':>11}  {'RAP pagos':>11}  {'conta velha':>12}")
    for t in ("obr", "esc", "eme", "fin", "sem"):
        s = {k: sum(m.get(t, {}).get(k, 0.0) for m in tipo_mes.values()) for k in ETAPAS}
        desembolso = s["pago"] + s["rap_pagos"]
        if not desembolso and not s["empenhado"]:
            continue
        velha = s["rap_pagos"] / desembolso if desembolso else 0.0
        print(f"{TIPOS.get(t, t)[:22]:>22}  {s['empenhado']/bi:>11.1f}  {s['pago']/bi:>11.1f}  "
              f"{s['rap_pagos']/bi:>11.1f}  {velha:>11.1%}")

    print(f"\n{'grupo':>14}  {'empenhado':>11}  {'pago':>11}  {'RAP pagos':>11}  {'conta velha':>12}")
    for g in list(GRUPOS.values()) + ["outros"]:
        s = {k: sum(m.get(g, {}).get(k, 0.0) for m in grupo_mes.values()) for k in ETAPAS}
        desembolso = s["pago"] + s["rap_pagos"]
        if not desembolso and not s["empenhado"]:
            continue
        velha = s["rap_pagos"] / desembolso if desembolso else 0.0
        print(f"{g:>14}  {s['empenhado']/bi:>11.1f}  {s['pago']/bi:>11.1f}  "
              f"{s['rap_pagos']/bi:>11.1f}  {velha:>11.1%}")

    print(f"\nsem par no SIOP: {sem/total:.2%} do empenhado" if total else "")
    print(f"saída: {saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
