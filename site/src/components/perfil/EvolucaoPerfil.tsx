import { createSignal } from "solid-js";
import Evolucao, { type Ponto } from "../explorer/Evolucao";
import type { Metrica } from "../../lib/dados";
import "../explorer/explorer.css";

interface Props {
  nominal: Ponto[];
  real: Ponto[];
  baseIpca: number | null;
  anoSelecionado: number | null;
  anoCorrente: number;
  /** Link do Explorer sem o parâmetro de ano; o clique numa barra abre aquele ano. */
  explorer: string;
}

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
    <div>
      <div class="perfil-ev-controles">
        <div class="ex-seg" role="group" aria-label="Valor">
          <button type="button" aria-pressed={metrica() === "atualizado"} onClick={() => setMetrica("atualizado")}>Dotação</button>
          <button type="button" aria-pressed={metrica() === "empenhado"} onClick={() => setMetrica("empenhado")}>Empenhado</button>
          <button type="button" aria-pressed={metrica() === "realizado"} onClick={() => setMetrica("realizado")}>Realizado</button>
        </div>
        <div class="ex-seg" role="group" aria-label="Correção pela inflação">
          <button type="button" aria-pressed={!real()} onClick={() => setReal(false)}>Nominal</button>
          <button type="button" aria-pressed={real()} disabled={props.baseIpca === null} onClick={() => setReal(true)}>
            Corrigido pelo IPCA
          </button>
        </div>
      </div>
      <Evolucao
        serie={real() ? props.real : props.nominal}
        metrica={metrica()}
        anoSelecionado={props.anoSelecionado}
        anoCorrente={props.anoCorrente}
        onAno={abrir}
      />
      <p class="ex-ev-nota">
        {real() && props.baseIpca
          ? `Valores em reais de ${props.baseIpca}, corrigidos pela média anual do IPCA (IBGE).`
          : "Valores nominais, sem correção pela inflação."}{" "}
        * {props.anoCorrente} ainda em execução. O código do órgão pode ter mudado em reorganizações do governo.
        Clique num ano para abri-lo no Explorer.
      </p>
    </div>
  );
}
