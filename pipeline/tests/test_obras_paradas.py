"""Testes das obras paradas (obras_paradas.py), sem rede: a cidade pelo nome, o "desde quando", o destino e a
ligação com os convênios do Transferegov.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import openpyxl

from orcamento_pipeline import obras_paradas as op

CAB = ["Data base", "Base de dados", "Empreendimento", "Núm. Instrumento", "Situação", "Local", "Exec. física",
       "Exec. financeira", "Valor Investimento", "Valor Desbloqueado", "Setor", "Repassador", "Causa da paralisação",
       "Obra PAC", "Pacto", "ID", "Situação origem"]
CIDADES = {("CE", "CARNAUBAL"): 2303402, ("RN", "BOA SAUDE"): 2405306, ("PB", "JOAO PESSOA"): 2507507}


def obra(id_, situacao, local, valor=100.0, base="SIMEC", nome="(1004938) PAC 2 - Quadra - Carnaubal - CE",
         origem="PARALISADA", causa=None):
    return [dt.datetime(2026, 4, 1), base, nome, "PAC2 6364/2013", situacao, local, 0.83, 0.64, valor, valor / 2,
            "Educação", "Fundo Nacional de Desenvolvimento da Educação", causa, "Não", "Manifestou interesse em repactuar",
            id_, origem]


def gravar(pasta: Path, data: str, linhas: list[list]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(CAB)
    for r in linhas:
        ws.append(r)
    ws.append(["Filtros aplicados:\nData base é abr/26"])  # a linha que o Power BI põe no fim
    wb.save(pasta / f"obras-{data}.xlsx")


class TestObrasParadas(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        self.cidades = mock.patch.object(op, "_cidades", return_value=CIDADES)
        self.cidades.start()

    def tearDown(self) -> None:
        self.cidades.stop()
        self.tmp.cleanup()

    def test_local(self) -> None:
        self.assertEqual(op._local("Carnaubal/CE", CIDADES), ("CE", 2303402))
        self.assertEqual(op._local("Januário Cicco/RN", CIDADES), ("RN", 2405306))  # nome antigo
        self.assertEqual(op._local("RS", CIDADES), ("RS", None))                    # obra do DNIT, só a UF
        self.assertEqual(op._local("Lugar Nenhum/CE", CIDADES), ("CE", None))

    def test_nome(self) -> None:
        self.assertEqual(op._nome("(1004938) PAC 2 - Quadra"), "PAC 2 - Quadra")
        self.assertEqual(op._nome("(EP) (29040) Vila Olímpica"), "Vila Olímpica")
        self.assertEqual(op._nome("urbanizacao  do   rio"), "Urbanizacao do rio")

    def test_montar(self) -> None:
        gravar(self.pasta, "2024-04", [obra("A", "Paralisada", "Carnaubal/CE"), obra("B", "Paralisada", "Carnaubal/CE"),
                                       obra("C", "Em execução", "João Pessoa/PB")])
        gravar(self.pasta, "2025-04", [obra("A", "Paralisada", "Carnaubal/CE"), obra("B", "Em execução", "Carnaubal/CE"),
                                       obra("C", "Paralisada", "João Pessoa/PB"), obra("D", "Paralisada", "RS", base="DNIT")])
        gravar(self.pasta, "2026-04", [
            obra("A", "Paralisada", "Carnaubal/CE", valor=300),
            obra("B", "Paralisada", "Carnaubal/CE", valor=200, origem="LICITAÇÃO", causa="Outros"),
            obra("C", "Concluída", "João Pessoa/PB"),
            obra("E", "Em execução", "João Pessoa/PB"),
            obra("F", "Paralisada", "RS", base="DNIT", causa="Abandono da empresa"),
        ])
        doc = op.montar(self.pasta, transferegov=False)

        self.assertEqual(doc["data_base"], "2026-04")
        b = doc["brasil"]
        self.assertEqual(b["total"][:2], [3, 600.0])
        self.assertEqual(b["ativas"], 4)
        self.assertEqual(b["sem_cidade"][0], 1)
        # A: parada nas três datas; B: voltou a andar em 2025 e parou de novo; F: só em 2026.
        desde = {o[5]: o[9] for o in doc["mun"]["2303402"][4]}  # pelo valor: A custa 300, B custa 200
        self.assertEqual(desde, {300.0: "2024-04", 200.0: "2026-04"})
        self.assertEqual(dict((d, n) for d, n, *_ in b["desde"]), {"2024-04": 1, "2026-04": 2})
        # Das 3 paradas de 2025: A continua, C ficou pronta, D saiu da lista.
        self.assertEqual(dict(b["destino"]["situacoes"]), {"Paralisada": 1, "Concluída": 1, "Saiu da lista": 1})
        # Carnaubal: 2 paradas de 2 ativas; João Pessoa: nenhuma parada, então fora de "mun".
        self.assertEqual(doc["mun"]["2303402"][:4], [2, 500.0, 250.0, 2])
        self.assertNotIn("2507507", doc["mun"])
        # "Outros" não é causa; a situação no órgão fica guardada.
        obras = {o[5]: o for o in doc["mun"]["2303402"][4]}
        self.assertIsNone(obras[200.0][7])
        self.assertEqual(obras[200.0][8], "Licitação")
        self.assertEqual(doc["uf"]["RS"]["sem_cidade"][0][7], "Abandono da empresa")
        # Em andamento (em execução + paradas): A, B, E e F. [obras, previsto, liberado, paradas, previsto das paradas]
        em = b["andamento"]
        self.assertEqual(em["total"], [4, 700.0, 350.0, 3, 600.0])
        self.assertEqual(em["setor"], [["Educação", 4, 700.0, 350.0, 3, 600.0]])
        self.assertEqual(em["uf"], {"CE": [2, 500.0, 250.0, 2, 500.0], "PB": [1, 100.0, 50.0, 0, 0], "RS": [1, 100.0, 50.0, 1, 100.0]})
        self.assertEqual([o[4] for o in em["maiores"]], [300.0, 200.0, 100.0, 100.0])
        self.assertEqual(em["maiores"][0][8], 1)

    def test_ultima_so_com_paralisadas(self) -> None:
        gravar(self.pasta, "2026-04", [obra("A", "Paralisada", "Carnaubal/CE")])
        with self.assertRaises(SystemExit):
            op.montar(self.pasta, transferegov=False)

    def test_transferegov(self) -> None:
        numeros = {"A": "900001", "B": "900002", "C": "900003"}
        convenios = [
            {"NR_CONVENIO": "900001", "ID_PROPOSTA": "1", "DIA_ASSIN_CONV": "18/11/2021", "DIA_FIM_VIGENC_CONV": "30/11/2027",
             "SIT_CONVENIO": "Em execução", "VL_GLOBAL_CONV": "265052,83", "VL_DESEMBOLSADO_CONV": "238856",
             "VL_SALDO_CONTA": "122310.72"},
            {"NR_CONVENIO": "900002", "ID_PROPOSTA": "2", "DIA_ASSIN_CONV": "", "DIA_FIM_VIGENC_CONV": "",
             "SIT_CONVENIO": "Em execução", "VL_GLOBAL_CONV": "1000", "VL_DESEMBOLSADO_CONV": "1000", "VL_SALDO_CONTA": "1000"},
            {"NR_CONVENIO": "900003", "ID_PROPOSTA": "3", "DIA_ASSIN_CONV": "01/02/2015", "DIA_FIM_VIGENC_CONV": "01/02/2020",
             "SIT_CONVENIO": "Prestação de Contas Concluída", "VL_GLOBAL_CONV": "100", "VL_DESEMBOLSADO_CONV": "80",
             "VL_SALDO_CONTA": "0"},
        ]
        propostas = [
            {"ID_PROPOSTA": "1", "UF_PROPONENTE": "CE", "COD_MUNIC_IBGE": "2303402", "NATUREZA_JURIDICA": op.MUNICIPAL},
            {"ID_PROPOSTA": "2", "UF_PROPONENTE": "SE", "COD_MUNIC_IBGE": "2800100", "NATUREZA_JURIDICA": op.MUNICIPAL},
            {"ID_PROPOSTA": "3", "UF_PROPONENTE": "CE", "COD_MUNIC_IBGE": "2303402", "NATUREZA_JURIDICA": op.MUNICIPAL},
        ]
        arquivos = {"siconv_convenio": convenios, "siconv_proposta": propostas,
                    "data_carga_siconv": [{"data_carga": "23/11/2026 06:35:40"}]}

        # O número do instrumento vem da coluna "Núm. Instrumento"; aqui, um por obra.
        def com_numero(linhas):
            for r in linhas:
                if len(r) == len(CAB) and r[15] in numeros:
                    r[3] = numeros[r[15]]
            return linhas

        gravar(self.pasta, "2026-04", com_numero([
            obra("A", "Paralisada", "Carnaubal/CE", base="CAIXA", valor=300),
            obra("B", "Paralisada", "João Pessoa/PB", base="CAIXA", valor=200),  # convênio de outro estado
            obra("C", "Paralisada", "CE", base="FUNASA", valor=100),             # sem cidade no TCU
            obra("D", "Em execução", "Carnaubal/CE"),
        ]))
        with mock.patch.object(op, "_linhas_tg", side_effect=lambda nome, forcar=False: iter(arquivos[nome])):
            doc = op.montar(self.pasta)

        tg = doc["brasil"]["transferegov"]
        self.assertEqual(tg["data"], "2026-11-23")
        # A e C ligadas; B descartada (o convênio é de Sergipe, a obra da Paraíba).
        self.assertEqual(tg["total"][0], 2)
        self.assertEqual(tg["total"][2], 238936.0)
        carnaubal = {t[5]: t for t in doc["mun"]["2303402"][4]}
        self.assertEqual(carnaubal[300.0][12], ["900001", 2021, "2027-11-30", "Em execução", 265052.83, 238856.0, 122310.72])
        # C não tinha cidade no TCU e ganhou a da prefeitura que assinou.
        self.assertIn(100.0, carnaubal)
        self.assertIsNone({t[5]: t for t in doc["mun"]["2507507"][4]}[200.0][12])
        self.assertEqual(doc["uf"]["CE"]["transferegov"][0], 2)
        self.assertEqual(tg["maiores_saldo"][0][12][0], "900001")

        # A atualização de cada publicação troca só os valores.
        novo = dict(convenios[0], VL_DESEMBOLSADO_CONV="250000", VL_SALDO_CONTA="0")
        n = op.atualizar_tg(doc, {"900001": novo, "900003": convenios[2]}, "2026-11-24")
        self.assertEqual(n, 2)
        self.assertEqual(tg["data"], "2026-11-24")
        self.assertEqual(tg["total"][2:], [250080.0, 0.0])
        self.assertEqual({t[5]: t for t in doc["mun"]["2303402"][4]}[300.0][12][5], 250000.0)


if __name__ == "__main__":
    unittest.main()
