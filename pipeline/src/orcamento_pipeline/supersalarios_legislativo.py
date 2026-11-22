"""Servidores e parlamentares do Legislativo federal (Câmara, Senado e TCU) que recebem acima do teto, por órgão.

    uv run supersalarios-legislativo                 # baixa os meses que faltam (12 por órgão) e monta o arquivo do site
    uv run supersalarios-legislativo --orgao camara  # só este órgão (os outros ficam como estão no cache)
    uv run supersalarios-legislativo --sem-baixar    # só copia pipeline/referencia/supersalarios-legislativo.json

Fontes (levantamento em docs/levantamento-supersalarios.md, "Legislativo federal"):
- Câmara: um CSV por mês nos "relatórios consolidados por ano e mês" da transparência, sem nome e sem CPF (a primeira
  coluna é o cargo seguido de um número), com o grupo funcional e o "Redutor Constitucional" (o corte pelo teto).
- Senado: a API de dados abertos administrativos (adm.senado.gov.br/adm-dadosabertos), a remuneração do mês inteiro
  com a "reversão do teto constitucional". Ela não diz quem é ativo: isso sai das listas de servidores ativos e
  inativos da mesma API, casadas pelo nome só na memória (nenhum nome é guardado).
- TCU: a API que a página consultaremuneracao.apps.tcu.gov.br chama, os servidores ativos e as autoridades ativas
  (ministros, ministros-substitutos e procuradores do MP junto ao TCU), estas no formato do contracheque nacional.

Só quem está na ativa. O teto é o do STF, como no resto da página. Ficam fora o 13º, o terço de férias, o abono de
permanência e as diárias. As famílias de pagamento ("escada"), na ordem: base (salário, vantagens pessoais e função,
menos o corte pelo teto); outros (eventuais, horas extras, substituições, gratificações de acúmulo); atrasados (a folha
complementar ou suplementar do mês); auxílios e indenizações. A conta é por pessoa no mês (as folhas normal e
complementar somadas). O imposto de renda, só de quem passa do teto (todos na faixa de 27,5%).

O cache em data/raw/supersalarios-legislativo/{órgão}/{AAAA-MM}.json.gz guarda só as somas de cada órgão e de cada
grupo (deputados, efetivos, comissionados...) no mês. Saída em site/public/data/indicadores/supersalarios-legislativo.json,
com cópia em pipeline/referencia/.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import shutil
import urllib.error
from collections import defaultdict
from datetime import date

from .cidades import RAIZ
from .supersalarios import _get
from .supersalarios_estados import GRUPOS, MINIMO_MESES, Somador, _num, candidatos, resumir

PASTA = RAIZ / "data" / "raw" / "supersalarios-legislativo"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios-legislativo.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios-legislativo.json"
MESES = 12

ORGAOS = {
    "camara": {"nome": "Câmara dos Deputados", "orcamento": "01000",
               "fonte": "Câmara dos Deputados, remuneração de servidores e parlamentares (relatórios consolidados por mês)",
               "url": "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes"},
    "senado": {"nome": "Senado Federal", "orcamento": "02000",
               "fonte": "Senado Federal, dados abertos administrativos (remuneração de servidores)",
               "url": "https://adm.senado.gov.br/adm-dadosabertos/swagger-ui/index.html"},
    "tcu": {"nome": "Tribunal de Contas da União", "orcamento": "03000",
            "fonte": "Tribunal de Contas da União, consulta de remuneração de autoridades e servidores",
            "url": "https://consultaremuneracao.apps.tcu.gov.br/"},
}
NOMES_GRUPOS = {
    "base": "Salário, vantagens pessoais e função, menos o corte pelo teto",
    "outros": "Eventuais, horas extras, substituições e gratificações de acúmulo",
    "retroativos": "Folha complementar (pagamentos atrasados)",
    "auxilios": "Auxílios e indenizações",
}
MESES_PT = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
            "novembro", "dezembro"]


# ---------------------------------------------------------------------------------------------------- Câmara
CAMARA_BASE = "https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao/relatorios-consolidados-por-ano-e-mes"
# Grupo funcional -> o nome no site; os que não estão aqui (inativos, pensões, aposentadoria parlamentar) ficam fora.
CAMARA_ATIVOS = {
    "Parlamentar": "Deputados", "Quadro Efetivo - RJU": "Servidores efetivos", "Cargo de Natureza Especial": "Cargos de natureza especial",
    "Secretário Parlamentar": "Secretários parlamentares", "Estagiários": "Estagiários",
}


def _camara_links(ano: int, ctx: dict) -> list[str]:
    if ano not in ctx:
        html = _get(f"{CAMARA_BASE}/{ano}").decode("utf-8", errors="replace")
        ctx[ano] = sorted(set(re.findall(rf'href="({re.escape(CAMARA_BASE)}/{ano}/[^"]+)"', html)))
    return ctx[ano]


def _camara_csv(ano: int, mes: int, ctx: dict) -> str | None:
    """Os endereços variam ("outubro-de-2026-csv", "fevereiro-de-2026-1"): tenta os do mês que não terminam em -pdf
    e fica com o que é CSV."""
    nome = MESES_PT[mes - 1]
    for url in _camara_links(ano, ctx):
        fim = url.rsplit("/", 1)[1]
        if not fim.startswith(nome) or str(ano) not in fim or fim.endswith("-pdf"):
            continue
        corpo = _get(url, timeout=300)
        if corpo[:200].lstrip().startswith(b"%PDF") or b";" not in corpo[:400]:
            continue
        return corpo.decode("latin-1")
    return None


def mes_camara(ano: int, mes: int, ctx: dict) -> tuple[Somador, Somador] | None:
    texto = _camara_csv(ano, mes, ctx)
    if not texto:
        return None
    pessoas: dict[str, dict] = {}
    for r in csv.DictReader(io.StringIO(texto), delimiter=";"):
        grupo = CAMARA_ATIVOS.get((r.get("Grupo Funcional") or "").strip())
        if not grupo:
            continue
        chave = (r.get("Cargo Individualizado do Servidor") or "").strip()
        p = pessoas.setdefault(chave, {"grupo": grupo, "base": 0.0, "outros": 0.0, "retroativos": 0.0, "auxilios": 0.0, "ir": 0.0, "prev": 0.0})
        v = lambda k: _num(r.get(k))
        fixa = v("Remuneração Fixa") + v("Vantagens de Natureza Pessoal") + v("Função ou Cargo em Comissão") - abs(v("Redutor Constitucional"))
        eventual = v("Outras Remunerações Eventuais/Provisórias(*)")
        if (r.get("Folha de Pagamento") or "").strip().lower().startswith("complementar"):
            p["retroativos"] += fixa + eventual
        else:
            p["base"] += fixa
            p["outros"] += eventual
        p["auxilios"] += v("Auxílios") + v("Vantagens Indenizatórias")
        p["ir"] += abs(v("Imposto de Renda"))
        p["prev"] += abs(v("Constribuição Previdenciária") or v("Contribuição Previdenciária"))
    return _somar("camara", ano, mes, pessoas)


# ---------------------------------------------------------------------------------------------------- Senado
SENADO_API = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/servidores"
SENADO_VINCULOS = {"PARLAMENTAR": "Senadores", "EFETIVO": "Servidores efetivos", "COMISSIONADO": "Comissionados", "REQUISITADO": "Requisitados"}


def _senado_listas(ctx: dict) -> tuple[dict[str, str], set[str]]:
    """Nome -> grupo dos ativos, e os nomes dos inativos. Só na memória: nenhum nome sai daqui."""
    if "ativos" not in ctx:
        ativos = json.loads(_get(f"{SENADO_API}/servidores/ativos", timeout=300))
        inativos = json.loads(_get(f"{SENADO_API}/servidores/inativos", timeout=300))
        ctx["ativos"] = {a["nome"]: SENADO_VINCULOS.get(a.get("vinculo") or "", "Outros") for a in ativos if isinstance(a.get("nome"), str)}
        ctx["inativos"] = {a["nome"] for a in inativos if isinstance(a.get("nome"), str)} - set(ctx["ativos"])
    return ctx["ativos"], ctx["inativos"]


def mes_senado(ano: int, mes: int, ctx: dict) -> tuple[Somador, Somador] | None:
    try:
        linhas = json.loads(_get(f"{SENADO_API}/remuneracoes/{ano}/{mes}", timeout=300))
    except urllib.error.HTTPError as erro:
        if erro.code in (400, 404):
            return None
        raise
    if not linhas:
        return None
    ativos, inativos = _senado_listas(ctx)
    pessoas: dict = {}
    for r in linhas:
        nome = r.get("nome")
        if nome in inativos:
            continue   # aposentado (a lista é a de hoje: quem se aposentou depois do mês conta como ativo)
        p = pessoas.setdefault(r.get("sequencial"), {"grupo": ativos.get(nome, "Outros"), "base": 0.0, "outros": 0.0,
                                                     "retroativos": 0.0, "auxilios": 0.0, "ir": 0.0, "prev": 0.0})
        v = lambda k: _num(r.get(k))
        # A reversão é negativa quando corta; positiva, quando devolve um corte anterior.
        fixa = v("remuneracao_basica") + v("vantagens_pessoais") + v("funcao_comissionada") + v("reversao_teto_constitucional")
        eventual = v("horas_extras") + v("outras_eventuais")
        if (r.get("tipo_folha") or "").strip().lower().startswith("suplementar"):
            p["retroativos"] += fixa + eventual
        else:
            p["base"] += fixa
            p["outros"] += eventual
        p["auxilios"] += v("auxilios") + v("vantagens_indenizatorias")
        p["ir"] += abs(v("imposto_renda"))
        p["prev"] += abs(v("previdencia"))
    return _somar("senado", ano, mes, pessoas)


# ---------------------------------------------------------------------------------------------------- TCU
TCU_API = "https://consultaremuneracao.apps.tcu.gov.br/api/publico/remuneracoes"
# Contracheque das autoridades: o que fica fora (13º, férias, abono de permanência) e o que é a base.
TCU_FORA = {"TRU-1006", "TRU-1007", "TRU-1011", "TRU-1012", "TRU-1014", "TRU-1018", "TRU-1019"}
TCU_BASE = {"TRU-1001", "TRU-1002", "TRU-1003", "TRU-1004", "TRU-1016", "TRU-1017"}


def _tcu(ano: int, mes: int, escopo: str) -> list[dict]:
    try:
        return json.loads(_get(f"{TCU_API}?mes={mes}&ano={ano}&escopo={escopo}", timeout=300)) or []
    except urllib.error.HTTPError as erro:
        if erro.code in (400, 404):
            return []
        raise


def mes_tcu(ano: int, mes: int, ctx: dict) -> tuple[Somador, Somador] | None:
    servidores = _tcu(ano, mes, "SERVIDOR_ATIVO")
    if not servidores:
        return None
    pessoas: dict = {}

    def plano(r: dict, grupo: str) -> dict:
        """O formato dos servidores (e o das autoridades até jul/2026): um campo por parcela."""
        v = lambda k: float(r.get(k) or 0)
        return {
            "grupo": grupo,
            # O sinal do abate-teto muda de um grupo para outro: vale o valor absoluto.
            "base": v("valorRemuneracaoBasica") + v("valorVantagNaturezaPessoal") + v("valorFuncaoCargoComissao") - abs(v("valorAbateTeto")),
            "outros": v("valorOutrasRemunTemporarias") + v("valorFeriasIndenizadas") + v("valorLicencaPremioIndeniz"),
            "retroativos": 0.0,
            "auxilios": v("valorAuxAlimentacao") + v("valorBeneficioPreEscola") + v("valorAjudaCusto") + v("valorOutrosAuxilios")
                        + v("valorRessarcAssistSaude") + v("valorOutrasIndenizacoes"),
            "ir": abs(v("valorImpostoDeRenda")), "prev": abs(v("valorContribuicaoPrevidenciaria")),
        }

    for r in servidores:
        pessoas[("s", (r.get("id") or {}).get("codPessoa") or len(pessoas))] = plano(r, "Servidores")
    for r in _tcu(ano, mes, "AUTORIDADE_ATIVA"):
        if not r.get("contracheque"):
            # Até jul/2026, as autoridades vinham num formato próprio, um campo por parcela (subsídio, GAJU, PVTAC...).
            v = lambda k: float(r.get(k) or 0)
            pessoas[("a", (r.get("id") or {}).get("codPessoa") or len(pessoas))] = {
                "grupo": "Ministros e procuradores",
                "base": v("valorSubsidio") + v("valorATS") + v("valorPVTAC") - abs(v("valorAbateTeto")),
                "outros": v("valorGaju") + v("valorGecjao") + v("valorRepresentaoPresidencia") + v("valorSubstituicaoAutoridade")
                          + v("valorFeriasIndenizadas") + v("valorLicencaPremioIndeniz"),
                "retroativos": 0.0,
                "auxilios": v("valorAuxAlimentacao") + v("valorBeneficioPreEscola") + v("valorAjudaCusto") + v("valorOutrosAuxilios")
                            + v("valorRessarcAssistSaude") + v("valorOutrasIndenizacoes"),
                "ir": abs(v("valorImpostoDeRenda")), "prev": abs(v("valorContribuicaoPrevidenciaria")),
            }
            continue
        p = {"grupo": "Ministros e procuradores", "base": 0.0, "outros": 0.0, "retroativos": 0.0, "auxilios": 0.0, "ir": 0.0, "prev": 0.0}
        for secao in (r.get("contracheque") or {}).get("secoes") or []:
            for item in secao.get("itens") or []:
                cod, valor = item.get("codigo"), float(item.get("valor") or 0)
                if not valor:
                    continue
                if secao.get("id") == "REMUNERATORIA":
                    if cod in TCU_BASE:
                        p["base"] += valor
                    elif cod not in TCU_FORA:
                        p["outros"] += valor
                elif secao.get("id") == "DESCONTO":
                    desc = (item.get("descricao") or "").lower()
                    if "abate teto" in desc:
                        p["base"] -= abs(valor)
                    elif "imposto de renda" in desc and "13" not in desc:
                        p["ir"] += abs(valor)
                    elif "previdenci" in desc and "13" not in desc:
                        p["prev"] += abs(valor)
                elif secao.get("id") == "INDENIZATORIA":
                    # Como no formato antigo: o acúmulo de jurisdição vai com os eventuais; a parcela por tempo de
                    # carreira, com as vantagens pessoais.
                    desc = (item.get("descricao") or "").lower()
                    if "cumulativ" in desc or "jurisdi" in desc:
                        p["outros"] += valor
                    elif "tempo" in desc or "antiguidade" in desc:
                        p["base"] += valor
                    else:
                        p["auxilios"] += valor
                elif secao.get("id") == "RETROATIVO":
                    p["retroativos"] += valor
                elif secao.get("id") in ("COMPENSATORIA", "TRANSITORIA"):
                    p["outros"] += valor
        pessoas[("a", r.get("codPessoa") or len(pessoas))] = p
    return _somar("tcu", ano, mes, pessoas)


# ---------------------------------------------------------------------------------------------------- comum
def _somar(orgao: str, ano: int, mes: int, pessoas: dict) -> tuple[Somador, Somador]:
    """Uma soma para o órgão inteiro e outra por grupo (deputados, efetivos...). Nada por pessoa sai daqui."""
    tudo, por_grupo = Somador(ano, mes), Somador(ano, mes)
    nome = ORGAOS[orgao]["nome"]
    for chave, p in pessoas.items():
        partes = {k: p[k] for k in ("base", "outros", "retroativos", "auxilios", "ir", "prev")}
        tudo.add(chave, orgao, nome, **partes)
        por_grupo.add(chave, p["grupo"], p["grupo"], **partes)
    return tudo, por_grupo


LEITORES = {"camara": mes_camara, "senado": mes_senado, "tcu": mes_tcu}


def carregar(orgao: str, so_cache: bool) -> dict[str, dict]:
    pasta = PASTA / orgao
    pasta.mkdir(parents=True, exist_ok=True)
    meses: dict[str, dict] = {}
    lista = candidatos(date.today())
    for a, m in lista:
        arq = pasta / f"{a}-{m:02d}.json.gz"
        if arq.exists():
            meses[f"{a}-{m:02d}"] = json.loads(gzip.decompress(arq.read_bytes()))
    if so_cache:
        return dict(sorted(meses.items())[-MESES:])
    ctx: dict = {}
    for a, m in lista:
        chave = f"{a}-{m:02d}"
        if len(meses) >= MESES and chave < min(meses):
            break
        if chave in meses:
            continue
        r = LEITORES[orgao](a, m, ctx)
        if r is None or (x := r[0].resultado()) is None:
            print(f"  {orgao} {chave}: nada a somar (ainda não publicado)", flush=True)
            continue
        doc = {"orgao": x["orgaos"][orgao], "teto": x["teto"], "grupos": (r[1].resultado() or {}).get("orgaos", {})}
        (pasta / f"{chave}.json.gz").write_bytes(gzip.compress(json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()))
        print(f"  {orgao} {chave}: {doc['orgao']['vinculos']} na ativa, {doc['orgao']['acima']} acima do teto", flush=True)
        meses[chave] = doc
    return dict(sorted(meses.items())[-MESES:])


def montar(orgao: str, meses: dict[str, dict]) -> dict:
    ordem = sorted(meses)
    nomes = sorted({g for m in ordem for g in meses[m]["grupos"]})
    grupos = {g: r for g in nomes if (r := resumir([meses[m]["grupos"][g] for m in ordem if g in meses[m]["grupos"]]))}
    return {**ORGAOS[orgao], "de": ordem[0], "ate": ordem[-1], "meses": len(ordem),
            "resumo": resumir([meses[m]["orgao"] for m in ordem]),
            "serie": {m: [meses[m]["orgao"]["vinculos"], meses[m]["orgao"]["acima"], round(meses[m]["orgao"]["excesso"])] for m in ordem},
            # A escada do último mês: a mediana dos 12 esconde uma mudança recente (na Câmara e no Senado, a partir de
            # jul-ago/2026, centenas passam do teto só com o salário, mesmo depois do corte).
            "ultimo_mes": {"mes": ordem[-1], "camadas": [[n, round(x)] for n, x in meses[ordem[-1]]["orgao"]["camadas"]]},
            "grupos_funcionais": dict(sorted(grupos.items(), key=lambda i: -(i[1]["excesso"] or 0)))}


def main() -> None:
    global MESES
    p = argparse.ArgumentParser(prog="supersalarios-legislativo", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está em data/raw, sem baixar")
    p.add_argument("--orgao", help="só estes órgãos (camara, senado, tcu), separados por vírgula")
    p.add_argument("--meses", type=int, default=MESES, help=f"quantos meses guardar por órgão (padrão {MESES})")
    args = p.parse_args()
    MESES = args.meses
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    pedidos = set(args.orgao.lower().split(",")) if args.orgao else set(ORGAOS)
    saida: dict = {}
    for orgao in ORGAOS:
        try:
            meses = carregar(orgao, args.so_cache or orgao not in pedidos)
        except Exception as erro:  # noqa: BLE001 — um órgão que falha não derruba os outros
            print(f"  {orgao}: falhou ({erro}); fica o que há no cache", flush=True)
            meses = carregar(orgao, True)
        if len(meses) >= MINIMO_MESES:
            saida[orgao] = montar(orgao, meses)
        elif meses:
            print(f"  {orgao}: só {len(meses)} meses no cache; fica fora até completar {MINIMO_MESES}", flush=True)
    doc = {"gerado": date.today().isoformat(), "grupos": GRUPOS, "nomes_grupos": NOMES_GRUPOS, "orgaos": saida}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    for orgao, o in saida.items():
        r = o["resumo"]
        print(f"{orgao} {o['de']} a {o['ate']} ({o['meses']} meses): {r['vinculos']} na ativa num mês típico, {r['acima'] or 0} acima do teto, "
              f"R$ {(r['excesso'] or 0) / 1e6:.1f} mi acima do teto")
        for g, x in list(o["grupos_funcionais"].items())[:6]:
            print(f"    {g[:30]:30s} {x['acima'] or 0:5d} de {x['vinculos']:6d}  R$ {(x['excesso'] or 0) / 1e6:6.1f} mi")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
