# /// script
# dependencies = ["certifi"]
# ///
"""Publica no Instagram @orcamentobrasileiro pela API.

    uv run --no-project --script publicar.py posts/<nome>
        mostra o que seria publicado (imagens e legenda.txt da pasta); não publica nada
    uv run --no-project --script publicar.py posts/<nome> --postar
        sobe as imagens e publica (1 imagem = post, 2 a 10 = carrossel, um .mp4 = Reel)
    uv run --no-project --script publicar.py --teste
        só confere o token e a cota do dia

Uma pasta de post tem as imagens (.png/.jpg, na ordem do nome) ou um .mp4, e legenda.txt.

A API só busca mídia por URL pública: os arquivos sobem para o bucket do espelho, em
social/<AAAA-MM-DD>-<nome>/, e o Instagram os lê em dados.orcamentobrasileiro.com.br. A Cloudflare
guarda esse endereço por 30 dias, então cada publicação usa uma pasta nova e nada é sobrescrito.

Segredos (variáveis de ambiente; fora do GitHub, em ~/.config/orcamento-br/*.env):
    INSTAGRAM_TOKEN                               token de usuário do sistema da Meta (EAA…)
    B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY     chave do bucket (só para --postar)
Pelo GitHub: o workflow "Instagram" (.github/workflows/instagram.yml).
"""
import datetime, json, os, re, ssl, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "https://graph.facebook.com/v21.0"
CONTA = "17841464857738019"  # @orcamentobrasileiro; o token é endereçado pelo id, não por /me
BUCKET = "orcamento-brasileiro-dados"
PUBLICO = f"https://dados.orcamentobrasileiro.com.br/file/{BUCKET}"
IMAGENS = {".jpg", ".jpeg", ".png"}
try:
    import certifi
    SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL = ssl.create_default_context()


def segredo(nome):
    if os.environ.get(nome):
        return os.environ[nome]
    for arquivo in (Path.home() / ".config" / "orcamento-br").glob("*.env"):
        for linha in arquivo.read_text().splitlines():
            if linha.startswith(nome + "="):
                return linha.split("=", 1)[1]
    sys.exit(f"Falta o segredo {nome}")


def token():
    t = segredo("INSTAGRAM_TOKEN")
    if not t.startswith("EAA"):
        sys.exit("O INSTAGRAM_TOKEN não parece um token da Meta (EAA…)")
    return t


def chama(metodo, caminho, tk, **params):
    dados = urllib.parse.urlencode(params).encode()
    url = f"{API}/{caminho}" + ("" if metodo == "POST" else "?" + dados.decode())
    pedido = urllib.request.Request(url, data=dados if metodo == "POST" else None, method=metodo,
                                    headers={"Authorization": f"Bearer {tk}"})
    try:
        with urllib.request.urlopen(pedido, timeout=60, context=SSL) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        corpo = re.sub(r"EAA[A-Za-z0-9_-]+", "<token>", e.read().decode())
        raise RuntimeError(f"Instagram recusou {caminho.split('/')[-1]}: {corpo[:500]}")


def espera(cid, tk, vezes=40):
    # O container é processado de forma assíncrona; publicar antes de FINISHED falha.
    for _ in range(vezes):
        estado = chama("GET", cid, tk, fields="status_code").get("status_code")
        if estado == "FINISHED":
            return
        if estado == "ERROR":
            raise RuntimeError(f"o Instagram não conseguiu processar {cid}")
        time.sleep(3)
    raise RuntimeError(f"o container {cid} não ficou pronto")


