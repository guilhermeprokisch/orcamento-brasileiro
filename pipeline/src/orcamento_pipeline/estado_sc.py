"""Salários pagos pelo governo de Santa Catarina em cada município, pela folha de pagamento.

    uv run estado-sc 2025
    uv run estado-sc 2025 --sem-baixar   # só copia pipeline/referencia/estado-sc.json

O Portal da Transparência de Santa Catarina (https://www.transparencia.sc.gov.br/remuneracao-servidores)
tem, para cada mês desde 2016, o botão "exportar CSV" com a folha dos servidores ativos do Poder
Executivo: órgão, unidade de exercício e salário bruto. É o mesmo arquivo do portal de dados
abertos (dados.sc.gov.br/dataset/remuneracao-servidores), que lá só tem 2022, parte de 2023 e
2026. Um mês leva cerca de 45 segundos para sair (~22 MB). O total das aposentadorias e pensões
vem do resumo da mesma página.

A unidade é onde o servidor trabalha (exercício, não lotação), e a cidade quase sempre está no
nome dela: "EEB DR RENATO RAMOS DA SILVA - LAGUNA", "9BPM/4CIA/2PEL/3GP - SIDEROPOLIS",
"PENITENCIARIA DE FLORIANOPOLIS". Os setores dos hospitais do estado vêm só com a sigla do
hospital ("EMERGENCIA-HHG/GETEC") e os departamentos da Udesc só com a sigla do centro ("CCT -
DEPARTAMENTO DE FISICA"): para esses há uma tabela abaixo. Fica sem cidade o que não tem lugar
no nome: as sedes das secretarias, a Fazenda, a Procuradoria, a reitoria da Udesc.

O arquivo traz nome e CPF (mascarado) de cada servidor: aqui só se leem órgão, unidade e valor,
linha a linha, sem gravar o arquivo. O cache em data/raw/estados/sc/{ano}-{mes}.json.gz guarda
só as somas de cada mês. No CI só a cópia (--sem-baixar): o ano fechado não muda.
Saída em site/public/data/estados/sc/{ano}.json, com cópia em pipeline/referencia/estado-sc.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date

from . import folha_estadual as fe
from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://api-portal-transparencia.apps.sm.okd4.ciasc.sc.gov.br/api/remuneracao-servidores"
PASTA_BRUTO = RAIZ / "data" / "raw" / "estados" / "sc"
SAIDA = RAIZ / "site" / "public" / "data" / "estados" / "sc"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "estado-sc.json"
ATIVOS = {"SITUACAO": 1, "TIPOCONSULTA": "SERVIDORES"}

# Grafias da folha que diferem do IBGE.
APELIDOS = {"FPOLIS": "FLORIANOPOLIS", "HERVAL DO OESTE": "HERVAL D OESTE", "B CAMBORIU": "BALNEARIO CAMBORIU"}
# Hospitais e institutos da Secretaria da Saúde, pela sigla que aparece nos setores.
HOSPITAIS = {
    "HHG": ("Hospital Regional Homero de Miranda Gomes", "SAO JOSE"),
    "HCR": ("Hospital Governador Celso Ramos", "FLORIANOPOLIS"),
    "HJG": ("Hospital Infantil Joana de Gusmão", "FLORIANOPOLIS"),
    "HHS": ("Hospital Regional Hans Dieter Schmidt", "JOINVILLE"),
    "HTR": ("Hospital Tereza Ramos", "LAGES"),
    "ICA": ("Instituto de Cardiologia", "SAO JOSE"),
    "MDV": ("Maternidade Darcy Vargas", "JOINVILLE"),
    "MCD": ("Maternidade Carmela Dutra", "FLORIANOPOLIS"),
    "HNR": ("Hospital Nereu Ramos", "FLORIANOPOLIS"),
    "IPQ": ("Instituto de Psiquiatria", "SAO JOSE"),
    "HWC": ("Hospital Regional Waldomiro Colautti", "IBIRAMA"),
    "MCK": ("Maternidade Dona Catarina Kuss", "MAFRA"),
    "HST": ("Hospital Santa Teresa", "SAO PEDRO DE ALCANTARA"),
    "CEPON": ("Cepon", "FLORIANOPOLIS"),
    "HFL": ("Hospital Florianópolis", "FLORIANOPOLIS"),
}
# Centros da Udesc, pela sigla no começo do nome do departamento.
UDESC = {
    "CCT": "JOINVILLE", "CAV": "LAGES", "CEFID": "FLORIANOPOLIS", "ESAG": "FLORIANOPOLIS", "FAED": "FLORIANOPOLIS",
    "CEART": "FLORIANOPOLIS", "CEAD": "FLORIANOPOLIS", "CEO": "CHAPECO", "CERES": "LAGUNA", "CEAVI": "IBIRAMA",
    "CEPLAN": "SAO BENTO DO SUL", "CESFI": "BALNEARIO CAMBORIU",
}
# Estações da Epagri, pela sigla no começo do nome da equipe.
EPAGRI = {"EEI": "ITAJAI", "EEL": "LAGES", "EECD": "CACADOR", "CEPAF": "CHAPECO"}
# Unidades com nome próprio, sem a cidade no nome.
UNIDADES = {"PENITENCIARIA SUL": "CRICIUMA", "HOSPITAL DE CUSTODIA E TRATAMENTO PSIQUIATRICO": "FLORIANOPOLIS"}
UDESC_PINHALZINHO = "ENGENHARIA DE ALIMENTOS"  # o único departamento do CEO que fica em Pinhalzinho
SUFIXO_ATO = re.compile(r"\s*\((LC|DEC|RESOL)[^)]*\)?\s*$")  # "(LC 741/2019)", "(RESOL 17/25)"
CODIGO = re.compile(r"^\d{6,}\s*-?\s*")
SETOR_DE_HOSPITAL = re.compile(r"-([A-Z]{2,5})/G[A-Z]+")

TEXTO = {
    "resumo": "pagou",
    "onde": "em salários a servidores estaduais que trabalham em",
    "maiores": "Onde o estado paga mais salários aqui",
    "aviso": "Só somas por cidade e por unidade: nenhum nome de servidor é guardado.",
    "nota": ("Só a folha de pagamento: o salário bruto dos servidores ativos do Poder Executivo que trabalham em escolas, "
             "hospitais, quartéis, delegacias e outras unidades do estado nesta cidade. Não entram obras, compras, repasses "
             "nem aposentadorias. A cidade sai do nome da unidade onde cada um trabalha; fica sem cidade o que não tem lugar "
             "no nome, como as sedes das secretarias, a Fazenda e a Procuradoria ({sem_cidade}, ou {parte_sem_cidade} da "
             "folha dos ativos), a maior parte com sede em Florianópolis. Quem trabalha em mais de uma cidade aparece só "
             "na da sua unidade."),
}


def area(orgao: str) -> str:
    o = fe.chave(orgao)
    if "EDUCACAO" in o or "UNIVERSIDADE" in o:
        return fe.EDUCACAO
    if "SAUDE" in o:
        return fe.SAUDE
    if any(p in o for p in ("POLICIA", "BOMBEIRO", "PRISIONAL", "SEGURANCA PUBLICA", "DEFESA CIVIL")):
        return fe.SEGURANCA
    return fe.OUTRAS


class Cidades:
    def __init__(self, ibge_por_nome: dict[str, str]) -> None:
        self.ibge = ibge_por_nome
        nomes = sorted(ibge_por_nome, key=len, reverse=True)
        self.no_texto = re.compile(r"\b(" + "|".join(map(re.escape, nomes)) + r")\b")
        self.cache: dict[tuple[str, str], tuple[str | None, str]] = {}

    def _nome(self, parte: str) -> str | None:
        n = fe.chave(SUFIXO_ATO.sub("", parte))
        n = APELIDOS.get(n, n)
        return n if n in self.ibge else None

    def de(self, unidade: str, orgao: str) -> tuple[str | None, str]:
        """(código do IBGE ou None, nome da unidade para mostrar)."""
        k = (unidade, orgao)
        if k not in self.cache:
            self.cache[k] = self._de(unidade, orgao)
        return self.cache[k]

    def _de(self, unidade: str, orgao: str) -> tuple[str | None, str]:
        u = " ".join(unidade.split())
        if h := SETOR_DE_HOSPITAL.search(u):
            if h.group(1) in HOSPITAIS:
                nome, cidade = HOSPITAIS[h.group(1)]
                return self.ibge[cidade], nome
        partes = [p.strip() for p in CODIGO.sub("", u).split(" - ")]
        if "UNIVERSIDADE" in fe.chave(orgao):
            # "CCT - DEPARTAMENTO DE FISICA" ou, em parte do ano, "DEPARTAMENTO DE FISICA CCT"
            centro = partes[0] if partes[0] in UDESC else u.rsplit(" ", 1)[-1]
            if centro in UDESC:
                cidade = "PINHALZINHO" if centro == "CEO" and UDESC_PINHALZINHO in u else UDESC[centro]
                return self.ibge[cidade], f"Udesc ({centro})"
        if "EPAGRI" in fe.chave(orgao) and (sigla := re.split(r"[- ]", partes[0])[0]) in EPAGRI:
            return self.ibge[EPAGRI[sigla]], f"Epagri ({sigla})"
        if (cidade := UNIDADES.get(fe.chave(partes[0]))) and len(partes) == 1:
            return self.ibge[cidade], partes[0]
        for i in range(len(partes) - 1, 0, -1):
            if cidade := self._nome(partes[i]):
                return self.ibge[cidade], " - ".join(partes[:i])
        achados = self.no_texto.findall(fe.chave(SUFIXO_ATO.sub("", " - ".join(partes))))
        if achados:
            return self.ibge[achados[-1]], " - ".join(partes)
        # "EEB X- NAVEGANTES": o hífen sem espaço antes
        if cidade := self._nome(partes[-1].rsplit("-", 1)[-1]):
            return self.ibge[cidade], partes[-1].rsplit("-", 1)[0].strip()
        return None, " - ".join(partes)


def _get(caminho: str, params: dict, timeout: int):
    url = f"{API}/{caminho}?" + urllib.parse.urlencode({k: json.dumps(v) if isinstance(v, dict) else v for k, v in params.items()})
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout, context=CONTEXTO_TLS)


def ultimo_mes_publicado() -> tuple[int, int]:
    with _get("data-ultima-atualizacao", {}, 60) as resp:
        d = json.load(resp)
    return int(d["ultimaCargaAno"]), int(d["ultimaCargaMes"])


def total_inativos(ano: int, mes: int) -> float:
    """Aposentadorias e pensões do mês, do resumo da página (sem nenhuma linha por pessoa)."""
    with _get("analise-detalhada", {"ano": ano, "mes": mes, "page": 1, "sort": {}, "filtro": {"TIPOCONSULTA": "GERAL"}}, 300) as resp:
        d = json.load(resp)
    return sum(float(c["valor_bruto"]) for c in d["data"] if c["categoria"] != "ATIVO")


def _valor(s: str) -> float:
    s = (s or "0").strip()
    return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s or 0)


def somar_mes(ano: int, mes: int, cidades: Cidades) -> fe.Mes:
    m = fe.Mes()
    for tentativa in range(3):
        try:
            m = fe.Mes()
            linhas = 0
            with _get("exportcsv", {"ano": ano, "mes": mes, "filtro": ATIVOS}, 900) as resp:
                for r in csv.DictReader(io.TextIOWrapper(resp, encoding="latin1", newline=""), delimiter=";"):
                    linhas += 1
                    v = _valor(r.get("ValorBruto"))
                    if not v:
                        continue
                    orgao = " ".join((r.get("OrgaoExercicio") or r.get("OrgaoOrigem") or "").split())
                    ibge, unidade = cidades.de(r.get("UnidadeExercicio") or "", orgao)
                    m.somar(ibge, area(orgao), unidade, orgao, v)
            if linhas < 50_000:
                raise RuntimeError(f"só {linhas} linhas no mês: arquivo incompleto")
            break
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(30 * (tentativa + 1))
    m.inativos = total_inativos(ano, mes)
    return m


# "15BPM/2CIA/2PEL/3GP" -> "15º Batalhão · 2ª Companhia · 2º Pelotão · 3º Grupo"
QUARTEIS = {"BPM": "º Batalhão", "CIA": "ª Companhia", "PEL": "º Pelotão", "GP": "º Grupo", "BBM": "º Batalhão de Bombeiros"}
QUARTEL = re.compile(r"^(\d+)(" + "|".join(QUARTEIS) + r")$")


def nome_de_quartel(nome: str) -> str:
    partes = [QUARTEL.match(p) for p in nome.split("/")]
    if len(partes) < 2 or not all(partes):
        return nome
    return " · ".join(m.group(1) + QUARTEIS[m.group(2)] for m in partes)


def renomear(m: fe.Mes) -> fe.Mes:
    for k in [k for k in m.unid if nome_de_quartel(k[2]) != k[2]]:
        v, n = m.unid.pop(k)
        u = m.unid[(k[0], k[1], nome_de_quartel(k[2]), k[3])]
        u[0] += v
        u[1] += n
    return m


def reavaliar(m: fe.Mes, cidades: Cidades) -> fe.Mes:
    """Passa de novo pelas tabelas as unidades do cache que ficaram sem cidade (sem baixar de novo)."""
    for (ibge, area_, unidade, orgao), (v, n) in list(m.unid.items()):
        if ibge:
            continue
        novo, nome = cidades.de(unidade, orgao)
        if novo:
            del m.unid[(ibge, area_, unidade, orgao)]
            u = m.unid[(novo, area_, nome, orgao)]
            u[0] += v
            u[1] += n
            m.sem_cidade[orgao] -= v
    return m


def main() -> None:
    p = argparse.ArgumentParser(prog="estado-sc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        fe.copiar_referencia(REFERENCIA, SAIDA)
        return

    cidades = Cidades(fe.municipios("SC"))
    meses: list[fe.Mes] = []
    try:
        ano_pub, mes_pub = ultimo_mes_publicado()
        ultimo = 12 if args.ano < ano_pub else mes_pub if args.ano == ano_pub else 0
        for mes in range(1, ultimo + 1):
            cache = PASTA_BRUTO / f"{args.ano}-{mes:02d}.json.gz"
            if cache.exists():
                meses.append(reavaliar(fe.Mes.ler(cache), cidades))
                continue
            m = somar_mes(args.ano, mes, cidades)
            print(f"  {args.ano}-{mes:02d}: ativos R$ {m.ativos / 1e6:.0f} mi, sem cidade R$ {sum(m.sem_cidade.values()) / 1e6:.0f} mi", flush=True)
            m.gravar(cache)
            meses.append(m)
            time.sleep(2)
    except Exception as erro:  # noqa: BLE001 — qualquer falha de download cai na cópia versionada
        if REFERENCIA.exists():
            print(f"  aviso: download falhou ({erro}); usando a cópia versionada", flush=True)
            fe.copiar_referencia(REFERENCIA, SAIDA)
            return
        raise
    if not meses:
        raise SystemExit(f"{args.ano}: nenhum mês publicado")
    meses = [renomear(m) for m in meses]
    doc = fe.montar(args.ano, meses, len(meses), "Portal da Transparência de Santa Catarina (remuneração dos servidores)", TEXTO)
    fe.gravar(doc, SAIDA / f"{args.ano}.json", REFERENCIA)


if __name__ == "__main__":
    main()
