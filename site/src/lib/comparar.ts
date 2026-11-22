/**
 * A página /comparar: dois lugares lado a lado (duas cidades ou dois estados).
 *
 * Tudo roda no navegador. O gasto, a receita e o saldo de cada ano vêm das fichas
 * (/dados/fichas/{ano}/{grupo}.json, as mesmas da troca de ano); dívida, Ideb, mortalidade
 * infantil, emendas e homicídios vêm de /dados/comparar/{grupo}.json.
 *
 * Os números viram um modelo (blocos com linhas, cada linha com o valor de A e de B), desenhado
 * frente a frente: o nome da linha no meio, a barra de A cresce para a esquerda e a de B para a direita.
 */
import { moedaCompleta, moedaCurta, pct } from "./formato";
import type { Ficha, Pacote } from "./ficha";

// ----- dados -----

/** Um lugar em /dados/comparar/{grupo}.json (montado em pages/dados/comparar/[grupo].json.ts). */
export interface LugarComparado {
  ibge: number;
  nome: string;
  uf: string;
  capital: boolean;
  pop: number;
  /** Anos com contas, do mais recente ao mais antigo. */
  anos: number[];
  /** Dívida consolidada líquida no último ano com RGF: [ano, dívida líquida, receita corrente líquida]. */
  divida: [number, number, number] | null;
  /** Ideb da rede municipal: [anos iniciais, anos finais] na edição mais recente (só cidades). */
  ideb: [number | null, number | null] | null;
  /** Gasto em educação por aluno da rede própria: [ano, valor]. */
  porAluno: [number, number] | null;
  /** Mortalidade infantil por mil nascidos vivos, nos anos somados; null com poucos nascimentos. */
  mortalidade: number | null;
  /** Emendas parlamentares pagas no último ano fechado: [ano, total]. */
  emendas: [number, number] | null;
  /** Homicídios por 100 mil moradores: [ano, taxa]. */
  homicidios: [number, number] | null;
}

interface ArquivoComparar {
  esfera: "mun" | "uf";
  limiteDivida: number;
  idebEdicao: number | null;
  mortalidadeAnos: number[];
  entes: Record<string, LugarComparado>;
}
type ArquivoFicha = Pacote & { entes: Record<string, Ficha> };

/** O lugar escolhido no campo "Onde" (public/explorador/onde.js). */
export interface Escolhido { tipo: "uf" | "mun"; codigo: string; nome: string; sigla: string }

const cache = new Map<string, Promise<unknown>>();
function baixar<T>(url: string): Promise<T | null> {
  if (!cache.has(url)) cache.set(url, fetch(url).then((r) => (r.ok ? r.json() : null)).catch(() => null));
  return cache.get(url) as Promise<T | null>;
}
const grupoDe = (l: Escolhido) => (l.tipo === "uf" ? "estados" : l.sigla.toLowerCase());

export interface Lado {
  l: Escolhido;
  info: LugarComparado;
  extra: ArquivoComparar;
  ficha: Ficha;
  pacote: Pacote;
}

/** Os anos com contas dos dois lugares, do mais recente ao mais antigo. */
export async function anosEmComum(a: Escolhido, b: Escolhido): Promise<{ anos: number[]; infoA: LugarComparado | null; infoB: LugarComparado | null }> {
  const [xa, xb] = await Promise.all([baixar<ArquivoComparar>(`/dados/comparar/${grupoDe(a)}.json`), baixar<ArquivoComparar>(`/dados/comparar/${grupoDe(b)}.json`)]);
  const infoA = xa?.entes[a.codigo] ?? null, infoB = xb?.entes[b.codigo] ?? null;
  const anos = infoA && infoB ? infoA.anos.filter((x) => infoB.anos.includes(x)) : [];
  return { anos, infoA, infoB };
}

