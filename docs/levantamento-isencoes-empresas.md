# Isenções e benefícios fiscais: que empresas recebem

Levantamento de 22/11/2026. Ele parte do galho "o que deixa de entrar" de `/impostos` (ver
[levantamento do caminho dos impostos](levantamento-caminho-impostos.md)). A pergunta: o site já mostra
quanto o governo deixa de cobrar com isenções e regimes especiais (R$ 569 bi da União em 2025, mais
R$ 258 bi de ICMS). Dá para dizer **quais empresas** ficam com esse dinheiro, quanto cada uma recebe, e
cruzar isso com o que o site já tem por CNPJ (contratos, emendas, dívida ativa)?

Dá, para a maior parte do que é federal. Desde 2024 as empresas fora do Simples declaram todo mês, na
**Dirbi**, quanto deixaram de pagar com cada benefício. A Receita publica esses dados com o CNPJ, o
nome e o valor, em arquivos que se baixam sem cadastro. Nos estados, quase nada sai por empresa.

## Antes: "a empresa recebeu" quer dizer duas coisas

O dado diz quem **deixou de recolher** o imposto. Isso nem sempre é quem ficou com o dinheiro:

- **Benefício do produto.** A lei zera o imposto de um produto: carne, café, leite, adubo, defensivo,
  remédio. Quem declara é quem vende. O supermercado que vende carne sem PIS/Cofins aparece como
  "beneficiado", mas parte do desconto vai para o preço que o consumidor paga, e ninguém sabe quanto.
  É a maior parte do valor: **cesta básica, insumos do agro e remédios somam 56% de 2025**.
- **Benefício da empresa.** A empresa precisa de um projeto aprovado, de uma habilitação ou de estar
  num lugar: Zona Franca de Manaus, Sudam e Sudene, Lei do Bem, Perse, Reidi, Padis, subvenção para
  investimento. Aqui o benefício é dela, e a pergunta "por que esta empresa?" faz sentido.

A página precisa separar os dois, senão vira uma lista de supermercados e frigoríficos "que não pagam
imposto", o que não é verdade.

## As fontes

Testado em 22/11/2026. As linhas marcadas "baixado" foram baixadas de verdade, sem cadastro; as
outras foram vistas na página ou na documentação. As federais vêm da Portaria RFB 319/2023
(transparência dos benefícios) e ficam na nuvem da Receita (`arquivos.receitafederal.gov.br`, pastas
públicas lidas por WebDAV, o mesmo jeito que `divida_ativa.py` usa para o cadastro de CNPJ). O
catálogo está em [dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/renuncias-fiscais-de-tributos-federais).

