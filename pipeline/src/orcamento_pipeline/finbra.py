"""Importa arquivos do FINBRA (SICONFI) baixados à mão para o cache da DCA.

    uv run finbra ~/Downloads/finbra          # lê todos os .zip e .csv da pasta
    uv run finbra ~/Downloads/finbra --substituir

O FINBRA entrega, por exercício e anexo, um arquivo com todos os municípios de
uma vez, o que evita ~5.570 consultas por ano à API. O download, porém, é
protegido por hCaptcha (https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf),
então uma pessoa baixa os arquivos e este comando só os lê. Uso pensado para o
histórico (anos fechados há tempo, que não mudam); os anos recentes continuam
vindo da API, que pega entregas atrasadas e retificações.

Destino, no mesmo formato do cache da API (ver cidades.CacheAno):
- despesa por função (Anexo I-E) -> data/raw/siconfi/dca-ie/{ano}.json.gz
- receitas orçamentárias (Anexo I-C) -> data/raw/siconfi/dca-ic/{ano}.json.gz
- despesa por natureza (Anexo I-D) -> data/raw/siconfi/dca-id/{ano}.json.gz
- balanço patrimonial (Anexo I-AB) -> data/raw/siconfi/dca-iab/{ano}.json.gz

Por padrão só preenche entes que ainda não estão no cache (a API, mais nova,
tem prioridade); `--substituir` sobrescreve.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

from .cidades import CacheAno

CAMPOS_RECEITA = ("coluna", "conta", "cod_conta", "valor", "populacao")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# Nome normalizado do cabeçalho -> campo do cache.
CABECALHO = {
    "codibge": "ibge", "codigoibge": "ibge", "ibge": "ibge", "codigomunicipio": "ibge",
    "uf": "uf", "populacao": "populacao", "coluna": "coluna", "conta": "conta",
    "identificadordaconta": "cod_conta", "codconta": "cod_conta", "valor": "valor",
    "instituicao": "instituicao", "exercicio": "exercicio",
}


def _texto(dados: bytes) -> str:
    for cod in ("utf-8-sig", "latin-1"):
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    raise ValueError("codificação desconhecida")


def _numero(v: str) -> float:
    v = v.strip().replace("R$", "").replace(" ", "")
    if not v:
        return 0.0
    if "," in v:  # formato brasileiro: 1.234.567,89
        v = v.replace(".", "").replace(",", ".")
    return float(v)


# Anexo da DCA (linha "Tabela: ... (Anexo I-X)" do arquivo) -> pasta do cache.
ANEXOS = {"I-E": "dca-ie", "I-C": "dca-ic", "I-D": "dca-id", "I-AB": "dca-iab"}


def ler_tabela(texto: str, nome: str) -> tuple[int | None, str | None, list[dict]]:
    """Acha a linha de cabeçalho (o FINBRA põe linhas de descrição antes) e devolve (ano, anexo, linhas)."""
    linhas = texto.splitlines()
    ano = anexo = None
    for i, linha in enumerate(linhas[:30]):
        campos = [_norm(c) for c in linha.split(";")]
        mapeados = [CABECALHO.get(c) for c in campos]
        if {"ibge", "conta", "valor"} <= set(filter(None, mapeados)):
            corpo = csv.reader(io.StringIO("\n".join(linhas[i + 1:])), delimiter=";")
            registros = []
            for valores in corpo:
                if len(valores) < len(mapeados):
                    continue
                r = {campo: valores[j].strip() for j, campo in enumerate(mapeados) if campo}
                registros.append(r)
            if ano is None and registros and registros[0].get("exercicio", "").isdigit():
                ano = int(registros[0]["exercicio"])
            return ano, anexo, registros
        a = re.search(r"Anexo\s+(I-[A-Z]+)", linha)
        if anexo is None and a:
            anexo = a.group(1)
        m = re.search(r"\b(20\d\d|19\d\d)\b", linha)
        if ano is None and m and re.search(r"exerc", _norm(linha)):
            ano = int(m.group(1))
    raise ValueError(f"{nome}: não achei o cabeçalho (Cod.IBGE, Conta, Valor) nas primeiras 30 linhas")


def arquivos(pasta: Path):
    """(nome, texto) de cada arquivo do FINBRA na pasta: zips que contêm finbra.csv e CSVs soltos.

    A pasta pode ser a de Downloads: zips de outras coisas são ignorados.
    """
    for p in sorted(pasta.iterdir()):
        if p.suffix.lower() == ".zip" and zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                for m in z.namelist():
                    if m.lower() == "finbra.csv":
                        yield f"{p.name}/{m}", _texto(z.read(m))
        elif p.suffix.lower() == ".csv" and p.name.lower().startswith("finbra"):
            yield p.name, _texto(p.read_bytes())


def importar(nome: str, texto: str, ano_forcado: int | None, substituir: bool) -> str:
    ano, anexo_dca, registros = ler_tabela(texto, nome)
    if ano is None:
        m = re.search(r"(20\d\d)", nome)
        ano = ano_forcado or (int(m.group(1)) if m else None)
    if ano is None:
        raise ValueError(f"{nome}: não achei o exercício; use --ano")
    # O anexo vem da linha "Tabela:" do arquivo, não das colunas: o I-D (despesa por natureza)
    # tem as mesmas colunas do I-E (por função) e seria misturado com ele.
    if anexo_dca not in ANEXOS:
        raise ValueError(f"{nome}: tabela {anexo_dca or 'não identificada'} não suportada (aceito {', '.join(ANEXOS)})")
    anexo = ANEXOS[anexo_dca]
    filtro = None if anexo == "dca-ie" else (lambda itens: [{k: i.get(k) for k in CAMPOS_RECEITA} for i in itens])

    por_ente: dict[str, list[dict]] = defaultdict(list)
    for r in registros:
        ibge = re.sub(r"\D", "", r.get("ibge", ""))
        if not ibge:
            continue
        por_ente[ibge].append({
            # Algumas contas trazem aspas sem escape no meio do texto (ex.: Transmissão "Inter Vivos").
            "coluna": r.get("coluna"), "conta": (r.get("conta") or "").replace('"', ""), "cod_conta": r.get("cod_conta"),
            "valor": _numero(r.get("valor", "")),
            "populacao": int(_numero(r["populacao"])) if r.get("populacao") else None,
        })

    cache = CacheAno(ano, anexo=anexo, filtro=filtro)
    novos = ja = 0
    for ibge, itens in por_ente.items():
        if cache.obter(int(ibge)) and not substituir:
            ja += 1
            continue
        cache.guardar(int(ibge), itens)
        novos += 1
    cache.salvar()
    return f"{nome}: {anexo} {ano}, {len(por_ente)} entes ({novos} gravados, {ja} já estavam no cache)"


def main() -> None:
    p = argparse.ArgumentParser(prog="finbra", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pasta", type=Path, help="pasta com os .zip/.csv baixados do FINBRA")
    p.add_argument("--ano", type=int, help="exercício, se não der para tirar do arquivo")
    p.add_argument("--substituir", action="store_true", help="sobrescreve o que já está no cache")
    args = p.parse_args()
    falhas = 0
    for nome, texto in arquivos(args.pasta.expanduser()):
        try:
            print(importar(nome, texto, args.ano, args.substituir), flush=True)
        except ValueError as e:
            falhas += 1
            print(f"ERRO {e}", flush=True)
    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
