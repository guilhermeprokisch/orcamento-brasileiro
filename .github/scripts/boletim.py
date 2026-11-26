#!/usr/bin/env python3
"""O e-mail mensal de quem segue uma cidade ou um estado (só biblioteca padrão).

Para cada pessoa que confirmou, lê o resumo de cada lugar que ela segue
(https://orcamentobrasileiro.com.br/seguir/resumo/<alvo>.json, gerado por site/src/lib/resumo.ts),
compara a chave de cada seção com a do último e-mail mandado (coluna `enviado` no D1) e só manda
e-mail se alguma seção mudou. Um e-mail por pessoa, com um bloco por lugar.

Modos:
  boletim.py                          envia de verdade (precisa de todos os segredos)
  boletim.py --ensaio --saida DIR     lê o banco, monta os e-mails em DIR e não envia nem grava nada
  boletim.py --teste-para EMAIL --teste-alvos mun-4205407,uf-SC
                                      manda um exemplo, como primeiro e-mail, sem tocar no banco

Variáveis: CF_ACCOUNT_ID, CF_D1_TOKEN (permissão D1 Edit), D1_SEGUIR_ID, SMTP_SENHA,
SMTP_USUARIO (padrão: o remetente), SMTP_HOST (mail.inout.email), SMTP_PORTA (465),
BOLETIM_DE (boletim@orcamentobrasileiro.com.br), SITE (https://orcamentobrasileiro.com.br).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import pathlib
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

SITE = os.environ.get("SITE", "https://orcamentobrasileiro.com.br").rstrip("/")
DE = os.environ.get("BOLETIM_DE", "boletim@orcamentobrasileiro.com.br")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
NUMERAIS = {1: "Uma coisa entrou", 2: "Duas coisas entraram", 3: "Três coisas entraram",
            4: "Quatro coisas entraram", 5: "Cinco coisas entraram"}
DIAS_SEM_CONFIRMAR = 7
# O logo vai dentro do e-mail (cid:), não como link: aparece mesmo com imagens externas bloqueadas.
MARCA = pathlib.Path(__file__).resolve().parents[2] / "site" / "public" / "email" / "marca.png"
MARCA_CID = "marca@orcamentobrasileiro.com.br"
PAUSA_S = 1.5


# ---------------------------------------------------------------- banco (API do D1)

def d1(sql: str, params: list | None = None) -> list[dict]:
    conta, token, banco = (os.environ.get(k) for k in ("CF_ACCOUNT_ID", "CF_D1_TOKEN", "D1_SEGUIR_ID"))
    if not (conta and token and banco):
        sys.exit("Faltam CF_ACCOUNT_ID, CF_D1_TOKEN ou D1_SEGUIR_ID.")
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{conta}/d1/database/{banco}/query",
        data=json.dumps({"sql": sql, "params": params or []}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = json.load(r)
    except urllib.error.HTTPError as e:
        corpo = json.loads(e.read() or b"{}")
        msg = "; ".join(x.get("message", "") for x in corpo.get("errors", [])) or str(e)
        raise RuntimeError(f"D1: {msg}") from None
    if not corpo.get("success"):
        raise RuntimeError(f"D1: {corpo.get('errors')}")
    return corpo["result"][0].get("results", [])


def inscritos() -> dict[int, dict]:
    """Pessoas confirmadas e o que cada uma segue. Antes, apaga pedidos sem confirmação há 7 dias."""
    limite = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DIAS_SEM_CONFIRMAR)).isoformat()
    try:
        d1("DELETE FROM seguindo WHERE confirmado = 0 AND criado_em < ?", [limite])
        d1("DELETE FROM pessoas WHERE id NOT IN (SELECT pessoa_id FROM seguindo)")
        linhas = d1("""SELECT p.id, p.email, p.token, s.alvo, s.enviado
                       FROM seguindo s JOIN pessoas p ON p.id = s.pessoa_id
                       WHERE s.confirmado = 1 ORDER BY p.id, s.criado_em""")
    except RuntimeError as e:
        if "no such table" in str(e):
            return {}  # ninguém se inscreveu ainda: as tabelas nascem na primeira inscrição
        raise
    pessoas: dict[int, dict] = {}
    for l in linhas:
        p = pessoas.setdefault(l["id"], {"id": l["id"], "email": l["email"], "token": l["token"], "alvos": []})
        p["alvos"].append((l["alvo"], json.loads(l["enviado"]) if l["enviado"] else None))
    return pessoas


# ---------------------------------------------------------------- resumos

_cache: dict[str, dict | None] = {}


def resumo(alvo: str) -> dict | None:
    if alvo not in _cache:
        try:
            req = urllib.request.Request(f"{SITE}/seguir/resumo/{alvo}.json", headers={"User-Agent": "orcamento-boletim"})
            with urllib.request.urlopen(req, timeout=30) as r:
                _cache[alvo] = json.load(r)
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"  ! sem resumo para {alvo}: {e}", file=sys.stderr)
            _cache[alvo] = None
    return _cache[alvo]


def novidades(r: dict, enviado: dict | None) -> list[dict]:
    """As seções cuja chave mudou desde o último e-mail; no primeiro e-mail, todas."""
    return [s for s in r["secoes"] if not enviado or enviado.get(s["id"]) != s["chave"]]


# ---------------------------------------------------------------- o e-mail

e = html.escape


def juntar(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else f"{', '.join(xs[:-1])} e {xs[-1]}"


def link_sair(token: str, alvo: str | None = None) -> str:
    q = {"t": token, **({"a": alvo} if alvo else {})}
    return f"{SITE}/seguir/sair?{urllib.parse.urlencode(q)}"


def html_secao(s: dict) -> str:
    # Blocos em linha: descem inteiros quando não cabem (celular), sem quebrar o valor no meio.
    numeros = "".join(
        f"""<div style="display:inline-block;vertical-align:top;width:165px;margin:0 16px 14px 0;">
