"""O registro dos pedidos enviados: docs/pedidos-lai/registro.csv, uma linha por pedido, sem dado pessoal (nem nome nem
CPF de quem pediu). Serve para acompanhar o prazo legal: 20 dias, prorrogáveis por mais 10 (art. 11 da Lei 12.527/2011);
depois, cabe recurso em 10 dias (art. 15)."""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from ..cidades import RAIZ

ARQUIVO = RAIZ / "docs" / "pedidos-lai" / "registro.csv"
COLUNAS = ["orgao", "assunto", "enviado_em", "canal", "protocolo", "prazo", "prazo_prorrogado", "situacao", "obs"]
PRAZO, PRORROGACAO = 20, 10


def prazos(enviado: dt.date) -> tuple[dt.date, dt.date]:
    return enviado + dt.timedelta(days=PRAZO), enviado + dt.timedelta(days=PRAZO + PRORROGACAO)


def ler(arquivo: Path = ARQUIVO) -> list[dict]:
    if not arquivo.exists():
        return []
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def anotar(orgao: str, assunto: str, canal: str, protocolo: str | None, obs: str = "",
           enviado: dt.date | None = None, arquivo: Path = ARQUIVO) -> dict:
    enviado = enviado or dt.date.today()
    p1, p2 = prazos(enviado)
    linha = {"orgao": orgao, "assunto": assunto, "enviado_em": enviado.isoformat(), "canal": canal,
             "protocolo": protocolo or "", "prazo": p1.isoformat(), "prazo_prorrogado": p2.isoformat(),
             "situacao": "aguardando", "obs": obs}
    novo = not arquivo.exists()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        w.writerow(linha)
    return linha


def vencidos(hoje: dt.date | None = None, arquivo: Path = ARQUIVO) -> list[dict]:
    """Pedidos ainda sem resposta cujo prazo (com a prorrogação) já passou: hora do recurso."""
    hoje = hoje or dt.date.today()
    return [r for r in ler(arquivo)
            if r["situacao"] == "aguardando" and dt.date.fromisoformat(r["prazo_prorrogado"]) < hoje]
