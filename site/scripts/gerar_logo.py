"""Gera a marca do Orçamento Brasileiro: a bandeira desenhada como gráfico.

Barras verdes verticais: a primeira alta e as outras crescentes (um gráfico de
colunas, sem fechar o retângulo da bandeira); por cima, o losango amarelo sólido e, no centro, um gráfico de pizza azul
com uma fatia branca.
Uso: python3 scripts/gerar_logo.py  (escreve em public/ e src/assets/)
"""
import math
from pathlib import Path

VERDE, AMARELO, AZUL, BRANCO = "#009C3B", "#FFDF00", "#002776", "#FFFFFF"

BARRAS, LARG_BARRA, VAO = 8, 12, 4          # barras verdes verticais
L = BARRAS * LARG_BARRA + (BARRAS - 1) * VAO  # largura total = 124
A = 86                                       # altura máxima (proporção ~10:7)
ALTURAS = [0.94, 0.56, 0.64, 0.72, 0.8, 0.87, 0.94, 1.0]  # fração de A, da esquerda à direita
RAIO_BARRA = 2.5
CX, CY = L / 2, A / 2
MARGEM_X, MARGEM_Y = 10, 9                   # distância do losango às bordas
R = 20                                       # raio da pizza
FATIA = 0.35                                 # fração da fatia branca


def barras() -> list[str]:
    return [
        f'<rect x="{i * (LARG_BARRA + VAO)}" y="{A - h * A:g}" width="{LARG_BARRA}" height="{h * A:g}" '
        f'rx="{RAIO_BARRA}" fill="{VERDE}"/>'
        for i, h in enumerate(ALTURAS)
    ]


def losango() -> str:
    pontos = f"{MARGEM_X},{CY:g} {CX:g},{MARGEM_Y} {L - MARGEM_X},{CY:g} {CX:g},{A - MARGEM_Y}"
    return f'<polygon points="{pontos}" fill="{AMARELO}"/>'


def pizza() -> list[str]:
    # Fatia branca a partir do topo, no sentido horário.
    ang = 2 * math.pi * FATIA
    x1, y1 = CX, CY - R
    x2, y2 = CX + R * math.sin(ang), CY - R * math.cos(ang)
    grande = 1 if FATIA > 0.5 else 0
    return [
        f'<circle cx="{CX:g}" cy="{CY:g}" r="{R}" fill="{AZUL}"/>',
        f'<path d="M{CX:g},{CY:g} L{x1:g},{y1:g} A{R},{R} 0 {grande} 1 {x2:.2f},{y2:.2f} Z" fill="{BRANCO}"/>',
    ]


def marca(_id: str = "") -> str:
    return "\n".join([*barras(), losango(), *pizza()])


def svg(conteudo: str, viewbox: str, titulo: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" aria-label="{titulo}">\n'
            f"<title>{titulo}</title>\n{conteudo}\n</svg>\n")


raiz = Path(__file__).resolve().parents[1]
(raiz / "src" / "assets").mkdir(parents=True, exist_ok=True)

# Só a marca (cabeçalho do site).
(raiz / "src" / "assets" / "marca.svg").write_text(
    svg(marca("m"), f"0 0 {L} {A}", "Orçamento Brasileiro"), encoding="utf-8")

# Favicon: marca centralizada num quadrado.
lado = L + 8
(raiz / "public" / "favicon.svg").write_text(
    svg(f'<g transform="translate(4 {(lado - A) / 2:g})">{marca("f")}</g>', f"0 0 {lado} {lado}", "Orçamento Brasileiro"),
    encoding="utf-8")

# Logo completo (marca + nome), para materiais fora do site.
texto = (
    f'<text x="{L + 24}" y="{CY + 17:g}" font-family="\'Source Sans 3\', \'Source Sans Pro\', Helvetica, Arial, sans-serif" '
    f'font-size="50" fill="#1b1b1b" letter-spacing="1">'
    f'<tspan font-weight="700">ORÇAMENTO</tspan><tspan font-weight="300">BRASILEIRO</tspan></text>'
)
(raiz / "public" / "logo.svg").write_text(
    svg(marca("l") + "\n" + texto, f"0 0 {L + 24 + 660} {A}", "Orçamento Brasileiro"), encoding="utf-8")
print("ok")