export async function carregarLado(l: Escolhido, ano: number): Promise<Lado | null> {
  const [extra, arq] = await Promise.all([
    baixar<ArquivoComparar>(`/dados/comparar/${grupoDe(l)}.json`),
    baixar<ArquivoFicha>(`/dados/fichas/${ano}/${grupoDe(l)}.json`),
  ]);
  const info = extra?.entes[l.codigo], ficha = arq?.entes[l.codigo];
  if (!extra || !arq || !info || !ficha) return null;
  return { l, info, extra, ficha, pacote: arq };
}

// ----- nomes e preposições -----

const PREP_UF: Record<string, "do" | "da" | "de"> = {
  AC: "do", AL: "de", AM: "do", AP: "do", BA: "da", CE: "do", DF: "do", ES: "do", GO: "de", MA: "do",
  MG: "de", MS: "de", MT: "de", PA: "do", PB: "da", PE: "de", PI: "do", PR: "do", RJ: "do", RN: "do",
  RO: "de", RR: "de", RS: "do", SC: "de", SE: "de", SP: "de", TO: "do",
};
const ESC: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ESC[c]);

interface Nome { curto: string; sujeito: string; em: string; de: string }
/** Cidades que se dizem com artigo: "o Rio de Janeiro gasta", "no Rio de Janeiro". As outras vão sem. */
const PREP_CIDADE: Record<string, "do" | "da"> = { "3304557": "do" };

function nomeDe(l: Escolhido): Nome {
  if (l.tipo === "mun" && !PREP_CIDADE[l.codigo]) return { curto: l.nome, sujeito: l.nome, em: `em ${l.nome}`, de: `de ${l.nome}` };
  const p = l.tipo === "mun" ? PREP_CIDADE[l.codigo] : PREP_UF[l.sigla] ?? "de";
  const art = { do: "o ", da: "a ", de: "" }[p];
  return { curto: l.nome, sujeito: `${art}${l.nome}`, em: `${{ do: "no", da: "na", de: "em" }[p]} ${l.nome}`, de: `${p} ${l.nome}` };
}
/** "Jandira", "o Ceará", "a Paraíba": o nome como entra no meio de uma frase. */
export const nomeNaFrase = (l: Escolhido) => nomeDe(l).sujeito;
const maiuscula = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// ----- números -----

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const porPessoa = (v: number) => `${v < 0 ? "−" : ""}R$ ${nf0.format(Math.round(Math.abs(v)))}`;

type Formato = "porMorador" | "moeda" | "pessoas" | "emCem" | "nota" | "taxa" | "pctReceita";
function valor(fmt: Formato, v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "—";
  switch (fmt) {
    case "porMorador": return porPessoa(v);
    case "moeda": return moedaCurta(v);
    case "pessoas": return nf0.format(v);
    case "emCem": return `R$ ${nf0.format(Math.round(v))}`;
    case "nota": return nf1.format(v);
    case "taxa": return nf1.format(v);
    case "pctReceita": return `${v >= 0 ? "+" : "−"}${pct(Math.abs(v))}`;
  }
}
/** "18%": nas frases, sem casa decimal. */
const pctFrase = (v: number) => `${nf0.format(Math.round(v * 100))}%`;
/** "2,3 vezes", "12 vezes" */
const vezes = (r: number) => `${r >= 10 ? nf0.format(r) : nf1.format(r).replace(/,0$/, "")} vezes`;

// ----- o modelo -----

/** Como a frase da diferença é escrita. */
type Frase =
  /** "Barueri gasta 2,3 vezes mais por morador em saúde que Jandira" */
  | { tipo: "verbo"; verbo: string; plural: string; comp: string }
  /** "A mortalidade infantil em Jandira é 1,8 vezes a de Barueri" */
  | { tipo: "medida"; medida: string; maior: string }
  /** "A nota das escolas é 0,7 ponto maior em Barueri (6,4) que em Jandira (5,7)" */
  | { tipo: "pontos"; medida: string }
  | { tipo: "nenhuma" };

