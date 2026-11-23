"""As páginas de governadores, deputados estaduais e distritais eleitos em 2022 (parte de politicos.py).

A base é o TSE de 2022 (a chave é tse-<SQ_CANDIDATO>, nunca o CPF). Sobre ela:
- o salário pela lei: o do deputado estadual é 75% do federal (CF, art. 27, §2º); o do governador, a lei de cada
  estado (tabela abaixo, levantada em 23/11/2026; docs/levantamento-parlamentar.md, seção 9.3);
- a verba de cada deputado nas Assembleias que a publicam nota a nota (assembleias.py) e, onde há, os assessores;
- para o governador, a saída do cargo em 2026 (11 dos 27 deixaram o cargo, quase todos para concorrer).

Para os estados sem verba aberta, a página diz o que a Assembleia publica (ASSEMBLEIAS, abaixo).
"""

from __future__ import annotations

import datetime as dt
import re
import statistics
from collections import Counter, defaultdict

from . import assembleias as ales

# ---------------------------------------------------------------- o que cada Assembleia publica

# tipo: "nota" (nota a nota, com CNPJ: entra na página), "total" (só o total por tipo de gasto), "fixo" (valor fixo,
# sem nota), "nada" (não publica) ou "travado" (publica, mas não dá para ler sem captcha, robô bloqueado ou senha).
# Entre as de "nota", só as de assembleias.UFS já são lidas; as outras ainda dizem "ainda não lemos".
ASSEMBLEIAS = {
    "AC": ("Assembleia Legislativa do Acre", "nada", None),
    "AL": ("Assembleia Legislativa de Alagoas", "total", "publica só o total de cada tipo de gasto, em PDF escaneado, sem dizer quem recebeu"),
    "AM": ("Assembleia Legislativa do Amazonas", "nota", None),
    "AP": ("Assembleia Legislativa do Amapá", "nota", None),
    "BA": ("Assembleia Legislativa da Bahia", "nota", None),
    "CE": ("Assembleia Legislativa do Ceará", "nota", None),
    "DF": ("Câmara Legislativa do Distrito Federal", "nota", None),
    "ES": ("Assembleia Legislativa do Espírito Santo", "total", "publica só o total de cada tipo de gasto, sem dizer quem recebeu"),
    "GO": ("Assembleia Legislativa de Goiás", "nota", None),
    "MA": ("Assembleia Legislativa do Maranhão", "total", "publica só o total de cada tipo de gasto, sem dizer quem recebeu"),
    "MG": ("Assembleia Legislativa de Minas Gerais", "nota", None),
    "MS": ("Assembleia Legislativa de Mato Grosso do Sul", "nota", None),
    "MT": ("Assembleia Legislativa de Mato Grosso", "nada", None),
    "PA": ("Assembleia Legislativa do Pará", "fixo", "paga a verba como um valor fixo de R$ 35 mil por mês, sem nota fiscal: não dá para saber em que foi gasta"),
    "PB": ("Assembleia Legislativa da Paraíba", "total", "publica as notas, mas com o CNPJ escondido"),
    "PE": ("Assembleia Legislativa de Pernambuco", "nota", None),
    "PI": ("Assembleia Legislativa do Piauí", "total", "publica só o total de cada tipo de gasto, sem dizer quem recebeu"),
    "PR": ("Assembleia Legislativa do Paraná", "travado", "só mostra esses gastos numa consulta com captcha"),
    "RJ": ("Assembleia Legislativa do Rio de Janeiro", "travado", "publica as notas num sistema que não autoriza a leitura automática"),
    "RN": ("Assembleia Legislativa do Rio Grande do Norte", "travado", "publica as notas num sistema que pede senha"),
    "RO": ("Assembleia Legislativa de Rondônia", "nota", None),
    "RR": ("Assembleia Legislativa de Roraima", "total", "publica só o total de cada tipo de gasto, e só desde setembro de 2025"),
    "RS": ("Assembleia Legislativa do Rio Grande do Sul", "total", "publica só o total de cada tipo de gasto, sem dizer quem recebeu"),
    "SC": ("Assembleia Legislativa de Santa Catarina", "total", "publica os gastos sem o CNPJ de quem recebeu"),
    "SE": ("Assembleia Legislativa de Sergipe", "total", "publica só o total de cada tipo de gasto, sem dizer quem recebeu"),
    "SP": ("Assembleia Legislativa de São Paulo", "nota", None),
    "TO": ("Assembleia Legislativa do Tocantins", "nota", None),
}

