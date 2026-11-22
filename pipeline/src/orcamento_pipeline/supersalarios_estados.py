"""Servidores do Executivo estadual que recebem acima do teto, somados por órgão.

    uv run supersalarios-estados                # baixa os meses que faltam (12 por estado) e monta o arquivo do site
    uv run supersalarios-estados --uf ES,PE     # só estes estados (os outros ficam como estão no cache)
    uv run supersalarios-estados --sem-baixar   # só copia pipeline/referencia/supersalarios-estados.json

Estados e fontes (levantamento em docs/levantamento-supersalarios.md, "A folha do Executivo nos 27 estados"):
- PR: Portal da Transparência do PR, o mesmo arquivo de `estado_pr.py` (zip mensal + cadastro dos vínculos).
- ES: dados.es.gov.br (CKAN), um CSV por mês com uma linha por rubrica (vantagem ou desconto) de cada vínculo.
- PE: dados.pe.gov.br (CKAN), um CSV por mês só com os ativos.
- PB: api.dados.pb.gov.br, API pública paginada (1.000 linhas por página).
- RN: api.remuneracao.rn.gov.br, a API que a página remuneracao.rn.gov.br chama: a lista dos órgãos do mês e um CSV
  por órgão (o id do órgão muda a cada mês).
- GO: dadosabertos.go.gov.br (CKAN), um CSV por mês.
- DF: transparencia.df.gov.br, um zip por ano com a folha de cada mês e o detalhamento por rubrica.
Os arquivos trazem o nome do servidor (e, em alguns, o CPF mascarado); aqui só se leem órgão e valores, linha a
linha, e os arquivos são apagados depois de somados. O cache em data/raw/supersalarios-estados/{uf}/{AAAA-MM}.json.gz
guarda só as somas de cada órgão no mês.

A conta é por vínculo, não por pessoa (quem tem dois cargos conta duas vezes), só com quem está na ativa, e usa o
teto nacional, o do STF: no Executivo estadual o limite é o salário do governador, mais baixo; aqui se mostra quem
passa do maior limite possível. Ficam fora o 13º e as férias.

As famílias de pagamento ("escada"), na ordem: base (o salário, menos o corte pelo teto); outros; atrasados; auxílios.
O que cada uma reúne depende do que o arquivo de cada estado separa (NOMES_UF); quando o arquivo não separa, a
família fica vazia. Como no Judiciário, o imposto de renda descontado e o que seria descontado se tudo fosse salário,
só dos vínculos acima do teto (todos na faixa de 27,5%); GO não publica o imposto e fica sem essa conta.

Saída em site/public/data/indicadores/supersalarios-estados.json, com cópia em pipeline/referencia/.
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
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import estado_pr as pr
from .cidades import RAIZ
from .supersalarios import ALIQUOTA_IR, DEGRAU, DEGRAUS, FAIXAS, MINIMO, _get, parcela_ir, teto

PASTA = RAIZ / "data" / "raw" / "supersalarios-estados"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios-estados.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios-estados.json"
MESES = 12
MINIMO_MESES = 6   # um estado com menos meses que isso (carga pela metade) não entra no site
GRUPOS = ["base", "outros", "retroativos", "auxilios"]
ESTADOS = ["PR", "ES", "PE", "PB", "RN", "GO", "DF"]

FONTES = {
    "PR": ("Portal da Transparência do Paraná (remuneração dos servidores)", "https://www.transparencia.pr.gov.br/pte/assunto/8/129"),
    "ES": ("Portal de Dados Abertos do Espírito Santo (remunerações do pessoal)", "https://dados.es.gov.br/dataset/portal-da-transparencia-pessoal"),
    "PE": ("Portal de Dados Abertos de Pernambuco (remuneração de servidores)", "https://dados.pe.gov.br/dataset/remuneracao-de-servidores"),
    "PB": ("API de Dados Abertos da Paraíba (remuneração dos servidores)", "https://api.dados.pb.gov.br/swagger/"),
    "RN": ("Portal da Remuneração do Rio Grande do Norte", "https://remuneracao.rn.gov.br/"),
    "GO": ("Portal de Dados Abertos de Goiás (folha de pagamento)", "https://dadosabertos.go.gov.br/dataset/folha-de-pagamento"),
    "DF": ("Portal da Transparência do Distrito Federal (remuneração dos servidores)", "https://www.transparencia.df.gov.br/"),
}
# O que cada família reúne em cada estado (o site usa estes nomes). Família ausente: o arquivo não separa.
NOMES_UF = {
    "PR": {"base": "Vencimento e gratificação, menos o corte pelo teto", "outros": "\"Outros\" (o arquivo não detalha)",
           "retroativos": "Pagamentos atrasados", "auxilios": "Auxílio-transporte e alimentação"},
    "ES": {"base": "Subsídio, vencimento e gratificações, menos o abate-teto", "outros": "Escalas extras, substituições e outras parcelas variáveis",
           "retroativos": "Pagamentos de meses anteriores", "auxilios": "Auxílios e indenizações"},
    "PE": {"base": "Remuneração do cargo e da função, menos o desconto do excedente ao teto",
           "outros": "Outras vantagens (inclui indenizações; o arquivo não separa)"},
    "PB": {"base": "Vantagens fixas, menos o redutor", "outros": "Vantagens variáveis (o arquivo não separa o 13º e as férias)"},
    "RN": {"base": "Remuneração do mês, menos o redutor do art. 37", "outros": "Outras remunerações (o arquivo não detalha)"},
    "GO": {"base": "Proventos do mês, sem 13º e férias (o arquivo não separa as partes)"},
    "DF": {"base": "Remuneração básica e função, menos o teto redutor",
           "outros": "Verbas eventuais, hora extra, licença-prêmio e outros recebimentos (como honorários)",
           "retroativos": "Verbas judiciais", "auxilios": "Benefícios (auxílios)"},
}
NOMES_LEGIVEIS = {"PR": "Paraná", "ES": "Espírito Santo", "PE": "Pernambuco", "PB": "Paraíba", "RN": "Rio Grande do Norte",
                  "GO": "Goiás", "DF": "Distrito Federal"}
FORA_PR = {"TJ", "MP", "AL"}   # no arquivo do PR só em parte
# Empresas estatais: o teto só vale para a que recebe dinheiro do Tesouro para pagar pessoal (Constituição, art. 37,
# § 9º), e os arquivos não dizem quais recebem. Ficam fora da conta, para não chamar de "acima do teto" quem pode não
# estar sujeito a ele.
ESTATAL = re.compile(r"\bCOMPANHIA\b|\bCIA\b|\bS\.?\s?/?A\b|\bBANCO\b|\bEMPRESA\b|\bCAESB\b|\bCAGEPA\b|\bCELEPAR\b|"
                     r"\bCOHAPAR\b|\bAPPA\b|PORTOS DE PARANAGU|\bTERRACAP\b|\bBRB\b|\bCOMPESA\b|\bCAERN\b|\bCESAN\b|"
                     r"\bSANEAGO\b|\bCELG\b|\bDATANORTE\b|\bPOTIGAS\b|\bCEASA\b|\bLOTEPAR\b|\bTECPAR\b|\bINVEST\b", re.I)
INATIVOS = re.compile(r"aposent|pension|inativ|reform|reserva|benefici|instituidor", re.I)


def _num(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return 0.0


class Somador:
    """Soma os vínculos de um mês por órgão. Nada por pessoa sai daqui: só as somas de cada órgão."""

    def __init__(self, ano: int, mes: int, com_ir: bool = True) -> None:
        self.t, self.parcela, self.com_ir = teto(ano, mes), parcela_ir(ano, mes), com_ir
        self.v: dict = {}

    def add(self, chave, sigla: str, nome: str, base: float = 0.0, outros: float = 0.0, retroativos: float = 0.0,
            auxilios: float = 0.0, ir: float = 0.0, prev: float = 0.0) -> None:
        x = self.v.get(chave)
        if x is None:
            x = self.v[chave] = [sigla, nome, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        x[2] += base; x[3] += outros; x[4] += retroativos; x[5] += auxilios; x[6] += ir; x[7] += prev

    def resultado(self) -> dict | None:
        t, por = self.t, {}
        for sigla, nome, base, outros, retro, aux, ir, prev in self.v.values():
            partes = {"base": base, "outros": outros, "retroativos": retro, "auxilios": aux}
            total = base + outros + retro + aux
            if total <= 0 or base <= 0:
                continue
            o = por.setdefault(sigla, {"nome": nome, "vinculos": 0, "acima": 0, "excesso": 0.0, "totais": [],
                                       "grupos": {g: 0.0 for g in GRUPOS}, "camadas": [[0, 0.0] for _ in GRUPOS],
                                       "hist": [0] * (DEGRAUS + 1), "ir": 0.0, "previdencia": 0.0, "ir_salario": 0.0})
            o["vinculos"] += 1
            o["totais"].append(total)
            if total > t and self.com_ir:
                # O imposto só para quem passa do teto: todos estão na faixa de 27,5%, e a conta "se fosse salário" vale.
                o["ir"] += ir
                o["previdencia"] += prev
                o["ir_salario"] += max(0.0, ALIQUOTA_IR * (total - prev) - self.parcela)
            soma = 0.0
            for k, g in enumerate(GRUPOS):
                soma += partes[g]
                o["grupos"][g] += partes[g]
                if soma > t:
                    o["camadas"][k][0] += 1
                    o["camadas"][k][1] += soma - t
            if total > t:
                o["acima"] += 1
                o["excesso"] += total - t
                o["hist"][min(DEGRAUS, int((total - t - 0.005) // DEGRAU))] += 1
        if not por:
            return None   # o arquivo do mês corrente às vezes sai antes, vazio
        for o in por.values():
            totais = o.pop("totais")
            o["mediana"] = round(statistics.median(totais), 2)
            o["pago"] = round(sum(totais), 2)
            for k in ("excesso", "ir", "previdencia", "ir_salario"):
                o[k] = round(o[k], 2)
            o["grupos"] = {g: round(x, 2) for g, x in o["grupos"].items()}
            o["camadas"] = [[n, round(x, 2)] for n, x in o["camadas"]]
        return {"teto": t, "orgaos": por}


def _baixar(url: str, destino: Path, timeout: int = 900) -> bool:
    """Grava a URL em `destino`; False se não existe (403/404)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        destino.write_bytes(_get(url, timeout=timeout))
        return True
    except urllib.error.HTTPError as erro:
        if erro.code in (403, 404):
            return False
        raise


