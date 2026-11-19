/**
 * Indicadores de resultado para pôr ao lado do gasto. Por enquanto, o Ideb por município e
 * rede (pipeline/…/ideb.py). Lido no build; sem o arquivo, tudo vem null.
 */
import { docCidades, docEstados, type Cidade } from "./cidades";

interface DocIdeb {
  edicao: number;
  fonte: string;
  anos: number[];
  /** mi/mf = rede municipal, anos iniciais/finais; ei/ef = rede estadual. Uma nota por ano. */
  mun: Record<string, Partial<Record<"mi" | "mf" | "ei" | "ef", (number | null)[]>>>;
}

const arquivos = import.meta.glob<DocIdeb>("../../public/data/indicadores/ideb.json", { eager: true, import: "default" });
const doc: DocIdeb | null = Object.values(arquivos)[0] ?? null;

export type Serie = "mi" | "mf" | "ei" | "ef";

export interface NotaIdeb {
  /** Nota da edição mais recente; null se a rede não teve nota nela. */
  nota: number | null;
  /** Nota da edição anterior com valor, e o ano dela. */
  antes: { ano: number; nota: number } | null;
  /** Mediana da mesma nota entre as cidades do mesmo porte (só para a rede municipal). */
  mediana: number | null;
  /** [ano, nota] das edições com valor. */
  historico: [number, number][];
}

export interface Ideb {
  edicao: number;
  fonte: string;
  mi: NotaIdeb | null;
  mf: NotaIdeb | null;
  ei: NotaIdeb | null;
  ef: NotaIdeb | null;
}

function mediana(v: number[]): number | null {
  if (v.length < 10) return null;
  const o = [...v].sort((a, b) => a - b);
  const m = o.length >> 1;
  return o.length % 2 ? o[m] : (o[m - 1] + o[m]) / 2;
}

// Mediana da nota mais recente da rede municipal em cada faixa de população.
const medianas = new Map<string, number | null>();
function medianaDaFaixa(faixa: number, serie: Serie): number | null {
  const chave = `${faixa}-${serie}`;
  if (!medianas.has(chave)) {
    const notas = (docCidades?.cidades ?? [])
      .filter((c) => c.faixa === faixa && c.ibge !== 53)
      .map((c) => doc?.mun[String(c.ibge)]?.[serie]?.at(-1))
      .filter((n): n is number => typeof n === "number");
    medianas.set(chave, mediana(notas));
  }
  return medianas.get(chave)!;
}

function nota(c: Cidade, serie: Serie): NotaIdeb | null {
  const valores = doc?.mun[String(c.ibge)]?.[serie];
  if (!doc || !valores) return null;
  const historico = valores.map((n, i) => [doc.anos[i], n] as const).filter((x): x is [number, number] => x[1] !== null);
  if (!historico.length) return null;
  const atual = valores.at(-1) ?? null;
  const anteriores = historico.filter(([ano]) => ano < doc.edicao);
  const ultimo = anteriores.at(-1);
  return {
    nota: atual,
    antes: ultimo ? { ano: ultimo[0], nota: ultimo[1] } : null,
    mediana: serie.startsWith("m") && c.faixa !== undefined ? medianaDaFaixa(c.faixa, serie) : null,
    historico,
  };
}

/** Ideb das redes municipal e estadual no município; null se não há nenhuma nota. */
export function idebDe(c: Cidade): Ideb | null {
  if (!doc || c.ibge === 53) return null;
  const r = { edicao: doc.edicao, fonte: doc.fonte, mi: nota(c, "mi"), mf: nota(c, "mf"), ei: nota(c, "ei"), ef: nota(c, "ef") };
  return r.mi || r.mf || r.ei || r.ef ? r : null;
}

// ----- Matrículas (Censo Escolar, pipeline/…/matriculas.py) -----

interface DocMatriculas {
  fonte: string;
  /** ano → ibge → [rede municipal, rede estadual] */
  anos: Record<string, Record<string, [number, number]>>;
}
const arquivosMatriculas = import.meta.glob<DocMatriculas>("../../public/data/indicadores/matriculas.json", { eager: true, import: "default" });
const docMatriculas: DocMatriculas | null = Object.values(arquivosMatriculas)[0] ?? null;

