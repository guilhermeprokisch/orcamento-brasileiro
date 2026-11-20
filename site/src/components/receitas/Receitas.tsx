import { createMemo, createResource, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import Treemap from "../explorer/Treemap";
import Tabela from "../explorer/Tabela";
import BarrasAno, { type Ponto } from "../explorer/BarrasAno";
import { carregarResumo, escalar, taxaRealizacao, type Item } from "../../lib/dados";
import {
  agruparR, carregarReceitas, creditoSemRefin, dimsDisponiveisR, DIMS_R, EXPLICA_ORIGEM, proximaSugeridaR,
  refinanciamento, ROTULO_DIM_R, ROTULOS_RECEITA, type DimR, type Filtro,
} from "../../lib/receitas";
import { moedaExtenso, pct } from "../../lib/formato";
import "../explorer/explorer.css";
import "./receitas.css";

type Vista = "mapa" | "lista";

interface Estado {
  ano: number | null;
  filtros: Filtro[];
  por: DimR | null;
  semRefin: boolean;
  vista: Vista;
  real: boolean;
}

/** Rótulos curtos das abas "Dividir por". */
const ABA: Record<DimR, string> = {
  origem: "Tipo", especie: "Subtipo", item: "Receita", parcela: "Parcela", orgao: "Órgão", categoria: "Categoria",
};
const ORDEM_ABAS: DimR[] = ["origem", "especie", "item", "parcela", "orgao", "categoria"];

const ehDim = (s: string | null): s is DimR => !!s && (DIMS_R as string[]).includes(s);

function lerUrl(): Estado {
  const p = new URLSearchParams(location.search);
  const ano = Number(p.get("ano"));
  const filtros = (p.get("f") ?? "")
    .split(",")
    .map((par) => par.split(":"))
    .filter(([d, c]) => ehDim(d) && c)
    .map(([d, c]) => ({ dim: d as DimR, cod: c }));
  const por = p.get("por");
  return {
    ano: Number.isInteger(ano) && ano > 0 ? ano : null,
    filtros,
    por: ehDim(por) && !filtros.some((f) => f.dim === por) ? por : proximaSugeridaR(filtros),
    semRefin: p.get("refin") === "0",
    vista: p.get("vista") === "lista" ? "lista" : "mapa",
    real: p.get("ipca") === "1",
  };
}

function escreverUrl(e: Estado, push: boolean) {
  const p = new URLSearchParams();
  if (e.ano) p.set("ano", String(e.ano));
  if (e.filtros.length) p.set("f", e.filtros.map((f) => `${f.dim}:${f.cod}`).join(","));
  if (e.por) p.set("por", e.por);
  if (e.semRefin) p.set("refin", "0");
  if (e.vista === "lista") p.set("vista", "lista");
  if (e.real) p.set("ipca", "1");
  const url = `${location.pathname}?${p.toString().replaceAll("%3A", ":").replaceAll("%2C", ",")}`;
  if (push) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

function baixarCsv(itens: Item[], dim: DimR, ano: number, real: boolean) {
  const esc = (s: string) => `"${s.replaceAll('"', '""')}"`;
  const linhas = itens.map((i) => [i.codigo, esc(i.nome), Math.round(i.valores.atualizado), Math.round(i.valores.realizado)].join(","));
  const cab = ["codigo", esc(ROTULO_DIM_R[dim].toLowerCase()), "previsto_atualizado", "arrecadado"].join(",");
  const blob = new Blob([[cab, ...linhas].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `receitas-uniao-${ano}-${dim}${real ? "-ipca" : ""}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

const dataCurta = (iso: string | null) => (iso ? iso.split("-").reverse().slice(0, 2).join("/") : "");

export default function Receitas() {
  const [estado, setEstado] = createSignal<Estado>(lerUrl());
  const [doc] = createResource(carregarReceitas);
  // O IPCA vem do resumo do explorador de gastos (mesmo ano-base nas duas páginas).
  const [resumo] = createResource(() => carregarResumo().catch(() => null));

  const anos = () => doc()?.anos ?? [];
  const anoPadrao = () => anos().filter((a) => !a.parcial).at(-1)?.ano ?? anos().at(-1)?.ano ?? null;
  const ano = createMemo(() => {
    const e = estado().ano;
    return e && anos().some((a) => a.ano === e) ? e : anoPadrao();
  });
  const anoDoc = () => anos().find((a) => a.ano === ano()) ?? null;
  const anoCorrente = () => anos().find((a) => a.parcial)?.ano ?? -1;

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

  const ipca = () => resumo()?.ipca ?? null;
  const fatorDe = (a: number | null) => {
    const i = ipca();
    return estado().real && i && a ? i.fatores[String(a)] ?? 1 : 1;
  };

  const serie = createMemo<Ponto[] | null>(() => {
    const d = doc();
    if (!d) return null;
    const e = estado();
    return d.anos.map((a) => ({ ano: a.ano, valores: escalar(agruparR(d, a, e.filtros, null, e.semRefin).total, fatorDe(a.ano)) }));
  });

  const grupo = createMemo(() => {
    const d = doc();
    const a = anoDoc();
    if (!d || !a) return null;
    const e = estado();
    const g = agruparR(d, a, e.filtros, e.por, e.semRefin);
    const f = fatorDe(a.ano);
    return { total: escalar(g.total, f), itens: g.itens.map((i) => ({ ...i, valores: escalar(i.valores, f) })) };
  });
  const total = () => grupo()?.total.realizado ?? 0;
  // Total do ano inteiro, com e sem o refinanciamento.
  const geral = createMemo(() => {
    const d = doc();
    const a = anoDoc();
    if (!d || !a) return null;
    const f = fatorDe(a.ano);
    const tudo = agruparR(d, a, [], null, false).total.realizado * f;
    const refin = refinanciamento(d, a, []) * f;
    return { tudo, refin, semRefin: tudo - refin, credito: creditoSemRefin(d, a) * f };
  });
  const totalGeral = () => (estado().semRefin ? geral()?.semRefin : geral()?.tudo) ?? 0;

  const trilha = createMemo(() => {
    const d = doc();
    const a = anoDoc();
    if (!d || !a) return [];
    const e = estado();
    return e.filtros.map((f, i) => ({
      ...f,
      nome: d.dims[f.dim][f.cod] ?? f.cod,
      total: agruparR(d, a, e.filtros.slice(0, i + 1), null, e.semRefin).total.realizado * fatorDe(a.ano),
      filtros: e.filtros.slice(0, i + 1),
    }));
  });
  const ultimo = () => trilha().at(-1);

  const descer = (item: Item) => {
    const e = estado();
    if (!e.por) return;
    const filtros = [...e.filtros, { dim: e.por, cod: item.codigo }];
    mudar({ filtros, por: proximaSugeridaR(filtros) }, true);
  };
  const irPara = (filtros: Filtro[]) => mudar({ filtros, por: proximaSugeridaR(filtros) }, true);
  const podeDescer = () => dimsDisponiveisR(estado().filtros).length > 1;
  const pai = () => (trilha().length > 1 ? trilha().at(-2)!.nome : `todas as receitas de ${ano() ?? ""}`);
  const subir = () => irPara(estado().filtros.slice(0, -1));

  // Nesta trilha, quanto é refinanciamento (para avisar quando a pessoa entra em "Operações de crédito").
  const refinAqui = createMemo(() => {
    const d = doc();
    const a = anoDoc();
    if (!d || !a || estado().semRefin) return 0;
    return refinanciamento(d, a, estado().filtros) * fatorDe(a.ano);
  });

  const legendaSerie = () =>
    `Arrecadado por ano${estado().semRefin ? ", sem refinanciamento" : ""}, ${
      estado().real && ipca() ? `em reais de ${ipca()!.base}` : "em valores nominais"}`;
  const ateQuando = () => {
    const a = anoDoc();
    return a?.parcial && a.ate ? ` até ${dataCurta(a.ate)}` : "";
  };
  const conferencia = () => {
    const a = anoDoc();
    if (!a?.oficial || estado().real) return null;
    const portal = geral()?.tudo ?? 0;
    return { oficial: a.oficial.realizado, dif: portal / a.oficial.realizado - 1 };
  };

  return (
    <div class="exp rec">
      <div class="exp-barra">
        <nav aria-label="Caminho" class="exp-caminho">
          <Show when={trilha().length > 0} fallback={<span class="forte">Receitas {ano() ?? ""}</span>}>
            <button type="button" class="link" onClick={() => irPara([])}>Receitas {ano() ?? ""}</button>
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
            <select onChange={(e) => mudar({ ano: Number(e.currentTarget.value) })} disabled={!doc()}>
              <For each={[...anos()].reverse()}>
                {(a) => <option value={a.ano} selected={a.ano === ano()}>{a.ano}{a.parcial ? ` (até ${dataCurta(a.ate)})` : ""}</option>}
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
            title="Tira das contas os títulos vendidos para pagar a dívida que vence (refinanciamento)"
            onClick={() => mudar({ semRefin: !estado().semRefin })}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" /></svg>
            Sem refinanciamento
          </button>
        </div>
      </div>

      <Show when={doc.error}>
        <p class="exp-erro">Não foi possível carregar os dados. {String(doc.error?.message ?? "")}</p>
      </Show>

      <section class="exp-topo">
        <div class="exp-titulo">
          <Show when={ultimo()}>
            <button type="button" class="link exp-voltar" onClick={subir}>← Voltar a {pai()}</button>
          </Show>
          <span class="sobretitulo">
            {ultimo() ? ROTULO_DIM_R[ultimo()!.dim] : "Receitas do governo federal"}
          </span>
          <Show when={grupo()} fallback={<h1>Receitas da União</h1>}>
            {(g) => (
              <>
                <h1>
                  <Show when={ultimo()} fallback={<>{moedaExtenso(g().total.realizado)} entraram em {ano()}{ateQuando()}</>}>
                    {ultimo()!.nome}
                  </Show>
                </h1>
                <p class="exp-lede">
                  <Show when={ultimo()} fallback={
                    <>De onde veio o dinheiro do governo federal{estado().semRefin ? ", sem contar o refinanciamento da dívida" : ""}.{" "}
                      Estava previsto {moedaExtenso(g().total.atualizado)}; entrou {pct(taxaRealizacao(g().total))} disso.</>
                  }>
                    Trouxe <strong class="marca">{moedaExtenso(g().total.realizado)}</strong> em {ano()}{ateQuando()},{" "}
                    {pct(g().total.realizado / Math.max(1, totalGeral()))} de tudo o que entrou.{" "}
                    <Show when={g().total.atualizado > 0}>Entrou {pct(taxaRealizacao(g().total))} do previsto.</Show>
                  </Show>
                </p>
                <Show when={ultimo()?.dim === "origem" && EXPLICA_ORIGEM[ultimo()!.cod]}>
                  <p class="rec-explica">{EXPLICA_ORIGEM[ultimo()!.cod]}</p>
                </Show>
              </>
            )}
          </Show>
        </div>
        <figure class="exp-serie">
          <figcaption>{legendaSerie()}</figcaption>
          <BarrasAno serie={serie()} metrica="realizado" anoSelecionado={ano()} anoCorrente={anoCorrente()}
            altura={120} rotulos="extremos" rotuloMetrica="Arrecadado" rotuloCorrente="ano em andamento"
            onAno={(a) => mudar({ ano: a }, true)} />
        </figure>
      </section>

      {/* O refinanciamento infla a "receita": avisa no topo e dentro das operações de crédito. */}
      <Show when={geral() && (trilha().length === 0 || refinAqui() > 0)}>
        <aside class="rec-aviso" aria-label="Sobre o refinanciamento da dívida">
          <Show when={!estado().semRefin} fallback={
            <p>
              Sem o refinanciamento, entraram <strong>{moedaExtenso(geral()!.semRefin)}</strong> em {ano()}. Ainda
              há <strong>{moedaExtenso(geral()!.credito)}</strong> de dívida nova nessa conta: títulos vendidos para
              cobrir o que faltou (o déficit) e outras despesas, não para pagar dívida velha.{" "}
              <button type="button" class="link" onClick={() => mudar({ semRefin: false })}>Ver com o refinanciamento</button>
            </p>
          }>
            <p>
              <strong>{moedaExtenso(trilha().length ? refinAqui() : geral()!.refin)}</strong>
              {trilha().length ? " disso" : ` (${pct(geral()!.refin / Math.max(1, geral()!.tudo))} do total)`} não é dinheiro
              novo: é dívida nova que paga dívida velha. Quando um título do Tesouro vence, o governo vende outro
              para pagar quem tinha o primeiro. Essa troca, o <em>refinanciamento da dívida</em>, aparece como
              receita aqui e como gasto no <a href="/explorer">explorador de gastos</a>.{" "}
              <button type="button" class="link" onClick={() => mudar({ semRefin: true })}>Ver sem o refinanciamento</button>
            </p>
          </Show>
        </aside>
      </Show>

      <div class="exp-abas">
        <Show when={ultimo()}>
          <button type="button" class="exp-subir" onClick={subir} title={`Voltar a ${pai()}`}>← Voltar um nível</button>
        </Show>
        <span class="muted">Dividir por</span>
        <div class="exp-abas-dims" role="tablist" aria-label="Dividir por">
          <For each={ORDEM_ABAS.filter((d) => dimsDisponiveisR(estado().filtros).includes(d))}>
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
            <Tabela itens={grupo()!.itens} metrica="realizado" total={Math.max(1, total())} rotulos={ROTULOS_RECEITA}
              rotuloNome={estado().por ? ROTULO_DIM_R[estado().por!] : "Nome"} podeDescer={podeDescer()} onEscolher={descer} />
          }>
            <Treemap itens={grupo()!.itens} metrica="realizado" total={Math.max(1, total())} rotulos={ROTULOS_RECEITA}
              podeDescer={podeDescer()} onEscolher={descer} />
          </Show>
        </Show>
      </Show>

      <p class="exp-nota">
        <Show when={estado().vista === "mapa"}>Cada bloco é proporcional ao que foi arrecadado; clique para descer um nível. </Show>
        Previsto = previsão atualizada no orçamento do ano. Valores já descontam devoluções (como a restituição do imposto de renda).
        <Show when={anoDoc()?.parcial}> {ano()} ainda está em andamento: dados até {dataCurta(anoDoc()!.ate)}.</Show>{" "}
        Fonte: <a href={doc()?.url ?? "https://portaldatransparencia.gov.br/download-de-dados/receitas"}>Portal da Transparência (CGU)</a>.
        <Show when={conferencia()}>
          {(c) => (
            <> O relatório oficial do Tesouro (RREO) registra {moedaExtenso(c().oficial)} em {ano()};
              {Math.abs(c().dif) < 0.005 ? " o arquivo do Portal bate com ele." : ` o arquivo do Portal, de onde vêm os detalhes, soma ${pct(Math.abs(c().dif))} a ${c().dif < 0 ? "menos" : "mais"}.`}</>
          )}
        </Show>
      </p>
    </div>
  );
}
