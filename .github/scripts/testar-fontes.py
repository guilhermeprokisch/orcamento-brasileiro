"""Testa se as fontes das cargas feitas à mão respondem daqui (um runner do GitHub, fora do Brasil).

    uv run --project pipeline python .github/scripts/testar-fontes.py

Para cada fonte: a resposta, o tamanho e, nos arquivos grandes, a velocidade de um pedaço baixado (lido e
descartado, nada fica no disco). Com a velocidade, estima quanto a carga inteira levaria. Não contorna
captcha nem bloqueio: se a fonte recusa, o teste só anota a recusa. Usa os endereços, o User-Agent e o
contexto TLS dos próprios programas do pipeline.

Escreve uma tabela em Markdown na saída e, no GitHub, no resumo da execução ($GITHUB_STEP_SUMMARY).
"""

from __future__ import annotations

import os
import re
import time
import traceback
import urllib.request

from orcamento_pipeline import contratos, divida_ativa as da, unidades_saude as us
from orcamento_pipeline.fontes import CONTEXTO_TLS, USER_AGENT

MB = 1 << 20
linhas: list[tuple[str, str, str]] = []


def anotar(fonte: str, ok: bool | None, detalhe: str) -> None:
    sinal = {True: "responde", False: "**não responde**", None: "parcial"}[ok]
    linhas.append((fonte, sinal, detalhe))
    print(f"[{sinal}] {fonte}: {detalhe}", flush=True)


def abrir(url: str, metodo: str = "GET", cab: dict | None = None, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(cab or {})}, method=metodo)
    return urllib.request.urlopen(req, timeout=timeout, context=None if url.startswith("ftp") else CONTEXTO_TLS)


def amostra(resp, limite_mb: int = 150, limite_s: int = 45) -> tuple[float, float]:
    """Lê até limite_mb ou limite_s segundos da resposta e descarta. Devolve (MB lidos, MB/s)."""
    ini, lidos = time.monotonic(), 0
    while lidos < limite_mb * MB and time.monotonic() - ini < limite_s:
        bloco = resp.read(4 * MB)
        if not bloco:
            break
        lidos += len(bloco)
    dt = max(time.monotonic() - ini, 1e-3)
    return lidos / MB, lidos / MB / dt


def minutos(total_mb: float, velocidade: float) -> str:
    return f"~{total_mb / max(velocidade, 0.01) / 60:.0f} min para {total_mb / 1024:.1f} GB"


def sonda(fonte: str):
    def deco(f):
        try:
            f(fonte)
        except Exception as erro:  # noqa: BLE001 — cada sonda é independente
            anotar(fonte, False, f"{type(erro).__name__}: {str(erro)[:160]}")
            traceback.print_exc()
        return f
    return deco


# ── dívida ativa ────────────────────────────────────────────────────────────────────────────────
tri = None


@sonda("PGFN, lista dos trimestres")
def _(fonte):
    global tri
    tri = da.ultimo_trimestre()
    anotar(fonte, True, f"último trimestre completo: {tri}")


@sonda("PGFN, download do arquivo grande")
def _(fonte):
    if not tri:
        raise RuntimeError("sem o trimestre (a lista falhou)")
    with abrir(da.URL_PGFN + tri + "/") as r:
        html = r.read().decode("latin-1")
    nome = next(n for n in da.TIPOS["nao_prev"] if f"{n}.zip" in html)
    with abrir(f"{da.URL_PGFN}{tri}/{nome}.zip", timeout=300) as r:
        tamanho = int(r.headers.get("Content-Length") or 0) / MB
        lidos, v = amostra(r)
    anotar(fonte, True, f"{nome}.zip, {tamanho:.0f} MB; {lidos:.0f} MB a {v:.1f} MB/s, {minutos(1500, v)} (os três arquivos)")


mes_receita = None


@sonda("Receita, lista do cadastro de CNPJ (WebDAV)")
def _(fonte):
    global mes_receita
    mes_receita = da.ultimo_mes_receita()
    with da._abrir(f"{da.URL_RECEITA}{mes_receita}/", receita=True, metodo="PROPFIND", cab={"Depth": "1"}) as r:
        xml = r.read().decode()
    tamanhos = [int(x) for x in re.findall(r"<d:getcontentlength>(\d+)</d:getcontentlength>", xml)]
    anotar(fonte, True, f"mês {mes_receita}: {len(tamanhos)} arquivos, {sum(tamanhos) / 1024**3:.1f} GB")


