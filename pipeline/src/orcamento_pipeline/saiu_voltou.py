"""Saiu daqui, voltou: quanto saiu de cada cidade e estado em impostos federais e quanto voltou da União.

    uv run saiu-voltou              # baixa o PIB dos municípios (IBGE) e monta a conta
    uv run saiu-voltou --sem-baixar # usa o PIB guardado em pipeline/referencia/pib-municipios.json

Não baixa nada além do PIB: junta o que outros comandos já gravaram em site/public/data/, todos de 2025.

    saiu    rfb-mun/2025.json        imposto federal recolhido na cidade (Receita Federal, `uv run rfb`)
            + PIB dos municípios     o mesmo total do país repartido pela parte de cada cidade no PIB (IBGE)
    voltou  federal-2025.json        repasses à prefeitura e a entidades, Bolsa Família e BPC (`uv run federal 2025`)
            inss/2025.json           aposentadorias, pensões e auxílios do INSS (`uv run inss`)
            gasto-direto.json        gasto dos órgãos federais na cidade (`uv run gasto-federal 2025`)
    ao lado emendas.json             emendas pagas (já estão dentro dos repasses: nunca somar)
            irpf-res.json            imposto de renda pela cidade onde a pessoa mora (último ano)

Para não contar duas vezes (ver docs/levantamento-saiu-voltou.md):
- as emendas são pagas como repasse e já estão nos repasses;
- o Fundeb do Portal é a complementação da União mais a parte do fundo feita de impostos federais (os 20% retidos do
  FPM e do FPE), e o FPM do Portal vem sem esses 20%;
- o arquivo do INSS não tem o BPC, que vem do Portal.

Dois casos à parte: em Brasília, do gasto dos órgãos federais só entra o Fundo Constitucional do DF (o resto atende o
país inteiro), e os repasses são os do GDF; no Rio, sai a folha da Marinha e da Aeronáutica paga dali para o país.

Saída: site/public/data/federal/saiu-voltou.json, com cópia em pipeline/referencia/ (usada se faltar um dos arquivos
de entrada, que vêm de fontes que às vezes pedem CAPTCHA).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from collections import defaultdict

from .cidades import RAIZ
from .fontes import CONTEXTO_TLS, USER_AGENT

DADOS = RAIZ / "site" / "public" / "data"
SAIDA = DADOS / "federal" / "saiu-voltou.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "saiu-voltou.json"
REF_PIB = RAIZ / "pipeline" / "referencia" / "pib-municipios.json"
URL_PIB = "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/last"   # PIB a preços correntes, mil reais
ANO = 2025
DF = "5300108"
RIO = "3304557"
FCDF = "Fundo Constitucional do DF"

# Uma linha por cidade (e por estado, com a última coluna).
COLUNAS = ["pop", "saiu", "estimado", "fpm", "sus", "fundeb", "outros_repasses", "entidades", "inss", "bpc",
           "bolsa_familia", "gasto_direto", "emendas", "ir_moradores"]
VOLTOU = ["fpm", "sus", "fundeb", "outros_repasses", "entidades", "inss", "bpc", "bolsa_familia", "gasto_direto"]


def baixar_pib() -> dict:
    req = urllib.request.Request(URL_PIB, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180, context=CONTEXTO_TLS) as resp:
        linhas = json.load(resp)[1:]
    ano = int(linhas[0]["D3C"])
    valores = {l["D1C"]: round(float(l["V"]) * 1000) for l in linhas if l["V"].replace(".", "").isdigit()}
    if len(valores) < 5500:
        raise RuntimeError(f"PIB dos municípios: só {len(valores)} cidades na resposta do IBGE")
    doc = {"fonte": "IBGE, PIB dos Municípios (SIDRA, tabela 5938)", "ano": ano, "mun": valores}
    REF_PIB.write_text(json.dumps(doc, separators=(",", ":")))
    return doc


def ler(caminho: str) -> dict:
    return json.loads((DADOS / caminho).read_text())


def montar(pib: dict) -> dict:
    rfb = ler(f"mapa/rfb-mun/{ANO}.json")
    fed = ler(f"mapa/federal-{ANO}.json")
    inss = ler(f"mapa/inss/{ANO}.json")
    gd = ler("federal/gasto-direto.json")
    emendas = ler("indicadores/emendas.json")
    irpf = ler("mapa/irpf-res.json")
    anos = ler(f"mapa/anos/{ANO}.json")
    nomes = ler("mapa/nomes.json")["mun"]
    if fed["ano"] != ANO or gd["ano"] != ANO:
        raise RuntimeError(f"os arquivos federais não são de {ANO}")
    ano_ir = max(irpf["anos"])
    ir = irpf["anos"][ano_ir]

    total_saiu = sum(v[0] for v in rfb.values())
    total_pib = sum(pib["mun"].values())
    pop = {k: v[0] for k, v in anos["mun"].items()}
    pop[DF] = anos["uf"]["53"][0]
    uf_de = {k: v[1] for k, v in nomes.items()}
    uf_de[DF] = "DF"

    gd_mun = dict(gd["mun"])
    gd_mun[DF] = gd_mun.pop("53")
    i_fcdf = gd["orgaos"].index(next(o for o in gd["orgaos"] if o.startswith(FCDF)))
    fcdf = next(v for i, v in gd_mun[DF][6] if i == i_fcdf)
    fora = {"brasilia": gd_mun[DF][0] - fcdf, "rio": gd_mun[RIO][4]}

    i_fed = {c: i for i, c in enumerate(fed["colunas"])}
    mun = {}
    for k in pop:
        f = fed["mun"].get(k, [0] * len(fed["colunas"]))
        rep = {c: f[i_fed[c]] for c in ("fpm", "saude", "fundeb", "royalties", "educacao", "assistencia", "outros")}
        if k == DF:   # o GDF recebe como estado
            rep = {c: fed["uf"]["DF"].get(c, 0) for c in rep}
        g = gd_mun.get(k, [0] * 5)
        direto = fcdf if k == DF else g[0] - (g[4] if k == RIO else 0)
        em = emendas["mun"].get(k, {}).get(str(ANO), [0, 0, 0, 0])
        mun[k] = {
            "pop": pop[k], "saiu": rfb.get(k, [0])[0],
            "estimado": total_saiu * pib["mun"][k] / total_pib if k in pib["mun"] else None,
            "fpm": rep["fpm"], "sus": rep["saude"], "fundeb": rep["fundeb"],
            "outros_repasses": rep["royalties"] + rep["educacao"] + rep["assistencia"] + rep["outros"],
            "entidades": f[i_fed["entidades"]], "inss": inss.get(k, [0])[0], "bpc": f[i_fed["bpc"]],
            "bolsa_familia": f[i_fed["bolsa_familia"]], "gasto_direto": direto,
            "emendas": em[1] + em[2] if k != DF else em[0], "ir_moradores": ir.get(k, [0, 0])[1],
        }

    # Estados: a soma das cidades e, à parte, o que a União repassou ao governo do estado (no DF já está na cidade).
    uf: dict = defaultdict(lambda: defaultdict(float))
    for k, r in mun.items():
        u = uf[uf_de[k]]
        for c in COLUNAS:
            u[c] += r[c] or 0
    for sigla, u in uf.items():
        u["governo_estadual"] = 0 if sigla == "DF" else sum(fed["uf"].get(sigla, {}).values())
        u["emendas"] = sum(emendas["mun"].get(k, {}).get(str(ANO), [0])[0] for k in mun if uf_de[k] == sigla)

    voltou_cidades = sum(sum(r[c] for c in VOLTOU) for r in mun.values())
    voltou_estados = sum(u["governo_estadual"] for u in uf.values())   # o GDF já está em Brasília
    brasil = {"pop": sum(pop.values()), "saiu": total_saiu, "voltou_cidades": voltou_cidades,
              "voltou_estados": voltou_estados, "fora_brasilia": fora["brasilia"], "fora_rio": fora["rio"],
              "fcdf": fcdf}

    linha = lambda r, cols: [None if r.get(c) is None else round(r[c]) for c in cols]
    return {
        "ano": ANO, "ano_pib": pib["ano"], "ano_ir": int(ano_ir),
        "fonte": "Receita Federal (arrecadação por município); IBGE (PIB dos Municípios); Portal da Transparência "
                 "(transferências, Bolsa Família, BPC e execução da despesa); Ministério da Previdência (benefícios "
                 "do INSS por município)",
        "colunas": COLUNAS,
        "brasil": {k: round(v) for k, v in brasil.items()},
        "mun": {("53" if k == DF else k): linha(r, COLUNAS) for k, r in mun.items()},
        "uf": {s: linha(u, COLUNAS + ["governo_estadual"]) for s, u in sorted(uf.items())},
    }


def resumo(doc: dict) -> None:
    b = doc["brasil"]
    print(f"Brasil {doc['ano']}: saíram R$ {b['saiu'] / 1e9:.0f} bi; voltaram às cidades R$ {b['voltou_cidades'] / 1e9:.0f} bi "
          f"(R$ {100 * b['voltou_cidades'] / b['saiu']:.0f} de cada 100) e aos governos estaduais R$ {b['voltou_estados'] / 1e9:.0f} bi")
    i = {c: n for n, c in enumerate(doc["colunas"])}
    for k, nome in [("3550308", "São Paulo"), ("2511400", "Picuí"), ("53", "Brasília")]:
        r = doc["mun"][k]
        v = sum(r[i[c]] for c in VOLTOU)
        print(f"  {nome}: voltaram R$ {100 * v / r[i['saiu']]:.0f} (recolhido) a R$ {100 * v / r[i['estimado']]:.0f} (estimado) de cada 100")


def main() -> None:
    p = argparse.ArgumentParser(prog="saiu-voltou", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true", help="usa o PIB guardado em pipeline/referencia")
    args = p.parse_args()
    try:
        pib = json.loads(REF_PIB.read_text()) if args.sem_baixar else baixar_pib()
    except Exception as e:  # o IBGE fora do ar não impede a conta: o PIB muda uma vez por ano
        print(f"PIB: {e}; usando {REF_PIB.relative_to(RAIZ)}")
        pib = json.loads(REF_PIB.read_text())
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc = montar(pib)
    except (FileNotFoundError, KeyError, RuntimeError) as e:
        if not REFERENCIA.exists():
            raise
        print(f"falta uma entrada ({e}): o site sai com a cópia de referência")
        shutil.copyfile(REFERENCIA, SAIDA)
        sys.exit(3)
    texto = json.dumps(doc, separators=(",", ":"), ensure_ascii=False)
    SAIDA.write_text(texto)
    REFERENCIA.write_text(texto)
    resumo(doc)
    print(f"saída: {SAIDA.relative_to(RAIZ)} ({len(texto) / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
