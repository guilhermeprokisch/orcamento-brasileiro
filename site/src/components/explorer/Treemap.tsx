import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { hierarchy, treemap, treemapSquarify, type HierarchyRectangularNode } from "d3-hierarchy";
import { faixa, taxaRealizacao, ROTULO_METRICA, type Item, type Metrica } from "../../lib/dados";
import { moedaCompleta, moedaCurta, pct } from "../../lib/formato";
import "./treemap.css";

interface Props {
  itens: Item[];
  metrica: Metrica;
  total: number;
  podeDescer: boolean;
  onEscolher: (item: Item) => void;
}

type No = HierarchyRectangularNode<{ item?: Item; children?: unknown[] }>;

export default function Treemap(props: Props) {
  let caixa!: HTMLDivElement;
  const [largura, setLargura] = createSignal(0);
  const [foco, setFoco] = createSignal<{ item: Item; x: number; y: number } | null>(null);

  onMount(() => {
    const ro = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)));
    ro.observe(caixa);
    onCleanup(() => ro.disconnect());
  });

  const altura = () => (largura() < 640 ? 420 : 540);

  const folhas = createMemo<No[]>(() => {
    const w = largura();
    if (!w) return [];
    const m = props.metrica;
    const raiz = hierarchy<{ item?: Item; children?: unknown[] }>(
      { children: props.itens.map((item) => ({ item })) },
      (d) => d.children as { item?: Item }[] | undefined,
    )
      .sum((d) => (d.item ? Math.max(0, d.item.valores[m]) : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    treemap<{ item?: Item }>()
      .tile(treemapSquarify.ratio(1.4))
      .size([w, altura()])
      .paddingInner(2)
      .round(true)(raiz);
    return (raiz.leaves() as No[]).filter((n) => (n.value ?? 0) > 0);
  });

  const mover = (item: Item, ev: PointerEvent) => {
    const r = caixa.getBoundingClientRect();
    setFoco({ item, x: ev.clientX - r.left, y: ev.clientY - r.top });
  };
  const focarTeclado = (item: Item, n: No) =>
    setFoco({ item, x: (n.x0 + n.x1) / 2, y: (n.y0 + n.y1) / 2 });

  const posTooltip = () => {
    const f = foco();
    if (!f) return {};
    const w = largura();
    const larg = Math.min(280, w - 16);
    const esquerda = Math.min(Math.max(8, f.x + 14), w - larg - 8);
    const emCima = f.y > altura() - 150;
    return {
      left: `${esquerda}px`,
      width: `${larg}px`,
      top: emCima ? undefined : `${f.y + 14}px`,
      bottom: emCima ? `${altura() - f.y + 14}px` : undefined,
    };
  };

  return (
    <div class="tm" ref={caixa} style={{ height: `${altura()}px` }} onPointerLeave={() => setFoco(null)}>
      <Show when={largura() > 0 && folhas().length === 0}>
        <p class="tm-vazio muted">Nenhum valor positivo de {ROTULO_METRICA[props.metrica].toLowerCase()} neste nível.</p>
      </Show>
      <For each={folhas()}>
        {(n) => {
          const item = n.data.item!;
          const f = faixa(taxaRealizacao(item.valores));
          const w = n.x1 - n.x0;
          const h = n.y1 - n.y0;
          const valor = item.valores[props.metrica];
          return (
            <button
              type="button"
              class="tm-cel"
              classList={{ "tm-fixo": !props.podeDescer }}
              style={{
                left: `${n.x0}px`, top: `${n.y0}px`, width: `${w}px`, height: `${h}px`,
                background: f ? `var(--exec-${f})` : "var(--neutral-cell)",
                color: f ? `var(--exec-ink-${f})` : "var(--text)",
              }}
              aria-label={`${item.nome}: ${moedaCurta(valor)}, ${pct(valor / props.total)} do total`}
              aria-disabled={!props.podeDescer}
              onClick={() => props.podeDescer && props.onEscolher(item)}
              onPointerMove={(e) => mover(item, e)}
              onFocus={() => focarTeclado(item, n)}
              onBlur={() => setFoco(null)}
            >
              <Show when={w >= 96 && h >= 40}>
                <span class="tm-nome" style={{ "-webkit-line-clamp": h >= 70 ? 3 : 1 }}>{item.nome}</span>
                <span class="tm-valor num">{moedaCurta(valor)}</span>
              </Show>
            </button>
          );
        }}
      </For>

      <Show when={foco()}>
        {(f) => {
          const v = () => f().item.valores;
          return (
            <div class="tm-tip" style={posTooltip()} role="status">
              <div class="tm-tip-nome">{f().item.nome}</div>
              <div class="tm-tip-cod muted small">Código {f().item.codigo}</div>
              <dl class="num small">
                <dt>{ROTULO_METRICA[props.metrica]}</dt>
                <dd><strong>{moedaCompleta(v()[props.metrica])}</strong></dd>
                <dt>Parcela do total</dt>
                <dd>{pct(v()[props.metrica] / props.total)}</dd>
                <Show when={props.metrica !== "atualizado"}>
                  <dt>Dotação atualizada</dt>
                  <dd>{moedaCurta(v().atualizado)}</dd>
                </Show>
                <Show when={props.metrica !== "empenhado"}>
                  <dt>Empenhado</dt>
                  <dd>{moedaCurta(v().empenhado)}</dd>
                </Show>
                <dt>Realizado</dt>
                <dd>{moedaCurta(v().realizado)} ({pct(taxaRealizacao(v()))})</dd>
              </dl>
              <Show when={props.podeDescer}>
                <div class="muted small">Clique para detalhar</div>
              </Show>
            </div>
          );
        }}
      </Show>
    </div>
  );
}
