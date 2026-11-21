import { createMemo, createResource, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import Treemap from "./Treemap";
import Tabela from "./Tabela";
import BarrasAno, { type Ponto } from "./BarrasAno";
import FaixaTipo from "./FaixaTipo";
import {
  agrupar, carregarAno, carregarResumo, DIMS, dimsDisponiveis, escalar, METRICAS, proximaSugerida,
  ROTULO_DIM, taxaRealizacao, temTipo, TIPOS_DESPESA, totaisDaTrilha, type Dim, type Filtro, type Item, type Metrica,
} from "../../lib/dados";
import { moedaExtenso, pct } from "../../lib/formato";
import "./explorer.css";

type Vista = "mapa" | "lista";

interface Estado {
  ano: number | null;
  metrica: Metrica;
  filtros: Filtro[];
  por: Dim | null;
  semRefin: boolean;
  vista: Vista;
  real: boolean;
}

/** Rótulos curtos das abas "Dividir por". */
const ABA: Record<Dim, string> = {
  orgao: "Órgão", funcao: "Área", subfuncao: "Subárea", uo: "Unidade",
  programa: "Programa", acao: "Ação", gnd: "Tipo de gasto", tipo: "Obrigatório ou não",
};

/** Ordem das abas, como no mock: as mais usadas primeiro. */
const ORDEM_ABAS: Dim[] = ["orgao", "tipo", "programa", "uo", "acao", "gnd", "funcao", "subfuncao"];

/** No mapa dividido por tipo de despesa, cada bloco com a cor da legenda (FaixaTipo). */
const corDoTipo = (item: Item) => {
  const t = TIPOS_DESPESA.find((x) => x.cod === item.codigo);
  return t && { fundo: t.cor, escuro: t.cod === "obr" };
};

const ehDim = (s: string | null): s is Dim => !!s && (DIMS as string[]).includes(s);

function lerUrl(): Estado {
  const p = new URLSearchParams(location.search);
  const ano = Number(p.get("ano"));
  const metrica = p.get("metrica") as Metrica;
  const filtros = (p.get("f") ?? "")
    .split(",")
    .map((par) => par.split(":"))
    .filter(([d, c]) => ehDim(d) && c)
    .map(([d, c]) => ({ dim: d as Dim, cod: c }));
  const por = p.get("por");
  return {
    ano: Number.isInteger(ano) && ano > 0 ? ano : null,
    metrica: METRICAS.includes(metrica) ? metrica : "atualizado",
    filtros,
    por: ehDim(por) && !filtros.some((f) => f.dim === por) ? por : proximaSugerida(filtros),
    semRefin: p.get("refin") === "0",
    vista: p.get("vista") === "lista" || p.get("vista") === "tabela" ? "lista" : "mapa",
    real: p.get("ipca") === "1",
  };
}

function escreverUrl(e: Estado, push: boolean) {
  const p = new URLSearchParams();
  if (e.ano) p.set("ano", String(e.ano));
  if (e.metrica !== "atualizado") p.set("metrica", e.metrica);
  if (e.filtros.length) p.set("f", e.filtros.map((f) => `${f.dim}:${f.cod}`).join(","));
  if (e.por) p.set("por", e.por);
  if (e.semRefin) p.set("refin", "0");
  if (e.vista === "lista") p.set("vista", "lista");
  if (e.real) p.set("ipca", "1");
  const url = `${location.pathname}?${p.toString().replaceAll("%3A", ":").replaceAll("%2C", ",")}`;
  if (push) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

/** Gera e baixa um CSV com os itens do nível atual. */
function baixarCsv(itens: Item[], dim: Dim, ano: number, real: boolean) {
  const cab = ["codigo", ROTULO_DIM[dim].toLowerCase(), "dotacao_inicial", "dotacao_atualizada", "empenhado", "realizado"];
  const esc = (s: string) => `"${s.replaceAll('"', '""')}"`;
  const linhas = itens.map((i) =>
    [i.codigo, esc(i.nome), ...(["inicial", "atualizado", "empenhado", "realizado"] as Metrica[]).map((m) => Math.round(i.valores[m]))].join(","),
  );
  const blob = new Blob([[cab.join(","), ...linhas].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `orcamento-${ano}-${dim}${real ? "-ipca" : ""}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function Explorer() {
  const [estado, setEstado] = createSignal<Estado>(lerUrl());
  const [resumo] = createResource(carregarResumo);
  const anoCorrente = new Date().getFullYear();

  // Ano padrão: o último ano completo (o corrente ainda está em execução).
  const ano = createMemo(() => {
    const e = estado().ano;
    const anos = resumo()?.anos.map((a) => a.ano) ?? [];
    if (e && anos.includes(e)) return e;
    return anos.filter((a) => a < anoCorrente).at(-1) ?? anos.at(-1) ?? null;
  });
  const [doc] = createResource(ano, carregarAno);

  const mudar = (parcial: Partial<Estado>, push = false) => {
    const novo = { ...estado(), ano: ano(), ...parcial };
    setEstado(novo);
    escreverUrl(novo, push);
  };

  onMount(() => {
    const voltar = () => setEstado(lerUrl());
    addEventListener("popstate", voltar);
    onCleanup(() => removeEventListener("popstate", voltar));
  });

  // Correção pela inflação: reais do ano-base do IPCA.
  const ipca = () => resumo()?.ipca ?? null;
  const fatorDe = (a: number | null) => {
    const i = ipca();
    return estado().real && i && a ? i.fatores[String(a)] ?? 1 : 1;
  };

  // Série histórica (todos os anos, carregados uma vez).
  const anosLista = () => resumo()?.anos.map((a) => a.ano) ?? [];
  const [todos] = createResource(
    () => (anosLista().length ? anosLista().join(",") : false),
    (chave: string) => Promise.all(chave.split(",").map(Number).map(carregarAno)),
  );
  const serie = createMemo<Ponto[] | null>(() => {
    const ds = todos();
    if (!ds) return null;
    const e = estado();
    return ds
      .map((d) => ({ ano: d.ano, valores: escalar(agrupar(d, e.filtros, null, e.semRefin).total, fatorDe(d.ano)) }))
      .sort((a, b) => a.ano - b.ano);
  });

  const grupo = createMemo(() => {
    const d = doc();
    if (!d) return null;
    const e = estado();
    const g = agrupar(d, e.filtros, e.por, e.semRefin);
    const f = fatorDe(ano());
    return { total: escalar(g.total, f), itens: g.itens.map((i) => ({ ...i, valores: escalar(i.valores, f) })) };
  });
  const total = () => grupo()?.total[estado().metrica] ?? 0;
  const totalGeral = createMemo(() => {
    const d = doc();
    if (!d) return 0;
    return agrupar(d, [], null, estado().semRefin).total.atualizado * fatorDe(ano());
  });

  const trilha = createMemo(() => {
    const d = doc();
    if (!d) return [];
    const e = estado();
    const totais = totaisDaTrilha(d, e.filtros, e.metrica, e.semRefin);
    return e.filtros.map((f, i) => ({
      ...f,
      nome: d.dims[f.dim][f.cod] ?? f.cod,
      total: totais[i] * fatorDe(ano()),
      filtros: e.filtros.slice(0, i + 1),
    }));
  });
  const ultimo = () => trilha().at(-1);

  const descer = (item: Item) => {
    const e = estado();
    if (!e.por) return;
    const filtros = [...e.filtros, { dim: e.por, cod: item.codigo }];
    mudar({ filtros, por: proximaSugerida(filtros) }, true);
  };
  const irPara = (filtros: Filtro[]) => mudar({ filtros, por: proximaSugerida(filtros) }, true);
  const podeDescer = () => dimsDisponiveis(estado().filtros).length > 1;
  // Voltar um nível: o passo anterior da trilha, ou o orçamento inteiro.
  const pai = () => (trilha().length > 1 ? trilha().at(-2)!.nome : `todo o orçamento de ${ano() ?? ""}`);
  const subir = () => irPara(estado().filtros.slice(0, -1));

  const legendaSerie = () =>
    estado().real && ipca() ? `Dotação por ano, em reais de ${ipca()!.base}` : "Dotação por ano, em valores nominais";

  return (
    <div class="exp">
      <div class="exp-barra">
        <nav aria-label="Caminho" class="exp-caminho">
          <Show when={trilha().length > 0} fallback={<span class="forte">Orçamento {ano() ?? ""}</span>}>
            <button type="button" class="link" onClick={() => irPara([])}>Orçamento {ano() ?? ""}</button>
          </Show>
          <For each={trilha()}>
            {(passo, i) => (
              <>
                <span class="sep" aria-hidden="true">/</span>
                <Show when={i() < trilha().length - 1} fallback={<span class="forte corta" title={passo.nome}>{passo.nome}</span>}>
                  <button type="button" class="link corta" title={passo.nome} onClick={() => irPara(passo.filtros)}>{passo.nome}</button>
                </Show>
              </>
            )}
          </For>
        </nav>
        <div class="exp-controles">
          <label class="exp-ano">
            <span class="visually-hidden">Ano</span>
            <select onChange={(e) => mudar({ ano: Number(e.currentTarget.value) })} disabled={!resumo()}>
              <For each={[...(resumo()?.anos ?? [])].reverse()}>
                {(a) => <option value={a.ano} selected={a.ano === ano()}>{a.ano}{a.ano === anoCorrente ? " (em execução)" : ""}</option>}
              </For>
            </select>
          </label>
          <button type="button" class="pilula" aria-pressed={estado().real} disabled={!ipca()}
            title={ipca() ? `Valores em reais de ${ipca()!.base}, corrigidos pelo IPCA` : undefined}
            onClick={() => mudar({ real: !estado().real })}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" /></svg>
            Corrigir inflação
          </button>
          <button type="button" class="pilula" aria-pressed={estado().semRefin}
            title="Tira das contas a rolagem da dívida pública (subfunções 841 e 842)"
            onClick={() => mudar({ semRefin: !estado().semRefin })}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" /></svg>
            Sem refinanciamento
          </button>
        </div>
      </div>

      <Show when={doc.error || resumo.error}>
        <p class="exp-erro">Não foi possível carregar os dados. {String((doc.error ?? resumo.error)?.message ?? "")}</p>
      </Show>

      <section class="exp-topo">
        <div class="exp-titulo">
          <Show when={ultimo()}>
            <button type="button" class="link exp-voltar" onClick={subir}>← Voltar a {pai()}</button>
          </Show>
          <span class="sobretitulo">
            {ultimo() ? (ultimo()!.dim === "tipo" ? ROTULO_DIM.tipo : `${ROTULO_DIM[ultimo()!.dim]} · ${ultimo()!.cod}`) : "Orçamento federal"}
          </span>
          <h1>{ultimo()?.nome ?? `Todo o orçamento de ${ano() ?? ""}`}</h1>
          <Show when={grupo()}>
            {(g) => {
              const t = () => g().total;
              const taxaEmp = () => (t().atualizado > 0 ? t().empenhado / t().atualizado : null);
              return (
                <p class="exp-lede">
                  <Show when={ultimo()} fallback={<>O governo federal pôde gastar <strong class="marca">{moedaExtenso(t().atualizado)}</strong> em {ano()}.</>}>
                    Teve <strong class="marca">{moedaExtenso(t().atualizado)}</strong> autorizados em {ano()}
                    , {pct(t().atualizado / Math.max(1, totalGeral()))} do orçamento federal.
                  </Show>{" "}
                  Empenhou {pct(taxaEmp())} e pagou {pct(taxaRealizacao(t()))}.
                </p>
              );
            }}
          </Show>
        </div>
        <figure class="exp-serie">
          <figcaption>{legendaSerie()}</figcaption>
          <BarrasAno serie={serie()} metrica="atualizado" anoSelecionado={ano()} anoCorrente={anoCorrente}
            altura={120} rotulos="extremos" onAno={(a) => mudar({ ano: a }, true)} />
        </figure>
      </section>

      <Show when={temTipo(doc()) && !estado().filtros.some((f) => f.dim === "tipo")}>
        <FaixaTipo doc={doc()!} ano={ano()!} filtros={estado().filtros} metrica={estado().metrica} semRefin={estado().semRefin}
          fator={fatorDe(ano())} onSemRefin={() => mudar({ semRefin: true })}
          onEscolher={(cod) => {
            const filtros = [...estado().filtros, { dim: "tipo" as Dim, cod }];
            const por = estado().por;
            mudar({ filtros, por: por && por !== "tipo" ? por : proximaSugerida(filtros) }, true);
          }} />
      </Show>

      <div class="exp-abas">
        <Show when={ultimo()}>
          <button type="button" class="exp-subir" onClick={subir} title={`Voltar a ${pai()}`}>← Voltar um nível</button>
        </Show>
        <span class="muted">Dividir por</span>
        <div class="exp-abas-dims" role="tablist" aria-label="Dividir por">
          <For each={ORDEM_ABAS.filter((d) => dimsDisponiveis(estado().filtros).includes(d) && (d !== "tipo" || temTipo(doc())))}>
            {(d) => (
              <button type="button" role="tab" aria-selected={d === estado().por} onClick={() => mudar({ por: d })}>
                {ABA[d]}
              </button>
            )}
          </For>
        </div>
        <span class="exp-abas-espaco" />
        <div class="exp-vistas">
          <button type="button" aria-pressed={estado().vista === "mapa"} onClick={() => mudar({ vista: "mapa" })}>Mapa</button>
          <span aria-hidden="true">|</span>
          <button type="button" aria-pressed={estado().vista === "lista"} onClick={() => mudar({ vista: "lista" })}>Lista</button>
          <span aria-hidden="true">|</span>
          <button type="button" disabled={!grupo() || !estado().por}
            onClick={() => baixarCsv(grupo()!.itens, estado().por!, ano()!, estado().real)}>Baixar CSV</button>
        </div>
      </div>

      <Show when={grupo()} fallback={<div class="exp-carregando" aria-busy="true">Carregando…</div>}>
        <Show when={(grupo()?.itens.length ?? 0) > 0} fallback={
          <div class="exp-carregando">
            <p>Este caminho não tem valores em {ano()}.</p>
            <button type="button" class="botao" onClick={() => irPara([])}>Voltar ao início</button>
          </div>
        }>
          <Show when={estado().vista === "mapa"} fallback={
            <Tabela itens={grupo()!.itens} metrica={estado().metrica} total={Math.max(1, total())}
              rotuloNome={estado().por ? ROTULO_DIM[estado().por!] : "Nome"} podeDescer={podeDescer()} onEscolher={descer} />
          }>
            <Treemap itens={grupo()!.itens} metrica={estado().metrica} total={Math.max(1, total())}
              podeDescer={podeDescer()} onEscolher={descer} corDe={estado().por === "tipo" ? corDoTipo : undefined} />
          </Show>
        </Show>
      </Show>

      <p class="exp-nota">
        <Show when={estado().vista === "mapa"}>Cada bloco é proporcional à dotação; clique para descer um nível. </Show>
        * {anoCorrente} ainda em execução. Pago = realizado ÷ dotação atualizada.
        <Show when={!estado().semRefin && trilha().length === 0}> Os totais incluem o refinanciamento da dívida pública.</Show>
      </p>
    </div>
  );
}
