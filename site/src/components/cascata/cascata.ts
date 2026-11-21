/**
 * Protótipo da cascata do gasto (/prototipo-cascata): três formas de ver por onde o dinheiro passa, nível a nível.
 *   ?v=1  cascata de foco: uma coluna por nível, as antigas encolhem e deixam o fio do caminho
 *   ?v=2  degraus (icicle): uma faixa por nível, cada uma é o zoom do pedaço escolhido na de cima
 *   ?v=3  três colunas que deslizam: pai, atual e filhos; ao clicar, tudo anda uma coluna
 *   ?onde=uniao | joao-pessoa      ?c=códigos do caminho, separados por "~"      ?cor=tamanho
 * Regra de ouro: não mostrar tudo. Em cada nível só os maiores; o resto vira "outros", que abre a lista.
 */
import { moedaCurta, pct } from "../../lib/formato";
import { OUTRAS, RAMPA } from "../../lib/cores";
import {
  caminhoAte, catPrincipal, filhos, fonteJoaoPessoa, fonteUniao, formatarCnpj, temFilhos, visiveis,
  type Fonte, type No, type Visiveis,
} from "./dados";

type Versao = 1 | 2 | 3;
type ModoCor = "tipo" | "tamanho";

interface Estado {
  v: Versao;
  onde: "uniao" | "joao-pessoa";
  cor: ModoCor;
  caminho: No[];
  /** "outros" aberto no painel (formas 1 e 2) ou na coluna (forma 3). */
  outros: No | null;
}

const VERDE = "#0e6b3b";
const NS = "http://www.w3.org/2000/svg";

let F: Fonte;
let E: Estado;
let raizEl: HTMLElement;
let largura = 0;
/** O que foi clicado por último, para a animação: "desce" (mais fundo), "sobe" ou "lado". */
let movimento: { tipo: "desce" | "sobe" | "lado" } | null = null;

// ——— utilidades ———

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const corta = (s: string, n: number) => (s.length <= n ? s : `${s.slice(0, Math.max(1, n - 1)).trimEnd()}…`);
const parte = (n: No) => (n.pai && n.pai.valor > 0 ? n.valor / n.pai.valor : 1);
const pctCurto = (v: number) => (v >= 0.995 ? "100%" : v >= 0.1 ? `${Math.round(v * 100)}%` : v >= 0.001 ? pct(v) : "<0,1%");
const plural = (nivel: string) => F.plural[nivel] ?? nivel.toLowerCase();
const celular = () => largura < 640;
const K = () => (celular() ? 6 : 7);
const vis = (n: No, escolhido?: No | null): Visiveis => visiveis(n, K(), F.plural, escolhido);
const lista = (v: Visiveis) => (v.outros ? [...v.itens, v.outros] : v.itens);
const atual = () => E.caminho[E.caminho.length - 1];
const usaTipo = () => E.cor === "tipo" && F.cats.length > 1;

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number | undefined>, pai?: Element) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined) e.setAttribute(k, String(v));
  pai?.appendChild(e);
  return e;
}

/** Afasta rótulos para não se encostarem (y desejados → y possíveis), dentro de [min, max]. */
function afastar(ys: number[], dist: number, min: number, max: number): number[] {
  const ordem = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  const out = ordem.map((o) => o.y);
  for (let i = 0; i < out.length; i++) out[i] = Math.max(out[i], i ? out[i - 1] + dist : min);
  for (let i = out.length - 1; i >= 0; i--) out[i] = Math.min(out[i], i < out.length - 1 ? out[i + 1] - dist : max);
  for (let i = 0; i < out.length; i++) out[i] = Math.max(out[i], i ? out[i - 1] + dist : min);
  const r = new Array(ys.length);
  ordem.forEach((o, j) => (r[o.i] = out[j]));
  return r;
}

/** Cor do pedaço "por tamanho": o caminho em verde, os maiores filhos na rampa, o resto em areia. */
function corTamanho(n: No, rank: number, escolhido: boolean, ativo: boolean): { fundo: string; escuro: boolean } {
  if (n.ehOutros) return { fundo: OUTRAS, escuro: false };
  if (escolhido) return { fundo: VERDE, escuro: true };
  if (!ativo) return { fundo: "#ddd5c3", escuro: false };
  const i = Math.min(rank + 1, RAMPA.length - 1);
  return { fundo: RAMPA[i], escuro: i < 2 };
}

/** Pedaços da mistura por categoria (para pintar uma barra), na ordem das categorias. */
function segmentos(n: No): { cor: string; frac: number }[] {
  const t = n.mix.reduce((s, v) => s + Math.max(0, v), 0) || 1;
  return n.mix.map((v, i) => ({ cor: F.cats[i].cor, frac: Math.max(0, v) / t })).filter((s) => s.frac > 0.002);
}

/** Retângulo pintado: cor única ou, no modo "tipo", a mistura em faixas (vertical: de cima para baixo). */
function pintar(g: Element, x: number, y: number, w: number, h: number, n: No, cor: { fundo: string }, vertical: boolean, apagado = false) {
  if (!usaTipo() || n.ehOutros) {
    el("rect", { x, y, width: Math.max(0.5, w), height: Math.max(0.5, h), fill: cor.fundo, class: n.ehOutros ? "cc-outros" : undefined }, g);
    if (n.ehOutros) el("rect", { x, y, width: Math.max(0.5, w), height: Math.max(0.5, h), fill: "url(#cc-hachura)" }, g);
    return;
  }
  let pos = 0;
  for (const s of segmentos(n)) {
    if (vertical) el("rect", { x, y: y + pos * h, width: Math.max(0.5, w), height: Math.max(0.3, s.frac * h), fill: s.cor, opacity: apagado ? 0.35 : 1 }, g);
    else el("rect", { x: x + pos * w, y, width: Math.max(0.3, s.frac * w), height: Math.max(0.5, h), fill: s.cor, opacity: apagado ? 0.35 : 1 }, g);
    pos += s.frac;
  }
}

