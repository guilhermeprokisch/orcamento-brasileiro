"""Preço pago comparado: o casamento da descrição livre com a lista de remédios e a comparação com as compras parecidas."""

from orcamento_pipeline.precos import casar, comparar, por_ente


def test_casa_o_mesmo_remedio_escrito_de_jeitos_diferentes():
    for descricao, unidade in [
        ("LOSARTANA POTÁSSICA 50MG COMPRIMIDO", "COM"),
        ("LOSARTAN 50MG", "COM"),
        ("LOSARTANA POT. 50 MG", "CP"),
        ("14016671 - LOSARTANA POTÁSSICA 50 MG BR0268856 COMPRIMIDO", "COM"),
        ("LOSARTANA POTÁSSICA 50 MG: A) FORMA FARMACÊUTICA: COMPRIMIDO;B) VIA DE ADMINISTRAÇÃO ORAL", "UN"),
    ]:
        assert casar(descricao, unidade) == 268856, descricao
    assert casar("DIPIRONA SODICA 500 MG/ML INJETAVEL AMP 2 ML", "AMP") == 268252
    assert casar("LEVOTIROXINA SODICA 50MCG", "COMP") == 268123
    assert casar("OMEPRAZOL 20MG CAPSULAS", "UNIDADE") == 267712


def test_nao_casa_outro_remedio_outra_dose_ou_outra_unidade():
    for descricao, unidade in [
        ("LOSARTANA POTÁSSICA 50 MG + HIDROCLOROTIAZIDA 12,5 MG", "COM"),   # associação
        ("LOSARTANA POTASSICA 50 MG C\\ 30CP", "ENV"),                        # embalagem
        ("ESOMEPRAZOL MAGNÉSIO 40 MG", "COM"),                               # outro princípio ativo
        ("OMEPRAZOL 40MG/ML", "UN"),                                         # solução
        ("ESOMEPRAZOL MAGNÉSIO 40 MG CX COM 28 CP", "UN"),                   # caixa
        ("AMOXICILINACLAVULONATO POTASSIO 500 MG  125 MG", "CP"),           # duas doses
        ("BUTILBROMETO DE ESCOPOLAMINA  DIPIRONA - 4MG/ML  500MG/ML", "AMP"),
        ("DIPIRONA 500MG/ML GOTAS", "FR"),
        ("METFORMINA 500 MG XR", "COMP"),
        ("PREDNISOLONA 20 MG", "CP"),
    ]:
        assert casar(descricao, unidade) is None, descricao


def _compra(preco, qtd, comprador, ibge=None, esfera="M", uf="SP"):
    return {"codigo": 268856, "ano": 2026, "data": "2026-04-10", "preco": preco, "qtd": qtd, "esfera": esfera, "uf": uf,
            "ibge": ibge, "comprador": comprador, "id_comprador": comprador, "fornecedor": "", "modalidade": "pregão", "link": "", "fonte": "c"}


def test_compara_com_as_compras_de_quantidade_parecida_e_tira_erro_de_unidade():
    compras = [_compra(0.05, 1000 * (i + 1), f"P{i}", ibge=3500000 + i) for i in range(30)]
    compras.append(_compra(0.31, 20000, "Cara", ibge=3599999))
    compras.append(_compra(9.99, 20000, "Caixa", ibge=3599998))   # 200 vezes: preço da caixa, fica de fora
    resumo, aceitas = comparar(compras)
    r = resumo[(268856, 2026)]
    assert r["fora"] == 1
    assert r["mediana"] == 0.05
    cara = next(x for x in aceitas if x["comprador"] == "Cara")
    assert round(cara["razao"], 1) == 6.2
    assert round(cara["a_mais"]) == 5200
    mun, _ = por_ente(aceitas)
    assert mun["3599999"]["n_caras"] == 1 and "3599998" not in mun


def test_sem_compras_suficientes_o_remedio_nao_tem_mediana():
    compras = [_compra(0.05, 1000, f"P{i}") for i in range(15)]
    resumo, aceitas = comparar(compras)
    assert resumo == {} and aceitas == []
