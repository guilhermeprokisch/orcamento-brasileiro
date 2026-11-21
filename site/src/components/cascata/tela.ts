/**
 * Forma 4 do protótipo da cascata: a tela livre, em Canvas 2D. Uma árvore da esquerda para a direita, como um mapa
 * mental, em que cada caixa abre os filhos (vários galhos abertos ao mesmo tempo). Arrasta para andar, roda ou pinça
 * para o zoom, e há tela cheia. Os nomes aparecem conforme o zoom (abaixo de um tamanho, só a caixa).
 *
 * Tamanhos: os filhos de uma caixa dividem um bloco de pelo menos 280 px, em proporção ao valor (com um mínimo para
 * caber o nome). Por isso cada nível é um "zoom" do anterior, e a fita do pai até os filhos se abre como um funil.
 */
import { moedaCurta, pct } from "../../lib/formato";
import { RAMPA } from "../../lib/cores";
import { caminhoAte, catPrincipal, filhos, type Fonte, type No } from "./dados";

export interface OpcoesTela {
  usaTipo: () => boolean;
  caminhoInicial: No[];
  aoEscolher: (n: No) => void;
  cartao: (n: No) => string;
}

export interface Tela {
  fonte: Fonte;
  raiz: HTMLElement;
  redesenhar(): void;
}

const LARG = 250;          // largura da caixa (mundo)
const VAO_COL = 150;        // espaço das fitas entre colunas
const COL = LARG + VAO_COL;
const MIN_H = 58;           // altura mínima de uma caixa: nome em duas linhas + valor
const BLOCO = 320;          // altura mínima do bloco de filhos
const ALT_RAIZ = 440;
const VAO = 8;
const VAO_GALHO = 26;
const K_INICIAL = 8;        // quantos filhos aparecem antes do "mais N"
const MAIS = 10;            // quantos o "mais N" abre de cada vez

const VERDE = "#0e6b3b";
const PAPEL = "#f7f4ec";
const TINTA = "#191919";
const AREIA = "#c3bba7";

interface Pos { x: number; y: number; h: number; d: number }

