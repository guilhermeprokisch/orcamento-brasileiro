/**
 * RASCUNHO (página /comparar). Os indicadores que não mudam com o ano das contas, para comparar
 * dois lugares no navegador: /dados/comparar/{uf}.json com as cidades de um estado e
 * /dados/comparar/estados.json com os 27 governos estaduais. O gasto, a receita e o saldo de cada
 * ano vêm das fichas (/dados/fichas/{ano}/{grupo}.json), que já existem para a troca de ano.
 */
import type { APIRoute, GetStaticPaths } from "astro";
import { docCidades, docEstados, NOMES_UF, type Cidade } from "../../../lib/cidades";
import { anosDe } from "../../../lib/ficha";
import { dividaDe, LIMITES } from "../../../lib/divida";
import { emendasDe, homicidiosDe, idebDe, mortalidadeDe, porAlunoDe, porAlunoEstado } from "../../../lib/indicadores";
import type { LugarComparado } from "../../../lib/comparar";

export const getStaticPaths: GetStaticPaths = () => [
  ...Object.keys(NOMES_UF).map((uf) => ({ params: { grupo: uf.toLowerCase() } })),
  { params: { grupo: "estados" } },
];

const arred = (v: number, casas = 2) => Math.round(v * 10 ** casas) / 10 ** casas;

function lugar(c: Cidade, esfera: "mun" | "uf", estados: Cidade[]): LugarComparado {
  const ehDF = c.ibge === 53;
  const div = ehDF && esfera === "mun" ? null : dividaDe(c.ibge, esfera);
  const ideb = esfera === "mun" ? idebDe(c) : null;
  const aluno = esfera === "mun" ? (ehDF ? null : porAlunoDe(c)) : porAlunoEstado(c, estados);
  const mort = ehDF && esfera === "mun" ? null : mortalidadeDe(c, esfera);
  const em = emendasDe(c, esfera);
  const hom = ehDF && esfera === "mun" ? null : homicidiosDe(c, esfera);
  return {
    ibge: c.ibge, nome: c.nome, uf: c.uf, capital: c.capital, pop: c.pop, anos: anosDe(c),
    divida: div ? [div.ultimo.ano, Math.round(div.ultimo.liquida), Math.round(div.ultimo.rcl)] : null,
    ideb: ideb && (ideb.mi?.nota != null || ideb.mf?.nota != null) ? [ideb.mi?.nota ?? null, ideb.mf?.nota ?? null] : null,
    porAluno: aluno ? [aluno.ano, Math.round(aluno.porAluno)] : null,
    mortalidade: mort?.taxa != null ? arred(mort.taxa, 1) : null,
    emendas: em ? [em.ano, Math.round(em.total)] : null,
    homicidios: hom ? [hom.ano, arred(hom.taxa, 1)] : null,
  };
}

export const GET: APIRoute = async ({ params }) => {
  const grupo = params.grupo!;
  const esfera = grupo === "estados" ? "uf" : "mun";
  const estados = docEstados?.cidades ?? [];
  const lista = esfera === "uf" ? estados : (docCidades?.cidades ?? []).filter((c) => c.uf.toLowerCase() === grupo);
  const entes: Record<string, LugarComparado> = {};
  for (const c of lista) entes[c.ibge] = lugar(c, esfera, estados);
  const ideb = esfera === "mun" ? lista.map(idebDe).find(Boolean) : null;
  const mort = lista.map((c) => mortalidadeDe(c, esfera)).find(Boolean);
  return new Response(JSON.stringify({
    esfera,
    limiteDivida: LIMITES[esfera],
    idebEdicao: ideb?.edicao ?? null,
    mortalidadeAnos: mort?.anos ?? [],
    entes,
  }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
};