# O salário do deputado estadual: 75% do federal em toda parte, menos onde a folha ou a lei mostram outra coisa e
# ainda falta conferir. Nesses estados a página não mostra o valor.
SALARIO_ESTADUAL_A_CONFERIR = {
    "MA": "o salário cheio só vale desde fevereiro de 2026, e não achamos os valores de antes",
    "MT": "a folha da Assembleia mostra R$ 41.729,57 por mês para deputado, acima do limite da Constituição; falta entender o que entra nesse valor",
}
NOTA_SALARIO_ESTADUAL = {
    "CE": "Na folha da Assembleia, quase todos recebem cerca de 15% a mais, um auxílio-saúde criado em 2025.",
    "RS": "A folha da Assembleia mostra R$ 34.772,11, um pouco abaixo; a diferença não foi explicada.",
}

# ---------------------------------------------------------------- o salário do governador

# (desde, valor) por estado, do levantamento de 23/11/2026; e a lei vigente. Onde a série tem um buraco, o ano
# sem todos os meses não ganha total.
SUBSIDIO_GOVERNADOR: dict[str, list[tuple[str, float]]] = {
    "AC": [("2023-01", 35462.22), ("2023-04", 37589.95), ("2024-02", 39717.69), ("2025-02", 41845.49)],
    "AL": [("2023-01", 27758.42), ("2023-09", 28591.17), ("2023-11", 29365.63), ("2024-06", 30833.91), ("2025-06", 32323.19), ("2026-05", 34262.58)],
    "AM": [("2023-01", 34070.00)],
    "AP": [("2023-01", 33000.00)],
    "BA": [("2023-01", 35462.22), ("2024-05", 36171.46), ("2024-09", 36894.89)],
    "CE": [("2023-01", 20083.63), ("2023-08", 20629.59), ("2024-07", 21788.97), ("2026-01", 22717.18), ("2026-05", 22878.41)],
    "DF": [("2023-01", 23449.55), ("2023-07", 29311.94)],
    "ES": [("2023-01", 29496.99), ("2023-04", 30971.84), ("2024-02", 33006.39), ("2025-02", 34774.64), ("2026-07", 36165.63)],
    "GO": [("2023-01", 27597.83), ("2023-05", 28403.69), ("2023-10", 29234.38), ("2024-05", 30585.01), ("2025-05", 32062.27), ("2026-05", 33428.12)],
    "MA": [("2023-01", 15915.40), ("2024-06", 33006.39)],
    "MG": [("2023-01", 10500.00), ("2023-04", 37589.96), ("2024-02", 39717.69), ("2025-02", 41845.49)],
    "MS": [("2023-01", 35462.27)],
    "PA": [("2023-01", 35363.55)],
    "PB": [("2023-01", 31173.06), ("2024-01", 32434.82), ("2025-01", 33696.58), ("2026-01", 35032.58)],
    "PE": [("2023-01", 22000.00)],
    "PI": [("2023-01", 29469.99), ("2023-04", 31238.19), ("2024-02", 33006.39), ("2025-02", 34774.64)],
    "PR": [("2023-01", 33763.00)],
    "RJ": [("2023-01", 21868.14)],
    "RN": [("2023-01", 21914.76)],
    "RO": [("2023-01", 35462.22)],
    "RR": [("2023-01", 34299.00)],
    "RS": [("2023-01", 35462.22)],
    "SC": [("2023-01", 25322.25)],
    "SE": [("2023-01", 39293.32), ("2023-04", 41650.92), ("2024-02", 44008.52), ("2025-02", 46366.19)],
    "SP": [("2023-01", 34572.89), ("2025-07", 36301.53)],
    "TO": [("2024-05", 31216.71), ("2025-05", 32518.44)],
}
LEI_GOVERNADOR = {
    "AM": "Lei 4.740/2018", "AP": "Lei 2.799/2022", "BA": "Lei 14.728/2024", "CE": "Lei 19.667/2026", "DF": "Lei distrital 7.255/2023",
    "ES": "Lei 12.795/2026", "MA": "Lei 12.282/2024", "MG": "Lei 24.314/2023", "PA": "Decreto Legislativo 1/2023",
    "PB": "Lei 12.550/2022", "PE": "Lei 18.137/2023", "PI": "Lei 7.955/2023", "PR": "Lei 21.348/2022", "RJ": "Lei 6.939/2014",
    "RO": "Lei 5.529/2023", "RR": "Lei 1.789/2023", "SC": "Lei 18.590/2023", "SE": "Lei 9.136/2022", "SP": "Lei 18.152/2025",
    "TO": "Lei 4.667/2025",
}
# Sem lei própria achada: o valor segue o reajuste geral dos servidores ou o do desembargador.
SEM_LEI_GOVERNADOR = {
    "AC": "acompanha o salário de desembargador do Tribunal de Justiça; não achamos a lei",
    "AL": "sobe com o reajuste geral dos servidores do estado; não há lei própria",
    "GO": "sobe com o reajuste geral dos servidores do estado; não há lei própria",
    "MS": "o valor vem da imprensa; não achamos a lei",
    "RN": "não achamos a lei; o valor é o da tabela oficial de salários do estado",
    "RS": "não confirmamos o número da lei",
}
# Mato Grosso: só valores de imprensa e calculados; o salário fica fora.
GOVERNADOR_A_CONFERIR = {"MT": "não achamos a lei que fixa o salário do governador de Mato Grosso"}
NOTA_GOVERNADOR = {
    "PE": "A governadora recebe pelo cargo de procuradora do Estado, que paga mais que o de governadora; a escolha é contestada no Supremo.",
    "TO": "Ficou afastado do cargo pelo Superior Tribunal de Justiça de setembro a dezembro de 2025 e voltou por decisão do Supremo.",
}

