/**
 * O caminho dos impostos (página /impostos), lido no build de pipeline/…/caminho_impostos.py: o que se paga de cada
 * imposto, quem cobra, o que é repassado por obrigação e quem fica com o dinheiro no fim. Sem o arquivo, vem null.
 *
 * O diagrama de fluxos é desenhado aqui, na hora de gerar o site (sem biblioteca): três colunas de barras ligadas por
 * faixas de largura proporcional ao dinheiro.
 */

export type Esfera = "uniao" | "estados" | "prefeituras" | "fundos";
export type TipoFluxo = "imposto" | "obrigatorio" | "programa" | "fica";

export interface No { id: string; nome: string; coluna: 0 | 1 | 2; esfera?: Esfera }
export interface Fluxo { id: string; de: string; para: string; valor: number; tipo: TipoFluxo; chave: string; nome: string }
export interface Governo { cobra: number; repassa: number; recebe: number; fica: number }
export interface ItemDeixa { nome: string; valor: number }
export interface DocCaminho {
  ano: number;
  gerado_em: string;
  populacao: number | null;
  fonte: { rtn: { url: string; arquivo: string; pagina: string }; dca: string; faltam: { sem_dca: number; com_ano_anterior: number; populacao_sem_nenhuma: number } };
  nos: No[];
  fluxos: Fluxo[];
  governos: Record<"uniao" | "estados" | "prefeituras", Governo>;
  fundeb: {
    estados_poem: number; estados_tiram: number; prefeituras_poem: number; prefeituras_tiram: number;
    por_uf: Record<string, Record<string, number>>;
    /** de onde vem o que os estados põem no fundo: icms, ipva, itcmd, fpe, ipi (R$ bi) */
    deducao_estados: Record<string, number>;
  };
  conferencia: { nome: string; lado_manda: string; manda: number; recebe: number }[];
  /** O que há dentro dos repasses para programas, por ligação ("c-uniao>f-prefeituras"). */
  programas?: Record<string, ItemDeixa[]>;
  /** O que há dentro dos impostos que juntam vários tributos ("outros-federais", "taxas", "cofins", "ir", "iptu"). */
  composicao?: Record<string, ItemDeixa[]>;
  /** "O que deixa de entrar": benefícios fiscais. */
  deixa?: {
    uniao?: { total: number; ano: number; estimativa: string; fonte: string; url: string; pagina: string; itens: ItemDeixa[]; por_imposto: Record<string, number>; itens_por_imposto?: Record<string, ItemDeixa[]>; serie?: { ano: number; valor: number; efetivo: boolean; pib: number | null }[] };
    estados?: { total: number; ano_referencia: number; sem: string[]; em_2024: number; fonte: string; url: string; serie?: { ano: number; valor: number; efetivo: boolean }[] };
  };
}

const arquivos = import.meta.glob<DocCaminho>("../../public/data/impostos/caminho.json", { eager: true, import: "default" });
export const docCaminho: DocCaminho | null = Object.values(arquivos)[0] ?? null;

export const GOVERNOS = [
  { chave: "uniao", nome: "União", curto: "União" },
  { chave: "estados", nome: "Estados e DF", curto: "Estados" },
  { chave: "prefeituras", nome: "Prefeituras", curto: "Prefeituras" },
] as const;

/** Uma cor por governo: a União no verde escuro, os estados no verde médio, as prefeituras no amarelo do site. */
export const COR: Record<Esfera, string> = { uniao: "#0a4a29", estados: "#4fae73", prefeituras: "#f2c919", fundos: "#a39a85" };
export const COR_CLARA: Record<Esfera, string> = { uniao: "#9bb7a5", estados: "#b9dfc6", prefeituras: "#f8e48c", fundos: "#d6d0c2" };

/** Em que governo começa cada imposto (o que cobra a maior parte), para a cor da barra da coluna 1. */
export function esferaDoImposto(doc: DocCaminho, id: string): Esfera {
  const saem = doc.fluxos.filter((f) => f.de === id).sort((a, b) => b.valor - a.valor);
  return (saem[0]?.para.slice(2) ?? "uniao") as Esfera;
}

