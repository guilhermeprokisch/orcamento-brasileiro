import { createMemo, createSignal, For, Show } from "solid-js";
import { ROTULO_METRICA, type Metrica, type Valores } from "../../lib/dados";
import { moedaCurta, moedaExtenso } from "../../lib/formato";
import "./barras-ano.css";

export interface Ponto {
  ano: number;
  valores: Valores;
}

interface Props {
  serie: Ponto[] | null; // null = carregando
  metrica: Metrica;
  anoSelecionado: number | null;
  anoCorrente: number;
  altura: number;
  /** "extremos": primeiro, selecionado e último ano; "todos": um rótulo por ano. */
  rotulos: "extremos" | "todos";
  onAno?: (ano: number) => void;
}

/** Barras por ano no estilo editorial: areia, ano escolhido em verde, ano corrente hachurado. */
export default function BarrasAno(props: Props) {
  const [foco, setFoco] = createSignal<number | null>(null);
  const serie = () => props.serie ?? [];
  const max = createMemo(() => Math.max(1, ...serie().map((p) => p.valores[props.metrica])));
  const n = () => Math.max(1, serie().length);
  const pontoFoco = () => serie().find((p) => p.ano === foco()) ?? null;
  const idxFoco = () => serie().findIndex((p) => p.ano === foco());

  const rotulo = (p: Ponto, i: number) => {
    const curto = props.rotulos === "todos" ? `’${String(p.ano).slice(2)}` : String(p.ano);
    const txt = p.ano === props.anoCorrente ? `${curto}*` : curto;
    if (props.rotulos === "todos") return txt;
    const ultimo = i === serie().length - 1;
    return i === 0 || ultimo || p.ano === props.anoSelecionado ? txt : "";
  };

  return (
    <div class="ba" onPointerLeave={() => setFoco(null)}>
      <Show when={props.serie === null}>
        <div class="ba-carregando" style={{ height: `${props.altura}px` }}>Carregando a série…</div>
      </Show>
      <Show when={props.serie !== null}>
        <div class="ba-barras" style={{ height: `${props.altura}px`, "grid-template-columns": `repeat(${n()}, minmax(0, 1fr))` }}>
          <For each={serie()}>
            {(p) => {
              const v = () => Math.max(0, p.valores[props.metrica]);
              return (
                <button
                  type="button"
                  class="ba-barra"
                  classList={{
                    sel: p.ano === props.anoSelecionado,
                    parcial: p.ano === props.anoCorrente && p.ano !== props.anoSelecionado,
                    foco: foco() === p.ano,
                  }}
                  style={{ height: `${(v() / max()) * 100}%` }}
                  aria-label={`${p.ano}: ${moedaExtenso(v())}`}
                  onPointerEnter={() => setFoco(p.ano)}
                  onFocus={() => setFoco(p.ano)}
                  onBlur={() => setFoco(null)}
                  onClick={() => props.onAno?.(p.ano)}
                  disabled={!props.onAno}
                />
              );
            }}
          </For>
        </div>
        <div class="ba-rotulos" style={{ "grid-template-columns": `repeat(${n()}, minmax(0, 1fr))` }}>
          <For each={serie()}>
            {(p, i) => <span classList={{ sel: p.ano === props.anoSelecionado }}>{rotulo(p, i())}</span>}
          </For>
        </div>
        <Show when={pontoFoco()}>
          {(p) => (
            <div class="ba-tip" role="status"
              style={{ left: `${Math.min(Math.max(((idxFoco() + 0.5) / n()) * 100, 12), 88)}%` }}>
              <strong>{p().ano}{p().ano === props.anoCorrente ? " (em execução)" : ""}</strong>
              <span class="num">{ROTULO_METRICA[props.metrica]}: {moedaCurta(p().valores[props.metrica])}</span>
              <Show when={props.onAno && p().ano !== props.anoSelecionado}><span class="ba-dica">Clique para ver {p().ano}</span></Show>
            </div>
          )}
        </Show>
      </Show>
    </div>
  );
}
