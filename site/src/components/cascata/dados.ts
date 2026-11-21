/**
 * A cascata do gasto (a vista "Cascata" do Explorer): a árvore do orçamento federal (órgão › unidade › programa › ação ›
 * tipo de gasto), montada do mesmo arquivo do ano que o Explorer carrega, com os filhos de cada nível calculados na
 * hora em que são abertos. Cada nó guarda a mistura por categoria (obrigatória, escolha do governo, emendas,
 * financeira), que serve de cor.
 *
 * A versão com uma cidade até o fornecedor (João Pessoa, empenhos do TCE-PB) ficou guardada em
 * pipeline/prototipo/cascata_joao_pessoa.py e pipeline/referencia/cascata-joao-pessoa-*.json.
 */
import { SUBFUNCOES_REFINANCIAMENTO, TIPOS_DESPESA, type Dim, type DocAno, type Metrica } from "../../lib/dados";
import { moedaCurta } from "../../lib/formato";

export interface Categoria { nome: string; cor: string; escuro?: boolean }

export interface No {
  cod: string;
  nome: string;
  /** O valor da métrica escolhida no Explorer (dotação, empenhado ou pago), já corrigido pela inflação se pedido. */
  valor: number;
  /** O tipo do nível: "Órgão", "Unidade"… */
  nivel: string;
  prof: number;
  pai: No | null;
  /** Valor por categoria (mesma ordem de Fonte.cats). */
  mix: number[];
  /** Dotação atualizada (o autorizado) e o pago, para os detalhes. */
  autorizado: number;
  pago: number;
  /** "mais N programas": junta os menores; `lista` traz quem são. */
  ehOutros?: boolean;
  lista?: No[];
  /** Um item que já junta vários (não acontece na União; fica para quando entrarem cidades). */
  info?: { resto?: number };
  _filhos?: No[];
  carregar?: () => No[];
}

export interface Fonte {
  ano: number;
  metrica: Metrica;
  /** "pagos", "autorizados"…: o que o valor é, nos detalhes. */
  rotuloValor: string;
  /** Para os valores por pessoa: a população do Brasil no ano. */
  populacao: number;
  raiz: No;
  cats: Categoria[];
  /** Uma frase por categoria, para quem não sabe o que é "obrigatória". */
  explicaCat: string[];
  plural: Record<string, string>;
  /** Uma linha que explica cada nível, para quem não conhece os nomes. */
  explica: Record<string, string>;
}

export function filhos(n: No): No[] {
  if (n._filhos === undefined) n._filhos = n.carregar ? n.carregar() : [];
  return n._filhos;
}

export const temFilhos = (n: No) => !n.ehOutros && filhos(n).length > 0;

export function caminhoAte(n: No): No[] {
  const c: No[] = [];
  for (let x: No | null = n; x; x = x.pai) c.unshift(x);
  return c;
}

/** Os níveis da cascata, na ordem; o caminho do Explorer só vira caminho aqui se seguir esta ordem. */
export const NIVEIS: [Dim, string][] = [
  ["orgao", "Órgão"], ["uo", "Unidade"], ["programa", "Programa"], ["acao", "Ação"], ["gnd", "Tipo de gasto"],
];

const ROTULO_VALOR: Record<Metrica, string> = {
  inicial: "previstos no orçamento (dotação inicial)",
  atualizado: "autorizados (dotação atualizada)",
  empenhado: "empenhados",
  realizado: "pagos",
};

export interface OpcoesFonte {
  ano: number;
  metrica: Metrica;
  semRefin: boolean;
  /** Fator do IPCA para reais do ano-base (1: valores nominais). */
  fator: number;
  populacao: number;
}

