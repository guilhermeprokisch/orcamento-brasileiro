"""As escolas da rede municipal de cada cidade: alunos, Ideb de cada uma e o dinheiro do PDDE.

    uv run escolas

Três fontes, juntas pela escola:
- Censo Escolar (INEP, microdados): cada escola em atividade, com a rede (municipal, estadual), o
  bairro e o número de alunos da educação básica. O ano mais recente com microdados publicados.
- Ideb por escola (INEP): a nota dos anos iniciais e dos anos finais na edição mais recente.
- PDDE, Dinheiro Direto na Escola (FNDE, pelos arquivos de transferências do Portal da
  Transparência, já baixados por federal.py): o dinheiro federal que vai para o conselho ou a caixa
  escolar de cada escola. O Portal traz o nome e o CNPJ do conselho, não o código da escola: o
  conselho é casado com a escola pelo nome, dentro da cidade ("CONSELHO ESCOLAR ELDA CAVALCANTE" com
  "EEF ELDA CAVALCANTE"). O que não casa fica só no total da cidade.

Como o INEP derruba conexões de fora do país (o caso do GitHub), o resultado também fica em
pipeline/referencia/escolas.json; sem o download, a saída é copiada de lá.

Saída em site/public/data/indicadores/escolas.json:
    {"fonte", "censo": 2024, "ideb": 2025, "pdde": 2025,
     "mun": {ibge: {"escolas": [[código INEP, nome, bairro, alunos, Ideb iniciais, Ideb finais, PDDE], ...],
                    "estaduais": escolas estaduais na cidade,
                    "pdde": [total na cidade, conselhos, valor casado com escolas municipais]}}}
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl

from .cidades import RAIZ
from .federal import PASTA_BRUTO as PASTA_PORTAL, siafi_para_ibge
from .fontes import USER_AGENT, contexto_tls_com_intermediario
from .ideb import INTERMEDIARIO

PASTA = RAIZ / "data" / "raw" / "inep"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "escolas.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "escolas.json"
URL_CENSO = "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ano}.zip"
URL_IDEB = "https://download.inep.gov.br/ideb/resultados/divulgacao_{etapa}_escolas_{edicao}.zip"
FONTE = "INEP (Censo Escolar e Ideb por escola) e FNDE, pelo Portal da Transparência (PDDE)"

# Palavras que não ajudam a reconhecer a escola: tipo de escola, rede, etapa, preposições e o
# começo do nome do conselho ("CONSELHO ESCOLAR", "CAIXA ESCOLAR", "APM DA" …).
VAZIAS = set("""
DE DA DO DAS DOS E A O AS OS EM NO NA
ESCOLA ESCOLAS ESCOLAR MUNICIPAL ESTADUAL MUN EST ENSINO FUNDAMENTAL MEDIO INFANTIL EDUCACAO BASICA
EMEF EMEI EMEIEF EMEB EMEFI EMEIF EM EE EEF EEEF EEEFM EEEM EF EI CEI CMEI CEMEI CMEF CEF CE CEU UE UEX
CENTRO CRECHE PRE NUCLEO INTEGRADO INTEGRAL TEMPO GRAU 1 2 I II III PROF PROFA PROFESSOR PROFESSORA DR DRA
CONSELHO CAIXA ASSOCIACAO ASSOC PAIS MESTRES MESTRE APM A.P.M APMC CPM CIRCULO UNIDADE EXECUTORA COMUNIDADE
COMUNITARIA COMUNITARIO DELIBERATIVO AMIGOS DIRETOR DIRETORES FUNCIONARIOS ALUNOS
""".split())


def palavras(nome: str) -> frozenset[str]:
    s = unicodedata.normalize("NFKD", nome.upper()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return frozenset(p for p in s.split() if p not in VAZIAS and len(p) > 1)


def baixar(url: str, destino: Path, contexto) -> Path | None:
    """Baixa um .zip do INEP; um arquivo estragado (corte no meio, página de erro) é apagado e conta como falha."""
    if destino.exists():
        if zipfile.is_zipfile(destino):
            return destino
        destino.unlink()   # o cache guardou um arquivo estragado: baixa de novo
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=600, context=contexto) as resp:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(resp.read())
        if not zipfile.is_zipfile(destino):
            destino.unlink()
            raise ValueError("o arquivo baixado não é um .zip")
        return destino
    except Exception as erro:   # o INEP recusa conexões de fora do país
        print(f"  {url}: {erro}", flush=True)
        return None


def censo(arq: Path) -> dict[str, list]:
    """INEP → [município, nome, bairro, rede (2 estadual, 3 municipal), alunos], só escolas em atividade."""
    escolas = {}
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if re.search(r"microdados_ed_basica_\d{4}\.csv$", n))
        with z.open(nome) as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";"):
                if r["TP_SITUACAO_FUNCIONAMENTO"] != "1" or r["TP_DEPENDENCIA"] not in ("2", "3"):
                    continue
                escolas[r["CO_ENTIDADE"]] = [r["CO_MUNICIPIO"], r["NO_ENTIDADE"].strip(), (r["NO_BAIRRO"] or "").strip(),
                                             int(r["TP_DEPENDENCIA"]), int(r["QT_MAT_BAS"] or 0)]
    return escolas


def ideb(arq: Path, edicao: int) -> dict[str, float]:
    """INEP → Ideb da escola na edição (só quem teve nota)."""
    notas = {}
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.endswith(".xlsx"))
        wb = openpyxl.load_workbook(io.BytesIO(z.read(nome)), read_only=True)
        cab = None
        for r in wb.worksheets[0].iter_rows(values_only=True):
            if cab is None:
                if r and r[0] == "SG_UF":
                    cab = {c: i for i, c in enumerate(r) if c}
                continue
            v = r[cab[f"VL_OBSERVADO_{edicao}"]] if f"VL_OBSERVADO_{edicao}" in cab else None
            if r[cab["ID_ESCOLA"]] and isinstance(v, (int, float)):
                notas[str(r[cab["ID_ESCOLA"]])] = round(float(v), 1)
    return notas


def pdde(ano: int) -> dict[str, dict[str, list]]:
    """Portal da Transparência → ibge → CNPJ do conselho → [nome, valor] (ação 0515, o PDDE)."""
    siafi = siafi_para_ibge()
    por = defaultdict(lambda: defaultdict(lambda: ["", 0.0]))
    for mes in range(1, 13):
        arq = PASTA_PORTAL / "transferencias" / f"{ano}{mes:02d}_Transferencias.zip"
        if not arq.exists():
            continue
        with zipfile.ZipFile(arq) as z, z.open(z.namelist()[0]) as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";"):
                if r["AÇÃO"] != "0515" or r["TIPO FAVORECIDO"] != "Entidades Sem Fins Lucrativos":
                    continue
                ibge = siafi.get(r["CÓDIGO MUNICÍPIO SIAFI"].strip())
                if not ibge:
                    continue
                c = por[ibge][r["CÓDIGO FAVORECIDO"]]
                c[0] = r["NOME FAVORECIDO"].strip()
                c[1] += float(r["VALOR TRANSFERIDO"].replace(".", "").replace(",", ".") or 0)
    return por


def casar(escolas: list[tuple[str, frozenset]], conselhos: list[tuple[str, frozenset]]) -> dict[str, str]:
    """Conselho → escola, pelo nome, na mesma cidade. Só casa quando a melhor escola é clara."""
    casados = {}
    for cnpj, pc in conselhos:
        if not pc:
            continue
        notas = sorted(((len(pc & pe) / len(pc | pe), inep) for inep, pe in escolas if pe and pc & pe), reverse=True)
        if not notas:
            continue
        melhor, inep = notas[0]
        segunda = notas[1][0] if len(notas) > 1 else 0
        if melhor >= 0.6 and melhor - segunda >= 0.2:
            casados[cnpj] = inep
    return casados


def usar_referencia(motivo: str) -> None:
    """Sem dados novos do INEP, a página sai com a última cópia boa (pipeline/referencia/escolas.json)."""
    if REFERENCIA.exists():
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        SAIDA.write_text(REFERENCIA.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"{motivo}: saída copiada de {REFERENCIA.relative_to(RAIZ)}", flush=True)
    else:
        print(f"{motivo}: sem cópia de referência", flush=True)


def main() -> None:
    hoje = date.today()
    contexto = contexto_tls_com_intermediario(INTERMEDIARIO)
    arq_censo = next((a for ano in range(hoje.year - 1, hoje.year - 4, -1)
                      if (a := baixar(URL_CENSO.format(ano=ano), PASTA / f"microdados_censo_escolar_{ano}.zip", contexto))), None)
    edicao = hoje.year - 1 if hoje.year % 2 == 0 else hoje.year - 2   # o Ideb sai nos anos ímpares, no ano seguinte
    arqs_ideb = {etapa: baixar(URL_IDEB.format(etapa=etapa, edicao=edicao), PASTA / f"divulgacao_{etapa}_escolas_{edicao}.zip", contexto)
                 for etapa in ("anos_iniciais", "anos_finais")}
    if not arq_censo or not all(arqs_ideb.values()):
        usar_referencia("sem o download do INEP")
        return
    ano_censo = int(re.search(r"(\d{4})", arq_censo.name).group(1))
    try:
        escolas = censo(arq_censo)
        ini, fin = ideb(arqs_ideb["anos_iniciais"], edicao), ideb(arqs_ideb["anos_finais"], edicao)
    except (zipfile.BadZipFile, StopIteration, KeyError, UnicodeDecodeError) as erro:
        usar_referencia(f"arquivo do INEP ilegível ({erro!r})")
        return
    print(f"Censo Escolar {ano_censo}: {len(escolas)} escolas municipais e estaduais em atividade", flush=True)
    print(f"Ideb {edicao}: {len(ini)} escolas nos anos iniciais, {len(fin)} nos finais", flush=True)
    ano_pdde = hoje.year - 1
    conselhos = pdde(ano_pdde)

    por_cidade = defaultdict(list)
    for inep, (mun, nome, bairro, rede, alunos) in escolas.items():
        por_cidade[mun].append((inep, nome, bairro, rede, alunos))
    saida, n_casados, valor_casado, valor_total = {}, 0, 0.0, 0.0
    for mun, lista in por_cidade.items():
        cs = conselhos.get(mun, {})
        casados = casar([(e[0], palavras(e[1])) for e in lista], [(cnpj, palavras(n)) for cnpj, (n, _) in cs.items()])
        dinheiro = defaultdict(float)
        for cnpj, inep in casados.items():
            dinheiro[inep] += cs[cnpj][1]
        municipais = sorted((e for e in lista if e[3] == 3), key=lambda e: -e[4])
        casado_mun = sum(dinheiro[e[0]] for e in municipais)
        total = sum(v for _, v in cs.values())
        n_casados += len(casados)
        valor_casado += sum(dinheiro.values())
        valor_total += total
        if not municipais and not total:
            continue
        saida[mun] = {
            "escolas": [[e[0], e[1], e[2], e[4], ini.get(e[0]), fin.get(e[0]), round(dinheiro[e[0]]) or None] for e in municipais],
            "estaduais": sum(1 for e in lista if e[3] == 2),
            "pdde": [round(total), len(cs), round(casado_mun)],
        }
    doc = {"fonte": FONTE, "censo": ano_censo, "ideb": edicao, "pdde": ano_pdde, "mun": dict(sorted(saida.items()))}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    total_conselhos = sum(len(v) for v in conselhos.values())
    print(f"PDDE {ano_pdde}: {n_casados} de {total_conselhos} conselhos casados com uma escola "
          f"({valor_casado / max(valor_total, 1):.0%} do dinheiro)")
    print(f"saída: {SAIDA.relative_to(RAIZ)} e {REFERENCIA.relative_to(RAIZ)} ({len(texto) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
