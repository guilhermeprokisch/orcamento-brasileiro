/**
 * O fundo de aposentadoria dos servidores (regime próprio de previdência) de cada prefeitura e estado,
 * lido no build de pipeline/…/previdencia.py (Índice de Situação Previdenciária do Ministério da
 * Previdência). Sem o arquivo, tudo vem null.
 */
import { docCidades } from "./cidades";

/** [nota, provisões, plano financeiro e Tesouro, dinheiro aplicado, RCL, ativos, aposentados, pensionistas, receita, despesa, ano do DRAA] */
type Linha = [string | null, number | null, number | null, number | null, number | null,
  number | null, number | null, number | null, number | null, number | null, number | null];
interface DocPrevidencia {
  fonte: string;
  versao: string;
  ano_draa: number | null;
  ano_contas: number | null;
  entes: Record<string, Linha>;
  extincao: number[];
  rgps: number[];
}
const arquivos = import.meta.glob<DocPrevidencia>("../../public/data/indicadores/previdencia.json", { eager: true, import: "default" });
const doc: DocPrevidencia | null = Object.values(arquivos)[0] ?? null;

export interface Fundo {
  tipo: "fundo";
  fonte: string;
  /** "ISP 2025, publicado em 04/12/2025" */
  versao: string;
  /** Ano do índice (2025). */
  anoIsp: number | null;
  nota: string | null;
  /** Quanto o fundo calcula que precisa ter hoje para pagar o que já prometeu (provisões matemáticas). */
  provisoes: number | null;
  /** A parte das provisões paga com o dinheiro de cada ano, sem fundo (plano financeiro e benefícios do Tesouro). */
  financeiro: number | null;
  /** O dinheiro aplicado pelo fundo. */
  aplicado: number | null;
  /** provisões − aplicado; negativo quando o dinheiro guardado cobre tudo. null sem avaliação ou com dados implausíveis. */
  falta: number | null;
  /** Receita corrente líquida (do ano das contas), quando plausível. */
  rcl: number | null;
  /** falta ÷ RCL: quantos anos de receita o rombo representa. */
  anos: number | null;
  /** Mediana de `anos` entre as cidades do mesmo porte com fundo próprio (ou entre os estados, sem o DF). */
  mediana: number | null;
  ativos: number | null;
  aposentados: number | null;
  pensionistas: number | null;
  /** O que entrou no fundo e o que saiu dele no ano das contas. */
  receita: number | null;
  despesa: number | null;
  /** Ano da avaliação atuarial usada (DRAA), e o ano das contas do índice. */
  anoDraa: number | null;
  anoContas: number | null;
  /** Quantos fundos o Ministério avaliou e quantos tiraram cada nota. */
  avaliados: number;
  porNota: Record<string, number>;
}
export type Previdencia = Fundo | { tipo: "extincao" | "inss" };

const popDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.pop]));
const faixaDe = new Map((docCidades?.cidades ?? []).map((c) => [String(c.ibge), c.faixa]));

/**
 * Como no gasto com pessoal: receita corrente líquida abaixo de R$ 1.500 por morador é declaração de parte
 * do ano. Dinheiro aplicado acima de três anos de receita é, quase sempre, erro de preenchimento.
 */
function contas(ibge: string, l: Linha): { falta: number | null; rcl: number | null; anos: number | null } {
  const [, provisoes, , aplicado, rclBruta] = l;
  const pop = popDe.get(ibge);
  const rcl = rclBruta && rclBruta > 0 && (ibge.length === 2 || !pop || rclBruta / pop >= 1500) ? rclBruta : null;
  if (provisoes === null || aplicado === null || (rclBruta && aplicado > 3 * rclBruta)) return { falta: null, rcl, anos: null };
  const falta = provisoes - aplicado;
  return { falta, rcl, anos: rcl ? falta / rcl : null };
}

function mediana(v: number[]): number | null {
  if (v.length < 10) return null;
  const s = [...v].sort((a, b) => a - b), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

const medianas = new Map<string, number | null>();
const porNota: Record<string, number> = {};
for (const v of Object.values(doc?.entes ?? {})) if (v[0]) porNota[v[0]] = (porNota[v[0]] ?? 0) + 1;

export function previdenciaDe(ibge: number, esfera: "mun" | "uf"): Previdencia | null {
  if (!doc) return null;
  const k = String(ibge);
  const l = doc.entes[k];
  if (!l) {
    if (esfera === "uf") return null;
    return { tipo: doc.extincao.includes(ibge) ? "extincao" : "inss" };
  }
  const { falta, rcl, anos } = contas(k, l);
  const grupo = esfera === "uf" ? "uf" : `faixa ${faixaDe.get(k)}`;
  if (!medianas.has(grupo)) {
    const pares = Object.entries(doc.entes)
      .filter(([x]) => (esfera === "uf" ? x.length === 2 && x !== "53" : x.length === 7 && faixaDe.get(x) === faixaDe.get(k)))
      .map(([x, v]) => contas(x, v).anos)
      .filter((a): a is number => a !== null);
    medianas.set(grupo, mediana(pares));
  }
  return {
    tipo: "fundo", fonte: doc.fonte, versao: doc.versao, anoIsp: Number(doc.versao.match(/\d{4}/)?.[0]) || null,
    nota: l[0], provisoes: l[1], financeiro: l[2], aplicado: l[3], falta, rcl, anos, mediana: medianas.get(grupo) ?? null,
    ativos: l[5], aposentados: l[6], pensionistas: l[7], receita: l[8], despesa: l[9],
    anoDraa: l[10], anoContas: doc.ano_contas, avaliados: Object.keys(doc.entes).length, porNota,
  };
}
