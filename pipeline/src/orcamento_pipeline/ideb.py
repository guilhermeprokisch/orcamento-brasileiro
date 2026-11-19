"""Ideb por município e por rede (municipal e estadual), para pôr a nota ao lado do gasto.

    uv run ideb            # a edição mais recente publicada
    uv run ideb 2023

O Ideb (Índice de Desenvolvimento da Educação Básica, do INEP) sai a cada dois anos e junta
a nota dos alunos numa prova nacional com a taxa de aprovação, numa escala de 0 a 10. As
planilhas "por município" trazem uma linha por município e rede. Aqui ficam duas redes:
- municipal: responsabilidade da prefeitura, vai ao lado do gasto dela em educação;
- estadual: responsabilidade do governo do estado, mostrada como contexto.

Etapas: anos iniciais (1º ao 5º ano) e anos finais (6º ao 9º) do ensino fundamental. O ensino
médio fica de fora por enquanto: é quase todo estadual.

O servidor de downloads do INEP não envia a cadeia de certificados completa; ver
fontes.contexto_tls_com_intermediario.

Cache em data/raw/inep/. Saída em site/public/data/indicadores/ideb.json:
    {"edicao": 2025, "anos": [2005, …], "mun": {ibge: {"mi": […], "mf": […], "ei": […], "ef": […]}}}
com uma nota por ano em cada lista (null quando não há): m/e = rede municipal/estadual,
i/f = anos iniciais/finais.
"""

from __future__ import annotations

import argparse
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import openpyxl

from .cidades import RAIZ
from .fontes import USER_AGENT, contexto_tls_com_intermediario

URL = "https://download.inep.gov.br/ideb/resultados/divulgacao_{etapa}_municipios_{edicao}.zip"
INTERMEDIARIO = "http://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt"
PASTA_BRUTO = RAIZ / "data" / "raw" / "inep"
SAIDA = RAIZ / "site" / "public" / "data" / "indicadores" / "ideb.json"
ETAPAS = {"anos_iniciais": "i", "anos_finais": "f"}
REDES = {"Municipal": "m", "Estadual": "e"}
PRIMEIRA_EDICAO = 2005


def baixar(etapa: str, edicao: int, contexto) -> Path | None:
    """O zip de uma etapa e edição; None se o INEP ainda não publicou essa edição."""
    arq = PASTA_BRUTO / f"divulgacao_{etapa}_municipios_{edicao}.zip"
    if arq.exists():
        return arq
    req = urllib.request.Request(URL.format(etapa=etapa, edicao=edicao), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=300, context=contexto) as resp:
            dados = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not dados.startswith(b"PK"):
        raise RuntimeError(f"{etapa} {edicao}: a resposta do INEP não é um zip")
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_bytes(dados)
    tmp.replace(arq)
    return arq


def ler(arq: Path, anos: list[int]) -> dict[str, dict[str, list[float | None]]]:
    """{ibge: {rede: [nota de cada ano]}} de uma planilha de divulgação."""
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.endswith(".xlsx"))
        wb = openpyxl.load_workbook(io.BytesIO(z.read(nome)), read_only=True)
    linhas = wb.worksheets[0].iter_rows(values_only=True)
    cab = next(l for l in linhas if l and l[0] == "SG_UF")  # a linha com os nomes técnicos das colunas
    col = {str(n): i for i, n in enumerate(cab) if n}
    faltam = [c for c in ("CO_MUNICIPIO", "REDE", f"VL_OBSERVADO_{anos[-1]}") if c not in col]
    if faltam:
        raise RuntimeError(f"{arq.name}: colunas não encontradas: {faltam}")
    notas: dict[str, dict[str, list[float | None]]] = {}
    for l in linhas:
        rede = REDES.get(str(l[col["REDE"]] or "").strip())
        ibge = str(l[col["CO_MUNICIPIO"]] or "").strip()
        if not rede or not ibge.isdigit():
            continue
        serie: list[float | None] = []
        for ano in anos:
            v = l[col[f"VL_OBSERVADO_{ano}"]] if f"VL_OBSERVADO_{ano}" in col else None
            try:
                serie.append(round(float(str(v).replace(",", ".")), 1))
            except (TypeError, ValueError):  # "-", "ND", "*" e vazios: sem nota nesse ano
                serie.append(None)
        if any(x is not None for x in serie):
            notas.setdefault(ibge, {})[rede] = serie
    return notas


def main() -> None:
    p = argparse.ArgumentParser(prog="ideb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("edicao", type=int, nargs="?", help="ano da edição (ímpar); padrão: a mais recente publicada")
    args = p.parse_args()
    contexto = contexto_tls_com_intermediario(INTERMEDIARIO)

    ultimo_impar = date.today().year - (date.today().year + 1) % 2
    candidatas = [args.edicao] if args.edicao else [ultimo_impar, ultimo_impar - 2]
    for edicao in candidatas:
        arquivos = {etapa: baixar(etapa, edicao, contexto) for etapa in ETAPAS}
        if all(arquivos.values()):
            break
    else:
        raise SystemExit(f"o INEP não tem as planilhas das edições {candidatas}")

    anos = list(range(PRIMEIRA_EDICAO, edicao + 1, 2))
    mun: dict[str, dict[str, list[float | None]]] = {}
    for etapa, sufixo in ETAPAS.items():
        for ibge, redes in ler(arquivos[etapa], anos).items():
            for rede, serie in redes.items():
                mun.setdefault(ibge, {})[rede + sufixo] = serie
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"edicao": edicao, "fonte": "INEP, Ideb por município e rede", "anos": anos, "mun": mun}, separators=(",", ":")))
    com = lambda k: sum(1 for m in mun.values() if k in m and m[k][-1] is not None)
    print(f"Ideb {edicao}: {len(mun)} municípios; com nota em {edicao}: rede municipal {com('mi')} (anos iniciais) e {com('mf')} (anos finais); "
          f"rede estadual {com('ei')} e {com('ef')}")


if __name__ == "__main__":
    main()