/** O que explicar ao clicar em cada pedaço (chave do imposto ou do repasse). Português simples, uma ou duas frases. */
export const EXPLICA: Record<string, string> = {
  ir: "Cobrado pela União de quem tem renda e de empresas com lucro. O imposto de renda descontado do salário dos servidores de estados e prefeituras fica com o próprio estado ou prefeitura.",
  inss: "A contribuição à Previdência descontada do salário e paga pelas empresas sobre a folha. Volta como aposentadoria, pensão e auxílio do INSS.",
  cofins: "Duas contribuições sobre o faturamento das empresas, embutidas no preço de quase tudo o que se compra. Pagam a saúde, a assistência e a previdência.",
  csll: "Contribuição sobre o lucro das empresas, cobrada junto com o imposto de renda delas.",
  importacao: "Cobrado sobre o que entra no país vindo de fora.",
  ipi: "Imposto federal sobre produtos industrializados. Junto com o imposto de renda, é a base do FPE e do FPM.",
  iof: "Imposto sobre empréstimos, câmbio, seguros e algumas aplicações.",
  "outros-federais": "Os tributos federais menores, somados: o salário-educação (pago pelas empresas sobre a folha, para a educação básica), o ITR (o imposto das terras rurais), a CIDE dos combustíveis e outras receitas da Receita Federal.",
  royalties: "Não é imposto: é o que as empresas pagam ao país para tirar petróleo, gás e minérios (royalties, participação especial e compensação pela mineração). A lei manda dividir com os estados e as cidades onde há produção, e um pouco com os demais.",
  icms: "O imposto estadual embutido no preço das mercadorias, da luz, do combustível e da conta de telefone. O maior imposto do país.",
  ipva: "Imposto anual sobre carros e motos, pago ao estado. Metade vai para a cidade onde o veículo está registrado.",
  itcmd: "Imposto estadual cobrado sobre heranças e doações.",
  iss: "Imposto das prefeituras sobre serviços: do conserto do carro ao plano de saúde.",
  iptu: "Imposto anual das prefeituras sobre casas, apartamentos e terrenos na cidade.",
  itbi: "Imposto das prefeituras sobre a compra e venda de imóveis.",
  taxas: "Taxas por serviços e fiscalização (como licenças e coleta de lixo) e a contribuição de iluminação pública na conta de luz.",
  fpe: "Fundo de Participação dos Estados: a Constituição manda a União dar 21,5% do imposto de renda e do IPI aos estados e ao DF, mais aos do Norte, do Nordeste e do Centro-Oeste. Para os estados mais pobres, é a maior fonte de dinheiro.",
  fpm: "Fundo de Participação dos Municípios: 25,5% do imposto de renda e do IPI vão para as prefeituras, mais para as cidades pequenas. Para a maioria delas, é a maior fonte de dinheiro.",
  "ipi-exportacao": "10% do IPI vão para os estados, conforme o quanto cada um exporta; o estado passa um quarto disso às suas prefeituras.",
  itr: "O imposto das terras rurais é dividido meio a meio com a prefeitura onde fica a terra (ou fica inteiro com ela, se ela mesma cobrar).",
  "salario-educacao": "A contribuição das empresas para a educação básica: dois terços vão para estados e prefeituras, pelo número de alunos.",
  "fundeb-uniao": "A União completa o Fundeb nos estados onde o dinheiro por aluno fica abaixo de um mínimo. Desde 2021, a parte dela vem crescendo.",
  "outros-obrigatorios": "A CIDE dos combustíveis, o IOF sobre o ouro e as compensações pelas perdas de ICMS (das exportações e do corte do imposto sobre combustíveis em 2022).",
  "cota-icms": "Um quarto do ICMS de cada estado vai para as suas prefeituras, a maior parte conforme o que cada cidade produz.",
  "cota-ipva": "Metade do IPVA vai para a prefeitura da cidade onde o veículo está registrado.",
  "cota-ipi": "A parte das prefeituras no IPI-exportação, na CIDE e nos royalties que o estado recebe.",
  fundeb: "O fundo da educação básica: estado e prefeituras põem 20% de vários impostos e repasses, e cada um tira pelo número de alunos da sua rede. Como as prefeituras têm mais alunos, o estado põe mais do que tira.",
  programas: "Dinheiro mandado com destino certo, não divisão de imposto: a maior parte é do SUS (consultas, exames, hospitais, agentes de saúde), e o resto vai para merenda e transporte escolar, assistência social, convênios para obras e emendas de deputados e senadores. Boa parte também é obrigatória por lei.",
  fundos: "3% do imposto de renda e do IPI vão para três fundos regionais: o FNO (Norte), o FNE (Nordeste) e o FCO (Centro-Oeste). Não são governos: é dinheiro que o Banco da Amazônia, o Banco do Nordeste e o Banco do Brasil emprestam, com juros menores, a empresas e produtores dessas regiões, e que volta quando os empréstimos são pagos.",
  fica: "O que o governo cobrou e não precisou repassar.",
};

