"""Mortalidade infantil por município (DATASUS), para pôr ao lado do gasto em saúde.

    uv run saude               # 2024 e 2025
    uv run saude 2023 2024

Mortalidade infantil é o número de bebês que morrem antes de completar 1 ano para cada mil
nascidos vivos, pela cidade onde a mãe mora. Vem de dois sistemas do Ministério da Saúde:
- SINASC (nascidos vivos): uma linha por nascimento, com o município de residência da mãe;
- SIM (mortalidade): uma linha por óbito; os não fetais com idade em minutos, horas, dias ou
  meses (código IDADE de 000 a 399, ou 400 = menos de 1 ano) são os óbitos infantis.
Os anos são somados, porque nas cidades pequenas uns poucos casos mudam muito a taxa.

Arquivos: os CSV anuais do OpenDataSUS no armazenamento do Ministério da Saúde
(SINASC/csv/SINASC_{ano}_csv.zip e SIM/csv/DO{aa}OPEN_csv.zip). Os dois ou três anos mais
recentes do SIM são preliminares. O resultado também fica em pipeline/referencia/saude.json,
versionado: se o download falhar, a saída é copiada de lá.

Cache em data/raw/datasus/. Saída em site/public/data/indicadores/saude.json:
    {"anos": [2024, 2025], "mun": {ibge: [nascidos vivos, óbitos infantis]}, "uf": {código: […]}}
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

BASE = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br"
PASTA = c.RAIZ / "data" / "raw" / "datasus"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "saude.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "saude.json"
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
FONTE = "Ministério da Saúde, DATASUS: SINASC (nascidos vivos) e SIM (mortalidade), por município de residência"


def baixar(caminho: str) -> Path:
    destino = PASTA / caminho.split("/")[-1]
    if not destino.exists():
        PASTA.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(f"{BASE}/{caminho}", headers={"User-Agent": USER_AGENT})
        tmp = destino.with_suffix(".tmp")
        with urllib.request.urlopen(req, timeout=900, context=CONTEXTO_TLS) as resp, tmp.open("wb") as f:
            shutil.copyfileobj(resp, f)
        tmp.replace(destino)
        print(f"  baixado {destino.name} ({destino.stat().st_size / 1e6:.0f} MB)", flush=True)
    return destino


def linhas(arquivo: Path):
    """As linhas do CSV dentro do zip, como dicionários (os arquivos vêm em latin-1, com ";")."""
    with zipfile.ZipFile(arquivo) as z, z.open(z.namelist()[0]) as bruto:
        yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")


def infantil(idade: str) -> bool:
    """IDADE do SIM: o primeiro dígito é a unidade (0 minutos, 1 horas, 2 dias, 3 meses, 4 anos)."""
    idade = idade.strip()
    return len(idade) == 3 and idade.isdigit() and (idade[0] in "0123" or idade == "400")


def main() -> None:
    p = argparse.ArgumentParser(prog="saude", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("anos", type=int, nargs="*", default=[2024, 2025])
    args = p.parse_args()

    # O DATASUS usa o código do município com 6 dígitos (sem o dígito verificador).
    seis = {ibge[:6]: ibge for ibge in json.loads(NOMES.read_text(encoding="utf-8"))["mun"]}
    mun: dict[str, list[int]] = {}
    sem_par = 0
    try:
        for ano in sorted(args.anos):
            nascidos = obitos = 0
            for l in linhas(baixar(f"SINASC/csv/SINASC_{ano}_csv.zip")):
                ibge = seis.get((l.get("CODMUNRES") or "").strip()[:6])
                if ibge:
                    mun.setdefault(ibge, [0, 0])[0] += 1
                    nascidos += 1
                else:
                    sem_par += 1
            for l in linhas(baixar(f"SIM/csv/DO{ano % 100:02d}OPEN_csv.zip")):
                if (l.get("TIPOBITO") or "").strip() != "2" or not infantil(l.get("IDADE") or ""):
                    continue
                ibge = seis.get((l.get("CODMUNRES") or "").strip()[:6])
                if ibge:
                    mun.setdefault(ibge, [0, 0])[1] += 1
                    obitos += 1
                else:
                    sem_par += 1
            fmt = lambda n: f"{n:,}".replace(",", ".")
            print(f"{ano}: {fmt(nascidos)} nascidos vivos, {fmt(obitos)} óbitos infantis ({obitos / nascidos * 1000:.1f} por mil)", flush=True)
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: DATASUS inacessível ({erro}); usando a cópia versionada", flush=True)
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REFERENCIA, SAIDA)
            return
        raise
    uf: dict[str, list[int]] = {}
    for ibge, (n, o) in mun.items():
        u = uf.setdefault(ibge[:2], [0, 0])
        u[0] += n
        u[1] += o
    if sem_par:
        print(f"  {sem_par:,} registros sem município de residência conhecido ficaram de fora".replace(",", "."), flush=True)
    texto = json.dumps({"fonte": FONTE, "anos": sorted(args.anos), "mun": mun, "uf": uf}, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
