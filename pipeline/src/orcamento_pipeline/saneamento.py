"""Água e esgoto em cada cidade e estado (IBGE, Censo 2022), para pôr ao lado do gasto em saneamento.

    uv run saneamento

Duas tabelas do Censo 2022 (resultados do universo), pela API de agregados do IBGE, contando
moradores em domicílios particulares permanentes ocupados:
- tabela 6894: os que têm ligação à rede geral de água e a usam como forma principal;
- tabela 7555: os que têm esgoto na rede geral ou pluvial, ou fossa ligada à rede.
Esgoto ligado à rede não quer dizer esgoto tratado: o tratamento não é medido pelo Censo.

Saída em site/public/data/indicadores/saneamento.json, com cópia versionada em
pipeline/referencia/saneamento.json (usada se a API falhar):
    {"fonte": …, "ano": 2022, "mun": {ibge: [moradores, com água da rede, com esgoto na rede]}, "uf": {código: […]}}
"""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/2022/variaveis/382?localidades={nivel}[all]&classificacao={cls}|58[95253]|86[95251]"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "saneamento.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "saneamento.json"
FONTE = "IBGE, Censo Demográfico 2022 (tabelas 6894 e 7555), moradores em domicílios particulares permanentes ocupados"
# (tabela, classificação, categoria do total, categoria que conta)
AGUA = (6894, 1821, 72129, 72144)
ESGOTO = (7555, 11558, 46292, 46290)


def consultar(tabela: int, cls: int, total: int, conta: int, nivel: str) -> dict[str, tuple[int, int]]:
    url = API.format(tabela=tabela, nivel=nivel, cls=f"{cls}[{total},{conta}]")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
        d = json.loads(resp.read())
    valores: dict[str, dict[str, int]] = {}
    for r in d[0]["resultados"]:
        categoria = next(iter(r["classificacoes"][0]["categoria"]))
        for s in r["series"]:
            v = s["serie"].get("2022")
            valores.setdefault(s["localidade"]["id"], {})[categoria] = int(v) if v and v.isdigit() else 0
    return {k: (v.get(str(total), 0), v.get(str(conta), 0)) for k, v in valores.items()}


def main() -> None:
    try:
        saida = {}
        for chave, nivel in (("mun", "N6"), ("uf", "N3")):
            agua, esgoto = consultar(*AGUA, nivel), consultar(*ESGOTO, nivel)
            saida[chave] = {k: [agua[k][0], agua[k][1], esgoto.get(k, (0, 0))[1]] for k in sorted(agua) if agua[k][0]}
        m = [sum(v[i] for v in saida["uf"].values()) for i in range(3)]
        print(f"{len(saida['mun'])} cidades; Brasil: {m[1] / m[0]:.1%} com água da rede, {m[2] / m[0]:.1%} com esgoto na rede", flush=True)
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as erro:
        if REFERENCIA.exists():
            print(f"  aviso: API do IBGE inacessível ({erro}); usando a cópia versionada", flush=True)
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REFERENCIA, SAIDA)
            return
        raise
    texto = json.dumps({"fonte": FONTE, "ano": 2022, **saida}, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
