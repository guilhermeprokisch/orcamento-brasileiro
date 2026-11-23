"""Mínimo em saúde e em educação (minimos.py): o que fica do Anexo 14 e como vira o registro de cada ente."""

from __future__ import annotations

import unittest

from orcamento_pipeline import minimos as m

SAUDE = "AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude"
EDUCACAO = "MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado"


def linha(conta: str, coluna: str, valor) -> dict:
    return {"cod_conta": conta, "coluna": coluna, "valor": valor, "conta": "…", "populacao": 1, "anexo": "RREO-Anexo 14"}


class Minimos(unittest.TestCase):
    def test_filtro_guarda_so_os_percentuais(self):
        itens = [
            linha(SAUDE, "Valor Apurado Até o Bimestre", 19751075346.31),
            linha(SAUDE, m.MINIMO, 15),
            linha(SAUDE, m.APLICADO, 23.85),
            linha(EDUCACAO, m.APLICADO, 25.17),
            linha("ResultadoPrimarioAcimaDaLinhaSemRPPSDemonstrativoSimplificado", "% em Relação à Meta (b/a)", 2.57),
        ]
        guardado = m.filtro(itens)
        self.assertEqual(len(guardado), 3)
        self.assertEqual(set(guardado[0]), {"cod_conta", "coluna", "valor"})

    def test_resumir(self):
        itens = m.filtro([linha(SAUDE, m.APLICADO, 23.85), linha(SAUDE, m.MINIMO, 15),
                          linha(EDUCACAO, m.APLICADO, 25.17), linha(EDUCACAO, m.MINIMO, 25)])
        self.assertEqual(m.resumir(itens), [23.85, 15, 25.17, 25])

    def test_sem_as_linhas_nao_ha_registro(self):
        # Guarulhos, Campinas e outras: o Anexo 14 vem sem as linhas de saúde e de educação.
        self.assertIsNone(m.resumir([]))

    def test_falta_uma_area(self):
        self.assertEqual(m.resumir(m.filtro([linha(EDUCACAO, m.APLICADO, 32.39)])), [None, None, 32.39, None])


if __name__ == "__main__":
    unittest.main()
