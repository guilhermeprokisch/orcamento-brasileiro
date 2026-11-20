# Dívida pública federal: fontes

Levantamento para a página `/divida` (item L do plano). Tudo conferido baixando os arquivos em
20/11/2026. Comando: `uv run divida-federal` (módulo `pipeline/src/orcamento_pipeline/divida_federal.py`).

## O que foi usado

### Tesouro Nacional: anexo do Relatório Mensal da Dívida (RMD)

- Página: <https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd>.
  Sem captcha. O endereço sem ano e mês redireciona para a edição mais recente
  (em 20/11/2026: `/2026/9`, setembro).
- Na página, o link `https://thot-arquivos.tesouro.gov.br/publicacao-anexo/<número>` com título
  `Anexo RMD_<Mês>_<aa>.zip` (3,6 MB). O número muda a cada edição, por isso o pipeline lê a página
  primeiro. O link responde 303 para `cdn.tesouro.gov.br`; o `HEAD` é recusado (405), só `GET` funciona.
- Dentro do zip, uma planilha com ~45 abas e a história mês a mês desde 2000 ou 2006. Valores em
  R$ bilhões, dívida "em poder do público" (sem os títulos que estão com o Banco Central):

  | Aba | O que tem | Desde |
  |-----|-----------|-------|
  | 2.1 | estoque da DPF por título (um mês por coluna) | dez/2000 |
  | 2.4 | composição da DPF: prefixado, índice de preços, taxa flutuante (Selic), câmbio | dez/2000 |
  | 2.7 | **detentores** dos títulos da DPMFi (dívida interna): instituições financeiras, fundos, previdência, não residentes, Tesouro Direto, governo, seguradoras, outros | jan/2007 (governo só desde jan/2011) |
  | 3.1 | vencimentos da DPF por faixa (até 12 meses, 1 a 2 anos…) | nov/2006 |
  | 3.7 | prazo médio da DPF, em anos | dez/2005 |
  | 4.2 | custo médio da DPF acumulado em 12 meses, % ao ano | dez/2005 |
  | 2.9 | **fatores de variação** da DPF, R$ milhões: títulos vendidos menos pagos (I.1), juros apropriados (I.2: juros e correção pela inflação, Selic e câmbio) e operações com o Banco Central (II) | jan/2007 |

  Notas: os detentores cobrem só a DPMFi (96% da DPF); a DPF externa não tem essa abertura. Na aba 2.7,
  mar/18 e abr/18 vêm como texto com asterisco (dados corrigidos). Desde set/2025, as cooperativas de
  crédito saíram de "outros" e foram para "instituições financeiras".
- O texto do RMD (PDF, link `publicacao/<número>`, que devolve uma página com o PDF num iframe) traz os
  mesmos números em prosa: serviu para conferir.

### Banco Central: SGS

