/**
 * A vista "Cascata" do Explorer: o mesmo orçamento numa tela livre (Canvas, components/cascata/tela.ts), para abrir
 * galho por galho, do total às ações. Usa o arquivo do ano, a métrica, o "sem refinanciamento" e a correção da
 * inflação do Explorer, e fica em sincronia com os degraus dele: clicar numa caixa muda o caminho do Explorer (o título
 * e os degraus acompanham), e voltar pelos degraus leva a tela até lá. "Ver em blocos" troca para o mapa no mesmo ponto.
 *
 * A cascata segue órgão › unidade › programa › ação › tipo de gasto. Um caminho com outros recortes (área, obrigatório
 * ou não…) não cabe nela: a tela mostra o orçamento inteiro, com um aviso.
 */
import { createEffect, createSignal, For, on, onCleanup, Show } from "solid-js";
import { TIPOS_DESPESA, type DocAno, type Filtro, type Metrica } from "../../lib/dados";
import { caminhoAte, exibir, filhos, fonteDoDoc, NIVEIS, populacaoDoBrasil, type Fonte, type No } from "../cascata/dados";
import { criarTela, type Tela } from "../cascata/tela";
import { htmlDetalhe } from "../cascata/detalhes";
import "../cascata/cascata.css";

interface Props {
  doc: DocAno;
  ano: number;
  metrica: Metrica;
  semRefin: boolean;
  /** Fator do IPCA (1: valores nominais). */
  fator: number;
  filtros: Filtro[];
  onCaminho: (filtros: Filtro[]) => void;
  onVerMapa: (filtros: Filtro[]) => void;
  /** A faixa "obrigatório ou não", com a mesma legenda de cores, já está acima da cascata: não repetir. */
  legendaAcima?: boolean;
}

const ABA: Record<string, string> = { funcao: "área", subfuncao: "subárea", tipo: "obrigatório ou não" };
const segueCascata = (fs: Filtro[]) => fs.every((f, i) => f.dim === NIVEIS[i]?.[0]);
const chave = (fs: Filtro[]) => fs.map((f) => `${f.dim}:${f.cod}`).join(",");
const filtrosDe = (n: No): Filtro[] => caminhoAte(n).slice(1).map((x, i) => ({ dim: NIVEIS[i][0], cod: x.cod }));

function caminhoDosFiltros(raiz: No, fs: Filtro[]): No[] {
  const c = [raiz];
  if (!segueCascata(fs)) return c;
  for (const f of fs) {
    const x = filhos(c[c.length - 1]).find((y) => y.cod === f.cod);
    if (!x) break;
    c.push(x);
  }
  return c;
}

export default function CascataVista(props: Props) {
  let host!: HTMLDivElement;
  let tela: Tela | null = null;
  let fonte: Fonte | null = null;
  /** O último caminho que a tela mandou (ou recebeu): evita ir e voltar entre a tela e o Explorer. */
  let enviado = "";
  const [cor, setCor] = createSignal<"tipo" | "tamanho">("tipo");
  const [pessoa, setPessoa] = createSignal(false);
  const [comTipo, setComTipo] = createSignal(true);

  // A árvore e a tela são refeitas quando muda o que os valores querem dizer (ano, métrica, refinanciamento, inflação).
  createEffect(on(() => [props.doc, props.metrica, props.semRefin, props.fator] as const, async ([doc, metrica, semRefin, fator]) => {
    const ano = props.ano;
    const populacao = await populacaoDoBrasil(ano);
    if (doc !== props.doc) return;   // chegou outro ano enquanto esperava
    const F = fonteDoDoc(doc, { ano, metrica, semRefin, fator, populacao });
    fonte = F;
    exibir.populacao = populacao;
    setComTipo(F.cats.length > 1);
    enviado = chave(props.filtros);
    host.innerHTML = "";
    tela = criarTela(host, F, {
      usaTipo: () => cor() === "tipo" && F.cats.length > 1,
      caminhoInicial: caminhoDosFiltros(F.raiz, props.filtros),
      semFio: true,
      cartao: (n) => htmlDetalhe(F, n),
      aoEscolher: (n) => {
        const fs = filtrosDe(n);
        enviado = chave(fs);
        props.onCaminho(fs);
      },
      verMapa: (n) => props.onVerMapa(filtrosDe(n)),
    });
  }));

  // Os degraus do Explorer mudaram o caminho: a tela vai até lá.
  createEffect(on(() => props.filtros, (fs) => {
    if (!tela || !fonte || chave(fs) === enviado) return;
    enviado = chave(fs);
    if (!segueCascata(fs)) return;
    const c = caminhoDosFiltros(fonte.raiz, fs);
    tela.selecionar(c[c.length - 1]);
  }, { defer: true }));

  createEffect(on([cor, pessoa], () => {
    exibir.porPessoa = pessoa();
    tela?.redesenhar();
  }, { defer: true }));
  onCleanup(() => { exibir.porPessoa = false; });

  const recorteDeFora = () => props.filtros.find((f, i) => f.dim !== NIVEIS[i]?.[0]);

  return (
    <div class="exp-cascata-vista">
      <div class="exp-cascata-barra">
        <Show when={comTipo() && cor() === "tipo" && !props.legendaAcima} fallback={<ul class="cc-legenda"><li><i class="cc-hachura" />os menores, juntos (“mais N”)</li></ul>}>
          <ul class="cc-legenda">
            <For each={TIPOS_DESPESA.filter((t) => t.cod !== "sem")}>{(t) => <li><i style={{ background: t.cor }} />{t.nome}</li>}</For>
            <li><i class="cc-hachura" />os menores, juntos (“mais N”)</li>
          </ul>
        </Show>
        <div class="exp-cascata-opcoes">
          <Show when={comTipo()}>
            <button type="button" class="pilula" aria-pressed={cor() === "tamanho"} onClick={() => setCor(cor() === "tipo" ? "tamanho" : "tipo")}
              title="Tira as cores de obrigatório ou não e deixa só o caminho em verde">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" /></svg>
              Só o caminho
            </button>
          </Show>
          <button type="button" class="pilula" aria-pressed={pessoa()} onClick={() => setPessoa(!pessoa())}
            title="Divide cada valor pela população do Brasil no ano (IBGE)">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" /></svg>
            Por pessoa
          </button>
        </div>
      </div>
      <Show when={recorteDeFora()}>
        {(f) => (
          <p class="exp-aviso" role="status">
            A cascata segue órgão › unidade › programa › ação › tipo de gasto. O recorte por {ABA[f().dim] ?? f().dim} não entra
            nela; por isso ela mostra o orçamento inteiro. Clicar numa caixa troca o caminho.
          </p>
        )}
      </Show>
      <div ref={host} class="exp-cascata-tela"><p class="cc-carregando">Carregando a cascata…</p></div>
    </div>
  );
}
