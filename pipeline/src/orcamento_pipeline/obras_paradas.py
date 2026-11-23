"""Obras paradas: as obras com dinheiro federal que o TCU considera paralisadas, por cidade e estado.

    uv run obras-paradas                  # lê as tabelas em data/raw/tcu-obras/ e grava o JSON
    uv run obras-paradas --sem-baixar     # só copia pipeline/referencia/obras-paradas.json

Fonte: o Painel de Obras Paralisadas do TCU (https://paineis.tcu.gov.br/obrasparalisadas). O TCU junta nove
bases do governo federal (Caixa, FNDE, Funasa, SISMOB, DNIT, Codevasf, SESu, Setec e outras obras do MEC) e
publica uma fotografia por semestre ("data-base"). O painel é um Power BI sem arquivo para baixar: cada
data-base é exportada à mão na página "Tabela de dados" (menu "…" da tabela → Exportar dados → xlsx, com o
filtro de Situação em "Todos") e salva como data/raw/tcu-obras/obras-AAAA-MM.xlsx. Ver
docs/levantamento-obras-paradas.md.

O que sai daqui:

- a última data-base inteira: cada obra paralisada com cidade, quem paga, valores, quanto foi feito, a causa
  e a situação que o próprio órgão informa (que nem sempre é "paralisada": o TCU tem critério próprio);
- desde quando a obra aparece parada nas datas-base seguidas, até a última ("na lista desde");
- o que aconteceu, na última data-base, com as obras que estavam paradas na anterior.

A cidade vem como texto ("Carnaubal/CE") e é casada pelo nome com o cadastro do SICONFI. Obras só com a UF
(DNIT, Codevasf, parte das universidades) ficam no estado, sem cidade.

Saída: site/public/data/obras-paradas/obras-paradas.json, com cópia em pipeline/referencia/. A carga é à mão
(uma vez por semestre, quando o TCU publica uma data-base nova); a publicação usa --sem-baixar.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .cidades import RAIZ, baixar_entes
from .folha_estadual import chave

PASTA = RAIZ / "data" / "raw" / "tcu-obras"
SAIDA = RAIZ / "site" / "public" / "data" / "obras-paradas" / "obras-paradas.json"
REFERENCIA = RAIZ / "pipeline" / "referencia" / "obras-paradas.json"
FONTE = "TCU, Painel de Obras Paralisadas (paineis.tcu.gov.br/obrasparalisadas), tabela de dados"
URL = "https://paineis.tcu.gov.br/obrasparalisadas"

PARALISADA = "Paralisada"
MAIORES_UF = 10
MAIORES_BRASIL = 25
CIDADES_UF = 10

# Quem paga, como aparece no site (o nome que o TCU usa fica no arquivo para conferir).
QUEM_PAGA = {
    "Fundo Nacional de Desenvolvimento da Educação": "FNDE (Educação)",
    "Ministério da Saúde": "Ministério da Saúde",
    "Fundação Nacional de Saúde": "Funasa",
    "Ministério das Cidades": "Ministério das Cidades",
    "Ministério da Educação": "Ministério da Educação",
    "Ministério da Integração e Desenvolvimento Regional": "Ministério da Integração",
    "Departamento Nacional de Infraestrutura de Transportes": "DNIT",
    "Ministério do Desenvolvimento e Assitência Social e Combate à Fome": "Ministério do Desenvolvimento Social",
    "Ministério da Agricultura e Pecuária": "Ministério da Agricultura",
    "Ministério da Justiça e Segurança Pública": "Ministério da Justiça",
}
# Quem acompanha a obra (a base de onde o TCU tirou a linha).
BASES = {
    "CAIXA": "Caixa",
    "SIMEC": "FNDE (SIMEC)",
    "SIMEC-Outros": "MEC (SIMEC)",
    "SESU": "MEC, universidades (SIMEC)",
    "SETEC": "MEC, institutos federais (SIMEC)",
    "SISMOB": "Ministério da Saúde (SISMOB)",
    "FUNASA": "Funasa",
    "DNIT": "DNIT (SIAC)",
    "CODEVASF": "Codevasf (SIGEC)",
}
# Causa genérica demais para mostrar.
CAUSA_VAZIA = {None, "", "Outros", "Outro", "Não informado"}
CAUSA_CURTA = {
    "Declaração de que a execução do objeto está paralisada por órgão ou entidade da Administração Pública "
    "Federal, independentemente do prazo.": "Declarada paralisada por órgão federal",
}
# Nomes de cidade que o TCU escreve diferente do SICONFI.
APELIDOS = {
    ("RN", "JANUARIO CICCO"): "BOA SAUDE",
    ("BA", "SANTA TEREZINHA"): "SANTA TERESINHA",
    ("MG", "BARAO DO MONTE ALTO"): "BARAO DE MONTE ALTO",
    ("SE", "AMPARO DO SAO FRANCISCO"): "AMPARO DE SAO FRANCISCO",
}


def _ler(arq: Path) -> list[dict]:
    """Uma data-base exportada do painel: lista de linhas como dicionários (sem a linha de filtros)."""
    import warnings

    import openpyxl

    warnings.filterwarnings("ignore", "Workbook contains no default style")

    ws = openpyxl.load_workbook(arq, read_only=True).worksheets[0]
    linhas = ws.iter_rows(values_only=True)
    cab = [str(c).strip() if c else "" for c in next(linhas)]
    obrigatorias = {"Data base", "Base de dados", "Empreendimento", "Situação", "Local", "Valor Investimento",
                    "Valor Desbloqueado", "Repassador", "ID"}
    faltam = obrigatorias - set(cab)
    if faltam:
        raise SystemExit(f"{arq.name}: o painel mudou, faltam as colunas {sorted(faltam)}")
    saida = []
    for r in linhas:
        if len(r) != len(cab) or not r[cab.index("ID")]:
            continue
        saida.append(dict(zip(cab, r)))
    return saida


def _data_base(arq: Path) -> str:
    m = re.fullmatch(r"obras-(\d{4}-\d{2})\.xlsx", arq.name)
    if not m:
        raise SystemExit(f"nome inesperado: {arq.name} (use obras-AAAA-MM.xlsx)")
    return m.group(1)


def _nome(s: str | None) -> str:
    """Tira o número da obra no SIMEC do começo, junta espaços e põe a primeira letra em maiúscula."""
    s = " ".join((s or "").split())
    s = re.sub(r"^(\((EP|[A-Z]{1,3})\)\s*)?\(\d+\)\s*", "", s)
    s = s.replace(" ? ", " – ")
    return s[:1].upper() + s[1:] if s else s


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(v) -> int | None:
    """Fração (0,53) → 53. Vazio continua vazio."""
    if v is None or v == "":
        return None
    try:
        return round(float(v) * 100)
    except (TypeError, ValueError):
        return None


def _cidades() -> dict[tuple[str, str], int]:
    return {(e["uf"], chave(e["ente"])): int(e["cod_ibge"]) for e in baixar_entes() if e["esfera"] == "M"}


def _local(local: str | None, cidades: dict[tuple[str, str], int]) -> tuple[str | None, int | None]:
    """"Carnaubal/CE" → ("CE", 2303402). "RS" → ("RS", None). Cidade que não casa → (UF, None)."""
    local = (local or "").strip()
    if "/" not in local:
        return (local if re.fullmatch(r"[A-Z]{2}", local) else None), None
    nome, uf = local.rsplit("/", 1)
    uf = uf.strip()
    k = chave(nome)
    k = APELIDOS.get((uf, k), k)
    return uf, cidades.get((uf, k))


def montar(pasta: Path) -> dict:
    arquivos = sorted(pasta.glob("obras-*.xlsx"))
    if not arquivos:
        raise SystemExit(f"nenhuma tabela em {pasta} (ver o começo deste arquivo)")
    datas = [_data_base(a) for a in arquivos]
    print(f"datas-base: {', '.join(datas)}", flush=True)
    tabelas = {d: _ler(a) for d, a in zip(datas, arquivos)}
    ultima = datas[-1]
    atual = tabelas[ultima]
    if not any(r["Situação"] != PARALISADA for r in atual):
        raise SystemExit(f"obras-{ultima}.xlsx só tem paralisadas: exporte com a Situação em 'Todos'")

    situacao = {d: {r["ID"]: r["Situação"] for r in t} for d, t in tabelas.items()}

    def desde(id_: str) -> str:
        """A primeira data-base da sequência de datas seguidas em que a obra aparece parada, até a última."""
        primeira = ultima
        for d in reversed(datas):
            if situacao[d].get(id_) != PARALISADA:
                break
            primeira = d
        return primeira

    cidades = _cidades()
    sem_casar: Counter = Counter()
    obras = []
    ativas_mun: Counter = Counter()
    ativas_uf: Counter = Counter()
    for r in atual:
        uf, ibge = _local(r["Local"], cidades)
        if r["Situação"] in ("Em execução", PARALISADA):
            if ibge:
                ativas_mun[ibge] += 1
            if uf:
                ativas_uf[uf] += 1
        if r["Situação"] != PARALISADA:
            continue
        if uf and not ibge and "/" in (r["Local"] or ""):
            sem_casar[r["Local"]] += 1
        causa = r.get("Causa da paralisação")
        causa = None if causa in CAUSA_VAZIA else CAUSA_CURTA.get(causa, causa)
        obras.append({
            "id": r["ID"],
            "nome": _nome(r["Empreendimento"]),
            "base": r["Base de dados"],
            "paga": QUEM_PAGA.get(r["Repassador"], r["Repassador"] or "Não informado"),
            "instrumento": str(r.get("Núm. Instrumento") or "").strip() or None,
            "uf": uf,
            "ibge": ibge,
            "local": r["Local"],
            "fisica": _pct(r.get("Exec. física")),
            "previsto": round(_num(r["Valor Investimento"]), 2),
            "liberado": round(_num(r["Valor Desbloqueado"]), 2),
            "setor": r.get("Setor") or "Não identificado",
            "causa": causa,
            "origem": (r.get("Situação origem") or "").strip().capitalize() or None,
            "pac": r.get("Obra PAC") not in (None, "Não"),
            "pacto": r.get("Pacto") == "Manifestou interesse em repactuar",
            "desde": desde(r["ID"]),
        })
    if sem_casar:
        print(f"aviso: {sum(sem_casar.values())} obras com cidade que não casou com o SICONFI; ficam só no estado:",
              ", ".join(f"{k} ({n})" for k, n in sem_casar.most_common(15)), flush=True)
    obras.sort(key=lambda o: -o["previsto"])

    def tupla(o: dict, com_local: bool) -> list:
        # [nome, base, quem paga, instrumento, % feito, previsto, liberado, causa, situação no órgão, desde,
        #  setor, pacto, (local, ibge)]
        t = [o["nome"], o["base"], o["paga"], o["instrumento"], o["fisica"], o["previsto"], o["liberado"],
             o["causa"], o["origem"], o["desde"], o["setor"], 1 if o["pacto"] else 0]
        if com_local:
            t += [o["local"], o["ibge"]]
        return t

    def soma(lista: list[dict]) -> list:
        return [len(lista), round(sum(o["previsto"] for o in lista), 2), round(sum(o["liberado"] for o in lista), 2)]

    def contagem(lista: list[dict], campo: str) -> list:
        g: dict[str, list[dict]] = defaultdict(list)
        for o in lista:
            g[o[campo]].append(o)
        return sorted(([k, *soma(v)] for k, v in g.items()), key=lambda x: (-x[1], str(x[0])))

    por_mun: dict[int, list[dict]] = defaultdict(list)
    por_uf: dict[str, list[dict]] = defaultdict(list)
    for o in obras:
        if o["ibge"]:
            por_mun[o["ibge"]].append(o)
        if o["uf"]:
            por_uf[o["uf"]].append(o)

    mun = {str(ibge): [*soma(lista), ativas_mun[ibge], [tupla(o, False) for o in lista]]
           for ibge, lista in sorted(por_mun.items())}
    uf = {}
    for sigla, lista in sorted(por_uf.items()):
        sem_cidade = [o for o in lista if not o["ibge"]]
        cid = contagem([o for o in lista if o["ibge"]], "ibge")[:CIDADES_UF]
        uf[sigla] = {
            "total": soma(lista),
            "ativas": ativas_uf[sigla],
            "cidades_com_obra": len({o["ibge"] for o in lista if o["ibge"]}),
            "cidades": [[str(c[0]), c[1], c[2], c[3]] for c in cid],
            "quem_paga": contagem(lista, "paga"),
            "maiores": [tupla(o, True) for o in lista[:MAIORES_UF]],
            "sem_cidade": [tupla(o, False) for o in sem_cidade],
        }

    # O que aconteceu com as obras que estavam paradas na data-base anterior.
    destino = None
    if len(datas) > 1:
        antes = datas[-2]
        paradas_antes = [k for k, v in situacao[antes].items() if v == PARALISADA]
        c = Counter(situacao[ultima].get(k, "Saiu da lista") for k in paradas_antes)
        destino = {"de": antes, "total": len(paradas_antes), "situacoes": c.most_common()}

    historico = []
    for d in datas:
        t = tabelas[d]
        par = [r for r in t if r["Situação"] == PARALISADA]
        historico.append({
            "data": d,
            "paralisadas": len(par),
            "em_execucao": sum(1 for r in t if r["Situação"] == "Em execução"),
            "previsto": round(sum(_num(r["Valor Investimento"]) for r in par), 2),
            "liberado": round(sum(_num(r["Valor Desbloqueado"]) for r in par), 2),
        })

    brasil = {
        "total": soma(obras),
        "ativas": sum(1 for r in atual if r["Situação"] in ("Em execução", PARALISADA)),
        "cidades_com_obra": len(por_mun),
        "sem_cidade": soma([o for o in obras if not o["ibge"]]),
        "quem_paga": contagem(obras, "paga"),
        "base": contagem(obras, "base"),
        "setor": contagem(obras, "setor"),
        "causa": contagem([o for o in obras if o["causa"]], "causa")[:12],
        "sem_causa": sum(1 for o in obras if not o["causa"]),
        "origem": contagem(obras, "origem"),
        "desde": sorted(([d, *soma([o for o in obras if o["desde"] == d])] for d in datas if any(o["desde"] == d for o in obras))),
        "pacto": soma([o for o in obras if o["pacto"]]),
        "maiores": [tupla(o, True) for o in obras[:MAIORES_BRASIL]],
        "uf": {s: [*v["total"], v["ativas"]] for s, v in uf.items()},
        "historico": historico,
        "destino": destino,
    }
    return {
        "data_base": ultima,
        "datas": datas,
        "fonte": FONTE,
        "url": URL,
        "bases": BASES,
        "brasil": brasil,
        "uf": uf,
        "mun": mun,
    }


def _gravar(doc: dict, arq: Path) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(arq)


def main() -> None:
    p = argparse.ArgumentParser(prog="obras-paradas", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-baixar", action="store_true",
                   help="não lê as tabelas: copia a cópia de referência para o site")
    p.add_argument("--pasta", type=Path, default=PASTA, help="onde estão as tabelas exportadas do painel")
    args = p.parse_args()

    if args.sem_baixar:
        if not REFERENCIA.exists():
            sys.exit(f"sem cópia de referência em {REFERENCIA}")
        SAIDA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCIA, SAIDA)
        print(f"copiado {REFERENCIA.relative_to(RAIZ)} → {SAIDA.relative_to(RAIZ)}")
        return

    doc = montar(args.pasta)
    b = doc["brasil"]
    print(f"{b['total'][0]} obras paralisadas em {doc['data_base']}: R$ {b['total'][1] / 1e9:.1f} bi previstos, "
          f"R$ {b['total'][2] / 1e9:.1f} bi liberados; {b['cidades_com_obra']} cidades; "
          f"{b['sem_cidade'][0]} só com o estado", flush=True)
    _gravar(doc, SAIDA)
    _gravar(doc, REFERENCIA)
    print(f"gravado {SAIDA.relative_to(RAIZ)} ({SAIDA.stat().st_size / 1e6:.1f} MB) e a cópia de referência")


if __name__ == "__main__":
    main()
