"""Testes das obras paradas (obras_paradas.py), sem rede: a cidade pelo nome, o "desde quando" e o destino.

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
        doc = op.montar(self.pasta)

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

    def test_ultima_so_com_paralisadas(self) -> None:
        gravar(self.pasta, "2026-04", [obra("A", "Paralisada", "Carnaubal/CE")])
        with self.assertRaises(SystemExit):
            op.montar(self.pasta)


if __name__ == "__main__":
    unittest.main()
