"""Prefeituras: quem ganha mais que o prefeito da própria cidade (piloto: Paraíba, pela folha do TCE-PB).

    uv run supersalarios-municipios               # baixa a folha dos dois últimos anos e monta o arquivo do site
    uv run supersalarios-municipios --sem-baixar  # só copia pipeline/referencia/supersalarios-municipios.json

No município, o teto é o subsídio do prefeito (Constituição, art. 37, XI), para a prefeitura, a câmara, as autarquias e
os institutos de previdência. Os procuradores municipais seguem o do desembargador, 90,25% do teto do STF (STF, RE
663.696).

Fonte: os dados abertos do TCE-PB (Sagres), um ZIP por ano com a folha mensal dos 223 municípios. O arquivo traz um
valor só por vínculo e mês (o total das vantagens), sem separar 13º, férias e indenizações, e sem o corte pelo teto.
Por isso a conta usa o valor típico de cada pessoa, a mediana dos meses em que ela aparece, e não o de cada mês: um mês
com 13º, férias ou um atrasado não faz ninguém passar do teto. Ainda assim é um limite superior, porque o valor típico
pode trazer indenizações que não entram no teto.

O prefeito sai da própria folha (tipo de cargo "Eletivos", cargo com "PREFEIT" e sem "VICE"), pela mediana dos meses.
Ficam fora da conta os eletivos (prefeito, vice, vereadores), os inativos e os pensionistas. Os 12 meses mais recentes
publicados, sem dezembro (o mês do 13º).

O arquivo traz nome e CPF (mascarado): aqui só se lê, na memória, e nada por pessoa é guardado. A saída tem somas por
município, e o site só mostra os números de um município com pelo menos 5 vínculos acima do teto.
Saída em site/public/data/indicadores/supersalarios-municipios.json, com cópia em pipeline/referencia/.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import statistics
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date

from . import cidades as c
from .cidades import RAIZ
from .supersalarios import teto
from .supersalarios_estados import _baixar

PASTA = RAIZ / "data" / "raw" / "supersalarios-municipios"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "supersalarios-municipios.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "supersalarios-municipios.json"
URL_PB = "https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/servidores/servidores-{ano}.zip"
FONTE = "Tribunal de Contas do Estado da Paraíba, dados abertos do Sagres (folha de pessoal dos municípios)"
URL_FONTE = "https://dados-abertos.tce.pb.gov.br/"
MESES = 12
MINIMO_MUNICIPIOS = 200   # um mês só conta se a folha tiver quase todos os 223 municípios (o mês corrente sai aos poucos)
MINIMO_MESES_PESSOA = 3   # o valor típico de quem aparece em menos meses que isso fica de fora
DESEMBARGADOR = 0.9025    # o teto dos procuradores municipais, sobre o do STF
FORA = {"Eletivos", "Inativos/Pensionistas", "Benefício previdenciário temporário"}
PREFEITO = re.compile(r"PREFEIT", re.I)
VICE = re.compile(r"\bVICE", re.I)
PROCURADOR = re.compile(r"\bPROCURADOR", re.I)
ASSESSOR = re.compile(r"ASSESSOR|AUXILIAR|ASSISTENTE|SECRETARI[OA] D", re.I)
CAMARA = re.compile(r"C[ÂA]MARA", re.I)
# Grupos de cargo para o resumo do estado (só os que somam pelo menos 5 acima do teto aparecem).
CARGOS = [
    ("procuradores", re.compile(r"PROCURADOR", re.I)),
    ("médicos", re.compile(r"M[ÉE]DIC", re.I)),
    ("secretários municipais", re.compile(r"^SECRET[ÁA]RI[OA]\b(?! (ESCOLAR|EXECUTIV|ADJUNT|DE (ESCOLA|GABINETE)))", re.I)),
    ("auditores e fiscais", re.compile(r"AUDITOR|FISCAL|TRIBUT", re.I)),
    ("controladores e contadores", re.compile(r"CONTROLADOR|CONTADOR|CONT[ÁA]BIL", re.I)),
    ("professores", re.compile(r"PROFESSOR", re.I)),
]


def _valor(s: str | None) -> float:
    """"14.000" é 14 mil e "1.687,26" é 1.687,26: o ponto separa milhares; a vírgula, os centavos."""
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _chave(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z]", "", s)


def _linhas(ano: int):
    """As linhas do ano, lidas direto do ZIP (o CSV tem mais de 500 MB) e apagado depois."""
    arq = PASTA / "tmp" / f"pb-{ano}.zip"
    try:
        if not _baixar(URL_PB.format(ano=ano), arq, timeout=1800):
            return
        with zipfile.ZipFile(arq) as z, z.open(z.namelist()[0]) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"), delimiter=";")
    finally:
        arq.unlink(missing_ok=True)


def carregar(hoje: date) -> dict:
    anos = [hoje.year - 1, hoje.year]
    municipios_mes: dict[str, set] = defaultdict(set)
    # Por pessoa (só na memória): {chave: [município, unidade é câmara?, cargo, {mês: valor}]}
    pessoas: dict[tuple, list] = {}
    prefeito: dict[str, dict[str, float]] = defaultdict(dict)   # município -> mês -> subsídio
    nomes: dict[str, str] = {}
    vinculos: dict[tuple[str, str], int] = defaultdict(int)     # (município, mês) -> vínculos na conta
    for ano in anos:
        for r in _linhas(ano):
            mes = (r.get("ano_mes") or "").strip()
            if len(mes) != 6 or mes.endswith("12"):
                continue
            m = f"{mes[:4]}-{mes[4:]}"
            mun = _chave(r.get("nome_municipio") or "")
            if not mun:
                continue   # algumas linhas vêm sem o nome do município
            nomes.setdefault(mun, (r.get("nome_municipio") or "").strip())
            municipios_mes[m].add(mun)
            tipo = (r.get("tipo_cargo") or "").strip()
            cargo = (r.get("descricao_cargo") or "").strip()
            valor = _valor(r.get("valor_vantagem"))
            if tipo == "Eletivos":
                if PREFEITO.search(cargo) and not VICE.search(cargo) and valor > 0:
                    prefeito[mun][m] = max(prefeito[mun].get(m, 0.0), valor)
                continue
            if tipo in FORA or valor <= 0:
                continue
            chave = (mun, r.get("codigo_unidade_gestora"), r.get("matricula"), r.get("cpf_cnpj"))
            p = pessoas.get(chave)
            if p is None:
                p = pessoas[chave] = [mun, bool(CAMARA.search(r.get("descricao_unidade_gestora") or "")), cargo, {}]
            p[3][m] = p[3].get(m, 0.0) + valor
            vinculos[(mun, m)] += 1
    # Os 12 meses mais recentes com a folha (quase) completa.
    meses = sorted(m for m, s in municipios_mes.items() if len(s) >= MINIMO_MUNICIPIOS)[-MESES:]
    return {"meses": meses, "pessoas": pessoas, "prefeito": prefeito, "nomes": nomes, "vinculos": vinculos}


def montar(d: dict) -> dict:
    meses = set(d["meses"])
    ibge = {_chave(e["ente"]): str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "PB"}
    # O teto do STF no mês mais recente; o dos procuradores é 90,25% dele.
    ultimo = max(meses)
    t_stf = teto(int(ultimo[:4]), int(ultimo[5:]))
    t_proc = round(DESEMBARGADOR * t_stf, 2)
    por_mun: dict[str, dict] = {}
    for mun, por_mes in d["prefeito"].items():
        vals = [v for m, v in por_mes.items() if m in meses]
        if vals:
            por_mun[mun] = {"prefeito": round(statistics.median(vals), 2)}
    cargos: dict[str, list[int | float]] = defaultdict(lambda: [0, 0.0])
    total = {"vinculos": 0, "acima": 0, "excesso": 0.0, "procuradores": 0, "camara": 0}
    for mun, camara, cargo, por_mes in d["pessoas"].values():
        vals = [v for m, v in por_mes.items() if m in meses]
        if len(vals) < MINIMO_MESES_PESSOA or mun not in por_mun:
            continue
        o = por_mun[mun]
        tipico = statistics.median(vals)
        proc = bool(PROCURADOR.search(cargo)) and not ASSESSOR.search(cargo)
        limite = t_proc if proc else o["prefeito"]
        if tipico <= limite:
            continue
        exc = (tipico - limite) * len(vals)
        o["acima"] = o.get("acima", 0) + 1
        o["excesso"] = o.get("excesso", 0.0) + exc
        o["camara"] = o.get("camara", 0) + camara
        o["procuradores"] = o.get("procuradores", 0) + proc
        o.setdefault("tipicos", []).append(tipico)
        for nome, rx in CARGOS:
            if rx.search(cargo):
                cargos[nome][0] += 1
                cargos[nome][1] += exc
                break
    saida = {}
    for mun, o in por_mun.items():
        vs = [d["vinculos"].get((mun, m), 0) for m in sorted(meses)]
        vinc = round(statistics.median(vs)) if vs else 0
        acima = o.get("acima", 0)
        mostra = acima >= 5
        saida[ibge.get(mun, mun)] = {
            "nome": d["nomes"].get(mun, mun), "ibge": ibge.get(mun), "prefeito": o["prefeito"], "vinculos": vinc,
            # Menos de 5 acima do teto: só se diz que há "menos de 5", para não apontar ninguém numa cidade pequena.
            "acima": acima if mostra else None, "algum": acima > 0,
            "excesso": round(o.get("excesso", 0.0)) if mostra else None,
            # Os grupos dentro da cidade seguem a mesma regra: abaixo de 5, não aparecem.
            "camara": o.get("camara", 0) if mostra and o.get("camara", 0) >= 5 else None,
            "procuradores": o.get("procuradores", 0) if mostra and o.get("procuradores", 0) >= 5 else None,
            "mediana_acima": round(statistics.median(o["tipicos"])) if mostra else None,
        }
        total["vinculos"] += vinc
        total["acima"] += acima
        total["excesso"] += o.get("excesso", 0.0)
        total["procuradores"] += o.get("procuradores", 0)
        total["camara"] += o.get("camara", 0)
    sem_prefeito = sorted(d["nomes"][m] for m in d["nomes"] if m not in por_mun)
    return {
        "gerado": date.today().isoformat(), "fonte": FONTE, "url": URL_FONTE, "uf": "PB",
        "de": min(meses), "ate": max(meses), "meses": len(meses), "teto_procuradores": t_proc,
        "total": {**total, "excesso": round(total["excesso"]), "municipios": len(por_mun),
                  "municipios_com_acima": sum(1 for o in saida.values() if o["algum"])},
        "cargos": {k: {"acima": n, "excesso": round(x)} for k, (n, x) in sorted(cargos.items(), key=lambda i: -i[1][1]) if n >= 5},
        "sem_prefeito": sem_prefeito,
        "municipios": dict(sorted(saida.items(), key=lambda i: -(i[1]["excesso"] or 0))),
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="supersalarios-municipios", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        if not REFERENCIA.exists():
            raise SystemExit(f"falta {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)}")
        return
    doc = montar(carregar(date.today()))
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    t = doc["total"]
    print(f"PB {doc['de']} a {doc['ate']} ({doc['meses']} meses): {t['acima']} vínculos acima do teto (o prefeito; o desembargador para "
          f"procuradores) num mês típico, em {t['municipios_com_acima']} de {t['municipios']} municípios; R$ {t['excesso'] / 1e6:.1f} mi")
    print(f"  procuradores: {t['procuradores']}; na câmara: {t['camara']}; sem prefeito na folha: {len(doc['sem_prefeito'])}")
    for k, v in doc["cargos"].items():
        print(f"  {k}: {v['acima']} (R$ {v['excesso'] / 1e6:.1f} mi)")
    for cod, o in list(doc["municipios"].items())[:12]:
        if o["acima"]:
            print(f"    {o['nome'][:28]:28s} prefeito R$ {o['prefeito']:>9,.0f}  {o['acima']:4d} de {o['vinculos']:6d}  R$ {o['excesso'] / 1e6:5.1f} mi")
    print(f"gravado em {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
