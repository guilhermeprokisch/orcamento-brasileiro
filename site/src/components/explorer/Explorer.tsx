import { createMemo, createResource, createSignal, For, lazy, onCleanup, onMount, Show } from "solid-js";
import Treemap from "./Treemap";
import Tabela from "./Tabela";
import BarrasAno, { type Ponto } from "./BarrasAno";
import Degraus, { deQuem, Voltar, type Degrau } from "./Degraus";
import FaixaTipo, { AvisoEmendas } from "./FaixaTipo";
import {
  agrupar, carregarAno, carregarResumo, DIMS, dimsDisponiveis, escalar, METRICAS, proximaSugerida,
  ROTULO_DIM, taxaRealizacao, temTipo, TIPOS_DESPESA, totaisDaTrilha, type Dim, type Filtro, type Item, type Metrica,
} from "../../lib/dados";
import { moedaCurta, moedaExtenso, pct } from "../../lib/formato";
import "./explorer.css";

/** Mapa de blocos, lista ou cascata (a tela livre em Canvas, carregada só quando é escolhida). */
type Vista = "mapa" | "lista" | "cascata";
const CascataVista = lazy(() => import("./CascataVista"));

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

/** Nos degraus, de quem é a fatia do passo seguinte: "44% do programa". */
const DE: Record<Dim, string> = {
  orgao: "do órgão", funcao: "da área", subfuncao: "da subárea", uo: "da unidade",
  programa: "do programa", acao: "da ação", gnd: "do tipo de gasto", tipo: "deste tipo",
};

/** Ordem das abas, como no mock: as mais usadas primeiro. */
const ORDEM_ABAS: Dim[] = ["orgao", "tipo", "programa", "uo", "acao", "gnd", "funcao", "subfuncao"];

/** O nome de um tipo de despesa ("Obrigatória"), para quando o arquivo do ano não traz os nomes. */
const nomeDoTipo = (f: Filtro): string | undefined =>
  f.dim === "tipo" ? TIPOS_DESPESA.find((t) => t.cod === f.cod)?.nome : undefined;

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
    vista: p.get("vista") === "lista" || p.get("vista") === "tabela" ? "lista" : p.get("vista") === "cascata" ? "cascata" : "mapa",
    real: p.get("ipca") === "1",
  };
}

function montarUrl(e: Estado): string {
  const p = new URLSearchParams();
  if (e.ano) p.set("ano", String(e.ano));
  if (e.metrica !== "atualizado") p.set("metrica", e.metrica);
  if (e.filtros.length) p.set("f", e.filtros.map((f) => `${f.dim}:${f.cod}`).join(","));
  if (e.por) p.set("por", e.por);
  if (e.semRefin) p.set("refin", "0");
  if (e.vista !== "mapa") p.set("vista", e.vista);
  if (e.real) p.set("ipca", "1");
  return `${location.pathname}?${p.toString().replaceAll("%3A", ":").replaceAll("%2C", ",")}`;
}

