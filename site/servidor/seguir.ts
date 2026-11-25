/**
 * Seguir uma cidade ou um estado por e-mail: o que as funções do Cloudflare Pages (functions/api/*)
 * têm em comum. Os inscritos ficam num banco D1 ligado ao projeto com o nome DB; o e-mail sai pelo
 * servidor do Homerow (mail.inout.email), como boletim@orcamentobrasileiro.com.br.
 *
 * Tabelas (criadas aqui na primeira chamada; não há migração a rodar):
 *   pessoas  — um e-mail, o código secreto dos links (token), quando confirmou e quando pediu por último
 *   seguindo — cada lugar que a pessoa segue ("mun-4205407", "uf-SC"), se já confirmou e, em `enviado`,
 *              a chave de cada seção mandada no último e-mail (ver src/lib/resumo.ts)
 *
 * Variáveis do projeto no Pages: SMTP_SENHA (secreta), e opcionalmente SMTP_HOST, SMTP_PORTA,
 * SMTP_USUARIO e BOLETIM_DE. Sem SMTP_SENHA o e-mail só vai para o log (para testar no computador).
 */

// Os tipos mínimos do D1 e do Pages que usamos, para não depender de @cloudflare/workers-types.
export interface D1Resultado<T> { results: T[] }
export interface D1Comando {
  bind(...valores: unknown[]): D1Comando;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<D1Resultado<T>>;
  run(): Promise<unknown>;
}
export interface D1 {
  prepare(sql: string): D1Comando;
  batch(comandos: D1Comando[]): Promise<unknown[]>;
}
export interface Ambiente {
  DB?: D1;
  ASSETS: { fetch(req: Request | string): Promise<Response> };
  SMTP_HOST?: string;
  SMTP_PORTA?: string;
  SMTP_USUARIO?: string;
  SMTP_SENHA?: string;
  BOLETIM_DE?: string;
}
export interface Contexto { request: Request; env: Ambiente }

export const SITE = "https://orcamentobrasileiro.com.br";
const DE_PADRAO = "boletim@orcamentobrasileiro.com.br";

