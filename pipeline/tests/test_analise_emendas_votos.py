import numpy as np

from orcamento_pipeline import analise_emendas_votos as a


def test_chave_tira_acento_e_titulo():
    assert a.chave("Dep. André Fernandes") == "andre fernandes"
    # o TSE grafa o mesmo nome com e sem acento conforme o ano
    assert a.chave("ROGÉRIO CORREIA DE MOURA BAPTISTA") == a.chave("ROGERIO CORREIA DE MOURA BAPTISTA")


def test_bloco_junta_fusoes_e_federacoes():
    assert a.bloco("PTB") == a.bloco("PATRIOTA") == "PRD"
    assert a.bloco("PSC") == "PODE"
    assert a.bloco("PT") == a.bloco("PC do B") == a.bloco("PV")
    assert a.bloco("PL") == "PL"


def test_blocos_da_coligacao_abre_a_federacao():
    col = "PP / REPUBLICANOS / Federação PSDB CIDADANIA (45-PSDB / 23-CIDADANIA) / UNIÃO"
    assert a.blocos_da_coligacao(col) == {"PP", "REPUBLICANOS", "PSDB+CIDADANIA", "UNIÃO"}
    assert a.blocos_da_coligacao("PARTIDO ISOLADO") == {"PARTIDO ISOLADO"}
    assert a.blocos_da_coligacao("#NULO") == set()


def test_ppml_dois_efeitos_recupera_o_coeficiente():
    rng = np.random.default_rng(0)
    n1, n2 = 60, 80
    g1, g2 = np.repeat(np.arange(n1), n2), np.tile(np.arange(n2), n1)
    x = rng.normal(size=n1 * n2) + 0.3 * rng.normal(size=n1)[g1]
    mu = np.exp(0.5 * x + rng.normal(size=n1)[g1] + rng.normal(size=n2)[g2])
    y = rng.poisson(mu).astype(float)
    b, ep, n = a.ppml_dois_efeitos(y, x[:, None], g1, g2)
    assert abs(b[0] - 0.5) < 3 * ep[0] and ep[0] < 0.05
    # agrupar por outra variável muda o erro padrão, não o coeficiente
    b2, ep2, _ = a.ppml_dois_efeitos(y, x[:, None], g1, g2, agrupar=g2)
    assert abs(b2[0] - b[0]) < 1e-9


def test_ppml_dois_efeitos_tira_grupos_so_com_zero():
    g1 = np.array([0, 0, 1, 1, 2, 2])
    g2 = np.array([0, 1, 0, 1, 0, 1])
    y = np.array([3.0, 5.0, 2.0, 7.0, 0.0, 0.0])   # o grupo 2 de g1 só tem zero
    _, _, n = a.ppml_dois_efeitos(y, np.array([0.1, 0.9, 0.4, 0.2, 0.5, 0.3])[:, None], g1, g2)
    assert n == 4