/** Nome curto do repasse, para rótulos dentro do diagrama. */
export const CURTO: Record<string, string> = {
  fpe: "FPE", fpm: "FPM", "ipi-exportacao": "IPI-exportação", itr: "ITR", royalties: "Royalties",
  "salario-educacao": "Salário-educação", "fundeb-uniao": "Fundeb (União)", "outros-obrigatorios": "Outros",
  "cota-icms": "¼ do ICMS", "cota-ipva": "½ do IPVA", "cota-ipi": "Outras cotas", fundeb: "Fundeb", programas: "Programas",
  fundos: "Fundos regionais", fica: "Fica",
};

// ── O desenho do diagrama ────────────────────────────────────────────────────────────────────────

export interface NoDesenhado { id: string; nome: string; coluna: number; x: number; y: number; w: number; h: number; valor: number; esfera: Esfera }
export interface FluxoDesenhado extends Fluxo { d: string; largura: number; y0: number; y1: number; esfera: Esfera; esferaDestino: Esfera }

export interface OpcoesDesenho {
  largura: number;
  altura: number;
  /** espaço entre as barras de uma coluna */
  vao: number;
  /** largura das barras */
  barra: number;
  /** x de cada coluna (a borda esquerda da barra) */
  colunas: number[];
  /** ordem dos nós (os que não estão aqui vão para o fim, na ordem do arquivo) */
  ordem?: string[];
  /** só desenha os nós destas colunas */
  soColunas?: number[];
  /** horizontal (padrão) ou de cima para baixo (troca x e y) */
  vertical?: boolean;
  /** espaço a mais embaixo de alguns nós (id → R$ bi), para desenhar ali o que deixa de entrar */
  extra?: Record<string, number>;
}

const ORDEM_PADRAO = [
  "t-ir", "t-inss", "t-cofins", "t-csll", "t-importacao", "t-ipi", "t-iof", "t-outros-federais", "t-royalties",
  "t-icms", "t-ipva", "t-itcmd", "t-taxas", "t-iss", "t-iptu", "t-itbi",
  "c-uniao", "c-estados", "c-prefeituras", "f-uniao", "f-fundos", "f-estados", "f-prefeituras",
];

const r1 = (v: number) => Math.round(v * 10) / 10;