let tabelasProntas = false;
export async function prepararBanco(db: D1): Promise<void> {
  if (tabelasProntas) return;
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS pessoas (
      id INTEGER PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      token TEXT NOT NULL UNIQUE,
      criado_em TEXT NOT NULL,
      confirmado_em TEXT,
      pedido_em TEXT
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS seguindo (
      pessoa_id INTEGER NOT NULL REFERENCES pessoas(id) ON DELETE CASCADE,
      alvo TEXT NOT NULL,
      criado_em TEXT NOT NULL,
      confirmado INTEGER NOT NULL DEFAULT 0,
      enviado TEXT,
      enviado_em TEXT,
      PRIMARY KEY (pessoa_id, alvo)
    )`),
  ]);
  tabelasProntas = true;
}

export const agora = () => new Date().toISOString();

export function novoToken(): string {
  const b = crypto.getRandomValues(new Uint8Array(24));
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Um e-mail que dá para usar: sem espaços, com @ e domínio com ponto, até 254 caracteres. */
export function emailValido(s: unknown): s is string {
  return typeof s === "string" && s.length <= 254 && /^[^\s@<>"',;]+@[^\s@<>"',;]+\.[a-z]{2,}$/i.test(s);
}

export const ALVO = /^(mun-\d{7}|uf-[A-Z]{2})$/;

export interface ResumoCurto { alvo: string; titulo: string; uf: string; esfera: "mun" | "uf"; url: string }

/** O lugar, lido do resumo que o site gera (seguir/resumo/<alvo>.json); null se não existe. */
export async function lugar(env: Ambiente, base: string, alvo: string): Promise<ResumoCurto | null> {
  if (!ALVO.test(alvo)) return null;
  const r = await env.ASSETS.fetch(new URL(`/seguir/resumo/${alvo}.json`, base).toString());
  if (!r.ok) return null;
  try {
    const j = (await r.json()) as ResumoCurto;
    return j && j.alvo === alvo ? j : null;
  } catch {
    return null;
  }
}

export const json = (dados: unknown, status = 200) =>
  new Response(JSON.stringify(dados), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });

export const escapar = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** "Florianópolis", "Florianópolis e Santa Catarina", "A, B e C" */
export const juntar = (xs: string[]) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} e ${xs.at(-1)}`);

export interface Mensagem { para: string; assunto: string; texto: string; html: string; cabecalhos?: Record<string, string> }

export async function enviar(env: Ambiente, m: Mensagem): Promise<void> {
  const de = env.BOLETIM_DE || DE_PADRAO;
  if (!env.SMTP_SENHA) {
    console.log(`[seguir] SMTP_SENHA ausente; e-mail não enviado.\nPara: ${m.para}\nAssunto: ${m.assunto}\n\n${m.texto}`);
    return;
  }
  // Import dinâmico: worker-mailer usa cloudflare:sockets, que só existe no Workers.
  const { WorkerMailer } = await import("worker-mailer");
  const mailer = await WorkerMailer.connect({
    host: env.SMTP_HOST || "mail.inout.email",
    port: Number(env.SMTP_PORTA || 465),
    secure: true,
    authType: "plain",
    credentials: { username: env.SMTP_USUARIO || de, password: env.SMTP_SENHA },
  });
  try {
    await mailer.send({
      from: { name: "Orçamento Brasileiro", email: de },
      to: { email: m.para },
      subject: m.assunto,
      text: m.texto,
      html: m.html,
      headers: m.cabecalhos,
    });
  } finally {
    await mailer.close().catch(() => {});
  }
}

/** O e-mail que pede para confirmar, no visual do mock aprovado (Claude Design, 26/11/2026). */
export function emailConfirmacao(nomes: string[], link: string): { assunto: string; texto: string; html: string } {
  const lugares = juntar(nomes);
  const assunto = `Confirme: seguir ${lugares}`;
  const texto = [
    `Falta um clique para seguir ${lugares}.`,
    "",
    `Alguém (esperamos que você) pediu para receber por este e-mail as novidades das contas de ${lugares}. Para confirmar, abra:`,
    link,
    "",
    "Depois disso, mandamos no máximo um e-mail por mês, e só quando sair dado novo.",
    "",
    "Não foi você? É só ignorar este e-mail. Sem a confirmação, apagamos o endereço em 7 dias.",
    "",
    "Orçamento Brasileiro · orcamentobrasileiro.com.br",
  ].join("\n");
  const l = escapar(lugares);
  const html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapar(assunto)}</title></head>
<body style="margin:0;padding:0;background:#e9e4d8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9e4d8;"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#f7f4ec;border-top:4px solid #0e6b3b;">
<tr><td style="padding:32px 32px 28px;font-family:Inter,Arial,sans-serif;color:#191919;">
<p style="margin:0 0 20px;font-family:Georgia,serif;font-size:20px;font-weight:700;">Orçamento Brasileiro</p>
<h1 style="margin:0 0 20px;font-family:Georgia,serif;font-size:28px;line-height:1.2;">Falta um clique para seguir ${l}</h1>
<p style="margin:0 0 24px;font-size:16px;line-height:1.55;color:#3d3a33;">Alguém (esperamos que você) pediu para receber por este e-mail as novidades das contas de <strong style="color:#191919;">${l}</strong>. Confirme no botão abaixo.</p>
<p style="margin:0 0 24px;"><a href="${escapar(link)}" style="display:inline-block;padding:15px 26px;background:#0e6b3b;color:#ffffff;text-decoration:none;font-weight:600;font-size:16px;">Confirmar e seguir</a></p>
<p style="margin:0 0 20px;font-size:15px;line-height:1.55;color:#3d3a33;">Depois disso, mandamos no máximo um e-mail por mês, e só quando sair dado novo: contas, contratos, emendas, a nota do Tesouro.</p>
<p style="margin:0;padding-top:16px;border-top:1px solid #c9c2b2;font-size:13px;line-height:1.5;color:#5c574c;">Não foi você? É só ignorar este e-mail. Sem a confirmação, apagamos o endereço em 7 dias.</p>
</td></tr></table>
<p style="margin:16px 0 0;font-family:Inter,Arial,sans-serif;font-size:12px;color:#5c574c;">Orçamento Brasileiro · dados abertos das contas públicas · orcamentobrasileiro.com.br</p>
</td></tr></table></body></html>`;
  return { assunto, texto, html };
}
