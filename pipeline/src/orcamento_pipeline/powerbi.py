"""Leitura de painéis Power BI públicos ("Publicar na Web"), pela mesma API que a página do painel usa.

O link do painel (app.powerbi.com/view?r=…) traz, em base64, a chave pública do relatório ("k"). Com ela:
- modelsAndExploration dá o id do modelo de dados;
- conceptualschema dá as tabelas e colunas;
- querydata devolve as linhas, num formato compacto (DSR) que ler_dsr desfaz.

Sem login e sem captcha: é o que o navegador de qualquer visitante faz para desenhar o painel.
"""

from __future__ import annotations

import base64
import gzip
import json
import time
import urllib.request

from .fontes import CONTEXTO_TLS

HOST = "https://wabi-brazil-south-b-primary-api.analysis.windows.net"
UA = "Mozilla/5.0 (orcamento-brasileiro; dados abertos)"


def chave_do_link(r: str) -> str:
    """O "k" do parâmetro r= do link do painel."""
    r = r.replace("%3D", "=")
    return json.loads(base64.b64decode(r + "=" * (-len(r) % 4)))["k"]


def _pedir(k: str, caminho: str, corpo: dict | None = None, host: str = HOST):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(host + caminho, data=dados, headers={
        "X-PowerBI-ResourceKey": k, "User-Agent": UA, "Accept-Encoding": "gzip",
        **({"Content-Type": "application/json"} if dados else {})})
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(pedido, timeout=300, context=CONTEXTO_TLS) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
                    b = gzip.decompress(b)
            return json.loads(b)
        except Exception:
            if tentativa == 3:
                raise
            time.sleep(5 * (tentativa + 1))


def modelo(k: str) -> int:
    return _pedir(k, f"/public/reports/{k}/modelsAndExploration?preferReadOnlySession=true")["models"][0]["id"]


def esquema(k: str, modelo_id: int) -> dict[str, list[str]]:
    """tabela → colunas (e medidas)."""
    d = _pedir(k, "/public/reports/conceptualschema", {"modelIds": [modelo_id]})
    saida = {}
    for e in d["schemas"][0]["schema"]["Entities"]:
        saida[e["Name"]] = [p["Name"] for p in e.get("Properties", [])]
    return saida


def _valor(v):
    if isinstance(v, str) and len(v) > 1 and v[-1] in "DML" and v[:-1].replace(".", "", 1).lstrip("-").isdigit():
        return float(v[:-1])
    return v


def ler_dsr(ds: dict) -> list[list]:
    """As linhas de um conjunto DSR: cada linha traz só o que mudou ("R": repete da anterior; "Ø": nulo), e as colunas de
    texto podem vir como índice num dicionário (ValueDicts)."""
    dicts = ds.get("ValueDicts", {})
    linhas: list[list] = []
    esquema_cols: list[dict] | None = None
    anterior: list = []
    for ph in ds.get("PH", []):
        for chave, rows in ph.items():
            if not chave.startswith("DM"):
                continue
            for row in rows:
                if "S" in row:
                    esquema_cols = row["S"]
                    anterior = [None] * len(esquema_cols)
                n = len(esquema_cols or [])
                rep, nul = row.get("R", 0), row.get("Ø", 0)
                vals = iter(row.get("C", []))
                atual = []
                for i in range(n):
                    if rep >> i & 1:
                        atual.append(anterior[i])
                    elif nul >> i & 1:
                        atual.append(None)
                    else:
                        v = next(vals, None)
                        dn = esquema_cols[i].get("DN")
                        if dn and isinstance(v, int):
                            v = dicts[dn][v]
                        atual.append(_valor(v))
                linhas.append(atual)
                anterior = atual
    return linhas


def consultar(k: str, modelo_id: int, tabela: str, colunas: list[str], janela: int = 30000) -> list[dict]:
    """Todas as linhas distintas das colunas pedidas de uma tabela (agrupadas, como num visual de tabela). Inclua uma
    coluna que identifique a linha (o número da emenda), senão linhas iguais se juntam."""
    sel = [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": c}, "Name": f"t.{c}"} for c in colunas]
    linhas: list[list] = []
    reinicio = None
    while True:
        janela_q: dict = {"Count": janela}
        if reinicio:
            janela_q["RestartTokens"] = reinicio
        consulta = {"version": "1.0.0", "queries": [{"Query": {"Commands": [{"SemanticQueryDataShapeCommand": {
            "Query": {"Version": 2, "From": [{"Name": "t", "Entity": tabela, "Type": 0}], "Select": sel},
            "Binding": {"Primary": {"Groupings": [{"Projections": list(range(len(colunas)))}]},
                        "DataReduction": {"DataVolume": 3, "Primary": {"Window": janela_q}}, "Version": 1}}}]}}],
            "modelId": modelo_id}
        d = _pedir(k, "/public/reports/querydata?synchronous=true", consulta)
        res = d["results"][0]["result"]
        if "error" in res.get("data", {}).get("dsr", {}) or "error" in res:
            raise RuntimeError(f"Power BI recusou a consulta em {tabela}: {json.dumps(res)[:300]}")
        ds = res["data"]["dsr"]["DS"][0]
        linhas += ler_dsr(ds)
        reinicio = ds.get("RT")
        if not reinicio:
            break
    return [dict(zip(colunas, l)) for l in linhas]
