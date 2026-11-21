"""Confere os dados antes de gerar o site: nenhum arquivo que está no ar pode sumir ou encolher muito.

Muitos programas de dados podem falhar sem parar a publicação (os "pode falhar" de dados.sh). Isso é bom
quando a fonte está fora do ar por um dia e a parte cai na cópia de referência, mas foi assim que as
emendas, a nota CAPAG e o gasto de Minas sumiram do site sem ninguém perceber (21/11/2026).

Como funciona:
1. Lista os arquivos de site/public/data com o tamanho de cada um.
2. Baixa o manifesto da versão que está no ar (/data/manifesto.json, gravado por esta mesma conferência
   na publicação anterior).
3. Para cada arquivo do manifesto: se sumiu, ou se ficou com menos da metade do tamanho, é erro. Aí a
   publicação para antes de gerar o site, e o site no ar continua como está.
4. Grava o manifesto novo em site/public/data/manifesto.json, que vai para o ar junto com o site.

Para tirar um arquivo de propósito (ou deixar encolher), ponha o caminho, relativo a site/public/data, em
.github/dados-podem-sair.txt, um por linha.

    python3 .github/scripts/conferir-dados.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS = Path(os.environ.get("CONFERIR_DADOS", RAIZ / "site" / "public" / "data"))   # outra pasta só para testar
MANIFESTO = DADOS / "manifesto.json"
NO_AR = os.environ.get("CONFERIR_NO_AR", "https://orcamentobrasileiro.com.br/data/manifesto.json")
PODEM_SAIR = RAIZ / ".github" / "dados-podem-sair.txt"
MINIMO = 0.5   # menos que isso do tamanho anterior conta como "encolheu demais"


def tamanho(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def main() -> int:
    atual = {str(p.relative_to(DADOS)): p.stat().st_size for p in sorted(DADOS.rglob("*"))
             if p.is_file() and p != MANIFESTO}
    try:
        with urllib.request.urlopen(urllib.request.Request(NO_AR, headers={"User-Agent": "orcamento-br"}), timeout=60) as r:
            anterior = json.loads(r.read())["arquivos"]
    except Exception as erro:   # primeira vez, ou o site fora do ar: não dá para comparar, mas não para a publicação
        print(f"::warning::Sem o manifesto do site no ar ({erro}); os dados não foram comparados com a versão anterior.")
        anterior = {}

    podem = set()
    if PODEM_SAIR.exists():
        podem = {l.strip() for l in PODEM_SAIR.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}

    sumiram = [c for c in anterior if c not in atual and c not in podem]
    encolheram = [(c, anterior[c], atual[c]) for c in anterior
                  if c in atual and c not in podem and anterior[c] > 0 and atual[c] < anterior[c] * MINIMO]
    novos = [c for c in atual if c not in anterior]

    print(f"{len(atual)} arquivos de dados; {len(anterior)} no manifesto do site no ar; {len(novos)} novos.")
    for c in sumiram:
        print(f"::error::Sumiu: {c} (estava no ar com {tamanho(anterior[c])})")
    for c, antes, agora in encolheram:
        print(f"::error::Encolheu demais: {c}, de {tamanho(antes)} para {tamanho(agora)}")
    if sumiram or encolheram:
        print("Algum programa de dados falhou sem cópia de referência (veja os avisos do passo anterior). "
              "O site no ar continua como está. Se a mudança for de propósito, ponha o caminho em .github/dados-podem-sair.txt.")
        return 1

    MANIFESTO.write_text(json.dumps({"arquivos": atual}, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"Tudo certo: nenhum arquivo sumiu ou encolheu mais da metade. Manifesto novo: {MANIFESTO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
