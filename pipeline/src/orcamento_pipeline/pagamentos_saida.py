"""Gravar o arquivo de pagamentos de um estado e conferir os totais com o que cada prefeitura declarou ao Tesouro.

Usado pelos coletores do Amazonas e do Tocantins (pagamentos_am.py e pagamentos_to.py), que leem fontes
diferentes mas chegam ao mesmo resumo por município (pagamentos_qlik.resumir).

A conferência compara o pago de cada cidade com o pago da DCA do mesmo ano (site/public/data/cidades/
municipios.json, gerado por cidades.py), como a página da cidade faz: algumas prefeituras declaram as
operações entre as próprias unidades, outras não, e vale a mais próxima das duas contas.
"""

from __future__ import annotations

import json
import re

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq

MUNICIPIOS_DCA = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
# Contas de folha que algumas prefeituras usam como credor, às vezes fora do grupo de pessoal (diaristas,
# prestadores do SUS, ajudas de custo): é dinheiro que vai para pessoas, não para um fornecedor. Os coletores
# põem essas linhas no grupo de pessoal (folha).
FOLHA_NOME = re.compile(r"^(FOPAG|FOLHA\s+(DE\s+)?PAGAMENTO)\b")
# Um CPF inteiro ou um número de 11 dígitos no nome, com ou sem pontos, traço e espaços ("028.633.156 - 09"):
# nunca pode ir para o arquivo.
CPF_NO_NOME = re.compile(r"(?<!\d)\d{3}\.?\s?\d{3}\.?\s?\d{3}\s*-?\s*\d{2}(?!\d)")


def gravar(uf: str, fonte: str, ano: int, mun: dict, so: list[str] | None) -> None:
    """Põe nome nos fornecedores que vieram só com o CNPJ e grava pagamentos-{uf}.json (site e referência).
    Numa carga de algumas cidades, junta com as que já estavam no arquivo do mesmo ano."""
    if sem_nome := pq.completar_nomes(mun):
        print(f"  {sem_nome} fornecedores sem nome nem no cadastro de CNPJ: aparecem pelo CNPJ")
    for resumo in mun.values():
        for credor in resumo["credores"]:
            if CPF_NO_NOME.search(credor[0]) or not pb.cnpj_valido(credor[1]):
                raise SystemExit(f"{uf}: credor que parece pessoa física entre os fornecedores ({credor[0][:20]}…); nada foi gravado")
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
    print(f"{uf} {ano}: {len(mun)} municípios, pago R$ {pq.br(pago / 1e9, 2)} bi")
    print(f"saída: {destino.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {referencia.relative_to(c.RAIZ)}")
    conferir(uf, ano, mun)


def diferenca(resumo: dict, dca: float) -> float:
    """A diferença para o pago declarado ao Tesouro, com e sem as operações internas: vale a menor."""
    return min((resumo["pago"] / dca - 1, (resumo["pago"] + resumo["intra"]) / dca - 1), key=abs)


def conferir(uf: str, ano: int, mun: dict, tolerancia: float = 0.05) -> None:
    if not MUNICIPIOS_DCA.exists():
        print(f"  sem {MUNICIPIOS_DCA.relative_to(c.RAIZ)}: não deu para conferir com o Tesouro")
        return
    dcas = {str(x["ibge"]): x for x in json.loads(MUNICIPIOS_DCA.read_text(encoding="utf-8"))["cidades"] if x["uf"] == uf}
    batem, destoam, sem_dca = [], [], []
    for ibge, resumo in sorted(mun.items()):
        x = dcas.get(ibge)
        if not x or x.get("ano") != ano or not x.get("total") or not x["total"][1]:
            sem_dca.append(x["nome"] if x else ibge)
            continue
        d = diferenca(resumo, x["total"][1])
        (batem if abs(d) < tolerancia else destoam).append((x["nome"], d, resumo["pago"], x["total"][1]))
    print(f"  conferência com a DCA {ano} (pago): {len(batem)} de {len(batem) + len(destoam)} cidades a menos de "
          f"{tolerancia:.0%}; sem DCA de {ano}: {len(sem_dca)}")
    for nome, d, pago, dca in sorted(destoam, key=lambda t: t[1]):
        print(f"    {nome}: {d:+.1%} (TCE R$ {pq.br(pago / 1e6, 1)} mi, Tesouro R$ {pq.br(dca / 1e6, 1)} mi)")
    if sem_dca:
        print(f"    sem DCA de {ano}: {', '.join(sem_dca)}")
