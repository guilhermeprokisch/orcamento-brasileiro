/**
 * Nota de capacidade de pagamento (CAPAG) do Tesouro Nacional, lida no build de
 * pipeline/…/capag.py. Sem o arquivo, tudo vem null.
 */
import { docCidades, type Cidade } from "./cidades";

type Linha = [string | null, number | null, string | null, number | null, string | null, number | null, string | null, number | null];
interface DocCapag {
  fonte: string;
  mun: { versao: string; notas: Record<string, Linha> };
  uf: { versao: string; notas: Record<string, Linha> };
}
const arquivos = import.meta.glob<DocCapag>("../../public/data/indicadores/capag.json", { eager: true, import: "default" });
const doc: DocCapag | null = Object.values(arquivos)[0] ?? null;

export interface Parcial {
  valor: number | null;
  nota: string | null;
}
export interface Capag {
  fonte: string;
  /** "setembro de 2026" */
  quando: string;
  /** Ano das contas avaliadas, quando o Tesouro informa. */
  anoBase: number | null;
  nota: string | null;
  endividamento: Parcial;
  poupanca: Parcial;
  liquidez: Parcial;
  /** Parte dos comparáveis (cidades do mesmo porte ou estados) com nota A ou B; e quantos têm nota. */
  boas: number | null;
  comparaveis: number;
}

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
/** "Capag Municípios 2026 - 01/09/2026" -> "setembro de 2026"; "Capag Estados 2026" -> "2026". */
function quando(versao: string): string {
  const d = versao.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (d) return `${MESES[Number(d[2]) - 1]} de ${d[3]}`;
  return versao.match(/\d{4}/)?.[0] ?? versao;
}
const boa = (n: string | null) => !!n && (n[0] === "A" || n[0] === "B");

export function capagDe(c: Cidade, esfera: "mun" | "uf"): Capag | null {
  if (!doc) return null;
  const base = doc[esfera];
  const l = base.notas[String(c.ibge)];
  if (!l) return null;
  let pares: (string | null)[];
  if (esfera === "uf") pares = Object.entries(base.notas).filter(([k]) => k !== "53").map(([, v]) => v[0]);
  else pares = (docCidades?.cidades ?? []).filter((x) => x.faixa === c.faixa && x.ibge !== 53).map((x) => base.notas[String(x.ibge)]?.[0] ?? null);
  const comNota = pares.filter((n): n is string => !!n);
  return {
    fonte: doc.fonte, quando: quando(base.versao), anoBase: l[7], nota: l[0],
    endividamento: { valor: l[1], nota: l[2] }, poupanca: { valor: l[3], nota: l[4] }, liquidez: { valor: l[5], nota: l[6] },
    boas: comNota.length >= 10 ? comNota.filter(boa).length / comNota.length : null, comparaveis: comNota.length,
  };
}
