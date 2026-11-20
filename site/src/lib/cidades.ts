/**
 * Gasto dos municípios e dos estados (SICONFI/DCA), lido no build a partir dos
 * JSONs gerados por pipeline/…/cidades.py. Se o pipeline não rodou, tudo vem vazio.
 * Os dois arquivos têm o mesmo formato; nos estados há uma faixa só ("estados").
 */

export interface Cidade {
  ibge: number;
  nome: string;
  uf: string;
  capital: boolean;
  pop: number;
  /** Ano da DCA usada (o mais recente entregue); null se não entregou nenhum. */
  ano: number | null;
  faixa?: number;
  /** [empenhado, pago] */
  total?: [number, number];
  /** função → [empenhado, pago] */
  f?: Record<string, [number, number]>;
  /** subfunção ("10.301", "10.FU") → empenhado */
  s?: Record<string, number>;
  /** ano → total empenhado */
  hist?: Record<string, number>;
}

export interface DocCidades {
  gerado: string;
  fonte: string;
  anos: number[];
  funcoes: Record<string, string>;
  subfuncoes: Record<string, string>;
  faixas: string[];
  /** ano → faixa → (função | "total" → mediana per capita do empenhado) e "n" */
  medianas: Record<string, Record<string, number>[]>;
  cidades: Cidade[];
}

const arquivos = import.meta.glob<DocCidades>("../../public/data/cidades/{municipios,estados}.json", { eager: true, import: "default" });
const arquivo = (nome: string) => Object.entries(arquivos).find(([k]) => k.endsWith(`/${nome}.json`))?.[1] ?? null;
export const docCidades: DocCidades | null = arquivo("municipios");
export const docEstados: DocCidades | null = arquivo("estados");

export const NOMES_UF: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul",
  MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul",
  SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins",
};

const PREPOSICAO_UF: Record<string, "do" | "da" | "de"> = {
  AC: "do", AL: "de", AM: "do", AP: "do", BA: "da", CE: "do", DF: "do", ES: "do", GO: "de", MA: "do",
  MG: "de", MS: "de", MT: "de", PA: "do", PB: "da", PE: "de", PI: "do", PR: "do", RJ: "do", RN: "do",
  RO: "de", RR: "de", RS: "do", SC: "de", SE: "de", SP: "de", TO: "do",
};
/** "do Acre", "da Bahia", "de Goiás". */
export const deUf = (uf: string) => `${PREPOSICAO_UF[uf] ?? "de"} ${NOMES_UF[uf] ?? uf}`;

export const slug = (s: string) =>
  s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export const caminhoCidade = (c: Pick<Cidade, "uf" | "nome" | "ibge">) =>
  c.ibge === 53 ? "/cidades/df/brasilia" : `/cidades/${c.uf.toLowerCase()}/${slug(c.nome)}`;

export const caminhoEstado = (uf: string) => `/estados/${uf.toLowerCase()}`;

/** Mediana per capita do grupo de comparação (faixa de população ou estados), no ano da DCA do ente. */
export function medianaDa(c: Cidade, chave: string, doc: DocCidades | null = docCidades): number | null {
  if (!doc || c.ano === null || c.faixa === undefined || c.ibge === 53) return null;
  const m = doc.medianas[String(c.ano)]?.[c.faixa];
  return m && m.n >= 10 ? m[chave] ?? 0 : null;
}

export interface LinhaFuncao {
  cod: string;
  nome: string;
  emp: number;
  pago: number;
  perCapita: number;
  mediana: number | null;
}

export function funcoesDa(c: Cidade, doc: DocCidades | null = docCidades): LinhaFuncao[] {
  if (!doc || !c.f) return [];
  return Object.entries(c.f)
    .map(([cod, [emp, pago]]) => ({
      cod, nome: doc.funcoes[cod] ?? cod, emp, pago,
      perCapita: emp / c.pop, mediana: medianaDa(c, cod, doc),
    }))
    .filter((l) => l.emp > 0)
    .sort((a, b) => b.emp - a.emp);
}

export interface LinhaSub {
  cod: string;
  nome: string;
  emp: number;
}

export function subfuncoesDa(c: Cidade, funcao: string, doc: DocCidades | null = docCidades): LinhaSub[] {
  if (!doc || !c.s) return [];
  return Object.entries(c.s)
    .filter(([cod, v]) => cod.startsWith(`${funcao}.`) && v > 0)
    .map(([cod, emp]) => ({ cod, nome: doc.subfuncoes[cod] ?? cod, emp }))
    .sort((a, b) => b.emp - a.emp);
}

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
export const habitantes = (n: number) => `${nf0.format(n)} moradores`;
/** "R$ 1.234" por pessoa (sem centavos). */
export const porPessoa = (v: number) => `R$ ${nf0.format(Math.round(v))}`;
