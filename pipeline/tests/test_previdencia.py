"""Fundo de aposentadoria dos servidores (previdencia.py): leitura da planilha do ISP e código do IBGE pelo nome."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import openpyxl

from orcamento_pipeline import previdencia as pv

TITULO = ["Índice de Situação Previdenciária 2025"]


def planilha(destino: Path, cobertura_total="PROVISÕES MATEMÁTICAS PREVIDENCIÁRIAS \nVALOR TOTAL", prefixo="") -> Path:
    """Um ISP de mentira com as cinco abas que o programa lê, no formato da planilha de 2025."""
    livro = openpyxl.Workbook()
    livro.remove(livro.active)

    def aba(nome, cabecalho, linhas):
        ws = livro.create_sheet(prefixo + nome)
        ws.append(TITULO)
        ws.append([])
        ws.append(cabecalho)
        for l in linhas:
            ws.append(l)

    aba("RESULTADO", ["ENTE", "CNPJ", "UF", "GRUPO", "SUBGRUPO", "INDICADOR DE SITUAÇÃO PREVIDENCIÁRIA", "PERFIL ATUARIAL", "CAPITAL"], [
        ["ABADIA DE GOIÁS - GO", 1, "GO", "MÉDIO PORTE", "MENOR MATURIDADE", "C", "II", "N"],
        ["GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS", 2, "RS", "ESTADO/DF", "ESTADO/DF", "B", "III", "N"],
        ["MAJOR IZIDORO - AL", 3, "AL", "PEQUENO PORTE", "MENOR MATURIDADE", "D", "I", "N"],
    ])
    aba("COBERTURA", ["ENTE", "UF", "GRUPO", "SUBGRUPO", "ATIVOS DAIR 12/2024", "ANO DRAA",
                      "PROVISÃO BENEFÍCIOS CONCEDIDOS PLANO FINANCEIRO - DRAA 2025", "PROVISÃO BENEFÍCIOS A CONCEDER PLANO FINANCEIRO - DRAA 2025",
                      "PROVISÃO BENEFÍCIOS CONCEDIDOS MANTIDOS PELO TESOURO - DRAA 2025", "PROVISÃO BENEFÍCIOS A CONCEDER MANTIDOS PELO TESOURO - DRAA 2025",
                      "PROVISÃO BENEFÍCIOS CONCEDIDOS PLANO PREVIDENCIÁRIO - DRAA 2025", "PROVISÃO BENEFÍCIOS A CONCEDER PLANO PREVIDENCIÁRIO - DRAA 2025",
                      cobertura_total], [
        ["ABADIA DE GOIÁS - GO", "GO", "", "", 44.0, 2025, "-", "-", "-", "-", "-", "-", "-"],
        ["GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS", "RS", "", "", 5.0, 2025, 90.0, 20.0, 0, 0, 1.0, -0.5, 110.5],
        ["MAJOR IZIDORO - AL", "AL", "", "", 1.0, 2025, 0, 0, 0, 0, 6.0, 4.0, 10.0],
    ])
    aba("GRUPOS", ["ENTE", "UF", "GRUPO", "SUBGRUPO", "FONTE", "SEGURADOS ATIVOS", "APOSENTADOS", "PENSIONISTAS"], [
        ["ABADIA DE GOIÁS - GO", "GO", "", "", "DIPR", 467, 47, 7],
        ["GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS", "RS", "", "", "DRAA", 71136, 145739, 32069],
    ])
    aba("SUFICIÊNCIA (NOVO)", ["ENTE", "UF", "GRUPO", "SUBGRUPO", "RECEITA \nCONSIDERADA", "DESPESA CONSIDERADA"], [
        ["ABADIA DE GOIÁS - GO", "GO", "", "", 11.5, 2.7],
    ])
    aba("SUSTENTABILIDADE", ["ENTE", "UF", "GRUPO", "SUBGRUPO", "PROVISÕES MATEMÁTICAS PREVIDENCIÁRIAS", "RECEITA CORRENTE LIQUIDA\n60%"], [
        ["GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS", "RS", "", "", 110.5, 36.0],
    ])
    livro.save(destino)
    return destino


class LerIsp(unittest.TestCase):
    def setUp(self) -> None:
        self.pasta = Path(tempfile.mkdtemp())

    def test_le_as_abas(self) -> None:
        entes, ano = pv.ler_isp(planilha(self.pasta / "isp.xlsx"))
        self.assertEqual(ano, 2025)
        rs = entes["GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS"]
        self.assertTrue(rs["estado"])
        self.assertEqual(rs["nota"], "B")
        self.assertEqual((rs["provisoes"], rs["aplicado"], rs["financeiro"]), (110.5, 5.0, 110.0))
        self.assertAlmostEqual(rs["rcl"], 60.0)   # a planilha traz 60% da receita corrente líquida
        self.assertEqual((rs["ativos"], rs["aposentados"], rs["pensionistas"]), (71136, 145739, 32069))
        # Sem avaliação atuarial: provisões e ano ficam vazios, o resto continua.
        abadia = entes["ABADIA DE GOIÁS - GO"]
        self.assertIsNone(abadia["provisoes"])
        self.assertIsNone(abadia["ano_draa"])
        self.assertEqual((abadia["receita"], abadia["despesa"]), (11.5, 2.7))

    def test_planilha_de_2024(self) -> None:
        """O ISP 2024 tem outro título para o total e abas numeradas ("09 COBERTURA")."""
        arq = planilha(self.pasta / "isp2024.xlsx", cobertura_total="PROVISÃO MATEMÁTICA TOTAL AJUSTADA", prefixo="09 ")
        cob = pv.ler_cobertura(openpyxl.load_workbook(arq, read_only=True, data_only=True))
        self.assertEqual(cob["MAJOR IZIDORO - AL"]["provisoes"], 10.0)


class Codigo(unittest.TestCase):
    INDICE = {("GO", "abadiadegoias"): 5200050, ("AL", "majorisidoro"): 2704906}

    def test_estado_pela_uf(self) -> None:
        self.assertEqual(pv.codigo("GOVERNO DO ESTADO DO RIO GRANDE DO SUL - RS", True, self.INDICE), 43)
        self.assertEqual(pv.codigo("GOVERNO DO DISTRITO FEDERAL - DF", True, self.INDICE), 53)

    def test_prefeitura_pelo_nome(self) -> None:
        self.assertEqual(pv.codigo("ABADIA DE GOIÁS - GO", False, self.INDICE), 5200050)
        # Grafia diferente da do IBGE: vai pela lista de apelidos.
        self.assertEqual(pv.codigo("MAJOR IZIDORO - AL", False, self.INDICE), 2704906)
        self.assertIsNone(pv.codigo("ABADIA DE GOIÁS - MG", False, self.INDICE))

    def test_ano_do_arquivo(self) -> None:
        self.assertEqual(pv.ano_isp_de("https://x/arquivos/resultado-final-isp-2025-_-publicado-em-04_12_2025-1.xlsx"), 2025)
        self.assertEqual(pv.ano_isp_de("ISP_2024_resultado_final_Revisado_29_11_2024.xlsx"), 2024)


if __name__ == "__main__":
    unittest.main()
