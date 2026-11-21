/**
 * Protótipo da cascata do gasto: a árvore de cada lugar (União e João Pessoa), com os filhos de cada nível calculados
 * na hora em que são abertos. Cada nó guarda a mistura por categoria (obrigatória ou não, na União; tipo de credor,
 * em João Pessoa), que pode servir de cor.
 */
import { SUBFUNCOES_REFINANCIAMENTO, TIPOS_DESPESA, type DocAno } from "../../lib/dados";
import { moedaCurta, moedaExtenso } from "../../lib/formato";

export interface Categoria { nome: string; cor: string; escuro?: boolean }

export interface Info {
  cnpj?: string;
  licitacao?: string;
  empenhos?: number;
  pessoas?: number;
  resto?: number;
  via?: string;
  tipoCredor?: number;
}

export interface No {
  cod: string;
  /** Igual de um ano para o outro (código na União; nome ou raiz do CNPJ em João Pessoa): acha a mesma caixa no ano anterior. */
  chave: string;
  nome: string;
  valor: number;
  /** O tipo do nível: "Órgão", "Área", "Credor"… */
  nivel: string;
  prof: number;
  pai: No | null;
  /** Valor por categoria (mesma ordem de Fonte.cats). */
  mix: number[];
  /** Dotação atualizada (o autorizado), só na União. */
  autorizado?: number;
  /** "outros N programas": junta os menores; `lista` traz quem são. */
  ehOutros?: boolean;
  lista?: No[];
  info?: Info;
  _filhos?: No[];
  carregar?: () => No[];
}

export interface Comparacao {
  /** O valor do ano anterior, já em reais do ano mostrado (corrigido pelo IPCA). */
  antes: number;
  variacao: number;
}

export interface Fonte {
  chave: "uniao" | "joao-pessoa";
  ano: number;
  /** Para os valores por pessoa: população do Brasil (União) ou da cidade, no ano. */
  populacao: number;
  /** Ligado quando o usuário pede a comparação: o mesmo nó no ano anterior (null: não existia). */
  comparar?: (n: No) => Comparacao | null;
  raiz: No;
  cats: Categoria[];
  /** Nome da cor por categoria: "Obrigatório ou não", "Quem recebe". */
  rotuloCor: string;
  /** Uma frase por categoria, para quem não sabe o que é "obrigatória" ou "previdência". */
  explicaCat: string[];
  /** Endereço deste nó no Explorer (União). */
  linkExplorer?: (n: No) => string;
  plural: Record<string, string>;
  /** Uma linha que explica cada nível, para quem não conhece os nomes. */
  explica: Record<string, string>;
  frase: string;
  fonte: string;
  /** Total pago a cada empresa no ano todo (João Pessoa), pela raiz do CNPJ. */
  porCnpj?: Map<string, { valor: number; areas: Set<string> }>;
}

export function filhos(n: No): No[] {
  if (n._filhos === undefined) n._filhos = n.carregar ? n.carregar() : [];
  return n._filhos;
}

export const temFilhos = (n: No) => !n.ehOutros && filhos(n).length > 0;

export function caminhoAte(n: No): No[] {
  const c: No[] = [];
  for (let x: No | null = n; x; x = x.pai) c.unshift(x);
  return c;
}

// ——— União: o arquivo do Explorer (site/public/data/explorer/2025.json), sem o refinanciamento da dívida ———

const NIVEIS_UNIAO: [string, string][] = [
  ["orgao", "Órgão"], ["uo", "Unidade"], ["programa", "Programa"], ["acao", "Ação"], ["gnd", "Tipo de gasto"],
];

