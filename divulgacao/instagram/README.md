# Instagram @orcamentobrasileiro

- `posts/<nome>/`: um post por pasta, com as imagens (JPEG 1080×1350, na ordem do nome do
  arquivo; de 1 a 10) ou um `.mp4` para Reel, e `legenda.txt`.
- `publicar.py`: publica uma pasta pela API do Instagram. Sem `--postar`, só mostra.
- `gera_perfil.py`: refaz `perfil.jpg`, a foto do perfil (o símbolo do site em fundo papel).

Publicar pelo GitHub (o token e a chave do bucket são segredos do repositório):

    gh workflow run instagram.yml -f post=<nome>                 # só confere
    gh workflow run instagram.yml -f post=<nome> -f postar=true  # publica

Ou na máquina, com os segredos em `~/.config/orcamento-br/*.env`:

    uv run --no-project --script divulgacao/instagram/publicar.py divulgacao/instagram/posts/<nome> [--postar]
