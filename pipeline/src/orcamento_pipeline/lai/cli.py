"""Pedidos pela Lei de Acesso à Informação (Lei 12.527/2011) pelos formulários dos órgãos, com um navegador que preenche
tudo e para só no que é da pessoa: login, CAPTCHA e o OK antes de enviar.

    uv run --extra lai lai configurar                    # cria ~/.config/orcamento-br/lai.toml para os seus dados
    uv run --extra lai lai orgaos                        # os formulários que o script sabe preencher
    uv run --extra lai lai enviar ALMG pedido.txt        # preenche, mostra, pergunta e envia
    uv run --extra lai lai enviar ALMG pedido.txt --ensaio   # preenche e para sem enviar
    uv run --extra lai lai prazos                        # os pedidos enviados e o prazo de cada um
    uv run --extra lai lai inspecionar <URL>             # lista os campos de um formulário novo

O arquivo do pedido: a primeira linha é "Assunto: ...", depois uma linha em branco e o texto. No texto, {nome} e
{email} viram os dados da pessoa (para a assinatura). Os textos prontos ficam em docs/pedidos-lai/textos/.

Os dados da pessoa ficam fora do repositório (~/.config/orcamento-br/lai.toml); a captura de tela de cada envio, que
os mostra, também (~/.config/orcamento-br/lai-comprovantes/). O registro dos pedidos (docs/pedidos-lai/registro.csv)
não tem dado pessoal.
"""

from __future__ import annotations

import argparse
import datetime as dt
import tempfile
from pathlib import Path

from . import navegador, registro
from .formularios import FORMULARIOS, Pedido, achar_protocolo
from .pessoa import Pessoa, carregar, criar_modelo

COMPROVANTES = Path.home() / ".config" / "orcamento-br" / "lai-comprovantes"

# Só para o ensaio sem os dados reais: valores que nenhum formulário aceitaria como verdadeiros.
FICTICIA = Pessoa(nome="Teste Ensaio", cpf="000.000.000-00", nascimento="01/01/1990", sexo="Masculino",
                  escolaridade="Ensino Superior", rg="0000000", rg_orgao="SSP", rg_uf="SP", email="teste@example.com",
                  ddd="11", telefone="900000000", cep="01001-000", uf="SP", municipio="São Paulo",
                  logradouro="Praça da Sé", numero="0", bairro="Sé")


def ler_pedido(orgao: str, arquivo: Path, pessoa: Pessoa) -> Pedido:
    linhas = arquivo.read_text(encoding="utf-8").strip().splitlines()
    if not linhas or not linhas[0].lower().startswith("assunto:"):
        raise SystemExit(f"{arquivo}: a primeira linha tem de ser 'Assunto: ...'")
    assunto = linhas[0].split(":", 1)[1].strip()
    texto = "\n".join(linhas[1:]).strip().replace("{nome}", pessoa.nome).replace("{email}", pessoa.email)
    return Pedido(orgao, assunto, texto)


