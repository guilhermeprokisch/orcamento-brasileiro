/**
 * As partes da página de cidade e de estado que mudam com o ano, montadas como HTML.
 * As mesmas funções desenham o ano mais recente no build (set:html) e os outros anos no
 * navegador (lib/troca-de-ano.ts), para as duas versões serem sempre iguais. Os estilos
 * ficam em styles/ficha.css, sob a classe .ficha.
 */
import { moedaCompleta, moedaCurta, moedaExtenso, pct } from "./formato";
import { corDaRampa } from "./cores";
import { termoHtml } from "./glossario";
import type { Ficha, Pacote } from "./ficha";

export interface Contexto {
  ano: number;
  esfera: "mun" | "uf";
  ibge: number;
  nome: string;
  uf: string;
  /** "a prefeitura de Fortaleza", "o governo do Ceará" */
  quem: string;
  /** "em Fortaleza", "no estado" */
  onde: string;
  destaques: { cod: string; titulo: string }[];
  ficha: Ficha;
  pacote: Pacote;
}

const nf0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const porPessoa = (v: number) => `R$ ${nf0.format(Math.round(v))}`;
const ESC: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ESC[c]);
const lista = new Intl.ListFormat("pt-BR", { style: "long", type: "conjunction" });

function comum(ctx: Contexto) {
  const ehDF = ctx.ibge === 53;
  const municipal = ctx.esfera === "mun" && !ehDF;
  const f = ctx.ficha;
  /** Mediana por morador do grupo de comparação naquele ano; null sem grupo ou com menos de 10 entes. */
  const mediana = (chave: string): number | null => {
    if (ehDF || f.faixa === undefined) return null;
    const m = ctx.pacote.medianas[f.faixa];
    return m && m.n >= 10 ? m[chave] ?? 0 : null;
  };
  let grupo: string | null = null;
  if (!ehDF && ctx.esfera === "uf") grupo = "dos estados";
  else if (!ehDF && f.faixa !== undefined && ctx.pacote.faixas[f.faixa]) {
    const r = ctx.pacote.faixas[f.faixa].replace(/habitantes$/, "moradores");   // dados antigos ainda dizem "habitantes"
    grupo = `das cidades ${/^(até|mais)\b/.test(r) ? `com ${r}` : r}`;
  }
  // Depois da frase do topo, que diz quem são, as cidades do mesmo porte viram só "as cidades parecidas".
  const parecidas = municipal && grupo ? "das cidades parecidas" : grupo;
  return { ehDF, municipal, f, mediana, grupo, parecidas };
}

function comparar(v: number, m: number | null): string | null {
  if (m === null || m <= 0) return null;
  const r = v / m;
  if (r > 1.15) return `${pct(r - 1)} acima`;
  if (r < 0.85) return `${pct(1 - r)} abaixo`;
  return "perto";
}

/** A frase do topo: quanto comprometeu (empenhou) e como fica frente à mediana. */
export function fraseHtml(ctx: Contexto): string {
  const { f, mediana, grupo, municipal } = comum(ctx);
  const emp = f.total[0], porHab = emp / f.pop, med = mediana("total"), comp = comparar(porHab, med);
  return `<p class="ficha-frase">Em ${ctx.ano}, ${esc(ctx.quem)} ${termoHtml("empenho", "comprometeu")} <strong class="marca">${moedaExtenso(emp)}</strong> em gastos,
    ou <strong>${porPessoa(porHab)} por morador</strong>.${comp && grupo ? ` Isso fica ${comp} da ${termoHtml("mediana", "mediana")} ${grupo} (${porPessoa(med!)})${municipal ? ", que no resto da página chamamos de cidades parecidas" : ""}.` : ""}</p>`;
}

