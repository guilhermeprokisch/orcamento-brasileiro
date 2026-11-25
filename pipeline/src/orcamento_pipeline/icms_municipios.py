"""ICMS arrecadado em cada município, para o mapa (hoje só São Paulo).

    uv run icms                 # usa a planilha já baixada, ou baixa da SEFAZ-SP
    uv run icms --forcar        # baixa a planilha de novo

Hoje o mapa estima o ICMS de cada cidade multiplicando por 4 a cota-parte que a prefeitura
recebe. A cota segue um índice (valor adicionado e critérios da lei estadual), não o imposto
recolhido ali. Este módulo troca a estimativa pelo valor oficial, onde o estado publica o
ICMS por município em formato aberto.

São Paulo: "Relatório da Receita Tributária", Tabela 1.10 — ICMS por Região e Município, da
Secretaria da Fazenda e Planejamento (SEFAZ-SP). Um arquivo consolidado histórico, com uma aba
por ano (ArrecMunic-ICMS-AAAA) e colunas Região | Município | jan … dez, em reais mil. Somamos
os doze meses. Limites do dado (observações da própria planilha):

- o valor é contabilizado pelo município do estabelecimento (inscrição estadual) centralizador;
- o ICMS recolhido por substituição tributária fica no município do substituto, não no do
  contribuinte substituído: grandes centros de substituição aparecem inflados;
- Simples Nacional e pessoas físicas entram como "Não Classificado", sem município (~5% do total);
- não inclui multas, juros, parcelamentos (PPI, PEP) nem o FECOEP, e exclui anistias.

Minas Gerais e outros estados: o pedido de LAI foi enviado e ainda não respondeu (ver
docs/pedidos-lai/icms-por-municipio.md). Quando o dado vier, acrescente um leitor aqui e some
aos mesmos arquivos de saída.

Saída: site/public/data/mapa/icms-mun.json = {ano: {ibge: ICMS em reais}}.
A planilha fica em data/raw/sefaz-sp/. Uma cópia de referência fica em pipeline/referencia/icms-mun.json,
usada na publicação quando o portal da SEFAZ-SP não responde (ver .github/scripts/dados.sh).
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT
from .rfb import PRIMEIRO_ANO, casador

PASTA = c.RAIZ / "data" / "raw" / "sefaz-sp"
ARQUIVO = PASTA / "tab110_ICMS_municipios.xlsx"
SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa" / "icms-mun.json"

# A SEFAZ publica o consolidado numa pasta por mês; o endereço muda de mês, mas o arquivo é o
# mesmo (a última versão). Procuramos de trás para frente a partir do mês atual.
URL_BASE = ("https://portal.fazenda.sp.gov.br/acessoinformacao/_layouts/download.aspx?SourceUrl="
            "/acessoinformacao/Downloads/Relatorios-da-Receita-Tributaria/{ano}/{mes}/"
            "tab110_ICMS_Região_Municípios_(2009-2025).xlsx")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Rótulos da coluna "Município" que não são municípios (viram None no casamento, mas listamos
# para não procurá-los nem contá-los como nomes sem par).
NAO_MUNICIPIO = {"total:", "total geral:", "não classificado", "nao classificado",
                 "outros estados", "município", "municipio"}


def _baixar(url: str, tentativas: int = 3) -> bytes:
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
                return resp.read()
        except (OSError, urllib.error.URLError):
            if n == tentativas - 1:
                raise
            time.sleep(5 * 3 ** n)
    raise AssertionError


def baixar_planilha(forcar: bool) -> Path:
    """Baixa o consolidado da SEFAZ-SP se não houver cache (ou com `forcar`). Procura do mês atual
    para trás até achar um arquivo de verdade (começa com 'PK')."""
    PASTA.mkdir(parents=True, exist_ok=True)
    if ARQUIVO.exists() and not forcar:
        return ARQUIVO
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    for _ in range(18):   # até 18 meses para trás
        url = URL_BASE.format(ano=ano, mes=urllib.parse.quote(MESES[mes - 1]))
        try:
            dados = _baixar(url)
        except OSError:
            dados = b""
        if dados.startswith(b"PK"):
            ARQUIVO.write_bytes(dados)
            print(f"  baixado {MESES[mes - 1]}/{ano} ({len(dados) / 1e6:.1f} MB)", flush=True)
            return ARQUIVO
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    if ARQUIVO.exists():
        print("  aviso: não achei o arquivo no portal da SEFAZ-SP; usando o cache", flush=True)
        return ARQUIVO
    raise FileNotFoundError("não achei o consolidado da Tabela 1.10 no portal da SEFAZ-SP")


def _linha_cabecalho(ws) -> int:
    """A linha (1-based) com 'ICMS - Região' | 'Município' | meses. Os dados começam na seguinte."""
    for i, linha in enumerate(ws.iter_rows(max_row=20, values_only=True), start=1):
        b = linha[1] if len(linha) > 1 else None
        if isinstance(b, str) and b.strip().lower() in ("município", "municipio"):
            return i
    raise ValueError(f"cabeçalho não encontrado na aba {ws.title!r}")


def ler_sp(arquivo: Path) -> dict[int, dict[str, float]]:
    """{ano: {ibge: ICMS em reais}} para São Paulo, somando os doze meses de cada município."""
    livro = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    ibge_de = casador()
    saida: dict[int, dict[str, float]] = {}
    sem_par: dict[str, float] = {}
    for aba in livro.worksheets:
        try:
            ano = int(aba.title.rsplit("-", 1)[-1])
        except ValueError:
            continue
        if ano < PRIMEIRO_ANO:
            continue
        cabecalho = _linha_cabecalho(aba)
        ano_doc: dict[str, float] = {}
        for linha in aba.iter_rows(min_row=cabecalho + 1, values_only=True):
            nome = linha[1] if len(linha) > 1 else None
            if not isinstance(nome, str) or not nome.strip() or nome.strip().lower() in NAO_MUNICIPIO:
                continue
            meses = sum(v for v in linha[2:14] if isinstance(v, (int, float)))   # jan..dez, em reais mil
            if meses <= 0:
                continue
            ibge = ibge_de(nome.strip(), "SP")
            if ibge is None:
                sem_par[nome.strip()] = sem_par.get(nome.strip(), 0) + meses
                continue
            ano_doc[ibge] = ano_doc.get(ibge, 0) + meses * 1000   # reais mil -> reais
        saida[ano] = ano_doc
    if sem_par:
        maiores = sorted(sem_par.items(), key=lambda x: -x[1])[:10]
        print("  nomes sem município correspondente: "
              + ", ".join(f"{n} (R$ {v / 1e3:.0f} mi)" for n, v in maiores), flush=True)
    return saida


def main() -> None:
    p = argparse.ArgumentParser(prog="icms", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--forcar", action="store_true", help="baixa a planilha da SEFAZ-SP de novo")
    args = p.parse_args()

    arquivo = baixar_planilha(args.forcar)
    # Quando houver Minas e outros estados, leia cada um e junte aqui, por ano, antes de gravar.
    por_estado = [ler_sp(arquivo)]
    anos: set[int] = set()
    for dados in por_estado:
        anos |= set(dados)

    saida: dict[str, dict[str, int]] = {}
    for ano in sorted(anos):
        doc: dict[str, int] = {}
        for dados in por_estado:
            for ibge, v in dados.get(ano, {}).items():
                doc[ibge] = doc.get(ibge, 0) + round(v)
        saida[str(ano)] = doc
        print(f"{ano}: {len(doc)} municípios, R$ {sum(doc.values()) / 1e9:.1f} bi", flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, separators=(",", ":")))
    print(f"saída: {SAIDA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
