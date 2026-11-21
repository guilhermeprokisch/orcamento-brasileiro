/**
 * A cascata do gasto: a árvore do orçamento federal (órgão › unidade › programa › ação › tipo de gasto), com os filhos
 * de cada nível calculados na hora em que são abertos. Cada nó guarda a mistura por categoria (obrigatória, escolha do
 * governo, emendas, financeira), que serve de cor. A versão com uma cidade até o fornecedor (João Pessoa, empenhos do
 * TCE-PB) ficou guardada em pipeline/prototipo/cascata_joao_pessoa.py e pipeline/referencia/cascata-joao-pessoa-*.json.
 */
import { SUBFUNCOES_REFINANCIAMENTO, TIPOS_DESPESA, type DocAno } from "../../lib/dados";
import { moedaCurta, moedaExtenso } from "../../lib/formato";

export interface Categoria { nome: string; cor: string; escuro?: boolean }

export interface Info {
  cnpj?: string;
  licitacao?: string;
  empenhos?: number;
  pessoas?: number;
  resto?: number;
  via?: string;
  tipoCredor?: number;
}

export interface No {
  cod: string;
  nome: string;
  valor: number;
  /** O tipo do nível: "Órgão", "Área", "Credor"… */
  nivel: string;
  prof: number;
  pai: No | null;
  /** Valor por categoria (mesma ordem de Fonte.cats). */
  mix: number[];
  /** Dotação atualizada (o autorizado), só na União. */
  autorizado?: number;
  /** "outros N programas": junta os menores; `lista` traz quem são. */
  ehOutros?: boolean;
  lista?: No[];
  info?: Info;
  _filhos?: No[];
  carregar?: () => No[];
}