export function desenhar(doc: DocCaminho, o: OpcoesDesenho) {
  const ordem = o.ordem ?? ORDEM_PADRAO;
  const pos = (id: string) => { const i = ordem.indexOf(id); return i < 0 ? 999 : i; };
  const fluxos = doc.fluxos.filter((f) => {
    const cd = doc.nos.find((n) => n.id === f.de)!.coluna, cp = doc.nos.find((n) => n.id === f.para)!.coluna;
    return !o.soColunas || (o.soColunas.includes(cd) && o.soColunas.includes(cp));
  });
  const valorDe = (id: string) => Math.max(
    fluxos.filter((f) => f.de === id).reduce((t, f) => t + f.valor, 0),
    fluxos.filter((f) => f.para === id).reduce((t, f) => t + f.valor, 0));
  const nos = doc.nos.filter((n) => !o.soColunas || o.soColunas.includes(n.coluna)).filter((n) => valorDe(n.id) > 0)
    .sort((a, b) => pos(a.id) - pos(b.id));
  const colunas = [...new Set(nos.map((n) => n.coluna))].sort();
  // Uma escala só para todas as colunas: a coluna com mais vãos é a que manda.
  const k = Math.min(...colunas.map((c) => {
    const daColuna = nos.filter((n) => n.coluna === c);
    return (o.altura - o.vao * (daColuna.length - 1)) / daColuna.reduce((t, n) => t + valorDe(n.id) + (o.extra?.[n.id] ?? 0), 0);
  }));
  const desenhados = new Map<string, NoDesenhado>();
  for (const c of colunas) {
    const daColuna = nos.filter((n) => n.coluna === c);
    const total = daColuna.reduce((t, n) => t + valorDe(n.id) + (o.extra?.[n.id] ?? 0), 0) * k + o.vao * (daColuna.length - 1);
    let y = (o.altura - total) / 2;
    for (const n of daColuna) {
      const h = valorDe(n.id) * k;
      const esfera = (n.esfera ?? esferaDoImposto(doc, n.id)) as Esfera;
      desenhados.set(n.id, { id: n.id, nome: n.nome, coluna: c, x: o.colunas[c], y, w: o.barra, h, valor: valorDe(n.id), esfera });
      y += h + (o.extra?.[n.id] ?? 0) * k + o.vao;
    }
  }
  // Cada faixa sai e chega empilhada na ordem dos nós do outro lado, para cruzar o mínimo.
  const saida = new Map<string, number>(), chegada = new Map<string, number>();
  const ordenados = [...fluxos].sort((a, b) => pos(a.de) - pos(b.de) || pos(a.para) - pos(b.para) || b.valor - a.valor);
  const porChegada = [...fluxos].sort((a, b) => pos(a.para) - pos(b.para) || pos(a.de) - pos(b.de) || b.valor - a.valor);
  const y1De = new Map<string, number>();
  for (const f of porChegada) {
    const p = desenhados.get(f.para)!;
    const j = chegada.get(f.para) ?? 0;
    y1De.set(f.id, p.y + j + (f.valor * k) / 2);
    chegada.set(f.para, j + f.valor * k);
  }
  const desenhadosF: FluxoDesenhado[] = ordenados.map((f) => {
    const a = desenhados.get(f.de)!, b = desenhados.get(f.para)!;
    const i = saida.get(f.de) ?? 0;
    const largura = f.valor * k;
    const y0 = a.y + i + largura / 2;
    saida.set(f.de, i + largura);
    const y1 = y1De.get(f.id)!;
    const x0 = a.x + a.w, x1 = b.x, xm = (x0 + x1) / 2;
    const d = o.vertical
      ? `M${r1(y0)},${r1(x0)}C${r1(y0)},${r1(xm)} ${r1(y1)},${r1(xm)} ${r1(y1)},${r1(x1)}`
      : `M${r1(x0)},${r1(y0)}C${r1(xm)},${r1(y0)} ${r1(xm)},${r1(y1)} ${r1(x1)},${r1(y1)}`;
    return { ...f, d, largura, y0, y1, esfera: a.esfera, esferaDestino: b.esfera };
  });
  return { nos: [...desenhados.values()], fluxos: desenhadosF, escala: k };
}

// ── De cada R$ 100 ───────────────────────────────────────────────────────────────────────────────

