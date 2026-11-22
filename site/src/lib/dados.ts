/** Leitura e agrupamento dos JSONs gerados pelo pipeline (pipeline/…/transformar.py). */

export type Dim = "orgao" | "uo" | "funcao" | "subfuncao" | "programa" | "acao" | "gnd" | "tipo";
export type Metrica = "inicial" | "atualizado" | "empenhado" | "realizado";

export const METRICAS: Metrica[] = ["inicial", "atualizado", "empenhado", "realizado"];
/** "tipo" (obrigatória, escolha do governo…) fica por último: só existe nos arquivos com o SIOP. */
export const DIMS: Dim[] = ["orgao", "funcao", "gnd", "uo", "subfuncao", "programa", "acao", "tipo"];

export const ROTULO_METRICA: Record<Metrica, string> = {
  inicial: "Dotação inicial",
  atualizado: "Dotação atualizada",
  empenhado: "Empenhado",
  realizado: "Realizado",
};

export const ROTULO_DIM: Record<Dim, string> = {
  orgao: "Órgão",
  uo: "Unidade orçamentária",
  funcao: "Função",
  subfuncao: "Subfunção",
  programa: "Programa",
  acao: "Ação",
  gnd: "Grupo de despesa",
  tipo: "Tipo de despesa",
};

/** "um órgão", "uma função"… usado em "Você escolheu … Um órgão". */
export const ARTIGO_DIM: Record<Dim, string> = {
  orgao: "Um órgão",
  uo: "Uma unidade orçamentária",
  funcao: "Uma função",
  subfuncao: "Uma subfunção",
  programa: "Um programa",
  acao: "Uma ação",
  gnd: "Um grupo de despesa",
  tipo: "Um tipo de despesa",
};

/** Próximo nível sugerido depois de escolher um item de cada dimensão. */
const SUGESTAO: Record<Dim, Dim[]> = {
  orgao: ["uo", "programa", "acao"],
  uo: ["programa", "acao"],
  funcao: ["subfuncao", "programa", "acao"],
  subfuncao: ["programa", "acao"],
  programa: ["acao"],
  acao: ["gnd", "uo"],
  gnd: ["orgao", "uo", "acao"],
  tipo: ["orgao", "programa", "acao"],
};

export interface Filtro {
  dim: Dim;
  cod: string;
}

export function dimsDisponiveis(filtros: Filtro[]): Dim[] {
  const usadas = new Set(filtros.map((f) => f.dim));
  return DIMS.filter((d) => !usadas.has(d));
}

/**
 * Tipo de despesa pelo identificador de resultado primário do SIOP (coluna "tipo", ver pipeline/…/transformar.py).
 * Cores como em /contas: obrigatórias em verde, o que o governo escolhe em amarelo.
 */
export const TIPOS_DESPESA = [
  { cod: "obr", nome: "Obrigatória", cor: "#1f7a47" },
  { cod: "esc", nome: "Escolha do governo", cor: "#ffe14d" },
  { cod: "eme", nome: "Emendas parlamentares", cor: "#d9822b" },
  { cod: "fin", nome: "Financeira (dívida)", cor: "#c3bba7" },
  { cod: "sem", nome: "Sem informação", cor: "#e9e4d8" },
] as const;

/** O arquivo do ano tem a coluna de tipo de despesa? (os gerados antes do SIOP não têm) */
export const temTipo = (doc: DocAno | undefined | null) => !!doc?.colunas.includes("tipo");

export function proximaSugerida(filtros: Filtro[]): Dim | null {
  const livres = dimsDisponiveis(filtros);
  const ultima = filtros.at(-1)?.dim;
  const preferidas = ultima ? SUGESTAO[ultima] : ["orgao" as Dim];
  return preferidas.find((d) => livres.includes(d)) ?? livres[0] ?? null;
}

export interface DocAno {
  ano: number;
  gerado_em: string;
  fonte: string;
  colunas: string[];
  dims: Record<Dim, Record<string, string>>;
  linhas: (string | number)[][];
}

export interface Ipca {
  base: number;
  metodo: string;
  fonte: string;
  ultimo_mes: string;
  fatores: Record<string, number>;
}

export interface ResumoAnos {
  gerado_em: string;
  anos: ({ ano: number; linhas: number } & Record<Metrica, number>)[];
  ipca?: Ipca | null;
}