def _ckan_recursos(base: str, pacote: str) -> list[str]:
    d = json.loads(_get(f"{base}/api/3/action/package_show?id={pacote}"))
    return [r["url"] for r in d["result"]["resources"]]


def _ckan_por_nome(base: str, pacote: str) -> dict[str, str]:
    """Nome do recurso (em minúsculas) -> URL. No ES, o endereço dos meses antigos não traz o mês; o nome traz."""
    d = json.loads(_get(f"{base}/api/3/action/package_show?id={pacote}"))
    return {(r.get("name") or "").strip().lower(): r["url"] for r in d["result"]["resources"]}


def _csv(arq: Path, enc: str = "utf-8-sig", sep: str = ";"):
    with arq.open(encoding=enc, errors="replace", newline="") as f:
        yield from csv.DictReader(f, delimiter=sep)


# ---------------------------------------------------------------------------------------------------- PR
def mes_pr(ano: int, mes: int, ctx: dict) -> dict | None:
    if "vinculos" not in ctx:
        ctx["vinculos"] = pr.ler_vinculos()
        print(f"  PR: {len(ctx['vinculos'])} vínculos no cadastro", flush=True)
    vinculos = ctx["vinculos"]
    arq = pr.PASTA_BRUTO / "tmp" / f"REMUNERACAO-{ano}-{mes:02d}.zip"
    try:
        if not pr._baixar(pr.URL_MES.format(ano=ano, mes=mes), arq):
            return None
        s = Somador(ano, mes)
        for r in pr._linhas(arq):
            cod = r["cod_vinculo"]
            sigla, inst, _lot, _mun, situacao = vinculos.get(cod, (r["sigla_orgao"], "", "", "", ""))
            if situacao in pr.INATIVOS or r["sigla_orgao"] == pr.PREVIDENCIA:
                continue
            sg = r["sigla_orgao"] or sigla
            if sg in FORA_PR:
                continue
            s.add(cod, sg, inst or sg, base=_num(r["vencimento"]) + _num(r["gratificacao"]) - abs(_num(r["redutor"])),
                  outros=_num(r["outros"]), retroativos=_num(r["retroativos"]), auxilios=_num(r["aux_transp_alim"]),
                  ir=abs(_num(r["ir"])), prev=abs(_num(r["previdencia"])))
        return s.resultado()
    finally:
        arq.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------------- ES
