"""Leitura de dois anexos da DCA: despesa por natureza (I-D) e balanço patrimonial (I-AB).

Respondem "com o quê o governo gasta" e "quanto tem em caixa e quanto deve". As contas são
achadas pelo nome: os códigos têm um zero a mais ou a menos conforme o ano.
"""

from __future__ import annotations

from .cidades import COL_EMPENHADO, _so_letras

# Ordem dos valores devolvidos (e gravados em site/public/data/mapa/contas/{ano}.json).
NATUREZA = ["pessoal", "juros", "custeio", "investimentos", "inversoes", "amortizacao",
            "rp_processados", "rp_nao_processados"]
BALANCO = ["caixa", "ativo_financeiro", "passivo_financeiro", "emprestimos_curto", "emprestimos_longo",
           "provisoes_longo", "passivo_circulante", "passivo_nao_circulante"]

GRUPOS = {  # nome da conta (só letras) -> campo
    "pessoaleencargossociais": "pessoal",
    "juroseencargosdadivida": "juros",
    "outrasdespesascorrentes": "custeio",
    "investimentos": "investimentos",
    "inversoesfinanceiras": "inversoes",
    "amortizacaodadivida": "amortizacao",
}
CONTAS_BALANCO = {
    "caixaeequivalentesdecaixa": "caixa",
    "ativofinanceiro": "ativo_financeiro",
    "passivofinanceiro": "passivo_financeiro",
    "emprestimosefinanciamentosacurtoprazo": "emprestimos_curto",
    "emprestimosefinanciamentosalongoprazo": "emprestimos_longo",
    "provisoesalongoprazo": "provisoes_longo",
    "passivocirculante": "passivo_circulante",
    "passivonaocirculante": "passivo_nao_circulante",
}


def _nome(conta: str) -> str:
    conta = " ".join((conta or "").split())
    if conta[:1].isdigit():
        conta = conta.partition(" ")[2].lstrip("- ")
    return _so_letras(conta)


def natureza(itens: list[dict]) -> list[int] | None:
    """Despesa empenhada por grupo e restos a pagar inscritos no ano (valores de `NATUREZA`)."""
    v = dict.fromkeys(NATUREZA, 0.0)
    achou = False
    for i in itens:
        nome, col, valor = _nome(i["conta"]), i["coluna"], float(i["valor"] or 0)
        if col == COL_EMPENHADO and nome in GRUPOS:
            v[GRUPOS[nome]] = max(v[GRUPOS[nome]], valor)
            achou = True
        elif nome == "totalgeraldadespesa" and col.startswith("Inscrição de R"):
            # "Inscrição de Restos a Pagar (Não) Processados" ou, até ~2017, "Inscrição de RP (Não) Processados"
            v["rp_nao_processados" if "Não" in col else "rp_processados"] = valor
    return [round(v[k]) for k in NATUREZA] if achou else None


def balanco(itens: list[dict]) -> list[int] | None:
    """Saldos do balanço patrimonial em 31/12 (valores de `BALANCO`)."""
    v: dict[str, float] = {}
    for i in itens:
        campo = CONTAS_BALANCO.get(_nome(i["conta"]))
        if campo:
            valor = float(i["valor"] or 0)
            # a mesma conta aparece no quadro principal e em sub-quadros: fica o maior valor
            if campo not in v or abs(valor) > abs(v[campo]):
                v[campo] = valor
    return [round(v.get(k, 0.0)) for k in BALANCO] if v else None
