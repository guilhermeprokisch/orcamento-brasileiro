// Fala com o comando `lai`, que roda só neste computador (127.0.0.1:8765). A página do órgão não pode chamar esse
// endereço direto (o navegador bloqueia), então o preencher.js pede por aqui.
const BASE = "http://127.0.0.1:8765";

chrome.runtime.onMessage.addListener((msg, _remetente, responder) => {
  if (msg.tipo === "pedido") {
    fetch(`${BASE}/pedido?senha=${encodeURIComponent(msg.senha)}`)
      .then((r) => (r.ok ? r.json() : { erro: `o comando respondeu ${r.status}` }))
      .then(responder)
      .catch(() => responder({ erro: "o comando lai não está rodando" }));
    return true;
  }
  if (msg.tipo === "evento") {
    fetch(`${BASE}/evento`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(msg.corpo) })
      .then(() => responder({ ok: true }))
      .catch(() => responder({ erro: "o comando lai não está rodando" }));
    return true;
  }
  return false;
});
