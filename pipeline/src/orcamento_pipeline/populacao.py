"""População de cada ano, por estado e por cidade (IBGE), para as taxas ano a ano.

    uv run populacao

- 2015 a 2021 e 2024 em diante: estimativas anuais do IBGE (tabela 6579). As de até 2021 foram
  feitas antes do Censo 2022, a partir do Censo 2010, e em muitos lugares ficaram acima da
  população que o Censo encontrou.
- 2022: o Censo (tabela 4709).
- 2023: o IBGE não publicou estimativa; fica a média geométrica entre 2022 e 2024.
Das cidades, ficam só as com mais de 50 mil habitantes (as mesmas de seguranca.py).

Saída em site/public/data/indicadores/populacao.json, com cópia versionada em
pipeline/referencia/populacao.json (usada se a API falhar):
    {"fonte": …, "anos": {"2024": {"33": 17219679, "3303500": …}}}
"""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from datetime import date

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/{anos}/variaveis/{var}?localidades=N3[all]|N6[all]"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "populacao.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "populacao.json"
POPULACAO = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
FONTE = "IBGE: estimativas da população (tabela 6579) e Censo 2022 (tabela 4709)"
PRIMEIRO_ANO = 2015
POP_MINIMA = 50_000


def consultar(tabela: int, anos: list[int], var: int) -> dict[str, dict[str, int]]:
    url = API.format(tabela=tabela, anos="|".join(map(str, anos)), var=var)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
        d = json.loads(resp.read())
    por_ano: dict[str, dict[str, int]] = {}
    for s in d[0]["resultados"][0]["series"]:
        for ano, v in s["serie"].items():
            if v and v.isdigit():
                por_ano.setdefault(ano, {})[s["localidade"]["id"]] = int(v)
    return por_ano


def main() -> None:
    ultimo = date.today().year
    guardar = {str(x["ibge"]) for x in json.loads(POPULACAO.read_text(encoding="utf-8"))["cidades"] if x["pop"] >= POP_MINIMA}
    try:
        estimados = [a for a in range(PRIMEIRO_ANO, ultimo + 1) if a not in (2022, 2023)]
        anos = consultar(6579, estimados, 9324)
        anos.update(consultar(4709, [2022], 93))
        if "2022" in anos and "2024" in anos:
            anos["2023"] = {k: round((v * anos["2024"][k]) ** 0.5) for k, v in anos["2022"].items() if k in anos["2024"]}
        anos = {a: {k: v for k, v in sorted(locais.items()) if len(k) == 2 or k in guardar} for a, locais in sorted(anos.items())}
        print(f"{len(anos)} anos ({min(anos)} a {max(anos)}); {len(next(iter(anos.values())))} lugares por ano", flush=True)
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: API do IBGE inacessível ({erro}); usando a cópia versionada", flush=True)
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REFERENCIA, SAIDA)
            return
        raise
    texto = json.dumps({"fonte": FONTE, "anos": anos}, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
