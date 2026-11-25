/**
 * O resumo de cada cidade e de cada estado que dá para seguir por e-mail (lib/resumo.ts).
 * Lido pelas funções de inscrição (o nome do lugar) e pelo envio mensal (.github/scripts/boletim.py).
 */
import type { APIRoute, GetStaticPaths } from "astro";
import { alvoDe, entesParaSeguir, resumoDe } from "../../../lib/resumo";

export const getStaticPaths: GetStaticPaths = () =>
  entesParaSeguir().map(({ c, esfera }) => ({ params: { alvo: alvoDe(c, esfera) }, props: { c, esfera } }));

export const GET: APIRoute = async ({ props }) => {
  const r = await resumoDe(props.c, props.esfera);
  return new Response(JSON.stringify(r), { headers: { "Content-Type": "application/json; charset=utf-8" } });
};
