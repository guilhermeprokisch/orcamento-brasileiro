/** Lista compacta para a busca de cidades: [nome, UF, caminho, população]. */
import type { APIRoute } from "astro";
import { caminhoCidade, docCidades } from "../../lib/cidades";

export const GET: APIRoute = () => {
  const itens = (docCidades?.cidades ?? []).map((c) => [c.nome, c.uf, caminhoCidade(c), c.pop]);
  return new Response(JSON.stringify(itens), { headers: { "Content-Type": "application/json; charset=utf-8" } });
};
