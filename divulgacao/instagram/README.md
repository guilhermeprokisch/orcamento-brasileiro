# Instagram @orcamentobrasileiro

As imagens dos posts não ficam no Git, só no bucket do espelho (dados.orcamentobrasileiro.com.br).
Cada pasta `posts/<nome>/` guarda no Git a `legenda.txt` e o `midia.json` com os endereços das
imagens; os JPEG (1080×1350, de 1 a 10, na ordem do nome) ou o `.mp4` do Reel ficam na mesma pasta
só na máquina de quem fez o post.

1. Na máquina, com as imagens na pasta e a chave do B2 em `~/.config/orcamento-br/b2.env`:

       uv run --no-project --script divulgacao/instagram/publicar.py divulgacao/instagram/posts/<nome> --enviar

   Sobe as imagens para `social/<data>-<nome>/` e grava `midia.json`.
2. Commit da `legenda.txt` e do `midia.json`, pull request, merge.
3. Publicar pelo GitHub (o token do Instagram é segredo do repositório):

       gh workflow run instagram.yml -f post=<nome>                 # só confere
       gh workflow run instagram.yml -f post=<nome> -f postar=true  # publica

Para trocar uma imagem já enviada, use uma pasta com nome novo: a Cloudflare guarda cada endereço
por 30 dias.

`gera_perfil.py` refaz `perfil.jpg`, a foto do perfil (o símbolo do site em fundo papel).
