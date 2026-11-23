/**
 * Preço pago comparado (pipeline/…/precos.py): o mesmo remédio comprado por cidades e estados diferentes.
 * precos.json traz, por cidade e por estado, as compras mais caras que as parecidas; remedios.json, a página nacional.
 */

/** [código, ano, data, preço, mediana das parecidas, quantidade, a mais, modalidade, comprador, fornecedor, link] */
export type Cara = [number, number, string, number, number, number, number, string, string, string, string];
/** [objeto, data da homologação, itens, valor homologado, link] */
export type SoUm = [string, string, number, number, string];

export interface DisputaRS { ano: number; informa: boolean; pregoes: number; itens: number; um: number; so_um: SoUm[]; n_so_um: number }
export interface PrecosEnte { n: number; r: number; baratas: number; caras: Cara[]; n_caras: number; n_dobro: number; rs?: DisputaRS }
interface DocPrecos {
  fonte: string; gerado: string; anos: number[];
  regras: { mais_cara: number; a_mais: number; erro: number };
  remedios: Record<string, [string, string]>;
  mun: Record<string, PrecosEnte>; uf: Record<string, PrecosEnte>;
}

/** [comprador, UF, esfera, código IBGE (prefeituras), data, preço, quantidade, vezes a mediana das parecidas, modalidade, link] */
export type CompraNacional = [string, string, string, number | null, string, number, number, number, string, string];
export interface AnoRemedio {
  n: number; compradores: number; fora: number; mediana: number; faixa: [number, number];
  /** [limite de quantidade do grupo (null no último), mediana do grupo] */
  grupos: [number | null, number][];
  regioes: Record<string, [number, number]>;
  compras: CompraNacional[];
}
export interface Remedio { codigo: number; nome: string; forma: string; anos: Record<string, AnoRemedio> }
interface DocNacional { gerado: string; anos: number[]; remedios: Remedio[] }

const arqPrecos = import.meta.glob<DocPrecos>("../../public/data/indicadores/precos.json", { eager: true, import: "default" });
export const docPrecos: DocPrecos | null = Object.values(arqPrecos)[0] ?? null;
const arqNacional = import.meta.glob<DocNacional>("../../public/data/precos/remedios.json", { eager: true, import: "default" });
export const docNacional: DocNacional | null = Object.values(arqNacional)[0] ?? null;

export function precosDe(ibge: number | string, esfera: "mun" | "uf" = "mun"): PrecosEnte | null {
  return docPrecos?.[esfera]?.[String(ibge)] ?? null;
}

export const nomeRemedio = (cod: number) => docPrecos?.remedios[String(cod)]?.[0] ?? String(cod);
export const formaRemedio = (cod: number) => docPrecos?.remedios[String(cod)]?.[1] ?? "unidade";

/** "comprimido" → "comprimidos"; "cápsula" → "cápsulas" */
export const plural = (forma: string) => `${forma}s`;
/** "o comprimido", "a cápsula", "a ampola" */
export const artigo = (forma: string) => (forma === "comprimido" ? `o ${forma}` : `a ${forma}`);

const nf = (min: number, max: number) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: min, maximumFractionDigits: max });
const nf0 = nf(0, 0), nf1 = nf(1, 1), nf2 = nf(2, 2), nf3 = nf(3, 3);
/** Preço de um comprimido: R$ 0,043; R$ 0,31; R$ 3,72. */
export const precoUnit = (v: number) => `R$ ${v < 0.1 ? nf3.format(v) : nf2.format(v)}`;
/** 7,8 vezes; 1,5 vez */
export const vezes = (r: number) => `${nf1.format(r)} ${r < 2 ? "vez" : "vezes"}`;
/** 840 mil; 1,2 milhão; 5.000 */
export function quantidade(n: number): string {
  if (n >= 1e6) return `${nf1.format(n / 1e6).replace(/,0$/, "")} ${n < 2e6 ? "milhão" : "milhões"}`;
  if (n >= 10000) return `${nf0.format(Math.round(n / 1000))} mil`;
  return nf0.format(n);
}
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
/** "2026-04-10" → "abril de 2026" */
export const mesAno = (d: string) => `${MESES[Number(d.slice(5, 7)) - 1]} de ${d.slice(0, 4)}`;
/** "2026-04-10" → "10/04/2026" */
export const dataCurta = (d: string) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
