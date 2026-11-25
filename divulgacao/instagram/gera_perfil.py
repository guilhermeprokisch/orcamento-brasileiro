# /// script
# dependencies = ["pillow"]
# ///
"""Foto de perfil do @orcamentobrasileiro: o símbolo do site em fundo papel, 1080x1080."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

L, K = 1080, 4                    # lado final e superamostragem
W = L * K
ESC = 5.4 * K                     # escala do símbolo (124x86 no SVG)
ox, oy = (W - 124 * ESC) / 2, (W - 86 * ESC) / 2
p = lambda x, y: (ox + x * ESC, oy + y * ESC)

img = Image.new("RGB", (W, W), "#f7f4ec")
d = ImageDraw.Draw(img)
barras = [(0, 5.16), (16, 30.96), (32, 29.24), (48, 24.08), (64, 17.2), (80, 11.18), (96, 5.16), (112, 0)]
for x, y in barras:
    d.rounded_rectangle([p(x, y), p(x + 12, 86)], radius=2.5 * ESC, fill="#009C3B")
d.polygon([p(10, 43), p(62, 9), p(114, 43), p(62, 77)], fill="#FFDF00")
d.ellipse([p(42, 23), p(82, 63)], fill="#002776")
# fatia branca: de -90° (topo) até o ponto (78.18, 54.76), sentido horário
fim = math.degrees(math.atan2(54.76 - 43, 78.18 - 62))
d.pieslice([p(42, 23), p(82, 63)], start=-90, end=fim, fill="#FFFFFF")

saida = Path(__file__).with_name("perfil.jpg")
img.resize((L, L), Image.LANCZOS).save(saida, quality=95)
print(saida)
