"""Coletor de Minas Gerais (pagamentos_mg.py): leitura do pacote do SICOM e classificação dos credores."""

from __future__ import annotations

import io
import json
import unittest
import zipfile

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_mg as mg
from orcamento_pipeline import pagamentos_qlik as pq

CNPJ_CEMIG = "06981180000116"
CNPJ_PREFEITURA = "18715383000140"


def zip_do_municipio(empenhos, credores, fontes) -> zipfile.ZipFile:
    def csv(cab, linhas):
        return "\n".join([";".join(cab)] + [";".join(map(str, l)) for l in linhas])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2025.3106200.empenho.empenho.csv",
                   csv(["seq_empenho", "cod_orgao", "num_empenho", "dsc_naturezadespesa"], empenhos))
        z.writestr("2025.3106200.empenho.credorEmpenho.csv", csv(["seq_empenho", "num_doc_credor", "nom_credor"], credores))
        z.writestr("2025.3106200.empenho.empenhoFonte.csv", csv(
            ["seq_empenho", "vlr_empenho", "vlr_reforco_emp", "vlr_anulacao_emp", "vlr_pagamento", "vlr_anu_pagamento",
             "vlr_outras_baixas", "vlr_anu_outras_baixas"], fontes))
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


class TesteMinasGerais(unittest.TestCase):
    def test_pago_soma_meses_e_outras_baixas(self):
        z = zip_do_municipio(
            [[1, "02", 10, "3.3.90.39.99 - OUTROS SERVIÇOS"]],
            [[1, "06.981.180/0001-16", "CEMIG DISTRIBUICAO S.A."]],
            [[1, 1000, 0, 0, 0, 0, 0, 0],            # empenho em janeiro
             [1, 0, 200, 50, 700, 0, 100, 0],        # reforço e anulação; pago 700 + retenções 100
             [1, 0, 0, 0, 0, 20, 0, 5]],             # estorno de parte do pagamento e da retenção
        )
        e = mg.empenhos(z)["1"]
        self.assertEqual(e[5], 1150.0)               # empenhado: 1000 + 200 - 50
        self.assertEqual(e[6], 775.0)                # pago: 700 - 20 + 100 - 5

    def test_classificacao(self):
        linhas = [
            mg.linha("1", ["02", "1", "3.3.90.39.99 - X", CNPJ_CEMIG, "CEMIG DISTRIBUICAO S.A.", 1000.0, 1000.0]),
            mg.linha("2", ["02", "2", "3.3.90.36.00 - X", "***.456.789-**", "FULANO DE TAL", 200.0, 200.0]),
            mg.linha("3", ["02", "3", "3.1.90.11.01 - X", CNPJ_PREFEITURA, "PREFEITURA MUNICIPAL", 5000.0, 5000.0]),
            mg.linha("4", ["02", "4", "3.1.91.13.99 - X", CNPJ_PREFEITURA, "INSTITUTO DE PREVIDENCIA", 300.0, 300.0]),
            mg.linha("5", ["02", "5", "3.3.90.39.99 - X", "-1", "FOLHA DE PAGAMENTO DIVERSOS", 40.0, 40.0]),
        ]
        resumo, _ = pq.resumir(linhas)
        t = resumo["tipos"]
        self.assertEqual(t[pb.EMPRESA], 1000)
        self.assertEqual(t[pb.PESSOA], 200)
        self.assertEqual(t[pb.FOLHA], 5040)          # grupo 1 e, sem documento, o nome de folha
        self.assertEqual(resumo["intra"], 300)       # modalidade 91 fica fora do total
        self.assertEqual(resumo["pago"], 6240)
        self.assertEqual(resumo["pessoas"], 1)
        self.assertEqual(resumo["credores"], [["CEMIG DISTRIBUICAO S.A.", CNPJ_CEMIG, 1000, 1]])
        texto = json.dumps(resumo)
        self.assertNotIn("FULANO", texto)
        self.assertNotIn("456", texto)

    def test_cpf_sai_do_nome_do_mei(self):
        self.assertEqual(mg.limpar_nome("FULANA DE TAL CPF 123.456.789 - 00"), "FULANA DE TAL")
        self.assertEqual(mg.limpar_nome("12345678900 FULANA DE TAL"), "FULANA DE TAL")
        self.assertEqual(mg.limpar_nome("BPF INSTITUICAO DE PAGAMENTOS LTDA"), "BPF INSTITUICAO DE PAGAMENTOS LTDA")

    def test_trava_pega_cpf_com_espacos(self):
        from orcamento_pipeline import pagamentos_saida as ps
        self.assertTrue(ps.CPF_NO_NOME.search("FULANA CPF 123.456.789 - 00"))
        self.assertFalse(ps.CPF_NO_NOME.search("EMPRESA LTDA 2025"))

    def test_nome_do_pacote(self):
        m = mg.NOME_ZIP.search("SICOM.2025.3106200.empenho.zip")
        self.assertEqual(m.groups(), ("2025", "3106200"))


if __name__ == "__main__":
    unittest.main()
