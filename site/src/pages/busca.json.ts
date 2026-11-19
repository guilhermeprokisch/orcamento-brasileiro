/**
 * Índice de busca gerado no build: um item por (dimensão, código), com o nome
 * e o valor mais recentes. Formato compacto: [tipo, código, nome, ano, dotação].
 */
import type { APIRoute } from "astro";
import { anoCorrente, docs } from "../lib/perfis";
import type { Dim } from "../lib/dados";

const DIMS: Dim[] = ["orgao", "funcao", "subfuncao", "uo", "programa", "acao"];

export const GET: APIRoute = () => {
  const itens = new Map<string, [Dim, string, string, number, number]>();
  // Anos completos em ordem crescente (o mais recente sobrescreve) e, por último,
  // o ano corrente só para o que não existia antes.
  const ordem = [...docs.filter((d) => d.ano !== anoCorrente), ...docs.filter((d) => d.ano === anoCorrente)];
  for (const d of ordem) {
    const soNovos = d.ano === anoCorrente;
    const iVal = d.colunas.indexOf("atualizado");
    for (const dim of DIMS) {
      const i = d.colunas.indexOf(dim);
      const somas = new Map<string, number>();
      for (const l of d.linhas) somas.set(l[i] as string, (somas.get(l[i] as string) ?? 0) + (l[iVal] as number));
      for (const [cod, nome] of Object.entries(d.dims[dim])) {
        if (soNovos && itens.has(`${dim}:${cod}`)) continue;
        itens.set(`${dim}:${cod}`, [dim, cod, nome, d.ano, Math.round(somas.get(cod) ?? 0)]);
      }
    }
  }
  return new Response(JSON.stringify({ v: 1, itens: [...itens.values()] }), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
};
