/**
 * A reforma tributária (Emenda Constitucional 132/2023, LC 214/2025) no desenho do caminho dos impostos.
 *
 * Não há arrecadação futura para desenhar: o que se faz é pegar o dinheiro do último ano fechado e trocar os impostos
 * conforme o calendário da lei. A própria lei sustenta a aproximação: o Senado fixa as alíquotas para que os impostos
 * novos arrecadem o mesmo que os antigos deixam de arrecadar (ADCT, art. 130), e a União compensa o FPE e o FPM pela
 * troca do IPI pelo Imposto Seletivo (EC 132, art. 7º). Os artigos estão em docs/reforma-tributaria-lei.md.
 */
import { bi, ORDEM_ESTREITO, ORDEM_PADRAO, totalPago, type DocCaminho, type Fluxo } from "./caminho-impostos";

/** Quanto resta das alíquotas do ICMS e do ISS em cada ano (ADCT, arts. 128 e 129). Antes de 2029, inteiras. */
const RESTA: Record<number, number> = { 2029: 0.9, 2030: 0.8, 2031: 0.7, 2032: 0.6, 2033: 0 };
const r1 = (v: number) => Math.round(v * 10) / 10;
const depoisDe = (ordem: string[], id: string, novo: string) => ordem.flatMap((x) => (x === id ? [x, novo] : [x]));

/** O IBS entra logo abaixo do ICMS, que é o lugar que ele vai ocupar. */
export const ORDEM_REFORMA = { largo: depoisDe(ORDEM_PADRAO, "t-icms", "t-ibs"), estreito: depoisDe(ORDEM_ESTREITO, "t-icms", "t-ibs") };

/** Os impostos que a reforma troca, no desenho de hoje. */
export const TROCADOS = ["t-cofins", "t-ipi", "t-icms", "t-iss"];

/** De cada R$ 100 pagos em impostos, quantos vieram dos que vão ser trocados. */
export function parteTrocada(doc: DocCaminho): number {
  const trocado = doc.fluxos.filter((f) => TROCADOS.includes(f.de)).reduce((t, f) => t + f.valor, 0);
  return Math.round((trocado / totalPago(doc)) * 100);
}

/** O caminho dos impostos como a lei manda que seja em `ano`, com o dinheiro de `doc`. */
export function caminhoEm(doc: DocCaminho, ano: number): DocCaminho {
  let nos = doc.nos.map((n) => ({ ...n }));
  let fluxos: Fluxo[] = doc.fluxos.map((f) => ({ ...f }));
  if (ano >= 2027) {
    // PIS, Cofins e IPI dão lugar à CBS e ao Imposto Seletivo; a lei fixa a soma dos dois (ADCT, arts. 126 e 130, I).
    const ipi = fluxos.filter((f) => f.de === "t-ipi").reduce((t, f) => t + f.valor, 0);
    fluxos = fluxos.filter((f) => f.de !== "t-ipi");
    nos = nos.filter((n) => n.id !== "t-ipi");
    for (const f of fluxos) {
      if (f.de === "t-cofins") { f.valor = r1(f.valor + ipi); f.nome = "CBS e Imposto Seletivo"; f.chave = "cbs"; }
      if (f.chave === "ipi-exportacao") { f.chave = "is-exportacao"; f.nome = "Seletivo e IPI-exportação"; }
    }
    for (const n of nos) if (n.id === "t-cofins") n.nome = "CBS e Seletivo";
  }
  const resta = RESTA[ano] ?? 1;
  if (resta < 1) {
    // O IBS arrecada o que o ICMS e o ISS deixam de arrecadar, e vai para os mesmos governos (ADCT, arts. 128 a 130).
    const ibs = new Map<string, number>();
    for (const f of fluxos) {
      if (f.de !== "t-icms" && f.de !== "t-iss") continue;
      ibs.set(f.para, (ibs.get(f.para) ?? 0) + f.valor * (1 - resta));
      f.valor = r1(f.valor * resta);
    }
    fluxos = fluxos.filter((f) => f.valor > 0);
    nos = nos.filter((n) => resta > 0 || (n.id !== "t-icms" && n.id !== "t-iss"));
    nos.push({ id: "t-ibs", nome: "IBS", coluna: 0 });
    for (const [para, valor] of ibs) fluxos.push({ id: `t-ibs>${para}:ibs`, de: "t-ibs", para, valor: r1(valor), tipo: "imposto", chave: "ibs", nome: "IBS" });
    for (const f of fluxos) if (f.chave === "cota-icms") { f.chave = "cota-ibs"; f.nome = resta === 0 ? "¼ do IBS" : "¼ ICMS e IBS"; }
  }
  return { ...doc, nos, fluxos };
}

