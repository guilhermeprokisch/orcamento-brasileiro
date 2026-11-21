"""Para quem as prefeituras de Pernambuco pagaram: os empenhos da API de dados abertos do TCE-PE.

    uv run pagamentos --uf PE                          # as 184 prefeituras, 2025 (cerca de 2 horas)
    uv run pagamentos --uf PE --municipio Recife       # uma cidade (junta-se às que já estão no arquivo)

Fonte: a API de dados abertos do Tribunal de Contas de Pernambuco
(https://sistemas.tcepe.tc.br/DadosAbertos/Exemplo!listar), método DespesasMunicipais: uma linha por
empenho, com a unidade gestora, o credor (FORNECEDOR, CPF_CNPJ e TIPOCREDOR), a natureza, a
modalidade e o elemento da despesa (por extenso, não pelo código) e os valores empenhado, liquidado
e pago. Entram todas as unidades que o município manda ao tribunal: prefeitura, Câmara, secretarias
com orçamento próprio, fundos, autarquias, fundações, empresas dependentes e o instituto ou fundo de
previdência. Os consórcios de municípios são unidades à parte e ficam de fora.

**A API só responde a endereços do Brasil** (o robô de publicação roda fora do país). Por isso a carga
é feita à mão, daqui, e fica em pipeline/referencia/pagamentos-pe.json; a publicação automática só
copia (`pagamentos --sem-baixar`), como em PB, AC e SC.

Uma chamada por município e ano (no máximo 100 mil linhas por chamada; se uma cidade chegar a isso,
ela é lida mês a mês). Cada município lido fica guardado em data/raw/tce-pe/ (só o resumo, alguns
KB), para a carga continuar de onde parou se cair no meio.

O "pago" de cada empenho é o que foi pago no próprio ano: conferido com o que as prefeituras
declararam ao Tesouro (DCA 2025, pago sem as operações internas), Ibimirim bate ao real
(R$ 135.832.782).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir): só o pago conta; operações entre unidades do município (modalidade 91)
ficam fora do total; folha, previdência, dívida e bancos e outros órgãos públicos à parte dos
fornecedores; pessoas físicas só no total e na contagem, sem nome e **sem CPF**. O TCE-PE já manda o
CPF mascarado ("***.***.123-45"); nem esse pedaço é gravado: só serve, na memória, para contar pessoas.

Saída em site/public/data/indicadores/pagamentos-pe.json, com cópia em pipeline/referencia/, no
mesmo formato do arquivo da Paraíba.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from .fontes import CONTEXTO_TLS, USER_AGENT

URL = "https://sistemas.tcepe.tc.br/DadosAbertos/{entidade}!json"
FONTE = "Tribunal de Contas do Estado de Pernambuco (TCE-PE), dados abertos de despesas municipais"
PASTA = c.RAIZ / "data" / "raw" / "tce-pe"
LIMITE = 100_000   # linhas por chamada ("limiteResultado")

# Natureza do órgão nas unidades jurisdicionadas: 16 são os consórcios de municípios.
NATUREZA_CONSORCIO = "16"

# TIPOCREDOR (TipoCredorMunicipal): 1 pessoa física, 2 pessoa jurídica, 3 folha de pagamento,
# 4 depósito judicial, 5 pessoa física estrangeira sem CPF, 6 pessoa jurídica estrangeira sem CNPJ.
PESSOA_FISICA, PESSOA_JURIDICA = {"1", "5"}, {"2", "6"}
FOLHA_DE_PAGAMENTO, DEPOSITO_JUDICIAL = "3", "4"

# A API manda a classificação por extenso. Só os códigos que as regras da Paraíba usam.
GRUPOS = {
    "PESSOAL E ENCARGOS SOCIAIS": "1", "JUROS E ENCARGOS DA DIVIDA": "2", "OUTRAS DESPESAS CORRENTES": "3",
    "INVESTIMENTOS": "4", "INVERSOES FINANCEIRAS": "5", "AMORTIZACAO DA DIVIDA": "6",
}
MODALIDADES = [
    (re.compile(r"^AP(LICACAO|\.)? DIRETA DECOR|ENTRE ORG.*FUNDOS"), "91"),
    (re.compile(r"CONSORCIO"), "71"),
    (re.compile(r"^TRANSF.* (A|AO|À) UNIAO"), "20"),
    (re.compile(r"^TRANSF.* ESTADOS"), "30"),
    (re.compile(r"^TRANSF.* MUNICIPIOS"), "40"),
    (re.compile(r"^TRANSF.* MULTIGOVERNAMENTA"), "70"),
    (re.compile(r"^TRANSF.* SEM FINS"), "50"),
    (re.compile(r"^TRANSF.* COM FINS"), "60"),
    (re.compile(r"PARCERIA PUBLICO.PRIVADA"), "67"),
    (re.compile(r"DELEGADA A ESTADOS"), "32"),
    (re.compile(r"DELEGADA A MUNICIPIOS"), "42"),
    (re.compile(r"EXTERIOR"), "80"),
    (re.compile(r"^APLICACAO DIRETA .*ART\.? 24 DA LEI COMPLEMENTAR"), "95"),
    (re.compile(r"^APLICACAO DIRETA .*ART\.? 25 DA LEI COMPLEMENTAR"), "96"),
    (re.compile(r"^APLICACOES DIRETAS"), "90"),
]
ELEMENTOS = [
    (re.compile(r"^APOSENTADORIAS"), "01"),
    (re.compile(r"^PENSOES (DO RPPS|DO MILITAR)|^PENSOES$"), "03"),
    (re.compile(r"^OUTROS BENEFICIOS PREVIDENCIARIOS"), "05"),
    (re.compile(r"^CONTRIBUICAO A ENTIDADES FECHADAS DE PREVIDENCIA"), "07"),
    (re.compile(r"^OBRIGACOES PATRONAIS"), "13"),
    (re.compile(r"^DIARIAS"), "14"),
    (re.compile(r"^AUXILIO FINANCEIRO A ESTUDANTES"), "18"),
    (re.compile(r"^OUTROS SERVICOS DE TERCEIROS\W+PESSOA FISICA"), "36"),
    (re.compile(r"^AUXILIO.ALIMENTACAO"), "46"),
    (re.compile(r"^OUTROS AUXILIOS FINANCEIROS A PESSOAS? FISICAS?"), "48"),
    (re.compile(r"^AUXILIO.TRANSPORTE"), "49"),
]


def _codigo(texto: str, regras) -> str:
    t = " ".join(pb._sem_acento(texto or "").split())
    return next((cod for padrao, cod in regras if padrao.search(t)), "")


def obter(entidade: str, tentativas: int = 4, espera: float = 20, **params) -> dict:
    """Uma chamada à API. Ela responde em ISO-8859-1 e às vezes cai no meio de uma resposta grande."""
    url = URL.format(entidade=entidade) + ("?" + urllib.parse.urlencode(params) if params else "")
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=900, context=CONTEXTO_TLS) as r:
                charset = r.headers.get_content_charset() or "iso-8859-1"
                resposta = json.loads(r.read().decode(charset))["resposta"]
            if resposta.get("status") != "OK":
                raise ValueError(f"{entidade}: status {resposta.get('status')!r}")
            return resposta
        except (OSError, ValueError) as e:
            if tentativa == tentativas:
                raise
            print(f"  {entidade} {params}: {e}; tentando de novo em {espera:.0f} s", flush=True)
            time.sleep(espera)
    raise AssertionError


def municipios() -> list[dict]:
    return obter("Municipios", UNIDADEFEDERATIVA="PE")["conteudo"]


def consorcios(ano: int) -> set[str]:
    """Os códigos das unidades gestoras que são consórcios de municípios."""
    unidades = obter("UnidadesJurisdicionadasMunicipais", EXERCICIO=ano)["conteudo"]
    return {u["ID_UNIDADEGESTORA"] for u in unidades if u.get("NATUREZAORGAO") == NATUREZA_CONSORCIO}


def empenhos(codigo: str, ano: int, pausa: float) -> list[dict]:
    """Todos os empenhos do ano de um município; mês a mês se o ano inteiro passar do limite."""
    r = obter("DespesasMunicipais", ANOREFERENCIA=ano, CODIGO_MUNICIPIO=codigo)
    if int(r["tamanhoResultado"]) < int(r.get("limiteResultado") or LIMITE):
        return r["conteudo"]
    linhas = []
    for mes in range(1, 13):
        time.sleep(pausa)
        m = obter("DespesasMunicipais", ANOREFERENCIA=ano, CODIGO_MUNICIPIO=codigo, MESREFERENCIA=mes)
        if int(m["tamanhoResultado"]) >= int(m.get("limiteResultado") or LIMITE):
            raise RuntimeError(f"{codigo} {ano}/{mes}: {m['tamanhoResultado']} linhas, o limite da API")
        linhas += m["conteudo"]
    return linhas


def linha(l: dict, de_consorcio: set[str]) -> pq.Linha:
    """Um empenho da API -> a linha que o resumo de AC e SC entende."""
    tipo = (l.get("TIPOCREDOR") or "").strip()
    nome = " ".join((l.get("FORNECEDOR") or "").split())
    grupo = GRUPOS.get(" ".join(pb._sem_acento(l.get("NATUREZA") or "").split()), "")
    modalidade = _codigo(l.get("MODALIDADE"), MODALIDADES)
    elemento = _codigo(l.get("ELEMENTODESPESA"), ELEMENTOS)
    if tipo == FOLHA_DE_PAGAMENTO and grupo != "1":
        grupo = "1"            # folha lançada fora do grupo de pessoal (pouco comum): continua sendo folha
    if tipo in PESSOA_FISICA:
        # O CPF vem mascarado; com o nome, serve só para contar pessoas, na memória. Nunca é gravado.
        doc = f"PF {l.get('CPF_CNPJ') or ''} {nome}"
    else:
        doc = re.sub(r"\D", "", l.get("CPF_CNPJ") or "").zfill(14)
    unidade = l.get("NOMEUNIDADEGESTORA") or ""
    if str(l.get("ID_UNIDADE_GESTORA") or "").strip() in de_consorcio:
        unidade = "Consórcio " + unidade   # o resumo deixa os consórcios de fora pelo nome
    if tipo == DEPOSITO_JUDICIAL:
        nome = nome or "DEPOSITO JUDICIAL"
        modalidade = modalidade if modalidade == "91" else "93"   # vai para "outros órgãos públicos" (Justiça)
    return pq.Linha(
        chave=f"{l.get('ID_UNIDADE_GESTORA')}/{(l.get('ID_EMPENHO') or '').strip()}", unidade=unidade, doc=doc, nome=nome,
        pessoa_fisica=True if tipo in PESSOA_FISICA else False if tipo in PESSOA_JURIDICA else None,
        grupo=grupo, modalidade=modalidade, elemento=elemento,
        empenhado=float(l.get("VALOREMPENHADO") or 0), pago=float(l.get("VALORPAGO") or 0),
    )


def carregar(ano: int, so: list[str] | None, pausa: float, refazer: bool) -> tuple[dict, list[str], Counter]:
    lista = [m for m in municipios() if m.get("CODIGOIBGE")]
    if so:
        pedidos = {pb._chave(n) for n in so}
        lista = [m for m in lista if pb._chave(m["MUNICIPIO"]) in pedidos]
        if len(lista) < len(pedidos):
            raise SystemExit(f"município não encontrado no TCE-PE: {sorted(pedidos - {pb._chave(m['MUNICIPIO']) for m in lista})}")
    de_consorcio = consorcios(ano)
    cache_arq = PASTA / f"resumos-{ano}.json"
    cache = {} if refazer or not cache_arq.exists() else json.loads(cache_arq.read_text(encoding="utf-8"))
    PASTA.mkdir(parents=True, exist_ok=True)
    print(f"PE {ano}: {len(lista)} municípios ({len(cache)} já lidos antes)", flush=True)
    resultado, vazios, sem_classe = {}, [], Counter()
    for i, m in enumerate(lista, 1):
        ibge = str(m["CODIGOIBGE"])
        if ibge in cache:
            resultado[ibge] = cache[ibge]
            continue
        t0 = time.time()
        brutas = empenhos(m["CODIGO"], ano, pausa)
        if not brutas:
            vazios.append(m["MUNICIPIO"])   # Fernando de Noronha é distrito do estado: não tem prefeitura
            continue
        for l in brutas:
            if l.get("NATUREZA") and not GRUPOS.get(" ".join(pb._sem_acento(l["NATUREZA"]).split())):
                sem_classe["natureza: " + l["NATUREZA"]] += 1
            if l.get("MODALIDADE") and not _codigo(l["MODALIDADE"], MODALIDADES):
                sem_classe["modalidade: " + l["MODALIDADE"]] += 1
        resumo, fora = pq.resumir(linha(l, de_consorcio) for l in brutas)
        resultado[ibge] = cache[ibge] = resumo
        cache_arq.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        consorcio = f", consórcios R$ {pq.br(fora['consorcios'] / 1e6, 1)} mi fora" if fora["consorcios"] else ""
        print(f"  [{i}/{len(lista)}] {m['MUNICIPIO']}: {pq.br(fora['linhas'])} empenhos, pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi"
              f"{consorcio} ({time.time() - t0:.0f} s)", flush=True)
        time.sleep(pausa)
    return resultado, vazios, sem_classe


def rodar(ano: int, so: list[str] | None, pausa: float, refazer: bool = False) -> None:
    mun, vazios, sem_classe = carregar(ano, so, pausa, refazer)
    if sem_classe:
        print(f"  classificação que o coletor não reconheceu (conferir): {dict(sem_classe.most_common(10))}")
    if vazios:
        print(f"  sem nenhum empenho no TCE-PE (ficaram de fora): {vazios}")
    pq.gravar("PE", FONTE, ano, mun, so)
