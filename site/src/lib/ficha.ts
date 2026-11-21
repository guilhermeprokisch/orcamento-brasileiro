/**
 * A "ficha" de um ente num ano: tudo o que a página da cidade ou do estado mostra e que muda
 * com o ano (gasto por área e subárea, receita, saldo, balanço e INSS). Lida no build a partir
 * do detalhe de cada ano gravado por pipeline/…/cidades.py (site/src/gerado/gasto) e dos
 * arquivos do mapa (lib/contas.ts). A página monta o ano mais recente; os outros anos vão
 * para /dados/fichas/{ano}/{uf|estados}.json e são desenhados no navegador (lib/ficha-html.ts).
 */
import { docCidades, docEstados, type Cidade, type DocCidades } from "./cidades";
import { balancoDe, contasDe, inssDe, naturezaDe, vermelhoNoAno, type Balanco, type Contas, type Esfera, type Inss, type Natureza, type Vermelho } from "./contas";

/** O registro de gasto (DCA, Anexo I-E) de um ente num ano. */
export interface Gasto {
  pop: number;
  faixa?: number;
  /** [empenhado, pago] */
  total: [number, number];
  /** função → [empenhado, pago] */
  f: Record<string, [number, number]>;
  /** subfunção ("10.301") → empenhado */
  s: Record<string, number>;
}

export interface Ficha extends Gasto {
  ano: number;
  /** Total empenhado no ano anterior, para a variação. */
  anterior: number | null;
  contas: Contas | null;
  natureza: Natureza | null;
  balanco: Balanco | null;
  inss: Inss | null;
}

/** O que a página precisa, além da ficha, para desenhar um ano: nomes e medianas daquele ano. */
export interface Pacote {
  ano: number;
  faixas: string[];
  /** faixa → (função | "total" → mediana por morador) e "n" */
  medianas: Record<string, number>[];
  funcoes: Record<string, string>;
  subfuncoes: Record<string, string>;
  /** Quantas prefeituras (ou estados) gastaram mais do que receberam naquele ano, para comparar. */
  vermelho?: Vermelho | null;
}

const arquivos = import.meta.glob<Record<string, Gasto>>("../gerado/gasto/*/*.json", { import: "default" });
const lidos = new Map<string, Promise<Record<string, Gasto> | null>>();
function gastosDo(tipo: "municipios" | "estados", ano: number) {
  const chave = `${tipo}/${ano}`;
  if (!lidos.has(chave)) {
    const ler = Object.entries(arquivos).find(([k]) => k.endsWith(`/${chave}.json`))?.[1];
    lidos.set(chave, ler ? ler() : Promise.resolve(null));
  }
  return lidos.get(chave)!;
}

export const docDa = (esfera: Esfera): DocCidades | null => (esfera === "uf" ? docEstados : docCidades);

/** Anos com gasto declarado pelo ente, do mais recente ao mais antigo. */
export const anosDe = (c: Cidade): number[] => Object.keys(c.hist ?? {}).map(Number).sort((a, b) => b - a);

export async function pacoteDe(esfera: Esfera, ano: number): Promise<Pacote | null> {
  const doc = docDa(esfera);
  if (!doc) return null;
  return {
    ano, faixas: doc.faixas, medianas: doc.medianas[String(ano)] ?? [], funcoes: doc.funcoes, subfuncoes: doc.subfuncoes,
    vermelho: await vermelhoNoAno(esfera, ano),
  };
}

export async function fichaDe(c: Cidade, esfera: Esfera, ano: number): Promise<Ficha | null> {
  let g = (await gastosDo(esfera === "uf" ? "estados" : "municipios", ano))?.[String(c.ibge)];
  // Sem o detalhe por ano (pipeline antigo), o ano mais recente ainda sai do documento principal.
  if (!g && ano === c.ano && c.total) g = { pop: c.pop, faixa: c.faixa, total: c.total, f: c.f ?? {}, s: c.s ?? {} };
  if (!g) return null;
  const e = { ...c, ano };
  const [contas, natureza, balanco, inss] = await Promise.all([contasDe(e, esfera), naturezaDe(e, esfera), balancoDe(e, esfera), inssDe(e, esfera)]);
  return { ...g, ano, anterior: c.hist?.[String(ano - 1)] ?? null, contas, natureza, balanco, inss };
}
