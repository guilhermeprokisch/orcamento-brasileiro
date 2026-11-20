/**
 * Dívida dos governos estaduais e das prefeituras (RGF, Anexo 2), lida no build de
 * pipeline/…/divida.py. Sem o arquivo, tudo vem null.
 */
import { docCidades } from "./cidades";

interface DocDivida {
  fonte: string;
  /** ano → código do ente → [dívida consolidada, dívida consolidada líquida, receita corrente líquida ajustada] */
  anos: Record<string, Record<string, [number, number, number]>>;
}
const arquivos = import.meta.glob<DocDivida>("../../public/data/{estados,cidades}/divida.json", { eager: true, import: "default" });
const docs: Record<"uf" | "mun", DocDivida | null> = {
  uf: arquivos["../../public/data/estados/divida.json"] ?? null,
  mun: arquivos["../../public/data/cidades/divida.json"] ?? null,
};

/**
 * Limite da dívida consolidada líquida, em vezes a receita corrente líquida (Resolução 40/2001 do
 * Senado): 2 para os estados, 1,2 para as prefeituras.
 */
export const LIMITES = { uf: 2, mun: 1.2 } as const;
/** Limite de alerta: 90% do limite (art. 59 da LRF). */
export const alerta = (esfera: "uf" | "mun") => LIMITES[esfera] * 0.9;

export interface AnoDivida {
  ano: number;
  bruta: number;
  liquida: number;
  rcl: number;
  /** dívida líquida ÷ receita corrente líquida */
  razao: number;
}

export interface Divida {
  fonte: string;
  anos: AnoDivida[];
  ultimo: AnoDivida;
  /** Mediana da razão no último ano: entre os 26 estados (sem o DF) ou entre as prefeituras do mesmo porte. */
  mediana: number | null;
  /** Quantas prefeituras do mesmo porte (ou estados) estão acima do limite. */
  acima: number;
}

const faixaDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.faixa]));
const popDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.pop]));
/**
 * Receita corrente líquida abaixo de R$ 1.500 por morador (a mediana das prefeituras passa de R$ 6.500)
 * é quase sempre declaração de só parte do ano: a dívida dividida por ela sai muitas vezes maior do que é.
 * Essas prefeituras ficam de fora, da página e das medianas.
 */
const RCL_MINIMA_POR_MORADOR = 1500;
const plausivel = (esfera: "uf" | "mun", ibge: string, rcl: number) =>
  rcl > 0 && (esfera === "uf" || !popDe.get(ibge) || rcl / popDe.get(ibge)! >= RCL_MINIMA_POR_MORADOR);

export function dividaDe(ibge: number, esfera: "uf" | "mun" = "uf"): Divida | null {
  const doc = docs[esfera];
  if (!doc) return null;
  const anos = Object.entries(doc.anos)
    .map(([ano, entes]) => {
      const v = entes[String(ibge)];
      return v && plausivel(esfera, String(ibge), v[2]) ? { ano: Number(ano), bruta: v[0], liquida: v[1], rcl: v[2], razao: v[1] / v[2] } : null;
    })
    .filter((x): x is AnoDivida => x !== null)
    .sort((a, b) => a.ano - b.ano);
  const ultimo = anos.at(-1);
  if (!ultimo) return null;
  const faixa = faixaDe.get(String(ibge));
  const razoes = Object.entries(doc.anos[String(ultimo.ano)] ?? {})
    .filter(([k, v]) => plausivel(esfera, k, v[2]) && (esfera === "uf" ? k !== "53" : faixaDe.get(k) === faixa))
    .map(([, v]) => v[1] / v[2]).sort((a, b) => a - b);
  const m = razoes.length >> 1;
  const mediana = razoes.length >= 10 ? (razoes.length % 2 ? razoes[m] : (razoes[m - 1] + razoes[m]) / 2) : null;
  return { fonte: doc.fonte, anos, ultimo, mediana, acima: razoes.filter((r) => r >= LIMITES[esfera]).length };
}
