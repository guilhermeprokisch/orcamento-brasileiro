"""A caixa de e-mail dos pedidos: lê as mensagens novas da conta do Homerow (pela skill homerow-workspace, que já tem as
credenciais), acha as devoluções ("mailbox full", "rejected") e as respostas dos órgãos, e atualiza a situação de cada
pedido no registro. Nada é apagado nem marcado como lido na caixa.

As mensagens já vistas ficam em ~/.config/orcamento-br/lai-caixa.json, para a mesma resposta não ser anotada duas vezes.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import time
from pathlib import Path

from . import registro

HOMEROW = Path(os.environ.get("LAI_HOMEROW", Path.home() / "Projects/homerow/.claude/skills/homerow-workspace/scripts/homerow.py"))
VISTOS = Path.home() / ".config" / "orcamento-br" / "lai-caixa.json"
DEVOLUCAO = re.compile(r"mailer-daemon|postmaster|undeliver|returned to sender|retornada|devolvid|não pode ser entregue|nao pode ser entregue|delivery status", re.I)
ENDERECO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
MOTIVOS = [(r"quota|mailbox (?:for user )?is full|caixa.{0,20}cheia", "caixa do órgão cheia"),
           (r"rbl|blacklist|blocklist|rejected|access denied|spam", "o servidor do órgão recusou o nosso"),
           (r"user unknown|no such user|does not exist|inexistente|not found", "endereço não existe")]


def _homerow(*args: str):
    if not HOMEROW.exists():
        raise SystemExit(f"Não achei a skill do Homerow em {HOMEROW} (defina LAI_HOMEROW).")
    # O servidor de e-mail às vezes falha logo depois de o Mac acordar: tenta de novo antes de desistir.
    for tentativa in range(4):
        r = subprocess.run(["python3", str(HOMEROW), "mail", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        time.sleep(30 * (tentativa + 1))
    raise SystemExit(f"Não consegui ler a caixa do Homerow: {(r.stderr or r.stdout).strip()[-400:]}")


def _dominio(canal: str) -> str | None:
    m = ENDERECO.search(canal)
    if m:
        return m.group(0).split("@")[1].lower()
    m = re.search(r"https?://([^/]+)", canal)
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else None


def _casa(remetente: str, dominio: str | None) -> bool:
    if not dominio:
        return False
    return remetente == dominio or remetente.endswith("." + dominio) or dominio.endswith("." + remetente)


def verificar(desde: str | None = None, anotar: bool = True) -> list[str]:
    linhas = registro.ler()
    if not linhas:
        return ["O registro está vazio."]
    desde = desde or min(r["enviado_em"] for r in linhas)
    vistos = set(json.loads(VISTOS.read_text()) if VISTOS.exists() else [])
    msgs = [m for m in _homerow("search", "", "--since", desde, "--limit", "500") if m["uid"] not in vistos]
    relato = []
    for m in sorted(msgs, key=lambda x: int(x["uid"])):
        remetente = m["from"].lower()
        if DEVOLUCAO.search(remetente) or DEVOLUCAO.search(m["subject"]):
            corpo = _homerow("read", m["uid"]).get("body") or ""
            motivo = next((txt for pad, txt in MOTIVOS if re.search(pad, corpo, re.I)), "motivo não identificado")
            for end in {e.lower() for e in ENDERECO.findall(corpo)}:
                for r in linhas:
                    if r["canal"].lower().endswith(end) and r["situacao"] == "aguardando":
                        r["situacao"], r["obs"] = "devolvido", f"{motivo} (e-mail {m['uid']})"
                        relato.append(f"{r['orgao']}: o e-mail para {end} voltou: {motivo}.")
        else:
            dom = ENDERECO.search(remetente)
            dom = dom.group(0).split("@")[1] if dom else ""
            for r in linhas:
                if _casa(dom, _dominio(r["canal"])):
                    # Não muda a situação: confirmação de recebimento, pedido de outro canal e resposta com os dados
                    # chegam todos assim, e só lendo dá para saber. Fica anotado para conferir.
                    r["obs"] = (r["obs"] + "; " if r["obs"] else "") + f"{m['date'][5:16]}: \"{m['subject'][:80]}\" (e-mail {m['uid']})"
                    relato.append(f"{r['orgao']}: chegou \"{m['subject'][:90]}\" de {m['from'][:60]} (ler: e-mail {m['uid']}).")
                    break
        vistos.add(m["uid"])
    if anotar:
        with registro.ARQUIVO.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=registro.COLUNAS)
            w.writeheader()
            w.writerows(linhas)
        VISTOS.parent.mkdir(parents=True, exist_ok=True)
        VISTOS.write_text(json.dumps(sorted(vistos)))
    return relato or ["Nada novo dos órgãos na caixa."]
