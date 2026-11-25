# /// script
# dependencies = ["certifi"]
# ///
"""Publica no Instagram @orcamentobrasileiro pela API.

As imagens não entram no Git: ficam só no bucket do espelho. Uma pasta de post tem, no Git,
`legenda.txt` e `midia.json` (os endereços públicos das imagens); as imagens em si ficam na
mesma pasta só na máquina de quem fez o post (o .gitignore as deixa de fora).

    uv run --no-project --script publicar.py posts/<nome> --enviar
        na máquina: sobe as imagens (JPEG, na ordem do nome; de 1 a 10) ou o .mp4 da pasta para
        o bucket, em social/<AAAA-MM-DD>-<nome>/, e grava midia.json. Precisa da chave do B2.
    uv run --no-project --script publicar.py posts/<nome>
        mostra o que seria publicado; não publica nada
    uv run --no-project --script publicar.py posts/<nome> --postar
        publica o que está em midia.json (1 imagem = post, 2 a 10 = carrossel, vídeo = Reel).
        Só precisa do token do Instagram; é o que o workflow "Instagram" roda.
    uv run --no-project --script publicar.py --teste
        confere o token e a cota do dia

O endereço público (dados.orcamentobrasileiro.com.br) fica 30 dias no cache da Cloudflare: para
trocar uma imagem já enviada, use uma pasta com nome novo.

Segredos (variáveis de ambiente; na máquina, em ~/.config/orcamento-br/*.env, chmod 600):
    INSTAGRAM_TOKEN                               token de usuário do sistema da Meta (EAA…)
    B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY     chave do bucket só para social/ (só para --enviar)
"""
import datetime, json, os, re, ssl, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path

API = "https://graph.facebook.com/v21.0"
CONTA = "17841464857738019"  # @orcamentobrasileiro; o token é endereçado pelo id, não por /me
BUCKET = "orcamento-brasileiro-dados"
PUBLICO = f"https://dados.orcamentobrasileiro.com.br/file/{BUCKET}"
IMAGENS = {".jpg", ".jpeg"}  # a API só aceita JPEG
try:
    import certifi
    SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL = ssl.create_default_context()


def segredo(nome):
    if os.environ.get(nome):
        return os.environ[nome].strip()
    for arquivo in (Path.home() / ".config" / "orcamento-br").glob("*.env"):
        for linha in arquivo.read_text().splitlines():
            if linha.startswith(nome + "="):
                return linha.split("=", 1)[1].strip()
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


def no_ar(url):
    # O Instagram busca a mídia como facebookexternalhit; um 404 lá vira um erro opaco.
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD",
                               headers={"User-Agent": "facebookexternalhit/1.1"}), timeout=30, context=SSL)
    except urllib.error.HTTPError as e:
        sys.exit(f"{url} respondeu {e.code}: rode --enviar de novo")


def arquivos_locais(pasta):
    if list(pasta.glob("*.png")):
        sys.exit("A API do Instagram só aceita JPEG: converta os .png")
    videos = sorted(pasta.glob("*.mp4"))
    imagens = sorted(p for p in pasta.iterdir() if p.suffix.lower() in IMAGENS)
    if videos and imagens or len(videos) > 1:
        sys.exit("Uma pasta tem ou um .mp4 (Reel) ou imagens, não os dois")
    if not videos and not 1 <= len(imagens) <= 10:
        sys.exit(f"{len(imagens)} imagens em {pasta}; o Instagram aceita de 1 a 10")
    return videos or imagens


def slug(texto):
    t = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "post"


def envia(pasta):
    """Sobe as mídias da pasta para o bucket e grava midia.json com os endereços públicos."""
    arquivos = arquivos_locais(pasta)
    destino = f"social/{datetime.date.today():%Y-%m-%d}-{slug(pasta.resolve().name)}"
    amb = {**os.environ, "B2_APPLICATION_KEY_ID": segredo("B2_APPLICATION_KEY_ID"),
           "B2_APPLICATION_KEY": segredo("B2_APPLICATION_KEY")}
    urls = []
    for a in arquivos:
        nome = f"{destino}/{a.name}"
        tipo = "video/mp4" if a.suffix.lower() == ".mp4" else "image/jpeg"
        subprocess.run(["uvx", "--from", "b2", "b2", "file", "upload", "--no-progress", "--quiet",
                        "--content-type", tipo, BUCKET, str(a), nome], env=amb, check=True,
                       stdout=subprocess.DEVNULL)
        url = f"{PUBLICO}/{urllib.parse.quote(nome)}"
        no_ar(url)
        urls.append(url)
    midia = {"tipo": "reel" if arquivos[0].suffix.lower() == ".mp4" else "imagens", "urls": urls}
    (pasta / "midia.json").write_text(json.dumps(midia, ensure_ascii=False, indent=2) + "\n")
    return midia


def le_post(pasta):
    if not pasta.is_dir():
        sys.exit(f"{pasta} não é uma pasta")
    legenda = (pasta / "legenda.txt").read_text().strip() if (pasta / "legenda.txt").exists() else ""
    if not legenda:
        sys.exit(f"Falta {pasta}/legenda.txt")
    if len(legenda) > 2200:
        sys.exit(f"Legenda com {len(legenda)} caracteres; o limite é 2200")
    midia = json.loads((pasta / "midia.json").read_text()) if (pasta / "midia.json").exists() else None
    if midia and not (midia.get("tipo") in ("imagens", "reel") and 1 <= len(midia.get("urls", [])) <= 10):
        sys.exit(f"{pasta}/midia.json inválido")
    return legenda, midia


def publica(midia, legenda, tk):
    urls = midia["urls"]
    if midia["tipo"] == "reel":
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
    legenda, midia = le_post(pasta)
    if "--enviar" in argv:
        midia = envia(pasta)
        print(f"Enviado: {pasta}/midia.json gravado. Faça o commit dele e da legenda.")
    if midia is None:
        arquivos = arquivos_locais(pasta)
        print("Ainda não enviado ao bucket (falta midia.json):\n  " + "\n  ".join(a.name for a in arquivos))
    else:
        tipo = "Reel" if midia["tipo"] == "reel" else "post" if len(midia["urls"]) == 1 else f"carrossel de {len(midia['urls'])}"
        print(f"{tipo}:\n  " + "\n  ".join(u.rsplit("/", 1)[1] for u in midia["urls"]))
    print(f"\nLegenda:\n{legenda}\n")
    if "--postar" not in argv:
        print("Nada foi publicado." + ("" if midia else " Rode --enviar antes de --postar."))
        sys.exit()
    if midia is None:
        sys.exit("Sem midia.json: rode --enviar na máquina onde estão as imagens")
    for u in midia["urls"]:
        no_ar(u)
    print("Publicado:", publica(midia, legenda, token()))
