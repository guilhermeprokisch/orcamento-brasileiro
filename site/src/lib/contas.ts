/**
 * Receita, saldo, tipo de gasto, balanço e benefícios do INSS de cada município e estado,
 * mais o ano em andamento, lidos no build dos arquivos da página /mapa (pipeline/…/mapa.py,
 * contas.py, inss.py e rreo.py). Cada ano só é carregado se alguma página precisar dele;
 * sem os arquivos, tudo vem null.
 */
import type { Cidade } from "./cidades";

/** Posições do registro de cada ente em mapa/anos/{ano}.json (mapa.py + receitas.CAMPOS). */
const R = {
  desp: 1, receita: 6, propria: 7, uniao: 8, estado: 9, fundeb: 10, credito: 11,
  iptu: 12, iss: 13, itbi: 14, taxas: 16, cosip: 17,
} as const;

interface DocAno {
  mun: Record<string, number[]>;
  uf: Record<string, number[]>;
}
type DocInss = Record<string, [number, number, number]>;
/** n e b na ordem de contas.NATUREZA e contas.BALANCO (pipeline). */
type DocContas = Record<string, { n?: number[]; b?: number[] }>;

const arquivosAno = import.meta.glob<DocAno>("../../public/data/mapa/anos/*.json", { import: "default" });
const arquivosInss = import.meta.glob<DocInss>("../../public/data/mapa/inss/*.json", { import: "default" });
const arquivosContas = import.meta.glob<DocContas>("../../public/data/mapa/contas/*.json", { import: "default" });

function leitor<T>(arquivos: Record<string, () => Promise<T>>) {
  const cache = new Map<number, Promise<T | null>>();
  return (ano: number) => {
    if (!cache.has(ano)) {
      const carregar = Object.entries(arquivos).find(([k]) => k.endsWith(`/${ano}.json`))?.[1];
      cache.set(ano, carregar ? carregar() : Promise.resolve(null));
    }
    return cache.get(ano)!;
  };
}
const docAno = leitor(arquivosAno);
const docInss = leitor(arquivosInss);
const docContas = leitor(arquivosContas);

export type Esfera = "mun" | "uf";

export interface Contas {
  ano: number;
  receita: number;
  despesa: number;
  /** receita − despesa empenhada */
  saldo: number;
  /** De onde veio a receita; a soma é a receita. */
  propria: number;
  uniao: number;
  estado: number;
  fundeb: number;
  credito: number;
  /** Tributos pagos direto à prefeitura (zerados nos estados). */
  iptu: number;
  iss: number;
  itbi: number;
  taxas: number;
  cosip: number;
}

/** O DF aparece em /cidades como Brasília, mas presta contas como estado. */
const chave = (e: Cidade, esfera: Esfera): [Esfera, string] => (e.ibge === 53 ? ["uf", "53"] : [esfera, String(e.ibge)]);

/** Receita e saldo no ano da DCA do ente; null se não há receita declarada nesse ano. */
export async function contasDe(e: Cidade, esfera: Esfera): Promise<Contas | null> {
  if (e.ano === null) return null;
  const [onde, id] = chave(e, esfera);
  const r = (await docAno(e.ano))?.[onde]?.[id];
  if (!r || r.length <= R.receita || !(r[R.receita] > 0)) return null;
  const v = (k: keyof typeof R) => r[R[k]] ?? 0;
  return {
    ano: e.ano, receita: v("receita"), despesa: v("desp"), saldo: v("receita") - v("desp"),
    propria: v("propria"), uniao: v("uniao"), estado: v("estado"), fundeb: v("fundeb"), credito: v("credito"),
    iptu: v("iptu"), iss: v("iss"), itbi: v("itbi"), taxas: v("taxas"), cosip: v("cosip"),
  };
}

export interface Natureza {
  ano: number;
  /** Soma dos seis grupos. Inclui pagamentos entre órgãos do próprio ente, então passa do total por área. */
  total: number;
  pessoal: number;
  juros: number;
  custeio: number;
  investimentos: number;
  inversoes: number;
  amortizacao: number;
  /** Restos a pagar inscritos no ano (gasto comprometido e não pago). */
  restos: number;
}

/** Despesa por natureza (com o quê gasta) no ano da DCA do ente. */
export async function naturezaDe(e: Cidade, esfera: Esfera): Promise<Natureza | null> {
  if (e.ano === null) return null;
  const n = (await docContas(e.ano))?.[chave(e, esfera)[1]]?.n;
  if (!n) return null;
  const [pessoal, juros, custeio, investimentos, inversoes, amortizacao, rpProcessados = 0, rpNaoProcessados = 0] = n;
  const total = pessoal + juros + custeio + investimentos + inversoes + amortizacao;
  return total > 0
    ? { ano: e.ano, total, pessoal, juros, custeio, investimentos, inversoes, amortizacao, restos: rpProcessados + rpNaoProcessados }
    : null;
}

