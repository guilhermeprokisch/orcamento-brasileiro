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
  # Dívida das prefeituras (RGF, Anexo 2): baixada pelo rgf-prefeituras.yml, que guarda o cache no release
  # "dados-siconfi" (rgf-a02-mun.tar, trazido pelo semente aplicar acima). Sem consultas: monta a saída com a
  # cópia de referência mais o que o cache tiver.
  pipe pode-falhar "Dívida das prefeituras" divida --prefeituras --max-chamadas 0
  # Gasto com pessoal (RGF, Anexo 1): estados pela API; prefeituras como a dívida (rgf-a01-mun.tar).
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
  # Quando o dinheiro sai (/contas#quando): empenhado, liquidado, pago e restos a pagar mês a mês, por tipo de
  # despesa. Lê os mesmos zips mensais que o passo acima já baixou e o cache rp-{ano}.json que o "Orçamento
  # federal" grava — por isso depende dos dois e fica aqui, no fim da fila. Ano fechado, como o gasto-federal.
  pipe pode-falhar "Fluxo mensal da despesa" fluxo 2025
  # Dívida ativa da União (PGFN) por cidade, com a cidade de cada empresa no cadastro de CNPJ da Receita: carga
  # feita à mão (uv run divida-ativa; ~1,5 GB da PGFN e ~6,7 GB da Receita, lidos e apagados), uma vez por
  # trimestre. Aqui só a cópia de referência.
  pipe pode-falhar "Dívida ativa da União" divida-ativa --sem-baixar
  # Benefícios fiscais por empresa (/impostos/empresas): a Dirbi da Receita (~1,6 GB por três anos), o cadastro de CNPJ
  # (natureza jurídica, ~1,3 GB) e a dívida ativa, numa carga à mão (uv run beneficios-fiscais), a cada atualização
  # semestral da Dirbi. Os Parquet ficam no bucket; aqui só a cópia de referência do resumo.
  pipe pode-falhar "Benefícios fiscais por empresa" beneficios-fiscais --sem-baixar
  # BNDES e estatais (/bndes e a seção da cidade): as operações do BNDES (~1,2 GB), o cadastro de CNPJ (~1,3 GB), o
  # Orçamento de Subsídios, o Resultado do Tesouro e a SEST, numa carga à mão (uv run bndes) quando o BNDES atualiza
  # (todo mês). Aqui só as cópias de referência.
  pipe pode-falhar "BNDES e estatais" bndes --sem-baixar
  # Juízes e promotores acima do teto (DadosJusBr): o supersalarios.yml baixa os meses novos todo dia 20 e abre um
  # pull request com a cópia de referência; aqui só essa cópia.
  pipe pode-falhar "Acima do teto (DadosJusBr)" supersalarios --sem-baixar
  # Acima do teto no Executivo federal (Portal da Transparência, servidores civis, honorários e jetons): carga à mão
  # (uv run supersalarios-federal; o Portal pede captcha depois de alguns downloads, e o comando completa os 12 meses
  # em mais de uma rodada). Aqui só a cópia de referência.
  pipe pode-falhar "Acima do teto: Executivo federal" supersalarios-federal --sem-baixar
  # Acima do teto no Executivo dos estados: o supersalarios-estados.yml baixa os meses novos de cada estado todo dia
  # 25 (um job por estado) e abre um pull request com a cópia de referência; aqui só essa cópia. CE, AL e PI recusam os
  # servidores do GitHub e rodam no dia 24 numa máquina de casa (.github/scripts/fora-do-github/).
  pipe pode-falhar "Acima do teto: Executivo dos estados" supersalarios-estados --sem-baixar
  # Acima do teto no Legislativo federal (Câmara, Senado e TCU): o supersalarios-legislativo.yml baixa os meses novos
  # todo dia 22 e abre um pull request com a cópia de referência; aqui só essa cópia.
  pipe pode-falhar "Acima do teto: Legislativo federal" supersalarios-legislativo --sem-baixar
  # Prefeituras da Paraíba (quem ganha mais que o prefeito, pela folha do TCE-PB): o supersalarios-municipios.yml baixa
  # todo dia 23 e abre um pull request com a cópia de referência; aqui só essa cópia.
  pipe pode-falhar "Acima do teto: prefeituras da Paraíba" supersalarios-municipios --sem-baixar
  # Políticos (deputados federais e senadores: cota, gabinete, emendas e TSE): o politicos.yml baixa todo dia 5 e abre
  # um pull request com a cópia de referência; aqui só essa cópia.
  pipe pode-falhar "Políticos" politicos --sem-baixar
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
  # Os contratos (PNCP) vêm do contratos.yml, que baixa os dias novos de janeiro a abril e abre um pull request
  # com pipeline/referencia/contratos.json e contratos-resumo.json; aqui só essas cópias.
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
  # Os Parquet do explorador vão para o bucket pelo contratos.yml; aqui só o resumo (cópia de referência).
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
