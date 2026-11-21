/**
 * A cascata do gasto (/cascata): por onde passa o dinheiro que o governo federal pagou, nível a nível, na tela livre
 * em Canvas (tela.ts). Este arquivo cuida da página: lê e grava a URL, carrega o ano, monta os detalhes de cada caixa
 * e liga os controles (ano, por pessoa, cor).
 *
 *   /cascata?ano=2024&pessoa=1&cor=tamanho&c=36000~36901   (c: os códigos do caminho, separados por "~")
 *
 * O Explorer leva para cá com o mesmo caminho ("Ver como cascata"); os detalhes de cada caixa voltam para lá.
 */
import { pct } from "../../lib/formato";
import { caminhoAte, dinheiro, exibir, filhos, fonteUniao, temFilhos, type Fonte, type No } from "./dados";
import { criarTela, type Tela } from "./tela";

type ModoCor = "tipo" | "tamanho";

interface Estado {
  ano: number | null;
  pessoa: boolean;
  cor: ModoCor;
  caminho: No[];
}

let F: Fonte;
let E: Estado;
let raizEl: HTMLElement;
let tela: Tela | null = null;
let populacao: Record<string, Record<string, number>> = {};
let anos: number[] = [];

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const parte = (n: No) => (n.pai && n.pai.valor > 0 ? n.valor / n.pai.valor : 1);
const pctCurto = (v: number) => (v >= 0.995 ? "100%" : v >= 0.1 ? `${Math.round(v * 100)}%` : v >= 0.001 ? pct(v) : "<0,1%");
const plural = (nivel: string) => F.plural[nivel] ?? nivel.toLowerCase();
const usaTipo = () => E.cor === "tipo" && F.cats.length > 1;

// ——— URL ———

function lerUrl(): Estado {
  const p = new URLSearchParams(location.search);
  return {
    ano: Number(p.get("ano")) || null,
    pessoa: p.get("pessoa") === "1",
    cor: p.get("cor") === "tamanho" ? "tamanho" : "tipo",
    caminho: [],
  };
}

function urlCom(mud: { ano?: number | null; c?: string | null } = {}) {
  const p = new URLSearchParams();
  const ano = "ano" in mud ? mud.ano : E.ano;
  const c = "c" in mud ? mud.c : E.caminho.slice(1).map((n) => n.cod).join("~");
  if (ano && ano !== anos[anos.length - 1]) p.set("ano", String(ano));
  if (E.pessoa) p.set("pessoa", "1");
  if (E.cor !== "tipo") p.set("cor", E.cor);
  if (c) p.set("c", c);
  const q = p.toString().replaceAll("%7E", "~");
  return `${location.pathname}${q ? `?${q}` : ""}`;
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

function atualizarControles() {
  raizEl.querySelectorAll<HTMLButtonElement>("[data-cor]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.cor === E.cor));
  });
  raizEl.querySelector("[data-pessoa]")?.setAttribute("aria-pressed", String(E.pessoa));
  const explorer = raizEl.querySelector<HTMLAnchorElement>("[data-explorer]");
  if (explorer && F?.linkExplorer) explorer.href = F.linkExplorer(E.caminho[E.caminho.length - 1] ?? F.raiz);
}

function salvarUrl() {
  history.replaceState(null, "", urlCom());
  atualizarControles();
}

// ——— textos ———

function htmlLegenda() {
  const menores = `<li><i class="cc-hachura"></i>os menores, juntos (“mais N”)</li>`;
  if (!usaTipo()) return `<ul class="cc-legenda">${menores}</ul>`;
  return `<ul class="cc-legenda">${F.cats.filter((c) => c.nome !== "Sem informação").map((c) =>
    `<li><i style="background:${c.cor}"></i>${esc(c.nome)}</li>`).join("")}${menores}</ul>`;
}