/** Gasto da prefeitura em educação por aluno da rede municipal, no ano das contas da cidade. */
export interface PorAluno {
  ano: number;
  fonte: string;
  alunos: number;
  porAluno: number;
  /** Mediana entre as cidades do mesmo porte, no mesmo ano; null com menos de 10 cidades. */
  mediana: number | null;
}

const gastoPorAluno = (c: Cidade): number | null => {
  const alunos = c.ano !== null ? docMatriculas?.anos[String(c.ano)]?.[String(c.ibge)]?.[0] : undefined;
  const gasto = c.f?.["12"]?.[0] ?? 0;
  return alunos && alunos > 0 && gasto > 0 ? gasto / alunos : null;
};
const medianasPorAluno = new Map<string, number | null>();
function medianaPorAluno(faixa: number, ano: number): number | null {
  const chave = `${faixa}-${ano}`;
  if (!medianasPorAluno.has(chave)) {
    const valores = (docCidades?.cidades ?? [])
      .filter((c) => c.faixa === faixa && c.ano === ano && c.ibge !== 53)
      .map(gastoPorAluno)
      .filter((v): v is number => v !== null);
    medianasPorAluno.set(chave, mediana(valores));
  }
  return medianasPorAluno.get(chave)!;
}

export function porAlunoDe(c: Cidade): PorAluno | null {
  const porAluno = gastoPorAluno(c);
  if (!docMatriculas || porAluno === null || c.ano === null) return null;
  return {
    ano: c.ano, fonte: docMatriculas.fonte, alunos: docMatriculas.anos[String(c.ano)][String(c.ibge)][0], porAluno,
    mediana: c.faixa !== undefined ? medianaPorAluno(c.faixa, c.ano) : null,
  };
}

/** Gasto do governo estadual em educação básica por aluno das escolas estaduais, no ano das contas do estado. */
export interface PorAlunoEstado {
  ano: number;
  fonte: string;
  alunos: number;
  porAluno: number;
  /** Gasto com universidades estaduais (subfunção Ensino Superior), que fica de fora da conta. */
  superior: number;
  /** Gasto em educação sem as universidades. */
  basica: number;
  /** Mediana dos 26 estados (sem o DF) no mesmo ano. */
  mediana: number | null;
  /** Posição entre os 27 (1 = quem mais gasta por aluno) e quantos entraram na conta. */
  posicao: number;
  de: number;
}

function contaEstado(e: Cidade): { alunos: number; basica: number; superior: number } | null {
  const alunosPorUf = e.ano !== null ? docMatriculas?.anos[String(e.ano)] : undefined;
  if (!alunosPorUf) return null;
  const uf = String(e.ibge);
  let alunos = 0;
  for (const [ibge, [, estadual]] of Object.entries(alunosPorUf)) if (ibge.startsWith(uf)) alunos += estadual;
  const total = e.f?.["12"]?.[0] ?? 0, superior = e.s?.["12.364"] ?? 0;
  return alunos > 0 && total > superior ? { alunos, basica: total - superior, superior } : null;
}

export function porAlunoEstado(e: Cidade, estados: Cidade[]): PorAlunoEstado | null {
  const conta = contaEstado(e);
  if (!conta || !docMatriculas || e.ano === null) return null;
  const doAno = estados.filter((x) => x.ano === e.ano)
    .map((x) => ({ x, c: contaEstado(x) }))
    .filter((v): v is { x: Cidade; c: NonNullable<ReturnType<typeof contaEstado>> } => v.c !== null)
    .map(({ x, c }) => ({ ibge: x.ibge, v: c.basica / c.alunos }));
  const ordem = [...doAno].sort((a, b) => b.v - a.v);
  return {
    ano: e.ano, fonte: docMatriculas.fonte, alunos: conta.alunos, porAluno: conta.basica / conta.alunos,
    superior: conta.superior, basica: conta.basica,
    mediana: mediana(doAno.filter((v) => v.ibge !== 53).map((v) => v.v)),
    posicao: ordem.findIndex((v) => v.ibge === e.ibge) + 1, de: ordem.length,
  };
}

// ----- Mortalidade infantil (DATASUS, pipeline/…/saude.py) -----

