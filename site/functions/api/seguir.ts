/**
 * POST /api/seguir  {email, alvos: ["mun-4205407", "uf-SC"]}
 * Guarda o pedido sem confirmar e manda o e-mail de confirmação. A resposta é a mesma se o e-mail já
 * seguia esses lugares, para não contar a ninguém quem segue o quê.
 */
import { ALVO, agora, emailConfirmacao, emailValido, enviar, json, lugar, novoToken, prepararBanco, type Contexto, type ResumoCurto } from "../../servidor/seguir";

/** Entre um e-mail de confirmação e outro para o mesmo endereço. */
const INTERVALO_MS = 10 * 60 * 1000;

export async function onRequestPost({ request, env }: Contexto): Promise<Response> {
  const db = env.DB;
  if (!db) return json({ erro: "Isso ainda não está funcionando. Tente de novo mais tarde." }, 503);

  let corpo: { email?: unknown; alvos?: unknown; site?: unknown };
  try {
    corpo = await request.json();
  } catch {
    return json({ erro: "Pedido inválido." }, 400);
  }
  // Campo escondido: só robô preenche.
  if (corpo.site) return json({ ok: true });

  const email = typeof corpo.email === "string" ? corpo.email.trim().toLowerCase() : "";
  if (!emailValido(email)) return json({ erro: "Confira o e-mail: parece que falta alguma coisa." }, 400);
  const alvos = [...new Set((Array.isArray(corpo.alvos) ? corpo.alvos : []).filter((a): a is string => typeof a === "string" && ALVO.test(a)))].slice(0, 4);
  if (!alvos.length) return json({ erro: "Marque o que você quer seguir." }, 400);
  const lugares = await Promise.all(alvos.map((a) => lugar(env, request.url, a)));
  if (lugares.some((l) => !l)) return json({ erro: "Não achamos esse lugar." }, 400);

  await prepararBanco(db);
  const quando = agora();
  let p = await db.prepare("SELECT id, token, pedido_em FROM pessoas WHERE email = ?").bind(email).first<{ id: number; token: string; pedido_em: string | null }>();
  if (!p) {
    p = await db.prepare("INSERT INTO pessoas (email, token, criado_em) VALUES (?, ?, ?) RETURNING id, token, pedido_em")
      .bind(email, novoToken(), quando).first<{ id: number; token: string; pedido_em: string | null }>();
    if (!p) return json({ erro: "Não deu certo agora. Tente de novo em alguns minutos." }, 500);
  }
  await db.batch(alvos.map((a) => db.prepare("INSERT OR IGNORE INTO seguindo (pessoa_id, alvo, criado_em) VALUES (?, ?, ?)").bind(p!.id, a, quando)));

  const pendentes = (await db.prepare("SELECT alvo FROM seguindo WHERE pessoa_id = ? AND confirmado = 0").bind(p.id).all<{ alvo: string }>()).results.map((r) => r.alvo);
  const recente = p.pedido_em && Date.now() - Date.parse(p.pedido_em) < INTERVALO_MS;
  if (pendentes.length && !recente) {
    const nomes: string[] = [];
    for (const a of pendentes) {
      const l = lugares.find((x) => x?.alvo === a) ?? (await lugar(env, request.url, a));
      if (l) nomes.push((l as ResumoCurto).titulo);
    }
    const link = new URL(`/api/confirmar?t=${encodeURIComponent(p.token)}`, request.url).toString();
    const m = emailConfirmacao(nomes, link);
    try {
      await enviar(env, { para: email, ...m });
    } catch (e) {
      console.error("[seguir] falha no envio da confirmação", e);
      return json({ erro: "Não conseguimos mandar o e-mail agora. Tente de novo em alguns minutos." }, 502);
    }
    await db.prepare("UPDATE pessoas SET pedido_em = ? WHERE id = ?").bind(quando, p.id).run();
  }
  return json({ ok: true });
}
