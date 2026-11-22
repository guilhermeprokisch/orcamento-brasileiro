/**
 * Benefícios fiscais por empresa (/impostos/empresas): o que cada empresa declarou à Receita, na Dirbi, que deixou de
 * pagar em impostos federais. Gerado por pipeline/…/beneficios_fiscais.py; lido no build. Sem o arquivo, vem null.
 *
 * Privacidade: empresário individual e MEI (nomes de pessoas) não aparecem pelo nome, só nos totais ("ocultas").
 */

export type Tipo = "empresa" | "produto" | "setor";

export interface Grupo {
  id: string;
  nome: string;
  sub: string;
  tipo: Tipo;
  valor: number;
  empresas: number;
  /** parte do grupo que fica com as 10 maiores dele */
  top10: number;
  maiores: { raiz: string; nome: string; valor: number }[];
}

export interface Maior {
  pos: number;
  /** raiz do CNPJ (8 dígitos); vazia para quem tem restrição judicial */
  raiz: string;
  nome: string;
  municipio: string;
  uf: string;
  setor: string;
  grupo: string;
  tipo: Tipo;
  beneficio: string;
  valor: number;
  /** dívida ativa em cobrança na PGFN (0 abaixo de R$ 100 mil) */
  cobranca: number;
  restricao: boolean;
}

export interface DocBeneficios {
  fonte: string;
  ano: number;
  /** "09/2026": a posição da dívida ativa */
  pgfn: string;
  contratosAno: number | null;
  empresasArquivo: string;
  porCnpj: string;
  anos: { ano: number; valor: number; empresas: number; meses: number; ultimoMes: number }[];
  total: number;
  empresas: number;
  mediana: number;
  concentracao: { top10: number; top100: number; top1pct: number; n1pct: number; bilhao: [number, number]; metadeBaixo: [number, number] };
  tipos: Partial<Record<Tipo, number>>;
  grupos: Grupo[];
  maiores: Maior[];
  /** [UF da matriz, valor, nº de empresas] */
  uf: [string, number, number][];
  cruzamentos: {
    /** [empresas, benefício delas, dívida em cobrança] */
    devem: [number, number, number];
    /** [empresas, valor dos contratos, benefício delas] */
    contratos: [number, number, number];
    /** [empresas, benefício delas]: benefício, dívida em cobrança e contrato */
    tres: [number, number];
  };
  restricao: [number, number];
  ocultas: [number, number];
}

const arquivos = import.meta.glob<DocBeneficios>("../../public/data/beneficios-fiscais/resumo.json", { eager: true, import: "default" });
export const docBeneficios: DocBeneficios | null = Object.values(arquivos)[0] ?? null;

export const COR_TIPO: Record<Tipo, string> = { empresa: "#0e6b3b", produto: "#c3bba7", setor: "#8a8475" };
export const NOME_TIPO: Record<Tipo, string> = { empresa: "da empresa", produto: "do produto", setor: "do setor" };

const pequenas = new Set(["de", "da", "do", "das", "dos", "e", "em", "para"]);
const SIGLAS = /^(s\/?a\.?|s\.a\.?|me|epp|eireli|ltda\.?|brf|jbs|lg|tcl|ii|iii|bmg|cnh|ocp|tag|hnk|br|gr|rm|isa|tec|ctva|basf)$/i;
/** "MOTO HONDA DA AMAZONIA LTDA" → "Moto Honda da Amazonia". Nomes que não estão em caixa alta ficam como estão. */
export function nomeEmpresa(s: string): string {
  if (!s || s !== s.toUpperCase()) return s;
  const limpo = s.replace(/\s+(LTDA\.?|S\/A\.?|S\.A\.?|SA|EIRELI|ME|EPP)\s*$/i, "").replace(/\s+-\s+EM RECUPERACAO JUDICIAL$/i, "");
  return limpo.toLowerCase().split(/\s+/).map((p, i) => {
    if ((SIGLAS.test(p) && !/^ltda/i.test(p)) || (p.length <= 4 && !/[aeiouáéíóúâêôãõ]/.test(p))) return p.toUpperCase();
    if (i > 0 && pequenas.has(p)) return p;
    return p.charAt(0).toUpperCase() + p.slice(1);
  }).join(" ");
}

/** "Restrição Judicial (15)" → "Nome escondido por decisão judicial (15)" */
export const nomeExibido = (m: { nome: string; raiz: string }) =>
  m.raiz ? nomeEmpresa(m.nome) : m.nome.replace(/restri[çc][ãa]o judicial/i, "Restrição judicial");