interface DocSaude {
  fonte: string;
  /** ano → {mun: ibge → [nascidos vivos, óbitos infantis], uf: código do estado → [...]} */
  anos: Record<string, { mun: Record<string, [number, number]>; uf: Record<string, [number, number]> }>;
}
const arquivosSaude = import.meta.glob<DocSaude>("../../public/data/indicadores/saude.json", { eager: true, import: "default" });
const docSaudeAnual: DocSaude | null = Object.values(arquivosSaude)[0] ?? null;
const anosSaude = docSaudeAnual ? Object.keys(docSaudeAnual.anos).sort() : [];
/** Os dois últimos anos, somados: o que a página compara. */
const ultimosSaude = anosSaude.slice(-2);
function somar(esfera: "mun" | "uf"): Record<string, [number, number]> {
  const soma: Record<string, [number, number]> = {};
  for (const ano of ultimosSaude) {
    for (const [k, v] of Object.entries(docSaudeAnual!.anos[ano][esfera])) {
      const s = (soma[k] ??= [0, 0]);
      s[0] += v[0];
      s[1] += v[1];
    }
  }
  return soma;
}
const docSaude = docSaudeAnual
  ? { fonte: docSaudeAnual.fonte, anos: ultimosSaude.map(Number), mun: somar("mun"), uf: somar("uf") }
  : null;

/** Uma série ano a ano só é mostrada quando todo ano tem pelo menos isto de nascimentos. */
export const NASCIDOS_SERIE = 1000;

export interface PontoSerie {
  ano: number;
  valor: number;
  /** Os dois anos mais recentes do DATASUS ainda são preliminares. */
  preliminar: boolean;
}

/** Abaixo disso, a taxa oscila demais de um ano para outro e não é comparada. */
export const NASCIDOS_MINIMO = 100;

export interface Mortalidade {
  fonte: string;
  anos: number[];
  nascidos: number;
  obitos: number;
  /** Óbitos antes de 1 ano por mil nascidos vivos; null com poucos nascimentos. */
  taxa: number | null;
  /** Mediana dos comparáveis (cidades do mesmo porte ou estados) e a taxa do Brasil. */
  mediana: number | null;
  brasil: number | null;
  /** Mortes antes de 1 ano por mil nascidos, ano a ano (vazia em cidades pequenas), e a do Brasil. */
  serie: PontoSerie[];
  serieBrasil: PontoSerie[];
}

const taxa = (v?: [number, number]) => (v && v[0] >= NASCIDOS_MINIMO ? (v[1] / v[0]) * 1000 : null);
const medianasSaude = new Map<string, number | null>();

export function mortalidadeDe(c: Cidade, esfera: "mun" | "uf"): Mortalidade | null {
  if (!docSaude) return null;
  const v = docSaude[esfera][String(c.ibge)];
  if (!v || !v[0]) return null;
  const chave = esfera === "uf" ? "uf" : `mun-${c.faixa}`;
  if (!medianasSaude.has(chave)) {
    const taxas = esfera === "uf"
      ? Object.entries(docSaude.uf).filter(([k]) => k !== "53").map(([, x]) => taxa(x))
      : (docCidades?.cidades ?? []).filter((x) => x.faixa === c.faixa && x.ibge !== 53).map((x) => taxa(docSaude.mun[String(x.ibge)]));
    medianasSaude.set(chave, mediana(taxas.filter((t): t is number => t !== null)));
  }
  const total = Object.values(docSaude.uf).reduce((s, x) => [s[0] + x[0], s[1] + x[1]], [0, 0]);
  const preliminar = (ano: string) => ultimosSaude.includes(ano);
  const doEnte = anosSaude.map((ano) => ({ ano, v: docSaudeAnual!.anos[ano][esfera][String(c.ibge)] }));
  const serie = doEnte.every((x) => x.v && x.v[0] >= NASCIDOS_SERIE)
    ? doEnte.map(({ ano, v }) => ({ ano: Number(ano), valor: (v![1] / v![0]) * 1000, preliminar: preliminar(ano) }))
    : [];
  const serieBrasil = anosSaude.map((ano) => {
    const t = Object.values(docSaudeAnual!.anos[ano].uf).reduce((s, x) => [s[0] + x[0], s[1] + x[1]], [0, 0]);
    return { ano: Number(ano), valor: (t[1] / t[0]) * 1000, preliminar: preliminar(ano) };
  });
  return {
    fonte: docSaude.fonte, anos: docSaude.anos, nascidos: v[0], obitos: v[1], taxa: taxa(v),
    mediana: medianasSaude.get(chave)!, brasil: total[0] ? (total[1] / total[0]) * 1000 : null, serie, serieBrasil,
  };
}

