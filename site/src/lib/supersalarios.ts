/**
 * Juízes e promotores acima do teto, por órgão, lido no build de pipeline/…/supersalarios.py (DadosJusBr).
 * Só somas por órgão e período; nenhuma pessoa. Sem o arquivo, `docSuper` é null e as partes somem.
 */
import { docBase } from "./perfis";

/** Um órgão num período. Contagens de "um mês típico" (média dos meses com dado); valores somados no período. */
export interface Periodo {
  meses: string[];
  membros: number;
  /** null quando menos de 5 passam do teto num mês típico (não se mostra). */
  acima: number | null;
  parte: number | null;
  excesso: number | null;
  pago: number;
  mediana: number;
  grupos: Record<string, number>;
  /** [quantos passam do teto, quanto passa] somando uma família de rubricas por vez, na ordem de `grupos`. */
  camadas: [number, number][];
  /** Quantos passam do teto em cada faixa num mês típico (null: menos de 5). */
  faixas: (number | null)[] | null;
}
export type Tipo = "tj" | "mp" | "trabalho" | "federal" | "superior" | "militar";
export interface Orgao {
  nome: string;
  tipo: Tipo;
  uf: string | null;
  periodos: Record<string, Periodo | null>;
}
interface DocSuper {
  fonte: string;
  url: string;
  gerado: string;
  ultimo_mes: string;
  tetos: Record<string, number>;
  periodos: { id: string; rotulo: string; de: string; ate: string }[];
  grupos: [string, string][];
  faixas: number[];
  tipos: Record<Tipo, string>;
  orgaos: Record<string, Orgao>;
  /** mês -> tipo -> [órgãos, membros, acima do teto, quanto passou] */
  serie: Record<string, Record<string, [number, number, number, number]>>;
}

const arquivos = import.meta.glob<DocSuper>("../../public/data/indicadores/supersalarios.json", { eager: true, import: "default" });
export const docSuper: DocSuper | null = Object.values(arquivos)[0] ?? null;

export const ORDEM_TIPOS: Tipo[] = ["tj", "mp", "trabalho", "federal", "superior", "militar"];

/** Cor de cada família de rubricas: o subsídio em cinza; o que vem por cima, do verde ao amarelo. */
export const CORES_GRUPOS: Record<string, string> = {
  subsidio: "#ddd5c3",
  pessoais: "#b3dfc4",
  acumulo: "#1f7a47",
  ferias: "#74c193",
  retroativos: "#0a4a29",
  auxilios: "#ffe14d",
};
/** Nomes curtos para a legenda. */
export const NOMES_CURTOS: Record<string, string> = {
  subsidio: "Subsídio",
  pessoais: "Tempo de serviço e abono",
  acumulo: "Acúmulo, plantão e licença compensatória",
  ferias: "Férias e licenças vendidas",
  retroativos: "Atrasados e rubricas opacas",
  auxilios: "Auxílios",
};

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
/** "2026-09" -> "setembro de 2026" */
export const mesExtenso = (m: string) => `${MESES[Number(m.slice(5, 7)) - 1]} de ${m.slice(0, 4)}`;
/** "2026-09" -> "set/26" */
export const mesCurto = (m: string) => `${MESES_CURTOS[Number(m.slice(5, 7)) - 1]}/${m.slice(2, 4)}`;

/** "tjsp" -> "TJSP", "trt2" -> "TRT-2", "trf4" -> "TRF-4", "tjmmg" -> "TJM-MG" */
export function sigla(id: string): string {
  const s = id.toUpperCase();
  const num = s.match(/^(TRT|TRF)(\d+)$/);
  if (num) return `${num[1]}-${num[2]}`;
  const tjm = s.match(/^TJM(\w\w)$/);
  if (tjm) return `TJM-${tjm[1]}`;
  return s;
}

export interface Linha extends Periodo {
  id: string;
  sigla: string;
  nome: string;
  tipo: Tipo;
  uf: string | null;
  /** Quanto passa do teto, em média, por membro, num mês. */
  porMembro: number | null;
}

/** Os órgãos com dado no período, do que mais passou do teto ao que menos. */
export function linhas(periodo: string, tipo?: Tipo): Linha[] {
  if (!docSuper) return [];
  return Object.entries(docSuper.orgaos)
    .filter(([, o]) => (!tipo || o.tipo === tipo) && o.periodos[periodo])
    .map(([id, o]) => {
      const p = o.periodos[periodo]!;
      return {
        ...p, id, sigla: sigla(id), nome: o.nome, tipo: o.tipo, uf: o.uf,
        porMembro: p.excesso === null ? null : p.excesso / (p.membros * p.meses.length),
      };
    })
    .sort((a, b) => (b.excesso ?? -1) - (a.excesso ?? -1) || b.membros - a.membros);
}

export interface Total {
  orgaos: number;
  /** Membros num mês típico (soma dos órgãos). */
  membros: number;
  /** Acima do teto num mês típico. */
  acima: number;
  parte: number;
  /** Quanto passou do teto no período, somando os meses com dado de cada órgão. */
  excesso: number;
  /** Quanto passou do teto, por mês, em média: soma de (excesso ÷ meses) de cada órgão. */
  excessoMes: number;
  porMembro: number;
  pago: number;
  grupos: Record<string, number>;
  camadas: { grupo: string; parte: number; excessoMes: number }[];
  faixas: number[];
  mediana: number;
}

