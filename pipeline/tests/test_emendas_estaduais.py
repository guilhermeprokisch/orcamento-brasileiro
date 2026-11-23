"""Testes das emendas estaduais (emendas_estaduais.py), sem rede: números, nomes, o relatório do RJ e a montagem.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import unittest
from unittest import mock

from orcamento_pipeline import emendas_estaduais as e
from orcamento_pipeline.emendas_estaduais import Linha


class Numeros(unittest.TestCase):
    def test_formatos_misturados(self):
        for s, v in [("R$ 1.234,56", 1234.56), ("300.000,00", 300000), ("100000", 100000), ("300.000", 300000),
                     ("100000,0", 100000), ("R$\xa0100.000,00", 100000), ("", 0), (" - ", 0), (2.5, 2.5)]:
            self.assertAlmostEqual(e.numero(s), v, msg=s)

    def test_texto_lido_duas_vezes(self):
        self.assertEqual(e.conserta("FUNDO MUNICIPAL DE SAÃ\x9aDE"), "FUNDO MUNICIPAL DE SAÚDE")
        self.assertEqual(e.conserta("Saúde"), "Saúde")


class Nomes(unittest.TestCase):
    def test_quem_recebe(self):
        self.assertEqual(e.grupo_pelo_nome("FUNDO MUNICIPAL DE SAÚDE DE FIGUEIRÃO"), 0)
        self.assertEqual(e.grupo_pelo_nome("Prefeitura Municipal de Mendes"), 0)
        self.assertEqual(e.grupo_pelo_nome("APM DA EE 26 DE AGOSTO"), 1)
        self.assertEqual(e.grupo_pelo_nome("SECRETARIA DE ESTADO DE EDUCAÇÃO"), 2)

    def test_autor_do_df(self):
        self.assertEqual(e.autor_df("ARLETE AVELAR SAMPAIO - ARLETE SAMPAIO"), ("ARLETE SAMPAIO", False))
        self.assertEqual(e.autor_df("AGACIEL MAIA - HERMETO - REGINALDO SARDINHA")[1], True)
        self.assertEqual(e.autor_df("MAX MACIEL"), ("MAX MACIEL", False))

    def test_area_do_ms_pelo_orgao(self):
        self.assertEqual(e.area_ms("Fundação de Desporto e Lazer de Mato Grosso do Sul - FUNDESPORTE"), "Esporte e lazer")
        self.assertEqual(e.area_ms("Secretaria de Estado de Saúde - SES"), "Saúde")

    def test_area(self):
        self.assertEqual(e.area("08 - Assistência Social"), "Assistência Social")
        self.assertEqual(e.area("SAÚDE"), "Saúde")


class PowerBI(unittest.TestCase):
    def test_linhas_compactas(self):
        from orcamento_pipeline import powerbi
        ds = {"ValueDicts": {"D0": ["Ana", "Bia"]},
              "PH": [{"DM0": [
                  {"S": [{"N": "G0", "T": 1, "DN": "D0"}, {"N": "G1", "T": 4}, {"N": "G2", "T": 1}], "C": [0, 100, "x"]},
                  {"C": [1], "R": 2 | 4},          # repete o valor e o texto da linha anterior
                  {"C": [0, "250.5D"], "Ø": 4},    # o texto é nulo; o número vem como texto
              ]}]}
        self.assertEqual(powerbi.ler_dsr(ds), [["Ana", 100, "x"], ["Bia", 100, "x"], ["Ana", 250.5, None]])

    def test_chave_do_link(self):
        from orcamento_pipeline import powerbi
        r = "eyJrIjoiY2QxNTM1MDctMzIxNi00NzIxLTljNDItYjkwMGE5NTUwN2Q5IiwidCI6ImVjNjNiYzNkIn0%3D"
        self.assertEqual(powerbi.chave_do_link(r), "cd153507-3216-4721-9c42-b900a95507d9")


class AreasSP(unittest.TestCase):
    def test_funcao_e_orgao(self):
        self.assertEqual(e.area_sp("10 - SAUDE", "SAÚDE"), "Saúde")
        self.assertEqual(e.area_sp("04 - ADMINISTRACAO; 06 - SEGURANCA PUBLICA", None), "Administração")
        self.assertEqual(e.area_sp(None, "CULTURA"), "Cultura")
        self.assertEqual(e.area_sp(None, None), "Não informado")
        self.assertEqual(e.num("194291.19999999998"), 194291.19999999998)


class RelatorioRJ(unittest.TestCase):
    def test_com_linha_de_total(self):
        t = ("Posição;Sigla UO;Cod Ação;Tit Ação;Ano Fonte;Fonte RJ;Fonte STN;Deputado;Cod. Emenda;Nº Empenho;Descrição; Dotação; Emp; Liq; Pago\n"
             "12 / 2025;ACADEPOL;4773;Capacitação;1;148;500;Fulano;18202523431; - ; - ;R$ 293.802,00;R$ 0,00;R$ 0,00;R$ 0,00\n"
             ";;;;;;;;;2025NE00001;curso;R$ 0,00;R$ 286.828,81;R$ 286.828,81;R$ 181.966,67\n"
             ";;;;;;;;18202523431 Total;;;R$ 293.802,00;R$ 286.828,81;R$ 286.828,81;R$ 181.966,67\n")
        self.assertAlmostEqual(e.pagos_relatorio_rj(t)["18202523431"], 181966.67)

    def test_sem_linha_de_total(self):
        t = ("posição;Sigla UO;Cod Ação;Tit Ação;Ano Fonte;Fonte RJ;Fonte STN;Autor;Cod. Emenda;Nº Empenho;Descrição;Dot;Emp;Liq;Pago\n"
             "8 / 2026;CEASA;8252;Bancos;1;148;500;Beltrana;51202616761; - ; - ;100.000,00;0,00;0,00;50.000,00\n"
             ";;;;;;;;63202616731; - ; - ;200.000,00;0,00;0,00;0,00\n"
             ";;;;;;;;;2026NE00010;obra;0,00;10,00;10,00;10,00\n")
        p = e.pagos_relatorio_rj(t)
        self.assertEqual(p["51202616761"], 50000)
        self.assertEqual(p["63202616731"], 10)


ELEITOS = [{"chave": "tse-1", "uf": "MG", "urna": "Zé Guilherme", "completo": "JOSE GUILHERME DA SILVA", "cargo": "Deputado Estadual"},
           {"chave": "tse-2", "uf": "MG", "urna": "Celinho Sintrocel", "completo": "JOSE CELIO DE ALVARENGA", "cargo": "Deputado Estadual"}]


class Montagem(unittest.TestCase):
    META = {"MG": {"nome": "Minas Gerais", "fonte": "x", "url": "x", "pago": True, "pix": True},
            "MS": {"nome": "Mato Grosso do Sul", "fonte": "x", "url": "x", "pago": False, "pix": False}}

    def linhas(self):
        return [
            Linha("MG", 2025, "ZÉ GUILHERME", False, 3109808, 0, "Transferência especial", True, 100000, 100000),
            Linha("MG", 2025, "ZÉ GUILHERME", False, None, 2, "Saúde", False, 50000, 40000),
            Linha("MG", 2025, "CELINHO DO SINTTROCEL", False, 3109808, 1, "Saúde", False, 30000, 0),
            Linha("MG", 2025, "BLOCO MINAS EM FRENTE", True, 3109808, 0, "Saúde", False, 70000, 70000),
            Linha("MS", 2025, "Mara Caseiro", False, 5003900, 0, "Saúde", False, 100000, None),
        ]

    def test_cidade_estado_e_deputado(self):
        ls = self.linhas()
        with mock.patch.object(e, "eleitos", return_value=ELEITOS):
            lig = e.ligar(ls)
        self.assertEqual(lig[("MG", "ZÉ GUILHERME")], "tse-1")
        self.assertEqual(lig[("MG", "CELINHO DO SINTTROCEL")], "tse-2")     # pelo apelido
        doc = e.montar(ls, lig, self.META)
        c = doc["mun"]["3109808"]["2025"]
        self.assertEqual((c["v"], c["i"], c["p"], c["pix"]), (170000, 200000, 170000, 100000))
        self.assertEqual(c["g"], [170000, 0, 0])
        self.assertEqual(c["aut"][0], ["Zé Guilherme", 100000, "tse-1"])
        self.assertIn(["coletiva", 70000, None], c["aut"])
        self.assertEqual(c["nAut"], 1)           # o Celinho não teve nada pago aqui
        uf = doc["uf"]["MG"]["2025"]
        self.assertEqual((uf["v"], uf["semCidade"]), (210000, 40000))
        d = doc["deputados"]["tse-1"]["2025"]
        self.assertEqual((d["v"], d["i"], d["est"], d["cid"], d["nc"]), (140000, 150000, 40000, [[3109808, 100000]], 1))
        self.assertNotIn("BLOCO MINAS EM FRENTE", json.dumps(doc["deputados"]))

    def test_sem_pago_mostra_o_indicado(self):
        doc = e.montar(self.linhas(), {}, self.META)
        ms = doc["mun"]["5003900"]["2025"]
        self.assertEqual((ms["v"], ms["p"]), (100000, None))
        self.assertFalse(doc["estados"]["MS"]["pago"])

    def test_pago_parcial_vira_indicado(self):
        ls = [Linha("SE", 2025, "Fulano", False, 2803005, 0, "Saúde", False, 100, 100 if i == 0 else None) for i in range(3)]
        meta = {"SE": {"nome": "Sergipe", "fonte": "x", "url": "x", "pago": True, "pix": True}}
        doc = e.montar(ls, {}, meta)
        c = doc["mun"]["2803005"]["2025"]
        self.assertEqual((c["v"], c["p"]), (300, None))

    def test_csv_com_quebra_de_linha(self):
        b = "a;b;c\n1;texto que\ncontinua;3\n4;5;6\n".encode()
        self.assertEqual(e.ler_csv_remendado(b, ";"), [{"a": "1", "b": "texto que continua", "c": "3"}, {"a": "4", "b": "5", "c": "6"}])

    def test_nao_guarda_quem_recebeu(self):
        doc = e.montar(self.linhas(), {}, self.META)
        texto = json.dumps(doc, ensure_ascii=False)
        self.assertNotRegex(texto, r"\d{3}\.\d{3}\.\d{3}-\d{2}")
        self.assertNotIn("FUNDO MUNICIPAL", texto)


if __name__ == "__main__":
    unittest.main()
