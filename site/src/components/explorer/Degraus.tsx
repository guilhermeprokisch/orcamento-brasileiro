/**
 * Os degraus: o caminho até aqui nos exploradores (estilo em styles/degraus.css). Um degrau por nível escolhido, com o
 * tipo do nível, o nome, o valor e quanto ele é do anterior; os anteriores voltam para aquele nível. O mesmo HTML das
 * páginas de busca (public/explorador/trilha.js), para os exploradores terem um só desenho.
 */
import { createSignal, For, Show, type JSX } from "solid-js";
import "../../styles/degraus.css";

export interface Degrau {
  /** O tipo do nível, em versalete: "Órgão", "Unidade", "Quem mandou". */
  tipo: string;
  nome: string;
  /** O valor já formatado ("R$ 254,1 bi"). */
  valor?: string;
  /** A fatia deste degrau no anterior (0 a 1) e de quem: "do ministério". */
  fatia?: number | null;
  de?: string;
  /** O endereço do nível (para abrir em outra aba) e o que fazer no clique. */
  href?: string;
  ir?: () => void;
}

/** "Ministério da Saúde" → "do ministério"; senão, o nome do nível ("do órgão"). Para "93% do ministério". */
const ARTIGO: Record<string, string> = {
  ministério: "do ministério", fundo: "do fundo", secretaria: "da secretaria", fundação: "da fundação", instituto: "do instituto",
  universidade: "da universidade", comando: "do comando", agência: "da agência", departamento: "do departamento",
  superintendência: "da superintendência", empresa: "da empresa", banco: "do banco", conselho: "do conselho", hospital: "do hospital",
  programa: "do programa", encargos: "dos encargos", operações: "das operações", serviço: "do serviço", tribunal: "do tribunal",
  justiça: "da justiça", câmara: "da câmara", senado: "do senado", presidência: "da presidência", gabinete: "do gabinete",
};
export function deQuem(nome: string, padrao: string): string {
  const primeira = nome.trim().split(/\s+/)[0]?.toLowerCase() ?? "";
  return ARTIGO[primeira] ?? padrao;
}

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
/** 0,93 → "93%"; 0,044 → "4,4%"; 0,0004 → "<0,1%". */
export function fatiaTexto(f: number): string {
  const p = f * 100;
  return p >= 99.5 ? "100%" : p >= 10 ? `${nf0.format(p)}%` : p >= 0.1 ? `${nf1.format(p)}%` : "<0,1%";
}

function abrir(ev: MouseEvent, ir?: () => void) {
  if (!ir || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
  ev.preventDefault();
  ir();
}

export default function Degraus(props: {
  passos: Degrau[];
  /** À direita da linha de cima (os controles do explorador). */
  extra?: JSX.Element;
  /** O texto da linha de cima quando ainda não há caminho (só o primeiro degrau). */
  dicaInicio?: string;
}) {
  const [aberto, setAberto] = createSignal(false);
  const temCaminho = () => props.passos.length > 1;
  return (
    <div class="degraus" classList={{ aberto: aberto() }}>
      <div class="degraus-cab">
        <span class="degraus-dica">
          {temCaminho() ? "O caminho até aqui: clique num degrau para voltar" : props.dicaInicio ?? ""}
        </span>
        {props.extra}
      </div>
      <Show when={temCaminho()}>
        <button type="button" class="degraus-abrir" aria-expanded={aberto()} onClick={() => setAberto(!aberto())}>
          Caminho: {props.passos.length} passos <span>{aberto() ? "fechar" : "abrir"}</span>
        </button>
        <ol class="degraus-lista" aria-label="O caminho até aqui">
          <For each={props.passos}>
            {(p, i) => {
              const atual = () => i() === props.passos.length - 1;
              const corpo = () => (
                <>
                  <span class="degrau-tipo">{p.tipo}</span>
                  <span class="degrau-nome" title={p.nome}>{p.nome}</span>
                  <Show when={p.valor}>
                    <span class="degrau-valor">
                      <strong>{p.valor}</strong>
                      <Show when={p.fatia != null && p.de}> <span class="degrau-parte">{fatiaTexto(p.fatia!)} {p.de}</span></Show>
                    </span>
                  </Show>
                  <Show when={p.fatia != null}>
                    <span class="degrau-barra" aria-hidden="true"><i style={{ width: `${Math.max(2, Math.min(100, Math.round(p.fatia! * 100)))}%` }} /></span>
                  </Show>
                </>
              );
              return (
                <li>
                  <Show when={!atual()} fallback={<div class="degrau" aria-current="page">{corpo()}</div>}>
                    <a class="degrau" href={p.href ?? "#"} onClick={(ev) => { setAberto(false); abrir(ev, p.ir); }}>{corpo()}</a>
                  </Show>
                </li>
              );
            }}
          </For>
        </ol>
      </Show>
    </div>
  );
}

/** "← Voltar a {nível anterior}", logo acima do conteúdo. */
export function Voltar(props: { para: string; onClick: () => void }) {
  return (
    <button type="button" class="degraus-voltar" onClick={props.onClick}>
      ← <span>Voltar a {props.para}</span>
    </button>
  );
}
