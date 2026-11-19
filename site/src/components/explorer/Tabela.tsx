import { createMemo, createSignal, For, Show } from "solid-js";
import { ROTULO_METRICA, type Item, type Metrica } from "../../lib/dados";
import { moedaCompleta, pct } from "../../lib/formato";

interface Props {
  itens: Item[];
  metrica: Metrica;
  total: number;
  rotuloNome: string;
  podeDescer: boolean;
  onEscolher: (item: Item) => void;
}

type Coluna = "nome" | "valor" | "parcela";

export default function Tabela(props: Props) {
  const [ordem, setOrdem] = createSignal<{ col: Coluna; desc: boolean }>({ col: "valor", desc: true });

  const linhas = createMemo(() => {
    const { col, desc } = ordem();
    const m = props.metrica;
    const s = [...props.itens].sort((a, b) =>
      col === "nome" ? a.nome.localeCompare(b.nome, "pt-BR") : a.valores[m] - b.valores[m],
    );
    return desc ? s.reverse() : s;
  });

  const ordenar = (col: Coluna) =>
    setOrdem((o) => ({ col, desc: o.col === col ? !o.desc : col !== "nome" }));

  const Cabecalho = (p: { col: Coluna; rotulo: string; classe?: string }) => {
    const ativo = () => ordem().col === p.col || (p.col === "parcela" && ordem().col === "valor");
    return (
      <th scope="col" class={p.classe}
        aria-sort={ativo() ? (ordem().desc ? "descending" : "ascending") : "none"}>
        <button type="button" onClick={() => ordenar(p.col)}>
          {p.rotulo}
          <span class="seta" classList={{ ativo: ativo(), desc: ordem().desc }} aria-hidden="true" />
        </button>
      </th>
    );
  };

  return (
    <div class="ex-tabela-wrap">
      <table class="ex-tabela">
        <thead>
          <tr>
            <Cabecalho col="nome" rotulo={props.rotuloNome} />
            <Cabecalho col="valor" rotulo={ROTULO_METRICA[props.metrica]} classe="n" />
            <Cabecalho col="parcela" rotulo="Percentual do total" classe="n" />
          </tr>
        </thead>
        <tbody>
          <For each={linhas()}>
            {(it) => (
              <tr>
                <th scope="row">
                  <Show when={props.podeDescer} fallback={<span>{it.nome}</span>}>
                    <button type="button" class="link" onClick={() => props.onEscolher(it)}>{it.nome}</button>
                  </Show>
                  <span class="cod">{it.codigo}</span>
                </th>
                <td class="n num">{moedaCompleta(it.valores[props.metrica])}</td>
                <td class="n num">{pct(it.valores[props.metrica] / props.total)}</td>
              </tr>
            )}
          </For>
        </tbody>
      </table>
    </div>
  );
}
