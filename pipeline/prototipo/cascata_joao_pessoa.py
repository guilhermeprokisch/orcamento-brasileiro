"""Protótipo da cascata do gasto: o que a prefeitura de João Pessoa pagou em 2025, área › tipo de despesa › credor.

    python pipeline/prototipo/cascata_joao_pessoa.py caminho/do/despesas-2025.zip

O ZIP é o mesmo dos pagamentos da Paraíba (pagamentos.py, cerca de 190 MB):
https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-2025.zip

As regras são as de pagamentos.py, para o total bater com /cidades: só o valor pago; fora as operações entre
unidades do município (modalidade 91) e os consórcios. Empresas (CNPJ válido, sem cara de MEI) aparecem pelo nome,
juntando as filiais pela raiz do CNPJ. Pagamentos a pessoas físicas (servidores, aposentados, prestadores, MEIs)
entram só como total e número de pessoas: **o CPF e o nome nunca são gravados**.

Saída: site/public/prototipo/cascata-joao-pessoa.json
    {"fonte", "ano", "nome", "valor", "tipos": [rótulos], "filhos": [
        {"nome": função, "valor", "filhos": [
            {"nome": elemento, "valor", "filhos": [
                {"nome", "valor", "n": empenhos, "tipo": índice em tipos, "cnpj"?, "licitacao"?, "pessoas"?}, ...]}]}]}
Em cada tipo de despesa ficam os 40 maiores credores; o resto vira um item "outros", com quantos são.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from orcamento_pipeline import pagamentos as p  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "site" / "public" / "prototipo" / "cascata-joao-pessoa.json"
MUNICIPIO = "JOAO PESSOA"
MAIORES = 40
PESSOAS_ROTULO = "Pagamentos a pessoas físicas"


def _por_tipo(itens: list[dict]) -> Counter:
    soma = Counter()
    for f in itens:
        soma[f["tipo"]] += f["valor"]
    return soma


def main(arq: str) -> None:
    # (função, elemento) -> credor -> [nome Counter, pago, empenhos, tipo, licitação Counter]
    arvore: dict[tuple[str, str], dict[str, list]] = defaultdict(dict)
    pessoas: dict[tuple[str, str], set] = defaultdict(set)   # só para contar; jogado fora no fim
    fora = Counter()
    for l in p.linhas(arq):
        if p._chave(l["municipio"] or "") != MUNICIPIO:
            continue
        pago = p.valor(l["valor_pago"])
        if p.CONSORCIO_UG.match(l["descricao_unidade_gestora"]):
            fora["consorcios"] += pago
            continue
        if l["codigo_modalidade_aplicacao"] == "91":
            fora["intra"] += pago
            continue
        if not pago:
            continue
        nome = " ".join((l["nome_credor"] or "").split())
        sem = p._sem_acento(nome)
        t = p.tipo_do_credor(l, sem)
        doc = re.sub(r"\D", "", l["cpf_cnpj"] or "").zfill(14)
        empresa_doc = p.eh_empresa(l["cpf_cnpj"], l["codigo_elemento_despesa"]) and not p.MEI.search(sem)
        chave = (l["funcao"].strip() or "Sem função", l["elemento_despesa"].strip() or "Sem elemento")
        if not empresa_doc:
            pessoas[chave].add(doc)
            c = arvore[chave].setdefault("#pessoas", [Counter(), 0.0, 0, p.PESSOA, Counter()])
        else:
            c = arvore[chave].setdefault(doc[:8], [Counter(), 0.0, 0, t, Counter(), doc])
            c[0][nome] += 1
            c[4][(l["modalidade_licitacao"] or "").strip()] += pago
        c[1] += pago
        c[2] += 1

    funcoes: dict[str, list] = defaultdict(list)
    for (funcao, elemento), credores in arvore.items():
        filhos = []
        for raiz, c in credores.items():
            if raiz == "#pessoas":
                n = len(pessoas[(funcao, elemento)])
                filhos.append({"nome": PESSOAS_ROTULO, "valor": round(c[1]), "n": c[2], "tipo": c[3], "pessoas": n})
            else:
                item = {"nome": c[0].most_common(1)[0][0], "valor": round(c[1]), "n": c[2], "tipo": c[3],
                        "cnpj": c[5]}
                lic = c[4].most_common(1)[0][0]
                if lic:
                    item["licitacao"] = lic
                filhos.append(item)
        filhos.sort(key=lambda f: -f["valor"])
        nomeados = [f for f in filhos if "pessoas" not in f]
        grupo_pessoas = [f for f in filhos if "pessoas" in f]
        resto = nomeados[MAIORES:]
        filhos = sorted(nomeados[:MAIORES] + grupo_pessoas, key=lambda f: -f["valor"])
        if resto:
            filhos.append({"nome": f"outros {len(resto)} credores", "valor": sum(f["valor"] for f in resto),
                           "n": sum(f["n"] for f in resto), "resto": len(resto),
                           "tipo": _por_tipo(resto).most_common(1)[0][0]})
        funcoes[funcao].append({"nome": elemento, "valor": sum(f["valor"] for f in filhos), "filhos": filhos})

    raiz = [{"nome": f, "valor": sum(e["valor"] for e in els), "filhos": sorted(els, key=lambda e: -e["valor"])}
            for f, els in funcoes.items()]
    raiz.sort(key=lambda f: -f["valor"])
    total = sum(f["valor"] for f in raiz)
    doc = {"fonte": p.FONTE, "ano": 2025, "nome": "Prefeitura de João Pessoa", "valor": total,
           "tipos": p.TIPOS, "filhos": raiz}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    SAIDA.write_text(texto, encoding="utf-8")
    print(f"pago R$ {total / 1e9:.3f} bi em {len(raiz)} áreas; fora: intra R$ {fora['intra'] / 1e6:.0f} mi,"
          f" consórcios R$ {fora['consorcios'] / 1e6:.0f} mi")
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
