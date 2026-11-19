import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { hierarchy, treemap, treemapSquarify, type HierarchyRectangularNode } from "d3-hierarchy";
import { scaleLinear } from "d3-scale";
import { type Item, type Metrica } from "../../lib/dados";
import { moedaExtenso, pct } from "../../lib/formato";
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

// Rampa sequencial de um só tom: maior valor = mais escuro.
const CLARO = "#46b9d7";
const ESCURO = "#1c4956";

export default function Treemap(props: Props) {
  let caixa!: HTMLDivElement;
  const [largura, setLargura] = createSignal(0);
  const [foco, setFoco] = createSignal<{ no: No } | null>(null);

  onMount(() => {
    const ro = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)));
    ro.observe(caixa);
    onCleanup(() => ro.disconnect());
  });

  const altura = () => (largura() < 640 ? 440 : 560);

  const folhas = createMemo<No[]>(() => {
    const w = largura();
    if (!w) return [];
    const m = props.metrica;
    const raiz = hierarchy<Dado>({ children: props.itens.map((item) => ({ item })) })
      .sum((d) => (d.item ? Math.max(0, d.item.valores[m]) : 0))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    treemap<Dado>()
      .tile(treemapSquarify.ratio(1.2))
      .size([w, altura()])
      .paddingInner(4)
      .round(true)(raiz);
    // Com paddingInner, blocos minúsculos podem sair com largura/altura negativa.
    return (raiz.leaves() as No[]).filter((n) => (n.value ?? 0) > 0 && n.x1 - n.x0 >= 1 && n.y1 - n.y0 >= 1);
  });

  const cor = createMemo(() => {
    const vs = folhas().map((n) => n.value ?? 0);
    const max = Math.max(1, ...vs);
    const min = Math.min(max, ...vs);
    const esc = scaleLinear<string>().domain([min, max]).range([CLARO, ESCURO]);
    const t = scaleLinear().domain([min, max]).range([0, 1]);
    return (v: number) => ({ fundo: esc(v), escuro: t(v) > 0.45 });
  });

  const posTooltip = () => {
    const f = foco();
    if (!f) return {};
    const n = f.no;
    const w = largura();
    const larg = Math.min(260, w - 16);
    const cx = (n.x0 + n.x1) / 2;
    const esquerda = Math.min(Math.max(8, cx - larg / 2), w - larg - 8);
    const abaixo = n.y0 < 140;
    return {
      left: `${esquerda}px`,
      width: `${larg}px`,
      top: abaixo ? `${Math.min(n.y1, altura() - 20) - 10}px` : undefined,
      bottom: abaixo ? undefined : `${altura() - n.y0 - 10}px`,
      "--seta": `${Math.min(Math.max(16, cx - esquerda), larg - 16)}px`,
    } as Record<string, string | undefined>;
  };

  return (
    <div class="tm" ref={caixa} style={{ height: `${altura()}px` }} onPointerLeave={() => setFoco(null)}>
      <Show when={largura() > 0 && folhas().length === 0}>
        <p class="tm-vazio">Nenhum valor positivo neste nível.</p>
      </Show>
      <div class="tm-celulas">
      <For each={folhas()}>
        {(n) => {
          const item = n.data.item!;
          const w = n.x1 - n.x0;
          const h = n.y1 - n.y0;
          const c = cor()(n.value ?? 0);
          const parcela = (n.value ?? 0) / props.total;
          const ativo = () => foco()?.no === n;
          return (
            <button
              type="button"
              class="tm-cel"
              classList={{ "tm-fixo": !props.podeDescer, "tm-ativo": ativo(), "tm-claro": !c.escuro }}
              style={{
                left: `${n.x0}px`, top: `${n.y0}px`, width: `${w}px`, height: `${h}px`,
                "--fundo": c.fundo,
              }}
              aria-label={`${item.nome}: ${moedaExtenso(item.valores[props.metrica])}, ${pct(parcela)} do total`}
              aria-disabled={!props.podeDescer}
              onClick={() => props.podeDescer && props.onEscolher(item)}
              onPointerEnter={() => setFoco({ no: n })}
              onFocus={() => setFoco({ no: n })}
              onBlur={() => setFoco(null)}
            >
              <Show when={w >= 56 && h >= 34}>
                <span class="tm-nome">{item.nome}</span>
                <span class="tm-pct num">{pct(parcela)}</span>
              </Show>
            </button>
          );
        }}
      </For>
      </div>

      <Show when={foco()}>
        {(f) => {
          const item = () => f().no.data.item!;
          const valor = () => item().valores[props.metrica];
          return (
            <div class="tm-tip" classList={{ "tm-tip-baixo": f().no.y0 < 140 }} style={posTooltip()} role="status">
              <div class="tm-tip-nome">{item().nome}</div>
              <div class="tm-tip-numeros">
                <div>
                  <div class="tm-tip-v num">{moedaExtenso(valor())}</div>
                  <div class="tm-tip-r">Valor</div>
                </div>
                <div>
                  <div class="tm-tip-v num">{pct(valor() / props.total)}</div>
                  <div class="tm-tip-r">Percentual</div>
                </div>
              </div>
            </div>
          );
        }}
      </Show>
    </div>
  );
}
