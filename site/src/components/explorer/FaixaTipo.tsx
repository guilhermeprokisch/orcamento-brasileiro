import { createMemo, For, Show } from "solid-js";
import { agrupar, TIPOS_DESPESA, type DocAno, type Dim, type Filtro, type Metrica } from "../../lib/dados";
import { moedaCurta, pct } from "../../lib/formato";
import { termoHtml } from "../../lib/glossario";

interface Props {
  doc: DocAno;
  ano: number;
  filtros: Filtro[];
  metrica: Metrica;
  semRefin: boolean;
  fator: number;
  onEscolher: (cod: string) => void;
  onSemRefin: () => void;
}

/** "Deste órgão, …": o sujeito da frase pelo último passo da trilha. */
const DESTE: Record<Dim, string> = {
  orgao: "Deste órgão", uo: "Desta unidade", funcao: "Desta área", subfuncao: "Desta subárea",
  programa: "Deste programa", acao: "Desta ação", gnd: "Deste grupo de despesa", tipo: "Deste tipo",
};

/** Como cada tipo entra na frase: "92% é despesa obrigatória". */
const NA_FRASE: Record<string, [singular: string, tudo: string]> = {
  obr: ["é despesa obrigatória", "é despesa obrigatória"],
  esc: ["é escolha do governo", "é escolha do governo"],
  eme: ["são emendas parlamentares", "é emenda parlamentar"],
  fin: ["é despesa financeira, quase toda com a dívida", "é despesa financeira, quase toda com a dívida"],
  sem: ["não tem essa informação", "está sem essa informação"],
};

/** A explicação curta de cada tipo, com o balão do glossário em cada nome. */
const EXPLICA = [
  `${termoHtml("despesa-obrigatoria", "Obrigatória")}: a lei ou a Constituição manda pagar.`,
  `${termoHtml("despesa-discricionaria", "Escolha do governo")}: o que ele decide onde pôr.`,
  `${termoHtml("emenda-parlamentar", "Emendas")}: o Congresso indica.`,
  `${termoHtml("despesa-financeira", "Financeira")}: juros, parcelas e rolagem da dívida, e empréstimos.`,
].join(" ");

const juntar = (partes: string[]) =>
  partes.length <= 1 ? (partes[0] ?? "") : `${partes.slice(0, -1).join(", ")} e ${partes.at(-1)}`;

/**
 * A divisão do que está na tela entre gasto obrigatório, escolha do governo, emendas e despesa financeira
 * (o identificador de resultado primário do SIOP): uma barra, a legenda e uma frase. Clicar num pedaço
 * filtra o Explorer por aquele tipo.
 */
export default function FaixaTipo(props: Props) {
  const partes = createMemo(() => {
    const g = agrupar(props.doc, props.filtros, "tipo", props.semRefin);
    const total = g.itens.reduce((s, i) => s + Math.max(0, i.valores[props.metrica]), 0);
    if (total <= 0) return null;
    const ordem = TIPOS_DESPESA.map((t) => t.cod);
    const lista = TIPOS_DESPESA.map((t) => {
      const item = g.itens.find((i) => i.codigo === t.cod);
      const valor = Math.max(0, item?.valores[props.metrica] ?? 0);
      return { ...t, valor: valor * props.fator, parcela: valor / total };
    // "Sem informação" são linhas que não acharam par no SIOP: em geral centavos; só aparece se pesar.
    }).filter((p) => p.valor > 0 && (p.cod !== "sem" || p.parcela >= 0.001));
    lista.sort((a, b) => ordem.indexOf(a.cod) - ordem.indexOf(b.cod));
    return lista;
  });

  const frase = () => {
    const l = partes();
    if (!l?.length) return "";
    const ultimo = props.filtros.at(-1);
    const sujeito = ultimo ? DESTE[ultimo.dim] : `Do orçamento federal de ${props.ano}`;
    const so = l.find((p) => p.parcela >= 0.995);
    if (so) return `${sujeito}, praticamente tudo ${NA_FRASE[so.cod][1]}.`;
    const ditos = [...l].sort((a, b) => b.parcela - a.parcela).filter((p) => p.parcela >= 0.005);
    const resto = ditos.map((p) => `${pctFrase(p.parcela)} ${NA_FRASE[p.cod][0]}`);
    return `${sujeito}, ${juntar(resto)}.`;
  };

  const financeira = () => partes()?.find((p) => p.cod === "fin")?.parcela ?? 0;

  return (
    <Show when={partes()?.length}>
      <section class="exp-tipo" aria-label="Obrigatório ou não">
        <p class="exp-tipo-frase">{frase()}</p>
        <div class="exp-tipo-barra" role="list">
          <For each={partes()!}>
            {(p) => (
              <button type="button" role="listitem" class="exp-tipo-pedaco" style={{ "flex-grow": p.parcela, background: p.cor }}
                title={`${p.nome}: ${moedaCurta(p.valor)} (${pct(p.parcela)}). Clique para ver só este tipo.`}
                aria-label={`${p.nome}: ${moedaCurta(p.valor)}, ${pct(p.parcela)}. Ver só este tipo.`}
                onClick={() => props.onEscolher(p.cod)} />
            )}
          </For>
        </div>
        <ul class="exp-tipo-legenda">
          <For each={partes()!}>
            {(p) => (
              <li>
                <button type="button" class="exp-tipo-item" onClick={() => props.onEscolher(p.cod)} title="Ver só este tipo">
                  <span class="cor" style={{ background: p.cor }} aria-hidden="true" />
                  <span class="nome">{p.nome}</span>
                  <span class="num">{pct(p.parcela)} · {moedaCurta(p.valor)}</span>
                </button>
              </li>
            )}
          </For>
        </ul>
        <p class="exp-tipo-nota">
          <span innerHTML={EXPLICA} />{" "}
          <a href="/contas#amarrado">Quanto do orçamento está amarrado →</a>
        </p>
        <Show when={props.ano === 2020}>
          <p class="exp-tipo-nota">
            Em 2020, os gastos da covid, como o auxílio emergencial, vieram por créditos extraordinários marcados como
            discricionários: por isso a escolha do governo é bem maior nesse ano.
          </p>
        </Show>
        <Show when={!props.semRefin && financeira() > 0.25}>
          <p class="exp-tipo-nota">
            Boa parte da despesa financeira é a rolagem da dívida, que troca títulos que vencem por novos.{" "}
            <button type="button" class="link" onClick={() => props.onSemRefin()}>Ver sem o refinanciamento</button>
          </p>
        </Show>
      </section>
    </Show>
  );
}

/** 0,4% e 92%: menos de 10% com uma casa, para não sumir. */
function pctFrase(p: number): string {
  return p < 0.1 ? pct(p) : `${Math.round(p * 100)}%`;
}