const EXPLICA_NOVO: Record<string, string> = {
  "t-cofins": "A CBS é a contribuição federal que toma o lugar do PIS e da Cofins. O Imposto Seletivo recai só sobre o que faz mal à saúde ou ao meio ambiente. A lei fixa a soma dos dois, não quanto cabe a cada um.",
  "t-ibs": "O imposto que toma o lugar do ICMS e do ISS. É um só, dividido entre o estado e a prefeitura do lugar para onde vai o produto ou o serviço. Quem arrecada e reparte é o Comitê Gestor do IBS.",
  "t-icms": "O ICMS, com a alíquota reduzida: a cada ano, de 2029 a 2032, ele perde um décimo. Deixa de existir em 2033.",
  "t-iss": "O ISS, com a alíquota reduzida: a cada ano, de 2029 a 2032, ele perde um décimo. Deixa de existir em 2033.",
};

/** Os balões dos pedaços que a reforma muda (o resto do desenho fica com os de sempre). */
export function dicasReforma(doc: DocCaminho, ano: number): Record<string, { t: string; v: string; x: string }> {
  const mudou = new Set<string>([...(ano >= 2027 ? ["t-cofins"] : []), ...(ano >= 2029 ? ["t-ibs", "t-icms", "t-iss"] : [])]);
  const nome: Record<string, string> = { "t-cofins": "CBS e Imposto Seletivo", "t-ibs": "IBS", "t-icms": "ICMS", "t-iss": "ISS" };
  const para: Record<string, string> = { "c-uniao": "a União", "c-estados": "os estados", "c-prefeituras": "as prefeituras" };
  const dicas: Record<string, { t: string; v: string; x: string }> = {};
  for (const id of mudou) {
    const saem = doc.fluxos.filter((f) => f.de === id);
    if (!saem.length) continue;
    dicas[id] = { t: nome[id], v: `${bi(saem.reduce((t, f) => t + f.valor, 0))}, no dinheiro de ${doc.ano}`, x: EXPLICA_NOVO[id] };
    for (const f of saem) dicas[f.id] = { t: `${nome[id]} para ${para[f.para] ?? f.para}`, v: `${bi(f.valor)}, no dinheiro de ${doc.ano}`, x: EXPLICA_NOVO[id] };
  }
  return dicas;
}

export interface PassoReforma { ano: number; rotulo: string; titulo: string; texto: string; artigo: string; foco: string[] }

/** O passo a passo da página: em cada ano, o que muda (`foco`, o que fica aceso no desenho) e o artigo que manda. */
export function passosReforma(doc: DocCaminho): PassoReforma[] {
  const meio = (ano: number): PassoReforma => {
    const pct = Math.round(RESTA[ano] * 100);
    return {
      ano, rotulo: String(ano), titulo: `${ano}: mais um décimo`, foco: ["t-icms", "t-iss", "t-ibs"], artigo: "ADCT, arts. 128 e 130, II e III",
      texto: `O ICMS e o ISS perdem mais um décimo da alíquota. De cada R$ 100 que eles arrecadavam, R$ ${pct} ainda vêm deles e R$ ${100 - pct} já vêm do IBS.`,
    };
  };
  return [
    { ano: doc.ano, rotulo: "Hoje", titulo: "Hoje: o que vai ser trocado", foco: TROCADOS, artigo: `Dinheiro de ${doc.ano}`,
      texto: `Em destaque, os quatro impostos que vão ser trocados: de cada R$ 100 pagos em ${doc.ano}, R$ ${parteTrocada(doc)} vieram deles. O resto, apagado, continua como está.` },
    { ano: 2027, rotulo: "2027", titulo: "2027: a primeira troca", foco: ["t-cofins"], artigo: "ADCT, arts. 126, 127 e 130, I",
      texto: "PIS, Cofins e IPI saem. No lugar entram a CBS e o Imposto Seletivo, que vão para a União do mesmo jeito. ICMS e ISS ainda não mudam: o IBS segue como teste, a 0,1%." },
    { ano: 2029, rotulo: "2029", titulo: "2029: o IBS começa a valer", foco: ["t-icms", "t-iss", "t-ibs"], artigo: "ADCT, arts. 128 e 130, II e III",
      texto: "O IBS é o imposto novo que troca o ICMS, do estado, e o ISS, da prefeitura, por um só, dividido entre os dois. Começa a valer em 2029: de cada R$ 100, R$ 90 ainda vêm do ICMS e do ISS e R$ 10 já vêm do IBS." },
    meio(2030), meio(2031), meio(2032),
    { ano: 2033, rotulo: "2033", titulo: "2033: fim da troca", foco: ["t-ibs"], artigo: "ADCT, arts. 129 e 130, II e III",
      texto: "ICMS e ISS deixam de existir. O IBS fica no lugar dos dois: uma parte vai para o estado e outra para a prefeitura." },
  ];
}
