"""Homicídios por estado (DATASUS, SIM), para pôr ao lado do gasto em segurança pública.

    uv run seguranca            # 2015 até o último ano fechado (hoje menos 2)
    uv run seguranca 2024 --forcar

Usa os mesmos arquivos do SIM que saude.py (OpenDataSUS, SIM/csv/DO{aa}OPEN_csv.zip, em
data/raw/datasus/). Pela causa básica do óbito (CID-10), conta, pelo estado onde a pessoa morava:
- agressões (X85 a Y09): os homicídios;
- intervenções legais (Y35 e Y36): mortes em ações da polícia;
- eventos de intenção indeterminada (Y10 a Y34): mortes violentas em que não se sabe se foi
  homicídio, acidente ou suicídio. Quando são muitas, os homicídios ficam subcontados.
Os anos mais recentes do SIM são preliminares: muitas mortes violentas ainda estão sem causa
definida, e os homicídios aparecem bem mais baixos do que vão ficar. Por isso a série vai até o
ano retrasado. Os anos já na cópia versionada só são contados de novo com --forcar.

Saída em site/public/data/indicadores/seguranca.json, com cópia versionada em
pipeline/referencia/seguranca.json (usada se o download falhar):
    {"fonte": …, "anos": {"2024": {"33": [agressões, intervenções legais, indeterminadas]}},
     "mun": {"2024": {ibge: [mesmo formato]}}}   # só cidades com mais de 50 mil habitantes
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import zipfile
from datetime import date

from . import cidades as c
from .saude import arquivo_sim, linhas

SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "seguranca.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "seguranca.json"
FONTE = "Ministério da Saúde, DATASUS: Sistema de Informações sobre Mortalidade (SIM), por local de residência"
PRIMEIRO_ANO = 2015
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
POPULACAO = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
POP_MINIMA = 50_000   # as cidades guardadas; a página mostra a partir de 100 mil


def tipo(cid: str) -> int | None:
    """0 agressão, 1 intervenção legal, 2 intenção indeterminada; None para as outras causas."""
    cid = cid.strip().upper()
    if len(cid) < 3 or not cid[1:3].isdigit():
        return None
    n = int(cid[1:3])
    if (cid[0] == "X" and n >= 85) or (cid[0] == "Y" and n <= 9):
        return 0
    if cid[0] == "Y" and n in (35, 36):
        return 1
    if cid[0] == "Y" and 10 <= n <= 34:
        return 2
    return None


def main() -> None:
    p = argparse.ArgumentParser(prog="seguranca", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("anos", type=int, nargs="*", default=list(range(PRIMEIRO_ANO, date.today().year - 1)))
    p.add_argument("--forcar", action="store_true", help="conta de novo também os anos já na cópia versionada")
    args = p.parse_args()

    anterior = json.loads(REFERENCIA.read_text(encoding="utf-8")) if REFERENCIA.exists() else {}
    anos: dict[str, dict[str, list[int]]] = dict(anterior.get("anos", {}))
    por_mun: dict[str, dict[str, list[int]]] = dict(anterior.get("mun", {}))
    # O DATASUS usa o código do município com 6 dígitos; só ficam as cidades com mais de POP_MINIMA habitantes.
    pop = {str(x["ibge"]): x["pop"] for x in json.loads(POPULACAO.read_text(encoding="utf-8"))["cidades"]}
    seis = {ibge[:6]: ibge for ibge in json.loads(NOMES.read_text(encoding="utf-8"))["mun"] if pop.get(ibge, 0) >= POP_MINIMA}
    try:
        for ano in sorted(args.anos):
            if str(ano) in anos and str(ano) in por_mun and not args.forcar:
                continue
            uf: dict[str, list[int]] = {}
            mun: dict[str, list[int]] = {}
            for l in linhas(arquivo_sim(ano)):
                t = tipo(l.get("CAUSABAS") or "")
                residencia = (l.get("CODMUNRES") or "").strip()
                codigo = residencia[:2]
                if t is None or not codigo.isdigit() or int(codigo) not in c.SIGLAS:
                    continue
                uf.setdefault(codigo, [0, 0, 0])[t] += 1
                if ibge := seis.get(residencia[:6]):
                    mun.setdefault(ibge, [0, 0, 0])[t] += 1
            anos[str(ano)] = dict(sorted(uf.items()))
            por_mun[str(ano)] = dict(sorted(mun.items()))
            soma = [sum(v[i] for v in uf.values()) for i in range(3)]
            print(f"{ano}: {soma[0] + soma[1]:,} homicídios ({soma[1]:,} em ações da polícia); {soma[2]:,} mortes violentas sem causa definida".replace(",", "."), flush=True)
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as erro:
        print(f"  aviso: DATASUS inacessível ({erro}); fica a cópia versionada", flush=True)
    if not anos:
        raise SystemExit("sem dados")
    texto = json.dumps({"fonte": FONTE, "anos": dict(sorted(anos.items())), "mun": dict(sorted(por_mun.items()))}, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
