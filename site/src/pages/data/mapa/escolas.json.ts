/**
 * Ideb da rede municipal e alunos das escolas da prefeitura para o mapa (/data/mapa/escolas.json),
 * montados no build a partir de indicadores/ideb.json e indicadores/matriculas.json (lib/indicadores.ts).
 * O mapa baixa este arquivo na abertura: a nota das escolas, o gasto por aluno e o cruzamento dos dois dependem dele.
 */
import type { APIRoute } from "astro";
import { escolasParaMapa } from "../../../lib/indicadores";

export const GET: APIRoute = () => new Response(JSON.stringify(escolasParaMapa()), { headers: { "Content-Type": "application/json" } });
