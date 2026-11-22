/**
 * Dívida ativa da União: o que empresas e pessoas devem ao governo federal e não pagaram, inscrito pela
 * Procuradoria-Geral da Fazenda Nacional (PGFN). Gerado por pipeline/…/divida_ativa.py; lido no build.
 * Sem o arquivo, tudo vem null.
 *
 * Privacidade: o arquivo não tem CPF nem nome de pessoa. As pessoas físicas só aparecem somadas, por
 * estado (a lista da PGFN não diz a cidade delas). Empresário individual e MEI também não têm nome.
 */
import type { Cidade } from "./cidades";

type Tipos = [number, number, number];
type Situacoes = [number, number, number, number, number];
/** [nome, CNPJ, valor, índice da situação que tem a maior parte da dívida, (só no Brasil) ibge da cidade] */
type Maior = [string, string, number, number, (string | null)?];

interface DocDividaAtiva {
  trimestre: string;
  /** "09/2026": o mês da posição dos dados */
  posicao: string;
  receita: string;
  fonte: string;
  tipos: string[];
  situacoes: string[];
  brasil: {
    total: number;
    empresas_valor: number;
    tipos: Tipos;
    situacoes: Situacoes;
    empresas: number;
    publico: number;
    fechadas: number;
    individuais: number;
    pessoas: [number, number];
    sem_cidade: [number, number];
    cidades: number;
    maiores: Maior[];
  };
  /** UF → [dívida das empresas, dívida das pessoas, nº de pessoas, empresas sem cidade: valor, nº] */
  uf: Record<string, [number, number, number, number, number]>;
  /** ibge → [total, tipos, situações, nº de empresas, órgãos públicos, empresas fechadas, maiores] */
  mun: Record<string, [number, Tipos, Situacoes, number, number, number, Maior[]]>;
}

const arquivos = import.meta.glob<DocDividaAtiva>("../../public/data/divida-ativa/divida-ativa.json", { import: "default" });
let doc: Promise<DocDividaAtiva | null> | null = null;
export const docDividaAtiva = () => (doc ??= Object.values(arquivos)[0]?.() ?? Promise.resolve(null));

export const NOMES_TIPO = ["Impostos e multas", "Contribuições ao INSS", "FGTS"];
/** Como cada situação aparece ao lado de uma empresa e nas barras. */
export const NOMES_SITUACAO = [
  "em cobrança na Justiça",
  "em cobrança, fora da Justiça",
  "parcelada ou negociada",
  "garantida (penhora ou depósito)",
  "suspensa por decisão judicial",
];

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
/** "09/2026" → "setembro de 2026" */
export const mesPorExtenso = (p: string) => `${MESES[Number(p.slice(0, 2)) - 1]} de ${p.slice(3)}`;

export interface Devedora {
  nome: string;
  cnpj: string;
  valor: number;
  situacao: string;
}

export interface DividaAtivaCidade {
  posicao: string;
  fonte: string;
  total: number;
  tipos: { nome: string; valor: number }[];
  situacoes: { nome: string; valor: number }[];
  empresas: number;
  /** Prefeitura, câmara, autarquias e outros órgãos públicos com endereço na cidade. */
  publico: number;
  /** Empresas baixadas, inaptas ou suspensas no cadastro da Receita. */
  fechadas: number;
  maiores: Devedora[];
  /** As pessoas do estado inteiro: a lista não diz a cidade delas. */
  pessoasUf: { valor: number; n: number };
  brasil: DocDividaAtiva["brasil"];
}

const devedora = ([nome, cnpj, valor, s]: Maior): Devedora => ({ nome, cnpj, valor, situacao: NOMES_SITUACAO[s] });

export async function dividaAtivaEm(c: Cidade): Promise<DividaAtivaCidade | null> {
  const d = await docDividaAtiva();
  if (!d) return null;
  const m = d.mun[String(c.ibge)];
  const [total, tipos, sit, empresas, publico, fechadas, maiores] = m ?? [0, [0, 0, 0], [0, 0, 0, 0, 0], 0, 0, 0, []];
  const uf = d.uf[c.uf];
  return {
    posicao: d.posicao, fonte: d.fonte, total, empresas, publico, fechadas, brasil: d.brasil,
    tipos: tipos.map((valor, i) => ({ nome: NOMES_TIPO[i], valor })),
    situacoes: sit.map((valor, i) => ({ nome: NOMES_SITUACAO[i], valor })),
    maiores: maiores.map(devedora),
    pessoasUf: { valor: uf?.[1] ?? 0, n: uf?.[2] ?? 0 },
  };
}

const SIGLAS = new Set(["me", "epp", "eireli", "s/a", "s.a.", "sa", "cnpj", "sus", "ltda", "brb", "cagepa", "see"]);
const PEQUENAS = new Set(["de", "da", "do", "das", "dos", "e", "em", "para", "a", "o", "as", "os", "com", "no", "na", "nos", "nas"]);
/** "CONSTRUTORA BOA OBRA LTDA" → "Construtora Boa Obra Ltda" */
export function nomeDeEmpresa(nome: string): string {
  const s = nome.replace(/\s+/g, " ").trim().replace(/(?<![A-Z])S\.? ?A\.?(?= |$)/g, "S.A.");
  if (s !== s.toUpperCase() || !/[A-ZÀ-Ú]{4}/.test(s)) return s;
  return s.toLowerCase().split(" ").map((x, i) =>
    x === "ltda" || x === "ltda." ? "Ltda" : SIGLAS.has(x) ? x.toUpperCase() : i > 0 && PEQUENAS.has(x) ? x : x.charAt(0).toUpperCase() + x.slice(1),
  ).join(" ");
}
