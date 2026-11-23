"""Preço pago comparado, fase 2: os remédios comprados nos pregões publicados no PNCP, de qualquer plataforma.

    uv run precos-pncp                       # baixa o que falta, do dia mais recente para trás, até 2025-01-01
    uv run precos-pncp --minutos 300         # para depois de 5 horas (o workflow usa isso)
    uv run precos-pncp --de 2026-09-01 --ate 2026-09-30

As prefeituras que não usam o Compras.gov.br compram por plataformas privadas (BNC, BLL, Licitanet, Portal de Compras
Públicas…) e publicam no Portal Nacional de Contratações Públicas sem o código CATMAT, com a descrição escrita à mão.
Este programa junta essas compras; quem compara é o `precos.py`, que lê o que este guarda.

Três passos, cada um guardado em data/raw/precos/pncp/ para a próxima execução continuar de onde parou:

1. **A lista do dia** (`/api/consulta/v1/contratacoes/publicacao`, modalidade 6, pregão eletrônico): uns 1.700 pregões
   por dia útil, em páginas de 50 que levam ~10 s cada. Fica só o que é de remédio (objeto com "medicamento" ou
   "farmácia"), em dias/{aaaammdd}.json.gz. É a parte lenta: umas 34 páginas por dia.
2. **Os itens da compra** (`/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens`): a descrição livre de cada item é
   casada com a lista de remédios (`precos.casar`).
3. **O resultado de cada item casado** (`…/itens/{n}/resultados`): o preço homologado, a quantidade e a empresa. O PNCP
   não tem resultado em lote: é uma chamada por item.

Guarda por compra, em compras/{cnpj}-{ano}-{seq}.json.gz: a compra (órgão, unidade, código IBGE, plataforma, datas) e
os itens casados com o resultado. Compra publicada há menos de 120 dias com item ainda sem resultado é consultada de
novo depois de 14 dias. Nunca guarda CPF: do fornecedor, só o CNPJ e o nome de pessoa jurídica.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT
from .precos import casar, sem_acento

PASTA = c.RAIZ / "data" / "raw" / "precos" / "pncp"
URL_LISTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
URL_PNCP = "https://pncp.gov.br/api/pncp/v1/orgaos"
INICIO = dt.date(2025, 1, 1)
REMEDIO = re.compile(r"MEDICAMENT|FARMAC|REMEDIO")
NAO_REMEDIO = re.compile(r"VETERINAR")   # o resto (manipulação, equipamento) os itens tiram, no casamento
LINHAS = 4
PAUSA = 1.0   # segundos depois de cada pedido, em cada linha: com 12 linhas sem pausa, o portal respondeu 429
_parar = threading.Event()


def _get(url: str, tentativas: int = 8) -> dict | list | None:
    """GET com espera crescente; 204 e 404 viram None. O portal limita os pedidos sem dizer quanto (429)."""
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120, context=CONTEXTO_TLS) as r:
                time.sleep(PAUSA)
                if r.status == 204:
                    return None
                return json.loads(r.read())
        except urllib.error.HTTPError as erro:
            if erro.code in (204, 404):
                return None
            time.sleep((30 if erro.code == 429 else 5) * (t + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError):
            time.sleep(5 * (t + 1))
    raise RuntimeError(f"sem resposta: {url}")


def _ler(arq):
    return json.loads(gzip.decompress(arq.read_bytes()))


def _gravar(arq, doc) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()))
    tmp.replace(arq)


def _resumo_compra(x: dict) -> dict:
    org, uni = x.get("orgaoEntidade") or {}, x.get("unidadeOrgao") or {}
    return {"cnpj": org.get("cnpj"), "ano": x.get("anoCompra"), "seq": x.get("sequencialCompra"), "esfera": org.get("esferaId"),
            "orgao": " ".join((org.get("razaoSocial") or "").split()), "unidade": " ".join((uni.get("nomeUnidade") or "").split()),
            "ibge": uni.get("codigoIbge") or "", "uf": uni.get("ufSigla") or "", "plataforma": x.get("usuarioNome") or "",
            "publicacao": (x.get("dataPublicacaoPncp") or "")[:10], "objeto": " ".join((x.get("objetoCompra") or "").split())[:300],
            "srp": x.get("srp"), "controle": x.get("numeroControlePNCP")}


def lista_do_dia(dia: dt.date) -> list[dict]:
    """Os pregões eletrônicos de remédio publicados no dia (guardados depois da primeira vez)."""
    arq = PASTA / "dias" / f"{dia:%Y%m%d}.json.gz"
    if arq.exists():
        return _ler(arq)
    compras, p = [], 1
    while not _parar.is_set():
        q = urllib.parse.urlencode({"dataInicial": f"{dia:%Y%m%d}", "dataFinal": f"{dia:%Y%m%d}", "codigoModalidadeContratacao": 6,
                                    "pagina": p, "tamanhoPagina": 50})
        d = _get(f"{URL_LISTA}?{q}")
        if not d:
            break
        for x in d.get("data") or []:
            obj = sem_acento(x.get("objetoCompra") or "")
            if REMEDIO.search(obj) and not NAO_REMEDIO.search(obj) and (x.get("orgaoEntidade") or {}).get("esferaId") in ("M", "E", "D"):
                compras.append(_resumo_compra(x))
        if p >= (d.get("totalPaginas") or 1):
            break
        p += 1
    else:
        return []   # interrompido: o dia não é guardado, e volta na próxima execução
    _gravar(arq, compras)
    return compras


def _arq_compra(x: dict):
    return PASTA / "compras" / f"{x['cnpj']}-{x['ano']}-{x['seq']}.json.gz"


def precisa_baixar(x: dict, hoje: dt.date) -> bool:
    arq = _arq_compra(x)
    if not arq.exists():
        return True
    doc = _ler(arq)
    if all(i.get("resultados") for i in doc["itens"]):
        return False
    publicada = dt.date.fromisoformat(x["publicacao"]) if x.get("publicacao") else hoje
    baixada = dt.date.fromisoformat(doc["baixada"])
    return (hoje - publicada).days < 120 and (hoje - baixada).days >= 14


def baixar_compra(x: dict, hoje: dt.date) -> int:
    """Os itens da compra casados com a lista de remédios e o resultado de cada um. Devolve quantas chamadas fez."""
    base = f"{URL_PNCP}/{x['cnpj']}/compras/{x['ano']}/{x['seq']}"
    itens, p, chamadas = [], 1, 0
    while True:
        d = _get(f"{base}/itens?pagina={p}&tamanhoPagina=500") or []
        chamadas += 1
        itens += d
        if len(d) < 500:
            break
        p += 1
    casados = []
    for i in itens:
        cod = casar(i.get("descricao") or "", i.get("unidadeMedida") or "")
        if cod is None:
            continue
        res = []
        if i.get("temResultado"):
            for r in _get(f"{base}/itens/{i['numeroItem']}/resultados") or []:
                if r.get("situacaoCompraItemResultadoId") not in (1, None) or r.get("dataCancelamento"):
                    continue
                pj = r.get("tipoPessoa") == "PJ"
                res.append({"preco": r.get("valorUnitarioHomologado"), "qtd": r.get("quantidadeHomologada"), "data": (r.get("dataResultado") or "")[:10],
                            "ordem": r.get("ordemClassificacaoSrp") or r.get("sequencialResultado") or 1,
                            "cnpj": (r.get("niFornecedor") or "") if pj else "",   # nunca o CPF
                            "fornecedor": " ".join((r.get("nomeRazaoSocialFornecedor") or "").split()) if pj else ""})
            chamadas += 1
        casados.append({"n": i.get("numeroItem"), "codigo": cod, "descricao": " ".join((i.get("descricao") or "").split())[:200],
                        "unidade": i.get("unidadeMedida"), "qtd": i.get("quantidade"), "estimado": i.get("valorUnitarioEstimado"),
                        "resultados": res})
    _gravar(_arq_compra(x), {**x, "baixada": hoje.isoformat(), "n_itens": len(itens), "itens": casados})
    return chamadas


def compras_guardadas():
    """Todas as compras já baixadas (para o precos.py)."""
    pasta = PASTA / "compras"
    if not pasta.exists():
        return
    for arq in sorted(pasta.glob("*.json.gz")):
        yield _ler(arq)


def main() -> None:
    p = argparse.ArgumentParser(prog="precos-pncp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--de", type=dt.date.fromisoformat, default=INICIO, help="primeiro dia de publicação (padrão 2025-01-01)")
    p.add_argument("--ate", type=dt.date.fromisoformat, default=None, help="último dia (padrão: ontem)")
    p.add_argument("--minutos", type=float, default=None, help="para depois desse tempo, guardando o que já baixou")
    p.add_argument("--linhas", type=int, default=LINHAS, help=f"downloads ao mesmo tempo (padrão {LINHAS})")
    args = p.parse_args()
    hoje = dt.date.today()
    ate = args.ate or hoje - dt.timedelta(days=1)
    fim = time.monotonic() + args.minutos * 60 if args.minutos else None
    if fim:
        threading.Thread(target=lambda: (time.sleep(max(0, fim - time.monotonic())), _parar.set()), daemon=True).start()

    # Do mais recente para trás: o ano atual fica pronto primeiro. Fim de semana entra (há publicação, pouca).
    dias = [ate - dt.timedelta(days=k) for k in range((ate - args.de).days + 1)]
    faltam = [d for d in dias if not (PASTA / "dias" / f"{d:%Y%m%d}.json.gz").exists()]
    print(f"{len(dias)} dias de {args.de} a {ate}; {len(faltam)} ainda sem a lista", flush=True)

    compras_total, chamadas, feitas = 0, 0, 0
    with ThreadPoolExecutor(args.linhas) as ex:
        # Para cada dia: a lista e, em seguida, as compras dela (assim a coleta avança junta e pode parar a qualquer hora).
        def dia_todo(d: dt.date) -> tuple[int, int]:
            if _parar.is_set():
                return 0, 0
            cs = lista_do_dia(d)
            n = 0
            for x in cs:
                if _parar.is_set():
                    break
                if precisa_baixar(x, hoje):
                    n += baixar_compra(x, hoje)
            return len(cs), n
        futuros = [ex.submit(dia_todo, d) for d in dias]
        for f in as_completed(futuros):
            n_compras, n_chamadas = f.result()
            compras_total += n_compras
            chamadas += n_chamadas
            feitas += 1
            if feitas % 20 == 0:
                print(f"  {feitas}/{len(dias)} dias; {compras_total} pregões de remédio; {chamadas} chamadas de itens e resultados", flush=True)
    guardadas = list(compras_guardadas())
    itens = sum(len(x["itens"]) for x in guardadas)
    com_preco = sum(1 for x in guardadas for i in x["itens"] if i["resultados"])
    sem_lista = sum(1 for d in dias if not (PASTA / "dias" / f"{d:%Y%m%d}.json.gz").exists())
    print(f"{'interrompido pelo tempo; ' if _parar.is_set() else ''}{len(guardadas)} pregões de remédio guardados, {itens} itens da lista "
          f"({com_preco} com preço homologado); faltam {sem_lista} dias")


if __name__ == "__main__":
    main()
