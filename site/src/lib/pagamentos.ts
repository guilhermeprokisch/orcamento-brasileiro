/**
 * Para quem cada prefeitura pagou no ano: os empenhos que o Tribunal de Contas do estado publica
 * (por enquanto só a Paraíba; pipeline/…/pagamentos.py). Lido no build; sem o arquivo, tudo vem null.
 */
import type { Cidade } from "./cidades";

interface DocPagamentos {
  fonte: string;
  ano: number;
  uf: string;
  /** Rótulo de cada posição de "tipos": fornecedores, pessoas físicas, folha, previdência, dívida e bancos, outros órgãos. */
  tipos: string[];
  mun: Record<string, {
    pago: number; empenhado: number; n: number; tipos: number[]; intra: number;
    pessoas: number; empresas: number;
    /** [nome, CNPJ, pago, empenhos] dos maiores fornecedores */
    credores: [string, string, number, number][];
  }>;
}
const arquivos = import.meta.glob<DocPagamentos>("../../public/data/indicadores/pagamentos.json", { eager: true, import: "default" });
const doc: DocPagamentos | null = Object.values(arquivos)[0] ?? null;

export interface Credor { nome: string; cnpj: string; pago: number; empenhos: number }
export interface Pagamentos {
  fonte: string;
  ano: number;
  /** Tudo o que foi pago no ano, sem as operações entre unidades do próprio município. */
  pago: number;
  /** Operações entre unidades do município (a prefeitura pagando o próprio instituto de previdência). */
  intra: number;
  fornecedores: number;
  nFornecedores: number;
  pessoas: { n: number; valor: number };
  /** Folha, previdência, dívida e bancos, outros órgãos públicos: o que não é fornecedor. */
  outros: { folha: number; previdencia: number; divida: number; orgaos: number; total: number };
  credores: Credor[];
  /** Fatia dos 5 maiores no que foi pago a fornecedores. */
  cinco: number;
}

export function pagamentosDe(c: Cidade): Pagamentos | null {
  const v = doc?.mun[String(c.ibge)];
  if (!doc || !v || !v.pago) return null;
  const [fornecedores, pessoas, folha, previdencia, divida, orgaos] = v.tipos;
  const credores = v.credores.map(([nome, cnpj, pago, empenhos]) => ({ nome, cnpj, pago, empenhos }));
  const cinco = fornecedores ? credores.slice(0, 5).reduce((s, x) => s + x.pago, 0) / fornecedores : 0;
  return {
    fonte: doc.fonte, ano: doc.ano, pago: v.pago, intra: v.intra, fornecedores, nFornecedores: v.empresas,
    pessoas: { n: v.pessoas, valor: pessoas },
    outros: { folha, previdencia, divida, orgaos, total: folha + previdencia + divida + orgaos },
    credores, cinco,
  };
}
