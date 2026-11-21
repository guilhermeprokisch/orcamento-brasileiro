"""Para quem as prefeituras do Ceará pagaram: os empenhos e os pagamentos da API de dados abertos do TCE-CE.

    uv run pagamentos --uf CE                            # as 184 prefeituras, 2025 (algumas horas)
    uv run pagamentos --uf CE --municipio Fortaleza      # uma cidade (junta-se às que já estão no arquivo)

Fonte: a API de dados abertos do SIM, o sistema em que as prefeituras cearenses prestam contas ao Tribunal
de Contas do Estado (https://api-dados-abertos.tce.ce.gov.br/sim/), sem cadastro nem chave. Duas tabelas:
- notas_empenhos: cada empenho, com a unidade, a classificação da despesa (o código "33903900" traz o
  grupo, a modalidade e o elemento), o valor empenhado e o credor (nome, tipo e documento);
- notas_pagamentos: cada pagamento, ligado ao empenho pelo órgão, pela unidade, pela data e pelo número.
As duas só trazem os valores e o credor quando a consulta diz o mês ("data_referencia_doc", AAAAMM): sem
ele, a API devolve só meia dúzia de campos. Então são duas consultas por município e mês, em páginas de
1.000 linhas. Cada município lido fica guardado em data/raw/tce-ce/ (só o resumo, alguns KB), para a
carga continuar de onde parou se cair no meio.

Entram todas as unidades que o município manda ao tribunal: prefeitura, Câmara, secretarias, fundos,
autarquias, hospitais municipais e o instituto de previdência. Consórcios de municípios, se aparecerem
como unidade, ficam de fora.

O "pago" é a soma das notas de pagamento de janeiro a dezembro dos empenhos do próprio ano, sem as
estornadas; o que se paga no ano seguinte (restos a pagar, que a API põe em janeiro do outro ano) fica de
fora, como no "pago" da prestação de contas ao Tesouro. Conferido com a DCA 2025: Abaiara bate ao real
(R$ 60.835.974). O empenhado é o valor das notas de empenho, sem descontar as anulações.

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir). O tribunal diz o tipo de cada credor: 1 é pessoa jurídica (com o CNPJ),
2 pessoa física e 6 a folha de pagamento (que vai para "folha", qualquer que seja o elemento). **O CPF
não vem**: o documento de pessoa física já chega cifrado pelo tribunal, e nem esse código é gravado; só
serve, na memória, para contar pessoas.

Saída em site/public/data/indicadores/pagamentos-ce.json, com cópia em pipeline/referencia/, no mesmo
formato do arquivo da Paraíba.
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
from . import pagamentos_saida
from .fontes import CONTEXTO_TLS, USER_AGENT

URL = "https://api-dados-abertos.tce.ce.gov.br/sim/{tabela}"
FONTE = "Tribunal de Contas do Estado do Ceará (TCE-CE), dados abertos do Sistema de Informações Municipais (SIM)"
PASTA = c.RAIZ / "data" / "raw" / "tce-ce"
PAGINA = 1000   # o máximo que a API devolve por chamada

# codigo_tipo_negociante
PESSOA_JURIDICA, PESSOA_FISICA, FOLHA_DE_PAGAMENTO = "1", "2", "6"

CHAVE = ["codigo_orgao", "codigo_unidade_orcamentaria", "data_emissao_empenho", "numero_empenho"]
CAMPOS_EMPENHO = CHAVE + ["data_referencia_doc", "codigo_elemento_despesa", "valor_empenhado",
                          "numero_documento_negociante", "codigo_tipo_negociante", "nome_negociante"]
CAMPOS_PAGAMENTO = CHAVE + ["numero_sub_empenho", "numero_nota_pagamento", "data_referencia_doc", "valor_nota_pagamento", "estado_de_estornado"]
# Sem uma ordem fixa, as páginas se sobrepõem: em Fortaleza, julho de 2025 veio com 6.987 linhas, mas só
# 4.901 empenhos diferentes (umas linhas repetidas, outras nunca vistas). Com a ordem, vêm todos.
ORDEM = {"notas_empenhos": CHAVE, "notas_pagamentos": CHAVE + ["numero_sub_empenho", "numero_nota_pagamento"],
         "unidades_orcamentarias": ["codigo_orgao", "codigo_unidade_orcamentaria"], "municipios": ["codigo_municipio"]}
CONSORCIO = re.compile(r"(?i)cons[oó]rcio")


def obter(tabela: str, tentativas: int = 4, espera: float = 20, **params) -> list[dict]:
    url = URL.format(tabela=tabela) + "?" + urllib.parse.urlencode(params)
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as r:
                d = json.load(r)
        except (OSError, ValueError) as e:
            if tentativa == tentativas:
                raise
            print(f"    {tabela}: {e}; tentando de novo em {espera:.0f} s", flush=True)
            time.sleep(espera)
            continue
        if "elements" not in d:
            raise RuntimeError(f"{tabela} {params}: {str(d)[:300]}")
        return d["elements"]
    raise AssertionError


def todas(tabela: str, campos: list[str] | None, pausa: float, **params) -> list[dict]:
    """Todas as páginas de uma consulta."""
    linhas, inicio = [], 0
    extra = {"$orderby": ",".join(ORDEM[tabela])}
    if campos:
        extra["$select"] = ",".join(campos)
    while True:
        pagina = obter(tabela, **params, **extra, **{"$start_index": inicio, "$count": PAGINA})
        linhas += pagina
        if len(pagina) < PAGINA:
            break
        inicio += PAGINA
        time.sleep(pausa)
    chaves = {tuple(str(l.get(k)) for k in ORDEM[tabela]) for l in linhas}
    if len(chaves) != len(linhas):
        raise RuntimeError(f"{tabela} {params}: {len(linhas)} linhas, mas só {len(chaves)} diferentes (páginas sobrepostas)")
    return linhas


def municipios() -> list[dict]:
    return [m for m in todas("municipios", None, 0) if m.get("codigo_municipio_ibge")]


def chave(l: dict) -> tuple:
    return tuple((l.get(k) or "").strip()[:10] if k == "data_emissao_empenho" else (l.get(k) or "").strip() for k in CHAVE)


def unidades_consorcio(codigo: str, exercicio: int) -> set[tuple[str, str]]:
    unidades = todas("unidades_orcamentarias", None, 0, codigo_municipio=codigo, exercicio_orcamento=exercicio)
    return {(u["codigo_orgao"].strip(), u["codigo_unidade_orcamentaria"].strip()) for u in unidades
            if CONSORCIO.search(u.get("nome_unidade") or "")}


def linha(e: dict, pago: float, de_consorcio: set) -> pq.Linha:
    """Um empenho da API, com o que foi pago nele no ano -> a linha que o resumo de AC e SC entende."""
    tipo = (e.get("codigo_tipo_negociante") or "").strip()
    nome = " ".join((e.get("nome_negociante") or "").split())
    cod = (e.get("codigo_elemento_despesa") or "").strip()   # "33903900": categoria, grupo, modalidade, elemento
    grupo, modalidade, elemento = cod[1:2], cod[2:4], cod[4:6]
    if tipo == FOLHA_DE_PAGAMENTO:
        grupo = "1"   # a folha paga fora do grupo de pessoal (auxílio-alimentação, por exemplo) continua sendo folha
    if tipo == PESSOA_FISICA:
        # O documento já vem cifrado pelo tribunal; com o nome, serve só para contar pessoas. Nunca é gravado.
        doc = f"PF {(e.get('numero_documento_negociante') or '').strip()} {nome}"
    else:
        doc = re.sub(r"\D", "", e.get("numero_documento_negociante") or "").zfill(14)
    k = chave(e)
    unidade = ("Consórcio " if (k[0], k[1]) in de_consorcio else "") + f"{k[0]}.{k[1]}"
    return pq.Linha(
        chave="/".join(k), unidade=unidade, doc=doc, nome=nome,
        pessoa_fisica=True if tipo == PESSOA_FISICA else False if tipo == PESSOA_JURIDICA else None,
        grupo=grupo, modalidade=modalidade, elemento=elemento,
        empenhado=float(e.get("valor_empenhado") or 0), pago=pago,
    )


def ler_municipio(codigo: str, ano: int, pausa: float) -> tuple[list[pq.Linha], dict]:
    exercicio = ano * 100   # a API escreve 2025 como 202500
    empenhos: dict[tuple, dict] = {}
    pagos: Counter = Counter()
    fora = {"estornado": 0.0, "sem_empenho": 0.0, "tipos": Counter()}
    for mes in range(1, 13):
        ref = ano * 100 + mes
        for e in todas("notas_empenhos", CAMPOS_EMPENHO, pausa, codigo_municipio=codigo, exercicio_orcamento=exercicio, data_referencia_doc=ref):
            empenhos[chave(e)] = e
        time.sleep(pausa)
        for p in todas("notas_pagamentos", CAMPOS_PAGAMENTO, pausa, codigo_municipio=codigo, exercicio_orcamento=exercicio, data_referencia_doc=ref):
            v = float(p.get("valor_nota_pagamento") or 0)
            if p.get("estado_de_estornado"):
                fora["estornado"] += v
            else:
                pagos[chave(p)] += v
        time.sleep(pausa)
    for k in set(pagos) - set(empenhos):
        fora["sem_empenho"] += pagos.pop(k)
    de_consorcio = unidades_consorcio(codigo, exercicio)
    for e in empenhos.values():
        tipo = (e.get("codigo_tipo_negociante") or "").strip()
        fora["tipos"][tipo] += 1
        if tipo not in (PESSOA_JURIDICA, PESSOA_FISICA, FOLHA_DE_PAGAMENTO):
            fora["tipos"][f"{tipo}: {' '.join((e.get('nome_negociante') or '').split())[:40]}"] += 1
    return [linha(e, pagos.get(k, 0.0), de_consorcio) for k, e in empenhos.items()], fora


def carregar(ano: int, so: list[str] | None, pausa: float, refazer: bool) -> dict:
    lista = municipios()
    if so:
        pedidos = {pb._chave(n) for n in so}
        lista = [m for m in lista if pb._chave(m["nome_municipio"]) in pedidos]
        if len(lista) < len(pedidos):
            raise SystemExit(f"município não encontrado no TCE-CE: {sorted(pedidos - {pb._chave(m['nome_municipio']) for m in lista})}")
    cache_arq = PASTA / f"resumos-{ano}.json"
    cache = {} if not cache_arq.exists() else json.loads(cache_arq.read_text(encoding="utf-8"))
    if refazer:   # ler de novo as cidades pedidas (todas, sem --municipio)
        pedidas = {str(m["codigo_municipio_ibge"]) for m in lista}
        cache = {k: v for k, v in cache.items() if k not in pedidas}
    PASTA.mkdir(parents=True, exist_ok=True)
    print(f"CE {ano}: {len(lista)} municípios ({sum(str(m['codigo_municipio_ibge']) in cache for m in lista)} já lidos antes)", flush=True)
    resultado, tipos = {}, Counter()
    for i, m in enumerate(lista, 1):
        ibge = str(m["codigo_municipio_ibge"])
        if ibge in cache:
            resultado[ibge] = cache[ibge]
            continue
        t0 = time.time()
        linhas, fora = ler_municipio(m["codigo_municipio"], ano, pausa)
        tipos.update(fora["tipos"])
        if not linhas:
            print(f"  [{i}/{len(lista)}] {m['nome_municipio']}: nenhum empenho em {ano}", flush=True)
            continue
        resumo, fora_resumo = pq.resumir(linhas)
        resultado[ibge] = cache[ibge] = resumo
        cache_arq.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        avisos = [f"{nome} R$ {pq.br(v / 1e6, 1)} mi fora" for nome, v in
                  (("estornado", fora["estornado"]), ("pago sem o empenho", fora["sem_empenho"]), ("consórcios", fora_resumo["consorcios"])) if v]
        print(f"  [{i}/{len(lista)}] {m['nome_municipio']}: {pq.br(len(linhas))} empenhos, pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi"
              f"{', ' + ', '.join(avisos) if avisos else ''} ({time.time() - t0:.0f} s)", flush=True)
    desconhecidos = Counter({t: n for t, n in tipos.items() if t not in (PESSOA_JURIDICA, PESSOA_FISICA, FOLHA_DE_PAGAMENTO)})
    if desconhecidos:
        print(f"  tipos de credor que o coletor não conhece (conferir): {dict(desconhecidos.most_common(12))}")
    return resultado


def rodar(ano: int, so: list[str] | None, pausa: float, refazer: bool = False) -> None:
    mun = carregar(ano, so, pausa, refazer)
    pagamentos_saida.gravar("CE", FONTE, ano, mun, so)
