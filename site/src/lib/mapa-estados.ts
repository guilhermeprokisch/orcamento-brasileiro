/**
 * O mapa do Brasil por estado, desenhado na hora de gerar o site, a partir da malha do IBGE que o
 * pipeline do mapa grava em public/data/mapa/estados.geojson (já simplificada). Sem o arquivo (um
 * `astro check` sem os dados, por exemplo), devolve null e a página usa outra forma.
 *
 * Projeção equirretangular com a longitude encolhida pelo cosseno de 15°S: no Brasil, a diferença
 * para uma projeção de verdade não aparece numa imagem deste tamanho.
 */

const arquivos = import.meta.glob<string>("../../public/data/mapa/estados.geojson", { eager: true, query: "?raw", import: "default" });

const SIGLA: Record<string, string> = {
  "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
  "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
  "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
};

// Estados pequenos demais para a sigla caber dentro: a sigla vai para o mar, ligada por uma linha.
// [longitude, latitude] de onde fica a sigla.
const FORA: Record<string, [number, number]> = {
  RN: [-33.6, -5.2], PB: [-33.6, -6.9], PE: [-33.6, -8.6], AL: [-33.6, -10.3], SE: [-33.6, -12.0],
  ES: [-37.4, -19.9], RJ: [-39.6, -23.9],
};
// Onde a sigla fica melhor que no centro do contorno.
const AJUSTE: Record<string, [number, number]> = { GO: [-50.2, -16.4], MG: [-44.6, -18.4], PR: [-51.6, -24.7], SC: [-51.5, -27.2], PI: [-42.9, -7.6], CE: [-39.6, -5.2] };

const COS = Math.cos((15 * Math.PI) / 180);
const ESCALA = 14;
const OESTE = -74.4, LESTE = -31.4, NORTE = 5.8, SUL = -34.2;
const x = (lon: number) => (lon - OESTE) * COS * ESCALA;
const y = (lat: number) => (NORTE - lat) * ESCALA;
const r1 = (v: number) => Math.round(v * 10) / 10;

export interface EstadoNoMapa {
  uf: string;
  d: string;
  /** onde fica a sigla */
  rx: number;
  ry: number;
  /** a linha do contorno até a sigla, nos estados pequenos */
  linha: [number, number, number, number] | null;
}

type Anel = [number, number][];

/** Centro (média ponderada pela área) do maior pedaço do estado. */
function centro(poligonos: Anel[][]): [number, number] {
  let melhor: [number, number] = [0, 0], maior = -1;
  for (const p of poligonos) {
    const anel = p[0];
    let a = 0, cx = 0, cy = 0;
    for (let i = 0; i < anel.length - 1; i++) {
      const [x0, y0] = anel[i], [x1, y1] = anel[i + 1];
      const f = x0 * y1 - x1 * y0;
      a += f; cx += (x0 + x1) * f; cy += (y0 + y1) * f;
    }
    if (Math.abs(a) > maior) { maior = Math.abs(a); melhor = [cx / (3 * a), cy / (3 * a)]; }
  }
  return melhor;
}

function montar(): { largura: number; altura: number; estados: EstadoNoMapa[] } | null {
  const texto = Object.values(arquivos)[0];
  if (!texto) return null;
  const geo = JSON.parse(texto) as { features: { properties: { id: string }; geometry: { type: string; coordinates: unknown } }[] };
  const estados = geo.features.flatMap((f) => {
    const uf = SIGLA[String(f.properties.id)];
    if (!uf) return [];
    const g = f.geometry;
    const poligonos = (g.type === "MultiPolygon" ? g.coordinates : [g.coordinates]) as Anel[][];
    const d = poligonos.map((p) => p.map((anel) => `M${anel.map(([lon, lat]) => `${r1(x(lon))},${r1(y(lat))}`).join("L")}Z`).join("")).join("");
    const [clon, clat] = centro(poligonos);
    const fora = FORA[uf];
    const [lon, lat] = fora ?? AJUSTE[uf] ?? [clon, clat];
    return [{
      uf, d, rx: r1(x(lon)), ry: r1(y(lat)),
      linha: fora ? [r1(x(clon)), r1(y(clat)), r1(x(lon) - 3), r1(y(lat))] as [number, number, number, number] : null,
    }];
  });
  return { largura: r1(x(LESTE)), altura: r1(y(SUL)), estados };
}

export const MAPA_ESTADOS = montar();
