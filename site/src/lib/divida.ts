/**
 * Dívida dos governos estaduais (RGF, Anexo 2), lida no build de pipeline/…/divida.py.
 * Sem o arquivo, tudo vem null.
 */
interface DocDivida {
  fonte: string;
  /** ano → código do estado → [dívida consolidada, dívida consolidada líquida, receita corrente líquida ajustada] */
  anos: Record<string, Record<string, [number, number, number]>>;
}
const arquivos = import.meta.glob<DocDivida>("../../public/data/estados/divida.json", { eager: true, import: "default" });
const doc: DocDivida | null = Object.values(arquivos)[0] ?? null;

/** Limite da dívida consolidada líquida dos estados: duas vezes a receita corrente líquida (Resolução 40/2001 do Senado). */
export const LIMITE = 2;
/** Limite de alerta: 90% do limite (art. 59 da LRF). */
export const ALERTA = LIMITE * 0.9;

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
  /** Mediana da razão entre os 26 estados (sem o DF) no último ano. */
  mediana: number | null;
}

export function dividaDe(ibge: number): Divida | null {
  if (!doc) return null;
  const anos = Object.entries(doc.anos)
    .map(([ano, estados]) => {
      const v = estados[String(ibge)];
      return v && v[2] > 0 ? { ano: Number(ano), bruta: v[0], liquida: v[1], rcl: v[2], razao: v[1] / v[2] } : null;
    })
    .filter((x): x is AnoDivida => x !== null)
    .sort((a, b) => a.ano - b.ano);
  const ultimo = anos.at(-1);
  if (!ultimo) return null;
  const razoes = Object.entries(doc.anos[String(ultimo.ano)] ?? {})
    .filter(([k, v]) => k !== "53" && v[2] > 0).map(([, v]) => v[1] / v[2]).sort((a, b) => a - b);
  const m = razoes.length >> 1;
  const mediana = razoes.length >= 10 ? (razoes.length % 2 ? razoes[m] : (razoes[m - 1] + razoes[m]) / 2) : null;
  return { fonte: doc.fonte, anos, ultimo, mediana };
}
