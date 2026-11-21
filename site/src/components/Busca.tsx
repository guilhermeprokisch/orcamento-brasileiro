import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { proximaSugerida, type Dim } from "../lib/dados";
import { moedaCurta } from "../lib/formato";
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

const GRUPO: Record<Dim, string> = {
  orgao: "Órgãos", funcao: "Áreas (funções)", subfuncao: "Subfunções", programa: "Programas",
  uo: "Unidades", acao: "Ações", gnd: "Tipos de gasto", tipo: "Tipos de despesa",
};
const PRIORIDADE: Record<Dim, number> = { orgao: 0, funcao: 1, programa: 2, uo: 3, subfuncao: 4, acao: 5, gnd: 6, tipo: 7 };
const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

let indice: Promise<{ itens: Entrada[]; ultimoAno: number }> | null = null;
function carregarIndice() {
  indice ??= fetch("/busca.json")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((j: { itens: Bruto[]; anoBase?: number }) => {
      const itens = j.itens.map(([dim, cod, nome, ano, valor]) => ({ dim, cod, nome, ano, valor, chave: norm(`${nome} ${cod}`) }));
      return { itens, ultimoAno: j.anoBase ?? Math.max(...itens.map((i) => i.ano)) };
    })
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

/** Divide o nome em trechos, marcando os que casam com os termos (sem acento). */
function destacar(nome: string, termos: string[]): { t: string; m: boolean }[] {
  let n = "";
  const mapa: number[] = [];
  for (let i = 0; i < nome.length; i++) {
    const c = norm(nome[i]);
    for (let k = 0; k < c.length; k++) { n += c[k]; mapa.push(i); }
  }
  const marcado = new Array(nome.length).fill(false);
  for (const t of termos) {
    let p = n.indexOf(t);
    while (p >= 0) {
      for (let k = p; k < p + t.length; k++) marcado[mapa[k]] = true;
      p = n.indexOf(t, p + t.length);
    }
  }
  const partes: { t: string; m: boolean }[] = [];
  for (let i = 0; i < nome.length; i++) {
    const ult = partes.at(-1);
    if (ult && ult.m === marcado[i]) ult.t += nome[i];
    else partes.push({ t: nome[i], m: marcado[i] });
  }
  return partes;
}

export default function Busca(props: { compacto?: boolean }) {
  const [aberta, setAberta] = createSignal(false);
  const [texto, setTexto] = createSignal("");
  const [dados, setDados] = createSignal<{ itens: Entrada[]; ultimoAno: number } | null>(null);
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
    // Só a instância de desktop responde ao atalho, para não abrir duas.
    if (props.compacto) return;
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

  const termos = createMemo(() => norm(texto()).split(/\s+/).filter(Boolean));

  const resultados = createMemo(() => {
    const d = dados();
    const ts = termos();
    if (!d || !ts.length) return [];
    const q = ts.join(" ");
    return d.itens
      .filter((e) => ts.every((t) => e.chave.includes(t)))
      .map((e) => {
        const n = norm(e.nome);
        let s = PRIORIDADE[e.dim] * 10;
        if (e.cod.toLowerCase() === q) s -= 100;
        if (n === q) s -= 50;
        else if (n.startsWith(q)) s -= 20;
        if (e.ano < d.ultimoAno) s += 15;
        return { e, s };
      })
      .sort((a, b) => a.s - b.s || b.e.valor - a.e.valor)
      .slice(0, 24)
      .map((r) => r.e);
  });

  /** Resultados agrupados por tipo, na ordem em que o primeiro de cada tipo aparece. */
  const grupos = createMemo(() => {
    const ordem: Dim[] = [];
    const por = new Map<Dim, { e: Entrada; i: number }[]>();
    resultados().forEach((e) => {
      if (!por.has(e.dim)) { por.set(e.dim, []); ordem.push(e.dim); }
      por.get(e.dim)!.push({ e, i: 0 });
    });
    let i = 0;
    const plano: Entrada[] = [];
    const lista = ordem.map((dim) => ({
      dim,
      itens: por.get(dim)!.map((x) => { plano.push(x.e); return { e: x.e, i: i++ }; }),
    }));
    return { lista, plano };
  });

  const teclar = (ev: KeyboardEvent) => {
    const n = grupos().plano.length;
    if (ev.key === "Escape") { ev.preventDefault(); fechar(); }
    else if (ev.key === "ArrowDown" && n) { ev.preventDefault(); setAtivo((i) => (i + 1) % n); }
    else if (ev.key === "ArrowUp" && n) { ev.preventDefault(); setAtivo((i) => (i - 1 + n) % n); }
    else if (ev.key === "Enter" && n) {
      ev.preventDefault();
      location.href = link(grupos().plano[ativo()]);
    }
  };

  const valor = (e: Entrada) => {
    const d = dados();
    if (d && e.ano < d.ultimoAno) return { v: `até ${e.ano}`, antigo: true };
    return { v: e.valor > 0 ? moedaCurta(e.valor) : "—", antigo: false };
  };

  return (
    <>
      <button type="button" class="busca-botao" classList={{ compacto: !!props.compacto }} ref={botao}
        onClick={abrir} aria-haspopup="dialog" aria-label={props.compacto ? "Buscar" : undefined}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <Show when={!props.compacto}><span>Buscar</span></Show>
      </button>

      <Show when={aberta()}>
        <div class="busca-fundo" onClick={(e) => e.target === e.currentTarget && fechar()}>
          <div class="busca-caixa" role="dialog" aria-modal="true" aria-label="Buscar no orçamento">
            <label class="busca-campo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
              <span class="visually-hidden">Buscar</span>
              <input
                ref={campo}
                type="search"
                placeholder="Órgão, programa, ação ou código"
                value={texto()}
                onInput={(e) => { setTexto(e.currentTarget.value); setAtivo(0); }}
                onKeyDown={teclar}
                role="combobox"
                aria-expanded={grupos().plano.length > 0}
                aria-controls="busca-lista"
                aria-activedescendant={grupos().plano.length ? `busca-r-${ativo()}` : undefined}
                autocomplete="off"
              />
              <button type="button" class="busca-esc" onClick={fechar}>Esc</button>
            </label>

            <Show when={erro()}><p class="busca-msg">Não foi possível carregar o índice de busca.</p></Show>
            <Show when={!erro() && !dados()}><p class="busca-msg">Carregando…</p></Show>
            <Show when={dados() && !texto().trim()}>
              <p class="busca-msg">Busque por nome ou código: “saúde”, “bolsa família”, “Fiocruz”, “26000”.</p>
            </Show>
            <Show when={dados() && texto().trim() && grupos().plano.length === 0}>
              <p class="busca-msg">Nada encontrado para “{texto()}”.</p>
            </Show>

            <div class="busca-lista" id="busca-lista" role="listbox">
              <For each={grupos().lista}>
                {(g) => (
                  <div role="group" aria-label={GRUPO[g.dim]}>
                    <div class="busca-grupo">{GRUPO[g.dim]}</div>
                    <For each={g.itens}>
                      {({ e, i }) => {
                        const v = valor(e);
                        return (
                          <a href={link(e)} id={`busca-r-${i}`} role="option" aria-selected={i === ativo()}
                            classList={{ ativo: i === ativo() }} onPointerEnter={() => setAtivo(i)}>
                            <span class="busca-nome">
                              <For each={destacar(e.nome, termos())}>
                                {(p) => (p.m ? <strong class="marca">{p.t}</strong> : <>{p.t}</>)}
                              </For>
                              <span class="busca-cod"> {e.cod}</span>
                            </span>
                            <span class="busca-valor num" classList={{ antigo: v.antigo }}>
                              {v.v}
                              <Show when={!v.antigo && e.valor > 0}><span class="busca-ano"> em {e.ano}</span></Show>
                            </span>
                          </a>
                        );
                      }}
                    </For>
                  </div>
                )}
              </For>
            </div>

            <div class="busca-rodape">
              <span>↑ ↓ para navegar · Enter para abrir</span>
              <span>Acentos e maiúsculas não importam</span>
            </div>
          </div>
        </div>
      </Show>
    </>
  );
}
