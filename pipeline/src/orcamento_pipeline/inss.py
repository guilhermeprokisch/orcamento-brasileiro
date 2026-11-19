"""Benefícios do INSS (RGPS) pagos em cada município, por ano.

    uv run inss                 # 2013 até o último ano publicado
    uv run inss --anos 2024 2025

Fonte: Ministério da Previdência Social, "Estatísticas Municipais", benefícios emitidos por
município (um XLSX por ano, 2-3 MB, com o código IBGE de 7 dígitos):
https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/estatisticas-municipais-2000-a-2022

Usa só o total de benefícios **previdenciários** (aposentadorias, pensões, auxílios). A coluna
de benefícios assistenciais fica de fora de propósito: ela inclui o BPC, que o mapa já traz do
Portal da Transparência.

Três ressalvas que a página do mapa repete:
- o valor é registrado no município da agência que paga, não no de residência: cidades sem
  agência bancária ficam subestimadas e as cidades-polo, infladas;
- é o valor líquido (depois de descontos como imposto de renda e consignado), cerca de 10%
  abaixo do bruto;
- benefícios de legislação específica (fora do RGPS e do BPC) não entram.

Saída: site/public/data/mapa/inss/{ano}.json = {ibge: [total, aposentadorias, pensões]}.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA_BRUTO = RAIZ / "data" / "raw" / "previdencia"
SAIDA = RAIZ / "site" / "public" / "data" / "mapa" / "inss"
BASE = "https://www.gov.br/previdencia/pt-br"


def url_do_ano(ano: int) -> str:
    """Os nomes dos arquivos não seguem um padrão único (conferido em 19/11/2026)."""
    if 2010 <= ano <= 2016:
        return f"{BASE}/outros/imagens/2018/02/Municipiosa_emitidosa_especiesa_{ano}a_divulgaa_o.xlsx"
    if ano == 2018:
        return f"{BASE}/outros/imagens/2020/02/bena_municipiosa_especiea_2018.xlsx"
    return f"{BASE}/assuntos/previdencia-social/arquivos/ben_municipios_especie_{ano}.xlsx"


def baixar(ano: int) -> Path:
    arq = PASTA_BRUTO / f"emitidos-municipios-{ano}.xlsx"
    if arq.exists():
        return arq
    PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
    # O gov.br recusa clientes sem identificação de navegador (403): o prefixo "Mozilla/5.0
    # (compatible; …)" é o formato padrão de robôs que se identificam.
    req = urllib.request.Request(url_do_ano(ano), headers={"User-Agent": f"Mozilla/5.0 (compatible; {USER_AGENT})"})
    with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
        dados = resp.read()
    if not dados.startswith(b"PK"):
        raise RuntimeError(f"INSS {ano}: a resposta não é um XLSX")
    arq.write_bytes(dados)
    return arq


def _norm(v) -> str:
    s = unicodedata.normalize("NFD", str(v or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ler(arq: Path, ano: int) -> dict[str, list[int]]:
    """{ibge: [total previdenciário, aposentadorias, pensões por morte]} em reais, no ano."""
    wb = load_workbook(arq, read_only=True, data_only=True)
    try:
        # A aba do valor anual muda de nome: "2013 - V", "Valor (R$) - 2019", "Valor_Total_2025".
        candidatas = [ws for ws in wb.worksheets
                      if str(ano) in ws.title and re.search(r"valor|\bv\b", _norm(ws.title)) and "dez" not in _norm(ws.title)]
        if not candidatas:
            raise RuntimeError(f"INSS {ano}: não achei a aba do valor anual entre {wb.sheetnames}")
        ws = candidatas[0]
        col: dict[str, int] = {}
        resultado: dict[str, list[int]] = {}
        for n, linha in enumerate(ws.iter_rows(values_only=True)):
            if n < 12 and len(col) < 3:  # cabeçalho em três linhas mescladas
                for j, v in enumerate(linha[:15]):  # até 2017 há uma segunda tabela, por UF, mais à direita
                    t = _norm(v)
                    if t.startswith("total de beneficios previdenciarios"):
                        col["total"] = j
                    elif t.startswith("total de aposentadorias"):
                        col["apos"] = j
                    elif t.startswith("pensoes por morte"):
                        col["pens"] = j
            ibge = next((str(v).strip().split(".")[0] for v in linha[:3] if re.fullmatch(r"\d{7}(\.0)?", str(v).strip())), None)
            if not ibge:
                continue
            if len(col) < 3:
                raise RuntimeError(f"INSS {ano}: cabeçalho incompleto na aba {ws.title!r}: {col}")
            num = lambda k: round(float(linha[col[k]] or 0))  # noqa: E731
            resultado[ibge] = [num("total"), num("apos"), num("pens")]
        return resultado
    finally:
        wb.close()


def main() -> None:
    p = argparse.ArgumentParser(prog="inss", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--anos", type=int, nargs="+", default=list(range(2013, date.today().year)))
    args = p.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)
    for ano in sorted(args.anos):
        try:
            dados = ler(baixar(ano), ano)
        except urllib.error.HTTPError as e:
            print(f"{ano}: não publicado ({e.code})", flush=True)
            continue
        (SAIDA / f"{ano}.json").write_text(json.dumps(dados, separators=(",", ":")))
        print(f"{ano}: {len(dados)} municípios, R$ {sum(v[0] for v in dados.values()) / 1e9:.1f} bi em benefícios previdenciários", flush=True)


if __name__ == "__main__":
    main()
