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
        ("AMOXICILINA CLAV. DE POTASSIO 500MG", "COMPRIMIDOS"),
        ("2037406 - OMEPRAZOL MAGNÉSIO 20 MG *** JUDICIAL MARCA LOSEC MUPS® ***", "COMPRIMIDO"),
        ("AAS TAMPONADO 100 MG - COMPRIMIDO (SOMALGIN CARDIO OU SIMILAR)", "UN"),
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


def test_pncp_tira_o_que_vem_de_outra_fonte_e_o_preco_da_caixa(monkeypatch):
    from orcamento_pipeline import precos, precos_pncp

    def item(n, descricao, preco, estimado, ordem=1):
        return {"n": n, "codigo": 268856, "descricao": descricao, "unidade": "Unidade", "qtd": 1000, "estimado": estimado,
                "resultados": [{"preco": preco, "qtd": 1000, "data": "2026-09-20", "ordem": ordem, "cnpj": "1" * 14, "fornecedor": "DISTRIBUIDORA X LTDA"}]}

    compra = {"cnpj": "08787392000192", "ano": 2026, "seq": 53, "esfera": "M", "orgao": "MUNICIPIO DE TACIMA", "unidade": "PREFEITURA MUNICIPAL",
              "ibge": "2516409", "uf": "PB", "plataforma": "Bolsa Nacional De Compras - BNC", "publicacao": "2026-08-18",
              "itens": [item(1, "LOSARTANA POTASSICA 50MG", 0.04, 0.05),
                        item(2, "LOSARTANA POTASSICA 50MG COMP", 30.41, 0.04),          # preço da caixa: fica de fora
                        item(3, "LOSARTANA 50 MG + HIDROCLOROTIAZIDA 12,5 MG", 0.2, 0.3)]}   # a regra do casamento tira
    federal = {**compra, "plataforma": "Compras.gov.br", "seq": 54}             # já vem da pesquisa de preço
    gaucha = {**compra, "uf": "RS", "seq": 55}                                   # vem do LicitaCon
    monkeypatch.setattr(precos_pncp, "compras_guardadas", lambda: iter([compra, federal, gaucha]))
    linhas, acima = precos.compras_pncp(sem_rs=False)
    assert acima == 1
    assert [(x["preco"], x["ibge"], x["fonte"]) for x in linhas] == [(0.04, 2516409, "p")]
    assert linhas[0]["comprador"] == "Prefeitura Municipal (Municipio de Tacima)"
    assert linhas[0]["link"] == "https://pncp.gov.br/app/editais/08787392000192/2026/53"


def test_nome_do_comprador_no_pncp_diz_a_cidade():
    from orcamento_pipeline.precos import nome_pncp

    assert nome_pncp("Unidade Única", "MUNICIPIO DE CORONEL EZEQUIEL") == "Unidade Única (Municipio de Coronel Ezequiel)"
    assert nome_pncp("Prefeitura", "MUNICIPIO DE CORONEL EZEQUIEL") == "Prefeitura (Municipio de Coronel Ezequiel)"
    assert nome_pncp("Americana", "MUNICIPIO DE AMERICANA") == "Americana"
    assert nome_pncp("FUNDO MUNICIPAL DE SAUDE DE TUCURUI", "MUNICIPIO DE TUCURUI") == "Fundo Municipal de Saude de Tucurui"
    assert nome_pncp("", "MUNICIPIO DE ARATACA") == "Municipio de Arataca"
    assert nome_pncp("Fundo Municipal de Saude", "FUNDO MUNICIPAL DE SAUDE", "Tucuruí") == "Fundo Municipal de Saude (Tucuruí)"
