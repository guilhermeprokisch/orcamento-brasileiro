// A trilha dos exploradores (/contratos, /emendas): "Contratos › Jandira (SP) › Comercial Rcs Ltda",
// com um link para cada passo. Guarda, na aba (sessionStorage), as páginas abertas pelos links do
// resultado; voltar a uma delas corta a trilha ali. Uma busca nova (o formulário) começa outra trilha.

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ler = (k) => { try { return sessionStorage.getItem(k); } catch { return null; } };
const gravar = (k, v) => { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* sem armazenamento: a trilha fica só com o passo atual */ } };
const MAXIMO = 5;

/**
 * `el` é o <nav data-voltar>; `inicio` é { url: "/contratos", titulo: "Contratos" }.
 * Devolve { titulo(t) } para dar nome ao passo atual quando ele for conhecido, e { novaBusca() }
 * para chamar antes de sair pelo formulário.
 */
export function ligarTrilha(el, { chave, inicio }) {
  const k = `trilha:${chave}`;
  const aqui = location.pathname.replace(/\/$/, "") + location.search;
  let lista = [];
  if (ler(`${k}:nova`)) gravar(`${k}:nova`, null);
  else { try { lista = JSON.parse(ler(k) || "[]"); } catch { lista = []; } }
  const i = lista.findIndex((p) => p.url === aqui);
  lista = i >= 0 ? lista.slice(0, i + 1) : [...lista, { url: aqui, titulo: "…" }].slice(-MAXIMO);

  const desenhar = () => {
    const passos = [
      `<a href="${esc(inicio.url)}">${esc(inicio.titulo)}</a>`,
      ...lista.slice(0, -1).map((p) => `<a href="${esc(p.url)}">${esc(p.titulo)}</a>`),
      `<span aria-current="page">${esc(lista.at(-1).titulo)}</span>`,
    ];
    el.innerHTML = passos.join(`<span class="sep" aria-hidden="true">›</span>`);
    el.hidden = false;
  };
  desenhar();
  return {
    titulo(t) {
      if (!t) return;
      lista.at(-1).titulo = t;
      gravar(k, JSON.stringify(lista));
      desenhar();
    },
    novaBusca() { gravar(`${k}:nova`, "1"); },
  };
}
