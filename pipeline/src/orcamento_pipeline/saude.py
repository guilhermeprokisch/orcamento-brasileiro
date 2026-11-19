"""Mortalidade infantil por município (DATASUS), para pôr ao lado do gasto em saúde.

    uv run saude               # 2015 até o ano passado (os anos fechados vêm da cópia versionada)
    uv run saude 2023 2024 --forcar

Mortalidade infantil é o número de bebês que morrem antes de completar 1 ano para cada mil
nascidos vivos, pela cidade onde a mãe mora. Vem de dois sistemas do Ministério da Saúde:
- SINASC (nascidos vivos): uma linha por nascimento, com o município de residência da mãe;
- SIM (mortalidade): uma linha por óbito; os não fetais com idade em minutos, horas, dias ou
  meses (código IDADE de 000 a 399, ou 400 = menos de 1 ano) são os óbitos infantis.
A página soma os dois últimos anos, porque nas cidades pequenas uns poucos casos mudam muito a
taxa; a série ano a ano aparece para os estados e as cidades grandes.

Arquivos: os CSV anuais do OpenDataSUS no armazenamento do Ministério da Saúde
(SINASC/csv/SINASC_{ano}_csv.zip; SIM/csv/DO{aa}OPEN_csv.zip nos anos recentes e
SIM/csv/Mortalidade_Geral_{ano}_csv.zip nos antigos). Os dois anos mais recentes são
preliminares e são contados de novo a cada execução; os outros ficam na cópia versionada em
pipeline/referencia/saude.json e só são recontados com --forcar.

Cache em data/raw/datasus/. Saída em site/public/data/indicadores/saude.json:
    {"anos": {"2024": {"mun": {ibge: [nascidos vivos, óbitos infantis]}, "uf": {código: […]}}}}
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
from datetime import date
from pathlib import Path

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

BASE = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br"
PASTA = c.RAIZ / "data" / "raw" / "datasus"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "saude.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "saude.json"
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
PRIMEIRO_ANO = 2015   # os CSV do OpenDataSUS vão de 2015 em diante
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


def arquivo_sim(ano: int) -> Path:
    """O arquivo de óbitos do ano: "DO25OPEN" nos anos recentes, "Mortalidade_Geral_2015" nos antigos."""
    nomes = [f"SIM/csv/DO{ano % 100:02d}OPEN_csv.zip", f"SIM/csv/Mortalidade_Geral_{ano}_csv.zip"]
    if ano < 2024:
        nomes.reverse()
    for nome in nomes:   # o que já está baixado primeiro
        if (PASTA / nome.split("/")[-1]).exists():
            return PASTA / nome.split("/")[-1]
    try:
        return baixar(nomes[0])
    except urllib.error.HTTPError:
        return baixar(nomes[1])


def linhas(arquivo: Path):
    """As linhas do CSV dentro do zip, como dicionários com as colunas em maiúsculas (os arquivos
    vêm em latin-1, com ";"; o de 2016 tem os nomes das colunas em minúsculas)."""
    with zipfile.ZipFile(arquivo) as z, z.open(z.namelist()[0]) as bruto:
        leitor = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
        cabecalho = [x.strip().upper() for x in next(leitor)]
        for linha in leitor:
            yield dict(zip(cabecalho, linha))


def infantil(idade: str) -> bool:
    """IDADE do SIM: o primeiro dígito é a unidade (0 minutos, 1 horas, 2 dias, 3 meses, 4 anos)."""
    idade = idade.strip()
    return len(idade) == 3 and idade.isdigit() and (idade[0] in "0123" or idade == "400")


def contar(ano: int, seis: dict[str, str]) -> dict[str, list[int]]:
    """ibge -> [nascidos vivos, óbitos infantis] de um ano, pelo município de residência da mãe."""
    mun: dict[str, list[int]] = {}
    sem_par = 0
    for l in linhas(baixar(f"SINASC/csv/SINASC_{ano}_csv.zip")):
        ibge = seis.get((l.get("CODMUNRES") or "").strip()[:6])
        if ibge:
            mun.setdefault(ibge, [0, 0])[0] += 1
        else:
            sem_par += 1
    for l in linhas(arquivo_sim(ano)):
        if (l.get("TIPOBITO") or "").strip() != "2" or not infantil(l.get("IDADE") or ""):
            continue
        ibge = seis.get((l.get("CODMUNRES") or "").strip()[:6])
        if ibge:
            mun.setdefault(ibge, [0, 0])[1] += 1
        else:
            sem_par += 1
    n, o = sum(v[0] for v in mun.values()), sum(v[1] for v in mun.values())
    fmt = lambda x: f"{x:,}".replace(",", ".")
    if not n:
        raise ValueError(f"{ano}: nenhum nascimento lido")
    print(f"{ano}: {fmt(n)} nascidos vivos, {fmt(o)} óbitos infantis ({o / n * 1000:.1f} por mil); {fmt(sem_par)} registros sem município", flush=True)
    return dict(sorted(mun.items()))


def main() -> None:
    hoje = date.today()
    p = argparse.ArgumentParser(prog="saude", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("anos", type=int, nargs="*", default=list(range(PRIMEIRO_ANO, hoje.year)))
    p.add_argument("--forcar", action="store_true", help="conta de novo também os anos já na cópia versionada")
    args = p.parse_args()

    # O DATASUS usa o código do município com 6 dígitos (sem o dígito verificador).
    seis = {ibge[:6]: ibge for ibge in json.loads(NOMES.read_text(encoding="utf-8"))["mun"]}
    anterior = json.loads(REFERENCIA.read_text(encoding="utf-8")) if REFERENCIA.exists() else {}
    anos: dict[str, dict] = dict(anterior.get("anos", {})) if isinstance(anterior.get("anos"), dict) else {}
    for ano in sorted(args.anos):
        # Os anos já fechados não mudam: ficam como estão na cópia versionada. Os dois últimos são preliminares.
        if str(ano) in anos and ano < hoje.year - 2 and not args.forcar:
            continue
        try:
            mun = contar(ano, seis)
        except (urllib.error.URLError, OSError, zipfile.BadZipFile, ValueError) as erro:
            print(f"  {ano}: DATASUS inacessível ou arquivo ilegível ({erro}); fica o que havia", flush=True)
            continue
        uf: dict[str, list[int]] = {}
        for ibge, (n, o) in mun.items():
            u = uf.setdefault(ibge[:2], [0, 0])
            u[0] += n
            u[1] += o
        anos[str(ano)] = {"mun": mun, "uf": dict(sorted(uf.items()))}
    if not anos:
        raise SystemExit("sem dados")
    texto = json.dumps({"fonte": FONTE, "anos": dict(sorted(anos.items()))}, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