/** Arredonda partes para somarem exatamente `total` (maior resto). */
export function partesInteiras(valores: number[], total = 100): number[] {
  const soma = valores.reduce((t, v) => t + v, 0);
  const brutos = valores.map((v) => (v / soma) * total);
  const inteiros = brutos.map(Math.floor);
  let falta = total - inteiros.reduce((t, v) => t + v, 0);
  const restos = brutos.map((v, i) => [v - Math.floor(v), i] as const).sort((a, b) => b[0] - a[0]);
  for (const [, i] of restos) { if (falta <= 0) break; inteiros[i]++; falta--; }
  return inteiros;
}

export function totalPago(doc: DocCaminho): number {
  return doc.fluxos.filter((f) => f.tipo === "imposto").reduce((t, f) => t + f.valor, 0);
}

// ── Siga um imposto ──────────────────────────────────────────────────────────────────────────────

export interface Rota { imposto: string; nome: string; total: number; destinos: { esfera: Esfera; valor: number; porque: string }[] }

/**
 * Para onde vai cada imposto, pelas regras de divisão: o FPE, o FPM e os fundos regionais saem do imposto de renda e do
 * IPI na proporção de cada um; o IPI-exportação só do IPI; o Fundeb sai dos impostos do estado na proporção do que
 * cada um põe no fundo (a dedução de 20% que a DCA registra). Os programas (SUS, convênios) e a parte da União no
 * Fundeb saem do caixa geral da União e não são de nenhum imposto em especial: ficam fora das rotas.
 */
