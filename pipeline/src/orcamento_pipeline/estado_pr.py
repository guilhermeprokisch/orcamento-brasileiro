"""Salários pagos pelo governo do Paraná em cada município, pela folha de pagamento.

    uv run estado-pr 2025
    uv run estado-pr 2025 --sem-baixar   # só copia pipeline/referencia/estado-pr.json

O Portal da Transparência do Paraná (https://www.transparencia.pr.gov.br/pte/assunto/8/129)
publica dois arquivos de URL fixa:
- REMUNERACAO_RH.zip (~32 MB): um registro por vínculo desde 2012, com o órgão, a lotação
  (a escola, o hospital) e o município da lotação;
- REMUNERACAO-AAAA-MM.zip (~12 MB por mês): o salário de cada vínculo no mês, bruto e líquido.
Os dois se juntam pelo código do vínculo. Usamos o salário bruto (remu_bruta), com 13º e férias.

O que fica de fora ou torto, pelo que os dados mostram:
- a Polícia Militar e a Polícia Civil vêm, na maior parte, com lotação e município trocados
  por "****": essa folha fica sem cidade (é quase tudo o que fica sem cidade);
- a lotação é a atual (ou a última) do vínculo, não a de cada mês: quem mudou de cidade depois
  aparece na cidade nova;
- aposentadorias e pensões não têm lugar de trabalho e ficam fora da conta.

Os arquivos trazem o nome de cada servidor; aqui só se lê o código do vínculo, o órgão, a
lotação, o município e o valor. Os zips são apagados depois de somados: o cache em
data/raw/estados/pr/{ano}-{mes}.json.gz guarda só as somas de cada mês.
Saída em site/public/data/estados/pr/{ano}.json, com cópia em pipeline/referencia/estado-pr.json.
O servidor de downloads às vezes para de responder por alguns minutos: o comando espera e tenta
de novo. No CI só a cópia (--sem-baixar): o ano fechado não muda.
"""

from __future__ import annotations

import argparse
import csv
import io
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

from . import folha_estadual as fe
from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

BASE = "https://www.transparencia.download.pr.gov.br/exportacao"
URL_RH = f"{BASE}/REMUNERACAO_RH/REMUNERACAO_RH.zip"
URL_MES = BASE + "/REMUNERACAO/REMUNERACAO-{ano}-{mes:02d}.zip"
PASTA_BRUTO = RAIZ / "data" / "raw" / "estados" / "pr"
SAIDA = RAIZ / "site" / "public" / "data" / "estados" / "pr"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "estado-pr.json"
MASCARA = "****"
INATIVOS = {"APOSENTADO", "PENSIONISTA", "PENSÃO ESPECIAL"}
PREVIDENCIA = "GOVERNO DO ESTADO"  # órgão pagador das aposentadorias e pensões no arquivo do mês
# Grafias do arquivo que diferem do IBGE.
APELIDOS = {"ITAPEJARA DO OESTE": "ITAPEJARA D OESTE", "SAO JORGE DO OESTE": "SAO JORGE D OESTE",
            "PEROLA DO OESTE": "PEROLA D OESTE", "MUNHOZ DE MELLO": "MUNHOZ DE MELO"}
TENTATIVAS = 5
GENERICAS: set[str] = {"CONVENIO"}  # mais os nomes das cidades, em main
UNIVERSIDADES = {"UEL", "UEM", "UNIOESTE", "UEPG", "UNICENTRO", "UENP", "UNESPAR"}

TEXTO = {
    "resumo": "pagou",
    "onde": "em salários a servidores estaduais que trabalham em",
    "maiores": "Onde o estado paga mais salários aqui",
    "aviso": "Só somas por cidade e por unidade: nenhum nome de servidor é guardado.",
    "nota": ("Só a folha de pagamento: o salário bruto, com 13º e férias, dos servidores ativos lotados em escolas, "
             "hospitais, delegacias e outras unidades do estado nesta cidade. Não entram obras, compras, repasses nem "
             "aposentadorias. Fica sem cidade quem a folha não liga a um lugar: no Paraná, quase só a Polícia Militar e a "
             "Polícia Civil, cuja lotação o estado não divulga ({sem_cidade}, ou {parte_sem_cidade} da folha dos ativos). A "
             "cidade é a da lotação atual de cada servidor: quem é lotado num lugar e trabalha em outro aparece no lugar da "
             "lotação."),
}


def area(sigla: str, instituicao: str) -> str:
    inst = fe.chave(instituicao)
    if sigla in UNIVERSIDADES or inst.startswith(("UNIVERSIDADE", "UNESPAR")) or "EDUCA" in inst or sigla in ("SEED", "CEPR"):
        return fe.EDUCACAO
    if sigla == "SESA" or "SAUDE" in inst:
        return fe.SAUDE
    if sigla == "SESP" or "SEGURANCA" in inst:
        return fe.SEGURANCA
    return fe.OUTRAS