/** Os quatro números grandes: empenhado, pago, por morador e a variação frente ao ano anterior. */
export function numerosHtml(ctx: Contexto): string {
  const { f } = comum(ctx);
  const [emp, pago] = f.total;
  const variacao = f.anterior ? emp / f.anterior - 1 : null;
  return `<section class="numeros" aria-label="Totais de ${ctx.ano}">
    <div><span>Gasto comprometido em ${ctx.ano}</span><strong class="num" title="${moedaCompleta(emp)}">${moedaCurta(emp)}</strong></div>
    <div><span>Pago no ano</span><strong class="num pago" title="${moedaCompleta(pago)}">${moedaCurta(pago)}</strong></div>
    <div><span>Por morador</span><strong class="num">${porPessoa(emp / f.pop)}</strong></div>
    <div><span>Em relação a ${ctx.ano - 1}</span><strong class="num">${variacao === null ? "—" : `${variacao >= 0 ? "+" : "−"}${pct(Math.abs(variacao))}`}</strong></div>
  </section>`;
}

/** Uma explicação curta para os nomes oficiais das áreas que não dizem o que são. */
const DICA_AREA: Record<string, (mun: boolean) => string> = {
  "01": (mun) => (mun ? "a Câmara de Vereadores" : "a Assembleia e o Tribunal de Contas"),
  "02": (mun) => (mun ? "em geral, dívidas de ações na Justiça (precatórios)" : "o Tribunal de Justiça"),
  "03": (mun) => (mun ? "a procuradoria do município" : "Ministério Público, Defensoria e Procuradoria"),
  "09": () => "aposentadorias e pensões dos servidores",
  "14": () => "direitos humanos, defesa do consumidor e outros",
  "15": (mun) => (mun ? "ruas, praças e obras na cidade" : "obras urbanas"),
  "24": () => "em geral, publicidade e comunicação oficial",
  "25": (mun) => (mun ? "em geral, a iluminação pública" : ""),
  "28": () => "dívida, repasses obrigatórios e outros gastos que não são de uma área",
};

/** Destaques (saúde, educação…) com as subáreas, e a tabela de gasto por morador em cada área. */
export function areasHtml(ctx: Contexto): string {
  const { f, mediana, parecidas: grupo } = comum(ctx);
  const emp = f.total[0];
  const funcoes = Object.entries(f.f)
    .map(([cod, [v]]) => ({ cod, nome: ctx.pacote.funcoes[cod] ?? cod, emp: v, perCapita: v / f.pop, mediana: mediana(cod) }))
    .filter((l) => l.emp > 0)
    .sort((a, b) => b.emp - a.emp);
  const subfuncoes = (funcao: string) => Object.entries(f.s)
    .filter(([cod, v]) => cod.startsWith(`${funcao}.`) && v > 0)
    .map(([cod, v]) => ({ nome: ctx.pacote.subfuncoes[cod] ?? cod, emp: v }))
    .sort((a, b) => b.emp - a.emp);
  const maxBarra = Math.max(1, ...funcoes.map((l) => Math.max(l.perCapita, l.mediana ?? 0)));
  const blocos = ctx.destaques
    .map((d) => ({ ...d, l: funcoes.find((x) => x.cod === d.cod), subs: subfuncoes(d.cod) }))
    .filter((b) => b.l);

  const destaques = blocos.length ? `<section class="destaques" style="--colunas:${Math.min(blocos.length, 3)}">
    ${blocos.map(({ l, subs, titulo }) => `<div class="destaque">
      <h2>${esc(titulo)}</h2>
      <p><strong class="num">${moedaCurta(l!.emp)}</strong> (${pct(l!.emp / emp)} do gasto), ${porPessoa(l!.perCapita)} por morador.</p>
      <ul class="subs">${subs.slice(0, 6).map((s, k) => `<li>
        <span class="lb-linha"><span>${esc(s.nome)}</span><strong class="num">${moedaCurta(s.emp)}</strong></span>
        <span class="lb-barra" style="width:${(s.emp / Math.max(1, subs[0].emp)) * 100}%;background:${corDaRampa(Math.min(1, k / 4))}"></span>
      </li>`).join("")}</ul>
    </div>`).join("")}
  </section>` : "";

  return `${destaques}
  <section class="areas">
    <div class="areas-topo">
      <h2>Para onde vai o dinheiro</h2>
      <p>Gasto por morador em cada área.${grupo ? ` <span class="so-largo">O traço mostra a mediana ${grupo}.</span>` : ""}</p>
    </div>
    <div class="tabela" role="table" aria-label="Gasto por área em ${ctx.ano}">
      <div class="linha cab" role="row">
        <span role="columnheader">Área</span>
        <span role="columnheader" class="so-largo">Por morador</span>
        <span role="columnheader" class="d">Por morador</span>
        <span role="columnheader" class="d so-largo">Mediana</span>
        <span role="columnheader" class="d">Total</span>
      </div>
      ${funcoes.map((l, i) => `<div class="linha" role="row">
        <span role="cell" class="nome">${esc(l.nome)}${DICA_AREA[l.cod]?.(ctx.esfera === "mun") ? `<small>${esc(DICA_AREA[l.cod](ctx.esfera === "mun"))}</small>` : ""}</span>
        <span role="cell" class="trilho so-largo">
          <span class="barra" style="width:${(l.perCapita / maxBarra) * 100}%;background:${corDaRampa(Math.min(1, i / 8))}"></span>
          ${l.mediana !== null && l.mediana > 0 ? `<span class="mediana" style="left:${(l.mediana / maxBarra) * 100}%" title="Mediana: ${porPessoa(l.mediana)}"></span>` : ""}
        </span>
        <span role="cell" class="d num">${porPessoa(l.perCapita)}</span>
        <span role="cell" class="d num so-largo muted">${l.mediana === null ? "—" : porPessoa(l.mediana)}</span>
        <span role="cell" class="d num" title="${moedaCompleta(l.emp)}">${moedaCurta(l.emp)}</span>
      </div>`).join("")}
    </div>
  </section>`;
}