export function fonteDoDoc(doc: DocAno, op: OpcoesFonte): Fonte {
  const col = (c: string) => doc.colunas.indexOf(c);
  const iV = col(op.metrica), iA = col("atualizado"), iP = col("realizado"), iSub = col("subfuncao"), iTipo = col("tipo");
  const cats: Categoria[] = iTipo >= 0
    ? TIPOS_DESPESA.map((t) => ({ nome: t.nome, cor: t.cor, escuro: t.cod === "obr" }))
    : [{ nome: "Gasto", cor: "#1f7a47", escuro: true }];
  const catDe = new Map<string, number>(TIPOS_DESPESA.map((t, i) => [t.cod, i]));
  const f = op.fator;

  const linhas = doc.linhas.filter((l) => (l[iV] as number) && !(op.semRefin && SUBFUNCOES_REFINANCIAMENTO.has(l[iSub] as string)));

  const criar = (ls: (string | number)[][], cod: string, nome: string, prof: number, pai: No | null): No => {
    const mix = new Array(cats.length).fill(0);
    let valor = 0, autorizado = 0, pago = 0;
    for (const l of ls) {
      const v = (l[iV] as number) * f;
      valor += v;
      autorizado += (l[iA] as number) * f;
      pago += (l[iP] as number) * f;
      mix[iTipo >= 0 ? catDe.get(l[iTipo] as string) ?? 4 : 0] += v;
    }
    const n: No = { cod, nome, valor, autorizado, pago, nivel: prof === 0 ? "Orçamento" : NIVEIS[prof - 1][1], prof, pai, mix };
    if (prof < NIVEIS.length) {
      n.carregar = () => {
        const [dim] = NIVEIS[prof];
        const i = col(dim);
        const grupos = new Map<string, (string | number)[][]>();
        for (const l of ls) {
          const c = l[i] as string;
          let g = grupos.get(c);
          if (!g) grupos.set(c, (g = []));
          g.push(l);
        }
        return [...grupos]
          .map(([c, g]) => criar(g, c, (doc.dims as Record<string, Record<string, string>>)[dim]?.[c] ?? c, prof + 1, n))
          .filter((x) => x.valor > 0)
          .sort((a, b) => b.valor - a.valor);
      };
    }
    return n;
  };
  return {
    ano: op.ano, metrica: op.metrica, rotuloValor: ROTULO_VALOR[op.metrica], populacao: op.populacao,
    raiz: criar(linhas, "uniao", `Orçamento federal ${op.ano}`, 0, null), cats,
    explicaCat: [
      "o governo é obrigado por lei ou pela Constituição a pagar: aposentadorias, salários, repasses a estados e cidades",
      "o governo decide se gasta e quanto: obras, compras, programas",
      "deputados e senadores indicaram para onde vai",
      "juros e pagamento da dívida pública",
      "o orçamento não marca de que tipo é",
    ],
    plural: { Orçamento: "orçamento", Órgão: "órgãos", Unidade: "unidades", Programa: "programas", Ação: "ações", "Tipo de gasto": "tipos de gasto" },
    explica: {
      Órgão: "o ministério ou o poder (Câmara, tribunais…)",
      Unidade: "quem gasta dentro do órgão: fundo, secretaria, autarquia",
      Programa: "o objetivo do gasto",
      Ação: "o que é feito com o dinheiro",
      "Tipo de gasto": "salários, custeio, obras, juros…",
    },
  };
}

/** Categoria com mais dinheiro no nó. */
export function catPrincipal(n: No): number {
  let m = 0;
  n.mix.forEach((v, i) => { if (v > n.mix[m]) m = i; });
  return m;
}

// ——— valores por pessoa ———

export const exibir = { porPessoa: false, populacao: 1 };
const nfP0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nfP2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "R$ 93,3 bi" ou, por pessoa, "R$ 437/pessoa". */
export function dinheiro(v: number, longo = false): string {
  if (!exibir.porPessoa) return moedaCurta(v);
  const p = v / Math.max(1, exibir.populacao);
  const t = Math.abs(p) >= 100 ? `R$ ${nfP0.format(p)}` : Math.abs(p) >= 0.01 ? `R$ ${nfP2.format(p)}` : "menos de R$ 0,01";
  return `${t}${longo ? " por pessoa" : "/pessoa"}`;
}

/** População do Brasil (soma das UFs) no ano, pelo arquivo de população do site; sem o ano, o mais próximo. */
let populacaoPromessa: Promise<Record<string, Record<string, number>>> | null = null;
export async function populacaoDoBrasil(ano: number): Promise<number> {
  populacaoPromessa ??= fetch("/data/indicadores/populacao.json").then((r) => (r.ok ? r.json() : { anos: {} })).then((d) => d.anos ?? {});
  const anos = await populacaoPromessa;
  const lista = Object.keys(anos).map(Number).sort((a, b) => a - b);
  if (!lista.length) return 1;
  const a = lista.includes(ano) ? ano : lista.reduce((m, x) => (Math.abs(x - ano) < Math.abs(m - ano) ? x : m), lista[0]);
  return Object.entries(anos[String(a)]).filter(([k]) => k.length === 2).reduce((s, [, v]) => s + v, 0);
}