function escreverUrl(e: Estado, push: boolean) {
  const url = montarUrl(e);
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

  // Um ano sem a coluna "tipo" (gerado sem o SIOP) não sabe filtrar nem dividir por obrigatório ou não: nele, o
  // filtro de tipo fica de fora das contas (com um aviso) e volta a valer num ano que tenha a coluna.
  const semTipo = () => !!doc() && !temTipo(doc());
  const vale = createMemo<Estado>(() => {
    const e = estado();
    if (!semTipo()) return e;
    const filtros = e.filtros.filter((f) => f.dim !== "tipo");
    const sugerida = proximaSugerida(filtros);
    return { ...e, filtros, por: e.por === "tipo" ? (sugerida === "tipo" ? null : sugerida) : e.por };
  });
  const tipoDeFora = () => (semTipo() ? estado().filtros.find((f) => f.dim === "tipo") : undefined);
  const dimsAqui = () => dimsDisponiveis(vale().filtros).filter((d) => d !== "tipo" || temTipo(doc()));

  // Série histórica (todos os anos, carregados uma vez).
  const anosLista = () => resumo()?.anos.map((a) => a.ano) ?? [];
  const [todos] = createResource(
    () => (anosLista().length ? anosLista().join(",") : false),
    (chave: string) => Promise.all(chave.split(",").map(Number).map(carregarAno)),
  );
  const serie = createMemo<Ponto[] | null>(() => {
    const ds = todos();
    if (!ds) return null;
    const e = vale();
    // Com o filtro de tipo, os anos sem a coluna ficam fora da série (não dá para saber o valor deles).
    const comTipo = e.filtros.some((f) => f.dim === "tipo");
    return ds
      .filter((d) => !comTipo || temTipo(d))
      .map((d) => ({ ano: d.ano, valores: escalar(agrupar(d, e.filtros, null, e.semRefin).total, fatorDe(d.ano)) }))
      .sort((a, b) => a.ano - b.ano);
  });

  const grupo = createMemo(() => {
    const d = doc();
    if (!d) return null;
    const e = vale();
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
    const e = vale();
    const totais = totaisDaTrilha(d, e.filtros, e.metrica, e.semRefin);
    return e.filtros.map((f, i) => ({
      ...f,
      nome: d.dims[f.dim]?.[f.cod] ?? nomeDoTipo(f) ?? f.cod,
      total: totais[i] * fatorDe(ano()),
      filtros: e.filtros.slice(0, i + 1),
    }));
  });
  const ultimo = () => trilha().at(-1);

  const descer = (item: Item) => {
    const e = vale();
    if (!e.por) return;
    const filtros = [...e.filtros, { dim: e.por, cod: item.codigo }];
    mudar({ filtros, por: proximaSugerida(filtros) }, true);
  };
  const irPara = (filtros: Filtro[]) => mudar({ filtros, por: proximaSugerida(filtros) }, true);
  const podeDescer = () => dimsAqui().length > 1;
  // Voltar um nível: o passo anterior da trilha, ou o orçamento inteiro.
  const pai = () => (trilha().length > 1 ? trilha().at(-2)!.nome : `todo o orçamento de ${ano() ?? ""}`);
  const subir = () => irPara(vale().filtros.slice(0, -1));

  // Os degraus: o orçamento inteiro e cada passo da trilha, com o valor e a fatia no passo anterior.
  const degraus = createMemo<Degrau[]>(() => {
    const d = doc();
    const e = estado();
    const urlDe = (filtros: Filtro[]) => montarUrl({ ...e, ano: ano(), filtros, por: proximaSugerida(filtros) });
    const raiz = d ? agrupar(d, [], null, e.semRefin).total[e.metrica] * fatorDe(ano()) : 0;
    const passos: Degrau[] = [{
      tipo: `Orçamento ${ano() ?? ""}`, nome: "Todo o orçamento", valor: d ? moedaCurta(raiz) : undefined,
      href: urlDe([]), ir: () => irPara([]),
    }];
    let antes = raiz;
    trilha().forEach((t, i) => {
      const anterior = trilha()[i - 1];
      passos.push({
        tipo: ABA[t.dim], nome: t.nome, valor: moedaCurta(t.total),
        fatia: antes > 0 ? Math.min(1, Math.max(0, t.total / antes)) : null,
        de: anterior ? deQuem(anterior.nome, DE[anterior.dim]) : "do orçamento",
        href: urlDe(t.filtros), ir: () => irPara(t.filtros),
      });
      antes = t.total;
    });
    return passos;
  });

  const legendaSerie = () =>
    estado().real && ipca() ? `Dotação por ano, em reais de ${ipca()!.base}` : "Dotação por ano, em valores nominais";

  return (
    <div class="exp">
      {/* Em cima, os controles que mudam a ficha toda; os degraus ficam junto das vistas, mais abaixo. */}
      <div class="exp-barra-topo">
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

      <Show when={tipoDeFora()}>
        {(f) => (
          <p class="exp-aviso" role="status">
            Os dados de {ano()} não dizem se cada gasto é obrigatório ou não. Por isso o filtro “{nomeDoTipo(f()) ?? f().cod}”
            ficou de fora: os números abaixo são de todo o gasto.{" "}
            <button type="button" class="link" onClick={() => mudar({ filtros: vale().filtros, por: vale().por })}>Tirar o filtro</button>
          </p>
        )}
      </Show>

      <Show when={temTipo(doc()) && !estado().filtros.some((f) => f.dim === "tipo")}>
        <FaixaTipo doc={doc()!} ano={ano()!} filtros={estado().filtros} metrica={estado().metrica} semRefin={estado().semRefin}
          fator={fatorDe(ano())} onSemRefin={() => mudar({ semRefin: true })}
          onEscolher={(cod) => {
            const filtros = [...estado().filtros, { dim: "tipo" as Dim, cod }];
            const por = estado().por;
            mudar({ filtros, por: por && por !== "tipo" ? por : proximaSugerida(filtros) }, true);
          }} />
      </Show>

      <Show when={ano() && vale().filtros.some((f) => f.dim === "tipo" && f.cod === "eme")}>
        <AvisoEmendas ano={ano()!} />
      </Show>

      {/* Os degraus logo acima das vistas (mapa, lista e cascata): clicar no gráfico muda o degrau sem rolar a página. */}
      <div class="exp-degraus">
        <Degraus passos={degraus()} dicaInicio={estado().vista === "cascata" ? "Clique numa caixa da cascata para abrir o que tem dentro" : "Clique num bloco do mapa para descer um nível"} />
      </div>

      <div class="exp-abas">
        <Show when={ultimo()}>
          <Voltar para={pai()} onClick={subir} />
        </Show>
        <Show when={estado().vista !== "cascata"} fallback={
          <span class="muted exp-cascata-niveis">Órgão › unidade › programa › ação › tipo de gasto, com vários galhos abertos</span>
        }>
          <span class="muted">Dividir por</span>
          <div class="exp-abas-dims" role="tablist" aria-label="Dividir por">
            <For each={ORDEM_ABAS.filter((d) => dimsAqui().includes(d))}>
              {(d) => (
                <button type="button" role="tab" aria-selected={d === vale().por} onClick={() => mudar({ por: d })}>
                  {ABA[d]}
                </button>
              )}
            </For>
          </div>
        </Show>
        <span class="exp-abas-espaco" />
        <div class="exp-vistas">
          <button type="button" aria-pressed={estado().vista === "mapa"} onClick={() => mudar({ vista: "mapa" })}>Mapa</button>
          <span aria-hidden="true">|</span>
          <button type="button" aria-pressed={estado().vista === "lista"} onClick={() => mudar({ vista: "lista" })}>Lista</button>
          <span aria-hidden="true">|</span>
          <button type="button" aria-pressed={estado().vista === "cascata"} onClick={() => mudar({ vista: "cascata" })}
            title="Uma tela livre para abrir galho por galho, do total às ações">Cascata</button>
          <span aria-hidden="true">|</span>
          <button type="button" disabled={!grupo() || !vale().por}
            onClick={() => baixarCsv(grupo()!.itens, vale().por!, ano()!, estado().real)}>Baixar CSV</button>
        </div>
      </div>

      <Show when={estado().vista === "cascata" && doc() && ano()}>
        <CascataVista doc={doc()!} ano={ano()!} metrica={estado().metrica} semRefin={estado().semRefin} fator={fatorDe(ano())}
          legendaAcima={temTipo(doc()) && !estado().filtros.some((f) => f.dim === "tipo")}
          filtros={vale().filtros}
          onCaminho={(filtros) => mudar({ filtros, por: proximaSugerida(filtros) })}
          onVerMapa={(filtros) => mudar({ filtros, por: proximaSugerida(filtros), vista: "mapa" }, true)} />
      </Show>

      <Show when={estado().vista !== "cascata" && grupo()} fallback={<Show when={estado().vista !== "cascata"}><div class="exp-carregando" aria-busy="true">Carregando…</div></Show>}>
        <Show when={(grupo()?.itens.length ?? 0) > 0} fallback={
          <div class="exp-carregando">
            <p>Este caminho não tem valores em {ano()}.</p>
            <button type="button" class="botao" onClick={() => irPara([])}>Voltar ao início</button>
          </div>
        }>
          <Show when={estado().vista === "mapa"} fallback={
            <Tabela itens={grupo()!.itens} metrica={estado().metrica} total={Math.max(1, total())}
              rotuloNome={vale().por ? ROTULO_DIM[vale().por!] : "Nome"} podeDescer={podeDescer()} onEscolher={descer} />
          }>
            <Treemap itens={grupo()!.itens} metrica={estado().metrica} total={Math.max(1, total())}
              podeDescer={podeDescer()} onEscolher={descer} corDe={vale().por === "tipo" ? corDoTipo : undefined} />
          </Show>
        </Show>
      </Show>

      <p class="exp-nota">
        <Show when={estado().vista === "mapa"}>Cada bloco é proporcional à dotação; clique para descer um nível. </Show>
        <Show when={estado().vista === "cascata"}>Na cascata, em cada nível aparecem os oito maiores e os outros ficam em “mais N”; cada caixa é proporcional ao valor dentro do seu nível (“Tamanho real” põe todas na escala do total). </Show>
        * {anoCorrente} ainda em execução. Pago = realizado ÷ dotação atualizada.
        <Show when={!estado().semRefin && trilha().length === 0}> Os totais incluem o refinanciamento da dívida pública.</Show>
      </p>
    </div>
  );
}
