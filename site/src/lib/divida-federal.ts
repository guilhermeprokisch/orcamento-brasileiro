/**
 * Dívida pública federal (página /divida), lida no build de pipeline/…/divida_federal.py:
 * o anexo do Relatório Mensal da Dívida do Tesouro e séries do Banco Central. Sem o arquivo, tudo vem null.
 */
import { docs } from "./perfis";
import { agrupar } from "./dados";

export interface DocDividaFederal {
  fonte: string;
  rmd: { mes: string; arquivo: string; url: string; titulo: string };
  /** "2014-01" … mês do último RMD */
  meses: string[];
  /** Estoque da dívida pública federal em poder do público, R$ bilhões */
  dpf: (number | null)[];
  /** PIB acumulado em 12 meses, R$ bilhões */
  pib12: (number | null)[];
  /** Dívida bruta do governo geral, R$ bilhões e % do PIB */
  dbgg: (number | null)[];
  dbgg_pib: (number | null)[];
  indexador: Record<"prefixado" | "inflacao" | "selic" | "cambio" | "demais", (number | null)[]>;
  detentores: Record<"bancos" | "fundos" | "previdencia" | "estrangeiros" | "tesouro_direto" | "governo" | "seguradoras" | "outros" | "total", (number | null)[]>;
  vence_12m: (number | null)[];
  prazo_medio: (number | null)[];
  custo_medio: (number | null)[];
  /** ano → [juros nominais do governo federal no ano, R$ bilhões; % do PIB] */
  juros: Record<string, [number, number | null]>;
  juros_12m: { ate: string; valor: number | null; pib: number | null };
  /** ano → [títulos vendidos menos pagos, juros e correções somados à dívida, operações com o Banco Central], R$ bilhões */
  fatores?: Record<string, [number, number, number]>;
  /** último mês somado em "fatores" (o ano em andamento vai até ele) */
  fatores_ate?: string;
}

const arquivos = import.meta.glob<DocDividaFederal>("../../public/data/federal/divida.json", { eager: true, import: "default" });
export const docDivida: DocDividaFederal | null = Object.values(arquivos)[0] ?? null;

const NOMES_MES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
/** "2026-09" → "setembro de 2026" */
export const mesExtenso = (m: string) => `${NOMES_MES[Number(m.slice(5)) - 1]} de ${m.slice(0, 4)}`;
/** "2026-09" → "set/2026" */
export const mesCurto = (m: string) => `${ABREV[Number(m.slice(5)) - 1]}/${m.slice(0, 4)}`;

/** Um ponto da série: o fim de cada ano e, se o último mês não for dezembro, ele também. */
export interface Ponto {
  i: number;
  mes: string;
  /** "2019" para dezembro; "set/2026" para o último mês */
  rotulo: string;
  fimDeAno: boolean;
}

export function pontos(d: DocDividaFederal): Ponto[] {
  const saida: Ponto[] = [];
  d.meses.forEach((mes, i) => {
    const ultimo = i === d.meses.length - 1;
    if (mes.endsWith("-12")) saida.push({ i, mes, rotulo: mes.slice(0, 4), fimDeAno: true });
    else if (ultimo) saida.push({ i, mes, rotulo: mesCurto(mes), fimDeAno: false });
  });
  return saida;
}

/** O último mês com o estoque da dívida. */
export function ultimoMes(d: DocDividaFederal): number {
  let i = d.meses.length - 1;
  while (i > 0 && d.dpf[i] === null) i--;
  return i;
}

export const DETENTORES = [
  { chave: "bancos", nome: "Bancos", o: "os bancos", de: "dos bancos", cor: "#0a4a29", explica: "bancos privados e públicos, inclusive o BNDES, corretoras e cooperativas de crédito" },
  { chave: "fundos", nome: "Fundos de investimento", o: "os fundos de investimento", de: "dos fundos de investimento", cor: "#1f7a47", explica: "os fundos onde as pessoas e as empresas aplicam" },
  { chave: "previdencia", nome: "Previdência", o: "a previdência", de: "da previdência", cor: "#4fae73", explica: "fundos de pensão, previdência privada e os regimes próprios dos servidores" },
  { chave: "estrangeiros", nome: "Estrangeiros", o: "os estrangeiros", de: "dos estrangeiros", cor: "#ffe14d", explica: "pessoas, fundos e empresas de fora do país" },
  { chave: "seguradoras", nome: "Seguradoras", o: "as seguradoras", de: "das seguradoras", cor: "#8fcea8", explica: "seguradoras e resseguradoras" },
  { chave: "tesouro_direto", nome: "Tesouro Direto", o: "as pessoas pelo Tesouro Direto", de: "das pessoas pelo Tesouro Direto", cor: "#b3dfc4", explica: "pessoas que compram títulos pela internet" },
  { chave: "governo", nome: "Fundos do governo", o: "os fundos do governo", de: "dos fundos do governo", cor: "#c3bba7", explica: "fundos administrados pela União, como o FAT e o FGTS" },
  { chave: "outros", nome: "Outros", o: "outros", de: "dos outros", cor: "#ddd5c3", explica: "contas de pessoas físicas em corretoras, empresas de capitalização e outros" },
] as const;

export const INDEXADORES = [
  { chave: "selic", nome: "Selic", cor: "#0a4a29", explica: "os juros acompanham a Selic, a taxa básica do Banco Central, dia a dia" },
  { chave: "inflacao", nome: "Inflação", cor: "#4fae73", explica: "os juros são a inflação (IPCA) mais uma taxa combinada na venda" },
  { chave: "prefixado", nome: "Juros fixos", cor: "#b3dfc4", explica: "a taxa é combinada na venda e não muda até o vencimento" },
  { chave: "cambio", nome: "Dólar e outras moedas", cor: "#ffe14d", explica: "a dívida é em dólar ou euro e cresce quando o real se desvaloriza" },
] as const;

/** Fatias (0 a 1) de cada grupo num mês; o denominador é o total do grupo (detentores) ou da dívida (indexadores). */
export function fatias<K extends string>(series: Record<K, (number | null)[]>, chaves: readonly K[], total: number, i: number): Record<K, number> {
  return Object.fromEntries(chaves.map((k) => [k, (series[k][i] ?? 0) / total])) as Record<K, number>;
}

/** Gasto pago (realizado) de um ano no orçamento federal: juros da dívida, saúde e educação, em reais. */
export function gastoNoOrcamento(ano: number): { juros: number; saude: number; educacao: number } | null {
  const doc = docs.find((d) => d.ano === ano);
  if (!doc) return null;
  const pago = (dim: "gnd" | "funcao", cod: string) => agrupar(doc, [{ dim, cod }], null).total.realizado;
  return { juros: pago("gnd", "2"), saude: pago("funcao", "10"), educacao: pago("funcao", "12") };
}
