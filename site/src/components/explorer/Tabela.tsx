import { createMemo, createSignal, For, Show } from "solid-js";
import { ROTULOS_DESPESA, taxaRealizacao, type Item, type Metrica, type Rotulos } from "../../lib/dados";
import { moedaCurta, pct } from "../../lib/formato";
import { corDaRampa } from "../../lib/cores";

interface Props {
  itens: Item[];
  metrica: Metrica;
  total: number;
  rotuloNome: string;
  podeDescer: boolean;
  onEscolher: (item: Item) => void;
  rotulos?: Rotulos;
}

const LIMITE = 12;

/** Lista editorial: nome, barra proporcional, valor, parcela e % pago. */
export default function Tabela(props: Props) {
  const r = () => props.rotulos ?? ROTULOS_DESPESA;
  const [todos, setTodos] = createSignal(false);
  const ordenados = createMemo(() => [...props.itens].sort((a, b) => b.valores[props.metrica] - a.valores[props.metrica]));
  const max = createMemo(() => Math.max(1, ...ordenados().map((i) => i.valores[props.metrica])));
  const visiveis = () => (todos() ? ordenados() : ordenados().slice(0, LIMITE));
  const resto = () => ordenados().slice(LIMITE);

  return (
    <div class="lista" role="table" aria-label={`${props.rotuloNome}s`}>
      <div class="lista-linha lista-cab" role="row">
        <span role="columnheader">{props.rotuloNome}</span>
        <span role="columnheader" class="so-largo">{r().colTrilho}</span>
        <span role="columnheader" class="d">Valor</span>
        <span role="columnheader" class="d so-largo">Parcela</span>
        <span role="columnheader" class="d">{r().colTaxa}</span>
      </div>
      <For each={visiveis()}>
        {(it, i) => {
          const v = () => it.valores[props.metrica];
          const taxa = taxaRealizacao(it.valores);
          return (
            <div class="lista-linha" role="row">
              <span role="cell" class="lista-nome">
                <Show when={props.podeDescer} fallback={<span>{it.nome}</span>}>
                  <button type="button" onClick={() => props.onEscolher(it)}>{it.nome}</button>
                </Show>
                <span class="lista-cod">{it.codigo}</span>
              </span>
              <span role="cell" class="so-largo lista-trilho">
                <span style={{ width: `${(Math.max(0, v()) / max()) * 100}%`, background: corDaRampa(Math.min(1, i() / 5)) }} />
              </span>
              <span role="cell" class="d num">{moedaCurta(v())}</span>
              <span role="cell" class="d num so-largo">{pct(v() / props.total)}</span>
              <span role="cell" class="d num">{taxa === null ? "—" : `${Math.round(taxa * 100)}%`}</span>
            </div>
          );
        }}
      </For>
      <Show when={resto().length > 0}>
        <button type="button" class="lista-mais" onClick={() => setTodos(!todos())}>
          <span>
            {todos()
              ? "Mostrar só os maiores"
              : `+ ${resto().length} itens menores (${moedaCurta(resto().reduce((s, x) => s + x.valores[props.metrica], 0))}, ${pct(resto().reduce((s, x) => s + x.valores[props.metrica], 0) / props.total)})`}
          </span>
          <span>{todos() ? "recolher" : "mostrar todos"}</span>
        </button>
      </Show>
    </div>
  );
}
