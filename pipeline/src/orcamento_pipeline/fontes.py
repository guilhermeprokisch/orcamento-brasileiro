"""Download dos arquivos brutos do Portal da Transparência."""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

# Orçamento da despesa: um zip por exercício (2014 em diante), com um CSV
# em latin-1, separado por ";", no nível órgão × UO × função × programa × ação × elemento.
URL_ORCAMENTO_DESPESA = (
    "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/"
    "orcamento-despesa/{ano}_OrcamentoDespesa.zip"
)

USER_AGENT = "orcamento-br-pipeline/0.1"


def baixar_orcamento_despesa(ano: int, destino: Path, forcar: bool = False) -> Path:
    """Baixa e extrai o CSV do orçamento da despesa de um exercício.

    Retorna o caminho do CSV. Não baixa de novo se o CSV já existir, a menos
    que `forcar` seja verdadeiro (o ano corrente muda todo dia).
    """
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{ano}_OrcamentoDespesa.csv"
    if csv.exists() and not forcar:
        return csv

    url = URL_ORCAMENTO_DESPESA.format(ano=ano)
    zip_path = destino / f"{ano}_OrcamentoDespesa.zip"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp, zip_path.open("wb") as out:
        shutil.copyfileobj(resp, out)

    with zipfile.ZipFile(zip_path) as zf:
        membros = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if len(membros) != 1:
            raise RuntimeError(f"{zip_path.name}: esperava 1 CSV, encontrei {membros}")
        # Extrai pelo nome esperado, nunca pelo caminho que vem dentro do zip.
        with zf.open(membros[0]) as src, csv.open("wb") as out:
            shutil.copyfileobj(src, out)

    zip_path.unlink()
    return csv
