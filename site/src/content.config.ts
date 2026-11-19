import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

/** Lições da seção Aprenda: uma por arquivo MDX, em src/content/licoes/<trilha>/NN-slug.mdx. */
const licoes = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/licoes" }),
  schema: z.object({
    trilha: z.enum(["orcamento", "dados"]),
    ordem: z.number(),
    titulo: z.string(),
    resumo: z.string(),
    minutos: z.number(),
    palavras: z.array(z.string()).default([]),
    fontes: z.array(z.string()).default([]),
    larga: z.boolean().default(false),
  }),
});

export const collections = { licoes };
