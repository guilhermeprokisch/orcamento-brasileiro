/**
 * BNDES e estatais: os empréstimos do BNDES (por ano, juro, setor, cliente e cidade), o custo dos subsídios de crédito e
 * o que entra e sai das estatais federais. Gerado por pipeline/…/bndes.py; lido no build. Sem os arquivos, tudo vem null.
 *
 * Privacidade: só aparece pelo nome quem é empresa ou órgão público no cadastro de CNPJ (nunca pessoa, empresário
 * individual ou MEI). O resto entra somado.
 */
import type { Cidade } from "./cidades";

/** As quatro faixas de juro, na ordem dos arquivos. */
export const FAIXAS = ["abaixo", "tlp", "mercado", "doacao"] as const;
export type Faixa = (typeof FAIXAS)[number];
export const NOME_FAIXA: Record<Faixa | "misto", string> = {
  abaixo: "Abaixo do de mercado",
  tlp: "TLP",
  mercado: "De mercado",
  doacao: "Doação",
  misto: "Misto",
};
export const COR_FAIXA: Record<Faixa | "misto", string> = {
  abaixo: "#0e6b3b",
  tlp: "#6f9c7f",
  mercado: "#c3bba7",
  doacao: "#ffe14d",
  misto: "#3d3a33",
};

/** [ano, direta, indireta, abaixo, tlp, mercado, doação] */
export type LinhaSerie = [number, number, number, number, number, number, number];
/** [nome, raiz, UF, para quê, faixa principal ou "misto", valor, valor abaixo do mercado, benefício fiscal do ano] */
export type Maior = [string, string, string, string, Faixa | "misto", number, number, number | null];

export interface DocResumo {
  gerado: string;
  fonte: string;
  /** a data do contrato mais recente nos arquivos */
  ultima: string;
  /** o último ano fechado */
  ano: number;
  serie: LinhaSerie[];
  /** [ano, desembolso total, desembolso para pessoas físicas] */
  desembolso: [number, number, number][];
  setores: [string, string, number][];
  programas_abaixo: [string, number][];
  maiores: Maior[];
  /** clientes que não aparecem pelo nome no ano: [quantos, valor] */
  sem_nome: [number, number];
  diretas: number;
  sem_cidade: number;
  cidades: { n: number; mediana: number };
  cruzamento: { anos: [number, number]; empresas: number; com_beneficio: number; valor: number; valor_com_beneficio: number } | null;
  osu: {
    edicao: number;
    anos: number[];
    tipos: { financeiros: number[]; crediticios: number[]; tributarios: number[]; total: number[] };
    financeiros: (string | number)[][];
    crediticios: (string | number)[][];
  } | null;
  rtn: { anos: number[]; dividendos: Record<string, number[]>; safra: Record<string, number[]> } | null;
  /** empresas: [sigla, nome, dependente, valores por ano…] */
  sest: { anos: number[]; periodo: Record<string, string>; empresas: (string | boolean | number)[][]; dependentes: number } | null;
}

/** ibge → [contratos, total, [abaixo, tlp, mercado, doação], clientes, por um banco, máquinas e veículos, maiores] */
type LinhaCidade = [number, number, [number, number, number, number], number, number, number, [string, string, number, string][]];
interface DocCidades { ano: number; fonte: string; mun: Record<string, LinhaCidade> }

/** raiz → [nome, UF, total desde `desde`, abaixo do mercado, último ano, 1 se teve empréstimo direto] */
export interface DocEmpresas { desde: number; ate: string; empresas: Record<string, [string, string, number, number, number, number]> }

const resumos = import.meta.glob<DocResumo>("../../public/data/bndes/resumo.json", { import: "default" });
const cidades = import.meta.glob<DocCidades>("../../public/data/bndes/cidades.json", { import: "default" });
let docR: Promise<DocResumo | null> | null = null;
let docC: Promise<DocCidades | null> | null = null;
export const docBndes = () => (docR ??= Object.values(resumos)[0]?.() ?? Promise.resolve(null));
const docBndesCidades = () => (docC ??= Object.values(cidades)[0]?.() ?? Promise.resolve(null));

