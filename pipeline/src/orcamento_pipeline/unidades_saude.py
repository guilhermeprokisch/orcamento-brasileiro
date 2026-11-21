"""Postos, UPAs e hospitais de cada cidade, o que o SUS pagou a cada hospital por internações, os
atendimentos sem internação de cada unidade e o trabalho dos postos (atenção básica).

    uv run unidades-saude                    # último ano fechado (~1,1 GB do SIH e ~28 GB do SIA, lidos em memória)
    uv run unidades-saude --so-atencao-basica # só refaz o SISAB e a cobertura sobre a referência que já existe
    uv run unidades-saude --sem-baixar       # só copia pipeline/referencia/unidades-saude.json (publicação)

Fontes do Ministério da Saúde:
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
- SISAB (Sistema de Informação em Saúde para a Atenção Básica, relatório público de validação, sem login
  nem captcha): o que cada estabelecimento (CNES) registrou no e-SUS APS, por mês e tipo de ficha, só os
  registros aprovados. Por unidade, no ano: atendimentos individuais (consulta com médico, enfermeiro e
  outros profissionais), atendimentos de dentista, procedimentos (medir a pressão, curativo, injeção),
  visitas domiciliares (sobretudo dos agentes comunitários) e atividades coletivas (com as reuniões). Uma planilha por mês e ficha, com o país
  inteiro; só os totais por CNES ficam em data/raw/datasus/sisab/. Ver docs/levantamento-sisab.md.
  Do Relatório de Produção do mesmo SISAB sai, por cidade, quem fez os atendimentos individuais do ano
  (médico, enfermeiro ou outro profissional); ele não desce ao posto e só dá as cidades estado por estado.
  Do relatório de atividade coletiva, também por cidade e estado por estado, saem as atividades em grupo com
  os moradores (educação em saúde, grupos, ações nas escolas, mobilização), as participações nelas e as
  reuniões da equipe, que o relatório de validação (por posto) não separa.
- SI-PNI (doses aplicadas pelo Programa Nacional de Imunizações, microdados da Rede Nacional de Dados em Saúde no
  OpenDataSUS, um .zip de ~1,6 GB por mês): uma linha por dose, com o estabelecimento (CNES) e a cidade. Por
  unidade e por cidade, as doses do ano. O SISAB não serve para vacinas: não as valida e muitas cidades
  (São Paulo, Fortaleza, BH, o Espírito Santo inteiro) lançam direto na rede nacional.
- Cobertura da atenção primária (relatorioaps.saude.gov.br, API aberta): por cidade, em dezembro do ano,
  as equipes (saúde da família e atenção primária), quantas pessoas elas dão conta de acompanhar pela
  conta do Ministério (3.500 por equipe de saúde da família, 2.625 por equipe de 30 horas e 1.750 por
  equipe de 20 horas, mais os cadastrados das equipes ribeirinhas, de rua e prisionais) e a cobertura em %.

O valor do SIH é o que o SUS paga pela tabela por internação; não é o orçamento do hospital, que tem
salários e outros custos pagos por fora (sobretudo nos hospitais públicos).

Cache em data/raw/datasus/cnes/, sih/, sia/ e sisab/. Saída em
site/public/data/indicadores/unidades-saude.json, com cópia em pipeline/referencia/:
    {"fonte", "ano": 2025, "cnes": "2026-11", "cobertura": {"mes": "2025-12", "brasil": 83.2},
     "mun": {ibge: {"unidades": [[CNES, nome, grupo, bairro, atendimentos, exames, cirurgias, valor,
                                  atendimentos individuais, de dentista, procedimentos, visitas, atividades coletivas,
                                 doses de vacina], ...],
                    "hospitais": [[CNES, nome, quem administra, internações, valor, bairro], ...],
                    "cobertura": [cobertura %, população, pessoas que as equipes dão conta, equipes de
                                  saúde da família, de atenção primária, ribeirinhas, de rua ou prisionais],
                    "profissionais": [atendimentos individuais com médico, com enfermeiro, com outros],
                    "coletivas": [atividades coletivas com os moradores, participações nelas, reuniões da equipe],
                    "vacinas": doses de vacina aplicadas na cidade, sem as do serviço privado}},
     "profissionais": [as mesmas contas do Brasil], "coletivas": [idem], "vacinas": [doses no Brasil, população]}
Os quatro primeiros números de cada unidade vêm do SIA; os cinco seguintes, do SISAB; o último, do SI-PNI.
"""

