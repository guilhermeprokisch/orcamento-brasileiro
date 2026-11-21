/**
 * As contas fecham? (página /contas), lido no build de pipeline/…/contas_federal.py: resultado primário
 * e nominal do Banco Central e despesas obrigatórias e discricionárias do Resultado do Tesouro Nacional.
 * Sem o arquivo, vem null.
 */

/** Resultado em % do PIB, com o sinal do dia a dia: positivo é sobra (superávit), negativo é falta (déficit). */
export interface Resultados {
  primario: (number | null)[];
  nominal: (number | null)[];
  juros: (number | null)[];
}

export interface DocContasFederal {
  fonte: string;
  gerado_em: string;
  /** 2002 … último ano fechado */
  anos: number[];
  /** setor público consolidado: União, estados, prefeituras e estatais */
  spc: Resultados;
  /** governo federal e Banco Central */
  central: Resultados;
  /** PIB de cada ano, R$ bilhões */
  pib: (number | null)[];
  /** Os 12 meses até o último mês publicado, quando ele não é dezembro: [primário, nominal, juros] */
  doze?: { ate: string; pib: number | null; spc: (number | null)[]; central: (number | null)[] };
  /** Resultado do Tesouro Nacional, tabela 2.1: despesa primária do governo central por tipo, R$ bilhões */
  rtn: {
    url: string;
    pagina: string;
    arquivo: string;
    anos: number[];
    repasses: (number | null)[];
    total: (number | null)[];
    previdencia: (number | null)[];
    pessoal: (number | null)[];
    outras: (number | null)[];
    controle: (number | null)[];
    discricionarias: (number | null)[];
  };
}

const arquivos = import.meta.glob<DocContasFederal>("../../public/data/federal/contas.json", { eager: true, import: "default" });
export const docContas: DocContasFederal | null = Object.values(arquivos)[0] ?? null;

/** As partes da despesa do governo central, da mais amarrada à mais livre. */
export const PARTES = [
  { chave: "previdencia", nome: "Aposentadorias e pensões do INSS", explica: "os benefícios da Previdência", cor: "#0a4a29" },
  { chave: "pessoal", nome: "Salários dos servidores", explica: "ativos, aposentados e pensionistas da União", cor: "#1f7a47" },
  { chave: "outras", nome: "Outras obrigatórias", explica: "BPC, abono e seguro-desemprego, Fundeb, precatórios, Legislativo e Judiciário", cor: "#4fae73" },
  { chave: "controle", nome: "Obrigatórias com ritmo controlado", explica: "Bolsa Família e parte da saúde: o valor é obrigatório, o mês do pagamento não", cor: "#8fcea8" },
  { chave: "discricionarias", nome: "O que o governo escolhe", explica: "investimentos, custeio dos ministérios, parte da saúde e da educação", cor: "#ffe14d" },
] as const;
export type ChaveParte = (typeof PARTES)[number]["chave"];
