import { scaleLinear } from "d3-scale";

/**
 * Cores de dados da direção editorial (mock "E · B refinado").
 * Rampa verde do maior valor (escuro) ao menor (claro); amarelo = destaque;
 * areia = "outros". Validada com o validador de paletas da skill de dataviz.
 */
export const RAMPA = ["#0a4a29", "#1f7a47", "#4fae73", "#74c193", "#8fcea8", "#b3dfc4"];
export const DESTAQUE = "#ffe14d";
export const OUTRAS = "#ddd5c3";

const escala = scaleLinear<string>()
  .domain(RAMPA.map((_, i) => i / (RAMPA.length - 1)))
  .range(RAMPA)
  .clamp(true);

/** t = 0 → verde mais escuro (maior valor); t = 1 → mais claro. */
export function corDaRampa(t: number): string {
  return escala(t);
}

/** Até onde da rampa o texto deve ser branco (fundos escuros). */
export const LIMIAR_TEXTO_ESCURO = 0.35;