| Fonte | O que cobre | Anos | Formato e lote | Campos | Serve? |
|---|---|---|---|---|---|
| **Dirbi**, renúncia por regime especial (pasta `QsZYAHeegq65LxC`) | Os 173 benefícios do Anexo Único da IN RFB 2.198/2024: PIS/Cofins, IPI, IRPJ, CSLL, INSS patronal, tributos na importação. Empresas fora do Simples que usam benefício | 2024, 2025 e 2026 (até agosto); atualizada em 08/09/2026 | Um zip por ano (2025: 175 MB, CSV de 645 MB, 6,3 milhões de linhas). **Baixado** | CNPJ da matriz, nome, município e UF da matriz, CNAE, mês, código do benefício, tributo, valor | **Sim, a fonte principal.** |
| Dirbi acumulada (mesma pasta) | Igual, uma coluna por benefício | 2024 a 2026 | Planilha de 159 MB. **Baixado** | Traz o **nome** de cada um dos 173 códigos no cabeçalho (os CSVs só trazem o número) | Só para os nomes dos códigos. |
| **ECF**, renúncia de IRPJ e CSLL (`en3AycCdmtiNaSi`) | Benefícios de IRPJ e CSLL declarados na escrituração anual: Sudam/Sudene, Rouanet (Pronac), PAT, fundos da criança e do idoso, Prouni, Perse, Rota 2030, Padis, horário eleitoral | 2015 a 2025; atualizada em 19/09/2026 | CSV, 49 MB, 183 mil linhas. **Baixado** | CNPJ, nome, CNAE, **natureza jurídica**, forma de tributação, uma coluna por benefício | **Sim**, para antes de 2024 e para as doações (Rouanet, PAT, fundos), que a Dirbi não tem. |
| **Importação**, II e IPI (`esY5GgztpRFpetw`) e PIS/Cofins (`StgJtexwrGCsXey`) | Tributo que não se pagou no desembaraço: drawback, Repetro, admissão temporária, entreposto, Zona Franca, isenções por produto | 2015 a 2025; atualizada em 15/12/2025 | Dois CSVs, 26 e 43 MB. **Baixado** | CNPJ do estabelecimento, nome, CNAE, regime (isenção, redução, **suspensão**), fundamento legal, ano, valor | Sim, para antes de 2024. |
| EFD-Contribuições, Perse (`3LwyLKF4jM2xcCJ`) | Receita sem PIS/Cofins no Perse | 2022 e 2023 | CSV, 3 MB, 24 mil linhas. **Baixado** | Raiz do CNPJ, nome, CNAE, receita desonerada | Pouco: é a receita desonerada, não o imposto. |
| Portal da Transparência, [renúncias](https://portaldatransparencia.gov.br/download-de-dados/renuncias) (CGU) | Os mesmos arquivos da Receita, já juntados, mais as listas de imunes e isentas e de habilitadas em regimes especiais | 2015 a 2023 completos; 2024 só a importação | Zip por ano, 3 a 20 MB. **Baixado** | Os mesmos, e um arquivo pronto "por beneficiário" | Só para conferir: parou em novembro de 2024. |
| Empresas habilitadas em regimes especiais | Quem pode usar Reidi, Repetro, Recap, Reporto, Padis, RET, Recof: 26 mil CNPJs (2024) | Desde 2008 | CSV, 11 MB. **Baixado** | CNPJ, regime, início e fim | Para a ficha da empresa ("habilitada no Reidi desde…"), sem valor. |
| Entidades imunes e isentas | 260 mil associações, igrejas, sindicatos, partidos, escolas filantrópicas | 2015 a 2023 | CSV, 45 MB. **Baixado** | CNPJ, nome, tipo, imune ou isenta | Fora do escopo (não são empresas e não trazem valor). |
| [Painel de Benefícios Fiscais](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/beneficios) da Receita (Power BI, maio de 2025) | O mesmo da Dirbi | 2024 em diante | Painel, sem lote | — | Não: os arquivos acima são a mesma coisa. |
| **Portaria RFB 745/2026** (publicada em 16/11/2026) | Manda a Receita publicar por CNPJ, revisando a cada seis meses, mais conjuntos (anexos II a VII: Dirbi, EFD-Contribuições, Sisen, desde 2015). Cria uma subcomissão para isso | — | Ainda sem data | — | **Acompanhar.** Pode trazer o que falta (receita desonerada, benefícios ainda fora da Dirbi). |

**Os programas que o pedido citou** estão todos dentro dessas fontes; nenhum precisa de fonte própria
para o valor:

- **Perse**: código 1 da Dirbi (11.471 empresas, R$ 4,9 bi em 2025) e colunas `perse_irpj` e
  `perse_csll` da ECF (2021 a 2023). O programa acabou em março de 2025.
- **Lei do Bem**: códigos 30 a 43 da Dirbi (R$ 18 bi em 2025, com a lei de informática).
- **Lei Rouanet (Pronac)**: coluna `pronac_deducao_ir` da ECF (R$ 2,0 bi em 2023), por empresa que
  patrocina. O [Salic](https://www.gov.br/leirouanet) diz que projeto cada empresa patrocinou; fica para
  depois.
- **Zona Franca e Suframa**: códigos 28, 44 a 60 e 130 da Dirbi (R$ 65 bi), e a importação para a ZFM.
- **Sudam e Sudene**: códigos 20 e 21 da Dirbi (R$ 27,7 bi) e as colunas `sudam_sudene_*` da ECF.
- **Reidi e Padis**: códigos 3 e 8 da Dirbi (R$ 6,5 bi e R$ 0,6 bi), mais a lista de habilitadas.
- **Desoneração da folha**: código 7 da Dirbi (24.827 empresas, R$ 15 bi).

**Nos estados (ICMS)**, quase nada sai por empresa com valor:

- **Minas Gerais** publicou em junho de 2026, no portal da transparência estadual, 4.101 empresas com
  R$ 19,4 bi de ICMS em 2025 (as 20 maiores com uns 40%). O demonstrativo da Secretaria da Fazenda
  ([Renuncias-2025.xlsx](https://www.fazenda.mg.gov.br/transparencia/renuncias/demonstrativos-das-desoneracoes-2025-exercicio/),
  baixado) só traz o total por tipo; a lista por empresa não foi achada para baixar. **A confirmar.**
- **Rio de Janeiro** (Lei 8.445/2019) e **Espírito Santo** (Compete-ES e Invest-ES, 1.822 empresas)
  publicam quem tem o benefício, sem o valor.
- **São Paulo** não publica: o TJSP mandou divulgar em junho de 2026, e o estado alega sigilo fiscal.
- Os outros estados, até onde se viu, só dão o total na lei de diretrizes orçamentárias. O valor de
  ICMS por empresa não sustenta uma página nacional; Minas pode entrar como exemplo quando a lista
  for achada.

## O que a amostra mostrou (Dirbi, 2025)

O ano de 2025 inteiro, de janeiro a dezembro: **R$ 366,5 bi** de 88.947 empresas (raízes de CNPJ). O
Demonstrativo dos Gastos Tributários dá R$ 569 bi para a União em 2025. A diferença é quase toda o que
não é de empresa fora do Simples: o próprio Simples (R$ 121 bi), as deduções do imposto de renda das
pessoas (despesas médicas, aposentadoria por doença grave) e as entidades filantrópicas. A Dirbi é,
na prática, **a parte das empresas fora do Simples**. Dezembro pesa o dobro dos outros meses (R$ 63 bi)
porque o IRPJ anual entra nele.

Por tributo: Cofins R$ 164 bi, IRPJ R$ 47 bi, PIS R$ 40 bi, Cofins na importação R$ 37 bi, IPI R$ 33 bi,
INSS patronal (a desoneração da folha) R$ 15 bi, imposto de importação R$ 9 bi, PIS na importação
R$ 9 bi, CSLL R$ 8 bi, IPI na importação R$ 5 bi.

### Muito concentrado

| | Empresas | Parte do total |
|---|---:|---:|
| As 10 maiores | 10 | 13% |
| As 44 que passam de R$ 1 bi cada | 44 | 28% (R$ 102 bi) |
| As 100 maiores | 100 | 40% |
| O 1% do topo | 889 | 73% |
| Metade das empresas, cada uma com menos de R$ 100 mil | 45.767 | 0,3% (R$ 1,1 bi) |

A mediana é R$ 90 mil por empresa no ano.

### Por grupo de benefício

O agrupamento foi feito neste levantamento a partir dos nomes dos 173 códigos. Os códigos de cada grupo:
Zona Franca 28, 44 a 60 e 130; Sudam/Sudene 20 e 21; cesta básica 9 a 16, 65, 68 a 90, 115, 116, 158 e
159; agro 22, 23, 63, 64, 66, 67 e 117; remédios e saúde 6, 26, 105 a 112 e 131 a 153; folha 7; inovação 8,
30 a 43 e 173; infraestrutura 2 a 5, 97 a 103, 120, 129 e 169; Perse 1; subvenção 29; doações 156 e 160 a
168 (vazias na Dirbi de 2025: estão na ECF).

| Grupo | Empresas | R$ bi | Parte | As 10 maiores do grupo ficam com | Tipo |
|---|---:|---:|---:|---:|---|
| Cesta básica e alimentos (carne, café, leite, queijo, óleo, arroz e feijão…) | 39.097 | 124,6 | 34% | 17% | produto |
| Insumos do agro (adubo, defensivo, semente) | 15.732 | 65,5 | 18% | 27% | produto |
| Zona Franca e áreas de livre comércio | 2.973 | 65,0 | 18% | **53%** | empresa |
| Sudam e Sudene (IRPJ no Norte e Nordeste) | 1.462 | 27,7 | 8% | 37% | empresa |
| Inovação (Lei do Bem e informática) | 3.470 | 18,4 | 5% | 20% | empresa |
| Desoneração da folha | 24.827 | 15,0 | 4% | 12% | setor |
| Remédios e saúde | 538 | 14,7 | 4% | 44% | produto |
| Outros (aeronaves e peças, químicos, transporte aéreo, Reiq) | 2.825 | 14,8 | 4% | 70% | produto |
| Infraestrutura, petróleo e energia (Reidi, Repetro, Recap, Reporto) | 1.649 | 8,2 | 2% | 25% | empresa |
| Subvenção para investimento | 517 | 7,7 | 2% | **63%** | empresa |
| Perse (eventos e turismo) | 11.471 | 4,9 | 1% | 13% | empresa |

Os benefícios "da empresa" (Zona Franca, Sudam/Sudene, inovação, infraestrutura, subvenção, Perse)
somam uns R$ 132 bi, 36% do total, e são os mais concentrados.

### As maiores

| Empresa | UF da matriz | R$ bi em 2025 | O benefício maior |
|---|---|---:|---|
| Moto Honda da Amazônia | AM | 10,9 | Zona Franca, venda para o resto do país |
| Samsung Eletrônica da Amazônia | AM | 8,4 | Zona Franca, informática e comunicação |
| JBS | SP | 4,8 | Carnes |
| Syngenta | SP | 3,8 | Defensivos |
| Yamaha Motor da Amazônia | AM | 3,7 | Zona Franca |
| Vale | RJ | 3,3 | Sudam/Sudene, redução de 75% do IRPJ |
| *Restrição judicial (15)* | SP | 3,2 | Adubos e fertilizantes |
| LG Electronics | SP | 3,2 | Zona Franca |
| Stellantis | MG | 3,1 | Subvenção para investimento |
| Yara Fertilizantes | RS | 2,8 | Adubos e fertilizantes |

Entre as 100 maiores, o benefício principal é a Zona Franca (17 empresas, R$ 41 bi), carnes (14,
R$ 22 bi), adubos (10, R$ 14 bi), defensivos (10, R$ 14 bi) e Sudam/Sudene (7, R$ 10 bi).

**Três empresas conseguiram na Justiça esconder o nome e o CNPJ.** Elas aparecem como "Restrição
Judicial (1)", "(3)" e "(15)", com o CNPJ em asteriscos: R$ 4,1 bi em 2025. A página tem de mostrar
assim mesmo, e dizer por quê.

### Por estado e setor

Por UF **da matriz**: São Paulo R$ 120 bi (21.435 empresas), Amazonas R$ 60 bi (941), Paraná R$ 29 bi,
Rio Grande do Sul R$ 24 bi, Rio de Janeiro e Minas R$ 24 bi cada, Santa Catarina R$ 17 bi. A Dirbi só
traz a matriz: um frigorífico com sede em São Paulo e fábricas em Mato Grosso conta inteiro em São
Paulo. A própria Fazenda avisa disso na nota da Plataforma de Desonerações. Um mapa por estado ou cidade
**não se sustenta** com esse dado.

Por setor (CNAE principal, dois dígitos): atacado R$ 63 bi, indústria de alimentos R$ 61 bi, química
R$ 33 bi, varejo R$ 31 bi, eletrônicos R$ 24 bi, motos e outros veículos R$ 21 bi. Aqui também vale o
aviso: é a atividade principal da matriz.

### A série (Portal da Transparência, 2015 a 2023)

Antes da Dirbi só havia a importação e o IRPJ e a CSLL da ECF, que somam bem menos:

| Ano | Empresas | R$ bi |
|---|---:|---:|
| 2015 | 20.672 | 75 |
| 2017 | 21.598 | 71 |
| 2019 | 24.293 | 119 |
| 2021 | 27.400 | 205 |
| 2023 | 39.723 | 179 |

A série **não emenda** com 2024 em diante: em 2023 não aparecem a cesta básica, os insumos do agro, a
desoneração da folha nem a Zona Franca fora da importação, que são a maior parte da Dirbi. A página deve
mostrar 2024 em diante e, se mostrar antes, só por benefício (Sudam/Sudene, Rouanet), nunca o total.

A importação tem uma armadilha: boa parte é **suspensão** (drawback, Repetro, admissão temporária,
entreposto), em que o imposto fica parado enquanto o bem é reexportado ou usado num regime. Em 2023, só
"bens em regimes aduaneiros especiais" foram R$ 29 bi. A Receita conta isso como renúncia, mas não é o
mesmo que uma isenção. Na Dirbi a importação entra só pelos benefícios do Anexo Único; dos regimes de
suspensão, só o Repetro está na lista (códigos 98 a 100). Isso ainda precisa ser conferido antes de somar.

## Os cruzamentos com o que o site já tem

As 88.947 empresas da Dirbi 2025, pela raiz do CNPJ:

- **Contratos com o governo (PNCP, 2025)**: 6.600 empresas com benefício também tiveram contrato em
  2025, que somam R$ 115 bi. Essas empresas declararam R$ 91 bi de benefício.
- **Emendas parlamentares (pagamentos de 2024 em diante, favorecido com CNPJ)**: 780 empresas, mas
  quase todo o valor é do Banco do Brasil (R$ 19,5 bi), que aparece porque paga as emendas, não
  porque as recebe. Fora ele, R$ 1 bi, quase tudo compra de veículos e máquinas (Stellantis, Toyota,
  CNH). **Não rende história**; serve só para a ficha.
- **Dívida ativa da União (PGFN, posição de setembro de 2026)**, só o devedor principal (o corresponsável
  repete o mesmo débito, e a página da dívida ativa também não o conta): das 85.305 empresas que podem aparecer
  pelo nome, **26.014 (30%) têm alguma dívida com a União** e declararam R$ 222 bi, 60% do benefício de 2025.
  A dívida delas soma R$ 595 bi, mas quase toda está garantida, parcelada ou suspensa na Justiça. **Em
  cobrança** são R$ 84 bi, de **16.318 empresas (18% do total)**, que declararam R$ 57 bi de benefício (16%).
  4.627 empresas devem mais de R$ 1 mi em cobrança; 129 devem mais de R$ 100 mi. Das 537 que tiveram mais
  de R$ 100 mi de benefício, 33 têm mais de R$ 1 mi em cobrança. A página usa a dívida em cobrança.
- **As três coisas juntas** (benefício em 2025, dívida em cobrança e contrato público em 2025): 575
  empresas, R$ 22 bi de benefício.

(Uma primeira conta, feita antes do pipeline, juntava os corresponsáveis e dava 31% e 61%; os números acima
são os do `beneficios_fiscais.py`.)

O cruzamento com a dívida é o mais forte, e é parecido com o que o TCE-SP apontou em São Paulo (3,3
mil empresas com incentivo de ICMS inscritas na dívida do estado). Mas precisa de cuidado no texto:
dívida em cobrança é o que a PGFN cobra, não uma condenação, e empresa grande quase sempre discute
alguma coisa. A frase certa é "também deve à União", com o valor e a situação, nunca "sonega".

## O que os dados sustentam e o que não sustentam

Sustentam:

- Quais empresas declararam benefício federal em 2024, 2025 e 2026, quanto, em qual benefício e em
  qual tributo, mês a mês.
- A concentração: o 1% do topo fica com 73%; as 100 maiores, com 40%.
- Os benefícios "da empresa" (Zona Franca, Sudam/Sudene, Lei do Bem, Perse, Reidi, subvenção) por
  empresa, que é onde a pergunta "quem recebe" faz mais sentido.
- Os cruzamentos por CNPJ com contratos e dívida ativa.

Não sustentam:

- **Quem fica com o dinheiro** nos benefícios de produto (cesta básica, adubo, remédio): a empresa
  declara, mas parte vai para o preço. A página diz "deixou de recolher", não "ganhou".
- **O lugar**: o estado e a cidade são os da matriz.
- **Somar a Dirbi com a ECF ou com a importação de 2024 em diante** sem antes conferir: a partir de 2024
  o arquivo da ECF cai de R$ 41 bi para R$ 13 bi, sinal de que a Receita tirou dele o que passou para a
  Dirbi. Antes de juntar as doações da ECF (Rouanet, PAT, fundos), é preciso conferir, empresa por
  empresa, se elas não estão na Dirbi.
- **A série longa** de um total só (2015 a 2023 é outra cobertura).
- **O Simples Nacional** (R$ 121 bi, o maior benefício do DGT) e o que é de pessoa física: não estão em
  nenhum arquivo por empresa, e não devem estar.
- **O ICMS por empresa**, fora Minas.
- **Se o benefício valeu a pena** (empregos, investimento). Nenhum dado aqui diz isso.
- **O valor é o que a empresa declarou.** A Receita confere depois; um valor errado pode ser
  corrigido a pedido da empresa (está na Portaria 745/2026).

## Privacidade

- Os arquivos não trazem CPF. Trazem a raiz ou o CNPJ completo da empresa.
- Mas **empresário individual e MEI são pessoas**: o nome deles costuma ser o nome da pessoa, às vezes
  com o CPF no fim. Na Dirbi 2025 há 98 nomes com um número de 11 dígitos (R$ 4 mi) e, entre as que
  aparecem na ECF, 328 empresas com natureza jurídica 213-5 (R$ 0,23 bi). 70 mil empresas da Dirbi não
  estão na ECF e precisam da natureza jurídica do cadastro de CNPJ, que `divida_ativa.py` já lê.
- Regra igual à da dívida ativa: natureza 213-5 (empresário individual, incluindo MEI) entra só nos
  totais, nunca pelo nome; um nome com 11 dígitos também não sai. O mesmo vale para os nomes em
  "Restrição Judicial", que já vêm escondidos.

## A proposta

### Onde entra

1. **Página própria**, no grupo "Impostos" do menu: `/impostos/empresas` (título "Quem deixa de pagar
   imposto"). O galho "o que deixa de entrar" de `/impostos` ganha um link "veja que empresas são".
2. **Na ficha da empresa** que o explorador de contratos e o de emendas já abrem pelo CNPJ: um bloco
   "Benefícios fiscais" com o total do ano, os benefícios principais e a habilitação em regimes
   especiais. É a mesma ficha que, juntando contratos, emendas, dívida ativa e benefício, responde à
   pergunta do pedido.
3. Nada no mapa (o lugar é o da matriz).

### A página, de cima para baixo

1. **O número**: R$ 366 bi em 2025, de 89 mil empresas; metade delas recebe menos de R$ 100 mil, e as
   100 maiores ficam com 40%. Um gráfico de concentração (as 10, as 100 e as 1.000 maiores contra o
   resto).
2. **"Dois tipos de benefício"**, com um exemplo de cada: a carne sem PIS/Cofins no supermercado (do
   produto) e a fábrica de motos na Zona Franca (da empresa).
3. **Os grupos** em barras, separados por tipo. Clicar num grupo abre as maiores empresas dele.
4. **As maiores**: tabela com nome, estado da matriz, setor, valor e benefício principal, com filtro por
   grupo, estado e setor, e marcas "também deve à União" e "tem contrato público".
5. **Busca por empresa** (nome ou CNPJ), que abre a ficha.
6. **Os avisos**: valor declarado pela empresa, estado da matriz, as três com restrição judicial, o
   Simples fora, os estados sem dado.

Seguindo o combinado, o mock vem antes do código, no Claude Design.

### O pipeline (quando for implementar)

Um `beneficios_fiscais.py`, no jeito do `divida_ativa.py`:

- Baixa a Dirbi de cada ano pela pasta pública da Receita (WebDAV) e lê o nome dos 173 códigos do
  cabeçalho da planilha acumulada (ou fixa a tabela no programa, com a fonte).
- Agrega por raiz de CNPJ, ano e código. 2025 dá 402 mil linhas, um parquet de 7 MB; os três anos ficam
  perto de 20 MB, no bucket (com o OK de cada envio).
- Aplica a regra de privacidade com a natureza jurídica do cadastro de CNPJ.
- Gera um JSON pequeno para a página (totais, grupos, as mil maiores) e o parquet por empresa para a
  ficha e a busca, como os contratos e as emendas.
- Junta a dívida ativa pela raiz do CNPJ, com o mesmo arquivo da PGFN que `divida_ativa.py` já baixa.

## Em aberto

- Página própria, só a ficha da empresa, ou as duas?
- Mostrar os benefícios de produto (cesta básica, adubo) com nome de empresa, ou só somados por
  benefício, com nome apenas nos benefícios "da empresa"?
- Entrar com o cruzamento da dívida ativa já na primeira versão?
- Ir atrás da lista de Minas por empresa (e do Salic, para a Rouanet por projeto)?
- Acompanhar o que a Portaria 745/2026 vai publicar nos próximos seis meses.

## O que foi implementado (22/11/2026)

- `pipeline/src/orcamento_pipeline/beneficios_fiscais.py` (`uv run beneficios-fiscais`): baixa a Dirbi de cada ano, lê a
  natureza jurídica no cadastro de CNPJ (para não nomear empresário individual nem MEI), soma a dívida ativa pelo devedor
  principal e junta os contratos do PNCP e as emendas pagas a empresas (sem o Banco do Brasil e a Caixa, que só pagam).
  Os grupos e os nomes dos 173 códigos ficam fixos no programa. Testes em `pipeline/tests/test_beneficios_fiscais.py`.
- Saídas: `data/publico/beneficios-fiscais-empresas.parquet` (5 MB, uma linha por empresa) e
  `beneficios-fiscais-por-cnpj.parquet` (8 MB, empresa × ano × benefício), que vão para o bucket; e o resumo
  `site/public/data/beneficios-fiscais/resumo.json`, com cópia em `pipeline/referencia/beneficios-fiscais.json`. A
  publicação automática só copia o resumo (`--sem-baixar`); a carga é à mão, a cada atualização semestral da Dirbi.
- A página `/impostos/empresas` (menu "Impostos" › "Quem deixa de pagar"), com a busca e a ficha de cada empresa
  (`?empresa=raiz do CNPJ`) consultando os Parquet no navegador. A ficha da empresa em `/contratos` ganha uma linha com o
  benefício e o link. O galho "o que deixa de entrar" de `/impostos` ganha a nota "Que empresas são essas".
- A Dirbi de 2026 vai até junho (a atualização de setembro); a página trata o ano como incompleto.
