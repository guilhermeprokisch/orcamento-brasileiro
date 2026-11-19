"""Matrículas por município e rede (Censo Escolar, INEP), para mostrar o gasto em educação por aluno.

    uv run matriculas              # 2024 e 2025
    uv run matriculas 2023 2024 2025

Fonte: Sinopse Estatística da Educação Básica, aba 1.2 (matrículas da educação básica por
dependência administrativa e município). Ficam duas redes:
- municipal: as escolas da prefeitura (creche, pré-escola, ensino fundamental, EJA…), que é o
  que o gasto da prefeitura em educação paga;
- estadual: as escolas do governo do estado na cidade, como contexto.

Como no Ideb (ideb.py), o INEP derruba conexões vindas de fora do país e o servidor não envia a
cadeia de certificados completa. O resultado também fica em pipeline/referencia/matriculas.json,
versionado: quando o download falha, a saída é copiada de lá, com um aviso.

Cache em data/raw/inep/. Saída em site/public/data/indicadores/matriculas.json:
    {"fonte": …, "anos": {"2025": {ibge: [rede municipal, rede estadual]}}}
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import openpyxl

from .cidades import RAIZ
from .fontes import USER_AGENT, contexto_tls_com_intermediario
from .ideb import INTERMEDIARIO

URL = "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopse_estatistica_censo_escolar_{ano}.zip"
PASTA_BRUTO = RAIZ / "data" / "raw" / "inep"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "matriculas.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "matriculas.json"
FONTE = "INEP, Censo Escolar (Sinopse Estatística da Educação Básica)"
COL_CODIGO = 3   # região, UF, município, código do município, e depois as matrículas


def baixar(ano: int, contexto) -> Path:
    arq = PASTA_BRUTO / f"sinopse_estatistica_censo_escolar_{ano}.zip"
    if not arq.exists():
        PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": USER_AGENT})
        tmp = arq.with_suffix(".tmp")
        with urllib.request.urlopen(req, timeout=600, context=contexto) as resp, tmp.open("wb") as f:
            shutil.copyfileobj(resp, f)
        tmp.replace(arq)
    return arq


def ler(arq: Path) -> dict[str, list[int]]:
    """{ibge: [matrículas da rede municipal, da rede estadual]} da aba 1.2 da sinopse."""
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        livro = openpyxl.load_workbook(io.BytesIO(z.read(nome)), read_only=True, data_only=True)
    aba = next(ws for ws in livro.worksheets if ws.title.strip().endswith("1.2"))
    linhas = aba.iter_rows(values_only=True)
    # O cabeçalho ocupa várias linhas, com células mescladas, e muda de um ano para outro: em 2025
    # há uma coluna "Rede Pública > Municipal"; em 2024 só "Urbana > Municipal" e "Rural > Municipal".
    cabecalho: list[list[str]] = []
    for linha in linhas:
        if linha[0] and str(linha[0]).strip().startswith("Região"):
            cabecalho.append([str(x or "") for x in linha])
            break
    for linha in linhas:
        if linha[0] not in (None, ""):
            primeira = linha
            break
        cabecalho.append([str(x or "") for x in linha])
    caminhos = colunas(cabecalho)
    cols = {rede: escolher(caminhos, rede) for rede in ("Municipal", "Estadual")}
    saida: dict[str, list[int]] = {}
    valor = lambda v: int(v) if isinstance(v, (int, float)) else 0   # "-" = nenhuma matrícula
    for linha in [primeira, *linhas]:
        codigo = str(linha[COL_CODIGO]).strip() if len(linha) > COL_CODIGO and linha[COL_CODIGO] is not None else ""
        if len(codigo) != 7 or not codigo.isdigit():
            continue
        saida[codigo] = [sum(valor(linha[i]) for i in cols["Municipal"]), sum(valor(linha[i]) for i in cols["Estadual"])]
    return saida


def colunas(cabecalho: list[list[str]]) -> list[tuple[str, ...]]:
    """O caminho de rótulos de cada coluna ("Rede Pública", "Municipal"), preenchendo as células mescladas."""
    largura = max(len(l) for l in cabecalho)
    preenchido = []
    for linha in cabecalho:
        atual, nova = "", []
        for i in range(largura):
            rotulo = re.sub(r"[\d\-–]+$", "", linha[i].strip()).strip() if i < len(linha) else ""
            atual = rotulo or atual
            nova.append(atual)
        preenchido.append(nova)
    return [tuple(x for x in (preenchido[n][i] for n in range(len(preenchido))) if x) for i in range(largura)]


def escolher(caminhos: list[tuple[str, ...]], rede: str) -> list[int]:
    """As colunas de uma rede: a da rede pública, se houver; senão, urbana mais rural."""
    da_rede = [i for i, c in enumerate(caminhos) if c and c[-1] == rede and i > COL_CODIGO]
    sem_local = [i for i in da_rede if not {"Urbana", "Rural"} & set(caminhos[i])]
    if sem_local:
        return sem_local[:1]
    urbana = [i for i in da_rede if "Urbana" in caminhos[i]][:1]
    rural = [i for i in da_rede if "Rural" in caminhos[i]][:1]
    if not (urbana and rural):
        raise ValueError(f"não achei as colunas da rede {rede} na aba 1.2")
    return urbana + rural


def main() -> None:
    p = argparse.ArgumentParser(prog="matriculas", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("anos", type=int, nargs="*", default=[2024, 2025])
    args = p.parse_args()
    contexto = contexto_tls_com_intermediario(INTERMEDIARIO)
    anos: dict[str, dict[str, list[int]]] = {}
    try:
        for ano in sorted(args.anos):
            dados = ler(baixar(ano, contexto))
            anos[str(ano)] = dados
            total = f"{sum(v[0] for v in dados.values()):,}".replace(",", ".")
            print(f"{ano}: {len(dados)} municípios, {total} matrículas na rede municipal", flush=True)
    except (urllib.error.URLError, OSError, zipfile.BadZipFile, StopIteration, ValueError) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: INEP inacessível ({erro}); usando a cópia versionada", flush=True)
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REFERENCIA, SAIDA)
            return
        raise
    doc = {"fonte": FONTE, "anos": anos}
    texto = json.dumps(doc, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