def _baixar(url: str, destino: Path) -> bool:
    """Grava a URL em `destino`; False se o arquivo ainda não existe (404)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for tentativa in range(TENTATIVAS):
        try:
            with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as resp, destino.open("wb") as f:
                while bloco := resp.read(1 << 20):
                    f.write(bloco)
            time.sleep(5)
            return True
        except urllib.error.HTTPError as erro:
            if erro.code == 404:
                return False
            if tentativa == TENTATIVAS - 1:
                raise
        except Exception:
            if tentativa == TENTATIVAS - 1:
                raise
        time.sleep(30 * (tentativa + 1))  # o servidor às vezes para de aceitar conexões por alguns minutos
    return False


def _linhas(arq: Path):
    with zipfile.ZipFile(arq) as z, z.open(z.namelist()[0]) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline=""), delimiter=";")


def ler_vinculos() -> dict[str, tuple[str, str, str, str, str]]:
    """Código do vínculo -> (sigla, instituição, lotação, município, situação). Sem nome."""
    arq = PASTA_BRUTO / "tmp" / "REMUNERACAO_RH.zip"
    try:
        _baixar(URL_RH, arq)
        return {r["cod_vinculo"]: (r["sigla"], " ".join(r["instituicao"].split()), " ".join(r["lotacao"].split()), r["municipio"], r["situacao"])
                for r in _linhas(arq)}
    finally:
        arq.unlink(missing_ok=True)


def somar_mes(ano: int, mes: int, vinculos: dict, ibge_por_nome: dict[str, str]) -> fe.Mes | None:
    arq = PASTA_BRUTO / "tmp" / f"REMUNERACAO-{ano}-{mes:02d}.zip"
    try:
        if not _baixar(URL_MES.format(ano=ano, mes=mes), arq):
            return None
        m = fe.Mes()
        for r in _linhas(arq):
            v = float(r["remu_bruta"] or 0)
            if not v:
                continue
            sigla, inst, lotacao, municipio, situacao = vinculos.get(r["cod_vinculo"], ("", "", "", MASCARA, ""))
            if situacao in INATIVOS or r["sigla_orgao"] == PREVIDENCIA:
                m.inativos += v
                continue
            nome = fe.chave(municipio)
            ibge = ibge_por_nome.get(APELIDOS.get(nome, nome)) if municipio != MASCARA else None
            m.somar(ibge, area(sigla, inst), "" if lotacao == MASCARA else lotacao, inst or sigla, v)
        return m
    finally:
        arq.unlink(missing_ok=True)


def sem_lotacoes_genericas(m: fe.Mes) -> fe.Mes:
    """Lotações que são só o nome da cidade ("CURITIBA - LOCAL") ficam nas somas, mas não na lista das
    maiores unidades: não dizem onde é."""
    for k in list(m.unid):
        nome = fe.chave(k[2])
        if k[2] and (nome.endswith(" LOCAL") or nome in GENERICAS or nome == fe.chave(k[3])):
            v, n = m.unid.pop(k)
            u = m.unid[(k[0], k[1], "", k[3])]
            u[0] += v
            u[1] += n
    return m


def main() -> None:
    p = argparse.ArgumentParser(prog="estado-pr", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ano", type=int)
    p.add_argument("--sem-baixar", action="store_true", help="só copia a versão guardada em pipeline/referencia")
    args = p.parse_args()
    saida = SAIDA / f"{args.ano}.json"
    if args.sem_baixar:
        fe.copiar_referencia(REFERENCIA, SAIDA)
        return

    ibge_por_nome = fe.municipios("PR")
    GENERICAS.update(ibge_por_nome)
    ultimo = 12 if args.ano < date.today().year else date.today().month
    meses: list[fe.Mes] = []
    vinculos = None
    try:
        for mes in range(1, ultimo + 1):
            cache = PASTA_BRUTO / f"{args.ano}-{mes:02d}.json.gz"
            if cache.exists():
                meses.append(fe.Mes.ler(cache))
                continue
            if vinculos is None:
                vinculos = ler_vinculos()
                print(f"  {len(vinculos)} vínculos no cadastro", flush=True)
            m = somar_mes(args.ano, mes, vinculos, ibge_por_nome)
            if m is None:
                break  # o mês ainda não foi publicado
            print(f"  {args.ano}-{mes:02d}: ativos R$ {m.ativos / 1e6:.0f} mi, sem cidade R$ {sum(m.sem_cidade.values()) / 1e6:.0f} mi", flush=True)
            m.gravar(cache)
            meses.append(m)
    except Exception as erro:  # noqa: BLE001 — qualquer falha de download cai na cópia versionada
        if REFERENCIA.exists():
            print(f"  aviso: download falhou ({erro}); usando a cópia versionada", flush=True)
            fe.copiar_referencia(REFERENCIA, SAIDA)
            return
        raise
    if not meses:
        raise SystemExit(f"{args.ano}: nenhum mês publicado")
    meses = [sem_lotacoes_genericas(m) for m in meses]
    doc = fe.montar(args.ano, meses, len(meses), "Portal da Transparência do Paraná (folha de pagamento)", TEXTO)
    fe.gravar(doc, saida, REFERENCIA)


if __name__ == "__main__":
    main()
