# Pedidos pela Lei de Acesso à Informação

Os pedidos que o projeto faz aos órgãos que não publicam o que a Lei 12.527/2011 manda publicar. Cada arquivo `.md`
desta pasta é um tema (o porquê, o texto e o acompanhamento); `textos/` tem o texto pronto de cada pedido, um arquivo
por órgão; `registro.csv` é a lista do que já foi enviado pelo script, com o prazo de cada um.

## Enviar pelos formulários dos órgãos

Muitos órgãos só aceitam o pedido pelo formulário do site. O comando `lai` abre o navegador, preenche o formulário com
os seus dados e o texto do pedido, e para nas partes que são suas: o login, o CAPTCHA e o OK antes de enviar.

Uma vez só:

```bash
cd pipeline
uv run --extra lai playwright install chromium
uv run --extra lai lai configurar
```

O segundo comando cria `~/.config/orcamento-br/lai.toml`. Preencha ali o nome, o CPF, o documento, o endereço e o
telefone. O arquivo fica só neste computador (permissão 600) e nunca vai para o git.

Para cada pedido:

```bash
uv run --extra lai lai enviar ALMG ../docs/pedidos-lai/textos/custo-dos-mandatos/ALMG.txt
```

1. Abre o formulário e preenche.
2. Se o site tiver CAPTCHA ou login, para e espera você fazer na janela (o script não resolve CAPTCHA).
3. Pergunta no terminal se pode enviar. Só envia com "s".
4. Procura o protocolo na página (ou pergunta) e anota em `registro.csv`, com o prazo legal: 20 dias, mais 10 se o
   órgão prorrogar (art. 11). Passado o prazo sem resposta, cabe recurso em 10 dias (art. 15).

A captura de tela de cada envio, que mostra os seus dados, fica em `~/.config/orcamento-br/lai-comprovantes/`, fora do
repositório.

Outros comandos:

```bash
uv run --extra lai lai orgaos                  # os formulários que o script preenche
uv run --extra lai lai prazos                  # o que foi enviado e quanto falta para cada prazo
uv run --extra lai lai enviar TCE-SE ARQ --ensaio   # preenche e para, sem enviar
uv run --extra lai lai inspecionar <URL>       # lista os campos de um formulário novo
```

O arquivo do pedido: a primeira linha é `Assunto: ...`, depois uma linha em branco e o texto. `{nome}` e `{email}` no
texto viram os seus dados (para a assinatura).

## Os formulários que o script conhece

| Órgão | Observação |
|---|---|
| TCE-SE | O protocolo chega por e-mail. |
| ALMG | O reCAPTCHA invisível do site recusa o navegador do script. Vai pela extensão do Chrome (abaixo): ela preenche, você clica em Enviar, e o protocolo volta para o terminal. Sem a extensão, `--colar` abre o formulário e copia o texto. |
| ALERJ | CAPTCHA. |
| ALERR | O formulário recarrega partes ao escolher o assunto; o script espera e confere. |
| TCE-RS | Pede a cópia do documento de identidade (`documento` no lai.toml) e tem CAPTCHA. O texto do pedido é publicado no site do tribunal, por isso vai sem a assinatura. |
| TCE-PR | Três etapas: o script preenche a identificação e o que reconhecer da descrição; você confere e conclui. |

Testados em 23/11/2026 com dados fictícios, sem enviar (`--ensaio`).

## A extensão do Chrome (para os sites com reCAPTCHA invisível)

Alguns sites dão uma nota de "robô" a cada navegador e recusam o navegador controlado pelo script. Para esses, a
extensão `pipeline/lai-extensao/` preenche o formulário no seu Chrome de verdade. Ela não clica em Enviar: o clique fica
com você.

Instalar uma vez: abra `chrome://extensions`, ligue o "Modo do desenvolvedor", clique em "Carregar sem compactação" e
escolha a pasta `pipeline/lai-extensao`.

Como funciona: o `lai enviar` abre uma ponte só no seu computador (127.0.0.1:8765) e abre o formulário no Chrome com
uma senha de uso único no endereço. A extensão vê a senha, pega os passos pela ponte, preenche e tira a senha do
endereço. Depois que você envia, ela lê o protocolo na página de confirmação e devolve ao terminal. Sem a senha, a
extensão não faz nada, e ela só roda nas páginas dos formulários que conhece (lista em `manifest.json`).

## Sem perguntar

`--direto` envia sem a pergunta de confirmação, nos formulários sem CAPTCHA e sem etapas desconhecidas (hoje, TCE-SE e
ALERR). Nos outros, o comando recusa a opção.

## Escrever um formulário novo

1. `uv run --extra lai lai inspecionar <URL>` lista os campos da página.
2. Em `pipeline/src/orcamento_pipeline/lai/formularios.py`, escreva a função que preenche (os ajudantes `escrever` e
   `escolher` já tratam campo com máscara, limite de caracteres e `<select>` que carrega depois) e acrescente o
   `Formulario` à lista, com o seletor do botão de enviar e os dados que ele exige.
3. Teste com `--ensaio --ficticia --sem-janela` e olhe a captura.

Os próximos: os que pedem login (TCM-GO, TCE-AM, ALRS, ALEAL, ALAP; o login fica com você, e o perfil do navegador
guarda a sessão), o Fala.BR/Informa.BR, que atende vários órgãos de uma vez, e os sistemas de e-SIC dos fornecedores
de portal municipal, que cobrem centenas de prefeituras e Câmaras cada um.
