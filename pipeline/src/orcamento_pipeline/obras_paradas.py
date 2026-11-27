"""Obras paradas: as obras com dinheiro federal que o TCU considera paralisadas, por cidade e estado.

    uv run obras-paradas                  # lê as tabelas do TCU, liga ao Transferegov e grava o JSON
    uv run obras-paradas --atualizar      # a cópia de referência com os valores do Transferegov de hoje
    uv run obras-paradas --sem-baixar     # só copia pipeline/referencia/obras-paradas.json

Fonte: o Painel de Obras Paralisadas do TCU (https://paineis.tcu.gov.br/obrasparalisadas). O TCU junta nove
bases do governo federal (Caixa, FNDE, Funasa, SISMOB, DNIT, Codevasf, SESu, Setec e outras obras do MEC) e
publica uma fotografia por semestre ("data-base"). O painel é um Power BI sem arquivo para baixar: cada
data-base é exportada à mão na página "Tabela de dados" (menu "…" da tabela → Exportar dados → xlsx, com o
filtro de Situação em "Todos") e salva como data/raw/tcu-obras/obras-AAAA-MM.xlsx. Ver
docs/levantamento-obras-paradas.md.

O que sai daqui:

- a última data-base inteira: cada obra paralisada com cidade, quem paga, valores, quanto foi feito, a causa
  e a situação que o próprio órgão informa (que nem sempre é "paralisada": o TCU tem critério próprio);
- desde quando a obra aparece parada nas datas-base seguidas, até a última ("na lista desde");
- o que aconteceu, na última data-base, com as obras que estavam paradas na anterior;
- o tamanho da lista inteira ("andamento"): as obras em execução e as paradas juntas, por tipo de obra, por quem
  paga e por estado, e as maiores. É o que a página /obras mostra.

A cidade vem como texto ("Carnaubal/CE") e é casada pelo nome com o cadastro do SICONFI. Obras só com a UF
(DNIT, Codevasf, parte das universidades) ficam no estado, sem cidade.

Transferegov: as obras da Caixa, da Funasa e parte das do FNDE são convênios ou contratos de repasse, e o número
que o TCU mostra ("Núm. Instrumento") é o número do convênio no Transferegov. Os arquivos abertos do
Transferegov (siconv_convenio e siconv_proposta, atualizados todo dia, sem cadastro) dão, para cada convênio, o
ano da assinatura, o fim do prazo, a situação do convênio e quanto a União já depositou na conta da obra
(desembolsado) e quanto ainda está lá (saldo em conta). O mesmo número às vezes existe em outro sistema; por isso
o convênio só vale se o estado de quem o assinou for o da obra. Obra sem cidade no TCU ganha a cidade da
prefeitura que assinou.

Todas as obras (/obras/todas): a última data-base inteira, obra a obra, com as quatro situações (em execução,
paralisada, concluída, cancelada). Fica fora do obras-paradas.json: a cópia de referência é um arquivo só
(pipeline/referencia/obras-todas.json) e o site recebe um arquivo por estado mais um índice
(site/public/data/obras/CE.json, …, indice.json), para o explorador baixar só o estado escolhido.

Saída: site/public/data/obras-paradas/obras-paradas.json, com cópia em pipeline/referencia/. A carga do TCU é à
mão (uma vez por ano, quando o TCU publica uma data-base nova); a publicação usa --atualizar, que baixa só o
siconv_convenio (~18 MB) e atualiza os valores dos convênios já ligados.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

from .cidades import RAIZ, baixar_entes
from .folha_estadual import chave
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA = RAIZ / "data" / "raw" / "tcu-obras"
SAIDA = RAIZ / "site" / "public" / "data" / "obras-paradas" / "obras-paradas.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "obras-paradas.json"
SAIDA_TODAS = RAIZ / "site" / "public" / "data" / "obras"
REFERENCIA_TODAS = RAIZ / "pipeline" / "referencia" / "obras-todas.json"
FONTE = "TCU, Painel de Obras Paralisadas (paineis.tcu.gov.br/obrasparalisadas), tabela de dados"
URL = "https://paineis.tcu.gov.br/obrasparalisadas"

PASTA_TG = RAIZ / "data" / "raw" / "transferegov"
URL_TG = "https://api-publica.transferegov.gestao.gov.br/downloads/dadosgov/"
FONTE_TG = "Transferegov.br, dados abertos (siconv_convenio e siconv_proposta)"
# Bases do TCU em que o número do instrumento pode ser um convênio do Transferegov.
BASES_TG = {"CAIXA", "FUNASA", "SIMEC", "SIMEC-Outros"}
MUNICIPAL = "Administração Pública Municipal"

PARALISADA = "Paralisada"
MAIORES_UF = 10
MAIORES_BRASIL = 25
MAIORES_SALDO = 20
MAIORES_ANDAMENTO = 15
EM_EXECUCAO = "Em execução"
# As situações do TCU, na ordem em que o explorador as mostra; na linha de cada obra vai a posição.
SITUACOES = [EM_EXECUCAO, PARALISADA, "Concluída", "Cancelada"]
PACS = [None, "PAC (legado)", "Novo PAC"]
SEM_UF = "sem-estado"
SEM_SETOR = "Não identificado"
CIDADES_UF = 10
# Código IBGE do estado (os dois primeiros dígitos do código da cidade).
UF_CODIGO = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17, "MA": 21, "PI": 22, "CE": 23, "RN": 24,
    "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41, "SC": 42,
    "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

# Quem paga, como aparece no site (o nome que o TCU usa fica no arquivo para conferir).
QUEM_PAGA = {
    "Fundo Nacional de Desenvolvimento da Educação": "FNDE (Educação)",
    "Ministério da Saúde": "Ministério da Saúde",
    "Fundação Nacional de Saúde": "Funasa",
    "Ministério das Cidades": "Ministério das Cidades",
    "Ministério da Educação": "Ministério da Educação",
    "Ministério da Integração e Desenvolvimento Regional": "Ministério da Integração",
    "Departamento Nacional de Infraestrutura de Transportes": "DNIT",
    "Ministério do Desenvolvimento e Assitência Social e Combate à Fome": "Ministério do Desenvolvimento Social",
    "Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome": "Ministério do Desenvolvimento Social",
    "Ministério da Agricultura e Pecuária": "Ministério da Agricultura",
    "Ministério da Justiça e Segurança Pública": "Ministério da Justiça",
}
# Quem acompanha a obra (a base de onde o TCU tirou a linha).
BASES = {
    "CAIXA": "Caixa",
    "SIMEC": "FNDE (SIMEC)",
    "SIMEC-Outros": "MEC (SIMEC)",
    "SESU": "MEC, universidades (SIMEC)",
    "SETEC": "MEC, institutos federais (SIMEC)",
    "SISMOB": "Ministério da Saúde (SISMOB)",
    "FUNASA": "Funasa",
    "DNIT": "DNIT (SIAC)",
    "CODEVASF": "Codevasf (SIGEC)",
}
# Causa genérica demais para mostrar.
CAUSA_VAZIA = {None, "", "Outros", "Outro", "Não informado"}
CAUSA_CURTA = {
    "Declaração de que a execução do objeto está paralisada por órgão ou entidade da Administração Pública "
    "Federal, independentemente do prazo.": "Declarada paralisada por órgão federal",
}
# Nomes de cidade que o TCU escreve diferente do SICONFI.
APELIDOS = {
    ("RN", "JANUARIO CICCO"): "BOA SAUDE",
    ("BA", "SANTA TEREZINHA"): "SANTA TERESINHA",
    ("MG", "BARAO DO MONTE ALTO"): "BARAO DE MONTE ALTO",
    ("SE", "AMPARO DO SAO FRANCISCO"): "AMPARO DE SAO FRANCISCO",
}


def _ler(arq: Path) -> list[dict]:
    """Uma data-base exportada do painel: lista de linhas como dicionários (sem a linha de filtros)."""
    import warnings

    import openpyxl

    warnings.filterwarnings("ignore", "Workbook contains no default style")

    ws = openpyxl.load_workbook(arq, read_only=True).worksheets[0]
    linhas = ws.iter_rows(values_only=True)
    cab = [str(c).strip() if c else "" for c in next(linhas)]
    obrigatorias = {"Data base", "Base de dados", "Empreendimento", "Situação", "Local", "Valor Investimento",
                    "Valor Desbloqueado", "Repassador", "ID"}
    faltam = obrigatorias - set(cab)
    if faltam:
        raise SystemExit(f"{arq.name}: o painel mudou, faltam as colunas {sorted(faltam)}")
    saida = []
    for r in linhas:
        if len(r) != len(cab) or not r[cab.index("ID")]:
            continue
        saida.append(dict(zip(cab, r)))
    return saida


def _data_base(arq: Path) -> str:
    m = re.fullmatch(r"obras-(\d{4}-\d{2})\.xlsx", arq.name)
    if not m:
        raise SystemExit(f"nome inesperado: {arq.name} (use obras-AAAA-MM.xlsx)")
    return m.group(1)


def _nome(s: str | None) -> str:
    """Tira o número da obra no SIMEC do começo, junta espaços e põe a primeira letra em maiúscula."""
    s = " ".join((s or "").split())
    s = re.sub(r"^(\((EP|[A-Z]{1,3})\)\s*)?\(\d+\)\s*", "", s)
    s = s.replace(" ? ", " – ")
    return s[:1].upper() + s[1:] if s else s


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(v) -> int | None:
    """Fração (0,53) → 53. Vazio continua vazio."""
    if v is None or v == "":
        return None
    try:
        return round(float(v) * 100)
    except (TypeError, ValueError):
        return None


def _cidades() -> dict[tuple[str, str], int]:
    return {(e["uf"], chave(e["ente"])): int(e["cod_ibge"]) for e in baixar_entes() if e["esfera"] == "M"}


def _local(local: str | None, cidades: dict[tuple[str, str], int]) -> tuple[str | None, int | None]:
    """"Carnaubal/CE" → ("CE", 2303402). "RS" → ("RS", None). Cidade que não casa → (UF, None)."""
    local = (local or "").strip()
    if "/" not in local:
        return (local if re.fullmatch(r"[A-Z]{2}", local) else None), None
    nome, uf = local.rsplit("/", 1)
    uf = uf.strip()
    k = chave(nome)
    k = APELIDOS.get((uf, k), k)
    return uf, cidades.get((uf, k))


# --- Transferegov -------------------------------------------------------------------------------------------

def _baixar_tg(nome: str, forcar: bool = False) -> Path:
    """Um zip dos dados abertos do Transferegov em data/raw/transferegov/ (baixa de novo com forcar)."""
    destino = PASTA_TG / f"{nome}.zip"
    if destino.exists() and not forcar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parte = destino.with_name(destino.name + ".part")
    req = urllib.request.Request(URL_TG + destino.name, headers={"User-Agent": USER_AGENT})
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as r, parte.open("wb") as f:
                shutil.copyfileobj(r, f, 8 << 20)
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    {destino.name}: {e}; tentando de novo", flush=True)
            time.sleep(10 * (tentativa + 1))
    else:
        raise RuntimeError(f"{destino.name}: não baixou")
    if not zipfile.is_zipfile(parte):
        raise RuntimeError(f"{destino.name}: a resposta não é um zip")
    parte.replace(destino)
    return destino


def _linhas_tg(nome: str, forcar: bool = False) -> Iterator[dict]:
    with zipfile.ZipFile(_baixar_tg(nome, forcar)) as z:
        membro = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(membro) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""), delimiter=";")


def _valor_tg(s: str | None) -> float:
    """"265052,83" → 265052.83. A mesma coluna às vezes vem com ponto ("122310.72")."""
    s = (s or "").strip()
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _iso(d: str | None) -> str | None:
    """"20/06/2028" → "2028-06-20"."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (d or "").strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _data_carga(forcar: bool = False) -> str | None:
    for r in _linhas_tg("data_carga_siconv", forcar):
        return _iso((r.get("data_carga") or "")[:10])
    return None