export async function fonteUniao(ano = 2025, populacao = 1): Promise<Fonte> {
  const r = await fetch(`/data/explorer/${ano}.json`);
  if (!r.ok) throw new Error(`Não consegui carregar ${ano} (HTTP ${r.status})`);
  const doc: DocAno = await r.json();
  const col = (c: string) => doc.colunas.indexOf(c);
  const iV = col("realizado"), iA = col("atualizado"), iSub = col("subfuncao"), iTipo = col("tipo");
  const cats: Categoria[] = iTipo >= 0
    ? TIPOS_DESPESA.map((t) => ({ nome: t.nome, cor: t.cor, escuro: t.cod === "obr" }))
    : [{ nome: "Gasto", cor: "#1f7a47", escuro: true }];
  const catDe = new Map<string, number>(TIPOS_DESPESA.map((t, i) => [t.cod, i]));

  let refin = 0;
  const linhas: (string | number)[][] = [];
  for (const l of doc.linhas) {
    const v = l[iV] as number;
    if (SUBFUNCOES_REFINANCIAMENTO.has(l[iSub] as string)) { refin += v; continue; }
    if (v) linhas.push(l);
  }

  const criar = (ls: (string | number)[][], cod: string, nome: string, prof: number, pai: No | null): No => {
    const mix = new Array(cats.length).fill(0);
    let valor = 0, autorizado = 0;
    for (const l of ls) {
      const v = l[iV] as number;
      valor += v;
      autorizado += l[iA] as number;
      mix[iTipo >= 0 ? catDe.get(l[iTipo] as string) ?? 4 : 0] += v;
    }
    const n: No = { cod, chave: cod, nome, valor, autorizado, nivel: prof === 0 ? "Orçamento" : NIVEIS_UNIAO[prof - 1][1], prof, pai, mix };
    if (prof < NIVEIS_UNIAO.length) {
      n.carregar = () => {
        const [dim] = NIVEIS_UNIAO[prof];
        const i = col(dim);
        const grupos = new Map<string, (string | number)[][]>();
        for (const l of ls) {
          const c = l[i] as string;
          let g = grupos.get(c);
          if (!g) grupos.set(c, (g = []));
          g.push(l);
        }
        return [...grupos]
          .map(([c, g]) => criar(g, c, (doc.dims as Record<string, Record<string, string>>)[dim]?.[c] ?? c, prof + 1, n))
          .filter((f) => f.valor > 0)
          .sort((a, b) => b.valor - a.valor);
      };
    }
    return n;
  };
  const raiz = criar(linhas, "uniao", `Orçamento federal ${ano}`, 0, null);
  return {
    chave: "uniao", ano, populacao, raiz, cats, rotuloCor: "Obrigatório ou não",
    explicaCat: [
      "o governo é obrigado por lei ou pela Constituição a pagar: aposentadorias, salários, repasses a estados e cidades",
      "o governo decide se gasta e quanto: obras, compras, programas",
      "deputados e senadores indicaram para onde vai",
      "juros e pagamento da dívida pública",
      "o orçamento não marca de que tipo é",
    ],
    linkExplorer: (n) => {
      const f = caminhoAte(n).slice(1).map((x, i) => `${NIVEIS_UNIAO[i][0]}:${x.cod}`).join(",");
      return `/explorer?ano=${ano}&metrica=realizado&refin=0${f ? `&f=${f}` : ""}`;
    },
    plural: { Orçamento: "orçamento", Órgão: "órgãos", Unidade: "unidades", Programa: "programas", Ação: "ações", "Tipo de gasto": "tipos de gasto" },
    explica: {
      Órgão: "o ministério ou o poder (Câmara, tribunais…)",
      Unidade: "quem gasta dentro do órgão: fundo, secretaria, autarquia",
      Programa: "o objetivo do gasto",
      Ação: "o que é feito com o dinheiro",
      "Tipo de gasto": "salários, custeio, obras, juros…",
    },
    frase: `Em ${ano}, o governo federal pagou ${moedaExtenso(raiz.valor)}, sem contar ${moedaExtenso(refin)} de rolagem da dívida (troca de dívida velha por nova, que fica de fora).`,
    fonte: "Orçamento federal (Tesouro e SIOP), valores pagos.",
  };
}

// ——— João Pessoa: os empenhos do TCE-PB (pipeline/prototipo/cascata_joao_pessoa.py) ———

interface NoJp {
  nome: string; valor: number; filhos?: NoJp[];
  n?: number; tipo?: number; cnpj?: string; licitacao?: string; pessoas?: number; resto?: number;
}

const CORES_CREDOR = ["#1f7a47", "#ffe14d", "#d9822b", "#eab98f", "#c3bba7", "#8a8475"];
const ERROS: Record<string, string> = {
  "Encargos Especias": "Encargos Especiais", "Assistêncial Social": "Assistência Social", "Subvenções Socias": "Subvenções Sociais",
};
const SIGLAS = new Set(["INSS", "CAGEPA", "SA", "S/A", "S.A.", "ME", "EPP", "JP", "BB", "BRB", "SFT", "URE-JP", "PB", "CNPJ", "LTDA-ME", "SPE", "UTI", "EIRELI"]);
const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e", "em", "para"]);