const barras = (itens: { rotulo: string; termo?: string; dica?: string; valor: string; titulo?: string; largura: number; cor: string }[]) =>
  `<ul class="barras">${itens.map((i) => `<li>
    <span class="lb-linha"><span>${i.termo ? termoHtml(i.termo, i.rotulo) : esc(i.rotulo)}${i.dica ? `<small class="so-largo"> · ${esc(i.dica)}</small>` : ""}</span><strong class="num"${i.titulo ? ` title="${i.titulo}"` : ""}>${i.valor}</strong></span>
    <span class="lb-barra" style="width:${i.largura}%;background:${i.cor}"></span>
  </li>`).join("")}</ul>`;

/**
 * Com o quê gasta, de onde vem o dinheiro, se sobrou ou faltou, o balanço e o INSS. `quais` escolhe
 * um pedaço, para a página da cidade, que os põe em lugares diferentes: "natureza" (com o quê
 * gasta), "receitas" (de onde vem, sobrou ou faltou, o balanço) ou "inss".
 */
export function contasHtml(ctx: Contexto, quais: "tudo" | "natureza" | "receitas" | "inss" = "tudo"): string {
  const quer = (q: string) => quais === "tudo" || quais === q;
  const { f, ehDF, municipal } = comum(ctx);
  const { contas, natureza, balanco, inss } = f;
  const quem = esc(ctx.quem);
  const deQuem = ehDF ? "do governo do Distrito Federal" : municipal ? "da prefeitura" : "do governo estadual";
  const partes: string[] = [];

  if (natureza && quer("natureza")) {
    const tipos = [
      { rotulo: "Salários e encargos dos servidores", v: natureza.pessoal },
      { rotulo: municipal ? "Serviços, materiais e contas do dia a dia" : "Serviços, materiais, repasses às prefeituras e contas do dia a dia", v: natureza.custeio },
      { rotulo: "Obras e equipamentos", v: natureza.investimentos },
      { rotulo: "Pagamento de dívida", v: natureza.amortizacao },
      { rotulo: "Juros da dívida", v: natureza.juros },
      { rotulo: "Compra de imóveis e participações", v: natureza.inversoes },
    ].filter((t) => t.v > 0).sort((a, b) => b.v - a.v);
    const emCem = (v: number) => Math.round((v / natureza.total) * 100);
    // A frase: as duas fatias do dia a dia (salários e custeio), da maior para a menor, e as obras.
    const principais = [
      { frase: "salários e encargos dos servidores", v: natureza.pessoal },
      { frase: municipal || ehDF ? "serviços, materiais e contas do dia a dia" : "serviços, materiais, repasses às prefeituras e contas do dia a dia", v: natureza.custeio },
    ].sort((a, b) => b.v - a.v).concat([{ frase: "obras e equipamentos", v: natureza.investimentos }]).filter((t) => t.v > 0);
    partes.push(`<section class="bloco">
      <div class="texto">
        <h2>Com o quê gasta</h2>
        <p>De cada R$ 100 que ${quem} gastou em ${natureza.ano}, ${principais.map((t, k) => `<strong>R$ ${emCem(t.v)}</strong> ${k === 0 ? "foram " : ""}para ${t.frase}`).join(", ").replace(/, ([^,]*)$/, " e $1")}.</p>
        <p class="menor"><strong>Serviços, materiais e contas do dia a dia</strong> é tudo o que ${municipal ? "a prefeitura" : "o governo"} gasta para funcionar
          e que não é salário de servidor: ${municipal
            ? "empresas contratadas (coleta de lixo, limpeza, vigilância, transporte escolar), organizações que administram hospitais e postos de saúde"
            : "empresas contratadas (limpeza, vigilância, transporte escolar, manutenção de estradas), organizações que administram hospitais"}, remédios, merenda, combustível, luz, água e aluguéis${municipal || ehDF ? "" : `.
          Na maioria dos estados, entra aqui também a parte do ICMS e do IPVA que a Constituição manda repassar às prefeituras`}.</p>
        <p class="menor">A soma, ${moedaCurta(natureza.total)}, é maior que o total por área porque aqui entram também os pagamentos entre
          órgãos ${municipal ? "da própria prefeitura" : "do próprio governo"}, como a contribuição ao fundo de previdência dos servidores.</p>
      </div>
      ${barras(tipos.map((t, k) => ({ rotulo: t.rotulo, valor: `${moedaCurta(t.v)} · ${pct(t.v / natureza.total)}`, titulo: moedaCompleta(t.v), largura: (t.v / tipos[0].v) * 100, cor: corDaRampa(Math.min(1, k / 4)) })))}
    </section>`);
  }

  if (contas && quer("receitas")) {
    // Partes abaixo de 0,05% ficam de fora (resíduos de classificação).
    const origens = [
      { rotulo: "Arrecadação própria", dica: municipal ? "ISS, IPTU, taxas e outras receitas da prefeitura" : ehDF ? "ICMS, IPVA, ISS, IPTU e outras receitas do DF" : "ICMS, IPVA e outras receitas do estado", v: contas.propria },
      { rotulo: "Repasses da União", dica: municipal ? "FPM, SUS e outros" : "FPE, SUS e outros", v: contas.uniao },
      { rotulo: municipal ? "Repasses do governo estadual" : "Repasses de outros estados", dica: municipal ? "parte do ICMS e do IPVA, entre outros" : "", v: contas.estado },
      { rotulo: "FUNDEB", termo: "fundeb", dica: "fundo da educação básica, com dinheiro de estados, municípios e União", v: contas.fundeb },
      { rotulo: "Empréstimos", dica: "dinheiro que terá de ser devolvido", v: contas.credito },
    ].filter((o) => o.v > contas.receita * 0.0005).sort((a, b) => b.v - a.v);
    const maior = Math.max(1, ...origens.map((o) => o.v));
    const emCem = Math.round((contas.propria / contas.receita) * 100);
    const tributos = municipal
      ? ([[termoHtml("iss"), contas.iss], [termoHtml("iptu"), contas.iptu], [`${termoHtml("itbi")} (compra de imóveis)`, contas.itbi],
          ["taxas", contas.taxas], ["contribuição de iluminação pública", contas.cosip]] as [string, number][]).filter((t) => t[1] > 0).sort((a, b) => b[1] - a[1])
      : [];
    partes.push(`<section class="bloco">
      <div class="texto">
        <h2>De onde vem o dinheiro</h2>
        <p>Em ${contas.ano}, ${quem} recebeu <strong>${moedaExtenso(contas.receita)}</strong>,
          ou ${porPessoa(contas.receita / f.pop)} por morador. De cada R$ 100,
          <strong>R$ ${emCem}</strong> ${emCem === 1 ? "foi arrecadado" : "foram arrecadados"} por ${municipal ? "ela mesma" : "ele mesmo"};
          o resto veio de fora.</p>
        ${tributos.length ? `<p class="menor">Direto à prefeitura, moradores e empresas pagaram ${lista.format(tributos.map(([nome, v]) => `${moedaCurta(v)} de ${nome}`))}.</p>` : ""}
      </div>
      ${barras(origens.map((o, k) => ({ rotulo: o.rotulo, termo: o.termo, dica: o.dica, valor: `${moedaCurta(o.v)} · ${pct(o.v / contas.receita)}`, titulo: moedaCompleta(o.v), largura: (o.v / maior) * 100, cor: corDaRampa(Math.min(1, k / 4)) })))}
    </section>`);

    const sobrou = contas.saldo >= 0;
    const parte = Math.abs(contas.saldo) / contas.receita;
    const maiorLado = Math.max(contas.receita, contas.despesa);
    partes.push(`<section class="bloco">
      <div class="texto">
        <h2>${sobrou ? "Sobrou" : "Faltou"} dinheiro no ano</h2>
        <p>Entraram ${moedaExtenso(contas.receita)} e os gastos comprometidos somaram ${moedaExtenso(contas.despesa)}:
          uma ${sobrou ? "sobra" : "falta"} de <strong class="marca">${moedaExtenso(Math.abs(contas.saldo))}</strong>, ${pct(parte)} da receita.</p>
        <p class="menor">${sobrou
          ? "É a conta simples do ano, não o resultado fiscal oficial: não considera dívidas antigas nem o dinheiro que já estava em caixa."
          : "Quem gasta mais do que recebe cobre a diferença com dinheiro guardado de anos anteriores ou deixando contas para o ano seguinte."}${parte > 0.3 ? " Uma diferença tão grande costuma indicar erro na declaração enviada ao Tesouro." : ""}</p>
      </div>
      <ul class="barras">
        <li><span class="lb-linha"><span>Receita</span><strong class="num" title="${moedaCompleta(contas.receita)}">${moedaCurta(contas.receita)}</strong></span>
          <span class="lb-barra" style="width:${(contas.receita / maiorLado) * 100}%;background:${corDaRampa(0)}"></span></li>
        <li><span class="lb-linha"><span>Despesa <small class="so-largo">· gasto comprometido (empenhado)</small></span><strong class="num" title="${moedaCompleta(contas.despesa)}">${moedaCurta(contas.despesa)}</strong></span>
          <span class="lb-barra" style="width:${(contas.despesa / maiorLado) * 100}%;background:${corDaRampa(0.6)}"></span></li>
        <li class="saldo"><span class="lb-linha"><span>${sobrou ? "Sobrou" : "Faltou"}</span><strong class="num" title="${moedaCompleta(contas.saldo)}">${moedaCurta(Math.abs(contas.saldo))}</strong></span></li>
      </ul>
    </section>`);
  }

  if (balanco && quer("receitas")) {
    const sinal = (v: number) => (v < 0 ? `−${moedaCurta(-v)}` : moedaCurta(v));
    const semPagar = natureza && natureza.restos > 0 ? natureza.restos : Math.max(0, f.total[0] - f.total[1]);
    const linhas = [
      { rotulo: "Dinheiro em caixa", v: moedaCurta(balanco.caixa), mostra: true },
      { rotulo: `${(balanco.sobra ?? 0) >= 0 ? "Sobra" : "Falta"} acumulada`, dica: "dinheiro e aplicações menos contas de curto prazo", v: sinal(balanco.sobra ?? 0), mostra: balanco.sobra !== null },
      { rotulo: "A mesma conta um ano antes", v: sinal(balanco.sobraAntes ?? 0), mostra: balanco.sobraAntes !== null },
      { rotulo: "Gasto do ano que ficou sem pagar", v: moedaCurta(semPagar), mostra: semPagar > 0 },
      { rotulo: "Dívida com empréstimos e financiamentos", v: moedaCurta(balanco.emprestimos), mostra: balanco.emprestimos > 0 },
      { rotulo: "Compromissos de longo prazo", dica: "em geral, aposentadorias futuras dos servidores", v: moedaCurta(balanco.provisoes), mostra: balanco.provisoes > 0 },
    ].filter((l) => l.mostra);
    partes.push(`<section class="bloco">
      <div class="texto">
        <h2>O que tinha e o que devia</h2>
        <p>Em 31 de dezembro de ${balanco.ano}, ${quem} tinha <strong>${moedaExtenso(balanco.caixa)}</strong> em caixa
          ${balanco.emprestimos > 0 ? `e devia <strong>${moedaExtenso(balanco.emprestimos)}</strong> em empréstimos e financiamentos.` : "e não declarou dívida com empréstimos."}</p>
        <p class="menor">Números do ${termoHtml("balanco-patrimonial", "balanço patrimonial")}, o retrato do fim do ano. A sobra acumulada é o que explica como
          um governo consegue gastar mais do que recebe num ano: ele usa o que guardou nos anteriores.
          Aqui a dívida é só a de empréstimos e financiamentos; a dívida da Lei de Responsabilidade Fiscal, mais abaixo,
          soma também precatórios e parcelamentos e desconta o dinheiro em caixa, por isso dá outro número.</p>
      </div>
      <ul class="linhas">${linhas.map((l) => `<li><span>${esc(l.rotulo)}${l.dica ? `<small class="so-largo"> · ${esc(l.dica)}</small>` : ""}</span><strong class="num">${l.v}</strong></li>`).join("")}</ul>
    </section>`);
  }

  if (inss && quer("inss")) {
    const partesInss = ([["Aposentadorias", inss.aposentadorias], ["Pensões por morte", inss.pensoes],
      ["Auxílios e outros benefícios", inss.total - inss.aposentadorias - inss.pensoes]] as [string, number][]).filter((p) => p[1] > 0);
    const frente = f.total[0] ? inss.total / f.total[0] : null;
    partes.push(`<section class="bloco">
      <div class="texto">
        <h2>O que chega direto às pessoas</h2>
        <p>Além do que ${quem} gasta, o governo federal paga aposentadorias, pensões e auxílios do INSS direto a quem tem direito.
          Em ${inss.ano}, foram <strong>${moedaExtenso(inss.total)}</strong> ${esc(ctx.onde)}, ou ${porPessoa(inss.total / f.pop)} por morador.${frente === null ? "" : frente >= 1
            ? ` É mais do que todo o gasto ${deQuem} no ano.` : ` Equivale a ${pct(frente)} de todo o gasto ${deQuem} no ano.`}</p>
        <p class="menor">Valor líquido pago pelas agências do INSS ${municipal ? "da cidade" : ehDF ? "do Distrito Federal" : "do estado"}; quem recebe numa agência de outro lugar
          conta lá. Não inclui BPC nem Bolsa Família.</p>
      </div>
      ${barras(partesInss.map(([nome, v], k) => ({ rotulo: nome, valor: `${moedaCurta(v)} · ${pct(v / inss.total)}`, titulo: moedaCompleta(v), largura: (v / partesInss[0][1]) * 100, cor: corDaRampa(Math.min(1, k / 3)) })))}
    </section>`);
  }

  const fonteInss = "INSS pelo Ministério da Previdência Social (Estatísticas Municipais)";
  if (partes.length && quais === "inss") {
    partes.push(`<p class="fonte">Fonte: ${fonteInss}.</p>`);
  } else if (partes.length && quais !== "natureza") {
    const id = ehDF ? "e53" : `${ctx.esfera === "mun" ? "c" : "e"}${ctx.ibge}`;
    const comInss = inss && quais === "tudo";
    partes.push(`<p class="fonte"><a href="/mapa/#${id}-a${ctx.ano}-saldo">Ver no mapa</a>: impostos pagos, repasses federais, comparação com ${municipal ? "cidades parecidas" : "outros estados"} e outros anos.
      Fontes: ${contas || natureza || balanco ? `contas declaradas ao Tesouro Nacional (DCA, Anexos I-C, I-D e I-AB)${comInss ? "; " : ""}` : ""}${comInss ? fonteInss : ""}.</p>`);
  }
  return partes.join("\n");
}
