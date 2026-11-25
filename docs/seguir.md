# Seguir uma cidade ou um estado por e-mail

Quem visita a página de uma cidade ou de um estado pode deixar o e-mail e receber, no máximo uma vez por mês, o que saiu de novo nas contas daquele lugar. O e-mail sai pelo servidor do Homerow (`mail.inout.email`) como `boletim@orcamentobrasileiro.com.br`, sem serviço de e-mail pago.

Mock aprovado em 26/11/2026: [Seguir cidade — mock](https://claude.ai/artifact/XeNu2DYPLS9enfPH678Tv3) (Claude Design).

## Como funciona

| Parte | Onde | O que faz |
|---|---|---|
| Botão e formulário | `site/src/components/Seguir.astro` | Na cabeça das páginas de cidade e de estado. Só aparece com `PUBLIC_SEGUIR=1` no build. |
| Resumo de cada lugar | `site/src/lib/resumo.ts` → `/seguir/resumo/<alvo>.json` | Gerado com o site. Cada seção (ano em andamento, contas, emendas, contratos, nota do Tesouro) tem uma `chave` que muda quando sai dado novo. |
| Inscrição | `site/functions/api/seguir.ts` | Guarda o pedido no D1 e manda o e-mail de confirmação. |
| Confirmação | `site/functions/api/confirmar.ts` → `/seguir/confirmado` | O link do e-mail de confirmação. |
| Saída | `site/functions/api/sair.ts` → `/seguir/sair` | Pede um clique e apaga. Atende também o "cancelar inscrição" com um clique do Gmail (RFC 8058). |
| Envio mensal | `.github/scripts/boletim.py`, `.github/workflows/boletim.yml` | Dia 27 de cada mês. Compara a chave de cada seção com a do último e-mail; só manda para quem tem novidade. |

Os alvos se escrevem `mun-<IBGE de 7 dígitos>` e `uf-<UF>`. O Distrito Federal é sempre `uf-DF`.

O banco tem duas tabelas, `pessoas` e `seguindo`, criadas pela própria função na primeira inscrição (`site/servidor/seguir.ts`). Pedidos sem confirmação são apagados depois de 7 dias, no envio mensal.

## Para ligar (uma vez)

1. **Caixa de e-mail.** No repositório do Homerow, acrescentar `boletim@orcamentobrasileiro.com.br` em `extraMailboxes` (`modules/settings.nix`), com uma senha só dela, e publicar o servidor. O domínio já tem MX, SPF, DKIM e DMARC.
2. **Banco D1.**
   ```bash
   npx wrangler login
   npx wrangler d1 create orcamento-seguir
   ```
   No painel da Cloudflare, em Workers & Pages → `orcamento-brasileiro` → Settings → Bindings, ligar o banco com o nome `DB`, em Production e em Preview.
3. **Senha do e-mail no Pages.** No mesmo projeto, em Settings → Variables and Secrets, criar `SMTP_SENHA` (secreta) com a senha da caixa `boletim@`. As outras variáveis têm padrão (`mail.inout.email`, porta 465, usuário = remetente).
4. **Segredos do GitHub** para o envio mensal:
   ```bash
   gh secret set D1_SEGUIR_ID
   gh secret set CF_D1_TOKEN
   gh secret set BOLETIM_SMTP_SENHA
   ```
   `CF_D1_TOKEN` é um token da Cloudflare com permissão "D1 Edit" na conta. `CLOUDFLARE_ACCOUNT_ID` já existe.
5. **Testar o e-mail** antes de ligar o botão: rodar o workflow Boletim à mão com `teste_para` = seu endereço. Ele manda um exemplo sem tocar no banco.
6. **Ligar o botão:**
   ```bash
   gh variable set SEGUIR_LIGADO --body 1
   ```
   A próxima publicação do site já mostra o botão, e o envio do dia 27 passa a rodar sozinho.

## Cuidados

- O boletim sai pelo mesmo IP do e-mail pessoal. Se muita gente marcar como spam, o e-mail do dia a dia também sofre. Por isso: confirmação obrigatória, cancelar com um clique, no máximo 400 e-mails por rodada e 1,5 s entre um e outro.
- Para olhar o que sairia sem mandar nada: workflow Boletim com `modo = ensaio`. Os e-mails ficam como artefato da execução por 7 dias.
- Testar no computador: `PUBLIC_SEGUIR=1 npm run build` e depois `npx wrangler pages dev dist --d1 DB` dentro de `site/`. Sem `SMTP_SENHA`, o e-mail de confirmação só aparece no log.
