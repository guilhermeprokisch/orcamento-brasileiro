# Saiu daqui, voltou: levantamento

Novembro de 2026, para o pedaço que falta do bloco 2 do [plano](plano-de-melhorias.md) ("O caminho dos impostos").
A pergunta: **quanto saiu de cada cidade e de cada estado em impostos federais, e quanto voltou da União?**

Todos os números abaixo saíram dos arquivos que o site já publica (`site/public/data/`), mais o PIB dos municípios
do IBGE, que o site ainda não usava. Ano: **2025**, o último fechado em todas as peças.

## O que o site já tem

| Peça | Arquivo do site | Comando | Anos | Cobertura | Lado |
|---|---|---|---|---|---|
| Imposto federal recolhido em cada cidade (Receita Federal, DARF e GPS, inclusive o INSS), #19 | `mapa/rfb-mun/{ano}.json` | `uv run rfb` | 2013 a 2025 | 5.570 cidades. Soma R$ 2.759 bi em 2025, o total do país | saiu |
| Imposto de renda pago por pessoas físicas, pela cidade de quem paga (declaração, carnê-leão) | mesmo arquivo, 2ª coluna | `uv run rfb` | 2013 a 2025 | 5.570 cidades. R$ 80 bi em 2025 | saiu (parte) |
| Imposto de renda pela cidade onde a pessoa **mora** (Grandes Números do IRPF), #27 e #30 | `mapa/irpf-res.json` | `uv run irpf` | 2022 a 2024 (ano dos rendimentos) | 5.570 cidades. R$ 349 bi em 2024 | saiu (parte) |
| Arrecadação federal por estado | `mapa/rfb.json` | `uv run mapa` | 2023 a 2025 | 27 UFs | saiu |
| Repasses da União à prefeitura, por programa (FPM, SUS, Fundeb, royalties, educação, assistência, outros) e a outras entidades da cidade | `mapa/federal-2025.json` (`mun`) | `uv run federal 2025` | **só 2025** | 5.570 cidades. R$ 475 bi à prefeitura, R$ 23 bi a outras entidades | voltou |
| Repasses da União ao governo do estado, pelos mesmos programas (FPE no lugar do FPM) | `mapa/federal-2025.json` (`uf`) | `uv run federal 2025` | só 2025 | 27 UFs. R$ 300 bi | voltou (estado) |
| Bolsa Família e BPC pagos às pessoas, pela cidade de quem recebe | `mapa/federal-2025.json` | `uv run federal 2025 --beneficios` (zips baixados à mão) | só 2025, 12 meses | 5.570 cidades. R$ 155 bi e R$ 116 bi | voltou |
| Aposentadorias, pensões e auxílios do INSS, pela cidade da agência que paga | `mapa/inss/{ano}.json` | `uv run inss` | 2013 a 2025 | 5.570 cidades. R$ 842 bi em 2025 (valor líquido) | voltou |
| Gasto que a União faz ela mesma (salários, custeio e obras dos órgãos federais), pela cidade da unidade que paga, #80 | `federal/gasto-direto.json` | `uv run gasto-federal 2025` | só 2025 | 591 cidades com unidade federal. R$ 339 bi, metade registrada em Brasília ([levantamento](levantamento-gasto-federal-direto.md)) | voltou |
| Emendas parlamentares pagas, pela cidade de quem recebeu, #38 | `indicadores/emendas.json` | `uv run emendas` | 2016 a 2026 | 5.487 cidades com emenda em 2025. R$ 43 bi | voltou (já dentro dos repasses) |
| Dívida ativa da União (o que pessoas e empresas devem ao governo federal), #113 | `divida-ativa/divida-ativa.json` | `uv run divida-ativa` | posição de 09/2026 | 5.570 cidades. R$ 3,6 tri de estoque | nenhum dos dois (ver abaixo) |

