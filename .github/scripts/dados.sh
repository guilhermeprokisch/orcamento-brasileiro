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
  if "$@" >"$arq.log" 2>&1; then echo ok >"$arq.status"
  elif [ $? -eq 3 ]; then echo referencia >"$arq.status"   # falhou, mas o site sai com a cópia de referência
  else echo "$tipo" >"$arq.status"; fi
  echo "$nome" >"$arq.nome"
  echo "$((SECONDS - ini))" >"$arq.tempo"
}
pipe() { local tipo="$1" nome="$2"; shift 2; passo "$tipo" "$nome" uv run --project pipeline "$@"; }

# com_referencia <cópia> <destino> <comando…>: se o comando falhar, põe no site a última versão boa (a cópia em
# pipeline/referencia/, feita à mão daqui do Brasil) em vez de deixar o site sem a parte. Sai com 3 nesse caso.
com_referencia() {
  local ref="$1" dest="$2"; shift 2
  "$@" && return 0
  [ -f "$ref" ] || return 1
  mkdir -p "$(dirname "$dest")" && cp "$ref" "$dest"
  echo "a fonte falhou: o site sai com a cópia de referência ($ref)"
  return 3
}
# pipe_ref <nome> <cópia> <destino> <comando do pipeline…>: um passo opcional com cópia de referência.
pipe_ref() { local nome="$1" ref="$2" dest="$3"; shift 3; passo pode-falhar "$nome" com_referencia "$ref" "$dest" uv run --project pipeline "$@"; }

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
  # CAPAG (Tesouro Transparente): aqui, e não na fila independente, para não consultar o Tesouro ao mesmo
  # tempo que o SICONFI (o servidor derrubava a conexão). Se falhar, fica a cópia de referência.
  pipe_ref "CAPAG" pipeline/referencia/capag.json site/public/data/indicadores/capag.json capag
}

fila_independente() {
  pipe obrigatorio "Orçamento federal (Explorer)" orcamento
  # Gasto do governo da Paraíba e de Minas Gerais por município.
  pipe pode-falhar "Gasto estadual localizado (PB)" estado-pb 2025
  # MG: em 21/11/2026 a fonte passou a vir só com o cabeçalho; sem os dados, fica a cópia de referência.
  pipe_ref "Gasto estadual localizado (MG)" pipeline/referencia/estado-mg-2025.json site/public/data/estados/mg/2025.json estado-mg 2025
  # Paraná e Santa Catarina: só a folha de pagamento, pela cidade onde cada servidor trabalha. Cargas feitas
  # à mão (uv run estado-pr 2025, uv run estado-sc 2025; o ano fechado não muda): o servidor do PR trava por
  # minutos depois de alguns downloads e o portal de SC leva 45 s por mês. Aqui só as cópias de referência.
  pipe pode-falhar "Folha estadual por cidade (PR)" estado-pr 2025 --sem-baixar
  pipe pode-falhar "Folha estadual por cidade (SC)" estado-sc 2025 --sem-baixar
  # INEP: quando recusa a conexão do GitHub, cada comando usa a cópia em pipeline/referencia/.
  pipe pode-falhar "Ideb" ideb
  pipe pode-falhar "Escolas" escolas
  pipe pode-falhar "Matrículas" matriculas
  pipe pode-falhar "Saneamento (Censo 2022)" saneamento
  # Os Parquet dos exploradores ficam no bucket e são gerados à mão; aqui só os resumos.
  pipe pode-falhar "Explorador de emendas" explorador-emendas --sem-baixar
  pipe pode-falhar "Receitas da União" receitas-uniao --sem-baixar
  # As contas fecham? (/contas): resultado primário e nominal (Banco Central) e despesas obrigatórias e
  # discricionárias (Resultado do Tesouro). Se o download falhar, usa pipeline/referencia/contas-federal.json.
  pipe pode-falhar "Contas federais" contas-federal
  # O caminho dos impostos (/impostos): montado à mão (uv run caminho-impostos) com a DCA de todos os estados e
  # prefeituras e o Resultado do Tesouro; o ano é fechado, então aqui só a cópia de referência.
  pipe pode-falhar "Caminho dos impostos" caminho-impostos --sem-baixar
  # O que o governo federal gasta ele mesmo em cada cidade (execução da despesa do Portal e cidade de
  # cada unidade no Compras.gov.br). Se um dos dois não responder, usa a cópia em pipeline/referencia/.
  pipe pode-falhar "Gasto federal direto nas cidades" gasto-federal 2025
  # Dívida ativa da União (PGFN) por cidade, com a cidade de cada empresa no cadastro de CNPJ da Receita: carga
  # feita à mão (uv run divida-ativa; ~1,5 GB da PGFN e ~6,7 GB da Receita, lidos e apagados), uma vez por
  # trimestre. Aqui só a cópia de referência.
  pipe pode-falhar "Dívida ativa da União" divida-ativa --sem-baixar
  # Juízes e promotores acima do teto (DadosJusBr): carga feita à mão uma vez por mês (uv run supersalarios; ~2.000
  # pacotes pequenos, lidos e somados por órgão, o cache em data/raw só com as somas). Aqui só a cópia de referência.
  pipe pode-falhar "Acima do teto (DadosJusBr)" supersalarios --sem-baixar
}