export interface Balanco {
  ano: number;
  caixa: number;
  /** Ativo financeiro menos passivo financeiro; null se o ente não declarou o ativo financeiro. */
  sobra: number | null;
  /** A mesma conta no balanço do ano anterior (valores da época). */
  sobraAntes: number | null;
  emprestimos: number;
  /** Provisões de longo prazo (em geral, aposentadorias futuras dos servidores). */
  provisoes: number;
}

/** Balanço patrimonial em 31/12 do ano da DCA do ente. */
export async function balancoDe(e: Cidade, esfera: Esfera): Promise<Balanco | null> {
  if (e.ano === null) return null;
  const id = chave(e, esfera)[1];
  const b = (await docContas(e.ano))?.[id]?.b;
  if (!b) return null;
  const sobraDe = (x?: number[]) => (x && x[1] > 0 ? x[1] - x[2] : null);
  const sobra = sobraDe(b);
  return {
    ano: e.ano, caixa: b[0], sobra,
    sobraAntes: sobra === null ? null : sobraDe((await docContas(e.ano - 1))?.[id]?.b),
    emprestimos: b[3] + b[4], provisoes: b[5],
  };
}

export interface Parcial {
  /** Ano em andamento e até que mês vão os números ("agosto"). */
  ano: number;
  ate: string;
  meses: number;
  receitaPrevista: number;
  receita: number;
  dotacao: number;
  empenhado: number;
  pago: number;
  /** Mesmo período do ano anterior, em valores da época; 0 se não há. */
  receitaAntes: number;
  empenhadoAntes: number;
}

interface DocParcial {
  ano: number;
  ate: string;
  meses: number;
  campos: string[];
  uf: Record<string, number[]>;
  mun: Record<string, number[]>;
}
const arquivosParcial = import.meta.glob<DocParcial>("../../public/data/mapa/parcial.json", { import: "default" });
let docParcial: Promise<DocParcial | null> | undefined;

/** Receita e despesa acumuladas no ano em andamento (RREO), se o ente entregou o último bimestre. */
export async function parcialDe(e: Cidade, esfera: Esfera): Promise<Parcial | null> {
  docParcial ??= Object.values(arquivosParcial)[0]?.() ?? Promise.resolve(null);
  const doc = await docParcial;
  const [onde, id] = chave(e, esfera);
  const r = doc?.[onde]?.[id];
  if (!doc || !r) return null;
  const v = (campo: string) => r[doc.campos.indexOf(campo)] ?? 0;
  if (!(v("receita") > 0 && v("receita_prevista") > 0 && v("dotacao") > 0)) return null;
  return {
    ano: doc.ano, ate: doc.ate, meses: doc.meses,
    receitaPrevista: v("receita_prevista"), receita: v("receita"), dotacao: v("dotacao"),
    empenhado: v("empenhado"), pago: v("pago"),
    receitaAntes: v("receita_ano_anterior"), empenhadoAntes: v("empenhado_ano_anterior"),
  };
}

export interface Inss {
  ano: number;
  total: number;
  aposentadorias: number;
  pensoes: number;
}

const somasPorUf = new Map<number, Promise<Record<string, [number, number, number]>>>();
function inssPorUf(ano: number) {
  if (!somasPorUf.has(ano)) {
    somasPorUf.set(ano, docInss(ano).then((doc) => {
      const soma: Record<string, [number, number, number]> = {};
      for (const [ibge, v] of Object.entries(doc ?? {})) {
        const s = (soma[ibge.slice(0, 2)] ??= [0, 0, 0]);
        v.forEach((x, i) => (s[i] += x));
      }
      return soma;
    }));
  }
  return somasPorUf.get(ano)!;
}

/** Benefícios do INSS pagos no município (ou somados no estado) no ano da DCA do ente. */
export async function inssDe(e: Cidade, esfera: Esfera): Promise<Inss | null> {
  if (e.ano === null) return null;
  const v = esfera === "uf" || e.ibge === 53
    ? (await inssPorUf(e.ano))[String(e.ibge).slice(0, 2)]
    : (await docInss(e.ano))?.[String(e.ibge)];
  return v && v[0] > 0 ? { ano: e.ano, total: v[0], aposentadorias: v[1], pensoes: v[2] } : null;
}