ES_FORA = re.compile(r"\b13\b|DECIMO|ABONO FERIAS|ADIANT.*FERIAS|AB FER|FERIAS DT|1/3", re.I)
ES_IR = re.compile(r"^IR\b|IMPOSTO|IRRF", re.I)
ES_PREV = re.compile(r"INSS|FPS|IPAJM|PREVID|CONTRIB", re.I)
ES_AUX = re.compile(r"AUX|AJUDA|INDEN|BOLSA|DIARIA|TRANSPORTE", re.I)
ES_OUTROS = re.compile(r"ESCALA|EXTRA|SUBSTITUI|BONIFICA|PRODUTIV|CONSELHO|CARGA HORARIA|PLANTAO|HORA|NOTURNO|JETON", re.I)
ES_RETRO = re.compile(r"EXERC|ANTERIOR|DIFEREN|RETROAT|ATRASAD", re.I)


def _mes_num(s: str) -> int:
    """"10/2026" -> 2026*12+10, para comparar a competência com o mês da folha."""
    m = re.match(r"(\d{1,2})/(\d{4})", s or "")
    return int(m.group(2)) * 12 + int(m.group(1)) if m else 0


def mes_es(ano: int, mes: int, ctx: dict) -> dict | None:
    if "urls" not in ctx:
        ctx["urls"] = _ckan_por_nome("https://dados.es.gov.br", "portal-da-transparencia-pessoal")
    url = ctx["urls"].get(f"remuneracoes-{mes:02d}_{ano}.csv")
    if not url:
        return None
    arq = PASTA / "tmp" / f"es-{ano}-{mes:02d}.csv"
    try:
        if not _baixar(url, arq):
            return None
        s = Somador(ano, mes)
        folha = ano * 12 + mes
        for r in _csv(arq):
            if (r.get("Situacao_Folha") or "").strip().upper() != "ATIVO":
                continue
            orgao = (r.get("Orgao") or "").strip()
            if not orgao or "PREVIDENCIA" in orgao.upper():
                continue
            rub = (r.get("Rubrica") or "").strip().upper()
            v = _num(r.get("Valor"))
            if not v:
                continue
            sinal = 1.0 if (r.get("VantagemDesconto") or "").strip().upper() == "V" else -1.0
            chave = (orgao, r.get("NumFunc"), r.get("NumVinc"))
            if "ABATE TETO EC" in rub:
                s.add(chave, orgao, orgao, base=-abs(v))
            elif "ABATE TETO" in rub:
                continue   # ABATE TETO RGPS: o teto do regime geral, para a contribuição; não é o corte pelo teto
            elif ES_IR.search(rub):
                s.add(chave, orgao, orgao, ir=-sinal * v)
            elif ES_PREV.search(rub):
                s.add(chave, orgao, orgao, prev=-sinal * v)
            elif ES_FORA.search(rub):
                continue
            elif sinal < 0 and not any(p.search(rub) for p in (ES_AUX, ES_OUTROS, ES_RETRO)) and rub not in (
                    "SUBSIDIO", "VENCIMENTO", "SALARIO BASE"):
                continue   # outros descontos (faltas, consignações, reposições): não mexem no que se recebe
            else:
                atrasado = folha - _mes_num(r.get("MesCompetencia")) >= 2 or bool(ES_RETRO.search(rub))
                g = "retroativos" if atrasado else "auxilios" if ES_AUX.search(rub) else "outros" if ES_OUTROS.search(rub) else "base"
                s.add(chave, orgao, orgao, **{g: sinal * v})
        return s.resultado()
    finally:
        arq.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------------- PE
