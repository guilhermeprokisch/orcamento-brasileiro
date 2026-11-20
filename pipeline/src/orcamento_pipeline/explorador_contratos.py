"""Arquivos do explorador de contratos (/contratos): um Parquet com todos os contratos e um resumo.

    uv run explorador-contratos

Lê os dias baixados do PNCP por contratos.py: o download completo (data/raw/pncp/contratos-todos,
todas as esferas, inclusive a federal) quando ele está inteiro; senão o das prefeituras e estados
(data/raw/pncp/contratos). Aplica os mesmos cortes da página da cidade: fora vendas e cessões de bens
(o dinheiro entra), e fora contratos maiores que metade de todo o gasto do ente no ano (erro de
digitação). Os federais não têm o gasto do órgão ao lado para comparar: ficam de fora os acima de
R$ 5 bilhões (em 2025, só erros; os maiores de verdade, do DNIT e do Serpro, ficam abaixo de R$ 4,5
bi). Uma unidade com mais de um contrato assim fica de fora inteira, porque os valores dela não são
confiáveis (em 2025, o Hospital Geral de Belém, do Exército: 41 de 100 contratos com R$ 10 bi a
R$ 640 bi, e os outros com valores de centenas de milhões para clínicas). O CPF de pessoa física
nunca entra; o nome entra, como o portal publica.

Saídas:
- data/publico/contratos-{ano}.parquet: um contrato por linha, ordenado por UF, ente e valor, em blocos
  de 30 mil linhas; o site consulta direto no bucket público (espelho.py envia data/publico/ para
  explorador/), baixando só os blocos de que precisa.
- data/publico/contratos-{ano}-por-cnpj.parquet: os mesmos contratos com empresa, ordenados por CNPJ,
  para a página de cada empresa.
- site/public/data/contratos/resumo.json: os números e rankings da página inicial, com cópia em
  pipeline/referencia/contratos-resumo.json para a publicação automática (--sem-baixar).
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from . import cidades as c
from .contratos import NAO_E_GASTO, PASTA, PASTA_TODOS, TIPO_DA_CATEGORIA, TIPOS, FATIA_MAXIMA

SAIDA_PARQUET = c.RAIZ / "data" / "publico" / "contratos-{ano}.parquet"
SAIDA_RESUMO = c.RAIZ / "site" / "public" / "data" / "contratos" / "resumo.json"
REFERENCIA_RESUMO = c.RAIZ / "pipeline" / "referencia" / "contratos-resumo.json"
NOMES = c.RAIZ / "site" / "public" / "data" / "mapa" / "nomes.json"
PREP_UF = {"AC": "do", "AL": "de", "AM": "do", "AP": "do", "BA": "da", "CE": "do", "DF": "do", "ES": "do", "GO": "de", "MA": "do",
           "MG": "de", "MS": "de", "MT": "de", "PA": "do", "PB": "da", "PE": "de", "PI": "do", "PR": "do", "RJ": "do", "RN": "do",
           "RO": "de", "RR": "de", "RS": "do", "SC": "de", "SE": "de", "SP": "de", "TO": "do"}
UF_CODIGO = {s: str(k) for k, s in c.SIGLAS.items()}
TETO = re.compile(r"credenciamento|chamamento p[uú]blico", re.I)
TETO_FEDERAL = 5e9   # acima disso, contrato federal é erro de digitação (ver acima)
MERENDA = re.compile(r"merenda|g[eê]neros aliment|alimenta[cç][aã]o escolar", re.I)


def dias(pasta: Path, ano: int) -> list[Path]:
    fim = min(dt.date(ano + 1, 3, 31), dt.date.today() - dt.timedelta(days=1))
    return [pasta / f"{dt.date(ano, 1, 1) + dt.timedelta(days=i):%Y%m%d}.json.gz" for i in range((fim - dt.date(ano, 1, 1)).days + 1)]


def linhas(ano: int):
    """Contratos do ano como dicionários, das duas pastas possíveis, já com os nomes de quem contratou."""
    nomes = json.loads(NOMES.read_text(encoding="utf-8"))
    completos = dias(PASTA_TODOS, ano)
    if all(a.exists() for a in completos):
        for arq in completos:
            for (ident, esfera, _poder, ibge, uf, cnpj_org, orgao, unidade, assin, cat, pessoa, cnpj, forn, obj, valor, publ) in \
                    json.loads(gzip.decompress(arq.read_bytes())):
                if esfera == "M" and ibge in nomes["mun"]:
                    ente, quem = ibge, f"Prefeitura de {nomes['mun'][ibge][0]}"
                elif esfera in ("E", "D"):
                    ente = "53" if esfera == "D" else UF_CODIGO.get(uf, "")
                    quem = "Governo do Distrito Federal" if ente == "53" else f"Governo {PREP_UF.get(uf, 'de')} {nomes['uf'].get(ente, ['?'])[0]}"
                elif esfera == "F":
                    ente, quem = "", " ".join(w.capitalize() if len(w) > 3 else w.lower() for w in orgao.split())
                else:
                    continue
                yield {"id": ident, "esfera": esfera if esfera != "D" else "E", "ente": ente, "uf": uf, "quem": quem,
                       "unidade": f"{cnpj_org} {unidade}" if esfera == "F" else "",
                       "ano": assin[:4], "cat": cat, "pessoa": pessoa, "cnpj": cnpj, "fornecedor": forn, "objeto": obj,
                       "valor": valor, "data": assin or publ}
        return
    print("o download completo (com os federais) ainda não terminou: só prefeituras e estados", flush=True)
    for arq in dias(PASTA, ano):
        if not arq.exists():
            continue
        publ = f"{arq.name[:4]}-{arq.name[4:6]}-{arq.name[6:8]}"
        for ident, chave, ano_ass, cat, pessoa, cnpj, forn, obj, valor in json.loads(gzip.decompress(arq.read_bytes())):
            mun = len(chave) == 7
            n = (nomes["mun"] if mun else nomes["uf"]).get(chave)
            if not n:
                continue
            quem = f"Prefeitura de {n[0]}" if mun else ("Governo do Distrito Federal" if chave == "53" else f"Governo {PREP_UF.get(n[1], 'de')} {n[0]}")
            yield {"id": ident, "esfera": "M" if mun else "E", "ente": chave, "uf": n[1], "quem": quem, "unidade": "", "ano": ano_ass,
                   "cat": cat, "pessoa": pessoa, "cnpj": cnpj if pessoa == "PJ" else "",   # nos dias antigos, os 8 dígitos de um CPF
                   "fornecedor": forn, "objeto": obj, "valor": valor, "data": publ}


def main() -> None:
    p = argparse.ArgumentParser(prog="explorador-contratos", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=dt.date.today().year - 1)
    p.add_argument("--sem-baixar", action="store_true", help="só copia o resumo versionado para o site (publicação automática)")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA_RESUMO.exists():
            SAIDA_RESUMO.parent.mkdir(parents=True, exist_ok=True)
            SAIDA_RESUMO.write_text(REFERENCIA_RESUMO.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA_RESUMO.relative_to(c.RAIZ)} (cópia de {REFERENCIA_RESUMO.relative_to(c.RAIZ)})")
        return
    gasto = {str(x["ibge"]): x["total"][0] for f in ("municipios", "estados")
             for x in json.loads((c.RAIZ / "site" / "public" / "data" / "cidades" / f"{f}.json").read_text(encoding="utf-8"))["cidades"] if x.get("total")}

    # Unidades federais com mais de um contrato impossível: fora inteiras (ver acima).
    impossiveis = Counter(r["unidade"] for r in linhas(args.ano)
                          if r["esfera"] == "F" and r["ano"] == str(args.ano) and (r["valor"] or 0) > TETO_FEDERAL)
    suspeitas = {u for u, n in impossiveis.items() if n > 1}
    for u in suspeitas:
        print(f"unidade federal fora: {u} ({impossiveis[u]} contratos acima de R$ {TETO_FEDERAL / 1e9:.0f} bi)")

    vistos: set[str] = set()
    tot = defaultdict(lambda: [0, 0.0])
    por_tipo = defaultdict(lambda: [0, 0.0])
    empresas = defaultdict(lambda: {"nome": Counter(), "lugares": set(), "n": 0, "valor": 0.0, "teto": 0.0})
    merenda = [0, 0.0]
    fora = 0
    with tempfile.TemporaryDirectory() as d:
        ndjson = Path(d) / "contratos.ndjson"
        with ndjson.open("w", encoding="utf-8") as saida:
            for r in linhas(args.ano):
                if r["ano"] != str(args.ano) or not r["valor"] or r["valor"] <= 0 or r["id"] in vistos or r["cat"] in NAO_E_GASTO:
                    continue
                vistos.add(r["id"])
                if (r["ente"] and gasto.get(r["ente"]) and r["valor"] > gasto[r["ente"]] * FATIA_MAXIMA) or \
                        (r["esfera"] == "F" and (r["valor"] > TETO_FEDERAL or r["unidade"] in suspeitas)):
                    fora += 1
                    continue
                tipo = TIPOS[TIPO_DA_CATEGORIA.get(r["cat"], 5)]
                teto = bool(TETO.search(r["objeto"]))
                linha = {"id": r["id"], "esfera": {"M": "Prefeitura", "E": "Governo estadual", "F": "Governo federal"}[r["esfera"]],
                         "ente": r["ente"], "uf": r["uf"], "quem": r["quem"], "tipo": tipo, "pessoa": r["pessoa"] or "",
                         "cnpj": r["cnpj"], "fornecedor": r["fornecedor"], "objeto": r["objeto"], "valor": round(r["valor"], 2),
                         "data": r["data"], "teto": teto}
                saida.write(json.dumps(linha, ensure_ascii=False) + "\n")
                t = tot[linha["esfera"]]
                t[0] += 1
                t[1] += r["valor"]
                pt = por_tipo[tipo]
                pt[0] += 1
                pt[1] += r["valor"]
                if MERENDA.search(r["objeto"]):
                    merenda[0] += 1
                    merenda[1] += r["valor"]
                if r["pessoa"] == "PJ" and r["cnpj"]:
                    e = empresas[r["cnpj"][:8]]
                    e["nome"][r["fornecedor"]] += 1
                    e["lugares"].add(r["ente"] or r["quem"])
                    e["n"] += 1
                    e["valor"] += r["valor"]
                    e["teto"] += r["valor"] if teto else 0
        destino = Path(str(SAIDA_PARQUET).format(ano=args.ano))
        destino.parent.mkdir(parents=True, exist_ok=True)
        duckdb.sql(f"""
            CREATE TABLE t AS SELECT id, esfera, ente, uf, quem, tipo, pessoa, cnpj, fornecedor, objeto, valor, CAST(data AS DATE) AS data, teto
                  FROM read_json('{ndjson}', format='newline_delimited', columns={{id:'VARCHAR', esfera:'VARCHAR', ente:'VARCHAR', uf:'VARCHAR',
                       quem:'VARCHAR', tipo:'VARCHAR', pessoa:'VARCHAR', cnpj:'VARCHAR', fornecedor:'VARCHAR', objeto:'VARCHAR',
                       valor:'DOUBLE', data:'VARCHAR', teto:'BOOLEAN'}})""")
        # Duas cópias: por lugar (busca, filtros, a página de uma cidade) e por CNPJ (a página de uma
        # empresa). A ordem faz o navegador baixar só os blocos onde está o que ele procura.
        duckdb.sql(f"COPY (SELECT * FROM t ORDER BY uf, ente, valor DESC) TO '{destino}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 30000)")
        por_cnpj = destino.with_name(destino.stem + "-por-cnpj.parquet")
        duckdb.sql(f"COPY (SELECT * FROM t WHERE cnpj <> '' ORDER BY cnpj, valor DESC) TO '{por_cnpj}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 10000)")

    empresa = lambda k, e: {"cnpj": k, "nome": e["nome"].most_common(1)[0][0], "lugares": len(e["lugares"]), "n": e["n"],
                            "valor": round(e["valor"]), "teto": e["teto"] > e["valor"] / 2}
    resumo = {
        "ano": args.ano, "fonte": "Portal Nacional de Contratações Públicas (PNCP)",
        "arquivo": f"https://f005.backblazeb2.com/file/orcamento-brasileiro-dados/explorador/{destino.name}",
        "porCnpj": f"https://f005.backblazeb2.com/file/orcamento-brasileiro-dados/explorador/{por_cnpj.name}",
        "total": {"n": sum(t[0] for t in tot.values()), "valor": round(sum(t[1] for t in tot.values()))},
        "esferas": {k: {"n": v[0], "valor": round(v[1])} for k, v in tot.items()},
        "tipos": sorted(([k, v[0], round(v[1])] for k, v in por_tipo.items() if v[1] > 0), key=lambda x: -x[2]),
        "merenda": {"n": merenda[0], "valor": round(merenda[1])},
        "fora": fora,
        "lugares": [empresa(k, e) for k, e in sorted(empresas.items(), key=lambda x: -len(x[1]["lugares"]))[:12]],
        "maiores": [empresa(k, e) for k, e in sorted(empresas.items(), key=lambda x: -x[1]["valor"])[:12]],
    }
    for alvo in (SAIDA_RESUMO, REFERENCIA_RESUMO):
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{resumo['total']['n']} contratos, R$ {resumo['total']['valor'] / 1e9:.1f} bi ({', '.join(f'{k}: {v[0]}' for k, v in tot.items())}); "
          f"{fora} acima de metade do orçamento ficaram de fora")
    print(f"saída: {destino.relative_to(c.RAIZ)} ({destino.stat().st_size / 1e6:.0f} MB) e {SAIDA_RESUMO.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