# Quem deixou o cargo em 2026: (dia em que saiu, ou None quando só sabemos o ano; frase de quem assumiu).
SAIDA_GOVERNADOR = {
    "AC": ("2026-04-02", "Quem assumiu foi a vice, Mailza Assis."),
    "AM": (None, "O vice também saiu, e a Assembleia elegeu Roberto Cidade, em 4 de maio, para terminar o mandato."),
    "DF": ("2026-03-30", "Quem assumiu foi a vice, Celina Leão."),
    "ES": ("2026-04-02", "Quem assumiu foi o vice, Ricardo Ferraço."),
    "GO": (None, "Quem assumiu foi o vice, Daniel Vilela."),
    "MG": ("2026-03-22", "Quem assumiu foi o vice, Mateus Simões."),
    "MT": (None, "Quem assumiu foi o vice, Otaviano Pivetta."),
    "PA": ("2026-04-02", "Quem assumiu foi a vice, Hana Ghassan."),
    "PB": ("2026-04-02", "Quem assumiu foi o vice, Lucas Ribeiro."),
    "RJ": ("2026-03-23", "O vice já tinha saído em 2025; quem assumiu foi o presidente do Tribunal de Justiça, Ricardo Couto."),
    "RR": ("2026-03-27", "Quem assumiu foi o vice, Edilson Damião, que teve o mandato cassado pelo TSE em 30 de abril."),
}