def mes_pe(ano: int, mes: int, ctx: dict) -> dict | None:
    if "urls" not in ctx:
        ctx["urls"] = _ckan_recursos("https://dados.pe.gov.br", "remuneracao-de-servidores")
    nomes = (f"/{ano}_{mes}_remuneracao_ativos.csv", f"/{ano}_{mes:02d}_remuneracao_ativos.csv")   # o mês vem com ou sem zero
    url = next((u for u in ctx["urls"] if u.lower().endswith(nomes)), None)
    if not url:
        return None
    arq = PASTA / "tmp" / f"pe-{ano}-{mes:02d}.csv"
    try:
        if not _baixar(url, arq):
            return None
        s = Somador(ano, mes)
        for i, r in enumerate(_csv(arq)):
            inst = (r.get("r_instituicao") or "").strip()
            s.add((inst, r.get("r_matricula"), i), inst, inst,
                  base=_num(r.get("r_remuneracao")) - abs(_num(r.get("r_desconto_excedente"))),
                  outros=_num(r.get("r_outras_vantagens")),
                  ir=abs(_num(r.get("r_imposto_renda"))), prev=abs(_num(r.get("r_descontos_previdencia"))))
        return s.resultado()
    finally:
        arq.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------------- PB
def mes_pb(ano: int, mes: int, ctx: dict) -> dict | None:
    base_url = f"https://api.dados.pb.gov.br/api/v1/remuneracao/servidor?ano={ano}&mes={mes}&per_page=1000"
    s = Somador(ano, mes)
    pagina, total = 1, 1
    while pagina <= total:
        d = json.loads(_get(f"{base_url}&page={pagina}", timeout=180))
        total = int(d.get("paginacao", {}).get("total_paginas") or 0)
        for i, r in enumerate(d.get("dados") or []):
            if (r.get("situacaoServidor") or "").upper() != "ATIVO":
                continue
            orgao = (r.get("orgaoLotacao") or "").strip()
            s.add((pagina, i), orgao, orgao, base=_num(r.get("vantagemFixa")) - abs(_num(r.get("valorRedutor"))),
                  outros=_num(r.get("vantagemVariavel")), ir=abs(_num(r.get("valorIr"))), prev=abs(_num(r.get("valorPrevidenciario"))))
        pagina += 1
        time.sleep(0.2)
    return s.resultado() if total else None