O mapa já faz a conta "de cada R$ 100 que saem, voltam R$ X" (medida `volta` em `site/src/mapa/pagina.html`):
repasses + benefícios + INSS + gasto direto, divididos pelo imposto recolhido pela Receita. Só para cidades e só
com o imposto medido na sede. As páginas de cidade e de estado mostram cada peça em separado (grupo "O que chega e o
que sai daqui"), mas não a conta.

## O que falta e onde existe

- **PIB de cada cidade** (IBGE, Contas Regionais, tabela SIDRA 5938, variável 37). Último ano: 2023. API aberta, sem
  cadastro: `https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/2023`. Serve para estimar quanto imposto
  federal foi **gerado** em cada cidade (ver "A conta"). Novo comando no pipeline.
- **As três parcelas extras de 1% do FPM** (julho, setembro, dezembro): o Portal não as mostra
  ([conciliação](conciliacao-federal.md)). São cerca de R$ 25 bi, 1% do que volta. A prefeitura as declara na DCA.
- **Seguro-desemprego e abono salarial** (R$ 90 bi, FAT): não há arquivo aberto por cidade. O Portal tem por cidade só
  o seguro-defeso e o Garantia-Safra, que são pequenos.
- **Aposentadorias de servidores federais civis e militares** (R$ 158 bi): sem cidade em nenhuma fonte aberta.
- **Salário dos servidores federais pela cidade onde trabalham**: o gasto direto registra na cidade da unidade que
  paga, e boa parte da folha é paga de Brasília. Daria para corrigir com o SIORG (ver o levantamento do gasto direto).
- **O INSS pela cidade onde a pessoa mora**: o Ministério da Previdência publica pela cidade da agência que paga. Não
  achamos a série por residência em arquivo aberto (o Anuário Estatístico da Previdência dá por estado).
- **Justiça Federal, do Trabalho, Ministério Público da União, Câmara e Senado**: fora do arquivo do gasto direto.

## A conta

### O que volta (medido)

Para uma **cidade**, em 2025:

    repasses à prefeitura (FPM, SUS, Fundeb, royalties, educação, assistência, outros)
    + repasses a outras entidades da cidade
    + Bolsa Família + BPC + INSS
    + gasto dos órgãos federais na cidade

Para um **estado**: a soma das cidades do estado + os repasses ao governo do estado (FPE, SUS, Fundeb…).

Para **não contar duas vezes**:

- As **emendas** já estão dentro dos repasses: são pagas como transferência à prefeitura ou à entidade. Conferido
  cidade a cidade: em 5.486 das 5.487 cidades com emenda em 2025, o que foi para a prefeitura e para entidades é menor
  que os repasses. Elas aparecem como "deste total, R$ X foram emendas", nunca somadas.
- O **Fundeb** do Portal é a complementação da União mais a parte do fundo formada por impostos federais (os 20%
  retidos do FPM e do FPE), e o FPM vem sem esses 20%. Somar os dois não conta duas vezes. A parte do Fundeb que vem
  do ICMS e do IPVA é dinheiro do estado e não entra.
- O **BPC** vem do Portal; o arquivo do INSS usa só os benefícios previdenciários, sem o BPC.
- O **gasto direto** é só a aplicação direta (modalidade 90) em salários, custeio e obras. Os repasses (modalidades 30
  a 50) já estão nos repasses; benefícios a pessoas e aposentadorias de servidores ficam de fora.
- A **dívida ativa** não é fluxo do ano: é o estoque do que deixou de ser pago desde sempre. Fica fora da conta. Pode
  aparecer ao lado, como "o que deveria ter saído e não saiu".

### O que saiu (medido e estimado)

**Medido**: o que a Receita Federal recolheu na cidade (`rfb-mun`). É o número oficial, mas mostra onde o imposto foi
**recolhido**, não onde foi **gerado**:

- a empresa recolhe na cidade da sede o imposto de todas as filiais, e também o imposto e o INSS descontados do
  salário de quem trabalha em outra cidade;
- os impostos embutidos nos preços (PIS/Cofins, IPI) são recolhidos pela fábrica ou pelo distribuidor, não onde a
  pessoa compra;
- o governo federal recolhe em Brasília o imposto de renda e o INSS descontados de todos os servidores federais.

O tamanho disso: São Paulo, Rio e Brasília recolhem R$ 1.411 bi, 51% do imposto federal do país, e têm 17% do PIB.
Barueri (SP), com 343 mil moradores, recolhe R$ 32 bi. Na cidade do meio da lista, o imposto recolhido é só um quarto
do que seria se seguisse o PIB.

**Estimado**: a parte da cidade no PIB do país (2023) vezes o imposto federal do país (2025). É o "se cada real de
riqueza produzida aqui pagasse a média de imposto federal do país". Tem dois defeitos, ditos no site: o imposto
federal não é igual em todo lugar (renda alta paga mais imposto de renda; a economia informal paga menos), e o PIB
também é registrado onde está a empresa, só que pelo estabelecimento, não pela sede. Por isso as duas medidas vão
juntas, como os dois extremos.

### O que nunca volta para uma cidade

Em 2025, de R$ 2.759 bi em impostos federais:

| Para onde foi | R$ bi | De cada R$ 100 |
|---|---:|---:|
| Voltou a alguma cidade (repasses, benefícios, INSS, gasto direto; em Brasília, o GDF e o Fundo Constitucional do DF) | 1.755 | 64 |
| Voltou aos governos estaduais (FPE e outros) | 296 | 11 |
| Gasto dos órgãos federais registrado em Brasília, que atende o país inteiro, e a folha militar paga do Rio | 174 | 6 |
| Sem cidade: aposentadorias de servidores federais, seguro-desemprego e abono, juros da dívida, subsídios (Plano Safra), Judiciário e Legislativo federais, unidades no exterior | o resto | 19 |

Os juros da dívida não "usam" o imposto diretamente: o governo federal gasta mais do que arrecada e cobre a diferença
com empréstimos. Por isso o "resto" não é a conta dos juros, e sim o que não dá para pôr numa cidade.

### Quanto volta, no país

A média do país (R$ 64 de cada R$ 100 voltam a alguma cidade) é a régua: uma cidade que recebe R$ 64 de cada R$ 100
está na média, não "perdendo". Pelo imposto **recolhido**, a cidade do meio da lista recebe R$ 510 de cada R$ 100;
pelo **estimado**, R$ 121. As duas medidas somam o mesmo total no país. Pelo estimado, em 2.295 das 5.510 cidades com
PIB volta menos do que sai; pelo recolhido, só em 438.

### Casos especiais

- **Brasília**: R$ 170 bi de gasto direto registrado ali são de órgãos que atendem o país inteiro, e o imposto
  recolhido ali (R$ 603 bi) inclui o descontado dos servidores federais de todo o Brasil. O gasto direto fica fora da
  conta do DF e aparece à parte, menos o Fundo Constitucional do DF (R$ 13 bi), que paga a polícia e parte da saúde e
  da educação de lá e entra. O DF entra também com os repasses ao GDF (como estado), os benefícios e o INSS: R$ 12.400
  por morador, R$ 6 de cada R$ 100 recolhidos ali, R$ 39 de cada R$ 100 pelo estimado.
- **Rio de Janeiro**: tira-se do gasto direto a folha da Marinha e da Aeronáutica paga dali para o país todo
  (R$ 17 bi, coluna `folha_central`).
- **INSS**: registrado na cidade da agência que paga. Cidades sem agência aparecem com menos; as cidades-polo, com mais.

### O ano em comum

2025 em tudo que entra na conta: imposto recolhido, repasses, Bolsa Família, BPC, INSS e gasto direto. O PIB é de
2023 (o último publicado), mas só entra como peso, a parte de cada cidade no total do país. O imposto de renda por
cidade onde a pessoa mora (2024) não entra na conta; pode aparecer ao lado, como a parte que mais se aproxima do que
os moradores pagam.

O arquivo federal (`federal-2025.json`) só existe para 2025. A seção fica presa a 2025 e não muda com o "Ano das
contas" da página, como o gasto direto.

## Exemplos (2025, por morador)

| Cidade | Moradores | Saiu, recolhido aqui | Saiu, estimado pelo PIB | Voltou | De cada R$ 100 (recolhido) | De cada R$ 100 (estimado) |
|---|---:|---:|---:|---:|---:|---:|
| São Paulo (SP) | 12,2 mi | R$ 45.692 | R$ 22.043 | R$ 7.607 | R$ 17 | R$ 35 |
| Barueri (SP) | 343 mil | R$ 93.269 | R$ 52.714 | R$ 6.321 | R$ 7 | R$ 12 |
| Uberlândia (MG) | 726 mil | R$ 19.578 | R$ 17.742 | R$ 7.712 | R$ 39 | R$ 43 |
| Nova Iguaçu (RJ) | 819 mil | R$ 1.745 | R$ 6.314 | R$ 5.525 | R$ 317 | R$ 87 |
| Picuí (PB) | 18 mil | R$ 1.674 | R$ 3.711 | R$ 11.636 | R$ 695 | R$ 314 |

Estados: São Paulo, R$ 37 (recolhido) ou R$ 41 (estimado) de cada R$ 100; Piauí, R$ 504 ou R$ 220.

## Fontes

- Receita Federal, arrecadação por município: ver `pipeline/src/orcamento_pipeline/rfb.py`.
- Portal da Transparência (CGU), transferências, Bolsa Família e BPC: `federal.py`.
- Ministério da Previdência, estatísticas municipais: `inss.py`.
- Portal da Transparência, execução da despesa, e Compras.gov.br: `gasto_federal.py`.
- CGU, emendas parlamentares: `emendas.py`.
- IBGE, PIB dos Municípios 2023 (SIDRA 5938): `saiu_voltou.py`, que guarda uma cópia em `pipeline/referencia/pib-municipios.json`.

## O que o site mostra

Comando: `uv run --project pipeline saiu-voltou` (no fim de `.github/scripts/dados.sh`, depois das quatro filas, porque
lê o que elas gravam). Saída: `site/public/data/federal/saiu-voltou.json`, com cópia em `pipeline/referencia/`.

- Páginas de cidade e de estado, primeiro bloco do grupo "O que chega e o que sai daqui": "de cada R$ 100 que saíram,
  voltaram entre R$ X e R$ Y" (recolhido e estimado), o que saiu e o que voltou por morador, as partes do que voltou,
  as emendas dentro do total e o quadro "O que esta conta não diz". Para um estado, a régua do país inclui os repasses
  aos governos estaduais (R$ 74 de cada R$ 100).
- /impostos, no fim de "Siga o seu imposto": "E na sua cidade?", com a busca de cidades e um atalho para cada estado.
- O mapa fica como está (a medida "de cada R$ 100" de lá usa só o imposto recolhido).
