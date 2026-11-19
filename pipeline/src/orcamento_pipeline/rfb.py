"""Arrecadação federal em cada município (Receita Federal), para o mapa.

    uv run rfb                 # baixa o que falta e grava todos os anos do mapa
    uv run rfb --forcar        # baixa de novo as planilhas (sem isso, só as com mais de 30 dias)

Fonte: "Arrecadação por Município", nos dados abertos da Receita Federal
(https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/copy_of_arrecadacao-das-receitas-administradas-pela-rfb-por-municipio).
Duas séries:

- receitas administradas pela Receita (impostos e contribuições, inclusive as do INSS),
  recolhidas em DARF e GPS, por município do contribuinte. É medido, mas mostra onde o
  imposto foi recolhido: a empresa recolhe no município da sede, inclusive o imposto
  descontado do salário de quem mora em outra cidade;
- imposto de renda pago por pessoas físicas (declaração, carnê-leão, ganho de capital),
  pelo município de quem paga. É a parte que mais se aproxima do que os moradores pagam
  diretamente.

Saída: site/public/data/mapa/rfb-mun/{ano}.json = {ibge: [arrecadação total, IR de pessoas físicas | null]}.
As planilhas ficam em data/raw/receita-federal/municipios/.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

PAGINA = ("https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/"
          "copy_of_arrecadacao-das-receitas-administradas-pela-rfb-por-municipio")
RAIZ_LINKS = "https://www.gov.br/receitafederal/pt-br/"
PASTA = c.RAIZ / "data" / "raw" / "receita-federal" / "municipios"
SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa" / "rfb-mun"
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
PRIMEIRO_ANO = 2013   # o primeiro ano do mapa

# Seções da página que interessam (título normalizado -> nome curto dos arquivos).
SECOES = {"receitasadministradaspelarfb": "total", "impostoderenda": "ir"}

# Grafias da Receita que não batem com o nome do IBGE (só letras e números, sem acento).
APELIDOS = {
    ("parati", "RJ"): "paraty", ("assu", "RN"): "acu", ("balneariodepicarras", "SC"): "balneariopicarras",
    ("santaisabeldopara", "PA"): "santaizabeldopara", ("bomjesus", "GO"): "bomjesusdegoias",
    ("embu", "SP"): "embudasartes",
    # nomes antigos de cidades que mudaram de nome
    ("fortalezadotabocao", "TO"): "tabocao", ("saovaleriodanatividade", "TO"): "saovalerio",
    ("livramentodobrumado", "BA"): "livramentodenossasenhora", ("saodomingosdepombal", "PB"): "saodomingos",
    ("saomigueldetouros", "RN"): "saomigueldogostoso", ("itabirinhademantena", "MG"): "itabirinha",
    ("campodesantana", "PB"): "tacima", ("vilaalta", "PR"): "altoparaiso",
}
# Fernando de Noronha é distrito estadual: não tem prefeitura nem lugar no mapa.
IGNORAR = {("fernandodenoronha", "PE")}


def _so_letras(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower())


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
        return resp.read()


def planilhas() -> list[tuple[str, str]]:
    """[(série, endereço da planilha)] na ordem da página, lidos da própria página da Receita."""
    pagina = _baixar(PAGINA).decode("utf-8", "ignore")
    achadas: list[tuple[str, str]] = []
    serie = None
    for m in re.finditer(r'<h[2-4][^>]*>(.*?)</h[2-4]>|<a[^>]+href="([^"]+)"[^>]*>\s*Excel\s*</a>', pagina, re.S):
        if m.group(1):
            serie = SECOES.get(_so_letras(html.unescape(re.sub("<[^>]+>", "", m.group(1)))))
        elif serie and m.group(2):
            href = m.group(2)
            achadas.append((serie, href if href.startswith("http") else RAIZ_LINKS + href.lstrip("/")))
    return achadas


def baixar_planilhas(forcar: bool) -> list[tuple[str, Path]]:
    """Baixa as planilhas que faltam (ou todas, com `forcar`). Sem rede, usa as que já estão na pasta."""
    PASTA.mkdir(parents=True, exist_ok=True)
    try:
        lista = planilhas()
    except OSError as erro:
        print(f"  aviso: página da Receita indisponível ({erro}); usando as planilhas já baixadas", flush=True)
        return sorted(((p.name.split("-")[0], p) for p in PASTA.glob("*.xlsx")), key=lambda x: x[1].name)
    saida = []
    for serie, url in lista:
        destino = PASTA / f"{serie}-{url.rstrip('/').split('/')[-1]}.xlsx"
        # A Receita revisa os anos recentes: planilhas com mais de 30 dias são baixadas de novo.
        velha = destino.exists() and time.time() - destino.stat().st_mtime > 30 * 86400
        if forcar or velha or not destino.exists():
            dados = _baixar(url)
            if not dados.startswith(b"PK"):   # a Receita às vezes devolve uma página de erro
                print(f"  aviso: {url} não é uma planilha; ficou de fora", flush=True)
                continue
            destino.write_bytes(dados)
            print(f"  baixado {destino.name} ({len(dados) / 1e6:.1f} MB)", flush=True)
        saida.append((serie, destino))
    return saida


def _numero(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def ler_total(arquivo: Path) -> dict[int, list[tuple[str, str, float]]]:
    """{ano: [(nome, UF, valor)]} da aba TOTAL. Vale para a planilha de vários anos (um ano por
    coluna) e para as de um ano só (o ano vem da linha "PERÍODO: 2018")."""
    livro = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    # A aba do total se chama "TOTAL" na maioria dos anos; em alguns, "Total" ou com espaço.
    ws = next((w for w in livro.worksheets if _so_letras(w.title) == "total"), livro.worksheets[-1])
    saida: dict[int, list] = {}
    anos_col: dict[int, int] = {}
    ano_unico = None
    for linha in ws.iter_rows(values_only=True):
        a = linha[0]
        if isinstance(a, str) and a.upper().startswith("PER") and (m := re.search(r"(\d{4})\s*$", a.strip())) and "A" not in a.upper().split(":")[-1]:
            ano_unico = int(m.group(1))
        if isinstance(a, str) and _so_letras(a) in ("municipio", "municipios"):
            for i, cab in enumerate(linha):
                if cab is not None and re.fullmatch(r"\d{4}", str(cab).strip()):
                    anos_col[i] = int(str(cab).strip())
            if not anos_col and ano_unico:
                anos_col = {2: ano_unico}
            continue
        if not anos_col or not isinstance(a, str) or not isinstance(linha[1], str) or len(linha[1].strip()) != 2:
            continue
        for i, ano in anos_col.items():
            v = _numero(linha[i]) if i < len(linha) else None
            if v is not None:
                saida.setdefault(ano, []).append((a.strip(), linha[1].strip(), v))
    return saida


def ler_ir(arquivo: Path) -> dict[int, list[tuple[str, str, float | None]]]:
    """{ano: [(nome, UF, IR de pessoas físicas)]}: None quando a Receita omite (sigilo) ou não tem o dado."""
    ws = openpyxl.load_workbook(arquivo, read_only=True, data_only=True).worksheets[0]
    saida: dict[int, list] = {}
    for linha in ws.iter_rows(values_only=True):
        ano, municipio = linha[0], linha[2] if len(linha) > 2 else None
        if not (isinstance(ano, (int, str)) and str(ano).strip().isdigit()) or not isinstance(municipio, str) or " - " not in municipio:
            continue
        nome, uf = municipio.rsplit(" - ", 1)
        saida.setdefault(int(str(ano).strip()), []).append((nome.strip(), uf.strip(), _numero(linha[3])))
    return saida


def main() -> None:
    p = argparse.ArgumentParser(prog="rfb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--forcar", action="store_true", help="baixa de novo todas as planilhas")
    args = p.parse_args()

    nomes = json.loads(NOMES.read_text(encoding="utf-8"))["mun"]
    chave = {(_so_letras(nm), uf): ibge for ibge, (nm, uf) in nomes.items()}
    por_uf: dict[str, list[str]] = {}
    for nm, uf in chave:
        por_uf.setdefault(uf, []).append(nm)
    parecidos: dict[tuple[str, str], str | None] = {}

    def ibge_de(nome: str, uf: str) -> str | None:
        k = (_so_letras(nome), uf)
        if k in IGNORAR:
            return None
        achado = chave.get(k) or chave.get((APELIDOS.get(k, ""), uf))
        if achado or uf not in por_uf:
            return achado
        # Grafias antigas ("Poxoréo", "Brasópolis"): o nome mais parecido do mesmo estado, se for bem parecido.
        if k not in parecidos:
            perto = difflib.get_close_matches(k[0], por_uf[uf], n=1, cutoff=0.85)
            parecidos[k] = chave[(perto[0], uf)] if perto else None
            if perto:
                print(f"  {nome} ({uf}) -> {nomes[parecidos[k]][0]}", flush=True)
        return parecidos[k]

    total: dict[int, dict[str, float]] = {}
    pf: dict[int, dict[str, float]] = {}
    sem_par: dict[tuple[str, str], float] = {}
    for serie, arq in baixar_planilhas(args.forcar):
        dados = ler_total(arq) if serie == "total" else ler_ir(arq)
        alvo = total if serie == "total" else pf
        for ano, linhas in dados.items():
            if ano < PRIMEIRO_ANO:
                continue
            d = alvo.setdefault(ano, {})
            for nome, uf, v in linhas:
                ibge = ibge_de(nome, uf)
                if ibge is None:
                    if v and serie == "total" and uf not in ("EX", "-") and (_so_letras(nome), uf) not in IGNORAR:
                        sem_par[(nome, uf)] = sem_par.get((nome, uf), 0) + v
                    continue
                if v is not None:
                    d[ibge] = d.get(ibge, 0) + v

    SAIDA.mkdir(parents=True, exist_ok=True)
    for ano in sorted(total):
        doc = {ibge: [round(v), round(pf[ano][ibge]) if ibge in pf.get(ano, {}) else None] for ibge, v in total[ano].items()}
        (SAIDA / f"{ano}.json").write_text(json.dumps(doc, separators=(",", ":")))
        com_pf = sum(1 for x in doc.values() if x[1] is not None)
        print(f"{ano}: {len(doc)} municípios, {com_pf} com IR de pessoas físicas, R$ {sum(x[0] for x in doc.values()) / 1e12:.2f} tri", flush=True)
    if sem_par:
        maiores = sorted(sem_par.items(), key=lambda x: -x[1])[:10]
        print(f"  {len(sem_par)} nomes sem município correspondente (somados em todos os anos): "
              + ", ".join(f"{n} ({u}) R$ {v / 1e6:.0f} mi" for (n, u), v in maiores), flush=True)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
