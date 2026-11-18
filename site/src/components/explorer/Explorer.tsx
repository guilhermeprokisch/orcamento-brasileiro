import { createMemo, createResource, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import Treemap from "./Treemap";
import {
  agrupar, carregarAno, carregarResumo, faixa, FAIXAS, METRICAS, ROTULO_DIM, ROTULO_DIM_PLURAL, ROTULO_METRICA,
  taxaRealizacao, VISOES, type Item, type Metrica, type Visao,
} from "../../lib/dados";
import { moedaCompleta, moedaCurta, pct } from "../../lib/formato";
import "./explorer.css";

interface Estado {
  ano: number | null;
  visao: Visao;
  metrica: Metrica;
  caminho: string[];
  semRefin: boolean;
}

function lerUrl(): Estado {
  const p = new URLSearchParams(location.search);
  const ano = Number(p.get("ano"));
  const visao = (p.get("por") ?? "orgao") as Visao;
  const metrica = (p.get("metrica") ?? "atualizado") as Metrica;
  return {
    ano: Number.isInteger(ano) && ano > 0 ? ano : null,
    visao: visao in VISOES ? visao : "orgao",
    metrica: METRICAS.includes(metrica) ? metrica : "atualizado",
    caminho: (p.get("c") ?? "").split(",").filter(Boolean),
    semRefin: p.get("refin") === "0",
  };
}

function escreverUrl(e: Estado, push: boolean) {
  const p = new URLSearchParams();
  if (e.ano) p.set("ano", String(e.ano));
  p.set("por", e.visao);
  p.set("metrica", e.metrica);
  if (e.semRefin) p.set("refin", "0");
  if (e.caminho.length) p.set("c", e.caminho.join(","));
  const url = `${location.pathname}?${p}`;
  if (push) history.pushState(null, "", url);
  else history.replaceState(null, "", url);
}

export default function Explorer() {
  const [estado, setEstado] = createSignal<Estado>(lerUrl());
  const [resumo] = createResource(carregarResumo);

  // Ano padrão: o último ano completo (o corrente ainda está em execução).
  const ano = createMemo(() => {
    const e = estado().ano;
    const anos = resumo()?.anos.map((a) => a.ano) ?? [];
    if (e && anos.includes(e)) return e;
    const corrente = new Date().getFullYear();
    const completos = anos.filter((a) => a < corrente);
    return completos.at(-1) ?? anos.at(-1) ?? null;
  });
  const [doc] = createResource(ano, carregarAno);

  const mudar = (parcial: Partial<Estado>, push = false) => {
    const novo = { ...estado(), ano: ano(), ...parcial };
    setEstado(novo);
    escreverUrl(novo, push);
  };

  onMount(() => {
    const voltar = () => setEstado(lerUrl());
    addEventListener("popstate", voltar);
    onCleanup(() => removeEventListener("popstate", voltar));
  });

  const niveis = () => VISOES[estado().visao].niveis;
  const grupo = createMemo(() => {
    const d = doc();
    if (!d) return null;
    return agrupar(d, [...niveis()], estado().caminho, estado().semRefin);
  });
  const filhos = createMemo(() => {
    const g = grupo();
    if (!g) return [];
    const m = estado().metrica;
    return [...g.filhos].sort((a, b) => b.valores[m] - a.valores[m]);
  });
  const podeDescer = () => estado().caminho.length < niveis().length - 1;

  const migalhas = createMemo(() => {
    const d = doc();
    if (!d) return [];
    return estado().caminho.map((cod, i) => ({
      nivel: niveis()[i],
      nome: d.dims[niveis()[i]][cod] ?? cod,
      caminho: estado().caminho.slice(0, i + 1),
    }));
  });

  const descer = (item: Item) => mudar({ caminho: [...estado().caminho, item.codigo] }, true);

  const total = () => grupo()?.total;
  const totalMetrica = () => Math.max(1, total()?.[estado().metrica] ?? 1);
  const vazio = () => {
    const t = total();
    return !!t && METRICAS.every((m) => t[m] === 0);
  };

  return (
    <div class="ex">
      <div class="ex-controles" role="group" aria-label="Filtros do Explorer">
        <label class="ex-campo">
          <span class="small muted">Ano</span>
          <select
            onChange={(e) => mudar({ ano: Number(e.currentTarget.value) })}
            disabled={!resumo()}
          >
            <For each={[...(resumo()?.anos ?? [])].reverse()}>
              {(a) => (
                <option value={a.ano} selected={a.ano === ano()}>
                  {a.ano}{a.ano === new Date().getFullYear() ? " (em execução)" : ""}
                </option>
              )}
            </For>
          </select>
        </label>

        <fieldset class="ex-campo">
          <legend class="small muted">Ver por</legend>
          <div class="seg">
            <For each={Object.entries(VISOES) as [Visao, (typeof VISOES)[Visao]][]}>
              {([k, v]) => (
                <button type="button" aria-pressed={estado().visao === k}
                  onClick={() => mudar({ visao: k, caminho: [] }, true)}>
                  {v.rotulo}
                </button>
              )}
            </For>
          </div>
        </fieldset>

        <fieldset class="ex-campo">
          <legend class="small muted">Tamanho dos blocos</legend>
          <div class="seg">
            <For each={["atualizado", "empenhado", "realizado"] as Metrica[]}>
              {(m) => (
                <button type="button" aria-pressed={estado().metrica === m} onClick={() => mudar({ metrica: m })}>
                  {m === "atualizado" ? "Dotação" : ROTULO_METRICA[m]}
                </button>
              )}
            </For>
          </div>
        </fieldset>

        <label class="ex-check">
          <input type="checkbox" checked={estado().semRefin}
            onChange={(e) => mudar({ semRefin: e.currentTarget.checked })} />
          <span>Excluir refinanciamento da dívida</span>
        </label>
      </div>

      <nav class="ex-migalhas" aria-label="Caminho">
        <ol>
          <li>
            <button type="button" class="link" onClick={() => mudar({ caminho: [] }, true)}
              aria-current={estado().caminho.length === 0 ? "page" : undefined}>
              Orçamento federal {ano() ?? ""}
            </button>
          </li>
          <For each={migalhas()}>
            {(m, i) => (
              <li>
                <span class="sep" aria-hidden="true">›</span>
                <button type="button" class="link" onClick={() => mudar({ caminho: m.caminho }, true)}
                  aria-current={i() === migalhas().length - 1 ? "page" : undefined}
                  title={ROTULO_DIM[m.nivel]}>
                  {m.nome}
                </button>
              </li>
            )}
          </For>
        </ol>
      </nav>

      <Show when={doc.error || resumo.error}>
        <p class="ex-erro">Não foi possível carregar os dados. {String((doc.error ?? resumo.error)?.message ?? "")}</p>
      </Show>

      <Show when={total()} fallback={<div class="ex-carregando muted" aria-busy="true">Carregando dados…</div>}>
        {(t) => (
          <>
            <section class="ex-numeros" aria-label="Totais do nível atual">
              <For each={METRICAS}>
                {(m) => (
                  <div class="ex-num" classList={{ ativo: m === estado().metrica }}>
                    <div class="small muted">{ROTULO_METRICA[m]}</div>
                    <div class="ex-num-valor num" title={moedaCompleta(t()[m])}>{moedaCurta(t()[m])}</div>
                  </div>
                )}
              </For>
              <div class="ex-num">
                <div class="small muted">Realizado / dotação atualizada</div>
                <div class="ex-num-valor num">{pct(taxaRealizacao(t()))}</div>
              </div>
            </section>

            <Show when={!vazio()} fallback={
              <div class="ex-vazio">
                <p>Este caminho não tem valores em {ano()}.</p>
                <button type="button" onClick={() => mudar({ caminho: [] }, true)}>Voltar ao início</button>
              </div>
            }>
              <div class="ex-cabecalho">
                <h2>
                  {grupo()?.proximo ? ROTULO_DIM_PLURAL[grupo()!.proximo!] : ""}
                  <span class="muted small"> · {filhos().length} {filhos().length === 1 ? "item" : "itens"} ·blocos por {ROTULO_METRICA[estado().metrica].toLowerCase()}</span>
                </h2>
                <div class="ex-legenda" aria-label="Legenda de cores">
                  <span class="small muted">Realizado da dotação atualizada:</span>
                  <ul>
                    <For each={FAIXAS}>
                      {(rotulo, i) => (
                        <li>
                          <span class="sw" style={{ background: i() === 0 ? "var(--neutral-cell)" : `var(--exec-${i()})` }} />
                          <span class="small">{rotulo}</span>
                        </li>
                      )}
                    </For>
                  </ul>
                </div>
              </div>

              <Treemap
                itens={filhos()}
                metrica={estado().metrica}
                total={totalMetrica()}
                podeDescer={podeDescer()}
                onEscolher={descer}
              />

              <div class="ex-tabela-wrap">
                <table class="ex-tabela">
                  <caption class="visually-hidden">Itens do nível atual</caption>
                  <thead>
                    <tr>
                      <th scope="col">{grupo()?.proximo ? ROTULO_DIM[grupo()!.proximo!] : ""}</th>
                      <th scope="col" class="n">Dotação atualizada</th>
                      <th scope="col" class="n">Empenhado</th>
                      <th scope="col" class="n">Realizado</th>
                      <th scope="col" class="n">% realizado</th>
                      <th scope="col" class="n">Parcela</th>
                    </tr>
                  </thead>
                  <tbody>
                    <For each={filhos()}>
                      {(f) => {
                        const tx = taxaRealizacao(f.valores);
                        return (
                          <tr>
                            <th scope="row">
                              <span class="sw" style={{ background: faixa(tx) ? `var(--exec-${faixa(tx)})` : "var(--neutral-cell)" }} />
                              <Show when={podeDescer()} fallback={<span>{f.nome}</span>}>
                                <button type="button" class="link" onClick={() => descer(f)}>{f.nome}</button>
                              </Show>
                              <span class="cod muted">{f.codigo}</span>
                            </th>
                            <td class="n num">{moedaCurta(f.valores.atualizado)}</td>
                            <td class="n num">{moedaCurta(f.valores.empenhado)}</td>
                            <td class="n num">{moedaCurta(f.valores.realizado)}</td>
                            <td class="n num">{pct(tx)}</td>
                            <td class="n num">{pct(f.valores[estado().metrica] / totalMetrica())}</td>
                          </tr>
                        );
                      }}
                    </For>
                  </tbody>
                </table>
              </div>
            </Show>
          </>
        )}
      </Show>
    </div>
  );
}
