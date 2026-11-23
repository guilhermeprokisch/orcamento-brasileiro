/**
 * Saiu daqui, voltou: o imposto federal que saiu de cada cidade e estado e o que voltou da União, em 2025.
 * Gerado por pipeline/…/saiu_voltou.py (ver docs/levantamento-saiu-voltou.md); lido no build.
 * Sem o arquivo, tudo vem null e a seção some.
 */

type Linha = (number | null)[];

interface DocSaiuVoltou {
  ano: number;
  ano_pib: number;
  fonte: string;
  colunas: string[];
  brasil: {
    pop: number;
    saiu: number;
    voltou_cidades: number;
    voltou_estados: number;
    /** Gasto dos órgãos federais registrado em Brasília que atende o país (sem o Fundo Constitucional do DF). */
    fora_brasilia: number;
    /** Folha da Marinha e da Aeronáutica paga do Rio para o país. */
    fora_rio: number;
    fcdf: number;
  };
  /** ibge (o DF é "53") → valores na ordem de `colunas` */
  mun: Record<string, Linha>;
  /** sigla → valores na ordem de `colunas`, mais o repasse ao governo do estado */
  uf: Record<string, Linha>;
}

const arquivos = import.meta.glob<DocSaiuVoltou>("../../public/data/federal/saiu-voltou.json", { import: "default" });
let doc: Promise<DocSaiuVoltou | null> | null = null;
const docSaiuVoltou = () => (doc ??= Object.values(arquivos)[0]?.() ?? Promise.resolve(null));

export interface Parte {
  nome: string;
  valor: number;
  /** Explicação curta, embaixo do nome. */
  nota?: string;
  /** O pedaço da frase: "em aposentadorias do INSS". */
  frase: string;
}

export interface SaiuVoltou {
  ano: number;
  anoPib: number;
  fonte: string;
  pop: number;
  /** Imposto federal recolhido aqui pela Receita (medido). */
  saiu: number;
  /** O imposto federal do país repartido pela parte daqui no PIB (estimado); null sem PIB. */
  estimado: number | null;
  voltou: number;
  partes: Parte[];
  emendas: number;
  /** De cada R$ 1 que saiu: pelo recolhido e pelo estimado. */
  razao: number | null;
  razaoEstimada: number | null;
  /** A média do país: o que volta às cidades (e, para um estado, também aos governos estaduais) de cada R$ 1. */
  brasil: DocSaiuVoltou["brasil"] & { razao: number };
}

/** A conta para uma cidade (esfera "mun", pelo código do IBGE) ou um estado (esfera "uf", pela sigla). */
export async function saiuVoltou(esfera: "mun" | "uf", chave: string): Promise<SaiuVoltou | null> {
  const d = await docSaiuVoltou();
  const l = d?.[esfera][chave];
  if (!d || !l) return null;
  const v = (c: string) => l[d.colunas.indexOf(c)] ?? 0;
  const governoEstadual = esfera === "uf" ? l[d.colunas.length] ?? 0 : 0;
  const ehDF = chave === "53" || chave === "DF";
  const partes: Parte[] = [
    { nome: "Aposentadorias e pensões do INSS", valor: v("inss"), frase: "em aposentadorias e pensões do INSS" },
    { nome: ehDF ? "Repasses ao governo do DF" : esfera === "uf" ? "Repasses às prefeituras" : "Repasses à prefeitura", valor: v("fpm") + v("sus") + v("fundeb") + v("outros_repasses"), nota: ehDF ? "FPE, SUS, Fundeb, convênios, emendas" : "FPM, SUS, Fundeb, merenda, convênios, emendas", frase: ehDF ? "em repasses ao governo do DF" : esfera === "uf" ? "em repasses às prefeituras" : "em repasses à prefeitura" },
    { nome: "Ao governo do estado", valor: governoEstadual, nota: "FPE, SUS, Fundeb, convênios, emendas", frase: "em repasses ao governo do estado" },
    { nome: "Bolsa Família e BPC", valor: v("bolsa_familia") + v("bpc"), nota: "pagos direto às pessoas", frase: "em Bolsa Família e BPC" },
    { nome: "O que os órgãos federais gastaram aqui", valor: v("gasto_direto"), nota: ehDF ? "só o Fundo Constitucional do DF" : "universidades, hospitais, quartéis, obras", frase: ehDF ? "no Fundo Constitucional do DF" : "no que os órgãos federais gastaram aqui" },
    { nome: "A outras entidades daqui", valor: v("entidades"), nota: "associações, hospitais filantrópicos, consórcios", frase: "em repasses a outras entidades" },
  ].filter((p) => p.valor > 0);
  const voltou = partes.reduce((s, p) => s + p.valor, 0);
  const saiu = v("saiu");
  const estimado = l[d.colunas.indexOf("estimado")];
  return {
    ano: d.ano, anoPib: d.ano_pib, fonte: d.fonte, pop: v("pop"), saiu, estimado, voltou,
    partes: partes.sort((a, b) => b.valor - a.valor), emendas: v("emendas"),
    razao: saiu > 0 ? voltou / saiu : null,
    razaoEstimada: estimado ? voltou / estimado : null,
    brasil: { ...d.brasil, razao: (d.brasil.voltou_cidades + (esfera === "uf" ? d.brasil.voltou_estados : 0)) / d.brasil.saiu },
  };
}

/** Os totais do país, para o atalho de /impostos. */
export async function brasilSaiuVoltou(): Promise<{ ano: number; razao: number } | null> {
  const d = await docSaiuVoltou();
  return d ? { ano: d.ano, razao: d.brasil.voltou_cidades / d.brasil.saiu } : null;
}
