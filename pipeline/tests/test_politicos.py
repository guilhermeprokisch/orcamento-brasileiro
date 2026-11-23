from orcamento_pipeline import politicos as p


def test_slug_igual_ao_das_emendas():
    from orcamento_pipeline.fichas_emendas import slug as slug_emendas
    for nome in ["Tabata Amaral", "Acácio Favacho", "ROMÁRIO", "Pastor Henrique Vieira"]:
        assert p.slug(nome) == slug_emendas(nome)


def test_nome_da_empresa_perde_o_cpf():
    assert p.limpa_nome_empresa("FULANO DE TAL 12345678901") == "FULANO DE TAL"
    assert p.limpa_nome_empresa("FULANO 123.456.789-01 ME") == "FULANO ME"
    assert p.limpa_nome_empresa("SJR IMOVEIS LTDA") == "SJR IMOVEIS LTDA"


def test_tipo_de_fornecedor():
    nat = {"12345678": p.EMPRESARIO_INDIVIDUAL, "87654321": "2062"}
    assert p.tipo_fornecedor("12345678000190", "QUALQUER", nat) == "pessoa_empresa"
    assert p.tipo_fornecedor("87654321000190", "EMPRESA LTDA", nat) == "empresa"
    assert p.tipo_fornecedor("11111111000190", "FULANO 12345678901", nat) == "pessoa_empresa"
    assert p.tipo_fornecedor("12345678901", "FULANO", nat) == "pessoa"
    assert p.tipo_fornecedor("586.***.***-53", "FULANA", nat) == "pessoa"
    assert p.tipo_fornecedor("", "SEM DOC", nat) == "outro"


def test_categorias():
    assert p.categoria("DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.", p.CATEGORIAS_CAMARA) == "Divulgação do mandato"
    assert p.categoria("PASSAGEM AÉREA - SIGEPA", p.CATEGORIAS_CAMARA) == "Passagens"
    assert p.categoria("LOCAÇÃO OU FRETAMENTO DE AERONAVES", p.CATEGORIAS_CAMARA) == "Aluguel de avião"
    assert p.categoria("Aluguel de imóveis para escritório político", p.CATEGORIAS_SENADO) == "Aluguel do escritório"
    assert p.categoria(None, p.CATEGORIAS_SENADO) == "Outros"


def test_teto_e_subsidio():
    assert p.teto_camara("SP", "2025-06") == 42837.33
    assert p.teto_camara("SP", "2026-03") == 48727.46
    assert p.subsidio("2025-01") == 44008.52
    assert p.subsidio("2025-02") == 46366.19


def test_receitas_de_campanha():
    assert p.grupo_receita("FUNDO ESPECIAL", "Recursos de partido político") == "Fundo eleitoral"
    assert p.grupo_receita("FUNDO PARTIDARIO", "Recursos de partido político") == "Fundo partidário"
    assert p.grupo_receita("OUTROS RECURSOS", "Recursos de pessoas físicas") == "Pessoas físicas"
    assert p.grupo_receita("OUTROS RECURSOS", "Recursos próprios") == "Recursos próprios"


def _pol(chave, casa, uf, mes_ano, feminino=False, cargo="Deputado federal"):
    ano, mes = mes_ano
    meses = [0] * 12
    meses[mes - 1] = 100
    return {"chave": chave, "casa": casa, "uf": uf, "feminino": feminino, "cargo": cargo,
            "anos": {str(ano): {"cota": {"mes": meses}}}}


def test_mesma_pessoa_em_duas_casas():
    dep = _pol("camara-1", "camara", "MS", (2023, 1))
    sen = _pol("senado-2", "senado", "MS", (2025, 6), feminino=True, cargo="Senador")
    p.ligar_mesma_pessoa([dep, sen], {"camara-1": "TEREZA CRISTINA CORREA DA COSTA DIAS", "senado-2": "Tereza Cristina Corrêa da Costa Dias"})
    assert sen["atual"] and not dep["atual"]
    assert dep["cargo"] == "Deputada federal" and sen["cargo"] == "Senadora"
    assert dep["outros"][0]["chave"] == "senado-2" and dep["outros"][0]["periodo"] == "jun/2025"


def test_pai_e_filho_na_mesma_casa_nao_se_juntam():
    pai = _pol("camara-1", "camara", "PI", (2023, 1))
    filho = _pol("camara-2", "camara", "PI", (2025, 6))
    p.ligar_mesma_pessoa([pai, filho], {"camara-1": "ÁTILA FREITAS LIRA", "camara-2": "ÁTILA DE MELO LIRA"})
    assert pai["atual"] and filho["atual"] and not pai["outros"] and not filho["outros"]
