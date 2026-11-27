/**
 * Para quem vai o dinheiro da saúde e da educação de cada prefeitura: entidades sem fins lucrativos,
 * organizações sociais, empresas, pessoal terceirizado, folha própria, outros governos e o resto.
 * Lido no build de public/data/indicadores/saude-entidades.json (pipeline/…/saude_entidades.py).
 */
import { docCidades, type Cidade } from "./cidades";

interface DocDestino {
  fonte: string;
  ano: number;
  grupos: string[];
  brasil: Record<string, number[]>;
  /** ibge → função ("10" saúde, "12" educação) → [liquidado, um valor por grupo] */
  mun: Record<string, Record<string, number[]>>;
}

const arquivos = import.meta.glob<DocDestino>("../../public/data/indicadores/saude-entidades.json", { eager: true, import: "default" });
const doc: DocDestino | null = Object.values(arquivos)[0] ?? null;

/** Índices dos grupos no arquivo. */
export const G = { entidades: 0, os: 1, empresas: 2, terceirizados: 3, folha: 4, governos: 5, prefeitura: 6 } as const;

export interface Destino {
  fonte: string;
  ano: number;
  total: number;
  /** valor de cada grupo, na ordem de G */
  valores: number[];
  /** parte que foi para entidades sem fins lucrativos, organizações sociais e empresas (0 a 1) */
  privado: number;
  /** a mesma parte, na mediana das cidades da mesma faixa de população; null se não houver cidades bastantes */
  privadoParecidas: number | null;
}

const privadoDe = (v: number[]) => (v[0] > 0 ? (v[1 + G.entidades] + v[1 + G.os] + v[1 + G.empresas]) / v[0] : 0);

const medianas = new Map<string, number | null>();
function medianaPrivado(faixa: number, funcao: string): number | null {
  const chave = `${faixa}-${funcao}`;
  if (medianas.has(chave)) return medianas.get(chave)!;
  const partes = (docCidades?.cidades ?? [])
    .filter((c) => c.faixa === faixa)
    .map((c) => doc?.mun[String(c.ibge)]?.[funcao])
    .filter((v): v is number[] => !!v && v[0] > 0)
    .map(privadoDe)
    .sort((a, b) => a - b);
  const m = partes.length >= 20 ? partes[Math.floor(partes.length / 2)] : null;
  medianas.set(chave, m);
  return m;
}

export function destinoDe(c: Cidade, funcao: "10" | "12"): Destino | null {
  const v = doc?.mun[String(c.ibge)]?.[funcao];
  if (!doc || !v || v[0] <= 0) return null;
  return {
    fonte: doc.fonte, ano: doc.ano, total: v[0], valores: v.slice(1), privado: privadoDe(v),
    privadoParecidas: c.faixa !== undefined ? medianaPrivado(c.faixa, funcao) : null,
  };
}
