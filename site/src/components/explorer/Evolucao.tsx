import { createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import { scaleBand, scaleLinear } from "d3-scale";
import { ROTULO_METRICA, taxaRealizacao, type Metrica, type Valores } from "../../lib/dados";
import { moedaCompleta, moedaCurta, moedaExtenso, pct } from "../../lib/formato";
import "./evolucao.css";

export interface Ponto {
  ano: number;
  valores: Valores;
}

interface Props {
  serie: Ponto[] | null; // null = carregando
  metrica: Metrica;
  anoSelecionado: number | null;
  anoCorrente: number;
  onAno: (ano: number) => void;
  compacto?: boolean;
}

// Barra com cantos arredondados só no topo, presa à linha de base.
function barra(x: number, y: number, w: number, h: number, r = 4) {
  if (h <= 0) return "";
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + rr}Q${x},${y} ${x + rr},${y}H${x + w - rr}Q${x + w},${y} ${x + w},${y + rr}V${y + h}Z`;
}

let contador = 0;

export default function Evolucao(props: Props) {
  let caixa!: HTMLDivElement;
  const idHachura = `ev-hachura-${++contador}`;
  const [largura, setLargura] = createSignal(0);
  const [foco, setFoco] = createSignal<number | null>(null);

  onMount(() => {
    const ro = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)));
    ro.observe(caixa);
    onCleanup(() => ro.disconnect());
  });

  const altura = () => (props.compacto ? 64 : 240);
  const M = () => (props.compacto
    ? { top: 4, right: 0, bottom: 4, left: 0 }
    : { top: 28, right: 8, bottom: 28, left: 64 });

  const serie = () => props.serie ?? [];

  const escalas = createMemo(() => {
    const m = M();
    const s = serie();
    const x = scaleBand<number>()
      .domain(s.map((p) => p.ano))
      .range([m.left, Math.max(m.left + 1, largura() - m.right)])
      .padding(props.compacto ? 0.2 : 0.28);
    const max = Math.max(1, ...s.map((p) => p.valores[props.metrica]));
    const y = scaleLinear().domain([0, max]).nice(4).range([altura() - m.bottom, m.top]);
    return { x, y };
  });

  const rotuloAno = (a: number) => {
    const curto = largura() < 560 ? `’${String(a).slice(2)}` : String(a);
    return a === props.anoCorrente ? `${curto}*` : curto;
  };

  const vazio = () => serie().length > 0 && serie().every((p) => p.valores[props.metrica] === 0);
  const pontoFoco = () => serie().find((p) => p.ano === foco()) ?? null;

  const posTip = () => {
    const p = pontoFoco();
    if (!p) return {};
    const { x } = escalas();
    const cx = (x(p.ano) ?? 0) + x.bandwidth() / 2;
    const larg = props.compacto ? 200 : Math.min(290, largura() - 8);
    const esquerda = Math.min(Math.max(props.compacto ? -40 : 4, cx - larg / 2), largura() - larg + (props.compacto ? 40 : -4));
    return props.compacto
      ? { left: `${esquerda}px`, width: `${larg}px`, top: `${altura() + 6}px` }
      : { left: `${esquerda}px`, width: `${larg}px`, top: "0px" };
  };

  return (
    <div class="ev-grafico" classList={{ compacto: !!props.compacto }} ref={caixa}
      style={{ height: `${altura()}px` }} onPointerLeave={() => setFoco(null)}>
      <Show when={props.serie === null}>
        <div class="ev-carregando" aria-busy="true">{props.compacto ? "Carregando…" : "Carregando a série histórica…"}</div>
      </Show>
      <Show when={vazio()}>
        <div class="ev-carregando">Sem valores em nenhum ano.</div>
      </Show>
      <Show when={largura() > 0 && serie().length > 0 && !vazio()}>
        <svg width={largura()} height={altura()} role="img"
          aria-label={`${ROTULO_METRICA[props.metrica]} por ano, de ${serie()[0]?.ano} a ${serie().at(-1)?.ano}`}>
          <defs>
            <pattern id={idHachura} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" class="ev-hachura-fundo" />
              <rect width="3" height="6" class="ev-hachura-traco" />
            </pattern>
          </defs>
          <Show when={!props.compacto}>
            <For each={escalas().y.ticks(4)}>
              {(t) => (
                <g>
                  <line class="ev-grade" x1={M().left} x2={largura() - M().right} y1={escalas().y(t)} y2={escalas().y(t)} />
                  <text class="ev-eixo" x={M().left - 8} y={escalas().y(t)} dy="0.32em" text-anchor="end">
                    {t === 0 ? "0" : moedaCurta(t).replace("R$ ", "")}
                  </text>
                </g>
              )}
            </For>
          </Show>
          <For each={serie()}>
            {(p) => {
              const x = () => escalas().x(p.ano) ?? 0;
              const bw = () => escalas().x.bandwidth();
              const v = () => Math.max(0, p.valores[props.metrica]);
              const y = () => escalas().y(v());
              const h = () => altura() - M().bottom - y();
              const sel = () => p.ano === props.anoSelecionado;
              const parcial = () => p.ano === props.anoCorrente && !sel() && foco() !== p.ano;
              return (
                <g class="ev-coluna" onPointerEnter={() => setFoco(p.ano)} onClick={() => props.onAno(p.ano)}>
                  <rect class="ev-alvo" x={x() - 2} y={M().top} width={bw() + 4} height={altura() - M().top - M().bottom} />
                  <path
                    d={barra(x(), y(), bw(), h(), props.compacto ? 2 : 4)}
                    class="ev-barra"
                    classList={{ sel: sel(), foco: foco() === p.ano, parcial: parcial() }}
                    style={parcial() ? { fill: `url(#${idHachura})` } : undefined}
                  />
                  <Show when={sel() && !props.compacto}>
                    {(() => {
                      // Perto das bordas, ancora o rótulo para dentro do gráfico.
                      const cx = () => x() + bw() / 2;
                      const ancora = () => (cx() > largura() - 44 ? "end" : cx() < M().left + 44 ? "start" : "middle");
                      const tx = () => (ancora() === "end" ? x() + bw() : ancora() === "start" ? x() : cx());
                      return (
                        <text class="ev-valor" x={tx()} y={y() - 8} text-anchor={ancora()}>{moedaCurta(v())}</text>
                      );
                    })()}
                  </Show>
                  <Show when={!props.compacto}>
                    <text class="ev-ano" classList={{ sel: sel() }} x={x() + bw() / 2} y={altura() - 8} text-anchor="middle">
                      {rotuloAno(p.ano)}
                    </text>
                  </Show>
                </g>
              );
            }}
          </For>
          <line class="ev-base" x1={M().left} x2={largura() - M().right} y1={altura() - M().bottom} y2={altura() - M().bottom} />
        </svg>
      </Show>

      <Show when={pontoFoco()}>
        {(p) => (
          <div class="ev-tip" style={posTip()} role="status">
            <div class="ev-tip-ano">{p().ano}{p().ano === props.anoCorrente ? " (em execução)" : ""}</div>
            <Show when={!props.compacto} fallback={
              <div class="ev-tip-linha num">
                {ROTULO_METRICA[props.metrica]}: <strong>{moedaExtenso(p().valores[props.metrica])}</strong>
              </div>
            }>
              <dl>
                <dt>Dotação atualizada</dt><dd class="num">{moedaExtenso(p().valores.atualizado)}</dd>
                <dt>Empenhado</dt><dd class="num">{moedaExtenso(p().valores.empenhado)}</dd>
                <dt>Realizado</dt><dd class="num">{moedaExtenso(p().valores.realizado)}</dd>
                <dt>Realizado / dotação</dt><dd class="num">{pct(taxaRealizacao(p().valores))}</dd>
              </dl>
            </Show>
            <Show when={p().ano !== props.anoSelecionado}>
              <div class="ev-tip-dica">Clique para ver {p().ano}</div>
            </Show>
          </div>
        )}
      </Show>

      <table class="visually-hidden">
        <caption>{ROTULO_METRICA[props.metrica]} por ano</caption>
        <thead><tr><th scope="col">Ano</th><th scope="col">{ROTULO_METRICA[props.metrica]}</th></tr></thead>
        <tbody>
          <For each={serie()}>
            {(p) => <tr><th scope="row">{p.ano}</th><td>{moedaCompleta(p.valores[props.metrica])}</td></tr>}
          </For>
        </tbody>
      </table>
    </div>
  );
}
