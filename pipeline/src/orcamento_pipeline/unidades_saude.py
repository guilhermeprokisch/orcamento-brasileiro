"""Postos, UPAs e hospitais de cada cidade, o que o SUS pagou a cada hospital por internações e os
atendimentos sem internação de cada unidade.

    uv run unidades-saude              # último ano fechado (~1,1 GB do SIH e ~28 GB do SIA, lidos em memória)
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
- SIA (Sistema de Informações Ambulatoriais, FTP do DATASUS, um .dbc por estado e mês, os estados grandes
  em partes a, b, c…): cada procedimento ambulatorial aprovado, com a unidade (CNES), o procedimento e o
  valor. Por unidade, no ano: atendimentos (grupo 03 da tabela SIGTAP: consultas, sessões, urgência),
  exames (grupo 02), cirurgias sem internação (grupo 04) e o valor aprovado de todos os grupos. Os
  arquivos (~28 GB por ano) não ficam no disco: cada um é baixado e aberto na memória, e só o total por
  unidade é guardado em data/raw/datasus/sia/. Postos e unidades básicas quase não aparecem: o SUS os
  paga pelo número de moradores, e as consultas deles vão para outro sistema (e-SUS APS/SISAB).

O valor do SIH é o que o SUS paga pela tabela por internação; não é o orçamento do hospital, que tem
salários e outros custos pagos por fora (sobretudo nos hospitais públicos).

Cache em data/raw/datasus/cnes/, data/raw/datasus/sih/ e data/raw/datasus/sia/. Saída em
site/public/data/indicadores/unidades-saude.json, com cópia em pipeline/referencia/:
    {"fonte", "ano": 2025, "cnes": "2026-11",
     "mun": {ibge: {"unidades": [[CNES, nome, grupo, bairro, atendimentos, exames, cirurgias, valor], ...],
                    "hospitais": [[CNES, nome, quem administra, internações, valor, bairro], ...]}}}
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import struct
import tempfile
import time
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date

from . import cidades as c
from .fontes import USER_AGENT

PASTA = c.RAIZ / "data" / "raw" / "datasus"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "unidades-saude.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "unidades-saude.json"
MUNICIPIOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
URL_CNES = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip"
URL_SIH = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RD{uf}{aa}{mm}.dbc"
PASTA_SIA = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/"
FONTE = "Ministério da Saúde: CNES (estabelecimentos), SIH/SUS (internações) e SIA/SUS (atendimentos ambulatoriais), pelo DATASUS"

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


def ler_sia(nome: str) -> dict[str, list]:
    """Um arquivo do SIA, baixado e aberto na memória → {CNES: [atendimentos, exames, cirurgias, valor]}.

    O .dbf tem registros de tamanho fixo: lê só as quatro colunas, sem passar pelo dbfread (dez vezes mais rápido)."""
    import datasus_dbc
    cache = PASTA / "sia" / f"{nome.removesuffix('.dbc')}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for t in range(4):
        try:
            req = urllib.request.Request(PASTA_SIA + nome, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=900) as resp:
                dbc = resp.read()
            break
        except Exception:
            time.sleep(15 * (t + 1))
    else:
        print(f"  {nome}: sem resposta", flush=True)
        return {}
    dbf = datasus_dbc.decompress_bytes(dbc)
    del dbc
    n, hl, rl = struct.unpack("<IHH", dbf[4:12])
    campos, off, i = {}, 1, 32
    while dbf[i] != 0x0D:
        campos[dbf[i:i + 11].split(b"\0")[0].decode()] = (off, off + dbf[i + 16])
        off += dbf[i + 16]
        i += 32
    (u0, u1), (p0, _), (q0, q1), (v0, v1) = (campos[c] for c in ("PA_CODUNI", "PA_PROC_ID", "PA_QTDAPR", "PA_VALAPR"))
    por: dict[bytes, list] = defaultdict(lambda: [0, 0, 0, 0.0])
    coluna = {b"03": 0, b"02": 1, b"04": 2}
    vista = memoryview(dbf)
    for k in range(hl, hl + n * rl, rl):
        r = vista[k:k + rl]
        if r[0] == 42:   # registro apagado
            continue
        x = por[bytes(r[u0:u1])]
        g = coluna.get(bytes(r[p0:p0 + 2]))
        if g is not None:
            x[g] += int(float(bytes(r[q0:q1]) or 0))
        x[3] += float(bytes(r[v0:v1]) or 0)
    res = {c.decode().strip().zfill(7): [a, e, ci, round(v, 2)] for c, (a, e, ci, v) in por.items()}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(res, separators=(",", ":")))
    return res


def sia(ano: int, paralelo: int) -> dict[str, list]:
    """Soma os arquivos do SIA do ano, em processos separados (cada um abre um arquivo de até ~3 GB na memória)."""
    aa = str(ano)[2:]
    req = urllib.request.Request(PASTA_SIA, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        lista = [linha.split()[-1] for linha in resp.read().decode("latin-1").splitlines() if linha.strip()]
    nomes = sorted(x for x in lista if re.fullmatch(rf"PA[A-Z]{{2}}{aa}\d{{2}}[a-z]?\.dbc", x))
    total: dict[str, list] = defaultdict(lambda: [0, 0, 0, 0.0])
    with ProcessPoolExecutor(paralelo) as ex:
        for i, parte in enumerate(ex.map(ler_sia, nomes), 1):
            for cod, (a, e, ci, v) in parte.items():
                t = total[cod]
                t[0] += a; t[1] += e; t[2] += ci; t[3] += v
            if i % 20 == 0 or i == len(nomes):
                print(f"  SIA {ano}: {i} de {len(nomes)} arquivos", flush=True)
    return total


def main() -> None:
    p = argparse.ArgumentParser(prog="unidades-saude", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=date.today().year - 1)
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--paralelo-sia", type=int, default=2, help="arquivos do SIA abertos ao mesmo tempo (cada um usa até ~3 GB de memória)")
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

    ambulatorio = sia(args.ano, args.paralelo_sia)
    for v in mun.values():
        for u in v["unidades"]:
            a, e, ci, val = ambulatorio.get(u[0], (0, 0, 0, 0))
            u.extend([a, e, ci, round(val)])

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
    com = [u for v in mun.values() for u in v["unidades"] if u[7] > 0]
    print(f"SIA {args.ano}: {len(com)} unidades da prefeitura com atendimentos, R$ {sum(u[7] for u in com) / 1e9:.1f} bi pela tabela")
    print(f"{args.ano}: {sum(len(v['unidades']) for v in mun.values())} unidades da prefeitura; "
          f"{n_h} hospitais com {tot} internações pelo SUS, R$ {val / 1e9:.1f} bi")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({len(texto) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
