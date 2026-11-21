/**
 * Forma 4 do protótipo da cascata: a tela livre, em Canvas 2D. Uma árvore da esquerda para a direita, como um mapa
 * mental, em que cada caixa abre os filhos (vários galhos abertos ao mesmo tempo). Arrasta para andar, roda ou pinça
 * para o zoom, e há tela cheia.
 *
 * Dois jeitos de medir as caixas:
 * - "em cada nível" (padrão): os filhos de uma caixa dividem um bloco de pelo menos 320 px, em proporção ao valor.
 *   Cada nível é um zoom do anterior; a etiqueta "ampliado N×" no funil diz quanto.
 * - "tamanho real": todas as caixas na mesma escala do total (um sankey de verdade). Os pequenos viram fios; o zoom
 *   estica só na vertical, para enxergá-los sem as caixas ficarem largas demais.
 */
import { moedaCurta, pct } from "../../lib/formato";
import { RAMPA } from "../../lib/cores";
import { caminhoAte, catPrincipal, filhos, type Fonte, type No } from "./dados";

export interface OpcoesTela {
  usaTipo: () => boolean;
  caminhoInicial: No[];
  aoEscolher: (n: No) => void;
  /** HTML dos detalhes de uma caixa (qualquer nível). */
  cartao: (n: No) => string;
}

export interface Tela {
  fonte: Fonte;
  raiz: HTMLElement;
  redesenhar(): void;
}

type Modo = "nivel" | "real";

const LARG = 250;          // largura da caixa (mundo)
const VAO_COL = 150;        // espaço das fitas entre colunas
const COL = LARG + VAO_COL;
const MIN_H = 58;           // altura mínima de uma caixa: nome em duas linhas + valor
const BLOCO = 320;          // altura mínima do bloco de filhos
const ALT_RAIZ = 440;
const VAO = 8;
const VAO_GALHO = 26;
const ALT_REAL = 900;       // no tamanho real, a altura do total
const MIN_REAL = 1.5;
const VAO_R = 2;
const VAO_GALHO_R = 10;
const K_INICIAL = 8;        // quantos filhos aparecem antes do "mais N"
const MAIS = 10;            // quantos o "mais N" abre de cada vez
const KY_MAX = 50000;

const VERDE = "#0e6b3b";
const PAPEL = "#f7f4ec";
const TINTA = "#191919";
const CINZA = "#5c574c";

interface Pos { x: number; y: number; h: number; d: number }
interface Camera { k: number; ky: number; x: number; y: number }

const facil = (t: number) => 1 - Math.pow(1 - t, 3);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const limitar = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const pctCurto = (v: number) => (v >= 0.995 ? "100%" : v >= 0.1 ? `${Math.round(v * 100)}%` : v >= 0.001 ? pct(v) : "<0,1%");
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const vezes = (z: number) => (z < 10 ? z.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : Math.round(z).toLocaleString("pt-BR"));

