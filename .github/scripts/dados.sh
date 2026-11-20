#!/usr/bin/env bash
# Os programas de dados da publicação (.github/workflows/publicar.yml), em quatro filas ao mesmo tempo.
#
# - Fila SICONFI: tudo que consulta a API do SICONFI, que aceita uma consulta por segundo. Fica em
#   fila única para não passar do limite. Começa pelas cidades e pelo mapa, de que as outras precisam.
# - Fila independente: o que não depende de nenhum outro passo.
# - Fila das cidades: espera municipios.json (passo das cidades).
# - Fila do mapa: espera nomes.json (passo do mapa); as camadas do mapa também escrevem na pasta dele.
#
# Cada passo grava a saída num arquivo próprio, mostrado inteiro no fim (num grupo recolhível do
# GitHub), para as filas não se misturarem. Um passo obrigatório que falha faz a publicação falhar;
# um opcional ("pode falhar") só gera um aviso, como o continue-on-error de antes.
set -uo pipefail

LOGS="$(mktemp -d)"
CIDADES_OK="$LOGS/cidades.ok"
MAPA_OK="$LOGS/mapa.ok"
uv sync --project pipeline --quiet   # uma vez só, antes das filas, para elas não disputarem o ambiente

# passo <obrigatorio|pode-falhar> <nome> <comando…>
passo() {
  local tipo="$1" nome="$2"; shift 2
  local arq="$LOGS/$(date +%s%N)-${nome//[^a-zA-Z0-9]/_}"
  local ini=$SECONDS
  if "$@" >"$arq.log" 2>&1; then echo ok >"$arq.status"; else echo "$tipo" >"$arq.status"; fi
  echo "$nome" >"$arq.nome"
  echo "$((SECONDS - ini))" >"$arq.tempo"
}
pipe() { local tipo="$1" nome="$2"; shift 2; passo "$tipo" "$nome" uv run --project pipeline "$@"; }

fila_siconfi() {
  # Histórico dos municípios (FINBRA, baixado à mão por causa do captcha): vem do release
  # "dados-siconfi" e preenche o que falta no cache. Sem ele, o site sai sem a receita e o
  # histórico das cidades.
  passo pode-falhar "Cache do SICONFI (release)" uv run --project pipeline semente aplicar
  # Estados e municípios: ~11 mil consultas na primeira vez; o limite deixa o resto para as execuções
  # seguintes (o cache de data/raw acumula).
  pipe obrigatorio "Estados e cidades (SICONFI)" cidades --max-chamadas 1000
  touch "$CIDADES_OK"
  # Dados da página /mapa, a partir dos caches do SICONFI.
  pipe obrigatorio "Mapa" mapa --max-chamadas 300
  touch "$MAPA_OK"
  # O ano em andamento (RREO): estados pela API; municípios do release mantido pelo bimestral.yml.
  pipe pode-falhar "Ano em andamento (RREO)" rreo --max-chamadas 200
  # Dívida dos governos estaduais (RGF, Anexo 2): o cache em data/raw guarda os anos já baixados.
  pipe pode-falhar "Dívida dos estados" divida
  # Dívida das prefeituras: feita à mão (uv run divida --prefeituras); aqui só a cópia de referência.
  pipe pode-falhar "Dívida das prefeituras" divida --prefeituras --max-chamadas 0
  # Gasto com pessoal (RGF, Anexo 1): estados pela API; prefeituras feitas à mão, só a cópia.
  pipe pode-falhar "Gasto com pessoal dos estados" pessoal
  pipe pode-falhar "Gasto com pessoal das prefeituras" pessoal --prefeituras --max-chamadas 0
  # Dívida pública federal (/divida): Tesouro, Banco Central e o RGF dos 27 estados. Se o download
  # falhar, usa a cópia em pipeline/referencia/divida-federal.json.
  pipe pode-falhar "Dívida federal" divida-federal
}

fila_independente() {
  pipe obrigatorio "Orçamento federal (Explorer)" orcamento
  # Gasto do governo da Paraíba e de Minas Gerais por município.
  pipe pode-falhar "Gasto estadual localizado (PB)" estado-pb 2025
  pipe pode-falhar "Gasto estadual localizado (MG)" estado-mg 2025
  # INEP: quando recusa a conexão do GitHub, cada comando usa a cópia em pipeline/referencia/.
  pipe pode-falhar "Ideb" ideb
  pipe pode-falhar "Escolas" escolas
  pipe pode-falhar "Matrículas" matriculas
  pipe pode-falhar "CAPAG" capag
  pipe pode-falhar "Saneamento (Censo 2022)" saneamento
  pipe pode-falhar "Emendas parlamentares (CGU)" emendas
  # Os Parquet dos exploradores ficam no bucket e são gerados à mão; aqui só os resumos.
  pipe pode-falhar "Explorador de emendas" explorador-emendas --sem-baixar
  pipe pode-falhar "Receitas da União" receitas-uniao --sem-baixar
}

# Espera um passo da fila SICONFI (ou a fila acabar: aí os passos seguintes usam o que houver).
esperar() { while [ ! -e "$1" ] && kill -0 "$PID_SICONFI" 2>/dev/null; do sleep 2; done; }

fila_cidades() {
  esperar "$CIDADES_OK"
  pipe pode-falhar "População de cada ano (IBGE)" populacao
  # Postos e hospitais: CNES, SIH e SIA baixados à mão; aqui só a cópia de referência.
  pipe pode-falhar "Postos e hospitais" unidades-saude --sem-baixar
  # Contratos (PNCP) e pagamentos (TCE-PB, painéis do AC e de SC): cargas feitas à mão; só as cópias.
  pipe pode-falhar "Contratos das prefeituras" contratos --sem-baixar
  pipe pode-falhar "Pagamentos das prefeituras" pagamentos --sem-baixar
}

fila_mapa() {
  esperar "$MAPA_OK"
  pipe pode-falhar "Mortalidade infantil" saude
  pipe pode-falhar "Homicídios" seguranca
  pipe pode-falhar "Explorador de contratos" explorador-contratos --sem-baixar
  # Camadas do mapa: arrecadação federal por município, imposto de renda por residência, dinheiro
  # federal (o Portal da Transparência às vezes responde com CAPTCHA) e INSS.
  pipe pode-falhar "Arrecadação federal por município" rfb
  pipe pode-falhar "Imposto de renda por cidade de residência" irpf
  pipe pode-falhar "Dinheiro federal" federal 2025
  pipe pode-falhar "INSS" inss
}

ini=$SECONDS
fila_siconfi & PID_SICONFI=$!
fila_independente & PID_INDEP=$!
fila_cidades & PID_CIDADES=$!
fila_mapa & PID_MAPA=$!
wait "$PID_SICONFI" "$PID_INDEP" "$PID_CIDADES" "$PID_MAPA"

falhou=0
for st in "$LOGS"/*.status; do
  base="${st%.status}"; nome="$(cat "$base.nome")"; tempo="$(cat "$base.tempo")"; status="$(cat "$st")"
  echo "::group::$nome (${tempo}s, $status)"
  cat "$base.log"
  echo "::endgroup::"
  case "$status" in
    obrigatorio) echo "::error::$nome falhou"; falhou=1 ;;
    pode-falhar) echo "::warning::$nome falhou; o site sai sem essa parte ou com a cópia de referência" ;;
  esac
done
echo "Programas de dados: $((SECONDS - ini))s no total, em quatro filas."
exit "$falhou"