export function rotas(doc: DocCaminho): Rota[] {
  const f = (de: string, para: string, chave: string) =>
    doc.fluxos.filter((x) => x.de === de && x.para === para && x.chave === chave).reduce((t, x) => t + x.valor, 0);
  const cobrado = (imp: string, gov: string) => f(`t-${imp}`, `c-${gov}`, imp);
  const nomeDe = (imp: string) => doc.nos.find((n) => n.id === `t-${imp}`)?.nome ?? imp;
  const irU = cobrado("ir", "uniao"), ipi = cobrado("ipi", "uniao");
  const base = irU + ipi;
  const fpe = f("c-uniao", "f-estados", "fpe"), fpm = f("c-uniao", "f-prefeituras", "fpm"), fundos = f("c-uniao", "f-fundos", "fundos");
  const ipiExp = f("c-uniao", "f-estados", "ipi-exportacao");
  const parteIr = irU / base, parteIpi = ipi / base;
  const roy = cobrado("royalties", "uniao");
  const royE = f("c-uniao", "f-estados", "royalties"), royM = f("c-uniao", "f-prefeituras", "royalties");
  const icms = cobrado("icms", "estados"), ipva = cobrado("ipva", "estados");
  const cotaIcms = f("c-estados", "f-prefeituras", "cota-icms"), cotaIpva = f("c-estados", "f-prefeituras", "cota-ipva");
  const fundebLiq = f("c-estados", "f-prefeituras", "fundeb");
  const ded = doc.fundeb.deducao_estados;
  const somaDed = Object.values(ded).reduce((t, v) => t + v, 0);
  const fundebDe = (imp: string) => fundebLiq * ((ded[imp] ?? 0) / somaDed);
  // A parte do FPE e do IPI-exportação que o estado põe no Fundeb a mais do que tira chega às prefeituras.
  const fundebFpe = fundebDe("fpe"), fundebIpi = fundebDe("ipi");

  const r: Rota[] = [];
  const rota = (imp: string, destinos: Rota["destinos"]) => {
    const total = destinos.reduce((t, d) => t + d.valor, 0);
    r.push({ imposto: imp, nome: nomeDe(imp), total, destinos: destinos.filter((d) => d.valor > 0.05) });
  };
  rota("ir", [
    { esfera: "uniao", valor: irU - (fpe + fpm + fundos) * parteIr, porque: "fica com a União" },
    { esfera: "estados", valor: (fpe - fundebFpe) * parteIr + cobrado("ir", "estados"), porque: "FPE e o imposto dos servidores estaduais" },
    { esfera: "prefeituras", valor: (fpm + fundebFpe) * parteIr + cobrado("ir", "prefeituras"), porque: "FPM, Fundeb e o imposto dos servidores municipais" },
    { esfera: "fundos", valor: fundos * parteIr, porque: "fundos regionais" },
  ]);
  rota("ipi", [
    { esfera: "uniao", valor: ipi - (fpe + fpm + fundos) * parteIpi - ipiExp, porque: "fica com a União" },
    { esfera: "estados", valor: (fpe - fundebFpe) * parteIpi + ipiExp * 0.75 - fundebIpi, porque: "FPE e IPI-exportação" },
    { esfera: "prefeituras", valor: (fpm + fundebFpe) * parteIpi + ipiExp * 0.25 + fundebIpi, porque: "FPM, Fundeb e a cota do IPI-exportação" },
    { esfera: "fundos", valor: fundos * parteIpi, porque: "fundos regionais" },
  ]);
  for (const imp of ["inss", "cofins", "csll", "importacao", "iof"]) rota(imp, [{ esfera: "uniao", valor: cobrado(imp, "uniao"), porque: "fica com a União" }]);
  rota("royalties", [
    { esfera: "uniao", valor: roy - royE - royM, porque: "fica com a União" },
    { esfera: "estados", valor: royE, porque: "estados produtores e os demais" },
    { esfera: "prefeituras", valor: royM, porque: "cidades produtoras e vizinhas" },
  ]);
  rota("icms", [
    { esfera: "estados", valor: icms - cotaIcms - fundebDe("icms"), porque: "fica com o estado" },
    { esfera: "prefeituras", valor: cotaIcms + fundebDe("icms"), porque: "um quarto do ICMS e o Fundeb" },
  ]);
  rota("ipva", [
    { esfera: "estados", valor: ipva - cotaIpva - fundebDe("ipva"), porque: "fica com o estado" },
    { esfera: "prefeituras", valor: cotaIpva + fundebDe("ipva"), porque: "metade do IPVA e o Fundeb" },
  ]);
  rota("itcmd", [
    { esfera: "estados", valor: cobrado("itcmd", "estados") - fundebDe("itcmd"), porque: "fica com o estado" },
    { esfera: "prefeituras", valor: fundebDe("itcmd"), porque: "o Fundeb" },
  ]);
  const salE = f("c-uniao", "f-estados", "salario-educacao"), salM = f("c-uniao", "f-prefeituras", "salario-educacao");
  const itr = f("c-uniao", "f-prefeituras", "itr");
  rota("outros-federais", [
    { esfera: "uniao", valor: cobrado("outros-federais", "uniao") - salE - salM - itr, porque: "fica com a União" },
    { esfera: "estados", valor: salE, porque: "salário-educação" },
    { esfera: "prefeituras", valor: salM + itr, porque: "salário-educação e metade do ITR" },
  ]);
  rota("taxas", [
    { esfera: "estados", valor: cobrado("taxas", "estados"), porque: "as do estado" },
    { esfera: "prefeituras", valor: cobrado("taxas", "prefeituras"), porque: "as da prefeitura" },
  ]);
  for (const imp of ["iss", "iptu", "itbi"]) rota(imp, [
    { esfera: "prefeituras", valor: cobrado(imp, "prefeituras"), porque: "fica com a prefeitura" },
    { esfera: "estados", valor: cobrado(imp, "estados"), porque: "o do Distrito Federal" },
  ]);
  return r;
}

/** Junta impostos da coluna 1 num nó só (para telas estreitas): {"t-outros": ["t-csll", "t-ipi", …]}. */
export function agrupar(doc: DocCaminho, grupos: Record<string, { nome: string; ids: string[] }>): DocCaminho {
  const destino = new Map<string, string>();
  for (const [novo, g] of Object.entries(grupos)) for (const id of g.ids) destino.set(id, novo);
  const troca = (id: string) => destino.get(id) ?? id;
  const somados = new Map<string, Fluxo>();
  for (const f of doc.fluxos) {
    const de = troca(f.de);
    const chave = de === f.de ? f.chave : de.slice(2);
    const id = `${de}>${f.para}:${chave}`;
    const atual = somados.get(id);
    if (atual) atual.valor += f.valor;
    else somados.set(id, { ...f, id, de, chave, nome: de === f.de ? f.nome : grupos[de].nome });
  }
  const nos: No[] = [];
  for (const n of doc.nos) {
    const novo = troca(n.id);
    if (novo === n.id) nos.push(n);
    else if (!nos.some((x) => x.id === novo)) nos.push({ id: novo, nome: grupos[novo].nome, coluna: n.coluna });
  }
  return { ...doc, nos, fluxos: [...somados.values()] };
}