/** Soma de vários órgãos num período. Órgãos com menos de 5 acima do teto entram nos membros e no pago. */
export function total(ls: Linha[]): Total | null {
  if (!docSuper || ls.length === 0) return null;
  const membros = ls.reduce((t, l) => t + l.membros, 0);
  const acima = ls.reduce((t, l) => t + (l.acima ?? 0), 0);
  const excessoMes = ls.reduce((t, l) => t + (l.excesso ?? 0) / l.meses.length, 0);
  const grupos = Object.fromEntries(docSuper.grupos.map(([g]) => [g, ls.reduce((t, l) => t + (l.grupos[g] ?? 0) / l.meses.length, 0)]));
  const camadas = docSuper.grupos.map(([g], i) => ({
    grupo: g,
    parte: ls.reduce((t, l) => t + l.camadas[i][0], 0) / membros,
    excessoMes: ls.reduce((t, l) => t + l.camadas[i][1] / l.meses.length, 0),
  }));
  const nFaixas = docSuper.faixas.length + 1;
  const faixas = Array.from({ length: nFaixas }, (_, i) => ls.reduce((t, l) => t + (l.faixas?.[i] ?? 0), 0));
  // Mediana aproximada: a mediana do órgão, pesada pelo número de membros.
  const porMediana = [...ls].sort((a, b) => a.mediana - b.mediana);
  let acc = 0;
  const mediana = porMediana.find((l) => (acc += l.membros) >= membros / 2)?.mediana ?? 0;
  return {
    orgaos: ls.length, membros, acima, parte: acima / membros, excesso: ls.reduce((t, l) => t + (l.excesso ?? 0), 0),
    excessoMes, porMembro: excessoMes / membros, pago: ls.reduce((t, l) => t + l.pago / l.meses.length, 0),
    grupos, camadas, faixas, mediana,
  };
}

/** Os órgãos com dado nos dois períodos, para comparar antes e depois sem que a cobertura mude a conta. */
export function nosDois(a: string, b: string, tipo?: Tipo): [Linha[], Linha[]] {
  const la = linhas(a, tipo), lb = linhas(b, tipo);
  const ids = new Set(lb.map((l) => l.id));
  const comuns = new Set(la.filter((l) => ids.has(l.id)).map((l) => l.id));
  return [la.filter((l) => comuns.has(l.id)), lb.filter((l) => comuns.has(l.id))];
}

/** A série mês a mês, juntando os tipos pedidos: quantos membros, que parte passa do teto e quanto passa por membro. */
export function serie(tipos: Tipo[] = ORDEM_TIPOS) {
  if (!docSuper) return [];
  return Object.entries(docSuper.serie).map(([mes, por]) => {
    const soma = tipos.reduce((t, k) => {
      const x = por[k];
      return x ? [t[0] + x[0], t[1] + x[1], t[2] + x[2], t[3] + x[3]] : t;
    }, [0, 0, 0, 0]);
    return { mes, orgaos: soma[0], membros: soma[1], parte: soma[1] ? soma[2] / soma[1] : 0, porMembro: soma[1] ? soma[3] / soma[1] : 0 };
  }).filter((x) => x.membros > 0);
}

/** O tribunal de justiça e o Ministério Público de um estado. */
export function doEstado(uf: string): { id: string; o: Orgao }[] {
  if (!docSuper) return [];
  const u = uf.toUpperCase();
  return Object.entries(docSuper.orgaos)
    .filter(([id, o]) => o.uf === u && (o.tipo === "tj" || o.tipo === "mp") && !id.startsWith("tjm"))
    .sort(([, a], [, b]) => (a.tipo === "tj" ? -1 : 1) - (b.tipo === "tj" ? -1 : 1))
    .map(([id, o]) => ({ id, o }));
}

export const tetoAtual = () => (docSuper ? Object.values(docSuper.tetos).at(-1)! : 46366.19);

// ---------------------------------------------------------------------------------------------------
// Executivo federal: servidores civis (SIAPE), de pipeline/…/supersalarios_federal.py (Portal da Transparência).


export interface OrgaoFederal {
  nome: string;
  meses: number;
  servidores: number;
  acima: number | null;
  parte: number | null;
  excesso: number | null;
  pago: number;
  mediana: number;
  grupos: Record<string, number>;
  camadas: [number, number][];
  faixas: (number | null)[] | null;
}
interface DocFederal {
  fonte: string;
  url: string;
  gerado: string;
  de: string;
  ate: string;
  meses: number;
  grupos: [string, string][];
  faixas: number[];
  orgaos: Record<string, OrgaoFederal>;
  /** mês -> [servidores, acima do teto, quanto passou] */
  serie: Record<string, [number, number, number]>;
}
const arquivosFederal = import.meta.glob<DocFederal>("../../public/data/indicadores/supersalarios-federal.json", { eager: true, import: "default" });
export const docFederal: DocFederal | null = Object.values(arquivosFederal)[0] ?? null;

