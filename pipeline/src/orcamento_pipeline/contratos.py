"""Contratos das prefeituras publicados no Portal Nacional de Contratações Públicas (PNCP).

    uv run contratos                 # contratos assinados no último ano fechado
    uv run contratos --ano 2025 --max-dias 60
    uv run contratos --sem-baixar    # só copia pipeline/referencia/contratos.json para o site (CI)

Fonte: a API de consulta do PNCP (/api/consulta/v1/contratos), que lista tudo o que foi publicado
num dia, de todas as esferas (cerca de 5 mil registros por dia, em páginas de 500). Baixa dia a dia,
pela data de publicação, do começo do ano até o fim de março do ano seguinte (contratos assinados
no fim do ano costumam ser publicados semanas depois), e guarda cada dia em
data/raw/pncp/contratos/{aaaammdd}.json.gz, só com prefeituras e câmaras (esfera M) e órgãos estaduais
(esfera E: governo, Assembleia, Justiça, Ministério Público… e o Distrito Federal, esfera D).

Por cidade e por estado (somando os órgãos estaduais, não as cidades), no ano da assinatura: quantos contratos, o valor somado, o valor por tipo (compras,
serviços, saúde, obras…), os 3 maiores contratos (o objeto e a empresa) e as 3 empresas que mais
receberam. Pessoas físicas e microempreendedores individuais (o nome do MEI é o da pessoa) não têm
o nome guardado: entram só nos totais. Contratos com valor maior que metade de todo o gasto da prefeitura (ou
do governo estadual) no ano são erro de digitação (há compras de livros de R$ 4,9 bilhões) e ficam de fora, contados à parte.
Vendas e cessões de bens da prefeitura também ficam de fora: nelas o dinheiro entra, não sai.

Saída em site/public/data/indicadores/contratos.json, com cópia em pipeline/referencia/contratos.json
(a primeira carga leva horas; nas seguintes, só os dias que faltam):
    {"fonte", "ano", "tipos": [...],
     "mun": {ibge: {"n", "total", "tipos": [valor por tipo, na ordem de "tipos"],
                    "maiores": [[objeto, valor, empresa ou null, raiz do CNPJ ou ""], ...],
                    "empresas": [[nome, valor, contratos, raiz do CNPJ], ...],
                    "pessoas": valor para pessoas físicas e MEI, "fora": [contratos, valor]}},
     "uf": {código: {... o mesmo, para os órgãos estaduais}}}
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

URL = "https://pncp.gov.br/api/consulta/v1/contratos"
PASTA = c.RAIZ / "data" / "raw" / "pncp" / "contratos"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "contratos.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "contratos.json"
MUNICIPIOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
FONTE = "Portal Nacional de Contratações Públicas (PNCP), contratos publicados"
ESTADOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "estados.json"
UF_CODIGO = {s: str(k) for k, s in c.SIGLAS.items()}

# Tipos do PNCP (categoriaProcesso) agrupados como aparecem na página.
TIPOS = ["Compras", "Serviços", "Serviços de saúde", "Obras e engenharia", "Aluguel de imóveis", "Outros"]
TIPO_DA_CATEGORIA = {2: 0, 4: 0, 8: 1, 6: 1, 3: 1, 10: 2, 7: 3, 9: 3, 5: 4}
# Cessão (1) e alienação de bens (11): a prefeitura cede ou vende um bem e quem paga é o outro lado.
NAO_E_GASTO = {1, 11}
# Um contrato só não passa de metade de tudo o que o ente gasta no ano: acima disso é erro de digitação
# (compras de alimentos de 84% do orçamento de uma cidade, livros de R$ 4,9 bilhões).
FATIA_MAXIMA = 0.5
PAUSA = 1.0   # segundos entre um pedido e outro de cada linha de download, para não passar do limite do portal
MEI = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}\s")   # "53.796.566 FRANCISCO …": a razão social do MEI leva o nome da pessoa


def baixar_pagina(dia: str, pagina: int) -> dict:
    q = urllib.parse.urlencode({"dataInicial": dia, "dataFinal": dia, "pagina": pagina, "tamanhoPagina": 500})
    for tentativa in range(8):
        try:
            req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as resp:
                time.sleep(PAUSA)
                if resp.status == 204:
                    return {"data": [], "totalPaginas": 0}
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
            if isinstance(erro, urllib.error.HTTPError) and erro.code == 404:
                return {"data": [], "totalPaginas": 0}
            # 429: o portal limita os pedidos (sem dizer quanto); espera cada vez mais.
            muitos = isinstance(erro, urllib.error.HTTPError) and erro.code == 429
            time.sleep((30 if muitos else 5) * (tentativa + 1))
    raise RuntimeError(f"{dia} p{pagina}: sem resposta")


def resumir_registro(x: dict) -> list | None:
    org, uni = x.get("orgaoEntidade") or {}, x.get("unidadeOrgao") or {}
    esfera = org.get("esferaId")
    if x.get("receita") or esfera not in ("M", "E", "D"):
        return None
    # Prefeitura: o código da cidade. Órgão estadual (ou do DF): o código do estado.
    chave = uni.get("codigoIbge") if esfera == "M" else UF_CODIGO.get(uni.get("ufSigla") or "", "53" if esfera == "D" else None)
    if not chave:
        return None
    cat = (x.get("categoriaProcesso") or {}).get("id")
    return [x.get("numeroControlePNCP"), chave, (x.get("dataAssinatura") or "")[:4], cat,
            x.get("tipoPessoa"), (x.get("niFornecedor") or "")[:8] if x.get("tipoPessoa") == "PJ" else "",   # nunca o CPF
            (x.get("nomeRazaoSocialFornecedor") or "").strip(),
            re.sub(r"\s+", " ", x.get("objetoContrato") or "").strip()[:220], x.get("valorGlobal") or 0]


# Download completo (--todos): todas as esferas, inclusive a federal, com os campos do explorador de
# contratos. Um registro por contrato, em data/raw/pncp/contratos-todos/{aaaammdd}.json.gz:
# [id, esfera, poder, ibge da unidade, UF, CNPJ do órgão, órgão, unidade, assinatura, categoria,
#  tipo de pessoa, CNPJ do fornecedor (vazio para pessoa física: o CPF não é guardado), fornecedor,
#  objeto, valor global, publicação]
PASTA_TODOS = c.RAIZ / "data" / "raw" / "pncp" / "contratos-todos"


def registro_completo(x: dict) -> list | None:
    org, uni = x.get("orgaoEntidade") or {}, x.get("unidadeOrgao") or {}
    if x.get("receita"):
        return None
    pessoa = x.get("tipoPessoa")
    return [x.get("numeroControlePNCP"), org.get("esferaId"), org.get("poderId"), uni.get("codigoIbge") or "",
            uni.get("ufSigla") or "", org.get("cnpj") or "", " ".join((org.get("razaoSocial") or "").split()),
            " ".join((uni.get("nomeUnidade") or "").split()), (x.get("dataAssinatura") or "")[:10],
            (x.get("categoriaProcesso") or {}).get("id"), pessoa, (x.get("niFornecedor") or "") if pessoa == "PJ" else "",
            " ".join((x.get("nomeRazaoSocialFornecedor") or "").split()),
            re.sub(r"\s+", " ", x.get("objetoContrato") or "").strip()[:600], x.get("valorGlobal") or 0,
            (x.get("dataPublicacaoPncp") or "")[:10]]


def baixar_dia_todos(dia: dt.date) -> int:
    arquivo = PASTA_TODOS / f"{dia:%Y%m%d}.json.gz"
    if arquivo.exists():
        return -1
    d = dia.strftime("%Y%m%d")
    primeira = baixar_pagina(d, 1)
    registros = list(primeira.get("data") or [])
    for p in range(2, (primeira.get("totalPaginas") or 1) + 1):
        registros += baixar_pagina(d, p).get("data") or []
    linhas = [r for r in map(registro_completo, registros) if r]
    tmp = arquivo.with_name(arquivo.name + ".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")).encode()))
    tmp.rename(arquivo)
    return len(linhas)


def baixar_dia(dia: dt.date) -> int:
    """Baixa um dia inteiro e guarda; devolve quantos registros de prefeituras e câmaras ele tem."""
    arquivo = PASTA / f"{dia:%Y%m%d}.json.gz"
    if arquivo.exists():
        return -1
    d = dia.strftime("%Y%m%d")
    primeira = baixar_pagina(d, 1)
    registros = list(primeira.get("data") or [])
    for p in range(2, (primeira.get("totalPaginas") or 1) + 1):
        registros += baixar_pagina(d, p).get("data") or []
    linhas = [r for r in map(resumir_registro, registros) if r]
    arquivo.write_bytes(gzip.compress(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")).encode()))
    return len(linhas)


def nome_empresa(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def agregar(ano: int) -> dict:
    gasto = {str(x["ibge"]): x["total"][0] for arq in (MUNICIPIOS, ESTADOS) if arq.exists()
             for x in json.loads(arq.read_text(encoding="utf-8"))["cidades"] if x.get("total")}
    vistos: set[str] = set()
    mun: dict[str, dict] = defaultdict(lambda: {"n": 0, "total": 0.0, "tipos": [0.0] * len(TIPOS), "contratos": [],
                                                "empresas": defaultdict(lambda: [Counter(), 0.0, 0]), "pessoas": 0.0, "fora": [0, 0.0]})
    for arquivo in sorted(PASTA.glob("*.json.gz")):
        for ident, ibge, ano_ass, cat, pessoa, cnpj, fornecedor, objeto, valor in json.loads(gzip.decompress(arquivo.read_bytes())):
            if ano_ass != str(ano) or not valor or valor <= 0 or ident in vistos or cat in NAO_E_GASTO:
                continue
            vistos.add(ident)
            m = mun[ibge]
            if gasto.get(ibge) and valor > gasto[ibge] * FATIA_MAXIMA:
                m["fora"][0] += 1
                m["fora"][1] += valor
                continue
            m["n"] += 1
            m["total"] += valor
            m["tipos"][TIPO_DA_CATEGORIA.get(cat, 5)] += valor
            empresa = pessoa == "PJ" and fornecedor and not MEI.match(fornecedor)
            if empresa:
                e = m["empresas"][cnpj]
                e[0][nome_empresa(fornecedor)] += 1
                e[1] += valor
                e[2] += 1
            else:
                m["pessoas"] += valor
            m["contratos"].append((valor, objeto, nome_empresa(fornecedor) if empresa else None, cnpj[:8] if empresa else ""))
    saida = {}
    for ibge, m in mun.items():
        if not m["n"]:
            continue
        maiores = sorted(m["contratos"], key=lambda x: -x[0])[:3]
        empresas = sorted(m["empresas"].items(), key=lambda x: -x[1][1])[:3]
        saida[ibge] = {"n": m["n"], "total": round(m["total"]), "tipos": [round(v) for v in m["tipos"]],
                       # o último campo é a raiz do CNPJ (8 dígitos), para o link aos contratos da empresa em
                       # todo o país (/contratos?empresa=); vazio para pessoa física e MEI
                       "maiores": [[o, round(v), f, r] for v, o, f, r in maiores],
                       "empresas": [[e[0].most_common(1)[0][0], round(e[1]), e[2], k[:8]] for k, e in empresas],
                       "pessoas": round(m["pessoas"]), "fora": [m["fora"][0], round(m["fora"][1])]}
    return {"fonte": FONTE, "ano": ano, "tipos": TIPOS,
            "mun": {k: v for k, v in sorted(saida.items()) if len(k) == 7},
            "uf": {k: v for k, v in sorted(saida.items()) if len(k) == 2}}


def limpar_cpf() -> None:
    """Tira de data/raw/pncp/contratos os 8 primeiros dígitos do CPF que os downloads antigos guardavam
    para pessoa física. Roda sempre (também na publicação, com o cache do GitHub), antes do espelho."""
    limpos = 0
    for arquivo in sorted(PASTA.glob("*.json.gz")):
        linhas = json.loads(gzip.decompress(arquivo.read_bytes()))
        if not any(r[4] != "PJ" and r[5] for r in linhas):
            continue
        for r in linhas:
            if r[4] != "PJ":
                r[5] = ""
        tmp = arquivo.with_name(arquivo.name + ".tmp")
        tmp.write_bytes(gzip.compress(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))
        tmp.replace(arquivo)
        limpos += 1
    if limpos:
        print(f"{limpos} dias sem o CPF de pessoa física em {PASTA.relative_to(c.RAIZ)}", flush=True)


def main() -> None:
    hoje = dt.date.today()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ano", type=int, default=hoje.year - 1, help="ano de assinatura (padrão: o último fechado)")
    p.add_argument("--max-dias", type=int, default=0, help="baixar no máximo este número de dias novos (0: todos)")
    p.add_argument("--paralelo", type=int, default=2, help="dias baixados ao mesmo tempo")
    p.add_argument("--sem-baixar", action="store_true", help="só copiar a referência versionada para o site (publicação automática)")
    p.add_argument("--todos", action="store_true", help="baixar todas as esferas, inclusive a federal, para o explorador (data/raw/pncp/contratos-todos)")
    args = p.parse_args()
    limpar_cpf()
    if args.sem_baixar:
        if REFERENCIA.exists():
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia de {REFERENCIA.relative_to(c.RAIZ)})")
        return

    if args.todos:
        PASTA_TODOS.mkdir(parents=True, exist_ok=True)
        fim = min(dt.date(args.ano + 1, 3, 31), hoje - dt.timedelta(days=1))
        dias = [dt.date(args.ano, 1, 1) + dt.timedelta(days=i) for i in range((fim - dt.date(args.ano, 1, 1)).days + 1)]
        faltam = [d for d in dias if not (PASTA_TODOS / f"{d:%Y%m%d}.json.gz").exists()]
        print(f"todas as esferas: {len(dias)} dias; faltam {len(faltam)}", flush=True)
        with ThreadPoolExecutor(args.paralelo) as ex:
            for i, (d, f) in enumerate({d: ex.submit(baixar_dia_todos, d) for d in faltam}.items(), 1):
                try:
                    f.result()
                except Exception as erro:
                    print(f"  {d}: {erro}", flush=True)
                if i % 25 == 0:
                    print(f"  {i} de {len(faltam)} dias", flush=True)
        print(f"pronto: {sum((PASTA_TODOS / f'{d:%Y%m%d}.json.gz').exists() for d in dias)} de {len(dias)} dias", flush=True)
        return
    PASTA.mkdir(parents=True, exist_ok=True)
    fim = min(dt.date(args.ano + 1, 3, 31), hoje - dt.timedelta(days=1))
    dias = [dt.date(args.ano, 1, 1) + dt.timedelta(days=i) for i in range((fim - dt.date(args.ano, 1, 1)).days + 1)]
    faltam = [d for d in dias if not (PASTA / f"{d:%Y%m%d}.json.gz").exists()]
    if args.max_dias:
        faltam = faltam[: args.max_dias]
    print(f"{len(dias)} dias de publicação; faltam {len(faltam)}", flush=True)
    feitos = falhas = 0
    with ThreadPoolExecutor(args.paralelo) as ex:
        futuros = {ex.submit(baixar_dia, d): d for d in faltam}
        for f, d in futuros.items():
            try:
                f.result()
                feitos += 1
            except Exception as erro:   # fica para a próxima execução
                falhas += 1
                print(f"  {d}: {erro}", flush=True)
            if (feitos + falhas) % 20 == 0:
                print(f"  {feitos + falhas} de {len(faltam)} dias", flush=True)

    completos = sum((PASTA / f"{d:%Y%m%d}.json.gz").exists() for d in dias)
    if completos < len(dias) and REFERENCIA.exists():
        # Sem todos os dias aqui (no CI, por exemplo), vale a cópia versionada.
        texto = REFERENCIA.read_text(encoding="utf-8")
        print(f"só {completos} de {len(dias)} dias baixados: usando {REFERENCIA.relative_to(c.RAIZ)}", flush=True)
    else:
        doc = agregar(args.ano)
        texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        if completos == len(dias):
            REFERENCIA.write_text(texto, encoding="utf-8")
        todos = [*doc["mun"].values(), *doc["uf"].values()]
        total = sum(x["total"] for x in todos)
        fora = sum(x["fora"][0] for x in todos)
        print(f"{args.ano}: {len(doc['mun'])} cidades ({sum(x['n'] for x in doc['mun'].values())} contratos) e {len(doc['uf'])} estados "
              f"({sum(x['n'] for x in doc['uf'].values())} contratos), R$ {total / 1e9:.1f} bi; "
              f"{fora} contratos com valor impossível deixados de fora", flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(texto, encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e6:.1f} MB)" + (f"; {falhas} dias falharam" if falhas else ""))


if __name__ == "__main__":
    main()
