"""Gasto do governo da Paraíba empenho a empenho, com o município onde foi aplicado.

    uv run estado-pb 2025

A prestação de contas ao Tesouro (SICONFI) diz quanto o governo estadual gastou por área, mas
não onde. A Paraíba é o único estado que publica o município em cada empenho, numa API aberta
(https://api.dados.pb.gov.br, sem cadastro). Este comando baixa `despesas/orcamentarias` mês a
mês (cerca de 50 consultas por ano, uma por segundo) e soma por município.

O que o campo "município" significa, pelo que os dados mostram:
- em obras, serviços e compras, é onde a despesa acontece (a mesma construtora aparece em
  cidades diferentes, uma por obra);
- na folha de pagamento, é a sede do órgão: a folha da Polícia Militar inteira aparece em
  Cabedelo e a da Secretaria de Saúde em João Pessoa. Por isso a folha (grupo "Pessoal e
  Encargos Sociais") é somada à parte e não entra no gasto "localizado".

Cache em data/raw/estados/pb/orcamentarias-{ano}-{mes}.json.gz.
Saída em site/public/data/estados/pb/{ano}.json: por município (código do IBGE), o gasto
localizado, por área e as maiores despesas. Credores pessoa física (diárias, ajudas de custo)
entram nas somas, mas nunca pelo nome.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

from .cidades import RAIZ, baixar_entes
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://api.dados.pb.gov.br/api/v1/despesas/orcamentarias"
PASTA_BRUTO = RAIZ / "data" / "raw" / "estados" / "pb"
SAIDA = RAIZ / "site" / "public" / "data" / "estados" / "pb"
POR_PAGINA = 1000
INTERVALO = 1.0  # segundos entre consultas
GRUPO_PESSOAL = 1
MAIORES = 6
# Nomes que a API escreve diferente do IBGE (sem acento, maiúsculas) -> nome no IBGE.
APELIDOS = {"SANTAREM": "JOCA CLAUDINO", "CAMPO DE SANTANA": "TACIMA", "SAO DOMINGOS DE POMBAL": "SAO DOMINGOS",
            "SERIDO": "SAO VICENTE DO SERIDO", "PEDRO REGIO": "PEDRO REGIS", "SAO BENTO DE POMBAL": "SAO BENTINHO"}


def _chave(nome: str) -> str:
    s = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("-", " ").replace("'", " ").split())


def baixar_mes(ano: int, mes: int, refazer: bool = False) -> list[dict]:
    """Todas as linhas de um mês. Meses fechados ficam em cache; o mês corrente é sempre refeito."""
    arq = PASTA_BRUTO / f"orcamentarias-{ano}-{mes:02d}.json.gz"
    if arq.exists() and not refazer:
        return json.loads(gzip.decompress(arq.read_bytes()))
    linhas: list[dict] = []
    pagina = 1
    while True:
        url = API + "?" + urllib.parse.urlencode({"ano": ano, "mes": mes, "per_page": POR_PAGINA, "page": pagina})
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        for tentativa in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as resp:
                    doc = json.load(resp)
                break
            except Exception:
                if tentativa == 3:
                    raise
                time.sleep(5 * 2 ** tentativa)
        linhas += doc["dados"]
        time.sleep(INTERVALO)
        if pagina >= doc["paginacao"]["total_paginas"]:
            break
        pagina += 1
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")).encode()))
    tmp.replace(arq)
    return linhas


def eh_empresa(doc: str | None) -> bool:
    """CNPJ completo (14 dígitos). CPFs vêm mascarados e são de pessoas: não publicamos o nome."""
    d = "".join(ch for ch in (doc or "") if ch.isdigit())
    return len(d) == 14 and "*" not in (doc or "")


def resumir(linhas: list[dict], ibge_por_nome: dict[str, str]) -> tuple[dict, dict]:
    """(por município, totais do estado)."""
    mun: dict = defaultdict(lambda: {"local": 0.0, "pago": 0.0, "folha": 0.0, "areas": defaultdict(float), "itens": defaultdict(float)})
    tot = {"empenhado": 0.0, "pago": 0.0, "folha": 0.0, "sem_municipio": 0.0, "nomes_sem_ibge": defaultdict(float)}
    for l in linhas:
        v, pago = float(l.get("valorEmpenhado") or 0), float(l.get("valorPago") or 0)
        tot["empenhado"] += v
        tot["pago"] += pago
        folha = l.get("codigoGrupo") == GRUPO_PESSOAL
        if folha:
            tot["folha"] += v
        nome = _chave(l.get("municipio") or "")
        ibge = ibge_por_nome.get(APELIDOS.get(nome, nome))
        if not ibge:
            tot["sem_municipio"] += v
            if nome:
                tot["nomes_sem_ibge"][nome] += v
            continue
        m = mun[ibge]
        if folha:
            m["folha"] += v
            continue
        m["local"] += v
        m["pago"] += pago
        m["areas"][f"{int(l['codigoFuncao']):02d}"] += v
        credor = " ".join((l.get("nomeCredor") or "").split()) if eh_empresa(l.get("cpfCnpjCredor")) else "Pessoas físicas"
        m["itens"][(credor, " ".join((l.get("nomeAcao") or "").split()), " ".join((l.get("nomeOrgao") or "").split()))] += v
    saida = {}
    for ibge, m in mun.items():
        maiores = sorted(m["itens"].items(), key=lambda x: -x[1])[:MAIORES]
        saida[ibge] = {
            "local": round(m["local"]), "pago": round(m["pago"]), "folha": round(m["folha"]),
            "areas": {k: round(v) for k, v in sorted(m["areas"].items(), key=lambda x: -x[1]) if v > 0},
            "maiores": [[credor, acao, orgao, round(v)] for (credor, acao, orgao), v in maiores if v > 0],
        }
    return saida, tot


def main() -> None:
    p = argparse.ArgumentParser(prog="estado-pb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    args = p.parse_args()
    hoje = date.today()
    ultimo_mes = 12 if args.ano < hoje.year else hoje.month

    ibge_por_nome = {_chave(e["ente"]): str(e["cod_ibge"]) for e in baixar_entes() if e["esfera"] == "M" and e["uf"] == "PB"}
    linhas: list[dict] = []
    for mes in range(1, ultimo_mes + 1):
        do_mes = baixar_mes(args.ano, mes, refazer=args.ano == hoje.year and mes >= hoje.month - 1)
        linhas += do_mes
        print(f"  {args.ano}-{mes:02d}: {len(do_mes)} linhas", flush=True)
    mun, tot = resumir(linhas, ibge_por_nome)

    nomes_areas = {f"{int(l['codigoFuncao']):02d}": " ".join(l["nomeFuncao"].split()).capitalize() for l in linhas}
    doc = {"ano": args.ano, "ate_mes": ultimo_mes, "fonte": "Portal de Dados Abertos da Paraíba (api.dados.pb.gov.br)",
           "estado": {k: round(tot[k]) for k in ("empenhado", "pago", "folha", "sem_municipio")},
           "areas": dict(sorted(nomes_areas.items())), "mun": mun}
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"{args.ano}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    local = sum(m["local"] for m in mun.values())
    print(f"{args.ano}: R$ {tot['empenhado'] / 1e9:.2f} bi empenhados, R$ {tot['folha'] / 1e9:.2f} bi de folha; "
          f"R$ {local / 1e9:.2f} bi localizados em {len(mun)} municípios; sem município reconhecido: R$ {tot['sem_municipio'] / 1e6:.1f} mi")
    for nome, v in sorted(tot["nomes_sem_ibge"].items(), key=lambda x: -x[1])[:12]:
        print(f"    sem código do IBGE: {nome} (R$ {v / 1e6:.2f} mi)")


if __name__ == "__main__":
    main()
