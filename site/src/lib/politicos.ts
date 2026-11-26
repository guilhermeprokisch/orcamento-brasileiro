/**
 * A página de cada político eleito (/politicos): os dados de pipeline/…/politicos.py, num arquivo só
 * (public/data/politicos/politicos.json). Deputados federais e senadores; governadores, deputados estaduais e
 * distritais eleitos em 2022 (politicos_estaduais.py).
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
  /** a verba do deputado estadual, no mesmo formato da cota (só nas Assembleias que publicam nota a nota) */
  verba?: Cota;
  salario?: number;
  /** o salário mensal pela lei (estaduais e governadores) */
  salarioMensal?: number;
  /** governador: os meses no cargo no ano (fração no mês em que saiu) */
  meses?: number;
  /** estadual sem verba aberta: o salário conta o ano inteiro desde a posse */
  mesesEstimados?: boolean;
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
  /** governador: os votos do segundo turno */
  votos2?: number;
  /** cargos estaduais: [cidade, UF, código do TSE, votos, parte dos votos] das cidades com mais votos */
  cidades?: [string, string, string, number, number][];
  nCidades?: number;
  /** [posição, de quantos] entre os eleitos do mesmo cargo e estado */
  posicao?: [number, number];
}
export interface Politico {
  chave: string;
  casa: "camara" | "senado" | "assembleia" | "governo";
  id: string;
  nome: string;
  uf: string;
  partido: string | null;
  /** estaduais: o partido pelo qual se elegeu em 2022 (o de hoje, em partido, só onde a Assembleia publica) */
  partidoEleicao?: string | null;
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
  /** governador que deixou o cargo em 2026 */
  saida?: { data: string | null; frase: string };
  nota?: string;
  /** o deputado na Assembleia (quando a Casa publica a verba) */
  assembleia?: { id: string; nome: string | null };
}
export interface Assembleia {
  nome: string;
  /** nota: nota a nota (lida); naoLida: publica nota a nota, mas ainda não lemos; total, fixo, nada, travado */
  tipo: "nota" | "naoLida" | "total" | "fixo" | "nada" | "travado";
  frase: string | null;
  verba: string;
  salarioAConferir: string | null;
}
export interface Governadores {
  subsidio: [string, number][];
  lei: string | null;
  semLei: string | null;
  aConferir: string | null;
}
export interface DocPoliticos {
  gerado: string;
  anos: string[];
  subsidio: [string, number][];
  maxSecretarios: number;
  ufs: Record<string, string>;
  fontes: Record<string, string>;
  assembleias?: Record<string, Assembleia>;
  governadores?: Record<string, Governadores>;
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

/** A página de uma cidade pelo nome e o estado (os votos do TSE não trazem o código do IBGE). */
const semAcento = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const porNome = new Map((docCidades?.cidades ?? []).map((c) => [`${semAcento(c.nome)}|${c.uf}`, c]));
export function caminhoCidadeNome(nome: string, uf: string): string | null {
  if (uf === "DF") return "/cidades/df/brasilia";
  const c = porNome.get(`${semAcento(nome)}|${uf}`);
  return c ? caminhoCidade(c) : null;
}

export const ehEstadual = (p: Pick<Politico, "casa">) => p.casa === "assembleia" || p.casa === "governo";

/** Os partidos que as fontes escrevem por extenso em maiúsculas, como aparecem na página. */
const NOME_PARTIDO: Record<string, string> = { REPUBLICANOS: "Republicanos", SOLIDARIEDADE: "Solidariedade", "UNIÃO": "União", CIDADANIA: "Cidadania",
  AVANTE: "Avante", NOVO: "Novo", PATRIOTA: "Patriota", PODE: "Podemos", PODEMOS: "Podemos", REDE: "Rede", AGIR: "Agir", MOBILIZA: "Mobiliza" };
export const nomePartido = (s: string) => NOME_PARTIDO[s.trim()] ?? s;

/** O partido para mostrar: o de hoje, se a Assembleia publica; senão "eleito pelo X" (o da eleição). */
export function partidoDe(p: Politico): string | null {
  if (p.partido) return /^s\/ ?partido$/i.test(p.partido) ? "sem partido" : nomePartido(p.partido);
  if (!p.partidoEleicao) return null;
  // O governador: o partido da eleição, sem repetir "eleito" (o cargo já diz "eleito em 2022" para quem saiu).
  return p.casa === "governo" ? p.partidoEleicao : `eleit${p.feminino ? "a" : "o"} pelo ${p.partidoEleicao}`;
}

/** "Governador eleito em 2022" para quem deixou o cargo; senão o cargo. */
export const cargoTopo = (p: Politico) => (p.casa === "governo" && p.saida ? `${p.cargo} eleit${p.feminino ? "a" : "o"} em 2022` : p.cargo);

/** "o Senado", "a Câmara" */
export const casaNome = (p: Politico) => (p.casa === "camara" ? "Câmara" : "Senado");