def _convenios(numeros: set[str], forcar: bool = False) -> dict[str, dict]:
    return {r["NR_CONVENIO"]: r for r in _linhas_tg("siconv_convenio", forcar) if r["NR_CONVENIO"] in numeros}


def _tg_de(c: dict) -> list:
    """[número, ano da assinatura, fim do prazo, situação do convênio, valor global, desembolsado, saldo em conta]"""
    assinatura = _iso(c.get("DIA_ASSIN_CONV"))
    return [c["NR_CONVENIO"], int(assinatura[:4]) if assinatura else None, _iso(c.get("DIA_FIM_VIGENC_CONV")),
            (c.get("SIT_CONVENIO") or "").strip() or None, round(_valor_tg(c.get("VL_GLOBAL_CONV")), 2),
            round(_valor_tg(c.get("VL_DESEMBOLSADO_CONV")), 2), round(_valor_tg(c.get("VL_SALDO_CONTA")), 2)]


def _ligar_transferegov(obras: list[dict], cidades: dict[tuple[str, str], int], forcar: bool = False) -> dict:
    """Põe em cada obra da Caixa, Funasa ou FNDE o convênio do Transferegov com o mesmo número (o["tg"])."""
    candidatas = [o for o in obras if o["base"] in BASES_TG and (o["instrumento"] or "").isdigit()]
    print(f"Transferegov: {len(candidatas)} obras com número de convênio; lendo siconv_convenio…", flush=True)
    conv = _convenios({o["instrumento"] for o in candidatas}, forcar)
    ids = {c["ID_PROPOSTA"] for c in conv.values()}
    print(f"  {len(conv)} convênios achados; lendo siconv_proposta…", flush=True)
    props = {r["ID_PROPOSTA"]: (r["UF_PROPONENTE"], r["COD_MUNIC_IBGE"], r["NATUREZA_JURIDICA"])
             for r in _linhas_tg("siconv_proposta", forcar) if r["ID_PROPOSTA"] in ids}
    ibges = set(cidades.values())
    ligadas = outro_estado = cidade_nova = 0
    for o in candidatas:
        c = conv.get(o["instrumento"])
        p = props.get(c["ID_PROPOSTA"]) if c else None
        if not p:
            continue
        uf, ibge, natureza = p
        if o["uf"] and uf != o["uf"]:
            outro_estado += 1  # o mesmo número em outro sistema: não é este convênio
            continue
        o["tg"] = _tg_de(c)
        ligadas += 1
        if not o["uf"]:
            o["uf"] = uf
        if not o["ibge"] and natureza == MUNICIPAL and ibge.isdigit() and int(ibge) in ibges:
            o["ibge"] = int(ibge)
            cidade_nova += 1
    print(f"  {ligadas} obras ligadas a um convênio; {outro_estado} descartadas (convênio de outro estado); "
          f"{cidade_nova} ganharam a cidade", flush=True)
    return {"data": _data_carga(forcar), "fonte": FONTE_TG,
            "url": "https://dados.gov.br/dados/conjuntos-dados/transferegov"}


