/**
 * As fichas de um ano (lib/ficha.ts), para as páginas de cidade e de estado trocarem de ano no
 * navegador: /dados/fichas/{ano}/{uf}.json com as cidades de um estado e
 * /dados/fichas/{ano}/estados.json com os 27 governos estaduais.
 */
import type { APIRoute, GetStaticPaths } from "astro";
import { NOMES_UF } from "../../../../lib/cidades";
import { docDa, fichaDe, pacoteDe, type Ficha } from "../../../../lib/ficha";

export const getStaticPaths: GetStaticPaths = () => {
  const ufs = Object.keys(NOMES_UF).map((uf) => uf.toLowerCase());
  return [
    ...(docDa("mun")?.anos ?? []).flatMap((ano) => ufs.map((grupo) => ({ params: { ano: String(ano), grupo } }))),
    ...(docDa("uf")?.anos ?? []).map((ano) => ({ params: { ano: String(ano), grupo: "estados" } })),
  ];
};

export const GET: APIRoute = async ({ params }) => {
  const ano = Number(params.ano), grupo = params.grupo!;
  const esfera = grupo === "estados" ? "uf" : "mun";
  const doc = docDa(esfera)!;
  const lista = esfera === "uf" ? doc.cidades : doc.cidades.filter((c) => c.uf.toLowerCase() === grupo);
  const entes: Record<string, Ficha> = {};
  for (const c of lista) {
    const f = await fichaDe(c, esfera, ano);
    if (f) entes[c.ibge] = f;
  }
  return new Response(JSON.stringify({ ...pacoteDe(esfera, ano), entes }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
};
