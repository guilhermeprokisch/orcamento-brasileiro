"""Cópia pública dos dados num bucket do Backblaze B2.

    uv run espelho                  # brutos, tratados, referência e o LEIA-ME
    uv run espelho --sem-brutos     # só o que o site usa (rápido)

Envia para b2://orcamento-brasileiro-dados:
- brutos/      ← data/raw (os arquivos das fontes, como vieram)
- tratados/    ← site/public/data (os JSONs que o site lê)
- referencia/  ← pipeline/referencia (as cargas longas, resumidas)
- explorador/  ← data/publico (o arquivo que o explorador de contratos consulta)
- LEIA-ME.md   ← pipeline/espelho/LEIA-ME.md
- indice.txt   o endereço de cada arquivo, um por linha (o bucket não deixa listar sem chave:
               com o índice dá para baixar tudo com `wget -x -nH -i indice.txt`)
- indice.csv   caminho, tamanho em bytes e data do envio de cada arquivo

Usa o programa `b2` (instalado na hora pelo uvx) e a chave nas variáveis B2_APPLICATION_KEY_ID e
B2_APPLICATION_KEY (no GitHub, os segredos B2_KEY_ID e B2_APPLICATION_KEY) ou a do
`b2 account authorize` feito no computador. Compara pelo tamanho, e não pela data: no CI os arquivos
voltam do cache com data nova, e comparar pela data mandaria tudo de novo a cada publicação. Nada é
apagado no bucket: um arquivo que sumiu daqui (um cache que expirou, por exemplo) continua lá.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from . import cidades as c

BUCKET = "orcamento-brasileiro-dados"
PASTAS = [
    ("brutos", c.RAIZ / "data" / "raw"),
    ("tratados", c.RAIZ / "site" / "public" / "data"),
    ("referencia", c.RAIZ / "pipeline" / "referencia"),
    ("explorador", c.RAIZ / "data" / "publico"),   # o Parquet do explorador de contratos (explorador_contratos.py)
]
LEIAME = c.RAIZ / "pipeline" / "espelho" / "LEIA-ME.md"
# Temporários que os pipelines escrevem e trocam de nome no fim.
IGNORAR = r"(\.tmp|\.part|~|\.DS_Store)$"
URL = f"https://f005.backblazeb2.com/file/{BUCKET}"


def b2(*args: str, capturar: bool = False) -> str:
    comando = (["b2"] if shutil.which("b2") else ["uvx", "--from", "b2", "b2"]) + list(args)
    print("$", " ".join(comando[-4:]), flush=True)
    return subprocess.run(comando, check=True, capture_output=capturar, text=True).stdout or ""


def indices() -> None:
    """Lista o bucket e envia indice.txt (endereços) e indice.csv (caminho, tamanho, data)."""
    arquivos = json.loads(b2("ls", "-r", "--json", f"b2://{BUCKET}", capturar=True) or "[]")
    arquivos = sorted((a for a in arquivos if not a["fileName"].startswith("indice.")), key=lambda a: a["fileName"])
    txt = "".join(f"{URL}/{urllib.parse.quote(a['fileName'])}\n" for a in arquivos)
    tabela = io.StringIO()
    w = csv.writer(tabela)
    w.writerow(["caminho", "tamanho_bytes", "enviado_em"])
    for a in arquivos:
        w.writerow([a["fileName"], a.get("contentLength") or a.get("size") or 0,
                    datetime.fromtimestamp(a["uploadTimestamp"] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")])
    with tempfile.TemporaryDirectory() as d:
        for nome, texto, tipo in (("indice.txt", txt, "text/plain; charset=utf-8"), ("indice.csv", tabela.getvalue(), "text/csv; charset=utf-8")):
            caminho = Path(d) / nome
            caminho.write_text(texto, encoding="utf-8")
            b2("file", "upload", "--no-progress", "--quiet", "--content-type", tipo, BUCKET, str(caminho), nome)
    print(f"  índice: {len(arquivos)} arquivos", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(prog="espelho", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-brutos", action="store_true", help="não envia data/raw")
    args = p.parse_args()
    falhas = 0
    for destino, origem in PASTAS:
        if args.sem_brutos and destino == "brutos":
            continue
        if not origem.exists():
            print(f"  {origem.relative_to(c.RAIZ)} não existe; pulando", flush=True)
            continue
        try:
            b2("sync", "--compare-versions", "size", "--threads", "8", "--exclude-regex", IGNORAR,
               "--no-progress", str(origem), f"b2://{BUCKET}/{destino}")
        except subprocess.CalledProcessError as erro:   # uma pasta que falhou não impede as outras
            falhas += 1
            print(f"  {destino}: falhou ({erro.returncode})", flush=True)
    b2("file", "upload", "--no-progress", "--quiet", "--content-type", "text/markdown; charset=utf-8", BUCKET, str(LEIAME), "LEIA-ME.md")
    indices()
    print(f"pronto: https://f005.backblazeb2.com/file/{BUCKET}/LEIA-ME.md" + (f" ({falhas} pasta(s) falharam)" if falhas else ""))
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
