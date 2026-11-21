/**
 * O explorador das emendas, no mesmo desenho do explorador de gastos e do de receitas (mapa de blocos, lista,
 * barras por ano, trilha e "dividir por"): cada clique filtra e desce um nível. Os dados são os pagamentos da CGU,
 * consultados no navegador com o DuckDB direto no Parquet do bucket (o mesmo da busca de /emendas), então todas
 * as listas são inteiras: todos os deputados e senadores, todas as comissões e bancadas, todas as cidades.
 * O estado fica na URL (?ano=, ?f=dim:código,…, ?por=, ?vista=), como nos outros exploradores.
 */
import { createEffect, createMemo, createSignal, For, on, onCleanup, onMount, Show } from "solid-js";
import Treemap from "../explorer/Treemap";
import Tabela from "../explorer/Tabela";
import BarrasAno, { type Ponto } from "../explorer/BarrasAno";
import type { Item, Rotulos, Valores } from "../../lib/dados";
import { moedaCurta, moedaExtenso, pct } from "../../lib/formato";
import "../explorer/explorer.css";
import "./explorer-emendas.css";

type Dim = "autoria" | "tipo" | "autor" | "uf" | "mun" | "grupo" | "favorecido" | "area";
interface Filtro { dim: Dim; cod: string }
/** vista null: automática (mapa, ou lista quando há muitos itens). */
interface Estado { ano: number; filtros: Filtro[]; por: Dim | null; vista: "mapa" | "lista" | null }
interface Props { parquet: string; ano: number; anos: number[] }

const UF_NOME: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo",
  GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul", MT: "Mato Grosso", PA: "Pará", PB: "Paraíba",
  PE: "Pernambuco", PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima",
  RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins",
};
const UF_CODIGO: Record<string, string> = {
  RO: "11", AC: "12", AM: "13", RR: "14", PA: "15", AP: "16", TO: "17", MA: "21", PI: "22", CE: "23", RN: "24", PB: "25", PE: "26",
  AL: "27", SE: "28", BA: "29", MG: "31", ES: "32", RJ: "33", SP: "35", PR: "41", SC: "42", RS: "43", MS: "50", MT: "51", GO: "52", DF: "53",
};
const AUTORIA: Record<string, string> = { parlamentares: "Deputados e senadores", bancadas: "Bancadas estaduais", comissoes: "Comissões do Congresso", relator: "Relator-geral do orçamento" };
const TIPO: Record<string, string> = { Individual: "Individuais", Pix: "Emendas Pix", Bancada: "De bancada", "Comissão": "De comissão", Relator: "De relator" };
const GRUPO: Record<string, string> = {
  "Prefeitura": "Prefeituras", "Governo estadual": "Governos estaduais", "Entidade sem fins lucrativos": "Entidades sem fins lucrativos",
  "Empresa": "Empresas", "Outros órgãos públicos": "Outros órgãos públicos",
};
const AREA: Record<string, string> = { "Encargos especiais": "Sem área definida (emendas Pix)", "Múltiplo": "Várias áreas", "Desporto e lazer": "Esporte e lazer" };
const pequenas = new Set(["de", "da", "do", "das", "dos", "e", "em", "a", "o"]);
const titulo = (s: string) => (s && s === s.toUpperCase() && /[A-Z]{3}/.test(s)
  ? s.toLowerCase().split(/\s+/).map((p, i) => (i > 0 && pequenas.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1))).join(" ") : s);

