"""Um adaptador por formulário de pedido de acesso à informação. Cada um sabe abrir a página, preencher os campos com os
dados da pessoa e o texto do pedido, e clicar em enviar. O que o script não faz, e para esperando a pessoa: login,
CAPTCHA, e qualquer etapa que o adaptador ainda não conhece.

Para escrever um adaptador novo: `uv run --extra lai lai inspecionar <URL>` lista os campos da página.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from . import navegador, passos
from .navegador import esperar_pessoa
from .pessoa import Pessoa

UFS = {"AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
       "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais",
       "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
       "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia",
       "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
       "TO": "Tocantins"}


@dataclass
class Pedido:
    orgao: str
    assunto: str
    texto: str   # já com a assinatura

    @property
    def sem_assinatura(self) -> str:
        """Para campos que o órgão publica (o TCE-RS avisa que a solicitação é pública): o texto sem o nome no fim."""
        return re.split(r"\n\s*Atenciosamente,", self.texto)[0].strip()

    @property
    def com_assunto(self) -> str:
        """Para formulários sem campo de assunto."""
        return f"Assunto: {self.assunto}\n\n{self.texto}"


# ---------------------------------------------------------------- ajudantes

def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").strip().lower()


def escrever(alvo, seletor: str, valor: str, digitar: bool = False) -> None:
    """Preenche um campo, se houver valor. digitar=True para campos com máscara (CPF, data), que só aceitam teclas.
    Se o campo tiver limite de caracteres menor que o texto, para e avisa (não corta o pedido sem ninguém ver)."""
    if not valor:
        return
    campo = alvo.locator(seletor).first
    limite = campo.get_attribute("maxlength")
    if limite and limite.isdigit() and 0 < int(limite) < len(valor):
        campo.fill(valor[: int(limite)])
        esperar_pessoa(f"O campo {seletor} aceita só {limite} caracteres e o texto tem {len(valor)}. "
                       "Ajuste o texto na janela.")
        return
    if digitar:
        campo.click()
        campo.press_sequentially(re.sub(r"\D", "", valor), delay=30)
    else:
        campo.fill(valor)


def escolher(alvo, seletor: str, texto: str, tentativas: int = 20) -> bool:
    """Escolhe a opção de um <select> pelo texto, sem ligar para acento e maiúsculas. Espera as opções carregarem
    (o município costuma vir depois de escolher o estado)."""
    if not texto:
        return False
    campo = alvo.locator(seletor).first
    for _ in range(tentativas):
        opcoes = campo.locator("option").all_inner_texts()
        for o in opcoes:
            if _norm(o) == _norm(texto):
                campo.select_option(label=o)
                return True
        alvo.wait_for_timeout(500)
    print(f"  aviso: não achei a opção '{texto}' em {seletor}; escolha na janela.")
    return False


def achar_protocolo(texto: str) -> str | None:
    for padrao in (r"protocolo[^0-9]{0,40}?(\d[\d./-]{3,}\d)", r"\bn[º°o.]\s*(\d[\d./-]{3,}\d)",
                   r"\bnúmero[^0-9]{0,20}(\d[\d./-]{3,}\d)"):
        m = re.search(padrao, texto, re.I)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------- os formulários

@dataclass
class Formulario:
    orgao: str
    nome: str
    url: str
    preencher: Callable[[object, Pedido, Pessoa], None]
    enviar: Callable[[object], None] | None   # None: a pessoa clica em enviar (etapas que o adaptador não conhece)
    campos: list[str] = field(default_factory=list)   # dados da pessoa que o formulário exige
    captcha: bool = False
    login: bool = False
    obs: str = ""
    pronto: str = ""   # um campo que só aparece quando o formulário terminou de carregar (alguns redirecionam antes)
    # reCAPTCHA invisível: o site dá nota de "robô" ao navegador e recusa o navegador controlado pelo script. Aí o
    # script não disfarça o navegador: abre o formulário no navegador normal da pessoa e copia o texto para colar.
    colar: bool = False
    # Os passos para a extensão do Chrome (e para o script), quando o formulário é descrito assim.
    passos: Callable[[Pedido, Pessoa], list[dict]] | None = None


def _tce_se(p, pedido: Pedido, s: Pessoa) -> None:
    c = lambda nome: f'[name$="{nome}"]'
    escrever(p, c("tbxNome"), s.nome)
    escrever(p, c("tbxCpf"), s.cpf)
    escrever(p, c("tbxDtNascimento"), s.nascimento)
    escrever(p, c("tbxTelefone"), s.telefone_completo)
    escrever(p, c("tbxEmail"), s.email)
    escrever(p, c("tbxLogradouro"), s.logradouro)
    escrever(p, c("tbxNumero"), s.numero)
    escrever(p, c("tbxBairro"), s.bairro)
    escrever(p, c("tbxComplemento"), s.complemento)
    escrever(p, c("tbxCep"), s.cep)
    escrever(p, c("tbxMunicipio"), s.municipio)
    escrever(p, c("tbxUF"), s.uf)
    escrever(p, c("tbxAssunto"), pedido.assunto)
    escrever(p, c("tbxMensagem"), pedido.texto)


def passos_almg(pedido: Pedido, s: Pessoa) -> list[dict]:
    return [
        passos.preencher('[name="nomeCompleto"]', s.nome),
        passos.preencher('[name="telefonePrincipal"]', s.telefone_completo),
        passos.preencher('[name="email"]', s.email),
        passos.preencher('[name="cpf"]', s.cpf),
        passos.marcar('[name="endereco.resideNoBrasil"]'),   # o primeiro é "Sim"
        passos.opcao('[name="endereco.siglaUf"]', UFS.get(s.uf, s.uf)),
        passos.opcao('[name="endereco.municipio"]', s.municipio),
        passos.preencher('[name="mensagem"]', pedido.com_assunto),
    ]


def _alerj(p, pedido: Pedido, s: Pessoa) -> None:
    p.locator('[name="tpessoa"]').first.check()   # pessoa física
    escrever(p, '[name="cpf"]', s.cpf)
    escrever(p, '[name="nome"]', s.nome)
    escrever(p, '[name="email"]', s.email)
    escrever(p, '[name="c_email"]', s.email)
    endereco = ", ".join(x for x in (f"{s.logradouro} {s.numero}".strip(), s.complemento, s.bairro) if x)
    escrever(p, '[name="endereco"]', endereco)
    escrever(p, '[name="cidade"]', s.municipio)
    escrever(p, '[name="uf"]', s.uf)
    escrever(p, '[name="tel_1"]', f"{s.ddd} {s.telefone}".strip())
    escrever(p, '[name="cep"]', s.cep)
    escrever(p, '[name="nascimento"]', s.nascimento)
    escrever(p, '[name="pedido"]', pedido.com_assunto)


def _alerr(p, pedido: Pedido, s: Pessoa) -> None:
    """JSF: cada <select> recarrega parte do formulário por ajax e pode apagar o que já foi escrito. Escolhe um por
    vez, espera a recarga, escreve o texto por último e confere tudo no fim."""
    def esperar():
        navegador.assentar(p, 5)
        p.wait_for_timeout(1500)

    for _ in range(3):
        for campo, texto in (("tipoResposta", "E-mail"), ("codigoGrupo", "SIC"), ("codigoAssunto", "Pedido de Informacao")):
            sel = f'[id="form:{campo}:select"]'
            if _norm(p.locator(f"{sel} option:checked").inner_text()) != _norm(texto):
                escolher(p, sel, texto)
                esperar()
        escrever(p, '[id="form:solicitante:field"]', s.nome)
        escrever(p, '[id="form:cpf:fieldCpf:field"]', s.cpf, digitar=True)
        escrever(p, '[id="form:email:field"]', s.email)
        escrever(p, '[id="form:telefone:field"]', f"{s.ddd}{s.telefone}")   # até 13 caracteres
        escrever(p, '[id="form:sintese:fieldTextarea"]', pedido.com_assunto)   # sem campo de assunto; até 4.000
        esperar()
        assunto = p.locator('[id="form:codigoAssunto:select"] option:checked').inner_text()
        if _norm(assunto) == _norm("Pedido de Informacao") and p.locator('[id="form:sintese:fieldTextarea"]').input_value():
            return
    esperar_pessoa("O formulário da ALERR não guardou todos os campos; confira o assunto e a síntese na janela.")


def passos_alpb(pedido: Pedido, s: Pessoa) -> list[dict]:
    """osTicket (open.php), o sistema de chamados que vários órgãos usam como SIC."""
    return [
        passos.preencher('[name="name"]', s.nome),
        passos.preencher('[name="home_address"]', ", ".join(x for x in (f"{s.logradouro} {s.numero}".strip(), s.complemento) if x)),
        passos.preencher('[name="home_neigh"]', s.bairro),
        passos.preencher('[name="home_city"]', s.municipio),
        passos.preencher('[name="home_state"]', s.uf),
        passos.preencher('[name="home_zip"]', s.cep),
        passos.preencher('[name="email"]', s.email),
        passos.preencher('[name="phone"]', s.telefone_completo),
        passos.preencher('[name="user_doc"]', s.cpf),
        passos.preencher('[name="user_date_nasc"]', s.nascimento),
        passos.opcao('[name="topicId"]', "Finanças e Orçamento"),
        passos.preencher('[name="subject"]', pedido.assunto),
        passos.preencher('[name="message"]', pedido.texto),
    ]


def _tce_rs(p, pedido: Pedido, s: Pessoa) -> None:
    if s.documento:
        p.locator('[name="P91_ARQUIVO"]').set_input_files(s.documento)
    if s.documento_verso:
        p.locator('[name="P91_ARQUIVO_2"]').set_input_files(s.documento_verso)
    escrever(p, '[name="P91_NOME"]', s.nome)
    escrever(p, '[name="P91_CPF"]', s.cpf, digitar=True)
    escrever(p, '[name="P91_RG"]', s.rg)
    escolher(p, '[name="P91_UF_RG"]', s.rg_uf)
    escrever(p, '[name="P91_EMAIL"]', s.email)
    escrever(p, '[name="P91_EMAIL2"]', s.email)
    escrever(p, '[name="P91_DDD"]', s.ddd, digitar=True)
    escrever(p, '[name="P91_TELEFONE"]', s.telefone)
    escolher(p, '[name="P91_TIPO_REMETENTE"]', "Outros", tentativas=1)   # não há "cidadão" na lista
    escolher(p, '[name="P91_SEXO"]', s.sexo, tentativas=1)
    escolher(p, '[name="P91_ESCOLARIDADE"]', s.escolaridade, tentativas=1)
    escrever(p, '[name="P91_SOLICITACAO"]', pedido.sem_assinatura)   # o campo é público: sem o nome no fim


def _tce_pr(p, pedido: Pedido, s: Pessoa) -> None:
    """Etapa 1 (identificação) preenchida; as etapas 2 (descrição) e 3 (conclusão) o adaptador preenche no que
    reconhece, e a pessoa confere e conclui."""
    p.get_by_label("Identificado").first.check()
    p.get_by_label("Pessoa Física").first.check()
    escrever(p, '[name="NmCidadao"]', s.nome)
    escolher(p, '[name="IdTpTratamento"]', s.sexo, tentativas=1)
    escrever(p, '[name="NrAnoNascimento"]', s.nascimento[-4:])
    escrever(p, '[name="NrCPF"]', s.cpf, digitar=True)
    escrever(p, '[name="NrDocumento"]', s.rg)
    escrever(p, '[name="SgOrgaoExpedidor"]', s.rg_orgao)
    escrever(p, '[name="NrCelular"]', f"{s.ddd}{s.telefone}", digitar=True)
    escolher(p, '[name="IdDesejaSMS"]', "Não", tentativas=1)
    escrever(p, '[name="DsEmailCidadao"]', s.email)
    escrever(p, '[name="DsEmailCidadaoConfirmacao"]', s.email)
    escrever(p, '[name="NrCEP"]', s.cep, digitar=True)
    escolher(p, '[name="MunicipioCidadao_SgUf"]', UFS.get(s.uf, s.uf))
    escolher(p, '[name="IdMunicipioCidadao"]', s.municipio)
    escrever(p, '[name="DsLogradouro"]', s.logradouro)
    escrever(p, '[name="NrLogradouro"]', s.numero)
    escrever(p, '[name="DsCompLogradouro"]', s.complemento)
    escrever(p, '[name="NmBairro"]', s.bairro)
    if navegador.ENSAIO:   # no ensaio, não manda nem a identificação ao servidor
        return
    esperar_pessoa("Confira a identificação no TCE-PR. O script vai clicar em 'Próximo' e preencher a descrição.")
    p.locator('[name="btnValidarIdentificacao"], #btnValidarIdentificacao').first.click()
    navegador.assentar(p)
    assunto = p.get_by_label(re.compile("assunto", re.I))
    if assunto.count():
        assunto.first.fill(pedido.assunto)
    texto = p.locator("textarea:visible")
    if texto.count():
        texto.first.fill(pedido.texto)


def _clicar(seletor: str) -> Callable[[object], None]:
    return lambda p: p.locator(seletor).first.click()


DADOS_BASE = ["nome", "cpf", "email"]

FORMULARIOS: dict[str, Formulario] = {f.orgao: f for f in [
    Formulario("TCE-SE", "Tribunal de Contas do Estado de Sergipe", "https://www.tce.se.gov.br/SitePages/esic.aspx",
               _tce_se, _clicar('[name$="btnEnviarEmail"]'),
               DADOS_BASE + ["nascimento", "telefone", "logradouro", "numero", "bairro", "cep", "municipio", "uf"],
               obs="O protocolo chega por e-mail.", pronto='[name$="tbxNome"]'),
    Formulario("ALMG", "Assembleia Legislativa de Minas Gerais", "https://www.almg.gov.br/apps/fale-com/assembleia",
               lambda p, ped, s: passos.executar(p, passos_almg(ped, s)), lambda p: p.get_by_role("button", name=re.compile(r"^\s*Enviar\s*$")).click(),
               DADOS_BASE + ["uf", "municipio"], pronto='[name="nomeCompleto"]', colar=True, passos=passos_almg,
               obs="O reCAPTCHA invisível recusa o navegador do script (23/11/2026): a extensão preenche no seu Chrome e você clica em Enviar."),
    Formulario("ALERJ", "Assembleia Legislativa do Estado do Rio de Janeiro",
               "http://www2.alerj.rj.gov.br/leideacesso/formulario-2016.asp",
               _alerj, _clicar('input[type="submit"]'), DADOS_BASE + ["nascimento"], captcha=True, pronto='[name="nome"]'),
    Formulario("ALERR", "Assembleia Legislativa do Estado de Roraima",
               "http://grp.al.rr.leg.br/grp/acessoexterno/programaAcessoExterno.faces?codigo=68000",
               _alerr, _clicar('input[type="submit"][value="Salvar"]'), DADOS_BASE,
               obs="Depois de salvar, o sistema pergunta se quer o comprovante.", pronto='[id="form:sintese:fieldTextarea"]'),
    Formulario("ALPB", "Assembleia Legislativa do Estado da Paraíba", "https://www.al.pb.leg.br/sic/open.php",
               lambda p, ped, s: passos.executar(p, passos_alpb(ped, s)), _clicar('[name="submit_x"]'),
               DADOS_BASE + ["nascimento", "telefone", "logradouro", "numero", "bairro", "cep", "municipio", "uf"],
               captcha=True, pronto='[name="name"]', passos=passos_alpb,
               obs="A Ouvidoria pede que o pedido venha por este portal, não por e-mail. O CAPTCHA recusou o navegador do script (23/11/2026): use --chrome."),
    Formulario("TCE-RS", "Tribunal de Contas do Estado do Rio Grande do Sul", "https://portal.tce.rs.gov.br/aplicprod/f?p=20000:91",
               _tce_rs, _clicar('#CRIAR, [name="CRIAR"]'), DADOS_BASE + ["rg", "rg_uf", "documento"], captcha=True,
               obs="Pede a cópia do documento de identidade. A solicitação é pública no site do TCE-RS.", pronto='[name="P91_NOME"]'),
    Formulario("TCE-PR", "Tribunal de Contas do Estado do Paraná",
               "https://servicos.tce.pr.gov.br/TCEPR/Tribunal/Ouvidoria/Atendimentos/Atendimento/PedidoAcessoInformacao",
               _tce_pr, None, DADOS_BASE + ["rg", "rg_orgao", "cep", "uf", "municipio", "logradouro", "numero", "bairro"],
               obs="Formulário em 3 etapas: o script preenche a 1ª e o que reconhecer da 2ª; você confere e conclui.",
               pronto='[name="NmCidadao"]'),
]}
