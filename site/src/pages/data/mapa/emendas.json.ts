/**
 * As emendas parlamentares para o mapa (/data/mapa/emendas.json), montadas no build a partir de
 * indicadores/emendas.json (lib/indicadores.ts). O mapa baixa este arquivo em segundo plano.
 */
import type { APIRoute } from "astro";
import { emendasParaMapa } from "../../../lib/indicadores";

export const GET: APIRoute = () => new Response(JSON.stringify(emendasParaMapa() ?? {}), { headers: { "Content-Type": "application/json" } });
