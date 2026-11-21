"""Testes do coletor de Pernambuco (TCE-PE), sem rede: linhas no formato da API DespesasMunicipais.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import unittest

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_qlik as pq
from orcamento_pipeline import pagamentos_tcepe as pe


def empenho(n: int, **campos) -> dict:
    base = {
        "ID_UNIDADE_GESTORA": "269", "ID_EMPENHO": f"{n:08d}    ", "NOMEUNIDADEGESTORA": "Prefeitura Municipal de Ibimirim",
        "TIPOCREDOR": "2", "CPF_CNPJ": "10835932000108", "FORNECEDOR": "COMPANHIA ENERGETICA DE PERNAMBUCO",
        "NATUREZA": "Outras Despesas Correntes", "MODALIDADE": "Aplicações Diretas",
        "ELEMENTODESPESA": "Outros Serviços de Terceiros ? Pessoa Jurídica", "VALOREMPENHADO": "100.00", "VALORPAGO": "100.00",
    }
    return {**base, **campos}


class TestClassificacao(unittest.TestCase):
    def test_codigos_por_extenso(self):
        self.assertEqual(pe._codigo("Ap. Direta Decor. de Op. entre Órg., Fundos e Ent. Integ. dos Orçamentos Fiscal e da Seguridade Social", pe.MODALIDADES), "91")
        self.assertEqual(pe._codigo("Transferências a Instituições Privadas sem Fins Lucrativos", pe.MODALIDADES), "50")
        self.assertEqual(pe._codigo("Transferências a Consórcios Públicos", pe.MODALIDADES), "71")
        self.assertEqual(pe._codigo("Aplicações Diretas", pe.MODALIDADES), "90")
        self.assertEqual(pe._codigo("Obrigações Patronais", pe.ELEMENTOS), "13")
        self.assertEqual(pe._codigo("APOSENTADORIAS, RESERVA REMUNERADA E REFORMAS", pe.ELEMENTOS), "01")
        self.assertEqual(pe._codigo("Diárias - Civil", pe.ELEMENTOS), "14")
        self.assertEqual(pe._codigo("Outros Serviços de Terceiros ? Pessoa Física", pe.ELEMENTOS), "36")
        self.assertEqual(pe._codigo("Outros Auxílios Financeiros a Pessoas Físicas", pe.ELEMENTOS), "48")
        self.assertEqual(pe._codigo("Material de Consumo", pe.ELEMENTOS), "")

    def test_tipos(self):
        t = lambda **c: pq.tipo_do_credor(pe.linha(empenho(1, **c), set()))
        self.assertEqual(t(), pb.EMPRESA)
        self.assertEqual(t(TIPOCREDOR="1", CPF_CNPJ="***.***.594-97", FORNECEDOR="FULANO DE TAL", ELEMENTODESPESA="Diárias - Civil"), pb.PESSOA)
        self.assertEqual(t(NATUREZA="Pessoal e Encargos Sociais", ELEMENTODESPESA="Vencimentos e Vantagens Fixas - Pessoal Civil"), pb.FOLHA)
        self.assertEqual(t(NATUREZA="Pessoal e Encargos Sociais", ELEMENTODESPESA="Obrigações Patronais"), pb.PREVIDENCIA)
        self.assertEqual(t(TIPOCREDOR="3", FORNECEDOR="FOLHA"), pb.FOLHA)
        self.assertEqual(t(TIPOCREDOR="4", FORNECEDOR="", CPF_CNPJ=""), pb.ORGAO)
        self.assertEqual(t(NATUREZA="Amortização da Dívida"), pb.DIVIDA)
        self.assertEqual(t(FORNECEDOR="BANCO DO BRASIL SA", CPF_CNPJ="00000000000191"), pb.DIVIDA)


class TestResumo(unittest.TestCase):
    def test_resumo_sem_cpf(self):
        linhas = [
            empenho(1),
            empenho(2, VALORPAGO="50.00", CPF_CNPJ="10835932000299"),   # filial da mesma empresa
            empenho(3, TIPOCREDOR="1", CPF_CNPJ="***.***.594-97", FORNECEDOR="FULANO DE TAL", VALORPAGO="30.00"),
            empenho(4, TIPOCREDOR="1", CPF_CNPJ="***.***.594-97", FORNECEDOR="FULANO DE TAL", VALORPAGO="20.00"),
            empenho(5, TIPOCREDOR="1", CPF_CNPJ="***.***.111-22", FORNECEDOR="BELTRANA", VALORPAGO="10.00"),
            empenho(6, MODALIDADE="Ap. Direta Decor. de Op. entre Órg., Fundos e Ent. Integ.", VALORPAGO="7.00"),
            empenho(7, ID_UNIDADE_GESTORA="999", NOMEUNIDADEGESTORA="Agreste Saúde", VALORPAGO="1000.00"),
            empenho(8, VALORPAGO="0", VALOREMPENHADO="5.00"),
        ]
        resumo, fora = pq.resumir(pe.linha(l, {"999"}) for l in linhas)
        self.assertEqual(fora["consorcios"], 1000.0)      # unidade de consórcio fica de fora
        self.assertEqual(resumo["intra"], 7)
        self.assertEqual(resumo["pago"], 210)
        self.assertEqual(resumo["pessoas"], 2)            # Fulano (dois empenhos) e Beltrana
        self.assertEqual(resumo["empresas"], 1)
        self.assertEqual(resumo["credores"], [["COMPANHIA ENERGETICA DE PERNAMBUCO", "10835932000108", 150, 2]])
        texto = json.dumps(resumo, ensure_ascii=False)
        self.assertNotIn("594", texto)
        self.assertNotIn("FULANO", texto)
        self.assertNotIn("BELTRANA", texto)


if __name__ == "__main__":
    unittest.main()