export interface Linha {
  rotulo: string;
  dica?: string;
  a: number | null;
  b: number | null;
  fmt: Formato;
  /** Qual lado é melhor quando o número é maior: "mais", "menos" ou nada (só diferente). */
  bom?: "mais" | "menos";
  frase: Frase;
  /** Linha principal do bloco: a frase dela vai para o topo do bloco. */
  principal?: boolean;
  /**
   * A régua da barra. No mesmo bloco, as linhas com a mesma régua têm barras na mesma escala
   * (a maior de todas enche o trilho). Sem nada, a régua é o formato: reais por morador com
   * reais por morador, e nunca moradores com reais.
   */
  regua?: string;
  /** A régua vai pelo menos até aqui: 10 na nota do Ideb, o limite da lei na dívida. */
  teto?: number;
}
export interface Bloco { id: string; titulo: string; nota?: string; linhas: Linha[]; frases: string[]; recolher?: number }

export interface Comparacao {
  A: Nome; B: Nome;
  ano: number;
  blocos: Bloco[];
  resumo: string[];
}

/** A diferença em poucas palavras: qual lado tem mais e quanto. */
function diferenca(linha: Linha): { lado: "a" | "b" | null; texto: string } | null {
  const { a, b } = linha;
  if (a === null || b === null) return null;
  // Sobra ou falta (com sinal): a diferença em vezes não faz sentido.
  if (a < 0 || b < 0) return null;
  if (linha.frase.tipo === "pontos") {
    const d = Math.abs(a - b);
    if (d < 0.15) return { lado: null, texto: "quase igual" };
    return { lado: a > b ? "a" : "b", texto: `${nf1.format(d)} ${d < 2 ? "ponto" : "pontos"} a mais` };
  }
  if (a <= 0 || b <= 0) {
    if (a <= 0 && b <= 0) return null;
    return { lado: a > b ? "a" : "b", texto: "só um tem" };
  }
  const r = Math.max(a, b) / Math.min(a, b);
  if (r < 1.1) return { lado: null, texto: "quase igual" };
  return { lado: a > b ? "a" : "b", texto: r >= 1.5 ? `${vezes(r)} mais` : `${pctFrase(r - 1)} a mais` };
}

function fraseDe(linha: Linha, A: Nome, B: Nome): string | null {
  const { a, b, frase } = linha;
  if (a === null || b === null || frase.tipo === "nenhuma") return null;
  const [maior, menor, vMaior, vMenor] = a >= b ? [A, B, a, b] : [B, A, b, a];
  const d = diferenca(linha);
  if (!d) return null;
  if (frase.tipo === "pontos") {
    if (d.lado === null) return `${maiuscula(frase.medida)} é quase igual ${A.em} (${valor(linha.fmt, a)}) e ${B.em} (${valor(linha.fmt, b)}).`;
    const dif = vMaior - vMenor;
    return `${maiuscula(frase.medida)} é ${nf1.format(dif)} ${dif < 2 ? "ponto" : "pontos"} maior ${maior.em} (${valor(linha.fmt, vMaior)}) que ${menor.em} (${valor(linha.fmt, vMenor)}).`;
  }
  if (vMenor <= 0) return null;
  const r = vMaior / vMenor;
  if (frase.tipo === "medida") {
    if (r < 1.1) return `${maiuscula(frase.medida)} é parecida ${A.em} e ${B.em}.`;
    return `${maiuscula(frase.medida)} ${maior.em} é ${r >= 1.5 ? `${vezes(r)} a ${menor.de}` : `${pctFrase(r - 1)} ${frase.maior} que a ${menor.de}`}.`;
  }
  if (r < 1.1) return `${maiuscula(A.sujeito)} e ${B.sujeito} ${frase.plural} quase o mesmo ${frase.comp}.`;
  return `${maiuscula(maior.sujeito)} ${frase.verbo} ${r >= 1.5 ? `${vezes(r)} mais` : `${pctFrase(r - 1)} a mais`} ${frase.comp} que ${menor.sujeito}.`;
}

/** Áreas cujo nome oficial não diz o que são (como em lib/ficha-html.ts, mais curto). */
const DICA_AREA: Record<string, string> = {
  "01": "Câmara ou Assembleia", "02": "em geral, precatórios", "09": "aposentadorias dos servidores",
  "15": "ruas, praças e obras", "25": "em geral, iluminação pública", "28": "dívida e outros",
};
const NOME_CURTO_AREA: Record<string, string> = { "28": "Encargos especiais" };
/** "em saúde", "em educação": o complemento das frases das áreas. */
const emArea = (nome: string) => `em ${nome.toLowerCase()}`;

