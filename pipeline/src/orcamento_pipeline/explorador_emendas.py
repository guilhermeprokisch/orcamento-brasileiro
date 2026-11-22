"""Arquivos do explorador de emendas (/emendas): dois Parquet e um resumo.

    uv run explorador-emendas            # a partir do zip da CGU já baixado por emendas.py
    uv run explorador-emendas --sem-baixar   # só copia o resumo versionado (publicação automática)
    uv run explorador-emendas --so-copias    # refaz as cópias ordenadas e as fichas prontas (depois, uv run espelho)

Lê o arquivo "Emendas Parlamentares" da CGU (data/raw/cgu/emendas/EmendasParlamentares.zip):
- PorFavorecido: cada pagamento de uma emenda, com o autor, o tipo, o mês, quem recebeu e onde. Vira
  data/publico/emendas-pagamentos.parquet, com a área (função) de cada emenda, do arquivo principal, e
  quem recebeu agrupado em prefeitura, governo estadual, entidade sem fins lucrativos, empresa e outros.
- Os textos: os planos de trabalho das emendas Pix (transferências especiais), os convênios e as
  parcerias com entidades, cada um com o objeto declarado. Vira data/publico/emendas-textos.parquet.
- O resumo da página inicial: site/public/data/emendas-explorador/resumo.json, com cópia versionada em
  pipeline/referencia/emendas-explorador-resumo.json.

O nome de quem recebeu entra como a CGU publica; o CPF de pessoa física, não.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from . import cidades as c
from . import fichas_emendas
from .rfb import casador

ZIP = c.RAIZ / "data" / "raw" / "cgu" / "emendas" / "EmendasParlamentares.zip"
PASTA = c.RAIZ / "data" / "publico"
SAIDA_RESUMO = c.RAIZ / "site" / "public" / "data" / "emendas-explorador" / "resumo.json"
REFERENCIA_RESUMO = c.RAIZ / "pipeline" / "referencia" / "emendas-explorador-resumo.json"
URL = "https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/explorador"
FONTE = "Controladoria-Geral da União, Portal da Transparência: emendas parlamentares"

# Bancadas e comissões por extenso (a mesma lista de site/src/lib/autores-emendas.ts).
COLETIVOS = {
    "BANCADA DA BAHIA": "Bancada da Bahia", "BANCADA DA PARAIBA": "Bancada da Paraíba", "BANCADA DE ALAGOAS": "Bancada de Alagoas",
    "BANCADA DE GOIAS": "Bancada de Goiás", "BANCADA DE MINAS GERAIS": "Bancada de Minas Gerais", "BANCADA DE PERNAMBUCO": "Bancada de Pernambuco",
    "BANCADA DE RONDONIA": "Bancada de Rondônia", "BANCADA DE RORAIMA": "Bancada de Roraima", "BANCADA DE SANTA CATARINA": "Bancada de Santa Catarina",
    "BANCADA DE SAO PAULO": "Bancada de São Paulo", "BANCADA DE SERGIPE": "Bancada de Sergipe", "BANCADA DE TOCANTINS": "Bancada do Tocantins",
    "BANCADA DO ACRE": "Bancada do Acre", "BANCADA DO AMAPA": "Bancada do Amapá", "BANCADA DO AMAZONAS": "Bancada do Amazonas",
    "BANCADA DO CEARA": "Bancada do Ceará", "BANCADA DO DISTRITO FEDERAL": "Bancada do Distrito Federal", "BANCADA DO ESPIRITO SANTO": "Bancada do Espírito Santo",
    "BANCADA DO MARANHAO": "Bancada do Maranhão", "BANCADA DO MATO GROSSO": "Bancada de Mato Grosso", "BANCADA DO MATO GROSSO DO SUL": "Bancada de Mato Grosso do Sul",
    "BANCADA DO PARA": "Bancada do Pará", "BANCADA DO PARANA": "Bancada do Paraná", "BANCADA DO PIAUI": "Bancada do Piauí",
    "BANCADA DO RIO DE JANEIRO": "Bancada do Rio de Janeiro", "BANCADA DO RIO GRANDE DO NORTE": "Bancada do Rio Grande do Norte",
    "BANCADA DO RIO GRANDE DO SUL": "Bancada do Rio Grande do Sul",
    "COM. AGRICULTURA E REFORMA AGRARIA": "Comissão de Agricultura e Reforma Agrária",
    "COM. AGRICULTURA PEC ABAST D. RURAL": "Comissão de Agricultura, Pecuária, Abastecimento e Desenvolvimento Rural",
    "COM. ASSUNTOS SOCIAIS": "Comissão de Assuntos Sociais", "COM. CONST. JUSTICA E CIDADANIA": "Comissão de Constituição, Justiça e Cidadania",
    "COM. CULTURA": "Comissão de Cultura", "COM. DA SAUDE": "Comissão de Saúde",
    "COM. DE INTEGRACAO NACIONAL E DES. REGIONAL": "Comissão de Integração Nacional e Desenvolvimento Regional",
    "COM. DE PREVI., ASSIS. SOCI, INFAN., ADOL. E FAMIL": "Comissão de Previdência, Assistência Social, Infância, Adolescência e Família",
    "COM. DEFESA DOS DIREITOS DA MULHER": "Comissão de Defesa dos Direitos da Mulher", "COM. DESENV REGIONAL E TURISMO": "Comissão de Desenvolvimento Regional e Turismo",
    "COM. DESENV. URBANO": "Comissão de Desenvolvimento Urbano", "COM. DIREITOS HUMANOS E MINORIAS": "Comissão de Direitos Humanos e Minorias",
    "COM. EDUCACAO": "Comissão de Educação", "COM. EDUCACAO, CULTURA E ESPORTE": "Comissão de Educação, Cultura e Esporte", "COM. ESPORTE": "Comissão do Esporte",
    "COM. MISTA, PLAN.ORC.E FISCALIZACAO": "Comissão Mista de Orçamento", "COM. RELACOES EXT E DEFESA NACIONAL": "Comissão de Relações Exteriores e Defesa Nacional",
    "COM. SEG. PUBLICA E COMB. CRIME ORG": "Comissão de Segurança Pública e Combate ao Crime Organizado",
    "COM. SERV.DE INFRA-ESTRUTURA": "Comissão de Serviços de Infraestrutura", "COM. TURISMO": "Comissão de Turismo", "RELATOR GERAL": "Relator-geral do Orçamento",
}
PEQUENAS = {"de", "da", "do", "das", "dos", "e"}


def nome_autor(s: str) -> str:
    t = " ".join((s or "").split())
    t = re.sub(r"\s*\(EX-PARLAMENTAR.*$", "", t, flags=re.I)   # "JOAO CURY NETO (EX-PARLAMENTAR ALBERTO MOURAO, …)"
    if t.upper() in COLETIVOS:
        return COLETIVOS[t.upper()]
    if t.upper().startswith("COM. "):
        return "Comissão de " + t[5:].lower()
    return " ".join(p.lower() if i and p.lower() in PEQUENAS else p.capitalize() for i, p in enumerate(t.split()))


def cidade(s: str) -> str:
    """"RIO DE JANEIRO" → "Rio de Janeiro"."""
    return " ".join(p.lower() if i and p.lower() in PEQUENAS else p.capitalize() for i, p in enumerate((s or "").split()))


def tipo_curto(t: str) -> str:
    t = t or ""
    if "Especiais" in t:
        return "Pix"
    if "Individual" in t:
        return "Individual"
    if "Bancada" in t:
        return "Bancada"
    if "Comiss" in t:
        return "Comissão"
    if "Relator" in t:
        return "Relator"
    return "Outra"


def grupo(natureza: str) -> str:
    n = (natureza or "").lower()
    if "municipal" in n or n.startswith("município") or n.startswith("municipio"):
        return "Prefeitura"
    if "estadual" in n or n.startswith("estado") or "distrito federal" in n:
        return "Governo estadual"
    if re.search(r"associa|funda[cç][aã]o privada|organiza[cç][aã]o social|servi[cç]o social|entidade|organiza[cç][aã]o religiosa|cooperativa", n):
        return "Entidade sem fins lucrativos"
    if re.search(r"sociedade|empres[aá]ria|limitada|ltda|individual|eireli|an[oô]nima", n) and "pública" not in n and "publica" not in n:
        return "Empresa"
    return "Outros órgãos públicos"


def numero(s: str) -> float:
    return float((s or "0").replace(".", "").replace(",", ".") or 0)


def linhas(z: zipfile.ZipFile, nome: str):
    with z.open(nome) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def gravar(regs, destino: Path, colunas: dict[str, str], ordem: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        nd = Path(d) / "x.ndjson"
        with nd.open("w", encoding="utf-8") as f:
            for r in regs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cols = ", ".join(f"{k}:'{v}'" for k, v in colunas.items())
        duckdb.sql(f"COPY (SELECT * FROM read_json('{nd}', format='newline_delimited', columns={{{cols}}}) ORDER BY {ordem}) "
                   f"TO '{destino}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 50000)")


PRIMEIRO_ANO_SERIE = 2017   # em 2016 há R$ 9 bi pagos à Caixa (Bolsa Família) como "relator", sem autor: fica fora da série
TIPOS = ("Individual", "Pix", "Bancada", "Comissão", "Relator")
AREAS_NO_CRUZADO = 7


# Cópias ordenadas para as fichas da busca (/emendas/buscar): cada uma em ordem de uma chave e em blocos
# pequenos, para o navegador baixar só os blocos daquela emenda, parlamentar, entidade ou lugar (menos de
# 1 MB por ficha, em vez de 3 a 16 MB). Os arquivos principais continuam para a busca por texto e o explorador.
COPIAS = {   # chave no resumo: (arquivo de origem, filtro, ordem, arquivo da cópia)
    "emenda": ("emendas-pagamentos", "", "emenda, ano", "emendas-pagamentos-por-emenda"),
    "autor": ("emendas-pagamentos", "", "autor, ano, valor DESC", "emendas-pagamentos-por-autor"),
    "codigo": ("emendas-pagamentos", "WHERE codigo <> ''", "codigo, ano", "emendas-pagamentos-por-cnpj"),
    "lugar": ("emendas-pagamentos", "", "uf, ibge, ano, valor DESC", "emendas-pagamentos-por-lugar"),
    "textosEmenda": ("emendas-textos", "", "emenda", "emendas-textos-por-emenda"),
    "textosAutor": ("emendas-textos", "", "autor, fonte, ano", "emendas-textos-por-autor"),
    "textosCodigo": ("emendas-textos", "WHERE codigo <> ''", "codigo", "emendas-textos-por-cnpj"),
}


def gravar_copias() -> dict[str, str]:
    """Grava as cópias ordenadas em data/publico e devolve o endereço de cada uma no espelho."""
    urls = {}
    for chave, (base, onde, ordem, nome) in COPIAS.items():
        duckdb.sql(f"COPY (SELECT * FROM read_parquet('{PASTA / base}.parquet') {onde} ORDER BY {ordem}) "
                   f"TO '{PASTA / nome}.parquet' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 10000)")
        urls[chave] = f"{URL}/{nome}.parquet"
    return urls


def gravar_fichas() -> str:
    """As fichas prontas da busca (fichas_emendas.py); devolve o endereço da pasta da versão no espelho."""
    v = fichas_emendas.gerar(PASTA / "emendas-pagamentos.parquet", PASTA / "emendas-textos.parquet", PASTA / "fichas")
    return f"{URL}/fichas/{v}"


def panorama(parquet: Path, ano: int) -> dict:
    """A visão geral da página /emendas, a partir dos pagamentos: a série por tipo, para onde (áreas, quem recebe)
    e o cruzamento tipo → quem recebe → área do ano fechado, e os maiores autores coletivos."""
    con = duckdb.connect()
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{parquet}')")
    q = lambda s, *v: con.execute(s, list(v)).fetchall()
    serie = defaultdict(dict)
    for a, t, v in q("SELECT ano, tipo, sum(valor) FROM p WHERE ano >= ? GROUP BY ALL ORDER BY ano", PRIMEIRO_ANO_SERIE):
        serie[a][t] = round(v)
    meses = dict(q("SELECT ano, max(mes) FROM p GROUP BY ano"))
    areas = [[a or "Sem área", round(v)] for a, v in q("SELECT area, sum(valor) v FROM p WHERE ano = ? GROUP BY area ORDER BY v DESC", ano)]
    principais = {a for a, _ in areas[:AREAS_NO_CRUZADO] if a not in ("Múltiplo", "Sem área")}
    cruzado = defaultdict(float)
    for t, g, a, v in q("SELECT tipo, grupo, area, sum(valor) FROM p WHERE ano = ? GROUP BY ALL", ano):
        cruzado[(t, g, a if a in principais else "Outras áreas")] += v
    [(n_emendas, n_lugares, n_autores)] = q("SELECT count(DISTINCT emenda), count(DISTINCT nullif(ibge, '')), count(DISTINCT autor) FILTER (tipo IN ('Individual', 'Pix')) FROM p WHERE ano = ?", ano)
    coletivos = [[a, t, round(v)] for a, t, v in q("SELECT autor, tipo, sum(valor) v FROM p WHERE ano = ? AND tipo IN ('Bancada', 'Comissão') GROUP BY ALL ORDER BY v DESC LIMIT 12", ano)]
    [cota] = q("SELECT quantile_cont(v, 0.5) FROM (SELECT sum(valor) v FROM p WHERE ano = ? AND tipo IN ('Individual', 'Pix') GROUP BY autor HAVING v > 1e6)", ano)
    return {
        "serie": [{"ano": a, "parcial": meses.get(a, 12) < 12, "meses": meses.get(a, 12), **{t: serie[a].get(t, 0) for t in TIPOS}} for a in sorted(serie)],
        "areas": areas,
        "grupos": [[g, round(v)] for g, v in q("SELECT grupo, sum(valor) v FROM p WHERE ano = ? GROUP BY grupo ORDER BY v DESC", ano)],
        "cruzado": [[t, g, a, round(v)] for (t, g, a), v in sorted(cruzado.items(), key=lambda x: -x[1]) if v >= 1e6],
        "coletivos": coletivos,
        "contagem": {"emendas": n_emendas, "lugares": n_lugares, "parlamentares": n_autores, "mediana_individual": round(cota[0])},
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="explorador-emendas", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true")
    p.add_argument("--so-panorama", action="store_true", help="refaz só a visão geral do resumo, a partir do Parquet já gravado")
    p.add_argument("--so-copias", action="store_true", help="refaz só as cópias ordenadas e as fichas prontas, a partir dos Parquets já gravados")
    args = p.parse_args()
    if args.so_copias:
        resumo = json.loads(REFERENCIA_RESUMO.read_text(encoding="utf-8"))
        resumo["copias"] = gravar_copias()
        resumo["fichas"] = gravar_fichas()
        for alvo in (SAIDA_RESUMO, REFERENCIA_RESUMO):
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for u in resumo["copias"].values():
            f = PASTA / u.rsplit("/", 1)[1]
            print(f"saída: data/publico/{f.name} ({f.stat().st_size / 1e6:.0f} MB)")
        return
    if args.so_panorama:
        resumo = json.loads(REFERENCIA_RESUMO.read_text(encoding="utf-8"))
        resumo["panorama"] = panorama(PASTA / "emendas-pagamentos.parquet", resumo["ano"])
        for alvo in (SAIDA_RESUMO, REFERENCIA_RESUMO):
            alvo.write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"saída: {REFERENCIA_RESUMO.relative_to(c.RAIZ)} (panorama de {resumo['ano']})")
        return
    if args.sem_baixar:
        if REFERENCIA_RESUMO.exists():
            SAIDA_RESUMO.parent.mkdir(parents=True, exist_ok=True)
            SAIDA_RESUMO.write_text(REFERENCIA_RESUMO.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA_RESUMO.relative_to(c.RAIZ)} (cópia da referência)")
        return

    z = zipfile.ZipFile(ZIP)
    principal = {r["Código da Emenda"]: r for r in linhas(z, "EmendasParlamentares.csv")}
    ibge_de = casador()
    ano_fechado = dt.date.today().year - 1

    pagamentos = []
    por_autor = defaultdict(float)
    tipo_autor = {}
    entidades = defaultdict(lambda: {"nome": "", "lugar": "", "valor": 0.0, "autores": Counter()})
    por_tipo = defaultdict(float)
    for r in linhas(z, "EmendasParlamentares_PorFavorecido.csv"):
        am = r["Ano/Mês"].strip()
        if not am[:4].isdigit():
            continue
        v = numero(r["Valor Recebido"])
        uf, mun = r["UF Favorecido"].strip(), r["Município Favorecido"].strip()
        g = grupo(r["Natureza Jurídica"])
        pf = r["Tipo Favorecido"].strip().lower().startswith("pessoa f")
        emenda = principal.get(r["Código da Emenda"], {})
        autor = nome_autor(r["Nome do Autor da Emenda"])
        tipo = tipo_curto(r["Tipo de Emenda"])
        pagamentos.append({"emenda": r["Código da Emenda"], "ano": int(am[:4]), "mes": int(am[4:6] or 0), "autor": autor, "tipo": tipo,
                           "favorecido": " ".join(r["Favorecido"].split()), "codigo": "" if pf else r["Código do Favorecido"].strip(),
                           "grupo": g, "uf": uf, "municipio": cidade(mun), "ibge": (ibge_de(mun, uf) or "") if mun and uf else "",
                           "area": emenda.get("Nome Função", "") or "", "valor": round(v, 2)})
        if int(am[:4]) == ano_fechado:
            por_tipo[tipo] += v
            if tipo in ("Individual", "Pix"):
                por_autor[autor] += v
            if g == "Entidade sem fins lucrativos" and not pf:
                e = entidades[r["Código do Favorecido"].strip()]
                e["nome"], e["lugar"] = " ".join(r["Favorecido"].split()), f"{cidade(mun)} ({uf})" if mun else uf
                e["valor"] += v
                e["autores"][autor] += v

    textos = []
    for r in linhas(z, "EmendasParlamentares_PlanodeTrabalhoTransferenciasEspeciais.csv"):
        cod = r["Emenda Parlamentar"].strip()
        textos.append({"fonte": "Plano de emenda Pix", "emenda": cod, "ano": int(cod[:4]) if cod[:4].isdigit() else 0,
                       "autor": nome_autor(r["Autor da Emenda"]), "beneficiario": " ".join(r["Beneficiário"].split()),
                       "codigo": r["CNPJ do Beneficiário"].strip(), "uf": r["UF do Beneficiário"].strip(), "municipio": "",
                       "objeto": " ".join(r["Detalhamento do Objeto"].split())[:600], "valor": round(numero(r["Valor"]), 2)})
    for r in linhas(z, "EmendasParlamentares_Convenios.csv"):
        e = principal.get(r["Código da Emenda"], {})
        textos.append({"fonte": "Convênio", "emenda": r["Código da Emenda"], "ano": int(e.get("Ano da Emenda") or 0),
                       "autor": nome_autor(e.get("Nome do Autor da Emenda", "")), "beneficiario": " ".join(r["Convenente"].split()),
                       "codigo": "", "uf": e.get("UF", "") or "", "municipio": cidade(e.get("Município", "") or ""),
                       "objeto": " ".join(r["Objeto Convênio"].split())[:600], "valor": round(numero(r["Valor Convênio"]), 2)})
    for r in linhas(z, "EmendasParlamentares_Parcerias.csv"):
        cod = r["Emenda Parlamentar"].strip()
        textos.append({"fonte": "Parceria com entidade", "emenda": cod, "ano": int(cod[:4]) if cod[:4].isdigit() else 0,
                       "autor": nome_autor(r["Autor da Emenda"]), "beneficiario": " ".join(r["Beneficiário (Ente Recebedor)"].split()),
                       "codigo": r["CNPJ Beneficiário (Ente Recebedor)"].strip(), "uf": r["UF"].strip(), "municipio": cidade(r["Município"]),
                       "objeto": " ".join(r["Objeto"].split())[:600], "valor": round(numero(r["Valor (R$)"]), 2)})

    PASTA.mkdir(parents=True, exist_ok=True)
    gravar(pagamentos, PASTA / "emendas-pagamentos.parquet",
           {"emenda": "VARCHAR", "ano": "INTEGER", "mes": "INTEGER", "autor": "VARCHAR", "tipo": "VARCHAR", "favorecido": "VARCHAR",
            "codigo": "VARCHAR", "grupo": "VARCHAR", "uf": "VARCHAR", "municipio": "VARCHAR", "ibge": "VARCHAR", "area": "VARCHAR", "valor": "DOUBLE"},
           "ano, autor, valor DESC")
    gravar(textos, PASTA / "emendas-textos.parquet",
           {"fonte": "VARCHAR", "emenda": "VARCHAR", "ano": "INTEGER", "autor": "VARCHAR", "beneficiario": "VARCHAR", "codigo": "VARCHAR",
            "uf": "VARCHAR", "municipio": "VARCHAR", "objeto": "VARCHAR", "valor": "DOUBLE"}, "fonte, ano, valor DESC")

    copias = gravar_copias()
    fichas = gravar_fichas()

    anos = sorted({r["ano"] for r in pagamentos})
    resumo = {
        "fonte": FONTE, "ano": ano_fechado, "anos": anos,
        "pagamentos": f"{URL}/emendas-pagamentos.parquet", "textos": f"{URL}/emendas-textos.parquet",
        "copias": copias,
        "fichas": fichas,
        "total": round(sum(por_tipo.values())),
        "tipos": {k: round(v) for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])},
        "autores": [[a, round(v)] for a, v in sorted(por_autor.items(), key=lambda x: -x[1])[:10]],
        "entidades": [{"codigo": k, "nome": e["nome"], "lugar": e["lugar"], "valor": round(e["valor"]), "autor": e["autores"].most_common(1)[0][0]}
                      for k, e in sorted(entidades.items(), key=lambda x: -x[1]["valor"])[:10]],
        "nomes": sorted({r["autor"] for r in pagamentos}),   # para a busca reconhecer um parlamentar
        "panorama": panorama(PASTA / "emendas-pagamentos.parquet", ano_fechado),
    }
    for alvo in (SAIDA_RESUMO, REFERENCIA_RESUMO):
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sem_cidade = sum(1 for r in pagamentos if r["municipio"] and not r["ibge"])
    print(f"{len(pagamentos)} pagamentos ({anos[0]}–{anos[-1]}), {len(textos)} textos; {ano_fechado}: R$ {resumo['total'] / 1e9:.1f} bi; "
          f"{len(resumo['nomes'])} autores; {sem_cidade} pagamentos sem cidade reconhecida")
    for f in ("emendas-pagamentos.parquet", "emendas-textos.parquet"):
        print(f"saída: data/publico/{f} ({(PASTA / f).stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
