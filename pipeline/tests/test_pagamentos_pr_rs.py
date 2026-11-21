"""Coletores do Paraná (pagamentos_pr.py) e do Rio Grande do Sul (pagamentos_rs.py): leitura e classificação dos credores."""

from __future__ import annotations

import io
import json
import unittest
import zipfile

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_pr as pr
from orcamento_pipeline import pagamentos_qlik as pq
from orcamento_pipeline import pagamentos_rs as rs

CNPJ_COPEL = "04368898000106"
CNPJ_PREFEITURA = "76417005000186"


def xml(tabela: str, registros: list[dict]) -> str:
    corpo = "".join(f"<{tabela} " + " ".join(f'{k}="{v}"' for k, v in r.items()) + "/>" for r in registros)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<root>{corpo}</root>'


def empenho(id_, entidade="MUNICÍPIO DE TESTE", ano="2025", doc=("CNPJ", CNPJ_COPEL), nome="COPEL DISTRIBUICAO S.A.",
            natureza=("3", "90", "39")):
    return {"idEmpenho": id_, "nrAnoEmpenho": ano, "nmEntidade": entidade, "sgDocCredor": doc[0].ljust(12),
            "nrDocCredor": doc[1], "nmCredor": nome, "cdGrupoNatureza": natureza[0], "cdModalidade": natureza[1],
            "cdElemento": natureza[2], "vlEmpenho": "1000.00"}


def zip_pr(empenhos, pagamentos, estornos) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2025_410000_Empenho.xml", xml("Empenho", empenhos))
        # O pagamento vem em duas partes, como o de Curitiba; um histórico traz um caractere de controle.
        z.writestr("2025_410000_EmpenhoPagamento_1.xml", xml("EmpenhoPagamento", pagamentos[:1]).replace('vlOperacao=', 'dsHistorico="A&#x1;B" vlOperacao=', 1))
        z.writestr("2025_410000_EmpenhoPagamento_2.xml", xml("EmpenhoPagamento", pagamentos[1:]))
        z.writestr("2025_410000_EmpenhoPagamentoEstorno.xml", xml("EmpenhoPagamentoEstorno", estornos))
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


class TesteParana(unittest.TestCase):
    def test_pago_do_ano_menos_estornos(self):
        z = zip_pr(
            [empenho("1"), empenho("2", entidade="CONSÓRCIO INTERMUNICIPAL DE SAÚDE"), empenho("9", ano="2024"),
             empenho("3", entidade="ASSOCIAÇÃO INTERMUNICIPAL DE SAÚDE DO CENTRO OESTE DO PARANÁ")],
            [{"idEmpenho": "1", "vlOperacao": "700.00", "dtOperacao": "2025-03-01T00:00:00", "vlPagamentoBruto": "BANCO"},
             {"idEmpenho": "1", "vlOperacao": "200.00", "dtOperacao": "2026-01-10T00:00:00"},    # ano seguinte: fora
             {"idEmpenho": "2", "vlOperacao": "50.00", "dtOperacao": "2025-03-01T00:00:00"},     # consórcio: fora
             {"idEmpenho": "3", "vlOperacao": "5.00", "dtOperacao": "2025-03-01T00:00:00"},      # associação de municípios: fora
             {"idEmpenho": "8", "vlOperacao": "30.00", "dtOperacao": "2025-03-01T00:00:00"}],    # restos a pagar: fora
            [{"idEmpenho": "1", "vlEstorno": "100.00", "dtEstorno": "2025-04-01T00:00:00"}],
        )
        emp, fora = pr.empenhos(z, 2025)
        self.assertEqual(list(emp), ["1"])
        self.assertEqual(emp["1"][8], 600.0)
        self.assertEqual(fora, {"pago no ano seguinte": 200.0, "consórcios": 55.0, "restos a pagar": 30.0})

    def test_classificacao(self):
        brutos = {
            "1": ["M", "3", "90", "39", "CNPJ", CNPJ_COPEL, "COPEL DISTRIBUICAO S.A.", 1000.0, 1000.0],
            "2": ["M", "3", "90", "36", "CPF", "***.456.789-**", "FULANO DE TAL", 200.0, 200.0],
            "3": ["M", "3", "90", "39", "CNPJ", CNPJ_COPEL, "FULANA DE TAL 123.456.789-09", 50.0, 50.0],   # MEI: pessoa
            "4": ["M", "1", "90", "11", "CNPJ", CNPJ_PREFEITURA, "MUNICIPIO DE TESTE", 5000.0, 5000.0],
            "5": ["M", "3", "91", "13", "CNPJ", CNPJ_PREFEITURA, "INSTITUTO DE PREVIDENCIA", 300.0, 300.0],
        }
        resumo, _ = pq.resumir(pr.linha(k, e) for k, e in brutos.items())
        t = resumo["tipos"]
        self.assertEqual(t[pb.EMPRESA], 1000)
        self.assertEqual(t[pb.PESSOA], 250)
        self.assertEqual(t[pb.FOLHA], 5000)
        self.assertEqual(resumo["intra"], 300)
        self.assertEqual(resumo["pessoas"], 2)
        self.assertEqual(resumo["credores"], [["COPEL DISTRIBUICAO S.A.", CNPJ_COPEL, 1000, 1]])
        texto = json.dumps(resumo)
        for proibido in ("FULAN", "456", "789"):
            self.assertNotIn(proibido, texto)

    def test_nome_do_pacote(self):
        self.assertEqual(pr.NOME_ZIP.match("2025_410690_Despesa.zip").groups(), ("2025", "410690"))
        self.assertIsNone(pr.NOME_ZIP.match("2025_410690_Receita.zip"))


