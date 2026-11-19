/**
 * Troca de ano nas páginas de cidade e de estado, no navegador. A página vem montada com o
 * ano mais recente; ao escolher outro, baixa /dados/fichas/{ano}/{grupo}.json e redesenha as
 * partes marcadas com data-parte, com as mesmas funções do build (lib/ficha-html.ts).
 * Partes que só existem para o ano mais recente (data-so-padrao) somem, com um aviso.
 * O ano escolhido vai para o endereço (?ano=2018), para dar para compartilhar.
 */
import { areasHtml, contasHtml, fraseHtml, numerosHtml, type Contexto } from "./ficha-html";
import type { Ficha, Pacote } from "./ficha";

export interface BaseDaPagina {
  ibge: number;
  nome: string;
  uf: string;
  esfera: "mun" | "uf";
  quem: string;
  onde: string;
  destaques: { cod: string; titulo: string }[];
  /** Anos com contas, do mais recente ao mais antigo. */
  anos: number[];
  /** O ano com que a página foi montada. */
  padrao: number;
  /** O arquivo de cada ano: a sigla do estado (cidades) ou "estados". */
  grupo: string;
}
export type ArquivoDoAno = Pacote & { entes: Record<string, Ficha> };

const baixados = new Map<string, Promise<ArquivoDoAno | null>>();
export function arquivoDoAno(ano: number, grupo: string): Promise<ArquivoDoAno | null> {
  const chave = `${ano}/${grupo}`;
  if (!baixados.has(chave)) {
    baixados.set(chave, fetch(`/dados/fichas/${chave}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
  }
  return baixados.get(chave)!;
}

const PARTES: [string, (ctx: Contexto) => string][] = [["frase", fraseHtml], ["numeros", numerosHtml], ["areas", areasHtml], ["contas", contasHtml]];
const lista = new Intl.ListFormat("pt-BR", { style: "long", type: "conjunction" });

/** Liga o seletor de ano. `aoTrocar` recebe o ano já desenhado (a página do estado atualiza a lista de cidades). */
export function iniciarTrocaDeAno(aoTrocar?: (ano: number, base: BaseDaPagina) => void) {
  const dados = document.getElementById("ficha-base");
  const achado = document.getElementById("ano-ficha") as HTMLSelectElement | null;
  if (!dados || !achado) return;
  const seletor = achado;
  const base: BaseDaPagina = JSON.parse(dados.textContent ?? "{}");
  const partes = PARTES.map(([nome, desenhar]) => ({ el: document.querySelector<HTMLElement>(`[data-parte="${nome}"]`), desenhar }));
  const original = new Map(partes.map((p) => [p.el, p.el?.innerHTML ?? ""]));
  const soPadrao = [...document.querySelectorAll<HTMLElement>("[data-so-padrao]")].filter((el) => el.textContent?.trim());
  const aviso = document.getElementById("aviso-ano");
  let vez = 0;

  const avisar = (texto: string | null) => {
    if (!aviso) return;
    aviso.hidden = !texto;
    aviso.textContent = texto ?? "";
  };

  async function mostrar(ano: number, mudarEndereco = true) {
    const minha = ++vez;
    if (ano === base.padrao) {
      for (const p of partes) if (p.el) p.el.innerHTML = original.get(p.el) ?? "";
      soPadrao.forEach((el) => (el.hidden = false));
      avisar(null);
    } else {
      partes.forEach((p) => p.el?.setAttribute("aria-busy", "true"));
      const arq = await arquivoDoAno(ano, base.grupo);
      if (minha !== vez) return;   // a pessoa já escolheu outro ano
      partes.forEach((p) => p.el?.removeAttribute("aria-busy"));
      const ficha = arq?.entes[String(base.ibge)];
      if (!arq || !ficha) {
        avisar(arq ? `Não há prestação de contas de ${ano}.` : `Não foi possível carregar ${ano}. Tente de novo.`);
        seletor.value = String(base.padrao);
        return mostrar(base.padrao, mudarEndereco);
      }
      const ctx: Contexto = { ...base, ano, ficha, pacote: arq };
      for (const p of partes) if (p.el) p.el.innerHTML = p.desenhar(ctx);
      soPadrao.forEach((el) => (el.hidden = true));
      const rotulos = soPadrao.map((el) => el.dataset.soPadrao!).filter(Boolean);
      avisar(rotulos.length ? `Mostrando ${ano}. ${lista.format(rotulos).replace(/^./, (c) => c.toUpperCase())} só ${rotulos.length > 1 ? "aparecem" : "aparece"} com ${base.padrao}.` : null);
    }
    document.querySelectorAll<HTMLElement>("[data-ano-texto]").forEach((el) => (el.textContent = String(ano)));
    if (mudarEndereco) {
      const url = new URL(location.href);
      if (ano === base.padrao) url.searchParams.delete("ano");
      else url.searchParams.set("ano", String(ano));
      history.replaceState(null, "", url);
    }
    aoTrocar?.(ano, base);
  }

  seletor.addEventListener("change", () => mostrar(Number(seletor.value)));
  const pedido = Number(new URLSearchParams(location.search).get("ano"));
  if (pedido && pedido !== base.padrao) {
    if (base.anos.includes(pedido)) {
      seletor.value = String(pedido);
      mostrar(pedido, false);
    } else {
      avisar(`Não há prestação de contas de ${pedido}. Mostrando ${base.padrao}.`);
    }
  }
}
