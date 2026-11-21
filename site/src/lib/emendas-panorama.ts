/**
 * A visão geral das emendas parlamentares (/emendas): o que é cada tipo, quanto foi pago por ano, para onde vai,
 * quem recebe e quanto chega por morador em cada estado e cidade. Lido no build a partir de dois arquivos:
 *   - emendas-explorador/resumo.json (pipeline/…/explorador_emendas.py, chave "panorama"): a série por tipo, as
 *     áreas, quem recebe e o cruzamento tipo → quem recebe → área do último ano fechado;
 *   - indicadores/emendas.json (pipeline/…/emendas.py): o pago a quem fica em cada cidade e estado, por ano.
 * A população é a da base do site (cidades.ts).
 */
import { docCidades, docEstados, NOMES_UF } from "./cidades";

export type Tipo = "Individual" | "Pix" | "Bancada" | "Comissão" | "Relator";

export interface Panorama {
  serie: ({ ano: number; parcial: boolean; meses: number } & Record<Tipo, number>)[];
  areas: [string, number][];
  grupos: [string, number][];
  /** [tipo, quem recebe, área, valor] */
  cruzado: [Tipo, string, string, number][];
  /** [bancada ou comissão, tipo, valor] */
  coletivos: [string, Tipo, number][];
  contagem: { emendas: number; lugares: number; parlamentares: number; mediana_individual: number };
}
export interface Resumo {
  fonte: string; ano: number; anos: number[]; pagamentos: string; textos: string; total: number;
  tipos: Record<string, number>;
  autores: [string, number][];
  entidades: { codigo: string; nome: string; lugar: string; valor: number; autor: string }[];
  nomes: string[];
  panorama?: Panorama;
}
interface DocEmendas {
  fonte: string; anos: number[];
  mun: Record<string, Record<string, [number, number, number, number]>>;
  uf: Record<string, Record<string, [number, number, number, number]>>;
}

const arqResumo = import.meta.glob<Resumo>("../../public/data/emendas-explorador/resumo.json", { eager: true, import: "default" });
const arqEmendas = import.meta.glob<DocEmendas>("../../public/data/indicadores/emendas.json", { eager: true, import: "default" });
export const resumo: Resumo | null = Object.values(arqResumo)[0] ?? null;
const docEmendas: DocEmendas | null = Object.values(arqEmendas)[0] ?? null;
export const panorama: Panorama | null = resumo?.panorama ?? null;

/** Os tipos, na ordem em que aparecem em toda a página. */
export const TIPOS: { id: Tipo; nome: string; termo: string; cor: string; texto: string; uma: string }[] = [
  { id: "Individual", nome: "Individuais", termo: "emenda-individual", cor: "#0a4a29", texto: "#fff",
    uma: "A cota de cada deputado e senador. Todos têm o mesmo valor; metade tem de ir para a saúde." },
  { id: "Pix", nome: "Emendas Pix", termo: "emenda-pix", cor: "#f2c919", texto: "#191919",
    uma: "Parte da cota individual que cai direto no caixa da prefeitura ou do estado, sem dizer para quê." },
  { id: "Bancada", nome: "De bancada", termo: "emenda-de-bancada", cor: "#4fae73", texto: "#191919",
    uma: "Os deputados e senadores de um estado indicam juntos, em geral para obras maiores." },
  { id: "Comissão", nome: "De comissão", termo: "emenda-de-comissao", cor: "#2c62a0", texto: "#fff",
    uma: "Indicadas por comissões da Câmara e do Senado. Cresceram muito depois do fim das de relator." },
  { id: "Relator", nome: "De relator", termo: "emenda-de-relator", cor: "#5c574c", texto: "#fff",
    uma: "O “orçamento secreto” de 2020 a 2022: não se sabia quem pedia. Hoje só se pagam restos antigos." },
];
export const TIPO = Object.fromEntries(TIPOS.map((t) => [t.id, t])) as Record<Tipo, (typeof TIPOS)[number]>;

const AREAS: Record<string, string> = {
  "Encargos especiais": "Sem área definida (Pix)", "Múltiplo": "Várias áreas", "Desporto e lazer": "Esporte e lazer",
  "Sem área": "Sem área", "Ciência e Tecnologia": "Ciência e tecnologia",
};
export const nomeArea = (a: string) => AREAS[a] ?? a;
const GRUPOS: Record<string, string> = {
  "Prefeitura": "Prefeituras", "Governo estadual": "Governos estaduais", "Entidade sem fins lucrativos": "Entidades sem fins lucrativos",
  "Empresa": "Empresas", "Outros órgãos públicos": "Outros órgãos públicos",
};
export const nomeGrupo = (g: string) => GRUPOS[g] ?? g;

/** O total de um ano da série. */
export const totalAno = (p: Panorama["serie"][number]) => TIPOS.reduce((t, x) => t + p[x.id], 0);

/** O último ano fechado do resumo e o total dele. */
export const ANO = resumo?.ano ?? 0;
export const TOTAL = resumo?.total ?? 0;
const popBrasil = (docEstados?.cidades ?? []).reduce((t, x) => t + (x.pop || 0), 0);
export const POR_MORADOR = popBrasil ? TOTAL / popBrasil : 0;

