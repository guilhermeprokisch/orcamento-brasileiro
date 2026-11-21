"""Testes dos coletores do Amazonas (TCE-AM) e do Tocantins (TCE-TO), sem rede.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import unittest
from collections import Counter
from unittest import mock

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_am as am
from orcamento_pipeline import pagamentos_qlik as pq
from orcamento_pipeline import pagamentos_to as to

EMPRESA = "35992959000135"   # CNPJ válido
CPF = "52998224725"          # CPF válido de exemplo (não é de ninguém)


def pagamento_am(id_pag: int, id_emp: int, valor: float, **campos) -> dict:
    base = {
        "idPagamentoEmpenho": id_pag, "idEmpenho": id_emp, "idUnidadeGestora": 395, "exercicio": 2025,
        "dtEmpenho": "2025-03-20T04:00:00.000+00:00", "nomeUnidadeGestora": "Prefeitura Municipal de Tabatinga",
        "cnpjCnpjCredor": EMPRESA, "nomCredor": "POSTO DE COMBUSTIVEL LTDA", "codTipoPessoa": 2,
        "codGrupoNatureza": 3, "codModalidadeAplicacao": 90, "codElementoDespesa": 30, "vlPagamentoEmpenho": valor,
    }
    return {**base, **campos}


class TestAmazonas(unittest.TestCase):
    def test_soma_por_empenho(self):
        empenhos, fora = {}, Counter()
        am.somar(empenhos, [pagamento_am(1, 10, 100.0), pagamento_am(2, 10, 50.0), pagamento_am(3, 11, 30.0)], 2025, fora)
        am.somar(empenhos, [pagamento_am(4, 10, 25.0)], 2025, fora)   # outro mês, mesmo empenho
        self.assertEqual(sorted((k, e.pago) for k, e in empenhos.items()), [("395/10", 175.0), ("395/11", 30.0)])
        resumo, _ = pq.resumir(empenhos.values())
        self.assertEqual((resumo["pago"], resumo["n"], resumo["empresas"]), (205, 2, 1))
        self.assertEqual(resumo["credores"][0][:3], ["POSTO DE COMBUSTIVEL LTDA", EMPRESA, 205])

    def test_conta_de_folha_fora_do_grupo_de_pessoal(self):
        empenhos, fora = {}, Counter()
        am.somar(empenhos, [pagamento_am(1, 10, 90.0, nomCredor="FOPAG - PRESTADOR DE SERVIÇOS SUS"),
                            pagamento_am(2, 11, 10.0, nomCredor="Folha de Pagamento - Diaristas")], 2025, fora)
        resumo, _ = pq.resumir(empenhos.values())
        self.assertEqual((resumo["tipos"][pb.FOLHA], resumo["credores"]), (100, []))

    def test_restos_ficam_fora(self):
        empenhos, fora = {}, Counter()
        am.somar(empenhos, [pagamento_am(1, 10, 100.0, dtEmpenho="2024-12-10T04:00:00.000+00:00")], 2025, fora)
        self.assertEqual((empenhos, fora["outro_ano"]), ({}, 100.0))

    def test_pessoa_fisica_sem_cpf_nem_nome(self):
        empenhos, fora = {}, Counter()
        am.somar(empenhos, [pagamento_am(1, 10, 80.0, cnpjCnpjCredor="000" + CPF, nomCredor="FULANO DE TAL", codTipoPessoa=1,
                                         codElementoDespesa=36),
                            pagamento_am(2, 11, 20.0, codGrupoNatureza=1, codElementoDespesa=11, nomCredor="FOPAG - SAUDE")], 2025, fora)
        resumo, _ = pq.resumir(empenhos.values())
        self.assertEqual((resumo["pessoas"], resumo["tipos"][pb.PESSOA], resumo["tipos"][pb.FOLHA]), (1, 80, 20))
        texto = json.dumps(resumo, ensure_ascii=False)
        self.assertNotIn(CPF, texto)
        self.assertNotIn("FULANO", texto)
        self.assertEqual(resumo["credores"], [])


def celulas(*valores: str) -> str:
    return "<tr>" + "".join(f"<td class=\"\" style=\"color:\">{v}'</td>" for v in valores) + "</tr>"


EMPENHO_CAB = ["Unidade Gestora", "Exercício", "Rubrica", "IdCredor", "Nome Credor", "Número Empenho", "Data", "Valor", "Sinal"]
PAGAMENTO_CAB = ["Uni. Gestora", "Exercício", "Rúbrica", "Número Empenho", "Número Pagamento", "Data", "Sinal", "Valor"]
UG = "37425451000180 - PREFEITURA MUNICIPAL DE ABREULÂNDIA"
CAMARA = "00495571000144 - CÂMARA MUNICIPAL DE ABREULÂNDIA"


def tabela(cabecalho: list[str], linhas: list[tuple]) -> bytes:
    cab = "<tr>" + "".join(f"<td><strong>{c}</strong></td>" for c in cabecalho) + "</tr>"
    return ("<table>" + cab + "".join(celulas(*l) for l in linhas) + "</table>").encode("latin-1")


class TestTocantins(unittest.TestCase):
    def planilhas(self):
        empenhos = tabela(EMPENHO_CAB, [
            (UG, "2025", "3390300101000000", EMPRESA, "SOUZA E MAGALHAES COMERCIO DE COMBUSTIVEIS LTDA", "2025000000001", "02/01/2025", "1.000,00", "+"),
            (UG, "2025", "3390300101000000", EMPRESA, "SOUZA E MAGALHAES COMERCIO DE COMBUSTIVEIS LTDA", "2025000000001", "02/06/2025", "100,00", "-"),
            (UG, "2025", "3390300101000000", EMPRESA, "SOUZA E MAGALHAES COMERCIO DE COMBUSTIVEIS LTDA", "2025000000001", "02/07/2025", "50,00", "E"),
            (UG, "2025", "3390360100000000", CPF, f"FULANO DE TAL {CPF}", "2025000000002", "03/01/2025", "500,00", "+"),
            (CAMARA, "2025", "3391130100000000", EMPRESA, "FUNDO DE PREVIDENCIA", "2025000000001", "03/01/2025", "70,00", "+"),
        ])
        pagamentos = tabela(PAGAMENTO_CAB, [
            (UG, "2025", "3390300101000000", "2025000000001", "1", "10/01/2025", "+", "600,00"),
            (UG, "2025", "3390300101000000", "2025000000001", "2", "10/02/2025", "+", "300,00"),
            (UG, "2025", "3390300101000000", "2025000000001", "3", "11/02/2025", "-", "100,00"),
            (UG, "2025", "3390360100000000", "2025000000002", "4", "10/01/2025", "+", "500,00"),
            (CAMARA, "2025", "3391130100000000", "2025000000001", "5", "10/01/2025", "+", "70,00"),   # mesmo número, outra unidade
        ])
        return lambda url, **_: empenhos if "empenho.php" in url else pagamentos

    def test_le_e_junta_pelo_empenho(self):
        with mock.patch.object(to, "baixar", side_effect=self.planilhas()):
            resumo, fora, unidades = to.ler_municipio("37425451000180", 2025)
        self.assertEqual(unidades, {"37425451000180", "00495571000144"})
        self.assertEqual((resumo["pago"], resumo["intra"], resumo["empenhado"]), (1300, 70, 1450))
        self.assertEqual((resumo["tipos"][pb.EMPRESA], resumo["tipos"][pb.PESSOA], resumo["pessoas"]), (800, 500, 1))
        self.assertEqual(resumo["credores"][0][:3], ["SOUZA E MAGALHAES COMERCIO DE COMBUSTIVEIS LTDA", EMPRESA, 800])
        self.assertNotIn(CPF, json.dumps(resumo))
        self.assertEqual(fora["n_sem_empenho"], 0)

    def test_cabecalho_mudou(self):
        ruim = tabela(["Unidade", "Valor"], [("x", "1,00")])
        with mock.patch.object(to, "baixar", return_value=ruim), self.assertRaises(SystemExit):
            list(to.planilha("empenho", "1", 2025))

    def test_principal(self):
        lista = [{"id": "1", "nome": "UNIDADE SUPERVISIONADA", "unidadePrincipal": "1"},
                 {"id": "2", "nome": "PREFEITURA MUNICIPAL", "unidadePrincipal": "1"},
                 {"id": "3", "nome": "CÂMARA MUNICIPAL", "unidadePrincipal": "0"}]
        self.assertEqual(to.principal(lista)["id"], "2")


if __name__ == "__main__":
    unittest.main()
