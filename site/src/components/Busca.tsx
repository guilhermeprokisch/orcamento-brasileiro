import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { proximaSugerida, ROTULO_DIM, type Dim } from "../lib/dados";
import { moedaExtenso } from "../lib/formato";
import "./busca.css";

type Bruto = [Dim, string, string, number, number];
interface Entrada {
  dim: Dim;
  cod: string;
  nome: string;
  ano: number;
  valor: number;
  chave: string;
}

const PRIORIDADE: Record<Dim, number> = { orgao: 0, funcao: 1, programa: 2, uo: 3, subfuncao: 4, acao: 5, gnd: 6 };
const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

let indice: Promise<Entrada[]> | null = null;
function carregarIndice(): Promise<Entrada[]> {
  indice ??= fetch("/busca.json")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((j: { itens: Bruto[] }) =>
      j.itens.map(([dim, cod, nome, ano, valor]) => ({ dim, cod, nome, ano, valor, chave: norm(`${nome} ${cod}`) })),
    )
    .catch((e) => {
      indice = null;
      throw e;
    });
  return indice;
}

function link(e: Entrada): string {
  if (e.dim === "orgao") return `/orgaos/${e.cod}`;
  const por = proximaSugerida([{ dim: e.dim, cod: e.cod }]);
  return `/explorer?ano=${e.ano}&f=${e.dim}:${e.cod}${por ? `&por=${por}` : ""}`;
}

export default function Busca() {
  const [aberta, setAberta] = createSignal(false);
  const [texto, setTexto] = createSignal("");
  const [dados, setDados] = createSignal<Entrada[] | null>(null);
  const [erro, setErro] = createSignal(false);
  const [ativo, setAtivo] = createSignal(0);
  let campo: HTMLInputElement | undefined;
  let botao: HTMLButtonElement | undefined;

  const abrir = () => {
    setAberta(true);
    setErro(false);
    carregarIndice().then(setDados, () => setErro(true));
    queueMicrotask(() => campo?.focus());
  };
  const fechar = () => {
    setAberta(false);
    botao?.focus();
  };

  onMount(() => {
    const atalho = (ev: KeyboardEvent) => {
      const alvo = ev.target;
      const digitando = alvo instanceof Element && alvo.closest("input, textarea, select, [contenteditable]");
      if (ev.key === "/" && !digitando && !aberta()) {
        ev.preventDefault();
        abrir();
      }
    };
    addEventListener("keydown", atalho);
    onCleanup(() => removeEventListener("keydown", atalho));
  });

  const resultados = createMemo(() => {
    const d = dados();
    const termos = norm(texto()).split(/\s+/).filter(Boolean);
    if (!d || !termos.length) return [];
    const q = termos.join(" ");
    return d
      .filter((e) => termos.every((t) => e.chave.includes(t)))
      .map((e) => {
        const n = norm(e.nome);
        let s = PRIORIDADE[e.dim] * 10;
        if (e.cod.toLowerCase() === q) s -= 100;
        if (n === q) s -= 50;
        else if (n.startsWith(q)) s -= 20;
        return { e, s };
      })
      .sort((a, b) => a.s - b.s || b.e.valor - a.e.valor)
      .slice(0, 30)
      .map((r) => r.e);
  });

  const teclar = (ev: KeyboardEvent) => {
    const n = resultados().length;
    if (ev.key === "Escape") { ev.preventDefault(); fechar(); }
    else if (ev.key === "ArrowDown" && n) { ev.preventDefault(); setAtivo((i) => (i + 1) % n); }
    else if (ev.key === "ArrowUp" && n) { ev.preventDefault(); setAtivo((i) => (i - 1 + n) % n); }
    else if (ev.key === "Enter" && n) {
      ev.preventDefault();
      location.href = link(resultados()[ativo()]);
    }
  };

  return (
    <>
      <button type="button" class="busca-botao" ref={botao} onClick={abrir} aria-haspopup="dialog">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8.5 2a6.5 6.5 0 0 1 5.2 10.4l4.4 4.4-1.4 1.4-4.4-4.4A6.5 6.5 0 1 1 8.5 2zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9z" /></svg>
        <span class="busca-rotulo">Buscar</span>
        <kbd class="busca-kbd">/</kbd>
      </button>

      <Show when={aberta()}>
        <div class="busca-fundo" onClick={(e) => e.target === e.currentTarget && fechar()}>
          <div class="busca-caixa" role="dialog" aria-modal="true" aria-label="Buscar no orçamento">
            <div class="busca-campo">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8.5 2a6.5 6.5 0 0 1 5.2 10.4l4.4 4.4-1.4 1.4-4.4-4.4A6.5 6.5 0 1 1 8.5 2zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9z" /></svg>
              <input
                ref={campo}
                type="search"
                placeholder="Órgão, programa, ação ou código…"
                value={texto()}
                onInput={(e) => { setTexto(e.currentTarget.value); setAtivo(0); }}
                onKeyDown={teclar}
                role="combobox"
                aria-expanded={resultados().length > 0}
                aria-controls="busca-lista"
                aria-activedescendant={resultados().length ? `busca-r-${ativo()}` : undefined}
                autocomplete="off"
              />
              <button type="button" class="busca-fechar" onClick={fechar} aria-label="Fechar busca">Esc</button>
            </div>

            <Show when={erro()}>
              <p class="busca-msg">Não foi possível carregar o índice de busca.</p>
            </Show>
            <Show when={!erro() && !dados()}>
              <p class="busca-msg">Carregando…</p>
            </Show>
            <Show when={dados() && !texto().trim()}>
              <p class="busca-msg">
                Busque por nome ou código: “saúde”, “bolsa família”, “Fiocruz”, “2000”. Acentos e maiúsculas não importam.
              </p>
            </Show>
            <Show when={dados() && texto().trim() && resultados().length === 0}>
              <p class="busca-msg">Nada encontrado para “{texto()}”.</p>
            </Show>

            <ul class="busca-lista" id="busca-lista" role="listbox">
              <For each={resultados()}>
                {(e, i) => (
                  <li role="option" id={`busca-r-${i()}`} aria-selected={i() === ativo()}>
                    <a href={link(e)} classList={{ ativo: i() === ativo() }} onPointerEnter={() => setAtivo(i())}>
                      <span class="busca-tipo">{ROTULO_DIM[e.dim]}</span>
                      <span class="busca-nome">{e.nome} <span class="busca-cod">{e.cod}</span></span>
                      <span class="busca-valor num">
                        {e.valor > 0 ? moedaExtenso(e.valor) : "—"} <span class="busca-ano">em {e.ano}</span>
                      </span>
                    </a>
                  </li>
                )}
              </For>
            </ul>
          </div>
        </div>
      </Show>
    </>
  );
}
