"""Servidores do Executivo estadual que recebem acima do teto, somados por órgão. Por enquanto, o Paraná.

    uv run supersalarios-estados               # baixa os meses que faltam (12) e monta o arquivo do site
    uv run supersalarios-estados --sem-baixar  # só copia pipeline/referencia/supersalarios-estados.json

Paraná: o mesmo Portal da Transparência que `estado_pr.py` usa. REMUNERACAO-AAAA-MM.zip traz, para cada vínculo
no mês, o vencimento, a gratificação, os retroativos, "outros", o auxílio-transporte e alimentação, o 13º e as
férias (juntos), o imposto de renda, a previdência e o redutor (o corte pelo teto). REMUNERACAO_RH.zip diz o órgão
e a situação de cada vínculo: aposentados e pensionistas ficam de fora. Os arquivos trazem o nome do servidor;
aqui só se leem o código do vínculo, o órgão e os valores, e os zips são apagados depois de somados. O cache em
data/raw/supersalarios-estados/pr/{AAAA-MM}.json.gz guarda só as somas de cada órgão no mês.

A conta é por vínculo, não por pessoa (quem tem dois cargos conta duas vezes), e usa o teto nacional, o do STF:
no Executivo estadual o limite é o salário do governador, mais baixo; aqui se mostra quem passa do maior limite
possível. Ficam de fora o TJ, o MP e a Assembleia, que aparecem no arquivo só em parte (os juízes e promotores
estão no comando `supersalarios`, pelo DadosJusBr). O Tribunal de Contas também aparece, mas só com aposentados e
pensionistas, pagos pela previdência do estado: sai com eles.

Camadas da "escada": vencimento e gratificação, menos o redutor; + "outros"; + retroativos; + auxílios. Fora o
13º e as férias. E, como no Judiciário, o imposto de renda descontado e o que seria descontado se tudo fosse
salário, mas só dos vínculos acima do teto (todos na faixa de 27,5%; abaixo dela, a conta não vale).

Saída em site/public/data/indicadores/supersalarios-estados.json, com cópia em pipeline/referencia/.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import statistics
from collections import defaultdict
from datetime import date

from . import estado_pr as pr
from .cidades import RAIZ
from .supersalarios import ALIQUOTA_IR, DEGRAU, DEGRAUS, FAIXAS, MINIMO, parcela_ir, teto

PASTA = RAIZ / "data" / "raw" / "supersalarios-estados"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios-estados.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios-estados.json"
MESES = 12
GRUPOS = ["base", "outros", "retroativos", "auxilios"]
NOMES_GRUPOS = {
    "base": "Vencimento e gratificação, menos o corte pelo teto",
    "outros": "\"Outros\" (o arquivo não detalha)",
    "retroativos": "Pagamentos atrasados",
    "auxilios": "Auxílio-transporte e alimentação",
}
FORA_PR = {"TJ", "MP", "AL"}   # no arquivo só em parte


def _num(s: str | None) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return 0.0


def somar_mes_pr(ano: int, mes: int, vinculos: dict) -> dict | None:
    arq = pr.PASTA_BRUTO / "tmp" / f"REMUNERACAO-{ano}-{mes:02d}.zip"
    try:
        if not pr._baixar(pr.URL_MES.format(ano=ano, mes=mes), arq):
            return None
        por_vinculo: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        orgao_de: dict[str, tuple[str, str]] = {}
        for r in pr._linhas(arq):
            cod = r["cod_vinculo"]
            sigla, inst, _lot, _mun, situacao = vinculos.get(cod, (r["sigla_orgao"], "", "", "", ""))
            if situacao in pr.INATIVOS or r["sigla_orgao"] == pr.PREVIDENCIA:
                continue
            s = r["sigla_orgao"] or sigla
            if s in FORA_PR:
                continue
            orgao_de[cod] = (s, inst or s)
            v = por_vinculo[cod]
            v["base"] += _num(r["vencimento"]) + _num(r["gratificacao"]) - abs(_num(r["redutor"]))
            v["outros"] += _num(r["outros"])
            v["retroativos"] += _num(r["retroativos"])
            v["auxilios"] += _num(r["aux_transp_alim"])
            v["ir"] += abs(_num(r["ir"]))
            v["prev"] += abs(_num(r["previdencia"]))
        t, parcela = teto(ano, mes), parcela_ir(ano, mes)
        por: dict[str, dict] = {}
        for cod, v in por_vinculo.items():
            total = sum(v[g] for g in GRUPOS)
            if total <= 0 or v["base"] <= 0:
                continue
            sigla, nome = orgao_de[cod]
            o = por.setdefault(sigla, {"nome": nome, "vinculos": 0, "acima": 0, "excesso": 0.0, "totais": [],
                                       "grupos": {g: 0.0 for g in GRUPOS}, "camadas": [[0, 0.0] for _ in GRUPOS],
                                       "hist": [0] * (DEGRAUS + 1), "ir": 0.0, "previdencia": 0.0, "ir_salario": 0.0})
            o["vinculos"] += 1
            o["totais"].append(total)
            if total > t:
                # O imposto só para quem passa do teto: todos estão na faixa de 27,5%, e a conta "se fosse salário" vale.
                # Para a maioria dos servidores, abaixo dela, a alíquota de cima inflaria o imposto que "falta".
                o["ir"] += v["ir"]
                o["previdencia"] += v["prev"]
                o["ir_salario"] += max(0.0, ALIQUOTA_IR * (total - v["prev"]) - parcela)
            soma = 0.0
            for k, g in enumerate(GRUPOS):
                soma += v[g]
                o["grupos"][g] += v[g]
                if soma > t:
                    o["camadas"][k][0] += 1
                    o["camadas"][k][1] += soma - t
            if total > t:
                o["acima"] += 1
                o["excesso"] += total - t
                o["hist"][min(DEGRAUS, int((total - t - 0.005) // DEGRAU))] += 1
        for o in por.values():
            totais = o.pop("totais")
            o["mediana"] = round(statistics.median(totais), 2)
            o["pago"] = round(sum(totais), 2)
            for k in ("excesso", "ir", "previdencia", "ir_salario"):
                o[k] = round(o[k], 2)
            o["grupos"] = {g: round(x, 2) for g, x in o["grupos"].items()}
            o["camadas"] = [[n, round(x, 2)] for n, x in o["camadas"]]
        if not por:
            return None   # o arquivo do mês corrente sai antes, vazio
        return {"teto": t, "orgaos": por}
    finally:
        arq.unlink(missing_ok=True)


def resumir(xs: list[dict]) -> dict | None:
    if not xs:
        return None
    n = len(xs)
    acima_tipico = statistics.median(x["acima"] for x in xs)
    meses_acima = sum(1 for x in xs if x["acima"] >= MINIMO)
    poucos, nenhum = acima_tipico < MINIMO, meses_acima == 0
    limites = [f // DEGRAU for f in FAIXAS]
    faixas = [0.0] * (len(FAIXAS) + 1)
    for x in xs:
        for i, c in enumerate(x["hist"]):
            faixas[sum(1 for lim in limites if i >= lim)] += c / n
    return {
        "nome": xs[-1]["nome"], "meses": n,
        "vinculos": round(statistics.median(x["vinculos"] for x in xs)),
        "acima": None if poucos else round(acima_tipico),
        "parte": None if poucos else round(statistics.median(x["acima"] / x["vinculos"] for x in xs), 4),
        "meses_acima": meses_acima,
        "excesso": None if nenhum else round(sum(x["excesso"] for x in xs)),
        "pago": round(sum(x["pago"] for x in xs)),
        "mediana": round(statistics.median(x["mediana"] for x in xs)),
        "grupos": {g: round(sum(x["grupos"][g] for x in xs)) for g in GRUPOS},
        "camadas": [[round(statistics.median(x["camadas"][k][0] for x in xs)), round(sum(x["camadas"][k][1] for x in xs))] for k in range(len(GRUPOS))],
        "faixas": None if nenhum else [round(f) if f >= MINIMO else None for f in faixas],
        "ir": round(sum(x["ir"] for x in xs)), "ir_salario": round(sum(x["ir_salario"] for x in xs)),
        "previdencia": round(sum(x["previdencia"] for x in xs)),
    }


def montar_uf(meses: dict[str, dict]) -> dict:
    ordem = sorted(meses)
    siglas = sorted({s for m in ordem for s in meses[m]["orgaos"]})
    orgaos = {s: r for s in siglas if (r := resumir([meses[m]["orgaos"][s] for m in ordem if s in meses[m]["orgaos"]]))}
    total = {}
    for m in ordem:
        os_ = meses[m]["orgaos"].values()
        total[m] = [sum(o["vinculos"] for o in os_), sum(o["acima"] for o in os_), round(sum(o["excesso"] for o in os_))]
    return {"de": ordem[0], "ate": ordem[-1], "meses": len(ordem), "orgaos": orgaos, "serie": total}


def carregar_pr(so_cache: bool) -> dict[str, dict]:
    pasta = PASTA / "pr"
    pasta.mkdir(parents=True, exist_ok=True)
    meses: dict[str, dict] = {}
    vinculos = None
    a, m = date.today().year, date.today().month
    for _ in range(MESES + 4):
        if len(meses) == MESES:
            break
        chave = f"{a}-{m:02d}"
        cache = pasta / f"{chave}.json.gz"
        if cache.exists():
            meses[chave] = json.loads(gzip.decompress(cache.read_bytes()))
        elif not so_cache:
            if vinculos is None:
                vinculos = pr.ler_vinculos()
                print(f"  PR: {len(vinculos)} vínculos no cadastro", flush=True)
            x = somar_mes_pr(a, m, vinculos)
            if x is None:
                print(f"  PR {chave}: ainda não publicado", flush=True)
            else:
                cache.write_bytes(gzip.compress(json.dumps(x, ensure_ascii=False, separators=(",", ":")).encode()))
                os_ = x["orgaos"].values()
                print(f"  PR {chave}: {sum(o['vinculos'] for o in os_)} vínculos, {sum(o['acima'] for o in os_)} acima do teto", flush=True)
                meses[chave] = x
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
    return meses


def main() -> None:
    p = argparse.ArgumentParser(prog="supersalarios-estados", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está em data/raw, sem baixar")
    args = p.parse_args()
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    meses = carregar_pr(args.so_cache)
    if not meses:
        raise SystemExit("PR: nenhum mês")
    doc = {
        "gerado": date.today().isoformat(), "grupos": [[g, NOMES_GRUPOS[g]] for g in GRUPOS], "faixas": FAIXAS,
        "estados": {"PR": {"fonte": "Portal da Transparência do Paraná (remuneração dos servidores)",
                           "url": "https://www.transparencia.pr.gov.br/pte/assunto/8/129", **montar_uf(meses)}},
    }
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    e = doc["estados"]["PR"]
    os_ = e["orgaos"].values()
    print(f"PR {e['de']} a {e['ate']}: {sum(o['vinculos'] for o in os_)} vínculos num mês típico, "
          f"{sum(o['acima'] or 0 for o in os_)} acima do teto, R$ {sum(o['excesso'] or 0 for o in os_) / 1e6:.1f} mi acima do teto")
    for s, o in sorted(e["orgaos"].items(), key=lambda i: -(i[1]["excesso"] or 0))[:10]:
        print(f"    {s:10s} {o['nome'][:45]:45s} {o['acima'] or 0:5d} de {o['vinculos']:6d}  R$ {(o['excesso'] or 0) / 1e6:6.1f} mi")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")
