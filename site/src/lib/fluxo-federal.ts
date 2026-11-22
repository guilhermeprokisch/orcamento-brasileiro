/**
 * Quando o dinheiro sai (seção #quando de /contas), lido no build de pipeline/…/fluxo.py:
 * execução da despesa federal mês a mês (Portal da Transparência), com as três etapas do gasto
 * separadas e os restos a pagar, classificada por tipo de despesa pelo resultado primário do SIOP.
 * Sem o arquivo, vem null.
 *
 * Cuidado que vale para todo cálculo daqui: `pago` é pagamento de empenho do próprio exercício e
 * `rap_pagos` é desembolso de compromisso de anos anteriores. As duas colunas não se sobrepõem —
 * somam-se para dar o desembolso do mês. Quem tratar as duas como gasto do ano conta duas vezes.
 */

/** As seis colunas de valor do arquivo mensal da CGU, em reais. */
export interface Etapas {
  empenhado: number;
  liquidado: number;
  pago: number;
  /** Praticamente zero no próprio ano: a inscrição é registrada no arquivo do ano seguinte. */
  rap_inscritos: number;
  rap_cancelados: number;
  rap_pagos: number;
}

export interface DocFluxo {
  ano: number;
  fonte: string;
  atualizado_em: string;
  sem_refinanciamento: boolean;
  observacao: string;
  /** "obr" | "esc" | "eme" | "fin" | "sem" → nome no site */
  tipos: Record<string, string>;
  /** "2025-01" → tipo → etapas */
  por_tipo: Record<string, Record<string, Etapas>>;
  /** "2025-01" → grupo de natureza de despesa → etapas */
  por_grupo: Record<string, Record<string, Etapas>>;
}

const arquivos = import.meta.glob<DocFluxo>("../../public/data/federal/fluxo-*.json", { eager: true, import: "default" });
/** O ano mais recente que o pipeline gerou. */
export const docFluxo: DocFluxo | null =
  Object.values(arquivos).sort((a, b) => b.ano - a.ano)[0] ?? null;

const ZERO: Etapas = { empenhado: 0, liquidado: 0, pago: 0, rap_inscritos: 0, rap_cancelados: 0, rap_pagos: 0 };

export const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** Os meses do arquivo, em ordem. */
export function meses(doc: DocFluxo): string[] {
  return Object.keys(doc.por_tipo).sort();
}

export const MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** "2025-03" → "março" */
export function mesLongo(competencia: string): string {
  return MESES_LONGOS[Number(competencia.slice(5, 7)) - 1] ?? competencia;
}

/** "2025-03" → "mar" */
export function mesCurto(competencia: string): string {
  return MESES_CURTOS[Number(competencia.slice(5, 7)) - 1] ?? competencia;
}

function soma(a: Etapas, b: Etapas | undefined): Etapas {
  if (!b) return a;
  return {
    empenhado: a.empenhado + b.empenhado,
    liquidado: a.liquidado + b.liquidado,
    pago: a.pago + b.pago,
    rap_inscritos: a.rap_inscritos + b.rap_inscritos,
    rap_cancelados: a.rap_cancelados + b.rap_cancelados,
    rap_pagos: a.rap_pagos + b.rap_pagos,
  };
}

/** Soma do ano de uma chave (um tipo de despesa ou um grupo); chave ausente devolve zeros. */
export function doAno(serie: Record<string, Record<string, Etapas>>, chave: string): Etapas {
  return Object.values(serie).reduce((t, mes) => soma(t, mes[chave]), { ...ZERO });
}

/** A série mensal de uma chave, na ordem dos meses. */
export function porMes(serie: Record<string, Record<string, Etapas>>, chave: string): { competencia: string; etapas: Etapas }[] {
  return Object.keys(serie).sort().map((competencia) => ({
    competencia,
    etapas: serie[competencia][chave] ?? { ...ZERO },
  }));
}

/** O que saiu do caixa: pagamento do próprio ano mais pagamento de restos a pagar. */
export function desembolso(e: Etapas): number {
  return e.pago + e.rap_pagos;
}

/** A parte do desembolso que pagou empenho de anos anteriores, de 0 a 1. */
export function contaVelha(e: Etapas): number {
  const total = desembolso(e);
  return total > 0 ? e.rap_pagos / total : 0;
}
