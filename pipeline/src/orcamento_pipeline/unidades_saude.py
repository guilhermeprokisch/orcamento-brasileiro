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
  outros profissionais), atendimentos de dentista, procedimentos (medir a pressão, curativo, injeção) e
  visitas domiciliares (sobretudo dos agentes comunitários). Uma planilha por mês e ficha, com o país
  inteiro; só os totais por CNES ficam em data/raw/datasus/sisab/. Ver docs/levantamento-sisab.md.
  Do Relatório de Produção do mesmo SISAB sai, por cidade, quem fez os atendimentos individuais do ano
  (médico, enfermeiro ou outro profissional); ele não desce ao posto e só dá as cidades estado por estado.
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
                                  atendimentos individuais, de dentista, procedimentos, visitas], ...],
                    "hospitais": [[CNES, nome, quem administra, internações, valor, bairro], ...],
                    "cobertura": [cobertura %, população, pessoas que as equipes dão conta, equipes de
                                  saúde da família, de atenção primária, ribeirinhas, de rua ou prisionais],
                    "profissionais": [atendimentos individuais com médico, com enfermeiro, com outros]}},
     "profissionais": [as mesmas contas do Brasil]}
Os quatro primeiros números de cada unidade vêm do SIA; os quatro últimos, do SISAB.
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
URL_COBERTURA = "https://relatorioaps-prd.saude.gov.br/cobertura/aps"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
       "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
FONTE = ("Ministério da Saúde: CNES (estabelecimentos), SIH/SUS (internações) e SIA/SUS (atendimentos ambulatoriais), "
         "pelo DATASUS; SISAB (produção dos postos, registros aprovados) e Relatórios da APS (cobertura da atenção primária)")
# Fichas do e-SUS APS no relatório de validação do SISAB → posição na lista de cada unidade.
FICHAS_SISAB = {"4": 0, "5": 1, "7": 2, "8": 3}   # atendimento individual, odontológico, procedimentos, visita domiciliar

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
    """Soma o ano: {CNES: [atendimentos individuais, de dentista, procedimentos, visitas domiciliares]}."""
    pedidos = [(f"{ano}{m:02d}", f) for m in range(1, 13) for f in FICHAS_SISAB]
    total: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
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
        enumerate(["atendimentos", "de dentista", "procedimentos", "visitas"])), flush=True)
    return total