/** A faixa que fica na altura `frac` do pedaço (de cima para baixo) é escura? Para escolher a cor do texto. */
function escuroNoMeio(n: No, frac: number): boolean {
  let acc = 0;
  const t = n.mix.reduce((s, v) => s + Math.max(0, v), 0) || 1;
  for (let i = 0; i < n.mix.length; i++) {
    acc += Math.max(0, n.mix[i]) / t;
    if (acc >= frac) return !!F.cats[i].escuro;
  }
  return false;
}

function defs(svg: SVGSVGElement) {
  const d = el("defs", {}, svg);
  const p = el("pattern", { id: "cc-hachura", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, d);
  el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#c3bba7", "stroke-width": 2 }, p);
}

/** Faixa entre um pedaço [y0,y1] em x0 e outro [t0,t1] em x1. */
const fita = (x0: number, y0: number, y1: number, x1: number, t0: number, t1: number) => {
  const xm = (x0 + x1) / 2;
  return `M${x0},${y0}C${xm},${y0} ${xm},${t0} ${x1},${t0}L${x1},${t1}C${xm},${t1} ${xm},${y1} ${x0},${y1}Z`;
};

/** Registro dos alvos clicáveis do desenho atual (data-k → nó). */
let alvos: No[] = [];
const alvo = (n: No) => (alvos.push(n), String(alvos.length - 1));

function clicar(n: No) {
  if (n.ehOutros) {
    E.outros = E.outros === n.pai && E.outros ? null : n.pai;
    movimento = null;
    desenhar();
    if (E.v !== 3 && E.outros) document.getElementById("cc-painel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return;
  }
  const antes = E.caminho.length;
  const novo = caminhoAte(n);
  // Clicar no que já está escolhido volta para ele (fecha os níveis abaixo).
  E.caminho = novo;
  E.outros = null;
  movimento = { tipo: novo.length > antes ? "desce" : novo.length < antes ? "sobe" : "lado" };
  salvarUrl();
  desenhar();
}

function ligarCliques(c: Element) {
  c.querySelectorAll<HTMLElement | SVGElement>("[data-k]").forEach((e) => {
    const ir = (ev: Event) => { ev.preventDefault(); clicar(alvos[Number(e.getAttribute("data-k"))]); };
    e.addEventListener("click", ir);
    e.addEventListener("keydown", (ev) => { const k = (ev as KeyboardEvent).key; if (k === "Enter" || k === " ") ir(ev); });
  });
}

// ——— URL ———

function lerUrl(): Estado {
  const p = new URLSearchParams(location.search);
  const v = Number(p.get("v"));
  return {
    v: (v === 2 || v === 3 ? v : 1) as Versao,
    onde: p.get("onde") === "joao-pessoa" ? "joao-pessoa" : "uniao",
    cor: p.get("cor") === "tamanho" ? "tamanho" : "tipo",
    caminho: [],
    outros: null,
  };
}

function resolverCaminho(raiz: No, codigos: string[]): No[] {
  const c = [raiz];
  for (const cod of codigos) {
    const f = filhos(c[c.length - 1]).find((x) => x.cod === cod);
    if (!f) break;
    c.push(f);
  }
  return c;
}

function urlCom(mud: Partial<{ v: Versao; onde: string; cor: ModoCor; c: string | null }>) {
  const p = new URLSearchParams();
  const v = mud.v ?? E.v, onde = mud.onde ?? E.onde, cor = mud.cor ?? E.cor;
  const c = "c" in mud ? mud.c : E.caminho.slice(1).map((n) => n.cod).join("~");
  if (v !== 1) p.set("v", String(v));
  if (onde !== "uniao") p.set("onde", onde);
  if (cor !== "tipo") p.set("cor", cor);
  if (c) p.set("c", c);
  const q = p.toString().replaceAll("%7E", "~");
  return `${location.pathname}${q ? `?${q}` : ""}`;
}

function salvarUrl() {
  history.replaceState(null, "", urlCom({}));
  atualizarControles();
}

function atualizarControles() {
  document.querySelectorAll<HTMLAnchorElement>("[data-v]").forEach((a) => {
    a.href = urlCom({ v: Number(a.dataset.v) as Versao });
    a.toggleAttribute("aria-current", Number(a.dataset.v) === E.v);
  });
  document.querySelectorAll<HTMLAnchorElement>("[data-onde]").forEach((a) => {
    a.href = urlCom({ onde: a.dataset.onde, c: null });
    a.toggleAttribute("aria-current", a.dataset.onde === E.onde);
  });
  document.querySelectorAll<HTMLButtonElement>("[data-cor]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.cor === E.cor));
    if (b.dataset.cor === "tipo") b.textContent = F?.rotuloCor ?? "Tipo";
  });
}

// ——— cabeçalho comum: frase, legenda de cores e o caminho (degraus) ———

function htmlLegenda() {
  if (!usaTipo()) return "";
  return `<ul class="cc-legenda">${F.cats.filter((c) => c.nome !== "Sem informação").map((c) =>
    `<li><i style="background:${c.cor}"></i>${esc(c.nome)}</li>`).join("")}</ul>`;
}

function htmlDegraus() {
  const cam = E.caminho;
  return `<ol class="cc-degraus" aria-label="O caminho até aqui">${cam.map((n, i) => {
    const ultimo = i === cam.length - 1;
    const fatia = i > 0 ? `<span class="cc-degrau-parte">${pctCurto(parte(n))} ${i === 1 ? "do total" : "do anterior"}</span>` : "";
    return `<li><button type="button" class="cc-degrau" data-k="${alvo(n)}" ${ultimo ? 'aria-current="step"' : ""}>
      <span class="cc-degrau-tipo">${esc(n.nivel)}</span>
      <span class="cc-degrau-nome" title="${esc(n.nome)}">${esc(n.nome)}</span>
      <span class="cc-degrau-valor"><strong>${moedaCurta(n.valor)}</strong> ${fatia}</span>
    </button></li>`;
  }).join("")}</ol>`;
}

/** O painel embaixo do desenho: a lista do "outros", o cartão do último nível, ou a lista do nível atual. */
function htmlPainel(): string {
  const cur = atual();
  if (E.outros) {
    const v = vis(E.outros, E.caminho.find((n) => n.pai === E.outros) ?? null);
    const resto = v.outros?.lista ?? [];
    return `<div class="cc-painel-cab"><h3>${esc(v.outros?.nome ?? "")}</h3>
      <span class="muted">dentro de ${esc(E.outros.nome)} · somam ${moedaCurta(v.outros?.valor ?? 0)}</span>
      <button type="button" class="cc-fechar" data-fechar>Fechar</button></div>
      ${htmlLinhas(resto.slice(0, 80), E.outros)}
      ${resto.length > 80 ? `<p class="muted">e mais ${resto.length - 80}, menores.</p>` : ""}`;
  }
  if (!temFilhos(cur)) return htmlCartao(cur);
  if (E.v === 2 || (E.v === 1 && celular())) {
    const v = vis(cur);
    return `<div class="cc-painel-cab"><h3>${esc(cur.nome)}: ${plural(lista(v)[0]?.nivel ?? "")}</h3></div>${htmlLinhas(lista(v), cur)}`;
  }
  return "";
}

function htmlLinhas(ns: No[], pai: No) {
  return `<ol class="cc-linhas">${ns.map((n) => `<li><button type="button" data-k="${alvo(n)}">
    <span class="cc-l-nome">${esc(n.nome)}</span>
    <span class="cc-l-valor num">${moedaCurta(n.valor)} · ${pctCurto(n.valor / Math.max(1, pai.valor))}</span>
    <span class="cc-l-barra">${htmlBarra(n, n.valor / Math.max(1, pai.valor))}</span>
  </button></li>`).join("")}</ol>`;
}

function htmlBarra(n: No, frac: number) {
  const w = Math.max(0.6, frac * 100);
  if (!usaTipo() || n.ehOutros) return `<i style="width:${w}%;background:${n.ehOutros ? "#c3bba7" : VERDE}"></i>`;
  return `<i style="width:${w}%;display:flex">${segmentos(n).map((s) => `<b style="flex:${s.frac};background:${s.cor}"></b>`).join("")}</i>`;
}

/** O fim do caminho: o que se sabe do último nível. */
function htmlCartao(n: No): string {
  const info = n.info ?? {};
  const linhas: string[] = [];
  let titulo = n.nome;
  let texto = "";
  if (F.chave === "uniao") {
    texto = `Este é o último degrau do orçamento federal: <strong>${esc(n.nome.toLowerCase())}</strong> da ação
      “${esc(n.pai?.nome ?? "")}”. Quem recebeu o dinheiro (a empresa, o contrato) está no Portal da Transparência, nota a nota,
      e ainda não está no site. Para ver a cascata ir até o fornecedor, troque para <a href="${urlCom({ onde: "joao-pessoa", c: null })}">João Pessoa</a>.`;
  } else if (info.pessoas !== undefined) {
    titulo = "Pessoas físicas";
    texto = `Pagamentos a <strong>${info.pessoas.toLocaleString("pt-BR")} pessoas</strong>: servidores pagos um a um, aposentados,
      autônomos, bolsistas e microempreendedores. O site não guarda nem mostra nomes ou CPF, só o total.`;
  } else if (info.resto) {
    texto = `São ${info.resto} credores menores deste tipo de despesa. O protótipo só traz os 40 maiores de cada tipo.`;
  } else if (info.via) {
    texto = `A prefeitura manda o total da folha para a conta <strong>${esc(info.via)}</strong> e o banco paga cada servidor.
      Os servidores não aparecem um a um.`;
  } else {
    const tipo = info.tipoCredor !== undefined ? F.cats[info.tipoCredor]?.nome : "";
    if (tipo) linhas.push(`<dt>Quem é</dt><dd>${esc(tipo === "Fornecedores" ? "Empresa ou entidade (fornecedor)" : tipo)}</dd>`);
    if (info.cnpj) linhas.push(`<dt>CNPJ</dt><dd class="num">${formatarCnpj(info.cnpj)}</dd>`);
    if (info.licitacao) linhas.push(`<dt>Como foi escolhido</dt><dd>${esc(info.licitacao)}</dd>`);
    const ano = info.cnpj ? F.porCnpj?.get(info.cnpj.slice(0, 8)) : undefined;
    if (ano && ano.valor > n.valor * 1.01) {
      linhas.push(`<dt>No ano todo</dt><dd>${moedaCurta(ano.valor)} da prefeitura, em ${ano.areas.size} ${ano.areas.size > 1 ? "áreas" : "área"}</dd>`);
    }
    texto = `Recebeu <strong>${moedaCurta(n.valor)}</strong> neste tipo de despesa${info.empenhos ? `, em ${info.empenhos} ${info.empenhos > 1 ? "empenhos" : "empenho"} (as notas de reserva do dinheiro)` : ""}.`;
  }
  const cam = E.caminho;
  const fio = cam.slice(1).map((x) => esc(x.nome)).join(" › ");
  return `<div class="cc-cartao">
    <span class="sobretitulo">${esc(n.nivel)} · fim do caminho</span>
    <h3>${esc(titulo)}</h3>
    <p class="cc-cartao-valor"><strong class="marca">${moedaCurta(n.valor)}</strong> · ${pctCurto(parte(n))} ${n.pai ? `de ${esc(n.pai.nome)}` : ""}</p>
    <p>${texto}</p>
    ${linhas.length ? `<dl>${linhas.join("")}</dl>` : ""}
    ${F.chave === "joao-pessoa" && info.cnpj && info.tipoCredor === 0 ? `<p><a href="/contratos?q=${encodeURIComponent(n.nome)}">Procurar contratos com esse nome</a></p>` : ""}
    <p class="cc-fio muted">${fio}</p>
  </div>`;
}

// ——— Forma 1: cascata de foco ———

function forma1(host: HTMLElement) {
  const W = largura;
  const mob = celular();
  const cam = E.caminho, cur = atual();
  interface Col { itens: No[]; sel: No | null; pai: No | null }
  const cols: Col[] = [{ itens: [cam[0]], sel: cam[0], pai: null }];
  for (let i = 1; i < cam.length; i++) cols.push({ itens: lista(vis(cam[i - 1], cam[i])), sel: cam[i], pai: cam[i - 1] });
  if (temFilhos(cur)) cols.push({ itens: lista(vis(cur)), sel: null, pai: cur });
  const nc = cols.length;

  const H = mob ? 470 : 560, topo = mob ? 34 : 40, base = 8, alt = H - topo - base;
  const barA = mob ? 10 : 16, barB = mob ? 14 : 22;
  const LA = mob ? 0 : Math.min(280, W * 0.24);
  const LB = mob ? Math.min(205, W * 0.58) : Math.min(360, W * 0.3);
  let passo = mob ? 18 : 54;
  const barC = mob ? 5 : 9;
  const minG = mob ? 48 : 110;
  const nRec = Math.max(0, nc - 2);
  const folga = () => W - nRec * passo - LA - barA - barB - LB;
  if (folga() < minG + 40 && nRec) passo = mob ? 12 : 30;
  let primeiro = 0;
  while (W - (nRec - primeiro) * passo - LA - barA - barB - LB < minG && primeiro < nRec) primeiro++;
  const G = W - (nRec - primeiro) * passo - LA - barA - barB - LB;

  const xCol = (i: number) => {
    if (i < nc - 2) return (i - primeiro) * passo + (primeiro ? 8 : 0);
    const xA = (nRec - primeiro) * passo + (primeiro ? 8 : 0) + LA;
    return i === nc - 2 ? xA : xA + barA + G;
  };
  const largBar = (i: number) => (i < nc - 2 ? barC : i === nc - 2 ? barA : barB);
  // Se só há uma coluna (folha na raiz), desenha como coluna A.
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: "cc-svg cc-f1", role: "group", "aria-label": "Cascata do gasto" });
  defs(svg);
  const gFitas = el("g", { class: "cc-fitas" }, svg);
  const gBarras = el("g", {}, svg);
  const gRot = el("g", { class: "cc-rotulos" }, svg);

  // posições verticais
  const pos = cols.map((c, i) => {
    const vao = i < nc - 2 ? 1.5 : mob ? 2.5 : 3.5;
    const total = c.itens.reduce((s, n) => s + n.valor, 0) || 1;
    const util = alt - vao * (c.itens.length - 1);
    let y = topo;
    return c.itens.map((n) => {
      const h = Math.max(1.2, (n.valor / total) * util);
      const r = { n, y0: y, y1: y + h };
      y += h + vao;
      return r;
    });
  });

  if (primeiro > 0) {
    el("text", { x: 0, y: topo + alt / 2, class: "cc-mais", "text-anchor": "start" }, svg).textContent = "…";
  }

  // fitas: só do pedaço escolhido de cada coluna para a coluna seguinte inteira
  for (let i = Math.max(0, primeiro); i < nc - 1; i++) {
    const sel = cols[i].sel;
    const src = pos[i].find((p) => p.n === sel);
    if (!src) continue;
    const x0 = xCol(i) + largBar(i), x1 = xCol(i + 1);
    const alvo2 = pos[i + 1];
    const tot = alvo2.reduce((s, p) => s + p.n.valor, 0) || 1;
    let acc = 0;
    const ativa = i >= nc - 2;
    alvo2.forEach((p, rank) => {
      const s0 = src.y0 + (acc / tot) * (src.y1 - src.y0);
      acc += p.n.valor;
      const s1 = src.y0 + (acc / tot) * (src.y1 - src.y0);
      const naTrilha = p.n === cols[i + 1].sel;
      let cor = "#c3bba7";
      if (usaTipo() && !p.n.ehOutros) cor = F.cats[catPrincipal(p.n)].cor;
      else if (ativa && !p.n.ehOutros) cor = corTamanho(p.n, rank, false, true).fundo;
      el("path", {
        d: fita(x0, s0, s1, x1, p.y0, p.y1), fill: cor,
        opacity: naTrilha ? (ativa ? 0.55 : 0.32) : ativa ? 0.3 : 0.16, class: naTrilha ? "cc-fita cc-fita-trilha" : "cc-fita",
      }, gFitas);
    });
  }

  // barras
  for (let i = primeiro; i < nc; i++) {
    const c = cols[i];
    const ativo = i >= nc - 2;
    const x = xCol(i), w = largBar(i);
    pos[i].forEach((p, rank) => {
      const escolhido = p.n === c.sel;
      const g = el("g", { class: `cc-no${escolhido ? " cc-sel" : ""}`, "data-k": alvo(p.n), tabindex: 0, role: "button", "aria-label": `${p.n.nome}: ${moedaCurta(p.n.valor)}` }, gBarras);
      el("title", {}, g).textContent = `${p.n.nome}\n${moedaCurta(p.n.valor)} · ${pctCurto(p.n.valor / Math.max(1, c.pai?.valor ?? p.n.valor))}`;
      // área de clique maior que a barra
      el("rect", { x: x - 4, y: p.y0, width: w + 8, height: Math.max(6, p.y1 - p.y0), fill: "transparent" }, g);
      pintar(g, x, p.y0, w, p.y1 - p.y0, p.n, corTamanho(p.n, rank, escolhido || i === 0, ativo || escolhido), false, !escolhido && !ativo);
      if (escolhido && i > 0) el("rect", { x: x - 2, y: p.y0, width: 2, height: Math.max(1, p.y1 - p.y0), fill: "#191919" }, g);
    });
  }

  // rótulos da coluna B (filhos ou irmãos do atual) e da coluna A
  const rotular = (i: number, lado: "dir" | "esq") => {
    const c = cols[i];
    const ps = pos[i];
    const mostrar = lado === "esq" && mob ? [] : ps;
    if (!mostrar.length) return;
    const dist = mob ? 30 : 34;
    const ys = afastar(mostrar.map((p) => (p.y0 + p.y1) / 2), dist, topo + 10, topo + alt - 14);
    const xBar = xCol(i);
    const chars = Math.floor((lado === "dir" ? LB - 22 : LA - 16) / (mob ? 6.4 : 7));
    mostrar.forEach((p, j) => {
      const escolhido = p.n === c.sel;
      const y = ys[j];
      const g = el("g", { class: `cc-rot${escolhido ? " cc-sel" : ""}${p.n.ehOutros ? " cc-rot-outros" : ""}`, "data-k": alvo(p.n), role: "button", tabindex: -1 }, gRot);
      const meio = (p.y0 + p.y1) / 2;
      const xt = lado === "dir" ? xBar + barB + 12 : xBar - 10;
      if (Math.abs(y - meio) > 3) {
        const xg = lado === "dir" ? xBar + barB + 2 : xBar - 2;
        el("path", { d: `M${xg},${meio}L${lado === "dir" ? xt - 3 : xt + 3},${y - 4}`, class: "cc-guia" }, g);
      }
      const anchor = lado === "dir" ? "start" : "end";
      const t1 = el("text", { x: xt, y: y - 3, "text-anchor": anchor, class: "cc-r-nome" }, g);
      t1.textContent = corta(p.n.nome, chars);
      const t2 = el("text", { x: xt, y: y + 12, "text-anchor": anchor, class: "cc-r-valor" }, g);
      t2.textContent = `${moedaCurta(p.n.valor)} · ${pctCurto(p.n.valor / Math.max(1, c.pai?.valor ?? p.n.valor))}${p.n.ehOutros ? " · ver lista" : ""}`;
    });
  };
  if (nc >= 2) {
    rotular(nc - 1, "dir");
    rotular(nc - 2, "esq");
  } else rotular(0, "dir");

  // cabeçalhos das duas colunas ativas
  const cab = (i: number, anchor: "start" | "end", x: number) => {
    const c = cols[i];
    const nivel = c.itens[0]?.nivel ?? "";
    const t = el("text", { x, y: 14, "text-anchor": anchor, class: "cc-cab" }, svg);
    t.textContent = i === 0 ? "" : plural(nivel).toUpperCase();
    if (!mob && i > 0 && F.explica[nivel]) {
      const t2 = el("text", { x, y: 29, "text-anchor": anchor, class: "cc-cab-explica" }, svg);
      t2.textContent = corta(F.explica[nivel], Math.floor((anchor === "end" ? LA + 40 : LB + 20) / 6));
    }
  };
  if (nc >= 2) {
    cab(nc - 1, "start", xCol(nc - 1));
    if (!mob) cab(nc - 2, "end", xCol(nc - 2) + barA);
  }

  host.appendChild(svg);

  if (movimento?.tipo === "desce" && nc >= 2) {
    // a coluna nova entra pela esquerda, como se saísse do pedaço escolhido
    const novos = [...gBarras.children].slice(-pos[nc - 1].length);
    for (const e of [...novos, gRot]) (e as SVGElement).animate?.([{ opacity: 0, transform: "translateX(-24px)" }, { opacity: 1, transform: "none" }], { duration: 320, easing: "ease-out" });
    gFitas.animate?.([{ opacity: 0 }, { opacity: 1 }], { duration: 320 });
  }
}

