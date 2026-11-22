"""O fundo de aposentadoria dos servidores (regime próprio de previdência, RPPS) de cada prefeitura e estado.

    uv run previdencia               # baixa a versão mais recente do ISP e o cadastro dos regimes
    uv run previdencia --sem-baixar  # usa o que já está em data/raw ou, sem isso, a cópia de referência

Fonte: Ministério da Previdência Social, Secretaria de Regime Próprio e Complementar.
- Índice de Situação Previdenciária (ISP-RPPS): a planilha do resultado final, publicada todo fim de
  ano (a de 2025 saiu em 04/12/2025). Uma linha por ente com regime próprio (~2.130), com a nota final
  (A a D) e, nas abas de cada indicador, os números usados na conta:
  - COBERTURA: as provisões matemáticas do Demonstrativo de Resultados da Avaliação Atuarial (DRAA) do
    ano, quanto o fundo calcula que precisa ter hoje para pagar as aposentadorias e pensões já
    prometidas, separadas em plano previdenciário (o que deveria ter dinheiro guardado), plano
    financeiro e benefícios mantidos pelo Tesouro (os dois pagos com o caixa de cada ano); e o dinheiro
    aplicado pelo fundo em 31/12 do ano anterior (DAIR);
  - GRUPOS: servidores ativos, aposentados e pensionistas;
  - SUFICIÊNCIA: o que entrou (contribuições) e saiu (benefícios) no ano anterior;
  - SUSTENTABILIDADE: a receita corrente líquida (a planilha traz 60% dela).
- Cadastro das unidades gestoras dos regimes (cnpj-ente-cpnj-ug, página "Estatísticas e informações dos
  RPPS"): diz quais entes estão extinguindo o regime próprio e quais já voltaram ao INSS (RGPS).

As planilhas não trazem o código do IBGE: as prefeituras são achadas pelo nome e pela UF em
site/public/data/cidades/municipios.json (rodar depois do passo das cidades).

O que falta ("déficit") = provisões matemáticas − dinheiro aplicado. É a mesma conta que o ISP usa no
indicador de comprometimento atuarial. Não desconta o plano de amortização que o fundo tenha aprovado
(as contribuições extras previstas para cobrir o rombo nas próximas décadas).

Saída em site/public/data/indicadores/previdencia.json, com cópia em pipeline/referencia/previdencia.json:
    {"fonte": …, "versao": "ISP 2025, publicado em 04/12/2025", "ano_draa": 2025, "ano_contas": 2024,
     "entes": {ibge: [nota, provisões, plano financeiro e Tesouro, dinheiro aplicado, RCL,
                      ativos, aposentados, pensionistas, receita do ano, despesa do ano, ano do DRAA]},
     "extincao": [ibge, …], "rgps": [ibge, …]}
Valores em reais; null quando a planilha não informa. Quem não entregou o DRAA do ano fica com o do ano
anterior (planilha do ISP anterior), e o último campo diz de que ano é.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import urllib.request
from pathlib import Path

import openpyxl

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

PAGINA_ISP = "https://www.gov.br/previdencia/pt-br/assuntos/rpps/indice-de-situacao-previdenciaria"
PAGINA_ESTATISTICAS = "https://www.gov.br/previdencia/pt-br/assuntos/rpps/estatisticas-e-informacoes-dos-rpps-1/estatisticas-informacoes-dos-rpps"
# Se a página mudar de lugar, estes são os arquivos de 2025.
ISP_PADRAO = PAGINA_ISP + "/arquivos/resultado-final-isp-2025-_-publicado-em-04_12_2025-1.xlsx"
ISP_ANTERIOR_PADRAO = PAGINA_ISP + "/arquivos/ISP_2024_resultado_final_Revisado_29_11_2024.xlsx"
CADASTRO_PADRAO = ("https://www.gov.br/previdencia/pt-br/assuntos/rpps/estatisticas-e-informacoes-dos-rpps/"
                   "cnpj-ente-cpnj-ug-_atualizado-ate-31-07-2025.csv")

PASTA = c.RAIZ / "data" / "raw" / "previdencia"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "previdencia.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "previdencia.json"
MUNICIPIOS = c.RAIZ / "site" / "public" / "data" / "cidades" / "municipios.json"
FONTE = "Ministério da Previdência Social, Índice de Situação Previdenciária dos regimes próprios (ISP-RPPS)"
CODIGO_UF = {sigla: codigo for codigo, sigla in c.SIGLAS.items()}

# Grafias da planilha do Ministério que não batem com o nome do IBGE: (UF, nome na planilha) -> nome no IBGE.
APELIDOS: dict[tuple[str, str], str] = {
    ("PE", "Belém de São Francisco"): "Belém do São Francisco",
    ("RN", "Boa Saúde (antigo Januário Cicco)"): "Boa Saúde",
    ("MG", "Brasópolis"): "Brazópolis",
    ("TO", "Couto de Magalhães"): "Couto Magalhães",
    ("RO", "Espigão do Oeste"): "Espigão D'Oeste",
    ("PE", "Iguaraci"): "Iguaracy",
    ("AL", "Major Izidoro"): "Major Isidoro",
    ("MT", "Poxoréo"): "Poxoréu",
    ("RN", "Serra Caiada (antigo Presidente Juscelino)"): "Serra Caiada",
    ("AL", "São Luiz do Quitunde"): "São Luís do Quitunde",
}


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300, context=CONTEXTO_TLS) as resp:
        return resp.read()


def _links(pagina: str, padrao: str) -> list[str]:
    html = _baixar(pagina).decode("utf-8", errors="replace")
    return sorted({u for u in re.findall(r'href="([^"]+)"', html) if re.search(padrao, u, re.I)})


def ano_isp_de(nome: str) -> int:
    """"resultado-final-isp-2025-…xlsx" -> 2025 (o primeiro ano no nome do arquivo)."""
    m = re.search(r"20\d\d", nome.split("/")[-1])
    return int(m.group(0)) if m else 0


def urls_isp() -> list[str]:
    """Os resultados finais dos dois anos mais recentes (planilhas "resultado final" da página), o mais novo primeiro."""
    try:
        links = [u for u in _links(PAGINA_ISP, r"\.xlsx$") if re.search(r"resultado.?final", u, re.I)]
    except Exception as erro:
        print(f"  página do ISP não respondeu ({erro}); usando os arquivos de 2025 e 2024", flush=True)
        links = []
    por_ano: dict[int, str] = {}
    for u in sorted(links):
        por_ano[ano_isp_de(u)] = u   # no mesmo ano, fica o último em ordem alfabética ("revisado", "-1")
    anos = sorted(por_ano, reverse=True)[:2]
    return [por_ano[a] for a in anos] if len(anos) == 2 else [ISP_PADRAO, ISP_ANTERIOR_PADRAO]


def url_cadastro() -> str:
    try:
        links = _links(PAGINA_ESTATISTICAS, r"cnpj-ente.*\.csv$")
    except Exception:
        return CADASTRO_PADRAO
    return links[-1] if links else CADASTRO_PADRAO


def obter(url: str, baixar: bool) -> Path | None:
    destino = PASTA / url.rstrip("/").split("/")[-1]
    if destino.exists():
        return destino
    if not baixar:
        return None
    PASTA.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(_baixar(url))
    print(f"  baixado {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)", flush=True)
    return destino


def _num(v) -> float | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def _cabecalho(linha: tuple) -> dict[str, int]:
    """Coluna de cada título, com o título só em letras ("provisoesmatematicasprevidenciariasvalortotal")."""
    return {re.sub(r"[^a-z0-9]", "", c._so_letras(str(x)) + "".join(re.findall(r"\d+", str(x)))): i
            for i, x in enumerate(linha) if x is not None}


def _coluna(col: dict[str, int], *comeco: str) -> int:
    for k, i in col.items():
        if any(k.startswith(p) for p in comeco):
            return i
    raise KeyError(f"coluna {comeco} não encontrada")


def aba(livro, nome: str):
    """(colunas, linhas) de uma aba: o cabeçalho é a linha que começa com "ENTE"."""
    ws = next(w for w in livro.worksheets if c._so_letras(w.title).startswith(c._so_letras(nome)))
    col, linhas = None, {}
    for linha in ws.iter_rows(values_only=True):
        if col is None:
            if linha and str(linha[0] or "").strip().upper() == "ENTE":
                col = _cabecalho(linha)
            continue
        if linha and linha[0] and " - " in str(linha[0]):
            linhas[str(linha[0]).strip()] = linha
    if col is None:
        raise ValueError(f"aba {nome}: cabeçalho não encontrado")
    return col, linhas


def ler_cobertura(livro) -> dict[str, dict]:
    """Aba COBERTURA: provisões matemáticas do DRAA (total e parte paga com o caixa de cada ano) e dinheiro aplicado."""
    col, cob = aba(livro, "COBERTURA")
    i_ativos = _coluna(col, "ativosdair")
    i_ano = _coluna(col, "anodraa")
    # "PROVISÕES MATEMÁTICAS PREVIDENCIÁRIAS VALOR TOTAL" (2025); "PROVISÃO MATEMÁTICA TOTAL AJUSTADA" (2024)
    i_total = _coluna(col, "provisoesmatematicasprevidenciariasvalortotal", "provisaomatematicatotal")
    i_fin = [i for k, i in col.items() if k.startswith("provisao") and ("planofinanceiro" in k or "tesouro" in k)]
    saida = {}
    for nome, l in cob.items():
        fin = [_num(l[i]) for i in i_fin]
        provisoes = _num(l[i_total])
        saida[nome] = {"provisoes": provisoes, "aplicado": _num(l[i_ativos]),
                       "financeiro": sum(v for v in fin if v) if any(v is not None for v in fin) else None,
                       "ano_draa": int(l[i_ano]) if provisoes is not None and isinstance(l[i_ano], (int, float)) else None}
    return saida


def ler_isp(arquivo: Path) -> tuple[dict[str, dict], int | None]:
    """Uma entrada por ente ("NOME - UF"), com os números das abas; e o ano do DRAA."""
    livro = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    col, res = aba(livro, "RESULTADO")
    i_uf, i_grupo = _coluna(col, "uf"), _coluna(col, "grupo")
    i_nota = _coluna(col, "indicadordesituacaoprevidenciaria")
    i_capital = _coluna(col, "capital")
    entes = {nome: {"uf": l[i_uf], "estado": "ESTADO" in str(l[i_grupo] or "").upper(),
                    "nota": (str(l[i_nota]).strip().upper() if l[i_nota] and str(l[i_nota]).strip().upper() in "ABCD" else None),
                    "capital": str(l[i_capital] or "").upper() == "S"}
             for nome, l in res.items()}

    for nome, cob in ler_cobertura(livro).items():
        if nome in entes:
            entes[nome].update(cob)

    col, gru = aba(livro, "GRUPOS")
    i_seg, i_apo, i_pen = _coluna(col, "seguradosativos"), _coluna(col, "aposentados"), _coluna(col, "pensionistas")
    for nome, l in gru.items():
        if nome in entes:
            entes[nome].update(ativos=_num(l[i_seg]), aposentados=_num(l[i_apo]), pensionistas=_num(l[i_pen]))

    col, suf = aba(livro, "SUFICI")
    i_rec, i_desp = _coluna(col, "receitaconsiderada"), _coluna(col, "despesaconsiderada")
    for nome, l in suf.items():
        if nome in entes:
            entes[nome].update(receita=_num(l[i_rec]), despesa=_num(l[i_desp]))

    col, sus = aba(livro, "SUSTENTABILIDADE")
    i_rcl = _coluna(col, "receitacorrenteliquida")
    sessenta = any(k.startswith("receitacorrenteliquida") and k.endswith("60") for k in col)
    for nome, l in sus.items():
        if nome in entes and (v := _num(l[i_rcl])):
            # A planilha traz 60% da receita corrente líquida (o título diz "RECEITA CORRENTE LIQUIDA 60%").
            entes[nome]["rcl"] = v / 0.6 if sessenta else v
    anos = [e["ano_draa"] for e in entes.values() if e.get("ano_draa")]
    ano_draa = max(set(anos), key=anos.count) if anos else None
    return entes, ano_draa


def _nome_e_uf(rotulo: str) -> tuple[str, str]:
    nome, _, uf = rotulo.rpartition(" - ")
    return nome.strip(), uf.strip().upper()


def indice_municipios() -> dict[tuple[str, str], int]:
    doc = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    return {(m["uf"], c._so_letras(m["nome"])): m["ibge"] for m in doc["cidades"] if m["ibge"] > 99}


def codigo(rotulo: str, estado: bool, indice: dict[tuple[str, str], int]) -> int | None:
    nome, uf = _nome_e_uf(rotulo)
    if estado or nome.upper().startswith("GOVERNO D"):
        return CODIGO_UF.get(uf)
    apelidos = {(u, c._so_letras(n)): c._so_letras(i) for (u, n), i in APELIDOS.items()}
    chave = c._so_letras(nome)
    return indice.get((uf, apelidos.get((uf, chave), chave)))


def ler_cadastro(arquivo: Path, indice: dict[tuple[str, str], int]) -> tuple[list[int], list[int]]:
    """Os entes que estão extinguindo o regime próprio e os que já voltaram ao INSS (sem nenhum RPPS ativo)."""
    texto = arquivo.read_bytes().decode("utf-8-sig", errors="replace")
    regimes: dict[tuple[str, str], set[str]] = {}
    for l in csv.DictReader(io.StringIO(texto), delimiter=";"):
        uf, ente = (l.get("UF") or "").strip().upper(), (l.get("ENTE") or "").strip()
        if uf and ente:
            regimes.setdefault((uf, ente), set()).add(c._so_letras(l.get("REGIME") or ""))
    extincao, rgps = [], []
    for (uf, ente), r in regimes.items():
        if "rpps" in r:
            continue
        ibge = codigo(f"{ente} - {uf}", False, indice)
        if ibge is None:
            continue
        (extincao if "extincaorpps" in r else rgps).append(ibge)
    return sorted(extincao), sorted(rgps)


def _inteiro(v: float | None) -> int | None:
    return None if v is None else round(v)


def main() -> None:
    p = argparse.ArgumentParser(prog="previdencia", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="não consulta o site do Ministério")
    args = p.parse_args()
    try:
        baixar = not args.sem_baixar
        arq_isp, arq_anterior = (obter(u, baixar) for u in (urls_isp() if baixar else [ISP_PADRAO, ISP_ANTERIOR_PADRAO]))
        arq_cad = obter(url_cadastro() if baixar else CADASTRO_PADRAO, baixar)
        if arq_isp is None or arq_cad is None:
            raise FileNotFoundError("planilhas não estão em data/raw/previdencia")
        gerar(arq_isp, arq_anterior, arq_cad)
    except Exception as erro:
        if not REFERENCIA.exists():
            raise
        print(f"  não deu para montar a partir das planilhas ({erro}); usando a cópia de referência", flush=True)
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"saída: {SAIDA.relative_to(c.RAIZ)} (cópia de {REFERENCIA.relative_to(c.RAIZ)})")


def gerar(arq_isp: Path, arq_anterior: Path | None, arq_cad: Path) -> None:
    indice = indice_municipios()
    entes, ano_draa = ler_isp(arq_isp)
    # Quem não entregou a avaliação atuarial do ano fica com a do ano anterior, se houver.
    do_anterior = 0
    if arq_anterior is not None:
        anterior = ler_cobertura(openpyxl.load_workbook(arq_anterior, read_only=True, data_only=True))
        for nome, e in entes.items():
            if e.get("provisoes") is None and (a := anterior.get(nome)) and a["provisoes"] is not None:
                e.update(a)
                do_anterior += 1
    ano_isp = ano_isp_de(arq_isp.name) or ano_draa
    publicado = re.search(r"(\d{2})_(\d{2})_(20\d\d)", arq_isp.name)
    saida: dict[str, list] = {}
    sem_codigo = []
    for rotulo, e in entes.items():
        ibge = codigo(rotulo, e["estado"], indice)
        if ibge is None:
            sem_codigo.append(rotulo)
            continue
        saida[str(ibge)] = [e["nota"], _inteiro(e.get("provisoes")), _inteiro(e.get("financeiro")), _inteiro(e.get("aplicado")),
                            _inteiro(e.get("rcl")), _inteiro(e.get("ativos")), _inteiro(e.get("aposentados")),
                            _inteiro(e.get("pensionistas")), _inteiro(e.get("receita")), _inteiro(e.get("despesa")),
                            e.get("ano_draa")]
    extincao, rgps = ler_cadastro(arq_cad, indice)
    extincao = [i for i in extincao if str(i) not in saida]
    rgps = [i for i in rgps if str(i) not in saida]
    doc = {"fonte": FONTE,
           "versao": f"ISP {ano_isp}" + (f", publicado em {publicado.group(1)}/{publicado.group(2)}/{publicado.group(3)}" if publicado else ""),
           "ano_draa": ano_draa, "ano_contas": ano_draa - 1 if ano_draa else None,
           "entes": dict(sorted(saida.items(), key=lambda kv: int(kv[0]))), "extincao": extincao, "rgps": rgps}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    mun = [k for k in saida if len(k) == 7]
    print(f"{doc['versao']}: {len(entes)} entes na planilha, {len(saida)} com código "
          f"({len(saida) - len(mun)} estados e DF, {len(mun)} prefeituras); {len(extincao)} extinguindo o regime, "
          f"{len(rgps)} que voltaram ao INSS; {do_anterior} com a avaliação atuarial do ano anterior", flush=True)
    if sem_codigo:
        print(f"  sem código do IBGE ({len(sem_codigo)}): {', '.join(sorted(sem_codigo))}", flush=True)
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} e {REFERENCIA.relative_to(c.RAIZ)} ({SAIDA.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