// ----- Homicídios por estado (DATASUS, pipeline/…/seguranca.py) -----

interface DocSeguranca {
  fonte: string;
  /** ano → código do estado → [agressões, intervenções legais, intenção indeterminada] */
  anos: Record<string, Record<string, [number, number, number]>>;
  /** ano → ibge → [mesmo formato], só cidades com mais de 50 mil habitantes */
  mun?: Record<string, Record<string, [number, number, number]>>;
}
const arquivosSeguranca = import.meta.glob<DocSeguranca>("../../public/data/indicadores/seguranca.json", { eager: true, import: "default" });
const docSeguranca: DocSeguranca | null = Object.values(arquivosSeguranca)[0] ?? null;

export interface Homicidios {
  fonte: string;
  ano: number;
  homicidios: number;
  policia: number;
  indeterminadas: number;
  /** Por 100 mil habitantes: o estado, a mediana dos estados e o Brasil. */
  taxa: number;
  taxaIndeterminadas: number;
  mediana: number | null;
  brasil: number | null;
  /** Homicídios (número de mortes) ano a ano. */
  serie: PontoSerie[];
}

/** A seção de homicídios aparece nas cidades a partir deste tamanho (os números menores oscilam demais). */
export const POP_HOMICIDIOS = 100_000;

/** Os números do último ano fechado; a população é a do ente na base do site. */
export function homicidiosDe(e: Cidade, esfera: "uf" | "mun" = "uf"): Homicidios | null {
  if (!docSeguranca || !docEstados) return null;
  const porAno = esfera === "uf" ? docSeguranca.anos : docSeguranca.mun ?? {};
  const ano = Object.keys(porAno).sort().at(-1);
  if (!ano || (esfera === "mun" && e.pop < POP_HOMICIDIOS)) return null;
  const doAno = porAno[ano];
  const v = doAno[String(e.ibge)] ?? (esfera === "mun" ? [0, 0, 0] as [number, number, number] : undefined);
  if (!v || !e.pop) return null;
  const por100mil = (n: number, p: number) => (n / p) * 1e5;
  // Comparação: os outros estados (sem o DF) ou as cidades do mesmo porte com a seção.
  const comparaveis = esfera === "uf"
    ? docEstados.cidades.filter((x) => x.ibge !== 53)
    : (docCidades?.cidades ?? []).filter((x) => x.faixa === e.faixa && x.pop >= POP_HOMICIDIOS);
  const taxas = comparaveis.map((x) => { const y = doAno[String(x.ibge)]; return por100mil(y ? y[0] + y[1] : 0, x.pop); });
  let n = 0, p = 0;
  for (const x of docEstados.cidades) { const y = docSeguranca.anos[ano]?.[String(x.ibge)]; if (y) { n += y[0] + y[1]; p += x.pop; } }
  return {
    fonte: docSeguranca.fonte, ano: Number(ano), homicidios: v[0] + v[1], policia: v[1], indeterminadas: v[2],
    taxa: por100mil(v[0] + v[1], e.pop), taxaIndeterminadas: por100mil(v[2], e.pop),
    mediana: mediana(taxas), brasil: p ? por100mil(n, p) : null,
    serie: Object.keys(porAno).sort().map((a) => {
      const y = porAno[a][String(e.ibge)];
      return { ano: Number(a), valor: y ? y[0] + y[1] : 0, preliminar: false };
    }),
  };
}

// ----- Água e esgoto (IBGE, Censo 2022, pipeline/…/saneamento.py) -----

interface DocSaneamento {
  fonte: string;
  ano: number;
  /** ibge (ou código do estado) → [moradores, com água da rede, com esgoto na rede] */
  mun: Record<string, [number, number, number]>;
  uf: Record<string, [number, number, number]>;
}
const arquivosSaneamento = import.meta.glob<DocSaneamento>("../../public/data/indicadores/saneamento.json", { eager: true, import: "default" });
const docSaneamento: DocSaneamento | null = Object.values(arquivosSaneamento)[0] ?? null;

export interface Saneamento {
  fonte: string;
  ano: number;
  moradores: number;
  /** Partes dos moradores (0 a 1). */
  agua: number;
  esgoto: number;
  /** Medianas dos comparáveis (cidades do mesmo porte ou estados) e o Brasil. */
  medianaAgua: number | null;
  medianaEsgoto: number | null;
  brasilAgua: number;
  brasilEsgoto: number;
}
const medianasSaneamento = new Map<string, [number | null, number | null]>();

