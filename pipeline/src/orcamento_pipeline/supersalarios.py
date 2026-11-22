"""Juízes, desembargadores, procuradores e promotores que recebem acima do teto, somados por órgão.

    uv run supersalarios               # baixa o que falta desde jan/2025 e monta o arquivo do site
    uv run supersalarios --sem-baixar  # só copia pipeline/referencia/supersalarios.json

Fonte: DadosJusBr (https://dadosjusbr.org), que coleta todo mês os contracheques que os tribunais mandam ao
CNJ e os que os Ministérios Públicos publicam, e padroniza as rubricas. Para cada órgão e ano,
api.dadosjusbr.org/v2/dados/{órgão}/{ano} lista os meses coletados e o pacote de cada um (um zip no S3,
sem cadastro, licença CC-BY 4.0). Do pacote se lê só remuneracao.csv: uma linha por rubrica de cada
contracheque (tipo R/B = subsídio, R/O = o que vem por cima, D = desconto), com a classificação do
DadosJusBr (desambiguacao_macro). O contracheque.csv, que traz o nome, nunca é aberto.

Para cada contracheque do mês, "o que conta" = subsídio − retenção pelo teto + tudo o que vem por cima,
menos o 13º e o terço de férias (pagos uma vez por ano a todos), as diárias (reembolso de viagem) e a
remuneração paga pelo órgão de origem (já contada lá). Passa do teto quem tem "o que conta" acima do
subsídio de ministro do STF do mês. A conta usa sempre o teto nacional, mesmo nos estados (o mais
generoso).

Ficam de fora os tribunais eleitorais e os conselhos (CNJ e CJF), que pagam só uma gratificação a juízes que
recebem o salário em outro tribunal e contariam a mesma pessoa duas vezes, e os tribunais superiores (STF,
STJ, TST, STM): os arquivos deles misturam ministros na ativa, aposentados, pensionistas e juízes convocados
de outros tribunais. E, em todos, só conta o contracheque com subsídio pago pelo órgão no mês (fora ficam
pensionistas, requisitados e quem só recebe uma diferença).

Nada aqui guarda pessoa: o cache em data/raw/supersalarios/{órgão}/{ano}-{mês}.json.gz tem só as somas
de cada órgão no mês. A saída também: por órgão e por período, quantos passam do teto num mês típico,
quanto passou no total, de onde vem o dinheiro e quantos ficam em cada faixa (faixa com menos de 5
pessoas sai como null).

Saída em site/public/data/indicadores/supersalarios.json, com cópia em pipeline/referencia/.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import shutil
import statistics
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://api.dadosjusbr.org/v2"
PASTA = RAIZ / "data" / "raw" / "supersalarios"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios.json"
FONTE = "DadosJusBr (dadosjusbr.org), a partir dos contracheques enviados ao CNJ e publicados pelos Ministérios Públicos"
INICIO = (2025, 1)
MINIMO = 5   # menos que isso numa faixa (ou acima do teto, num órgão) não aparece

# Subsídio de ministro do STF a partir de cada mês (Lei 14.520/2023). Em 2026 não houve reajuste.
TETOS = [((2023, 4), 41650.92), ((2024, 2), 44008.52), ((2025, 2), 46366.19)]

# Os dois períodos do site. Em 25/03/2026 o STF limitou o que vem por cima do subsídio (70% do teto), com
# efeito nos pagamentos de maio (em abril os tribunais ainda pagaram como antes): antes e depois são
# comparados lado a lado, nunca somados.
PERIODOS = [
    {"id": "2025", "de": (2025, 1), "ate": (2025, 12), "rotulo": "2025"},
    {"id": "2026", "de": (2026, 5), "ate": (2099, 12), "rotulo": "desde maio de 2026"},
]

# As famílias de rubricas, na ordem da "escada": cada degrau soma uma família ao que vem antes.
GRUPOS = ["subsidio", "pessoais", "acumulo", "ferias", "retroativos", "auxilios"]
NOMES_GRUPOS = {
    "subsidio": "Subsídio, menos o corte pelo teto",
    "pessoais": "Vantagens pessoais (tempo de serviço, abono de permanência)",
    "acumulo": "Acúmulo de funções, plantão, licença compensatória, substituições",
    "ferias": "Férias e licenças vendidas",
    "retroativos": "Pagamentos atrasados e rubricas que não dizem o que são",
    "auxilios": "Auxílios (saúde, alimentação, creche, moradia)",
}
PESSOAIS = {"tempo-de-servico", "abono-permanencia", "irredutibilidade", "pae", "vpni", "adicional-tempo-servico"}
ACUMULO = {"grat-exercicio-cumulativo", "licenca-compensatoria", "plantao", "grat-funcao", "substituicao", "grat-outras",
           "grat-acervo", "grat-localidade", "dif-entrancia", "hora-extra", "jeton", "grat-encargo", "gratificacao-encargos"}
FERIAS = {"indenizacao-ferias", "licenca-premio", "abono-pecuniario"}
FORA = {"grat-natalina", "terco-constitucional-ferias", "diarias", "remuneracao-origem"}
# Faixas do quanto passa do teto no mês, em reais. O cache guarda um histograma de R$ 10 mil em R$ 10 mil
# (o último degrau junta tudo acima de R$ 300 mil), para mudar as faixas sem baixar de novo.
FAIXAS = [10_000, 50_000, 100_000]
DEGRAU, DEGRAUS = 10_000, 30

TIPOS = {  # (entidade, jurisdição) do DadosJusBr -> tipo no site
    ("Tribunal", "Estadual"): "tj", ("Ministério", "Ministério"): "mp", ("Tribunal", "Trabalho"): "trabalho",
    ("Tribunal", "Federal"): "federal", ("Tribunal", "Militar"): "militar",
}
NOMES_TIPOS = {"tj": "Tribunais de justiça dos estados", "mp": "Ministérios Públicos", "trabalho": "Justiça do Trabalho",
               "federal": "Justiça Federal", "militar": "Justiça Militar"}
FORA_DA_CONTA = {"tse"}


# Quem paga: a Justiça Federal, a do Trabalho, o Ministério Público da União e a Justiça e o MP do Distrito
# Federal estão no orçamento da União; os tribunais de justiça, os MPs e as justiças militares dos estados, no
# do estado. O imposto de renda que cada um desconta é de quem paga (Constituição, art. 157, I).
DA_UNIAO = {"mpf", "mpt", "mpm", "tjdft", "mpdft"}


def pagador(o: dict) -> str:
    return "uniao" if o["tipo"] in ("trabalho", "federal") or o["id"] in DA_UNIAO else "estado"


def teto(ano: int, mes: int) -> float:
    return [v for (a, m), v in TETOS if (ano, mes) >= (a, m)][-1]


# Quando o DadosJusBr não classificou a rubrica (comum em 2026, com o contracheque único), a família sai do
# nome da rubrica e, para as vantagens pessoais, da categoria do CNJ.
PELO_NOME = [
    ("fora", re.compile(r"natalina|13[º°o]? sal|1/3|ter[çc]o (constitucional )?de f[ée]rias|di[áa]rias", re.I)),
    ("pessoais", re.compile(r"tempo de servi|\bATS\b|VPNI|PVTAC|adicionais temporais|quinqu[êe]n|anu[êe]nio|abono de perman|irredutib", re.I)),
    ("acumulo", re.compile(r"compensat|folga|acervo|ac[úu]mulo|cumulativ|plant[ãa]o|substitui|hora.? extra|jeton", re.I)),
    ("ferias", re.compile(r"f[ée]rias|licen[çc]a.?pr[êe]mio|abono pecuni", re.I)),
    ("auxilios", re.compile(r"aux[íi]lio|assist[êe]ncia (m[ée]dica|sa[úu]de)|ajuda de custo", re.I)),
]


def grupo(macro: str, categoria: str = "", item: str = "") -> str:
    if not macro:
        for nome, padrao in PELO_NOME:
            if padrao.search(item):
                return nome
        if "pessoa" in categoria.lower():
            return "pessoais"
        return "retroativos"
    if macro in FORA:
        return "fora"
    if macro.startswith("aux-"):
        return "auxilios"
    for nome, conj in (("pessoais", PESSOAIS), ("acumulo", ACUMULO), ("ferias", FERIAS)):
        if macro in conj:
            return nome
    return "retroativos"   # opaco, misturada, sem classificação, retroativos, URV, juros e correção


def _get(url: str, timeout: int = 120) -> bytes:
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout, context=CONTEXTO_TLS) as resp:
                return resp.read()
        except urllib.error.HTTPError as erro:
            if erro.code in (400, 403, 404):   # 403: o Portal da Transparência responde assim ao arquivo que ainda não saiu
                raise
            if tentativa == 3:
                raise
        except Exception:
            if tentativa == 3:
                raise
        time.sleep(5 * (tentativa + 1))
    raise RuntimeError("inalcançável")


def _valor(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


# Imposto de renda: na faixa de cima da tabela mensal, 27,5% menos a parcela a deduzir (R$ 896,00 até abril de
# 2025, R$ 908,73 desde maio de 2025; a mudança de 2026 só mexeu nas rendas até R$ 7.350).
ALIQUOTA_IR = 0.275
PARCELAS_IR = [((2023, 5), 884.96), ((2024, 2), 896.00), ((2025, 5), 908.73)]


def parcela_ir(ano: int, mes: int) -> float:
    return [v for (a, m), v in PARCELAS_IR if (ano, mes) >= (a, m)][-1]


def _e_ir(item: str) -> bool:
    i = item.lower()
    if any(x in i for x in ("13", "natal", "féria", "feria")):
        return False   # IR do 13º e das férias, cobrado à parte
    return "imposto" in i or i.startswith("ir") or "irrf" in i


def _e_previdencia(item: str) -> bool:
    i = item.lower()
    return any(x in i for x in ("previd", "pss", "contribui")) and "teto" not in i


def somar_pacote(conteudo: bytes, t: float, parcela: float = 908.73) -> dict:
    """As somas de um órgão num mês, a partir do remuneracao.csv do pacote. Nada por pessoa sai daqui.

    Além do que passa do teto, soma o imposto de renda e a previdência descontados e o imposto que seria
    cobrado se tudo o que conta fosse tributado como salário (27,5% do que sobra depois da previdência, menos a
    parcela a deduzir): a diferença é o que deixa de ser cobrado porque parte do pagamento se chama indenização."""
    por_cc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    macros: Counter = Counter()
    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        with zf.open("remuneracao.csv") as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", newline=""), delimiter=";"):
                v = _valor(r.get("valor"))
                if not v:
                    continue
                tipo, cc = r.get("tipo"), r.get("id_contracheque")
                if tipo == "R/B":
                    por_cc[cc]["subsidio"] += v
                    por_cc[cc]["bruto_base"] += v
                elif tipo == "R/O":
                    macro = (r.get("desambiguacao_macro") or "").strip()
                    item = (r.get("item") or "").strip()
                    g = grupo(macro, r.get("categoria") or "", item)
                    macros[(g, macro or f"(sem classificação) {item[:60]}")] += v
                    por_cc[cc][g] += v
                elif tipo == "D":
                    item = r.get("item") or ""
                    if "teto" in item.lower():
                        por_cc[cc]["subsidio"] -= abs(v)   # a retenção vem como desconto
                    elif _e_ir(item):
                        por_cc[cc]["ir"] += abs(v)
                    elif _e_previdencia(item):
                        por_cc[cc]["prev"] += abs(v)
    grupos = {g: 0.0 for g in GRUPOS}
    camadas = [[0, 0.0] for _ in GRUPOS]
    hist = [0] * (DEGRAUS + 1)
    totais: list[float] = []
    acima = 0
    excesso = 0.0
    ir = prev = ir_salario = 0.0
    for partes in por_cc.values():
        if partes.get("bruto_base", 0.0) <= 0:
            continue   # sem subsídio pago pelo órgão: pensionista, requisitado, convocado de outro tribunal
        soma = 0.0
        for i, g in enumerate(GRUPOS):
            soma += partes.get(g, 0.0)
            grupos[g] += partes.get(g, 0.0)
            if soma > t:
                camadas[i][0] += 1
                camadas[i][1] += soma - t
        if soma <= 0:
            continue
        totais.append(soma)
        ir += partes.get("ir", 0.0)
        prev += partes.get("prev", 0.0)
        ir_salario += max(0.0, ALIQUOTA_IR * (soma - partes.get("prev", 0.0)) - parcela)
        if soma > t:
            acima += 1
            excesso += soma - t
            hist[min(DEGRAUS, int((soma - t - 0.005) // DEGRAU))] += 1
    return {
        "membros": len(totais), "acima": acima, "excesso": round(excesso, 2), "pago": round(sum(totais), 2),
        "mediana": round(statistics.median(totais), 2) if totais else None, "teto": t,
        "grupos": {g: round(v, 2) for g, v in grupos.items()},
        "camadas": [[n, round(v, 2)] for n, v in camadas], "hist": hist,
        "ir": round(ir, 2), "previdencia": round(prev, 2), "ir_salario": round(ir_salario, 2),
        "macros": {f"{g}|{m}": round(v, 2) for (g, m), v in macros.most_common(40)},
    }


def orgaos() -> list[dict]:
    lista = json.loads(_get(f"{API}/orgaos"))
    saida = []
    for o in lista:
        tipo = TIPOS.get((o.get("entidade"), o.get("jurisdicao")))
        if tipo and o["id_orgao"] not in FORA_DA_CONTA:
            saida.append({"id": o["id_orgao"], "nome": o["nome"], "tipo": tipo, "uf": o.get("uf")})
    return saida


def meses_a_buscar(hoje: date) -> list[tuple[int, int]]:
    meses, (a, m) = [], INICIO
    while (a, m) <= (hoje.year, hoje.month):
        meses.append((a, m))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return meses


def atualizar_orgao(o: dict, meses: list[tuple[int, int]]) -> tuple[str, int, int | str]:
    """Baixa os meses que faltam no cache. Devolve (órgão, meses no cache, meses baixados agora ou o erro)."""
    try:
        return _atualizar(o, meses)
    except Exception as erro:  # noqa: BLE001 — um órgão que falha não para os outros; fica o que já está no cache
        return o["id"], len(list((PASTA / o["id"]).glob("*.json.gz"))), f"erro: {erro}"


def _atualizar(o: dict, meses: list[tuple[int, int]]) -> tuple[str, int, int]:
    pasta = PASTA / o["id"]
    pasta.mkdir(parents=True, exist_ok=True)
    falta = [(a, m) for a, m in meses if not (pasta / f"{a}-{m:02d}.json.gz").exists()]
    novos = 0
    for ano in sorted({a for a, _ in falta}):
        try:
            lista = json.loads(_get(f"{API}/dados/{o['id']}/{ano}"))
        except urllib.error.HTTPError as erro:
            if erro.code in (400, 404):
                continue
            raise
        for d in lista or []:
            mes = int(d.get("mes") or 0)
            url = (d.get("pacote_de_dados") or {}).get("url")
            if (ano, mes) not in falta or not url:
                continue
            soma = somar_pacote(_get(url), teto(ano, mes), parcela_ir(ano, mes))
            soma["inconsistente"] = bool(d.get("inconsistente"))
            arq = pasta / f"{ano}-{mes:02d}.json.gz"
            tmp = arq.with_name(arq.name + ".tmp")
            tmp.write_bytes(gzip.compress(json.dumps(soma, separators=(",", ":")).encode()))
            tmp.replace(arq)
            novos += 1
    return o["id"], len(list(pasta.glob("*.json.gz"))), novos


def completo(x: dict) -> bool:
    """Um mês em que o órgão só mandou o subsídio (nada por cima de ninguém) é coleta incompleta, não salário."""
    extra = sum(v for g, v in x["grupos"].items() if g != "subsidio")
    return x["membros"] > 0 and extra > 0.005 * max(x["grupos"]["subsidio"], 1)


def ler_cache(aid: str, tipo: str = "") -> dict[str, dict]:
    meses = {arq.name[:7]: json.loads(gzip.decompress(arq.read_bytes())) for arq in sorted((PASTA / aid).glob("*.json.gz"))}
    incompletos = [m for m, x in meses.items() if not completo(x)]
    if incompletos:
        print(f"  {aid}: meses só com o subsídio, deixados de fora: {', '.join(incompletos)}")
    return {m: x for m, x in meses.items() if m not in incompletos}


def _no_periodo(mes: str, p: dict) -> bool:
    a, m = int(mes[:4]), int(mes[5:7])
    return p["de"] <= (a, m) <= p["ate"]


def resumir(meses: dict[str, dict]) -> dict | None:
    """Um órgão num período: o mês típico (médias) e o total do período."""
    if not meses:
        return None
    ms = list(meses.values())
    n = len(ms)
    membros = sum(x["membros"] for x in ms)
    acima = sum(x["acima"] for x in ms)
    if not membros:
        return None
    # "Um mês típico" é a mediana dos meses: um mês com atrasados pagos a todos não puxa a conta.
    acima_tipico = statistics.median(x["acima"] for x in ms)
    parte_tipica = statistics.median(x["acima"] / x["membros"] for x in ms if x["membros"])
    meses_acima = sum(1 for x in ms if x["acima"] >= MINIMO)
    grupos = {g: round(sum(x["grupos"][g] for x in ms)) for g in GRUPOS}
    limites = [f // DEGRAU for f in FAIXAS]   # degrau do histograma onde cada faixa começa
    faixas = [0.0] * (len(FAIXAS) + 1)
    for x in ms:
        for i, c in enumerate(x["hist"]):
            faixas[sum(1 for lim in limites if i >= lim)] += c / n
    faixas = [round(f) for f in faixas]
    poucos = acima_tipico < MINIMO          # não mostra quantos num mês típico
    nenhum = meses_acima == 0               # nem o valor do período
    return {
        "meses": sorted(meses),
        "membros": round(membros / n),                 # num mês típico
        "acima": None if poucos else round(acima_tipico),   # num mês típico (mediana)
        "parte": None if poucos else round(parte_tipica, 4),
        "meses_acima": meses_acima,                         # meses com pelo menos 5 acima do teto
        "excesso": None if nenhum else round(sum(x["excesso"] for x in ms)),   # soma do período
        "pago": round(sum(x["pago"] for x in ms)),
        "mediana": round(statistics.median([x["mediana"] for x in ms if x["mediana"] is not None])),
        "grupos": grupos,
        "camadas": [[round(statistics.median(x["camadas"][i][0] for x in ms)), round(sum(x["camadas"][i][1] for x in ms))] for i in range(len(GRUPOS))],
        "faixas": None if nenhum else [f if f >= MINIMO else None for f in faixas],
        # Imposto de renda descontado e o que seria descontado se tudo fosse salário, nos meses em que o arquivo
        # traz o desconto do IR (sem ele, null).
        **_imposto(ms),
    }


def _imposto(ms: list[dict]) -> dict:
    com_ir = [x for x in ms if x.get("ir", 0) > 0]
    if len(com_ir) < len(ms) / 2:
        return {"ir": None, "ir_salario": None, "previdencia": None, "meses_ir": len(com_ir)}
    return {"ir": round(sum(x["ir"] for x in com_ir)), "ir_salario": round(sum(x["ir_salario"] for x in com_ir)),
            "previdencia": round(sum(x["previdencia"] for x in com_ir)), "meses_ir": len(com_ir)}


def montar(lista: list[dict]) -> dict:
    caches = {o["id"]: ler_cache(o["id"], o["tipo"]) for o in lista}
    saida_orgaos = {}
    serie: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0.0]))
    macros: Counter = Counter()
    for o in lista:
        meses = caches[o["id"]]
        if not meses:
            continue
        for mes, x in meses.items():
            s = serie[mes][o["tipo"]]
            s[0] += 1
            s[1] += x["membros"]
            s[2] += x["acima"]
            s[3] += x["excesso"]
            for k, v in x["macros"].items():
                macros[k] += v
        periodos = {p["id"]: resumir({m: x for m, x in meses.items() if _no_periodo(m, p)}) for p in PERIODOS}
        saida_orgaos[o["id"]] = {"nome": o["nome"], "tipo": o["tipo"], "uf": o["uf"], "pagador": pagador(o), "periodos": periodos}
    print("  rubricas por família (R$ mi, todos os meses), as maiores:")
    for k, v in macros.most_common(30):
        print(f"    {v / 1e6:9.1f}  {k}")
    ultimo = max(serie) if serie else None
    return {
        "fonte": FONTE, "url": "https://dadosjusbr.org", "gerado": date.today().isoformat(), "ultimo_mes": ultimo,
        "tetos": {f"{a}-{m:02d}": v for (a, m), v in TETOS},
        "periodos": [{"id": p["id"], "rotulo": p["rotulo"], "de": "%d-%02d" % p["de"],
                      "ate": min("%d-%02d" % p["ate"], ultimo or "")} for p in PERIODOS],
        "grupos": [[g, NOMES_GRUPOS[g]] for g in GRUPOS], "faixas": FAIXAS, "tipos": NOMES_TIPOS,
        "orgaos": saida_orgaos,
        "serie": {mes: {t: [n, mem, ac, round(ex)] for t, (n, mem, ac, ex) in sorted(por.items())} for mes, por in sorted(serie.items())},
    }


def gravar(doc: dict) -> None:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    for p in doc["periodos"]:
        rs = [o["periodos"][p["id"]] for o in doc["orgaos"].values() if o["periodos"].get(p["id"])]
        membros = sum(r["membros"] for r in rs)
        acima = sum((r["parte"] or 0) * r["membros"] for r in rs)
        excesso = sum(r["excesso"] or 0 for r in rs)
        print(f"{p['rotulo']}: {len(rs)} órgãos, {membros} membros num mês típico, {acima / max(membros, 1):.0%} acima do teto, "
              f"R$ {excesso / 1e9:.2f} bi acima do teto no período")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")


def main() -> None:
    p = argparse.ArgumentParser(prog="supersalarios", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está em data/raw, sem baixar")
    p.add_argument("--orgaos", help="só estes órgãos, separados por vírgula (para testar)")
    args = p.parse_args()
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    lista = orgaos()
    if args.orgaos:
        lista = [o for o in lista if o["id"] in args.orgaos.split(",")]
    print(f"{len(lista)} órgãos", flush=True)
    if not args.so_cache:
        meses = meses_a_buscar(date.today())
        with ThreadPoolExecutor(max_workers=6) as ex:
            for aid, n, novos in ex.map(lambda o: atualizar_orgao(o, meses), lista):
                print(f"  {aid}: {n} meses no cache ({novos}{'' if isinstance(novos, str) else ' novos'})", flush=True)
    gravar(montar(lista))