// ——— Forma 2: degraus (icicle com zoom) ———

function forma2(host: HTMLElement) {
  const W = largura;
  const mob = celular();
  const cam = E.caminho, cur = atual();
  interface Banda { itens: No[]; sel: No | null; pai: No | null }
  const bandas: Banda[] = [{ itens: [cam[0]], sel: cam[0], pai: null }];
  for (let i = 1; i < cam.length; i++) bandas.push({ itens: lista(vis(cam[i - 1], cam[i])), sel: cam[i], pai: cam[i - 1] });
  if (temFilhos(cur)) bandas.push({ itens: lista(vis(cur)), sel: null, pai: cur });

  const LW = mob ? 0 : Math.min(230, W * 0.22);
  const X0 = mob ? 0 : LW + 14;
  const BW = W - X0;
  const BH = mob ? 46 : 58, CH = mob ? 16 : 22, DH = mob ? 36 : 0;
  const passo = DH + BH + CH;
  const H = bandas.length * passo - CH + 4;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: "cc-svg cc-f2", role: "group", "aria-label": "Degraus do gasto" });
  defs(svg);

  const geo: { x0: number; x1: number; n: No }[][] = bandas.map((b) => {
    const tot = b.itens.reduce((s, n) => s + n.valor, 0) || 1;
    const vao = 2;
    const util = BW - vao * (b.itens.length - 1);
    let x = X0;
    return b.itens.map((n) => {
      const w = Math.max(1, (n.valor / tot) * util);
      const r = { x0: x, x1: x + w, n };
      x += w + vao;
      return r;
    });
  });

  bandas.forEach((b, d) => {
    const y = d * passo + DH;
    const g = el("g", { class: "cc-banda" }, svg);
    const ultima = d === bandas.length - 1;
    // o degrau da esquerda (ou a linha de cima, no celular)
    const s = b.sel;
    const nivel = b.itens[0]?.nivel ?? "";
    if (!mob) {
      const gd = el("g", { class: `cc-degrau-svg${s === cur ? " atual" : ""}${s ? "" : " vazio"}`, "data-k": s ? alvo(s) : undefined, role: s ? "button" : undefined, tabindex: s ? 0 : undefined }, g);
      const p = 12;
      el("path", { d: `M0,${y}H${LW - p}L${LW},${y + BH / 2}L${LW - p},${y + BH}H0Z`, class: "cc-degrau-fundo" }, gd);
      el("text", { x: 12, y: y + 15, class: "cc-d-tipo" }, gd).textContent = s ? nivel.toUpperCase() : `${plural(nivel).toUpperCase()}`;
      el("text", { x: 12, y: y + 33, class: "cc-d-nome" }, gd).textContent = s ? corta(s.nome, Math.floor((LW - 30) / 7.4)) : "Escolha um pedaço →";
      el("text", { x: 12, y: y + 49, class: "cc-d-valor" }, gd).textContent = s
        ? `${moedaCurta(s.valor)}${d > 0 ? ` · ${pctCurto(parte(s))} ${d === 1 ? "do total" : "do anterior"}` : ""}`
        : corta(F.explica[nivel] ?? "", Math.floor((LW - 30) / 6));
    } else {
      const gd = el("g", { class: `cc-degrau-svg${s === cur ? " atual" : ""}`, "data-k": s ? alvo(s) : undefined, role: s ? "button" : undefined }, g);
      el("text", { x: 0, y: y - 21, class: "cc-d-tipo" }, gd).textContent = s ? nivel.toUpperCase() : `${plural(nivel).toUpperCase()}: TOQUE NUM PEDAÇO`;
      if (s) {
        const t = el("text", { x: 0, y: y - 6, class: "cc-d-nome" }, gd);
        t.textContent = `${corta(s.nome, 30)} · ${moedaCurta(s.valor)}${d > 0 ? ` · ${pctCurto(parte(s))}` : ""}`;
      }
    }
    // os pedaços
    const gp = el("g", { class: "cc-pedacos" }, g);
    geo[d].forEach((p, rank) => {
      const escolhido = p.n === s;
      const w = p.x1 - p.x0;
      const gn = el("g", { class: `cc-no${escolhido ? " cc-sel" : ""}`, "data-k": alvo(p.n), role: "button", tabindex: 0, "aria-label": `${p.n.nome}: ${moedaCurta(p.n.valor)}` }, gp);
      el("title", {}, gn).textContent = `${p.n.nome}\n${moedaCurta(p.n.valor)} · ${pctCurto(p.n.valor / Math.max(1, b.pai?.valor ?? p.n.valor))}`;
      const cor = corTamanho(p.n, rank, escolhido || d === 0, ultima || escolhido);
      const apagado = !escolhido && !ultima;
      pintar(gn, p.x0, y, w, BH, p.n, cor, true, apagado);
      if (escolhido && d > 0) el("rect", { x: p.x0, y: y + BH - 4, width: w, height: 4, fill: "#191919" }, gn);
      // no modo "tipo" o pedaço é pintado em faixas; o texto fica sobre a faixa do meio
      const claro = usaTipo() && !p.n.ehOutros ? (apagado ? false : escuroNoMeio(p.n, 0.35)) : cor.escuro;
      const classe = `cc-p-txt${claro ? " claro" : ""}`;
      const chars = Math.floor((w - 10) / 6.6);
      if (w >= 58 && chars >= 6) {
        el("text", { x: p.x0 + 6, y: y + 18, class: `${classe} cc-p-nome` }, gn).textContent = corta(p.n.nome, chars);
        el("text", { x: p.x0 + 6, y: y + 34, class: classe }, gn).textContent =
          corta(`${moedaCurta(p.n.valor)} · ${pctCurto(p.n.valor / Math.max(1, b.pai?.valor ?? p.n.valor))}`, chars);
      } else if (w >= 26) {
        el("text", { x: p.x0 + w / 2, y: y + BH / 2 + 4, class: classe, "text-anchor": "middle" }, gn).textContent = pctCurto(p.n.valor / Math.max(1, b.pai?.valor ?? p.n.valor));
      }
    });
    // o funil até a banda seguinte: do pedaço escolhido para a largura toda
    if (!ultima && s) {
      const p = geo[d].find((q) => q.n === s);
      if (p) {
        const y1 = y + BH, y2 = (d + 1) * passo + DH;
        el("path", { d: `M${p.x0},${y1}L${p.x1},${y1}L${X0 + BW},${y2 - (mob ? DH : 0)}L${X0},${y2 - (mob ? DH : 0)}Z`, class: "cc-funil" }, g);
      }
    }
  });
  host.appendChild(svg);

  if (movimento?.tipo === "desce" && bandas.length >= 2) {
    const ultimaG = svg.querySelectorAll(".cc-banda");
    const nova = ultimaG[ultimaG.length - 1]?.querySelector(".cc-pedacos") as SVGGElement | null;
    const de = geo[bandas.length - 2]?.find((q) => q.n === bandas[bandas.length - 2].sel);
    if (nova && de) {
      const sx = Math.max(0.02, (de.x1 - de.x0) / BW);
      nova.animate?.([
        { transform: `translate(${de.x0 - X0 * sx}px, -${passo}px) scale(${sx}, 1)`, opacity: 0.4 },
        { transform: "none", opacity: 1 },
      ], { duration: 380, easing: "cubic-bezier(.2,.7,.2,1)" });
    }
  }
}