# ---------------------------------------------------------------------------------------------------- RN
def _get_paciente(url: str, timeout: int = 300) -> bytes:
    """Como _get, mas espera quando o servidor pede calma (HTTP 429), como o do RN depois de alguns CSVs seguidos."""
    for espera in (0, 30, 60, 120, 240):
        time.sleep(espera)
        try:
            return _get(url, timeout=timeout)
        except urllib.error.HTTPError as erro:
            if erro.code != 429:
                raise
    raise RuntimeError(f"{url}: o servidor continuou pedindo para esperar (HTTP 429)")


def mes_rn(ano: int, mes: int, ctx: dict) -> dict | None:
    api = "https://api.remuneracao.rn.gov.br"
    try:
        d = json.loads(_get_paciente(f"{api}/ObterPorOrgao?mes={mes:02d}&ano={ano}&pagina=1", timeout=120) or b"null")
    except urllib.error.HTTPError as erro:
        if erro.code in (400, 404, 500):
            return None
        raise
    except json.JSONDecodeError:
        return None   # mês ainda não publicado: a API responde com o corpo vazio
    if not isinstance(d, dict):
        return None
    orgaos = d.get("itens") or []
    if not orgaos:
        return None
    s = Somador(ano, mes)
    for o in orgaos:
        nome = (o.get("orgao") or "").strip()
        if INATIVOS.search(nome):
            continue   # o "órgão" dos aposentados
        texto = _get_paciente(f"{api}/ExportarPorOrgao?mes={mes:02d}&ano={ano}&id={o['id']}").decode("utf-8-sig", errors="replace")
        for i, r in enumerate(csv.DictReader(io.StringIO(texto), delimiter=";")):
            if (r.get("Dt.Inativacao") or "").strip():
                continue
            s.add((o["id"], i), nome, nome, base=_num(r.get("RemuneracaoMes")) - abs(_num(r.get("RedutorArt.37/CF"))),
                  outros=_num(r.get("OutrasRemuneracoes")), ir=abs(_num(r.get("IRPF"))), prev=abs(_num(r.get("Previdencia"))))
        time.sleep(3)
    return s.resultado()


