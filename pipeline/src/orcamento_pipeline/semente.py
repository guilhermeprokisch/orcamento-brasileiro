"""Leva e traz o cache do SICONFI por um release do GitHub.

    uv run semente publicar    # sobe data/raw/siconfi/{dca,rreo}-*/ para o release (precisa de permissão de escrita)
    uv run semente publicar dca-id dca-iab    # só os anexos que mudaram
    uv run semente aplicar     # baixa o release e junta ao cache local o que falta
    uv run semente aplicar rreo-a01           # só uma das pastas

Os arquivos do FINBRA são baixados à mão (o site tem captcha; ver finbra.py), então o
histórico dos municípios só existe na máquina de quem baixou. Para o CI e outras
máquinas terem os mesmos dados sem refazer ~70 mil consultas à API, o cache já
importado fica nos anexos do release `dados-siconfi`: um .tar por pasta do cache
(dca-ie.tar, dca-ic.tar…, e rreo-a01.tar com os relatórios bimestrais dos municípios),
cada um com os arquivos {pasta}/{ano}.json.gz.

`aplicar` só preenche entes que ainda não estão no cache local (o que a API trouxe
depois tem prioridade) e anota em data/raw/siconfi/semente.json a versão de cada
anexo já aplicada, para não baixar de novo o que não mudou. Se o release ou o `gh`
não estiverem disponíveis, avisa e segue: o site sai sem o histórico.

Usa a CLI do GitHub (`gh`); o repositório é o do checkout ou o de GH_REPO.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

from . import cidades as c

RELEASE = "dados-siconfi"
PASTAS = ("dca-*", "rreo-*")
MEMBRO = re.compile(r"^((?:dca|rreo)-[a-z0-9]+)/(\d{4}(?:-b\d)?)\.json\.gz$")
NOTAS = """Cache das Declarações de Contas Anuais (DCA) de municípios e estados, já importado do \
FINBRA e da API do SICONFI (Tesouro Nacional). Não é uma versão do código: serve para o CI \
e outras máquinas gerarem o site sem baixar tudo de novo.

Um .tar por anexo: despesa por função (dca-ie), receitas (dca-ic), despesa por natureza \
(dca-id), balanço patrimonial (dca-iab) e relatórios bimestrais do ano em andamento (rreo-a01). Gerado por `uv run semente publicar` e lido por \
`uv run semente aplicar`."""


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def publicar(so: list[str] | None = None) -> None:
    pastas = sorted(p for padrao in PASTAS for p in c.PASTA_BRUTO.glob(padrao))
    anexos = [p for p in pastas if p.is_dir() and any(p.glob("*.json.gz")) and (not so or p.name in so)]
    if not anexos or (so and len(anexos) != len(set(so))):
        raise SystemExit(f"nada para publicar em {c.PASTA_BRUTO}" if not so else f"anexo não encontrado entre {so}")
    with tempfile.TemporaryDirectory() as tmp:
        pacotes = []
        for pasta in anexos:
            pacote = Path(tmp) / f"{pasta.name}.tar"
            with tarfile.open(pacote, "w") as tar:  # os .json.gz já são compactados
                for arq in sorted(pasta.glob("*.json.gz")):
                    tar.add(arq, arcname=f"{pasta.name}/{arq.name}")
            pacotes.append(str(pacote))
            print(f"  {pacote.name}: {pacote.stat().st_size / 1e6:.0f} MB", flush=True)
        if _gh("release", "view", RELEASE).returncode != 0:
            r = _gh("release", "create", RELEASE, "--title", "Dados do SICONFI (cache)", "--notes", NOTAS, "--latest=false")
            if r.returncode != 0:
                raise SystemExit(f"não consegui criar o release: {r.stderr.strip()}")
        r = _gh("release", "upload", RELEASE, *pacotes, "--clobber")
        if r.returncode != 0:
            raise SystemExit(f"falha no envio: {r.stderr.strip()}")
    print(f"release {RELEASE}: {len(pacotes)} anexos enviados")


def _juntar(anexo: str, ano: str, dados: bytes) -> int:
    """Junta um arquivo do release ao cache local. Devolve quantos entes entraram."""
    destino = c.PASTA_BRUTO / anexo / f"{ano}.json.gz"
    if not destino.exists():  # nada local: o arquivo entra como veio
        entes = len(json.loads(gzip.decompress(dados)))
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(destino.name + ".tmp")
        tmp.write_bytes(dados)
        tmp.replace(destino)
        return entes
    cache = c.CacheAno(ano, anexo=anexo)
    novos = cache.juntar(json.loads(gzip.decompress(dados)))
    cache.salvar()
    return novos


def aplicar(so: list[str] | None = None) -> None:
    r = _gh("release", "view", RELEASE, "--json", "assets")
    if r.returncode != 0:
        print(f"  aviso: release {RELEASE} indisponível ({r.stderr.strip() or 'gh falhou'}); seguindo sem ele", flush=True)
        return
    marca_arq = c.PASTA_BRUTO / "semente.json"
    try:
        marca = json.loads(marca_arq.read_text())
    except (OSError, ValueError):
        marca = {}
    for anexo in sorted(json.loads(r.stdout)["assets"], key=lambda a: a["name"]):
        nome, versao = anexo["name"], anexo["updatedAt"]
        if not nome.endswith(".tar") or (so and nome.removesuffix(".tar") not in so):
            continue
        if marca.get(nome) == versao:
            print(f"  {nome}: já aplicado", flush=True)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            d = _gh("release", "download", RELEASE, "--pattern", nome, "--dir", tmp)
            if d.returncode != 0:
                print(f"  aviso: não baixei {nome} ({d.stderr.strip()})", flush=True)
                continue
            entes = arquivos = 0
            with tarfile.open(Path(tmp) / nome) as tar:
                for membro in tar:
                    m = MEMBRO.match(membro.name)
                    if not m or not membro.isfile():  # só o que este comando publica
                        continue
                    entes += _juntar(m[1], m[2], tar.extractfile(membro).read())
                    arquivos += 1
        marca[nome] = versao
        c.PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
        marca_arq.write_text(json.dumps(marca, indent=1))
        print(f"  {nome}: {arquivos} anos, {entes} entes novos no cache", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(prog="semente", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("acao", choices=["publicar", "aplicar"])
    p.add_argument("anexos", nargs="*", help="pastas do cache a enviar ou a trazer (padrão: todas)")
    args = p.parse_args()
    publicar(args.anexos) if args.acao == "publicar" else aplicar(args.anexos)


if __name__ == "__main__":
    main()