export const CORES_FEDERAL: Record<string, string> = { base: "#ddd5c3", eventuais: "#74c193", honorarios: "#0a4a29", indenizacoes: "#ffe14d" };
export const NOMES_FEDERAL: Record<string, string> = {
  base: "Salário", eventuais: "Pagamentos eventuais", honorarios: "Honorários e jetons", indenizacoes: "Auxílios e indenizações",
};

/** Nome sem acento, sem "- Administração Direta" e sem a sigla ou a UF no fim ("Universidade Federal Fluminense - RJ"). */
const normal = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/ - (administracao direta|orcamento fiscal.*)$/, "").replace(/ - [a-z]{2,12}$/, "")
    .replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
/** Órgãos que o SIAPE escreve abreviados ou com o nome antigo. */
const APELIDOS: Record<string, string> = {
  "min gestao e inov em serv publicos": "46000",
  "min desenv assis soci famil combate fome": "55000",
  "min desenvolv ind comercio e servicos": "28000",
  "min da integ e do desenv regional": "53000",
  "ministerio do meio ambiente": "44000",
  "min dos dir hum e da cidadania": "81000",
  "ministerio da ciencia tecnologia inovacoes e comunicacoes": "24000",
};

/** Nome do órgão de exercício no SIAPE -> código do órgão no orçamento (para a página /orgaos/[cod]). */
const codOrcamento = (() => {
  const mapa = new Map<string, string>(Object.entries(APELIDOS));
  if (!docBase) return mapa;
  for (const [cod, nome] of Object.entries(docBase.dims.uo)) mapa.set(normal(nome), `${cod.slice(0, 2)}000`);
  for (const [cod, nome] of Object.entries(docBase.dims.orgao)) mapa.set(normal(nome), cod);
  return mapa;
})();

const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e", "em"]);
/** "MINISTERIO DA FAZENDA" -> o nome do órgão no orçamento, se casar; senão, "Ministerio da Fazenda". */
function nomeLegivel(nome: string, orcamento: string | null): string {
  if (nome !== nome.toUpperCase()) return nome;
  const doOrcamento = orcamento && docBase?.dims.orgao[orcamento];
  if (doOrcamento) return doOrcamento;
  return nome.toLowerCase().split(" ").map((p, i) => (i > 0 && MINUSCULAS.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1))).join(" ");
}

export interface LinhaFederal extends OrgaoFederal {
  cod: string;
  /** Código do órgão no orçamento, quando o nome casa. */
  orcamento: string | null;
  porServidor: number | null;
}

/** Os órgãos do Executivo federal, do que mais passou do teto ao que menos. */
export function linhasFederal(): LinhaFederal[] {
  if (!docFederal) return [];
  return Object.entries(docFederal.orgaos)
    .map(([cod, o]) => {
      const orcamento = codOrcamento.get(normal(o.nome)) ?? null;
      return {
        ...o, cod, orcamento, nome: nomeLegivel(o.nome, orcamento),
        porServidor: o.excesso === null || o.acima === null ? null : o.excesso / (o.acima * o.meses),
      };
    })
    .sort((a, b) => (b.excesso ?? -1) - (a.excesso ?? -1) || b.servidores - a.servidores);
}

/** Soma do Executivo federal, por mês em média. */
export function totalFederal(ls: LinhaFederal[] = linhasFederal()) {
  if (!docFederal || !ls.length) return null;
  const n = docFederal.meses;
  const servidores = ls.reduce((t, l) => t + l.servidores, 0);
  const acima = ls.reduce((t, l) => t + (l.acima ?? 0), 0);
  const excesso = ls.reduce((t, l) => t + (l.excesso ?? 0), 0);
  const grupos = Object.fromEntries(docFederal.grupos.map(([g]) => [g, ls.reduce((t, l) => t + l.grupos[g] / l.meses, 0)]));
  const camadas = docFederal.grupos.map(([g], i) => ({
    grupo: g,
    acima: ls.reduce((t, l) => t + l.camadas[i][0], 0),
    excessoMes: ls.reduce((t, l) => t + l.camadas[i][1] / l.meses, 0),
  }));
  // Os grupos só dos que passam do teto não estão no arquivo; o que vem dos honorários sai das camadas.
  return { servidores, acima, parte: acima / servidores, excesso, excessoMes: excesso / n, grupos, camadas, meses: n };
}

/** "de julho a agosto de 2026" (ou com os dois anos, quando mudam). */
export function periodoFederal(): string {
  if (!docFederal) return "";
  const { de, ate } = docFederal;
  return de.slice(0, 4) === ate.slice(0, 4)
    ? `de ${mesExtenso(de).replace(/ de \d{4}$/, "")} a ${mesExtenso(ate)}`
    : `de ${mesExtenso(de)} a ${mesExtenso(ate)}`;
}

/** Os órgãos do SIAPE que casam com um órgão do orçamento. */
export const federalDoOrgao = (cod: string) => linhasFederal().filter((l) => l.orcamento === cod);
