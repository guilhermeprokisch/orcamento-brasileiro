/**
 * Os avisos das páginas de cidade e de estado (item E do plano de melhorias). Cada um tem uma regra
 * escrita, que a página mostra ao lado; o levantamento das fontes e dos cortes está em
 * docs/levantamento-avisos.md.
 *
 * 1. Mínimo em saúde e em educação não aplicado: o percentual que o próprio governo apurou (RREO Anexo 14,
 *    6º bimestre), lido no build de pipeline/…/minimos.py.
 * 2. Vários anos seguidos gastando mais do que arrecada: despesa empenhada × receita arrecadada da DCA
 *    (mapa/serie.json).
 * 3. Dado com cara de erro: a mesma série, olhando o dado e não o governo.
 *
 * Sem os arquivos, não há aviso.
 */

type Esfera = "uf" | "mun";

interface DocMinimos {
  fonte: string;
  campos: string[];
  /** ano → código do ente → [saúde aplicada, mínimo de saúde, educação aplicada, mínimo de educação], em % */
  anos: Record<string, Record<string, [number | null, number | null, number | null, number | null]>>;
}
interface DocSerie {
  anos: number[];
  /** código do ente → [despesa empenhada ano a ano, receita arrecadada ano a ano] */
  mun: Record<string, [(number | null)[], (number | null)[]]>;
  uf: Record<string, [(number | null)[], (number | null)[]]>;
}

const arquivos = import.meta.glob<DocMinimos | DocSerie>(
  ["../../public/data/{estados,cidades}/minimos.json", "../../public/data/mapa/serie.json"],
  { eager: true, import: "default" },
);
const minimos: Record<Esfera, DocMinimos | null> = {
  uf: (arquivos["../../public/data/estados/minimos.json"] as DocMinimos) ?? null,
  mun: (arquivos["../../public/data/cidades/minimos.json"] as DocMinimos) ?? null,
};
const serie = (arquivos["../../public/data/mapa/serie.json"] as DocSerie) ?? null;

// ---- as regras -------------------------------------------------------------------------------------------

/** Mínimos da Constituição e da LC 141/2012, em % da receita de impostos e transferências. */
export const MINIMOS = { saude: { mun: 15, uf: 12 }, educacao: { mun: 25, uf: 25 } } as const;
/** EC 119/2022: sem punição por não aplicar o mínimo em educação nesses anos (pandemia). */
export const ANOS_SEM_AVISO_EDUCACAO = [2020, 2021];
/** Déficit: pelo menos tantos anos seguidos, até o último entregue… */
export const DEFICIT_ANOS = 3;
/** …com a despesa acima da receita em mais desta fração da receita, em cada um. */
export const DEFICIT_CORTE = 0.02;
/** Dado: anos a partir deste. */
export const DADO_DESDE = 2016;
/** Dado: receita e despesa diferentes em mais desta fração da receita. */
export const DADO_DIFERENCA = 0.3;
/** Dado: despesa ou receita tantas vezes acima ou abaixo da mediana do próprio ente. */
export const DADO_ESCALA = 5;

// ---- 1. mínimo em saúde e em educação --------------------------------------------------------------------

export type Area = "saude" | "educacao";

export interface AvisoMinimo {
  tipo: "minimo";
  area: Area;
  ano: number;
  /** % aplicado no ano */
  aplicado: number;
  /** % mínimo da lei */
  minimo: number;
  /** Outros anos no arquivo em que também ficou abaixo (do mais recente para o mais antigo). */
  outros: { ano: number; aplicado: number }[];
  fonte: string;
}

/**
 * O percentual como declarado. Há quem declare fração (0,28 em vez de 28%: Amapá, Anápolis, Japeri):
 * acima de zero e abaixo de 1 é lido como fração. Zero ou mais de 100% é erro de preenchimento: fica de fora.
 */
function percentual(v: number | null | undefined): number | null {
  if (v === null || v === undefined || !(v > 0)) return null;
  const p = v < 1 ? v * 100 : v;
  return p > 100 ? null : p;
}

/** O mínimo que vale para o ente. O DF soma o mínimo estadual (12%) e o municipal (15%) sobre partes da receita. */
function minimoDe(area: Area, esfera: Esfera, ibge: number, declarado: number | null): number {
  if (area === "saude" && ibge === 53 && declarado !== null) {
    const d = percentual(declarado);
    if (d !== null && d >= 12 && d <= 15) return d;
  }
  return MINIMOS[area][esfera];
}

function avisosMinimo(ibge: number, esfera: Esfera): AvisoMinimo[] {
  const doc = minimos[esfera];
  if (!doc) return [];
  const anos = Object.keys(doc.anos).map(Number).sort((a, b) => b - a);
  const avisos: AvisoMinimo[] = [];
  for (const [area, i] of [["saude", 0], ["educacao", 2]] as const) {
    const pontos = anos
      .map((ano) => {
        const v = doc.anos[String(ano)][String(ibge)];
        const aplicado = percentual(v?.[i]);
        return aplicado === null ? null : { ano, aplicado, minimo: minimoDe(area, esfera, ibge, v![i + 1]) };
      })
      .filter((p): p is { ano: number; aplicado: number; minimo: number } => p !== null)
      .filter((p) => !(area === "educacao" && ANOS_SEM_AVISO_EDUCACAO.includes(p.ano)));
    const [ultimo, ...antes] = pontos;
    if (!ultimo || ultimo.aplicado >= ultimo.minimo) continue;
    avisos.push({
      tipo: "minimo", area, ano: ultimo.ano, aplicado: ultimo.aplicado, minimo: ultimo.minimo, fonte: doc.fonte,
      outros: antes.filter((p) => p.aplicado < p.minimo).map(({ ano, aplicado }) => ({ ano, aplicado })),
    });
  }
  return avisos;
}

