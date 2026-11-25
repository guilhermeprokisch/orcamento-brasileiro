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

  const gUf = g.append("g");
  // Bolhas e grupos ficam fora do <g> do zoom, em coordenadas de tela: o tamanho do marcador é em
  // pixels, e a cada passo do zoom eles só mudam de lugar; ao fim do gesto, os grupos são refeitos.
  const gBolhas = svg.append("g").attr("class", "camada-bolhas"), gGrupos = svg.append("g").attr("class", "camada-grupos");
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
  let emDesenho = [];           // os municípios do desenho atual, do maior para o menor
  // Os retratos são de parlamentares. Filtrando por bancada, relator ou comissão, o dinheiro na
  // tela não é deles: os grupos ficam sem rosto, para não sugerir uma ligação que não existe.
  const caraCabe = () => !filtroTipo || filtroTipo === "Individual" || filtroTipo === "Pix";
  const main = document.getElementById("main"), palco = document.getElementById("palco");

  // Uma escala só para tudo que está na tela: a área do círculo é o valor, seja de um município
  // sozinho, seja de um grupo. O domínio vai até o maior grupo da escala atual.
  let raio = d3.scaleSqrt().range([0, 46]);
  const R_MIN_BOLHA = 3.5, R_MIN_GRUPO = 15, CELULA = 88;   // px

  const ligarEventos = (sel) => sel
    .on("pointerenter", (ev, d) => mostrar(d, ev))
    .on("pointermove", (ev, d) => mostrar(d, ev))
    .on("pointerleave", () => esconder())
    .on("click", (ev, d) => { ev.stopPropagation(); abrirMunicipio(d); });

  /** Um <pattern> por parlamentar, criado na hora em que o primeiro grupo precisa dele. */
  const padroes = new Map();
  function padraoDe(nome) {
    if (padroes.has(nome)) return padroes.get(nome);
    const foto = caras[nome]?.foto;
    if (!foto) { padroes.set(nome, null); return null; }
    const id = `cara-${padroes.size}`;
    defs.append("pattern").attr("id", id).attr("patternContentUnits", "objectBoundingBox").attr("width", 1).attr("height", 1)
      .append("image").attr("width", 1).attr("height", 1).attr("preserveAspectRatio", "xMidYMin slice").attr("href", foto);
    padroes.set(nome, id);
    return id;
  }

  // ---- Agrupamento: municípios vizinhos na escala atual viram um grupo ----------------------
  // A célula é fixa em pixels: ao aproximar, cabem menos municípios em cada uma e os grupos se
  // abrem, até sobrar um município por célula. Com uma cidade aberta não se agrupa nada.
  let grupos = [], soltos = [];
  function agrupar() {
    const t = d3.zoomTransform(svg.node());
    const m = palco.getBoundingClientRect();
    const celula = munSel ? 0 : CELULA;
    const cels = new Map();
    for (const d of emDesenho) {
      const p = projecao(d.c), [x, y] = t.apply(p);
      if (x < -CELULA || y < -CELULA || x > m.width + CELULA || y > m.height + CELULA) continue;
      const v = valorDe(d);
      const chave = celula ? `${Math.floor(x / celula)},${Math.floor(y / celula)}` : d.ibge;
      let g = cels.get(chave);
      if (!g) cels.set(chave, (g = { itens: [], v: 0, sx: 0, sy: 0, por: new Map(), maior: d }));
      g.itens.push(d); g.v += v; g.sx += p[0] * v; g.sy += p[1] * v;
      if (valorDe(g.maior) < v) g.maior = d;
      if (!autorSel) for (const [nome, val] of d.ap ?? []) g.por.set(nome, (g.por.get(nome) ?? 0) + val);
    }
    grupos = []; soltos = [];
    for (const g of cels.values()) {
      if (g.itens.length === 1) { soltos.push(g.itens[0]); continue; }
      g.px = g.sx / g.v; g.py = g.sy / g.v;
      g.id = g.itens.map((d) => d.ibge).sort().join("|");
      // quem mandou mais para o grupo, entre os parlamentares (não os colegiados), com foto
      g.quem = autorSel ? [[autorSel, g.v]] : [...g.por.entries()].sort((a, b) => b[1] - a[1]);
      g.dono = g.quem.find(([n]) => caras[n]?.foto)?.[0] ?? null;
      grupos.push(g);
    }
    const maior = Math.max(d3.max(grupos, (g) => g.v) ?? 0, d3.max(soltos, valorDe) ?? 0, 1);
    raio.domain(escala === "raiz" ? [0, maior] : [Math.max(1, (d3.min(soltos, valorDe) ?? 1)), maior]);
    desenharMarcas();
    desenharLegenda(maior);
  }

  const raioGrupo = (g) => Math.max(R_MIN_GRUPO, raio(g.v));
  const raioSolto = (d) => Math.max(R_MIN_BOLHA, raio(valorDe(d)));
  const comRosto = () => modoCara && caraCabe();

  function desenharMarcas() {
    const t = d3.zoomTransform(svg.node());
    // municípios sozinhos: a bolha de sempre, agora em px de tela
    const bolhas = gBolhas.selectAll("circle").data(soltos, (d) => d.ibge);
    bolhas.exit().remove();
    const autorPadrao = comCara() ? "url(#cara-autor)" : null;
    bolhas.enter().append("circle").attr("class", "bolha").call(ligarEventos).merge(bolhas)
      .attr("data-ibge", (d) => d.ibge)
      .attr("r", raioSolto)
      .classed("foto", !!autorPadrao)
      .classed("escolhida", (d) => munSel?.ibge === d.ibge)
      .style("fill", autorPadrao)
      .each(function (d) { const [x, y] = t.apply(projecao(d.c)); d3.select(this).attr("cx", x).attr("cy", y); });

    // grupos: círculo com o retrato de quem mais mandou e o número de municípios
    const gs = gGrupos.selectAll("g.marca-grupo").data(grupos, (g) => g.id);
    gs.exit().remove();
    const novos = gs.enter().append("g").attr("class", "marca-grupo")
      .on("pointerenter", (ev, g) => mostrarGrupo(g, ev))
      .on("pointermove", (ev, g) => mostrarGrupo(g, ev))
      .on("pointerleave", () => esconder())
      .on("click", (ev, g) => { ev.stopPropagation(); esconder(true); aproximarGrupo(g); });
    novos.append("circle").attr("class", "fundo");
    novos.append("circle").attr("class", "aro");
    novos.append("rect").attr("class", "selo").attr("rx", 9).attr("height", 18);
    novos.append("text").attr("class", "selo-txt").attr("text-anchor", "middle").attr("dy", "0.35em");
    novos.merge(gs).each(function (g) {
      const r = raioGrupo(g), [x, y] = t.apply([g.px, g.py]);
      const padrao = comRosto() && g.dono ? padraoDe(g.dono) : null;
      const n = String(g.itens.length), larg = 12 + 7 * n.length;
      const sel = d3.select(this).attr("transform", `translate(${x},${y})`).classed("foto", !!padrao);
      sel.select(".fundo").attr("r", r).style("fill", padrao ? `url(#${padrao})` : null);
      sel.select(".aro").attr("r", r + 1);
      sel.select(".selo").attr("x", r * 0.62 - larg / 2).attr("y", -r * 0.62 - 9).attr("width", larg);
      sel.select(".selo-txt").attr("x", r * 0.62).attr("y", -r * 0.62).text(n);
    });
  }

  /** Durante o gesto do zoom, só muda de lugar; os grupos são refeitos ao soltar. */
  function reposicionar() {
    const t = d3.zoomTransform(svg.node());
    gBolhas.selectAll("circle").each(function (d) { const [x, y] = t.apply(projecao(d.c)); d3.select(this).attr("cx", x).attr("cy", y); });
    gGrupos.selectAll("g.marca-grupo").attr("transform", (g) => { const [x, y] = t.apply([g.px, g.py]); return `translate(${x},${y})`; });
  }

  /** Clique num grupo: aproxima até ele se abrir. */
  function aproximarGrupo(g) {
    const m = palco.getBoundingClientRect(), t = d3.zoomTransform(svg.node());
    const ps = g.itens.map((d) => projecao(d.c));
    const [x0, x1] = d3.extent(ps, (p) => p[0]), [y0, y1] = d3.extent(ps, (p) => p[1]);
    const cabe = 0.6 / Math.max((x1 - x0) / m.width, (y1 - y0) / m.height, 1e-9);
    const k = Math.min(40, Math.max(t.k * 2.4, Math.min(cabe, t.k * 8)));
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(m.width / 2 - k * cx, m.height / 2 - k * cy).scale(k));
  }

  function mostrarGrupo(g, ev) {
    if (fixado) return;
    gGrupos.selectAll("g.marca-grupo").classed("acesa", (x) => x.id === g.id);
    const quem = g.quem.slice(0, 3);
    cartao.innerHTML = `
      <h2>${g.itens.length} municípios <span>juntos nesta escala</span></h2>
      <p class="val">${brl(g.v)}</p>
      <p class="sub">pago em ${rotuloAno()} · maior: ${escapar(g.maior.n)} (${escapar(g.maior.u)}), ${brl(valorDe(g.maior))}</p>
      ${quem.length ? `<dl><dt>Parlamentares que mais mandaram</dt><dd class="autores-cara">${quem.map(([nome, v]) =>
        `<div>${cara(nome, "p")}<span><b>${escapar(nome)}</b> ${brl(v)}</span></div>`).join("")}</dd></dl>` : ""}
      <p class="dica">Clique para aproximar e abrir o grupo.</p>`;
    cartao.classList.remove("fixo");
    cartao.hidden = false;
    const r = cartao.getBoundingClientRect(), m = palco.getBoundingClientRect();
    cartao.style.left = Math.min(m.width - r.width - 10, Math.max(10, ev.clientX - m.left + 16)) + "px";
    cartao.style.top = Math.min(m.height - r.height - 10, Math.max(10, ev.clientY - m.top + 14)) + "px";
  }

  function recalcular() {
    const visiveis = lugares
      .filter((d) => valorDe(d) > 0 && !(semDF && d.ibge === DF))
      .sort((a, b) => valorDe(b) - valorDe(a));
    const vals = visiveis.map(valorDe);
    const rMax = Math.min(46, Math.max(26, (window.innerWidth || 900) / 26));
    raio = (escala === "raiz" ? d3.scaleSqrt() : d3.scaleLog().clamp(true)).range(escala === "raiz" ? [0, rMax] : [2, rMax]);
    emDesenho = visiveis;

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

    agrupar();
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
    gGrupos.selectAll("g.marca-grupo").classed("acesa", false);
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
    gGrupos.selectAll("g.marca-grupo").classed("acesa", false);
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
    agrupar();   // sem grupos: a cidade aberta e as vizinhas aparecem uma a uma
    const m = palco.getBoundingClientRect(), [x, y] = projecao(d.c), k = 7;
    svg.transition().duration(650).call(zoom.transform,
      d3.zoomIdentity.translate(m.width / 2 - k * x, m.height / 2 - k * y).scale(k));
  }
  function fecharMunicipio() {
    munSel = null; munDados = null;
    main.classList.remove("com-mun");
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
    .on("end", () => { svg.classed("arrastando", false); agrupar(); })
    .on("zoom", (ev) => {
      g.attr("transform", ev.transform);
      reposicionar();
      gUf.attr("stroke-width", 0.6 / ev.transform.k);
    });
  svg.call(zoom);

  const refluir = () => recalcular();
  function dimensionar() {
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
