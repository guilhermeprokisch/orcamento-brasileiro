// O campo "Onde" dos exploradores (/contratos, /emendas): digita-se o nome de uma cidade ou de um
// estado e aparecem sugestões, separadas em Estados e Cidades, como na busca do topo do site. A escolha
// vira uma etiqueta com ✕. Quem usa recebe { tipo: "uf" | "mun", codigo, nome, sigla, rotulo } ou null.

const sem = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

let lugares = null;
/** Estados e cidades, de /data/mapa/nomes.json (o mesmo arquivo do mapa). */
export async function carregarLugares() {
  if (lugares) return lugares;
  const nomes = await fetch("/data/mapa/nomes.json").then((r) => r.json());
  const lista = [];
  for (const [codigo, [nome, sigla]] of Object.entries(nomes.uf)) lista.push({ tipo: "uf", codigo, nome, sigla, rotulo: nome, chave: sem(`${nome} ${sigla}`) });
  for (const [codigo, [nome, sigla]] of Object.entries(nomes.mun)) lista.push({ tipo: "mun", codigo, nome, sigla, rotulo: `${nome} (${sigla})`, chave: sem(`${nome} ${sigla}`) });
  lugares = { lista, porCodigo: new Map(lista.map((l) => [l.codigo, l])), porSigla: new Map(lista.filter((l) => l.tipo === "uf").map((l) => [l.sigla, l])) };
  return lugares;
}

/** O nome com o trecho digitado em destaque. */
function marcar(nome, termo) {
  const i = sem(nome).indexOf(termo);
  if (!termo || i < 0) return esc(nome);
  return `${esc(nome.slice(0, i))}<strong class="marca">${esc(nome.slice(i, i + termo.length))}</strong>${esc(nome.slice(i + termo.length))}`;
}

/**
 * Liga o campo. `raiz` é o elemento [data-onde] (com [data-onde-input], [data-onde-lista], [data-chip],
 * [data-chip-texto] e [data-chip-tirar]); `aoMudar(lugar)` é chamado a cada escolha ou remoção.
 */
export function ligarOnde(raiz, aoMudar) {
  const campo = raiz.querySelector("[data-onde-input]");
  const lista = raiz.querySelector("[data-onde-lista]");
  const chip = raiz.querySelector("[data-chip]");
  let achados = [], ativo = -1, escolhido = null;

  const fechar = () => { lista.hidden = true; campo.setAttribute("aria-expanded", "false"); ativo = -1; };
  const desenhar = () => {
    const termos = sem(campo.value).trim().split(/\s+/).filter(Boolean);
    if (!termos.length || !lugares) { fechar(); return; }
    const casa = (l) => termos.every((t) => l.chave.includes(t));
    const ordem = (a, b) => Number(!a.chave.startsWith(termos[0])) - Number(!b.chave.startsWith(termos[0])) || a.nome.localeCompare(b.nome, "pt-BR");
    const estados = lugares.lista.filter((l) => l.tipo === "uf" && casa(l)).sort(ordem).slice(0, 4);
    const cidades = lugares.lista.filter((l) => l.tipo === "mun" && casa(l)).sort(ordem).slice(0, 8);
    achados = [...estados, ...cidades];
    ativo = achados.length ? 0 : -1;
    const item = (l, i) => `<button type="button" role="option" id="onde-${i}" class="${i === ativo ? "ativo" : ""}" data-i="${i}" aria-selected="${i === ativo}">
      <span>${marcar(l.nome, termos[0])}</span><small>${l.tipo === "uf" ? "estado" : l.sigla}</small></button>`;
    lista.innerHTML = achados.length
      ? `${estados.length ? `<div class="onde-grupo">Estados</div>${estados.map((l, i) => item(l, i)).join("")}` : ""}
         ${cidades.length ? `<div class="onde-grupo">Cidades</div>${cidades.map((l, i) => item(l, i + estados.length)).join("")}` : ""}`
      : `<p class="onde-msg">Nenhuma cidade ou estado com “${esc(campo.value.trim())}”.</p>`;
    lista.hidden = false;
    campo.setAttribute("aria-expanded", "true");
    campo.setAttribute("aria-activedescendant", ativo >= 0 ? `onde-${ativo}` : "");
  };
  const mover = (d) => {
    if (!achados.length) return;
    ativo = (ativo + d + achados.length) % achados.length;
    lista.querySelectorAll("[data-i]").forEach((b) => { const sim = Number(b.dataset.i) === ativo; b.classList.toggle("ativo", sim); b.setAttribute("aria-selected", String(sim)); if (sim) b.scrollIntoView({ block: "nearest" }); });
    campo.setAttribute("aria-activedescendant", `onde-${ativo}`);
  };
  const escolher = (l) => {
    escolhido = l;
    chip.hidden = !l;
    raiz.querySelector("[data-chip-texto]").textContent = l ? l.rotulo : "";
    campo.value = "";
    campo.hidden = !!l;
    fechar();
    aoMudar(l);
  };

  campo.addEventListener("focus", () => carregarLugares().then(desenhar), { once: true });
  campo.addEventListener("input", async () => { await carregarLugares(); desenhar(); });
  campo.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { ev.preventDefault(); if (lista.hidden) desenhar(); else mover(1); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); mover(-1); }
    else if (ev.key === "Enter" && !lista.hidden && ativo >= 0) { ev.preventDefault(); escolher(achados[ativo]); }
    else if (ev.key === "Escape") fechar();
  });
  lista.addEventListener("mousedown", (ev) => ev.preventDefault());   // o clique não tira o foco antes de escolher
  lista.addEventListener("click", (ev) => { const b = ev.target.closest("[data-i]"); if (b) escolher(achados[Number(b.dataset.i)]); });
  campo.addEventListener("blur", () => setTimeout(fechar, 100));
  raiz.querySelector("[data-chip-tirar]").addEventListener("click", () => { escolher(null); campo.focus(); });

  return {
    /** Mostra um lugar já escolhido (vindo do endereço), sem avisar. */
    async definir(codigo) {
      const l = (await carregarLugares()).porCodigo.get(codigo);
      if (!l) return;
      escolhido = l; chip.hidden = false; raiz.querySelector("[data-chip-texto]").textContent = l.rotulo; campo.hidden = true;
      return l;
    },
    get escolhido() { return escolhido; },
  };
}