export function criarTela(host: HTMLElement, F: Fonte, op: OpcoesTela): Tela {
  host.innerHTML = `<div class="cc4" tabindex="-1">
    <canvas class="cc4-canvas" aria-label="Tela livre do gasto: arraste para andar, use a roda ou pinça para o zoom, clique numa caixa para abrir e ver os detalhes."></canvas>
    <div class="cc4-topo"><ol class="cc4-fio"></ol></div>
    <div class="cc4-botoes cc4-canto">
      <button type="button" data-acao="cheia" class="cc4-cheia-btn"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg><span>Tela cheia</span></button>
    </div>
    <div class="cc4-botoes cc4-zoom">
      <button type="button" data-acao="procurar" class="cc4-procurar-btn"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg><span>Procurar</span></button>
      <button type="button" data-acao="modo" class="cc4-modo-btn" aria-pressed="false" title="Todas as caixas na mesma escala do total"><span class="longo">Tamanho real</span><span class="curto">Real</span></button>
      <button type="button" data-acao="mais" aria-label="Aproximar">+</button>
      <button type="button" data-acao="menos" aria-label="Afastar">−</button>
      <button type="button" data-acao="ajustar"><span class="longo">Ver tudo</span><span class="curto">Tudo</span></button>
      <button type="button" data-acao="fechar"><span class="longo">Fechar galhos</span><span class="curto">Fechar</span></button>
    </div>
    <div class="cc4-aviso" hidden>Tamanho real: todas as caixas na mesma escala do total. Os pequenos viram fios; dê zoom para esticar na vertical.</div>
    <div class="cc4-dica">Arraste para andar · roda ou pinça: zoom · clique: abrir e ver detalhes · duplo clique: focar · /: procurar</div>
    <div class="cc4-busca" hidden>
      <input type="search" placeholder="Procurar órgão, programa, ação, fornecedor…" aria-label="Procurar na árvore" autocomplete="off" />
      <ol class="cc4-resultados" aria-live="polite"></ol>
    </div>
    <canvas class="cc4-mapa" aria-hidden="true"></canvas>
    <nav class="cc4-lista visually-hidden" aria-label="A árvore aberta, em lista"></nav>
    <div class="cc4-balao" hidden></div>
    <aside class="cc4-cartao" hidden>
      <button type="button" class="cc4-resumo" data-acao="detalhes"></button>
      <div class="cc4-corpo"><button type="button" class="cc4-x" data-acao="min-cartao" aria-label="Fechar os detalhes">×</button><div class="cc4-conteudo"></div></div>
    </aside>
  </div>`;
  const caixa = host.querySelector<HTMLElement>(".cc4")!;
  const cv = caixa.querySelector<HTMLCanvasElement>("canvas")!;
  const ctx = cv.getContext("2d")!;
  const balao = caixa.querySelector<HTMLElement>(".cc4-balao")!;
  const cartao = caixa.querySelector<HTMLElement>(".cc4-cartao")!;
  const resumoEl = cartao.querySelector<HTMLElement>(".cc4-resumo")!;
  const conteudo = cartao.querySelector<HTMLElement>(".cc4-conteudo")!;
  const fioEl = caixa.querySelector<HTMLElement>(".cc4-fio")!;
  const busca = caixa.querySelector<HTMLElement>(".cc4-busca")!;
  const campo = busca.querySelector<HTMLInputElement>("input")!;
  const resultados = busca.querySelector<HTMLElement>(".cc4-resultados")!;
  const mapa = caixa.querySelector<HTMLCanvasElement>(".cc4-mapa")!;
  const mctx = mapa.getContext("2d")!;
  const listaEl = caixa.querySelector<HTMLElement>(".cc4-lista")!;
  const avisoEl = caixa.querySelector<HTMLElement>(".cc4-aviso")!;

  // listras do "mais N": não podem parecer uma categoria (a financeira é cinza)
  const tile = document.createElement("canvas");
  tile.width = tile.height = 8;
  const tctx = tile.getContext("2d")!;
  tctx.fillStyle = PAPEL;
  tctx.fillRect(0, 0, 8, 8);
  tctx.strokeStyle = "#8a8475";
  tctx.lineWidth = 1.6;
  tctx.beginPath(); tctx.moveTo(-2, 10); tctx.lineTo(10, -2); tctx.moveTo(-2, 2); tctx.lineTo(2, -2); tctx.moveTo(6, 10); tctx.lineTo(10, 6); tctx.stroke();
  const listras = ctx.createPattern(tile, "repeat")!;

  // ——— estado ———
  const abertos = new Set<No>();
  const mostrar = new Map<No, number>();
  const outrosDe = new Map<No, No>();
  let sel: No | null = null;
  let quente: No | null = null;
  let modo: Modo = "nivel";
  for (const n of op.caminhoInicial) abertos.add(n);
  abertos.add(F.raiz);
  const ultimo = op.caminhoInicial[op.caminhoInicial.length - 1];
  if (ultimo && ultimo !== F.raiz) sel = ultimo;
  // um item escolhido que esteja fora dos primeiros: mostra até ele
  for (let i = 1; i < op.caminhoInicial.length; i++) {
    const pai = op.caminhoInicial[i - 1];
    const j = filhos(pai).indexOf(op.caminhoInicial[i]);
    if (j >= K_INICIAL) mostrar.set(pai, j + 1);
  }

  let W = 0, H = 0, dpr = 1;
  const cam: Camera = { k: 1, ky: 1, x: 40, y: 40 };
  let camDe: Camera = { ...cam }, camPara: Camera = { ...cam }, camT = 1, camIni = 0;
  let minimizado = false;

  let pos = new Map<No, Pos>();
  let antes = new Map<No, Pos>();
  let animT = 1, animIni = 0;
  const DUR = 380;

  // ——— a árvore visível ———
  function visiveis(n: No): No[] {
    // "N credores menores" (o resto que o arquivo do protótipo já juntou) vai para o fim, dentro do "mais N"
    const todos = filhos(n);
    const fs = todos.some((f) => f.info?.resto) ? [...todos.filter((f) => !f.info?.resto), ...todos.filter((f) => f.info?.resto)] : todos;
    const k = mostrar.get(n) ?? K_INICIAL;
    if (fs.length <= k + 1) return fs;
    const resto = fs.slice(k);
    let o = outrosDe.get(n);
    if (!o) {
      o = { cod: "#outros", nome: "", valor: 0, nivel: fs[0].nivel, prof: n.prof + 1, pai: n, mix: [], ehOutros: true };
      outrosDe.set(n, o);
    }
    o.lista = resto;
    o.valor = resto.reduce((s, f) => s + f.valor, 0);
    o.mix = new Array(n.mix.length).fill(0);
    for (const f of resto) f.mix.forEach((v, i) => (o!.mix[i] += v));
    o.nome = `mais ${resto.reduce((s, f) => s + (f.info?.resto ?? 1), 0)} ${F.plural[o.nivel] ?? "itens"}`;
    return [...fs.slice(0, k), o];
  }
  const abre = (n: No) => !n.ehOutros && filhos(n).length > 0;
  const galho = (n: No) => abertos.has(n) && abre(n);
  const escalaReal = () => ALT_REAL / Math.max(1, F.raiz.valor);
  const vao = () => (modo === "real" ? VAO_R : VAO);
  const vaoGalho = () => (modo === "real" ? VAO_GALHO_R : VAO_GALHO);

  function alturas(n: No, h: number): number[] {
    const ks = visiveis(n);
    if (modo === "real") return ks.map((f) => Math.max(MIN_REAL, f.valor * escalaReal()));
    const bloco = Math.max(h, BLOCO);
    const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
    const util = bloco - VAO * (ks.length - 1);
    return ks.map((f) => Math.max(MIN_H, (f.valor / tot) * util));
  }

  /** Quanto o bloco de filhos está ampliado em relação à escala do total (só no modo "em cada nível"). */
  function ampliacao(n: No, h: number): number {
    const ks = visiveis(n);
    const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
    const util = Math.max(h, BLOCO) - VAO * (ks.length - 1);
    return (util / tot) / (ALT_RAIZ / Math.max(1, F.raiz.valor));
  }

  /** Mede (altura ocupada por cada galho) e posiciona. */
  function calcular() {
    const ext = new Map<No, number>();
    const hs = new Map<No, number>();
    const entre = (ks: No[], i: number) => (i ? (galho(ks[i]) || galho(ks[i - 1]) ? vaoGalho() : vao()) : 0);
    const medir = (n: No, h: number): number => {
      hs.set(n, h);
      let e = h;
      if (galho(n)) {
        const ks = visiveis(n);
        const hk = alturas(n, h);
        let soma = 0;
        ks.forEach((f, i) => { soma += medir(f, hk[i]) + entre(ks, i); });
        e = Math.max(h, soma);
      }
      ext.set(n, e);
      return e;
    };
    const novo = new Map<No, Pos>();
    const por = (n: No, d: number, topo: number) => {
      const h = hs.get(n)!, e = ext.get(n)!;
      novo.set(n, { x: d * COL, y: topo + (e - h) / 2, h, d });
      if (galho(n)) {
        const ks = visiveis(n);
        const soma = ks.reduce((s, f, i) => s + ext.get(f)! + entre(ks, i), 0);
        let y = topo + (e - soma) / 2;
        ks.forEach((f, i) => {
          y += entre(ks, i);
          por(f, d + 1, y);
          y += ext.get(f)!;
        });
      }
    };
    medir(F.raiz, modo === "real" ? ALT_REAL : ALT_RAIZ);
    por(F.raiz, 0, 0);
    return novo;
  }

  function relayout(animar = true) {
    // posição de agora (no meio de uma animação) vira o ponto de partida
    const agora = new Map<No, Pos>();
    for (const n of pos.keys()) agora.set(n, posDe(n)!);
    antes = agora;
    pos = calcular();
    atualizarLista();
    animT = animar ? 0 : 1;
    animIni = performance.now();
    pedir();
  }

  function posDe(n: No): Pos | null {
    const p = pos.get(n);
    if (!p) return null;
    if (animT >= 1) return p;
    const t = facil(animT);
    let a = antes.get(n);
    if (!a) {
      // caixa nova: sai de dentro do pai
      const pai = n.pai && (antes.get(n.pai) ?? pos.get(n.pai));
      a = pai ? { x: pai.x + LARG * 0.6, y: pai.y + pai.h / 2 - p.h / 2, h: p.h * 0.3, d: p.d } : p;
    }
    return { x: lerp(a.x, p.x, t), y: lerp(a.y, p.y, t), h: lerp(a.h, p.h, t), d: p.d };
  }
  const alfaDe = (n: No) => (animT >= 1 || antes.has(n) ? 1 : facil(animT));

  // ——— câmera (k no eixo x, ky no y; no modo "em cada nível" são iguais) ———
  const sx = (x: number) => x * cam.k + cam.x;
  const sy = (y: number) => y * cam.ky + cam.y;
  const paraMundo = (px: number, py: number) => ({ x: (px - cam.x) / cam.k, y: (py - cam.y) / cam.ky });

  function caixaDe(ns: No[]) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const n of ns) {
      const p = pos.get(n);
      if (!p) continue;
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x + LARG); y1 = Math.max(y1, p.y + p.h);
    }
    return { x0, y0, x1, y1 };
  }
  const cartaoAberto = () => !cartao.hidden && !minimizado;
  function margens() {
    const fioBaixo = fioEl.getBoundingClientRect().bottom - caixa.getBoundingClientRect().top;
    const cel = W < 720;
    const m = cel ? 24 : 70;
    const dir = !cel && cartaoAberto() ? cartao.offsetWidth + 36 : m;
    const baixo = cel ? (cartaoAberto() ? cartao.offsetHeight + 70 : 112) : 60;
    return { esq: m, dir, topo: Math.max(64, fioBaixo + 12), baixo };
  }
  function enquadrar(b: { x0: number; y0: number; x1: number; y1: number }, kMax = 1.1, animar = true) {
    if (!Number.isFinite(b.x0) || !W) return;
    const mg = margens();
    const larg = Math.max(80, W - mg.esq - mg.dir), alt = Math.max(80, H - mg.topo - mg.baixo);
    const bw = Math.max(1, b.x1 - b.x0), bh = Math.max(0.01, b.y1 - b.y0);
    let k: number, ky: number;
    if (modo === "nivel") { k = ky = limitar(Math.min(kMax, larg / bw, alt / bh), 0.03, 4); }
    else { k = limitar(Math.min(1.1, larg / bw), 0.25, 1.1); ky = limitar(Math.min(KY_MAX, alt / bh), 0.05, KY_MAX); }
    irPara({ k, ky, x: mg.esq + (larg - bw * k) / 2 - b.x0 * k, y: mg.topo + (alt - bh * ky) / 2 - b.y0 * ky }, animar);
  }
  function irPara(alvo: Camera, animar = true) {
    camDe = { ...cam };
    camPara = alvo;
    camT = animar ? 0 : 1;
    camIni = performance.now();
    if (!animar) Object.assign(cam, alvo);
    pedir();
  }
  /** Um passo da animação da câmera: o centro anda em linha reta e o zoom em escala logarítmica (do fio ao detalhe). */
  function passoCamera(t: number) {
    const e = facil(t);
    const cx0 = (W / 2 - camDe.x) / camDe.k, cx1 = (W / 2 - camPara.x) / camPara.k;
    const cy0 = (H / 2 - camDe.y) / camDe.ky, cy1 = (H / 2 - camPara.y) / camPara.ky;
    cam.k = Math.exp(lerp(Math.log(camDe.k), Math.log(camPara.k), e));
    cam.ky = Math.exp(lerp(Math.log(camDe.ky), Math.log(camPara.ky), e));
    cam.x = W / 2 - lerp(cx0, cx1, e) * cam.k;
    cam.y = H / 2 - lerp(cy0, cy1, e) * cam.ky;
  }
  function zoomPara(base: Camera, fator: number, px0: number, py0: number, px: number, py: number) {
    let k: number, ky: number;
    if (modo === "nivel") { k = ky = limitar(base.k * fator, 0.03, 4); }
    else { ky = limitar(base.ky * fator, 0.05, KY_MAX); k = limitar(ky, 0.25, 1.1); }
    const wx = (px0 - base.x) / base.k, wy = (py0 - base.y) / base.ky;
    cam.k = k; cam.ky = ky; cam.x = px - wx * k; cam.y = py - wy * ky;
  }
  function zoomEm(fator: number, px: number, py: number) {
    camT = 1;
    zoomPara({ ...cam }, fator, px, py, px, py);
    pedir();
  }

  /** Depois de abrir uma caixa: se ela e os filhos não couberem na tela, anda (e muda o zoom, se preciso) até caberem. */
  function mostrarGalho(n: No) {
    const ns = W < 720 && galho(n) ? visiveis(n) : [n, ...(galho(n) ? visiveis(n) : [])];
    const b = caixaDe(ns);
    const mg = margens();
    const s0 = { x: sx(b.x0), y: sy(b.y0), x1: sx(b.x1), y1: sy(b.y1) };
    const cabe = s0.x >= 0 && s0.x1 <= W - mg.dir + 20 && s0.y >= mg.topo - 20 && s0.y1 <= H - 40 && (s0.y1 - s0.y) > 40;
    if (!cabe) enquadrar(b, W < 720 ? 1 : Math.max(cam.k, 0.5));
  }

  /** Os detalhes ficam à direita (embaixo, no celular): anda para a caixa escolhida não ficar atrás deles. */
  function desviarDoCartao(n: No) {
    const p = pos.get(n);
    if (!p || !cartaoAberto()) return;
    const r = cartao.getBoundingClientRect(), c = caixa.getBoundingClientRect();
    const x1 = sx(p.x + LARG), y1 = sy(p.y + p.h);
    const limX = r.left - c.left - 24, limY = r.top - c.top - 16;
    if (W >= 720 && x1 > limX) irPara({ ...cam, x: cam.x - (x1 - limX) });
    else if (W < 720 && y1 > limY) irPara({ ...cam, y: cam.y - (y1 - limY) });
  }

  // ——— desenho ———
  let pedido = 0;
  function pedir() { if (!pedido) pedido = requestAnimationFrame(quadro); }

  function quadro(t: number) {
    pedido = 0;
    let mais = false;
    if (animT < 1) { animT = Math.min(1, (t - animIni) / DUR); mais = true; }
    if (camT < 1) { camT = Math.min(1, (t - camIni) / 450); passoCamera(camT); mais = true; }
    desenhar();
    if (mais) pedir();
  }

  const noCaminho = () => new Set(sel ? caminhoAte(sel) : []);

  function corDe(n: No, rank: number, trilha: boolean): string | CanvasPattern {
    if (n.ehOutros) return listras;
    if (op.usaTipo()) return F.cats[catPrincipal(n)].cor;
    if (trilha || n === F.raiz) return VERDE;
    return RAMPA[Math.min(rank + 1, RAMPA.length - 1)];
  }

  function cortar(t: string, larg: number): string {
    if (ctx.measureText(t).width <= larg) return t;
    let u = t;
    while (u.length > 1 && ctx.measureText(`${u}…`).width > larg) u = u.slice(0, -1);
    return `${u.trimEnd()}…`;
  }

  function linhasDe(nome: string, larg: number, max: number): string[] {
    const out: string[] = [];
    let l = "";
    for (const p of nome.split(/\s+/)) {
      const t = l ? `${l} ${p}` : p;
      if (ctx.measureText(t).width <= larg || !l) l = t;
      else { out.push(l); l = p; if (out.length === max) break; }
    }
    if (out.length < max && l) out.push(l);
    if (out.length > max) out.length = max;
    if (out.join(" ").length < nome.length) out[out.length - 1] = cortar(`${out[out.length - 1]}…`, larg);
    return out.map((s) => cortar(s, larg));
  }

  /** "R$ 93,3 bi · 44% · 2,7% do total": o "do total" só entra se couber. */
  function linhaValor(n: No, larg: number): string {
    const pai = n.pai;
    const base = `${moedaCurta(n.valor)}${pai ? ` · ${pctCurto(n.valor / Math.max(1, pai.valor))}` : ""}`;
    if (n.ehOutros) return cortar(`${base} · clique para ver mais`, larg);
    if (pai && pai !== F.raiz) {
      const comTotal = `${base} · ${pctCurto(n.valor / Math.max(1, F.raiz.valor))} do total`;
      if (ctx.measureText(comTotal).width <= larg) return comTotal;
    }
    return cortar(base, larg);
  }

  /** Faixa da esquerda: a cor (ou a mistura por categoria, de cima para baixo). */
  function faixa(n: No, x: number, y: number, w: number, h: number, rank: number, trilha: boolean) {
    if (op.usaTipo() && !n.ehOutros) {
      const t = n.mix.reduce((s, v) => s + Math.max(0, v), 0) || 1;
      let yy = y;
      n.mix.forEach((v, i) => {
        const hh = (Math.max(0, v) / t) * h;
        if (hh <= 0) return;
        ctx.fillStyle = F.cats[i].cor;
        ctx.fillRect(x, yy, w, hh);
        yy += hh;
      });
    } else {
      ctx.fillStyle = corDe(n, rank, trilha);
      ctx.fillRect(x, y, w, h);
    }
  }

  function retangulo(x: number, y: number, w: number, h: number, r: number) {
    const rr = Math.min(r, h / 2, w / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  /** Caixa alta: em vez de espaço vazio, o resumo do que tem dentro (coordenadas do mundo, modo "em cada nível"). */
  function caixaGrande(n: No, p: Pos, fx: number, larg: number) {
    const x = p.x + fx + 12;
    let y = p.y + 18;
    const fim = p.y + p.h - 10;
    ctx.fillStyle = CINZA;
    ctx.font = "600 10.5px Inter, system-ui, sans-serif";
    ctx.fillText(n.nivel.toUpperCase(), x, y);
    y += 8;
    const tam = Math.max(15, Math.min(20, p.h / 10));
    ctx.font = `700 ${tam}px "Source Serif 4", Georgia, serif`;
    ctx.fillStyle = TINTA;
    for (const l of linhasDe(n.nome, larg - 4, 4)) { y += tam * 1.15; if (y > fim) return; ctx.fillText(l, x, y); }
    y += tam * 1.1;
    if (y > fim) return;
    ctx.font = `600 ${Math.round(tam * 0.85)}px Inter, system-ui, sans-serif`;
    ctx.fillStyle = VERDE;
    ctx.fillText(moedaCurta(n.valor), x, y);
    const linha = (t: string) => {
      y += 17;
      if (y > fim) return false;
      ctx.font = "400 12.5px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#3d3a33";
      ctx.fillText(cortar(t, larg + 20), x, y);
      return true;
    };
    if (n.pai && !linha(`${pctCurto(n.valor / Math.max(1, n.pai.valor))} de ${n.pai.nome}`)) return;
    if (n.pai && n.pai !== F.raiz && !linha(`${pctCurto(n.valor / Math.max(1, F.raiz.valor))} do total`)) return;
    const qtos = filhos(n).length;
    if (qtos && !linha(`${qtos} ${qtos > 1 ? F.plural[filhos(n)[0].nivel] ?? "itens" : filhos(n)[0].nivel.toLowerCase()} dentro`)) return;
    if (F.cats.length > 1) {
      const t = n.mix.reduce((s2, v) => s2 + Math.max(0, v), 0) || 1;
      const ms = n.mix.map((v, i) => ({ i, f: Math.max(0, v) / t })).filter((m) => m.f >= 0.01).sort((a, b) => b.f - a.f);
      y += 8;
      for (const m of ms) {
        y += 17;
        if (y > fim) return;
        ctx.fillStyle = F.cats[m.i].cor;
        ctx.fillRect(x, y - 9, 10, 10);
        ctx.font = "400 12.5px Inter, system-ui, sans-serif";
        ctx.fillStyle = "#3d3a33";
        ctx.fillText(cortar(`${F.cats[m.i].nome} ${pctCurto(m.f)}`, larg), x + 16, y);
      }
    }
  }

  function botaoAbrir(n: No, cx: number, cy: number, r: number, lw: number) {
    const aberto = galho(n);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = aberto ? TINTA : n.ehOutros ? PAPEL : "#fff";
    ctx.fill();
    ctx.lineWidth = lw;
    ctx.strokeStyle = TINTA;
    ctx.stroke();
    ctx.fillStyle = aberto ? "#fff" : TINTA;
    ctx.font = `600 ${Math.round(r * 1.55)}px Inter, system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(aberto ? "−" : n.ehOutros ? "…" : abre(n) ? "+" : "›", cx, cy + r * 0.55);
    ctx.textAlign = "start";
  }

  function desenhar() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = PAPEL;
    ctx.fillRect(0, 0, W, H);
    ctx.textBaseline = "alphabetic";
    if (modo === "nivel") desenharNivel(); else desenharReal();
    cabecalhos();
    desenharMapa();
  }

  /** Modo "em cada nível": desenha no mundo (o texto cresce com o zoom). */
  function desenharNivel() {
    ctx.setTransform(dpr * cam.k, 0, 0, dpr * cam.k, dpr * cam.x, dpr * cam.y);
    const vis = { x0: -cam.x / cam.k, y0: -cam.y / cam.k, x1: (W - cam.x) / cam.k, y1: (H - cam.y) / cam.k };
    const trilha = noCaminho();
    const ordem = [...pos.keys()];
    const px = 1 / cam.k;

    // fitas: do pai (lado direito, repartido pelos filhos) até cada filho
    for (const n of ordem) {
      if (!galho(n)) continue;
      const p = posDe(n)!;
      const ks = visiveis(n).filter((f) => pos.has(f));
      const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
      let acc = 0;
      const x0 = p.x + LARG;
      let topoFilhos = Infinity;
      ks.forEach((f, rank) => {
        const q = posDe(f)!;
        topoFilhos = Math.min(topoFilhos, q.y);
        const s0 = p.y + (acc / tot) * p.h;
        acc += f.valor;
        const s1 = p.y + (acc / tot) * p.h;
        const x1 = q.x;
        if (Math.max(x0, x1) < vis.x0 || Math.min(x0, x1) > vis.x1 || Math.max(s1, q.y + q.h) < vis.y0 || Math.min(s0, q.y) > vis.y1) return;
        const xm = (x0 + x1) / 2;
        const naTrilha = trilha.has(f) || f === quente;
        ctx.globalAlpha = (f.ehOutros ? 0.35 : naTrilha ? 0.5 : 0.2) * alfaDe(f);
        ctx.fillStyle = corDe(f, rank, naTrilha);
        ctx.beginPath();
        ctx.moveTo(x0, s0);
        ctx.bezierCurveTo(xm, s0, xm, q.y, x1, q.y);
        ctx.lineTo(x1, q.y + q.h);
        ctx.bezierCurveTo(xm, q.y + q.h, xm, s1, x0, s1);
        ctx.closePath();
        ctx.fill();
      });
      // a lupa: quanto este bloco de filhos está ampliado em relação ao total
      const z = ampliacao(n, pos.get(n)!.h);
      if (z >= 1.5 && 11 * cam.k >= 7 && animT >= 1) {
        const t = `ampliado ${vezes(z)}×`;
        ctx.globalAlpha = 1;
        ctx.font = "italic 600 11.5px Inter, system-ui, sans-serif";
        const w = ctx.measureText(t).width + 26;
        const lx = x0 + VAO_COL / 2 - w / 2, ly = Math.min(topoFilhos, p.y) - 26;
        retangulo(lx, ly, w, 19, 9.5);
        ctx.fillStyle = "#fff";
        ctx.fill();
        ctx.lineWidth = px;
        ctx.strokeStyle = "#8a8475";
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(lx + 11, ly + 8.6, 3.6, 0, Math.PI * 2);
        ctx.moveTo(lx + 13.6, ly + 11.2); ctx.lineTo(lx + 16, ly + 13.6);
        ctx.lineWidth = 1.3;
        ctx.strokeStyle = CINZA;
        ctx.stroke();
        ctx.fillStyle = CINZA;
        ctx.fillText(t, lx + 20, ly + 13.5);
      }
    }
    ctx.globalAlpha = 1;

    const rotulosTela: { x: number; y: number; w: number; h: number; n: No }[] = [];
    for (const n of ordem) {
      const p = posDe(n)!;
      if (p.x > vis.x1 || p.x + LARG < vis.x0 || p.y > vis.y1 || p.y + p.h < vis.y0) continue;
      const rank = (n.pai ? visiveis(n.pai) : [n]).indexOf(n);
      const naTrilha = trilha.has(n);
      ctx.globalAlpha = alfaDe(n);
      retangulo(p.x, p.y, LARG, p.h, 4);
      ctx.fillStyle = n.ehOutros ? PAPEL : naTrilha ? "#fff3b0" : "#ffffff";
      ctx.fill();
      ctx.lineWidth = (naTrilha || n === quente ? 2 : 1) * px;
      ctx.strokeStyle = naTrilha || n === quente ? TINTA : "#c9c2b2";
      if (n.ehOutros) ctx.setLineDash([5 * px, 4 * px]);
      ctx.stroke();
      ctx.setLineDash([]);
      const fx = n.ehOutros ? 12 : 7;
      faixa(n, p.x, p.y, fx, p.h, rank, naTrilha);
      const alturaTela = p.h * cam.k;
      if (alturaTela >= 14 && 12 * cam.k >= 6) {
        const larg = LARG - fx - 40;
        if (p.h >= 120 && !n.ehOutros) caixaGrande(n, p, fx, larg);
        else {
          ctx.font = `${n.ehOutros ? "italic " : ""}600 13px Inter, system-ui, sans-serif`;
          ctx.fillStyle = n.ehOutros ? CINZA : TINTA;
          const cabem = Math.max(1, Math.min(3, Math.floor((p.h - 26) / 16)));
          const linhas = alturaTela >= 26 ? linhasDe(n.nome, larg, cabem) : linhasDe(n.nome, larg, 1);
          const blocoTxt = linhas.length * 16 + (alturaTela >= 30 ? 15 : 0);
          let y = p.y + Math.max(15, (p.h - blocoTxt) / 2 + 12);
          for (const l of linhas) { ctx.fillText(l, p.x + fx + 9, y); y += 16; }
          if (alturaTela >= 30) {
            ctx.font = "400 12px Inter, system-ui, sans-serif";
            ctx.fillStyle = CINZA;
            ctx.fillText(linhaValor(n, larg), p.x + fx + 9, y - 1);
          }
        }
        botaoAbrir(n, p.x + LARG - 18, p.y + Math.min(p.h / 2, 26), 9, 1.2 * px);
      } else if (LARG * cam.k >= 46 && alturaTela >= 12) {
        rotulosTela.push({ x: (p.x + fx) * cam.k + cam.x + 4, y: p.y * cam.k + cam.y, w: (LARG - fx) * cam.k - 8, h: alturaTela, n });
      }
    }
    ctx.globalAlpha = 1;

    // zoom afastado: o nome em letra de tamanho fixo na tela, para não virar só caixa
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    for (const r of rotulosTela) {
      ctx.font = `${r.n.ehOutros ? "italic " : ""}600 11px Inter, system-ui, sans-serif`;
      ctx.fillStyle = r.n.ehOutros ? CINZA : TINTA;
      const duas = r.h >= 30;
      ctx.fillText(cortar(r.n.nome, r.w), r.x, r.y + (duas ? r.h / 2 - 2 : r.h / 2 + 4));
      if (duas) {
        ctx.font = "400 10.5px Inter, system-ui, sans-serif";
        ctx.fillStyle = CINZA;
        ctx.fillText(cortar(moedaCurta(r.n.valor), r.w), r.x, r.y + r.h / 2 + 11);
      }
    }
  }

  /** Modo "tamanho real": tudo em pixels de tela, com o zoom vertical separado do horizontal. */
  function desenharReal() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const trilha = noCaminho();
    const ordem = [...pos.keys()];
    const fora = (y0: number, y1: number) => y1 < 0 || y0 > H;

    for (const n of ordem) {
      if (!galho(n)) continue;
      const p = posDe(n)!;
      const ks = visiveis(n).filter((f) => pos.has(f));
      const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
      let acc = 0;
      const x0 = sx(p.x + LARG);
      ks.forEach((f, rank) => {
        const q = posDe(f)!;
        const s0 = sy(p.y + (acc / tot) * p.h);
        acc += f.valor;
        const s1 = sy(p.y + (acc / tot) * p.h);
        const x1 = sx(q.x), t0 = sy(q.y), t1 = sy(q.y + q.h);
        if (x1 < 0 || x0 > W || fora(Math.min(s0, t0), Math.max(s1, t1))) return;
        const xm = (x0 + x1) / 2;
        const naTrilha = trilha.has(f) || f === quente;
        ctx.globalAlpha = (f.ehOutros ? 0.35 : naTrilha ? 0.5 : 0.22) * alfaDe(f);
        ctx.fillStyle = corDe(f, rank, naTrilha);
        ctx.beginPath();
        ctx.moveTo(x0, s0);
        ctx.bezierCurveTo(xm, s0, xm, t0, x1, t0);
        ctx.lineTo(x1, Math.max(t1, t0 + 0.6));
        ctx.bezierCurveTo(xm, Math.max(t1, t0 + 0.6), xm, Math.max(s1, s0 + 0.6), x0, Math.max(s1, s0 + 0.6));
        ctx.closePath();
        ctx.fill();
      });
    }
    ctx.globalAlpha = 1;

    for (const n of ordem) {
      const p = posDe(n)!;
      const x = sx(p.x), w = LARG * cam.k, y = sy(p.y), h = p.h * cam.ky;
      if (x > W || x + w < 0 || fora(y, y + h)) continue;
      const rank = (n.pai ? visiveis(n.pai) : [n]).indexOf(n);
      const naTrilha = trilha.has(n);
      ctx.globalAlpha = alfaDe(n);
      if (h < 3) {
        // um fio: só a cor, na largura da caixa
        ctx.fillStyle = naTrilha ? TINTA : n.ehOutros ? listras : typeof corDe(n, rank, false) === "string" ? (corDe(n, rank, false) as string) : "#8a8475";
        ctx.fillRect(x, y, w, Math.max(1, h));
        continue;
      }
      ctx.fillStyle = n.ehOutros ? PAPEL : naTrilha ? "#fff3b0" : "#ffffff";
      ctx.fillRect(x, y, w, h);
      ctx.lineWidth = naTrilha || n === quente ? 2 : 1;
      ctx.strokeStyle = naTrilha || n === quente ? TINTA : "#c9c2b2";
      if (n.ehOutros) ctx.setLineDash([5, 4]);
      ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
      ctx.setLineDash([]);
      const fx = Math.max(4, (n.ehOutros ? 12 : 7) * cam.k);
      faixa(n, x, y, fx, h, rank, naTrilha);
      if (h >= 14 && w >= 70) {
        const larg = w - fx - (h >= 22 ? 34 : 12);
        const tx = x + fx + 8;
        ctx.font = `${n.ehOutros ? "italic " : ""}600 12.5px Inter, system-ui, sans-serif`;
        ctx.fillStyle = n.ehOutros ? CINZA : TINTA;
        const linhas = h >= 48 ? linhasDe(n.nome, larg, Math.min(3, Math.floor((h - 22) / 15))) : [cortar(n.nome, larg)];
        const bloco = linhas.length * 15 + (h >= 30 ? 14 : 0);
        let ty = y + Math.max(13, (h - bloco) / 2 + 11);
        for (const l of linhas) { ctx.fillText(l, tx, ty); ty += 15; }
        if (h >= 30) {
          ctx.font = "400 11.5px Inter, system-ui, sans-serif";
          ctx.fillStyle = CINZA;
          ctx.fillText(linhaValor(n, larg), tx, ty - 1);
        }
        if (h >= 22) botaoAbrir(n, x + w - 16, y + Math.min(h / 2, 24), 8, 1.2);
      }
    }
    ctx.globalAlpha = 1;
  }

  /** Títulos das colunas, presos no alto da tela. */
  function cabecalhos() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const niveis = new Map<number, string>();
    for (const [n, p] of pos) if (!niveis.has(p.d)) niveis.set(p.d, n.nivel);
    ctx.fillStyle = "rgba(247,244,236,0.92)";
    ctx.fillRect(0, 0, W, 44);
    ctx.strokeStyle = "#ddd6c6";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, 44.5); ctx.lineTo(W, 44.5); ctx.stroke();
    let inicioProximo = W >= 720 ? W - 150 : W - 56;
    for (const [d, nivel] of [...niveis].sort((a, b) => b[0] - a[0])) {
      const x0 = sx(d * COL);
      if (x0 > W || x0 + LARG * cam.k < 0) continue;
      const x = Math.max(8, x0);
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      const titulo = (d === 0 ? nivel : F.plural[nivel] ?? nivel).toUpperCase();
      const largTitulo = ctx.measureText(titulo).width;
      // da direita para a esquerda: um título não pisa no seguinte (colunas estreitas, ou a de trás presa na borda)
      if (x + largTitulo + 12 > inicioProximo) continue;
      inicioProximo = x;
      ctx.fillStyle = CINZA;
      ctx.fillText(titulo, x, 19);
      if (F.explica[nivel] && LARG * cam.k > 120) {
        ctx.font = "400 11px Inter, system-ui, sans-serif";
        ctx.fillStyle = "#8a8475";
        const lim = Math.min(Math.max(80, Math.min(COL * cam.k - 16, 320)), (W >= 720 ? W - 160 : W - 8) - x);
        ctx.fillText(cortar(F.explica[nivel], lim), x, 34);
      }
    }
  }

  // ——— minimapa: a árvore inteira, com o retângulo do que está na tela ———
  const MW = 200, MH = 128;
  let mapaT = { sxm: 1, sym: 1, x0: 0, y0: 0, ox: 0, oy: 0 };
  function desenharMapa() {
    if (getComputedStyle(mapa).display === "none") return;
    if (mapa.width !== MW * dpr) { mapa.width = MW * dpr; mapa.height = MH * dpr; mapa.style.width = `${MW}px`; mapa.style.height = `${MH}px`; }
    const b = caixaDe([...pos.keys()]);
    if (!Number.isFinite(b.x0)) return;
    const s = Math.min((MW - 12) / (b.x1 - b.x0), (MH - 12) / (b.y1 - b.y0));
    const ox = (MW - (b.x1 - b.x0) * s) / 2, oy = (MH - (b.y1 - b.y0) * s) / 2;
    mapaT = { sxm: s, sym: s, x0: b.x0, y0: b.y0, ox, oy };
    mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    mctx.clearRect(0, 0, MW, MH);
    mctx.fillStyle = "rgba(255,255,255,0.92)";
    mctx.fillRect(0, 0, MW, MH);
    const trilha = noCaminho();
    for (const [n, p] of pos) {
      mctx.fillStyle = trilha.has(n) ? VERDE : n.ehOutros ? "#e6e0d2" : "#b5ad9b";
      mctx.fillRect(ox + (p.x - b.x0) * s, oy + (p.y - b.y0) * s, Math.max(1, LARG * s), Math.max(1, p.h * s));
    }
    const v0 = paraMundo(0, 0), v1 = paraMundo(W, H);
    mctx.strokeStyle = TINTA;
    mctx.lineWidth = 1.5;
    mctx.strokeRect(ox + (v0.x - b.x0) * s, oy + (v0.y - b.y0) * s, Math.max(3, (v1.x - v0.x) * s), Math.max(3, (v1.y - v0.y) * s));
  }
  let arrastandoMapa = false;
  const irPeloMapa = (e: PointerEvent) => {
    const r = mapa.getBoundingClientRect();
    const wx = (e.clientX - r.left - mapaT.ox) / mapaT.sxm + mapaT.x0, wy = (e.clientY - r.top - mapaT.oy) / mapaT.sym + mapaT.y0;
    camT = 1;
    cam.x = W / 2 - wx * cam.k;
    cam.y = H / 2 - wy * cam.ky;
    pedir();
  };
  mapa.addEventListener("pointerdown", (e) => { arrastandoMapa = true; mapa.setPointerCapture(e.pointerId); irPeloMapa(e); });
  mapa.addEventListener("pointermove", (e) => { if (arrastandoMapa) irPeloMapa(e); });
  mapa.addEventListener("pointerup", () => { arrastandoMapa = false; });

  // ——— lista para leitor de tela: a mesma árvore aberta, em HTML ———
  let alvosLista: No[] = [];
  function atualizarLista() {
    alvosLista = [];
    const item = (n: No): string => {
      const ks = galho(n) ? visiveis(n) : [];
      alvosLista.push(n);
      const rot = `${n.nivel}: ${n.nome}, ${moedaCurta(n.valor)}${n.pai ? `, ${pctCurto(n.valor / Math.max(1, n.pai.valor))} de ${n.pai.nome}` : ""}`;
      return `<li><button type="button" data-l="${alvosLista.length - 1}" ${abre(n) ? `aria-expanded="${galho(n)}"` : ""}>${esc(rot)}</button>${ks.length ? `<ul>${ks.map(item).join("")}</ul>` : ""}</li>`;
    };
    listaEl.innerHTML = `<ul>${item(F.raiz)}</ul>`;
  }
  listaEl.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-l]");
    if (b) escolher(alvosLista[Number(b.dataset.l)], true);
  });

  // ——— procurar ———
  const normal = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  let indice: { n: No; chave: string }[] | null = null;
  function montarIndice() {
    const out: { n: No; chave: string }[] = [];
    const andar = (n: No) => { for (const f of filhos(n)) { out.push({ n: f, chave: normal(f.nome) }); andar(f); } };
    andar(F.raiz);
    return out;
  }
  let achados: No[] = [];
  function procurar() {
    const q = normal(campo.value.trim());
    if (q.length < 2) { resultados.innerHTML = ""; achados = []; return; }
    indice ??= montarIndice();
    const partes = q.split(/\s+/);
    achados = indice.filter((i) => partes.every((t) => i.chave.includes(t))).map((i) => i.n).sort((a, b) => b.valor - a.valor).slice(0, 14);
    resultados.innerHTML = achados.length
      ? achados.map((n, i) => `<li><button type="button" data-r="${i}"><span class="cc4-r-nome">${esc(n.nome)}</span>
          <span class="cc4-r-onde">${esc(n.nivel)} · ${esc(caminhoAte(n).slice(1, -1).map((x) => x.nome).join(" › ") || "primeiro nível")}</span>
          <span class="cc4-r-valor">${moedaCurta(n.valor)}</span></button></li>`).join("")
      : `<li class="cc4-r-nada">Nada com “${esc(campo.value.trim())}”.</li>`;
  }
  campo.addEventListener("input", procurar);
  campo.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { abrirBusca(false); caixa.focus(); }
    if (e.key === "Enter" && achados[0]) irAte(achados[0]);
    e.stopPropagation();
  });
  resultados.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-r]");
    if (b) irAte(achados[Number(b.dataset.r)]);
  });
  function abrirBusca(abrir = busca.hidden) {
    busca.hidden = !abrir;
    if (abrir) { campo.focus(); campo.select(); }
  }
  /** Abre o caminho até o item (mostrando-o mesmo que esteja no "mais N") e leva a tela até ele. */
  function irAte(n: No) {
    const c = caminhoAte(n);
    for (let i = 1; i < c.length; i++) {
      const pai = c[i - 1], filho = c[i];
      if (!visiveis(pai).includes(filho)) mostrar.set(pai, Math.max(mostrar.get(pai) ?? K_INICIAL, filhos(pai).indexOf(filho) + 2));
      if (!visiveis(pai).includes(filho)) mostrar.set(pai, filhos(pai).length);
    }
    abrirBusca(false);
    escolher(n, false, false);
    setTimeout(() => {
      enquadrar(caixaDe([n, ...(galho(n) ? visiveis(n) : [])]), 1);
      if (cartaoAberto() && !galho(n)) setTimeout(() => desviarDoCartao(n), 480);
    }, 40);
  }

  // ——— o fio (degraus) e os detalhes ———
  function atualizarFio() {
    const c = sel ? caminhoAte(sel) : [F.raiz];
    fioEl.innerHTML = c.map((n, i) => `<li><button type="button" data-fio="${i}" ${i === c.length - 1 ? 'aria-current="step"' : ""}>
      <span class="cc4-fio-tipo">${esc(n.nivel)}</span><span class="cc4-fio-nome">${esc(n.nome)}</span>
      <span class="cc4-fio-valor">${moedaCurta(n.valor)}${i ? ` · ${pctCurto(n.valor / Math.max(1, n.pai!.valor))}` : ""}</span></button></li>`).join("");
    fioEl.querySelectorAll<HTMLButtonElement>("[data-fio]").forEach((b) => b.addEventListener("click", () => {
      const n = c[Number(b.dataset.fio)];
      escolher(n, false, false);
      setTimeout(() => enquadrar(caixaDe([n, ...(galho(n) ? visiveis(n) : [])]), 1.1), 40);
    }));
  }

  function mostrarCartao(n: No | null) {
    if (!n || n.ehOutros) { cartao.hidden = true; return; }
    resumoEl.innerHTML = `<span class="cc4-resumo-nome">${esc(n.nome)}</span><span class="cc4-resumo-valor">${moedaCurta(n.valor)}</span><span class="cc4-resumo-abrir">Detalhes</span>`;
    conteudo.innerHTML = op.cartao(n);
    cartao.classList.toggle("min", minimizado);
    cartao.hidden = false;
  }

  function escolher(n: No, alternar: boolean, mover = true) {
    if (n.ehOutros && n.pai) {
      mostrar.set(n.pai, (mostrar.get(n.pai) ?? K_INICIAL) + MAIS);
      relayout();
      return;
    }
    sel = n;
    for (const a of caminhoAte(n).slice(0, -1)) abertos.add(a);
    if (abre(n)) {
      if (alternar && abertos.has(n)) {
        // fecha a caixa e tudo o que estava aberto dentro
        const fechar = (x: No) => { abertos.delete(x); for (const f of filhos(x)) if (abertos.has(f)) fechar(f); };
        fechar(n);
      } else abertos.add(n);
    }
    op.aoEscolher(n);
    atualizarFio();
    mostrarCartao(n);
    relayout();
    if (!mover) return;
    if (galho(n)) setTimeout(() => mostrarGalho(n), 30);
    else setTimeout(() => desviarDoCartao(n), 30);
  }

  // ——— interação ———
  function noEm(px: number, py: number): No | null {
    const m = paraMundo(px, py);
    // fios finos (tamanho real): pelo menos 6 px de tela para acertar o clique
    const folga = (p: Pos) => Math.max(0, (6 / cam.ky - p.h) / 2);
    let melhor: No | null = null, dist = Infinity;
    for (const [n, p] of pos) {
      if (m.x < p.x || m.x > p.x + LARG) continue;
      const f = folga(p);
      if (m.y >= p.y - f && m.y <= p.y + p.h + f) {
        const d = Math.abs(m.y - (p.y + p.h / 2));
        if (d < dist) { dist = d; melhor = n; }
      }
    }
    return melhor;
  }

  function htmlBalao(n: No): string {
    const t = n.mix.reduce((a, v) => a + Math.max(0, v), 0) || 1;
    const barra = F.cats.length > 1 && !n.ehOutros
      ? `<span class="cc4-b-mix">${n.mix.map((v, i) => (v > 0 ? `<b style="flex:${v / t};background:${F.cats[i].cor}"></b>` : "")).join("")}</span>
         <span class="cc4-b-cat">${esc(F.cats[catPrincipal(n)].nome)}: ${pctCurto(n.mix[catPrincipal(n)] / t)}</span>`
      : "";
    return `<span class="cc4-b-nivel">${esc(n.nivel)}${n.ehOutros ? " · os menores, juntos" : F.explica[n.nivel] ? ` · ${esc(F.explica[n.nivel])}` : ""}</span>
      <strong>${esc(n.nome)}</strong>
      <span class="cc4-b-valor">${moedaCurta(n.valor)}${n.pai ? ` · ${pctCurto(n.valor / Math.max(1, n.pai.valor))} de ${esc(n.pai.nome)}` : ""}</span>
      ${n !== F.raiz && n.pai !== F.raiz ? `<span>${pctCurto(n.valor / Math.max(1, F.raiz.valor))} do total</span>` : ""}
      ${barra}
      <span class="cc4-b-dica">${n.ehOutros ? "Clique para ver mais 10" : abre(n) ? (galho(n) ? "Clique para fechar · detalhes ao lado" : "Clique para abrir · detalhes ao lado") : "Clique para ver os detalhes"}</span>`;
  }

  const toques = new Map<number, { x: number; y: number }>();
  let arrasto: { x: number; y: number; cx: number; cy: number; moveu: boolean } | null = null;
  let pinca: { d: number; base: Camera; mx: number; my: number } | null = null;
  const local = (e: PointerEvent | WheelEvent | MouseEvent) => {
    const r = cv.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  cv.addEventListener("pointerdown", (e) => {
    cv.setPointerCapture(e.pointerId);
    const p = local(e);
    toques.set(e.pointerId, p);
    camT = 1;
    if (toques.size === 1) arrasto = { x: p.x, y: p.y, cx: cam.x, cy: cam.y, moveu: false };
    else if (toques.size === 2) {
      const [a, b] = [...toques.values()];
      pinca = { d: Math.hypot(a.x - b.x, a.y - b.y), base: { ...cam }, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
      arrasto = null;
    }
  });
  cv.addEventListener("pointermove", (e) => {
    const p = local(e);
    if (toques.has(e.pointerId)) toques.set(e.pointerId, p);
    if (pinca && toques.size === 2) {
      const [a, b] = [...toques.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      // o ponto do mundo que estava sob os dedos continua sob eles
      zoomPara(pinca.base, d / Math.max(1, pinca.d), pinca.mx, pinca.my, (a.x + b.x) / 2, (a.y + b.y) / 2);
      pedir();
      return;
    }
    if (arrasto) {
      const dx = p.x - arrasto.x, dy = p.y - arrasto.y;
      if (Math.abs(dx) + Math.abs(dy) > 5) arrasto.moveu = true;
      if (arrasto.moveu) { cam.x = arrasto.cx + dx; cam.y = arrasto.cy + dy; balao.hidden = true; pedir(); }
      return;
    }
    if (e.pointerType === "mouse") {
      const n = noEm(p.x, p.y);
      if (n !== quente) {
        quente = n;
        cv.style.cursor = n ? "pointer" : "grab";
        pedir();
        if (n) balao.innerHTML = htmlBalao(n);
      }
      if (n) {
        balao.hidden = false;
        const bw = balao.offsetWidth || 290, bh = balao.offsetHeight || 120;
        const bx = p.x + 18 + bw > W ? p.x - bw - 12 : p.x + 18;
        const by = Math.min(Math.max(50, p.y + 16), H - bh - 8);
        balao.style.transform = `translate(${bx}px, ${by}px)`;
      } else balao.hidden = true;
    }
  });
  const soltar = (e: PointerEvent) => {
    const p = local(e);
    const era = arrasto;
    toques.delete(e.pointerId);
    if (toques.size < 2) pinca = null;
    if (toques.size === 0) arrasto = null;
    if (era && !era.moveu && e.type === "pointerup") {
      const n = noEm(p.x, p.y);
      if (n) { escolher(n, true); balao.innerHTML = htmlBalao(n); }
    }
  };
  cv.addEventListener("pointerup", soltar);
  cv.addEventListener("pointercancel", soltar);
  cv.addEventListener("pointerleave", () => { if (quente) { quente = null; pedir(); } balao.hidden = true; });
  cv.addEventListener("dblclick", (e) => {
    const p = local(e);
    const n = noEm(p.x, p.y);
    if (!n) return;
    enquadrar(caixaDe([n, ...(galho(n) ? visiveis(n) : [])]), 2);
  });
  cv.addEventListener("wheel", (e) => {
    e.preventDefault();
    const p = local(e);
    // pinça no trackpad (ctrl) e roda do mouse (linhas): zoom; dois dedos no trackpad: andar
    if (e.ctrlKey || e.metaKey || e.deltaMode === 1 || (Math.abs(e.deltaY) >= 50 && e.deltaX === 0 && Number.isInteger(e.deltaY))) {
      zoomEm(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0018) * (e.deltaMode === 1 ? 16 : 1)), p.x, p.y);
    } else {
      camT = 1;
      cam.x -= e.deltaX;
      cam.y -= e.deltaY;
      pedir();
    }
    balao.hidden = true;
  }, { passive: false });

  caixa.addEventListener("keydown", (e) => {
    const passo = 60;
    if (e.key === "ArrowLeft") cam.x += passo; else if (e.key === "ArrowRight") cam.x -= passo;
    else if (e.key === "ArrowUp") cam.y += passo; else if (e.key === "ArrowDown") cam.y -= passo;
    else if (e.key === "+" || e.key === "=") zoomEm(1.25, W / 2, H / 2);
    else if (e.key === "-") zoomEm(0.8, W / 2, H / 2);
    else if (e.key === "/") abrirBusca(true);
    else if (e.key === "Escape" && !busca.hidden) abrirBusca(false);
    else if (e.key === "Escape" && caixa.classList.contains("cheia")) alternarCheia();
    else return;
    e.preventDefault();
    pedir();
  });

  function alternarCheia() {
    const cheia = !caixa.classList.contains("cheia");
    if (cheia) {
      caixa.classList.add("cheia");
      document.documentElement.classList.add("cc4-sem-rolar");
      caixa.requestFullscreen?.().catch(() => {});
    } else {
      caixa.classList.remove("cheia");
      document.documentElement.classList.remove("cc4-sem-rolar");
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    }
    caixa.querySelector(".cc4-cheia-btn span")!.textContent = cheia ? "Sair da tela cheia" : "Tela cheia";
    caixa.focus();
  }
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement && caixa.classList.contains("cheia")) alternarCheia();
  });

  let tempoAviso = 0;
  function trocarModo() {
    modo = modo === "nivel" ? "real" : "nivel";
    caixa.querySelector(".cc4-modo-btn")!.setAttribute("aria-pressed", String(modo === "real"));
    // o aviso aparece por alguns segundos, para não cobrir o desenho
    avisoEl.hidden = modo !== "real";
    clearTimeout(tempoAviso);
    if (modo === "real") tempoAviso = window.setTimeout(() => { avisoEl.hidden = true; }, 7000);
    if (modo === "nivel") cam.ky = cam.k;
    relayout();
    const foco = sel ?? F.raiz;
    setTimeout(() => enquadrar(caixaDe(modo === "real" ? [...pos.keys()] : [foco, ...(galho(foco) ? visiveis(foco) : [])]), 1.1), 30);
  }

  caixa.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-acao]");
    if (!b) return;
    const a = b.dataset.acao;
    if (a === "cheia") alternarCheia();
    else if (a === "procurar") abrirBusca();
    else if (a === "modo") trocarModo();
    else if (a === "mais") zoomEm(1.3, W / 2, H / 2);
    else if (a === "menos") zoomEm(1 / 1.3, W / 2, H / 2);
    else if (a === "ajustar") enquadrar(caixaDe([...pos.keys()]), 1.1);
    else if (a === "fechar") {
      abertos.clear(); abertos.add(F.raiz); mostrar.clear(); sel = null;
      op.aoEscolher(F.raiz); atualizarFio(); mostrarCartao(null); relayout();
      setTimeout(() => enquadrar(caixaDe([...pos.keys()]), 1.1), 40);
    } else if (a === "detalhes") { minimizado = false; cartao.classList.remove("min"); if (sel) setTimeout(() => desviarDoCartao(sel!), 30); }
    else if (a === "min-cartao") { minimizado = true; cartao.classList.add("min"); }
  });

  // ——— tamanho ———
  function medirTela() {
    const r = caixa.getBoundingClientRect();
    dpr = window.devicePixelRatio || 1;
    const novoW = Math.max(200, Math.floor(r.width)), novoH = Math.max(200, Math.floor(r.height));
    if (W && (novoW !== W || novoH !== H)) { cam.x += (novoW - W) / 2; cam.y += (novoH - H) / 2; }
    W = novoW; H = novoH;
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = `${W}px`; cv.style.height = `${H}px`;
    pedir();
  }
  new ResizeObserver(medirTela).observe(caixa);

  medirTela();
  // no celular os detalhes começam fechados (uma linha embaixo), para sobrar tela
  minimizado = W < 720;
  pos = calcular();
  atualizarLista();
  atualizarFio();
  mostrarCartao(sel);
  // começa mostrando o último galho aberto; no celular, só ele (o caminho inteiro ficaria pequeno demais)
  const foco = sel ? (galho(sel) ? sel : sel.pai ?? F.raiz) : F.raiz;
  const inicio = W < 720 ? (galho(foco) ? visiveis(foco) : [foco]) : [...caminhoAte(foco), ...(galho(foco) ? visiveis(foco) : [])];
  enquadrar(caixaDe(inicio), 1, false);
  if (sel) requestAnimationFrame(() => desviarDoCartao(sel!));
  document.fonts?.ready.then(pedir);

  return { fonte: F, raiz: caixa, redesenhar: () => { atualizarFio(); if (sel) mostrarCartao(sel); pedir(); } };
}
