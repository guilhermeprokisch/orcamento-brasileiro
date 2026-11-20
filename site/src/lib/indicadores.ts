/**
 * Indicadores de resultado para pôr ao lado do gasto. Por enquanto, o Ideb por município e
 * rede (pipeline/…/ideb.py). Lido no build; sem o arquivo, tudo vem null.
 */
import { docCidades, docEstados, type Cidade } from "./cidades";
import { nomeAutor } from "./autores-emendas";

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
  /** As mesmas notas como série, e a mediana das cidades do mesmo porte em cada edição (só rede municipal). */
  serie: PontoSerie[];
  referencia: PontoSerie[];
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

// Mediana da nota da rede municipal em cada faixa de população, numa edição (padrão: a mais recente).
const medianas = new Map<string, number | null>();
function medianaDaFaixa(faixa: number, serie: Serie, i = -1): number | null {
  const chave = `${faixa}-${serie}-${i}`;
  if (!medianas.has(chave)) {
    const notas = (docCidades?.cidades ?? [])
      .filter((c) => c.faixa === faixa && c.ibge !== 53)
      .map((c) => doc?.mun[String(c.ibge)]?.[serie]?.at(i))
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
  const comparar = serie.startsWith("m") && c.faixa !== undefined;
  const referencia: PontoSerie[] = comparar
    ? doc.anos.map((ano, i) => ({ ano, valor: medianaDaFaixa(c.faixa!, serie, i), preliminar: false }))
      .filter((p): p is PontoSerie => p.valor !== null && historico.some(([a]) => a === p.ano))
    : [];
  return {
    nota: atual,
    antes: ultimo ? { ano: ultimo[0], nota: ultimo[1] } : null,
    mediana: comparar ? medianaDaFaixa(c.faixa!, serie) : null,
    historico,
    serie: historico.map(([ano, valor]) => ({ ano, valor, preliminar: false })),
    referencia,
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
  /** Ano em que o número deve estar subcontado (ex.: mais mortes violentas sem causa do que homicídios). */
  marca?: boolean;
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
  /** Homicídios ano a ano: por 100 mil habitantes quando há a população do ano, senão o número de mortes. */
  serie: PontoSerie[];
  serieEmTaxa: boolean;
  /** A taxa do Brasil ano a ano (vazia sem a população). */
  serieBrasil: PontoSerie[];
}

// População de cada ano (IBGE, pipeline/…/populacao.py): ano → código do estado ou ibge → pessoas.
const arquivosPopulacao = import.meta.glob<{ fonte: string; anos: Record<string, Record<string, number>> }>("../../public/data/indicadores/populacao.json", { eager: true, import: "default" });
const docPopulacao = Object.values(arquivosPopulacao)[0] ?? null;

/** A seção de homicídios aparece nas cidades a partir deste tamanho (os números menores oscilam demais). */
export const POP_HOMICIDIOS = 100_000;

/** A série de um ente, em taxa quando todo ano tem população, e a do Brasil. */
function serieHomicidios(porAno: Record<string, Record<string, [number, number, number]>>, id: string) {
  const anos = Object.keys(porAno).sort();
  const pops = docPopulacao?.anos ?? {};
  const emTaxa = anos.every((a) => pops[a]?.[id]);
  const serie = anos.map((a) => {
    const y = porAno[a][id];
    const n = y ? y[0] + y[1] : 0;
    // Mais mortes violentas sem causa definida do que homicídios: parte deles não foi contada.
    return { ano: Number(a), valor: emTaxa ? (n / pops[a][id]) * 1e5 : n, preliminar: false, marca: !!y && y[2] > n };
  });
  const serieBrasil = !emTaxa ? [] : anos.flatMap((a) => {
    let n = 0, p = 0;
    for (const [uf, y] of Object.entries(docSeguranca!.anos[a] ?? {})) if (pops[a]?.[uf]) { n += y[0] + y[1]; p += pops[a][uf]; }
    return p ? [{ ano: Number(a), valor: (n / p) * 1e5, preliminar: false }] : [];
  });
  return { serie, serieEmTaxa: emTaxa, serieBrasil };
}

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
  // A população do mesmo ano dos homicídios, quando o IBGE tem; senão, a da base do site.
  const popDoAno = (x: Cidade) => docPopulacao?.anos[ano]?.[String(x.ibge)] ?? x.pop;
  const taxas = comparaveis.map((x) => { const y = doAno[String(x.ibge)]; return por100mil(y ? y[0] + y[1] : 0, popDoAno(x)); });
  let n = 0, p = 0;
  for (const x of docEstados.cidades) { const y = docSeguranca.anos[ano]?.[String(x.ibge)]; if (y) { n += y[0] + y[1]; p += popDoAno(x); } }
  return {
    fonte: docSeguranca.fonte, ano: Number(ano), homicidios: v[0] + v[1], policia: v[1], indeterminadas: v[2],
    taxa: por100mil(v[0] + v[1], popDoAno(e)), taxaIndeterminadas: por100mil(v[2], popDoAno(e)),
    mediana: mediana(taxas), brasil: p ? por100mil(n, p) : null,
    ...serieHomicidios(porAno, String(e.ibge)),
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
  /** Mediana por morador das cidades do mesmo porte. */
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

// ----- Para o mapa: os quatro números de "Como está a cidade", de cada cidade e estado -----

export interface SituacaoDoMapa {
  /** medida → { ano (texto), fonte, mun: ibge → valor, uf: código → valor, brasil } ; valor null = sem dado comparável */
  [medida: string]: { ano: string; fonte: string; mun: Record<string, number | null>; uf: Record<string, number | null>; brasil: number | null };
}

/** Mortalidade infantil (por mil, 2 anos), homicídios (por 100 mil), água e esgoto na rede (fração). */
export function situacaoParaMapa(): SituacaoDoMapa {
  const r1 = (v: number) => Math.round(v * 10) / 10;
  const r3 = (v: number) => Math.round(v * 1000) / 1000;
  const out: SituacaoDoMapa = {};
  if (docSaude) {
    const t = (v?: [number, number]) => (v && v[0] >= NASCIDOS_MINIMO ? r1((v[1] / v[0]) * 1000) : null);
    const br = Object.values(docSaude.uf).reduce((s, x) => [s[0] + x[0], s[1] + x[1]], [0, 0]);
    out.mort = {
      ano: docSaude.anos.join(" e "), fonte: docSaude.fonte,
      mun: Object.fromEntries(Object.entries(docSaude.mun).map(([k, v]) => [k, t(v)])),
      uf: Object.fromEntries(Object.entries(docSaude.uf).map(([k, v]) => [k, t(v)])),
      brasil: br[0] ? r1((br[1] / br[0]) * 1000) : null,
    };
  }
  const ano = docSeguranca ? Object.keys(docSeguranca.anos).sort().at(-1) : undefined;
  const pops = ano ? docPopulacao?.anos[ano] : undefined;
  if (docSeguranca && ano && pops) {
    const taxa = (y: [number, number, number] | undefined, p: number) => r1((((y?.[0] ?? 0) + (y?.[1] ?? 0)) / p) * 1e5);
    const uf: Record<string, number | null> = {}, mun: Record<string, number | null> = {};
    let n = 0, p = 0;
    for (const [k, pop] of Object.entries(pops)) {
      if (k.length === 2) {
        const y = docSeguranca.anos[ano][k];
        uf[k] = taxa(y, pop);
        if (y) { n += y[0] + y[1]; p += pop; }
      } else if (docSeguranca.mun?.[ano]) mun[k] = taxa(docSeguranca.mun[ano][k], pop);
    }
    out.hom = { ano, fonte: docSeguranca.fonte, mun, uf, brasil: p ? r1((n / p) * 1e5) : null };
  }
  if (docSaneamento) {
    for (const [medida, i] of [["agua", 1], ["esgoto", 2]] as const) {
      const br = Object.values(docSaneamento.uf).reduce((s, x) => [s[0] + x[0], s[1] + x[i]], [0, 0]);
      out[medida] = {
        ano: String(docSaneamento.ano), fonte: docSaneamento.fonte,
        mun: Object.fromEntries(Object.entries(docSaneamento.mun).map(([k, v]) => [k, v[0] ? r3(v[i] / v[0]) : null])),
        uf: Object.fromEntries(Object.entries(docSaneamento.uf).map(([k, v]) => [k, v[0] ? r3(v[i] / v[0]) : null])),
        brasil: br[0] ? r3(br[1] / br[0]) : null,
      };
    }
  }
  return out;
}

// ----- Emendas parlamentares que chegaram (CGU, pipeline/…/emendas.py) -----

interface DocEmendas {
  fonte: string;
  anos: number[];
  /** ibge → ano → [total, prefeitura, entidades e empresas, estado e outros] */
  mun: Record<string, Record<string, [number, number, number, number]>>;
  uf: Record<string, Record<string, [number, number, number, number]>>;
  autores: Record<string, Record<string, [string, number][]>>;
  areas: Record<string, Record<string, [string, number][]>>;
}
const arquivosEmendas = import.meta.glob<DocEmendas>("../../public/data/indicadores/emendas.json", { eager: true, import: "default" });
const docEmendas: DocEmendas | null = Object.values(arquivosEmendas)[0] ?? null;

export interface Emendas {
  fonte: string;
  ano: number;
  total: number;
  prefeitura: number;
  entidades: number;
  estadoEOutros: number;
  porHab: number;
  /** Mediana por morador das cidades do mesmo porte (ou dos estados). */
  mediana: number | null;
  autores: [string, number][];
  areas: [string, number][];
  /** Total por ano, em R$ milhões; o ano corrente marcado como preliminar. */
  serie: PontoSerie[];
}

export function emendasDe(c: Cidade, esfera: "mun" | "uf"): Emendas | null {
  if (!docEmendas || !c.pop) return null;
  const porAno = docEmendas[esfera][String(c.ibge)];
  if (!porAno) return null;
  const anoAtual = new Date().getFullYear();
  // O último ano fechado: o ano corrente ainda está em andamento.
  const ano = docEmendas.anos.filter((a) => a < anoAtual).at(-1);
  if (!ano) return null;
  // Na cidade, o total deixa de fora os órgãos estaduais e federais com sede nela (quase sempre a
  // capital): eles atendem o estado inteiro e já contam na página do estado.
  const totalDe = (x: number[] | undefined) => (!x ? 0 : esfera === "mun" ? x[1] + x[2] : x[0]);
  const v = porAno[String(ano)] ?? [0, 0, 0, 0];
  const comparaveis = esfera === "uf"
    ? (docEstados?.cidades ?? []).filter((x) => x.ibge !== 53)
    : (docCidades?.cidades ?? []).filter((x) => x.faixa === c.faixa);
  const valores = comparaveis.filter((x) => x.pop).map((x) => totalDe(docEmendas[esfera][String(x.ibge)]?.[String(ano)]) / x.pop);
  return {
    fonte: docEmendas.fonte, ano, total: totalDe(v), prefeitura: v[1], entidades: v[2], estadoEOutros: v[3],
    porHab: totalDe(v) / c.pop, mediana: mediana(valores),
    autores: docEmendas.autores[String(c.ibge)]?.[String(ano)] ?? [],
    areas: docEmendas.areas[String(c.ibge)]?.[String(ano)] ?? [],
    serie: docEmendas.anos.map((a) => ({ ano: a, valor: totalDe(porAno[String(a)]) / 1e6, preliminar: a >= anoAtual })),
  };
}

/** As emendas pagas na cidade em cada ano: [à prefeitura, a entidades e empresas]. Fora o DF. */
export function emendasPorAno(c: Cidade): Record<string, [number, number]> | undefined {
  const porAno = c.ibge === 53 ? undefined : docEmendas?.mun[String(c.ibge)];
  if (!porAno) return undefined;
  return Object.fromEntries(Object.entries(porAno).map(([a, v]) => [a, [v[1], v[2]] as [number, number]]));
}

/**
 * Para o mapa (/data/mapa/emendas.json): as emendas do último ano fechado de cada cidade e estado,
 * [total, prefeitura, entidades e empresas, estado e outros, por morador], e os 3 maiores autores.
 */
export function emendasParaMapa() {
  if (!docEmendas) return null;
  const ano = docEmendas.anos.filter((a) => a < new Date().getFullYear()).at(-1);
  if (!ano) return null;
  const a = String(ano);
  const pop = new Map([...(docCidades?.cidades ?? []), ...(docEstados?.cidades ?? [])].map((x) => [String(x.ibge), x.pop]));
  const linhas = (esfera: "mun" | "uf") => Object.fromEntries(Object.entries(docEmendas[esfera])
    .filter(([k, v]) => v[a] && pop.get(k))
    .map(([k, v]) => {
      // Cidade: sem os órgãos estaduais e federais com sede nela (ver emendasDe).
      const x = esfera === "mun" ? [v[a][1] + v[a][2], v[a][1], v[a][2], 0] : v[a];
      return [k, [...x, Math.round((x[0] / pop.get(k)!) * 100) / 100]];
    }));
  // Os nomes dos autores vão uma vez só, numa lista; cada lugar guarda [índice do nome, valor].
  const nomesAutores: string[] = [], indice = new Map<string, number>();
  const idx = (n: string) => { if (!indice.has(n)) { indice.set(n, nomesAutores.length); nomesAutores.push(nomeAutor(n)); } return indice.get(n)!; };
  const autores = Object.fromEntries(Object.entries(docEmendas.autores)
    .map(([k, v]) => [k, (v[a] ?? []).slice(0, 3).map(([n, valor]) => [idx(n), valor])])
    .filter(([, v]) => v.length));
  return { ano, fonte: docEmendas.fonte, mun: linhas("mun"), uf: linhas("uf"), nomesAutores, autores };
}

// Contratos das prefeituras publicados no PNCP (pipeline/…/contratos.py), no ano da assinatura.
interface ContratosCidade {
  n: number;
  total: number;
  /** valor por tipo, na ordem de DocContratos.tipos */
  tipos: number[];
  /** [objeto, valor, empresa (null para pessoa física ou MEI)] */
  maiores: [string, number, string | null][];
  /** [nome, valor, contratos] */
  empresas: [string, number, number][];
  pessoas: number;
  /** [contratos, valor] com valor maior que todo o gasto da prefeitura no ano: erro de digitação */
  fora: [number, number];
}
interface DocContratos { fonte: string; ano: number; tipos: string[]; mun: Record<string, ContratosCidade>; uf?: Record<string, ContratosCidade> }
const arquivosContratos = import.meta.glob<DocContratos>("../../public/data/indicadores/contratos.json", { eager: true, import: "default" });
const docContratos: DocContratos | null = Object.values(arquivosContratos)[0] ?? null;

export interface Contratos extends ContratosCidade {
  fonte: string;
  ano: number;
  porHab: number;
  /** [tipo, valor], do maior para o menor, sem os vazios */
  porTipo: [string, number][];
}

/** Os contratos da prefeitura (mun) ou dos órgãos estaduais (uf), no ano da assinatura. */
export function contratosDe(c: Cidade, esfera: "mun" | "uf" = "mun"): Contratos | null {
  const v = docContratos?.[esfera]?.[String(c.ibge)];
  if (!docContratos || !v || !c.pop) return null;
  const porTipo = docContratos.tipos.map((t, i) => [t, v.tipos[i] ?? 0] as [string, number])
    .filter(([, x]) => x > 0).sort((a, b) => b[1] - a[1]);
  return { ...v, fonte: docContratos.fonte, ano: docContratos.ano, porHab: v.total / c.pop, porTipo };
}

// Escolas da rede municipal (pipeline/…/escolas.py): Censo Escolar, Ideb por escola e PDDE.
interface DocEscolas {
  fonte: string;
  censo: number;
  ideb: number;
  pdde: number;
  /** escolas: [código INEP, nome, bairro, alunos, Ideb iniciais, Ideb finais, PDDE]; pdde: [total, conselhos, casado] */
  mun: Record<string, { escolas: [string, string, string, number, number | null, number | null, number | null][]; estaduais: number; pdde: [number, number, number] }>;
}
const arquivosEscolas = import.meta.glob<DocEscolas>("../../public/data/indicadores/escolas.json", { eager: true, import: "default" });
const docEscolas: DocEscolas | null = Object.values(arquivosEscolas)[0] ?? null;

export interface Escola { inep: string; nome: string; bairro: string; alunos: number; ideb: [number | null, number | null]; pdde: number | null }
export interface Escolas {
  fonte: string; censo: number; edicaoIdeb: number; anoPdde: number;
  escolas: Escola[]; alunos: number; estaduais: number;
  pdde: { total: number; conselhos: number; casado: number };
}

export function escolasDe(c: Cidade): Escolas | null {
  const v = docEscolas?.mun[String(c.ibge)];
  if (!docEscolas || !v) return null;
  const escolas = v.escolas.map(([inep, nome, bairro, alunos, i, f, pdde]) => ({ inep, nome, bairro, alunos, ideb: [i, f] as [number | null, number | null], pdde }));
  return {
    fonte: docEscolas.fonte, censo: docEscolas.censo, edicaoIdeb: docEscolas.ideb, anoPdde: docEscolas.pdde,
    escolas, alunos: escolas.reduce((s, e) => s + e.alunos, 0), estaduais: v.estaduais,
    pdde: { total: v.pdde[0], conselhos: v.pdde[1], casado: v.pdde[2] },
  };
}

// Postos, UPAs e hospitais (pipeline/…/unidades_saude.py): CNES, internações do SIH/SUS e atendimentos do SIA/SUS.
interface DocUnidadesSaude {
  fonte: string;
  ano: number;
  cnes: string;
  /** unidades: [CNES, nome, grupo, bairro, atendimentos, exames, cirurgias, valor]; hospitais: [CNES, nome, quem administra, internações, valor, bairro] */
  mun: Record<string, { unidades: [string, string, string, string, number?, number?, number?, number?][]; hospitais: [string, string, string, number, number, string][] }>;
}
const arquivosUnidades = import.meta.glob<DocUnidadesSaude>("../../public/data/indicadores/unidades-saude.json", { eager: true, import: "default" });
const docUnidades: DocUnidadesSaude | null = Object.values(arquivosUnidades)[0] ?? null;

export interface UnidadesSaude {
  fonte: string; ano: number; mesCnes: string;
  /** atendimentos, exames e cirurgias sem internação no ano, e o valor pago pela tabela do SUS (SIA) */
  unidades: { cnes: string; nome: string; grupo: string; bairro: string; atendimentos: number; exames: number; cirurgias: number; valor: number }[];
  porGrupo: [string, number][];
  hospitais: { cnes: string; nome: string; quem: string; internacoes: number; valor: number; bairro: string }[];
}

export function unidadesSaudeDe(c: Cidade): UnidadesSaude | null {
  const v = docUnidades?.mun[String(c.ibge)];
  if (!docUnidades || !v) return null;
  // Primeiro o que a pessoa mais procura: o posto, a urgência, o hospital.
  const ORDEM = ["Posto ou unidade básica", "Urgência", "Hospital", "Especialidades", "Saúde mental (CAPS)", "Exames", "Vacinação", "Atenção domiciliar", "Vigilância em saúde", "Academia da saúde"];
  const ordem = (g: string) => (ORDEM.indexOf(g) + 1 || 99);
  const unidades = v.unidades.map(([cnes, nome, grupo, bairro, atendimentos = 0, exames = 0, cirurgias = 0, valor = 0]) => ({ cnes, nome, grupo, bairro, atendimentos, exames, cirurgias, valor }))
    .sort((x, y) => ordem(x.grupo) - ordem(y.grupo) || x.nome.localeCompare(y.nome, "pt-BR"));
  const conta = new Map<string, number>();
  for (const u of unidades) conta.set(u.grupo, (conta.get(u.grupo) ?? 0) + 1);
  return {
    fonte: docUnidades.fonte, ano: docUnidades.ano, mesCnes: docUnidades.cnes,
    unidades, porGrupo: [...conta].sort((a, b) => b[1] - a[1]),
    hospitais: v.hospitais.map(([cnes, nome, quem, internacoes, valor, bairro]) => ({ cnes, nome, quem, internacoes, valor, bairro })),
  };
}
