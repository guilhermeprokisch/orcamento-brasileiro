/** Leitura e agrupamento das receitas da União (pipeline/…/receitas_uniao.py). */

import type { Item, Rotulos, Valores } from "./dados";

export type DimR = "origem" | "especie" | "item" | "parcela" | "orgao" | "categoria";

export const DIMS_R: DimR[] = ["origem", "especie", "item", "parcela", "orgao", "categoria"];

/** Nome de cada nível no caminho ("Tipo · impostos"). */
export const ROTULO_DIM_R: Record<DimR, string> = {
  origem: "Tipo de receita",
  especie: "Subtipo",
  item: "Receita",
  parcela: "Parcela",
  orgao: "Órgão que arrecada",
  categoria: "Categoria",
};

/** Próximo nível sugerido depois de escolher um item de cada dimensão. */
const SUGESTAO: Record<DimR, DimR[]> = {
  origem: ["especie", "item"],
  especie: ["item"],
  item: ["parcela", "orgao"],
  parcela: ["orgao"],
  orgao: ["origem", "especie", "item"],
  categoria: ["origem"],
};

export interface Filtro {
  dim: DimR;
  cod: string;
}

export interface AnoReceitas {
  ano: number;
  ate: string | null;
  parcial: boolean;
  oficial: { fonte: string; realizado: number; previsto_inicial?: number; previsto_atualizado?: number } | null;
  linhas: (string | number)[][];
}

export interface DocReceitas {
  gerado_em: string;
  fonte: string;
  url: string;
  colunas: string[];
  dims: Record<DimR, Record<string, string>>;
  anos: AnoReceitas[];
}

export const ROTULOS_RECEITA: Rotulos = {
  atualizado: "Previsto",
  empenhado: null,
  realizado: "Arrecadado",
  taxa: "do previsto",
  colTrilho: "Arrecadado",
  colTaxa: "Do previsto",
  codigo: false, // os códigos das receitas são internos (calculados do nome)
};

/** O que é cada tipo de receita, em português simples. */
export const EXPLICA_ORIGEM: Record<string, string> = {
  impostos: "Imposto de renda, IPI, IOF, imposto de importação e algumas taxas. Uma parte vai para estados e municípios.",
  contribuicoes: "Contribuições ao INSS (de empresas e trabalhadores), Cofins, PIS e a contribuição sobre o lucro (CSLL). Pagam sobretudo a previdência, a saúde e a assistência social.",
  credito: "Dinheiro emprestado: o Tesouro vende títulos da dívida a bancos, fundos e pessoas. A maior parte serve para pagar títulos que estão vencendo.",
  patrimonial: "Rendimentos do que a União tem: royalties do petróleo e da mineração, dividendos das estatais, concessões e aluguéis.",
  "outras-capital": "Principalmente o rendimento do dinheiro do Tesouro guardado no Banco Central e o lucro do próprio Banco Central.",
  servicos: "Tarifas e serviços cobrados pela União, como navegação aérea, e juros de empréstimos que ela fez.",
  amortizacoes: "Empréstimos que a União fez (ao BNDES, a estados e municípios, ao Fies) e que estão sendo devolvidos.",
  "outras-correntes": "Multas, devolução de dinheiro de anos anteriores, indenizações e outras entradas.",
  industrial: "Venda do petróleo e do gás que cabem à União nos contratos de partilha do pré-sal.",
  alienacao: "Venda de bens e direitos da União (imóveis, ações, direitos de exploração).",
};

export function dimsDisponiveisR(filtros: Filtro[]): DimR[] {
  const usadas = new Set(filtros.map((f) => f.dim));
  return DIMS_R.filter((d) => !usadas.has(d));
}

export function proximaSugeridaR(filtros: Filtro[]): DimR | null {
  const livres = dimsDisponiveisR(filtros);
  const ultima = filtros.at(-1)?.dim;
  const preferidas = ultima ? SUGESTAO[ultima] : ["origem" as DimR];
  return preferidas.find((d) => livres.includes(d)) ?? livres[0] ?? null;
}

let cache: Promise<DocReceitas> | null = null;

export function carregarReceitas(): Promise<DocReceitas> {
  if (!cache) {
    cache = fetch("/data/receitas/uniao.json").then((r) => {
      if (!r.ok) throw new Error(`Não consegui carregar as receitas (HTTP ${r.status})`);
      return r.json();
    });
    cache.catch(() => (cache = null));
  }
  return cache;
}

const zero = (): Valores => ({ inicial: 0, atualizado: 0, empenhado: 0, realizado: 0 });

/**
 * Filtra as linhas de um ano e agrupa pela dimensão `por`. O previsto vai em `atualizado` e o
 * arrecadado em `realizado`, para os componentes do explorador de gastos servirem sem mudança.
 */
export function agruparR(doc: DocReceitas, ano: AnoReceitas, filtros: Filtro[], por: DimR | null, semRefin = false) {
  const idx = (c: string) => doc.colunas.indexOf(c);
  const iFiltros = filtros.map((f) => idx(f.dim));
  const iPrev = idx("previsto");
  const iReal = idx("realizado");
  const iRefin = idx("refin");
  const iPor = por ? idx(por) : -1;

  const total = zero();
  const grupos = new Map<string, Valores>();
  for (const l of ano.linhas) {
    if (semRefin && l[iRefin]) continue;
    let ok = true;
    for (let k = 0; k < filtros.length; k++) {
      if (l[iFiltros[k]] !== filtros[k].cod) { ok = false; break; }
    }
    if (!ok) continue;
    const p = l[iPrev] as number;
    const r = l[iReal] as number;
    total.atualizado += p;
    total.realizado += r;
    if (por) {
      const cod = l[iPor] as string;
      let g = grupos.get(cod);
      if (!g) grupos.set(cod, (g = zero()));
      g.atualizado += p;
      g.realizado += r;
    }
  }
  const itens: Item[] = por
    ? [...grupos].map(([codigo, valores]) => ({ codigo, nome: doc.dims[por][codigo] ?? codigo, valores }))
    : [];
  return { total, itens };
}

/** Soma do refinanciamento da dívida num ano (com os filtros aplicados). */
export function refinanciamento(doc: DocReceitas, ano: AnoReceitas, filtros: Filtro[]): number {
  const iRefin = doc.colunas.indexOf("refin");
  const iReal = doc.colunas.indexOf("realizado");
  const iFiltros = filtros.map((f) => doc.colunas.indexOf(f.dim));
  let s = 0;
  for (const l of ano.linhas) {
    if (!l[iRefin]) continue;
    if (filtros.every((f, k) => l[iFiltros[k]] === f.cod)) s += l[iReal] as number;
  }
  return s;
}

/** Dívida nova que não é refinanciamento (títulos vendidos para cobrir o déficit), num ano. */
export function creditoSemRefin(doc: DocReceitas, ano: AnoReceitas): number {
  const iOrig = doc.colunas.indexOf("origem");
  const iRefin = doc.colunas.indexOf("refin");
  const iReal = doc.colunas.indexOf("realizado");
  let s = 0;
  for (const l of ano.linhas) if (l[iOrig] === "credito" && !l[iRefin]) s += l[iReal] as number;
  return s;
}
