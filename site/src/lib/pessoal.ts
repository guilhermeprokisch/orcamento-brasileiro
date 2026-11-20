/**
 * Gasto com pessoal dos governos estaduais e das prefeituras (RGF, Anexo 1, Poder Executivo), lido no
 * build de pipeline/…/pessoal.py. Sem o arquivo, tudo vem null.
 */
import { docCidades } from "./cidades";

interface DocPessoal {
  fonte: string;
  /** ano → código do ente → [despesa total com pessoal, RCL ajustada, despesa bruta, ativos, aposentados e pensionistas] */
  anos: Record<string, Record<string, [number, number, number, number, number]>>;
}
const arquivos = import.meta.glob<DocPessoal>("../../public/data/{estados,cidades}/pessoal.json", { eager: true, import: "default" });
const docs: Record<"uf" | "mun", DocPessoal | null> = {
  uf: arquivos["../../public/data/estados/pessoal.json"] ?? null,
  mun: arquivos["../../public/data/cidades/pessoal.json"] ?? null,
};

/** Limite do Poder Executivo, como parte da receita corrente líquida (art. 20 da LRF). */
export const LIMITES_PESSOAL = { uf: 0.49, mun: 0.54 } as const;
/** Prudencial: 95% do limite (art. 22). Alerta: 90% (art. 59). */
export const prudencial = (esfera: "uf" | "mun") => LIMITES_PESSOAL[esfera] * 0.95;
export const alertaPessoal = (esfera: "uf" | "mun") => LIMITES_PESSOAL[esfera] * 0.9;

export interface AnoPessoal {
  ano: number;
  dtp: number;
  rcl: number;
  bruta: number;
  ativos: number;
  inativos: number;
  /** despesa total com pessoal ÷ receita corrente líquida ajustada */
  razao: number;
}

export interface Pessoal {
  fonte: string;
  anos: AnoPessoal[];
  ultimo: AnoPessoal;
  /** Mediana da razão no último ano: entre os 26 estados (sem o DF) ou entre as prefeituras do mesmo porte. */
  mediana: number | null;
}

const faixaDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.faixa]));
const popDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.pop]));
/**
 * Como na dívida: receita corrente líquida abaixo de R$ 1.500 por morador é declaração de parte do ano,
 * e mais de 100% da receita em pessoal é erro de preenchimento. Esses ficam de fora.
 */
const plausivel = (esfera: "uf" | "mun", ibge: string, v: number[]) =>
  v[1] > 0 && v[0] / v[1] < 1 && (esfera === "uf" || !popDe.get(ibge) || v[1] / popDe.get(ibge)! >= 1500);

export function pessoalDe(ibge: number, esfera: "uf" | "mun" = "uf"): Pessoal | null {
  const doc = docs[esfera];
  if (!doc) return null;
  const anos = Object.entries(doc.anos)
    .map(([ano, entes]) => {
      const v = entes[String(ibge)];
      return v && plausivel(esfera, String(ibge), v)
        ? { ano: Number(ano), dtp: v[0], rcl: v[1], bruta: v[2], ativos: v[3], inativos: v[4], razao: v[0] / v[1] } : null;
    })
    .filter((x): x is AnoPessoal => x !== null)
    .sort((a, b) => a.ano - b.ano);
  const ultimo = anos.at(-1);
  if (!ultimo) return null;
  const faixa = faixaDe.get(String(ibge));
  const razoes = Object.entries(doc.anos[String(ultimo.ano)] ?? {})
    .filter(([k, v]) => plausivel(esfera, k, v) && (esfera === "uf" ? k !== "53" : faixaDe.get(k) === faixa))
    .map(([, v]) => v[0] / v[1]).sort((a, b) => a - b);
  const m = razoes.length >> 1;
  const mediana = razoes.length >= 10 ? (razoes.length % 2 ? razoes[m] : (razoes[m - 1] + razoes[m]) / 2) : null;
  return { fonte: doc.fonte, anos, ultimo, mediana };
}
