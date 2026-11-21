"""Testes dos coletores do Ceará e do Espírito Santo, sem rede: a classificação dos credores e o CPF.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import unittest
from unittest import mock

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_ce as ce
from orcamento_pipeline import pagamentos_es as es
from orcamento_pipeline import pagamentos_qlik as pq

CNPJ_ENEL = "07047251000170"


def empenho_ce(numero: str, tipo: str, nome: str, doc: str, codigo: str, valor: float = 100.0) -> dict:
    return {"codigo_orgao": "02", "codigo_unidade_orcamentaria": "201 ", "data_emissao_empenho": "2025-03-10T00:00:00",
            "numero_empenho": numero, "codigo_tipo_negociante": tipo, "nome_negociante": nome,
            "numero_documento_negociante": doc, "codigo_elemento_despesa": codigo, "valor_empenhado": valor}


class TesteCeara(unittest.TestCase):
    def test_classificacao(self):
        linhas = [
            ce.linha(empenho_ce("1", "1", "ENEL", CNPJ_ENEL, "33903900"), 1000.0, set()),
            ce.linha(empenho_ce("2", "2", "FULANA DE TAL", "aB3dE5fG7hI9jK1lM3nO5p==", "33903600"), 200.0, set()),
            ce.linha(empenho_ce("3", "6", "FOLHA DE PAGAMENTO", "xYz12345abc+defGHIjk9==", "33904600"), 5000.0, set()),
            ce.linha(empenho_ce("4", "1", "INSTITUTO DE PREVIDENCIA", "12345678000195", "31911300"), 300.0, set()),
            # tipo 7: servidor com diárias. Os dígitos do código cifrado ("191") não podem virar o CNPJ do Banco do Brasil.
            ce.linha(empenho_ce("5", "7", "CICRANO SERVIDOR", "abc191defGHIjklMNOpqrs==", "33901400"), 40.0, set()),
        ]
        resumo, _ = pq.resumir(linhas)
        t = resumo["tipos"]
        self.assertEqual(t[pb.EMPRESA], 1000)
        self.assertEqual(t[pb.PESSOA], 240)
        self.assertEqual(t[pb.FOLHA], 5000)          # tipo 6: folha, mesmo fora do grupo de pessoal
        self.assertEqual(resumo["intra"], 300)       # modalidade 91 fica fora do total
        self.assertEqual(resumo["pago"], 6240)
        self.assertEqual(resumo["pessoas"], 2)
        self.assertEqual(resumo["credores"], [["ENEL", CNPJ_ENEL, 1000, 1]])
        texto = json.dumps(resumo)
        self.assertNotIn("FULANA", texto)
        self.assertNotIn("aB3dE5", texto)
        self.assertNotIn("CICRANO", texto)

    def test_consorcio_fica_fora(self):
        l = ce.linha(empenho_ce("9", "1", "ENEL", CNPJ_ENEL, "33903900"), 50.0, {("02", "201")})
        resumo, fora = pq.resumir([l])
        self.assertEqual((resumo["pago"], fora["consorcios"]), (0, 50.0))

    def test_para_se_as_paginas_se_sobrepoem(self):
        pagina = [{"codigo_orgao": "01", "codigo_unidade_orcamentaria": "101", "data_emissao_empenho": "x", "numero_empenho": str(i)} for i in range(3)]
        with mock.patch.object(ce, "obter", side_effect=[pagina + pagina[:1] * 997, []]):
            with self.assertRaises(RuntimeError):
                ce.todas("notas_empenhos", None, 0, codigo_municipio="002")


class TesteEspiritoSanto(unittest.TestCase):
    def empenho(self, nome, codigo, ident, grupo="3", modalidade="90", elemento="39", pago=100.0):
        return ["Prefeitura Municipal de Piúma", nome, codigo, ident, grupo, modalidade, elemento, pago, pago]

    def test_classificacao(self):
        linhas = [
            es.linha(("UG", "1"), self.empenho("ESCELSA", CNPJ_ENEL, "CNPJ", pago=1000.0)),
            es.linha(("UG", "2"), self.empenho("BELTRANO DA SILVA", "", "CPF", elemento="36", pago=200.0)),
            es.linha(("UG", "3"), self.empenho("DIVERSOS SERVIDORES", "12345", "IDENTIFICAÇÃO ESPECIAL", pago=4000.0)),
            es.linha(("UG", "4"), self.empenho("BANCO DO BRASIL S A", "00000000000191", "INSCRIÇÃO GENÉRICA - OUTROS", pago=50.0)),
            es.linha(("UG", "5"), self.empenho("FOLHA DE PAGAMENTO", "99999999999999", "INSCRIÇÃO GENÉRICA - OUTROS", grupo="1", elemento="11", pago=3000.0)),
        ]
        resumo, _ = pq.resumir(linhas)
        t = resumo["tipos"]
        self.assertEqual(t[pb.EMPRESA], 1000)
        self.assertEqual(t[pb.PESSOA], 200)
        self.assertEqual(t[pb.FOLHA], 7000)
        self.assertEqual(t[pb.DIVIDA], 50)
        self.assertEqual(resumo["pessoas"], 1)
        self.assertNotIn("BELTRANO", json.dumps(resumo))

    def test_consorcio_de_municipios_fica_fora(self):
        e = self.empenho("ESCELSA", CNPJ_ENEL, "CNPJ")
        e[0] = "Consórcio Público da Região Sul"
        resumo, fora = pq.resumir([es.linha(("UG", "1"), e)])
        self.assertEqual((resumo["pago"], fora["consorcios"]), (0, 100.0))


if __name__ == "__main__":
    unittest.main()