def enviar(orgao: str, arquivo: Path, ensaio: bool, ficticia: bool, janela: bool) -> None:
    f = FORMULARIOS.get(orgao.upper())
    if not f:
        raise SystemExit(f"Não sei preencher o formulário de {orgao}. Veja `lai orgaos`.")
    pessoa = FICTICIA if ficticia else carregar()
    if ficticia:   # um "documento" de teste para os formulários que pedem anexo
        doc = Path(tempfile.gettempdir()) / "lai-documento-ficticio.txt"
        doc.write_text("documento de teste\n", encoding="utf-8")
        pessoa.documento = str(doc)
    faltam = pessoa.faltam(f.campos)
    if faltam:
        raise SystemExit(f"O formulário de {f.orgao} pede: {', '.join(faltam)}. Preencha em ~/.config/orcamento-br/lai.toml.")
    pedido = ler_pedido(f.orgao, arquivo, pessoa)
    navegador.ENSAIO = ensaio
    print(f"{f.nome}: {f.url}")
    if f.obs:
        print(f"  {f.obs}")
    with navegador.abrir(visivel=janela) as p:
        p.goto(f.url, wait_until="domcontentloaded")
        navegador.assentar(p)
        if f.pronto:
            p.wait_for_selector(f.pronto, state="visible")
        if f.login:
            navegador.esperar_pessoa("Faça o login no site do órgão.")
        f.preencher(p, pedido, pessoa)
        if f.captcha:
            navegador.esperar_pessoa("Resolva o CAPTCHA (o script não resolve).")
        COMPROVANTES.mkdir(parents=True, exist_ok=True)
        base = COMPROVANTES / f"{dt.date.today().isoformat()}-{f.orgao}"
        p.screenshot(path=f"{base}-preenchido.png", full_page=True)
        if ensaio:
            print(f"Ensaio: preenchido e não enviado. Captura em {base}-preenchido.png")
            return
        if f.enviar is None:
            navegador.esperar_pessoa("Confira, avance as etapas que faltam e conclua o envio na janela.")
        else:
            if not navegador.confirmar(f"Confira a janela. Enviar o pedido a {f.nome}?"):
                print("Não enviado.")
                return
            f.enviar(p)
            navegador.assentar(p)
            p.wait_for_timeout(2000)
        p.screenshot(path=f"{base}-enviado.png", full_page=True)
        protocolo = achar_protocolo(p.locator("body").inner_text())
        if protocolo:
            print(f"Protocolo achado na página: {protocolo}")
        else:
            protocolo = input("Não achei o protocolo na página. Digite-o (ou Enter, se não apareceu): ").strip() or None
    linha = registro.anotar(f.orgao, pedido.assunto, f"formulário: {f.url}", protocolo, obs=f.obs)
    print(f"Anotado em {registro.ARQUIVO.name}: prazo {linha['prazo']} (com prorrogação, {linha['prazo_prorrogado']}).")


def prazos() -> None:
    hoje = dt.date.today()
    for r in registro.ler():
        falta = (dt.date.fromisoformat(r["prazo"]) - hoje).days
        aviso = "" if r["situacao"] != "aguardando" else (
            f"faltam {falta} dias" if falta >= 0 else
            "vencido: cabe recurso" if dt.date.fromisoformat(r["prazo_prorrogado"]) < hoje else "em prorrogação")
        print(f"{r['orgao']:8} {r['enviado_em']}  prazo {r['prazo']}  {r['situacao']:10} {aviso}  {r['protocolo']}")


def main() -> None:
    p = argparse.ArgumentParser(prog="lai", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("configurar", help="cria o arquivo com os seus dados")
    sub.add_parser("orgaos", help="os formulários que o script preenche")
    sub.add_parser("prazos", help="os pedidos enviados e os prazos")
    e = sub.add_parser("enviar", help="preenche e envia um pedido")
    e.add_argument("orgao")
    e.add_argument("arquivo", type=Path)
    e.add_argument("--ensaio", action="store_true", help="preenche e para, sem enviar")
    e.add_argument("--ficticia", action="store_true", help="no ensaio, usa dados de teste em vez dos seus")
    e.add_argument("--sem-janela", action="store_true", help="no ensaio, sem abrir a janela do navegador")
    i = sub.add_parser("inspecionar", help="lista os campos de um formulário")
    i.add_argument("url")
    i.add_argument("--saida", type=Path)
    a = p.parse_args()

    if a.cmd == "configurar":
        print(f"Preencha os seus dados em {criar_modelo()} (só este computador lê o arquivo).")
    elif a.cmd == "orgaos":
        for f in FORMULARIOS.values():
            marcas = ", ".join(m for m, v in (("CAPTCHA", f.captcha), ("login", f.login), ("envio manual", f.enviar is None)) if v)
            print(f"{f.orgao:8} {f.nome}{f' ({marcas})' if marcas else ''}")
    elif a.cmd == "prazos":
        prazos()
    elif a.cmd == "enviar":
        if (a.ficticia or a.sem_janela) and not a.ensaio:
            raise SystemExit("--ficticia e --sem-janela só valem com --ensaio.")
        enviar(a.orgao, a.arquivo, a.ensaio, a.ficticia, janela=not a.sem_janela)
    elif a.cmd == "inspecionar":
        for c in navegador.inspecionar(a.url, a.saida):
            if c["visivel"]:
                print(f"{c['tag']:8} {c['tipo']:10} {c['nome'] or c['id']:40} {c['rotulo']}{' *' if c['obrigatorio'] else ''}")


if __name__ == "__main__":
    main()
