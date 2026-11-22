"""Testes da dívida ativa (divida_ativa.py), sem rede: as somas e as regras de privacidade.

    uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from orcamento_pipeline import divida_ativa as da

CAB = ("CPF_CNPJ;TIPO_PESSOA;TIPO_DEVEDOR;NOME_DEVEDOR;UF_DEVEDOR;UNIDADE_RESPONSAVEL;NUMERO_INSCRICAO;"
       "TIPO_SITUACAO_INSCRICAO;SITUACAO_INSCRICAO;RECEITA_PRINCIPAL;DATA_INSCRICAO;INDICADOR_AJUIZADO;VALOR_CONSOLIDADO")
CPF_MASCARADO = "XXX982247XX"
PESSOA = "MARIA DA SILVA"
MEI = "JOSE SOUZA 52998224725"


def linha(doc, pessoa, devedor, nome, sit, aj, valor, uf="PB"):
    return f"{doc};{pessoa};{devedor};{nome};{uf};PB;1;{sit};X;Y;01/01/2020;{aj};{valor}"


LINHAS = [
    linha("35.992.959/0001-35", "Pessoa jurídica", "PRINCIPAL", "CONSTRUTORA BOA OBRA LTDA", "Em cobrança", "SIM", "1000.50"),
    linha("35.992.959/0001-35", "Pessoa jurídica", "PRINCIPAL", "CONSTRUTORA BOA OBRA LTDA", "Benefício Fiscal", "NAO", "200"),
    # O sócio corresponsável repete o mesmo débito: não pode contar duas vezes.
    linha("XXX111222XX", "Pessoa física", "CORRESPONSAVEL", "SOCIO DA CONSTRUTORA", "Em cobrança", "SIM", "1000.50"),
    linha(CPF_MASCARADO, "Pessoa física", "PRINCIPAL", PESSOA, "Em cobrança", "NAO", "300"),
    linha("11.222.333/0001-81", "Pessoa jurídica", "PRINCIPAL", MEI, "Garantia", "SIM", "5000"),
    linha("44.555.666/0001-00", "Pessoa jurídica", "PRINCIPAL", "MUNICIPIO DE CAMPINA", "Suspenso por decisão judicial", "NAO", "700"),
    linha("77.888.999/0001-11", "Pessoa jurídica", "PRINCIPAL", "EMPRESA SEM CADASTRO SA", "Em cobrança", "NAO", "50"),
]


class DividaAtiva(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.zip = self.tmp / "nao_prev.zip"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("arquivo_lai_SIDA_1_202609.csv", "\n".join([CAB, *LINHAS]).encode("latin-1"))
        # Cadastro já em cache: cnpj; município SIAFI; ativa; natureza jurídica.
        (self.tmp / "cadastro-2026-11.csv").write_text(
            "35992959000135;2051;1;2062\n11222333000181;2051;0;2135\n44555666000100;2051;1;1244\n77888999000111;0;-1;\n",
            encoding="utf-8")

    def montar(self) -> dict:
        dev = da.Devedores()
        dev.ler("nao_prev", self.zip)
        mun, ativa, nat = da.cadastro(dev, "2026-11", self.tmp)
        with mock.patch.object(da, "siafi_para_ibge", return_value={"2051": "2504009"}):
            return da.montar(dev, mun, ativa, nat, "2026_trimestre_03", "2026-11")

    def test_somas(self) -> None:
        doc = self.montar()
        b = doc["brasil"]
        self.assertEqual(b["total"], round(1000.5 + 200 + 5000 + 700 + 50) + 300)  # sem o corresponsável
        self.assertEqual(b["pessoas"], [300, 1])
        self.assertEqual(b["sem_cidade"], [50, 1])
        total, tipos, sit, empresas, publico, fechadas, maiores = doc["mun"]["2504009"]
        self.assertEqual(total, round(1000.5 + 200 + 5000 + 700))
        self.assertEqual(empresas, 3)
        self.assertEqual(publico, 700)
        self.assertEqual(fechadas, 5000)
        self.assertEqual(sit, [1000, 0, 200, 5000, 700])
        self.assertEqual(doc["uf"]["PB"][1:3], [300, 1])
        self.assertEqual(doc["posicao"], "09/2026")

    def test_privacidade(self) -> None:
        texto = json.dumps(self.montar(), ensure_ascii=False)
        for proibido in (CPF_MASCARADO, "982247", PESSOA, "SOCIO", "JOSE SOUZA", "52998224725"):
            self.assertNotIn(proibido, texto)
        nomes = [m[0] for m in json.loads(texto)["mun"]["2504009"][6]]
        self.assertEqual(nomes, ["CONSTRUTORA BOA OBRA LTDA", "MUNICIPIO DE CAMPINA"])

    def test_situacao_da_empresa(self) -> None:
        maiores = self.montar()["mun"]["2504009"][6]
        self.assertEqual(maiores[0][1:], ["35.992.959/0001-35", 1200, da.S["justica"]])


if __name__ == "__main__":
    unittest.main()