export function saneamentoDe(c: Cidade, esfera: "mun" | "uf"): Saneamento | null {
  const doc = docSaneamento;
  if (!doc) return null;
  const v = doc[esfera][String(c.ibge)];
  if (!v || !v[0]) return null;
  const chave = esfera === "uf" ? "uf" : `mun-${c.faixa}`;
  if (!medianasSaneamento.has(chave)) {
    const linhas = esfera === "uf"
      ? Object.entries(doc.uf).filter(([k]) => k !== "53").map(([, x]) => x)
      : (docCidades?.cidades ?? []).filter((x) => x.faixa === c.faixa).map((x) => doc.mun[String(x.ibge)]).filter(Boolean);
    medianasSaneamento.set(chave, [mediana(linhas.map((x) => x[1] / x[0])), mediana(linhas.map((x) => x[2] / x[0]))]);
  }
  const [medianaAgua, medianaEsgoto] = medianasSaneamento.get(chave)!;
  const br = Object.values(doc.uf).reduce((s, x) => [s[0] + x[0], s[1] + x[1], s[2] + x[2]], [0, 0, 0]);
  return {
    fonte: doc.fonte, ano: doc.ano, moradores: v[0], agua: v[1] / v[0], esgoto: v[2] / v[0],
    medianaAgua, medianaEsgoto, brasilAgua: br[1] / br[0], brasilEsgoto: br[2] / br[0],
  };
}

// ----- Imposto de renda pela cidade onde a pessoa mora (Receita, pipeline/…/irpf.py) -----

interface DocIrpf {
  fonte: string;
  /** ano-calendário → ibge → [declarantes, imposto devido] */
  anos: Record<string, Record<string, [number, number]>>;
}
const arquivosIrpf = import.meta.glob<DocIrpf>("../../public/data/mapa/irpf-res.json", { eager: true, import: "default" });
const docIrpf: DocIrpf | null = Object.values(arquivosIrpf)[0] ?? null;

export interface IrMoradores {
  fonte: string;
  ano: number;
  declarantes: number;
  valor: number;
  porHab: number;
  /** Mediana por habitante das cidades do mesmo porte. */
  mediana: number | null;
}
const medianasIr = new Map<string, number | null>();

/** As cidades somadas por estado: código do estado → [declarantes, imposto devido]. */
function irPorEstado(ano: string): Record<string, [number, number]> {
  const soma: Record<string, [number, number]> = {};
  for (const [ibge, v] of Object.entries(docIrpf!.anos[ano])) {
    const s = (soma[ibge.slice(0, 2)] ??= [0, 0]);
    s[0] += v[0];
    s[1] += v[1];
  }
  return soma;
}

export function irMoradoresDe(c: Cidade, esfera: "mun" | "uf" = "mun"): IrMoradores | null {
  if (!docIrpf || !c.pop) return null;
  const ano = Object.keys(docIrpf.anos).sort().at(-1);
  if (!ano) return null;
  if (esfera === "uf") {
    const porUf = irPorEstado(ano);
    const v = porUf[String(c.ibge)];
    if (!v) return null;
    const pop = new Map((docEstados?.cidades ?? []).map((x) => [String(x.ibge), x.pop]));
    const valores = Object.entries(porUf).filter(([k]) => k !== "53" && pop.get(k)).map(([k, x]) => x[1] / pop.get(k)!);
    return { fonte: docIrpf.fonte, ano: Number(ano), declarantes: v[0], valor: v[1], porHab: v[1] / c.pop, mediana: mediana(valores) };
  }
  const v = docIrpf.anos[ano][String(c.ibge)];
  if (!v) return null;
  const chave = `${ano}-${c.faixa}`;
  if (!medianasIr.has(chave)) {
    const doAno = docIrpf.anos[ano];
    const valores = (docCidades?.cidades ?? [])
      .filter((x) => x.faixa === c.faixa && x.pop && doAno[String(x.ibge)])
      .map((x) => doAno[String(x.ibge)][1] / x.pop);
    medianasIr.set(chave, mediana(valores));
  }
  return { fonte: docIrpf.fonte, ano: Number(ano), declarantes: v[0], valor: v[1], porHab: v[1] / c.pop, mediana: medianasIr.get(chave)! };
}
