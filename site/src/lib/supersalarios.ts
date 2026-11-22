/**
 * Juízes e promotores acima do teto, por órgão, lido no build de pipeline/…/supersalarios.py (DadosJusBr).
 * Só somas por órgão e período; nenhuma pessoa. Sem o arquivo, `docSuper` é null e as partes somem.
 */
import { docBase } from "./perfis";
import { docCidades, docEstados, type Cidade } from "./cidades";
import { porAlunoDe, porAlunoEstado } from "./indicadores";

/** Um órgão num período. Contagens de "um mês típico" (média dos meses com dado); valores somados no período. */
export interface Periodo {
  meses: string[];
  membros: number;
  /** Quantos passam do teto num mês típico (a mediana dos meses); null quando são menos de 5 (não se mostra). */
  acima: number | null;
  parte: number | null;
  /** Meses do período com pelo menos 5 acima do teto. */
  meses_acima: number;
  /** Soma do período; null quando nenhum mês teve 5 ou mais acima do teto. */
  excesso: number | null;
  pago: number;
  mediana: number;
  grupos: Record<string, number>;
  /** [quantos passam do teto, quanto passa] somando uma família de rubricas por vez, na ordem de `grupos`. */
  camadas: [number, number][];
  /** Quantos passam do teto em cada faixa num mês típico (null: menos de 5). */
  faixas: (number | null)[] | null;
  /** Imposto de renda descontado no período e o que seria descontado se tudo fosse salário (null sem o desconto no arquivo). */
  ir: number | null;
  ir_salario: number | null;
  previdencia: number | null;
  meses_ir: number;
}
export type Tipo = "tj" | "mp" | "trabalho" | "federal" | "superior" | "militar";
export interface Orgao {
  nome: string;
  tipo: Tipo;
  uf: string | null;
  /** De quem é o orçamento que paga (e o imposto de renda descontado). */
  pagador: "estado" | "uniao";
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

export const ORDEM_TIPOS: Tipo[] = ["tj", "mp", "trabalho", "federal", "militar"];

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
  pagador: "estado" | "uniao";
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
        ...p, id, sigla: sigla(id), nome: o.nome, tipo: o.tipo, uf: o.uf, pagador: o.pagador,
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

// O imposto de renda que deixa de entrar. O que um estado desconta dos seus juízes e promotores é dele
// (Constituição, art. 157, I) e entra na base dos mínimos de educação (25%) e saúde (12%). O que a União
// desconta é repartido: metade do imposto de renda vai para o FPM (25,5%), o FPE (21,5%) e os fundos
// regionais (3%) (art. 159, I).
export const MINIMO_EDUCACAO = 0.25;
export const MINIMO_SAUDE = 0.12;
export const PARTE_FPM = 0.255;
export const PARTE_FPE = 0.215;
export const PARTE_FUNDOS = 0.03;

export interface Imposto {
  orgaos: number;
  /** Membros (num mês típico) dos órgãos com o desconto do IR no arquivo. */
  membros: number;
  /** Membros de todos os órgãos daquele pagador, para dizer quanto a conta cobre. */
  membrosTodos: number;
  ir: number;
  irSalario: number;
  /** O que deixa de ser descontado: irSalario − ir. */
  diferenca: number;
  /** O que passou do teto, nos órgãos daquele pagador (todos). */
  excesso: number;
}

/** O imposto de renda descontado e o que seria descontado se tudo fosse salário, por pagador, num período. */
export function imposto(periodo: string, ls?: Linha[]): Record<"estado" | "uniao", Imposto> {
  const todas = ls ?? linhas(periodo);
  const soma = (pag: "estado" | "uniao"): Imposto => {
    const daqui = todas.filter((l) => l.pagador === pag);
    const com = daqui.filter((l) => l.ir !== null && l.ir_salario !== null);
    const ir = com.reduce((t, l) => t + l.ir!, 0);
    const irSalario = com.reduce((t, l) => t + l.ir_salario!, 0);
    return {
      orgaos: com.length, membros: com.reduce((t, l) => t + l.membros, 0), membrosTodos: daqui.reduce((t, l) => t + l.membros, 0),
      ir, irSalario, diferenca: Math.max(0, irSalario - ir), excesso: daqui.reduce((t, l) => t + (l.excesso ?? 0), 0),
    };
  };
  return { estado: soma("estado"), uniao: soma("uniao") };
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
  /** Num mês típico (a mediana dos meses); null quando são menos de 5. */
  acima: number | null;
  parte: number | null;
  /** Meses com pelo menos 5 acima do teto. */
  meses_acima: number;
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
  if (nome === nome.toLowerCase()) return nome.charAt(0).toUpperCase() + nome.slice(1);   // GO: tudo em minúsculas
  if (nome !== nome.toUpperCase()) return nome;
  const doOrcamento = orcamento && docBase?.dims.orgao[orcamento];
  if (doOrcamento) return doOrcamento;
  return nome.toLowerCase().split(" ").map((p, i) => (i > 0 && MINUSCULAS.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1))).join(" ");
}

