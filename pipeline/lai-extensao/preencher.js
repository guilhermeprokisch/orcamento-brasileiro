// Preenche o formulário quando a página abre com #lai=<senha> (o comando `lai enviar` abre assim). Sem a senha, não
// faz nada. Não clica em enviar. Depois do envio, procura o protocolo na página e manda ao comando.
(() => {
  const CHAVE = "lai-senha";
  const casou = location.hash.match(/lai=([\w-]+)/);
  let senha = casou ? casou[1] : null;
  if (casou) {
    sessionStorage.setItem(CHAVE, senha); // para achar o protocolo se a página recarregar depois do envio
    history.replaceState(null, "", location.pathname + location.search); // tira a senha do endereço
  } else {
    senha = sessionStorage.getItem(CHAVE);
    if (!senha) return;
    observarResultado(senha); // voltou depois do envio
    return;
  }

  const evento = (corpo) => chrome.runtime.sendMessage({ tipo: "evento", corpo: { senha, ...corpo } });
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").trim().toLowerCase();

  function faixa(texto, cor = "#0e6b3b") {
    let el = document.getElementById("lai-faixa");
    if (!el) {
      el = document.createElement("div");
      el.id = "lai-faixa";
      el.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:2147483647;padding:12px 16px;font:15px/1.4 system-ui,sans-serif;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,.3)";
      document.documentElement.appendChild(el);
    }
    el.style.background = cor;
    el.textContent = texto;
  }

  async function achar(seletor, ms = 30000) {
    for (let t = 0; t < ms; t += 250) {
      const el = document.querySelector(seletor);
      if (el) return el;
      await espera(250);
    }
    throw new Error(`não achei ${seletor}`);
  }

  // Campos controlados por React só aceitam o valor pelo "setter" nativo, seguido dos eventos.
  function definir(el, valor) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, valor);
    for (const tipo of ["input", "change", "blur"]) el.dispatchEvent(new Event(tipo, { bubbles: true }));
  }

  async function executar(p) {
    const el = await achar(p.seletor);
    if (p.acao === "preencher") {
      if (p.valor) definir(el, p.valor);
    } else if (p.acao === "marcar") {
      if (!el.checked) el.click();
    } else if (p.acao === "escolher") {
      if (!p.texto) return;
      for (let t = 0; t < 20000; t += 250) { // o município só carrega depois da UF
        const op = [...el.options].find((o) => norm(o.text) === norm(p.texto));
        if (op) return definir(el, op.value);
        await espera(250);
      }
      throw new Error(`não achei a opção "${p.texto}"`);
    } else {
      throw new Error(`passo desconhecido: ${p.acao}`);
    }
    await espera(150);
  }

  (async () => {
    faixa("lai: buscando o pedido no seu computador…");
    const pedido = await chrome.runtime.sendMessage({ tipo: "pedido", senha });
    if (!pedido || pedido.erro) {
      faixa(`lai: ${pedido ? pedido.erro : "sem resposta"}. Rode de novo o comando lai enviar.`, "#a8461f");
      sessionStorage.removeItem(CHAVE);
      return;
    }
    try {
      if (pedido.pronto) await achar(pedido.pronto);
      for (const p of pedido.passos) await executar(p);
    } catch (e) {
      faixa(`lai: ${e.message}. Complete à mão.`, "#a8461f");
      evento({ tipo: "erro", mensagem: e.message });
      return;
    }
    faixa("lai: formulário preenchido. Confira os dados e clique em Enviar. Depois, o protocolo vai sozinho para o terminal.");
    evento({ tipo: "preenchido" });
    observarResultado(senha);
  })();

  function observarResultado(senha) {
    const PALAVRAS = /protocolo|registrad[ao]|recebid[ao]|enviad[ao] com sucesso|sucesso/i;
    const inicial = document.body ? document.body.innerText : "";
    let enviado = false;
    const olhar = () => {
      if (enviado || !document.body) return;
      const texto = document.body.innerText;
      const m = texto.match(PALAVRAS);
      if (!m || inicial.includes(texto.slice(Math.max(0, m.index - 100), m.index + 200))) return;
      enviado = true;
      const trecho = texto.slice(Math.max(0, m.index - 300), m.index + 300);
      chrome.runtime.sendMessage({ tipo: "evento", corpo: { senha, tipo: "resultado", trecho } });
      sessionStorage.removeItem(CHAVE);
      const el = document.getElementById("lai-faixa");
      if (el) el.textContent = "lai: confirmação lida e mandada ao terminal.";
    };
    new MutationObserver(olhar).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    setTimeout(olhar, 1000);
  }
})();
