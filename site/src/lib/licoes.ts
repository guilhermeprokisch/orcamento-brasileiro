/** Lista ordenada das lições (as duas trilhas em sequência), para as páginas de Aprenda. */
import { getCollection, type CollectionEntry } from "astro:content";
import { TRILHAS, slugDe, type Trilha } from "./aprenda";

export type Licao = CollectionEntry<"licoes">;

const ORDEM_TRILHAS = Object.keys(TRILHAS) as Trilha[];

export async function todasAsLicoes(): Promise<Licao[]> {
  const todas = await getCollection("licoes");
  return todas.sort(
    (a, b) =>
      ORDEM_TRILHAS.indexOf(a.data.trilha) - ORDEM_TRILHAS.indexOf(b.data.trilha) || a.data.ordem - b.data.ordem,
  );
}

export const urlLicao = (l: Licao) => `/aprenda/${l.data.trilha}/${slugDe(l.id)}`;
/** chave usada no localStorage para marcar a lição como lida */
export const chaveLicao = (l: Licao) => `${l.data.trilha}/${slugDe(l.id)}`;