export interface LinhaFederal extends OrgaoFederal {
  cod: string;
  /** Parte do que passou do teto que veio dos pagamentos eventuais (o que o degrau dos eventuais acrescenta). */
  eventuaisParte: number | null;
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
      const eventuais = o.camadas[1][1] - o.camadas[0][1];
      return {
        ...o, cod, orcamento, nome: nomeLegivel(o.nome, orcamento),
        eventuaisParte: o.excesso ? Math.max(0, eventuais) / o.excesso : null,
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

/** Só aparece pelo nome o órgão com pelo menos 5 pessoas acima do teto num mês típico; os outros entram só nas somas. */
export const MOSTRA_NOME = (o: { acima: number | null; excesso: number | null }) => o.acima !== null && o.excesso !== null;
/** Quando mais da metade do que passou do teto veio de pagamentos eventuais ou atrasados. */
export const EXTRA_EVENTUAL = 0.5;

/** Os órgãos do SIAPE que casam com um órgão do orçamento. */
export const federalDoOrgao = (cod: string) => linhasFederal().filter((l) => l.orcamento === cod);

// ---------------------------------------------------------------------------------------------------
// O FPM que cada prefeitura deixou de receber: a parte do imposto de renda que a União não descontou dos juízes
// e promotores que ela paga, dividida como o FPM que a cidade recebeu no mesmo ano (mapa/federal-{ano}.json,
// pipeline/…/federal.py; a primeira coluna de cada município é o FPM).

interface DocRepasses { ano: number; colunas: string[]; mun: Record<string, number[]> }
const arquivosRepasses = import.meta.glob<DocRepasses>("../../public/data/mapa/federal-[0-9]*.json", { eager: true, import: "default" });

/** O FPM de cada cidade no ano do período (ou no mais recente), e o total do país. */
function fpmDoAno(ano: number) {
  const docs = Object.values(arquivosRepasses).sort((a, b) => b.ano - a.ano);
  const doc = docs.find((x) => x.ano === ano) ?? docs[0];
  if (!doc) return null;
  const i = doc.colunas.indexOf("fpm");
  if (i < 0) return null;
  const total = Object.values(doc.mun).reduce((t, v) => t + (v[i] ?? 0), 0);
  return { ano: doc.ano, total, de: (ibge: number) => doc.mun[String(ibge)]?.[i] ?? null };
}

export interface FpmPerdido {
  ano: string;
  /** O FPM que a prefeitura recebeu no ano. */
  recebido: number;
  anoFpm: number;
  /** O imposto que a União deixou de descontar e a parte dele que iria para o FPM, no país. */
  irUniao: number;
  fpmPais: number;
  /** A parte desta cidade. */
  perdido: number;
}

/** Quanto do FPM desta cidade deixou de existir porque a União não descontou o IR do extra acima do teto. */
export function fpmPerdido(ibge: number): FpmPerdido | null {
  if (!docSuper) return null;
  const p = docSuper.periodos[0];
  const uniao = imposto(p.id).uniao;
  if (!uniao.orgaos || uniao.diferenca <= 0) return null;
  const fpm = fpmDoAno(Number(p.id));
  const recebido = fpm?.de(ibge) ?? null;
  if (!fpm || !recebido || !fpm.total) return null;
  const fpmPais = uniao.diferenca * PARTE_FPM;
  return { ano: p.rotulo, recebido, anoFpm: fpm.ano, irUniao: uniao.diferenca, fpmPais, perdido: fpmPais * (recebido / fpm.total) };
}

// ---------------------------------------------------------------------------------------------------
// Comparações: o que o mesmo dinheiro pagaria nos serviços, com os números que o site já tem (gasto por aluno das
// redes estaduais e municipais, gasto em saúde de cada governo, FPM de cada cidade).


export interface Comparacao {
  /** Quantos alunos um ano de escola pagaria, e o custo por aluno usado. */
  alunos: number | null;
  porAluno: number | null;
  rede: "estadual" | "municipal";
  /** Quantos dias de todo o gasto daquele governo com saúde. */
  diasSaude: number | null;
  anoContas: number | null;
}

/** O que `valor` pagaria em escola e saúde para um governo (estado ou prefeitura), pelos números dele. */
export function comparar(valor: number, ente: Cidade, esfera: "uf" | "mun"): Comparacao {
  const aluno = esfera === "uf" ? porAlunoEstado(ente, docEstados?.cidades ?? []) : porAlunoDe(ente);
  const saude = ente.f?.["10"]?.[0] ?? 0;
  return {
    alunos: aluno ? valor / aluno.porAluno : null, porAluno: aluno?.porAluno ?? null, rede: esfera === "uf" ? "estadual" : "municipal",
    diasSaude: saude > 0 ? valor / (saude / 365) : null, anoContas: ente.ano,
  };
}

/** As mesmas comparações para o conjunto dos 27 governos estaduais. */
export function compararEstados(valor: number) {
  const estados = docEstados?.cidades ?? [];
  let alunos = 0, basica = 0, saude = 0;
  for (const e of estados) {
    const a = porAlunoEstado(e, estados);
    if (a) { alunos += a.alunos; basica += a.basica; }
    saude += e.f?.["10"]?.[0] ?? 0;
  }
  const porAluno = alunos > 0 ? basica / alunos : null;
  return {
    porAluno, alunos: porAluno ? valor / porAluno : null,
    diasSaude: saude > 0 ? valor / (saude / 365) : null,
  };
}

/** Quantas cidades pequenas (até 10 mil moradores) teriam o FPM de um ano inteiro pago com `valor`. */
export function fpmDeCidadesPequenas(valor: number) {
  const fpm = docSuper ? fpmDoAno(Number(docSuper.periodos[0].id)) : null;
  if (!fpm || !docCidades) return null;
  const valores = docCidades.cidades.filter((c) => c.pop <= 10_000).map((c) => fpm.de(c.ibge)).filter((v): v is number => !!v).sort((a, b) => a - b);
  if (!valores.length) return null;
  const mediana = valores[Math.floor(valores.length / 2)];
  return { cidades: valor / mediana, mediana, ano: fpm.ano };
}

// ---------------------------------------------------------------------------------------------------
// Executivo dos estados que publicam a folha com as partes do salário, de pipeline/…/supersalarios_estados.py.

export interface OrgaoEstadual {
  nome: string;
  meses: number;
  vinculos: number;
  acima: number | null;
  parte: number | null;
  meses_acima: number;
  excesso: number | null;
  pago: number;
  mediana: number;
  grupos: Record<string, number>;
  camadas: [number, number][];
  faixas: (number | null)[] | null;
  ir: number;
  ir_salario: number;
  previdencia: number;
}
interface ExecutivoUf {
  nome: string;
  /** O que cada família de pagamento reúne neste estado; família ausente: o arquivo não separa. */
  grupos: Record<string, string>;
  /** false quando o arquivo não traz o imposto de renda (GO). */
  com_ir: boolean;
  /** Empresas estatais deixadas de fora (o teto só vale para as que dependem do Tesouro, e o arquivo não diz quais). */
  estatais_fora: string[];
  /** Um cuidado próprio do arquivo deste estado (um mês deixado de fora, uma parte que não se separa). */
  nota?: string;
  fonte: string;
  url: string;
  de: string;
  ate: string;
  meses: number;
  orgaos: Record<string, OrgaoEstadual>;
  /** mês -> [vínculos, acima do teto, quanto passou] */
  serie: Record<string, [number, number, number]>;
}
interface DocEstadosTeto { gerado: string; grupos: string[]; faixas: number[]; estados: Record<string, ExecutivoUf> }
const arquivosEstadosTeto = import.meta.glob<DocEstadosTeto>("../../public/data/indicadores/supersalarios-estados.json", { eager: true, import: "default" });
export const docEstadosTeto: DocEstadosTeto | null = Object.values(arquivosEstadosTeto)[0] ?? null;

/** Os estados com a folha do Executivo, do que mais passou do teto ao que menos. */
export function estadosComExecutivo() {
  return Object.keys(docEstadosTeto?.estados ?? {}).map((uf) => ({ uf, e: executivoDoEstado(uf)! }))
    .filter((x) => x.e).sort((a, b) => b.e.excesso - a.e.excesso);
}

/** O Executivo de um estado: os órgãos (do que mais passou do teto ao que menos) e as somas. */
export function executivoDoEstado(uf: string) {
  const e = docEstadosTeto?.estados[uf.toUpperCase()];
  if (!e || !docEstadosTeto) return null;
  // A parte do que passou do teto que veio dos pagamentos atrasados (o que o degrau dos retroativos acrescenta).
  const orgaos = Object.entries(e.orgaos).map(([sigla, o]) => ({
    ...o, sigla, nome: nomeLegivel(o.nome, null),
    atrasadosParte: o.excesso ? Math.max(0, o.camadas[2][1] - o.camadas[1][1]) / o.excesso : null,
  }))
    .sort((a, b) => (b.excesso ?? -1) - (a.excesso ?? -1) || b.vinculos - a.vinculos);
  const vinculos = orgaos.reduce((t, o) => t + o.vinculos, 0);
  const camadas = docEstadosTeto.grupos.map((g, i) => ({
    grupo: g, acima: orgaos.reduce((t, o) => t + o.camadas[i][0], 0), excesso: orgaos.reduce((t, o) => t + o.camadas[i][1], 0),
  }));
  const ultima = camadas.at(-1)!;
  const grupos = Object.fromEntries(docEstadosTeto.grupos.map((g) => [g, orgaos.reduce((t, o) => t + o.grupos[g], 0)]));
  const ir = orgaos.reduce((t, o) => t + o.ir, 0), irSalario = orgaos.reduce((t, o) => t + o.ir_salario, 0);
  const periodo = e.de.slice(0, 4) === e.ate.slice(0, 4)
    ? `de ${mesExtenso(e.de).replace(/ de \d{4}$/, "")} a ${mesExtenso(e.ate)}`
    : `de ${mesExtenso(e.de)} a ${mesExtenso(e.ate)}`;
  return {
    ...e, periodo, orgaos, vinculos, acima: ultima.acima, parte: ultima.acima / vinculos, excesso: ultima.excesso,
    camadas, grupos, nomesGrupos: e.grupos, ir, irSalario, irPerdido: e.com_ir ? Math.max(0, irSalario - ir) : 0,
    estatais_fora: e.estatais_fora.map((n) => nomeLegivel(n, null)),
  };
}

// ---------------------------------------------------------------------------------------------------- Legislativo
// Câmara, Senado e TCU (pipeline/…/supersalarios_legislativo.py). Mesma forma do Executivo dos estados: somas por mês
// resumidas pela mediana, "acima" nulo quando são menos de 5 num mês típico.
export interface GrupoLegislativo {
  nome: string;
  meses: number;
  vinculos: number;
  acima: number | null;
  parte: number | null;
  meses_acima: number;
  excesso: number | null;
  grupos: Record<string, number>;
  /** Por família de pagamento, na ordem de `grupos` do arquivo: [quantos passam do teto até aqui, quanto passa]. */
  camadas: [number, number][];
  ir: number;
  ir_salario: number;
}
export interface OrgaoLegislativo {
  nome: string;
  orcamento: string;
  fonte: string;
  url: string;
  de: string;
  ate: string;
  meses: number;
  resumo: GrupoLegislativo;
  /** mês -> [na ativa, acima do teto, quanto passou] */
  serie: Record<string, [number, number, number]>;
  /** A escada do último mês (quantos passam do teto com cada família, quanto passa). */
  ultimo_mes: { mes: string; camadas: [number, number][] };
  /** Deputados, servidores efetivos, comissionados…, do que mais passou do teto ao que menos. */
  grupos_funcionais: Record<string, GrupoLegislativo>;
}
interface DocLegislativo {
  gerado: string;
  grupos: string[];
  nomes_grupos: Record<string, string>;
  orgaos: Record<string, OrgaoLegislativo>;
}
const arquivosLegislativo = import.meta.glob<DocLegislativo>("../../public/data/indicadores/supersalarios-legislativo.json", { eager: true, import: "default" });
export const docLegislativo: DocLegislativo | null = Object.values(arquivosLegislativo)[0] ?? null;

/** De onde veio o que passou do teto: a parte que cada família acrescenta à escada (eventuais, atrasados, auxílios). */
export function partesDoExcesso(g: GrupoLegislativo): { eventuais: number; atrasados: number; auxilios: number } {
  const c = g.camadas.map(([, x]) => x);
  const tot = c.at(-1) || 1;
  const d = (i: number) => Math.max(0, (c[i] ?? 0) - (c[i - 1] ?? 0)) / tot;
  return { eventuais: d(1), atrasados: d(2), auxilios: d(3) };
}

/** Os órgãos do Legislativo com os números do período, do que mais passou do teto ao que menos. */
export function linhasLegislativo() {
  if (!docLegislativo) return [];
  return Object.entries(docLegislativo.orgaos)
    .map(([id, o]) => ({ id, ...o, partes: partesDoExcesso(o.resumo) }))
    .sort((a, b) => (b.resumo.excesso ?? 0) - (a.resumo.excesso ?? 0));
}

/** O órgão do Legislativo cuja página no site é /orgaos/[cod], se houver. */
export function legislativoDoOrgao(cod: string) {
  return linhasLegislativo().find((o) => o.orcamento === cod) ?? null;
}
