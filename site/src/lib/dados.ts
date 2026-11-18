/** Leitura e agrupamento dos JSONs gerados pelo pipeline (pipeline/…/transformar.py). */

export type Dim = "orgao" | "uo" | "funcao" | "subfuncao" | "programa" | "acao" | "gnd";
export type Metrica = "inicial" | "atualizado" | "empenhado" | "realizado";

export const METRICAS: Metrica[] = ["inicial", "atualizado", "empenhado", "realizado"];

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
};

export const ROTULO_DIM_PLURAL: Record<Dim, string> = {
  orgao: "Órgãos",
  uo: "Unidades orçamentárias",
  funcao: "Funções",
  subfuncao: "Subfunções",
  programa: "Programas",
  acao: "Ações",
  gnd: "Grupos de despesa",
};

/** Caminhos de drill-down do Explorer. */
export const VISOES = {
  orgao: { rotulo: "Órgão", niveis: ["orgao", "uo", "programa", "acao"] as Dim[] },
  funcao: { rotulo: "Função", niveis: ["funcao", "subfuncao", "programa", "acao"] as Dim[] },
  gnd: { rotulo: "Natureza da despesa", niveis: ["gnd", "orgao", "uo", "acao"] as Dim[] },
} as const;
export type Visao = keyof typeof VISOES;

export interface DocAno {
  ano: number;
  gerado_em: string;
  fonte: string;
  colunas: string[];
  dims: Record<Dim, Record<string, string>>;
  linhas: (string | number)[][];
}

export interface ResumoAnos {
  gerado_em: string;
  anos: ({ ano: number; linhas: number } & Record<Metrica, number>)[];
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

/**
 * Filtra as linhas pelo caminho (um código por nível já escolhido) e agrupa
 * pelo próximo nível. Retorna o total do nó atual e os filhos.
 */
/** Subfunções de refinanciamento da dívida (rolagem: troca dívida velha por nova). */
export const SUBFUNCOES_REFINANCIAMENTO = new Set(["841", "842"]);

export function agrupar(doc: DocAno, niveis: Dim[], caminho: string[], semRefinanciamento = false) {
  const idx = (c: string) => doc.colunas.indexOf(c);
  const iNiveis = niveis.map(idx);
  const iVal = METRICAS.map(idx);
  const iSub = idx("subfuncao");
  const proximo = caminho.length < niveis.length ? niveis[caminho.length] : null;
  const iProx = proximo ? idx(proximo) : -1;

  const total = zero();
  const grupos = new Map<string, Valores>();

  for (const l of doc.linhas) {
    if (semRefinanciamento && SUBFUNCOES_REFINANCIAMENTO.has(l[iSub] as string)) continue;
    let ok = true;
    for (let k = 0; k < caminho.length; k++) {
      if (l[iNiveis[k]] !== caminho[k]) { ok = false; break; }
    }
    if (!ok) continue;
    let g: Valores | undefined;
    if (proximo) {
      const cod = l[iProx] as string;
      g = grupos.get(cod);
      if (!g) grupos.set(cod, (g = zero()));
    }
    METRICAS.forEach((m, j) => {
      const v = l[iVal[j]] as number;
      total[m] += v;
      if (g) g[m] += v;
    });
  }

  const filhos: Item[] = proximo
    ? [...grupos].map(([codigo, valores]) => ({
        codigo,
        nome: doc.dims[proximo][codigo] ?? codigo,
        valores,
      }))
    : [];

  return { total, filhos, proximo };
}

export function taxaRealizacao(v: Valores): number | null {
  return v.atualizado > 0 ? v.realizado / v.atualizado : null;
}

/** Faixa de cor 1–5 para a taxa de realização; 0 = sem dotação. */
export function faixa(taxa: number | null): number {
  if (taxa === null) return 0;
  if (taxa < 0.2) return 1;
  if (taxa < 0.4) return 2;
  if (taxa < 0.6) return 3;
  if (taxa < 0.8) return 4;
  return 5;
}

export const FAIXAS = ["sem dotação", "até 20%", "20–40%", "40–60%", "60–80%", "80% ou mais"];