/** Os grupos da versão estreita do diagrama. */
export const GRUPOS_ESTREITO = {
  "t-federais": { nome: "Outros federais", ids: ["t-csll", "t-importacao", "t-ipi", "t-iof", "t-outros-federais"] },
  "t-estaduais": { nome: "IPVA e outros", ids: ["t-ipva", "t-itcmd"] },
  "t-municipais": { nome: "IPTU, ITBI e taxas", ids: ["t-iptu", "t-itbi", "t-taxas"] },
};
export const ORDEM_ESTREITO = [
  "t-ir", "t-inss", "t-cofins", "t-federais", "t-royalties", "t-icms", "t-estaduais", "t-iss", "t-municipais",
  "c-uniao", "c-estados", "c-prefeituras", "f-uniao", "f-fundos", "f-estados", "f-prefeituras",
];

// ── Números para o texto ─────────────────────────────────────────────────────────────────────────

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Bilhões em texto curto: "R$ 2,7 tri", "R$ 867 bi", "R$ 8,8 bi". */
export function bi(v: number): string {
  if (v >= 999.5) return `R$ ${nf1.format(v / 1000)} tri`;
  if (v >= 99.5) return `R$ ${nf0.format(v)} bi`;
  return `R$ ${nf1.format(v).replace(/,0$/, "")} bi`;
}

/** Bilhões por extenso: "R$ 2,7 trilhões", "R$ 867 bilhões". */
export function biExtenso(v: number): string {
  if (v >= 999.5) { const t = Math.round(v / 100) / 10; return `R$ ${nf1.format(t).replace(/,0$/, "")} ${t < 2 ? "trilhão" : "trilhões"}`; }
  if (v >= 99.5) return `R$ ${nf0.format(v)} bilhões`;
  const x = Math.round(v * 10) / 10;
  return `R$ ${nf1.format(x).replace(/,0$/, "")} ${x < 2 ? "bilhão" : "bilhões"}`;
}

/** Soma dos fluxos que atendem ao filtro. */
export function soma(doc: DocCaminho, filtro: (f: Fluxo) => boolean): number {
  return doc.fluxos.filter(filtro).reduce((t, f) => t + f.valor, 0);
}

/** Reais por morador, arredondados para a centena: "R$ 19.800". */
export function porMorador(doc: DocCaminho, v: number): string | null {
  if (!doc.populacao) return null;
  return `R$ ${nf0.format(Math.round((v * 1e3) / doc.populacao / 100) * 100)}`;
}

/** Afasta rótulos (centros y) para ficarem a pelo menos `min` um do outro, dentro de [0, altura]. */
export function afastar(ys: number[], min: number, altura: number): number[] {
  const idx = ys.map((y, i) => [y, i] as const).sort((a, b) => a[0] - b[0]);
  const saida = idx.map(([y]) => y);
  for (let i = 1; i < saida.length; i++) saida[i] = Math.max(saida[i], saida[i - 1] + min);
  const excesso = saida.at(-1)! - (altura - min / 2);
  if (excesso > 0) {
    saida[saida.length - 1] -= excesso;
    for (let i = saida.length - 2; i >= 0; i--) saida[i] = Math.min(saida[i], saida[i + 1] - min);
  }
  const r = new Array<number>(ys.length);
  idx.forEach(([, i], j) => (r[i] = saida[j]));
  return r;
}