// ——— Forma 3: três colunas que deslizam (HTML, com as fitas num SVG por cima) ———

function forma3(host: HTMLElement) {
  const cam = E.caminho, cur = atual();
  const k = cam.length;
  interface Col { titulo: string; explica: string; itens: No[]; sel: No | null; pai: No | null; vazia?: string; cartao?: No }
  const colDe = (pai: No | null, sel: No | null): Col => {
    if (!pai) return { titulo: "", explica: "", itens: sel ? [sel] : [], sel, pai: null };
    const v = vis(pai, sel);
    const nivel = v.itens[0]?.nivel ?? "";
    return { titulo: plural(nivel), explica: F.explica[nivel] ?? "", itens: lista(v), sel, pai };
  };
  const A: Col = k >= 3 ? colDe(cam[k - 3], cam[k - 2]) : k === 2 ? colDe(null, cam[0]) : { titulo: "", explica: "", itens: [], sel: null, pai: null, vazia: "Aqui aparece de onde o dinheiro veio." };
  const B: Col = k >= 2 ? colDe(cam[k - 2], cur) : colDe(null, cur);
  const C: Col = temFilhos(cur) ? colDe(cur, null) : { titulo: "", explica: "", itens: [], sel: null, pai: cur, cartao: cur };
  if (k === 1) B.titulo = "";

  const htmlCol = (c: Col, qual: string) => {
    if (c.cartao) return `<section class="cc3-col ${qual} cc3-fim"><header><h3>${esc(c.titulo)}</h3></header>${htmlCartao(c.cartao)}</section>`;
    const aberto = E.outros && c.pai === E.outros;
    const linhas = c.itens.map((n) => {
      const escolhido = n === c.sel;
      const frac = n.valor / Math.max(1, c.pai?.valor ?? n.valor);
      const linha = `<li><button type="button" class="cc3-linha${escolhido ? " sel" : ""}${n.ehOutros ? " outros" : ""}" data-k="${alvo(n)}" data-no>
        <span class="cc3-nome">${esc(n.nome)}</span>
        <span class="cc3-valor num">${moedaCurta(n.valor)}${c.pai ? ` · ${pctCurto(frac)}` : ""}${n.ehOutros ? (aberto ? " · fechar" : " · abrir") : ""}</span>
        <span class="cc-l-barra">${htmlBarra(n, c.pai ? frac : 1)}</span>
      </button></li>`;
      if (n.ehOutros && aberto) {
        const resto = n.lista ?? [];
        return linha + resto.slice(0, 60).map((r) => `<li class="cc3-extra"><button type="button" class="cc3-linha" data-k="${alvo(r)}" data-no>
          <span class="cc3-nome">${esc(r.nome)}</span>
          <span class="cc3-valor num">${moedaCurta(r.valor)} · ${pctCurto(r.valor / Math.max(1, c.pai?.valor ?? 1))}</span>
          <span class="cc-l-barra">${htmlBarra(r, r.valor / Math.max(1, c.pai?.valor ?? 1))}</span></button></li>`).join("") +
          (resto.length > 60 ? `<li class="cc3-extra muted">e mais ${resto.length - 60}, menores</li>` : "");
      }
      return linha;
    }).join("");
    const dentro = c.pai ? `<span class="cc3-dentro">em ${esc(corta(c.pai.nome, 40))}</span>` : "";
    return `<section class="cc3-col ${qual}">
      <header>${c.titulo ? `<h3>${esc(c.titulo)}</h3>${dentro}` : ""}${c.explica ? `<p class="cc3-explica">${esc(c.explica)}</p>` : ""}</header>
      ${c.vazia ? `<p class="cc3-vazia">${esc(c.vazia)}</p>` : `<ol>${linhas}</ol>`}
    </section>`;
  };
  host.innerHTML = `<div class="cc3"><div class="cc3-trilho">${htmlCol(A, "a")}${htmlCol(B, "b")}${htmlCol(C, "c")}</div><svg class="cc3-fios" aria-hidden="true"></svg></div>`;
  const caixa = host.querySelector<HTMLElement>(".cc3")!;
  const trilho = host.querySelector<HTMLElement>(".cc3-trilho")!;
  const fios = host.querySelector<SVGSVGElement>(".cc3-fios")!;

  const desenharFios = () => {
    fios.innerHTML = "";
    const cx = caixa.getBoundingClientRect();
    fios.setAttribute("viewBox", `0 0 ${cx.width} ${cx.height}`);
    fios.setAttribute("width", String(cx.width));
    fios.setAttribute("height", String(cx.height));
    const cols = [...trilho.querySelectorAll<HTMLElement>(".cc3-col")];
    for (let i = 0; i < 2; i++) {
      const sel = cols[i].querySelector<HTMLElement>(".cc3-linha.sel");
      const destino = [...cols[i + 1].querySelectorAll<HTMLElement>(":scope > ol > li:not(.cc3-extra) > .cc3-linha")];
      if (!sel || !destino.length) continue;
      const rs = sel.getBoundingClientRect();
      const nos = destino.map((d) => alvos[Number(d.dataset.k)]);
      const tot = nos.reduce((s, n) => s + n.valor, 0) || 1;
      const x0 = rs.right - cx.left;
      let acc = 0;
      destino.forEach((d, j) => {
        const rd = d.getBoundingClientRect();
        const s0 = rs.top - cx.top + 4 + (acc / tot) * (rs.height - 8);
        acc += nos[j].valor;
        const s1 = rs.top - cx.top + 4 + (acc / tot) * (rs.height - 8);
        const meio = rd.top - cx.top + rd.height / 2;
        const esp = Math.max(1.2, s1 - s0);
        const cor = usaTipo() && !nos[j].ehOutros ? F.cats[catPrincipal(nos[j])].cor : nos[j].ehOutros ? "#c3bba7" : VERDE;
        el("path", { d: fita(x0, s0, s1, rd.left - cx.left, meio - esp / 2, meio + esp / 2), fill: cor, opacity: d.classList.contains("sel") ? 0.5 : 0.22 }, fios);
      });
    }
  };

  const colW = trilho.querySelector<HTMLElement>(".cc3-col.b")?.getBoundingClientRect().left! - trilho.querySelector<HTMLElement>(".cc3-col.a")!.getBoundingClientRect().left;
  if (movimento?.tipo === "desce" || movimento?.tipo === "sobe") {
    const dir = movimento.tipo === "desce" ? 1 : -1;
    fios.style.opacity = "0";
    const a = trilho.animate?.([{ transform: `translateX(${dir * colW}px)` }, { transform: "none" }], { duration: 300, easing: "cubic-bezier(.2,.7,.2,1)" });
    const fim = () => { desenharFios(); fios.animate?.([{ opacity: 0 }, { opacity: 1 }], { duration: 160 }); fios.style.opacity = "1"; };
    if (a) a.onfinish = fim; else fim();
  } else {
    if (movimento?.tipo === "lado") trilho.querySelector(".cc3-col.c")?.animate?.([{ opacity: 0 }, { opacity: 1 }], { duration: 220 });
    requestAnimationFrame(desenharFios);
  }
  // as listas podem rolar (o "outros" aberto): refaz as fitas
  trilho.querySelectorAll(".cc3-col").forEach((c) => c.addEventListener("scroll", () => requestAnimationFrame(desenharFios), { passive: true }));
}

