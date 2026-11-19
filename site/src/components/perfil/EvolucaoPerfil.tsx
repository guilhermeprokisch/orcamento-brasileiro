import { createSignal } from "solid-js";
import BarrasAno, { type Ponto } from "../explorer/BarrasAno";
import type { Metrica } from "../../lib/dados";

interface Props {
  nominal: Ponto[];
  real: Ponto[];
  baseIpca: number | null;
  anoSelecionado: number | null;
  anoCorrente: number;
  /** Link do Explorer sem o parâmetro de ano; o clique numa barra abre aquele ano. */
  explorer: string;
}

const METRICAS: [Metrica, string][] = [["atualizado", "Dotação"], ["empenhado", "Empenhado"], ["realizado", "Pago"]];

/** Evolução do perfil: escolha de valor e de correção como links de texto, barras grandes. */
export default function EvolucaoPerfil(props: Props) {
  const [real, setReal] = createSignal(props.baseIpca !== null);
  const [metrica, setMetrica] = createSignal<Metrica>("atualizado");

  const abrir = (ano: number) => {
    const u = new URL(props.explorer, location.origin);
    u.searchParams.set("ano", String(ano));
    if (real()) u.searchParams.set("ipca", "1");
    location.href = u.pathname + u.search;
  };

  return (
    <div class="perfil-ev">
      <div class="perfil-ev-texto">
        <h2>{props.nominal.length} anos de orçamento</h2>
        <p>
          {real() && props.baseIpca
            ? `Em reais de ${props.baseIpca}, corrigidos pela média anual do IPCA. Clique num ano para abri-lo no Explorer.`
            : "Em valores nominais, sem correção pela inflação. Clique num ano para abri-lo no Explorer."}
        </p>
        <div class="perfil-ev-opcoes">
          {METRICAS.map(([m, rotulo]) => (
            <button type="button" aria-pressed={metrica() === m} onClick={() => setMetrica(m)}>{rotulo}</button>
          ))}
          <span aria-hidden="true">|</span>
          <button type="button" aria-pressed={!real()} onClick={() => setReal(!real())} disabled={props.baseIpca === null}>
            {real() ? "Ver nominal" : "Corrigir pelo IPCA"}
          </button>
        </div>
      </div>
      <div class="perfil-ev-grafico">
        <BarrasAno serie={real() ? props.real : props.nominal} metrica={metrica()} anoSelecionado={props.anoSelecionado}
          anoCorrente={props.anoCorrente} altura={240} rotulos="todos" onAno={abrir} />
      </div>
    </div>
  );
}
