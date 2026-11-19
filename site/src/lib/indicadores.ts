/**
 * Indicadores de resultado para pôr ao lado do gasto. Por enquanto, o Ideb por município e
 * rede (pipeline/…/ideb.py). Lido no build; sem o arquivo, tudo vem null.
 */
import { docCidades, type Cidade } from "./cidades";

interface DocIdeb {
  edicao: number;
  fonte: string;
  anos: number[];
  /** mi/mf = rede municipal, anos iniciais/finais; ei/ef = rede estadual. Uma nota por ano. */
  mun: Record<string, Partial<Record<"mi" | "mf" | "ei" | "ef", (number | null)[]>>>;
}

const arquivos = import.meta.glob<DocIdeb>("../../public/data/indicadores/ideb.json", { eager: true, import: "default" });
const doc: DocIdeb | null = Object.values(arquivos)[0] ?? null;

export type Serie = "mi" | "mf" | "ei" | "ef";

export interface NotaIdeb {
  /** Nota da edição mais recente; null se a rede não teve nota nela. */
  nota: number | null;
  /** Nota da edição anterior com valor, e o ano dela. */
  antes: { ano: number; nota: number } | null;
  /** Mediana da mesma nota entre as cidades do mesmo porte (só para a rede municipal). */
  mediana: number | null;
  /** [ano, nota] das edições com valor. */
  historico: [number, number][];
}

export interface Ideb {
  edicao: number;
  fonte: string;
  mi: NotaIdeb | null;
  mf: NotaIdeb | null;
  ei: NotaIdeb | null;
  ef: NotaIdeb | null;
}

function mediana(v: number[]): number | null {
  if (v.length < 10) return null;
  const o = [...v].sort((a, b) => a - b);
  const m = o.length >> 1;
  return o.length % 2 ? o[m] : (o[m - 1] + o[m]) / 2;
}

// Mediana da nota mais recente da rede municipal em cada faixa de população.
const medianas = new Map<string, number | null>();
function medianaDaFaixa(faixa: number, serie: Serie): number | null {
  const chave = `${faixa}-${serie}`;
  if (!medianas.has(chave)) {
    const notas = (docCidades?.cidades ?? [])
      .filter((c) => c.faixa === faixa && c.ibge !== 53)
      .map((c) => doc?.mun[String(c.ibge)]?.[serie]?.at(-1))
      .filter((n): n is number => typeof n === "number");
    medianas.set(chave, mediana(notas));
  }
  return medianas.get(chave)!;
}

function nota(c: Cidade, serie: Serie): NotaIdeb | null {
  const valores = doc?.mun[String(c.ibge)]?.[serie];
  if (!doc || !valores) return null;
  const historico = valores.map((n, i) => [doc.anos[i], n] as const).filter((x): x is [number, number] => x[1] !== null);
  if (!historico.length) return null;
  const atual = valores.at(-1) ?? null;
  const anteriores = historico.filter(([ano]) => ano < doc.edicao);
  const ultimo = anteriores.at(-1);
  return {
    nota: atual,
    antes: ultimo ? { ano: ultimo[0], nota: ultimo[1] } : null,
    mediana: serie.startsWith("m") && c.faixa !== undefined ? medianaDaFaixa(c.faixa, serie) : null,
    historico,
  };
}

/** Ideb das redes municipal e estadual no município; null se não há nenhuma nota. */
export function idebDe(c: Cidade): Ideb | null {
  if (!doc || c.ibge === 53) return null;
  const r = { edicao: doc.edicao, fonte: doc.fonte, mi: nota(c, "mi"), mf: nota(c, "mf"), ei: nota(c, "ei"), ef: nota(c, "ef") };
  return r.mi || r.mf || r.ei || r.ef ? r : null;
}