// ——— desenho geral ———

function desenhar() {
  alvos = [];
  const cur = atual();
  const topo = raizEl.querySelector<HTMLElement>("#cc-topo")!;
  const desenho = raizEl.querySelector<HTMLElement>("#cc-desenho")!;
  const painel = raizEl.querySelector<HTMLElement>("#cc-painel")!;
  largura = Math.floor(desenho.getBoundingClientRect().width);

  topo.innerHTML = `<p class="cc-frase">${esc(F.frase)}</p>
    <div class="cc-topo-linha">${htmlLegenda()}</div>
    ${E.v === 2 ? "" : htmlDegraus()}
    <p class="cc-dica muted">${temFilhos(cur)
      ? `${E.v === 2 ? "Clique num pedaço para abrir o nível de baixo; num degrau, para voltar." : "Clique num item para abrir o nível seguinte; num degrau ou coluna anterior, para voltar."} Em cada nível aparecem só os maiores; o resto fica em “outros”.`
      : "Fim do caminho: este é o último nível dos dados."}</p>`;
  desenho.innerHTML = "";
  desenho.dataset.v = String(E.v);
  if (E.v === 1) forma1(desenho);
  else if (E.v === 2) forma2(desenho);
  else forma3(desenho);
  painel.innerHTML = E.v === 3 ? "" : htmlPainel();
  painel.hidden = !painel.innerHTML;
  painel.querySelector("[data-fechar]")?.addEventListener("click", () => { E.outros = null; movimento = null; desenhar(); });
  ligarCliques(topo);
  ligarCliques(desenho);
  ligarCliques(painel);
  movimento = null;
}