from __future__ import annotations

import argparse
import csv
import html
import http.cookiejar
import io
import json
import os
import re
import struct
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
import zlib
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
URL_SISAB = "https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/envio/RelValidacao.xhtml"
URL_PRODUCAO = "https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/RelSauProducao.xhtml"
URL_COLETIVA = "https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/RelSauAtivColetiva.xhtml"
URL_PNI = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv/vacinacao_{mes}_{ano}_csv.zip"
URL_COBERTURA = "https://relatorioaps-prd.saude.gov.br/cobertura/aps"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
       "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
FONTE = ("Ministério da Saúde: CNES (estabelecimentos), SIH/SUS (internações) e SIA/SUS (atendimentos ambulatoriais), "
         "pelo DATASUS; SISAB (produção dos postos, registros aprovados), SI-PNI (doses de vacina, Rede Nacional de Dados em Saúde) "
         "e Relatórios da APS (cobertura da atenção primária)")
# Fichas do e-SUS APS no relatório de validação do SISAB → posição na lista de cada unidade.
# Atendimento individual, odontológico, procedimentos, visita domiciliar e atividade coletiva. A vacinação (ficha
# 14) fica de fora: o SISAB não a valida e muitas cidades (São Paulo, Fortaleza, BH, o Espírito Santo inteiro)
# lançam as vacinas direto na Rede Nacional de Dados em Saúde, sem nada no SISAB. Ver docs/levantamento-sisab.md.
FICHAS_SISAB = {"4": 0, "5": 1, "7": 2, "8": 3, "6": 4}

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


