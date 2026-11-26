/** GET /api/confirmar?t=<token> — o link do e-mail de confirmação. Confirma tudo que a pessoa pediu para seguir. */
import { agora, prepararBanco, type Contexto } from "../../servidor/seguir";

export async function onRequestGet({ request, env }: Contexto): Promise<Response> {
  const url = new URL(request.url);
  const volta = (q: string) => Response.redirect(new URL(`/seguir/confirmado?${q}`, url).toString(), 303);
  const t = url.searchParams.get("t") ?? "";
  if (!env.DB || !t) return volta("erro=1");
  await prepararBanco(env.DB);
  const p = await env.DB.prepare("SELECT id FROM pessoas WHERE token = ?").bind(t).first<{ id: number }>();
  if (!p) return volta("erro=1");
  await env.DB.batch([
    env.DB.prepare("UPDATE seguindo SET confirmado = 1 WHERE pessoa_id = ?").bind(p.id),
    env.DB.prepare("UPDATE pessoas SET confirmado_em = COALESCE(confirmado_em, ?) WHERE id = ?").bind(agora(), p.id),
  ]);
  const alvos = (await env.DB.prepare("SELECT alvo FROM seguindo WHERE pessoa_id = ? ORDER BY criado_em").bind(p.id).all<{ alvo: string }>()).results.map((r) => r.alvo);
  return volta(`a=${encodeURIComponent(alvos.join(","))}`);
}