API sem chave: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.<série>/dados?formato=json&dataInicial=01/01/2014&dataFinal=31/12/2099`.
Os códigos foram achados no portal de dados abertos do BC (`dadosabertos.bcb.gov.br/api/3/action/package_search`).

| Série | O que é |
|-------|---------|
| 13761 | dívida bruta do governo geral (DBGG), R$ milhões, metodologia desde 2008 |
| 13762 | DBGG, % do PIB |
| 4607  | juros nominais do Governo Federal, fluxo do mês, R$ milhões (NFSP sem desvalorização cambial) |
| 5751  | os mesmos juros, acumulados em 12 meses, % do PIB |
| 4382  | PIB acumulado em 12 meses, R$ milhões |

Escolhemos os juros do **Governo Federal** (4607), e não os do "Governo Federal e Banco Central"
(4606) nem os do setor público consolidado (4616), porque a página fala da dívida do Tesouro.

### Dívida dos estados (bloco "E os estados?")

API do SICONFI, `rgf` com `no_anexo=RGF-Anexo 02`, `co_esfera=E`, 3º quadrimestre do último ano fechado,
uma consulta por estado (27). Guardamos a dívida consolidada, a linha "Reestruturação da Dívida de
Estados e Municípios" (a dívida renegociada com a União, Lei 9.496/1997 e seguintes), a dívida
consolidada líquida e a receita corrente líquida ajustada. Fim de 2025: R$ 1.255,9 bi de dívida
consolidada (o mesmo total de `site/public/data/estados/divida.json`), dos quais R$ 768,2 bi (61%) na
linha de reestruturação. Cuidado: nem todo estado usa essa linha. O Rio Grande do Sul lança a dívida
com a União em "Empréstimos internos" (R$ 108 bi), por isso a página diz "pelo menos" e não mostra a
divisão estado a estado. Os conjuntos do CKAN com a dívida dos estados por credor
(`estoque-da-divida-de-estados-e-do-distrito-federal`, `saldos-devedores-e-fluxo-de-recebimentos-de-haveres-financeiros-por-mutuario`)
pararam em 2017 e 2019.

### Orçamento (saúde, educação e juros pagos)

Dos arquivos do Explorer (`site/public/data/explorer/<ano>.json`, Portal da Transparência), no build:
valor pago (realizado) da função 10 (saúde), da função 12 (educação) e do grupo de despesa 2 (juros e
encargos da dívida).

## Conferência com o RMD de setembro de 2026

| Número | Planilha (pipeline) | Texto do RMD |
|--------|--------------------|--------------|
| Estoque da DPF | R$ 9.382,95 bi | R$ 9.382,95 bilhões |
| Vence em 12 meses | 19,95% | 19,95% |
| Prazo médio | 4,10 anos | 4,10 anos |
| Custo médio 12 meses | 12,63% a.a. | 12,63% a.a. |
| Instituições financeiras | 31,33% | 31,33% |
| Previdência | 22,41% (R$ 2.025,04 bi) | 22,41% (R$ 2.025,04 bilhões) |
| Fundos | R$ 2.072,57 bi | R$ 2.072,57 bilhões |
| Não residentes | 9,58% | 9,58% |
| Tesouro Direto | 3,09% | 3,09% |
| Seguradoras | 3,26% | 3,26% |
| Taxa flutuante (Selic) | 51,60% | 51,60% |

DBGG em set/2026: 82,95% do PIB (BC). DPF em % do PIB, calculada: 70,0%.

Fatores de variação (aba 2.9): a soma de cada ano bate com a diferença de estoque entre dezembros
(2025: 439,1 + 880,0 = 1.319,0 = 8.635,09 − 7.316,07). De jan/2014 a set/2026, a dívida cresceu
R$ 7,26 tri: R$ 6,34 tri de juros apropriados e R$ 0,93 tri de títulos vendidos além dos pagos.

## Cuidados

- **Duas contas de juros.** Os juros nominais do BC (R$ 868 bi em 2025) contam tudo o que a dívida
  acumulou no ano, pago ou não. O orçamento (grupo 2, R$ 364 bi pagos em 2025) conta o que saiu do caixa,
  e parte dos juros entra lá como amortização ou refinanciamento. A página usa o BC para o custo e cita
  o orçamento, com link para o Explorer.
- **DPF × DBGG.** A DPF (Tesouro) é a dívida do governo federal com o público. A DBGG (BC) soma estados,
  prefeituras e as operações compromissadas do BC: é a usada para comparar países. A página mostra as duas.
- **Saúde e educação** são o gasto federal pago, inclusive o que a União repassa a estados e prefeituras.

## Não usado (e por quê)

- CKAN do Tesouro Transparente, conjunto `estoque-da-divida-publica-federal`: CSV de 12 MB com o estoque
  por título, sem detentores; o anexo do RMD já traz tudo num arquivo só.
- CKAN, `fatores-de-variacao-da-divida-publica-federal`: os mesmos fatores da aba 2.9 do anexo, que
  já usamos.
- Não há conjunto de detentores no CKAN (a busca por "detentores" volta vazia).
