"""Parte comum de estado_pr.py e estado_sc.py: a folha de pagamento do estado somada por cidade.

Os dois estados publicam o salário de cada servidor com o lugar onde ele trabalha. Cada
comando lê a sua fonte e entrega, mês a mês, somas por (município, área, unidade, órgão); daqui
para a frente é igual: cache dos meses em data/raw/estados/{uf}/, saída no formato lido por
site/src/lib/estadual.ts e cópia em pipeline/referencia/ para o CI.

Nunca passa por aqui nome nem CPF de servidor: só a soma dos salários e quantos vínculos
entraram nela. Uma unidade só aparece pelo nome (entre as maiores da cidade) se tiver pelo
menos MINIMO_VINCULOS pessoas, para não mostrar o salário de alguém sozinho.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

from .cidades import RAIZ, baixar_entes

MAIORES = 6
MINIMO_VINCULOS = 5

# Áreas pelo código de função do orçamento: o site escreve o nome (lib/estadual.ts).
EDUCACAO, SAUDE, SEGURANCA, OUTRAS = "12", "10", "06", "00"
NOMES_AREAS = {EDUCACAO: "Educação", SAUDE: "Saúde", SEGURANCA: "Segurança pública", OUTRAS: "Outras áreas do governo"}


def chave(nome: str) -> str:
    s = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[-'/().,]", " ", s).split())


def municipios(uf: str) -> dict[str, str]:
    """Nome sem acento, em maiúsculas -> código do IBGE."""
    return {chave(e["ente"]): str(e["cod_ibge"]) for e in baixar_entes() if e["esfera"] == "M" and e["uf"] == uf}


class Mes:
    """Somas de um mês. `unid` vai por (ibge, área, unidade, órgão) -> [valor, vínculos]."""

    def __init__(self) -> None:
        self.ativos = 0.0       # toda a folha dos servidores ativos
        self.inativos = 0.0     # aposentadorias e pensões (não têm lugar de trabalho)
        self.sem_cidade: dict[str, float] = defaultdict(float)  # ativos sem cidade, por órgão
        self.unid: dict[tuple, list] = defaultdict(lambda: [0.0, 0])

    def somar(self, ibge: str | None, area: str, unidade: str, orgao: str, valor: float) -> None:
        self.ativos += valor
        if not ibge:
            self.sem_cidade[orgao] += valor
            ibge = ""  # a unidade fica guardada com o código vazio, para conferir o que não achou cidade
        u = self.unid[(ibge, area, unidade, orgao)]
        u[0] += valor
        u[1] += 1

    def gravar(self, arq: Path) -> None:
        doc = {"ativos": self.ativos, "inativos": self.inativos, "sem_cidade": self.sem_cidade,
               "unid": [[*k, round(v, 2), n] for k, (v, n) in self.unid.items()]}
        arq.parent.mkdir(parents=True, exist_ok=True)
        tmp = arq.with_name(arq.name + ".tmp")
        tmp.write_bytes(gzip.compress(json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()))
        tmp.replace(arq)

    @classmethod
    def ler(cls, arq: Path) -> "Mes":
        doc = json.loads(gzip.decompress(arq.read_bytes()))
        m = cls()
        m.ativos, m.inativos = doc["ativos"], doc["inativos"]
        m.sem_cidade.update(doc["sem_cidade"])
        for ibge, area, unidade, orgao, v, n in doc["unid"]:
            m.unid[(ibge, area, unidade, orgao)] = [v, n]
        return m


def montar(ano: int, meses: list[Mes], ate_mes: int, fonte: str, texto: dict) -> dict:
    """O documento lido pelo site. `texto["nota"]` pode usar {sem_cidade} e {parte_sem_cidade}."""
    mun: dict = defaultdict(lambda: {"local": 0.0, "areas": defaultdict(float), "unid": defaultdict(lambda: [0.0, 0])})
    tot = defaultdict(float)
    sem_cidade = defaultdict(float)
    sem_unidade = defaultdict(float)
    for m in meses:
        tot["ativos"] += m.ativos
        tot["inativos"] += m.inativos
        for orgao, v in m.sem_cidade.items():
            sem_cidade[orgao] += v
        for (ibge, area, unidade, orgao), (v, n) in m.unid.items():
            if not ibge:
                sem_unidade[(unidade, orgao)] += v
                continue
            x = mun[ibge]
            x["local"] += v
            x["areas"][area] += v
            u = x["unid"][(unidade, orgao)]
            u[0] += v
            u[1] = max(u[1], n)  # vínculos no mês de mais gente, não a soma dos meses
    tot["local"] = sum(x["local"] for x in mun.values())
    tot["sem_cidade"] = sum(sem_cidade.values())

    saida = {}
    for ibge, x in mun.items():
        maiores = sorted(((k, v) for k, (v, n) in x["unid"].items() if n >= MINIMO_VINCULOS and k[0]), key=lambda i: -i[1])
        saida[ibge] = {
            "local": round(x["local"]), "pago": 0, "folha": 0,
            "areas": {k: round(v) for k, v in sorted(x["areas"].items(), key=lambda i: -i[1]) if v > 0},
            # mesmo formato da Paraíba: [credor, ação, órgão, valor]; aqui a "ação" é a unidade
            "maiores": [["", unidade, orgao, round(v)] for (unidade, orgao), v in maiores[:MAIORES]],
        }
    parte = tot["sem_cidade"] / tot["ativos"] if tot["ativos"] else 0
    texto = {**texto, "nota": texto["nota"].format(sem_cidade=_bi(tot["sem_cidade"]), parte_sem_cidade=f"{100 * parte:.0f}%".replace(".", ","))}
    print("  unidades sem cidade (as maiores):")
    for (unidade, orgao), v in sorted(sem_unidade.items(), key=lambda i: -i[1])[:25]:
        print(f"    R$ {v / 1e6:6.1f} mi  {unidade or '(sem nome)'} · {orgao[:40]}")
    return {
        "ano": ano, "ate_mes": ate_mes, "fonte": fonte, "texto": texto,
        "estado": {"folha_ativos": round(tot["ativos"]), "local": round(tot["local"]), "sem_cidade": round(tot["sem_cidade"]),
                   "inativos": round(tot["inativos"]), "cidades": len(saida),
                   "sem_cidade_por_orgao": {k: round(v) for k, v in sorted(sem_cidade.items(), key=lambda i: -i[1]) if v >= 1e6}},
        "areas": NOMES_AREAS, "mun": saida,
    }


def _bi(v: float) -> str:
    if v >= 1e9:
        return f"R$ {v / 1e9:.1f} {'bilhão' if v < 1.95e9 else 'bilhões'}".replace(".", ",")
    return f"R$ {v / 1e6:.0f} milhões"


def gravar(doc: dict, saida: Path, referencia: Path) -> None:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (saida, referencia):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    e = doc["estado"]
    pct = lambda k: f"{100 * e[k] / e['folha_ativos']:.1f}%"  # noqa: E731
    print(f"{doc['ano']}: folha dos ativos R$ {e['folha_ativos'] / 1e9:.2f} bi; com cidade R$ {e['local'] / 1e9:.2f} bi "
          f"({pct('local')}) em {e['cidades']} cidades; sem cidade R$ {e['sem_cidade'] / 1e9:.2f} bi ({pct('sem_cidade')}); "
          f"aposentadorias e pensões (fora da conta) R$ {e['inativos'] / 1e9:.2f} bi")
    for orgao, v in list(e["sem_cidade_por_orgao"].items())[:10]:
        print(f"    sem cidade: {orgao} R$ {v / 1e6:.0f} mi")
    print(f"saída: {saida.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB) e {referencia.relative_to(RAIZ)}")


def copiar_referencia(referencia: Path, pasta: Path) -> None:
    """Copia a versão guardada para pasta/{ano}.json (o ano é o do próprio arquivo)."""
    saida = pasta / f"{json.loads(referencia.read_text(encoding='utf-8'))['ano']}.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(referencia, saida)
    print(f"saída: {saida.relative_to(RAIZ)} (cópia de {referencia.relative_to(RAIZ)})")
