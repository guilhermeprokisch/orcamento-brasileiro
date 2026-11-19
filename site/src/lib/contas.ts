/**
 * Receita, saldo e benefícios do INSS de cada município e estado, lidos no build
 * dos arquivos da página /mapa (pipeline/…/mapa.py e inss.py). Cada ano só é
 * carregado se alguma página precisar dele; sem os arquivos, tudo vem null.
 */
import type { Cidade } from "./cidades";

/** Posições do registro de cada ente em mapa/anos/{ano}.json (mapa.py + receitas.CAMPOS). */
const R = {
  desp: 1, receita: 6, propria: 7, uniao: 8, estado: 9, fundeb: 10, credito: 11,
  iptu: 12, iss: 13, itbi: 14, taxas: 16, cosip: 17,
} as const;

interface DocAno {
  mun: Record<string, number[]>;
  uf: Record<string, number[]>;
}
type DocInss = Record<string, [number, number, number]>;

const arquivosAno = import.meta.glob<DocAno>("../../public/data/mapa/anos/*.json", { import: "default" });
const arquivosInss = import.meta.glob<DocInss>("../../public/data/mapa/inss/*.json", { import: "default" });

function leitor<T>(arquivos: Record<string, () => Promise<T>>) {
  const cache = new Map<number, Promise<T | null>>();
  return (ano: number) => {
    if (!cache.has(ano)) {
      const carregar = Object.entries(arquivos).find(([k]) => k.endsWith(`/${ano}.json`))?.[1];
      cache.set(ano, carregar ? carregar() : Promise.resolve(null));
    }
    return cache.get(ano)!;
  };
}
const docAno = leitor(arquivosAno);
const docInss = leitor(arquivosInss);

export type Esfera = "mun" | "uf";

export interface Contas {
  ano: number;
  receita: number;
  despesa: number;
  /** receita − despesa empenhada */
  saldo: number;
  /** De onde veio a receita; a soma é a receita. */
  propria: number;
  uniao: number;
  estado: number;
  fundeb: number;
  credito: number;
  /** Tributos pagos direto à prefeitura (zerados nos estados). */
  iptu: number;
  iss: number;
  itbi: number;
  taxas: number;
  cosip: number;
}

/** O DF aparece em /cidades como Brasília, mas presta contas como estado. */
const chave = (e: Cidade, esfera: Esfera): [Esfera, string] => (e.ibge === 53 ? ["uf", "53"] : [esfera, String(e.ibge)]);

/** Receita e saldo no ano da DCA do ente; null se não há receita declarada nesse ano. */
export async function contasDe(e: Cidade, esfera: Esfera): Promise<Contas | null> {
  if (e.ano === null) return null;
  const [onde, id] = chave(e, esfera);
  const r = (await docAno(e.ano))?.[onde]?.[id];
  if (!r || r.length <= R.receita || !(r[R.receita] > 0)) return null;
  const v = (k: keyof typeof R) => r[R[k]] ?? 0;
  return {
    ano: e.ano, receita: v("receita"), despesa: v("desp"), saldo: v("receita") - v("desp"),
    propria: v("propria"), uniao: v("uniao"), estado: v("estado"), fundeb: v("fundeb"), credito: v("credito"),
    iptu: v("iptu"), iss: v("iss"), itbi: v("itbi"), taxas: v("taxas"), cosip: v("cosip"),
  };
}

export interface Inss {
  ano: number;
  total: number;
  aposentadorias: number;
  pensoes: number;
}

const somasPorUf = new Map<number, Promise<Record<string, [number, number, number]>>>();
function inssPorUf(ano: number) {
  if (!somasPorUf.has(ano)) {
    somasPorUf.set(ano, docInss(ano).then((doc) => {
      const soma: Record<string, [number, number, number]> = {};
      for (const [ibge, v] of Object.entries(doc ?? {})) {
        const s = (soma[ibge.slice(0, 2)] ??= [0, 0, 0]);
        v.forEach((x, i) => (s[i] += x));
      }
      return soma;
    }));
  }
  return somasPorUf.get(ano)!;
}

/** Benefícios do INSS pagos no município (ou somados no estado) no ano da DCA do ente. */
export async function inssDe(e: Cidade, esfera: Esfera): Promise<Inss | null> {
  if (e.ano === null) return null;
  const v = esfera === "uf" || e.ibge === 53
    ? (await inssPorUf(e.ano))[String(e.ibge).slice(0, 2)]
    : (await docInss(e.ano))?.[String(e.ibge)];
  return v && v[0] > 0 ? { ano: e.ano, total: v[0], aposentadorias: v[1], pensoes: v[2] } : null;
}

/** Link para o ente na página /mapa, já na pergunta "sobrou ou faltou". */
export const caminhoNoMapa = (e: Cidade, esfera: Esfera) => {
  const [onde, id] = chave(e, esfera);
  return `/mapa/#${onde === "mun" ? "c" : "e"}${id}-a${e.ano}-saldo`;
};