CAB = ["cd_orgao", "nome_orgao", "tipo_operacao", "ano_empenho", "dt_operacao", "nr_empenho", "cd_elemento", "tp_pessoa",
       "cnpj_cpf", "nm_credor", "vl_empenho", "vl_pagamento"]


def op(orgao, tipo, ano, dt, nr, ve="", vp="", elemento="3.3.90.39", tp="PJ", doc=CNPJ_COPEL, nome="RGE SUL S.A."):
    return [orgao, f"PM {orgao}", tipo, ano, dt, nr, elemento, tp, doc, nome, ve, vp]


class TesteRioGrandeDoSul(unittest.TestCase):
    def test_soma_por_orgao(self):
        linhas = [CAB,
                  op("40100", "E", "2025", "2025-01-05", "1", ve="1000.00"),
                  op("40100", "L", "2025", "2025-02-01", "1"),
                  op("40100", "P", "2025", "2025-02-10", "1", vp="800.00"),
                  op("40100", "P", "2025", "2025-03-10", "1", vp="-100.00"),    # estorno
                  op("40100", "P", "2025", "2026-01-10", "1", vp="50.00"),      # pago no ano seguinte: fora
                  op("40100", "P", "2024", "2025-02-10", "7", vp="40.00"),      # restos a pagar: fora
                  op("40101", "E", "2025", "2025-01-05", "1", ve="10.00"),
                  op("40101", "P", "2025", "2025-01-06", "1", vp="10.00")]
        orgaos = list(rs.orgaos_do_arquivo(linhas, 2025))
        self.assertEqual([o[0] for o in orgaos], ["40100", "40101"])
        cd, nome, emp, restos = orgaos[0]
        self.assertEqual(emp["1"][4:], [1000.0, 700.0])
        self.assertEqual(restos, 40.0)

    def test_orgao_em_dois_trechos_para_a_carga(self):
        linhas = [CAB, op("1", "E", "2025", "2025-01-01", "1"), op("2", "E", "2025", "2025-01-01", "1"),
                  op("1", "E", "2025", "2025-01-01", "2")]
        with self.assertRaises(SystemExit):
            list(rs.orgaos_do_arquivo(linhas, 2025))

    def test_classificacao_e_cpf(self):
        brutos = [
            ["3.3.90.39", "PJ", CNPJ_COPEL, "RGE SUL DISTRIBUIDORA DE ENERGIA S.A.", 1000.0, 1000.0],
            ["3.3.90.36", "PF", "12345678909", "FULANO DE TAL", 200.0, 200.0],
            ["3.3.90.36", "PF", "12345678909", "FULANO DE TAL", 100.0, 100.0],   # a mesma pessoa
            ["3.1.90.11", "PJ", CNPJ_PREFEITURA, "PREFEITURA MUNICIPAL", 5000.0, 5000.0],
            ["3.3.91.13", "PJ", CNPJ_PREFEITURA, "PREVIMPA", 300.0, 300.0],
        ]
        resumo, _ = pq.resumir(rs.linha(str(i), "PM DE TESTE", e) for i, e in enumerate(brutos))
        t = resumo["tipos"]
        self.assertEqual(t[pb.EMPRESA], 1000)
        self.assertEqual(t[pb.PESSOA], 300)
        self.assertEqual(t[pb.FOLHA], 5000)
        self.assertEqual(resumo["intra"], 300)
        self.assertEqual(resumo["pessoas"], 1)
        self.assertEqual(resumo["n"], 4)
        texto = json.dumps(resumo)
        self.assertNotIn("12345678909", texto)
        self.assertNotIn("FULANO", texto)

    def test_resumo_aos_poucos_igual_ao_de_uma_vez(self):
        linhas = [rs.linha(str(i), "PM", ["3.3.90.39", "PJ", CNPJ_COPEL, "RGE", 10.0 * i, 10.0 * i]) for i in range(1, 4)]
        r = pq.Resumo()
        for l in linhas:
            r.somar(l)
        self.assertEqual(r.fechar(), pq.resumir(linhas)[0])


if __name__ == "__main__":
    unittest.main()