# ---------------------------------------------------------------------------------------------------- GO
def mes_go(ano: int, mes: int, ctx: dict) -> dict | None:
    if "urls" not in ctx:
        ctx["urls"] = _ckan_recursos("https://dadosabertos.go.gov.br", "folha-de-pagamento")
    url = next((u for u in ctx["urls"] if u.lower().endswith(f"folhapagamento_{ano}{mes:02d}.csv")), None)
    if not url:
        return None
    arq = PASTA / "tmp" / f"go-{ano}-{mes:02d}.csv"
    try:
        if not _baixar(url, arq):
            return None
        s = Somador(ano, mes, com_ir=False)
        nomes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        linhas = []
        for r in _csv(arq):
            if (r.get("DESC_SITUACAO_FUNCIONAL") or "").strip().lower() != "ativo":
                continue
            cod = (r.get("CODG_ORGAO") or "").strip()
            nomes[cod][(r.get("NOME_DEPTO_ORGAO") or "").strip()] += 1
            base = (_num(r.get("VALR_PROVENTO")) - _num(r.get("VALR_DECIMO_TERCEIRO"))
                    - _num(r.get("VLR_FERIAS_MAIS_UM_TERCO_FERIAS")) - abs(_num(r.get("VALR_CORTE_TETO"))))
            linhas.append((r.get("ID_SERVIDOR_ORGAO") or len(linhas), cod, base))
        # O arquivo não traz o nome do órgão, só o departamento: fica o departamento mais comum de cada órgão.
        nome_de = {c: max(d, key=d.get) for c, d in nomes.items()}
        for chave, cod, base in linhas:
            s.add(chave, cod, nome_de.get(cod, cod), base=base)
        return s.resultado()
    finally:
        arq.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------------------- DF
DF_FORA = re.compile(r"13|natal|f[ée]rias|dec(imo)?\.? ?terc|grat\.? ?nat", re.I)   # "DEC TERCEIRO-ATIVO", "GRAT.NATALINA"…