<div style="font-family:Georgia,serif;font-size:28px;font-weight:700;line-height:1.15;white-space:nowrap;color:{'#5c574c' if n.get('apagado') else '#191919'};">{e(n['valor'])}</div>
<div style="font-size:13px;line-height:1.35;color:#5c574c;">{e(n['rotulo'])}</div></div>"""
        for n in s["numeros"]
    )
    texto = f'<p style="margin:2px 0 0;font-size:15px;line-height:1.5;color:#3d3a33;">{e(s["texto"])}</p>' if s.get("texto") else ""
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #c9c2b2;margin:0 0 16px;">
<tr><td style="padding:22px;">
<h3 style="margin:0 0 14px;font-family:Georgia,serif;font-size:21px;line-height:1.25;color:#191919;">{e(s['pergunta'])}</h3>
<div style="font-size:0;">{numeros}</div>
{texto}</td></tr></table>"""


def html_lugar(r: dict, novas: list[dict], primeiro: bool, varios: bool) -> str:
    intro = ("Este é o primeiro e-mail: o resumo do que a página mostra hoje." if primeiro
             else f"{NUMERAIS.get(len(novas), f'{len(novas)} coisas entraram')} na página desde o último e-mail.")
    titulo_tag = "h2" if varios else "h1"
    retrato = ""
    if r.get("retrato"):
        linhas = "".join(
            f"""<tr><td style="padding:10px 0;border-bottom:1px solid #ddd6c6;font-size:15px;color:#191919;">{e(rot)}</td>
<td align="right" style="padding:10px 0;border-bottom:1px solid #ddd6c6;font-size:15px;white-space:nowrap;"><strong>{e(v)}</strong>{f'<br><span style="font-size:13px;color:#5c574c;">parecidas: {e(m)}</span>' if m else ''}</td></tr>"""
            for rot, v, m in r["retrato"]["linhas"]
        )
        # A frase vem do nosso próprio build, com <strong> já montado.
        retrato = f"""<p style="margin:28px 0 14px;padding-top:14px;border-top:1px solid #191919;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#3d3a33;">Para lembrar: o retrato de {r['retrato']['ano']}</p>
<p style="margin:0 0 14px;font-family:Georgia,serif;font-size:19px;line-height:1.5;color:#191919;">{r['retrato']['frase']}</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #c9c2b2;">{linhas}</table>"""
    return f"""<p style="margin:0 0 10px;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#0e6b3b;">Você segue {e(r['titulo'])}</p>
<{titulo_tag} style="margin:0 0 12px;font-family:Georgia,serif;font-size:{'28' if varios else '32'}px;line-height:1.15;color:#191919;">O que saiu de novo sobre as contas de {e(r['titulo'])}</{titulo_tag}>
<p style="margin:0 0 20px;font-size:16px;line-height:1.55;color:#3d3a33;">{e(intro)}</p>
{''.join(html_secao(s) for s in novas)}
{retrato}
<p style="margin:24px 0 36px;"><a href="{e(r['url'])}" style="display:inline-block;padding:15px 24px;background:#0e6b3b;color:#ffffff;text-decoration:none;font-weight:600;font-size:16px;">Ver a página de {e(r['titulo'])}</a></p>"""


