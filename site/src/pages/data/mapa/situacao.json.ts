/**
 * Os números de "Como está a cidade" para o mapa (/data/mapa/situacao.json): mortalidade infantil,
 * homicídios, água e esgoto de cada cidade e estado, montados no build a partir dos arquivos de
 * indicadores (lib/indicadores.ts). O mapa só baixa este arquivo quando alguém escolhe uma dessas perguntas.
 */
import type { APIRoute } from "astro";
import { situacaoParaMapa } from "../../../lib/indicadores";

export const GET: APIRoute = () => new Response(JSON.stringify(situacaoParaMapa()), { headers: { "Content-Type": "application/json" } });