# O nome público dos governadores que usaram na urna só um nome (ou o nome inteiro).
NOME_PUBLICO = {"SP": "Tarcísio de Freitas", "MG": "Romeu Zema", "PB": "João Azevêdo", "SE": "Fábio Mitidieri",
                "BA": "Jerônimo Rodrigues", "PA": "Helder Barbalho", "AP": "Clécio Luís", "PR": "Ratinho Junior",
                "RN": "Fátima Bezerra"}

MES_INICIO = {"governo": 1, "assembleia": 2}   # o governador toma posse em janeiro; o deputado, em fevereiro


def limpa_urna(s: str) -> str:
    """"Pr.alcides Fernandes" → "Pr. Alcides Fernandes"."""
    return re.sub(r"\.(\w)", lambda m: ". " + m.group(1).upper(), s or "")


def valor_em(tabela: list[tuple[str, float]], mes: str) -> float | None:
    v = [x for desde, x in tabela if desde <= mes]
    return v[-1] if v else None


def mes_hoje() -> str:
    return dt.date.today().strftime("%Y-%m")


def ultimo_mes_fechado() -> tuple[int, int]:
    h = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    return h.year, h.month


def salario_governador(uf: str, ano: int) -> dict | None:
    """O salário do ano (12 meses e 13º, ou até a saída), pela tabela da lei. None se falta algum mês."""
    tabela = SUBSIDIO_GOVERNADOR.get(uf)
    if not tabela or uf in GOVERNADOR_A_CONFERIR:
        return None
    ua, um = ultimo_mes_fechado()
    ate = 12 if ano < ua else um if ano == ua else 0
    saida = SAIDA_GOVERNADOR.get(uf)
    fracao_ultimo = 1.0
    if saida and ano >= 2026:
        if not saida[0]:
            return None              # não sabemos o mês em que saiu
        d = dt.date.fromisoformat(saida[0])
        if ano > d.year:
            return None
        ate, fracao_ultimo = d.month, (d.day - 1) / 30
    if ate <= 0:
        return None
    valores = [valor_em(tabela, f"{ano}-{m:02d}") for m in range(1, ate + 1)]
    if any(v is None for v in valores):
        return None
    base = sum(valores[:-1]) + valores[-1] * fracao_ultimo
    meses = len(valores) - 1 + fracao_ultimo
    total = base + valores[-1] * meses / 12          # 13º proporcional
    return {"total": round(total), "meses": round(meses, 2), "mensal": valores[-1],
            "mudou": [[desde, v] for desde, v in tabela if desde[:4] == str(ano)]}


def salario_estadual(subsidio_federal, ano: int, meses: int) -> int:
    """Como o federal (politicos.salario_do_ano): os meses no cargo, o subsídio de cada um (75% do federal), mais 13º
    e 1/3 de férias proporcionais."""
    if not meses:
        return 0
    ua, um = ultimo_mes_fechado()
    ate = 12 if ano < ua else um
    ini = MES_INICIO["assembleia"] if ano == 2023 else 1
    valores = [subsidio_federal(f"{ano}-{m:02d}") * 0.75 for m in range(ini, ate + 1)][-meses:]
    return round(sum(valores) + (valores[-1] * (1 + 1 / 3)) * len(valores) / 12)


# ---------------------------------------------------------------- ligar a Assembleia ao TSE

TITULOS = {"doutor": "dr", "doutora": "dra", "delegado": "del", "delegada": "del", "capitao": "cap", "coronel": "cel",
           "professor": "prof", "professora": "profa", "sargento": "sgt", "tenente": "ten", "pastor": "pr", "pastora": "pra",
           "apostolo": "ap", "cabo": "cb", "soldado": "sd", "major": "maj", "comandante": "cmt", "missionario": "miss"}
LIGA = {"de", "da", "do", "das", "dos", "e"}
# As Casas que não dão id ao deputado: a chave é o nome, e grafias diferentes do mesmo nome podem aparecer.
SEM_ID = {"MS", "CE"}


