import { createMemo, createResource, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import Treemap from "./Treemap";
import Tabela from "./Tabela";
import {
  agrupar, ARTIGO_DIM, carregarAno, carregarResumo, DIMS, dimsDisponiveis, METRICAS, proximaSugerida,
  ROTULO_DIM, ROTULO_METRICA, totaisDaTrilha, type Dim, type Filtro, type Item, type Metrica,
} from "../../lib/dados";
import { moedaCompleta, moedaExtenso } from "../../lib/formato";
import "./explorer.css";

type Vista = "mapa" | "tabela";

interface Estado {
  ano: number | null;
  metrica: Metrica;
  filtros: Filtro[];
  por: Dim | null;
  semRefin: boolean;
  vista: Vista;
}

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
    vista: p.get("vista") === "tabela" ? "tabela" : "mapa",
  };
}

function escreverUrl(e: Estado, push: boolean) {
  const p = new URLSearchParams();
  if (e.ano) p.set("ano", String(e.ano));
  if (e.metrica !== "atualizado") p.set("metrica", e.metrica);
  if (e.filtros.length) p.set("f", e.filtros.map((f) => `${f.dim}:${f.cod}`).join(","));
  if (e.por) p.set("por", e.por);
  if (e.semRefin) p.set("refin", "0");
  if (e.vista === "tabela") p.set("vista", "tabela");
  const url = `${location.pathname}?${p.toString().replaceAll("%3A", ":").replaceAll("%2C", ",")}`;
  if (push) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

const dataCurta = (iso: string) =>
  new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });

