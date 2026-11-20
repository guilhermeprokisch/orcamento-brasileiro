"""Para quem as prefeituras do Acre e de Santa Catarina pagaram: os empenhos dos painéis Qlik dos tribunais.

    uv run pagamentos --uf AC                                # as 22 prefeituras do Acre, 2025
    uv run pagamentos --uf SC --municipio Florianópolis      # uma cidade (junta-se às que já estão no arquivo)
    uv run pagamentos --uf SC                                # as 295 de SC: cerca de 3 milhões de empenhos, horas

O TCE-AC (Acre Transparente, "Despesa") e o TCE-SC (Farol, "Despesas Municipais") não publicam arquivo
para baixar, mas os painéis em Qlik respondem, sem login, a consultas pela mesma conexão que o
navegador usa (qlik.py). **Os dois servidores só aceitam acesso do Brasil** (conferido em 20/11/2026:
da Áustria e da Alemanha, o do Acre não responde e o de SC devolve 403). Por isso a carga é feita à
mão, de um computador no Brasil, e fica em pipeline/referencia/; a publicação automática só copia
(`pagamentos --sem-baixar`), como na Paraíba.

Uma cidade de cada vez, uma consulta de cada vez, com pausa entre as páginas. Antes de cada carga, os
nomes das tabelas e dos campos são conferidos: se o painel mudar, a carga para em vez de gravar errado.

O que se lê, por empenho do ano (o número do empenho entra sempre, porque o Qlik junta linhas iguais):
- AC: tabela EMPENHO, uma linha por empenho, com o valor pago dele. Os estornos vêm em linhas à parte,
  com valor negativo. Município pelo nome do ente (NOME_ENTE), unidade pela "entidade".
- SC: tabela Empenho, com os pagamentos (Pagamento) e os estornos de pagamento (ESTORNO_PAGAMENTO)
  ligados a ela. O pago é o que foi pago no próprio ano, menos o que foi estornado; o que se paga
  no ano seguinte (restos a pagar) fica de fora, como no "pago" da prestação de contas ao Tesouro.
  Município pelo ente (nomeEnte), só os do tipo MUNICIPIO (os consórcios são entes à parte).

Daí em diante, as mesmas regras da Paraíba (pagamentos.py): só o pago conta; operações entre unidades do
município (modalidade 91) ficam fora do total; folha, previdência, dívida e bancos e outros órgãos
públicos à parte dos fornecedores; consórcios fora; pessoas físicas só no total e na contagem, sem
nome e **sem CPF** (o número só serve, na memória, para contar pessoas, e nunca é gravado). Os maiores
fornecedores que o tribunal manda sem nome ganham a razão social do cadastro aberto de CNPJ.

Conferido com o que as prefeituras declararam ao Tesouro (DCA 2025, pago sem as operações internas):
Florianópolis bate ao centavo (R$ 3.572.088.570); Rio Branco fica 0,2% abaixo (R$ 1.707,8 mi contra 1.711,3 mi).

Saída em site/public/data/indicadores/pagamentos-{uf}.json, com cópia em pipeline/referencia/, no
mesmo formato do arquivo da Paraíba.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from . import cidades as c
from . import pagamentos as pb
from .fontes import CONTEXTO_TLS, USER_AGENT
from .qlik import ErroQlik, Sessao

# Nome de empresa pelo CNPJ, para os fornecedores que o tribunal manda sem nome (no Acre, cerca de 13% do
# que Rio Branco pagou a empresas em 2025). Cadastro aberto da Receita Federal, servido por estes dois sites.
URLS_CNPJ = ["https://minhareceita.org/{cnpj}", "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"]
CACHE_CNPJ = c.RAIZ / "data" / "raw" / "cnpj" / "nomes.json"


@dataclass
class Painel:
    uf: str
    host: str
    app: str
    fonte: str
    campo_ano: str
    campo_ente: str
    # O que precisa existir no modelo do painel: {tabela: [campos]}.
    campos: dict[str, list[str]]
    # Na ordem: chave do empenho, unidade, CPF/CNPJ, nome do credor, tipo de pessoa, grupo, modalidade, elemento.
    dimensoes: list[str]
    # Na ordem: empenhado, pago ({ano} é trocado pelo ano da carga).
    medidas: list[str]
    # Para listar só os municípios: (campo, valor). None quando o campo do ente já só tem municípios e o estado.
    filtro_municipio: tuple[str, str] | None = None
    fora: set[str] = field(default_factory=set)   # entes que não são prefeitura (o governo do estado)

    def __post_init__(self):
        assert len(self.dimensoes) == 8 and len(self.medidas) == 2


AC = Painel(
    uf="AC",
    host="qlik.tceac.tc.br",
    app="7e2eb635-c55d-41d4-9d1e-3d33c6730a1c",
    fonte="Tribunal de Contas do Estado do Acre (TCE-AC), painel Despesa do Acre Transparente",
    campo_ano="ano_empenho",
    campo_ente="NOME_ENTE",
    campos={"EMPENHO": ["NOME_ENTE", "entidade", "NUMERO_EMPENHO", "ano_empenho", "CREDOR", "NOME_CREDOR", "NOME_TIPO_CREDOR",
                        "numero_grupo_natureza_despesa", "numero_modalidade_aplicacao", "numero_elemento_despesa",
                        "VALOR_EMPENHO", "valor_pago"]},
    dimensoes=["NUMERO_EMPENHO", "entidade", "CREDOR", "NOME_CREDOR", "NOME_TIPO_CREDOR",
               "numero_grupo_natureza_despesa", "numero_modalidade_aplicacao", "numero_elemento_despesa"],
    medidas=["Sum(VALOR_EMPENHO)", "Sum(valor_pago)"],
    fora={"ESTADO DO ACRE"},
)

SC = Painel(
    uf="SC",
    host="paineistransparencia.tce.sc.gov.br",
    app="74a8ae0b-233d-44e6-b341-1f718d19802f",
    fonte="Tribunal de Contas do Estado de Santa Catarina (TCE-SC), painel Farol de despesas municipais",
    campo_ano="Ano_Empenho",
    campo_ente="nomeEnte",
    campos={
        "Empenho": ["Chave_Empenho", "ID Empenho", "CPF_CNPJ", "NOME_CREDOR", "tipo_pessoa_aux", "Valor Empenho", "identificadorUG"],
        "ESTORNO": ["ID Empenho", "Valor Estorno"],
        "ENTE": ["nomeEnte", "identificadorTipoEnte", "idEnte"],
        "UNIDADE_GESTORA": ["nomeUG", "identificadorUG", "idEnte"],
        "Calendario_Empenho": ["Ano_Empenho"],
        "Pagamento": ["ID Empenho", "Valor Transação Pagamento", "Data Pagamento"],
        "CALENDARIO_PAGAMENTO": ["Ano_Pagamento"],
        "ESTORNO_PAGAMENTO": ["ID PagamentoEmpenho", "Valor Estorno Pagamento"],
        "GrupoNatureza": ["codigoGrupoNaturezaDespesa"],
        "ModalidadeAplicacao": ["codigoModalidadeAplicacao"],
        "ElementoDespesa": ["codigoElementoDespesa"],
    },
    dimensoes=["Chave_Empenho", "nomeUG", "CPF_CNPJ", "NOME_CREDOR", "tipo_pessoa_aux",
               "codigoGrupoNaturezaDespesa", "codigoModalidadeAplicacao", "codigoElementoDespesa"],
    # Os estornos (do empenho e do pagamento) vêm com sinal negativo.
    medidas=["RangeSum(Sum([Valor Empenho]), Sum([Valor Estorno]))",
             "RangeSum(Sum({<Ano_Pagamento={{ano}}>} [Valor Transação Pagamento]), Sum({<Ano_Pagamento={{ano}}>} [Valor Estorno Pagamento]))"],
    filtro_municipio=("identificadorTipoEnte", "MUNICIPIO"),
)

PAINEIS = {"AC": AC, "SC": SC}


@dataclass
class Linha:
    """Um empenho, já com os nomes do coletor da Paraíba."""
    chave: str
    unidade: str
    doc: str
    nome: str
    pessoa_fisica: bool | None
    grupo: str
    modalidade: str
    elemento: str
    empenhado: float
    pago: float


def linha(valores: list) -> Linha:
    chave, unidade, doc, nome, tipo, grupo, modalidade, elemento, empenhado, pago = valores
    tipo = (tipo or "").upper()
    return Linha(
        chave=chave or "", unidade=unidade or "", doc=re.sub(r"\D", "", doc or "").zfill(14), nome=" ".join((nome or "").split()),
        pessoa_fisica=True if "FISICA" in pb._sem_acento(tipo) else False if "JURIDICA" in pb._sem_acento(tipo) else None,
        grupo=(grupo or "").strip(), modalidade=(modalidade or "").strip().zfill(2), elemento=(elemento or "").strip().zfill(2),
        empenhado=empenhado or 0.0, pago=pago or 0.0,
    )


def tipo_do_credor(l: Linha) -> int:
    t = pb.tipo_do_credor({"codigo_natureza": l.grupo, "codigo_elemento_despesa": l.elemento,
                           "codigo_modalidade_aplicacao": l.modalidade, "cpf_cnpj": l.doc}, pb._sem_acento(l.nome))
    # O tribunal diz se é pessoa física: vale mais que o teste dos dígitos.
    if t == pb.EMPRESA and l.pessoa_fisica:
        return pb.PESSOA
    return t


def resumir(linhas) -> tuple[dict, dict]:
    """Os empenhos de um município -> o resumo no formato da Paraíba, e o que ficou de fora."""
    m = {"pago": 0.0, "empenhado": 0.0, "n": 0, "tipos": [0.0] * len(pb.TIPOS), "intra": 0.0, "pessoas": set(),
         "empresas": defaultdict(lambda: [Counter(), Counter(), 0.0, 0])}
    fora = {"linhas": 0, "consorcios": 0.0}
    for l in linhas:
        fora["linhas"] += 1
        if pb.CONSORCIO_UG.match(l.unidade):
            fora["consorcios"] += l.pago
            continue
        if l.modalidade == "91":
            m["intra"] += l.pago
            continue
        m["empenhado"] += l.empenhado
        if not l.pago:
            continue
        t = tipo_do_credor(l)
        m["pago"] += l.pago
        m["n"] += 1
        m["tipos"][t] += l.pago
        if t == pb.PESSOA:
            m["pessoas"].add(l.doc)   # só para contar; jogado fora no fim
        elif t == pb.EMPRESA:
            e = m["empresas"][l.doc[:8]]
            e[0][l.nome] += 1
            e[1][l.doc] += l.pago
            e[2] += l.pago
            e[3] += 1
    empresas = sorted(m["empresas"].values(), key=lambda e: -e[2])
    resumo = {
        "pago": round(m["pago"]), "empenhado": round(m["empenhado"]), "n": m["n"],
        "tipos": [round(v) for v in m["tipos"]], "intra": round(m["intra"]),
        "pessoas": len(m["pessoas"]), "empresas": len(m["empresas"]),
        "credores": [[nome_mais_comum(e[0]), e[1].most_common(1)[0][0], round(e[2]), e[3]] for e in empresas[:pb.MAIORES]],
    }
    return resumo, fora


def nome_mais_comum(nomes: Counter) -> str:
    com_nome = [(n, q) for n, q in nomes.most_common() if n]
    return com_nome[0][0] if com_nome else ""


def nome_do_cnpj(cnpj: str, cache: dict) -> str:
    if cnpj in cache:
        return cache[cnpj]
    for url in URLS_CNPJ:
        try:
            req = urllib.request.Request(url.format(cnpj=cnpj), headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30, context=CONTEXTO_TLS) as r:
                nome = (json.load(r).get("razao_social") or "").strip()
        except (OSError, ValueError):
            continue
        if nome:
            cache[cnpj] = nome
            time.sleep(0.5)
            return nome
    return ""


def completar_nomes(mun: dict) -> int:
    """Põe o nome (razão social) nos maiores fornecedores que vieram só com o CNPJ."""
    cache = json.loads(CACHE_CNPJ.read_text(encoding="utf-8")) if CACHE_CNPJ.exists() else {}
    faltou = 0
    for resumo in mun.values():
        for credor in resumo["credores"]:
            if not credor[0]:
                credor[0] = nome_do_cnpj(credor[1], cache) or f"CNPJ {formatar_cnpj(credor[1])}"
                faltou += credor[0].startswith("CNPJ ")
    CACHE_CNPJ.parent.mkdir(parents=True, exist_ok=True)
    CACHE_CNPJ.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    return faltou


def formatar_cnpj(d: str) -> str:
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else d


def br(v: float, casas: int = 0) -> str:
    """1234567.8 -> 1.234.567,8"""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def municipios(s: Sessao, doc: int, painel: Painel) -> list[str]:
    s.limpar(doc)
    if painel.filtro_municipio:
        campo, valor = painel.filtro_municipio
        s.selecionar(doc, campo, [valor])
    nomes = [n for n in s.valores(doc, painel.campo_ente) if n not in painel.fora]
    s.limpar(doc)
    return nomes


def abrir(painel: Painel, ano: int, pausa: float) -> tuple[Sessao, int, dict]:
    """Abre o painel e confere que ele ainda tem as tabelas, os campos e o ano que o coletor lê."""
    s = Sessao(painel.host, painel.app, pausa=pausa).__enter__()
    try:
        doc = s.abrir_doc()
        tabelas = s.conferir_campos(doc, painel.campos)
        anos = s.valores(doc, painel.campo_ano)
        if str(ano) not in anos:
            raise ErroQlik(f"o painel do {painel.uf} não tem {ano} (tem {', '.join(anos)})")
    except BaseException:
        s.__exit__()
        raise
    return s, doc, tabelas


def ler_municipio(s: Sessao, doc: int, painel: Painel, ano: int, nome: str, medidas: list[str]) -> tuple[dict, dict]:
    s.limpar(doc)
    s.selecionar(doc, painel.campo_ano, [ano])
    s.selecionar(doc, painel.campo_ente, [nome])
    total: list[int] = []
    resumo, fora = resumir(linha(v) for v in s.ler_tabela(doc, painel.dimensoes, medidas, total=total))
    if fora["linhas"] != total[0]:
        raise ErroQlik(f"{nome}: o Qlik disse {total[0]} linhas e vieram {fora['linhas']}")
    return resumo, fora


def carregar(painel: Painel, ano: int, so: list[str] | None, pausa: float, ibge_por_nome: dict[str, str],
             tentativas: int = 3, espera: float = 30) -> tuple[dict, list[str]]:
    resultado, sem_ibge = {}, []
    s, doc, tabelas = abrir(painel, ano, pausa)
    try:
        nomes = municipios(s, doc, painel)
        if so:
            pedidos = {pb._chave(n) for n in so}
            nomes = [n for n in nomes if pb._chave(n) in pedidos]
            if len(nomes) < len(pedidos):
                raise SystemExit(f"município não encontrado no painel do {painel.uf}: {sorted(pedidos - {pb._chave(n) for n in nomes})}")
        print(f"{painel.uf} {ano}: {len(nomes)} municípios; modelo com {br(sum(t[0] for t in tabelas.values()))} linhas", flush=True)
        medidas = [m.replace("{ano}", str(ano)) for m in painel.medidas]
        for i, nome in enumerate(nomes, 1):
            ibge = ibge_por_nome.get(pb._chave(nome))
            if not ibge:
                sem_ibge.append(nome)
                continue
            if i > 1:
                time.sleep(pausa)
            t0 = time.time()
            # Numa carga longa a conexão pode cair: abre de novo e repete a cidade, algumas vezes.
            for tentativa in range(1, tentativas + 1):
                try:
                    resumo, fora = ler_municipio(s, doc, painel, ano, nome, medidas)
                    break
                except (ErroQlik, OSError) as e:
                    if tentativa == tentativas:
                        raise
                    print(f"  {nome}: {e}; tentando de novo em {espera:.0f} s", flush=True)
                    s.__exit__()
                    time.sleep(espera)
                    s, doc, _ = abrir(painel, ano, pausa)
            resultado[ibge] = resumo
            print(f"  [{i}/{len(nomes)}] {nome}: {br(fora['linhas'])} empenhos, pago R$ {br(resumo['pago'] / 1e6, 1)} mi"
                  f" ({time.time() - t0:.0f} s)", flush=True)
    finally:
        s.__exit__()
    return resultado, sem_ibge


def saida(uf: str):
    nome = f"pagamentos-{uf.lower()}.json"
    return pb.SAIDA.with_name(nome), pb.REFERENCIA.with_name(nome)


def rodar(uf: str, ano: int, so: list[str] | None, pausa: float) -> None:
    painel = PAINEIS[uf]
    ibge_por_nome = {pb._chave(e["ente"]): str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == uf}
    mun, sem_ibge = carregar(painel, ano, so, pausa, ibge_por_nome)
    if sem_nome := completar_nomes(mun):
        print(f"  {sem_nome} fornecedores sem nome nem no cadastro de CNPJ: aparecem pelo CNPJ")
    destino, referencia = saida(uf)

    # Carga de algumas cidades: junta com as que já estavam no arquivo do mesmo ano.
    if so and referencia.exists():
        antigo = json.loads(referencia.read_text(encoding="utf-8"))
        if antigo.get("ano") == ano:
            mun = {**antigo["mun"], **mun}
    doc = {"fonte": painel.fonte, "ano": ano, "uf": uf, "tipos": pb.TIPOS, "mun": dict(sorted(mun.items()))}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for arq in (destino, referencia):
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(texto, encoding="utf-8")
    if sem_ibge:
        print(f"  sem código do IBGE (ficaram de fora): {sem_ibge}")
    print(f"saída: {destino.relative_to(c.RAIZ)} ({len(mun)} municípios, {len(texto) / 1e3:.0f} KB) e {referencia.relative_to(c.RAIZ)}")