def profissionais_estado(ano: int, uf: str) -> dict[str, list[int]]:
    """Atendimentos individuais do ano em cada cidade do estado, por categoria do profissional, do Relatório
    de Produção do SISAB: {ibge de 6 dígitos: [com médico, com enfermeiro, com outros profissionais]}.

    O relatório só dá a linha por cidade com o estado escolhido. Escolher "Estado" na página é um pedido
    AJAX do JSF que traz a lista de estados; depois o formulário pede o .csv com as cidades nas linhas e as
    26 categorias de profissional nas colunas, nos 12 meses do ano."""
    cache = PASTA / "sisab" / f"profissionais-{ano}-{uf}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for t in range(4):
        try:
            abre = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            abre.addheaders = [("User-Agent", USER_AGENT)]
            with abre.open(URL_PRODUCAO, timeout=120) as resp:
                pagina = resp.read().decode("utf-8", "replace")
            estado = re.search(r'id="javax.faces.ViewState" value="([^"]+)"', pagina).group(1)
            categorias = re.findall(r'<option value="(\d+)"', re.search(
                r'name="categoriaProfissional"[^>]*>(.*?)</select>', pagina, re.S).group(1))
            ajax = [("j_idt44", "j_idt44"), ("unidGeo", "estado"), ("javax.faces.source", "unidGeo"),
                    ("javax.faces.partial.event", "change"), ("javax.faces.partial.execute", "unidGeo unidGeo"),
                    ("javax.faces.partial.render", "regioes script"), ("javax.faces.behavior.event", "valueChange"),
                    ("javax.faces.partial.ajax", "true"), ("javax.faces.ViewState", estado)]
            req = urllib.request.Request(URL_PRODUCAO, urllib.parse.urlencode(ajax).encode(), headers={"Faces-Request": "partial/ajax"})
            with abre.open(req, timeout=120) as resp:
                resp.read()
            campos = ([("j_idt44", "j_idt44"), ("lsCid", ""), ("lsSigtap", ""), ("unidGeo", "estado"), ("estados", uf)]
                      + [("j_idt76", f"{ano}{m:02d}") for m in range(1, 13)]
                      + [("categoriaProfissional", k) for k in categorias]
                      + [("selectLinha", "MUN.CO_MUNICIPIO_IBGE"), ("selectcoluna", "CO_CATEGORIA_PROFISSIONAL"),
                         ("idadeInicio", "0"), ("idadeFim", "0"), ("tpProducao", "4"), ("j_idt192", "j_idt192"),
                         ("javax.faces.ViewState", estado)])
            with abre.open(URL_PRODUCAO, urllib.parse.urlencode(campos).encode(), timeout=900) as resp:
                tipo, dados = resp.headers.get("Content-Type", ""), resp.read()
            if "csv" not in tipo:
                raise ValueError("o SISAB não devolveu o .csv")
            break
        except Exception as erro:
            if t == 3:
                print(f"  SISAB profissionais {ano} {uf}: {erro}", flush=True)
                return {}
            time.sleep(20 * (t + 1))
    linhas = list(csv.reader(io.StringIO(dados.decode("latin-1")), delimiter=";"))
    cab = next(i for i, l in enumerate(linhas) if l[:3] == ["Uf", "Ibge", "Municipio"])
    nomes = linhas[cab]
    filtros = " ".join(" ".join(l) for l in linhas[:cab])
    if ("Médico" not in nomes or "Enfermeiro" not in nomes or f"Estado: {uf}." not in filtros
            or "Atendimento Individual" not in filtros or f"DEZ/{ano}" not in filtros or f"JAN/{ano}" not in filtros):
        raise ValueError(f"SISAB profissionais {ano} {uf}: .csv em formato inesperado")
    med, enf = nomes.index("Médico"), nomes.index("Enfermeiro")
    por = {}
    for l in linhas[cab + 1:]:
        if len(l) > enf and l[0] == uf and l[1].isdigit():
            n = [int(x.replace(".", "") or 0) for x in l[3:len(nomes)] if x.replace(".", "").isdigit()]
            m, e = int(l[med].replace(".", "")), int(l[enf].replace(".", ""))
            por[l[1]] = [m, e, sum(n) - m - e]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(por, separators=(",", ":")))
    return por


def profissionais(ano: int, paralelo: int) -> dict[str, list[int]]:
    """Junta os 27 estados: {ibge de 6 dígitos: [atendimentos com médico, com enfermeiro, com outros]}."""
    total: dict[str, list[int]] = {}
    faltam = []
    with ThreadPoolExecutor(paralelo) as ex:
        for uf, parte in zip(UFS, ex.map(lambda uf: profissionais_estado(ano, uf), UFS)):
            if not parte:
                faltam.append(uf)
            total.update(parte)
    if faltam:
        raise SystemExit(f"SISAB profissionais {ano}: sem resposta para {', '.join(faltam)}; rode de novo (o que já veio fica no cache)")
    soma = [sum(v[i] for v in total.values()) for i in range(3)]
    print(f"  SISAB {ano}, atendimentos por profissional: {len(total)} cidades; médico {soma[0] / 1e6:.0f} mi, "
          f"enfermeiro {soma[1] / 1e6:.0f} mi, outros {soma[2] / 1e6:.0f} mi", flush=True)
    return total


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


def juntar_atencao_basica(doc: dict, paralelo: int) -> None:
    """Põe a produção do SISAB em cada unidade (pelo CNES) e a cobertura em cada cidade."""
    ano = doc["ano"]
    producao = sisab(ano, paralelo)
    por_cidade, brasil = cobertura(ano)
    por_profissional = profissionais(ano, paralelo)
    for ibge, v in doc["mun"].items():
        for u in v["unidades"]:
            u[:] = u[:8] + [0] * (8 - len(u)) + producao.get(u[0], [0, 0, 0, 0])
        if ibge[:6] in por_cidade:
            v["cobertura"] = por_cidade[ibge[:6]]
        if sum(por_profissional.get(ibge[:6], [])) > 0:
            v["profissionais"] = por_profissional[ibge[:6]]
    doc["cobertura"] = {"mes": f"{ano}-12", "brasil": brasil}
    doc["profissionais"] = [sum(v[i] for v in por_profissional.values()) for i in range(3)]
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
        juntar_atencao_basica(doc, args.paralelo_sisab)
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
    juntar_atencao_basica(doc, args.paralelo_sisab)
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
