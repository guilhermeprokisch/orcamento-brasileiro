/**
 * Obras paradas: as obras com dinheiro federal que o TCU considera paralisadas (Painel de Obras Paralisadas),
 * por cidade e estado. Gerado por pipeline/…/obras_paradas.py a partir das tabelas exportadas do painel;
 * lido no build. Sem o arquivo, tudo vem null.
 */
import { NOMES_UF, type Cidade } from "./cidades";

/** [n.º de obras, valor previsto, valor liberado] */
type Soma = [number, number, number];
/** [nome, base, quem paga, instrumento, % feito, previsto, liberado, causa, situação no órgão, desde, setor,
 *  quis repactuar (0/1), (local, ibge)] */
type ObraBruta = [string, string, string, string | null, number | null, number, number, string | null, string | null,
  string, string, number, string?, (number | null)?];

interface DocObras {
  data_base: string;
  datas: string[];
  fonte: string;
  url: string;
  bases: Record<string, string>;
  brasil: {
    total: Soma;
    ativas: number;
    cidades_com_obra: number;
    sem_cidade: Soma;
    quem_paga: [string, ...Soma][];
    base: [string, ...Soma][];
    setor: [string, ...Soma][];
    causa: [string, ...Soma][];
    sem_causa: number;
    origem: [string, ...Soma][];
    desde: [string, ...Soma][];
    pacto: Soma;
    maiores: ObraBruta[];
    uf: Record<string, [...Soma, number]>;
    historico: { data: string; paralisadas: number; em_execucao: number; previsto: number; liberado: number }[];
    destino: { de: string; total: number; situacoes: [string, number][] } | null;
  };
  uf: Record<string, {
    total: Soma;
    ativas: number;
    cidades_com_obra: number;
    cidades: [string, ...Soma][];
    quem_paga: [string, ...Soma][];
    maiores: ObraBruta[];
    sem_cidade: ObraBruta[];
  }>;
  /** ibge → [n.º, previsto, liberado, obras ativas (em execução + paradas), obras] */
  mun: Record<string, [...Soma, number, ObraBruta[]]>;
}

const arquivos = import.meta.glob<DocObras>("../../public/data/obras-paradas/obras-paradas.json", { import: "default" });
let doc: Promise<DocObras | null> | null = null;
export const docObrasParadas = () => (doc ??= Object.values(arquivos)[0]?.() ?? Promise.resolve(null));

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
/** "2026-04" → "abril de 2026" */
export const mesAno = (d: string) => `${MESES[Number(d.slice(5, 7)) - 1]} de ${d.slice(0, 4)}`;
/** "2026-04" → "abr/2026" */
export const mesAnoCurto = (d: string) => `${MESES[Number(d.slice(5, 7)) - 1].slice(0, 3)}/${d.slice(0, 4)}`;

/** Situações do órgão que dizem a mesma coisa que o TCU: não vale repetir ao lado da obra. */
const MESMA_SITUACAO = /^(paralisad[ao]|obra paralisada)$/i;

export interface Obra {
  nome: string;
  /** Quem acompanha a obra (a base de onde o TCU tirou a linha), já por extenso. */
  base: string;
  quemPaga: string;
  instrumento: string | null;
  feito: number | null;
  previsto: number;
  liberado: number;
  causa: string | null;
  /** A situação que o órgão informa, quando é diferente de "paralisada". */
  noOrgao: string | null;
  desde: string;
  setor: string;
  repactuar: boolean;
  local: string | null;
  ibge: number | null;
}

const obra = (o: ObraBruta, bases: Record<string, string>): Obra => ({
  nome: o[0],
  base: bases[o[1]] ?? o[1],
  quemPaga: o[2],
  instrumento: o[3],
  feito: o[4],
  previsto: o[5],
  liberado: o[6],
  causa: o[7],
  noOrgao: o[8] && !MESMA_SITUACAO.test(o[8]) ? o[8] : null,
  desde: o[9],
  setor: o[10],
  repactuar: o[11] === 1,
  local: o[12] ?? null,
  ibge: o[13] ?? null,
});

export interface Contagem { nome: string; n: number; previsto: number; liberado: number }
const contagem = ([nome, n, previsto, liberado]: [string, ...Soma]): Contagem => ({ nome, n, previsto, liberado });

