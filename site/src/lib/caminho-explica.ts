/**
 * O que dizer de cada pedaço do diagrama do caminho dos impostos: o título, o valor, a explicação e, quando houver, a
 * lista do que há dentro (os tributos de um grupo, os programas de um repasse, os maiores benefícios fiscais de um
 * imposto). Usado pelo painel ao lado do diagrama (Painel.astro) e pelo balão que aparece ao passar o mouse ou tocar
 * (Diagrama.astro). As chaves são os data-id do desenho.
 */
import {
  agrupar, bi, EXPLICA, GOVERNOS, GRUPOS_ESTREITO, porMorador, soma, totalPago, type DocCaminho, type Esfera, type Fluxo,
} from "./caminho-impostos";

export interface Info {
  titulo: string;
  valor: string;
  texto: string;
  lista?: { nome: string; valor: string }[];
  /** os outros data-id que acendem junto quando este é escolhido */
  ligados: string[];
}

/** Os repasses que saem de cada imposto, pelas regras de divisão (para acender o caminho inteiro de um imposto). */
const SEGUE: Record<string, string[]> = {
  ir: ["fpe", "fpm", "fundos"], ipi: ["fpe", "fpm", "fundos", "ipi-exportacao", "cota-ipi"], royalties: ["royalties", "cota-ipi"],
  "outros-federais": ["salario-educacao", "itr", "outros-obrigatorios"], icms: ["cota-icms", "fundeb"], ipva: ["cota-ipva", "fundeb"],
  itcmd: ["fundeb"],
};

// ── O que deixa de entrar ────────────────────────────────────────────────────────────────────────

export interface BarraDeixa { id: string; imposto: string; nome: string; valor: number; esfera: Esfera }

const NOME_DEIXA: Record<string, string> = {
  ir: "Imposto de renda", cofins: "Cofins e PIS", inss: "INSS", csll: "CSLL", ipi: "IPI", iof: "IOF",
  importacao: "Importação", "outros-federais": "Outros federais", icms: "ICMS",
};
const ORDEM_DEIXA = ["ir", "inss", "cofins", "csll", "importacao", "ipi", "iof", "outros-federais", "icms"];
/** No celular, os benefícios menores juntos (como os impostos menores no diagrama). */
const DEIXA_ESTREITO: Record<string, string[]> = { ir: ["ir"], inss: ["inss"], cofins: ["cofins"], federais: ["csll", "importacao", "ipi", "iof", "outros-federais"], icms: ["icms"] };

/** As barras de "o que deixa de entrar", uma por imposto (ids x-…), na ordem dos impostos do diagrama. */
export function barrasDeixa(doc: DocCaminho, estreito = false): BarraDeixa[] {
  const por = doc.deixa?.uniao?.por_imposto ?? {};
  const valor = (imp: string) => (imp === "icms" ? doc.deixa?.estados?.total ?? 0 : por[imp] ?? 0);
  if (estreito) {
    return Object.entries(DEIXA_ESTREITO).map(([id, imps]) => ({
      id: `x-${id}`, imposto: id, nome: id === "federais" ? "Outros federais" : NOME_DEIXA[id], esfera: (id === "icms" ? "estados" : "uniao") as Esfera,
      valor: imps.reduce((t, i) => t + valor(i), 0),
    })).filter((b) => b.valor > 0.5);
  }
  return ORDEM_DEIXA.map((imp) => ({ id: `x-${imp}`, imposto: imp, nome: NOME_DEIXA[imp], valor: valor(imp), esfera: (imp === "icms" ? "estados" : "uniao") as Esfera }))
    .filter((b) => b.valor > 0.5);
}

// ── As explicações ───────────────────────────────────────────────────────────────────────────────

