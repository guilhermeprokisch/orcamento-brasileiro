"""Testes do resumo de São Paulo (TCE-SP e TCM-SP), com arquivos pequenos de mentira.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from orcamento_pipeline import pagamentos as pb
from orcamento_pipeline import pagamentos_sp as sp

CNPJ = "11222333000181"       # CNPJ válido (exemplo da Receita)
CNPJ_FILIAL = "11222333000262"
CPF = "52998224725"           # CPF válido (exemplo), nunca pode chegar ao resumo


def tcm(linhas: list[dict]) -> Path:
    """Um CSV como o do TCM-SP: 54 colunas, em CP850, cabeçalho com os acentos estragados."""
    cab = ["Id Empenho"] + [f"c{i}" for i in range(1, 54)]
    for _, (i, texto) in sp.COLUNAS_TCM.items():
        cab[i] = "Cïü" + texto if texto.startswith("digo") else texto + "ïü"
    arq = Path(tempfile.mkdtemp()) / "Empenho2025.csv"
    with arq.open("w", encoding="cp850", newline="") as f:
        w = csv.writer(f)
        w.writerow(cab)
        for d in linhas:
            l = [""] * 54
            for k, v in d.items():
                l[sp.COLUNAS_TCM[k][0]] = v
            w.writerow(l)
    return arq


def tce(linhas: list[dict]) -> Path:
    cab = ["id_despesa_detalhe", *sp.COLUNAS_TCE, "historico_despesa"]
    texto = io.StringIO()
    w = csv.writer(texto, delimiter=";")
    w.writerow(cab)
    for d in linhas:
        w.writerow([d.get(k, "") for k in cab])
    arq = Path(tempfile.mkdtemp()) / "despesas-2025.zip"
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("despesas-2025.csv", texto.getvalue().encode("latin-1"))
    return arq


def fase(fase: str, valor: str, empenho: str = "1-2025", **extra) -> dict:
    d = {"ano_exercicio": "2025", "codigo_municipio_ibge": "3509502", "ds_orgao": "PREFEITURA MUNICIPAL DE CAMPINAS",
         "tp_despesa": fase, "nr_empenho": f" {empenho}", "tp_identificador_despesa": "CNPJ - PESSOA JURÍDICA",
         "nr_identificador_despesa": CNPJ, "ds_despesa": "CONSTRUTORA BOA OBRA LTDA", "vl_despesa": valor,
         "ds_elemento": "44905107 - OBRAS"}
    d.update(extra)
    return d


class TesteCapital(unittest.TestCase):
    def test_soma_separa_e_descarta_o_cpf(self):
        base = {"exercicio": "2025", "sigla": "PMSP", "empresa": "PREFEITURA DO MUNICÍPIO DE SÃO PAULO",
                "grupo": "3", "modalidade": "90", "elemento": "39", "cancelado": ".00"}
        arq = tcm([
            {**base, "doc": CNPJ, "nome": "CONSTRUTORA BOA OBRA LTDA", "empenhado": "1000.00", "pago": "800.00"},
            {**base, "doc": CNPJ_FILIAL, "nome": "CONSTRUTORA BOA OBRA LTDA", "empenhado": "500.00", "pago": "500.00"},
            {**base, "doc": CPF, "nome": "FULANA DE TAL", "elemento": "36", "empenhado": "300.00", "pago": "300.00"},
            {**base, "doc": CPF, "nome": "FULANA DE TAL", "elemento": "36", "empenhado": "200.00", "cancelado": "50.00", "pago": "100.00"},
            # A prefeitura pagando o próprio fundo de previdência: fora do total.
            {**base, "doc": CNPJ, "nome": "FUNPREV", "modalidade": "91", "grupo": "1", "elemento": "13", "empenhado": "900.00", "pago": "900.00"},
        ])
        r, fora = sp.resumir_tcm(arq, 2025)
        self.assertEqual(fora["linhas"], 5)
        self.assertEqual(r["pago"], 1700)
        self.assertEqual(r["empenhado"], 1950)
        self.assertEqual(r["intra"], 900)
        self.assertEqual(r["tipos"][pb.EMPRESA], 1300)
        self.assertEqual(r["tipos"][pb.PESSOA], 400)
        self.assertEqual(r["pessoas"], 1)
        self.assertEqual(r["empresas"], 1)
        self.assertEqual(r["credores"], [["CONSTRUTORA BOA OBRA LTDA", CNPJ, 1300, 2]])
        texto = json.dumps(r)
        self.assertNotIn(CPF, texto)
        self.assertNotIn("FULANA", texto)

    def test_arquivo_mudou(self):
        arq = tcm([])
        texto = arq.read_text(encoding="cp850").replace("CPF_CNPJ", "DOCUMENTO", 1)
        arq.write_text(texto, encoding="cp850")
        with self.assertRaises(SystemExit):
            sp.resumir_tcm(arq, 2025)


class TesteInterior(unittest.TestCase):
    def test_fases_restos_e_pessoa(self):
        arq = tce([
            fase("Empenhado", "1.000,00"),
            fase("Reforço", "200,00"),
            fase("Anulação", "100,00"),
            fase("Valor Liquidado", "1.100,00"),
            fase("Valor Pago", "600,00"),
            fase("Valor Pago", "500,00"),           # o mesmo empenho, pago em duas vezes
            fase("Valor Pago", "999,00", empenho="7-2024"),   # restos a pagar de 2024: fora
            fase("Empenhado", "50,00", empenho="2-2025", tp_identificador_despesa="PESSOA FÍSICA",
                 nr_identificador_despesa="910018", ds_despesa="FULANO DE TAL", ds_elemento="33903601 - ESTAGIÁRIOS"),
            fase("Valor Pago", "50,00", empenho="2-2025", tp_identificador_despesa="PESSOA FÍSICA",
                 nr_identificador_despesa="910018", ds_despesa="FULANO DE TAL", ds_elemento="33903601 - ESTAGIÁRIOS"),
            fase("Valor Pago", "70,00", empenho="3-2025", ds_orgao="CONSÓRCIO INTERMUNICIPAL DE SAÚDE"),
            fase("Valor Pago", "10,00", codigo_municipio_ibge="9999999"),
        ])
        mun, fora = sp.resumir_tce(arq, 2025, {"3509502"})
        m = mun["3509502"]
        self.assertEqual(m["empenhado"], 1150)
        self.assertEqual(m["pago"], 1150)
        self.assertEqual(m["n"], 2)
        self.assertEqual(m["tipos"][pb.EMPRESA], 1100)
        self.assertEqual(m["tipos"][pb.PESSOA], 50)
        self.assertEqual(m["pessoas"], 1)
        self.assertEqual(m["credores"], [["CONSTRUTORA BOA OBRA LTDA", CNPJ, 1100, 1]])
        self.assertEqual(fora["outro_ano"]["Valor Pago"], 999)
        self.assertEqual(fora["sem_ibge"]["9999999"], 10)
        self.assertNotIn("910018", json.dumps(mun))
        self.assertNotIn("FULANO", json.dumps(mun))


class TesteNomes(unittest.TestCase):
    def tipo(self, nome: str) -> str:
        l = sp.qlik.Linha("", "PREFEITURA", CNPJ, nome, False, "3", "90", "39", 0.0, 1.0)
        return pb.TIPOS[sp.tipo_do_credor(l)]

    def test_o_que_nao_e_fornecedor(self):
        self.assertEqual(self.tipo("FOLHA DE PAGAMENTO BEM ESTAR ANIMAL"), "Folha de pagamento")
        self.assertEqual(self.tipo("PMDUMONT - FOLHA DE PAGAMENTO"), "Folha de pagamento")
        self.assertEqual(self.tipo("I.N.S.S. (FOLHA PAGTO)"), "Previdência")
        self.assertEqual(self.tipo("SAAE - SERVICO AUTONOMO DE AGUA E ESGOTO"), "Outros órgãos públicos")
        self.assertEqual(self.tipo("UMMES UNIAO DOS MUNICIPIOS DA MEDIA SOROCABANA"), "Outros órgãos públicos")
        self.assertEqual(self.tipo("EMPRESA FOLHA DA MANHA S.A."), "Fornecedores")
        self.assertEqual(self.tipo("INFORMATICA DE MUNICIPIOS ASSOCIADOS S/A"), "Fornecedores")

    def test_nome_estragado(self):
        from collections import Counter
        self.assertEqual(sp.nome_limpo(Counter({"VEROCHEQUE REFEIï¿½ï¿½ES LTDA.": 5, "VEROCHEQUE REFEIÇÕES LTDA": 1})),
                         "VEROCHEQUE REFEIÇÕES LTDA")
        self.assertEqual(sp.nome_limpo(Counter({"SERVIï¿½O DE SAï¿½DE": 3})), "")   # vai buscar no cadastro de CNPJ


if __name__ == "__main__":
    unittest.main()