def sobe(arquivos, pasta):
    """Envia ao bucket e devolve as URLs públicas, já conferidas."""
    amb = {**os.environ, "B2_APPLICATION_KEY_ID": segredo("B2_APPLICATION_KEY_ID"),
           "B2_APPLICATION_KEY": segredo("B2_APPLICATION_KEY")}
    urls = []
    for a in arquivos:
        nome = f"social/{pasta}/{a.name}"
        tipo = {".mp4": "video/mp4", ".png": "image/png"}.get(a.suffix.lower(), "image/jpeg")
        subprocess.run(["uvx", "--from", "b2", "b2", "file", "upload", "--no-progress", "--quiet",
                        "--content-type", tipo, BUCKET, str(a), nome], env=amb, check=True,
                       stdout=subprocess.DEVNULL)
        url = f"{PUBLICO}/{urllib.parse.quote(nome)}"
        # O Instagram busca a mídia como facebookexternalhit; um 404 lá vira um erro opaco.
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD",
                               headers={"User-Agent": "facebookexternalhit/1.1"}), timeout=30, context=SSL)
        urls.append(url)
    return urls


def publica(urls, legenda, tk, reel=False):
    if reel:
        cid = chama("POST", f"{CONTA}/media", tk, media_type="REELS", video_url=urls[0],
                    caption=legenda, share_to_feed="true")["id"]
        espera(cid, tk, vezes=120)  # vídeo leva minutos
    elif len(urls) == 1:
        cid = chama("POST", f"{CONTA}/media", tk, image_url=urls[0], caption=legenda)["id"]
        espera(cid, tk)
    else:
        filhos = []
        for u in urls:
            f = chama("POST", f"{CONTA}/media", tk, image_url=u, is_carousel_item="true")["id"]
            espera(f, tk)
            filhos.append(f)
        cid = chama("POST", f"{CONTA}/media", tk, media_type="CAROUSEL", children=",".join(filhos),
                    caption=legenda)["id"]
        espera(cid, tk)
    mid = chama("POST", f"{CONTA}/media_publish", tk, creation_id=cid)["id"]
    return chama("GET", mid, tk, fields="permalink").get("permalink", mid)


def le_post(pasta):
    if not pasta.is_dir():
        sys.exit(f"{pasta} não é uma pasta")
    legenda = (pasta / "legenda.txt").read_text().strip() if (pasta / "legenda.txt").exists() else ""
    if not legenda:
        sys.exit(f"Falta {pasta}/legenda.txt")
    if len(legenda) > 2200:
        sys.exit(f"Legenda com {len(legenda)} caracteres; o limite é 2200")
    videos = sorted(pasta.glob("*.mp4"))
    imagens = sorted(p for p in pasta.iterdir() if p.suffix.lower() in IMAGENS)
    if videos and imagens or len(videos) > 1:
        sys.exit("Uma pasta tem ou um .mp4 (Reel) ou imagens, não os dois")
    if not videos and not 1 <= len(imagens) <= 10:
        sys.exit(f"{len(imagens)} imagens; o Instagram aceita de 1 a 10")
    return (videos or imagens), legenda, bool(videos)


def slug(texto):
    t = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "post"


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--teste" in argv:
        tk = token()
        conta = chama("GET", CONTA, tk, fields="username,media_count")
        cota = chama("GET", f"{CONTA}/content_publishing_limit", tk, fields="quota_usage,config")["data"][0]
        print(f"@{conta['username']}: {conta['media_count']} posts; hoje {cota['quota_usage']} de "
              f"{cota['config']['quota_total']} publicações")
        sys.exit()
    pastas = [a for a in argv if not a.startswith("--")]
    if len(pastas) != 1:
        sys.exit(__doc__)
    pasta = Path(pastas[0])
    arquivos, legenda, reel = le_post(pasta)
    tipo = "Reel" if reel else "post" if len(arquivos) == 1 else f"carrossel de {len(arquivos)}"
    print(f"{tipo}:\n  " + "\n  ".join(a.name for a in arquivos) + f"\n\nLegenda:\n{legenda}\n")
    if "--postar" not in argv:
        print("Nada foi publicado. Confira e rode de novo com --postar.")
        sys.exit()
    tk = token()
    urls = sobe(arquivos, f"{datetime.date.today():%Y-%m-%d}-{slug(pasta.resolve().name)}")
    print("Publicado:", publica(urls, legenda, tk, reel))