def meses_df(ano: int, faltam: list[int]) -> dict[int, dict]:
    """O zip do DF é anual: baixa uma vez e soma os meses que faltam daquele ano."""
    arq = PASTA / "tmp" / f"df-{ano}.zip"
    saida: dict[int, dict] = {}
    try:
        if not _baixar(f"https://www.transparencia.df.gov.br/arquivos/portal-dados-abertos/Remuneracao_{ano}.zip", arq, timeout=1800):
            return saida
        with zipfile.ZipFile(arq) as z:
            nomes = z.namelist()
            for mes in faltam:
                folha = next((n for n in nomes if n.endswith(f"Remuneracao_{ano}_{mes:02d}.csv")), None)
                if not folha:
                    continue
                # 13º e férias vêm dentro das verbas eventuais: o detalhamento por rubrica diz quanto.
                fora: dict[tuple, float] = defaultdict(float)
                det = next((n for n in nomes if n.endswith(f"Remuneracao_Detalhamento_{ano}_{mes:02d}.csv")), None)
                if det:
                    with z.open(det) as f:
                        for r in csv.DictReader(io.TextIOWrapper(f, encoding="cp1252", errors="replace", newline=""), delimiter=";"):
                            if (r.get("NATUREZA") or "").strip().upper() == "VERBAS EVENTUAIS" and DF_FORA.search(r.get("DESCRIÇÃO DA RUBRICA") or ""):
                                # os descontos de adiantamento do 13º e das férias também vêm nas verbas eventuais
                                sinal = -1.0 if (r.get("TIPO DE RUBRICA") or "").strip().upper().startswith("DESC") else 1.0
                                fora[((r.get("CÓDIGO DO ÓRGÃO") or "").strip(), (r.get("MATRÍCULA") or "").strip())] += sinal * _num(r.get("VALOR"))
                s = Somador(ano, mes)
                with z.open(folha) as f:
                    for r in csv.DictReader(io.TextIOWrapper(f, encoding="cp1252", errors="replace", newline=""), delimiter=";"):
                        if INATIVOS.search(r.get("SITUAÇÃO") or ""):
                            continue
                        cod, mat = (r.get("CÓDIGO DO ÓRGÃO") or "").strip(), (r.get("MATRÍCULA") or "").strip()
                        orgao = " ".join((r.get("ÓRGÃO") or "").split())
                        s.add((cod, mat), cod, orgao,
                              base=_num(r.get("REMUNERAÇÃO BÁSICA")) + _num(r.get("VALOR DA FUNÇÃO")) + _num(r.get("COMISSÃO CONSELHEIRO"))
                              - abs(_num(r.get("TETO REDUTOR"))),
                              outros=_num(r.get("HORA EXTRA")) + _num(r.get("VERBAS EVENTUAIS")) - fora.get((cod, mat), 0.0)
                              + _num(r.get("LICENÇA PRÊMIO")) + _num(r.get("OUTROS RECEBIMENTOS")),
                              retroativos=_num(r.get("VERBAS JUDICIAIS")), auxilios=_num(r.get("BENEFÍCIOS")),
                              ir=abs(_num(r.get("IRRF"))), prev=abs(_num(r.get("SEG. SOCIAL"))))
                x = s.resultado()
                if x:
                    saida[mes] = x
        return saida
    finally:
        arq.unlink(missing_ok=True)


LEITORES = {"PR": mes_pr, "ES": mes_es, "PE": mes_pe, "PB": mes_pb, "RN": mes_rn, "GO": mes_go}


# ---------------------------------------------------------------------------------------------------- montagem
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


def montar_uf(uf: str, meses: dict[str, dict]) -> dict:
    ordem = sorted(meses)
    siglas = sorted({s for m in ordem for s in meses[m]["orgaos"]})
    nome = {s: meses[m]["orgaos"][s]["nome"] for m in ordem for s in meses[m]["orgaos"]}
    estatais = sorted({nome[s] for s in siglas if ESTATAL.search(f"{s} {nome[s]}")})
    siglas = [s for s in siglas if not ESTATAL.search(f"{s} {nome[s]}")]
    orgaos = {s: r for s in siglas if (r := resumir([meses[m]["orgaos"][s] for m in ordem if s in meses[m]["orgaos"]]))}
    serie = {m: [sum(o["vinculos"] for s, o in meses[m]["orgaos"].items() if s in orgaos),
                 sum(o["acima"] for s, o in meses[m]["orgaos"].items() if s in orgaos),
                 round(sum(o["excesso"] for s, o in meses[m]["orgaos"].items() if s in orgaos))] for m in ordem}
    fonte, url = FONTES[uf]
    return {"nome": NOMES_LEGIVEIS[uf], "fonte": fonte, "url": url, "grupos": NOMES_UF[uf], "com_ir": uf != "GO",
            "de": ordem[0], "ate": ordem[-1], "meses": len(ordem), "orgaos": orgaos, "serie": serie, "estatais_fora": estatais}


def candidatos(hoje: date) -> list[tuple[int, int]]:
    a, m, saida = hoje.year, hoje.month, []
    for _ in range(MESES + 4):
        saida.append((a, m))
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
    return saida