function htmlFrase(): string {
  let t = esc(F.frase);
  if (E.pessoa) {
    t += ` <span class="cc-pessoa">Por pessoa: <strong class="marca">${dinheiro(F.raiz.valor).replace("/pessoa", "")}</strong>, dividindo pelos ${F.populacao.toLocaleString("pt-BR")} brasileiros (IBGE, ${F.ano}).</span>`;
  }
  return t;
}

/** Os detalhes de qualquer caixa: o que é, quanto é, de que tipo e os maiores dentro. */
function htmlDetalhe(n: No): string {
  if (!temFilhos(n)) return htmlFim(n);
  const raiz = F.raiz;
  const fs = filhos(n);
  const linhas: string[] = [];
  if (n.pai) linhas.push(`<dt>Do nível de cima</dt><dd>${pctCurto(parte(n))} de ${esc(n.pai.nome)}</dd>`);
  if (n !== raiz) {
    const cem = (n.valor / raiz.valor) * 100;
    const cada = cem >= 1 ? `R$ ${cem.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} de cada R$ 100` : `R$ ${(cem * 10).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} de cada R$ 1.000`;
    linhas.push(`<dt>Do total</dt><dd>${pctCurto(n.valor / raiz.valor)}: ${cada} do orçamento federal</dd>`);
  }
  if (n.autorizado) linhas.push(`<dt>Autorizado</dt><dd>${dinheiro(n.autorizado)}; pagou ${pctCurto(n.valor / n.autorizado)} disso no ano</dd>`);
  linhas.push(`<dt>Dentro</dt><dd>${fs.length} ${fs.length > 1 ? plural(fs[0].nivel) : fs[0].nivel.toLowerCase()}</dd>`);
  const t = n.mix.reduce((a, v) => a + Math.max(0, v), 0) || 1;
  const mix = n.mix.map((v, i) => ({ i, f: Math.max(0, v) / t })).filter((m) => m.f >= 0.005).sort((a, b) => b.f - a.f);
  const htmlMix = F.cats.length > 1 ? `<div class="cc-det-mix">
      <span class="cc-det-barra">${mix.map((m) => `<b style="flex:${m.f};background:${F.cats[m.i].cor}"></b>`).join("")}</span>
      <ul>${mix.map((m) => `<li><i style="background:${F.cats[m.i].cor}"></i><strong>${esc(F.cats[m.i].nome)} ${pctCurto(m.f)}</strong>
        <span>${esc(F.explicaCat[m.i] ?? "")}</span></li>`).join("")}</ul></div>` : "";
  const maiores = fs.slice(0, 3).map((f) => `<li><span>${esc(f.nome)}</span><span class="num">${dinheiro(f.valor)} · ${pctCurto(f.valor / Math.max(1, n.valor))}</span></li>`).join("");
  return `<div class="cc-cartao cc-detalhe">
    <span class="sobretitulo">${esc(n.nivel)}</span>
    ${F.explica[n.nivel] ? `<p class="cc-det-explica">${esc(F.explica[n.nivel])}</p>` : ""}
    <h3>${esc(n.nome)}</h3>
    <p class="cc-cartao-valor"><strong class="marca">${dinheiro(n.valor, true)}</strong> pagos em ${F.ano}</p>
    <dl>${linhas.join("")}</dl>
    ${htmlMix}
    <h4>Os maiores dentro</h4>
    <ol class="cc-det-maiores">${maiores}</ol>
    ${F.linkExplorer ? `<p><a href="${F.linkExplorer(n)}">Ver no Explorer</a> (o mapa de blocos, com outros recortes)</p>` : ""}
  </div>`;
}

