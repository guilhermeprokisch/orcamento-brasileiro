"""O mapa das emendas (/emendas/mapa): bolhas por município, retratos dos parlamentares e as emendas de
cada cidade, uma a uma.

    uv run emendas-mapa                # tudo, a partir dos Parquets do explorador (depois, uv run espelho)
    uv run emendas-mapa --sem-fotos    # idem, sem baixar fotos novas (usa as que já estão no cache)
    uv run emendas-mapa --sem-baixar   # só copia o resumo versionado (publicação automática)

Lê data/publico/emendas-pagamentos.parquet e emendas-textos.parquet (gravados por `uv run
explorador-emendas`, à mão) e o cadastro de deputados e senadores das APIs abertas da Câmara e do
Senado (legislaturas 55 a 57), para casar cada autor com a foto oficial.

Saída em data/publico/emendas-mapa/<versão>/ (o espelho leva para explorador/emendas-mapa/ no bucket;
a versão vem do conteúdo dos Parquets, como nas fichas da busca, e o cache nunca mistura duas cargas):
- municipios.json   {"anos", "mun": {ibge: {n, u, s: [R$ mil por ano], st: {tipo: [por ano]},
                     ar: [[área, R$ mil]×3], au: [[autor, R$ mil]×3], t: [[tipo, R$ mil]], ap: [[parlamentar, R$ mil]×3]}}}
- autores.json      {autor: {foto: "fotos/<slug>.jpg", casa, partido, uf}}, só quem casou com o cadastro
- por-autor.json    {"ibges": [...], "anos": [...], "autores": {autor: {tipo, t, p: [[i_mun, i_ano, R$ mil], ...]}}}
- mun/<ibge>.json   [[emenda, autor, tipo, ano_inicial, ano_final, R$ mil, favorecido, área, objeto], ...]
- fotos/<slug>.jpg  as fotos oficiais, copiadas (o site nunca aponta para a Câmara ou o Senado)
e um resumo pequeno em site/public/data/emendas-mapa/resumo.json (cópia em pipeline/referencia/), com o
endereço da versão no bucket, que a página lê no build. Localmente, um link simbólico em
site/public/data/emendas-mapa/<versão> aponta para a pasta gerada, para o servidor de desenvolvimento.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

import duckdb

from . import cidades as c
from .fichas_emendas import versao

PUBLICO = c.RAIZ / "data" / "publico"
PAGAMENTOS = PUBLICO / "emendas-pagamentos.parquet"
TEXTOS = PUBLICO / "emendas-textos.parquet"
SAIDA = PUBLICO / "emendas-mapa"
CACHE_FOTOS = c.RAIZ / "data" / "raw" / "parlamentares"
SAIDA_RESUMO = c.RAIZ / "site" / "public" / "data" / "emendas-mapa" / "resumo.json"
REFERENCIA_RESUMO = c.RAIZ / "pipeline" / "referencia" / "emendas-mapa-resumo.json"
URL = "https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/explorador/emendas-mapa"
LEGISLATURAS = (55, 56, 57)   # 2015–2019, 2019–2023, 2023–2027
PESSOA = ("Individual", "Pix")   # os tipos de emenda que têm um parlamentar por autor
DF = "5300108"
UA = {"User-Agent": "orcamento-brasileiro (github.com/guilhermeprokisch/orcamento-brasileiro)", "Accept": "application/json"}


def chave(nome: str) -> str:
    """Nome comparável: sem acento, sem pontuação, minúsculo, sem o "Dep."/"Sen." que o Portal às vezes põe."""
    n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    n = re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z ]", " ", n)).strip().lower()
    return re.sub(r"^(dep|sen|deputad[oa]|senador[a]?) ", "", n)


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", chave(nome)).strip("-") or "sem-nome"


def baixar_json(url: str, nome: str) -> dict:
    CACHE_FOTOS.mkdir(parents=True, exist_ok=True)
    arq = CACHE_FOTOS / nome
    if not arq.exists():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            arq.write_bytes(r.read())
    return json.loads(arq.read_text(encoding="utf-8"))


def cadastro() -> dict[str, dict]:
    """Deputados e senadores das legislaturas recentes, por nome comparável (nome de urna e nome civil)."""
    pessoas: dict[str, dict] = {}
    for leg in LEGISLATURAS:
        pag, url = 1, f"https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura={leg}&itens=100"
        while url:
            doc = baixar_json(url, f"camara-{leg}-{pag}.json")
            for d in doc["dados"]:
                pessoas.setdefault(chave(d["nome"]), {"nome": d["nome"], "foto": d["urlFoto"], "partido": d.get("siglaPartido"),
                                                       "uf": d.get("siglaUf"), "casa": "Câmara"})
            url = next((l["href"] for l in doc["links"] if l["rel"] == "next"), None)
            pag += 1
    for leg in LEGISLATURAS:
        doc = baixar_json(f"https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/{leg}.json", f"senado-{leg}.json")
        raiz = doc.get("ListaParlamentarLegislatura", doc).get("Parlamentares", {})
        lista = raiz.get("Parlamentar", []) if isinstance(raiz, dict) else raiz
        for p in lista if isinstance(lista, list) else [lista]:
            i = p.get("IdentificacaoParlamentar", {})
            if not i.get("NomeParlamentar"):
                continue
            reg = {"nome": i["NomeParlamentar"], "foto": (i.get("UrlFotoParlamentar") or "").replace("http://", "https://"),
                   "partido": i.get("SiglaPartidoParlamentar"), "uf": i.get("UfParlamentar"), "casa": "Senado"}
            # O nome de urna e o nome civil entram os dois: a emenda ora traz um, ora o outro.
            for n in (i["NomeParlamentar"], i.get("NomeCompletoParlamentar") or ""):
                if n:
                    pessoas.setdefault(chave(n), reg)
    return pessoas


def baixar_foto(url: str, destino: Path) -> bool:
    """Copia a foto oficial para o cache (uma vez) e de lá para a saída. Falha vira "sem foto", não erro."""
    cache = CACHE_FOTOS / "fotos" / destino.name
    if not cache.exists():
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]}), timeout=60) as r:
                dados = r.read()
            if len(dados) < 1000:
                return False
            cache.write_bytes(dados)
        except Exception:
            return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cache, destino)
    return True


def titulo(s: str | None) -> str | None:
    """Favorecido e objeto vêm em CAIXA ALTA; baixa para título simples, sem pretensão de acerto total."""
    if not s:
        return s
    s = s.strip()
    if s != s.upper():
        return s
    pequenas = {"de", "da", "do", "das", "dos", "e", "em", "para", "a", "o", "as", "os", "ao", "no", "na", "nos", "nas", "com", "por"}
    siglas = {"sus", "upa", "ubs", "mac", "ltda", "eireli", "me", "epp", "sa", "s/a", "caps", "samu", "esf"}
    out = []
    for i, w in enumerate(s.lower().split()):
        out.append(w if (w in pequenas and i) else (w.upper() if w in siglas else w.capitalize()))
    return " ".join(out)


def gerar(sem_fotos: bool) -> dict:
    v = versao(PAGAMENTOS, TEXTOS)
    pasta = SAIDA / v
    if pasta.exists():
        shutil.rmtree(pasta)
    (pasta / "mun").mkdir(parents=True)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW p AS SELECT * FROM '{PAGAMENTOS}' WHERE ibge IS NOT NULL AND ibge <> '' AND valor > 0")
    anos = [a for (a,) in con.sql("SELECT DISTINCT ano FROM p ORDER BY 1").fetchall()]
    i_ano = {a: i for i, a in enumerate(anos)}

    # ---- municipios.json
    serie: dict[str, dict] = defaultdict(dict)
    for ibge, ano, val in con.sql("SELECT ibge, ano, sum(valor) FROM p GROUP BY 1, 2").fetchall():
        serie[ibge][ano] = round(val / 1e3)
    por_tipo: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    for ibge, tipo, ano, val in con.sql("SELECT ibge, tipo, ano, sum(valor) FROM p GROUP BY 1, 2, 3").fetchall():
        por_tipo[ibge][tipo][ano] = round(val / 1e3)
    nome = {i: (n, u) for i, n, u in con.sql("SELECT ibge, mode(municipio), mode(uf) FROM p GROUP BY 1").fetchall()}

    def topn(coluna: str, n: int, onde: str = "") -> dict[str, list]:
        r: dict[str, list] = defaultdict(list)
        for ibge, k, val in con.sql(f"""
            SELECT ibge, {coluna}, valor FROM (
              SELECT ibge, {coluna}, sum(valor) AS valor,
                     row_number() OVER (PARTITION BY ibge ORDER BY sum(valor) DESC) AS r
              FROM p {onde} GROUP BY 1, 2) WHERE r <= {n}""").fetchall():
            r[ibge].append([k, round(val / 1e3)])
        return r

    areas, autores, tipos = topn("area", 3), topn("autor", 3), topn("tipo", 5)
    # O maior autor de um município quase nunca é gente (é o relator-geral, uma comissão, uma bancada):
    # os três maiores parlamentares vão à parte, para os retratos.
    pessoas = topn("autor", 3, f"WHERE tipo IN {PESSOA} AND autor <> 'Sem Informação'")
    mun = {}
    for ibge, por_ano in serie.items():
        n, u = nome.get(ibge, ("?", "?"))
        mun[ibge] = {"n": n, "u": u, "s": [por_ano.get(a, 0) for a in anos],
                     "st": {t: [s.get(a, 0) for a in anos] for t, s in por_tipo[ibge].items()},
                     "ar": areas.get(ibge, []), "au": autores.get(ibge, []), "t": tipos.get(ibge, []), "ap": pessoas.get(ibge, [])}
    (pasta / "municipios.json").write_text(json.dumps({"anos": anos, "unidade": "R$ mil", "mun": mun}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- autores.json: quem casou com o cadastro, com a foto copiada
    pessoas_cad = cadastro()
    autores_pessoa = con.sql(f"SELECT autor, sum(valor) FROM p WHERE tipo IN {PESSOA} AND autor <> 'Sem Informação' GROUP BY 1 ORDER BY 2 DESC").fetchall()
    casados, valor_ok, valor_total = {}, 0.0, 0.0
    for autor, val in autores_pessoa:
        valor_total += val
        reg = pessoas_cad.get(chave(autor))
        if not reg or not reg["foto"]:
            continue
        destino = pasta / "fotos" / f"{slug(autor)}.jpg"
        tem_foto = (not sem_fotos and baixar_foto(reg["foto"], destino)) or (sem_fotos and baixar_foto_do_cache(destino))
        casados[autor] = {"foto": f"fotos/{destino.name}" if tem_foto else None, "casa": reg["casa"], "partido": reg["partido"], "uf": reg["uf"]}
        if tem_foto:
            valor_ok += val
    (pasta / "autores.json").write_text(json.dumps(casados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- por-autor.json: onde cada autor pagou, por ano (o filtro "só este parlamentar")
    ibges = sorted(serie)
    i_mun = {k: i for i, k in enumerate(ibges)}
    por_autor: dict[str, dict] = {}
    for autor, ibge, ano, val in con.sql("SELECT autor, ibge, ano, sum(valor) FROM p GROUP BY 1, 2, 3").fetchall():
        por_autor.setdefault(autor, {"p": []})["p"].append([i_mun[ibge], i_ano[ano], round(val / 1e3)])
    for autor, tipo, total in con.sql("""
            SELECT autor, arg_max(tipo, v), sum(v) FROM (SELECT autor, tipo, sum(valor) AS v FROM p GROUP BY 1, 2) GROUP BY autor""").fetchall():
        por_autor[autor]["tipo"] = tipo
        por_autor[autor]["t"] = round(total / 1e3)
    for a in por_autor.values():
        a["p"].sort(key=lambda x: -x[2])
    (pasta / "por-autor.json").write_text(json.dumps({"ibges": ibges, "anos": anos, "unidade": "R$ mil", "autores": por_autor},
                                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- mun/<ibge>.json: as emendas de cada município, uma a uma
    con.execute(f"""
        CREATE TABLE t AS SELECT emenda, any_value(objeto) AS objeto FROM '{TEXTOS}'
          WHERE objeto IS NOT NULL AND objeto <> '' GROUP BY 1""")
    # Pagamento sem número de emenda não é uma emenda: agrupa por autor e favorecido, e não ganha objeto.
    con.execute("""
        CREATE TABLE e AS
        SELECT p.ibge, p.emenda, any_value(p.autor) AS autor, any_value(p.tipo) AS tipo,
               min(p.ano) AS a0, max(p.ano) AS a1, round(sum(p.valor) / 1e3)::BIGINT AS mil,
               arg_max(p.favorecido, p.valor) AS favorecido, arg_max(p.area, p.valor) AS area,
               CASE WHEN p.emenda = 'Sem informação' THEN NULL ELSE any_value(t.objeto) END AS objeto
        FROM p LEFT JOIN t USING (emenda)
        GROUP BY p.ibge, p.emenda, CASE WHEN p.emenda = 'Sem informação' THEN p.autor || '|' || p.favorecido ELSE '' END""")
    atual, linhas, n_emendas = None, [], 0

    def gravar():
        nonlocal n_emendas
        if atual is None:
            return
        linhas.sort(key=lambda l: -l[5])
        (pasta / "mun" / f"{atual}.json").write_text(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        n_emendas += len(linhas)
    for ibge, em, autor, tipo, a0, a1, mil, fav, area, obj in con.sql("SELECT * FROM e ORDER BY ibge").fetchall():
        if ibge != atual:
            gravar()
            atual, linhas = ibge, []
        linhas.append([em, autor, tipo, a0, a1, int(mil), titulo(fav), area, titulo(obj)])
    gravar()

    total = round(sum(v for s in serie.values() for v in s.values()))
    com_foto = sum(1 for a in casados.values() if a["foto"])
    resumo = {"versao": v, "base": f"{URL}/{v}", "anos": anos, "unidade": "R$ mil",
              "municipios": len(mun), "emendas": n_emendas, "total_mil": total,
              "brasilia_mil": sum(serie.get(DF, {}).values()),
              "parlamentares": {"autores": len(autores_pessoa), "com_foto": com_foto, "valor_com_foto": round(valor_ok / valor_total, 3) if valor_total else 0},
              "fonte": "Controladoria-Geral da União, Portal da Transparência: emendas parlamentares, pagamentos por favorecido; "
                       "fotos e dados dos parlamentares: Câmara dos Deputados e Senado Federal (dados abertos)"}
    tam = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
    print(f"versão {v}: {len(mun)} municípios · {n_emendas} emendas · {len(autores_pessoa)} parlamentares, {com_foto} com foto "
          f"({resumo['parlamentares']['valor_com_foto']:.1%} do valor) · {tam / 1e6:.0f} MB em {pasta.relative_to(c.RAIZ)}")
    return resumo


def baixar_foto_do_cache(destino: Path) -> bool:
    cache = CACHE_FOTOS / "fotos" / destino.name
    if not cache.exists():
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cache, destino)
    return True


def ligar_para_desenvolvimento(v: str) -> None:
    """site/public/data/emendas-mapa/<versão> → data/publico/emendas-mapa/<versão>: o servidor de desenvolvimento
    serve a pasta gerada no mesmo caminho que o site usa quando não há bucket. A pasta é ignorada pelo git."""
    alvo = SAIDA_RESUMO.parent / v
    if alvo.is_symlink() or alvo.exists():
        return
    alvo.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(SAIDA / v, alvo.parent), alvo)


def main() -> None:
    p = argparse.ArgumentParser(prog="emendas-mapa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia o resumo da referência (publicação automática)")
    p.add_argument("--sem-fotos", action="store_true", help="não baixa fotos novas; usa só as do cache")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA_RESUMO.exists():
            SAIDA_RESUMO.parent.mkdir(parents=True, exist_ok=True)
            SAIDA_RESUMO.write_text(REFERENCIA_RESUMO.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA_RESUMO.relative_to(c.RAIZ)} (cópia da referência)")
        return
    if not PAGAMENTOS.exists() or not TEXTOS.exists():
        raise SystemExit("faltam data/publico/emendas-pagamentos.parquet e emendas-textos.parquet: rode `uv run explorador-emendas` antes")
    resumo = gerar(args.sem_fotos)
    for alvo in (SAIDA_RESUMO, REFERENCIA_RESUMO):
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ligar_para_desenvolvimento(resumo["versao"])
    print(f"saída: {REFERENCIA_RESUMO.relative_to(c.RAIZ)} · depois, `uv run espelho` leva a pasta para o bucket")


if __name__ == "__main__":
    main()