def tokens(s: str) -> list[str]:
    s = ales.sem_acento(s or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)                       # "Professor Cleiton (cleitinho)"
    s = re.sub(r"\s-\s.*$", "", s)                         # "ALMIR BIE - COMBUSTIVEIS..."
    s = re.sub(r"^dep(utad[oa])?\b\.?\s*", "", s.strip())
    ts = [TITULOS.get(t, t) for t in re.findall(r"[a-z0-9]+", s)]
    return [t for t in ts if t not in LIGA]


def chave_nome(s: str) -> str:
    return "-".join(tokens(s))


def ligar_assembleia(eleitos: list[dict], deputados_ales: dict[str, set]) -> dict[str, list[str]]:
    """chave do eleito no TSE → as chaves "<uf>-<dep>" dele na Assembleia, no mesmo estado. Primeiro pelo nome de
    urna ou pelo nome completo, iguais; depois, para quem sobrou, quando as palavras de um nome (2 ou mais) estão todas
    no outro ("Conte Lopes" e "Capitão Conte Lopes"; "Luiz Fernando Teixeira" e o nome completo). Só liga quando o
    par é único dos dois lados. Nas Casas sem id (CE, MS), as grafias do mesmo nome se juntam."""
    saida: dict[str, list[str]] = {}
    for uf, deps in deputados_ales.items():
        por_nome: dict[str, set[str]] = defaultdict(set)
        nome_da_chave: dict[str, str] = {}
        for dep_chave, nome in deps:
            n = chave_nome(nome)
            if n:
                por_nome[n].add(dep_chave)
                nome_da_chave[dep_chave] = n
        daqui = [e for e in eleitos if e["uf"] == uf]
        usados: set[str] = set()
        # 1. nomes iguais
        for e in daqui:
            for n in (e["urna"], e.get("completo")):
                achados = por_nome.get(chave_nome(n or ""), set())
                if len(achados) == 1 or (achados and uf in SEM_ID):
                    saida[e["chave"]] = sorted(achados)
                    usados |= achados
                    break
                if len(achados) > 1:
                    print(f"  {uf}: '{n}' aparece {len(achados)} vezes na Assembleia; não liga", flush=True)
        # 2. um nome contido no outro, para quem sobrou
        livres = {n: ks - usados for n, ks in por_nome.items() if ks - usados}
        propostas: dict[str, set[str]] = defaultdict(set)     # eleito → nomes da Assembleia
        for e in daqui:
            if e["chave"] in saida:
                continue
            for n in livres:
                tn = set(n.split("-"))
                for nome_e in (e["urna"], e.get("completo")):
                    te = set(tokens(nome_e or ""))
                    menor = tn if len(tn) <= len(te) else te
                    if len(menor) >= 2 and (tn <= te or te <= tn):
                        propostas[e["chave"]].add(n)
        donos: dict[str, list[str]] = defaultdict(list)
        for ch, ns in propostas.items():
            for n in ns:
                donos[n].append(ch)
        for ch, ns in propostas.items():
            ns_unicos = [n for n in ns if len(donos[n]) == 1]
            if len(ns_unicos) == 1 or (ns_unicos and uf in SEM_ID):
                saida[ch] = sorted(k for n in ns_unicos for k in livres[n])
        # 3. nas Casas sem id, as grafias quase iguais de um nome já ligado (erro de digitação: "AGUYIAR")
        if uf in SEM_ID:
            import difflib
            ligados = {k for ks in saida.values() for k in ks}
            for dep_chave, n in nome_da_chave.items():
                if dep_chave in ligados:
                    continue
                melhores = []
                for ch, ks in saida.items():
                    if not ks or not ks[0].startswith(uf + "-"):
                        continue
                    r = max(difflib.SequenceMatcher(None, n, nome_da_chave[k]).ratio() for k in ks)
                    melhores.append((r, ch))
                melhores.sort(reverse=True)
                if melhores and melhores[0][0] >= 0.9 and (len(melhores) == 1 or melhores[1][0] < 0.85):
                    saida[melhores[0][1]].append(dep_chave)
    return saida


