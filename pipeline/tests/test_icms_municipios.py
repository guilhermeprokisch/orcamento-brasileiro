"""Testes do ICMS por município (icms_municipios.py), sem rede: leitura da Tabela 1.10 da SEFAZ-SP.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import openpyxl

from orcamento_pipeline import icms_municipios as m


# Códigos IBGE dos municípios usados no teste (batem com site/public/data/mapa/nomes.json).
CUBATAO = "3513504"
SAO_PAULO = "3550308"


def planilha(linhas: list[tuple], ano: int = 2024) -> Path:
    """Escreve uma aba no formato da SEFAZ-SP (cabeçalho na linha 11, dados a partir da 12) e devolve o caminho."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"ArrecMunic-ICMS-{ano}"
    ws.append(["TABELA 1.10"])
    for _ in range(3):
        ws.append([None])
    ws.append(["Valores nominais em reais mil"])
    for _ in range(4):
        ws.append([None])
    ws.append(["ICMS - Região", "Município"] + [f"mes{i}" for i in range(1, 13)])  # linha 11
    for linha in linhas:
        ws.append(list(linha))
    arq = Path(tempfile.mkdtemp()) / "tab110.xlsx"
    wb.save(arq)
    return arq


class LerSP(unittest.TestCase):
    def test_soma_meses_e_converte_de_mil_para_reais(self):
        # Região só na primeira linha do bloco; 12 meses de 100 mil -> 1,2 milhão de reais.
        arq = planilha([
            ("DT-02 - LITORAL", "CUBATAO") + (100.0,) * 12,
            (None, "SAO PAULO") + (200.0,) * 12,
        ])
        dados = m.ler_sp(arq)
        self.assertEqual(dados[2024][CUBATAO], 100.0 * 12 * 1000)     # 1,2 mi de reais
        self.assertEqual(dados[2024][SAO_PAULO], 200.0 * 12 * 1000)   # 2,4 mi de reais

    def test_ignora_totais_nao_classificado_e_outros_estados(self):
        arq = planilha([
            ("DT-02 - LITORAL", "CUBATAO") + (10.0,) * 12,
            (None, "Total:") + (9999.0,) * 12,
            (None, "Não Classificado") + (9999.0,) * 12,
            (None, "Outros Estados") + (9999.0,) * 12,
        ])
        dados = m.ler_sp(arq)
        self.assertEqual(set(dados[2024]), {CUBATAO})

    def test_mes_com_sigilo_deixa_cidade_sem_valor_oficial(self):
        # Sigilo fiscal: um mês "******" torna o total do ano incompleto; a cidade fica de fora
        # (o mapa volta à estimativa) em vez de publicar um número subestimado.
        arq = planilha([
            ("DT-02 - LITORAL", "CUBATAO", 50.0, "******") + (50.0,) * 10,   # 11 meses numéricos
            (None, "SAO PAULO") + (50.0,) * 12,                              # 12 meses: fica
        ])
        dados = m.ler_sp(arq)
        self.assertNotIn(CUBATAO, dados[2024])
        self.assertEqual(dados[2024][SAO_PAULO], 50.0 * 12 * 1000)

    def test_anos_anteriores_a_2013_ficam_de_fora(self):
        arq = planilha([("DT-02 - LITORAL", "CUBATAO") + (10.0,) * 12], ano=2012)
        self.assertNotIn(2012, m.ler_sp(arq))


if __name__ == "__main__":
    unittest.main()