/** "EXEMPLAR SERVICE E LIMPEZA LTDA" → "Exemplar Service e Limpeza Ltda" */
export function nomeProprio(s: string): string {
  if (s !== s.toUpperCase()) return s;
  return s.split(/\s+/).map((p, i) => {
    if (SIGLAS.has(p)) return p;
    const b = p.toLowerCase();
    if (i > 0 && MINUSCULAS.has(b)) return b;
    return b.replace(/(^|[-/(])(\p{L})/gu, (_, a, l) => a + l.toUpperCase());
  }).join(" ");
}

export const formatarCnpj = (c: string) => c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");

export async function fonteJoaoPessoa(ano = 2025, populacao = 1): Promise<Fonte> {
  const r = await fetch(`/prototipo/cascata-joao-pessoa-${ano}.json`);
  if (!r.ok) throw new Error(`Não consegui carregar João Pessoa (HTTP ${r.status})`);
  const d: { ano: number; nome: string; valor: number; tipos: string[]; filhos: NoJp[]; fonte: string } = await r.json();
  const cats: Categoria[] = d.tipos.map((nome, i) => ({ nome, cor: CORES_CREDOR[i], escuro: i === 0 }));
  const NIV = ["Área", "Tipo de despesa", "Credor"];
  const porCnpj = new Map<string, { valor: number; areas: Set<string> }>();

  const conv = (o: NoJp, prof: number, pai: No | null, i: number): No => {
    let nome = ERROS[o.nome] ?? o.nome;
    const n: No = { cod: String(i), chave: nome, nome, valor: o.valor, nivel: prof === 0 ? "Prefeitura" : NIV[prof - 1], prof, pai, mix: new Array(cats.length).fill(0) };
    if (o.filhos) {
      n._filhos = [...o.filhos].sort((a, b) => b.valor - a.valor).map((f, j) => conv(f, prof + 1, n, j));
      for (const f of n._filhos) f.mix.forEach((v, k) => (n.mix[k] += v));
    } else {
      const t = o.tipo ?? 0;
      n.mix[t] = o.valor;
      n.info = { empenhos: o.n, tipoCredor: t, cnpj: o.cnpj, licitacao: o.licitacao, pessoas: o.pessoas, resto: o.resto };
      // a chave do credor é a raiz do CNPJ (o nome muda de grafia de um ano para o outro)
      n.chave = o.cnpj ? `${t === 2 ? "folha:" : ""}${o.cnpj.slice(0, 8)}` : o.pessoas !== undefined ? "#pessoas" : o.resto ? "#resto" : nome;
      if (t === 2 && o.cnpj) { n.info.via = nomeProprio(nome); nome = "Folha de pagamento"; }
      else if (o.pessoas !== undefined) nome = `${o.pessoas.toLocaleString("pt-BR")} pessoas físicas`;
      else if (o.resto) nome = `${o.resto} credores menores (fora do protótipo)`;
      else nome = nomeProprio(nome);
      n.nome = nome;
      if (o.cnpj && t === 0) {
        const raizCnpj = o.cnpj.slice(0, 8);
        const e = porCnpj.get(raizCnpj) ?? { valor: 0, areas: new Set<string>() };
        e.valor += o.valor;
        let area: No | null = pai;
        while (area && area.prof > 1) area = area.pai;
        if (area) e.areas.add(area.nome);
        porCnpj.set(raizCnpj, e);
      }
    }
    return n;
  };
  const raiz = conv({ nome: `${d.nome} ${d.ano}`, valor: d.valor, filhos: d.filhos }, 0, null, 0);
  return {
    chave: "joao-pessoa", ano: d.ano, populacao, raiz, cats, rotuloCor: "Quem recebe", porCnpj,
    explicaCat: [
      "empresas e entidades contratadas pela prefeitura",
      "pessoas pagas uma a uma: autônomos, bolsistas, microempreendedores (sem nome nem CPF aqui)",
      "salários dos servidores, que a prefeitura manda para a conta da folha",
      "aposentadorias, pensões e a contribuição ao INSS ou ao instituto de previdência",
      "juros, parcelas da dívida e tarifas de bancos",
      "repasses a outros governos, fundos e consórcios",
    ],
    plural: { Prefeitura: "prefeitura", Área: "áreas", "Tipo de despesa": "tipos de despesa", Credor: "credores" },
    explica: {
      Área: "saúde, educação, urbanismo… (a função do gasto)",
      "Tipo de despesa": "salários, serviços, material, obras (o elemento de despesa)",
      Credor: "quem recebeu: a empresa, o órgão ou, somadas, as pessoas físicas",
    },
    frase: `Em ${d.ano}, a prefeitura de João Pessoa (com Câmara, fundos e instituto de previdência) pagou ${moedaExtenso(d.valor)}.`,
    fonte: "Tribunal de Contas da Paraíba (TCE-PB), empenhos pagos em 2025. Pessoas físicas só no total, sem nome nem CPF.",
  };
}

// ——— "Não mostrar tudo": os maiores de cada nível e o resto junto ———

export interface Visiveis { itens: No[]; outros: No | null }

export function visiveis(n: No, k: number, plural: Record<string, string>, escolhido?: No | null): Visiveis {
  const fs = filhos(n);
  if (fs.length <= k + 1 && !fs.some((f) => f.info?.resto)) return { itens: fs.slice(), outros: null };
  // "N credores menores" (o resto que o arquivo do protótipo já juntou) vai sempre para "outros".
  let top = fs.filter((f) => !f.info?.resto).slice(0, k);
  // Os pedacinhos (menos de 0,6% do nível) também vão para "outros", mas ficam pelo menos três.
  while (top.length > 3 && top[top.length - 1].valor < n.valor * 0.006) top.pop();
  if (escolhido && !top.includes(escolhido)) {
    top = top.slice(0, Math.max(1, top.length - 1));
    top.push(escolhido);
    top.sort((a, b) => b.valor - a.valor);
  }
  const resto = fs.filter((f) => !top.includes(f));
  if (resto.length <= 1) return { itens: fs.filter((f) => top.includes(f) || resto.includes(f)), outros: null };
  const mix = new Array(n.mix.length).fill(0);
  for (const f of resto) f.mix.forEach((v, i) => (mix[i] += v));
  const nivel = resto[0].nivel;
  const outros: No = {
    cod: "#outros", chave: "#outros", nome: `outros ${resto.reduce((s, f) => s + (f.info?.resto ?? 1), 0)} ${plural[nivel] ?? "itens"}`, valor: resto.reduce((s, f) => s + f.valor, 0),
    nivel, prof: n.prof + 1, pai: n, mix, ehOutros: true, lista: resto,
  };
  return { itens: top, outros };
}

/** Categoria com mais dinheiro no nó. */
export function catPrincipal(n: No): number {
  let m = 0;
  n.mix.forEach((v, i) => { if (v > n.mix[m]) m = i; });
  return m;
}

// ——— valores por pessoa ———

export const exibir = { porPessoa: false, populacao: 1 };
const nfP0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nfP2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "R$ 93,3 bi" ou, por pessoa, "R$ 437/pessoa". */
export function dinheiro(v: number, longo = false): string {
  if (!exibir.porPessoa) return moedaCurta(v);
  const p = v / Math.max(1, exibir.populacao);
  const t = Math.abs(p) >= 100 ? `R$ ${nfP0.format(p)}` : Math.abs(p) >= 0.01 ? `R$ ${nfP2.format(p)}` : "menos de R$ 0,01";
  return `${t}${longo ? " por pessoa" : "/pessoa"}`;
}

/** O mesmo nó na árvore do ano anterior, seguindo as chaves do caminho. */
export function noAnterior(n: No, raizAntes: No): No | null {
  let x: No = raizAntes;
  for (const y of caminhoAte(n).slice(1)) {
    const f = filhos(x).find((z) => z.chave === y.chave);
    if (!f) return null;
    x = f;
  }
  return x;
}

/** "▲ 12%", "▼ 3,4%", "= 0%". */
export function setaVariacao(v: number): string {
  const p = Math.abs(v) * 100;
  const t = p >= 10 ? nfP0.format(p) : p.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  return Math.abs(v) < 0.0005 ? "= 0%" : `${v > 0 ? "▲" : "▼"} ${t}%`;
}