def texto_lugar(r: dict, novas: list[dict]) -> str:
    partes = [f"O QUE SAIU DE NOVO SOBRE AS CONTAS DE {r['titulo'].upper()}", ""]
    for s in novas:
        partes.append(s["pergunta"])
        partes += [f"  {n['valor']} — {n['rotulo']}" for n in s["numeros"]]
        if s.get("texto"):
            partes.append(f"  {s['texto']}")
        partes.append("")
    partes.append(f"Ver a página: {r['url']}")
    return "\n".join(partes)


def montar(pessoa: dict, blocos: list[tuple[dict, list[dict], bool]]) -> EmailMessage:
    hoje = dt.date.today()
    mes = f"{MESES[hoje.month - 1].capitalize()} de {hoje.year}"
    titulos = [r["titulo"] for r, _, _ in blocos]
    if len(blocos) == 1:
        r, novas, primeiro = blocos[0]
        assunto = f"{r['titulo']}: o resumo das contas" if primeiro else f"{r['titulo']}: {juntar([s['curto'] for s in novas])}"
    else:
        assunto = f"{juntar(titulos)}: o que saiu de novo"
    varios = len(blocos) > 1
    corpo = "".join(html_lugar(r, n, p, varios) for r, n, p in blocos)
    sair_um = "".join(f'<a href="{e(link_sair(pessoa["token"], r["alvo"]))}" style="color:#0e6b3b;margin-right:16px;">Parar de seguir {e(r["titulo"])}</a> ' for r, _, _ in blocos)
    sair_tudo = link_sair(pessoa["token"])
    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{e(assunto)}</title></head>
