"""Postos, UPAs e hospitais de cada cidade, e o que o SUS pagou a cada hospital por internações.

    uv run unidades-saude              # internações do último ano fechado (~1,1 GB de arquivos do DATASUS)
    uv run unidades-saude --sem-baixar # só copia pipeline/referencia/unidades-saude.json (publicação)

Duas fontes do Ministério da Saúde:
- CNES (Cadastro Nacional de Estabelecimentos de Saúde, OpenDataSUS, CSV atualizado todo mês): cada
  estabelecimento ativo, com o tipo, a natureza jurídica e o bairro. Daqui saem as unidades da
  prefeitura: natureza jurídica de órgão ou entidade municipal (1031, 1120, 1155, 1244, 1279). A
  "esfera administrativa" do CNES diz quem faz a gestão, não quem é o dono (farmácias e clínicas
  particulares aparecem como municipais), por isso não é usada. Ficam de fora consultórios,
  farmácias e unidades administrativas (secretaria, centrais de regulação e de abastecimento).
- SIH (Sistema de Informações Hospitalares, FTP do DATASUS, um arquivo .dbc por estado e mês): cada
  internação paga pelo SUS, com o hospital (CNES), a cidade do hospital e o valor. Por hospital, no
  ano: quantas internações começaram (AIH do tipo 1, sem as de continuação) e o valor total pago.
  Entram todos os hospitais que atendem pelo SUS na cidade: municipais, estaduais, federais e
  filantrópicos ou particulares conveniados.

O valor do SIH é o que o SUS paga pela tabela por internação; não é o orçamento do hospital, que tem
salários e outros custos pagos por fora (sobretudo nos hospitais públicos).

Cache em data/raw/datasus/cnes/ e data/raw/datasus/sih/. Saída em
site/public/data/indicadores/unidades-saude.json, com cópia em pipeline/referencia/:
    {"fonte", "ano": 2025, "cnes": "2026-11",
     "mun": {ibge: {"unidades": [[CNES, nome, grupo, bairro], ...],
                    "hospitais": [[CNES, nome, quem administra, internações, valor, bairro], ...]}}}
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from . import cidades as c
from .fontes import USER_AGENT

PASTA = c.RAIZ / "data" / "raw" / "datasus"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "unidades-saude.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "unidades-saude.json"
MUNICIPIOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
URL_CNES = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip"
URL_SIH = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RD{uf}{aa}{mm}.dbc"
FONTE = "Ministério da Saúde: CNES (estabelecimentos) e SIH/SUS (internações), pelo DATASUS"

MUNICIPAL = {"1031", "1120", "1155", "1244", "1279"}
# Tipo de unidade do CNES → grupo mostrado na página (os que não estão aqui ficam de fora).
GRUPO = {
    "1": "Posto ou unidade básica", "2": "Posto ou unidade básica", "71": "Posto ou unidade básica", "72": "Posto ou unidade básica",
    "20": "Urgência", "21": "Urgência", "73": "Urgência", "42": "Urgência",
    "5": "Hospital", "7": "Hospital", "15": "Hospital", "62": "Hospital",
    "4": "Especialidades", "36": "Especialidades", "39": "Exames", "70": "Saúde mental (CAPS)", "77": "Atenção domiciliar",
    "50": "Vigilância em saúde", "85": "Vacinação", "74": "Academia da saúde", "78": "Saúde mental (CAPS)", "79": "Especialidades",
}


def quem_administra(natureza: str, gestao: str) -> str:
    """Quem é o dono do hospital; para os não públicos, também quem contrata o serviço pelo SUS.

    Fundações e associações (natureza 3xxx) são "sem fins lucrativos": Santas Casas, mas também
    hospitais universitários mantidos por fundações, como o HC de São Paulo."""
    if natureza in MUNICIPAL:
        return "da prefeitura"
    if natureza in {"1023", "1112", "1147", "1236", "1260"}:
        return "do governo do estado"
    if natureza in {"1015", "1104", "1139", "1252"}:
        return "do governo federal"
    if natureza.startswith("1"):
        return "público"
    dono = "sem fins lucrativos" if natureza.startswith("3") else "particular"
    contrata = {"MUNICIPAL": "pela prefeitura", "ESTADUAL": "pelo estado"}.get(gestao)
    return f"{dono}, contratado {contrata}" if contrata else dono


def baixar(url: str, destino, tentativas: int = 4):
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=600) as resp:
                dados = resp.read()
            tmp = destino.with_name(destino.name + ".tmp")
            tmp.write_bytes(dados)
            tmp.rename(destino)
            return destino
        except Exception as erro:
            if "550" in str(erro) or "404" in str(erro):   # o mês ainda não saiu
                return None
            time.sleep(10 * (t + 1))
    print(f"  {url}: sem resposta", flush=True)
    return None


def cnes() -> tuple[dict, str]:
    """CNES ativos → {CNES: (ibge de 6 dígitos, nome, tipo, natureza jurídica, bairro, gestão)}, e o mês do arquivo."""
    arq = PASTA / "cnes" / "cnes_estabelecimentos_csv.zip"
    if arq.exists() and time.time() - arq.stat().st_mtime > 20 * 86400:
        arq.unlink()   # o arquivo é atualizado todo mês
    baixar(URL_CNES, arq)
    estab = {}
    with zipfile.ZipFile(arq) as z, z.open(z.namelist()[0]) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";"):
            if r["CO_MOTIVO_DESAB"].strip():
                continue
            estab[r["CO_CNES"].strip().zfill(7)] = (r["CO_IBGE"].strip(), " ".join(r["NO_FANTASIA"].split()),
                                                     r["TP_UNIDADE"].strip(), r["CO_NATUREZA_JUR"].strip(), " ".join(r["NO_BAIRRO"].split()),
                                                     r["DS_ESFERA_ADMINISTRATIVA"].strip())
    mes = time.strftime("%Y-%m", time.localtime(arq.stat().st_mtime))
    return estab, mes


def ler_sih(arq) -> dict[str, list]:
    """Um arquivo do SIH → {CNES: [cidade do hospital, internações, valor]}."""
    import datasus_dbc
    import dbfread
    por = defaultdict(lambda: ["", 0, 0.0])
    with tempfile.TemporaryDirectory() as d:
        dbf = os.path.join(d, "rd.dbf")
        datasus_dbc.decompress(str(arq), dbf)
        for r in dbfread.DBF(dbf, encoding="latin-1", load=False):
            h = por[(r["CNES"] or "").strip().zfill(7)]
            h[0] = (r["MUNIC_MOV"] or "").strip()
            h[1] += 1 if str(r["IDENT"]).strip() == "1" else 0
            h[2] += float(r["VAL_TOT"] or 0)
    return por


def sih(ano: int, paralelo: int) -> dict[str, list]:
    aa = str(ano)[2:]
    pedidos = [(uf, f"{m:02d}") for uf in sorted(c.SIGLAS.values()) for m in range(1, 13)]
    def um(p):
        uf, mm = p
        arq = baixar(URL_SIH.format(uf=uf, aa=aa, mm=mm), PASTA / "sih" / f"RD{uf}{aa}{mm}.dbc")
        return ler_sih(arq) if arq else {}
    total = defaultdict(lambda: ["", 0, 0.0])
    with ThreadPoolExecutor(paralelo) as ex:
        for i, parte in enumerate(ex.map(um, pedidos), 1):
            for cnes_, (mun, n, v) in parte.items():
                t = total[cnes_]
                t[0] = mun or t[0]
                t[1] += n
                t[2] += v
            if i % 27 == 0:
                print(f"  SIH {ano}: {i} de {len(pedidos)} arquivos", flush=True)
    return total


def main() -> None:
    p = argparse.ArgumentParser(prog="unidades-saude", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=date.today().year - 1)
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--sem-baixar", action="store_true")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA.exists():
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia da referência)")
        return

    estab, mes = cnes()
    print(f"CNES ({mes}): {len(estab)} estabelecimentos ativos", flush=True)
    seis_para_sete = {str(x["ibge"])[:6]: str(x["ibge"]) for x in json.loads(MUNICIPIOS.read_text(encoding="utf-8"))["cidades"] if len(str(x["ibge"])) == 7}
    mun: dict[str, dict] = defaultdict(lambda: {"unidades": [], "hospitais": []})
    for cod, (ibge6, nome, tipo, natureza, bairro, _) in estab.items():
        ibge = seis_para_sete.get(ibge6)
        if ibge and natureza in MUNICIPAL and tipo in GRUPO:
            mun[ibge]["unidades"].append([cod, nome, GRUPO[tipo], bairro])

    internacoes = sih(args.ano, args.paralelo)
    for cod, (ibge6, n, valor) in internacoes.items():
        ibge = seis_para_sete.get(ibge6)
        if not ibge or n <= 0:
            continue
        e = estab.get(cod)
        nome, natureza, bairro, gestao = (e[1], e[3], e[4], e[5]) if e else (f"Estabelecimento {cod}", "", "", "")
        mun[ibge]["hospitais"].append([cod, nome, quem_administra(natureza, gestao), n, round(valor), bairro])
    for v in mun.values():
        v["unidades"].sort(key=lambda u: (u[2], u[1]))
        v["hospitais"].sort(key=lambda h: -h[3])

    doc = {"fonte": FONTE, "ano": args.ano, "cnes": mes, "mun": dict(sorted(mun.items()))}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    n_h = sum(len(v["hospitais"]) for v in mun.values())
    tot = sum(h[3] for v in mun.values() for h in v["hospitais"])
    val = sum(h[4] for v in mun.values() for h in v["hospitais"])
    print(f"{args.ano}: {sum(len(v['unidades']) for v in mun.values())} unidades da prefeitura; "
          f"{n_h} hospitais com {tot} internações pelo SUS, R$ {val / 1e9:.1f} bi")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({len(texto) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