def carregar(uf: str, so_cache: bool) -> dict[str, dict]:
    pasta = PASTA / uf.lower()
    pasta.mkdir(parents=True, exist_ok=True)
    meses: dict[str, dict] = {}
    lista = candidatos(date.today())
    for a, m in lista:   # o que já está no cache
        arq = pasta / f"{a}-{m:02d}.json.gz"
        if arq.exists():
            meses[f"{a}-{m:02d}"] = json.loads(gzip.decompress(arq.read_bytes()))
    if so_cache:
        return dict(sorted(meses.items())[-MESES:])

    def guardar(a: int, m: int, x: dict | None) -> None:
        chave = f"{a}-{m:02d}"
        if x is None:
            print(f"  {uf} {chave}: ainda não publicado", flush=True)
            return
        (pasta / f"{chave}.json.gz").write_bytes(gzip.compress(json.dumps(x, ensure_ascii=False, separators=(",", ":")).encode()))
        os_ = x["orgaos"].values()
        print(f"  {uf} {chave}: {sum(o['vinculos'] for o in os_)} vínculos, {sum(o['acima'] for o in os_)} acima do teto", flush=True)
        meses[chave] = x

    if uf == "DF":
        por_ano: dict[int, list[int]] = defaultdict(list)
        for a, m in lista:
            if f"{a}-{m:02d}" not in meses:
                por_ano[a].append(m)
        for a in sorted(por_ano, reverse=True):
            if len(meses) >= MESES:
                break
            achados = meses_df(a, por_ano[a])
            for m in sorted(por_ano[a], reverse=True):
                if m in achados:
                    guardar(a, m, achados[m])
    else:
        ctx: dict = {}
        for a, m in lista:
            chave = f"{a}-{m:02d}"
            if len(meses) >= MESES and chave < min(meses):
                break
            if chave in meses:
                continue
            guardar(a, m, LEITORES[uf](a, m, ctx))
    return dict(sorted(meses.items())[-MESES:])


def main() -> None:
    p = argparse.ArgumentParser(prog="supersalarios-estados", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    p.add_argument("--so-cache", action="store_true", help="monta a saída com o que já está em data/raw, sem baixar")
    p.add_argument("--uf", help="só estes estados, separados por vírgula (os outros vêm do cache)")
    args = p.parse_args()
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    pedidos = set(args.uf.upper().split(",")) if args.uf else set(ESTADOS)
    estados = {}
    for uf in ESTADOS:
        try:
            meses = carregar(uf, args.so_cache or uf not in pedidos)
        except Exception as erro:  # noqa: BLE001 — um estado que falha não derruba os outros; fica o que há no cache
            print(f"  {uf}: falhou ({erro}); fica o que há no cache", flush=True)
            meses = carregar(uf, True)
        if len(meses) >= MINIMO_MESES:
            estados[uf] = montar_uf(uf, meses)
        elif meses:
            print(f"  {uf}: só {len(meses)} meses no cache; fica fora até completar {MINIMO_MESES}", flush=True)
    doc = {"gerado": date.today().isoformat(), "faixas": FAIXAS, "grupos": GRUPOS, "estados": estados}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    for uf, e in estados.items():
        os_ = e["orgaos"].values()
        exc = sum(o["excesso"] or 0 for o in os_)
        print(f"{uf} {e['de']} a {e['ate']} ({e['meses']} meses): {sum(o['vinculos'] for o in os_)} vínculos num mês típico, "
              f"{sum(o['acima'] or 0 for o in os_)} acima do teto, R$ {exc / 1e6:.1f} mi acima do teto")
        for s, o in sorted(e["orgaos"].items(), key=lambda i: -(i[1]["excesso"] or 0))[:5]:
            print(f"    {s[:12]:12s} {o['nome'][:42]:42s} {o['acima'] or 0:5d} de {o['vinculos']:6d}  R$ {(o['excesso'] or 0) / 1e6:6.1f} mi")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")