export default function Explorer() {
  const [estado, setEstado] = createSignal<Estado>(lerUrl());
  const [resumo] = createResource(carregarResumo);

  // Ano padrão: o último ano completo (o corrente ainda está em execução).
  const ano = createMemo(() => {
    const e = estado().ano;
    const anos = resumo()?.anos.map((a) => a.ano) ?? [];
    if (e && anos.includes(e)) return e;
    const corrente = new Date().getFullYear();
    return anos.filter((a) => a < corrente).at(-1) ?? anos.at(-1) ?? null;
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

  const grupo = createMemo(() => {
    const d = doc();
    if (!d) return null;
    const e = estado();
    return agrupar(d, e.filtros, e.por, e.semRefin);
  });
  const itens = createMemo(() => {
    const m = estado().metrica;
    return [...(grupo()?.itens ?? [])].sort((a, b) => b.valores[m] - a.valores[m]);
  });
  const total = () => grupo()?.total[estado().metrica] ?? 0;

  const trilha = createMemo(() => {
    const d = doc();
    if (!d) return [];
    const e = estado();
    const totais = totaisDaTrilha(d, e.filtros, e.metrica, e.semRefin);
    return e.filtros.map((f, i) => ({
      ...f,
      nome: d.dims[f.dim][f.cod] ?? f.cod,
      total: totais[i],
      filtros: e.filtros.slice(0, i + 1),
    }));
  });
  const totalGeral = createMemo(() => {
    const d = doc();
    if (!d) return 0;
    return agrupar(d, [], null, estado().semRefin).total[estado().metrica];
  });

  const descer = (item: Item) => {
    const e = estado();
    if (!e.por) return;
    const filtros = [...e.filtros, { dim: e.por, cod: item.codigo }];
    mudar({ filtros, por: proximaSugerida(filtros) }, true);
  };
  const irPara = (filtros: Filtro[]) => mudar({ filtros, por: proximaSugerida(filtros) }, true);
  const podeDescer = () => dimsDisponiveis(estado().filtros).length > 1;
  const ultimo = () => trilha().at(-1);

  return (
    <div class="ex">
      <aside class="ex-lado" aria-label="Seleção">
        <button type="button" class="ex-recomecar" onClick={() => irPara([])}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 12h3v9h6v-6h2v6h6v-9h3L12 3z" /></svg>
          Recomeçar
        </button>

        <div class="ex-lado-bloco">
          <label class="ex-ano">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 2v2H4a1 1 0 0 0-1 1v15a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1h-3V2h-2v2H9V2H7zM5 9h14v10H5V9z" />
            </svg>
            <span class="visually-hidden">Ano</span>
            <select onChange={(e) => mudar({ ano: Number(e.currentTarget.value) })} disabled={!resumo()}>
              <For each={[...(resumo()?.anos ?? [])].reverse()}>
                {(a) => (
                  <option value={a.ano} selected={a.ano === ano()}>
                    {a.ano}{a.ano === new Date().getFullYear() ? " (em execução)" : ""}
                  </option>
                )}
              </For>
            </select>
          </label>
          <label class="ex-refin">
            <input type="checkbox" checked={estado().semRefin}
              onChange={(e) => mudar({ semRefin: e.currentTarget.checked })} />
            <span>Excluir refinanciamento da dívida</span>
          </label>
        </div>

        <ol class="ex-trilha">
          <li classList={{ atual: estado().filtros.length === 0 }}>
            <span class="ponto" aria-hidden="true" />
            <button type="button" onClick={() => irPara([])}>
              <span class="rotulo">Todo o orçamento</span>
              <span class="nome num">{moedaExtenso(totalGeral())}</span>
            </button>
          </li>
          <For each={trilha()}>
            {(passo, i) => (
              <li classList={{ atual: i() === trilha().length - 1 }}>
                <span class="trilho" aria-hidden="true" />
                <span class="ponto" aria-hidden="true" />
                <button type="button" onClick={() => irPara(passo.filtros)}>
                  <span class="rotulo">{ROTULO_DIM[passo.dim]}</span>
                  <span class="nome">{passo.nome}</span>
                  <span class="valor num">{moedaExtenso(passo.total)}</span>
                </button>
              </li>
            )}
          </For>
        </ol>
      </aside>

      <section class="ex-principal">
        <Show when={doc.error || resumo.error}>
          <p class="ex-erro">Não foi possível carregar os dados. {String((doc.error ?? resumo.error)?.message ?? "")}</p>
        </Show>

        <header class="ex-cabeca">
          <div class="ex-titulo">
            <Show when={ultimo()} fallback={
              <>
                <h2>Você está vendo o orçamento de {ano() ?? "…"} por {estado().por ? ROTULO_DIM[estado().por!].toLowerCase() : ""}</h2>
                <p>Escolha um item abaixo para começar a explorar.</p>
              </>
            }>
              {(u) => (
                <>
                  <p class="ex-escolheu">Você escolheu</p>
                  <h2 class="ex-nome">{u().nome}</h2>
                  <p>{ARTIGO_DIM[u().dim]} <span class="cod">{u().cod}</span></p>
                </>
              )}
            </Show>
          </div>
          <div class="ex-total">
            <div class="ex-total-rotulo">{ROTULO_METRICA[estado().metrica]} {ano() ?? ""}</div>
            <div class="ex-total-valor num" title={moedaCompleta(total())}>{doc() ? moedaExtenso(total()) : "…"}</div>
            <Show when={doc()}>
              <div class="ex-total-data">Dados baixados em {dataCurta(doc()!.gerado_em)}</div>
            </Show>
          </div>
        </header>

        <div class="ex-cartao">
          <div class="ex-barra">
            <label class="ex-por">
              <span>Detalhar por:</span>
              <select onChange={(e) => mudar({ por: e.currentTarget.value as Dim })}>
                <For each={dimsDisponiveis(estado().filtros)}>
                  {(d) => <option value={d} selected={d === estado().por}>{ROTULO_DIM[d]}</option>}
                </For>
              </select>
            </label>
            <label class="ex-por">
              <span>Valor:</span>
              <select onChange={(e) => mudar({ metrica: e.currentTarget.value as Metrica })}>
                <For each={METRICAS}>
                  {(m) => <option value={m} selected={m === estado().metrica}>{ROTULO_METRICA[m]}</option>}
                </For>
              </select>
            </label>
            <div class="ex-vistas" role="group" aria-label="Forma de visualização">
              <button type="button" aria-pressed={estado().vista === "mapa"} title="Mapa de blocos"
                onClick={() => mudar({ vista: "mapa" })}>
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1 1h8v9H1zM10 1h5v5h-5zM10 7h5v8h-5zM1 11h8v4H1z" /></svg>
                <span class="visually-hidden">Mapa de blocos</span>
              </button>
              <button type="button" aria-pressed={estado().vista === "tabela"} title="Tabela"
                onClick={() => mudar({ vista: "tabela" })}>
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1 2h14v3H1zM1 6.5h14v3H1zM1 11h14v3H1z" /></svg>
                <span class="visually-hidden">Tabela</span>
              </button>
            </div>
          </div>

          <Show when={grupo()} fallback={<div class="ex-carregando" aria-busy="true">Carregando…</div>}>
            <Show when={itens().length > 0} fallback={
              <div class="ex-carregando">
                <p>Este caminho não tem valores em {ano()}.</p>
                <button type="button" class="ex-botao" onClick={() => irPara([])}>Recomeçar</button>
              </div>
            }>
              <Show when={estado().vista === "mapa"} fallback={
                <Tabela itens={itens()} metrica={estado().metrica} total={Math.max(1, total())}
                  rotuloNome={estado().por ? ROTULO_DIM[estado().por!] : "Nome"}
                  podeDescer={podeDescer()} onEscolher={descer} />
              }>
                <Treemap itens={itens()} metrica={estado().metrica} total={Math.max(1, total())}
                  podeDescer={podeDescer()} onEscolher={descer} />
              </Show>
            </Show>
          </Show>
        </div>
      </section>
    </div>
  );
}
