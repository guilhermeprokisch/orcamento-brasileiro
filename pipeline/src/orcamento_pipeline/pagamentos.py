"""Para quem cada prefeitura da Paraíba pagou: os empenhos que o Tribunal de Contas (TCE-PB) publica.

    uv run pagamentos                # baixa o ZIP de 2025 (cerca de 190 MB) e resume
    uv run pagamentos --ano 2024
    uv run pagamentos --uf AC        # Acre e Santa Catarina: pelos painéis dos tribunais (pagamentos_qlik.py)
    uv run pagamentos --uf PE        # Pernambuco: pela API de dados abertos do TCE-PE (pagamentos_tcepe.py)
    uv run pagamentos --sem-baixar   # só copia pipeline/referencia/pagamentos*.json para o site (CI)

Fonte: os dados abertos do TCE-PB, um ZIP por ano com todas as 223 prefeituras
(https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-{ano}.zip).
Dentro, um CSV de quase 2 GB, separado por ";", com uma linha por empenho: o município (pelo nome),
a unidade gestora (prefeitura, Câmara, fundos, instituto de previdência…), o credor (nome e CPF ou
CNPJ) e os valores empenhado, liquidado e pago no ano. O CSV é lido direto do ZIP, linha a linha.

Só o valor **pago** conta: somar empenhado, liquidado e pago contaria o mesmo dinheiro três vezes.
Como na prestação de contas ao Tesouro (DCA), entram todas as unidades do município (a Câmara
também, mas não os consórcios de vários municípios, que o arquivo põe na cidade-sede) e ficam de fora as operações entre elas (modalidade 91, "intraorçamentária": a prefeitura
pagando a contribuição ao próprio instituto de previdência, por exemplo), que só mudam o dinheiro
de bolso.

O que não é fornecedor fica à parte, para a lista não ser dominada por isso:
- folha: todo o grupo "Pessoal e encargos sociais", que a prefeitura paga a si mesma (a conta da
  folha) ou a cada servidor;
- previdência: aposentadorias, pensões e contribuição patronal, e o que vai para o INSS ou para o
  instituto de previdência do município;
- dívida e bancos: juros e amortização da dívida e tudo o que vai para bancos (tarifas, Pasep,
  parcelamentos);
- outros órgãos públicos: a própria prefeitura, fundos municipais, Receita Federal, ministérios,
  tribunais (precatórios), governo do estado, Detran, consórcios públicos de municípios.

Pessoas físicas (pelo CPF) entram só como total e número de pessoas: **o CPF nunca é guardado**, e
o nome também não. Microempreendedores individuais cujo nome traz o CPF ou o número da empresa na
frente (o nome do MEI é o da pessoa) contam como pessoa física, como nos contratos (contratos.py).

Saída em site/public/data/indicadores/pagamentos.json, com cópia em pipeline/referencia/pagamentos.json:
    {"fonte", "ano", "uf": "PB", "tipos": [rótulo de cada tipo de credor],
     "mun": {ibge: {"pago", "empenhado", "n" (empenhos com pagamento), "tipos": [pago por tipo],
                    "pessoas": número de pessoas físicas, "empresas": número de fornecedores,
                    "credores": [[nome, CNPJ, pago, empenhos], ...os 15 maiores fornecedores]}}}
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict

from . import cidades as c
from .fontes import CONTEXTO_TLS, USER_AGENT

URL = "https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-{ano}.zip"
PASTA = c.RAIZ / "data" / "raw" / "tce-pb"
SAIDA = c.RAIZ / "site" / "public" / "data" / "indicadores" / "pagamentos.json"
REFERENCIA = c.RAIZ / "pipeline" / "referencia" / "pagamentos.json"
FONTE = "Tribunal de Contas do Estado da Paraíba (TCE-PB), dados abertos de despesas dos municípios"
MAIORES = 15

TIPOS = ["Fornecedores", "Pessoas físicas", "Folha de pagamento", "Previdência", "Dívida e bancos", "Outros órgãos públicos"]
EMPRESA, PESSOA, FOLHA, PREVIDENCIA, DIVIDA, ORGAO = range(len(TIPOS))

# Elementos do grupo "Pessoal" que são previdência: aposentadorias, pensões, outros benefícios,
# contribuição a entidade de previdência e obrigações patronais.
ELEMENTOS_PREVIDENCIA = {"01", "03", "05", "07", "13"}
# Elementos que só existem para pessoa física: serviços de pessoa física, diárias, auxílios, bolsas.
ELEMENTOS_PESSOA = {"14", "18", "36", "46", "48", "49"}
# Transferências a outros governos e a consórcios públicos.
MODALIDADES_ORGAO = {"20", "22", "30", "31", "32", "35", "36", "40", "41", "42", "45", "46", "70", "71", "72", "73", "74", "75", "76", "93"}

PREVIDENCIA_NOME = re.compile(r"PREVID|\bINSS\b|SEGURO SOCIAL|SEGURIDADE SOCIAL|\bIPAM\b|\bIPM\b|\bIPSEM\b|PREV\b")
BANCO_NOME = re.compile(r"^(BANCO|BCO\.?)\s|^BB - |CAIXA ECON|^BRADESCO|^ITAU UNIBANCO|^SANTANDER|^SICOOB|^SICREDI|^BANCO DO NORDESTE")
ORGAO_NOME = re.compile(
    r"PREFEITURA|^MUNICIPIO D|\bCAMARA MUNICIPAL|\bSECRETARIA\b|\bSEC\.? (MUN|DE )|^MINISTERIO|RECEITA FEDERAL"
    r"|\bFUNDO (MUNICIPAL|MUN\b|MUN\.|NACIONAL|ESTADUAL|DE (SAUDE|ASSIST|PREVID|DESENV)|ARRENDAMENTO)|^FNDE|^FMS\b|^FMAS\b"
    r"|\bTRIBUNAL\b|JUSTICA (DO|DA|FEDERAL|ESTADUAL)|^GOVERNO D|^ESTADO D|TESOURO|\bPASEP\b|^UNIAO FEDERAL"
    r"|CONSORCIO (PUBLICO|INTER|DE SAUDE)|^DEPARTAMENTO (ESTADUAL|NACIONAL|MUNICIPAL)|\bDETRAN\b|^DER\b"
    r"|UNIVERSIDADE (ESTADUAL|FEDERAL)|^INSTITUTO FEDERAL|PROCURADORIA|DEFENSORIA|MINISTERIO PUBLICO|^AGENCIA (ESTADUAL|NACIONAL|MUNICIPAL)"
    r"|^SUPERINTENDENCIA|^AUTARQUIA|^CONTROLADORIA|^PODER JUDICIARIO|^JUIZO\b|^VARA\b"
)
# Unidades gestoras que são consórcios de municípios: o arquivo põe cada uma na cidade-sede.
CONSORCIO_UG = re.compile(r"(?i)\s*cons[oó]rcio")
# "12.345.678 FULANO DE TAL" ou "FULANO DE TAL 12345678901 - LOJA": o nome do MEI é o da pessoa, às vezes com o CPF.
MEI = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}\s|(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")


def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().upper()


def _chave(nome: str) -> str:
    return " ".join(_sem_acento(nome or "").replace("-", " ").replace("'", " ").split())


def _digitos_ok(numero: str, pesos: list[int]) -> bool:
    for i in (len(pesos) - 1, len(pesos)):
        soma = sum(int(d) * p for d, p in zip(numero[:i], pesos[-i:]))
        dv = soma % 11
        if int(numero[i]) != (0 if dv < 2 else 11 - dv):
            return False
    return True


def cnpj_valido(doc: str) -> bool:
    return len(doc) == 14 and doc.isdigit() and len(set(doc)) > 1 and _digitos_ok(doc, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])


def cpf_valido(doc: str) -> bool:
    return len(doc) == 11 and doc.isdigit() and len(set(doc)) > 1 and _digitos_ok(doc, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])


def eh_empresa(doc: str, elemento: str) -> bool:
    """O arquivo põe CPF e CNPJ no mesmo campo, o CPF com três zeros na frente. Muitos CNPJs antigos
    também começam com zeros (o do Banco do Brasil é 00.000.000/0001-91): decidem os dígitos
    verificadores e, quando os dois servem, o número da filial e o tipo de gasto."""
    doc = re.sub(r"\D", "", doc or "").zfill(14)
    cnpj = cnpj_valido(doc)
    cpf = doc.startswith("000") and cpf_valido(doc[3:])
    if cnpj and cpf:
        return doc[8:10] == "00" and elemento not in ELEMENTOS_PESSOA
    return cnpj


def valor(s: str) -> float:
    """"1.234,56" -> 1234.56"""
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def baixar(ano: int, refazer: bool = False):
    arq = PASTA / f"despesas-{ano}.zip"
    if arq.exists() and not refazer:
        return arq
    PASTA.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".parte")
    print(f"baixando {URL.format(ano=ano)}", flush=True)
    req = urllib.request.Request(URL.format(ano=ano), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600, context=CONTEXTO_TLS) as resp, tmp.open("wb") as f:
        while bloco := resp.read(1 << 20):
            f.write(bloco)
    tmp.rename(arq)
    return arq


def linhas(arq):
    with zipfile.ZipFile(arq) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""), delimiter=";")


def tipo_do_credor(l: dict, nome: str) -> int:
    grupo, elemento, modalidade = l["codigo_natureza"], l["codigo_elemento_despesa"], l["codigo_modalidade_aplicacao"]
    if grupo == "1":
        return PREVIDENCIA if elemento in ELEMENTOS_PREVIDENCIA else FOLHA
    if grupo in ("2", "6") or BANCO_NOME.search(nome):
        return DIVIDA
    if PREVIDENCIA_NOME.search(nome):
        return PREVIDENCIA
    if modalidade in MODALIDADES_ORGAO or ORGAO_NOME.search(nome):
        return ORGAO
    if not eh_empresa(l["cpf_cnpj"], elemento) or MEI.search(nome):
        return PESSOA
    return EMPRESA


def juntar(m: dict, outro: dict) -> None:
    for k in ("pago", "empenhado", "n", "intra"):
        m[k] += outro[k]
    m["tipos"] = [a + b for a, b in zip(m["tipos"], outro["tipos"])]
    m["pessoas"] |= outro["pessoas"]
    for raiz, (nomes, docs, pago, n) in outro["empresas"].items():
        e = m["empresas"][raiz]
        e[0].update(nomes)
        e[1].update(docs)
        e[2] += pago
        e[3] += n


def resumir(arq, ibge_por_nome: dict[str, str]) -> tuple[dict, dict]:
    novo = lambda: {"pago": 0.0, "empenhado": 0.0, "n": 0, "tipos": [0.0] * len(TIPOS), "intra": 0.0,
                    "pessoas": set(), "empresas": defaultdict(lambda: [Counter(), Counter(), 0.0, 0])}
    mun: dict[str, dict] = defaultdict(novo)
    fora = {"linhas": 0, "sem_municipio": 0.0, "consorcios": 0.0, "nomes": Counter(), "orfas": None}
    com_prefeitura: set[str] = set()
    for i, l in enumerate(linhas(arq), 1):
        fora["linhas"] = i
        pago, empenhado = valor(l["valor_pago"]), valor(l["valor_empenhado"])
        ibge = ibge_por_nome.get(_chave(l["municipio"] or ""))
        if not ibge:
            if l["municipio"] or l["codigo_unidade_gestora"]:
                fora["sem_municipio"] += pago
                fora["nomes"][l["municipio"]] += 1
                continue
            ibge = ""   # linha sem município e sem unidade gestora: ver depois do laço
        elif l["codigo_unidade_gestora"].startswith("201"):   # 201xxx é a prefeitura; 101xxx a Câmara, 3xxxxx e 6xxxxx autarquias e fundos
            com_prefeitura.add(ibge)
        if CONSORCIO_UG.match(l["descricao_unidade_gestora"]):
            fora["consorcios"] += pago   # consórcio de várias prefeituras: não é gasto só desta cidade
            continue
        m = mun[ibge]
        if l["codigo_modalidade_aplicacao"] == "91":
            m["intra"] += pago
            continue
        m["empenhado"] += empenhado
        if not pago:
            continue
        nome = " ".join((l["nome_credor"] or "").split())
        t = tipo_do_credor(l, _sem_acento(nome))
        m["pago"] += pago
        m["n"] += 1
        m["tipos"][t] += pago
        doc = re.sub(r"\D", "", l["cpf_cnpj"] or "").zfill(14)
        if t == PESSOA:
            # Só para contar quantas pessoas: o número é jogado fora no fim e nunca é gravado.
            m["pessoas"].add(doc)
        elif t == EMPRESA:
            e = m["empresas"][doc[:8]]   # filiais da mesma empresa juntas, pela raiz do CNPJ
            e[0][nome] += 1
            e[1][doc] += pago
            e[2] += pago
            e[3] += 1
        if i % 500_000 == 0:
            print(f"  {i:,} linhas".replace(",", "."), flush=True)

    # Em 2025, a prefeitura de Pedras de Fogo veio inteira sem o nome do município e sem o código da unidade
    # (o credor da folha é "Prefeitura Municipal de Pedras de Fogo" e os históricos citam a cidade). Se
    # exatamente uma cidade estiver sem a prefeitura no arquivo, as linhas órfãs são dela.
    if "" in mun:
        orfas = mun.pop("")
        faltam = sorted(set(ibge_por_nome.values()) - com_prefeitura)
        if len(faltam) == 1:
            juntar(mun[faltam[0]], orfas)
            fora["orfas"] = (faltam[0], orfas["pago"] + orfas["intra"])
        else:
            fora["sem_municipio"] += orfas["pago"] + orfas["intra"]
            fora["nomes"]["(sem município)"] += orfas["n"]

    saida = {}
    for ibge, m in sorted(mun.items()):
        empresas = sorted(m["empresas"].values(), key=lambda e: -e[2])
        saida[ibge] = {
            "pago": round(m["pago"]), "empenhado": round(m["empenhado"]), "n": m["n"],
            "tipos": [round(v) for v in m["tipos"]], "intra": round(m["intra"]),
            "pessoas": len(m["pessoas"]), "empresas": len(m["empresas"]),
            "credores": [[e[0].most_common(1)[0][0], e[1].most_common(1)[0][0], round(e[2]), e[3]] for e in empresas[:MAIORES]],
        }
    return saida, fora


def copiar_referencia() -> None:
    """Um arquivo por estado: pagamentos.json (PB) e pagamentos-{uf}.json (os outros)."""
    for ref in sorted(REFERENCIA.parent.glob("pagamentos*.json")):
        destino = SAIDA.with_name(ref.name)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(ref.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"saída: {destino.relative_to(c.RAIZ)} (cópia de {ref.relative_to(c.RAIZ)})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ano", type=int, default=2025)
    p.add_argument("--refazer", action="store_true", help="baixar o ZIP de novo, mesmo se já existir (PE: ler de novo as cidades já lidas)")
    p.add_argument("--sem-baixar", action="store_true", help="só copiar a referência versionada para o site (publicação automática)")
    p.add_argument("--uf", default="PB", choices=["PB", "AC", "SC", "PE"],
                   help="AC e SC vêm dos painéis dos tribunais, PE da API do TCE-PE (os três só respondem do Brasil)")
    p.add_argument("--municipio", action="append", help="AC, SC e PE: só esta cidade (pode repetir); junta-se às que já estão no arquivo")
    p.add_argument("--pausa", type=float, default=1.0, help="AC, SC e PE: segundos entre uma consulta e outra")
    args = p.parse_args()
    if args.sem_baixar:
        copiar_referencia()
        return
    if args.uf == "PE":
        from . import pagamentos_tcepe
        pagamentos_tcepe.rodar(args.ano, args.municipio, args.pausa, args.refazer)
        return
    if args.uf != "PB":
        from . import pagamentos_qlik
        pagamentos_qlik.rodar(args.uf, args.ano, args.municipio, args.pausa)
        return

    arq = baixar(args.ano, args.refazer)
    ibge_por_nome = {_chave(e["ente"]): str(e["cod_ibge"]) for e in c.baixar_entes() if e["esfera"] == "M" and e["uf"] == "PB"}
    mun, fora = resumir(arq, ibge_por_nome)
    doc = {"fonte": FONTE, "ano": args.ano, "uf": "PB", "tipos": TIPOS, "mun": mun}
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    for destino in (SAIDA, REFERENCIA):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")

    pago = sum(m["pago"] for m in mun.values())
    por_tipo = [sum(m["tipos"][i] for m in mun.values()) for i in range(len(TIPOS))]
    print(f"{args.ano}: {fora['linhas']:,} empenhos, {len(mun)} municípios, pago R$ {pago / 1e9:.2f} bi".replace(",", "."))
    for t, v in zip(TIPOS, por_tipo):
        print(f"  {t}: R$ {v / 1e9:.2f} bi ({v / pago:.0%})")
    print(f"  entre unidades do próprio município (fora do total): R$ {sum(m['intra'] for m in mun.values()) / 1e9:.2f} bi")
    print(f"  consórcios de municípios (fora do total): R$ {fora['consorcios'] / 1e6:.0f} mi")
    if fora["orfas"]:
        print(f"  linhas sem município nem unidade, atribuídas a {fora['orfas'][0]} (a única cidade sem a prefeitura no arquivo): R$ {fora['orfas'][1] / 1e6:.0f} mi")
    if fora["sem_municipio"] or fora["nomes"]:
        print(f"  sem município reconhecido: R$ {fora['sem_municipio'] / 1e6:.0f} mi em {sum(fora['nomes'].values())} linhas {dict(fora['nomes'].most_common(5))}")
    print(f"saída: {SAIDA.relative_to(c.RAIZ)} ({len(texto) / 1e3:.0f} KB) e {REFERENCIA.relative_to(c.RAIZ)}")


if __name__ == "__main__":
    main()
