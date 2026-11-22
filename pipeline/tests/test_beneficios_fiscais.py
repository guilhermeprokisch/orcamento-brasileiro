"""Testes dos benefícios fiscais por empresa (beneficios_fiscais.py), sem rede: as somas, os grupos e a privacidade.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import duckdb

from orcamento_pipeline import beneficios_fiscais as bf

CAB = "CNPJ,Nome,Município,UF,Cnae,Mês,Ano,Código_IN,Tributo,Valor"
MEI = "JOSE SOUZA 52998224725"


def linhas(ano: int) -> list[str]:
    return [
        # Uma fábrica na Zona Franca, com Sudene também; duas filiais da mesma raiz somam juntas.
        f'04.337.168/0001-48,MOTO TESTE DA AMAZONIA LTDA,MANAUS,AM,3091101,1,{ano},54,IPI,"1000000,00"',
        f'04.337.168/0002-29,MOTO TESTE DA AMAZONIA LTDA,MANAUS,AM,3091101,2,{ano},54,IPI,"500000,00"',
        f'04.337.168/0001-48,MOTO TESTE DA AMAZONIA LTDA,MANAUS,AM,3091101,12,{ano},20,IRPJ,"250000,00"',
        # Um supermercado com carne (benefício do produto).
        f'11.222.333/0001-81,MERCADO BOM PRECO LTDA,CAMPINA GRANDE,PB,4711302,3,{ano},79,Cofins,"300000,00"',
        # Empresário individual pelo nome com CPF, e outro pela natureza jurídica: só nos totais.
        f'22.333.444/0001-90,{MEI},RECIFE,PE,4712100,3,{ano},79,Cofins,"7000,00"',
        f'33.444.555/0001-02,MARIA DA SILVA,RECIFE,PE,4712100,3,{ano},79,Cofins,"9000,00"',
        # Quem escondeu o nome na Justiça.
        f'**.***.***/****-**,Restrição Judicial (15),SAO PAULO,SP,2013402,5,{ano},22,Cofins,"800000,00"',
    ] + [f'11.222.333/0001-81,MERCADO BOM PRECO LTDA,CAMPINA GRANDE,PB,4711302,{m},{ano},79,Cofins,"1,00"' for m in range(1, 13)]


class Beneficios(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        arq = d / "renuncia-por-regime-2025.zip"
        with zipfile.ZipFile(arq, "w") as z:
            z.writestr("2025.csv", "﻿" + "\n".join([CAB, *linhas(2025)]) + "\n")
        self.con = duckdb.connect()
        with mock.patch.object(bf, "PASTA", d):
            bf.ler_dirbi(self.con, {2025: arq})
        self.con.execute("CREATE TABLE ct (chave VARCHAR, n_contratos INTEGER, contratos DOUBLE)")
        self.con.execute("INSERT INTO ct VALUES ('04337168', 3, 1234.0)")
        self.con.execute("CREATE TABLE em (chave VARCHAR, emendas DOUBLE)")
        nat = {"04337168": "2062", "11222333": "2062", "22333444": "2135", "33444555": "2135"}
        div = {"11222333": [500000.0, 200000.0, 300000.0, 0.0, 0.0]}
        self.doc, self.ocultas, self.ano = bf.montar(self.con, nat, {"3091101": "Fabricação de motocicletas"}, div, "09/2026", 2025)
        self.d = d
        self.nat, self.div = nat, div

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_somas(self) -> None:
        self.assertEqual(self.ano, 2025)
        self.assertEqual(self.doc["empresas"], 5)
        self.assertEqual(self.doc["total"], round(1_750_000 + 300_012 + 7_000 + 9_000 + 800_000))
        moto = next(m for m in self.doc["maiores"] if m["raiz"] == "04337168")
        self.assertEqual(moto["valor"], 1_750_000)
        self.assertEqual(moto["grupo"], "zfm")
        self.assertEqual(moto["tipo"], "empresa")
        self.assertEqual(moto["setor"], "Fabricação de motocicletas")
        self.assertEqual(moto["beneficio"], "Zona Franca: industrializados para território nacional")

    def test_privacidade(self) -> None:
        self.assertEqual(self.ocultas, {"22333444", "33444555"})
        nomes = {m["nome"] for m in self.doc["maiores"]} | {x["nome"] for g in self.doc["grupos"] for x in g["maiores"]}
        self.assertNotIn(MEI, nomes)
        self.assertNotIn("MARIA DA SILVA", nomes)
        self.assertEqual(self.doc["ocultas"], [2, 16_000])
        with mock.patch.object(bf, "PUBLICO", self.d), mock.patch.object(bf, "SAIDA_EMPRESAS", self.d / "e.parquet"), \
                mock.patch.object(bf, "SAIDA_DETALHE", self.d / "p.parquet"), mock.patch.object(bf, "RAIZ", self.d):
            bf.gravar_parquets(self.con, self.ocultas, {}, self.div, self.ano)
        texto = duckdb.sql(f"SELECT string_agg(nome, '|') FROM '{self.d / 'e.parquet'}'").fetchall()[0][0]
        self.assertNotIn("SILVA", texto)
        self.assertNotIn("52998224725", texto)
        chaves = {c for (c,) in duckdb.sql(f"SELECT DISTINCT chave FROM '{self.d / 'p.parquet'}'").fetchall()}
        self.assertEqual(chaves, {"04337168", "11222333", "rj15"})

    def test_restricao_judicial(self) -> None:
        self.assertEqual(self.doc["restricao"], [1, 800_000])
        rj = next(m for m in self.doc["maiores"] if m["restricao"])
        self.assertEqual(rj["raiz"], "")
        self.assertEqual(rj["grupo"], "agro")

    def test_cruzamentos(self) -> None:
        self.assertEqual(self.doc["cruzamentos"]["devem"], [1, 300_012, 200_000])
        self.assertEqual(self.doc["cruzamentos"]["contratos"], [1, 1234, 1_750_000])
        mercado = next(m for m in self.doc["maiores"] if m["raiz"] == "11222333")
        self.assertEqual(mercado["cobranca"], 200_000)

    def test_grupos_nao_se_repetem(self) -> None:
        vistos: dict[int, str] = {}
        for g in bf.GRUPOS:
            for k in g[4]:
                self.assertNotIn(k, vistos, f"código {k} em {vistos.get(k)} e {g[0]}")
                vistos[k] = g[0]
        self.assertTrue(all(1 <= k <= 173 for k in vistos))

    def test_nomes(self) -> None:
        self.assertEqual(bf.nome_beneficio(52), "Zona Franca: TI e comunicação")
        self.assertEqual(bf.nome_beneficio(161), "Pronac (Lei Rouanet)")
        self.assertEqual(bf.nome_beneficio(79), "Carnes")


if __name__ == "__main__":
    unittest.main()
