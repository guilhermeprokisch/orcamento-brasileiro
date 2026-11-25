/**
 * Parar de seguir.
 *   GET  /api/sair?t=<token>[&a=<alvo>]  → leva à página que pede para confirmar (/seguir/sair)
 *   POST /api/sair?t=<token>[&a=<alvo>]  → apaga; sem `a`, apaga a pessoa e tudo que ela segue.
 * O POST também atende o "cancelar inscrição" com um clique do Gmail e de outros (RFC 8058), que manda
 * "List-Unsubscribe=One-Click" no corpo e espera só um 200.
 */
import { ALVO, prepararBanco, type Contexto } from "../../servidor/seguir";

export async function onRequestGet({ request }: Contexto): Promise<Response> {
  const url = new URL(request.url);
  return Response.redirect(new URL(`/seguir/sair${url.search}`, url).toString(), 303);
}

export async function onRequestPost({ request, env }: Contexto): Promise<Response> {
  const url = new URL(request.url);
  const corpo = await request.text();
  const form = new URLSearchParams(corpo);
  const umClique = form.get("List-Unsubscribe") === "One-Click";
  const t = form.get("t") ?? url.searchParams.get("t") ?? "";
  const a = form.get("a") ?? url.searchParams.get("a") ?? "";
  const pronto = (q: string) => (umClique ? new Response("ok") : Response.redirect(new URL(`/seguir/sair?${q}`, url).toString(), 303));

  if (!env.DB || !t) return pronto("erro=1");
  await prepararBanco(env.DB);
  const p = await env.DB.prepare("SELECT id FROM pessoas WHERE token = ?").bind(t).first<{ id: number }>();
  // Token que não existe mais: a pessoa já saiu. Para quem clicou, dá no mesmo.
  if (!p) return pronto(`feito=1${a ? `&a=${encodeURIComponent(a)}` : ""}`);

  if (a && ALVO.test(a)) {
    await env.DB.prepare("DELETE FROM seguindo WHERE pessoa_id = ? AND alvo = ?").bind(p.id, a).run();
    const resto = await env.DB.prepare("SELECT COUNT(*) AS n FROM seguindo WHERE pessoa_id = ?").bind(p.id).first<{ n: number }>();
    if (!resto?.n) await env.DB.prepare("DELETE FROM pessoas WHERE id = ?").bind(p.id).run();
    return pronto(`feito=1&a=${encodeURIComponent(a)}`);
  }
  await env.DB.batch([
    env.DB.prepare("DELETE FROM seguindo WHERE pessoa_id = ?").bind(p.id),
    env.DB.prepare("DELETE FROM pessoas WHERE id = ?").bind(p.id),
  ]);
  return pronto("feito=1");
}