export function explicacoes(doc: DocCaminho): Record<string, Info> {
  const total = totalPago(doc);
  const nomeNo = new Map(doc.nos.map((n) => [n.id, n.nome]));
  const curto = (id: string) => nomeNo.get(id)!.replace(" e DF", "");
  const em100 = (v: number) => { const x = (v / total) * 100; return x >= 1 ? `R$ ${Math.round(x)}` : "menos de R$ 1"; };
  const linha = (v: number) => `${bi(v)} · ${em100(v)} de cada R$ 100`;
  const lista = (itens?: { nome: string; valor: number }[]) => itens?.map((i) => ({ nome: i.nome, valor: bi(i.valor) }));
  const info: Record<string, Info> = {};

  // Faixas
  for (const f of doc.fluxos) {
    const de = curto(f.de), para = curto(f.para);
    const titulo = f.tipo === "imposto" ? `${f.nome} cobrado por ${para === "União" ? "a União" : para === "Prefeituras" ? "as prefeituras" : "os estados"}`
      : f.tipo === "fica" ? `${de}: o que fica` : `${f.nome}: ${de} → ${para}`;
    const programas = f.tipo === "programa" ? doc.programas?.[`${f.de}>${f.para}`] : undefined;
    info[f.id] = {
      titulo, valor: linha(f.valor), texto: EXPLICA[f.chave] ?? "",
      lista: lista(programas ?? (f.tipo === "imposto" && doc.fluxos.filter((x) => x.de === f.de).length === 1 ? doc.composicao?.[f.chave] : undefined)),
      ligados: [f.id, f.de, f.para],
    };
  }

  // Barras e caixas
  for (const n of doc.nos) {
    const entram = doc.fluxos.filter((f) => f.para === n.id), saem = doc.fluxos.filter((f) => f.de === n.id);
    const valor = Math.max(entram.reduce((t, f) => t + f.valor, 0), saem.reduce((t, f) => t + f.valor, 0));
    const gov = GOVERNOS.find((g) => n.id.endsWith(g.chave));
    let texto = "";
    let itens: Info["lista"];
    if (n.coluna === 0) {
      const imp = n.id.slice(2);
      texto = EXPLICA[imp] ?? "";
      const naoCobrado = imp === "icms" ? doc.deixa?.estados?.total : doc.deixa?.uniao?.por_imposto[imp];
      if (naoCobrado && naoCobrado >= 0.5) texto += ` Além disso, ${bi(naoCobrado)} deixaram de ser cobrados com benefícios fiscais (o tracejado embaixo da barra).`;
      itens = lista(doc.composicao?.[imp]) ?? (saem.length > 1 ? saem.map((f) => ({ nome: `Cobrado por ${nomeNo.get(f.para)}`, valor: bi(f.valor) })) : undefined);
    } else if (n.coluna === 1 && gov) {
      const g = doc.governos[gov.chave];
      texto = `Cobrou ${bi(g.cobra)} em impostos e repassou ${bi(g.repassa)} a outros governos.`;
      itens = [...saem].sort((a, b) => b.valor - a.valor).map((f) => ({ nome: f.tipo === "fica" ? "Fica com ele mesmo" : `${f.nome} → ${curto(f.para)}`, valor: bi(f.valor) }));
    } else if (n.coluna === 2 && gov) {
      const g = doc.governos[gov.chave];
      texto = `Ficou com ${bi(g.fica)}${porMorador(doc, g.fica) ? ` (${porMorador(doc, g.fica)} por morador do país)` : ""}: ${bi(g.cobra - g.repassa)} do que cobrou e ${bi(g.recebe)} de repasses.`;
      itens = [...entram].sort((a, b) => b.valor - a.valor).map((f) => ({ nome: f.tipo === "fica" ? "Do que ele mesmo cobrou" : `${f.nome} (${curto(f.de)})`, valor: bi(f.valor) }));
    } else if (n.id === "f-fundos") {
      texto = EXPLICA.fundos;
    }
    // Um imposto acende também os repasses que saem dele (o FPM do imposto de renda, a cota do ICMS…) e o que fica.
    const depois = n.coluna === 0 ? doc.fluxos.filter((f) => (SEGUE[n.id.slice(2)] ?? []).includes(f.chave)
      || (f.tipo === "fica" && saem.some((s) => s.para === f.de))) : [];
    info[n.id] = {
      titulo: n.nome, valor: linha(valor), texto, lista: itens,
      ligados: [n.id, ...entram.map((f) => f.id), ...saem.map((f) => f.id), ...entram.map((f) => f.de), ...saem.map((f) => f.para),
        ...depois.flatMap((f) => [f.id, f.para]), ...(n.coluna === 0 ? [`x-${n.id.slice(2)}`] : [])],
    };
  }

  // O que deixa de entrar
  const u = doc.deixa?.uniao, e = doc.deixa?.estados;
  for (const b of [...barrasDeixa(doc), ...barrasDeixa(doc, true)]) {
    if (info[b.id]) continue;
    const icms = b.imposto === "icms";
    const itens = icms ? undefined : b.imposto === "federais"
      ? ["csll", "importacao", "ipi", "iof", "outros-federais"].map((i) => ({ nome: NOME_DEIXA[i], valor: bi(u?.por_imposto[i] ?? 0) }))
      : lista(u?.itens_por_imposto?.[b.imposto]);
    info[b.id] = {
      titulo: icms ? "Incentivos de ICMS dos estados" : `Benefícios fiscais: ${b.nome.toLowerCase().replace("inss", "INSS").replace("csll", "CSLL").replace("ipi", "IPI").replace("iof", "IOF").replace("cofins e pis", "Cofins e PIS")}`,
      valor: `${bi(b.valor)} por ano que deixam de entrar`,
      texto: icms
        ? `O ICMS que os estados projetam deixar de cobrar com incentivos a empresas e setores, para atrair fábricas e baratear produtos (${e?.fonte ?? "Tesouro Nacional"}${e?.sem?.length ? `, sem ${e.sem.join(" e ")}` : ""}).`
        : `O que a Receita Federal estima deixar de cobrar com isenções, deduções e regimes especiais. Não está no caminho acima porque nunca foi pago. Os maiores:`,
      lista: itens,
      ligados: [b.id, `t-${b.imposto}`],
    };
  }

  // Atalhos (botões "acenda um pedaço"): um conjunto de faixas de uma vez, com um resumo.
  const ids = (filtro: (f: Fluxo) => boolean) => doc.fluxos.filter(filtro);
  const grupo = (id: string, titulo: string, texto: string, fluxos: Fluxo[], totalGrupo?: number, itens?: Info["lista"]) => {
    info[id] = {
      titulo, valor: linha(totalGrupo ?? fluxos.reduce((t, f) => t + f.valor, 0)), texto,
      lista: itens ?? [...fluxos].sort((a, b) => b.valor - a.valor).map((f) => ({
        nome: f.tipo === "imposto" ? `${f.nome} cobrado pelos ${curto(f.para).toLowerCase()}` : f.tipo === "fica" ? `${curto(f.de)} fica com`
          : `${f.nome} (${curto(f.de)} → ${curto(f.para)})`,
        valor: bi(f.valor),
      })),
      ligados: [...new Set(fluxos.flatMap((f) => [f.id, f.de, f.para]))],
    };
  };
  const fb = doc.fundeb;
  grupo("g-uniao", "A União divide", "O que a Constituição e as leis mandam a União passar a estados, prefeituras e aos fundos regionais: a maior parte é do imposto de renda e do IPI.",
    ids((f) => f.de === "c-uniao" && f.tipo === "obrigatorio"));
  grupo("g-icms", "O caminho do ICMS", `Os estados cobraram ${bi(soma(doc, (f) => f.de === "t-icms"))} de ICMS. Um quarto vai para as prefeituras, e mais um pedaço chega a elas pelo Fundeb.`,
    ids((f) => f.de === "t-icms" || f.chave === "cota-icms" || f.chave === "fundeb"), soma(doc, (f) => f.de === "t-icms"));
  grupo("g-fundeb", "O Fundeb", `Estados puseram ${bi(fb.estados_poem)} no fundo e tiraram ${bi(fb.estados_tiram)}; prefeituras puseram ${bi(fb.prefeituras_poem)} e tiraram ${bi(fb.prefeituras_tiram)}. A União completa onde o dinheiro por aluno fica abaixo do mínimo.`,
    ids((f) => f.chave === "fundeb" || f.chave === "fundeb-uniao"));
  const progs = ids((f) => f.tipo === "programa");
  const somados = new Map<string, number>();
  for (const f of progs) for (const i of doc.programas?.[`${f.de}>${f.para}`] ?? []) somados.set(i.nome, (somados.get(i.nome) ?? 0) + i.valor);
  grupo("g-programas", "Os programas", EXPLICA.programas, progs, undefined,
    somados.size ? [...somados].sort((a, b) => b[1] - a[1]).map(([nome, v]) => ({ nome, valor: bi(v) })) : undefined);
  grupo("g-fica", "O que cada um guarda", "O que cada governo cobrou e não precisou repassar.", ids((f) => f.tipo === "fica"));

  // O diagrama do celular junta impostos pequenos num nó só: os ids juntados ganham texto próprio, e os ids
  // originais acendem também o nó juntado.
  const estreito = agrupar(doc, GRUPOS_ESTREITO);
  const grupoDe = new Map(Object.entries(GRUPOS_ESTREITO).flatMap(([g, x]) => x.ids.map((id) => [id, g] as const)));
  for (const n of estreito.nos) if (!info[n.id]) {
    const g = GRUPOS_ESTREITO[n.id as keyof typeof GRUPOS_ESTREITO];
    const saem = estreito.fluxos.filter((f) => f.de === n.id);
    info[n.id] = {
      titulo: n.nome, valor: linha(saem.reduce((t, f) => t + f.valor, 0)), texto: "Vários impostos menores, somados:",
      lista: g?.ids.map((id) => ({ nome: nomeNo.get(id) ?? id, valor: bi(soma(doc, (f) => f.de === id)) })),
      ligados: [n.id, ...saem.map((f) => f.id), ...saem.map((f) => f.para)],
    };
  }
  for (const f of estreito.fluxos) if (!info[f.id]) info[f.id] = { ...info[f.de], ligados: [f.id, f.de, f.para] };
  for (const [id, i] of Object.entries(info)) {
    const extra = i.ligados.flatMap((l) => {
      const g = grupoDe.get(l);
      if (g) return [g];
      const m = l.match(/^(t-[^>]+)>(.+):/);
      const gf = m && grupoDe.get(m[1]);
      return gf ? [`${gf}>${m![2]}:${gf.slice(2)}`] : [];
    });
    if (extra.length) info[id] = { ...i, ligados: [...i.ligados, ...extra] };
  }
  return info;
}