export function montar(la: Lado, lb: Lado, ano: number): Comparacao {
  const A = nomeDe(la.l), B = nomeDe(lb.l);
  const fa = la.ficha, fb = lb.ficha;
  const mun = la.l.tipo === "mun";
  const pm = (v: number | undefined | null, f: Ficha) => (v === undefined || v === null ? null : v / f.pop);
  const blocos: Bloco[] = [];

  // 1. Quanto gasta
  blocos.push({
    id: "quanto", titulo: "Quanto gasta", frases: [],
    nota: `Gasto comprometido (empenhado) em ${ano}, declarado ao Tesouro.`,
    linhas: [
      { rotulo: "Gasto por morador", a: fa.total[0] / fa.pop, b: fb.total[0] / fb.pop, fmt: "porMorador", principal: true,
        frase: { tipo: "verbo", verbo: "gasta", plural: "gastam", comp: "por morador" } },
      { rotulo: "Gasto total no ano", a: fa.total[0], b: fb.total[0], fmt: "moeda", frase: { tipo: "nenhuma" } },
      { rotulo: "Moradores", a: fa.pop, b: fb.pop, fmt: "pessoas", frase: { tipo: "nenhuma" } },
    ],
  });

  // 2. Para onde vai o dinheiro: cada área, por morador, da maior para a menor (somando os dois lados).
  const cods = [...new Set([...Object.keys(fa.f), ...Object.keys(fb.f)])]
    .map((cod) => ({ cod, a: (fa.f[cod]?.[0] ?? 0) / fa.pop, b: (fb.f[cod]?.[0] ?? 0) / fb.pop }))
    .filter((x) => x.a > 0 || x.b > 0)
    .sort((x, y) => Math.max(y.a, y.b) - Math.max(x.a, x.b));
  const nomeArea = (cod: string) => NOME_CURTO_AREA[cod] ?? la.pacote.funcoes[cod] ?? cod;
  const areas: Linha[] = cods.map((x) => ({
    rotulo: nomeArea(x.cod), dica: DICA_AREA[x.cod], a: x.a, b: x.b, fmt: "porMorador",
    principal: x.cod === "10" || x.cod === "12",
    frase: { tipo: "verbo", verbo: "gasta", plural: "gastam", comp: `por morador ${emArea(nomeArea(x.cod))}` },
  }));
  // Saúde e educação primeiro, que é o que a pessoa procura.
  areas.sort((x, y) => Number(!!y.principal) - Number(!!x.principal));
  blocos.push({ id: "areas", titulo: "Para onde vai o dinheiro", nota: "Gasto por morador em cada área.", linhas: areas, frases: [], recolher: 10 });

  // 3. Com o quê gasta
  const na = fa.natureza, nb = fb.natureza;
  if (na && nb) {
    blocos.push({
      id: "com-o-que", titulo: "Com o quê gasta", nota: "Por morador.", frases: [],
      linhas: [
        { rotulo: "Salários dos servidores", a: pm(na.pessoal, fa), b: pm(nb.pessoal, fb), fmt: "porMorador",
          frase: { tipo: "verbo", verbo: "gasta", plural: "gastam", comp: "por morador com salários de servidores" } },
        { rotulo: "Serviços, materiais e contas do dia a dia", a: pm(na.custeio, fa), b: pm(nb.custeio, fb), fmt: "porMorador",
          frase: { tipo: "verbo", verbo: "gasta", plural: "gastam", comp: "por morador com serviços, materiais e contas do dia a dia" } },
        { rotulo: "Obras e equipamentos", a: pm(na.investimentos, fa), b: pm(nb.investimentos, fb), fmt: "porMorador", principal: true,
          frase: { tipo: "verbo", verbo: "investe", plural: "investem", comp: "por morador em obras e equipamentos" } },
      ],
    });
  }

  // 4. De onde vem o dinheiro
  const ca = fa.contas, cb = fb.contas;
  if (ca && cb) {
    blocos.push({
      id: "de-onde", titulo: "De onde vem o dinheiro", nota: "Receita por morador.", frases: [],
      linhas: [
        { rotulo: "Tudo o que entrou", a: pm(ca.receita, fa), b: pm(cb.receita, fb), fmt: "porMorador",
          frase: { tipo: "verbo", verbo: "recebe", plural: "recebem", comp: "por morador" } },
        { rotulo: "Arrecadação própria", dica: mun ? "ISS, IPTU, taxas" : "ICMS, IPVA", a: pm(ca.propria, fa), b: pm(cb.propria, fb), fmt: "porMorador", principal: true,
          frase: { tipo: "verbo", verbo: "arrecada", plural: "arrecadam", comp: "por morador com impostos próprios" } },
        { rotulo: "De cada R$ 100, arrecadados por conta própria", a: ca.receita ? (ca.propria / ca.receita) * 100 : null, b: cb.receita ? (cb.propria / cb.receita) * 100 : null, fmt: "emCem", teto: 100,
          frase: { tipo: "nenhuma" } },
        { rotulo: "Repasses da União", dica: mun ? "FPM, SUS e outros" : "FPE, SUS e outros", a: pm(ca.uniao, fa), b: pm(cb.uniao, fb), fmt: "porMorador",
          frase: { tipo: "verbo", verbo: "recebe", plural: "recebem", comp: "por morador da União" } },
        ...(mun ? [{ rotulo: "Repasses do governo estadual", dica: "parte do ICMS e do IPVA", a: pm(ca.estado, fa), b: pm(cb.estado, fb), fmt: "porMorador" as const,
          frase: { tipo: "verbo" as const, verbo: "recebe", plural: "recebem", comp: "por morador do governo estadual" } }] : []),
        { rotulo: "FUNDEB", dica: "fundo da educação básica", a: pm(ca.fundeb, fa), b: pm(cb.fundeb, fb), fmt: "porMorador",
          frase: { tipo: "verbo", verbo: "recebe", plural: "recebem", comp: "por morador do FUNDEB" } },
      ],
    });

    // 5. Sobrou ou faltou
    const sobra = (c: NonNullable<Ficha["contas"]>, n: Nome) => {
      const p = c.receita ? c.saldo / c.receita : 0;
      return `${n.sujeito} ${p >= 0 ? "terminou o ano com sobra de" : "gastou mais do que recebeu: faltaram"} ${pct(Math.abs(p))} da receita`;
    };
    blocos.push({
      id: "saldo", titulo: "Sobrou ou faltou", nota: "Receita menos gasto comprometido no ano.",
      frases: [`${maiuscula(sobra(ca, A))}; ${sobra(cb, B)}.`],
      linhas: [
        { rotulo: "Sobra (+) ou falta (−) por morador", a: ca.saldo / fa.pop, b: cb.saldo / fb.pop, fmt: "porMorador", frase: { tipo: "nenhuma" } },
        { rotulo: "Em relação ao que entrou", a: ca.receita ? ca.saldo / ca.receita : null, b: cb.receita ? cb.saldo / cb.receita : null, fmt: "pctReceita", frase: { tipo: "nenhuma" } },
      ],
    });
  }

  // 6. Dívida (RGF): o último ano declarado de cada um.
  const da = la.info.divida, db = lb.info.divida;
  if (da || db) {
    const limite = la.extra.limiteDivida;
    const frasesDiv: string[] = [];
    const desc = (d: [number, number, number] | null, n: Nome) => !d ? `${n.sujeito} não tem a dívida declarada ao Tesouro`
      : d[1] <= 0 ? `${n.sujeito} tem mais dinheiro em caixa do que dívidas`
      : `${n.sujeito} deve R$ ${nf0.format(Math.round((d[1] / d[2]) * 100))} para cada R$ 100 que arrecada no ano`;
    const fraseDiv = maiuscula([desc(da, A), desc(db, B)].join("; "));
    if (fraseDiv) frasesDiv.push(`${fraseDiv}. O limite da lei é R$ ${nf0.format(limite * 100)}.`);
    const anos = [...new Set([da?.[0], db?.[0]].filter(Boolean))];
    blocos.push({
      id: "divida", titulo: "Dívida", frases: frasesDiv,
      nota: `Dívida consolidada líquida (dívidas menos dinheiro em caixa), no fim de ${anos.join(" e ")}.`,
      linhas: [
        { rotulo: "Dívida por morador", a: da ? Math.max(0, da[1]) / la.info.pop : null, b: db ? Math.max(0, db[1]) / lb.info.pop : null, fmt: "porMorador", bom: "menos",
          frase: { tipo: "verbo", verbo: "deve", plural: "devem", comp: "por morador" } },
        { rotulo: "Para cada R$ 100 de receita", dica: `limite: R$ ${nf0.format(limite * 100)}`, a: da ? Math.max(0, da[1] / da[2]) * 100 : null, b: db ? Math.max(0, db[1] / db[2]) * 100 : null, fmt: "emCem", bom: "menos", teto: limite * 100,
          frase: { tipo: "nenhuma" } },
      ],
    });
  }

  // 7. Escola: Ideb (cidades) e gasto por aluno.
  const linhasEscola: Linha[] = [];
  if (mun && (la.info.ideb || lb.info.ideb)) {
    linhasEscola.push(
      { rotulo: "Nota do Ideb, 1º ao 5º ano", dica: "escolas da prefeitura, de 0 a 10", a: la.info.ideb?.[0] ?? null, b: lb.info.ideb?.[0] ?? null, fmt: "nota", bom: "mais", principal: true, teto: 10,
        frase: { tipo: "pontos", medida: "a nota das escolas da prefeitura do 1º ao 5º ano" } },
      { rotulo: "Nota do Ideb, 6º ao 9º ano", dica: "escolas da prefeitura, de 0 a 10", a: la.info.ideb?.[1] ?? null, b: lb.info.ideb?.[1] ?? null, fmt: "nota", bom: "mais", teto: 10,
        frase: { tipo: "pontos", medida: "a nota das escolas da prefeitura do 6º ao 9º ano" } },
    );
  }
  if (la.info.porAluno || lb.info.porAluno) {
    linhasEscola.push({ rotulo: "Gasto em educação por aluno", dica: mun ? "alunos da rede municipal" : "alunos das escolas estaduais, sem universidades",
      a: la.info.porAluno?.[1] ?? null, b: lb.info.porAluno?.[1] ?? null, fmt: "porMorador", principal: !mun,
      frase: { tipo: "verbo", verbo: "gasta", plural: "gastam", comp: "por aluno" } });
  }
  if (linhasEscola.length) {
    const ed = la.extra.idebEdicao;
    blocos.push({ id: "escola", titulo: "Escola", linhas: linhasEscola, frases: [],
      nota: [mun && ed ? `Ideb de ${ed}` : "", la.info.porAluno ? `gasto por aluno de ${la.info.porAluno[0]}` : ""].filter(Boolean).join("; ") + "." });
  }

  // 8. Saúde e segurança
  const linhasSaude: Linha[] = [];
  if (la.info.mortalidade !== null || lb.info.mortalidade !== null) {
    linhasSaude.push({ rotulo: "Mortalidade infantil", dica: "bebês que morrem antes de 1 ano, a cada mil nascidos", a: la.info.mortalidade, b: lb.info.mortalidade, fmt: "taxa", bom: "menos", principal: true, regua: "mortalidade",
      frase: { tipo: "medida", medida: "a mortalidade infantil", maior: "maior" } });
  }
  if (la.info.homicidios || lb.info.homicidios) {
    linhasSaude.push({ rotulo: "Homicídios", dica: "por 100 mil moradores", a: la.info.homicidios?.[1] ?? null, b: lb.info.homicidios?.[1] ?? null, fmt: "taxa", bom: "menos", regua: "homicidios",
      frase: { tipo: "medida", medida: "a taxa de homicídios", maior: "maior" } });
  }
  if (linhasSaude.length) {
    const anosM = la.extra.mortalidadeAnos;
    blocos.push({ id: "saude", titulo: "Saúde e segurança", linhas: linhasSaude, frases: [],
      nota: [anosM.length ? `Mortalidade infantil de ${anosM.join(" e ")} somados` : "", la.info.homicidios ? `homicídios de ${la.info.homicidios[0]}` : ""].filter(Boolean).join("; ") + "." });
  }

  // 9. Emendas parlamentares
  if (la.info.emendas || lb.info.emendas) {
    const anoE = la.info.emendas?.[0] ?? lb.info.emendas?.[0];
    blocos.push({
      id: "emendas", titulo: "Emendas parlamentares", frases: [],
      nota: `Pagas em ${anoE} por indicação de deputados e senadores${mun ? ", à prefeitura e a entidades da cidade" : ""}.`,
      linhas: [
        { rotulo: "Por morador", a: la.info.emendas ? la.info.emendas[1] / la.info.pop : null, b: lb.info.emendas ? lb.info.emendas[1] / lb.info.pop : null, fmt: "porMorador", principal: true,
          frase: { tipo: "verbo", verbo: "recebeu", plural: "receberam", comp: "por morador em emendas" } },
        { rotulo: "Total", a: la.info.emendas?.[1] ?? null, b: lb.info.emendas?.[1] ?? null, fmt: "moeda", frase: { tipo: "nenhuma" } },
      ],
    });
  }

  // As frases de cada bloco: as das linhas principais (as do saldo e da dívida já vêm prontas).
  for (const bl of blocos) {
    for (const l of bl.linhas.filter((x) => x.principal)) {
      const f = fraseDe(l, A, B);
      if (f) bl.frases.push(f);
    }
  }

  // O resumo do topo: o gasto por morador, saúde, educação, a área com a maior diferença e os resultados.
  const resumo: string[] = [];
  const add = (l: Linha | undefined) => { const f = l && fraseDe(l, A, B); if (f && !resumo.includes(f)) resumo.push(f); };
  add(blocos[0].linhas[0]);
  add(areas.find((x) => x.rotulo === nomeArea("10")));
  add(areas.find((x) => x.rotulo === nomeArea("12")));
  const outra = areas
    .filter((x) => !x.principal && x.a !== null && x.b !== null && Math.min(x.a, x.b) >= 30)
    .sort((x, y) => Math.max(y.a! / y.b!, y.b! / y.a!) - Math.max(x.a! / x.b!, x.b! / x.a!))[0];
  if (outra && Math.max(outra.a! / outra.b!, outra.b! / outra.a!) >= 1.5) add(outra);
  add(blocos.find((b) => b.id === "de-onde")?.linhas[1]);
  add(linhasEscola[0]);
  add(linhasSaude[0]);

  return { A, B, ano, blocos, resumo };
}