export interface Fonte {
  chave: "uniao";
  ano: number;
  /** Para os valores por pessoa: população do Brasil (União) ou da cidade, no ano. */
  populacao: number;
  raiz: No;
  cats: Categoria[];
  /** Nome da cor por categoria: "Obrigatório ou não", "Quem recebe". */
  rotuloCor: string;
  /** Uma frase por categoria, para quem não sabe o que é "obrigatória" ou "previdência". */
  explicaCat: string[];
  /** Endereço deste nó no Explorer (União). */
  linkExplorer?: (n: No) => string;
  plural: Record<string, string>;
  /** Uma linha que explica cada nível, para quem não conhece os nomes. */
  explica: Record<string, string>;
  frase: string;
  fonte: string;
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

// ——— União: o arquivo do Explorer (site/public/data/explorer/2025.json), sem o refinanciamento da dívida ———

const NIVEIS_UNIAO: [string, string][] = [
  ["orgao", "Órgão"], ["uo", "Unidade"], ["programa", "Programa"], ["acao", "Ação"], ["gnd", "Tipo de gasto"],
];

export async function fonteUniao(ano = 2025, populacao = 1): Promise<Fonte> {
  const r = await fetch(`/data/explorer/${ano}.json`);
  if (!r.ok) throw new Error(`Não consegui carregar ${ano} (HTTP ${r.status})`);
  const doc: DocAno = await r.json();
  const col = (c: string) => doc.colunas.indexOf(c);
  const iV = col("realizado"), iA = col("atualizado"), iSub = col("subfuncao"), iTipo = col("tipo");
  const cats: Categoria[] = iTipo >= 0
    ? TIPOS_DESPESA.map((t) => ({ nome: t.nome, cor: t.cor, escuro: t.cod === "obr" }))
    : [{ nome: "Gasto", cor: "#1f7a47", escuro: true }];
  const catDe = new Map<string, number>(TIPOS_DESPESA.map((t, i) => [t.cod, i]));

  let refin = 0;
  const linhas: (string | number)[][] = [];
  for (const l of doc.linhas) {
    const v = l[iV] as number;
    if (SUBFUNCOES_REFINANCIAMENTO.has(l[iSub] as string)) { refin += v; continue; }
    if (v) linhas.push(l);
  }

  const criar = (ls: (string | number)[][], cod: string, nome: string, prof: number, pai: No | null): No => {
    const mix = new Array(cats.length).fill(0);
    let valor = 0, autorizado = 0;
    for (const l of ls) {
      const v = l[iV] as number;
      valor += v;
      autorizado += l[iA] as number;
      mix[iTipo >= 0 ? catDe.get(l[iTipo] as string) ?? 4 : 0] += v;
    }
    const n: No = { cod, nome, valor, autorizado, nivel: prof === 0 ? "Orçamento" : NIVEIS_UNIAO[prof - 1][1], prof, pai, mix };
    if (prof < NIVEIS_UNIAO.length) {
      n.carregar = () => {
        const [dim] = NIVEIS_UNIAO[prof];
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
          .filter((f) => f.valor > 0)
          .sort((a, b) => b.valor - a.valor);
      };
    }
    return n;
  };
  const raiz = criar(linhas, "uniao", `Orçamento federal ${ano}`, 0, null);
  return {
    chave: "uniao", ano, populacao, raiz, cats, rotuloCor: "Obrigatório ou não",
    explicaCat: [
      "o governo é obrigado por lei ou pela Constituição a pagar: aposentadorias, salários, repasses a estados e cidades",
      "o governo decide se gasta e quanto: obras, compras, programas",
      "deputados e senadores indicaram para onde vai",
      "juros e pagamento da dívida pública",
      "o orçamento não marca de que tipo é",
    ],
    linkExplorer: (n) => {
      const f = caminhoAte(n).slice(1).map((x, i) => `${NIVEIS_UNIAO[i][0]}:${x.cod}`).join(",");
      return `/explorer?ano=${ano}&metrica=realizado&refin=0${f ? `&f=${f}` : ""}`;
    },
    plural: { Orçamento: "orçamento", Órgão: "órgãos", Unidade: "unidades", Programa: "programas", Ação: "ações", "Tipo de gasto": "tipos de gasto" },
    explica: {
      Órgão: "o ministério ou o poder (Câmara, tribunais…)",
      Unidade: "quem gasta dentro do órgão: fundo, secretaria, autarquia",
      Programa: "o objetivo do gasto",
      Ação: "o que é feito com o dinheiro",
      "Tipo de gasto": "salários, custeio, obras, juros…",
    },
    frase: `Em ${ano}, o governo federal pagou ${moedaExtenso(raiz.valor)}, sem contar ${moedaExtenso(refin)} de rolagem da dívida (troca de dívida velha por nova, que fica de fora).`,
    fonte: "Orçamento federal (Tesouro e SIOP), valores pagos.",
  };
}

// ——— "Não mostrar tudo": os maiores de cada nível e o resto junto ———

export interface Visiveis { itens: No[]; outros: No | null }

export function visiveis(n: No, k: number, plural: Record<string, string>, escolhido?: No | null): Visiveis {
  const fs = filhos(n);
  if (fs.length <= k + 1 && !fs.some((f) => f.info?.resto)) return { itens: fs.slice(), outros: null };
  // "N credores menores" (o resto que o arquivo do protótipo já juntou) vai sempre para "outros".
  let top = fs.filter((f) => !f.info?.resto).slice(0, k);
  // Os pedacinhos (menos de 0,6% do nível) também vão para "outros", mas ficam pelo menos três.
  while (top.length > 3 && top[top.length - 1].valor < n.valor * 0.006) top.pop();
  if (escolhido && !top.includes(escolhido)) {
    top = top.slice(0, Math.max(1, top.length - 1));
    top.push(escolhido);
    top.sort((a, b) => b.valor - a.valor);
  }
  const resto = fs.filter((f) => !top.includes(f));
  if (resto.length <= 1) return { itens: fs.filter((f) => top.includes(f) || resto.includes(f)), outros: null };
  const mix = new Array(n.mix.length).fill(0);
  for (const f of resto) f.mix.forEach((v, i) => (mix[i] += v));
  const nivel = resto[0].nivel;
  const outros: No = {
    cod: "#outros", nome: `outros ${resto.reduce((s, f) => s + (f.info?.resto ?? 1), 0)} ${plural[nivel] ?? "itens"}`, valor: resto.reduce((s, f) => s + f.valor, 0),
    nivel, prof: n.prof + 1, pai: n, mix, ehOutros: true, lista: resto,
  };
  return { itens: top, outros };
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