# ---------------------------------------------------------------- montagem

def montar(tse_dados: dict, carregado: tuple[list, dict], subsidio_federal, resumo_linhas, nat: dict[str, str]) -> tuple[list[dict], dict]:
    """As páginas novas e o que vai no topo do JSON (o que cada Assembleia publica; o salário dos governadores).
    carregado: o que assembleias.carregar() devolve (as notas e os deputados de cada Casa)."""
    linhas, info = carregado
    eleitos = [dict(t, chave=k) for k, t in tse_dados.items() if k.startswith("tse-")]
    nomes_ales: dict[str, set] = defaultdict(set)
    for uf, dep, nome, *_ in linhas:
        nomes_ales[uf].add((f"{uf}-{dep}", nome))
    for k, d in info.items():
        if d.get("nome"):
            nomes_ales[k.split("-", 1)[0]].add((k, d["nome"]))
    ligacao = ligar_assembleia([e for e in eleitos if e["cargo"] != "Governador"], nomes_ales)
    ligados = {k for ks in ligacao.values() for k in ks}
    for uf in ales.UFS:
        eleitos_uf = [e for e in eleitos if e["uf"] == uf and e["cargo"] != "Governador"]
        fora = sorted(e["urna"] for e in eleitos_uf if e["chave"] not in ligacao)
        com_verba = {f"{l[0]}-{l[1]}" for l in linhas if l[0] == uf}
        print(f"{uf}: {len(eleitos_uf) - len(fora)} de {len(eleitos_uf)} eleitos ligados à Assembleia; sem ligação: "
              f"{', '.join(fora) or 'nenhum'}; {len(com_verba - ligados)} nomes com verba sem eleito (suplentes)", flush=True)

    # As linhas de cada deputado, por ano.
    por_dep: dict[tuple, list] = defaultdict(list)
    for uf, dep, nome, ano, mes, cat, forn, doc, v in linhas:
        por_dep[(f"{uf}-{dep}", ano)].append((ales.categoria(cat), forn, doc, v, mes))
    # A comparação: gasto médio por mês de todos os deputados da Casa com 6 meses ou mais (suplentes incluídos).
    # Cada eleito junta as linhas das chaves dele; quem sobra (suplentes) conta sozinho.
    colegas: dict[tuple, list] = defaultdict(list)
    resumos: dict[tuple, dict] = {}
    dono = {k: ch for ch, ks in ligacao.items() for k in ks}
    grupos: dict[tuple, list] = defaultdict(list)
    for (dk, ano), ls in por_dep.items():
        grupos[(dono.get(dk, dk), ano)] += ls
    for (quem, ano), ls in grupos.items():
        r = resumo_linhas(ls, nat)
        if r:
            resumos[(quem, ano)] = r
            if r["meses"] >= 6:
                uf_ = quem.split("-", 1)[0] if not quem.startswith("tse-") else tse_dados[quem]["uf"]
                colegas[(uf_, ano)].append(r["porMes"])

    politicos = []
    for e in sorted(eleitos, key=lambda e: e["chave"]):
        uf, cargo_tse = e["uf"], e["cargo"]
        governo = cargo_tse == "Governador"
        feminino = e.get("genero") == "FEMININO"
        casa = "governo" if governo else "assembleia"
        if governo:
            cargo = "Governadora" if feminino else "Governador"
        elif cargo_tse == "Deputado Distrital":
            cargo = "Deputada distrital" if feminino else "Deputado distrital"
        else:
            cargo = "Deputada estadual" if feminino else "Deputado estadual"
        dks = ligacao.get(e["chave"], [])
        dk = next((k for k in dks if k in info), dks[0] if dks else None)
        d = info.get(dk, {}) if dk else {}
        nome = NOME_PUBLICO.get(uf) if governo and uf in NOME_PUBLICO else (d.get("nome") if d.get("nome") and uf in ("SP", "MG", "GO", "PE") else limpa_urna(e["urna"]))
        por_ano: dict[str, dict] = {}
        for ano in range(2023, dt.date.today().year + 1):
            item: dict = {}
            if governo:
                s = salario_governador(uf, ano)
                if s:
                    item["salario"] = s["total"]
                    item["salarioMensal"] = s["mensal"]
                    item["meses"] = s["meses"]
            else:
                r = resumos.get((e["chave"], ano)) if dks else None
                if r:
                    r = dict(r)
                    lista = sorted(colegas.get((uf, ano), []))
                    if r["meses"] >= 6 and len(lista) >= 3:
                        r["comparacao"] = {"mediana": round(statistics.median(lista)), "n": len(lista), "colegas": lista}
                    item["verba"] = r
                if uf not in SALARIO_ESTADUAL_A_CONFERIR:
                    ua, um = ultimo_mes_fechado()
                    if ano <= ua:
                        # Os meses no cargo: os meses com verba, onde a Casa publica; senão, o ano inteiro desde a posse.
                        cheio = (12 if ano < ua else um) - (MES_INICIO["assembleia"] - 1 if ano == 2023 else 0)
                        meses = r["meses"] if r else cheio
                        item["salario"] = salario_estadual(subsidio_federal, ano, meses)
                        item["salarioMensal"] = round(subsidio_federal(f"{ano}-12" if ano < ua else mes_hoje()) * 0.75, 2)
                        item["mesesEstimados"] = not r
            if item:
                por_ano[str(ano)] = item
        p = {
            "chave": e["chave"], "casa": casa, "id": e["sq"], "nome": nome, "uf": uf,
            "partido": d.get("partido") or None, "partidoEleicao": e.get("partido"),
            "cargo": cargo, "feminino": feminino, "foto": d.get("foto") or None, "autor": None, "tse": e,
            "assessores": d.get("assessores"), "anos": por_ano,
        }
        if dk:
            p["assembleia"] = {"id": dk.split("-", 1)[1], "nome": d.get("nome")}
        if governo:
            saida = SAIDA_GOVERNADOR.get(uf)
            if saida:
                p["saida"] = {"data": saida[0], "frase": saida[1]}
            if uf in NOTA_GOVERNADOR:
                p["nota"] = NOTA_GOVERNADOR[uf]
        elif uf in NOTA_SALARIO_ESTADUAL:
            p["nota"] = NOTA_SALARIO_ESTADUAL[uf]
        politicos.append(p)
    for p in politicos:      # o "completo" só serve para ligar à Câmara e ao Senado; a página não usa
        p["tse"] = {k: v for k, v in p["tse"].items() if k not in ("chave",)}

    lidas = set(ales.UFS)
    extras = {
        "assembleias": {uf: {"nome": nome, "tipo": tipo if (tipo != "nota" or uf in lidas) else "naoLida",
                             "frase": frase, "verba": ales.NOME_VERBA.get(uf, "verba de gabinete"),
                             "salarioAConferir": SALARIO_ESTADUAL_A_CONFERIR.get(uf)}
                        for uf, (nome, tipo, frase) in ASSEMBLEIAS.items()},
        "governadores": {uf: {"subsidio": [[a, v] for a, v in SUBSIDIO_GOVERNADOR.get(uf, [])], "lei": LEI_GOVERNADOR.get(uf),
                              "semLei": SEM_LEI_GOVERNADOR.get(uf), "aConferir": GOVERNADOR_A_CONFERIR.get(uf)}
                         for uf in ASSEMBLEIAS},
    }
    n = Counter(p["cargo"].split()[0] for p in politicos)
    print(f"estaduais: {len(politicos)} páginas ({dict(n)}); {sum(1 for p in politicos if any('verba' in x for x in p['anos'].values()))} com verba", flush=True)
    return politicos, extras