/** Cada dimensão: o rótulo, a expressão SQL do código e, quando o nome não sai de um dicionário, a do nome. */
const DIMS: Record<Dim, { aba: string; rotulo: string; cod: string; nome?: string; dic?: Record<string, string>; fmt?: (s: string) => string }> = {
  autoria: { aba: "Quem manda", rotulo: "Quem manda", dic: AUTORIA,
    cod: "CASE WHEN tipo IN ('Individual', 'Pix') THEN 'parlamentares' WHEN tipo = 'Bancada' THEN 'bancadas' WHEN tipo = 'Comissão' THEN 'comissoes' ELSE 'relator' END" },
  autor: { aba: "Quem mandou", rotulo: "Quem mandou", cod: "autor" },
  tipo: { aba: "Tipo de emenda", rotulo: "Tipo de emenda", cod: "tipo", dic: TIPO },
  uf: { aba: "Estado", rotulo: "Estado", cod: "coalesce(nullif(uf, ''), '—')", dic: { ...UF_NOME, "—": "Sem estado" } },
  mun: { aba: "Cidade", rotulo: "Cidade", cod: "coalesce(nullif(ibge, ''), '—')", nome: "CASE WHEN ibge <> '' THEN municipio || ' (' || uf || ')' ELSE 'Sem cidade' END" },
  grupo: { aba: "Tipo de recebedor", rotulo: "Tipo de recebedor", cod: "grupo", dic: GRUPO },
  favorecido: { aba: "Quem recebeu", rotulo: "Quem recebeu", cod: "coalesce(nullif(codigo, ''), favorecido)", nome: "favorecido", fmt: titulo },
  area: { aba: "Área", rotulo: "Área", cod: "coalesce(nullif(area, ''), 'Sem área')", fmt: (s) => AREA[s] ?? s },
};
const ORDEM: Dim[] = ["autoria", "autor", "tipo", "uf", "mun", "grupo", "favorecido", "area"];
/** Depois de escolher algo numa dimensão, a próxima mais útil. */
const SUGESTAO: Record<Dim, Dim[]> = {
  autoria: ["autor"], tipo: ["autor"], autor: ["mun", "uf", "favorecido"], uf: ["mun", "autor"], mun: ["favorecido", "autor"],
  grupo: ["favorecido", "autor"], favorecido: ["autor", "area"], area: ["autor", "mun"],
};
const ehDim = (s: string | null): s is Dim => !!s && s in DIMS;
const livres = (f: Filtro[]) => ORDEM.filter((d) => !f.some((x) => x.dim === d));
const proxima = (f: Filtro[]): Dim | null => {
  const l = livres(f);
  const ultima = f.at(-1)?.dim;
  return (ultima ? SUGESTAO[ultima] : ["autoria" as Dim]).find((d) => l.includes(d)) ?? l[0] ?? null;
};
const ROTULOS: Rotulos = { atualizado: "", empenhado: null, realizado: "Pago", taxa: "", colTrilho: "Pago", colTaxa: "", codigo: false, soRealizado: true };
const valores = (v: number): Valores => ({ inicial: 0, atualizado: 0, empenhado: 0, realizado: v });
const MAX_MAPA = 30;
const sem = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// ----- O DuckDB: carregado uma vez, na primeira consulta. -----
let conexao: Promise<any> | null = null;
function conectar(parquet: string) {
  conexao ??= (async () => {
    const endereco = "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";   // o mesmo da busca de /emendas
    const duckdb: any = await import(/* @vite-ignore */ endereco);
    const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
    const url = URL.createObjectURL(new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }));
    const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), new Worker(url));
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(url);
    const c = await db.connect();
    await c.query(`CREATE VIEW p AS SELECT * FROM read_parquet('${parquet}')`);
    return c;
  })();
  conexao.catch(() => (conexao = null));
  return conexao;
}
async function consulta(parquet: string, sql: string, v: unknown[] = []) {
  const c = await conectar(parquet);
  const st = await c.prepare(sql);
  const r = await st.query(...v);
  await st.close();
  return r.toArray().map((l: any) => l.toJSON());
}

