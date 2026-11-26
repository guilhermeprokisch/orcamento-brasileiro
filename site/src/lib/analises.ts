/**
 * A seção Análises: a lista das análises publicadas e os números da análise emendas × votos.
 *
 * Os números vêm de analises/emendas-votos/resultados.json, que é a cópia, no repositório, do que o comando
 * `uv run analise-emendas-votos` gravou e publicou no espelho (pipeline/…/analise_emendas_votos.py). A página não
 * refaz conta nenhuma: só troca o formato, de coeficiente para reais ("se uma cidade recebe R$ 100…").
 */
import resultados from "../../../analises/emendas-votos/resultados.json";

const REPO = "https://github.com/orcamento-brasileiro/orcamento-brasileiro/tree/main/analises";

export interface Analise {
  slug: string;
  titulo: string;
  /** A resposta em uma frase, em negrito na lista e no alto da página. */
  resposta: string;
  resumo: string;
  data: string;          // AAAA-MM-DD
  temas: string[];
  fontes: string;
  github: string;
}

export const GITHUB_ANALISES = REPO;

export const ANALISES: Analise[] = [
  {
    slug: "emendas-votos",
    titulo: "Emenda parlamentar: para todas as cidades ou só para as que deram voto?",
    resposta: "Para as que deram mais voto. A cidade onde o deputado não teve voto quase nunca vê emenda dele.",
    resumo: `Cruzamos R$ ${Math.round(resultados.painel.emendas_bi)} bilhões em emendas pagas de 2023 a 2026 com os votos de ${resultados.painel.deputados} deputados em cada cidade. O tamanho da cidade quase não conta.`,
    data: "2026-11-25",
    temas: ["Emendas parlamentares", "Eleições"],
    fontes: "Portal da Transparência, FNS, TSE, IBGE",
    github: `${REPO}/emendas-votos`,
  },
];

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
/** "2026-11-25" → "25 de novembro de 2026". */
export function dataPorExtenso(iso: string): string {
  const [a, m, d] = iso.split("-").map(Number);
  return `${d} de ${MESES[m - 1]} de ${a}`;
}

// ---------------------------------------------------------------- formato

/** Um coeficiente de elasticidade → quanto recebe a cidade com o dobro (de votos, de moradores), se a outra recebe R$ 100. */
const comODobro = (coef: number) => Math.round(100 * 2 ** coef);
/** Uma diferença em fração (0,65 = +65%) → reais para cada R$ 100. */
const para100 = (fracao: number) => Math.round(100 * (1 + fracao));
/** 0,047 → "5%". */
export const porcento = (fracao: number) => `${Math.round(fracao * 100)}%`;
/** 6.5 → "6,5". */
export const decimal = (v: number, casas = 1) => v.toFixed(casas).replace(".", ",");
/** 30,77 → "31"; 4,83 → "4,8"; 0,19 → "0,2". */
export const vezes = (v: number) => (v >= 10 ? String(Math.round(v)) : v === 1 ? "1" : decimal(v));

// ---------------------------------------------------------------- emendas × votos

const r = resultados;
const dono = r.dono_do_municipio;
const anosPagamento = Object.keys(r.robustez.veteranos_por_ano_de_pagamento) as (keyof typeof r.robustez.veteranos_por_ano_de_pagamento)[];
const pref = r.prefeitos_2024;
const situacoes = [
  { chave: "prefeito_do_partido", nome: "O prefeito eleito é do partido do deputado" },
  { chave: "partido_na_coligacao", nome: "O partido do deputado apoiou o prefeito eleito" },
  { chave: "partido_disputou_e_perdeu", nome: "O partido do deputado disputou e perdeu" },
] as const;

export const EMENDAS_VOTOS = {
  bilhoes: Math.round(r.painel.emendas_bi),
  deputados: r.painel.deputados,
  /** Se uma cidade recebe R$ 100: a que deu o dobro de votos, e a que tem o dobro de moradores. */
  dobroDeVotos: comODobro(r.elasticidades.votos_e_populacao.votos.coef),
  dobroDeMoradores: comODobro(r.elasticidades.votos_e_populacao.populacao.coef),
  chanceSemVoto: dono[0].chance_receber,
  chanceMaisDaMetade: dono[dono.length - 1].chance_receber,
  vezesDono: Math.round(dono[dono.length - 1].multiplicador),
  /** O "dono" da cidade: uma linha por faixa da fatia dos votos da cidade que foi do deputado. */
  dono: dono.map((f, i) => ({
    faixa: f.fatia_local === "zero voto" ? "nenhum voto" : f.fatia_local,
    vezes: f.multiplicador,
    chance: f.chance_receber,
    semVoto: i === 0,
  })),
  /** Por ano de pagamento, entre os veteranos: quanto recebe a cidade com o dobro de votos, para cada R$ 100. */
  porAno: anosPagamento.map((ano) => ({ ano, reais: comODobro(r.robustez.veteranos_por_ano_de_pagamento[ano].votos.coef) })),
  /** Prefeitos de 2024: para cada R$ 100 na cidade onde o partido ficou de fora, antes e depois da posse. */
  prefeitos: situacoes.map((s) => ({
    nome: s.nome,
    antes: para100(pref.destino_da_emenda_2023_24[s.chave].em_porcentagem),
    depois: para100(pref.destino_da_emenda_2025_26[s.chave].em_porcentagem),
  })),
  ganharAPrefeitura: pref.ganhar_a_prefeitura_depois_x_antes.em_porcentagem,
  /** Votos de 2026. */
  votos: {
    deputados: r.votos_2026.deputados,
    comEmenda: r.votos_2026.associacao.recebeu_em_porcentagem,
    porAno: Object.entries(r.votos_2026.associacao_por_ano_de_pagamento).map(([ano, v]) => ({ ano, diferenca: v.em_porcentagem })),
    cresceuComEmenda: r.votos_2026.variacao_com_emenda,
    cresceuSemEmenda: r.votos_2026.variacao_sem_emenda,
  },
  /** As três tentativas de tirar o aliado da conta: a diferença sem e com o controle. */
  aliado: [
    {
      nome: "a base antiga do deputado: os votos dele em 2018",
      de: r.votos_2018.votos_2026_sem_controlar_2018.recebeu.em_porcentagem,
      para: r.votos_2018.votos_2026_controlando_2018.recebeu.em_porcentagem,
    },
    {
      nome: "o prefeito do partido dele, eleito em 2024",
      de: pref.votos_2026.so_emenda.recebeu.em_porcentagem,
      para: pref.votos_2026.emenda_e_prefeito.recebeu.em_porcentagem,
    },
    {
      nome: "o grupo local: o deputado estadual que faz campanha junto com ele*",
      de: r.dobradinhas.votos_2026.so_emenda.recebeu.em_porcentagem,
      para: r.dobradinhas.votos_2026.controlando_parceiros_em_2022_e_2026.recebeu.em_porcentagem,
    },
  ],
  dobradinhas: {
    deputadosNaConta: r.dobradinhas.votos_2026.so_emenda.deputados,
    deputadosComParceiro: r.dobradinhas.deputados_com_parceiro,
    ganhoDoDeputado: r.dobradinhas.votos_2026.so_emenda.recebeu.em_porcentagem,
    ganhoDoParceiro: r.dobradinhas.votos_dos_parceiros_2026.recebeu.em_porcentagem,
  },
  estadualBi: r.painel.pagas_a_governo_estadual_bi,
};
