/**
 * Autor das emendas → página do político (/data/politicos/autores.json), montado no build a partir de
 * lib/politicos.ts. A busca de emendas (/emendas/buscar?autor=) lê este arquivo para pôr o link no topo.
 * A chave é o slug do nome do autor (sem acento, minúsculas, hífens).
 */
import type { APIRoute } from "astro";
import { mapaAutores } from "../../../lib/politicos";

export const GET: APIRoute = () => new Response(JSON.stringify(mapaAutores()), { headers: { "Content-Type": "application/json" } });