export interface BndesCidade {
  ano: number;
  contratos: number;
  total: number;
  faixas: { faixa: Faixa; valor: number }[];
  clientes: number;
  porBanco: number;
  maquinas: number;
  maiores: { nome: string; raiz: string; valor: number; para: string }[];
  /** o que não está entre os maiores: [clientes, valor] */
  outros: [number, number];
}

export async function bndesEm(c: Cidade): Promise<BndesCidade | null> {
  const d = await docBndesCidades();
  const m = d?.mun[String(c.ibge)];
  if (!d || !m) return null;
  const [contratos, total, fx, clientes, porBanco, maquinas, maiores] = m;
  const somaMaiores = maiores.reduce((s, x) => s + x[2], 0);
  return {
    ano: d.ano, contratos, total, clientes, porBanco, maquinas,
    faixas: FAIXAS.map((faixa, i) => ({ faixa, valor: fx[i] })),
    maiores: maiores.map(([nome, raiz, valor, para]) => ({ nome, raiz, valor, para })),
    outros: [clientes - maiores.length, total - somaMaiores],
  };
}

/** O ano na série: total, por forma e por faixa. */
export function doAno(s: LinhaSerie[], ano: number) {
  const l = s.find((x) => x[0] === ano);
  if (!l) return null;
  const [, direta, indireta, abaixo, tlp, mercado, doacao] = l;
  return { total: direta + indireta, direta, indireta, faixas: { abaixo, tlp, mercado, doacao } as Record<Faixa, number> };
}

/** Os nomes das estatais como o Tesouro escreve, mais curtos para a página. */
export const NOME_ESTATAL: Record<string, string> = {
  "Caixa Econômica Federal": "Caixa",
  "Empresa Brasileira de Correios e Telégrafos (Correios)": "Correios",
  "Demais Dividendos e Participações": "Outras",
  BNB: "Banco do Nordeste",
  EBSERH: "Ebserh (hospitais universitários)",
  EMBRAPA: "Embrapa (pesquisa agropecuária)",
  "CONCEIÇÃO": "Grupo Hospitalar Conceição",
  HCPA: "Hospital de Clínicas de Porto Alegre",
  CODEVASF: "Codevasf (vales do São Francisco e do Parnaíba)",
  CONAB: "Conab (abastecimento)",
  CBTU: "CBTU (trens urbanos)",
  CPRM: "Serviço Geológico do Brasil",
  EBC: "EBC (rádio e TV públicas)",
  TRENSURB: "Trensurb (trem de Porto Alegre)",
  "INFRA S.A.": "Infra S.A. (planejamento de transportes)",
};

/** Os nomes dos programas do Orçamento de Subsídios, em palavras simples. */
export const NOME_PROGRAMA: [RegExp, string][] = [
  [/Fundos Constitucionais/i, "Fundos regionais (FNE, FNO, FCO)"],
  [/Fundo de Amparo ao Trabalhador/i, "FAT no BNDES"],
  [/FNDCT/i, "Ciência e tecnologia (FNDCT)"],
  [/Marinha Mercante/i, "Marinha Mercante"],
  [/FIES/i, "Crédito estudantil (Fies)"],
  [/Rio Grande do Sul/i, "Emergência do Rio Grande do Sul"],
  [/Garantia à Exportação/i, "Garantia à exportação (FGE)"],
  [/Empréstimos da União ao BNDES/i, "Empréstimos do Tesouro ao BNDES"],
  [/Banco da Terra/i, "Banco da Terra"],
  [/PROEX/i, "Exportação (Proex)"],
  [/FDA \(/i, "Fundo da Amazônia (FDA)"],
  [/FDNE/i, "Fundo do Nordeste (FDNE)"],
  [/FDCO/i, "Fundo do Centro-Oeste (FDCO)"],
  [/PRONAF/i, "Pronaf"],
];
export const nomePrograma = (s: string) => NOME_PROGRAMA.find(([r]) => r.test(s))?.[1] ?? s;