export default function ExplorerEmendas(props: Props) {
  const lerUrl = (): Estado => {
    const p = new URLSearchParams(location.search);
    const ano = Number(p.get("ano"));
    const filtros = (p.get("f") ?? "").split("|").map((x) => [x.slice(0, x.indexOf(":")), x.slice(x.indexOf(":") + 1)])
      .filter(([d, c]) => ehDim(d) && c).map(([d, c]) => ({ dim: d as Dim, cod: c }));
    const por = p.get("por");
    return {
      ano: props.anos.includes(ano) ? ano : props.ano, filtros,
      por: ehDim(por) && !filtros.some((f) => f.dim === por) ? por : proxima(filtros),
      vista: p.get("vista") === "lista" ? "lista" : p.get("vista") === "mapa" ? "mapa" : null,
    };
  };
  const [estado, setEstado] = createSignal<Estado>(lerUrl());
  const mudar = (parcial: Partial<Estado>, push = false) => {
    const e = { ...estado(), ...parcial };
    setEstado(e);
    const p = new URLSearchParams(location.search);
    for (const k of ["ano", "f", "por", "vista"]) p.delete(k);
    if (e.ano !== props.ano) p.set("ano", String(e.ano));
    if (e.filtros.length) p.set("f", e.filtros.map((f) => `${f.dim}:${f.cod}`).join("|"));
    if (e.por && e.por !== proxima(e.filtros)) p.set("por", e.por);
    if (e.vista) p.set("vista", e.vista);
    const url = `${location.pathname}${p.size ? `?${p}` : ""}${location.hash}`;
    if (push) history.pushState(null, "", url); else history.replaceState(null, "", url);
  };
  onMount(() => {
    const voltar = () => setEstado(lerUrl());
    addEventListener("popstate", voltar);
    onCleanup(() => removeEventListener("popstate", voltar));
  });

  const [itens, setItens] = createSignal<Item[] | null>(null);
  const [total, setTotal] = createSignal(0);
  const [totalAno, setTotalAno] = createSignal(0);
  const [serie, setSerie] = createSignal<Ponto[] | null>(null);
  const [nomes, setNomes] = createSignal<Record<string, string>>({});
  const [erro, setErro] = createSignal("");
  const [carregando, setCarregando] = createSignal(true);
  const [primeira, setPrimeira] = createSignal(true);
  const [busca, setBusca] = createSignal("");

  const onde = (f: Filtro[]) => ({ sql: f.map((x) => `${DIMS[x.dim].cod} = ?`), v: f.map((x) => x.cod) });
  const nomeDe = (d: Dim, cod: string, nomeSql?: string) => DIMS[d].dic?.[cod] ?? DIMS[d].fmt?.(nomeSql ?? cod) ?? nomeSql ?? cod;

  // Cada mudança de ano, filtro ou divisão refaz as consultas; uma consulta velha que chega tarde é jogada fora.
  let vez = 0;
  // Só refaz quando o que se pergunta muda (trocar mapa por lista, não).
  const pergunta = createMemo(() => JSON.stringify([estado().ano, estado().filtros, estado().por]));
  createEffect(on(pergunta, async () => {
    const { ano, filtros, por } = estado();
    const minha = ++vez;
    setCarregando(true); setErro(""); setBusca("");
    try {
      const w = onde(filtros);
      const where = (extra: string[]) => { const t = [...extra, ...w.sql]; return t.length ? `WHERE ${t.join(" AND ")}` : ""; };
      const d = por ? DIMS[por] : null;
      const lista = d ? await consulta(props.parquet,
        `SELECT ${d.cod} AS cod, ${d.nome ? `mode(${d.nome})` : "NULL"} AS nome, sum(valor) AS v FROM p ${where(["ano = ?"])} GROUP BY 1 HAVING sum(valor) > 0`, [ano, ...w.v]) : [];
      const [t] = await consulta(props.parquet, `SELECT coalesce(sum(valor), 0) AS v FROM p ${where(["ano = ?"])}`, [ano, ...w.v]);
      const [tAno] = await consulta(props.parquet, `SELECT coalesce(sum(valor), 0) AS v FROM p WHERE ano = ?`, [ano]);
      const s = await consulta(props.parquet, `SELECT ano, sum(valor) AS v FROM p ${where([`ano >= ${props.anos[0]}`])} GROUP BY ano ORDER BY ano`, w.v);
      const n: Record<string, string> = {};
      for (const f of filtros) {
        const dd = DIMS[f.dim];
        if (dd.nome) { const [x] = await consulta(props.parquet, `SELECT mode(${dd.nome}) AS nome FROM p WHERE ${dd.cod} = ?`, [f.cod]); n[`${f.dim}:${f.cod}`] = nomeDe(f.dim, f.cod, x?.nome); }
        else n[`${f.dim}:${f.cod}`] = nomeDe(f.dim, f.cod);
      }
      if (minha !== vez) return;
      setItens(por ? lista.map((x: any) => ({ codigo: String(x.cod), nome: nomeDe(por, String(x.cod), x.nome ?? undefined), valores: valores(x.v) })) : []);
      setTotal(t.v); setTotalAno(tAno.v); setNomes(n);
      setSerie(s.map((x: any) => ({ ano: x.ano, valores: valores(x.v) })));
    } catch (e: any) {
      if (minha === vez) setErro(String(e?.message ?? e));
    } finally {
      if (minha === vez) { setCarregando(false); setPrimeira(false); }
    }
  }));

  const trilha = () => estado().filtros.map((f, i) => ({ ...f, nome: nomes()[`${f.dim}:${f.cod}`] ?? "…", filtros: estado().filtros.slice(0, i + 1) }));
  const ultimo = () => trilha().at(-1);
  const irPara = (filtros: Filtro[]) => mudar({ filtros, por: proxima(filtros), vista: null }, true);
  const podeDescer = () => livres(estado().filtros).length > 1;
  const descer = (it: Item) => {
    const e = estado(); if (e.por) irPara([...e.filtros, { dim: e.por, cod: it.codigo }]);
  };
  const filtrados = createMemo(() => {
    const t = sem(busca().trim());
    const l = itens() ?? [];
    return t ? l.filter((i) => sem(i.nome).includes(t)) : l;
  });
  /** No mapa, uma lista longa mostra só os maiores (o resto vira poeira); por isso ela abre como lista. */
  const noMapa = createMemo(() => [...filtrados()].sort((a, b) => b.valores.realizado - a.valores.realizado).slice(0, MAX_MAPA));
  const vista = () => estado().vista ?? ((itens()?.length ?? 0) > MAX_MAPA ? "lista" : "mapa");
  const subir = () => irPara(estado().filtros.slice(0, -1));
  const pai = () => (trilha().length > 1 ? trilha().at(-2)!.nome : `todas as emendas de ${estado().ano}`);
  /** O caminho para as emendas uma a uma, no explorador de busca. */
  const detalhe = () => {
    const u = ultimo(); const a = estado().ano;
    if (!u) return null;
    if (u.dim === "autor") return { href: `/emendas/buscar?autor=${encodeURIComponent(u.cod)}&ano=${a}`, texto: "Ver as emendas uma a uma: para onde, para quem e o plano das Pix" };
    if (u.dim === "mun" && u.cod !== "—") return { href: `/emendas/buscar?ente=${u.cod}&ano=${a}`, texto: "Ver quem recebeu na cidade, emenda por emenda" };
    if (u.dim === "uf" && UF_CODIGO[u.cod]) return { href: `/emendas/buscar?ente=${UF_CODIGO[u.cod]}&ano=${a}`, texto: "Ver quem recebeu no estado, emenda por emenda" };
    if (u.dim === "favorecido" && /^\d{14}$/.test(u.cod)) return { href: `/emendas/buscar?entidade=${u.cod}`, texto: "Ver todos os anos e o que foi feito" };
    return null;
  };
  const baixarCsv = () => {
    const d = estado().por; if (!d) return;
    const cel = (x: string) => (/[";\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x);
    const csv = "﻿" + [["codigo", DIMS[d].rotulo.toLowerCase(), "pago"].join(";"), ...(itens() ?? []).sort((a, b) => b.valores.realizado - a.valores.realizado)
      .map((i) => [i.codigo, cel(i.nome), String(Math.round(i.valores.realizado))].join(";"))].join("\n");
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" })), download: `emendas-${estado().ano}-${d}.csv` });
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const anoCorrente = new Date().getFullYear();

  return (
    <div class="exp exp-emendas">
      <div class="exp-barra">
        <nav aria-label="Caminho" class="exp-caminho">
          <Show when={trilha().length > 0} fallback={<span class="forte">Emendas {estado().ano}</span>}>
            <button type="button" class="link" onClick={() => irPara([])}>Emendas {estado().ano}</button>
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
            <select onChange={(e) => mudar({ ano: Number(e.currentTarget.value) })}>
              <For each={[...props.anos].reverse()}>{(a) => <option value={a} selected={a === estado().ano}>{a}{a === anoCorrente ? " (até agora)" : ""}</option>}</For>
            </select>
          </label>
        </div>
      </div>

      <Show when={erro()}><p class="exp-erro">Não foi possível consultar as emendas agora ({erro()}). Tente de novo em instantes.</p></Show>

      <section class="exp-topo">
        <div class="exp-titulo">
          <Show when={ultimo()}><button type="button" class="link exp-voltar" onClick={subir}>← Voltar a {pai()}</button></Show>
          <span class="sobretitulo">{ultimo() ? DIMS[ultimo()!.dim].rotulo : "Emendas parlamentares pagas"}</span>
          <h1>{ultimo()?.nome ?? `Todas as emendas de ${estado().ano}`}</h1>
          <Show when={!primeira()}>
            <p class="exp-lede">
              <Show when={ultimo()} fallback={<>Foram pagos <strong class="marca">{moedaExtenso(total())}</strong> em emendas em {estado().ano}{estado().ano === anoCorrente ? ", até agora" : ""}.</>}>
                <strong class="marca">{moedaExtenso(total())}</strong> pagos em {estado().ano}, {pct(total() / Math.max(1, totalAno()))} de todas as emendas do ano.
              </Show>
            </p>
            <Show when={detalhe()}>{(d) => <p class="exp-lede"><a href={d().href}><strong>{d().texto} →</strong></a></p>}</Show>
          </Show>
        </div>
        <figure class="exp-serie">
          <figcaption>Pago por ano{ultimo() ? `: ${ultimo()!.nome}` : ""}</figcaption>
          <BarrasAno serie={serie()} metrica="realizado" anoSelecionado={estado().ano} anoCorrente={anoCorrente} altura={120} rotulos="extremos"
            rotuloMetrica="Pago" rotuloCorrente="até agora" onAno={(a) => mudar({ ano: a }, true)} />
        </figure>
      </section>

      <div class="exp-abas">
        <Show when={ultimo()}><button type="button" class="exp-subir" onClick={subir} title={`Voltar a ${pai()}`}>← Voltar um nível</button></Show>
        <span class="muted">Dividir por</span>
        <div class="exp-abas-dims" role="tablist" aria-label="Dividir por">
          <For each={livres(estado().filtros)}>
            {(d) => <button type="button" role="tab" aria-selected={d === estado().por} onClick={() => mudar({ por: d })}>{DIMS[d].aba}</button>}
          </For>
        </div>
        <span class="exp-abas-espaco" />
        <div class="exp-vistas">
          <button type="button" aria-pressed={vista() === "mapa"} onClick={() => mudar({ vista: "mapa" })}>Mapa</button>
          <span aria-hidden="true">|</span>
          <button type="button" aria-pressed={vista() === "lista"} onClick={() => mudar({ vista: "lista" })}>Lista</button>
          <span aria-hidden="true">|</span>
          <button type="button" disabled={!itens()?.length} onClick={baixarCsv}>Baixar CSV</button>
        </div>
      </div>

      <Show when={(itens()?.length ?? 0) > 12}>
        <label class="exp-filtrar">
          <span>Procurar na lista de {itens()!.length.toLocaleString("pt-BR")}</span>
          <input type="search" value={busca()} onInput={(e) => { setBusca(e.currentTarget.value); if (e.currentTarget.value) mudar({ vista: "lista" }); }}
            placeholder={estado().por === "autor" ? "Ex.: o nome de um deputado ou de uma comissão" : estado().por === "mun" ? "Ex.: o nome da sua cidade" : "Digite um nome"} />
        </label>
      </Show>

      <div class="exp-resultado" classList={{ "exp-ocupado": carregando() && !primeira() }}>
        <Show when={!primeira()} fallback={
          <div class="exp-carregando" aria-busy="true"><p><strong>Preparando o motor de consulta…</strong></p><p class="muted">Na primeira vez leva alguns segundos; depois cada clique é rápido.</p></div>
        }>
          <Show when={filtrados().length > 0} fallback={
            <div class="exp-carregando"><p>{busca() ? `Nada com “${busca()}” nesta lista.` : `Nenhuma emenda paga neste caminho em ${estado().ano}.`}</p>
              <Show when={!busca()}><button type="button" class="botao" onClick={() => irPara([])}>Voltar ao início</button></Show></div>
          }>
            <Show when={vista() === "mapa" && !busca()} fallback={
              <Tabela itens={filtrados()} metrica="realizado" total={Math.max(1, total())} rotulos={ROTULOS}
                rotuloNome={estado().por ? DIMS[estado().por!].rotulo : "Nome"} podeDescer={podeDescer()} onEscolher={descer} />
            }>
              <Show when={filtrados().length > MAX_MAPA}>
                <p class="exp-aviso">O mapa mostra os {MAX_MAPA} maiores de {filtrados().length.toLocaleString("pt-BR")}. <button type="button" class="link" onClick={() => mudar({ vista: "lista" })}>Ver a lista inteira</button></p>
              </Show>
              <Treemap itens={noMapa()} metrica="realizado" total={Math.max(1, total())} rotulos={ROTULOS} podeDescer={podeDescer()} onEscolher={descer} />
            </Show>
          </Show>
        </Show>
      </div>

      <p class="exp-nota">
        <Show when={vista() === "mapa"}>Cada bloco é proporcional ao valor pago; clique para detalhar. </Show>
        Valores pagos no ano, inclusive emendas indicadas em anos anteriores, pelo lugar de quem recebeu. {anoCorrente}: até agora.
        Fonte: Controladoria-Geral da União, Portal da Transparência.
      </p>
    </div>
  );
}
