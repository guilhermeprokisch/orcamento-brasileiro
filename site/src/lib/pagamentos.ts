/**
 * Para quem cada prefeitura pagou no ano: os empenhos que o Tribunal de Contas do estado publica
 * (por enquanto Paraíba, Acre e Santa Catarina; pipeline/…/pagamentos.py e pagamentos_qlik.py).
 * Um arquivo por estado: pagamentos.json (PB) e pagamentos-{uf}.json. Lido no build; sem arquivo, tudo vem null.
 */
import type { Cidade } from "./cidades";

interface DocPagamentos {
  fonte: string;
  ano: number;
  uf: string;
  /** Rótulo de cada posição de "tipos": fornecedores, pessoas físicas, folha, previdência, dívida e bancos, outros órgãos. */
  tipos: string[];
  /** Que unidades do município entram no total ("a prefeitura, a Câmara e…"), quando o estado diz; senão, o texto padrão. */
  entra?: string;
  mun: Record<string, {
    /** Quando a cidade tem fonte ou unidades diferentes das do estado (a capital de SP, pelo TCM-SP). */
    fonte?: string; entra?: string;
    pago: number; empenhado: number; n: number; tipos: number[]; intra: number;
    pessoas: number; empresas: number;
    /** [nome, CNPJ, pago, empenhos] dos maiores fornecedores */
    credores: [string, string, number, number][];
  }>;
}
const arquivos = import.meta.glob<DocPagamentos>("../../public/data/indicadores/pagamentos*.json", { eager: true, import: "default" });
const docs = Object.values(arquivos);
/** Estados com o arquivo de pagamentos no build (PB, AC, SC…). */
export const ufsComPagamentos = (): string[] => docs.map((d) => d.uf.toUpperCase());

export interface Credor { nome: string; cnpj: string; pago: number; empenhos: number }
export interface Pagamentos {
  fonte: string;
  ano: number;
  /** Que unidades do município entram no total, quando o arquivo diz (SP); null usa o texto padrão. */
  entra: string | null;
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
  const doc = docs.find((d) => d.mun[String(c.ibge)]);
  const v = doc?.mun[String(c.ibge)];
  if (!doc || !v || !v.pago) return null;
  const [fornecedores, pessoas, folha, previdencia, divida, orgaos] = v.tipos;
  const credores = v.credores.map(([nome, cnpj, pago, empenhos]) => ({ nome, cnpj, pago, empenhos }));
  const cinco = fornecedores ? credores.slice(0, 5).reduce((s, x) => s + x.pago, 0) / fornecedores : 0;
  return {
    fonte: v.fonte ?? doc.fonte, ano: doc.ano, entra: v.entra ?? doc.entra ?? null, pago: v.pago, intra: v.intra, fornecedores, nFornecedores: v.empresas,
    pessoas: { n: v.pessoas, valor: pessoas },
    outros: { folha, previdencia, divida, orgaos, total: folha + previdencia + divida + orgaos },
    credores, cinco,
  };
}
