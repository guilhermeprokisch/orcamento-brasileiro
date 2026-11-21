// Os degraus das páginas de busca (/contratos, /emendas/buscar): o caminho até aqui, um degrau por página aberta
// pelos links do resultado, com o tipo do passo ("Onde", "Empresa", "Quem mandou"), o nome e o valor. Guarda, na aba
// (sessionStorage), os passos; voltar a um deles corta o caminho ali. Uma busca nova (o formulário) começa outro.
// O HTML e as classes são os do componente Solid dos exploradores (components/explorer/Degraus.tsx), com o estilo em
// src/styles/degraus.css.

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ler = (k) => { try { return sessionStorage.getItem(k); } catch { return null; } };
const gravar = (k, v) => { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* sem armazenamento: o caminho fica só com o passo atual */ } };
const MAXIMO = 6;
const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
/** 0,93 → "93%"; 0,044 → "4,4%". */
const fatiaTexto = (f) => { const p = f * 100; return p >= 99.5 ? "100%" : p >= 10 ? `${nf0.format(p)}%` : p >= 0.1 ? `${nf1.format(p)}%` : "<0,1%"; };
const parametros = (url) => new URLSearchParams(url.split("?")[1] || "");

/**
 * A fatia de um passo no anterior, só quando ele é um pedaço do anterior: o mesmo conjunto (`base`), o mesmo ano e
 * todos os filtros do anterior ainda valendo ("Jandira" → "merenda em Jandira"; não "Jandira" → "a empresa no Brasil").
 */
function fatia(ant, p) {
  if (!ant || !(ant.v > 0) || !(p.v >= 0) || ant.base !== p.base || ant.ano !== p.ano) return null;
  const a = parametros(ant.url), b = parametros(p.url);
  for (const [k, v] of a) if (k !== "ano" && b.get(k) !== v) return null;
  return p.v <= ant.v ? p.v / ant.v : null;
}

function degrau(p, ant, atual) {
  const f = fatia(ant, p);
  const corpo = `<span class="degrau-tipo">${esc(p.tipo)}</span><span class="degrau-nome" title="${esc(p.titulo)}">${esc(p.titulo)}</span>`
    + (p.valor ? `<span class="degrau-valor"><strong>${esc(p.valor)}</strong>${f != null && ant.de ? ` <span class="degrau-parte">${fatiaTexto(f)} ${esc(ant.de)}</span>` : ""}</span>` : "")
    + (f != null ? `<span class="degrau-barra" aria-hidden="true"><i style="width:${Math.max(2, Math.round(f * 100))}%"></i></span>` : "");
  return `<li>${atual ? `<div class="degrau" aria-current="page">${corpo}</div>` : `<a class="degrau" href="${esc(p.url)}">${corpo}</a>`}</li>`;
}

/**
 * `el` é o <nav data-voltar> dos degraus; `botao`, o lugar do "← Voltar a …" logo acima do resultado (opcional).
 * `inicio` é o primeiro degrau: { url, titulo, tipo, valor, v, base, ano, de, volta }.
 * Cada passo: o tipo ("Onde"), o nome, o valor já formatado e o número (v) com o conjunto (base) e o ano, para a
 * fatia no anterior; `de` é como o passo seguinte se refere a ele ("12% da cidade"); `volta`, o nome no botão
 * ("Voltar a todos os contratos"). Devolve { titulo(t) } e { passo({ … }) } para completar o passo atual quando os
 * dados chegam, e { novaBusca() } para chamar antes de sair pelo formulário.
 */
export function ligarTrilha(el, { chave, inicio, botao }) {
  const k = `trilha:${chave}`;
  const aqui = location.pathname.replace(/\/$/, "") + location.search;
  // Na página inicial do explorador, o caminho recomeça.
  if (aqui === inicio.url) {
    gravar(k, null); gravar(`${k}:nova`, null);
    el.hidden = true; if (botao) botao.hidden = true;
    return { titulo() {}, passo() {}, novaBusca() {} };
  }
  let lista = [];
  if (ler(`${k}:nova`)) gravar(`${k}:nova`, null);
  else { try { lista = JSON.parse(ler(k) || "[]"); } catch { lista = []; } }
  const i = lista.findIndex((p) => p.url === aqui);
  lista = i >= 0 ? lista.slice(0, i + 1) : [...lista, { url: aqui, titulo: "…", tipo: "" }].slice(-MAXIMO);
  let aberto = false;

  const desenhar = () => {
    const passos = [inicio, ...lista];
    el.className = `degraus${aberto ? " aberto" : ""}`;
    el.setAttribute("aria-label", "Caminho");
    el.innerHTML = `<div class="degraus-cab"><span class="degraus-dica">O caminho até aqui: clique num degrau para voltar</span></div>
      <button type="button" class="degraus-abrir" aria-expanded="${aberto}">Caminho: ${passos.length} passos <span>${aberto ? "fechar" : "abrir"}</span></button>
      <ol class="degraus-lista" aria-label="O caminho até aqui">${passos.map((p, j) => degrau(p, passos[j - 1], j === passos.length - 1)).join("")}</ol>`;
    el.querySelector(".degraus-abrir").addEventListener("click", () => { aberto = !aberto; desenhar(); });
    el.hidden = false;
    if (botao) {
      const ant = passos.at(-2);
      botao.innerHTML = `<a class="degraus-voltar" href="${esc(ant.url)}" title="Voltar a ${esc(ant.volta || ant.titulo)}">← <span>Voltar a ${esc(ant.volta || ant.titulo)}</span></a>`;
      botao.hidden = false;
    }
  };
  desenhar();
  const salvar = () => { gravar(k, JSON.stringify(lista)); desenhar(); };
  return {
    titulo(t) {
      if (!t) return;
      lista.at(-1).titulo = t;
      salvar();
    },
    passo(p) {
      Object.assign(lista.at(-1), Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined)));
      salvar();
    },
    novaBusca() { gravar(`${k}:nova`, "1"); },
  };
}
