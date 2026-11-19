"""Gasto do governo de Minas Gerais distribuído por município.

    uv run estado-mg 2025

Minas publica, no conjunto "Planejamento e Monitoramento" do portal de dados abertos
(https://dados.mg.gov.br/dataset/planejamento-e-monitoramento, licença CC-BY 4.0), a execução
de cada ação do plano plurianual (PPAG) dividida pelo município "da destinação do bem ou
serviço". São arquivos pequenos (o maior tem 11 MB), sem cadastro, de 2012 em diante.

O que é diferente da Paraíba (estado_pb.py):
- quem informa o município são os órgãos, no monitoramento do plano; não sai do empenho.
  Não há credor nem nota: o menor nível é programa e órgão;
- a distribuição cobre a despesa inteira, inclusive salários;
- parte fica em "Diversos municípios" (de uma região ou do estado inteiro) e não é atribuída
  a cidade nenhuma;
- as "operações especiais" (repasses constitucionais às prefeituras, dívida, aposentadorias)
  são somadas à parte: o repasse à prefeitura já aparece no site como receita dela;
- o orçamento de investimento das empresas do estado (Cemig, Copasa…) também fica à parte.

Em 2024 a fonte traz só R$ 5 bi (a despesa do estado passa de R$ 100 bi): o ano é recusado.

Cache em data/raw/estados/mg/. Saída em site/public/data/estados/mg/{ano}.json, no formato
lido por site/src/lib/estadual.ts.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import time
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

from .cidades import RAIZ, baixar_entes
from .fontes import CONTEXTO_TLS, USER_AGENT

BASE = "https://dados.mg.gov.br/dataset/a3cf45b7-74c0-40df-b1bb-5eb0dc507ef3/resource/"
ARQUIVOS = {
    "ft_plan_acao_ppag": "938c0263-4a47-4fb0-9267-e21c912b827d",
    "dm_municipio_plan": "1cc1db6f-2d55-410c-9ec8-268b79bf230b",
    "dm_funcao_plan": "ec8c7204-b424-4a07-bf66-3903b1219a7e",
    "dm_programa_plan": "12b65fe9-3e59-4a18-8d12-94c3f8077ad8",
    "dm_orgao_plan": "ffe79ea1-bc43-45f2-8664-00e393e70dda",
}
PASTA_BRUTO = RAIZ / "data" / "raw" / "estados" / "mg"
SAIDA = RAIZ / "site" / "public" / "data" / "estados" / "mg"
VALIDADE = 24 * 3600  # os arquivos mudam todo dia; baixa de novo depois disso
MAIORES = 6
MINIMO_PLAUSIVEL = 30e9  # abaixo disso o ano está incompleto na fonte (2024 tem R$ 5 bi)
ORCAMENTO_DAS_EMPRESAS = "5"   # id_tipo_orcam
OPERACAO_ESPECIAL = "7"        # id_tipo_acao
# Grafias da fonte que diferem do IBGE.
APELIDOS = {"DONA EUSEBIA": "DONA EUZEBIA", "BRASOPOLIS": "BRAZOPOLIS", "SAO THOME DAS LETRAS": "SAO TOME DAS LETRAS"}

TEXTO = {
    "resumo": "gastou",
    "onde": "em ações destinadas a",
    "nota": ("Distribuição informada pelos próprios órgãos do estado no acompanhamento do plano plurianual, por município "
             "de destino do bem ou serviço; inclui salários. Não entram aqui os repasses obrigatórios à prefeitura, a "
             "dívida e as aposentadorias, nem o que o estado registrou como \"diversos municípios\"."),
}


def _chave(nome: str) -> str:
    s = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("-", " ").replace("'", " ").split())


def baixar(nome: str) -> Path:
    arq = PASTA_BRUTO / f"{nome}.csv.gz"
    if arq.exists() and time.time() - arq.stat().st_mtime < VALIDADE:
        return arq
    arq.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"{BASE}{ARQUIVOS[nome]}/download/{nome}.csv.gz", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
            dados = resp.read()
    except Exception:
        if arq.exists():  # sem rede: fica o arquivo anterior
            return arq
        raise
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_bytes(dados)
    tmp.replace(arq)
    time.sleep(1)
    return arq


def ler(nome: str):
    with gzip.open(baixar(nome), "rt", encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


def resumir(ano: int, ibge_por_nome: dict[str, str]) -> tuple[dict, dict, dict]:
    """(por município, totais do estado, nomes das áreas)."""
    municipios = {r["id_municipio"]: r["nome"] for r in ler("dm_municipio_plan")}
    funcoes = {r["id_funcao"]: (f"{int(r['cd_funcao']):02d}", r["nome"]) for r in ler("dm_funcao_plan")}
    programas = {r["id_programa"]: " ".join(r["nome"].split()) for r in ler("dm_programa_plan")}
    orgaos = {r["id_orgao"]: " ".join(r["nome"].split()) for r in ler("dm_orgao_plan")}

    mun: dict = defaultdict(lambda: {"local": 0.0, "operacoes": 0.0, "empresas": 0.0, "areas": defaultdict(float), "itens": defaultdict(float)})
    tot = defaultdict(float)
    areas: dict[str, str] = {}
    for r in ler("ft_plan_acao_ppag"):
        if r["ano_ppag"] != str(ano):
            continue
        v = float(r["vr_realizado"] or 0)
        if not v:
            continue
        empresa, operacao = r["id_tipo_orcam"] == ORCAMENTO_DAS_EMPRESAS, r["id_tipo_acao"] == OPERACAO_ESPECIAL
        tot["empresas" if empresa else "empenhado"] += v
        nome = _chave(municipios.get(r["id_municipio"], ""))
        ibge = ibge_por_nome.get(APELIDOS.get(nome, nome))
        if not ibge:
            if not empresa:
                tot["diversos_estado" if nome.endswith("ESTADUAL") else "diversos_regiao" if nome.startswith("DIVERSOS") else "sem_municipio"] += v
            continue
        m = mun[ibge]
        if empresa:
            m["empresas"] += v
        elif operacao:
            m["operacoes"] += v
            tot["operacoes"] += v
        else:
            m["local"] += v
            tot["local"] += v
            cod, nome_area = funcoes.get(r["id_funcao"], ("00", "Outras"))
            m["areas"][cod] += v
            areas[cod] = " ".join(nome_area.split()).capitalize()
            m["itens"][(programas.get(r["id_programa"], "Programa não identificado"), orgaos.get(r["id_orgao"], ""))] += v
    saida = {}
    for ibge, m in mun.items():
        maiores = sorted(m["itens"].items(), key=lambda x: -x[1])[:MAIORES]
        saida[ibge] = {
            "local": round(m["local"]), "pago": 0, "folha": 0,
            "operacoes": round(m["operacoes"]), "empresas": round(m["empresas"]),
            "areas": {k: round(v) for k, v in sorted(m["areas"].items(), key=lambda x: -x[1]) if v > 0},
            # mesmo formato da Paraíba: [credor, ação, órgão, valor]; aqui não há credor
            "maiores": [["", programa, orgao, round(v)] for (programa, orgao), v in maiores if v > 0],
        }
    return saida, tot, areas


def main() -> None:
    p = argparse.ArgumentParser(prog="estado-mg", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    args = p.parse_args()

    ibge_por_nome = {_chave(e["ente"]): str(e["cod_ibge"]) for e in baixar_entes() if e["esfera"] == "M" and e["uf"] == "MG"}
    mun, tot, areas = resumir(args.ano, ibge_por_nome)
    if tot["empenhado"] < MINIMO_PLAUSIVEL:
        raise SystemExit(f"{args.ano}: a fonte traz só R$ {tot['empenhado'] / 1e9:.1f} bi; ano incompleto, nada foi gravado")

    doc = {"ano": args.ano, "ate_mes": 12, "fonte": "Portal de Dados Abertos de Minas Gerais (Planejamento e Monitoramento do PPAG)",
           "texto": TEXTO,
           "estado": {k: round(tot[k]) for k in ("empenhado", "local", "operacoes", "empresas", "diversos_regiao", "diversos_estado", "sem_municipio")},
           "areas": dict(sorted(areas.items())), "mun": mun}
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"{args.ano}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    bi = lambda k: f"R$ {tot[k] / 1e9:.1f} bi"
    print(f"{args.ano}: {bi('empenhado')} do orçamento do estado; {bi('local')} em ações com município ({len(mun)} municípios), "
          f"{bi('operacoes')} em operações especiais com município; sem cidade: {bi('diversos_estado')} no estado inteiro, "
          f"{bi('diversos_regiao')} em regiões, {bi('sem_municipio')} com nome não reconhecido; empresas: {bi('empresas')}")


if __name__ == "__main__":
    main()
