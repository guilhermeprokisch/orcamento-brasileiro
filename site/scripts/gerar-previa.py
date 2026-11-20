"""Gera site/public/previa.png (1200 × 630), a imagem que aparece na prévia dos links no WhatsApp e nas redes.

    uv run --with pillow python site/scripts/gerar-previa.py . <pasta das fontes>

A pasta das fontes precisa de SourceSerif4.ttf e Inter.ttf, as fontes do site (licença aberta, do
repositório google/fonts: ofl/sourceserif4 e ofl/inter). O mapa usa os dados gerados pelo pipeline
(site/public/data/mapa/estados.geojson e site/public/data/cidades/estados.json).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ, FONTES = Path(sys.argv[1]), Path(sys.argv[2])
S = 2  # desenha em dobro e reduz, para as bordas ficarem lisas
W, H = 1200 * S, 630 * S
PAPEL, TINTA, TEXTO2, VERDE = "#f7f4ec", "#191919", "#3d3a33", "#0e6b3b"
VERDES = ["#dfe9d6", "#b9d4b0", "#86b98a", "#4f9a66", "#0e6b3b"]

img = Image.new("RGB", (W, H), PAPEL)
d = ImageDraw.Draw(img)


def fonte(arquivo: str, tamanho: int, peso: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTES / arquivo), tamanho * S)
    eixos = f.get_variation_axes()
    f.set_variation_by_axes([peso if "eight" in str(a.get("name", "")).lower() or a.get("name") == b"Weight" else a["default"] for a in eixos])
    return f


serif = lambda t, p=700: fonte("SourceSerif4.ttf", t, p)
sans = lambda t, p=400: fonte("Inter.ttf", t, p)

# Marca (a mesma do site: barras verdes, losango amarelo e círculo azul), 124 × 86 na escala k.
def marca(x: float, y: float, k: float) -> None:
    for i, (topo, alt) in enumerate([(5.16, 80.84), (30.96, 55.04), (29.24, 56.76), (24.08, 61.92), (17.2, 68.8), (11.18, 74.82), (5.16, 80.84), (0, 86)]):
        bx = x + 16 * i * k
        d.rounded_rectangle([bx, y + topo * k, bx + 12 * k, y + (topo + alt) * k], radius=2.5 * k, fill="#009C3B")
    d.polygon([(x + 10 * k, y + 43 * k), (x + 62 * k, y + 9 * k), (x + 114 * k, y + 43 * k), (x + 62 * k, y + 77 * k)], fill="#FFDF00")
    cx, cy, r = x + 62 * k, y + 43 * k, 20 * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#002776")
    # a fatia branca vai do topo (−90°) até o ponto (78,18; 54,76)
    fim = math.degrees(math.atan2(54.76 - 43, 78.18 - 62))
    d.pieslice([cx - r, cy - r, cx + r, cy + r], start=-90, end=fim, fill="#FFFFFF")


# O Brasil, cada estado num tom de verde pelo gasto do governo estadual por habitante (dados do site).
def mapa(x0: float, y0: float, largura: float) -> None:
    geo = json.loads((RAIZ / "site/public/data/mapa/estados.geojson").read_text(encoding="utf-8"))
    estados = {str(e["ibge"]): e for e in json.loads((RAIZ / "site/public/data/cidades/estados.json").read_text(encoding="utf-8"))["cidades"]}
    por_hab = {k: e["total"][0] / e["pop"] for k, e in estados.items() if e.get("total") and e.get("pop")}
    ordem = sorted(por_hab.values())
    cor = lambda v: VERDES[min(4, int(5 * ordem.index(v) / len(ordem)))]
    lon0, lat0, lon1, lat1 = -74.2, 5.6, -34.6, -34.0
    k = math.cos(math.radians(-15))
    esc = largura / ((lon1 - lon0) * k)
    pr = lambda p: (x0 + (p[0] - lon0) * k * esc, y0 + (lat0 - p[1]) * esc)
    for f in geo["features"]:
        g = f["geometry"]
        for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            pts = [pr(p) for p in poly[0]]
            v = por_hab.get(str(f["properties"]["id"]))
            d.polygon(pts, fill=cor(v) if v is not None else "#e2dccd", outline=PAPEL, width=2 * S)


def texto(x: float, y: float, s: str, f, cor=TINTA, largura: float | None = None, entre: float = 1.15) -> float:
    """Escreve quebrando linhas em `largura`; devolve o y depois do texto."""
    linhas, atual = [], ""
    for palavra in s.split():
        teste = (atual + " " + palavra).strip()
        if largura and d.textlength(teste, font=f) > largura * S and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    linhas.append(atual)
    alt = f.size * entre
    for i, l in enumerate(linhas):
        d.text((x * S, y * S + i * alt), l, font=f, fill=cor)
    return y + len(linhas) * alt / S


M = 72
d.rectangle([0, 0, W, 10 * S], fill=TINTA)
marca(M * S, 56 * S, 0.62 * S)
d.text(((M + 92) * S, 58 * S), "Orçamento Brasileiro", font=serif(34, 700), fill=TINTA)
y = texto(M, 168, "De onde vem e para onde vai o dinheiro público", serif(64, 700), largura=640, entre=1.08)
texto(M, y + 26, "Da sua cidade, do seu estado e do país: impostos, repasses, gastos, dívidas e o que eles produzem.", sans(28, 400), cor=TEXTO2, largura=620, entre=1.4)
mapa(800 * S, 92 * S, 340 * S)
d.rectangle([M * S, 548 * S, (1200 - M) * S, 551 * S], fill=TINTA)
d.text((M * S, 566 * S), "orcamentobrasileiro.com.br", font=sans(26, 600), fill=VERDE)
d.text(((1200 - M) * S, 566 * S), "Dados oficiais, de graça", font=sans(24, 400), fill=TEXTO2, anchor="ra")

saida = RAIZ / "site/public/previa.png"
img.resize((1200, 630), Image.LANCZOS).save(saida, optimize=True)
print(saida, saida.stat().st_size // 1024, "KB")
