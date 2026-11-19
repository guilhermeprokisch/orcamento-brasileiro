/**
 * Números reais usados nas lições (calculados no build, a partir dos mesmos
 * dados do Explorer). Assim o texto acompanha a atualização diária.
 */
import { agrupar, type Filtro, type Valores } from "./dados";
import { anoBase, anoCorrente, docBase, docs, fatorIpca, linkExplorer } from "./perfis";
import { moedaCurta, moedaExtenso } from "./formato";

export const TRILHAS = {
  orcamento: { nome: "Entenda o orçamento", resumo: "Quem decide, de onde vem o dinheiro, para onde vai e quem fiscaliza." },
  dados: { nome: "Aprenda a ler os dados", resumo: "Como usar o Explorer, o que cada número quer dizer e como comparar sem se enganar. Com exercícios usando os dados reais." },
} as const;
export type Trilha = keyof typeof TRILHAS;

/** "03-caminho-de-cada-real" → "caminho-de-cada-real" */
export const slugDe = (id: string) => id.split("/").at(-1)!.replace(/^\d+-/, "");

const zero: Valores = { inicial: 0, atualizado: 0, empenhado: 0, realizado: 0 };
function total(filtros: Filtro[], ano = anoBase, semRefin = false): Valores {
  const d = docs.find((x) => x.ano === ano) ?? null;
  return d ? agrupar(d, filtros, null, semRefin).total : zero;
}

export const ANO = anoBase ?? new Date().getFullYear() - 1;
export const PRIMEIRO_ANO = docs[0]?.ano ?? 2014;

export const federal = total([]);
export const federalSemRefin = total([], ANO, true);
export const refinanciamento = federal.atualizado - federalSemRefin.atualizado;
export const parcelaRefin = federal.atualizado ? refinanciamento / federal.atualizado : 0;

export const saude = total([{ dim: "orgao", cod: "36000" }]);
export const atencaoPrimaria = total([{ dim: "orgao", cod: "36000" }, { dim: "programa", cod: "5119" }]);
export const fazenda = total([{ dim: "orgao", cod: "25000" }]);
export const fazendaSemRefin = total([{ dim: "orgao", cod: "25000" }], ANO, true);
export const presidencia = total([{ dim: "orgao", cod: "20000" }]);

const educacaoInicio = total([{ dim: "funcao", cod: "12" }], PRIMEIRO_ANO);
export const educacao = {
  anoInicio: PRIMEIRO_ANO,
  inicioNominal: educacaoInicio.atualizado,
  inicioReal: educacaoInicio.atualizado * fatorIpca(PRIMEIRO_ANO),
  base: total([{ dim: "funcao", cod: "12" }]).atualizado,
};
export const fatorInicio = fatorIpca(PRIMEIRO_ANO);

/** Grupos de despesa (GND) do ano-base, do maior para o menor. */
export const gnds = docBase
  ? agrupar(docBase, [], "gnd", true).itens.sort((a, b) => b.valores.atualizado - a.valores.atualizado)
  : [];

/** Soma de qualquer recorte no ano-base (sem refinanciamento por padrão, como o Explorer mostra a parcela). */
export const valor = (filtros: Filtro[], semRefin = true) => total(filtros, ANO, semRefin);
const f = (dim: Filtro["dim"], cod: string): Filtro => ({ dim, cod });

export const ANO_CORRENTE = anoCorrente;
export const contagem = (() => {
  const doc = docBase;
  const conta = (dim: Filtro["dim"]) => {
    if (!doc) return 0;
    const i = doc.colunas.indexOf(dim);
    return new Set(doc.linhas.map((l) => l[i])).size;
  };
  return { orgaos: conta("orgao"), uos: conta("uo"), funcoes: conta("funcao"), subfuncoes: conta("subfuncao"), programas: conta("programa"), acoes: conta("acao"), gnds: conta("gnd") };
})();

// recortes usados nas lições (ano-base)
export const funcaoSaude = valor([f("funcao", "10")]);
export const saudeNaPrevidencia = valor([f("orgao", "36000"), f("funcao", "09")]);
export const fundoSaude = valor([f("uo", "36901")], false);
export const atencaoEspecializada = valor([f("orgao", "36000"), f("programa", "5118")], false);
export const previdencia = valor([f("funcao", "09")]);
export const previdenciaBasica = valor([f("funcao", "09"), f("subfuncao", "271")]);
export const encargosEspeciais = valor([f("funcao", "28")]);
export const transferencias = valor([f("subfuncao", "845")]);
export const educacaoBasicaTransf = valor([f("subfuncao", "847")]);
export const servicoDividaInterna = valor([f("subfuncao", "843")]);
export const bolsaFamilia = valor([f("programa", "5128")], false);
export const educacaoMinisterio = valor([f("orgao", "26000")], false);
export const gnd = {
  pessoal: valor([f("gnd", "1")]),
  juros: valor([f("gnd", "2")]),
  custeio: valor([f("gnd", "3")]),
  investimentos: valor([f("gnd", "4")]),
  inversoes: valor([f("gnd", "5")]),
  amortizacao: valor([f("gnd", "6")]),
  amortizacaoComRefin: valor([f("gnd", "6")], false),
  reserva: valor([f("gnd", "9")]),
};
export const reservaFuncao = valor([f("funcao", "99")], false);
export const fpm = valor([f("acao", "0045")]);
export const fpe = valor([f("acao", "0044")]);
/** transferências especiais: as emendas individuais que vão direto ao caixa do estado ou município */
export const transferenciasEspeciais = valor([f("acao", "0EC2")]);

/** Link para o Explorer com filtros, no ano-base. */
export const link = (filtros: [Filtro["dim"], string][] = [], extra: Record<string, string | number> = {}) =>
  linkExplorer(filtros.map(([dim, cod]) => f(dim, cod)), extra, ANO);
/** parcela de a em b */
export const de = (a: number, b: number) => (b ? a / b : 0);
/** pago ÷ autorizado */
export const pagoDe = (v: Valores) => de(v.realizado, v.atualizado);
export const empenhadoDe = (v: Valores) => de(v.empenhado, v.atualizado);

// formatação para o texto corrido
export const bi = (v: number) => moedaExtenso(v);
export const curto = (v: number) => moedaCurta(v);
export const pctInt = (v: number) => `${Math.round(v * 100)}%`;
export const pct1 = (v: number) => `${(v * 100).toFixed(1).replace(".", ",")}%`;
export const explorer = (q = "") => `/explorer?ano=${ANO}${q ? `&${q}` : ""}`;

/** "95" → "cerca de 1h35"; "55" → "55 min" */
export function duracao(min: number): string {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = Math.round((min % 60) / 5) * 5;
  return `cerca de ${h}h${m ? String(m).padStart(2, "0") : ""}`;
}
