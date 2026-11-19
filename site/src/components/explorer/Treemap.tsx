import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { hierarchy, treemap, treemapSquarify, type HierarchyRectangularNode } from "d3-hierarchy";
import { taxaRealizacao, type Item, type Metrica } from "../../lib/dados";
import { moedaCurta, pct } from "../../lib/formato";
import { RAMPA } from "../../lib/cores";
import "./treemap.css";

interface Props {
  itens: Item[];
  metrica: Metrica;
  total: number;
  podeDescer: boolean;
  onEscolher: (item: Item) => void;
}

type Dado = { item?: Item; children?: Dado[] };
type No = HierarchyRectangularNode<Dado>;

/** Mapa de blocos editorial: cores chapadas da rampa verde, separação cor de papel, % em serifa. */
export default function Treemap(props: Props) {
  let caixa!: HTMLDivElement;
  const [largura, setLargura] = createSignal(0);
  const [foco, setFoco] = createSignal<No | null>(null);

  onMount(() => {
    const ro = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)));
    ro.observe(caixa);
    onCleanup(() => ro.disconnect());
  });

  const altura = () => (largura() < 640 ? 440 : 520);

  const folhas = createMemo<No[]>(() => {
    const w = largura();
    if (!w) return [];
    const m = props.metrica;
    const raiz = hierarchy<Dado>({ children: props.itens.map((item) => ({ item })) })
      .sum((d) => (d.item ? Math.max(0, d.item.valores[m]) : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    treemap<Dado>().tile(treemapSquarify.ratio(1.3)).size([w, altura()]).paddingInner(2).round(true)(raiz);
    return (raiz.leaves() as No[]).filter((n) => (n.value ?? 0) > 0 && n.x1 - n.x0 >= 1 && n.y1 - n.y0 >= 1);
  });

  // Cor pela posição no ranking, como no mock: 1º verde-escuro, 2º verde, depois mais claros.
  const cor = (rank: number) => ({ fundo: RAMPA[Math.min(rank, RAMPA.length - 1)], escuro: rank < 2 });
  const pctBloco = (p: number) => (p >= 0.01 ? `${Math.round(p * 100)}%` : pct(p));

  const posTip = () => {
    const n = foco();
    if (!n) return {};
    const w = largura();
    const larg = Math.min(280, w - 16);
    const cx = (n.x0 + n.x1) / 2;
    const esquerda = Math.min(Math.max(8, cx - larg / 2), w - larg - 8);
    const embaixo = n.y0 < 120;
    return {
      left: `${esquerda}px`,
      width: `${larg}px`,
      top: embaixo ? `${Math.min(n.y1, altura() - 40) + 8}px` : undefined,
      bottom: embaixo ? undefined : `${altura() - n.y0 + 8}px`,
    };
  };

  return (
    <div class="tm" ref={caixa} style={{ height: `${altura()}px` }} onPointerLeave={() => setFoco(null)}>
      <Show when={largura() > 0 && folhas().length === 0}>
        <p class="tm-vazio">Nenhum valor positivo neste nível.</p>
      </Show>
      <div class="tm-celulas">
        <For each={folhas()}>
          {(n, rank) => {
            const item = n.data.item!;
            const w = n.x1 - n.x0;
            const h = n.y1 - n.y0;
            const c = cor(rank());
            const parcela = (n.value ?? 0) / props.total;
            const area = w * h;
            const tamPct = Math.max(18, Math.min(64, Math.sqrt(area) / 5.5));
            const taxa = taxaRealizacao(item.valores);
            return (
              <button
                type="button"
                class="tm-cel"
                classList={{ "tm-fixo": !props.podeDescer, "tm-ativo": foco() === n, "tm-escuro": c.escuro }}
                style={{ left: `${n.x0}px`, top: `${n.y0}px`, width: `${w}px`, height: `${h}px`, "--fundo": c.fundo }}
                aria-label={`${item.nome}: ${moedaCurta(item.valores[props.metrica])}, ${pct(parcela)} do total`}
                aria-disabled={!props.podeDescer}
                onClick={() => props.podeDescer && props.onEscolher(item)}
                onPointerEnter={() => setFoco(() => n)}
                onFocus={() => setFoco(() => n)}
                onBlur={() => setFoco(null)}
              >
                <Show when={w >= 52 && h >= 34}>
                  <span class="tm-pct" style={{ "font-size": `${tamPct}px` }}>{pctBloco(parcela)}</span>
                </Show>
                <Show when={w >= 120 && h >= 90}>
                  <span class="tm-rotulo">
                    <strong>{item.nome}</strong>
                    <span class="num">{moedaCurta(item.valores[props.metrica])}{taxa !== null ? ` · ${Math.round(taxa * 100)}% pago` : ""}</span>
                  </span>
                </Show>
              </button>
            );
          }}
        </For>
      </div>

      <Show when={foco()}>
        {(n) => {
          const item = () => n().data.item!;
          const taxa = () => taxaRealizacao(item().valores);
          return (
            <div class="tm-tip" style={posTip()} role="status">
              <strong>{item().nome}</strong>
              <dl class="num">
                <dt>Dotação atualizada</dt><dd>{moedaCurta(item().valores.atualizado)}</dd>
                <dt>Empenhado</dt><dd>{moedaCurta(item().valores.empenhado)}</dd>
                <dt>Pago</dt><dd>{moedaCurta(item().valores.realizado)}{taxa() !== null ? ` (${pct(taxa())})` : ""}</dd>
                <dt>Parcela</dt><dd>{pct((n().value ?? 0) / props.total)}</dd>
              </dl>
              <Show when={props.podeDescer}><span class="tm-dica">Clique para detalhar</span></Show>
            </div>
          );
        }}
      </Show>
    </div>
  );
}
