"""Para quem as prefeituras do Tocantins pagaram: as planilhas de empenho e pagamento do TCE-TO (SICAP).

    uv run pagamentos --uf TO                        # as 139 prefeituras, 2025 (cerca de meia hora)
    uv run pagamentos --uf TO --municipio Gurupi     # uma cidade (junta-se às que já estão no arquivo)

Fonte: o Portal do Cidadão do Tribunal de Contas do Tocantins (https://portaldocidadao.tceto.tc.br,
"Municípios (a partir de 2013)" → Dados abertos), sem login. Para cada município e ano:
- portaldocidadao.tceto.tc.br/estadomunicipios/getUnidades: as unidades gestoras (o código é o CNPJ);
- www.tceto.tc.br/sicap/contabilx/relatorios/planilhas/{empenho,pagamento}.php: as planilhas
  "consolidadas" (remessa 14, a última do ano), que trazem todas as unidades do município que
  prestaram contas: prefeitura, Câmara, secretarias, fundos e o fundo ou instituto de previdência
  (o arquivo é o mesmo qualquer que seja a unidade pedida; pedimos o da prefeitura). Quando a Câmara
  não manda os dados ao tribunal, ela fica de fora, e a carga avisa (Gurupi, em 2025; o que a
  prefeitura declarou ao Tesouro também ficou sem ela).

As planilhas são tabelas HTML com extensão .xls (Palmas: 66 MB de empenhos e 49 MB de pagamentos).
Lidas na memória, sem gravar o arquivo. A de pagamento não traz o credor: ele vem da de empenho,
pelo número do empenho na mesma unidade. Cada linha tem um sinal: "-" é anulação de empenho ou
estorno de pagamento, "E" é reforço de empenho. A rubrica (3390350102…) dá o grupo (2º dígito), a modalidade (3º e 4º) e o
elemento da despesa (5º e 6º). Os pagamentos são só de empenhos do próprio ano (restos a pagar ficam
fora, como no pago da prestação de contas ao Tesouro). Cada município lido fica guardado em
data/raw/tce-to/ (só o resumo), para a carga continuar de onde parou.

Conferido com o que as prefeituras declararam ao Tesouro (DCA 2025, pago sem as operações internas):
Abreulândia bate ao real (R$ 35.491.598) e Palmas fica 0,3% abaixo (R$ 2.163,5 mi contra 2.170,1 mi).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py) e do resumo de AC e SC
(pagamentos_qlik.resumir). Pessoas físicas só no total e na contagem, sem nome e **sem CPF**: a
planilha traz o CPF inteiro (e às vezes também dentro do nome); ele só serve, na memória, para contar
pessoas, e nunca é gravado.

O portal respondeu de um endereço do Brasil (21/11/2026); não se sabe se responde de fora. A carga é
feita à mão, como nos outros estados, e fica em pipeline/referencia/pagamentos-to.json; a publicação
automática só copia (`pagamentos --sem-baixar`).
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter

from . import cidades as c
from . import pagamentos as pb
from . import pagamentos_qlik as pq
from . import pagamentos_saida as saida
from .fontes import CONTEXTO_TLS, USER_AGENT

UNIDADES = "https://portaldocidadao.tceto.tc.br/estadomunicipios/getUnidades"
PLANILHA = "https://www.tceto.tc.br/sicap/contabilx/relatorios/planilhas/{tipo}.php"
FONTE = "Tribunal de Contas do Estado do Tocantins (TCE-TO), dados abertos do SICAP no Portal do Cidadão"
PASTA = c.RAIZ / "data" / "raw" / "tce-to"
CONSOLIDADA = 14   # a partir de 2025: 1 a 12 são os meses, 13 a do ordenador, 14 a consolidada

# Colunas que o coletor lê em cada planilha: se o tribunal mudar o cabeçalho, a carga para.
COLUNAS = {
    "empenho": {"unidade": "Unidade Gestora", "rubrica": "Rubrica", "doc": "IdCredor", "nome": "Nome Credor",
                "empenho": "Número Empenho", "valor": "Valor", "sinal": "Sinal"},
    "pagamento": {"unidade": "Uni. Gestora", "rubrica": "Rúbrica", "empenho": "Número Empenho",
                  "valor": "Valor", "sinal": "Sinal"},
}
LINHA = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELULA = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def baixar(url: str, tentativas: int = 4, espera: float = 20) -> bytes:
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=900, context=CONTEXTO_TLS) as r:
                return r.read()
        except OSError as e:
            if tentativa == tentativas:
                raise
            print(f"  {url}: {e}; tentando de novo em {espera:.0f} s", flush=True)
            time.sleep(espera)
    raise AssertionError


def unidades(ibge: str, ano: int) -> list[dict]:
    q = urllib.parse.urlencode({"municipio": ibge, "exercicio": ano, "remessa": CONSOLIDADA, "ajax": "true"})
    return json.loads(baixar(f"{UNIDADES}?{q}"))


def principal(lista: list[dict]) -> dict | None:
    """A prefeitura: a planilha consolidada dela traz todas as unidades do município."""
    principais = [u for u in lista if str(u.get("unidadePrincipal")) == "1"] or lista
    return next((u for u in principais if "PREFEITURA" in pb._sem_acento(u["nome"])), principais[0] if principais else None)


def planilha(tipo: str, unidade: str, ano: int):
    """As linhas da planilha, como dicionários com os nomes de COLUNAS."""
    q = urllib.parse.urlencode({"unidade": unidade, "exercicio": ano, "bimestre": CONSOLIDADA, "status": 1, "conferencia": 1})
    texto = baixar(f"{PLANILHA.format(tipo=tipo)}?{q}").decode("latin-1")
    cabecalho, posicao = None, {}
    for m in LINHA.finditer(texto):
        celulas = [html.unescape(TAG.sub("", x)).strip().removesuffix("'").strip() for x in CELULA.findall(m.group(1))]
        if cabecalho is None:
            cabecalho = celulas
            faltam = [nome for nome in COLUNAS[tipo].values() if nome not in cabecalho]
            if faltam:
                raise SystemExit(f"a planilha de {tipo} do TCE-TO mudou: faltam as colunas {faltam} (tem {cabecalho})")
            posicao = {campo: cabecalho.index(nome) for campo, nome in COLUNAS[tipo].items()}
            continue
        if len(celulas) == len(cabecalho):
            yield {campo: celulas[i] for campo, i in posicao.items()}


def sinal(l: dict) -> int:
    """"+" é o empenho ou o pagamento; "-" a anulação ou o estorno; "E", só nos empenhos, um reforço
    (na Câmara de Palmas, os empenhos estimativos aumentados ao longo do ano)."""
    if l["sinal"] not in ("+", "-", "E"):
        raise SystemExit(f"sinal desconhecido na planilha do TCE-TO: {l['sinal']!r}")
    return -1 if l["sinal"] == "-" else 1


def ler_municipio(unidade: str, ano: int) -> tuple[dict, Counter, set[str]]:
    """Empenhos e pagamentos da planilha consolidada -> o resumo do município."""
    fora: Counter = Counter()
    empenhos: dict[tuple[str, str], pq.Linha] = {}
    for l in planilha("empenho", unidade, ano):
        chave = (l["unidade"][:14], l["empenho"])
        e = empenhos.get(chave)
        if e is None:
            doc = re.sub(r"\D", "", l["doc"])
            rub = l["rubrica"]
            nome = " ".join(l["nome"].split())
            grupo = "1" if saida.FOLHA_NOME.match(pb._sem_acento(nome)) else rub[1:2]
            e = empenhos[chave] = pq.Linha(
                chave="/".join(chave), unidade=l["unidade"].partition(" - ")[2],
                doc=doc.zfill(14),   # na memória só: o CPF serve para contar pessoas e nunca é gravado
                nome=nome, pessoa_fisica=True if len(doc) == 11 else False if len(doc) == 14 else None,
                grupo=grupo, modalidade=rub[2:4], elemento=rub[4:6], empenhado=0.0, pago=0.0,
            )
        e.empenhado += sinal(l) * pb.valor(l["valor"])
    unidades_no_arquivo = {u for u, _ in empenhos}
    for l in planilha("pagamento", unidade, ano):
        valor = sinal(l) * pb.valor(l["valor"])
        if not l["empenho"].startswith(str(ano)):
            fora["outro_ano"] += valor   # não aconteceu em 2025; fica de olho
            continue
        e = empenhos.get((l["unidade"][:14], l["empenho"]))
        if e is None:
            fora["sem_empenho"] += valor
            fora["n_sem_empenho"] += 1
            continue
        e.pago += valor
        fora["pagamentos"] += 1
    resumo, f = pq.resumir(empenhos.values())
    fora["empenhos"] = f["linhas"]
    fora["consorcios"] = f["consorcios"]
    return resumo, fora, unidades_no_arquivo


def carregar(ano: int, so: list[str] | None, pausa: float, refazer: bool) -> tuple[dict, list[str]]:
    entes = sorted((e for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "TO"), key=lambda e: pb._chave(e["ente"]))
    if so:
        pedidos = {pb._chave(n) for n in so}
        entes = [e for e in entes if pb._chave(e["ente"]) in pedidos]
        if len(entes) < len(pedidos):
            raise SystemExit(f"município não encontrado no Tocantins: {sorted(pedidos - {pb._chave(e['ente']) for e in entes})}")
    cache_arq = PASTA / f"resumos-{ano}.json"
    cache = json.loads(cache_arq.read_text(encoding="utf-8")) if cache_arq.exists() else {}
    PASTA.mkdir(parents=True, exist_ok=True)
    print(f"TO {ano}: {len(entes)} municípios ({len(cache)} já lidos antes)", flush=True)
    resultado, vazios = {}, []
    for i, ente in enumerate(entes, 1):
        ibge, nome = str(ente["cod_ibge"]), ente["ente"]
        if ibge in cache and not refazer:   # com --refazer, lê de novo as cidades pedidas e guarda as outras
            resultado[ibge] = cache[ibge]
            continue
        t0 = time.time()
        lista = unidades(ibge, ano)
        pref = principal(lista)
        if not pref:
            vazios.append(nome)
            continue
        resumo, fora, no_arquivo = ler_municipio(pref["id"], ano)
        avisos = []
        if fora["outro_ano"]:
            avisos.append(f"R$ {pq.br(fora['outro_ano'] / 1e6, 1)} mi de empenhos de outro ano")
        if fora["n_sem_empenho"]:
            avisos.append(f"{fora['n_sem_empenho']} pagamentos sem o empenho (R$ {pq.br(fora['sem_empenho'] / 1e6, 2)} mi)")
        if fora["consorcios"]:
            avisos.append(f"consórcios R$ {pq.br(fora['consorcios'] / 1e6, 1)} mi")
        # O portal lista também unidades extintas; o que importa é a Câmara estar no consolidado.
        if any("CAMARA" in pb._sem_acento(u["nome"]) and u["id"] not in no_arquivo for u in lista):
            avisos.append("a Câmara não está no consolidado")
        if not resumo["pago"]:
            vazios.append(nome)
            print(f"  [{i}/{len(entes)}] {nome}: nenhum pagamento em {ano}", flush=True)
            continue
        resultado[ibge] = cache[ibge] = resumo
        cache_arq.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  [{i}/{len(entes)}] {nome}: {pq.br(fora['pagamentos'])} pagamentos de {pq.br(fora['empenhos'])} empenhos, "
              f"pago R$ {pq.br(resumo['pago'] / 1e6, 1)} mi ({time.time() - t0:.0f} s)"
              + (f"; {'; '.join(avisos)}" if avisos else ""), flush=True)
        time.sleep(pausa)
    return resultado, vazios


def rodar(ano: int, so: list[str] | None, pausa: float, refazer: bool = False) -> None:
    mun, vazios = carregar(ano, so, pausa, refazer)
    if vazios:
        print(f"  sem a planilha da prefeitura no TCE-TO (ficaram de fora): {vazios}")
    saida.gravar("TO", FONTE, ano, mun, so)