@sonda("Receita, download de Estabelecimentos0.zip")
def _(fonte):
    if not mes_receita:
        raise RuntimeError("sem o mês (a lista falhou)")
    with da._abrir(f"{da.URL_RECEITA}{mes_receita}/Estabelecimentos0.zip", receita=True) as r:
        tamanho = int(r.headers.get("Content-Length") or 0) / MB
        lidos, v = amostra(r)
    anotar(fonte, True, f"{tamanho:.0f} MB; {lidos:.0f} MB a {v:.1f} MB/s, {minutos(6.7 * 1024, v)} (Estabelecimentos e Empresas)")


# ── postos e hospitais ──────────────────────────────────────────────────────────────────────────
@sonda("CNES (OpenDataSUS, S3)")
def _(fonte):
    with abrir(us.URL_CNES, timeout=300) as r:
        tamanho = int(r.headers.get("Content-Length") or 0) / MB
        lidos, v = amostra(r, 100, 30)
    anotar(fonte, True, f"{tamanho:.0f} MB; {lidos:.0f} MB a {v:.1f} MB/s")


@sonda("SIH (FTP do DATASUS)")
def _(fonte):
    url = us.URL_SIH.format(uf="AC", aa="25", mm="01")
    ini = time.monotonic()
    with abrir(url, timeout=300) as r:
        dados = r.read()
    dt = time.monotonic() - ini
    anotar(fonte, True, f"RDAC2501.dbc inteiro: {len(dados) / MB:.1f} MB em {dt:.0f} s")


@sonda("SIA (FTP do DATASUS)")
def _(fonte):
    ini = time.monotonic()
    with abrir(us.PASTA_SIA, timeout=300) as r:
        lista = r.read().decode("latin-1").splitlines()
    t_lista = time.monotonic() - ini
    arquivos = {}
    for linha in lista:
        partes = linha.split()
        if len(partes) >= 4 and re.fullmatch(r"PA[A-Z]{2}25\d{2}[a-z]?\.dbc", partes[-1]):
            tam = next((int(p) for p in partes if p.isdigit() and int(p) > 10_000), 0)
            arquivos[partes[-1]] = tam
    total = sum(arquivos.values()) / MB
    maior = max(arquivos, key=arquivos.get)
    with abrir(us.PASTA_SIA + maior, timeout=900) as r:
        lidos, v = amostra(r)
    anotar(fonte, True, f"lista em {t_lista:.0f} s, {len(arquivos)} arquivos de 2025 ({total / 1024:.1f} GB); "
                        f"{maior}: {lidos:.0f} MB a {v:.1f} MB/s, {minutos(total, v)}")


@sonda("SISAB (relatório público)")
def _(fonte):
    with abrir(us.URL_SISAB) as r:
        html = r.read().decode("utf-8", "replace")
        status = r.status
    captcha = bool(re.search(r"captcha|recaptcha|hcaptcha", html, re.I))
    form = "javax.faces.ViewState" in html
    anotar(fonte, None if captcha else (form or None),
           f"HTTP {status}, {len(html) / 1024:.0f} KB, formulário JSF: {'sim' if form else 'não'}, captcha: {'sim' if captcha else 'não'}")


@sonda("SI-PNI (vacinas, S3)")
def _(fonte):
    url = us.URL_PNI.format(mes="jan", ano=2025)
    with abrir(url, timeout=300) as r:
        tamanho = int(r.headers.get("Content-Length") or 0) / MB
        lidos, v = amostra(r, 100, 30)
    anotar(fonte, True, f"jan/2025: {tamanho:.0f} MB; {lidos:.0f} MB a {v:.1f} MB/s, {minutos(tamanho * 12, v)} (12 meses)")


@sonda("Cobertura da APS (API)")
def _(fonte):
    url = f"{us.URL_COBERTURA}?unidadeGeografica=MUNICIPIO&nuCompInicio=202512&nuCompFim=202512"
    with abrir(url, timeout=300) as r:
        dados = r.read()
    anotar(fonte, True, f"HTTP {r.status}, {len(dados) / 1024:.0f} KB")


# ── contratos ───────────────────────────────────────────────────────────────────────────────────
@sonda("PNCP (API de consulta)")
def _(fonte):
    ini = time.monotonic()
    d = contratos.baixar_pagina("20250312", 1)
    dt = time.monotonic() - ini
    paginas = d.get("totalPaginas") or 0
    registros = len(d.get("data") or [])
    # O comando baixa ~455 dias (o ano e o 1º trimestre do seguinte), duas linhas de download ao mesmo tempo.
    est = 455 * max(paginas, 1) * dt / 2 / 3600
    anotar(fonte, True, f"12/03/2025, página 1: {registros} registros em {dt:.1f} s, {paginas} páginas no dia; "
                        f"o ano inteiro levaria ~{est:.0f} h nesse ritmo")


tabela = ["| Fonte | Resultado | Detalhe |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in linhas]
texto = "\n".join(tabela)
print("\n" + texto)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write("## Fontes testadas deste runner\n\n" + texto + "\n")
