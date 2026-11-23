"""Um formulário descrito como uma lista de passos, que tanto o navegador do script (Playwright) quanto a extensão do
Chrome (pipeline/lai-extensao/) sabem executar. Cada passo é um dicionário simples, para ir em JSON à extensão:

    {"acao": "preencher", "seletor": "[name=email]", "valor": "..."}
    {"acao": "marcar",    "seletor": "[name=tipo]"}                      # radio ou checkbox
    {"acao": "escolher",  "seletor": "[name=uf]", "texto": "Minas Gerais"}   # <select>, pelo texto da opção; espera
                                                                         # as opções carregarem (município depois da UF)

A extensão nunca clica em enviar: os formulários que ela preenche têm verificação anti-robô, e o envio fica com a pessoa.
"""

from __future__ import annotations


def preencher(seletor: str, valor: str) -> dict:
    return {"acao": "preencher", "seletor": seletor, "valor": valor}


def marcar(seletor: str) -> dict:
    return {"acao": "marcar", "seletor": seletor}


def opcao(seletor: str, texto: str) -> dict:
    return {"acao": "escolher", "seletor": seletor, "texto": texto}


def executar(pagina, passos: list[dict]) -> None:
    """Os mesmos passos no navegador do script."""
    from .formularios import escolher, escrever   # aqui dentro: formularios importa este módulo

    for p in passos:
        if p["acao"] == "preencher":
            escrever(pagina, p["seletor"], p["valor"])
        elif p["acao"] == "marcar":
            pagina.locator(p["seletor"]).first.check()
        elif p["acao"] == "escolher":
            escolher(pagina, p["seletor"], p["texto"])
        else:
            raise ValueError(f"passo desconhecido: {p['acao']}")