// ---- 3. dado com cara de erro ----------------------------------------------------------------------------

export type Motivo =
  | { tipo: "falta" }
  | { tipo: "repetido"; qual: "despesa" | "receita" | "as duas" }
  | { tipo: "diferenca"; /** (despesa − receita) ÷ receita */ razao: number }
  | { tipo: "escala"; qual: "despesa" | "receita" | "as duas"; /** valor ÷ mediana do ente */ vezes: number };

export interface AvisoDado {
  tipo: "dado";
  /** Do mais antigo para o mais recente. */
  anos: { ano: number; motivos: Motivo[] }[];
}

const mediana = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const qual = (d: boolean, r: boolean) => (d && r ? "as duas" : d ? "despesa" : "receita") as "despesa" | "receita" | "as duas";

function motivosDoDado(ibge: number, esfera: Esfera): Map<number, Motivo[]> {
  const motivos = new Map<number, Motivo[]>();
  const s = serie?.[esfera]?.[String(ibge)];
  if (!serie || !s) return motivos;
  const [desp, rec] = s;
  const anos = serie.anos;
  const med = [desp, rec].map((x) => {
    const v = x.filter((n): n is number => !!n);
    return v.length >= 4 ? mediana(v) : null;
  });
  const fora = (v: number | null, m: number | null) => !!v && !!m && (v > DADO_ESCALA * m || v < m / DADO_ESCALA);
  const anota = (ano: number, m: Motivo) => motivos.set(ano, [...(motivos.get(ano) ?? []), m]);
  const comDado = anos.filter((a, i) => a >= DADO_DESDE && !!desp[i]);
  anos.forEach((ano, i) => {
    if (ano < DADO_DESDE) return;
    const d = desp[i], r = rec[i];
    if (!d) {
      if (comDado.length && ano > comDado[0]) anota(ano, { tipo: "falta" });
      return;
    }
    const repD = i > 0 && d === desp[i - 1], repR = i > 0 && !!r && r === rec[i - 1];
    if (repD || repR) anota(ano, { tipo: "repetido", qual: qual(repD, repR) });
    const escD = fora(d, med[0]), escR = fora(r, med[1]);
    if (escD || escR) {
      const vezes = escD ? d / med[0]! : r! / med[1]!;
      anota(ano, { tipo: "escala", qual: qual(escD, escR), vezes });
    }
    if (r && Math.abs(d - r) / r > DADO_DIFERENCA) anota(ano, { tipo: "diferenca", razao: (d - r) / r });
  });
  return motivos;
}

// ---- 2. vários anos gastando mais do que arrecada --------------------------------------------------------

export interface AvisoDeficit {
  tipo: "deficit";
  /** Do mais antigo para o mais recente: (despesa − receita) ÷ receita. */
  anos: { ano: number; razao: number; despesa: number; receita: number }[];
}

function avisoDeficit(ibge: number, esfera: Esfera, suspeitos: Map<number, Motivo[]>): AvisoDeficit | null {
  const s = serie?.[esfera]?.[String(ibge)];
  if (!serie || !s) return null;
  const [desp, rec] = s;
  let i = desp.findLastIndex((v) => !!v);
  // Só vale se o último ano entregue é recente: o atual ou o anterior.
  if (i < 0 || serie.anos[i] < serie.anos.at(-1)! - 1) return null;
  const anos: AvisoDeficit["anos"] = [];
  for (; i >= 0; i--) {
    const d = desp[i], r = rec[i], ano = serie.anos[i];
    // Um ano de dado suspeito não conta e interrompe a sequência.
    if (!d || !r || suspeitos.has(ano) || (d - r) / r <= DEFICIT_CORTE) break;
    anos.unshift({ ano, razao: (d - r) / r, despesa: d, receita: r });
  }
  return anos.length >= DEFICIT_ANOS ? { tipo: "deficit", anos } : null;
}

// ---- tudo junto ------------------------------------------------------------------------------------------

export type Aviso = AvisoMinimo | AvisoDeficit | AvisoDado;

/** Os avisos de um ente, na ordem da página: mínimos, déficit e, por último, os do dado. */
export function avisosDe(ibge: number, esfera: Esfera): Aviso[] {
  const motivos = motivosDoDado(ibge, esfera);
  const deficit = avisoDeficit(ibge, esfera, motivos);
  const dado: AvisoDado | null = motivos.size
    ? { tipo: "dado", anos: [...motivos].sort(([a], [b]) => a - b).map(([ano, m]) => ({ ano, motivos: m })) }
    : null;
  return [...avisosMinimo(ibge, esfera), ...(deficit ? [deficit] : []), ...(dado ? [dado] : [])];
}