<body style="margin:0;padding:0;background:#e9e4d8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9e4d8;"><tr><td align="center" style="padding:24px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#f7f4ec;font-family:Inter,Arial,sans-serif;">
<tr><td style="background:#191919;padding:20px 28px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="font-family:Georgia,serif;font-size:20px;font-weight:700;color:#f7f4ec;"><img src="cid:{MARCA_CID}" width="35" height="24" alt="" style="vertical-align:-4px;margin-right:10px;border:0;">Orçamento Brasileiro</td>
<td align="right" style="font-size:13px;color:#ddd6c6;">{mes}</td></tr></table></td></tr>
<tr><td style="padding:32px 28px 0;">{corpo}</td></tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;font-family:Inter,Arial,sans-serif;">
<tr><td style="padding:16px 28px 8px;font-size:13px;line-height:1.5;color:#3d3a33;">Você recebe este e-mail porque pediu para seguir {e(juntar(titulos))} no Orçamento Brasileiro. Os números vêm do Tesouro, da CGU, do Portal Nacional de Contratações Públicas e de outras fontes oficiais.</td></tr>
<tr><td style="padding:0 28px 32px;font-size:13px;line-height:1.8;">{sair_um}<a href="{e(sair_tudo)}" style="color:#0e6b3b;">Sair de tudo</a></td></tr>
</table></td></tr></table></body></html>"""

    texto = "\n\n".join(texto_lugar(r, n) for r, n, _ in blocos) + f"\n\n—\nPara parar de receber: {sair_tudo}\n"
    m = EmailMessage()
    m["From"] = formataddr(("Orçamento Brasileiro", DE))
    m["To"] = pessoa["email"]
    m["Subject"] = assunto
    m["Date"] = formatdate(localtime=False, usegmt=True)  # sem Date, o Gmail manda para o spam
    m["Message-ID"] = make_msgid(domain=DE.split("@")[1])
    m["Reply-To"] = "contato@orcamentobrasileiro.com.br"
    # Cancelar com um clique (RFC 8058): o POST vai para functions/api/sair.ts.
    m["List-Unsubscribe"] = f"<{SITE}/api/sair?t={urllib.parse.quote(pessoa['token'])}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    m.set_content(texto)
    m.add_alternative(doc, subtype="html")
    m.get_body(("html",)).add_related(MARCA.read_bytes(), "image", "png", cid=f"<{MARCA_CID}>",
                                      filename="marca.png", disposition="inline")
    return m


# ---------------------------------------------------------------- envio

class Correio:
    def __init__(self):
        self.senha = os.environ.get("SMTP_SENHA")
        if not self.senha:
            sys.exit("Falta SMTP_SENHA.")
        self.smtp: smtplib.SMTP_SSL | None = None

    def _abrir(self):
        self.smtp = smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "mail.inout.email"), int(os.environ.get("SMTP_PORTA", "465")), timeout=60)
        self.smtp.login(os.environ.get("SMTP_USUARIO", DE), self.senha)

    def mandar(self, m: EmailMessage):
        for tentativa in (1, 2):
            try:
                if not self.smtp:
                    self._abrir()
                self.smtp.send_message(m)
                return
            except (smtplib.SMTPServerDisconnected, ConnectionError, TimeoutError):
                self.smtp = None
                if tentativa == 2:
                    raise

    def fechar(self):
        if self.smtp:
            try:
                self.smtp.quit()
            except smtplib.SMTPException:
                pass


def principal():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ensaio", action="store_true", help="monta os e-mails sem enviar nem gravar")
    ap.add_argument("--saida", type=pathlib.Path, help="pasta para os e-mails do ensaio")
    ap.add_argument("--limite", type=int, default=400, help="no máximo tantos e-mails por rodada")
    ap.add_argument("--teste-para", help="manda um exemplo para este endereço, sem usar o banco")
    ap.add_argument("--teste-alvos", default="mun-4205407", help="lugares do exemplo, separados por vírgula")
    a = ap.parse_args()

    if a.teste_para:
        pessoa = {"id": 0, "email": a.teste_para, "token": "teste", "alvos": [(x.strip(), None) for x in a.teste_alvos.split(",")]}
        pessoas = {0: pessoa}
    else:
        pessoas = inscritos()
    print(f"{len(pessoas)} pessoa(s) com inscrição confirmada.")

    correio = None if a.ensaio else Correio()
    enviados = 0
    try:
        for p in pessoas.values():
            if enviados >= a.limite:
                print(f"Limite de {a.limite} e-mails atingido; o resto fica para a próxima rodada.")
                break
            blocos = []
            for alvo, enviado in p["alvos"]:
                r = resumo(alvo)
                if r and (novas := novidades(r, enviado)):
                    blocos.append((r, novas, not enviado))
            if not blocos:
                continue
            m = montar(p, blocos)
            if a.ensaio:
                if a.saida:
                    a.saida.mkdir(parents=True, exist_ok=True)
                    (a.saida / f"{p['id']}.html").write_text(m.get_body(("html",)).get_content(), encoding="utf-8")
                print(f"  [ensaio] {m['Subject']}")
                enviados += 1
                continue
            correio.mandar(m)
            enviados += 1
            print(f"  enviado: {m['Subject']}")
            if not a.teste_para:
                quando = dt.datetime.now(dt.timezone.utc).isoformat()
                for r, _, _ in blocos:
                    chaves = json.dumps({s["id"]: s["chave"] for s in r["secoes"]})
                    d1("UPDATE seguindo SET enviado = ?, enviado_em = ? WHERE pessoa_id = ? AND alvo = ?", [chaves, quando, p["id"], r["alvo"]])
            time.sleep(PAUSA_S)
    finally:
        if correio:
            correio.fechar()
    print(f"{enviados} e-mail(s) {'montados' if a.ensaio else 'enviados'}.")


if __name__ == "__main__":
    principal()