/** O último nível (o tipo de gasto da ação): até onde vão os dados do orçamento federal. */
function htmlFim(n: No): string {
  const fio = caminhoAte(n).slice(1).map((x) => esc(x.nome)).join(" › ");
  return `<div class="cc-cartao">
    <span class="sobretitulo">${esc(n.nivel)} · fim do caminho</span>
    <h3>${esc(n.nome)}</h3>
    <p class="cc-cartao-valor"><strong class="marca">${dinheiro(n.valor, true)}</strong> · ${pctCurto(parte(n))} ${n.pai ? `de ${esc(n.pai.nome)}` : ""}</p>
    <p>Este é o último degrau do orçamento federal: <strong>${esc(n.nome.toLowerCase())}</strong> da ação
      “${esc(n.pai?.nome ?? "")}”. Quem recebeu o dinheiro (a empresa, o contrato) está no Portal da Transparência,
      nota a nota, e ainda não está neste site.</p>
    ${F.linkExplorer ? `<p><a href="${F.linkExplorer(n)}">Ver no Explorer</a></p>` : ""}
    <p class="cc-fio muted">${fio}</p>
  </div>`;
}

// ——— desenho ———

function desenhar() {
  const topo = raizEl.querySelector<HTMLElement>("#cc-topo")!;
  const desenho = raizEl.querySelector<HTMLElement>("#cc-desenho")!;
  topo.innerHTML = `<p class="cc-frase">${htmlFrase()}</p><div class="cc-topo-linha">${htmlLegenda()}</div>`;
  if (tela && tela.fonte === F && desenho.contains(tela.raiz)) { tela.redesenhar(); return; }
  desenho.innerHTML = "";
  tela = criarTela(desenho, F, {
    usaTipo,
    caminhoInicial: E.caminho,
    aoEscolher: (n) => { E.caminho = caminhoAte(n); salvarUrl(); },
    cartao: htmlDetalhe,
  });
}

/** População do Brasil no ano (soma das UFs); sem o ano, o mais próximo. */
function populacaoDe(ano: number): number {
  const lista = Object.keys(populacao).map(Number).sort((a, b) => a - b);
  if (!lista.length) return 1;
  const a = lista.includes(ano) ? ano : lista.reduce((m, x) => (Math.abs(x - ano) < Math.abs(m - ano) ? x : m), lista[0]);
  return Object.entries(populacao[String(a)]).filter(([k]) => k.length === 2).reduce((s, [, v]) => s + v, 0);
}

export async function iniciar(el: HTMLElement) {
  raizEl = el;
  E = lerUrl();
  const desenho = el.querySelector<HTMLElement>("#cc-desenho")!;
  desenho.innerHTML = `<p class="cc-carregando">Carregando…</p>`;
  try {
    const [pop, resumo] = await Promise.all([
      fetch("/data/indicadores/populacao.json").then((r) => (r.ok ? r.json() : { anos: {} })),
      fetch("/data/explorer/anos.json").then((r) => {
        if (!r.ok) throw new Error(`Não consegui carregar a lista de anos (HTTP ${r.status})`);
        return r.json();
      }),
    ]);
    populacao = pop.anos ?? {};
    // anos completos (o corrente ainda está em execução)
    anos = (resumo.anos ?? []).map((a: { ano: number }) => a.ano).filter((a: number) => a < new Date().getFullYear());
    const ano = E.ano && anos.includes(E.ano) ? E.ano : anos[anos.length - 1];
    F = await fonteUniao(ano, populacaoDe(ano));
    exibir.populacao = F.populacao;
    exibir.porPessoa = E.pessoa;
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
  el.querySelector("[data-pessoa]")?.addEventListener("click", () => {
    E.pessoa = !E.pessoa;
    exibir.porPessoa = E.pessoa;
    salvarUrl();
    desenhar();
  });
  // ano: troca os dados (recarrega, mantendo o caminho; um código que não exista no outro ano para onde der)
  const sel = el.querySelector<HTMLSelectElement>("#cc-ano");
  if (sel) {
    sel.innerHTML = [...anos].reverse().map((a) => `<option value="${a}" ${a === F.ano ? "selected" : ""}>${a}</option>`).join("");
    sel.disabled = false;
    sel.addEventListener("change", () => { location.href = urlCom({ ano: Number(sel.value) }); });
  }
  if (F.cats.length <= 1) el.querySelector<HTMLElement>(".cc-cores")?.setAttribute("hidden", "");
  desenhar();
}