export interface Estado { codigo: string; uf: string; nome: string; valor: number; pop: number; porHab: number }
/** O pago a quem fica em cada estado (prefeituras, governo, entidades), por morador, do maior para o menor. */
export function porEstado(ano = ANO): Estado[] {
  if (!docEmendas) return [];
  return (docEstados?.cidades ?? [])
    .map((e) => ({ e, v: docEmendas.uf[String(e.ibge)]?.[String(ano)]?.[0] ?? 0 }))
    .filter(({ e, v }) => v > 0 && e.pop)
    .map(({ e, v }) => ({ codigo: String(e.ibge), uf: e.uf, nome: NOMES_UF[e.uf] ?? e.nome, valor: v, pop: e.pop, porHab: v / e.pop }))
    .sort((a, b) => b.porHab - a.porHab);
}

export interface CidadeEmendas { ibge: string; nome: string; uf: string; pop: number; valor: number; porHab: number; peso: number | null }
const mediana = (v: number[]) => { const s = [...v].sort((a, b) => a - b); const m = s.length >> 1; return s.length ? (s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2) : 0; };
const FAIXAS: [string, number, number][] = [
  ["até 5 mil moradores", 0, 5e3], ["de 5 a 20 mil", 5e3, 2e4], ["de 20 a 100 mil", 2e4, 1e5], ["de 100 a 500 mil", 1e5, 5e5], ["mais de 500 mil", 5e5, Infinity],
];
/**
 * As cidades (sem o DF): o que chegou à prefeitura e a entidades e empresas da cidade (sem os órgãos estaduais e
 * federais com sede nela, como em indicadores.ts), por morador, e o peso no que a prefeitura gastou (pago) no ano.
 */
export function cidades(ano = ANO) {
  if (!docEmendas || !docCidades) return null;
  const lista: CidadeEmendas[] = docCidades.cidades.filter((c) => c.ibge !== 53 && c.pop).map((c) => {
    const v = docEmendas.mun[String(c.ibge)]?.[String(ano)];
    const valor = v ? v[1] + v[2] : 0;
    const gasto = c.ano === ano && c.total ? c.total[1] : 0;
    return { ibge: String(c.ibge), nome: c.nome, uf: c.uf, pop: c.pop, valor, porHab: valor / c.pop, peso: gasto ? (v?.[1] ?? 0) / gasto : null };
  });
  const porHab = [...lista].sort((a, b) => b.porHab - a.porHab);
  const grandes = porHab.filter((c) => c.pop >= 1e5);
  const pesos = lista.filter((c) => c.peso !== null);
  const med = mediana(lista.map((c) => c.porHab));
  return {
    /** Uma cidade média de exemplo: de 10 a 50 mil moradores, com o valor por morador mais perto da mediana. */
    meio: lista.filter((c) => c.pop >= 1e4 && c.pop < 5e4).sort((a, b) => Math.abs(a.porHab - med) - Math.abs(b.porHab - med))[0],
    maior: [...lista].sort((a, b) => b.pop - a.pop)[0],
    n: lista.length,
    semNada: lista.filter((c) => c.valor === 0).length,
    mediana: med,
    faixas: FAIXAS.map(([rotulo, de, ate]) => { const f = lista.filter((c) => c.pop >= de && c.pop < ate); return { rotulo, de, ate, n: f.length, mediana: mediana(f.map((c) => c.porHab)) }; }),
    maisPorHab: porHab.slice(0, 5),
    grandesMais: grandes.slice(0, 5),
    grandesMenos: grandes.slice(-5).reverse(),
    peso: { n: pesos.length, mediana: mediana(pesos.map((c) => c.peso!)), acima10: pesos.filter((c) => c.peso! > 0.1).length, acima20: pesos.filter((c) => c.peso! > 0.2).length },
  };
}

/** A posição de cada estado no mapa de quadradinhos: [coluna, linha]. */
export const GRADE_UF: Record<string, [number, number]> = {
  RR: [2, 0], AP: [3, 0],
  AM: [1, 1], PA: [2, 1], MA: [3, 1], CE: [4, 1], RN: [5, 1],
  AC: [0, 2], RO: [1, 2], MT: [2, 2], TO: [3, 2], PI: [4, 2], PB: [5, 2],
  MS: [1, 3], GO: [2, 3], DF: [3, 3], BA: [4, 3], PE: [5, 3],
  SP: [2, 4], MG: [3, 4], ES: [4, 4], AL: [5, 4],
  PR: [2, 5], RJ: [3, 5], SE: [5, 5],
  RS: [1, 6], SC: [2, 6],
};

/** Os endereços das páginas das emendas (no protótipo; na página final, /emendas e /emendas/explorar). */
export const ROTA = { inicio: "/prototipo-emendas", explorar: "/prototipo-emendas/explorar", busca: "/emendas" };
/** O explorador já aberto num caminho: filtros "dim:código" e, se quiser, a lista. */
export const noExplorador = (filtros: string[], lista = false) =>
  `${ROTA.explorar}?f=${filtros.map(encodeURIComponent).join("|")}${lista ? "&vista=lista" : ""}`;
