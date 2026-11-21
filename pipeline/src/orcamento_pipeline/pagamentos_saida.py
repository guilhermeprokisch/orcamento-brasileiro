"""Gravar o arquivo de pagamentos de um estado e conferir com o que cada prefeitura declarou ao Tesouro.

Usado pelos coletores do Ceará e do Espírito Santo (pagamentos_ce.py e pagamentos_es.py), que montam o
resumo de cada município com pagamentos_qlik.resumir, no mesmo formato da Paraíba.

A conferência compara o pago de cada cidade com o "pago" da prestação de contas ao Tesouro (DCA, do
SICONFI) que o site já tem em site/public/data/cidades/municipios.json, como faz a página da cidade:
vale a mais próxima de duas contas, com ou sem as operações entre unidades do próprio município
(algumas prefeituras as declaram, outras não).
"""

from __future__ import annotations

import json

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq

CIDADES = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"


def gravar(uf: str, fonte: str, ano: int, mun: dict, so: list[str] | None) -> None:
    """Põe nome nos fornecedores que vieram só com o CNPJ e grava pagamentos-{uf}.json (site e referência).
    Numa carga de algumas cidades, junta com as que já estavam no arquivo do mesmo ano."""
    if sem_nome := pq.completar_nomes(mun):
        print(f"  {sem_nome} fornecedores sem nome nem no cadastro de CNPJ: aparecem pelo CNPJ")
    destino, referencia = pq.saida(uf)
    if so and referencia.exists():
        antigo = json.loads(referencia.read_text(encoding="utf-8"))
        if antigo.get("ano") == ano:
            mun = {**antigo["mun"], **mun}
    doc = {"fonte": fonte, "ano": ano, "uf": uf, "tipos": pb.TIPOS, "mun": dict(sorted(mun.items()))}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for arq in (destino, referencia):
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(texto, encoding="utf-8")
    pago = sum(m["pago"] for m in mun.values())
    por_tipo = [sum(m["tipos"][i] for m in mun.values()) for i in range(len(pb.TIPOS))]
    print(f"{uf} {ano}: {len(mun)} municípios, pago R$ {pq.br(pago / 1e9, 2)} bi")
    for t, v in zip(pb.TIPOS, por_tipo):
        print(f"  {t}: R$ {pq.br(v / 1e9, 2)} bi ({v / pago:.0%})" if pago else f"  {t}: 0")
    print(f"saída: {destino.relative_to(c.RAIZ)} ({len(mun)} municípios, {len(texto) / 1e3:.0f} KB) e {referencia.relative_to(c.RAIZ)}")
    conferir(uf, ano, mun)


def diferencas(uf: str, ano: int, mun: dict) -> tuple[list[tuple[str, str, float, float]], list[str]]:
    """[(ibge, nome, pago aqui, pago na DCA)] das cidades com DCA do mesmo ano, e as que não têm."""
    if not CIDADES.exists():
        return [], []
    cidades = {str(x["ibge"]): x for x in json.loads(CIDADES.read_text(encoding="utf-8"))["cidades"] if x["uf"] == uf}
    linhas, sem_dca = [], []
    for ibge, m in sorted(mun.items()):
        x = cidades.get(ibge)
        if not x or x.get("ano") != ano or not x.get("total"):
            sem_dca.append(x["nome"] if x else ibge)
            continue
        dca = x["total"][1]
        # A mais próxima das duas contas: sem ou com as operações entre unidades do município.
        aqui = min((m["pago"], m["pago"] + m["intra"]), key=lambda v: abs(v - dca))
        linhas.append((ibge, x["nome"], aqui, dca))
    return linhas, sem_dca


def conferir(uf: str, ano: int, mun: dict) -> None:
    linhas, sem_dca = diferencas(uf, ano, mun)
    if not linhas:
        print("  conferência com a DCA: sem o arquivo das cidades (rode o pipeline das cidades antes)")
        return
    dif = sorted(((aqui / dca - 1 if dca else 0.0), nome, aqui, dca) for _, nome, aqui, dca in linhas)
    perto = sum(abs(d) < 0.05 for d, *_ in dif)
    print(f"  conferência com a DCA {ano}: {perto} de {len(dif)} cidades a menos de 5%"
          f" ({sum(abs(d) < 0.01 for d, *_ in dif)} a menos de 1%)")
    for d, nome, aqui, dca in sorted(dif, key=lambda x: -abs(x[0])):
        if abs(d) >= 0.05:
            print(f"    {nome}: {d:+.1%} (aqui R$ {pq.br(aqui / 1e6, 1)} mi, DCA R$ {pq.br(dca / 1e6, 1)} mi)")
    if sem_dca:
        print(f"  sem DCA de {ano} para comparar: {sem_dca}")
