"""Imposto de renda das pessoas físicas pela cidade onde moram (Receita Federal, Grandes Números do IRPF).

    uv run irpf

A arrecadação por município (rfb.py) mostra onde o imposto foi recolhido: o imposto descontado do
salário entra na cidade da sede da empresa, não na de quem trabalha. Aqui é o contrário: a Receita
soma as declarações de imposto de renda pela cidade de residência de quem declara (Tabela 13 das
"Grandes Números do IRPF", formulários completo e simplificado). Fica o imposto devido no ano,
que é o descontado do salário mais o pago na declaração, menos o que a pessoa recebe de volta.

Os anos vêm da página das Grandes Números: cada edição tem uma planilha de tabelas
("GN_IRPF_AC2024.xlsx"). O ano é o ano-calendário (o dos rendimentos), não o da declaração.

Cache em data/raw/receita-federal/irpf/. Saída em site/public/data/mapa/irpf-res.json:
    {"fonte": …, "anos": {"2024": {ibge: [declarantes, imposto devido]}}}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

from . import cidades as c
from .rfb import _baixar, _so_letras, casador

LISTA = ("https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/estudos/imposto-de-renda/"
         "estudos-por-ano/grandes-numeros-do-IRPF-2008-a-2025")
PASTA = c.RAIZ / "data" / "raw" / "receita-federal" / "irpf"
SAIDA = c.RAIZ / "site" / "public" / "data" / "mapa" / "irpf-res.json"
PRIMEIRO_ANO = 2022   # a Tabela 13 por município existe nas edições a partir desta
FONTE = "Receita Federal, Grandes Números do IRPF (Tabela 13, por município de residência do declarante)"


def edicoes() -> dict[int, str]:
    """ano-calendário -> endereço da página da planilha de tabelas, pelas páginas da lista."""
    achadas: dict[int, str] = {}
    for inicio in (0, 20, 40, 60):
        pagina = _baixar(f"{LISTA}?b_start:int={inicio}").decode("utf-8", "replace")
        for url, ano in re.findall(r'href="(https://[^"]*grandes-numeros-do-irpf-\d{4}-ano-calendario-(\d{4})-tabelas[^"/]*)', pagina):
            achadas.setdefault(int(ano), url.removesuffix("/view"))
    return {a: u for a, u in achadas.items() if a >= PRIMEIRO_ANO}


def baixar(ano: int, url: str) -> Path:
    destino = PASTA / f"GN_IRPF_AC{ano}.xlsx"
    if not destino.exists():
        PASTA.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(_baixar(f"{url}/@@download/file"))
        print(f"  baixado {destino.name} ({destino.stat().st_size / 1e6:.0f} MB)", flush=True)
    return destino


def ler(arquivo: Path, ibge_de) -> dict[str, list[float]]:
    livro = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    aba = next(w for w in livro.worksheets
               if "municipio" in _so_letras(str(next(w.iter_rows(max_row=1, values_only=True))[0] or "")))
    por: dict[str, list[float]] = {}
    col: dict[str, int] = {}
    sem_par = 0
    for linha in aba.iter_rows(values_only=True):
        if not col:
            if linha and linha[0] == "tipo_formulario":
                col = {str(x): i for i, x in enumerate(linha) if x}
            continue
        nome = str(linha[col["descricao"]] or "")
        if not (m := re.fullmatch(r"(.+) - ([A-Z]{2})", nome.strip())):
            continue
        ibge = ibge_de(m.group(1), m.group(2))
        if ibge is None:
            sem_par += 1
            continue
        v = por.setdefault(ibge, [0, 0.0])
        v[0] += int(linha[col["qtde_contribuintes"]] or 0)
        v[1] += float(linha[col["imposto_devido_total"]] or 0)
    if sem_par:
        print(f"  {sem_par} linhas sem município correspondente", flush=True)
    return por


def main() -> None:
    ibge_de = casador()
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")).get("anos", {}) if SAIDA.exists() else {}
    anos: dict[str, dict[str, list]] = dict(anterior)
    for ano, url in sorted(edicoes().items()):
        try:
            por = ler(baixar(ano, url), ibge_de)
        except Exception as erro:   # uma edição com outro formato não derruba as outras
            print(f"{ano}: não deu para ler ({erro})", flush=True)
            continue
        anos[str(ano)] = {k: [n, round(v)] for k, (n, v) in sorted(por.items())}
        total = sum(v for _, v in por.values())
        print(f"{ano}: {len(por)} municípios, R$ {total / 1e9:.1f} bi de imposto devido", flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"fonte": FONTE, "anos": dict(sorted(anos.items()))}, separators=(",", ":")), encoding="utf-8")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({SAIDA.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