def _todas(doc: dict) -> Iterator[tuple[str, list]]:
    """Cada obra paralisada uma vez só, com a UF: as das cidades e as que só têm o estado."""
    sigla = {v: k for k, v in UF_CODIGO.items()}
    for ibge, m in doc["mun"].items():
        for t in m[4]:
            yield sigla.get(int(ibge) // 100000, ""), t
    for uf, u in doc["uf"].items():
        for t in u["sem_cidade"]:
            yield uf, t


def _somar_tg(doc: dict) -> None:
    """Os totais do Transferegov no Brasil e em cada estado, a partir das obras (depois de montar ou atualizar)."""
    tg = doc["brasil"].get("transferegov")
    if tg is None:
        return
    por_uf: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
    total = [0, 0.0, 0.0, 0.0]
    vistos = set()  # um convênio que paga duas obras conta uma vez só
    for uf, t in _todas(doc):
        if not t[12] or t[12][0] in vistos:
            continue
        vistos.add(t[12][0])
        for soma in (total, por_uf[uf]):
            soma[0] += 1
            soma[1] += t[12][4]
            soma[2] += t[12][5]
            soma[3] += t[12][6]
    # [n.º de obras ligadas, valor global, desembolsado, saldo em conta]
    tg["total"] = [total[0], *(round(v, 2) for v in total[1:])]
    for uf, u in doc["uf"].items():
        s = por_uf.get(uf, [0, 0.0, 0.0, 0.0])
        u["transferegov"] = [s[0], *(round(v, 2) for v in s[1:])]
    tg["maiores_saldo"].sort(key=lambda t: -(t[12][6] if t[12] else 0))


def atualizar_tg(doc: dict, conv: dict[str, dict], data: str | None) -> int:
    """Troca os valores dos convênios já ligados pelos do siconv_convenio de hoje. Devolve quantos achou."""
    listas = [m[4] for m in doc["mun"].values()]
    for u in doc["uf"].values():
        listas += [u["maiores"], u["sem_cidade"]]
    listas += [doc["brasil"]["maiores"], doc["brasil"]["transferegov"]["maiores_saldo"]]
    vistos = set()
    for lista in listas:
        for t in lista:
            if t[12] and t[12][0] in conv:
                t[12] = _tg_de(conv[t[12][0]])
                vistos.add(t[12][0])
    doc["brasil"]["transferegov"]["data"] = data
    _somar_tg(doc)
    return len(vistos)


# --- TCU -----------------------------------------------------------------------------------------------------

def todas_as_obras(atual: list[dict], cidades: dict[tuple[str, str], int], data_base: str) -> dict:
    """A data-base inteira, obra a obra, para o explorador (/obras/todas). Os textos que se repetem (tipo de obra,
    quem paga, situação, PAC) viram listas, e cada obra guarda só a posição."""
    setores = [k for k, _ in Counter(r.get("Setor") or SEM_SETOR for r in atual).most_common()]
    paga = lambda r: QUEM_PAGA.get(r["Repassador"], r["Repassador"] or "Não informado")  # noqa: E731
    pagadores = [k for k, _ in Counter(paga(r) for r in atual).most_common()]
    i_setor = {k: i for i, k in enumerate(setores)}
    i_paga = {k: i for i, k in enumerate(pagadores)}
    por_uf: dict[str, list[list]] = defaultdict(list)
    for r in atual:
        if r["Situação"] not in SITUACOES:
            raise SystemExit(f"situação nova no painel: {r['Situação']!r} (obra {r['ID']})")
        uf, ibge = _local(r["Local"], cidades)
        local = (r["Local"] or "").strip()
        cidade = local.rsplit("/", 1)[0].strip() if "/" in local else None
        pac = r.get("Obra PAC")
        # [nome, cidade (como o TCU escreve) ou null, ibge ou null, tipo de obra, quem paga, situação, % feito,
        #  previsto, liberado, PAC]: os quatro do meio e o último são posições nas listas do índice
        por_uf[uf or SEM_UF].append([
            _nome(r["Empreendimento"]), cidade, ibge, i_setor[r.get("Setor") or SEM_SETOR], i_paga[paga(r)],
            SITUACOES.index(r["Situação"]), _pct(r.get("Exec. física")), round(_num(r["Valor Investimento"]), 2),
            round(_num(r["Valor Desbloqueado"]), 2), PACS.index(pac) if pac in PACS else 0,
        ])
    for lista in por_uf.values():
        lista.sort(key=lambda t: (-t[7], t[0]))
    return {"data_base": data_base, "fonte": FONTE, "url": URL, "situacoes": SITUACOES, "setores": setores,
            "quem_paga": pagadores, "pac": PACS, "uf": dict(sorted(por_uf.items()))}


def gravar_todas(doc: dict, pasta: Path = SAIDA_TODAS) -> dict:
    """Um arquivo por estado e o índice (as listas, os totais e quantas obras há em cada arquivo). Devolve o índice."""
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("*.json"):
        velho.unlink()
    situacao = [0] * len(doc["situacoes"])
    total = [0, 0.0, 0.0]
    ufs = {}
    for uf, obras in doc["uf"].items():
        _gravar({"uf": uf, "data_base": doc["data_base"], "obras": obras}, pasta / f"{uf}.json")
        ufs[uf] = [len(obras), round(sum(t[7] for t in obras), 2), round(sum(t[8] for t in obras), 2)]
        for t in obras:
            situacao[t[5]] += 1
        for i in range(3):
            total[i] += ufs[uf][i]
    indice = {k: doc[k] for k in ("data_base", "fonte", "url", "situacoes", "setores", "quem_paga", "pac")}
    # total e cada estado: [n.º de obras, previsto, liberado]; por_situacao segue a ordem de "situacoes"
    indice |= {"total": [total[0], round(total[1], 2), round(total[2], 2)], "por_situacao": situacao, "uf": ufs}
    _gravar(indice, pasta / "indice.json")
    return indice


def montar(pasta: Path, transferegov: bool = True, forcar_tg: bool = False) -> dict:
    return montar_tudo(pasta, transferegov, forcar_tg)[0]


def montar_tudo(pasta: Path, transferegov: bool = True, forcar_tg: bool = False) -> tuple[dict, dict]:
    """O documento das obras paradas e o de todas as obras (ver todas_as_obras), lendo as tabelas uma vez só."""
    arquivos = sorted(pasta.glob("obras-*.xlsx"))
    if not arquivos:
        raise SystemExit(f"nenhuma tabela em {pasta} (ver o começo deste arquivo)")
    datas = [_data_base(a) for a in arquivos]
    print(f"datas-base: {', '.join(datas)}", flush=True)
    tabelas = {d: _ler(a) for d, a in zip(datas, arquivos)}
    ultima = datas[-1]
    atual = tabelas[ultima]
    if not any(r["Situação"] != PARALISADA for r in atual):
        raise SystemExit(f"obras-{ultima}.xlsx só tem paralisadas: exporte com a Situação em 'Todos'")

    situacao = {d: {r["ID"]: r["Situação"] for r in t} for d, t in tabelas.items()}

    def desde(id_: str) -> str:
        """A primeira data-base da sequência de datas seguidas em que a obra aparece parada, até a última."""
        primeira = ultima
        for d in reversed(datas):
            if situacao[d].get(id_) != PARALISADA:
                break
            primeira = d
        return primeira

    cidades = _cidades()
    sem_casar: Counter = Counter()
    obras = []
    ativas_mun: Counter = Counter()
    ativas_uf: Counter = Counter()
    andamento = []
    for r in atual:
        uf, ibge = _local(r["Local"], cidades)
        if r["Situação"] in (EM_EXECUCAO, PARALISADA):
            if ibge:
                ativas_mun[ibge] += 1
            if uf:
                ativas_uf[uf] += 1
            andamento.append({
                "nome": _nome(r["Empreendimento"]),
                "paga": QUEM_PAGA.get(r["Repassador"], r["Repassador"] or "Não informado"),
                "setor": r.get("Setor") or SEM_SETOR,
                "uf": uf,
                "ibge": ibge,
                "local": r["Local"],
                "fisica": _pct(r.get("Exec. física")),
                "previsto": round(_num(r["Valor Investimento"]), 2),
                "liberado": round(_num(r["Valor Desbloqueado"]), 2),
                "parada": r["Situação"] == PARALISADA,
                "pac": r.get("Obra PAC") if r.get("Obra PAC") not in (None, "Não") else None,
            })
        if r["Situação"] != PARALISADA:
            continue
        if uf and not ibge and "/" in (r["Local"] or ""):
            sem_casar[r["Local"]] += 1
        causa = r.get("Causa da paralisação")
        causa = None if causa in CAUSA_VAZIA else CAUSA_CURTA.get(causa, causa)
        obras.append({
            "id": r["ID"],
            "nome": _nome(r["Empreendimento"]),
            "base": r["Base de dados"],
            "paga": QUEM_PAGA.get(r["Repassador"], r["Repassador"] or "Não informado"),
            "instrumento": str(r.get("Núm. Instrumento") or "").strip() or None,
            "uf": uf,
            "ibge": ibge,
            "local": r["Local"],
            "fisica": _pct(r.get("Exec. física")),
            "previsto": round(_num(r["Valor Investimento"]), 2),
            "liberado": round(_num(r["Valor Desbloqueado"]), 2),
            "setor": r.get("Setor") or SEM_SETOR,
            "causa": causa,
            "origem": (r.get("Situação origem") or "").strip().capitalize() or None,
            "pac": r.get("Obra PAC") not in (None, "Não"),
            "pacto": r.get("Pacto") == "Manifestou interesse em repactuar",
            "desde": desde(r["ID"]),
        })
    if sem_casar:
        print(f"aviso: {sum(sem_casar.values())} obras com cidade que não casou com o SICONFI; ficam só no estado:",
              ", ".join(f"{k} ({n})" for k, n in sem_casar.most_common(15)), flush=True)
    info_tg = _ligar_transferegov(obras, cidades, forcar_tg) if transferegov else None
    obras.sort(key=lambda o: -o["previsto"])

    def tupla(o: dict, com_local: bool) -> list:
        # [nome, base, quem paga, instrumento, % feito, previsto, liberado, causa, situação no órgão, desde,
        #  setor, pacto, convênio do Transferegov (ver _tg_de) ou null, (local, ibge)]
        t = [o["nome"], o["base"], o["paga"], o["instrumento"], o["fisica"], o["previsto"], o["liberado"],
             o["causa"], o["origem"], o["desde"], o["setor"], 1 if o["pacto"] else 0, o.get("tg")]
        if com_local:
            t += [o["local"], o["ibge"]]
        return t

    def soma(lista: list[dict]) -> list:
        return [len(lista), round(sum(o["previsto"] for o in lista), 2), round(sum(o["liberado"] for o in lista), 2)]

    def contagem(lista: list[dict], campo: str) -> list:
        g: dict[str, list[dict]] = defaultdict(list)
        for o in lista:
            g[o[campo]].append(o)
        return sorted(([k, *soma(v)] for k, v in g.items()), key=lambda x: (-x[1], str(x[0])))

    por_mun: dict[int, list[dict]] = defaultdict(list)
    por_uf: dict[str, list[dict]] = defaultdict(list)
    for o in obras:
        if o["ibge"]:
            por_mun[o["ibge"]].append(o)
        if o["uf"]:
            por_uf[o["uf"]].append(o)

    mun = {str(ibge): [*soma(lista), ativas_mun[ibge], [tupla(o, False) for o in lista]]
           for ibge, lista in sorted(por_mun.items())}
    uf = {}
    for sigla, lista in sorted(por_uf.items()):
        sem_cidade = [o for o in lista if not o["ibge"]]
        cid = contagem([o for o in lista if o["ibge"]], "ibge")[:CIDADES_UF]
        uf[sigla] = {
            "total": soma(lista),
            "ativas": ativas_uf[sigla],
            "cidades_com_obra": len({o["ibge"] for o in lista if o["ibge"]}),
            "cidades": [[str(c[0]), c[1], c[2], c[3]] for c in cid],
            "quem_paga": contagem(lista, "paga"),
            "maiores": [tupla(o, True) for o in lista[:MAIORES_UF]],
            "sem_cidade": [tupla(o, False) for o in sem_cidade],
        }

    # O que aconteceu com as obras que estavam paradas na data-base anterior.
    destino = None
    if len(datas) > 1:
        antes = datas[-2]
        paradas_antes = [k for k, v in situacao[antes].items() if v == PARALISADA]
        c = Counter(situacao[ultima].get(k, "Saiu da lista") for k in paradas_antes)
        destino = {"de": antes, "total": len(paradas_antes), "situacoes": c.most_common()}

    historico = []
    for d in datas:
        t = tabelas[d]
        par = [r for r in t if r["Situação"] == PARALISADA]
        historico.append({
            "data": d,
            "paralisadas": len(par),
            "em_execucao": sum(1 for r in t if r["Situação"] == EM_EXECUCAO),
            "previsto": round(sum(_num(r["Valor Investimento"]) for r in par), 2),
            "liberado": round(sum(_num(r["Valor Desbloqueado"]) for r in par), 2),
        })

    def soma_andamento(lista: list[dict]) -> list:
        # [obras em andamento, previsto, liberado, quantas delas paradas, previsto das paradas]
        paradas = [o for o in lista if o["parada"]]
        return [len(lista), round(sum(o["previsto"] for o in lista), 2), round(sum(o["liberado"] for o in lista), 2),
                len(paradas), round(sum(o["previsto"] for o in paradas), 2)]

    def contagem_andamento(campo: str) -> list:
        g: dict[str, list[dict]] = defaultdict(list)
        for o in andamento:
            g[o[campo]].append(o)
        return sorted(([k, *soma_andamento(v)] for k, v in g.items()), key=lambda x: (-x[2], str(x[0])))

    andamento.sort(key=lambda o: -o["previsto"])
    em_andamento = {
        "total": soma_andamento(andamento),
        "setor": contagem_andamento("setor"),
        "quem_paga": contagem_andamento("paga"),
        "uf": {k: v for k, *v in sorted(([u, *s] for u, *s in contagem_andamento("uf") if u), key=lambda x: x[0])},
        # [nome, quem paga, setor, % feito, previsto, liberado, local, ibge, parada (0/1), PAC ou null]
        "maiores": [[o["nome"], o["paga"], o["setor"], o["fisica"], o["previsto"], o["liberado"], o["local"], o["ibge"],
                     1 if o["parada"] else 0, o["pac"]] for o in andamento[:MAIORES_ANDAMENTO]],
    }

    brasil = {
        "total": soma(obras),
        "ativas": len(andamento),
        "andamento": em_andamento,
        "cidades_com_obra": len(por_mun),
        "sem_cidade": soma([o for o in obras if not o["ibge"]]),
        "quem_paga": contagem(obras, "paga"),
        "base": contagem(obras, "base"),
        "setor": contagem(obras, "setor"),
        "causa": contagem([o for o in obras if o["causa"]], "causa")[:12],
        "sem_causa": sum(1 for o in obras if not o["causa"]),
        "origem": contagem(obras, "origem"),
        "desde": sorted(([d, *soma([o for o in obras if o["desde"] == d])] for d in datas if any(o["desde"] == d for o in obras))),
        "pacto": soma([o for o in obras if o["pacto"]]),
        "maiores": [tupla(o, True) for o in obras[:MAIORES_BRASIL]],
        "uf": {s: [*v["total"], v["ativas"]] for s, v in uf.items()},
        "historico": historico,
        "destino": destino,
    }
    if info_tg:
        com_saldo = sorted((o for o in obras if o.get("tg") and o["tg"][6] > 0), key=lambda o: -o["tg"][6])
        brasil["transferegov"] = {**info_tg, "maiores_saldo": [tupla(o, True) for o in com_saldo[:MAIORES_SALDO]]}
    doc = {
        "data_base": ultima,
        "datas": datas,
        "fonte": FONTE,
        "url": URL,
        "bases": BASES,
        "brasil": brasil,
        "uf": uf,
        "mun": mun,
    }
    _somar_tg(doc)
    return doc, todas_as_obras(atual, cidades, ultima)


def _gravar(doc: dict, arq: Path) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(arq)


def main() -> None:
    p = argparse.ArgumentParser(prog="obras-paradas", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true",
                   help="não lê as tabelas: copia a cópia de referência para o site")
    p.add_argument("--atualizar", action="store_true",
                   help="a cópia de referência com os valores do Transferegov de hoje (para a publicação)")
    p.add_argument("--sem-transferegov", action="store_true", help="não liga as obras ao Transferegov")
    p.add_argument("--forcar", action="store_true", help="baixa de novo os arquivos do Transferegov")
    p.add_argument("--pasta", type=Path, default=PASTA, help="onde estão as tabelas exportadas do painel")
    args = p.parse_args()

    if args.sem_baixar or args.atualizar:
        if not REFERENCIA.exists():
            sys.exit(f"sem cópia de referência em {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)} → {SAIDA.relative_to(RAIZ)}")
        if REFERENCIA_TODAS.exists():
            i = gravar_todas(json.loads(REFERENCIA_TODAS.read_text(encoding="utf-8")))
            print(f"todas as obras: {i['total'][0]} em {len(i['uf'])} arquivos em {SAIDA_TODAS.relative_to(RAIZ)}")
        if args.sem_baixar:
            return
        doc = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        if "transferegov" not in doc["brasil"]:
            print("a cópia de referência não tem o Transferegov; fica como está")
            return
        numeros = {t[12][0] for _, t in _todas(doc) if t[12]}
        try:
            conv = _convenios(numeros, forcar=True)
            data = _data_carga(forcar=True)
        except Exception as e:  # sem o Transferegov, o site sai com os valores da cópia de referência
            print(f"Transferegov indisponível ({e}); o site sai com a cópia de referência")
            sys.exit(3)
        n = atualizar_tg(doc, conv, data)
        _gravar(doc, SAIDA)
        t = doc["brasil"]["transferegov"]["total"]
        print(f"Transferegov de {data}: {n} de {len(numeros)} convênios atualizados; desembolsado "
              f"R$ {t[2] / 1e9:.2f} bi, saldo em conta R$ {t[3] / 1e6:.1f} mi")
        return

    doc, todas = montar_tudo(args.pasta, transferegov=not args.sem_transferegov, forcar_tg=args.forcar)
    b = doc["brasil"]
    print(f"{b['total'][0]} obras paralisadas em {doc['data_base']}: R$ {b['total'][1] / 1e9:.1f} bi previstos, "
          f"R$ {b['total'][2] / 1e9:.1f} bi liberados; {b['cidades_com_obra']} cidades; "
          f"{b['sem_cidade'][0]} só com o estado", flush=True)
    if "transferegov" in b:
        t = b["transferegov"]["total"]
        print(f"Transferegov ({b['transferegov']['data']}): {t[0]} obras com convênio; desembolsado R$ {t[2] / 1e9:.2f} bi, "
              f"saldo em conta R$ {t[3] / 1e6:.1f} mi", flush=True)
    _gravar(doc, SAIDA)
    _gravar(doc, REFERENCIA)
    print(f"gravado {SAIDA.relative_to(RAIZ)} ({SAIDA.stat().st_size / 1e6:.1f} MB) e a cópia de referência")
    _gravar(todas, REFERENCIA_TODAS)
    i = gravar_todas(todas)
    print(f"todas as obras: {i['total'][0]} ({', '.join(f'{n} {s.lower()}' for s, n in zip(i['situacoes'], i['por_situacao']))}) "
          f"em {len(i['uf'])} arquivos em {SAIDA_TODAS.relative_to(RAIZ)}; cópia de referência com "
          f"{REFERENCIA_TODAS.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
