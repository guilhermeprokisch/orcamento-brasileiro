"""Nota de capacidade de pagamento (CAPAG) das prefeituras e dos estados, do Tesouro Nacional.

    uv run capag

A CAPAG é a nota que o Tesouro dá às contas de cada ente (A, B, C ou D; com "+" quando a
contabilidade é de boa qualidade). Com nota A ou B, a União pode ser garantidora de um
empréstimo. Ela junta três notas parciais:
- endividamento: dívida consolidada ÷ receita corrente líquida;
- poupança corrente: despesas correntes ÷ receitas correntes (quanto da receita do dia a dia
  o dia a dia consome);
- liquidez: o dinheiro em caixa frente às contas a pagar de curto prazo.

Fonte: conjuntos "capag-municipios" e "capag-estados" no portal de dados abertos do Tesouro
(CKAN). Este comando pega sempre a versão mais recente de cada um. A das prefeituras é uma
planilha de ~25 MB (aba "Prévia da CAPAG"); a dos estados, um CSV pequeno.

Cache em data/raw/tesouro/capag/. Saída em site/public/data/indicadores/capag.json:
    {"mun": {"versao": "…", "notas": {ibge: [nota, ind1, nota1, ind2, nota2, ind3, nota3, ano base]}},
     "uf":  {"versao": "…", "notas": {código do estado: [mesmo formato]}}}
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id={}"
PASTA = c.RAIZ / "data" / "raw" / "tesouro" / "capag"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "capag.json"
CODIGO_UF = {sigla: str(codigo) for codigo, sigla in c.SIGLAS.items()}


def _baixar(url: str, tentativas: int = 4) -> bytes:
    """Baixa com algumas tentativas: o servidor às vezes derruba a conexão (Connection reset) quando a
    publicação, que roda fora do Brasil e com várias consultas ao mesmo tempo, pede demais."""
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
                return resp.read()
        except (OSError, urllib.error.URLError):
            if n == tentativas - 1:
                raise
            time.sleep(5 * 3 ** n)   # 5, 15, 45 segundos
    raise AssertionError


def mais_recente(conjunto: str) -> tuple[str, Path]:
    """(nome da versão, arquivo local) do recurso mais recente de um conjunto do CKAN do Tesouro."""
    recursos = json.loads(_baixar(API.format(conjunto)))["result"]["resources"]
    r = max(recursos, key=lambda x: x.get("created") or "")
    destino = PASTA / r["url"].rstrip("/").split("/")[-1]
    if not destino.exists():
        PASTA.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(_baixar(r["url"]))
        print(f"  baixado {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)", flush=True)
    return r["name"].strip(), destino


def _numero(v) -> float | None:
    """0.27, "27,98%" ou "n.d." -> fração (0.2798) ou None."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and (m := re.fullmatch(r"\s*(-?[\d.]*,?\d+)\s*%\s*", v)):
        return float(m.group(1).replace(".", "").replace(",", ".")) / 100
    return None


def _nota(v) -> str | None:
    v = str(v or "").strip().upper()
    return v if re.fullmatch(r"[A-D]\+?", v) else None


def municipios(arquivo: Path) -> dict[str, list]:
    livro = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    aba = next(w for w in livro.worksheets if w.title.lower().startswith("prévia") or w.title.lower().startswith("previa"))
    notas: dict[str, list] = {}
    col: dict[str, int] = {}
    for linha in aba.iter_rows(values_only=True):
        if not col:
            if linha and str(linha[0] or "").startswith("Código Município"):
                col = {str(x).strip(): i for i, x in enumerate(linha) if x}
            continue
        ibge = str(linha[col["Código Município Completo"]] or "").strip()
        if not re.fullmatch(r"\d{7}", ibge):
            continue
        origem = str(linha[col.get("Origem da Nota Final", -1)] or "") if "Origem da Nota Final" in col else ""
        ano_base = int(m.group(1)) if (m := re.search(r"(\d{4})", origem)) else None
        notas[ibge] = [_nota(linha[col["CAPAG"]]),
                       _numero(linha[col["Indicador 1"]]), _nota(linha[col["Nota 1"]]),
                       _numero(linha[col["Indicador 2"]]), _nota(linha[col["Nota 2"]]),
                       _numero(linha[col["Indicador 3"]]), _nota(linha[col["Nota 3"]]), ano_base]
    return notas


def estados(arquivo: Path) -> dict[str, list]:
    texto = arquivo.read_bytes().decode("utf-8-sig", errors="replace")
    notas: dict[str, list] = {}
    for l in csv.DictReader(io.StringIO(texto), delimiter=";"):
        l = {k.strip(): (v or "").strip() for k, v in l.items() if k}
        uf = l.get("UF", "")
        if uf not in CODIGO_UF:
            continue
        final = next((v for k, v in l.items() if k.lower().startswith("classifica")), "")
        notas[CODIGO_UF[uf]] = [_nota(final), _numero(l.get("Indicador 1")), _nota(l.get("Nota 1")),
                                _numero(l.get("Indicador 2")), _nota(l.get("Nota 2")),
                                _numero(l.get("Indicador 3")), _nota(l.get("Nota 3")), None]
    return notas


def main() -> None:
    saida = {}
    for chave, conjunto, ler in (("mun", "capag-municipios", municipios), ("uf", "capag-estados", estados)):
        versao, arq = mais_recente(conjunto)
        notas = ler(arq)
        com_nota = sum(1 for v in notas.values() if v[0])
        print(f"{conjunto}: {versao} — {len(notas)} entes, {com_nota} com nota final", flush=True)
        saida[chave] = {"versao": versao, "notas": notas}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"fonte": "Tesouro Nacional, Capacidade de Pagamento (CAPAG)", **saida},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({SAIDA.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
