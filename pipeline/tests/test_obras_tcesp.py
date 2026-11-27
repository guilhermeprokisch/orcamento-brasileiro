"""Testes das obras do estado e das prefeituras de SP (obras_tcesp.py), sem rede: o nome da obra, o que fica de fora
e como as obras entram na lista do TCU.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orcamento_pipeline import obras_paradas as op
from orcamento_pipeline import obras_tcesp as t


def linha(cidade="Guarulhos", situacao="Paralisada", esfera="MUNICIPAL", valor=1000.0, objeto="CONSTRUÇÃO DE CRECHE",
          empresa="CONSTRUTORA EXEMPLO LTDA", orgao="PREFEITURA MUNICIPAL DE GUARULHOS", ano=2022):
    return [cidade, situacao, esfera, valor, empresa, "00000000000100", orgao, ano, objeto]


class NomeDaObra(unittest.TestCase):
    def test_tira_o_comeco_e_poe_em_minusculas(self) -> None:
        self.assertEqual(
            t.nome_da_obra("CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM SERVIÇOS DE ENGENHARIA PARA EXECUÇÃO DE PAVIMENTAÇÃO "
                           "E DRENAGEM DOS BAIRROS TOQUE TOQUE PEQUENO E TOQUE TOQUE GRANDE"),
            "Execução de pavimentação e drenagem dos bairros Toque Toque Pequeno e Toque Toque Grande")

    def test_presente_contrato(self) -> None:
        self.assertEqual(t.nome_da_obra("CONSTITUI OBJETO DO PRESENTE CONTRATO A CONSTRUÇÃO DE CLÍNICA VETERINÁRIA"),
                         "Construção de clínica veterinária")
        self.assertEqual(t.nome_da_obra("O PRESENTE INSTRUMENTO TEM POR OBJETO A CONTRATAÇÃO DE EMPRESA PARA CONSTRUÇÃO "
                                        "DE ESCADA HIDRÁULICA"), "Construção de escada hidráulica")

    def test_sem_para(self) -> None:
        self.assertEqual(t.nome_da_obra("CONTRATAÇÃO DE EMPRESA ESPECIALIZADA EM EXECUÇÃO DE OBRAS DE PAVIMENTAÇÃO"),
                         "Execução de obras de pavimentação")

    def test_siglas_nomes_e_cidade(self) -> None:
        self.assertEqual(
            t.nome_da_obra("REFORMA DA EMEF JOÃO GARCIA ANDREO LOCALIZADA NA AVENIDA FRANCISCO ARNALDO DA SILVA Nº 668 "
                           "NESTA CIDADE DE FERNANDÓPOLIS/SP", "Fernandópolis"),
            "Reforma da EMEF João Garcia Andreo localizada na avenida Francisco Arnaldo da Silva Nº 668 nesta cidade de "
            "Fernandópolis/SP")

    def test_aspas(self) -> None:
        self.assertEqual(t.nome_da_obra('REFORMA DA EMEF "MILTON MONTI"'), 'Reforma da EMEF "Milton Monti"')

    def test_vazio(self) -> None:
        self.assertEqual(t.nome_da_obra(None), "")


class Montar(unittest.TestCase):
    def setUp(self) -> None:
        self.p = mock.patch.object(t, "_municipios", return_value={"GUARULHOS": "3518800", "FLORINIA": "3516101"})
        self.p.start()
        self.addCleanup(self.p.stop)

    def bruto(self, tabela, fontes=None):
        return {"periodo": [[1, "Data Base: 17/10/2026"]], "municipios": [[-1, "Todos (com obras)"], [3550308, "São Paulo"]],
                "tabela": tabela, "fontes": {str(f): fontes.get(f, []) if fontes else [] for f in t.FONTES}}

    def test_tira_repetidas_e_so_federais(self) -> None:
        a = linha(valor=10.0)
        federal = linha(objeto="CONSTRUÇÃO DE UBS", valor=5.0)
        misto = linha(objeto="CONSTRUÇÃO DE QUADRA", valor=7.0)
        d = t.montar(self.bruto([a, a, federal, misto], {1: [a, misto], 5: [federal, misto], 8: [federal]}))
        self.assertEqual(d["data_base"], "2026-10-17")
        self.assertEqual(d["repetidas"], 1)
        self.assertEqual(d["so_federal"], [1, 5.0])
        self.assertEqual([o[0] for o in d["obras"]], ["Construção de creche", "Construção de quadra"])
        # sem fonte informada: 0; só não federal: 1; com alguma federal: 2
        self.assertEqual([o[9] for o in d["obras"]], [1, 2])

    def test_situacao_esfera_e_cidade(self) -> None:
        d = t.montar(self.bruto([
            linha(situacao="Em execução - atrasada", esfera="ESTADUAL", valor=3.0, cidade="São Paulo",
                  orgao="SECRETARIA  DOS TRANSPORTES"),
            linha(situacao="Em execução - no prazo", valor=2.0, cidade="Florínea", objeto=None),
            linha(valor=1.0),
        ]))
        self.assertEqual(d["obras"], [
            ["Construção de creche", "São Paulo", 3550308, 1, 0, 1, 3.0, 2022, "Secretaria dos Transportes", 0],
            ["Obra sem descrição, contratada com Construtora Exemplo LTDA", "Florínea", 3516101, 2, 0, 0, 2.0, 2022,
             None, 0],
            ["Construção de creche", "Guarulhos", 3518800, 2, 1, 0, 1.0, 2022, None, 0],
        ])

    def test_situacao_nova(self) -> None:
        with self.assertRaises(SystemExit):
            t.montar(self.bruto([linha(situacao="Concluída")]))


class Juntar(unittest.TestCase):
    TODAS = {"data_base": "2026-04", "fonte": "TCU", "url": "u", "situacoes": op.SITUACOES, "setores": ["Educação"],
             "quem_paga": ["FNDE (Educação)"], "pac": op.PACS,
             "uf": {"SP": [["Creche", "Guarulhos", 3518800, 0, 0, 1, 50, 5.0, 2.0, 0]],
                    "CE": [["Quadra", "Carnaubal", 2303402, 0, 0, 0, 80, 9.0, 1.0, 0]]}}
    TCESP = {"data_base": "2026-10-17", "fonte": t.FONTE, "url": t.URL, "uf": "SP", "repetidas": 0, "so_federal": [2, 3.0],
             "obras": [["Ponte", "Guarulhos", 3518800, 2, 1, 0, 8.0, 2022, "PREFEITURA", 1],
                       ["Metrô", "São Paulo", 3550308, 1, 0, 1, 1.0, 2023, "METRÔ", 0]]}

    def test_juntar(self) -> None:
        todas = json.loads(json.dumps(self.TODAS))
        doc = t.juntar(todas, self.TCESP)
        self.assertEqual(todas, self.TODAS)  # não mexe no original
        self.assertEqual(doc["esferas"], ["União", "Governo do estado", "Prefeitura"])
        self.assertEqual(doc["setores"], ["Educação", op.SEM_SETOR])
        self.assertEqual(doc["quem_paga"], ["FNDE (Educação)", "Governo do estado", "Prefeitura"])
        self.assertEqual(doc["uf"]["SP"], [
            ["Ponte", "Guarulhos", 3518800, 1, 2, 1, None, 8.0, None, 0, 2, 0, 2022, "PREFEITURA"],
            ["Creche", "Guarulhos", 3518800, 0, 0, 1, 50, 5.0, 2.0, 0],
            ["Metrô", "São Paulo", 3550308, 1, 1, 0, None, 1.0, None, 0, 1, 1, 2023, "METRÔ"],
        ])
        self.assertEqual(doc["uf"]["CE"], self.TODAS["uf"]["CE"])
        self.assertEqual(doc["tcesp"]["obras"], 2)

        with tempfile.TemporaryDirectory() as tmp:
            i = op.gravar_todas(doc, Path(tmp))
        self.assertEqual(i["total"], [4, 23.0, 3.0])
        self.assertEqual(i["por_esfera"], [2, 1, 1])
        self.assertEqual(i["por_situacao"], [2, 2, 0, 0])
        self.assertEqual(i["uf"]["SP"], [3, 14.0, 2.0])
        self.assertEqual(i["tcesp"]["data_base"], "2026-10-17")

    def test_sem_tcesp(self) -> None:
        doc = t.juntar(self.TODAS, None)
        self.assertEqual(doc["uf"], self.TODAS["uf"])
        self.assertEqual(doc["esferas"][0], "União")
        with tempfile.TemporaryDirectory() as tmp:
            i = op.gravar_todas(doc, Path(tmp))
        self.assertEqual(i["por_esfera"], [2, 0, 0])
        self.assertNotIn("tcesp", i)


if __name__ == "__main__":
    unittest.main()
