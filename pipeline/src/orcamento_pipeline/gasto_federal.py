"""O que o governo federal gasta ele mesmo em cada cidade (universidades, hospitais, quartéis…).

    uv run gasto-federal 2025              # baixa a execução da despesa do ano e a tabela de unidades
    uv run gasto-federal 2025 --sem-baixar # só copia pipeline/referencia/gasto-federal-direto.json

Fontes (ver docs/levantamento-gasto-federal-direto.md):

- Portal da Transparência (CGU), "Execução da despesa": um zip por mês (~6 MB), com o valor pago
  por unidade gestora (UG), órgão, ação e elemento de despesa.
- Compras.gov.br, tabela de unidades (UASG): a cidade de cada unidade. Nas unidades federais, o
  código da UASG é o mesmo da UG no SIAFI.

O gasto vai para a cidade da unidade que pagou. Entra só a aplicação direta (modalidade 90) em
pessoal da ativa, custeio e investimentos; ficam de fora os repasses (já na camada "Dinheiro
federal" do mapa), os benefícios pagos a pessoas (INSS, BPC, Bolsa Família, seguro-desemprego e
abono, que seguem quem recebe), aposentadorias e pensões de servidores, subvenções a bancos,
precatórios e a dívida.

Problema conhecido: muito gasto fica registrado na sede do órgão. A folha do Exército é paga em
Brasília, a da Marinha e a da Aeronáutica no Rio, os remédios e vacinas comprados pelo Ministério
da Saúde e as obras do DNIT aparecem em Brasília. O arquivo de saída guarda essas somas para o
site avisar.

Saída: site/public/data/federal/gasto-direto.json, com cópia em pipeline/referencia/ (usada com
--sem-baixar ou se o download falhar: o Portal às vezes responde com CAPTCHA).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

PASTA_EXECUCAO = RAIZ / "data" / "raw" / "portal-transparencia" / "despesas-execucao"
PASTA_UASG = RAIZ / "data" / "raw" / "compras"
SAIDA = RAIZ / "site" / "public" / "data" / "federal" / "gasto-direto.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "gasto-federal-direto.json"
URL_EXECUCAO = ("https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/"
                "despesas-execucao/{am}_Despesas.zip")
URL_UASG = "https://dadosabertos.compras.gov.br/modulo-uasg/1_consultarUasg?pagina={p}&statusUasg={s}"
FONTE = "Portal da Transparência (CGU), execução da despesa; Compras.gov.br, cidade de cada unidade (UASG)"

BRASILIA = "5300108"
# Benefícios pagos a pessoas (seguem quem recebe, não a unidade que paga), aposentadorias e
# pensões de servidores, subvenções econômicas e sentenças judiciais.
ELEMENTOS_FORA = {
    "01": "aposentadorias e pensões de servidores", "03": "aposentadorias e pensões de servidores",
    "05": "benefícios a pessoas", "06": "benefícios a pessoas", "08": "benefícios a pessoas",
    "09": "benefícios a pessoas", "10": "benefícios a pessoas", "48": "benefícios a pessoas",
    "53": "benefícios a pessoas", "54": "benefícios a pessoas", "55": "benefícios a pessoas",
    "56": "benefícios a pessoas", "57": "benefícios a pessoas", "58": "benefícios a pessoas",
    "59": "benefícios a pessoas", "86": "benefícios a pessoas",
    "45": "subvenções econômicas", "91": "sentenças judiciais",
}
# Fundo do Regime Geral (aposentadorias do INSS) e Fundo de Amparo ao Trabalhador (seguro e abono).
UO_FORA = {"33904": "benefícios a pessoas", "40901": "benefícios a pessoas"}
GRUPOS = {"1": "pessoal", "3": "custeio", "4": "obras"}
# Unidades que pagam daqui a folha de servidores de outras cidades.
FOLHA_CENTRAL = re.compile(r"FOLHA DE PAGAMENTO|PAGAMENTO DE PESSOAL|PAGADORIA|CENTRO DE PAGAMENTO|"
                           r"SUBDIRETORIA DE PAGAMENTO|PAGAMENTO DE INATIVOS")
MAIORES = 6


def _baixar(url: str, destino: Path, zip_: bool) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
            dados = resp.read()
        if zip_ and not dados.startswith(b"PK"):
            raise RuntimeError(f"{url}: a resposta não é um zip (o Portal pode estar pedindo CAPTCHA)")
        destino.write_bytes(dados)
    return destino


def unidades() -> dict[str, tuple[str, str, str]]:
    """{código da UG: (IBGE, UF, município)} pela tabela de UASGs ativas e inativas."""
    mapa: dict[str, tuple[str, str, str]] = {}
    for status in ("true", "false"):
        p, total = 1, 1
        while p <= total:
            arq = PASTA_UASG / f"uasg-{status}-{p}.json"
            if not arq.exists():
                _baixar(URL_UASG.format(p=p, s=status), arq, zip_=False)
                time.sleep(0.5)
            doc = json.loads(arq.read_text(encoding="utf-8"))
            total = doc.get("totalPaginas") or total
            for r in doc["resultado"]:
                ibge = str(r.get("codigoMunicipioIbge") or "")
                # Uma UG ativa vale mais que a inativa de mesmo código (lida depois).
                mapa.setdefault(r["codigoUasg"], (ibge, r.get("siglaUf") or "", r.get("nomeMunicipioIbge") or ""))
            p += 1
    return mapa


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


# Nomes mais curtos e claros para o site; os fundos das Forças são parte delas.
NOMES = {
    "Comando do Exército": "Exército", "Fundo do Exército": "Exército",
    "Comando da Marinha": "Marinha", "Fundo Naval": "Marinha",
    "Comando da Aeronáutica": "Aeronáutica", "Fundo Aeronáutico": "Aeronáutica",
    "Empresa Brasileira de Serviços Hospitalares": "Hospitais universitários (Ebserh)",
    "Fundo Constitucional do Distrito Federal": "Fundo Constitucional do DF (polícia, saúde e educação do DF)",
}


def _nome_orgao(s: str) -> str:
    s = s.replace(" - Unidades com vínculo direto", "").replace(" - Orçamento Fiscal e Seguridade Social", "").strip()
    s = s.replace("Instituto Federal de Educação, Ciência e Tecnologia", "Instituto Federal")
    return NOMES.get(s, s)


def somar(ano: int, ugs: dict[str, tuple[str, str, str]]) -> dict:
    """Gasto direto pago no ano (pago no ano + restos a pagar pagos), por cidade da unidade."""
    mun: dict = defaultdict(lambda: {"g": defaultdict(float), "folha": 0.0, "ugs": set(), "org": defaultdict(float)})
    brasil = defaultdict(float)
    fora = defaultdict(float)
    sem_cidade: dict = defaultdict(float)
    meses = 0
    for mes in range(1, 13):
        am = f"{ano}{mes:02d}"
        try:
            arq = _baixar(URL_EXECUCAO.format(am=am), PASTA_EXECUCAO / f"{am}_Despesas.zip", zip_=True)
        except urllib.error.HTTPError as e:
            if e.code == 404 and mes > 1:
                break  # mês ainda não publicado
            raise
        meses += 1
        with zipfile.ZipFile(arq) as z:
            texto = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1", newline="")
            for l in csv.DictReader(texto, delimiter=";"):
                if l["Código Modalidade da Despesa"] != "90":
                    continue
                grupo = GRUPOS.get(l["Código Grupo de Despesa"])
                if not grupo:
                    continue
                v = _num(l["Valor Pago (R$)"]) + _num(l["Valor Restos a Pagar Pagos (R$)"])
                if not v:
                    continue
                motivo = UO_FORA.get(l["Código Unidade Orçamentária"]) or ELEMENTOS_FORA.get(l["Código Elemento de Despesa"])
                if motivo:
                    fora[motivo] += v
                    continue
                brasil[grupo] += v
                ug, nome_ug = l["Código Unidade Gestora"], l["Nome Unidade Gestora"]
                ibge, _uf, municipio = ugs.get(ug, ("", "", ""))
                if not ibge and nome_ug.startswith("FCDF"):
                    ibge = BRASILIA  # Fundo Constitucional do DF: polícia, saúde e educação do DF
                if not ibge or ibge == "0":
                    sem_cidade["exterior" if municipio == "EXTERIOR" else "sem_cidade"] += v
                    continue
                m = mun[ibge]
                m["g"][grupo] += v
                m["ugs"].add(ug)
                m["org"][_nome_orgao(l["Nome Órgão Subordinado"])] += v
                if grupo == "pessoal" and FOLHA_CENTRAL.search(nome_ug):
                    m["folha"] += v
        print(f"  {am}: {len(mun)} cidades", flush=True)
    return {"mun": mun, "brasil": brasil, "fora": fora, "sem_cidade": sem_cidade, "meses": meses}


def montar(ano: int, r: dict) -> dict:
    orgaos: list[str] = []
    indice: dict[str, int] = {}
    saida = {}
    for ibge, m in sorted(r["mun"].items()):
        g = m["g"]
        total = sum(g.values())
        if total < 1:
            continue
        maiores = []
        for nome, v in sorted(m["org"].items(), key=lambda x: -x[1])[:MAIORES]:
            if nome not in indice:
                indice[nome] = len(orgaos)
                orgaos.append(nome)
            maiores.append([indice[nome], round(v)])
        # O site chama o Distrito Federal de 53 (é município e estado ao mesmo tempo).
        chave = "53" if ibge == BRASILIA else ibge
        saida[chave] = [round(total), round(g["pessoal"]), round(g["custeio"]), round(g["obras"]),
                        round(m["folha"]), len(m["ugs"]), maiores]
    total = sum(r["brasil"].values())
    df = saida.get("53", [0])[0]
    folha_fora_df = sum(v[4] for k, v in saida.items() if k != "53")
    return {
        "ano": ano, "meses": r["meses"], "fonte": FONTE,
        "colunas": ["total", "pessoal", "custeio", "obras", "folha_central", "unidades", "maiores"],
        "brasil": {
            "total": round(total), **{k: round(v) for k, v in r["brasil"].items()},
            "brasilia": df, "sem_cidade": round(r["sem_cidade"]["sem_cidade"]),
            "exterior": round(r["sem_cidade"]["exterior"]), "folha_central_fora_df": folha_fora_df,
            "cidades": len(saida),
            "fora": {k: round(v) for k, v in sorted(r["fora"].items(), key=lambda x: -x[1])},
        },
        "orgaos": orgaos, "mun": saida,
    }


def copiar_referencia() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REFERENCIA, SAIDA)
    print(f"saída: {SAIDA.relative_to(RAIZ)} (cópia de {REFERENCIA.relative_to(RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(prog="gasto-federal", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return
    try:
        ugs = unidades()
        r = somar(args.ano, ugs)
    except Exception as erro:  # noqa: BLE001 — qualquer falha de download cai na cópia versionada
        if REFERENCIA.exists():
            print(f"  aviso: download falhou ({erro}); usando a cópia versionada", flush=True)
            copiar_referencia()
            return
        raise
    doc = montar(args.ano, r)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    b = doc["brasil"]
    bi = lambda v: f"R$ {v / 1e9:.1f} bi ({100 * v / b['total']:.0f}%)"  # noqa: E731
    print(f"{b['cidades']} cidades; gasto direto {bi(b['total'])}: Brasília {bi(b['brasilia'])}, sem cidade "
          f"{bi(b['sem_cidade'])}, exterior {bi(b['exterior'])}, folha central fora do DF {bi(b['folha_central_fora_df'])}")
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
