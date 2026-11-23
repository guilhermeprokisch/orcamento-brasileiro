import datetime as dt

from orcamento_pipeline import assembleias as a
from orcamento_pipeline import politicos as p
from orcamento_pipeline import politicos_estaduais as e


def test_documento_nunca_guarda_cpf():
    assert a.documento("16.551.514/0001-75") == "16551514000175"
    assert a.documento("123.456.789-01") == "PF"
    assert a.documento("586.***.***-53") == "PF"
    assert a.documento("") == ""


def test_fornecedor_pessoa_e_mei():
    assert a.fornecedor("FULANA DE TAL", "PF") == ""
    assert a.fornecedor("Renato Andre dos Reis 12345678901", "31254604000198") == "MEI"
    assert a.fornecedor("FULANO 123.456.789-01", "31254604000198") == "MEI"
    assert a.fornecedor("Auto Posto Mais Ltda.", "12345678000190") == "Auto Posto Mais Ltda."
    linha = a.linha("MG", 1, "Dep", 2025, 3, "Combustível", "FULANO 12345678901", "12345678000190", "10,5")
    assert linha[6] == "MEI" and linha[8] == 10.5


def test_valor():
    assert a.valor("R$ 1.234,56") == 1234.56
    assert a.valor("905.00") == 905.0
    assert a.valor(12) == 12.0
    assert a.valor("") == 0.0


def test_categorias_estaduais():
    assert a.categoria("A - COMBUSTÍVEIS E LUBRIFICANTES") == "Combustível"
    assert a.categoria("02 -  COMUNICAÇÃO, TELEFONE E DADOS") == "Telefone, internet e correio"
    assert a.categoria("H - SERV.UTIL.PÚBLICA (TELEF.MÓVEL/FIXA, ENERGIA, ÁGUA, GÁS ETC)") == "Telefone, luz e água"
    assert a.categoria("N - MORADIA") == "Moradia"
    assert a.categoria("REFERE-SE A DISPONIBILIZACAO DO BENEFICIO ALIMENTACAO, DE ABRIL/2025") == "Vale-alimentação e refeição"
    assert a.categoria("CONSULTORIAS E TRABALHOS TÉCNICOS") == "Consultorias e assessorias"


def test_empresa_de_uma_pessoa_pelo_nome():
    assert p.parece_pessoa("RACHEL SCHEIN")
    assert p.parece_pessoa("Alysson Matheus Silva de Santana Sociedade Individual")
    assert p.parece_pessoa("MEI")
    assert not p.parece_pessoa("NAVIGATORS COMUNICAÇÃO E MARKETING LTDA")
    assert not p.parece_pessoa("GOL LINHAS AÉREAS S.A.")
    assert not p.parece_pessoa("MEIRELES CONSTRUÇÕES LTDA")
    assert p.uma_pessoa_pelo_nome("35.596.258 JOSE FRANCISCO DE ABREU NETO")
    assert not p.uma_pessoa_pelo_nome("4TEMPOS PRODUTORA")


def test_resumo_de_verba_soma_pessoas():
    linhas = [("Combustível", "AUTO POSTO X LTDA", "11111111000191", 100.0, 1),
              ("Escritório e manutenção", "", "PF", 50.0, 1),
              ("Consultorias e assessorias", "RACHEL SCHEIN", "22222222000191", 30.0, 2)]
    r = p.resumo_linhas(linhas, {})
    assert r["total"] == 180 and r["meses"] == 2
    assert r["pessoas"] == [1, 50] and r["pessoaEmpresa"] == [1, 30]
    assert [f[0] for f in r["fornecedores"]] == ["Auto Posto X Ltda"]


def test_salario_do_governador_com_saida(monkeypatch):
    class Hoje(dt.date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 23)
    monkeypatch.setattr(e.dt, "date", Hoje)
    s = e.salario_governador("SP", 2025)
    assert s["total"] == round(6 * 34572.89 + 6 * 36301.53 + 36301.53)
    mg = e.salario_governador("MG", 2026)          # saiu em 22/03/2026
    assert mg["meses"] == round(2 + 21 / 30, 2)
    assert e.salario_governador("GO", 2026) is None  # só sabemos que saiu em 2026
    assert e.salario_governador("MT", 2025) is None  # a conferir
    assert e.salario_governador("TO", 2023) is None  # falta a lei de 2023


def test_ligar_assembleia_pelo_nome():
    eleitos = [{"chave": "tse-1", "uf": "SP", "urna": "Eduardo Suplicy", "completo": "EDUARDO MATARAZZO SUPLICY"},
               {"chave": "tse-2", "uf": "MS", "urna": "Paulo Corrêa", "completo": "PAULO JOSE ARAUJO CORREA"}]
    deps = {"SP": {("SP-300693", "Eduardo Suplicy")}, "MS": {("MS-PAULO CORRÊA", "Dep. Paulo Corrêa")}}
    assert e.ligar_assembleia(eleitos, deps) == {"tse-1": ["SP-300693"], "tse-2": ["MS-PAULO CORRÊA"]}


def test_ligar_com_titulo_e_nome_contido():
    eleitos = [{"chave": "tse-1", "uf": "SP", "urna": "Capitão Conte Lopes", "completo": "ROBERVAL CONTE LOPES LIMA"},
               {"chave": "tse-2", "uf": "MS", "urna": "Coronel David", "completo": "DAVID JOSE"},
               {"chave": "tse-3", "uf": "CE", "urna": "Alysson Aguiar", "completo": "ALYSSON AGUIAR X"}]
    deps = {"SP": {("SP-1", "Conte Lopes")}, "MS": {("MS-CEL. DAVID", "Cel. David")},
            "CE": {("CE-ALYSSON AGUIAR", "ALYSSON AGUIAR"), ("CE-ALYSSON AGUIAR.", "ALYSSON AGUIAR."),
                   ("CE-ALYSSON AGUYIAR", "ALYSSON AGUYIAR")}}
    r = e.ligar_assembleia(eleitos, deps)
    assert r["tse-1"] == ["SP-1"] and r["tse-2"] == ["MS-CEL. DAVID"]
    assert sorted(r["tse-3"]) == ["CE-ALYSSON AGUIAR", "CE-ALYSSON AGUIAR.", "CE-ALYSSON AGUYIAR"]


def test_homonimos_na_assembleia_nao_ligam():
    eleitos = [{"chave": "tse-1", "uf": "CE", "urna": "Fulano", "completo": "FULANO DE TAL"}]
    deps = {"SP": {("SP-1", "Fulano"), ("SP-2", "FULANO")}}
    eleitos[0]["uf"] = "SP"
    assert e.ligar_assembleia(eleitos, deps) == {}


def test_estadual_e_federal_da_mesma_pessoa():
    federal = {"chave": "camara-1", "casa": "camara", "uf": "SP", "feminino": True, "cargo": "Deputado federal",
               "anos": {"2023": {"cota": {"mes": [100] + [0] * 11}}}}
    estadual = {"chave": "tse-9", "casa": "assembleia", "uf": "SP", "feminino": True, "cargo": "Deputada estadual",
                "anos": {"2025": {"verba": {"mes": [0] * 9 + [10, 10, 10]}, "salario": 1}}}
    p.ligar_mesma_pessoa([federal, estadual], {"camara-1": "BRUNA DIAS FURLAN", "tse-9": "Bruna Dias Furlan"})
    assert estadual["atual"] and not federal["atual"]
    assert federal["cargo"] == "Deputada federal"
    assert federal["outros"][0]["chave"] == "tse-9"