export type Valores = Record<Metrica, number>;

export interface Item {
  codigo: string;
  nome: string;
  valores: Valores;
}

const cache = new Map<number, Promise<DocAno>>();

export function carregarAno(ano: number): Promise<DocAno> {
  let p = cache.get(ano);
  if (!p) {
    p = fetch(`/data/explorer/${ano}.json`).then((r) => {
      if (!r.ok) throw new Error(`Não consegui carregar ${ano} (HTTP ${r.status})`);
      return r.json();
    });
    p.catch(() => cache.delete(ano));
    cache.set(ano, p);
  }
  return p;
}

export async function carregarResumo(): Promise<ResumoAnos> {
  const r = await fetch("/data/explorer/anos.json");
  if (!r.ok) throw new Error(`Não consegui carregar a lista de anos (HTTP ${r.status})`);
  return r.json();
}

const zero = (): Valores => ({ inicial: 0, atualizado: 0, empenhado: 0, realizado: 0 });

/** Subfunções de refinanciamento da dívida (rolagem: troca dívida velha por nova). */
export const SUBFUNCOES_REFINANCIAMENTO = new Set(["841", "842"]);

/**
 * Aplica os filtros (um código por dimensão já escolhida) e agrupa pela
 * dimensão `por`. Retorna o total filtrado e os grupos.
 */
export function agrupar(doc: DocAno, filtros: Filtro[], por: Dim | null, semRefinanciamento = false) {
  const idx = (c: string) => doc.colunas.indexOf(c);
  const iFiltros = filtros.map((f) => idx(f.dim));
  const iVal = METRICAS.map(idx);
  const iSub = idx("subfuncao");
  const iPor = por ? idx(por) : -1;

  const total = zero();
  const grupos = new Map<string, Valores>();

  for (const l of doc.linhas) {
    if (semRefinanciamento && SUBFUNCOES_REFINANCIAMENTO.has(l[iSub] as string)) continue;
    let ok = true;
    for (let k = 0; k < filtros.length; k++) {
      if (l[iFiltros[k]] !== filtros[k].cod) { ok = false; break; }
    }
    if (!ok) continue;
    let g: Valores | undefined;
    if (por) {
      const cod = l[iPor] as string;
      g = grupos.get(cod);
      if (!g) grupos.set(cod, (g = zero()));
    }
    METRICAS.forEach((m, j) => {
      const v = l[iVal[j]] as number;
      total[m] += v;
      if (g) g[m] += v;
    });
  }

  const itens: Item[] = por
    ? [...grupos].map(([codigo, valores]) => ({
        codigo,
        nome: doc.dims[por]?.[codigo] ?? codigo,
        valores,
      }))
    : [];

  return { total, itens };
}

/** Total de cada passo da trilha (filtros[0..i]). */
export function totaisDaTrilha(doc: DocAno, filtros: Filtro[], m: Metrica, semRefin: boolean): number[] {
  return filtros.map((_, i) => agrupar(doc, filtros.slice(0, i + 1), null, semRefin).total[m]);
}

export function escalar(v: Valores, fator: number): Valores {
  if (fator === 1) return v;
  return {
    inicial: v.inicial * fator,
    atualizado: v.atualizado * fator,
    empenhado: v.empenhado * fator,
    realizado: v.realizado * fator,
  };
}

/** Nomes dos valores nos componentes do explorador (mapa, lista e barras), para servirem a gastos e receitas. */
export interface Rotulos {
  atualizado: string;
  empenhado: string | null; // null: não mostra
  realizado: string;
  /** depois da porcentagem no bloco: "42% pago" */
  taxa: string;
  /** cabeçalhos da lista */
  colTrilho: string;
  colTaxa: string;
  /** mostra o código ao lado do nome na lista (padrão: sim) */
  codigo?: boolean;
  /** só há o valor realizado (emendas: o pago): sem a coluna de taxa na lista e sem o previsto no balão */
  soRealizado?: boolean;
}

export const ROTULOS_DESPESA: Rotulos = {
  atualizado: "Dotação atualizada", empenhado: "Empenhado", realizado: "Pago",
  taxa: "pago", colTrilho: "Dotação", colTaxa: "Pago",
};

export function taxaRealizacao(v: Valores): number | null {
  return v.atualizado > 0 ? v.realizado / v.atualizado : null;
}
