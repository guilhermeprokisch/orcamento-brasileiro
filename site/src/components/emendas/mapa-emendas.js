(async () => {
  const raiz = document.querySelector(".mapa-emendas");
  const BASE = raiz.dataset.base;   // a pasta versionada dos dados (bucket; localmente, a cópia em /data/)
  const svg = d3.select("#mapa"), g = svg.append("g");
  // A cara do autor escolhido vira o preenchimento das bolhas. Em objectBoundingBox o mesmo
  // padrão serve a todos os círculos: cada um recorta a foto no seu próprio tamanho.
  const defs = svg.append("defs");
  const padrao = defs.append("pattern").attr("id", "cara-autor")
    .attr("patternContentUnits", "objectBoundingBox").attr("width", 1).attr("height", 1);
  const padraoImg = padrao.append("image").attr("width", 1).attr("height", 1)
    .attr("preserveAspectRatio", "xMidYMid slice");

  const gUf = g.append("g"), gBolhas = g.append("g");
  const projecao = d3.geoMercator(), caminho = d3.geoPath(projecao);
  const cartao = document.getElementById("cartao");

  const brl = (mil) => {                      // valores chegam em R$ mil
    const v = mil * 1e3;
    if (v >= 1e9) return "R$ " + (v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " bi";
    if (v >= 1e6) return "R$ " + (v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi";
    return "R$ " + Math.round(v).toLocaleString("pt-BR");
  };

  const [uf, mun, dados, caras] = await Promise.all([
    d3.json("/data/mapa/estados.geojson"),
    d3.json("/data/mapa/municipios.geojson"),
    d3.json(`${BASE}/municipios.json`),
    d3.json(`${BASE}/autores.json`),   // foto, partido e casa de cada parlamentar
  ]);

  for (const a of Object.values(caras)) if (a.foto) a.foto = `${BASE}/${a.foto}`;

  const escapar = (s) => String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  /** A cara do autor: foto quando é gente, monograma quando é bancada, comissão ou o relator. */
  function cara(nome, tam = "") {
    const p = caras[nome];
    if (p && p.foto) return `<img class="cara ${tam}" src="${escapar(p.foto)}" alt="" loading="lazy"
      onerror="this.replaceWith(Object.assign(document.createElement('span'),
        {className:'cara ${tam} vazia', textContent:${JSON.stringify(sigla(nome))}}))">`;
    return `<span class="cara ${tam} vazia">${escapar(sigla(nome))}</span>`;
  }
  function sigla(nome) {
    const limpo = nome.replace(/^(Bancada d[oae]s?|Comissão d[oae]s?)\s*/i, "").trim();
    return limpo.split(/\s+/).filter((p) => p.length > 2).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
  }
  /** Linha de apoio do autor. Comissão, bancada e relator são colegiados: não têm cara, e dizer
   *  "sem foto" soaria defeito — o que falta mesmo é só a dos parlamentares que não casaram. */
  const colegiado = (nome) => /^(bancada|comissão|comissao|relator)/i.test(nome);
  const legenda2 = (nome) => {
    const p = caras[nome];
    if (p) return `${p.casa}${p.partido ? ` · ${p.partido}` : ""}${p.uf ? `-${p.uf}` : ""}`;
    return colegiado(nome) ? "colegiado do Congresso" : "não achei no cadastro";
  };

  // O IBGE entrega os polígonos no sentido anti-horário (padrão GeoJSON); o d3 espera o contrário e
  // leria cada um como "o globo inteiro menos o polígono" — o que estoura o contorno e joga os
  // centróides no antípoda. Inverte polígono a polígono, como faz src/mapa/pagina.html.
  for (const geo of [uf, mun]) {
    for (const f of geo.features) {
      const gm = f.geometry;
      for (const p of (gm.type === "Polygon" ? [gm.coordinates] : gm.coordinates)) {
        if (d3.geoArea({ type: "Polygon", coordinates: p }) > 2 * Math.PI) for (const anel of p) anel.reverse();
      }
    }
  }

  // Centróide de cada município a partir da própria malha: nada de novo no pipeline.
  const centro = new Map();
  for (const f of mun.features) {
    const id = String(f.properties?.id ?? f.properties?.codarea ?? f.id ?? "");
    if (id) centro.set(id, d3.geoCentroid(f));
  }

  const ANOS = dados.anos;
  const lugares = Object.entries(dados.mun)
    .map(([ibge, d]) => ({ ibge, ...d, c: centro.get(ibge) }))
    .filter((d) => d.c && Number.isFinite(d.c[0]));
  const semCentro = Object.keys(dados.mun).length - lugares.length;
  if (semCentro) console.warn(`${semCentro} municípios sem centróide na malha`);

  let iAno = ANOS.length, escala = "raiz", semDF = true;   // iAno === ANOS.length ⇒ todos os anos
  let autorSel = null, serieAutor = null;   // serieAutor: Map ibge → série anual só desse autor
  let filtroTipo = "";                      // "" = todos os tipos de emenda
  // Com um autor escolhido vale a série dele; sem autor, a do tipo pedido (d.st) ou a soma (d.s).
  // Os dados por autor não têm o tipo repartido, por isso um exclui o outro.
  const valorDe = (d) => {
    const s = serieAutor ? serieAutor.get(d.ibge) : (filtroTipo ? d.st?.[filtroTipo] : d.s);
    if (!s) return 0;
    return iAno === ANOS.length ? s.reduce((a, b) => a + b, 0) : s[iAno];
  };
  // Brasília concentra ~40% de tudo: é a sede das entidades que recebem, não o lugar do gasto.
  // Com ela dentro, a bolha dela engole a escala e o resto do país vira poeira.
  const DF = "5300108";

  // Com um autor escolhido, as bolhas dele levam o rosto dele (um só, grande o bastante).
  let modoCara = true;
  const comCara = () => !!(modoCara && autorSel && caras[autorSel]?.foto);
  const RETRATOS = 8;           // quantas chamadas, somando as duas colunas
  let emDesenho = [];           // os municípios do desenho atual, do maior para o menor
  // Os retratos são de parlamentares. Filtrando por bancada, relator ou comissão, o dinheiro na
  // tela não é deles: as chamadas saem, para não sugerir uma ligação que não existe.
  const caraCabe = () => !filtroTipo || filtroTipo === "Individual" || filtroTipo === "Pix";
  const main = document.getElementById("main"), palco = document.getElementById("palco");
  const colEsq = document.getElementById("col-esq"), colDir = document.getElementById("col-dir");
  const svgLinhas = d3.select("#linhas");

  let raio = () => 0;
  /** Com cara, a bolha tem um piso: abaixo de ~5px o rosto não é rosto, é um borrão. */
  // Dividir o raio pelo zoom cheio mantinha a bolha do mesmo tamanho na tela: ao aproximar, o
  // mapa crescia e ela parecia encolher, e continuava difícil de acertar. Dividindo pela raiz do
  // zoom ela cresce junto, só mais devagar que o mapa, e ganha um piso para ser clicável.
  let kZoom = 1;
  const compZoom = () => Math.sqrt(kZoom);
  const raioDe = (v) => {
    const r = (comCara() ? Math.max(5, raio(v)) : raio(v)) * compZoom();
    return Math.max(2.2 * compZoom(), r) / kZoom;
  };

  const ligarEventos = (sel) => sel
    .on("pointerenter", (ev, d) => mostrar(d, ev))
    .on("pointermove", (ev, d) => mostrar(d, ev))
    .on("pointerleave", () => esconder())
    .on("click", (ev, d) => { ev.stopPropagation(); abrirMunicipio(d); });

  /** Os municípios do desenho que estão dentro do palco agora. */
  function naTela() {
    const t = d3.zoomTransform(svg.node());
    const m = palco.getBoundingClientRect();
    return emDesenho.filter((d) => {
      const [x, y] = t.apply(projecao(d.c));
      return x > 0 && y > 0 && x < m.width && y < m.height;
    });
  }

  /** As chamadas: os parlamentares que mais mandaram para o que está na tela (somando o que cada
   *  município guarda dos seus três maiores), cada um ancorado no maior município dele à vista. */
  let chamadasAtuais = [];
  function escolherRetratos() {
    const cabe = temColunas();
    main.classList.toggle("sem-colunas", !cabe);
    if (!cabe) { chamadasAtuais = []; pintarColunas(); return; }

    const soma = new Map();
    for (const d of naTela()) {
      for (const [nome, v] of d.ap ?? []) {
        if (!caras[nome]?.foto) continue;
        const r = soma.get(nome) ?? { nome, v: 0, anc: null, ancV: 0, n: 0 };
        r.v += v; r.n += 1;
        if (v > r.ancV) { r.ancV = v; r.anc = d; }
        soma.set(nome, r);
      }
    }
    const top = [...soma.values()].sort((a, b) => b.v - a.v).slice(0, RETRATOS);
    // Cada um vai para a coluna do lado em que está o seu município; equilibra 4 e 4; de cima para baixo.
    const meio = palco.getBoundingClientRect().width / 2;
    const telaDe = (r) => d3.zoomTransform(svg.node()).apply(projecao(r.anc.c));
    for (const r of top) { const [x, y] = telaDe(r); r.tx = x; r.ty = y; }
    let esq = top.filter((r) => r.tx < meio).sort((a, b) => a.ty - b.ty);
    let dir = top.filter((r) => r.tx >= meio).sort((a, b) => a.ty - b.ty);
    const metade = Math.ceil(top.length / 2);
    while (esq.length > metade) dir.push(esq.pop());
    while (dir.length > metade) esq.push(dir.pop());
    esq.sort((a, b) => a.ty - b.ty); dir.sort((a, b) => a.ty - b.ty);
    for (const r of esq) r.lado = "esq";
    for (const r of dir) r.lado = "dir";
    chamadasAtuais = [...esq, ...dir];
    pintarColunas();
  }

  function pintarColunas() {
    for (const [col, lado] of [[colEsq, "esq"], [colDir, "dir"]]) {
      const itens = chamadasAtuais.filter((r) => r.lado === lado);
      const sel = d3.select(col).selectAll("button.chamada").data(itens, (r) => r.nome);
      sel.exit().remove();
      sel.enter().append("button").attr("type", "button").attr("class", "chamada")
        .on("click", async (ev, r) => { await carregarAutores(); if (porAutor.autores[r.nome]) escolher(r.nome); })
        .on("pointerenter", (ev, r) => acender(r.nome))
        .on("pointerleave", () => acender(null))
        .merge(sel)
        .attr("data-nome", (r) => r.nome)
        .html((r) => `${cara(r.nome)}<span><b>${escapar(r.nome)}</b><small>${escapar(legenda2(r.nome))}</small>
          <span class="v"><strong>${brl(r.v)}</strong> à vista · maior: ${escapar(r.anc.n)}</span></span>`);
      // ordena o DOM pela lista (o join mantém a ordem dos dados em novos nós, mas não reordena os velhos)
      d3.select(col).selectAll("button.chamada").data(itens, (r) => r.nome).order();
      col.querySelector(".vazio")?.remove();
      if (!itens.length) col.insertAdjacentHTML("beforeend",
        `<p class="vazio">Nenhum parlamentar com foto entre os municípios à vista.</p>`);
    }
    desenharLinhas();
  }

  /** Linha do retrato ao município, nas coordenadas do main (as colunas ficam fora do mapa). */
  function desenharLinhas() {
    const mm = main.getBoundingClientRect(), pm = palco.getBoundingClientRect();
    const t = d3.zoomTransform(svg.node());
    const gs = svgLinhas.selectAll("g").data(chamadasAtuais, (r) => r.nome);
    gs.exit().remove();
    const novos = gs.enter().append("g");
    novos.append("line"); novos.append("circle").attr("r", 3.4);
    novos.merge(gs).each(function (r) {
      const bt = main.querySelector(`button.chamada[data-nome="${CSS.escape(r.nome)}"]`);
      if (!bt) return;
      const cx = bt.getBoundingClientRect();
      const [ax, ay] = t.apply(projecao(r.anc.c));
      const x2 = pm.left - mm.left + ax, y2 = pm.top - mm.top + ay;
      // sai da borda do cartão que olha para o mapa, no meio da altura: da foto, cruzava o texto
      const x1 = (r.lado === "esq" ? cx.right : cx.left) - mm.left, y1 = cx.top + cx.height / 2 - mm.top;
      const dentro = ax > 0 && ay > 0 && ax < pm.width && ay < pm.height;
      d3.select(this).attr("display", dentro ? null : "none").attr("data-nome", r.nome);
      d3.select(this).select("line").attr("x1", x1).attr("y1", y1).attr("x2", x2).attr("y2", y2);
      d3.select(this).select("circle").attr("cx", x2).attr("cy", y2);
    });
  }

  function acender(nome) {
    svgLinhas.selectAll("g").classed("acesa", (r) => r.nome === nome);
    d3.selectAll("button.chamada").classed("acesa", (r) => r.nome === nome);
    const anc = chamadasAtuais.find((r) => r.nome === nome)?.anc;
    gBolhas.selectAll("circle").classed("acesa", (d) => !!anc && d.ibge === anc.ibge);
  }

  /** O rosto do autor escolhido nas bolhas dele; sem autor, bolha lisa. */
  function aplicarCaras() {
    gBolhas.selectAll("circle").attr("display", null)
      .classed("foto", comCara())
      .style("fill", comCara() ? "url(#cara-autor)" : null);
    escolherRetratos();
  }

  function recalcular() {
    const visiveis = lugares
      .filter((d) => valorDe(d) > 0 && !(semDF && d.ibge === DF))
      .sort((a, b) => valorDe(b) - valorDe(a));
    const vals = visiveis.map(valorDe);
    const max = d3.max(vals) || 1;
    const rMax = Math.min(34, Math.max(18, (window.innerWidth || 900) / 34));
    raio = escala === "raiz"
      ? d3.scaleSqrt().domain([0, max]).range([0, rMax])
      : d3.scaleLog().domain([Math.max(1, d3.min(vals) || 1), max]).range([1.1, rMax]).clamp(true);

    emDesenho = visiveis;
    const bolhas = gBolhas.selectAll("circle").data(visiveis, (d) => d.ibge);
    bolhas.exit().remove();
    bolhas.enter().append("circle").attr("class", "bolha")
      .call(ligarEventos)
      .merge(bolhas)
      .attr("cx", (d) => projecao(d.c)[0]).attr("cy", (d) => projecao(d.c)[1])
      .attr("r", (d) => raioDe(valorDe(d)))
      .attr("data-ibge", (d) => d.ibge);

    const total = d3.sum(vals);
    totalGeral = { total, n: visiveis.length };
    pintarTotal();
    const fv = document.getElementById("faixa-v");
    if (fv) fv.textContent = `${brl(total)} em ${visiveis.length} municípios`;

    document.getElementById("top").innerHTML = visiveis.slice(0, 10).map((d) =>
      `<li data-ibge="${d.ibge}"><span><b>${escapar(d.n)}</b><small>${escapar(d.u)}</small>
         <i>${brl(valorDe(d))}</i></span></li>`).join("");

    const nota = document.getElementById("nota-cara");
    nota.hidden = !!autorSel || !caraCabe();
    document.getElementById("marca-todos").textContent = modoCara ? "esconder os retratos" : "mostrar os retratos";

    aplicarCaras();
    desenharLegenda(max);
  }

  function rotuloAno() { return iAno === ANOS.length ? "2014–2026" : String(ANOS[iAno]); }

  function desenharLegenda(max) {
    const l = d3.select("#legenda"); l.selectAll("*").remove();
    const passos = [max, max / 4, max / 25].filter((v) => v > 0);
    const rBase = Math.max(6, raio(passos[0]) || 1);
    // A caixa acompanha a maior bolha: com altura fixa o rótulo de cima saía cortado.
    const alt = 2 * rBase + 12, larg = 2 * rBase + 86;
    l.attr("viewBox", `0 0 ${larg} ${alt}`).attr("width", larg).attr("height", alt)
     .style("width", larg + "px").style("height", alt + "px");
    const cx = rBase + 2;
    for (const v of passos) {
      const r = Math.max(1.4, raio(v));
      l.append("circle").attr("cx", cx).attr("cy", alt - 4 - r).attr("r", r);
      l.append("text").attr("x", cx + rBase + 7).attr("y", alt - 4 - 2 * r).attr("dy", "0.35em").text(brl(v));
    }
  }

  let fixado = null;   // ibge do município com o cartão preso pelo clique
  function mostrar(d, ev, prender = false) {
    if (fixado && !prender && fixado !== d.ibge) return;   // com cartão preso, o hover não manda
    if (prender) fixado = d.ibge;
    gBolhas.selectAll("circle").classed("acesa", (x) => x.ibge === d.ibge);
    const total = d.s.reduce((a, b) => a + b, 0);
    const lista = (arr) => arr.length
      ? arr.map(([k, v]) => `${k} <span style="color:var(--texto-3)">${brl(v)}</span>`).join(" · ") : "—";
    cartao.innerHTML = `
      <h2>${d.n} <span>${d.u}</span></h2>
      <p class="val">${brl(valorDe(d))}</p>
      <p class="sub">pago em ${rotuloAno()}${iAno === ANOS.length ? "" : ` · ${brl(total)} em 2014–2026`}</p>
      <dl>
        <dt>Áreas</dt><dd>${lista(d.ar)}</dd>
        <dt>Quem mandou</dt><dd class="autores-cara">${d.au.length ? d.au.map(([nome, v]) =>
          `<div data-autor="${escapar(nome)}">${cara(nome, "p")}
             <span><b>${escapar(nome)}</b> ${brl(v)}</span></div>`).join("") : "—"}</dd>
        <dt>Tipos</dt><dd>${lista(d.t)}</dd>
      </dl>
      <p class="sub" style="margin-top:7px">Áreas, autores e tipos: todo o período.</p>
      <p class="dica">Clique na bolha para ver as emendas dela, uma a uma.</p>`;
    cartao.classList.toggle("fixo", fixado === d.ibge);
    cartao.hidden = false;
    const r = cartao.getBoundingClientRect(), m = palco.getBoundingClientRect();
    cartao.style.left = Math.min(m.width - r.width - 10, Math.max(10, ev.clientX - m.left + 16)) + "px";
    cartao.style.top = Math.min(m.height - r.height - 10, Math.max(10, ev.clientY - m.top + 14)) + "px";
  }
  function esconder(forcar = false) {
    if (fixado && !forcar) return;
    fixado = null;
    cartao.hidden = true;
    cartao.classList.remove("fixo");
    gBolhas.selectAll("circle").classed("acesa", false);
  }

  // No cartão preso: ✕ fecha, e um clique no autor leva o mapa para ele.
  cartao.onclick = async (ev) => {
    if (ev.target.closest(".fechar")) { esconder(true); return; }
    const alvo = ev.target.closest("[data-autor]");
    if (!alvo) return;
    const nome = alvo.dataset.autor;
    await carregarAutores();
    if (!porAutor.autores[nome]) return;    // "Sem Informação" e afins não viram seleção
    esconder(true);
    escolher(nome);
  };
  // Clicar no vazio do mapa solta o cartão.
  svg.on("click", () => esconder(true));

  // ---- Modo município: a bolha é a porta de entrada --------------------------------------
  // Clicou numa bolha: o mapa centra nela, o resto esmaece, e o painel lista as emendas do
  // município uma a uma (um arquivo por município, baixado na hora).
  let munSel = null, munDados = null, munFiltro = "", munBusca = "", munLimite = 60;
  const elMun = {
    nome: document.getElementById("mun-nome"), resumo: document.getElementById("mun-resumo"),
    busca: document.getElementById("mun-busca"), chips: document.getElementById("mun-chips"),
    conta: document.getElementById("mun-conta"), lista: document.getElementById("mun-lista"),
    mais: document.getElementById("mun-mais"),
  };

  async function abrirMunicipio(d) {
    const trocou = munSel?.ibge !== d.ibge;
    munSel = d; munFiltro = ""; munBusca = ""; munLimite = 60; elMun.busca.value = "";
    esconder(true);
    if (!main.classList.contains("com-mun")) { main.classList.add("com-mun"); dimensionar(); }
    focarMunicipio(d);
    if (trocou) { munDados = null; pintarMunicipio(); }
    const [dados] = await Promise.all([d3.json(`${BASE}/mun/${d.ibge}.json`).catch(() => []), carregarPop()]);
    if (munSel !== d) return;
    munDados = dados;
    pintarMunicipio();
  }
  function focarMunicipio(d) {
    gBolhas.selectAll("circle").classed("escolhida", (x) => x.ibge === d.ibge);
    const m = palco.getBoundingClientRect(), [x, y] = projecao(d.c), k = 7;
    svg.transition().duration(650).call(zoom.transform,
      d3.zoomIdentity.translate(m.width / 2 - k * x, m.height / 2 - k * y).scale(k));
  }
  function fecharMunicipio() {
    munSel = null; munDados = null;
    main.classList.remove("com-mun");
    gBolhas.selectAll("circle").classed("escolhida", false);
    dimensionar();
  }
  // Uma emenda paga em mais de um ano entra no ano escolhido se o pagamento passou por ele; o valor
  // mostrado é o total dela (o arquivo não reparte por ano), e o texto do resumo avisa.
  const noAno = (l) => iAno === ANOS.length || (l[3] <= ANOS[iAno] && ANOS[iAno] <= l[4]);
  const munDoAno = () => (munDados ?? []).filter(noAno);
  const munFiltradas = () => munDoAno().filter((l) => {
    if (munFiltro && l[2] !== munFiltro) return false;
    if (!munBusca) return true;
    const t = munBusca.toLowerCase();
    return [l[0], l[1], l[6], l[7], l[8]].some((c) => c && String(c).toLowerCase().includes(t));
  });
  /** O número no alto é do que está em foco: o Brasil (ou o autor), ou o município aberto. */
  let totalGeral = { total: 0, n: 0 };
  function pintarTotal() {
    const el = document.getElementById("total"), sub = document.getElementById("total-sub");
    el.parentElement.classList.toggle("mun", !!munSel);
    if (munSel) {
      const d = munSel;
      el.textContent = brl(valorDe(d));
      sub.textContent = `${d.n}, ${d.u} · ${munDados ? `${munDados.length} emendas · ` : ""}${rotuloAno()}`;
      return;
    }
    el.textContent = brl(totalGeral.total);
    sub.textContent = `${totalGeral.n.toLocaleString("pt-BR")} municípios · ${rotuloAno()}`
      + `${filtroTipo && !autorSel ? ` · só ${filtroTipo.toLowerCase()}` : ""}`
      + `${semDF ? " · sem Brasília" : ""}`;
  }

  // População do /mapa/ (anos/2024.json: [pop, despesa, …] por município), para o "por habitante".
  let popDe = null;
  async function carregarPop() {
    if (popDe) return popDe;
    const doc = await d3.json("/data/mapa/anos/2024.json").catch(() => null);
    popDe = new Map(Object.entries(doc?.mun ?? {}).map(([k, v]) => [k, v?.[0]]));
    return popDe;
  }
  const slugDe = (s) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  function pintarMunicipio() {
    const d = munSel; if (!d) return;
    pintarTotal();
    const todas = munDoAno();
    const total = valorDe(d);
    const saude = todas.filter((l) => l[7] === "Saúde").reduce((a, l) => a + l[5], 0);
    const somaLista = todas.reduce((a, l) => a + l[5], 0);
    const pop = popDe?.get(d.ibge);
    const hab = pop ? ` · <b>${brl(total / pop)}</b> por habitante (${(pop / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil hab.)` : "";
    const ficha = `/cidades/${d.u.toLowerCase()}/${slugDe(d.n)}/`;
    elMun.nome.innerHTML = `${escapar(d.n)}<small>${escapar(d.u)}</small>
      <a class="ficha" href="${ficha}" title="A ficha de ${escapar(d.n)} no Orçamento Brasileiro">Ficha da cidade →</a>`;
    elMun.resumo.innerHTML = munDados
      ? `Recebeu <b>${brl(total)}</b> em <b>${todas.length.toLocaleString("pt-BR")} emendas</b> em ${rotuloAno()}`
        + (somaLista ? ` · ${Math.round((100 * saude) / somaLista)}% para a saúde` : "") + hab
        + ` · <a href="/emendas/buscar?ente=${d.ibge}">abrir no buscador de emendas</a>`
      : `Carregando as emendas…`;
    // chips por tipo, com as contagens
    const porTipo = d3.rollup(todas, (v) => v.length, (l) => l[2]);
    const ordem = ["Individual", "Comissão", "Bancada", "Relator", "Pix"].filter((t) => porTipo.has(t));
    elMun.chips.innerHTML = [["", `Todas · ${todas.length}`], ...ordem.map((t) => [t, `${t} · ${porTipo.get(t)}`])]
      .map(([t, r]) => `<button type="button" data-t="${t}" aria-pressed="${t === munFiltro}">${r}</button>`).join("");
    const f = munFiltradas();
    elMun.conta.textContent = munDados ? `${Math.min(munLimite, f.length)} de ${f.length}` : "";
    elMun.lista.innerHTML = f.length ? f.slice(0, munLimite).map(([num, autor, tipo, a0, a1, mil, fav, area, obj]) => `
      <li>
        ${cara(autor)}
        <div style="min-width:0">
          <div class="quem"><button type="button" data-autor="${escapar(autor)}">${escapar(autor)}</button>
            <small>${tipo} · ${a0 === a1 ? a0 : `${a0}–${a1}`}</small></div>
          <div class="objeto${obj ? "" : " vazio"}">${obj ? escapar(obj) : "Sem objeto informado"}</div>
          <div class="para">para <b>${escapar(fav ?? "—")}</b> · ${escapar(area ?? "—")}${num && num !== "Sem informação"
            ? ` · <a href="/emendas/buscar?emenda=${encodeURIComponent(num)}" title="A ficha desta emenda: todos os pagamentos, para quem e onde">emenda ${escapar(num)} →</a>
               <a class="externo" href="https://portaldatransparencia.gov.br/emendas/detalhe?codigoEmenda=${encodeURIComponent(num)}&amp;ano=${escapar(String(num).slice(0, 4))}" target="_blank" rel="noopener" title="No Portal da Transparência">Portal ↗</a>`
            : " · sem número de emenda"}</div>
        </div>
        <div class="valor">${brl(mil)}</div>
      </li>`).join("")
      : `<li class="nada">${munDados ? "Nenhuma emenda com esse filtro." : ""}</li>`;
    elMun.mais.hidden = f.length <= munLimite;
    elMun.mais.textContent = `Mostrar mais ${Math.min(60, f.length - munLimite)} de ${f.length - munLimite} restantes`;
  }
  document.getElementById("mun-voltar").onclick = fecharMunicipio;
  elMun.busca.oninput = () => { munBusca = elMun.busca.value.trim(); munLimite = 60; pintarMunicipio(); };
  elMun.chips.onclick = (ev) => { const b = ev.target.closest("button"); if (!b) return; munFiltro = b.dataset.t; munLimite = 60; pintarMunicipio(); };
  elMun.mais.onclick = () => { munLimite += 60; pintarMunicipio(); };
  // o nome do autor na lista vira busca por ele, sem sair do município
  elMun.lista.onclick = (ev) => {
    const b = ev.target.closest("button[data-autor]"); if (!b) return;
    munBusca = elMun.busca.value = b.dataset.autor; munLimite = 60; pintarMunicipio();
  };
  document.getElementById("mun-csv").onclick = () => {
    if (!munSel || !munDados) return;
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const txt = ["emenda;autor;tipo;ano_inicio;ano_fim;valor_reais;favorecido;area;objeto",
      ...munFiltradas().map((l) => [l[0], l[1], l[2], l[3], l[4], l[5] * 1000, l[6], l[7], l[8]].map(esc).join(";"))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\ufeff" + txt], { type: "text/csv;charset=utf-8" }));
    a.download = `emendas-${munSel.ibge}-${munSel.n.normalize("NFD").replace(/[^\w]+/g, "-").toLowerCase()}.csv`;
    a.click(); URL.revokeObjectURL(a.href);
  };

  const zoom = d3.zoom().scaleExtent([1, 40])
    .on("start", () => svg.classed("arrastando", true))
    .on("end", () => { svg.classed("arrastando", false); aplicarCaras(); })
    .on("zoom", (ev) => {
      g.attr("transform", ev.transform);
      kZoom = ev.transform.k;
      gBolhas.selectAll("circle").attr("r", (d) => raioDe(valorDe(d)));
      desenharLinhas();
      gUf.attr("stroke-width", 0.6 / ev.transform.k);
    });
  svg.call(zoom);

  const temColunas = () => modoCara && !autorSel && !munSel && caraCabe() && innerWidth > 1100;
  /** Redesenha; se as colunas entraram ou saíram, o palco mudou de largura e o mapa é reajustado. */
  function refluir() {
    if (main.classList.contains("sem-colunas") === !temColunas()) recalcular();
    else dimensionar();
  }
  function dimensionar() {
    // Sem colunas quando não há o que pôr nelas, antes de medir: o mapa ganha a largura toda.
    main.classList.toggle("sem-colunas", !temColunas());
    const m = palco.getBoundingClientRect();
    svg.attr("viewBox", `0 0 ${m.width} ${m.height}`);
    projecao.fitExtent([[18, 18], [m.width - 18, m.height - 18]], uf);
    gUf.selectAll("path").data(uf.features).join("path").attr("class", "uf").attr("d", caminho);
    recalcular();
    svg.call(zoom.transform, d3.zoomIdentity);
  }
  addEventListener("resize", dimensionar);

  const seletorAno = document.getElementById("ano");
  seletorAno.innerHTML = [`<option value="${ANOS.length}">2014–2026, tudo</option>`,
    ...ANOS.map((a, i) => `<option value="${i}">${a}${a === 2026 ? " (até agora)" : ""}</option>`).reverse()].join("");
  seletorAno.value = String(ANOS.length);
  seletorAno.onchange = () => { iAno = +seletorAno.value; recalcular(); esconder(); if (munSel) pintarMunicipio(); };
  const grupo = (sel, aplicar) => {
    for (const b of document.querySelectorAll(`${sel} button`)) b.onclick = () => {
      aplicar(b);
      for (const o of document.querySelectorAll(`${sel} button`)) o.ariaPressed = String(o === b);
      refluir(); esconder();
    };
  };
  document.getElementById("marca-todos").onclick = () => { modoCara = !modoCara; refluir(); };
  grupo("#tipo", (b) => { filtroTipo = b.dataset.t; if (porAutor) pintarLista(); });
  grupo("#escala", (b) => { escala = b.dataset.e; });
  // Brasília não é um controle: é uma decisão de edição, explicada no aviso, com uma saída para quem quiser ver.
  const verDf = document.getElementById("ver-df");
  verDf.onclick = (ev) => {
    ev.preventDefault();
    semDF = !semDF;
    verDf.textContent = semDF ? "Ver com Brasília" : "Esconder Brasília de novo";
    recalcular(); esconder();
  };

  // ---- Seletor de autor -------------------------------------------------------------------
  // O arquivo por autor (3,8 MB) só é baixado quando alguém abre o seletor.
  let porAutor = null;
  const abre = document.getElementById("abre-autor"), painel = document.getElementById("painel-autor");
  const fundo = document.getElementById("fundo-autor"), lista = document.getElementById("lista-autor");
  const busca = document.getElementById("busca-autor"), faixa = document.getElementById("faixa");
  async function carregarAutores() {
    if (porAutor) return porAutor;
    lista.innerHTML = `<li style="color:var(--texto-2)">Carregando os autores…</li>`;
    porAutor = await d3.json(`${BASE}/por-autor.json`);
    return porAutor;
  }

  function pintarLista() {
    if (!porAutor) return;
    const termo = busca.value.trim().toLowerCase();
    const itens = Object.entries(porAutor.autores)
      .filter(([nome, a]) => nome !== "Sem Informação"
        && (!filtroTipo || a.tipo === filtroTipo)
        && (!termo || nome.toLowerCase().includes(termo)))
      .sort((a, b) => b[1].t - a[1].t).slice(0, 60);
    // Primeira linha sempre: sem ela, quem escolhe um autor fica preso nele — o ✕ da faixa
    // é o único caminho de volta e passa despercebido.
    const voltar = `<li data-autor="" aria-current="${!autorSel}">
      <span class="cara vazia">BR</span>
      <span><b>Todos os autores</b><small>o país inteiro, somando todo mundo</small></span></li>`;
    lista.innerHTML = voltar + (itens.length ? itens.map(([nome, a]) => `
      <li data-autor="${escapar(nome)}" aria-current="${nome === autorSel}">
        ${cara(nome)}
        <span><b>${escapar(nome)}</b><small>${escapar(legenda2(nome))} · ${a.tipo}</small></span>
        <i>${brl(a.t)}</i>
      </li>`).join("") : `<li style="color:var(--texto-2)">Nada com esse nome.</li>`);
  }

  function abrirPainel(abrir) {
    abre.setAttribute("aria-expanded", String(abrir));
    painel.hidden = fundo.hidden = !abrir;
    if (!abrir) return;
    const r = abre.getBoundingClientRect();
    painel.style.left = Math.min(innerWidth - 362, r.left) + "px";
    painel.style.top = r.bottom + 4 + "px";
    busca.value = "";              // reabrir sempre começa do zero, senão o texto antigo se acumula
    carregarAutores().then(pintarLista);
    busca.focus();
  }

  function escolher(nome) {
    if (nome && munSel) fecharMunicipio();
    autorSel = nome;
    if (!nome) {
      serieAutor = null; faixa.hidden = true;
      document.getElementById("autor-rotulo").textContent = "todos os autores";
    } else {
      const a = porAutor.autores[nome];
      serieAutor = new Map();
      for (const [iMun, iA, v] of a.p) {
        const ibge = porAutor.ibges[iMun];
        let s = serieAutor.get(ibge);
        if (!s) serieAutor.set(ibge, (s = new Array(ANOS.length).fill(0)));
        s[iA] += v;
      }
      document.getElementById("autor-rotulo").textContent = nome;
      const foto = caras[nome]?.foto;
      padraoImg.attr("href", foto || null);
      faixa.innerHTML = `${cara(nome, "g")}
        <span><h2>${escapar(nome)}</h2><small>${escapar(legenda2(nome))}</small>
          <span class="v" id="faixa-v"></span></span>
        ${foto ? `<button type="button" class="troca" id="troca-marca"></button>` : ""}
        <button type="button" id="limpa-autor" title="Ver todos os autores">✕</button>`;
      faixa.hidden = false;
      document.getElementById("limpa-autor").onclick = () => { escolher(null); pintarLista(); };
      const tm = document.getElementById("troca-marca");
      if (tm) {
        const rotular = () => { tm.textContent = modoCara ? "ver como bolha" : "ver a cara"; };
        rotular();
        tm.onclick = () => { modoCara = !modoCara; rotular(); recalcular(); };
      }
    }
    document.getElementById("tipo").closest(".cel").classList.toggle("inerte", !!nome);
    abrirPainel(false);
    refluir(); esconder();
  }

  abre.onclick = () => abrirPainel(abre.getAttribute("aria-expanded") !== "true");
  fundo.onclick = () => abrirPainel(false);
  busca.oninput = pintarLista;
  lista.onclick = (ev) => { const li = ev.target.closest("li[data-autor]"); if (li) escolher(li.dataset.autor); };
  addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    if (!painel.hidden) abrirPainel(false);
    else if (munSel) fecharMunicipio();
    else esconder(true);
  });
  document.getElementById("top").onpointerover = (ev) => {
    const li = ev.target.closest("li"); if (!li) return;
    const d = lugares.find((x) => x.ibge === li.dataset.ibge);
    if (d) mostrar(d, { clientX: li.getBoundingClientRect().left - 16, clientY: li.getBoundingClientRect().top });
  };
  document.getElementById("top").onpointerleave = esconder;

  // No computador o aviso fica aberto; no celular, fechado, senão come a tela do mapa.
  const aviso = document.getElementById("aviso");
  // Começa fechado: o aviso é leitura de uma vez, e aberto comia a tela.
  aviso.open = false;
  aviso.ontoggle = () => requestAnimationFrame(dimensionar);

  dimensionar();
})();
