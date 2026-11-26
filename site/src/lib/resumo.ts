/**
 * O resumo de uma cidade ou de um estado para o e-mail de quem segue (seguir/resumo/[alvo].json.ts).
 *
 * Cada seção tem uma `chave` que muda quando sai dado novo (o ano das contas, o mês do relatório
 * bimestral, a edição da nota do Tesouro). O envio (.github/scripts/boletim.py) guarda a última
 * chave mandada para cada pessoa e só manda a seção de novo quando a chave muda. Os textos já saem
 * prontos daqui, com os mesmos formatos da página, para o e-mail não refazer contas.
 */
import { caminhoCidade, caminhoEstado, docCidades, docEstados, funcoesDa, medianaDa, NOMES_UF, porPessoa, type Cidade } from "./cidades";
import { capagDe } from "./capag";
import { parcialDe } from "./contas";
import { moedaCurta, moedaExtenso } from "./formato";
import { contratosDe, emendasDe } from "./indicadores";

export type Esfera = "mun" | "uf";

export interface Numero { valor: string; rotulo: string; apagado?: boolean }
export interface Secao {
  id: "andamento" | "contas" | "emendas" | "contratos" | "capag";
  /** Muda quando a seção tem dado novo. */
  chave: string;
  /** Nome curto, para o assunto do e-mail: "emendas", "a nota do Tesouro". */
  curto: string;
  pergunta: string;
  numeros: Numero[];
  texto: string | null;
  /** Âncora da seção na página. */
  ancora: string;
}
export interface Resumo {
  alvo: string;
  esfera: Esfera;
  nome: string;
  uf: string;
  /** "Florianópolis", "Santa Catarina" */
  titulo: string;
  url: string;
  secoes: Secao[];
  /** O retrato das contas do último ano, que vai em todo e-mail. */
  retrato: { ano: number; frase: string; linhas: [string, string, string | null][] } | null;
}

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct0 = (v: number) => `${nf0.format(v * 100)}%`;

/** "mun-4205407", "uf-SC" */
export const alvoDe = (c: Cidade, esfera: Esfera) => (esfera === "uf" ? `uf-${c.uf}` : `mun-${c.ibge}`);

export function entesParaSeguir(): { c: Cidade; esfera: Esfera }[] {
  return [
    ...(docCidades?.cidades ?? []).filter((c) => c.ibge !== 53).map((c) => ({ c, esfera: "mun" as const })),
    ...(docEstados?.cidades ?? []).map((c) => ({ c, esfera: "uf" as const })),
  ];
}