interface Comum {
  dataBase: string;
  datas: string[];
  fonte: string;
  url: string;
}
const comum = (d: DocObras): Comum => ({ dataBase: d.data_base, datas: d.datas, fonte: d.fonte, url: d.url });

export interface ObrasCidade extends Comum {
  n: number;
  previsto: number;
  liberado: number;
  /** Obras federais ativas na cidade (em execução + paradas), na mesma lista do TCU. */
  ativas: number;
  obras: Obra[];
}

/** As obras paradas de uma cidade. null sem o arquivo; n = 0 quando a cidade não tem nenhuma na lista. */
export async function obrasNaCidade(c: Pick<Cidade, "ibge">): Promise<ObrasCidade | null> {
  const d = await docObrasParadas();
  if (!d) return null;
  const chave = c.ibge === 53 ? "5300108" : String(c.ibge);
  const m = d.mun[chave];
  if (!m) return { ...comum(d), n: 0, previsto: 0, liberado: 0, ativas: 0, obras: [] };
  return { ...comum(d), n: m[0], previsto: m[1], liberado: m[2], ativas: m[3], obras: m[4].map((o) => obra(o, d.bases)) };
}

export interface ObrasEstado extends Comum {
  n: number;
  previsto: number;
  liberado: number;
  ativas: number;
  cidadesComObra: number;
  cidades: { ibge: number; n: number; previsto: number; liberado: number }[];
  quemPaga: Contagem[];
  maiores: Obra[];
  semCidade: Obra[];
}

export async function obrasNoEstado(uf: string): Promise<ObrasEstado | null> {
  const d = await docObrasParadas();
  const e = d?.uf[uf];
  if (!d) return null;
  if (!e) return { ...comum(d), n: 0, previsto: 0, liberado: 0, ativas: 0, cidadesComObra: 0, cidades: [], quemPaga: [], maiores: [], semCidade: [] };
  return {
    ...comum(d),
    n: e.total[0],
    previsto: e.total[1],
    liberado: e.total[2],
    ativas: e.ativas,
    cidadesComObra: e.cidades_com_obra,
    cidades: e.cidades.map(([ibge, n, previsto, liberado]) => ({ ibge: Number(ibge), n, previsto, liberado })),
    quemPaga: e.quem_paga.map(contagem),
    maiores: e.maiores.map((o) => obra(o, d.bases)),
    semCidade: e.sem_cidade.map((o) => obra(o, d.bases)),
  };
}

export interface ObrasBrasil extends Comum {
  n: number;
  previsto: number;
  liberado: number;
  ativas: number;
  cidadesComObra: number;
  semCidade: Contagem;
  quemPaga: Contagem[];
  setor: Contagem[];
  causa: Contagem[];
  semCausa: number;
  noOrgao: Contagem[];
  desde: Contagem[];
  repactuar: Contagem;
  maiores: Obra[];
  estados: { uf: string; nome: string; n: number; previsto: number; liberado: number; ativas: number }[];
  historico: DocObras["brasil"]["historico"];
  destino: DocObras["brasil"]["destino"];
}

export async function obrasNoBrasil(): Promise<ObrasBrasil | null> {
  const d = await docObrasParadas();
  if (!d) return null;
  const b = d.brasil;
  return {
    ...comum(d),
    n: b.total[0],
    previsto: b.total[1],
    liberado: b.total[2],
    ativas: b.ativas,
    cidadesComObra: b.cidades_com_obra,
    semCidade: contagem(["", ...b.sem_cidade]),
    quemPaga: b.quem_paga.map(contagem),
    setor: b.setor.map(contagem),
    causa: b.causa.map(contagem),
    semCausa: b.sem_causa,
    noOrgao: b.origem.map(contagem),
    desde: b.desde.map(contagem),
    repactuar: contagem(["", ...b.pacto]),
    maiores: b.maiores.map((o) => obra(o, d.bases)),
    estados: Object.entries(b.uf)
      .map(([uf, [n, previsto, liberado, ativas]]) => ({ uf, nome: NOMES_UF[uf] ?? uf, n, previsto, liberado, ativas }))
      .sort((a, b) => b.n - a.n),
    historico: b.historico,
    destino: b.destino,
  };
}
