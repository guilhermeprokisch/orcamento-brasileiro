"""Obras do governo de São Paulo e das prefeituras paulistas, do Painel de Obras do TCE-SP, para /obras/todas.

    uv run obras-tcesp                # baixa o painel, grava a cópia de referência e refaz os arquivos do site
    uv run obras-tcesp --sem-baixar   # só refaz os arquivos do site com as cópias de referência

Fonte: o Painel de Obras do Tribunal de Contas do Estado de São Paulo (https://paineldeobras.tce.sp.gov.br), que
acompanha as obras em andamento contratadas pelo estado e pelas prefeituras (e órgãos delas) de SP. O painel é um
Pentaho que responde em JSON às consultas da própria página, com o usuário anônimo que ela usa. Só há uma data-base
por vez, e a obra sai da lista quando acaba: não há "pronta" nem "cancelada".

O que entra: cada linha da tabela do painel (cidade, situação, esfera, valor do contrato, empresa, órgão, ano,
objeto), menos as linhas repetidas idênticas e as obras pagas só com dinheiro federal (fontes "Transferências e
convênios federais" e "Emendas parlamentares individuais"), que podem já estar na lista do TCU. Não há número de
convênio para casar uma lista com a outra. A cidade é casada pelo nome com o cadastro do SICONFI e com a lista de
cidades do próprio painel, que usa o código IBGE. Ver docs/levantamento-obras-estados-municipios.md.

Situação: "Em execução - no prazo" e "Em execução - atrasada" viram "Em execução" (com a marca de atrasada);
"Paralisada" continua. O nome da obra é o objeto do contrato, em maiúsculas no painel: aqui vira texto normal,
sem o começo burocrático ("Contratação de empresa para…").

Saída: pipeline/referencia/obras-tcesp.json (a cópia de referência) e, juntando à lista do TCU
(pipeline/referencia/obras-todas.json), os arquivos do explorador em site/public/data/obras/ (ver obras_paradas.py).
A publicação roda este comando depois do obras-paradas; se o painel não responder, fica o que obras-paradas gravou
com a cópia de referência.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from . import obras_paradas as op
from .cidades import RAIZ
from .folha_estadual import chave, municipios
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA = RAIZ / "data" / "raw" / "tcesp-obras"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "obras-tcesp.json"
FONTE = "TCE-SP, Painel de Obras (paineldeobras.tce.sp.gov.br)"
URL = "https://paineldeobras.tce.sp.gov.br"
API = "https://paineldeobras.tce.sp.gov.br/pentaho/plugin/cda/api/doQuery"
CDA = "/public/Obra/painel_obras.cda"
UF = "SP"
# Nomes que o painel escreve diferente do SICONFI.
APELIDOS = {"FLORINEA": "FLORINIA"}

# As esferas do explorador, na ordem dos botões "De quem é o dinheiro". As obras do TCU são todas da União.
ESFERAS = ["União", "Governo do estado", "Prefeitura"]
ESFERA = {"ESTADUAL": 1, "MUNICIPAL": 2}
# situação no painel → (posição em op.SITUACOES, atrasada)
SITUACAO = {
    "Em execução - no prazo": (0, 0),
    "Em execução - atrasada": (0, 1),
    "Paralisada": (1, 0),
}
# Fontes do filtro do painel (selFonteRecurso). As duas federais decidem quais obras ficam de fora.
FONTES = {1: "Tesouro", 2: "Transferências e convênios estaduais", 3: "Fundos especiais",
          4: "Recursos próprios da administração indireta", 5: "Transferências e convênios federais",
          6: "Outras fontes", 7: "Operações de crédito", 8: "Emendas parlamentares individuais"}
FEDERAIS = {5, 8}
COLUNAS = ["ds_municipio", "ds_situacao", "esfera", "vl_ajuste", "nome", "doc", "ds_entidade", "ano_ajuste",
           "objeto_ajuste"]

# --- O nome da obra -----------------------------------------------------------------------------------------

# "O presente instrumento tem por objeto a…", "Constitui objeto do presente contrato a…"
_PRESENTE = re.compile(
    r"^(?:o presente (?:instrumento|contrato|termo)[^.;:]{0,40}?\b(?:tem|terá) (?:como|por) objeto|"
    r"constitui (?:o )?objeto d(?:[oa]|est[ea]) (?:presente )?(?:contrato|instrumento|termo|licitação)|objeto:)\s+(?:(?:a|o|as|os)\s+)?",
    re.I,
)
# O começo que não diz o que é a obra ("Contratação de empresa especializada em serviços de engenharia para…").
_COMECO = re.compile(
    r"^(?:termo de contrato|contrato|contratação|contratacao|prestação de serviços?|objeto)\b[^.;:]*?"
    r"\b(?:para|visando(?: [àa])?|objetivando|com vistas [àa])\s+(?:(?:a|o|as|os)\s+)?"
    r"|^(?:para|objeto:?)\s+(?:(?:a|o|as|os)\s+)?",
    re.I,
)
# O que sobra quando não há "para" ("Contratação de empresa especializada em execução de…").
_EMPRESA = re.compile(
    r"^contrata\W{0,2}[çc]?[ãa]?o de (?:uma )?(?:empresa|consórcio|consorcio)s?"
    r"(?: especializada| de engenharia| de construção civil| do ramo(?: de [a-zçãéêíóúõ ]+?)?| de prestação de serviços?)?"
    r"(?: (?:em|na|no|nos|nas|de|para))?\s+(?:(?:serviços|obras) de engenharia (?:para|de|na|no)\s+)?",
    re.I,
)
# Siglas que ficam em maiúsculas.
SIGLAS = {
    "sp", "sabesp", "cdhu", "der", "daee", "fde", "cptm", "emtu", "ee", "emef", "emei", "emeief", "cemei", "cei",
    "ceu", "ubs", "usf", "upa", "ama", "caps", "cras", "creas", "samu", "eta", "ete", "pac", "apae", "sesc",
    "senai", "etec", "fatec", "unesp", "usp", "unicamp", "led", "brt", "vlt", "psf", "esf", "cmei", "emeb", "epp",
    "ltda", "me", "s/a", "sa", "cnpj", "cep", "km", "nº", "ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi",
    "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx", "pmsp", "sme", "smo", "seduc", "sehab",
    "siurb", "sptrans", "metrô", "dersa", "hc", "fmusp", "ima", "cpp", "ctr", "ecopontos",
}
# Depois destas palavras vem um nome próprio (de rua, bairro, escola, rio), que fica com iniciais maiúsculas.
_ANTES_DE_NOME = {
    "rua", "ruas", "avenida", "avenidas", "av", "av.", "estrada", "estradas", "rodovia", "rodovias", "bairro",
    "bairros", "jardim", "jd", "jd.", "vila", "vl", "vl.", "parque", "córrego", "corrego", "rio", "ribeirão",
    "praça", "pça", "escola", "estação", "estações", "residencial", "núcleo", "loteamento", "distrito", "travessa",
    "alameda", "viaduto", "ponte", "complexo", "conjunto", "chácara", "chácaras", "sítio", "fazenda", "hospital",
    "centro", "ginásio", "teatro", "museu", "estádio", "ee", "emef", "emei", "creche", "ubs", "usf", "upa",
}
# Palavras que ligam partes de um nome próprio e ficam em minúsculas ("Rua Tenente Catão Roxo", "Vila São João da
# Boa Vista").
_LIGA = {"de", "do", "da", "dos", "das", "e", "d'"}
# Palavras que encerram o nome próprio.
_FIM = {
    "com", "para", "no", "na", "nos", "nas", "em", "entre", "localizado", "localizada", "localizados", "sito",
    "sita", "situado", "situada", "até", "ate", "conforme", "incluindo", "inclusive", "através", "pelo", "pela",
    "ao", "à", "a", "o", "as", "os", "que", "s/n", "s/nº", "nº", "n°", "lote", "trecho", "estaca", "estacas",
    "município", "municipio", "neste", "nesta", "deste", "desta", "por", "sob", "sobre", "junto", "km",
}


def _titulo(p: str) -> str:
    """A primeira letra em maiúscula, mesmo depois de aspas ou parênteses."""
    m = re.search(r"[^\W\d_]", p)
    return p[:m.start()] + p[m.start()].upper() + p[m.start() + 1:] if m else p


def nome_da_obra(objeto: str | None, cidade: str | None = None) -> str:
    """O objeto do contrato, que o painel dá em maiúsculas, como texto normal: sem o começo burocrático, em
    minúsculas, com siglas em maiúsculas e nomes próprios (a cidade da obra e o que vem depois de "rua", "bairro",
    "escola"…) com iniciais maiúsculas. É uma aproximação: nome próprio solto no meio do texto fica em minúsculas."""
    s = " ".join((objeto or "").replace("¿", " ").split()).strip(" .;,-")
    if not s:
        return ""
    s = s.lower()
    s = _PRESENTE.sub("", s, count=1).strip()
    s = _COMECO.sub("", s, count=1).strip()
    s = _EMPRESA.sub("", s, count=1).strip()
    # "contratação de empresa para construção de empresa para construção de…": a repetição que aparece no painel
    s = re.sub(r"^(.{8,60}?) de empresa para \1", r"\1", s)
    palavras = s.split(" ")
    saida, em_nome = [], False
    for i, p in enumerate(palavras):
        nu = p.strip(".,;:()\"'")
        if nu in SIGLAS or (re.search(r"\d", nu) and re.search(r"[a-z]", nu) and "-" in nu):
            q = p.upper()
        elif em_nome and nu in _LIGA:
            q = p
        elif em_nome and nu and nu not in _FIM and not re.match(r"^\d", nu):
            q = _titulo(p)
        else:
            q = p
            em_nome = False
        saida.append(q)
        if re.search(r"[,;:()]$", p) or nu in _FIM:
            em_nome = False
        if nu in _ANTES_DE_NOME:
            em_nome = True
    s = " ".join(saida)
    if cidade:
        s = re.sub(rf"\b{re.escape(cidade.lower())}\b", cidade, s)
    s = re.sub(r"/sp\b", "/SP", s)
    return _titulo(s)


def _empresa(nome: str | None) -> str:
    """"CONSTRUTORA EXEMPLO LTDA" → "Construtora Exemplo LTDA"."""
    pal = [p for p in " ".join((nome or "").split()).lower().split(" ") if p]
    miudas = _LIGA | {"para", "o", "a", "ao", "à", "em", "no", "na"}
    return " ".join(p.upper() if p.strip(".,") in SIGLAS else p if i and p in miudas else _titulo(p)
                    for i, p in enumerate(pal))


def _orgao(nome: str | None, esfera: int) -> str | None:
    """O órgão que contratou, em texto normal. A prefeitura em si fica de fora (a linha já diz "Prefeitura")."""
    n = " ".join((nome or "").split())
    if not n or (esfera == 2 and re.match(r"(?i)^prefeitura (municipal|do munic[ií]pio)\b", n)):
        return None
    # "Secretaria da Educação / Fundação para o Desenvolvimento da Educação": quem contratou é o da direita
    return _empresa(n.rsplit(" / ", 1)[-1])


# --- O painel -----------------------------------------------------------------------------------------------

def _consulta(acesso: str, **params: str) -> list[list]:
    q = {"path": CDA, "dataAccessId": acesso, "userid": "anony", "password": "zero"}
    q |= {f"param{k}": v for k, v in params.items()}
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(q)}", headers={"User-Agent": USER_AGENT})
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as r:
                d = json.load(r)
            return d["resultset"]
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            print(f"    TCE-SP {acesso}: {e}; tentando de novo", flush=True)
            time.sleep(10 * (tentativa + 1))
    raise RuntimeError(f"TCE-SP {acesso}: não respondeu")


def _tabela(fonte: int = -1) -> list[list]:
    return _consulta("obrasTabela", pPeriodo="1", pMunicipio="-1", pSituacao="-1", pFonteRecurso=str(fonte),
                     pContratante="-1", pContratado="-1")


def baixar(pasta: Path = PASTA) -> dict:
    """As consultas do painel, gravadas como vieram em data/raw/tcesp-obras/ (para refazer sem rede)."""
    pasta.mkdir(parents=True, exist_ok=True)
    bruto = {
        "periodo": _consulta("selPeriodo"),
        "municipios": _consulta("selMunicipio"),
        "tabela": _tabela(),
        "fontes": {str(f): _tabela(f) for f in FONTES},
    }
    (pasta / "painel.json").write_text(json.dumps(bruto, ensure_ascii=False), encoding="utf-8")
    return bruto


def _data_base(periodo: list[list]) -> str:
    """"Data Base: 17/10/2026" → "2026-10-17"."""
    textos = [str(r[1]) for r in periodo if r and str(r[0]) == "1"] or [str(r[-1]) for r in periodo]
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", textos[0] if textos else "")
    if not m:
        raise SystemExit(f"data-base inesperada no painel do TCE-SP: {periodo!r}")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def _municipios() -> dict[str, str]:
    """As cidades de SP no cadastro do SICONFI (a lista de cidades do painel só tem parte delas)."""
    return municipios(UF)


def montar(bruto: dict) -> dict:
    """A cópia de referência: uma linha por obra, já sem repetidas e sem as pagas só com dinheiro federal."""
    cidades = {k: int(v) for k, v in _municipios().items()}
    cidades |= {chave(nome): int(cod) for cod, nome in bruto["municipios"] if int(cod) > 0}
    fontes: dict[tuple, set[int]] = {}
    for f, linhas in bruto["fontes"].items():
        for r in linhas:
            fontes.setdefault(tuple(r), set()).add(int(f))
    vistas: set[tuple] = set()
    obras, repetidas, so_federal, sem_cidade = [], 0, [0, 0.0], Counter()
    for r in bruto["tabela"]:
        t = tuple(r)
        if t in vistas:
            repetidas += 1
            continue
        vistas.add(t)
        linha = dict(zip(COLUNAS, r))
        fs = fontes.get(t, set())
        if fs and fs <= FEDERAIS:
            so_federal[0] += 1
            so_federal[1] += float(linha["vl_ajuste"] or 0)
            continue
        if linha["ds_situacao"] not in SITUACAO:
            raise SystemExit(f"situação nova no painel do TCE-SP: {linha['ds_situacao']!r}")
        if linha["esfera"] not in ESFERA:
            raise SystemExit(f"esfera nova no painel do TCE-SP: {linha['esfera']!r}")
        cidade = " ".join((linha["ds_municipio"] or "").split())
        ibge = cidades.get(chave(cidade)) or cidades.get(APELIDOS.get(chave(cidade), ""))
        if not ibge:
            sem_cidade[cidade] += 1
        situacao, atrasada = SITUACAO[linha["ds_situacao"]]
        # [nome, cidade, ibge, esfera, situação, atrasada, valor do contrato, ano do contrato, órgão, sem dinheiro
        #  federal informado (fonte só não federal: 1; com alguma fonte federal: 2; sem fonte informada: 0)]
        obras.append([
            nome_da_obra(linha["objeto_ajuste"], cidade)
            or (f"Obra sem descrição, contratada com {_empresa(linha['nome'])}" if linha["nome"] else "Obra sem descrição"),
            cidade or None, ibge, ESFERA[linha["esfera"]], situacao,
            atrasada, round(float(linha["vl_ajuste"] or 0), 2), linha["ano_ajuste"],
            _orgao(linha["ds_entidade"], ESFERA[linha["esfera"]]), 0 if not fs else 2 if fs & FEDERAIS else 1,
        ])
    if sem_cidade:
        print(f"    TCE-SP: cidades sem código IBGE: {dict(sem_cidade)}", flush=True)
    obras.sort(key=lambda o: (-o[6], o[0]))
    return {"data_base": _data_base(bruto["periodo"]), "fonte": FONTE, "url": URL, "uf": UF,
            "repetidas": repetidas, "so_federal": [so_federal[0], round(so_federal[1], 2)], "obras": obras}


# --- Juntar à lista do TCU ----------------------------------------------------------------------------------

def juntar(todas: dict, tcesp: dict | None) -> dict:
    """A lista do TCU (op.todas_as_obras) com as obras do TCE-SP no arquivo de SP. Cada obra do TCE-SP vira uma linha
    no formato das do TCU, mais quatro posições: [nome, cidade, ibge, tipo de obra, quem paga, situação, % feito
    (null), valor do contrato, liberado (null), PAC (0), esfera, atrasada, ano do contrato, órgão]. As linhas do TCU
    continuam com dez posições (a esfera delas é a União). Devolve um documento novo; `todas` fica como está."""
    doc = json.loads(json.dumps(todas))
    doc["esferas"] = ESFERAS
    if not tcesp or not tcesp.get("obras"):
        return doc
    if op.SEM_SETOR not in doc["setores"]:
        doc["setores"].append(op.SEM_SETOR)
    for nome in ESFERAS[1:]:
        if nome not in doc["quem_paga"]:
            doc["quem_paga"].append(nome)
    sem_tipo = doc["setores"].index(op.SEM_SETOR)
    paga = {e: doc["quem_paga"].index(ESFERAS[e]) for e in (1, 2)}
    linhas = doc["uf"].setdefault(tcesp["uf"], [])
    for nome, cidade, ibge, esfera, situacao, atrasada, valor, ano, orgao, _ in tcesp["obras"]:
        linhas.append([nome, cidade, ibge, sem_tipo, paga[esfera], situacao, None, valor, None, 0, esfera, atrasada,
                       ano, orgao])
    linhas.sort(key=lambda t: (-t[7], t[0]))
    doc["tcesp"] = {"data_base": tcesp["data_base"], "fonte": tcesp["fonte"], "url": tcesp["url"], "uf": tcesp["uf"],
                    "obras": len(tcesp["obras"]), "so_federal": tcesp["so_federal"]}
    return doc


def ler_referencia(arq: Path = REFERENCIA) -> dict | None:
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None


def gravar_site(tcesp: dict | None) -> dict:
    """Refaz os arquivos do explorador: a lista do TCU (cópia de referência) mais as obras do TCE-SP."""
    if not op.REFERENCIA_TODAS.exists():
        sys.exit(f"sem cópia de referência em {op.REFERENCIA_TODAS} (rode uv run obras-paradas antes)")
    todas = json.loads(op.REFERENCIA_TODAS.read_text(encoding="utf-8"))
    return op.gravar_todas(juntar(todas, tcesp))


def main() -> None:
    p = argparse.ArgumentParser(prog="obras-tcesp", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true",
                   help="não baixa o painel: refaz os arquivos do site com a cópia de referência")
    args = p.parse_args()

    if args.sem_baixar:
        tcesp = ler_referencia()
    else:
        try:
            tcesp = montar(baixar())
        except Exception as e:  # sem o painel, o site sai com a cópia de referência
            print(f"painel do TCE-SP indisponível ({e}); o site sai com a cópia de referência")
            gravar_site(ler_referencia())
            sys.exit(3)
        op._gravar(tcesp, REFERENCIA)
        n = Counter((t[3], t[4], t[5]) for t in tcesp["obras"])
        print(f"TCE-SP de {tcesp['data_base']}: {len(tcesp['obras'])} obras "
              f"({sum(v for k, v in n.items() if k[0] == 1)} do estado, {sum(v for k, v in n.items() if k[0] == 2)} "
              f"das prefeituras; {sum(v for k, v in n.items() if k[1] == 1)} paradas, "
              f"{sum(v for k, v in n.items() if k[2] == 1)} atrasadas); R$ "
              f"{sum(t[6] for t in tcesp['obras']) / 1e9:.1f} bi em contratos. Fora: {tcesp['repetidas']} repetidas e "
              f"{tcesp['so_federal'][0]} só com dinheiro federal", flush=True)
    i = gravar_site(tcesp)
    print(f"todas as obras: {i['total'][0]} em {len(i['uf'])} arquivos em {op.SAIDA_TODAS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
