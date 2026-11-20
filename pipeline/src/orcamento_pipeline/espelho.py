"""Cópia pública dos dados num bucket do Backblaze B2.

    uv run espelho                  # brutos, tratados, referência e o LEIA-ME
    uv run espelho --sem-brutos     # só o que o site usa (rápido)

Envia para b2://orcamento-brasileiro-dados:
- brutos/      ← data/raw (os arquivos das fontes, como vieram)
- tratados/    ← site/public/data (os JSONs que o site lê)
- referencia/  ← pipeline/referencia (as cargas longas, resumidas)
- LEIA-ME.md   ← pipeline/espelho/LEIA-ME.md

Usa o programa `b2` (instalado na hora pelo uvx) e a chave nas variáveis B2_APPLICATION_KEY_ID e
B2_APPLICATION_KEY (no GitHub, os segredos B2_KEY_ID e B2_APPLICATION_KEY) ou a do
`b2 account authorize` feito no computador. Compara pelo tamanho, e não pela data: no CI os arquivos
voltam do cache com data nova, e comparar pela data mandaria tudo de novo a cada publicação. Nada é
apagado no bucket: um arquivo que sumiu daqui (um cache que expirou, por exemplo) continua lá.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from . import cidades as c

BUCKET = "orcamento-brasileiro-dados"
PASTAS = [
    ("brutos", c.RAIZ / "data" / "raw"),
    ("tratados", c.RAIZ / "site" / "public" / "data"),
    ("referencia", c.RAIZ / "pipeline" / "referencia"),
]
LEIAME = c.RAIZ / "pipeline" / "espelho" / "LEIA-ME.md"
# Temporários que os pipelines escrevem e trocam de nome no fim.
IGNORAR = r"(\.tmp|\.part|~|\.DS_Store)$"


def b2(*args: str) -> None:
    comando = (["b2"] if shutil.which("b2") else ["uvx", "--from", "b2", "b2"]) + list(args)
    print("$", " ".join(comando[-4:]), flush=True)
    subprocess.run(comando, check=True)


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
    b2("file", "upload", "--no-progress", "--content-type", "text/markdown; charset=utf-8", BUCKET, str(LEIAME), "LEIA-ME.md")
    print(f"pronto: https://f005.backblazeb2.com/file/{BUCKET}/LEIA-ME.md" + (f" ({falhas} pasta(s) falharam)" if falhas else ""))
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
