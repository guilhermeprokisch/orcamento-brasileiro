/**
 * Os detalhes de uma caixa da cascata (o cartão ao lado da tela): o que é o nível, quanto é, de que tipo é o gasto,
 * os maiores dentro e o botão que leva ao mapa de blocos do Explorer no mesmo lugar.
 */
import { pct } from "../../lib/formato";
import { caminhoAte, dinheiro, filhos, temFilhos, type Fonte, type No } from "./dados";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const parte = (n: No) => (n.pai && n.pai.valor > 0 ? n.valor / n.pai.valor : 1);
const pctCurto = (v: number) => (v >= 0.995 ? "100%" : v >= 0.1 ? `${Math.round(v * 100)}%` : v >= 0.001 ? pct(v) : "<0,1%");
const botaoMapa = `<p><button type="button" class="cc-ver-mapa" data-acao="ver-mapa">Ver em blocos</button> (o mapa do Explorer, neste ponto)</p>`;

/** Autorizado e pago, conforme o que a caixa mostra. */
function linhaExecucao(F: Fonte, n: No): string {
  if (!n.autorizado) return "";
  if (F.metrica === "realizado") return `<dt>Autorizado</dt><dd>${dinheiro(n.autorizado)}; pagou ${pctCurto(n.valor / n.autorizado)} disso no ano</dd>`;
  return `<dt>Pago</dt><dd>${dinheiro(n.pago)}: ${pctCurto(n.pago / n.autorizado)} do autorizado</dd>`;
}

export function htmlDetalhe(F: Fonte, n: No): string {
  if (!temFilhos(n)) return htmlFim(F, n);
  const raiz = F.raiz;
  const fs = filhos(n);
  const plural = (nivel: string) => F.plural[nivel] ?? nivel.toLowerCase();
  const linhas: string[] = [];
  if (n.pai) linhas.push(`<dt>Do nível de cima</dt><dd>${pctCurto(parte(n))} de ${esc(n.pai.nome)}</dd>`);
  if (n !== raiz) {
    const cem = (n.valor / raiz.valor) * 100;
    const cada = cem >= 1 ? `R$ ${cem.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} de cada R$ 100` : `R$ ${(cem * 10).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} de cada R$ 1.000`;
    linhas.push(`<dt>Do total</dt><dd>${pctCurto(n.valor / raiz.valor)}: ${cada} do orçamento federal</dd>`);
  }
  const ex = linhaExecucao(F, n);
  if (ex) linhas.push(ex);
  linhas.push(`<dt>Dentro</dt><dd>${fs.length} ${fs.length > 1 ? plural(fs[0].nivel) : fs[0].nivel.toLowerCase()}</dd>`);
  const t = n.mix.reduce((a, v) => a + Math.max(0, v), 0) || 1;
  const mix = n.mix.map((v, i) => ({ i, f: Math.max(0, v) / t })).filter((m) => m.f >= 0.005).sort((a, b) => b.f - a.f);
  const htmlMix = F.cats.length > 1 ? `<div class="cc-det-mix">
      <span class="cc-det-barra">${mix.map((m) => `<b style="flex:${m.f};background:${F.cats[m.i].cor}"></b>`).join("")}</span>
      <ul>${mix.map((m) => `<li><i style="background:${F.cats[m.i].cor}"></i><strong>${esc(F.cats[m.i].nome)} ${pctCurto(m.f)}</strong>
        <span>${esc(F.explicaCat[m.i] ?? "")}</span></li>`).join("")}</ul></div>` : "";
  const maiores = fs.slice(0, 3).map((f) => `<li><span>${esc(f.nome)}</span><span class="num">${dinheiro(f.valor)} · ${pctCurto(f.valor / Math.max(1, n.valor))}</span></li>`).join("");
  return `<div class="cc-cartao cc-detalhe">
    <span class="sobretitulo">${esc(n.nivel)}</span>
    ${F.explica[n.nivel] ? `<p class="cc-det-explica">${esc(F.explica[n.nivel])}</p>` : ""}
    <h3>${esc(n.nome)}</h3>
    <p class="cc-cartao-valor"><strong class="marca">${dinheiro(n.valor, true)}</strong> ${F.rotuloValor} em ${F.ano}</p>
    <dl>${linhas.join("")}</dl>
    ${htmlMix}
    <h4>Os maiores dentro</h4>
    <ol class="cc-det-maiores">${maiores}</ol>
    ${botaoMapa}
  </div>`;
}

/** O último nível (o tipo de gasto da ação): até onde vão os dados do orçamento federal. */
function htmlFim(F: Fonte, n: No): string {
  const fio = caminhoAte(n).slice(1).map((x) => esc(x.nome)).join(" › ");
  const ex = linhaExecucao(F, n);
  return `<div class="cc-cartao">
    <span class="sobretitulo">${esc(n.nivel)} · fim do caminho</span>
    <h3>${esc(n.nome)}</h3>
    <p class="cc-cartao-valor"><strong class="marca">${dinheiro(n.valor, true)}</strong> · ${pctCurto(parte(n))} ${n.pai ? `de ${esc(n.pai.nome)}` : ""}</p>
    ${ex ? `<dl>${ex}</dl>` : ""}
    <p>Este é o último degrau do orçamento federal: <strong>${esc(n.nome.toLowerCase())}</strong> da ação
      “${esc(n.pai?.nome ?? "")}”. Quem recebeu o dinheiro (a empresa, o contrato) está no Portal da Transparência,
      nota a nota, e ainda não está neste site.</p>
    ${botaoMapa}
    <p class="cc-fio muted">${fio}</p>
  </div>`;
}