const facil = (t: number) => 1 - Math.pow(1 - t, 3);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const pctCurto = (v: number) => (v >= 0.995 ? "100%" : v >= 0.1 ? `${Math.round(v * 100)}%` : v >= 0.001 ? pct(v) : "<0,1%");
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export function criarTela(host: HTMLElement, F: Fonte, op: OpcoesTela): Tela {
  host.innerHTML = `<div class="cc4" tabindex="-1">
    <canvas class="cc4-canvas" aria-label="Tela livre do gasto: arraste para andar, use a roda ou pinça para o zoom, clique numa caixa para abrir."></canvas>
    <div class="cc4-topo"><ol class="cc4-fio"></ol></div>
    <div class="cc4-botoes cc4-canto">
      <button type="button" data-acao="cheia" class="cc4-cheia-btn"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg><span>Tela cheia</span></button>
    </div>
    <div class="cc4-botoes cc4-zoom">
      <button type="button" data-acao="procurar" class="cc4-procurar-btn"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg><span>Procurar</span></button>
      <button type="button" data-acao="mais" aria-label="Aproximar">+</button>
      <button type="button" data-acao="menos" aria-label="Afastar">−</button>
      <button type="button" data-acao="ajustar">Ver tudo</button>
      <button type="button" data-acao="fechar">Fechar galhos</button>
    </div>
    <div class="cc4-dica">Arraste para andar · roda ou pinça: zoom · clique: abrir · duplo clique: focar · /: procurar</div>
    <div class="cc4-busca" hidden>
      <input type="search" placeholder="Procurar órgão, programa, ação, fornecedor…" aria-label="Procurar na árvore" autocomplete="off" />
      <ol class="cc4-resultados" aria-live="polite"></ol>
    </div>
    <canvas class="cc4-mapa" aria-hidden="true"></canvas>
    <nav class="cc4-lista visually-hidden" aria-label="A árvore aberta, em lista"></nav>
    <div class="cc4-balao" hidden></div>
    <aside class="cc4-cartao" hidden><button type="button" class="cc4-x" data-acao="fechar-cartao" aria-label="Fechar">×</button><div></div></aside>
  </div>`;
  const caixa = host.querySelector<HTMLElement>(".cc4")!;
  const cv = caixa.querySelector<HTMLCanvasElement>("canvas")!;
  const ctx = cv.getContext("2d")!;
  const balao = caixa.querySelector<HTMLElement>(".cc4-balao")!;
  const cartao = caixa.querySelector<HTMLElement>(".cc4-cartao")!;
  const fioEl = caixa.querySelector<HTMLElement>(".cc4-fio")!;
  const busca = caixa.querySelector<HTMLElement>(".cc4-busca")!;
  const campo = busca.querySelector<HTMLInputElement>("input")!;
  const resultados = busca.querySelector<HTMLElement>(".cc4-resultados")!;
  const mapa = caixa.querySelector<HTMLCanvasElement>(".cc4-mapa")!;
  const mctx = mapa.getContext("2d")!;
  const listaEl = caixa.querySelector<HTMLElement>(".cc4-lista")!;

  // ——— estado ———
  const abertos = new Set<No>();
  const mostrar = new Map<No, number>();
  const outrosDe = new Map<No, No>();
  let sel: No | null = null;
  let quente: No | null = null;
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
  const cam = { k: 1, x: 40, y: 40 };
  let camDe = { ...cam }, camPara = { ...cam }, camT = 1, camIni = 0;

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

  function alturas(n: No, h: number): number[] {
    const ks = visiveis(n);
    const bloco = Math.max(h, BLOCO);
    const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
    const util = bloco - VAO * (ks.length - 1);
    return ks.map((f) => Math.max(MIN_H, (f.valor / tot) * util));
  }

  /** Mede (altura ocupada por cada galho) e posiciona. */
  function calcular() {
    const ext = new Map<No, number>();
    const hs = new Map<No, number>();
    const medir = (n: No, h: number): number => {
      hs.set(n, h);
      let e = h;
      if (abertos.has(n) && abre(n)) {
        const ks = visiveis(n);
        const hk = alturas(n, h);
        let soma = 0;
        ks.forEach((f, i) => {
          const ef = medir(f, hk[i]);
          const galho = abertos.has(f) && abre(f);
          soma += ef + (i ? (galho || (abertos.has(ks[i - 1]) && abre(ks[i - 1])) ? VAO_GALHO : VAO) : 0);
        });
        e = Math.max(h, soma);
      }
      ext.set(n, e);
      return e;
    };
    const novo = new Map<No, Pos>();
    const por = (n: No, d: number, topo: number) => {
      const h = hs.get(n)!, e = ext.get(n)!;
      novo.set(n, { x: d * COL, y: topo + (e - h) / 2, h, d });
      if (abertos.has(n) && abre(n)) {
        const ks = visiveis(n);
        const soma = ks.reduce((s, f, i) => s + ext.get(f)! + (i ? ((abertos.has(f) && abre(f)) || (abertos.has(ks[i - 1]) && abre(ks[i - 1])) ? VAO_GALHO : VAO) : 0), 0);
        let y = topo + (e - soma) / 2;
        ks.forEach((f, i) => {
          if (i) y += (abertos.has(f) && abre(f)) || (abertos.has(ks[i - 1]) && abre(ks[i - 1])) ? VAO_GALHO : VAO;
          por(f, d + 1, y);
          y += ext.get(f)!;
        });
      }
    };
    medir(F.raiz, ALT_RAIZ);
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

  // ——— câmera ———
  function caixaDe(ns: No[]) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const n of ns) {
      const p = pos.get(n);
      if (!p) continue;
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x + LARG); y1 = Math.max(y1, p.y + p.h);
    }
    return { x0, y0, x1, y1 };
  }
  function enquadrar(b: { x0: number; y0: number; x1: number; y1: number }, kMax = 1.1, animar = true) {
    if (!Number.isFinite(b.x0) || !W) return;
    // embaixo do fio (os degraus no alto) e acima dos botões
    const fioBaixo = fioEl.getBoundingClientRect().bottom - caixa.getBoundingClientRect().top;
    const m = W < 640 ? 24 : 70, topo = Math.max(64, fioBaixo + 12), baixo = W < 640 ? 70 : 60;
    const k = Math.min(kMax, (W - 2 * m) / (b.x1 - b.x0), (H - topo - baixo) / (b.y1 - b.y0));
    const kk = Math.max(0.05, k);
    const alvo = { k: kk, x: (W - (b.x1 - b.x0) * kk) / 2 - b.x0 * kk, y: topo + (H - topo - baixo - (b.y1 - b.y0) * kk) / 2 - b.y0 * kk };
    irPara(alvo, animar);
  }
  function irPara(alvo: { k: number; x: number; y: number }, animar = true) {
    camDe = { ...cam };
    camPara = alvo;
    camT = animar ? 0 : 1;
    camIni = performance.now();
    if (!animar) Object.assign(cam, alvo);
    pedir();
  }
  function zoomEm(fator: number, sx: number, sy: number) {
    camT = 1;
    const k = Math.min(4, Math.max(0.03, cam.k * fator));
    const f = k / cam.k;
    cam.x = sx - (sx - cam.x) * f;
    cam.y = sy - (sy - cam.y) * f;
    cam.k = k;
    pedir();
  }
  const paraMundo = (sx: number, sy: number) => ({ x: (sx - cam.x) / cam.k, y: (sy - cam.y) / cam.k });

  /** Depois de abrir uma caixa: se ela e os filhos não couberem na tela, anda (e afasta, se preciso) até caberem. */
  function mostrarGalho(n: No) {
    // no celular, só os filhos (a caixa aberta fica na borda, com a fita saindo dela)
    const ns = W < 640 && abertos.has(n) ? visiveis(n) : [n, ...(abertos.has(n) ? visiveis(n) : [])];
    const b = caixaDe(ns);
    const s0 = { x: b.x0 * cam.k + cam.x, y: b.y0 * cam.k + cam.y, x1: b.x1 * cam.k + cam.x, y1: b.y1 * cam.k + cam.y };
    const cabe = s0.x >= 0 && s0.x1 <= W && s0.y >= 50 && s0.y1 <= H - 40;
    if (!cabe) enquadrar(b, W < 640 ? 1 : Math.max(cam.k, 0.5));
  }

  /** O cartão do fim do caminho fica à direita (embaixo, no celular): anda para a caixa escolhida não ficar atrás dele. */
  function desviarDoCartao(n: No) {
    const p = pos.get(n);
    if (!p) return;
    const r = cartao.getBoundingClientRect(), c = caixa.getBoundingClientRect();
    const sx1 = (p.x + LARG) * cam.k + cam.x, sy1 = (p.y + p.h) * cam.k + cam.y;
    const limX = r.left - c.left - 24, limY = r.top - c.top - 16;
    if (W >= 720 && sx1 > limX) irPara({ ...cam, x: cam.x - (sx1 - limX) });
    else if (W < 720 && sy1 > limY) irPara({ ...cam, y: cam.y - (sy1 - limY) });
  }

  // ——— desenho ———
  let pedido = 0;
  function pedir() { if (!pedido) pedido = requestAnimationFrame(quadro); }

  function quadro(t: number) {
    pedido = 0;
    let mais = false;
    if (animT < 1) { animT = Math.min(1, (t - animIni) / DUR); mais = true; }
    if (camT < 1) {
      camT = Math.min(1, (t - camIni) / 420);
      const e = facil(camT);
      cam.k = lerp(camDe.k, camPara.k, e); cam.x = lerp(camDe.x, camPara.x, e); cam.y = lerp(camDe.y, camPara.y, e);
      mais = true;
    }
    desenhar();
    if (mais) pedir();
  }

  const noCaminho = () => new Set(sel ? caminhoAte(sel) : []);

  function corDe(n: No, rank: number, trilha: boolean): string {
    if (n.ehOutros) return AREIA;
    if (op.usaTipo()) return F.cats[catPrincipal(n)].cor;
    if (trilha || n === F.raiz) return VERDE;
    return RAMPA[Math.min(rank + 1, RAMPA.length - 1)];
  }

  function linhasDe(nome: string, larg: number, max: number): string[] {
    const ps = nome.split(/\s+/);
    const out: string[] = [];
    let l = "";
    for (const p of ps) {
      const t = l ? `${l} ${p}` : p;
      if (ctx.measureText(t).width <= larg || !l) l = t;
      else { out.push(l); l = p; if (out.length === max) break; }
    }
    if (out.length < max && l) out.push(l);
    if (out.length > max) out.length = max;
    // a última linha cortada com reticências, se sobrou texto
    const usado = out.join(" ").length;
    if (usado < nome.length) {
      let u = out[out.length - 1];
      while (u.length > 1 && ctx.measureText(`${u}…`).width > larg) u = u.slice(0, -1);
      out[out.length - 1] = `${u.trimEnd()}…`;
    }
    return out.map((s) => {
      let u = s;
      if (ctx.measureText(u).width <= larg) return u;
      while (u.length > 1 && ctx.measureText(`${u}…`).width > larg) u = u.slice(0, -1);
      return `${u}…`;
    });
  }

  const rotulosTela: { x: number; y: number; w: number; h: number; n: No }[] = [];

  function cortar(t: string, larg: number): string {
    if (ctx.measureText(t).width <= larg) return t;
    let u = t;
    while (u.length > 1 && ctx.measureText(`${u}…`).width > larg) u = u.slice(0, -1);
    return `${u.trimEnd()}…`;
  }

  /** Caixa alta (os níveis de cima, ou um item que é quase tudo): em vez de espaço vazio, o resumo do que tem dentro. */
  function caixaGrande(n: No, p: Pos, fx: number, larg: number, parte: number) {
    const x = p.x + fx + 12;
    let y = p.y + 18;
    const fim = p.y + p.h - 10;
    ctx.fillStyle = "#5c574c";
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
    if (n.pai) {
      y += 18;
      if (y > fim) return;
      ctx.font = "400 12.5px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#3d3a33";
      ctx.fillText(cortar(`${pctCurto(parte)} de ${n.pai.nome}`, larg + 20), x, y);
    }
    const qtos = filhos(n).length;
    if (qtos) {
      y += 17;
      if (y > fim) return;
      ctx.font = "400 12.5px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#3d3a33";
      const pl = filhos(n)[0].nivel;
      ctx.fillText(`${qtos} ${qtos > 1 ? F.plural[pl] ?? "itens" : pl.toLowerCase()} dentro`, x, y);
    }
    // a mistura por categoria (obrigatória, escolha do governo…), uma linha por categoria
    if (F.cats.length > 1) {
      const t = n.mix.reduce((s2, v) => s2 + Math.max(0, v), 0) || 1;
      const linhas = n.mix.map((v, i) => ({ i, f: Math.max(0, v) / t })).filter((m) => m.f >= 0.01).sort((a, b) => b.f - a.f);
      y += 10;
      for (const m of linhas) {
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

  function desenhar() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = PAPEL;
    ctx.fillRect(0, 0, W, H);
    ctx.setTransform(dpr * cam.k, 0, 0, dpr * cam.k, dpr * cam.x, dpr * cam.y);
    const vis = { x0: -cam.x / cam.k, y0: -cam.y / cam.k, x1: (W - cam.x) / cam.k, y1: (H - cam.y) / cam.k };
    const trilha = noCaminho();
    const ordem = [...pos.keys()];

    // fitas: do pai (lado direito, repartido pelos filhos) até cada filho
    for (const n of ordem) {
      if (!abertos.has(n) || !abre(n)) continue;
      const p = posDe(n)!;
      const ks = visiveis(n).filter((f) => pos.has(f));
      const tot = ks.reduce((s, f) => s + f.valor, 0) || 1;
      let acc = 0;
      const x0 = p.x + LARG;
      ks.forEach((f, rank) => {
        const q = posDe(f)!;
        const s0 = p.y + (acc / tot) * p.h;
        acc += f.valor;
        const s1 = p.y + (acc / tot) * p.h;
        const x1 = q.x;
        if (Math.max(x0, x1) < vis.x0 || Math.min(x0, x1) > vis.x1 || Math.max(s1, q.y + q.h) < vis.y0 || Math.min(s0, q.y) > vis.y1) return;
        const xm = (x0 + x1) / 2;
        const naTrilha = trilha.has(f) || f === quente;
        ctx.globalAlpha = (naTrilha ? 0.5 : 0.2) * alfaDe(f);
        ctx.fillStyle = corDe(f, rank, naTrilha);
        ctx.beginPath();
        ctx.moveTo(x0, s0);
        ctx.bezierCurveTo(xm, s0, xm, q.y, x1, q.y);
        ctx.lineTo(x1, q.y + q.h);
        ctx.bezierCurveTo(xm, q.y + q.h, xm, s1, x0, s1);
        ctx.closePath();
        ctx.fill();
      });
    }
    ctx.globalAlpha = 1;

    // caixas
    const px = 1 / cam.k;   // um pixel de tela, no mundo
    for (const n of ordem) {
      const p = posDe(n)!;
      if (p.x > vis.x1 || p.x + LARG < vis.x0 || p.y > vis.y1 || p.y + p.h < vis.y0) continue;
      const irmaos = n.pai ? visiveis(n.pai) : [n];
      const rank = irmaos.indexOf(n);
      const naTrilha = trilha.has(n);
      const aberto = abertos.has(n) && abre(n);
      ctx.globalAlpha = alfaDe(n);
      // fundo
      retangulo(p.x, p.y, LARG, p.h, 4);
      ctx.fillStyle = n.ehOutros ? PAPEL : naTrilha ? "#fff3b0" : "#ffffff";
      ctx.fill();
      ctx.lineWidth = (naTrilha || n === quente ? 2 : 1) * px;
      ctx.strokeStyle = naTrilha || n === quente ? TINTA : "#c9c2b2";
      if (n.ehOutros) ctx.setLineDash([5 * px, 4 * px]);
      ctx.stroke();
      ctx.setLineDash([]);
      // faixa da esquerda: a cor (ou a mistura por categoria)
      const fx = 7;
      if (op.usaTipo() && !n.ehOutros) {
        const t = n.mix.reduce((s, v) => s + Math.max(0, v), 0) || 1;
        let y = p.y;
        n.mix.forEach((v, i) => {
          const hh = (Math.max(0, v) / t) * p.h;
          if (hh <= 0) return;
          ctx.fillStyle = F.cats[i].cor;
          ctx.fillRect(p.x, y, fx, hh);
          y += hh;
        });
      } else {
        ctx.fillStyle = corDe(n, rank, naTrilha);
        ctx.fillRect(p.x, p.y, fx, p.h);
      }
      // textos, só quando a caixa tem tamanho na tela
      const alturaTela = p.h * cam.k;
      const pai = n.pai;
      const parte = pai ? n.valor / Math.max(1, pai.valor) : 1;
      if (alturaTela >= 14 && 12 * cam.k >= 6) {
        const larg = LARG - fx - 40;
        ctx.textBaseline = "alphabetic";
        if (p.h >= 120 && !n.ehOutros) caixaGrande(n, p, fx, larg, parte);
        else {
          ctx.font = `${n.ehOutros ? "italic " : ""}600 13px Inter, system-ui, sans-serif`;
          ctx.fillStyle = n.ehOutros ? "#5c574c" : TINTA;
          const cabem = Math.max(1, Math.min(3, Math.floor((p.h - 26) / 16)));
          const linhas = alturaTela >= 26 ? linhasDe(n.nome, larg, cabem) : linhasDe(n.nome, larg, 1);
          const blocoTxt = linhas.length * 16 + (alturaTela >= 30 ? 15 : 0);
          let y = p.y + Math.max(15, (p.h - blocoTxt) / 2 + 12);
          for (const l of linhas) { ctx.fillText(l, p.x + fx + 9, y); y += 16; }
          if (alturaTela >= 30) {
            ctx.font = "400 12px Inter, system-ui, sans-serif";
            ctx.fillStyle = "#5c574c";
            ctx.fillText(cortar(`${moedaCurta(n.valor)}${pai ? ` · ${pctCurto(parte)}` : ""}${n.ehOutros ? " · clique para ver mais" : ""}`, larg), p.x + fx + 9, y - 1);
          }
        }
        // + / − / › à direita
        const cx = p.x + LARG - 18, cy = p.y + Math.min(p.h / 2, 26);
        ctx.beginPath();
        ctx.arc(cx, cy, 9, 0, Math.PI * 2);
        ctx.fillStyle = aberto ? TINTA : n.ehOutros ? PAPEL : "#fff";
        ctx.fill();
        ctx.lineWidth = 1.2 * px;
        ctx.strokeStyle = TINTA;
        ctx.stroke();
        ctx.fillStyle = aberto ? "#fff" : TINTA;
        ctx.font = "600 14px Inter, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(aberto ? "−" : n.ehOutros ? "…" : abre(n) ? "+" : "›", cx, cy + 5);
        ctx.textAlign = "start";
      } else if (LARG * cam.k >= 46 && alturaTela >= 12) {
        // zoom afastado: o nome em letra de tamanho fixo na tela, para não virar só caixa
        rotulosTela.push({ x: (p.x + fx) * cam.k + cam.x + 4, y: p.y * cam.k + cam.y, w: (LARG - fx) * cam.k - 8, h: alturaTela, n });
      }
    }
    ctx.globalAlpha = 1;

    // os nomes do zoom afastado, já em pixels de tela
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    for (const r of rotulosTela) {
      ctx.font = `${r.n.ehOutros ? "italic " : ""}600 11px Inter, system-ui, sans-serif`;
      ctx.fillStyle = r.n.ehOutros ? "#5c574c" : TINTA;
      const duas = r.h >= 30;
      ctx.fillText(cortar(r.n.nome, r.w), r.x, r.y + (duas ? r.h / 2 - 2 : r.h / 2 + 4));
      if (duas) {
        ctx.font = "400 10.5px Inter, system-ui, sans-serif";
        ctx.fillStyle = "#5c574c";
        ctx.fillText(cortar(moedaCurta(r.n.valor), r.w), r.x, r.y + r.h / 2 + 11);
      }
    }
    rotulosTela.length = 0;

    // cabeçalhos das colunas, presos no alto da tela
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const niveis = new Map<number, string>();
    for (const [n, p] of pos) if (!niveis.has(p.d)) niveis.set(p.d, n.nivel);
    ctx.fillStyle = "rgba(247,244,236,0.92)";
    ctx.fillRect(0, 0, W, 44);
    ctx.strokeStyle = "#ddd6c6";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, 44.5); ctx.lineTo(W, 44.5); ctx.stroke();
    let inicioProximo = W >= 720 ? W - 150 : W;
    for (const [d, nivel] of [...niveis].sort((a, b) => b[0] - a[0])) {
      const sx = d * COL * cam.k + cam.x;
      if (sx > W || sx + LARG * cam.k < 0) continue;
      const x = Math.max(8, sx);
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      const largTitulo = ctx.measureText((d === 0 ? nivel : F.plural[nivel] ?? nivel).toUpperCase()).width;
      // da direita para a esquerda: um título não pisa no seguinte (colunas estreitas, ou a de trás presa na borda)
      if (x + largTitulo + 12 > inicioProximo) continue;
      inicioProximo = x;
      ctx.fillStyle = "#5c574c";
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      const titulo = d === 0 ? nivel.toUpperCase() : (F.plural[nivel] ?? nivel).toUpperCase();
      ctx.fillText(titulo, x, 19);
      if (F.explica[nivel] && LARG * cam.k > 120) {
        ctx.font = "400 11px Inter, system-ui, sans-serif";
        ctx.fillStyle = "#8a8475";
        let t = F.explica[nivel];
        const lim = Math.min(Math.max(80, Math.min(COL * cam.k - 16, 320)), (W >= 720 ? W - 160 : W - 8) - x);
        while (t.length > 3 && ctx.measureText(t).width > lim) t = `${t.slice(0, -2)}…`.replace(/…+$/, "…");
        ctx.fillText(t, x, 34);
      }
    }
    desenharMapa();
  }

  // ——— minimapa: a árvore inteira, com o retângulo do que está na tela ———
  const MW = 200, MH = 128;
  let mapaT = { s: 1, x0: 0, y0: 0, ox: 0, oy: 0 };
  function desenharMapa() {
    if (getComputedStyle(mapa).display === "none") return;
    if (mapa.width !== MW * dpr) { mapa.width = MW * dpr; mapa.height = MH * dpr; mapa.style.width = `${MW}px`; mapa.style.height = `${MH}px`; }
    const b = caixaDe([...pos.keys()]);
    if (!Number.isFinite(b.x0)) return;
    const s = Math.min((MW - 12) / (b.x1 - b.x0), (MH - 12) / (b.y1 - b.y0));
    const ox = (MW - (b.x1 - b.x0) * s) / 2, oy = (MH - (b.y1 - b.y0) * s) / 2;
    mapaT = { s, x0: b.x0, y0: b.y0, ox, oy };
    mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    mctx.clearRect(0, 0, MW, MH);
    mctx.fillStyle = "rgba(255,255,255,0.92)";
    mctx.fillRect(0, 0, MW, MH);
    const trilha = noCaminho();
    for (const [n, p] of pos) {
      mctx.fillStyle = trilha.has(n) ? VERDE : n.ehOutros ? "#ddd5c3" : "#b5ad9b";
      mctx.fillRect(ox + (p.x - b.x0) * s, oy + (p.y - b.y0) * s, Math.max(1, LARG * s), Math.max(1, p.h * s));
    }
    const v = { x0: -cam.x / cam.k, y0: -cam.y / cam.k, x1: (W - cam.x) / cam.k, y1: (H - cam.y) / cam.k };
    mctx.strokeStyle = TINTA;
    mctx.lineWidth = 1.5;
    mctx.strokeRect(ox + (v.x0 - b.x0) * s, oy + (v.y0 - b.y0) * s, (v.x1 - v.x0) * s, (v.y1 - v.y0) * s);
  }
  // clicar ou arrastar no minimapa leva a tela até ali
  let arrastandoMapa = false;
  const irPeloMapa = (e: PointerEvent) => {
    const r = mapa.getBoundingClientRect();
    const wx = (e.clientX - r.left - mapaT.ox) / mapaT.s + mapaT.x0, wy = (e.clientY - r.top - mapaT.oy) / mapaT.s + mapaT.y0;
    camT = 1;
    cam.x = W / 2 - wx * cam.k;
    cam.y = H / 2 - wy * cam.k;
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
      const aberto = abertos.has(n) && abre(n);
      const ks = aberto ? visiveis(n) : [];
      alvosLista.push(n);
      const rot = `${n.nivel}: ${n.nome}, ${moedaCurta(n.valor)}${n.pai ? `, ${pctCurto(n.valor / Math.max(1, n.pai.valor))} de ${n.pai.nome}` : ""}`;
      return `<li><button type="button" data-l="${alvosLista.length - 1}" ${abre(n) ? `aria-expanded="${aberto}"` : ""}>${esc(rot)}</button>${ks.length ? `<ul>${ks.map(item).join("")}</ul>` : ""}</li>`;
    };
    listaEl.innerHTML = `<ul>${item(F.raiz)}</ul>`;
  }
  listaEl.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-l]");
    if (b) escolher(alvosLista[Number(b.dataset.l)], true);
  });

  // ——— procurar ———
  const normal = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
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
    const cam2 = caminhoAte(n);
    for (let i = 1; i < cam2.length; i++) {
      const pai = cam2[i - 1], filho = cam2[i];
      if (!visiveis(pai).includes(filho)) mostrar.set(pai, Math.max(mostrar.get(pai) ?? K_INICIAL, filhos(pai).indexOf(filho) + 2));
      if (!visiveis(pai).includes(filho)) mostrar.set(pai, filhos(pai).length);
    }
    abrirBusca(false);
    escolher(n, false);
    setTimeout(() => {
      enquadrar(caixaDe([n, ...(abertos.has(n) ? visiveis(n) : [])]), 1);
      if (!cartao.hidden) setTimeout(() => desviarDoCartao(n), 460);
    }, 40);
  }

  // ——— o fio (degraus) e o cartão ———
  function atualizarFio() {
    const c = sel ? caminhoAte(sel) : [F.raiz];
    fioEl.innerHTML = c.map((n, i) => `<li><button type="button" data-fio="${i}" ${i === c.length - 1 ? 'aria-current="step"' : ""}>
      <span class="cc4-fio-tipo">${esc(n.nivel)}</span><span class="cc4-fio-nome">${esc(n.nome)}</span>
      <span class="cc4-fio-valor">${moedaCurta(n.valor)}${i ? ` · ${pctCurto(n.valor / Math.max(1, n.pai!.valor))}` : ""}</span></button></li>`).join("");
    fioEl.querySelectorAll<HTMLButtonElement>("[data-fio]").forEach((b) => b.addEventListener("click", () => {
      const n = c[Number(b.dataset.fio)];
      escolher(n, false);
      const ns = [n, ...(abertos.has(n) ? visiveis(n) : [])];
      enquadrar(caixaDe(ns), 1.1);
    }));
  }

  function mostrarCartao(n: No | null) {
    if (!n || abre(n) || n.ehOutros) { cartao.hidden = true; return; }
    cartao.querySelector("div")!.innerHTML = op.cartao(n);
    cartao.hidden = false;
  }

  function escolher(n: No, alternar: boolean) {
    if (n.ehOutros && n.pai) {
      mostrar.set(n.pai, (mostrar.get(n.pai) ?? K_INICIAL) + MAIS);
      relayout();
      return;
    }
    sel = n;
    // abre o caminho todo até ela
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
    if (abertos.has(n)) setTimeout(() => mostrarGalho(n), 30);
    else if (!cartao.hidden) setTimeout(() => desviarDoCartao(n), 30);
  }

  // ——— interação ———
  function noEm(sx: number, sy: number): No | null {
    const m = paraMundo(sx, sy);
    for (const [n, p] of pos) if (m.x >= p.x && m.x <= p.x + LARG && m.y >= p.y && m.y <= p.y + p.h) return n;
    return null;
  }

  const toques = new Map<number, { x: number; y: number }>();
  let arrasto: { x: number; y: number; cx: number; cy: number; moveu: boolean } | null = null;
  let pinca: { d: number; k: number; mx: number; my: number; cx: number; cy: number } | null = null;
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
      pinca = { d: Math.hypot(a.x - b.x, a.y - b.y), k: cam.k, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, cx: cam.x, cy: cam.y };
      arrasto = null;
    }
  });
  cv.addEventListener("pointermove", (e) => {
    const p = local(e);
    if (toques.has(e.pointerId)) toques.set(e.pointerId, p);
    if (pinca && toques.size === 2) {
      const [a, b] = [...toques.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      const k = Math.min(4, Math.max(0.03, pinca.k * (d / pinca.d)));
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      // o ponto do mundo que estava sob os dedos continua sob eles
      const wx = (pinca.mx - pinca.cx) / pinca.k, wy = (pinca.my - pinca.cy) / pinca.k;
      cam.k = k; cam.x = mx - wx * k; cam.y = my - wy * k;
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
      if (n !== quente) { quente = n; cv.style.cursor = n ? "pointer" : "grab"; pedir(); }
      if (n) {
        balao.innerHTML = `<strong>${esc(n.nome)}</strong><span>${esc(n.nivel)}${n.ehOutros ? " (os menores, juntos)" : ""}</span>
          <span>${moedaCurta(n.valor)}${n.pai ? ` · ${pctCurto(n.valor / Math.max(1, n.pai.valor))} de ${esc(n.pai.nome)}` : ""}</span>
          ${n !== F.raiz ? `<span>${pctCurto(n.valor / Math.max(1, F.raiz.valor))} do total</span>` : ""}`;
        balao.hidden = false;
        const bx = Math.min(p.x + 16, W - 280), by = Math.min(p.y + 16, H - 110);
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
      if (n) escolher(n, true);
    }
  };
  cv.addEventListener("pointerup", soltar);
  cv.addEventListener("pointercancel", soltar);
  cv.addEventListener("pointerleave", () => { if (quente) { quente = null; pedir(); } balao.hidden = true; });
  cv.addEventListener("dblclick", (e) => {
    const p = local(e);
    const n = noEm(p.x, p.y);
    if (!n) return;
    const ns = [n, ...(abertos.has(n) ? visiveis(n) : [])];
    enquadrar(caixaDe(ns), 2);
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

  // teclado: setas andam, + e − dão zoom
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

  caixa.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-acao]");
    if (!b) return;
    const a = b.dataset.acao;
    if (a === "cheia") alternarCheia();
    else if (a === "procurar") abrirBusca();
    else if (a === "mais") zoomEm(1.3, W / 2, H / 2);
    else if (a === "menos") zoomEm(1 / 1.3, W / 2, H / 2);
    else if (a === "ajustar") enquadrar(caixaDe([...pos.keys()]), 1.1);
    else if (a === "fechar") {
      abertos.clear(); abertos.add(F.raiz); mostrar.clear(); sel = null;
      op.aoEscolher(F.raiz); atualizarFio(); mostrarCartao(null); relayout();
      setTimeout(() => enquadrar(caixaDe([...pos.keys()]), 1.1), 40);
    } else if (a === "fechar-cartao") cartao.hidden = true;
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
  pos = calcular();
  atualizarLista();
  atualizarFio();
  mostrarCartao(sel);
  // começa mostrando o último galho aberto (ou tudo, se só a raiz estiver aberta)
  const foco = sel ? (abertos.has(sel) ? sel : sel.pai ?? F.raiz) : F.raiz;
  // no celular, só o último galho (o caminho inteiro ficaria pequeno demais); o fio no alto mostra de onde veio
  const inicio = W < 640 ? (abertos.has(foco) ? visiveis(foco) : [foco]) : [...caminhoAte(foco), ...(abertos.has(foco) ? visiveis(foco) : [])];
  enquadrar(caixaDe(inicio), 1, false);
  if (sel && !cartao.hidden) requestAnimationFrame(() => desviarDoCartao(sel!));
  document.fonts?.ready.then(pedir);

  return { fonte: F, raiz: caixa, redesenhar: () => { atualizarFio(); pedir(); } };
}