# Espera um passo da fila SICONFI (ou a fila acabar: aí os passos seguintes usam o que houver).
esperar() { while [ ! -e "$1" ] && kill -0 "$PID_SICONFI" 2>/dev/null; do sleep 2; done; }

fila_cidades() {
  esperar "$CIDADES_OK"
  pipe pode-falhar "População de cada ano (IBGE)" populacao
  # Fundo de aposentadoria dos servidores (ISP-RPPS, Ministério da Previdência): planilha anual, achada pelo nome
  # da cidade em municipios.json. Se o site do Ministério não responder, usa pipeline/referencia/previdencia.json.
  pipe pode-falhar "Previdência dos servidores (ISP)" previdencia
  # Postos e hospitais: CNES, SIH e SIA baixados à mão; aqui só a cópia de referência.
  pipe pode-falhar "Postos e hospitais" unidades-saude --sem-baixar
  # Contratos (PNCP) e pagamentos (TCE-PB; TCE-AC e TCE-SC pelos painéis e TCE-PE pela API, que só respondem
  # do Brasil, e este robô roda fora do país): cargas feitas à mão (uv run pagamentos [--uf AC|SC|PE]); aqui
  # só as cópias (pipeline/referencia/pagamentos*.json, todas de uma vez).
  # CE (API do TCE-CE) e ES (arquivos do TCE-ES) também: uv run pagamentos --uf CE|ES, à mão; aqui só as cópias.
  pipe pode-falhar "Contratos das prefeituras" contratos --sem-baixar
  pipe pode-falhar "Pagamentos das prefeituras" pagamentos --sem-baixar
  # (O passo acima copia também AM e TO, pagamentos-am.json e -to.json: uv run pagamentos --uf AM|TO, à mão,
  # e PR e RS, pagamentos-pr.json e -rs.json: uv run pagamentos --uf PR|RS, à mão; o TCE-RS só responde do Brasil.)
}

fila_mapa() {
  esperar "$MAPA_OK"
  # Emendas: precisam de nomes.json, que o passo do mapa grava (por isso aqui, e não na fila independente).
  pipe_ref "Emendas parlamentares (CGU)" pipeline/referencia/emendas.json site/public/data/indicadores/emendas.json emendas
  pipe pode-falhar "Mortalidade infantil" saude
  pipe pode-falhar "Homicídios" seguranca
  pipe pode-falhar "Explorador de contratos" explorador-contratos --sem-baixar
  # Camadas do mapa: arrecadação federal por município, imposto de renda por residência, dinheiro
  # federal (o Portal da Transparência às vezes responde com CAPTCHA) e INSS.
  pipe pode-falhar "Arrecadação federal por município" rfb
  pipe_ref "Imposto de renda por cidade de residência" pipeline/referencia/irpf-res.json site/public/data/mapa/irpf-res.json irpf
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
    referencia) echo "::warning::$nome: a fonte falhou; o site sai com a cópia de referência (pipeline/referencia/)" ;;
  esac
done
echo "Programas de dados: $((SECONDS - ini))s no total, em quatro filas."
exit "$falhou"