export async function resumoDe(c: Cidade, esfera: Esfera): Promise<Resumo> {
  const mun = esfera === "mun";
  const doc = mun ? docCidades : docEstados;
  const ehDF = c.ibge === 53;
  const titulo = mun ? c.nome : NOMES_UF[c.uf] ?? c.nome;
  const quem = mun ? "a prefeitura" : ehDF ? "o governo do Distrito Federal" : "o governo do estado";
  const Quem = quem[0].toUpperCase() + quem.slice(1);
  const parecidas = mun ? "nas cidades do mesmo tamanho" : "nos estados";
  const secoes: Secao[] = [];

  // O ano em andamento: o relatório bimestral mais recente.
  const p = await parcialDe(c, esfera);
  if (p && p.receitaPrevista > 0 && p.dotacao > 0) {
    secoes.push({
      id: "andamento", chave: `${p.ano}-${p.meses}`, curto: `as contas até ${p.ate}`, ancora: "ano-atual",
      pergunta: `Como estão as contas de ${p.ano}, até ${p.ate}?`,
      numeros: [
        { valor: moedaCurta(p.receita), rotulo: `arrecadados, ${pct0(p.receita / p.receitaPrevista)} do previsto para o ano` },
        { valor: moedaCurta(p.pago), rotulo: `já pagos, ${pct0(p.pago / p.dotacao)} do orçamento do ano` },
      ],
      texto: null,
    });
  }

  // As contas do último ano fechado.
  const total = c.total?.[0] ?? 0;
  const mediana = mun ? medianaDa(c, "total", doc) : null;
  if (c.ano !== null && total > 0 && c.pop) {
    const antes = c.hist?.[String(c.ano - 1)];
    const varia = antes ? total / antes - 1 : null;
    const numeros: Numero[] = [
      { valor: moedaCurta(total), rotulo: "em gastos comprometidos" },
      { valor: porPessoa(total / c.pop), rotulo: "por morador" },
    ];
    if (mediana) numeros.push({ valor: porPessoa(mediana), rotulo: parecidas, apagado: true });
    secoes.push({
      id: "contas", chave: String(c.ano), curto: `as contas de ${c.ano}`, ancora: "areas",
      pergunta: `Quanto ${quem} gastou em ${c.ano}?`,
      numeros,
      texto: varia === null ? null : `Foi ${nf1.format(Math.abs(varia) * 100)}% ${varia >= 0 ? "a mais" : "a menos"} que em ${c.ano - 1}.`,
    });
  }

  // Emendas parlamentares do último ano fechado.
  const e = emendasDe(c, esfera);
  if (e && e.total > 0) {
    const numeros: Numero[] = [
      { valor: moedaCurta(e.total), rotulo: "em emendas" },
      { valor: porPessoa(e.porHab), rotulo: "por morador" },
    ];
    if (e.mediana) numeros.push({ valor: porPessoa(e.mediana), rotulo: parecidas, apagado: true });
    secoes.push({
      id: "emendas", chave: String(e.ano), curto: "emendas", ancora: "emendas",
      pergunta: `Quanto deputados e senadores mandaram para ${mun ? "a cidade" : "o estado"} em ${e.ano}?`,
      numeros,
      texto: mun ? `${moedaExtenso(e.prefeitura)} foram para a prefeitura e ${moedaExtenso(e.entidades)} para entidades e empresas da cidade.` : null,
    });
  }

  // Contratos publicados no PNCP.
  const k = contratosDe(c, esfera);
  if (k && k.n > 0) {
    const [tipo, valor] = k.porTipo[0] ?? [null, 0];
    secoes.push({
      id: "contratos", chave: String(k.ano), curto: "contratos", ancora: "contratos",
      pergunta: `O que ${quem} contratou em ${k.ano}?`,
      numeros: [
        { valor: nf0.format(k.n), rotulo: k.n === 1 ? "contrato publicado" : "contratos publicados" },
        { valor: moedaCurta(k.total), rotulo: "somados" },
      ],
      texto: tipo && valor > 0 && k.porTipo.length > 1 ? `A maior parte, ${moedaExtenso(valor)}, em ${tipo.toLowerCase()}.` : null,
    });
  }

  // A nota do Tesouro (CAPAG).
  const cp = capagDe(c, esfera);
  if (cp?.nota) {
    const numeros: Numero[] = [{ valor: cp.nota, rotulo: `nota do Tesouro, ${cp.quando}` }];
    if (cp.boas !== null) numeros.push({ valor: pct0(cp.boas), rotulo: `${mun ? "das cidades do mesmo tamanho" : "dos estados"} têm A ou B`, apagado: true });
    secoes.push({
      id: "capag", chave: cp.quando, curto: "a nota do Tesouro", ancora: "capag",
      pergunta: `${Quem} consegue pegar empréstimo com juros baixos?`,
      numeros,
      texto: "Com nota A ou B, a União serve de garantia nos empréstimos, e os juros ficam mais baixos.",
    });
  }

  // O retrato: de cada R$ 100, quanto foi para as três maiores áreas.
  let retrato: Resumo["retrato"] = null;
  if (c.ano !== null && total > 0 && c.pop) {
    const areas = funcoesDa(c, doc).slice(0, 3);
    const partes = areas.map((a) => `<strong>R$ ${nf0.format(Math.round((a.emp / total) * 100))}</strong> para ${a.nome.toLowerCase()}`);
    const frase = partes.length
      ? `De cada <strong>R$ 100</strong> que ${quem} gastou, ${partes.slice(0, -1).join(", ")}${partes.length > 1 ? " e " : ""}${partes.at(-1)}.`
      : "";
    const linhas: [string, string, string | null][] = [
      ["Gasto por morador", porPessoa(total / c.pop), mediana ? porPessoa(mediana) : null],
      ...funcoesDa(c, doc).filter((a) => a.cod === "12" || a.cod === "10")
        .sort((a, b) => a.cod.localeCompare(b.cod)).reverse()
        .map((a): [string, string, string | null] => [`${a.nome}, por morador`, porPessoa(a.perCapita), a.mediana ? porPessoa(a.mediana) : null]),
    ];
    retrato = { ano: c.ano, frase, linhas };
  }

  return {
    alvo: alvoDe(c, esfera), esfera, nome: c.nome, uf: c.uf, titulo,
    url: `https://orcamentobrasileiro.com.br${mun ? caminhoCidade(c) : caminhoEstado(c.uf)}`,
    secoes, retrato,
  };
}