def ler_planilha(dados: bytes) -> list[list[str]]:
    """O .xlsx do SISAB (texto em células inlineStr, uma aba) → linhas de texto."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    return [[html.unescape(t) for t in re.findall(r"<t[^>]*>([^<]*)</t>", linha)]
            for linha in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S)]


def sisab_mes(competencia: str, ficha: str) -> dict[str, int]:
    """Registros aprovados de uma ficha num mês, por CNES, do relatório público de validação do SISAB.

    É uma página JSF: abre a página (cookie da sessão e ViewState), depois manda o formulário pedindo a
    planilha do Brasil inteiro com as colunas IBGE, CNES e tipo de unidade, só os aprovados, pela data da
    produção (não do envio)."""
    cache = PASTA / "sisab" / f"{competencia}-{ficha}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for t in range(4):
        try:
            abre = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            abre.addheaders = [("User-Agent", USER_AGENT)]
            with abre.open(URL_SISAB, timeout=120) as resp:
                pagina = resp.read().decode("utf-8", "replace")
            estado = re.search(r'id="javax.faces.ViewState" value="([^"]+)"', pagina).group(1)
            campos = [("j_idt44", "j_idt44"), ("unidGeo", "brasil"), ("periodo", "producao"), ("j_idt70", competencia),
                      ("colunas", "ibge"), ("colunas", "cnes"), ("colunas", "tp_unidade"), ("j_idt77", "1%"),
                      ("j_idt87", ficha), ("j_idt99", "j_idt99"), ("javax.faces.ViewState", estado)]
            with abre.open(URL_SISAB, urllib.parse.urlencode(campos).encode(), timeout=900) as resp:
                dados = resp.read()
            if dados[:2] != b"PK":
                raise ValueError("o SISAB não devolveu a planilha")
            break
        except Exception as erro:
            if t == 3:
                print(f"  SISAB {competencia} ficha {ficha}: {erro}", flush=True)
                return {}
            time.sleep(20 * (t + 1))
    linhas = ler_planilha(dados)
    cab = next(i for i, l in enumerate(linhas) if l[:2] == ["IBGE", "CNES"])
    if linhas[cab][-1] != "Total" or not any(f"Produção: {competencia[4:]}/{competencia[:4]}" in " ".join(l) for l in linhas[:cab]):
        raise ValueError(f"SISAB {competencia} ficha {ficha}: planilha em formato inesperado")
    por: dict[str, int] = defaultdict(int)
    for l in linhas[cab + 1:]:
        if len(l) >= 5 and l[1].isdigit():
            por[l[1].zfill(7)] += int(l[-1].replace(".", ""))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(por, separators=(",", ":")))
    return por


def sisab(ano: int, paralelo: int) -> dict[str, list[int]]:
    """Soma o ano: {CNES: [atendimentos individuais, de dentista, procedimentos, visitas domiciliares,
    atividades coletivas]}."""
    pedidos = [(f"{ano}{m:02d}", f) for m in range(1, 13) for f in FICHAS_SISAB]
    total: dict[str, list[int]] = defaultdict(lambda: [0] * len(FICHAS_SISAB))
    faltam = []
    with ThreadPoolExecutor(paralelo) as ex:
        for (comp, ficha), parte in zip(pedidos, ex.map(lambda p: sisab_mes(*p), pedidos)):
            if not parte:
                faltam.append(f"{comp}/{ficha}")
            for cod, n in parte.items():
                total[cod][FICHAS_SISAB[ficha]] += n
    if faltam:
        raise SystemExit(f"SISAB {ano}: sem resposta para {', '.join(faltam)}; rode de novo (o que já veio fica no cache)")
    print(f"  SISAB {ano}: {len(total)} estabelecimentos; " + ", ".join(
        f"{nome} {sum(v[i] for v in total.values()) / 1e6:.0f} mi" for i, nome in
        enumerate(["atendimentos", "de dentista", "procedimentos", "visitas", "atividades coletivas"])), flush=True)
    return total


def csv_do_estado(url: str, uf: str, montar, rotulo: str) -> list[list[str]] | None:
    """Pede um .csv a um relatório JSF do SISAB com um estado escolhido; devolve as linhas ou None.

    Esses relatórios só dão a linha por cidade com o estado escolhido. Escolher "Estado" na página é um
    pedido AJAX do JSF que traz a lista de estados (sem ele o campo `estados` não é aceito); depois vai o
    formulário montado por `montar(pagina, viewstate)`, que diz o resto (meses, linhas, colunas, botão)."""
    for t in range(4):
        try:
            abre = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            abre.addheaders = [("User-Agent", USER_AGENT)]
            with abre.open(url, timeout=120) as resp:
                pagina = resp.read().decode("utf-8", "replace")
            estado = re.search(r'id="javax.faces.ViewState" value="([^"]+)"', pagina).group(1)
            ajax = [("j_idt44", "j_idt44"), ("unidGeo", "estado"), ("javax.faces.source", "unidGeo"),
                    ("javax.faces.partial.event", "change"), ("javax.faces.partial.execute", "unidGeo unidGeo"),
                    ("javax.faces.partial.render", "regioes script"), ("javax.faces.behavior.event", "valueChange"),
                    ("javax.faces.partial.ajax", "true"), ("javax.faces.ViewState", estado)]
            req = urllib.request.Request(url, urllib.parse.urlencode(ajax).encode(), headers={"Faces-Request": "partial/ajax"})
            with abre.open(req, timeout=120) as resp:
                resp.read()
            campos = [("j_idt44", "j_idt44"), ("unidGeo", "estado"), ("estados", uf)] + montar(pagina, estado)
            with abre.open(url, urllib.parse.urlencode(campos).encode(), timeout=900) as resp:
                tipo, dados = resp.headers.get("Content-Type", ""), resp.read()
            if "csv" not in tipo:
                raise ValueError("o SISAB não devolveu o .csv")
            return list(csv.reader(io.StringIO(dados.decode("latin-1")), delimiter=";"))
        except Exception as erro:
            if t == 3:
                print(f"  SISAB {rotulo} {uf}: {erro}", flush=True)
                return None
            time.sleep(20 * (t + 1))
    return None


def opcoes(pagina: str, campo: str) -> list[str]:
    """Os valores de um <select> da página (para marcar todas as opções)."""
    return re.findall(r'<option value="(\d+)"', re.search(rf'name="{campo}"[^>]*>(.*?)</select>', pagina, re.S).group(1))


def numero(x: str) -> int:
    x = x.replace(".", "").strip()
    return int(x) if x.isdigit() else 0


def conferir(linhas: list[list[str]], inicio: list[str], uf: str, ano: int, exige: list[str], rotulo: str) -> int:
    """Acha o cabeçalho da tabela no .csv e confere nos filtros o estado, o ano inteiro e o que mais se pediu."""
    cab = next((i for i, l in enumerate(linhas) if l[:len(inicio)] == inicio), None)
    filtros = " ".join(" ".join(l) for l in linhas[:cab or 0])
    if cab is None or f"Estado: {uf}." not in filtros or f"JAN/{ano}" not in filtros or f"DEZ/{ano}" not in filtros \
            or any(e not in filtros and e not in linhas[cab] for e in exige):
        raise ValueError(f"SISAB {rotulo} {ano} {uf}: .csv em formato inesperado")
    return cab


def profissionais_estado(ano: int, uf: str) -> dict[str, list[int]]:
    """Atendimentos individuais do ano em cada cidade do estado, por categoria do profissional, do Relatório
    de Produção do SISAB: {ibge de 6 dígitos: [com médico, com enfermeiro, com outros profissionais]}.
    O .csv traz as cidades nas linhas e as 26 categorias de profissional nas colunas, nos 12 meses do ano."""
    cache = PASTA / "sisab" / f"profissionais-{ano}-{uf}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    montar = lambda pagina, estado: (
        [("lsCid", ""), ("lsSigtap", "")] + [("j_idt76", f"{ano}{m:02d}") for m in range(1, 13)]
        + [("categoriaProfissional", k) for k in opcoes(pagina, "categoriaProfissional")]
        + [("selectLinha", "MUN.CO_MUNICIPIO_IBGE"), ("selectcoluna", "CO_CATEGORIA_PROFISSIONAL"), ("idadeInicio", "0"),
           ("idadeFim", "0"), ("tpProducao", "4"), ("j_idt192", "j_idt192"), ("javax.faces.ViewState", estado)])
    linhas = csv_do_estado(URL_PRODUCAO, uf, montar, f"profissionais {ano}")
    if linhas is None:
        return {}
    cab = conferir(linhas, ["Uf", "Ibge", "Municipio"], uf, ano, ["Médico", "Enfermeiro", "Atendimento Individual"], "profissionais")
    nomes = linhas[cab]
    med, enf = nomes.index("Médico"), nomes.index("Enfermeiro")
    por = {}
    for l in linhas[cab + 1:]:
        if len(l) > enf and l[0] == uf and l[1].isdigit():
            total = sum(numero(x) for x in l[3:len(nomes)])
            m, e = numero(l[med]), numero(l[enf])
            por[l[1]] = [m, e, total - m - e]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(por, separators=(",", ":")))
    return por


# Tipos de atividade coletiva do SISAB: as três primeiras são reuniões da equipe; as outras, com os moradores.
REUNIOES = ("Reunião de equipe", "Reunião com outras equipes", "Reunião intersetorial")


def coletivas_estado(ano: int, uf: str) -> dict[str, list[int]]:
    """Atividades coletivas do ano em cada cidade do estado, do relatório de atividade coletiva do SISAB:
    {ibge de 6 dígitos: [atividades com os moradores, participantes delas, reuniões da equipe]}.
    Dois .csv por estado (quantidade de atividades e número de participantes), com os 7 tipos nas colunas."""
    cache = PASTA / "sisab" / f"coletivas-{ano}-{uf}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    por: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for medida, rotulo in (("qtac", "Quantidade de Atividade Coletiva"), ("ndp", "Número de participantes")):
        montar = lambda pagina, estado, medida=medida: (
            [("lsSigtap", "")] + [("j_idt72", f"{ano}{m:02d}") for m in range(1, 13)]
            + [("tipoAtividade", k) for k in opcoes(pagina, "tipoAtividade")]
            + [("selectLinha", "MUN.CO_MUNICIPIO_IBGE"), ("selectcoluna", "tpat"), ("j_idt83", medida),
               ("j_idt134", "j_idt134"), ("javax.faces.ViewState", estado)])
        linhas = csv_do_estado(URL_COLETIVA, uf, montar, f"atividades coletivas {ano}")
        if linhas is None:
            return {}
        cab = conferir(linhas, ["Uf", "Ibge", "Municipio"], uf, ano, [rotulo, "Educacao em saúde"], "atividades coletivas")
        nomes = linhas[cab]
        reuniao = [i for i, n in enumerate(nomes) if n.startswith(REUNIOES)]
        if len(reuniao) != 3 or len([n for n in nomes[3:] if n]) != 7:
            raise ValueError(f"SISAB atividades coletivas {ano} {uf}: colunas inesperadas {nomes}")
        for l in linhas[cab + 1:]:
            if len(l) >= len(nomes) - 1 and l[0] == uf and l[1].isdigit():
                valores = {i: numero(l[i]) for i in range(3, len(nomes)) if nomes[i]}
                fora = sum(v for i, v in valores.items() if i not in reuniao)
                if medida == "qtac":
                    por[l[1]][0] += fora
                    por[l[1]][2] += sum(valores[i] for i in reuniao)
                else:
                    por[l[1]][1] += fora
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(por, separators=(",", ":")))
    return dict(por)


def por_estado(ano: int, paralelo: int, funcao, nome: str, partes: list[str]) -> dict[str, list[int]]:
    """Junta os 27 estados de um relatório por cidade e imprime as somas do Brasil."""
    total: dict[str, list[int]] = {}
    faltam = []
    with ThreadPoolExecutor(paralelo) as ex:
        for uf, parte in zip(UFS, ex.map(lambda uf: funcao(ano, uf), UFS)):
            if not parte:
                faltam.append(uf)
            total.update(parte)
    if faltam:
        raise SystemExit(f"SISAB {nome} {ano}: sem resposta para {', '.join(faltam)}; rode de novo (o que já veio fica no cache)")
    print(f"  SISAB {ano}, {nome}: {len(total)} cidades; " + ", ".join(
        f"{p} {sum(v[i] for v in total.values()) / 1e6:.1f} mi" for i, p in enumerate(partes)), flush=True)
    return total


MESES_PNI = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def pni_mes(ano: int, mes: int) -> dict[str, dict[str, int]]:
    """Doses de vacina aplicadas num mês (SI-PNI, microdados da Rede Nacional de Dados em Saúde no OpenDataSUS):
    {"cnes": {CNES: doses}, "mun": {ibge de 6 dígitos: doses sem as do serviço privado}}.

    Cada mês é um .zip de 1,5 a 1,8 GB com um .csv de uma linha por dose. O .zip não vai para o disco: é lido
    enquanto baixa, descompactando o deflate na hora (o cabeçalho local do zip diz onde os dados começam), e só
    o total por estabelecimento e por cidade fica no cache. Ficam de fora os registros apagados e os que não
    estão na situação "final"."""
    cache = PASTA / "pni" / f"{ano}{mes:02d}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = URL_PNI.format(mes=MESES_PNI[mes - 1], ano=ano)
    for t in range(4):
        try:
            por_cnes: dict[bytes, int] = defaultdict(int)
            por_mun: dict[bytes, int] = defaultdict(int)
            linhas_ruins = 0
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300) as resp:
                cab = resp.read(30)
                if cab[:4] != b"PK\x03\x04" or struct.unpack("<H", cab[8:10])[0] != 8:
                    raise ValueError("o .zip não começa com um arquivo comprimido em deflate")
                nome, extra = struct.unpack("<HH", cab[26:30])
                resp.read(nome + extra)
                z = zlib.decompressobj(-15)
                resto, colunas = b"", None
                while not z.eof:
                    bloco = resp.read(1 << 20)
                    if not bloco:
                        raise ValueError("o .zip acabou antes do fim do .csv")
                    partes = (resto + z.decompress(bloco)).split(b"\n")
                    resto = partes.pop()
                    if colunas is None:
                        colunas = partes.pop(0).decode("latin-1").strip().split(";")
                        i_cnes, i_mun = colunas.index("co_cnes_estabelecimento"), colunas.index("co_municipio_estabelecimento")
                        i_st, i_del, i_estr = colunas.index("st_documento"), colunas.index("dt_deletado_rnds"), colunas.index("no_estrategia")
                    for l in partes:
                        c = l.split(b";")
                        if len(c) != len(colunas):
                            linhas_ruins += 1
                            continue
                        if c[i_st] != b"final" or c[i_del].strip():
                            continue
                        por_cnes[c[i_cnes]] += 1
                        if c[i_estr] != b"Servi\xe7o Privado":
                            por_mun[c[i_mun]] += 1
            break
        except Exception as erro:
            if t == 3:
                print(f"  SI-PNI {ano}-{mes:02d}: {erro}", flush=True)
                return {}
            time.sleep(30 * (t + 1))
    total = sum(por_cnes.values())
    if total < 1_000_000 or linhas_ruins > total / 1000:
        raise SystemExit(f"SI-PNI {ano}-{mes:02d}: {total} doses e {linhas_ruins} linhas fora do formato; confira o arquivo")
    doc = {"cnes": {k.decode().zfill(7): v for k, v in por_cnes.items() if k.strip()},
           "mun": {k.decode(): v for k, v in por_mun.items() if k.strip()}, "ruins": linhas_ruins}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"  SI-PNI {ano}-{mes:02d}: {total / 1e6:.1f} mi doses", flush=True)
    return doc


def pni(ano: int, paralelo: int) -> tuple[dict[str, int], dict[str, int]]:
    """Soma o ano: doses por estabelecimento (CNES) e por cidade (sem o serviço privado)."""
    por_cnes: dict[str, int] = defaultdict(int)
    por_mun: dict[str, int] = defaultdict(int)
    faltam = []
    with ProcessPoolExecutor(paralelo) as ex:
        for mes, parte in zip(range(1, 13), ex.map(pni_mes, [ano] * 12, range(1, 13))):
            if not parte:
                faltam.append(f"{mes:02d}")
                continue
            for k, v in parte["cnes"].items():
                por_cnes[k] += v
            for k, v in parte["mun"].items():
                por_mun[k] += v
    if faltam:
        raise SystemExit(f"SI-PNI {ano}: sem resposta para os meses {', '.join(faltam)}; rode de novo (o que já veio fica no cache)")
    print(f"  SI-PNI {ano}: {sum(por_cnes.values()) / 1e6:.0f} mi doses em {len(por_cnes)} estabelecimentos", flush=True)
    return por_cnes, por_mun


def cobertura(ano: int) -> tuple[dict[str, list], float]:
    """Cobertura da atenção primária em dezembro do ano, por cidade (ibge de 6 dígitos), e a do Brasil."""
    cache = PASTA / "sisab" / f"cobertura-{ano}12.json"
    if not cache.exists():
        url = f"{URL_COBERTURA}?unidadeGeografica=MUNICIPIO&nuCompInicio={ano}12&nuCompFim={ano}12"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            dados = json.loads(resp.read())
        if len(dados) < 5000:
            raise SystemExit(f"cobertura {ano}12: só {len(dados)} cidades")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
    dados = json.loads(cache.read_text())
    por = {}
    for x in dados:
        pop, cap = int(x["qtPopulacao"] or 0), int(x["qtCapacidadeEquipe"] or 0)
        por[x["coMunicipioIbge"]] = [round(min(100.0, float(x["qtCobertura"] or 0)), 1), pop, min(cap, pop),
                                     int(x["qtEsf"] or 0), int(x["qtEap30"] or 0) + int(x["qtEap20"] or 0),
                                     sum(int(x[k] or 0) for k in ("qtEsfr", "qtEcr", "qtEapp20", "qtEapp30"))]
    pop = sum(v[1] for v in por.values())
    return por, round(100 * sum(v[2] for v in por.values()) / pop, 1) if pop else 0.0


def juntar_atencao_basica(doc: dict, paralelo: int, paralelo_pni: int) -> None:
    """Põe a produção do SISAB e as doses de vacina (SI-PNI) em cada unidade (pelo CNES) e a cobertura, quem
    atendeu, as atividades coletivas e as doses aplicadas em cada cidade."""
    ano = doc["ano"]
    producao = sisab(ano, paralelo)
    por_cidade, brasil = cobertura(ano)
    por_profissional = por_estado(ano, paralelo, profissionais_estado, "atendimentos por profissional", ["médico", "enfermeiro", "outros"])
    por_coletiva = por_estado(ano, paralelo, coletivas_estado, "atividades coletivas", ["com moradores", "participantes", "reuniões"])
    doses_cnes, doses_mun = pni(ano, paralelo_pni)
    for ibge, v in doc["mun"].items():
        for u in v["unidades"]:
            u[:] = u[:8] + [0] * (8 - len(u)) + producao.get(u[0], [0] * len(FICHAS_SISAB)) + [doses_cnes.get(u[0], 0)]
        if doses_mun.get(ibge[:6], 0) > 0:
            v["vacinas"] = doses_mun[ibge[:6]]
        if ibge[:6] in por_cidade:
            v["cobertura"] = por_cidade[ibge[:6]]
        if sum(por_profissional.get(ibge[:6], [])) > 0:
            v["profissionais"] = por_profissional[ibge[:6]]
        if sum(por_coletiva.get(ibge[:6], [])) > 0:
            v["coletivas"] = por_coletiva[ibge[:6]]
    doc["cobertura"] = {"mes": f"{ano}-12", "brasil": brasil}
    doc["profissionais"] = [sum(v[i] for v in por_profissional.values()) for i in range(3)]
    doc["coletivas"] = [sum(v[i] for v in por_coletiva.values()) for i in range(3)]
    doc["vacinas"] = [sum(doses_mun.values()), sum(v[1] for v in por_cidade.values())]   # doses no Brasil e população
    doc["fonte"] = FONTE
    com = [u for v in doc["mun"].values() for u in v["unidades"] if sum(u[8:]) > 0]
    print(f"SISAB {ano}: {len(com)} unidades da prefeitura com produção; "
          f"{sum(u[8] for u in com) / 1e6:.0f} mi atendimentos, {sum(u[11] for u in com) / 1e6:.0f} mi visitas; "
          f"cobertura da atenção primária no Brasil {brasil}%", flush=True)


def gravar(doc: dict) -> str:
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return texto


def main() -> None:
    p = argparse.ArgumentParser(prog="unidades-saude", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=date.today().year - 1)
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--paralelo-sia", type=int, default=2, help="arquivos do SIA abertos ao mesmo tempo (cada um usa até ~3 GB de memória)")
    p.add_argument("--paralelo-sisab", type=int, default=3, help="planilhas do SISAB pedidas ao mesmo tempo")
    p.add_argument("--paralelo-pni", type=int, default=4, help="meses do SI-PNI (vacinas, ~1,6 GB cada, lidos enquanto baixam) ao mesmo tempo")
    p.add_argument("--sem-baixar", action="store_true")
    p.add_argument("--so-atencao-basica", action="store_true", help="refaz só o SISAB e a cobertura, sobre a referência")
    args = p.parse_args()
    if args.sem_baixar:
        if REFERENCIA.exists():
            SAIDA.parent.mkdir(parents=True, exist_ok=True)
            SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia da referência)")
        return
    if args.so_atencao_basica:
        doc = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        juntar_atencao_basica(doc, args.paralelo_sisab, args.paralelo_pni)
        texto = gravar(doc)
        print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({len(texto) / 1e6:.1f} MB)")
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
    juntar_atencao_basica(doc, args.paralelo_sisab, args.paralelo_pni)
    texto = gravar(doc)
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
