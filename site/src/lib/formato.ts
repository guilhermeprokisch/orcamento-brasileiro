const nf = (digitos: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digitos, maximumFractionDigits: digitos });

const nf0 = nf(0);
const nf1 = nf(1);
const nf2 = nf(2);

/** "R$ 5,74 tri", "R$ 345,6 bi", "R$ 12,3 mi", "R$ 900 mil" */
export function moedaCurta(v: number): string {
  const a = Math.abs(v);
  const s = v < 0 ? "−" : "";
  if (a >= 1e12) return `${s}R$ ${nf2.format(a / 1e12)} tri`;
  if (a >= 1e9) return `${s}R$ ${nf1.format(a / 1e9)} bi`;
  if (a >= 1e6) return `${s}R$ ${nf1.format(a / 1e6)} mi`;
  if (a >= 1e3) return `${s}R$ ${nf0.format(a / 1e3)} mil`;
  return `${s}R$ ${nf0.format(a)}`;
}

/** "R$ 5,7 trilhões", "R$ 254,1 bilhões", "R$ 1,2 milhão" */
export function moedaExtenso(v: number): string {
  const a = Math.abs(v);
  const s = v < 0 ? "−" : "";
  const un = (n: number, sing: string, plur: string) => {
    const x = Math.round(n * 10) / 10;
    return `${s}R$ ${nf1.format(x).replace(/,0$/, "")} ${x < 2 ? sing : plur}`;
  };
  if (a >= 1e12) return un(a / 1e12, "trilhão", "trilhões");
  if (a >= 1e9) return un(a / 1e9, "bilhão", "bilhões");
  if (a >= 1e6) return un(a / 1e6, "milhão", "milhões");
  if (a >= 1e3) return `${s}R$ ${nf0.format(a / 1e3)} mil`;
  return `${s}R$ ${nf0.format(a)}`;
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
export const moedaCompleta = (v: number) => brl.format(v);

export function pct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${nf1.format(v * 100)}%`;
}
