/**
 * O que o governo federal gastou ele mesmo em cada cidade: o valor pago pelas unidades federais
 * com endereço nela (universidades, institutos federais, quartéis, superintendências…).
 * Gerado por pipeline/…/gasto_federal.py; lido no build. Sem o arquivo, tudo vem null.
 */
import type { Cidade } from "./cidades";

interface DocGastoFederal {
  ano: number;
  meses: number;
  fonte: string;
  brasil: {
    total: number;
    pessoal: number;
    custeio: number;
    obras: number;
    /** Registrado em Brasília, onde ficam as sedes. */
    brasilia: number;
    /** Unidades sem cidade no cadastro (quase todas folhas de pagamento centrais em Brasília). */
    sem_cidade: number;
    exterior: number;
    /** Folha paga fora do DF por unidades que pagam servidores de várias cidades (Marinha e Aeronáutica, no Rio). */
    folha_central_fora_df: number;
    cidades: number;
  };
  orgaos: string[];
  /** ibge → [total, pessoal, custeio, obras, folha central, unidades, [[órgão, valor], …]] */
  mun: Record<string, [number, number, number, number, number, number, [number, number][]]>;
}

const arquivos = import.meta.glob<DocGastoFederal>("../../public/data/federal/gasto-direto.json", { import: "default" });
let doc: Promise<DocGastoFederal | null> | null = null;
const docGastoFederal = () => (doc ??= Object.values(arquivos)[0]?.() ?? Promise.resolve(null));

export interface GastoFederal {
  ano: number;
  fonte: string;
  total: number;
  partes: { nome: string; valor: number }[];
  /** Folha paga daqui a servidores de outras cidades. */
  folhaCentral: number;
  unidades: number;
  orgaos: { nome: string; valor: number }[];
  /** Totais do país, para o aviso sobre o que fica na sede. */
  brasil: DocGastoFederal["brasil"];
}

/**
 * O gasto federal direto na cidade. `null` só se o arquivo não existe; uma cidade sem nenhuma
 * unidade federal recebe total 0 (o bloco explica por quê).
 */
export async function gastoFederalEm(c: Cidade): Promise<GastoFederal | null> {
  const d = await docGastoFederal();
  if (!d) return null;
  const m = d.mun[String(c.ibge)];
  const [total, pessoal, custeio, obras, folhaCentral, unidades, maiores] = m ?? [0, 0, 0, 0, 0, 0, []];
  return {
    ano: d.ano, fonte: d.fonte, total, folhaCentral, unidades, brasil: d.brasil,
    partes: [
      { nome: "Salários de servidores da ativa", valor: pessoal },
      { nome: "Serviços, materiais e contas do dia a dia", valor: custeio },
      { nome: "Obras e equipamentos", valor: obras },
    ].filter((p) => p.valor > 0),
    orgaos: maiores.map(([i, valor]) => ({ nome: d.orgaos[i], valor })),
  };
}
