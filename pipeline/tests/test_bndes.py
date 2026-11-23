"""Testes do BNDES (bndes.py), sem rede: as faixas de juro, o "para quê", a identificação das indiretas e a privacidade.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from orcamento_pipeline import bndes as b

CAB_D = ('"cliente";"cnpj";"descricao_do_projeto";"uf";"municipio";"municipio_codigo";"numero_do_contrato";"data_da_contratacao";'
         '"valor_contratado_reais";"valor_desembolsado_reais";"fonte_de_recurso_desembolsos";"custo_financeiro";"juros";'
         '"prazo_carencia_meses";"prazo_amortizacao_meses";"modalidade_de_apoio";"forma_de_apoio";"produto";"instrumento_financeiro";'
         '"inovacao";"area_operacional";"setor_cnae";"subsetor_cnae_agrupado";"subsetor_cnae_codigo";"subsetor_cnae_nome";"setor_bndes";'
         '"subsetor_bndes";"porte_do_cliente";"natureza_do_cliente";"instituicao_financeira_credenciada";'
         '"cnpj_da_instituicao_financeira_credenciada";"tipo_de_garantia";"tipo_de_excepcionalidade";"situacao_do_contrato"')
CAB_I = ('"cliente";"cpf_cnpj";"uf";"municipio";"municipio_codigo";"data_da_contratacao";"valor_da_operacao_em_reais";'
         '"valor_desembolsado_reais";"fonte_de_recurso_desembolsos";"custo_financeiro";"juros";"prazo_carencia_meses";'
         '"prazo_amortizacao_meses";"modalidade_de_apoio";"forma_de_apoio";"produto";"instrumento_financeiro";"inovacao";'
         '"area_operacional";"setor_cnae";"subsetor_cnae_agrupado";"subsetor_cnae_codigo";"subsetor_cnae_nome";"setor_bndes";'
         '"subsetor_bndes";"porte_do_cliente";"natureza_do_cliente";"instituicao_financeira_credenciada";"cnpj_do_agente_financeiro";'
         '"situacao_da_operacao"')


def direta(cliente, cnpj, ibge, data, valor, custo, modalidade="REEMBOLSÁVEL", instr="LOGÍSTICA – RODOVIAS PRIMEIRO CICLO",
           natureza="PRIVADA", setor="INFRAESTRUTURA"):
    return (f'"{cliente}";"{cnpj}";"PROJETO";"PB";"X";{ibge};1;"{data}";"{valor}";"0";"-";"{custo}";"1,5";0;0;"{modalidade}";'
            f'"DIRETA";"BNDES FINEM";"{instr}";"NÃO";"-";"-";"-";"-";"CONCESSIONARIAS RODOVIAS";"{setor}";"-";"GRANDE";"{natureza}";'
            f'"-";"-";"-";"-";"ATIVO"')


def indireta(cliente, doc, ibge, data, valor, custo, instr="MATERIAIS INDUSTRIALIZADOS"):
    return (f'"{cliente}";"{doc}";" PB";"JOAO PESSOA";{ibge};"{data}";{valor};"{valor},0";"-";"{custo}";"1,5";0;0;"REEMBOLSÁVEL";'
            f'"INDIRETA";"BNDES FINAME";"{instr}";"NÃO";"-";"-";"-";"-";"FABRICACAO DE EMBALAGENS";"INDUSTRIA";"-";"MÉDIA";"PRIVADA";'
            f'"BANCO X";"00.000.000.0001-00";"ATIVA"')


class Regras(unittest.TestCase):
    def test_faixas(self):
        self.assertEqual(b.faixa_de_juro("TLP", "REEMBOLSÁVEL"), "tlp")
        self.assertEqual(b.faixa_de_juro("TAXA FIXA", "REEMBOLSÁVEL"), "abaixo")
        self.assertEqual(b.faixa_de_juro("TAXA REFERENCIAL (TR", "REEMBOLSÁVEL"), "abaixo")
        self.assertEqual(b.faixa_de_juro("TJLP", "REEMBOLSÁVEL"), "abaixo")
        self.assertEqual(b.faixa_de_juro("SELIC", "REEMBOLSÁVEL"), "mercado")
        self.assertEqual(b.faixa_de_juro("US$ / CESTA", "REEMBOLSÁVEL"), "mercado")
        self.assertEqual(b.faixa_de_juro("SEM CUSTO", "NÃO REEMBOLSÁVEL"), "doacao")

    def test_faixa_em_sql_igual_a_python(self):
        con = duckdb.connect()
        casos = [("TLP", "REEMBOLSÁVEL"), ("TAXA FIXA", "REEMBOLSÁVEL"), ("TAXA REFERENCIAL (TR", "X"), ("SELIC", "X"),
                 ("SEM CUSTO", "NÃO REEMBOLSÁVEL"), ("IPCA", "X"), ("TJLP", "X")]
        for custo, modalidade in casos:
            sql = con.execute(f"SELECT {b.SQL_FAIXA} FROM (SELECT ? AS custo, ? AS modalidade)", [custo, modalidade]).fetchone()[0]
            self.assertEqual(sql, b.faixa_de_juro(custo, modalidade), custo)

    def test_para_que(self):
        self.assertEqual(b.para_que("LOGÍSTICA – RODOVIAS PRIMEIRO CICLO", "BNDES FINEM"), "Rodovias")
        self.assertEqual(b.para_que("BK AQUISIÇÃO E COMERCIALIZAÇÃO – ÔNIBUS E CAMINHÃO", "BNDES FINAME"), "Ônibus e caminhões")
        self.assertEqual(b.para_que("FUNDO DA MARINHA MERCANTE", "BNDES FINEM"), "Barcos e estaleiros (Marinha Mercante)")
        # Debênture: pelo setor da empresa.
        self.assertEqual(b.para_que("DEBENTURES - OFERTAS PÚBLICAS PADRÃO", "BNDES DEBENTURES SIMPLES",
                                    "CAPTACAO, TRATAMENTO E DISTRIBUICAO DE AGUA"), "Saneamento")

    def test_nomes_e_documentos(self):
        self.assertEqual(b.digitos_visiveis("**.*16.560/0001-**"), "16560")
        self.assertEqual(b.digitos_visiveis(""), "")
        self.assertEqual(b.raiz_no_nome("BOM JESUS AGROPECUARIA LTDA (08895796)"), "08895796")
        self.assertEqual(b.normalizar_nome("CONCESSIONÁRIA ROTA DO OESTE S.A. (19521322)"), "CONCESSIONARIA ROTA DO OESTE S")
        self.assertEqual(b.nome_limpo("COPOBRAS S/A. INDUSTRIA E COMERCIO DE EMBALAGENS"), "Copobras S.A. Industria e Comercio de Embalagens")
        self.assertFalse(b.pode_nomear("JOSE SOUZA 52998224725", "2062"))
        self.assertFalse(b.pode_nomear("JOSE SOUZA", "2135"))
        self.assertFalse(b.pode_nomear("JOSE SOUZA", None))
        self.assertTrue(b.pode_nomear("COPOBRAS SA", "2054"))
        self.assertFalse(b.pode_nomear("OSMAR TESTE E OUTRO", "4120"))   # produtor rural pessoa física


class Montagem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.d, self.i = t / "d.csv", t / "i.csv"
        self.d.write_text("\n".join([
            CAB_D,
            direta("RODOVIA TESTE S.A.", "11.222.333/0001-81", 9999999, "2025-03-10", "9000000000,0", "TLP"),
            direta("MUNICIPIO DE JOAO PESSOA", "08.778.326/0001-56", 2507507, "2025-05-10", "50000000,0", "TAXA FIXA",
                   instr="BNDES PMAT", natureza="ADMINISTRAÇÃO PÚBLICA DIRETA - GOVERNO MUNICIPAL", setor="COMERCIO/SERVICOS"),
            direta("FUNDO TESTE", "22.333.444/0001-05", 2507507, "2025-06-10", "1000000,0", "SEM CUSTO",
                   modalidade="NÃO REEMBOLSÁVEL", instr="FUNDO AMAZÔNIA"),
        ]) + "\n", encoding="utf-8")
        self.i.write_text("\n".join([
            CAB_I,
            # Empresa achada no cadastro pelos dígitos e pelo nome.
            indireta("EMBALAGENS PARAIBA LTDA", "**.*45.678/0001-**", 2507507, "2025-02-01", 30000000, "TLP"),
            indireta("EMBALAGENS PARAIBA LTDA", "**.*45.678/0001-**", 2507507, "2026-02-01", 1000000, "TAXA FIXA"),
            # Pessoa física pelo nome, empresário individual com CPF no nome: nunca pelo nome.
            indireta("MARIA DA SILVA", "**.*11.222/3344-**", 2507507, "2025-04-01", 200000, "TAXA FIXA"),
            indireta("JOSE SOUZA 52998224725", "**.*98.224/7250-**", 2507507, "2025-04-02", 300000, "SELIC"),
            # Produtor rural pessoa física com CNPJ (natureza 412-0): só somado.
            indireta("ANTONIO PRODUTOR E OUTRO", "**.*44.555/0001-**", 2507507, "2025-04-03", 400000, "TAXA FIXA"),
        ]) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _con(self):
        con = duckdb.connect()
        b.ler_operacoes(con, self.d, self.i)
        con.execute("CREATE OR REPLACE TEMP TABLE nat (raiz VARCHAR, natureza_rfb VARCHAR)")
        # O que o cadastro teria achado: a embalagem (pelos dígitos e pelo nome) e a natureza das diretas.
        con.execute("UPDATE op SET raiz = '12345678' WHERE cliente = 'EMBALAGENS PARAIBA LTDA'")
        con.execute("UPDATE op SET raiz = '33444555' WHERE cliente = 'ANTONIO PRODUTOR E OUTRO'")
        con.execute("INSERT INTO nat VALUES ('11222333', '2054'), ('08778326', '1244'), ('22333444', '3999'), ('12345678', '2062'), ('33444555', '4120')")
        b.marcar_nomeaveis(con)
        return con

    def test_faixas_e_cidades(self):
        con = self._con()
        r, c, e = b.montar(con, [[2025, 10, 1]], None, None, None)
        self.assertEqual(r["ano"], 2025)   # 2026 só até fevereiro: o ano fechado é 2025
        s = next(x for x in r["serie"] if x[0] == 2025)
        self.assertEqual(s[1], 9_051_000_000)        # diretas
        self.assertEqual(s[3], 50_000_000 + 200_000 + 400_000)  # abaixo do mercado
        self.assertEqual(s[6], 1_000_000)             # doação
        self.assertEqual(r["sem_cidade"], 9_000_000_000)
        jp = c["mun"]["2507507"]
        self.assertEqual(jp[0], 6)                    # contratos
        self.assertEqual(jp[1], 81_900_000)
        nomes = [m[0] for m in jp[6]]
        self.assertIn("Embalagens Paraiba Ltda", nomes)
        self.assertEqual(e["empresas"]["12345678"][2], 31_000_000)

    def test_privacidade(self):
        con = self._con()
        r, c, e = b.montar(con, [], None, None, None)
        texto = json.dumps([r, c, e], ensure_ascii=False)
        for proibido in ("MARIA", "Maria", "JOSE", "Jose", "52998224725", "98.224", "**.", "ANTONIO", "Antonio", "33444555"):
            self.assertNotIn(proibido, texto)
        self.assertEqual(r["sem_nome"][0], 3)   # as três pessoas, só somadas


class Referencia(unittest.TestCase):
    def test_sem_baixar_copia(self):
        with tempfile.TemporaryDirectory() as t:
            ref, saida = Path(t) / "ref", Path(t) / "site"
            ref.mkdir()
            (ref / "bndes.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(b, "REFERENCIA", ref), mock.patch.object(b, "SAIDA", saida), mock.patch.object(b, "RAIZ", Path(t)):
                b.copiar_referencia()
            self.assertTrue((saida / "resumo.json").exists())


if __name__ == "__main__":
    unittest.main()
