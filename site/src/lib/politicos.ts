/**
 * A página de cada político eleito (/politicos): os dados de pipeline/…/politicos.py, num arquivo só
 * (public/data/politicos/politicos.json). Por ora, deputados federais e senadores.
 */
import { docCidades, caminhoCidade, slug } from "./cidades";

export interface Cota {
  total: number;
  meses: number;
  porMes: number;
  /** [categoria, valor], do maior para o menor */
  categorias: [string, number][];
  /** valor de cada mês, de janeiro a dezembro */
  mes: number[];
  /** [nome, CNPJ, categoria principal, valor] das maiores empresas */
  fornecedores: [string, string, string, number][];
  /** [quantas, valor]: empresário individual e MEI, somados */
  pessoaEmpresa: [number, number];
  /** [quantas notas, valor]: pessoas físicas, somadas */
  pessoas: [number, number];
  semDocumento: number;
  /** Câmara: a soma do teto do estado nos meses com despesa */
  teto?: number;
  comparacao?: { mediana: number; n: number; colegas: number[] | null; pares?: [string, string, number][] };
}
export interface Emendas {
  total: number;
  lugares: number;
  pix: number;
  posicao: number;
  de: number;
  /** [município, UF, código IBGE, valor] */
  onde: [string, string, string | null, number][];
  area: [string, number][];
}
export interface Ano {
  cota?: Cota;
  salario?: number;
  gabinete?: { gasto: number; disponivel: number; meses: number };
  emendas?: Emendas;
}
export interface Tse {
  eleicao: number;
  cargo: string;
  uf: string;
  partido: string;
  genero: string;
  situacao: string;
  urna: string;
  votos: number | null;
  bens: { total: number; tipos: [string, number][] } | null;
  receitas: { total: number; origens: [string, number][]; partidos: [string, number][]; pf: [number, number] } | null;
}
export interface Politico {
  chave: string;
  casa: "camara" | "senado";
  id: string;
  nome: string;
  uf: string;
  partido: string | null;
  cargo: string;
  feminino: boolean;
  foto: string | null;
  /** o nome do autor nas emendas (/emendas/buscar?autor=) */
  autor: string | null;
  tse: Tse | null;
  assessores: number | null;
  anos: Record<string, Ano>;
  slug: string;
  /** false quando a mesma pessoa tem uma página de cargo mais recente (deputado até jan/2023 e senador depois) */
  atual: boolean;
  /** as páginas da mesma pessoa em outro cargo */
  outros: { chave: string; cargo: string; periodo: string | null; atual: boolean; slug: string }[];
  /** endereços que esta página já teve (redirecionam para o atual) */
  slugsAntigos: string[];
}
export interface DocPoliticos {
  gerado: string;
  anos: string[];
  subsidio: [string, number][];
  maxSecretarios: number;
  ufs: Record<string, string>;
  fontes: Record<string, string>;
  politicos: Politico[];
}

const arquivos = import.meta.glob<DocPoliticos>("../../public/data/politicos/politicos.json", { eager: true, import: "default" });
export const docPoliticos: DocPoliticos | null = Object.values(arquivos)[0] ?? null;

export const caminhoPolitico = (p: Pick<Politico, "uf" | "slug">) => `/politicos/${p.uf.toLowerCase()}/${p.slug}`;

/** O autor das emendas (como a CGU escreve, ou como o explorador escreve) → endereço da página do político. */
export function mapaAutores(): Record<string, string> {
  const m: Record<string, string> = {};
  // Quem passou pelas duas Casas tem o mesmo autor nas duas páginas: vale a do cargo atual.
  for (const p of docPoliticos?.politicos ?? []) if (p.autor && (p.atual !== false || !m[slug(p.autor)])) m[slug(p.autor)] = caminhoPolitico(p);
  return m;
}
const autores = mapaAutores();
export const politicoDoAutor = (autor: string): string | null => autores[slug(autor)] ?? null;

/** O ano que a página abre: o último fechado, se houver dado nele; senão o mais recente. */
export function anoPadrao(p: Politico): string {
  const anos = Object.keys(p.anos).sort();
  const fechado = String(new Date().getFullYear() - 1);
  return anos.includes(fechado) ? fechado : anos.at(-1)!;
}

/** O endereço da página de uma cidade pelo código IBGE (null se não houver a página). */
const porIbge = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c]));
export function caminhoIbge(ibge: string | null): string | null {
  if (!ibge) return null;
  if (ibge === "5300108") return "/cidades/df/brasilia";
  const c = porIbge.get(ibge);
  return c ? caminhoCidade(c) : null;
}

/** "o Senado", "a Câmara" */
export const casaNome = (p: Politico) => (p.casa === "camara" ? "Câmara" : "Senado");
