"""Para quem as prefeituras do Amazonas pagaram: os pagamentos da API de dados abertos do TCE-AM.

    uv run pagamentos --uf AM                          # as 62 prefeituras, 2025 (cerca de 20 minutos)
    uv run pagamentos --uf AM --municipio Parintins    # uma cidade (junta-se às que já estão no arquivo)

Fonte: a API de dados abertos do Tribunal de Contas do Amazonas (https://econtasapi.tce.am.gov.br/
swagger-ui/index.html), sem login nem chave:
- /transparencia/dados-abertos/unidades: as unidades gestoras, com o município e a esfera (2 = municipal);
- /transparencia/dados-abertos/pagamentos/{unidade}/{ano}/{mês}: cada pagamento do mês, com o empenho
  a que se refere, o credor (nome, CPF ou CNPJ e o tipo de pessoa), o grupo, a modalidade e o elemento
  da despesa e o valor pago.

Entram todas as unidades municipais que o tribunal lista para a cidade: prefeitura, secretarias com
orçamento próprio, Câmara, fundos, autarquias, fundações e o instituto de previdência. Os consórcios
de municípios são unidades à parte (põem-se na cidade-sede) e ficam de fora. Uma chamada por unidade
e mês (3.500 no ano), quatro de cada vez (Manaus: 148 mil pagamentos, 3 minutos). Cada município lido
fica guardado em data/raw/tce-am/ (só o resumo, alguns KB), para a carga continuar de onde parou.

O pago é a soma dos pagamentos do ano feitos a empenhos do próprio ano; o que se paga de empenhos de
anos anteriores (restos a pagar; em Manaus, R$ 177 mi em 2025) fica fora, como no pago da prestação de
contas ao Tesouro. A API não traz estornos, nem os reforços e as anulações dos empenhos, então o
"empenhado" não é calculado (fica 0; o site não o usa). Conferido com a DCA 2025 (pago): Manaus fica
3% acima (R$ 10.887 mi contra 10.567 mi), Alvarães 1% acima.

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir): só o pago conta; operações entre unidades do município (modalidade 91)
ficam fora do total; folha, previdência, dívida e bancos e outros órgãos públicos à parte dos
fornecedores; pessoas físicas só no total e na contagem, sem nome e **sem CPF**. A API manda o CPF
inteiro: ele só serve, na memória, para contar pessoas, e nunca é gravado.

A API respondeu de um endereço do Brasil (21/11/2026); não se sabe se responde de fora. A carga é feita
à mão, como nos outros estados, e fica em pipeline/referencia/pagamentos-am.json; a publicação
automática só copia (`pagamentos --sem-baixar`).
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida as saida
from .fontes import CONTEXTO_TLS, USER_AGENT

API = "https://econtasapi.tce.am.gov.br/transparencia/dados-abertos"
FONTE = "Tribunal de Contas do Estado do Amazonas (TCE-AM), dados abertos de pagamentos"
PASTA = c.RAIZ / "data" / "raw" / "tce-am"
ESFERA_MUNICIPAL = 2
PESSOA_FISICA, PESSOA_JURIDICA = 1, 2   # codTipoPessoa


def obter(caminho: str, tentativas: int = 4, espera: float = 20):
    url = f"{API}/{caminho}"
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as r:
                return json.load(r)
        except (OSError, ValueError) as e:
            if tentativa == tentativas:
                raise
            print(f"  {caminho}: {e}; tentando de novo em {espera:.0f} s", flush=True)
            time.sleep(espera)
    raise AssertionError


def unidades() -> dict[str, list[dict]]:
    """Município (nome, como o tribunal escreve) -> unidades gestoras municipais."""
    por_municipio: dict[str, list[dict]] = defaultdict(list)
    for u in obter("unidades"):
        if u.get("esfera") == ESFERA_MUNICIPAL:
            por_municipio[u["desMunicipio"]].append(u)
    return dict(por_municipio)


def meses(unidade: int, ano: int):
    """Os pagamentos de uma unidade, mês a mês: quatro meses de cada vez, para não segurar o ano todo na memória."""
    with ThreadPoolExecutor(4) as ex:
        for lote in ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12)):
            yield from ex.map(lambda m: obter(f"pagamentos/{unidade}/{ano}/{m}"), lote)


def somar(empenhos: dict, brutos: list[dict], ano: int, fora: Counter) -> None:
    """Junta os pagamentos de um mês por empenho: do primeiro pagamento, o credor e a classificação;
    de todos, o valor pago."""
    for p in brutos:
        valor = p.get("vlPagamentoEmpenho") or 0
        if p.get("exercicio") != ano or not str(p.get("dtEmpenho") or "").startswith(str(ano)):
            fora["outro_ano"] += valor   # não aconteceu em 2025; fica de olho
            continue
        chave = f"{p['idUnidadeGestora']}/{p['idEmpenho']}"
        if chave in empenhos:
            empenhos[chave].pago += valor
            continue
        tipo = p.get("codTipoPessoa")
        nome = " ".join((p.get("nomCredor") or "").split())
        grupo = "1" if saida.FOLHA_NOME.match(pb._sem_acento(nome)) else str(p.get("codGrupoNatureza") or "")
        empenhos[chave] = pq.Linha(
            chave=chave, unidade=p.get("nomeUnidadeGestora") or "",
            # Na memória só: o CPF serve para contar pessoas e nunca é gravado.
            doc=re.sub(r"\D", "", p.get("cnpjCnpjCredor") or "").zfill(14),
            nome=nome, pessoa_fisica=True if tipo == PESSOA_FISICA else False if tipo == PESSOA_JURIDICA else None,
            grupo=grupo, modalidade=str(p.get("codModalidadeAplicacao") or "").zfill(2),
            elemento=str(p.get("codElementoDespesa") or "").zfill(2), empenhado=0.0, pago=valor,
        )


def ler_municipio(lista: list[dict], ano: int, pausa: float) -> tuple[dict, Counter]:
    fora: Counter = Counter()
    empenhos: dict[str, pq.Linha] = {}
    for u in lista:
        if pb.CONSORCIO_UG.match(u["nome"]):
            fora["consorcios"] += 1   # consórcio de várias prefeituras: não é gasto só desta cidade
            continue
        for brutos in meses(u["id_unidade_gestora"], ano):
            fora["pagamentos"] += len(brutos)
            somar(empenhos, brutos, ano, fora)
        time.sleep(pausa)
    resumo, _ = pq.resumir(empenhos.values())
    fora["empenhos"] = len(empenhos)
    return resumo, fora


def carregar(ano: int, so: list[str] | None, pausa: float, refazer: bool) -> tuple[dict, list[str]]:
    ibge_por_nome = {pb._chave(e["ente"]): str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "AM"}
    por_municipio = unidades()
    nomes = sorted(por_municipio)
    if so:
        pedidos = {pb._chave(n) for n in so}
        nomes = [n for n in nomes if pb._chave(n) in pedidos]
        if len(nomes) < len(pedidos):
            raise SystemExit(f"município não encontrado no TCE-AM: {sorted(pedidos - {pb._chave(n) for n in nomes})}")
    cache_arq = PASTA / f"resumos-{ano}.json"
    cache = json.loads(cache_arq.read_text(encoding="utf-8")) if cache_arq.exists() else {}
    PASTA.mkdir(parents=True, exist_ok=True)
    print(f"AM {ano}: {len(nomes)} municípios, {sum(len(por_municipio[n]) for n in nomes)} unidades "
          f"({len(cache)} municípios já lidos antes)", flush=True)
    resultado, sem_ibge = {}, []
    for i, nome in enumerate(nomes, 1):
        ibge = ibge_por_nome.get(pb._chave(nome))
        if not ibge:
            sem_ibge.append(nome)
            continue
        if ibge in cache and not refazer:   # com --refazer, lê de novo as cidades pedidas e guarda as outras
            resultado[ibge] = cache[ibge]
            continue
        t0 = time.time()
        resumo, fora = ler_municipio(por_municipio[nome], ano, pausa)
        if fora["outro_ano"]:
            print(f"  {nome}: R$ {pq.br(fora['outro_ano'] / 1e6, 1)} mi em pagamentos de empenhos de outro ano (fora)")
        if not resumo["pago"]:
            print(f"  [{i}/{len(nomes)}] {nome}: nenhum pagamento em {ano}")
            continue
        resultado[ibge] = cache[ibge] = resumo
        cache_arq.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  [{i}/{len(nomes)}] {nome}: {pq.br(fora['pagamentos'])} pagamentos de {pq.br(fora['empenhos'])} empenhos, "
              f"pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi ({time.time() - t0:.0f} s)", flush=True)
    return resultado, sem_ibge


def rodar(ano: int, so: list[str] | None, pausa: float, refazer: bool = False) -> None:
    mun, sem_ibge = carregar(ano, so, pausa, refazer)
    if sem_ibge:
        print(f"  sem código do IBGE (ficaram de fora): {sem_ibge}")
    saida.gravar("AM", FONTE, ano, mun, so)