// ----- desenho -----

const titulo = (v: number | null, fmt: Formato) => (v !== null && (fmt === "moeda" || fmt === "porMorador") ? ` title="${moedaCompleta(v)}"` : "");
const melhorLado = (l: Linha): "a" | "b" | null => {
  if (!l.bom || l.a === null || l.b === null || l.a === l.b) return null;
  return (l.bom === "mais") === (l.a > l.b) ? "a" : "b";
};
const rotuloHtml = (l: Linha) => `<span class="cp-rotulo">${esc(l.rotulo)}${l.dica ? `<small>${esc(l.dica)}</small>` : ""}</span>`;
const largura = (v: number | null, max: number) => (v === null || max <= 0 ? 0 : (Math.abs(v) / max) * 100);
const maxDe = (l: Linha) => Math.max(Math.abs(l.a ?? 0), Math.abs(l.b ?? 0));
const frasesHtml = (fr: string[]) => (fr.length ? `<ul class="cp-frases">${fr.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : "");

/**
 * O fim da régua de cada linha do bloco: o maior valor entre as linhas da mesma régua (e o teto,
 * se houver). Assim, em "Para onde vai o dinheiro", saúde e transporte não ficam do mesmo tamanho.
 */
function reguas(bl: Bloco): Map<Linha, number> {
  const chave = (l: Linha) => l.regua ?? l.fmt;
  const fim = new Map<string, number>();
  for (const l of bl.linhas) fim.set(chave(l), Math.max(fim.get(chave(l)) ?? 0, l.teto ?? 0, maxDe(l)));
  return new Map(bl.linhas.map((l) => [l, fim.get(chave(l))!]));
}

/** Uma linha: o valor de A e a barra dele à esquerda, o nome no meio, B à direita. */
function linhaHtml(l: Linha, max: number): string {
  const bom = melhorLado(l);
  const lado = (s: "a" | "b") => {
    const v = l[s];
    return `<div class="cp-esp cp-${s}${bom === s ? " cp-bom" : ""}">
      <span class="cp-trilho"><span class="cp-barra${v !== null && v < 0 ? " neg" : ""}" style="width:${largura(v, max)}%"></span></span>
      <strong class="num"${titulo(v, l.fmt)}>${valor(l.fmt, v)}</strong>
    </div>`;
  };
  return `<div class="cp-linha-esp">${lado("a")}${rotuloHtml(l)}${lado("b")}</div>`;
}

/** As linhas do bloco; as que passam de `recolher` ficam num "ver as outras". */
function linhasHtml(bl: Bloco): string {
  const fim = reguas(bl);
  const linha = (l: Linha) => linhaHtml(l, fim.get(l)!);
  const vis = bl.recolher ? bl.linhas.slice(0, bl.recolher) : bl.linhas;
  const resto = bl.recolher ? bl.linhas.slice(bl.recolher) : [];
  return vis.map(linha).join("") + (resto.length
    ? `<details class="cp-mais cp-centro"><summary>Ver as outras ${resto.length} áreas</summary>${resto.map(linha).join("")}</details>` : "");
}

/**
 * A largura do número, igual em todas as linhas do bloco (pelo número mais comprido), para que
 * os trilhos das barras tenham o mesmo comprimento e dê para comparar uma linha com a outra.
 */
const larguraNumero = (bl: Bloco) =>
  (Math.max(...bl.linhas.flatMap((l) => [emCh(valor(l.fmt, l.a)), emCh(valor(l.fmt, l.b))])) + 0.3).toFixed(1);
/**
 * Quanto o texto ocupa, em ch (a largura de um algarismo, que é tabular nesses números): medido
 * na Source Serif 4 em negrito. Algarismos, "$", "−" e "+" valem 1.
 */
const LARGURA_CH: Record<string, number> = { R: 1.26, ".": 0.55, ",": 0.55, " ": 0.39, b: 1.13, m: 1.68, i: 0.59, l: 0.6, t: 0.66, r: 0.86, "%": 1.65, "—": 1.54 };
const emCh = (t: string) => [...t].reduce((s, c) => s + (LARGURA_CH[c] ?? 1), 0);

export function desenhar(c: Comparacao): string {
  return `<section class="cp-resumo" aria-label="As maiores diferenças">
    <h2>Em ${c.ano}, as diferenças que mais chamam a atenção</h2>
    <ul>${c.resumo.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
  </section>
  <div class="cp-espelho">
    <div class="cp-cabeca-esp"><h2 class="cp-a">${esc(c.A.curto)}</h2><span>×</span><h2 class="cp-b">${esc(c.B.curto)}</h2></div>
    ${c.blocos.map((bl) => `<section class="cp-bloco" id="cp-${bl.id}" style="--cp-num:${larguraNumero(bl)}ch">
      <div class="cp-bloco-topo cp-centro"><h3>${esc(bl.titulo)}</h3>${bl.nota ? `<p class="cp-nota">${esc(bl.nota)}</p>` : ""}</div>
      ${frasesHtml(bl.frases)}
      ${linhasHtml(bl)}
    </section>`).join("")}
  </div>`;
}
