/**
 * As emendas dos deputados estaduais (pipeline/…/emendas_estaduais.py): o que cada um indicou no orçamento do estado,
 * para qual cidade e quanto o governo do estado pagou. Só alguns estados publicam isso de um jeito que dá para ler;
 * nos outros, a página diz que ainda não temos.
 */
import { docCidades, type Cidade } from "./cidades";
import { caminhoPolitico, docPoliticos } from "./politicos";
import type { PontoSerie } from "./indicadores";

export interface ItemEstadual {
  /** O valor que a página mostra: o pago, onde o estado publica, ou o indicado. */
  v: number;
  i: number;
  /** O pago, ou null onde o estado (ou o ano) não publica. */
  p: number | null;
  n: number;
  pix?: number;
  /** [prefeitura, entidades, estado e outros]; ausente onde o estado não diz quem recebe. */
  g?: [number, number, number];
  areas: [string, number][];
}
export interface ItemCidade extends ItemEstadual {
  /** [nome como o estado escreve, valor, chave do eleito no TSE]; "coletiva" junta blocos, bancadas e emendas em grupo. */
  aut: [string, number, string | null][];
  nAut: number;
}
export interface ItemDeputado extends ItemEstadual {
  /** O que foi para o estado inteiro, sem uma cidade. */
  est: number;
  cid: [number, number][];
  nc: number;
}
export interface EstadoEmendas {
  nome: string;
  fonte: string;
  url: string;
  anos: number[];
  pago: boolean;
  pix: boolean;
  nota: string | null;
}
interface DocEmendasEstaduais {
  gerado: string;
  anos: number[];
  estados: Record<string, EstadoEmendas>;
  mun: Record<string, Record<string, ItemCidade>>;
  uf: Record<string, Record<string, ItemEstadual & { semCidade: number }>>;
  deputados: Record<string, Record<string, ItemDeputado>>;
}

const arquivos = import.meta.glob<DocEmendasEstaduais>("../../public/data/indicadores/emendas-estaduais.json", { eager: true, import: "default" });
export const docEmendasEstaduais: DocEmendasEstaduais | null = Object.values(arquivos)[0] ?? null;

const anoAtual = new Date().getFullYear();

/** A página de /politicos de um eleito, pela chave do TSE. */
const porChave = new Map((docPoliticos?.politicos ?? []).map((p) => [p.chave, p]));
export function politicoDaChave(chave: string | null): { nome: string; href: string } | null {
  const p = chave ? porChave.get(chave) : undefined;
  return p ? { nome: p.nome, href: caminhoPolitico(p) } : null;
}

/** "ZÉ GUILHERME" → "Zé Guilherme"; nomes em caixa mista ficam como estão. */
export function nomeLegivel(s: string): string {
  if (s !== s.toUpperCase()) return s;
  const pequenas = new Set(["de", "da", "do", "das", "dos", "e"]);
  return s.toLowerCase().split(/\s+/).map((w, i) => (i && pequenas.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(" ");
}

function mediana(v: number[]): number | null {
  if (!v.length) return null;
  const s = [...v].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export interface EmendasEstaduaisCidade {
  uf: string;
  estado: EstadoEmendas;
  ano: number;
  item: ItemCidade;
  /** O valor mostrado é o pago (e não só o indicado). */
  pago: boolean;
  porHab: number;
  /** Mediana por morador das cidades do mesmo estado que receberam alguma emenda no ano. */
  mediana: number | null;
  autores: { nome: string; href: string | null; valor: number; coletiva: boolean }[];
  serie: PontoSerie[];
}

/**
 * As emendas estaduais que chegaram à cidade no último ano fechado. null quando o estado ainda não está na conta
 * (a página mostra só uma linha) ou quando a cidade não recebeu nada.
 */
export function emendasEstaduaisDe(c: Cidade): EmendasEstaduaisCidade | null {
  const d = docEmendasEstaduais;
  const estado = d?.estados[c.uf];
  if (!d || !estado || !c.pop) return null;
  const porAno = d.mun[String(c.ibge)];
  const ano = estado.anos.filter((a) => a < anoAtual).at(-1);
  const item = ano ? porAno?.[String(ano)] : undefined;
  if (!ano || !item || item.v <= 0) return null;
  // Comparação: as cidades do mesmo estado e da mesma faixa de população (cada estado tem regras e cotas próprias),
  // contando as que não receberam nada. Com menos de 5 cidades na faixa, não compara.
  const parecidas = (docCidades?.cidades ?? []).filter((x) => x.uf === c.uf && x.pop && x.faixa === c.faixa);
  const valores = parecidas.map((x) => (d.mun[String(x.ibge)]?.[String(ano)]?.v ?? 0) / x.pop);
  return {
    uf: c.uf, estado, ano, item, pago: item.p !== null, porHab: item.v / c.pop,
    mediana: c.ibge === 53 || valores.length < 5 ? null : mediana(valores),
    autores: item.aut.map(([nome, valor, chave]) => {
      const p = politicoDaChave(chave);
      return { nome: nome === "coletiva" ? "Emendas em grupo" : p?.nome ?? nomeLegivel(nome), href: p?.href ?? null, valor, coletiva: nome === "coletiva" };
    }),
    serie: estado.anos.map((a) => ({ ano: a, valor: (porAno?.[String(a)]?.v ?? 0) / 1e6, preliminar: a >= anoAtual })),
  };
}

/** Os estados que já estão na conta, para a frase "ainda não temos". */
export const estadosComEmendas = (): string[] => Object.keys(docEmendasEstaduais?.estados ?? {});

/** As emendas de um deputado estadual por ano, e o estado de onde vêm. */
export function emendasDoDeputado(chave: string, uf: string): { estado: EstadoEmendas; anos: Record<string, ItemDeputado> } | null {
  const d = docEmendasEstaduais;
  const estado = d?.estados[uf];
  const anos = d?.deputados[chave];
  return estado && anos ? { estado, anos } : null;
}

/** Nome de cidade pelo código IBGE (para a lista de cidades do deputado). */
const cidadesPorIbge = new Map((docCidades?.cidades ?? []).map((x) => [x.ibge, x]));
/** Brasília (5300108) é a página do DF (53): uma emenda de MG para uma entidade em Brasília aparece assim. */
export const cidadeDoIbge = (ibge: number): Cidade | undefined => cidadesPorIbge.get(ibge === 5300108 ? 53 : ibge);

/** A cota de cada deputado do estado no ano: a mediana do indicado e se quase todos têm o mesmo valor. */
export function cotaDoEstado(uf: string, ano: string): { mediana: number; n: number; igual: boolean } | null {
  const d = docEmendasEstaduais;
  if (!d) return null;
  const vs = Object.entries(d.deputados).filter(([k]) => porChave.get(k)?.uf === uf).map(([, a]) => a[ano]?.i ?? 0).filter((x) => x > 0);
  const m = mediana(vs);
  if (!m || vs.length < 5) return null;
  const perto = vs.filter((x) => Math.abs(x / m - 1) <= 0.1).length;
  return { mediana: m, n: vs.length, igual: perto / vs.length >= 0.75 };
}