export async function iniciar(el: HTMLElement) {
  raizEl = el;
  E = lerUrl();
  atualizarControles();
  const desenho = el.querySelector<HTMLElement>("#cc-desenho")!;
  desenho.innerHTML = `<p class="cc-carregando">Carregando…</p>`;
  try {
    F = E.onde === "joao-pessoa" ? await fonteJoaoPessoa() : await fonteUniao();
  } catch (e) {
    desenho.innerHTML = `<p class="cc-erro">Não foi possível carregar os dados. ${esc(String((e as Error).message))}</p>`;
    return;
  }
  const c = new URLSearchParams(location.search).get("c");
  E.caminho = resolverCaminho(F.raiz, c ? c.split("~") : []);
  atualizarControles();
  el.querySelectorAll<HTMLButtonElement>("[data-cor]").forEach((b) => b.addEventListener("click", () => {
    E.cor = b.dataset.cor as ModoCor;
    salvarUrl();
    desenhar();
  }));
  if (F.cats.length <= 1) el.querySelector<HTMLElement>(".cc-cores")?.setAttribute("hidden", "");
  desenhar();
  let ultimo = largura;
  new ResizeObserver(() => {
    const w = Math.floor(desenho.getBoundingClientRect().width);
    if (Math.abs(w - ultimo) > 4) { ultimo = w; desenhar(); }
  }).observe(desenho);
}
