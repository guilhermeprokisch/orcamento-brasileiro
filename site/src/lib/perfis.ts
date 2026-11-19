/**
 * Helpers usados só no build (páginas estáticas e índice de busca).
 * Lê os JSONs gerados pelo pipeline; se ele não rodou, tudo vem vazio.
 */
import { agrupar, escalar, proximaSugerida, type Dim, type DocAno, type Filtro, type Item, type ResumoAnos, type Valores } from "./dados";

const resumos = import.meta.glob<ResumoAnos>("../../public/data/explorer/anos.json", { eager: true, import: "default" });
const arquivos = import.meta.glob<DocAno>("../../public/data/explorer/[0-9]*.json", { eager: true, import: "default" });

export const resumo: ResumoAnos | null = Object.values(resumos)[0] ?? null;
export const docs: DocAno[] = Object.values(arquivos).sort((a, b) => a.ano - b.ano);
export const anoCorrente = new Date().getFullYear();

/** Último ano completo (o corrente ainda está em execução). */
export const anoBase: number | null =
  docs.filter((d) => d.ano < anoCorrente).at(-1)?.ano ?? docs.at(-1)?.ano ?? null;
export const docBase: DocAno | null = docs.find((d) => d.ano === anoBase) ?? null;

export const fatorIpca = (ano: number) => resumo?.ipca?.fatores[String(ano)] ?? 1;

export interface PontoSerie {
  ano: number;
  nominal: Valores;
  real: Valores;
}

/** Totais de cada ano para um filtro (nominal e corrigido pelo IPCA). */
export function serieHistorica(filtros: Filtro[]): PontoSerie[] {
  return docs.map((d) => {
    const nominal = agrupar(d, filtros, null).total;
    return { ano: d.ano, nominal, real: escalar(nominal, fatorIpca(d.ano)) };
  });
}

/** Itens de uma dimensão dentro de um filtro, no ano-base, do maior para o menor. */
export function maiores(filtros: Filtro[], por: Dim, ano = anoBase): Item[] {
  const d = docs.find((x) => x.ano === ano);
  if (!d) return [];
  return agrupar(d, filtros, por).itens
    .filter((i) => i.valores.atualizado > 0 || i.valores.realizado > 0)
    .sort((a, b) => b.valores.atualizado - a.valores.atualizado);
}

export function linkExplorer(filtros: Filtro[], extra: Record<string, string | number> = {}, ano = anoBase): string {
  const p = new URLSearchParams();
  if (ano) p.set("ano", String(ano));
  if (filtros.length) p.set("f", filtros.map((f) => `${f.dim}:${f.cod}`).join(","));
  const por = proximaSugerida(filtros);
  if (por) p.set("por", por);
  for (const [k, v] of Object.entries(extra)) p.set(k, String(v));
  return `/explorer?${p.toString().replaceAll("%3A", ":").replaceAll("%2C", ",")}`;
}

/** Órgãos que ganham página: os que existem no ano-base ou no ano corrente. */
export function orgaosComPerfil(): { cod: string; nome: string }[] {
  const mapa = new Map<string, string>();
  for (const d of docs.filter((x) => x.ano === anoBase || x.ano === anoCorrente)) {
    for (const [cod, nome] of Object.entries(d.dims.orgao)) if (!mapa.has(cod) || d.ano === anoBase) mapa.set(cod, nome);
  }
  return [...mapa].map(([cod, nome]) => ({ cod, nome })).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}
