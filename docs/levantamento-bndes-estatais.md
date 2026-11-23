# BNDES, crédito subsidiado e estatais: o que os dados dizem

Levantamento de 23/11/2026, para o item "Estatais e crédito subsidiado (BNDES, Plano Safra)" de
[plano-de-melhorias.md](plano-de-melhorias.md). Quatro perguntas:

1. **Quem recebe empréstimo do BNDES**: por empresa e por cidade, quanto, para quê, e se o juro foi
   abaixo do de mercado.
2. **Quanto custa o subsídio** para o Tesouro (subsídios de crédito, Plano Safra, equalização de juros).
3. **As estatais federais**: quanto o Tesouro põe nas que vivem do orçamento e quanto as outras devolvem
   em dividendos.
4. **Ligação com /impostos/empresas**: a mesma empresa pode ter isenção e crédito barato.

## Antes: três avisos que a página precisa dar

- **Empréstimo não é doação.** O dinheiro volta com juros. O que custa ao Tesouro é o **subsídio**: a
  diferença entre o juro cobrado e o que o próprio governo paga para se financiar. Somar o valor
  emprestado como se fosse gasto está errado. A exceção é o apoio **não reembolsável** (Fundo Amazônia,
  Fundo Social), que é doação mesmo e aparece à parte.
- **O valor contratado não é o valor liberado.** O arquivo de operações traz quanto foi contratado em
  cada ano; o dinheiro sai aos poucos (desembolso), às vezes em vários anos, às vezes nunca inteiro.
- **Nas operações indiretas, o BNDES empresta a um banco** (Itaú, Bradesco, BB, cooperativas, bancos de
  montadora), que empresta ao cliente e fica com o risco. O cliente escolhe o banco, não o BNDES.

## As fontes do BNDES

Portal de dados abertos (CKAN): `https://dadosabertos.bndes.gov.br`, conjunto
[operacoes-financiamento](https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento), atualizado
em 11/11/2026. Baixado sem cadastro, os dois arquivos em CSV separados por `;`, em Windows-1252 (o DuckDB
recusa abrir como latin-1; converter antes com `iconv -c -f cp1252`).

| Arquivo | O que cobre | Anos | Tamanho | Linhas | Cidade (IBGE) | Documento do cliente |
|---|---|---|---:|---:|---|---|
| **Operações não automáticas** (`operacoes-financiamento-operacoes-nao-automaticas.csv`) | Diretas (o BNDES empresta ao cliente) e indiretas não automáticas (o banco repassa, mas o BNDES analisa o projeto). Inclui o não reembolsável | 02/01/2002 a 30/09/2026 | 20 MB | 24.035 | `municipio_codigo`, 7 dígitos, **onde fica o projeto**; 9999999 ou 0 quando é "diversos" ou "sem município" | **CNPJ completo** |
| **Operações indiretas automáticas** (`operacoes-financiamento-operacoes-indiretas-automaticas.csv`) | O banco aprova sozinho dentro das regras do BNDES: Finame (máquinas, caminhões, ônibus), BNDES Automático (capital de giro, PME), crédito rural | 02/01/2002 a 30/09/2026 | **1,21 GB** | 2.398.240 | `municipio_codigo`, 7 dígitos, **todas as linhas de 2025 têm cidade** | **Mascarado**: `**.*99.999/9999-**`, só 9 dos 14 dígitos |

O servidor corta o download do arquivo grande no meio sem dar erro (veio com 1,08 GB, parando em
dezembro de 2022). O pipeline tem de conferir o tamanho e retomar com `curl -C -` (ou `Range`).

Campos que servem (os dois arquivos têm quase os mesmos): cliente, CNPJ, UF, município e código,
data da contratação, valor contratado, valor desembolsado, **fonte do dinheiro** (FAT, Tesouro, Fundo
Clima, Fundo da Marinha Mercante, FUST, recursos próprios), **custo financeiro** (TJLP, TLP, Selic, taxa
fixa, TR, IPCA, dólar), **juros** (o spread do BNDES, em % ao ano), carência e prazo, modalidade
(reembolsável ou não), forma (direta ou indireta), produto e programa (Finem, Finame, Fundo Clima, Mais
Inovação, Pronaf…), setor (CNAE e o setor do BNDES), porte, natureza (privada, pública, governo
estadual ou municipal), o banco que repassou e a situação (ativo ou liquidado). Os não automáticos
trazem ainda a descrição do projeto e o tipo de garantia.

Outros conjuntos do mesmo portal que podem ajudar:

| Conjunto | O que tem | Serve? |
|---|---|---|
| `desembolsos` (estatísticas por mês) | Quanto saiu por mês desde 1995, por porte (com **pessoa física** à parte), setor, UF, produto e banco | **Sim**, para o total do ano e para dizer o que fica fora das operações |
| `distribuicao-dividendos-juros` | Dividendos e JCP que o BNDES pagou ao Tesouro desde 2000 | Sim, para a parte das estatais |
| `operacoes-equalizadas` | Resultado agregado do BNDES com as operações equalizadas | Pouco: 1 KB, sem operação |
| `tesouro-nacional` | Empresas que receberam dinheiro dos empréstimos do Tesouro (leis de 2009 a 2014) | Para a história do PSI, depois |
| `captacoes-devolucoes-tesouro`, `saldos-contabeis-repasses-tesouro` | O que o BNDES deve e devolveu ao Tesouro | Para uma frase: o BNDES já devolveu antecipado o grosso |

### Quanto foi contratado

R$ bilhões, valor contratado no ano, somando os dois arquivos:

| Ano | Diretas e não automáticas | Indiretas automáticas | Total |
|---|---:|---:|---:|
| 2019 | 29,5 | 11,0 | 40,5 |
| 2020 | 37,6 | 16,5 | 54,1 |
| 2021 | 34,8 | 18,1 | 52,9 |
| 2022 | 47,2 | 34,0 | 81,2 |
| 2023 | 43,9 | 34,0 | 77,9 |
| 2024 | 94,5 | 46,3 | 140,8 |
| 2025 | 73,5 | 54,1 | **127,6** |
| 2026 (até setembro) | 40,5 | 57,7 | 98,2 |

Os picos antigos ficam em 2010 a 2014 (até R$ 193 bi em 2013, só nas diretas e não automáticas, e
R$ 70 bi nas automáticas): é a época dos empréstimos do Tesouro ao BNDES (PSI).

**Pelas estatísticas de desembolso, saíram R$ 169,7 bi em 2025**, dos quais **R$ 33,6 bi para pessoas
físicas** (quase tudo crédito rural). Nos arquivos de operação, o agro inteiro de 2025 soma só R$ 4,4 bi.
Ou seja: **o crédito rural para pessoa física quase não está nos arquivos de operação.** A página deve
dizer isso e mostrar o total de pessoas físicas só pela estatística de desembolso, por ano e por UF.

### O juro: abaixo do mercado ou não

O campo `custo_financeiro` diz a base do juro; o BNDES soma o spread dele (campo `juros`, em 2025 quase
sempre entre 1% e 3% ao ano). A classificação proposta, para a página:

| Grupo na página | Custos | Por quê |
|---|---|---|
| **Juro abaixo do de mercado** | TJLP, taxa fixa, TR | A TJLP é fixada pelo governo abaixo do custo do Tesouro (foi trocada pela TLP em 2018; quase não há contrato novo). Taxa fixa e TR são as linhas com dinheiro de fundo (Fundo Clima, FUST, FNDCT) ou com equalização do Tesouro (Pronaf, PCA, Brasil Soberano, Mais Inovação) |
| **TLP** | TLP | Segue o juro do título do Tesouro corrigido pela inflação (NTN-B). Foi criada para acabar com o subsídio da TJLP; o prazo longo ainda é uma vantagem, mas o Tesouro não paga a diferença |
| **Juro de mercado** | Selic, CDI, IPCA, dólar ou cesta de moedas | O cliente paga o mesmo que pagaria a um banco (a moeda estrangeira é do Fundo da Marinha Mercante e de captações externas) |
| **Doação** (não reembolsável) | sem custo | Não volta. Fundo Amazônia, Fundo Social, cultura |

| R$ bi contratados | 2022 | 2023 | 2024 | 2025 | 2026 (até set.) |
|---|---:|---:|---:|---:|---:|
| Juro abaixo do de mercado | 14,8 | 19,6 | 49,2 | **38,7** | 60,5 |
| TLP | 47,1 | 41,8 | 65,9 | **62,5** | 28,3 |
| Juro de mercado | 18,8 | 16,2 | 24,2 | **23,9** | 8,4 |
| Doação | 0,6 | 0,3 | 1,5 | **2,6** | 1,0 |

Em 2025, o juro abaixo do de mercado veio de: Fundo Clima R$ 8,9 bi, Brasil Soberano (tarifaço) R$ 6,1
bi, ônibus e caminhões R$ 5,9 bi, Mais Inovação R$ 6,1 bi (TR e taxa fixa), capital de giro de pequenas e
médias R$ 3,2 bi, armazéns R$ 1,0 bi, FUST R$ 1,3 bi, saneamento R$ 0,6 bi, Pronaf R$ 0,5 bi.

**O que a classificação não diz:** quanto custou, em reais, cada contrato. Para isso seria preciso a taxa
do Tesouro no dia, o prazo e o fluxo de pagamento de cada um. O custo vem do Tesouro e da SPE, somado
por programa (ver mais abaixo). A página mostra "quanto foi com juro abaixo do de mercado", nunca "quanto
de subsídio esta empresa recebeu".

### Quem recebe

**As maiores de 2025** (contratado no ano):

| Cliente | Forma | R$ bi | Para quê | Juro |
|---|---|---:|---|---|
| EPR Iguaçu | direta | 9,2 | Rodovias no Paraná | TLP |
| EcoRioMinas | direta | 7,3 | Rodovias Rio–Minas | TLP |
| Concessionária de Rodovias Noroeste Paulista | direta | 5,7 | Rodovias | TLP |
| Bloco de Onze Aeroportos do Brasil | direta | 4,6 | Aeroportos | TLP |
| Starnav Serviços Marítimos | direta | 2,5 | Barcos de apoio (Marinha Mercante) | dólar |
| Rumo | direta | 2,5 | Ferrovia e inovação | misto |
| Bram Offshore | direta | 2,2 | Barcos de apoio (Marinha Mercante) | dólar |
| Corsan | direta | 2,0 | Saneamento (debêntures) | misto |
| Eldorado Brasil Celulose | direta | 1,1 | Ferrovia e hidrovia | mercado |
| Ibama | direta | 0,8 | **Doação do Fundo Amazônia** | — |
| Suzano | direta | 0,8 | Fundo Clima | misto |
| Transmaroni Transportes | indireta | 0,7 | Caminhões (Finame) | TLP e taxa fixa |

De 2023 a 2025, os maiores somados: CCR RioSP (rodovia Dutra), R$ 10,8 bi; Estado de São Paulo, R$ 9,7 bi;
EPR Iguaçu, R$ 9,2 bi; EcoRioMinas, R$ 7,3 bi; EPR Litoral Pioneiro, R$ 6,4 bi. **Governos também tomam**:
estados, prefeituras e a União somaram R$ 28,5 bi de 2020 a 2025 nas diretas (São Paulo estado e cidade,
Mato Grosso do Sul, Ceará, Pará). A Petrobras, que tomou R$ 19,4 bi só em 2009, não tem contrato novo desde 2018.

**Muito concentrado nas diretas**: em 2025, 334 clientes diretos somaram R$ 73,5 bi. Nas indiretas, 43,9
mil clientes somaram R$ 54,1 bi, o maior com R$ 0,7 bi; o teto do Finame/Automático por empresa no ano
aparece muito (R$ 150 mi).

**Por cidade**: em 2025, 3.341 cidades tiveram ao menos uma operação; a mediana é R$ 1,5 mi por cidade.
As maiores: São Paulo R$ 5,0 bi (1.009 operações), Itajaí R$ 2,8 bi, Belo Horizonte R$ 1,8 bi, Curitiba
R$ 1,6 bi. **João Pessoa**: 100 operações, R$ 117 mi (Copobras, embalagens, R$ 34 mi; locadoras e
transportadoras comprando ônibus e caminhões).

Mas **R$ 53,6 bi das diretas de 2025 (73%) não têm cidade**: rodovias, aeroportos e debêntures que passam
por várias cidades vêm como "diversos" ou "sem município", com o código 9999999 ou 0. A página da cidade
mostra só o que tem cidade e avisa disso; a página do estado pode somar o que tem UF.

O município das diretas é **onde está o projeto**; o das indiretas é o do cliente (o mais comum é a sede).

### Privacidade

- **Diretas**: o CNPJ vem inteiro e o cliente é empresa ou governo. Todas as linhas têm 14 dígitos.
- **Indiretas**: o documento vem mascarado. **Há pessoas físicas pelo nome** (em 2023 a 2025, uns 16 mil
  contratos e R$ 4,5 bi com nome de gente) e **6.070 linhas com um número de 11 dígitos no nome**, o
  jeito do empresário individual e do MEI: um CPF.
- Regra proposta: **só aparece pelo nome quem bater com uma empresa do cadastro de CNPJ da Receita**
  (nome igual e os 9 dígitos visíveis iguais), e que não seja empresário individual nem MEI (natureza
  213-5), como já faz `beneficios_fiscais.py`. Todo o resto entra só nos totais, como "outros clientes,
  inclusive pessoas". Nenhum arquivo publicado guarda o campo `cpf_cnpj` das indiretas; guarda a raiz
  do CNPJ achada no cadastro.
- Antes de 2011, nas indiretas, o nome do cliente pessoa física foi trocado pelo nome do banco. Essas
  linhas entram só no total.

## Ligação com os benefícios fiscais (/impostos/empresas)

Pela raiz do CNPJ, com o `beneficios-fiscais-empresas.parquet` (Dirbi 2024 e 2025):

- **Diretas, 2024 e 2025**: das 518 empresas privadas que tomaram empréstimo direto, **286 declararam
  benefício fiscal maior que zero** em 2024 ou 2025. Elas ficam com R$ 113,6 bi dos R$ 143,2 bi emprestados
  (79%). (Uma primeira conta dava 316 e 85%, porque contava também as que aparecem na Dirbi com valor zero.)
- **Indiretas, 2025**: com nome e dígitos visíveis, 3.857 clientes batem com a Dirbi; são R$ 27,7 bi dos
  R$ 54,1 bi (51%). A Dirbi não tem as empresas do Simples, que são a maioria dos clientes pequenos.
- As que mais têm as duas coisas (benefício 2024+2025 e BNDES direto 2024+2025): Stellantis (R$ 6,4 bi
  de benefício, R$ 0,2 bi de BNDES), Coamo (2,6 e 0,6), Laticínios Bela Vista (1,5 e 0,7), Eurofarma (1,4 e
  0,5), Suzano (1,3 e 4,3), Aché (1,3 e 0,4), Três Tentos (1,1 e 0,6).

Dá para pôr o BNDES na ficha da empresa de /impostos/empresas (uma linha "Empréstimos do BNDES: R$ X
contratados desde 2020, Y% com juro abaixo do de mercado") e, na página do BNDES, a coluna "também tem
benefício fiscal".

## Quanto custa o subsídio

Duas contas diferentes, que **não se somam**:

- **O custo estimado** (Orçamento de Subsídios da União, OSU): para os subsídios de crédito, é a diferença
  entre o juro cobrado e o que o Tesouro paga para se financiar, calculada pelo governo. Não é dinheiro que
  saiu no ano.
- **O que foi pago** (Resultado do Tesouro Nacional, RTN, e Portal da Transparência): a equalização de
  juros, que é o Tesouro pagando ao banco a diferença entre o juro do Plano Safra e o juro de mercado.

| Fonte | URL | Anos | Formato | Cidade | Testado |
|---|---|---|---|---|---|
| **OSU, 10ª edição** (Ministério do Planejamento, 16/11/2026) | [página](https://www.gov.br/planejamento/pt-br/assuntos/avaliacao-de-politicas-publicas/orcamento-de-subsidios-da-uniao); anexo `osu_2026-anexos-publicacao_enviado.xlsx` | 2003 a 2025 | xlsx, 430 KB; Tab_1 por programa e tipo, em R$ mil | Não (Tab_6 por região) | Baixado |
| **RTN, série histórica** (Tesouro) | [CKAN](https://www.tesourotransparente.gov.br/ckan/dataset/resultado-do-tesouro-nacional); o nome do arquivo muda todo mês (`seriehistoricajul26.xlsx`), achar pelo `package_show` | 1997 a jul/2026 | xlsx, 4,3 MB; tabela 2.2, linha 4.3.15 (subsídios por programa) e 1.4.2 (dividendos por empresa) | Não | Baixado |
| Portal da Transparência, orçamento da despesa | `…/orcamento-despesa/{ano}_OrcamentoDespesa.zip` (o projeto já tem) | 2014 a 2026 | zip | Não | Já usado |
| **Banco Central, Matriz de Dados do Crédito Rural** (API OData, `CusteioInvestimentoComercialIndustrialSemFiltros`) | olinda.bcb.gov.br | 2013 em diante, mensal | JSON, ~13 MB por mês | **Sim** (`codMunicIbge`), por programa e fonte do dinheiro | Baixado (jul/2025) |
| Banco Central, SICOR microdados | bcb.gov.br/htms/sicor/DadosBrutos | todos os anos | gz, 65 MB por ano mais 454 MB do complemento | Sim, pelo complemento | Lido em parte. **O arquivo `SICOR_MUTUARIOS` tem CPF: não baixar** |

**OSU, R$ bi** (2023 / 2024 / 2025): total 661,0 / 662,4 / 709,7 (5,6% do PIB em 2025), dos quais
tributários 534,0 / 546,8 / 569,2 (os mesmos de /impostos), **financeiros** 44,1 / 65,0 / 60,8 e
**creditícios** 82,9 / 50,5 / 79,6.

- Financeiros de 2025 (dinheiro que sai): FCVS 23,8; Pronaf 8,9; tarifa social de energia 8,3; Minha Casa
  Minha Vida 8,6; investimento rural 5,8; custeio agropecuário 2,2; FNDCT 1,4; Proex 0,6; seguro rural 0,6;
  PSI 0,2.
- Creditícios de 2025 (custo implícito): fundos constitucionais (FNE, FNO, FCO) 32,1; **FAT 26,7** (o
  dinheiro do FAT que fica no BNDES); FNDCT 5,3; Fundo da Marinha Mercante 4,6; FIES 2,7; emergencial do RS
  2,5; FGE 2,3; **empréstimos da União ao BNDES 1,4**. A metodologia mudou em 2025, e o próprio relatório
  diz que parte da queda do FIES e da alta do FAT vem disso. A série não emenda.

**O que o Tesouro pagou** (RTN, R$ bi, 2023 / 2024 / 2025): subsídios, subvenções e Proagro 21,7 / 17,8 /
25,5. Equalização do **Plano Safra** (Pronaf, custeio, investimento e preços agrícolas, soma feita aqui):
**11,0 / 8,6 / 16,9**. PSI, o programa antigo do BNDES: 0,5 / 0,2 / 0,2.

**Plano Safra por cidade**: pela Matriz do Banco Central, R$ 92,6 bi dos R$ 361,4 bi de crédito rural de
2025 foram com dinheiro equalizado (LCA 29,3; poupança rural 22,1; BNDES 20,9; recursos livres 20,3),
por município e sem CPF. É o volume emprestado, não o custo. Pode entrar na página da cidade numa segunda
etapa ("aqui, R$ X de crédito rural com juro pago em parte pelo Tesouro"); fica fora desta primeira.

## As estatais federais

| Fonte | URL | Anos | O que tem | Testado |
|---|---|---|---|---|
| **SEST, dados financeiros** (Ministério da Gestão) | `gov.br/gestao/…/sestdadosfinanceiros.zip` | 2016 a 2025 | Balanço, resultado e fluxo de caixa por estatal: subvenção do Tesouro, dividendos e JCP pagos à União, AFAC, aporte de capital | zip 2,9 MB (CSV 33 MB, em reais). Baixado |
| SEST, identificação | `…/sestidentificacao.zip` | fev/2026 | Sigla, CNPJ, se é dependente, controle direto ou indireto | Baixado |
| Boletim trimestral da SEST | `…/Dados_Desagregados_Boletim_Trimestral_Sest_2T26.xlsx` | 2025 e 1º sem. 2026 | O mesmo, mais recente | Baixado |
| RTN, tabela 2.2, linha 1.4.2 | ver acima | 1997 em diante | Dividendos por empresa (BB, BNB, BNDES, Caixa, Correios, Eletrobras, IRB, Petrobras, demais) | Baixado; bate com a SEST |

Cuidado: nos dados da SEST, os grupos (Petrobras, BB) repetem as controladoras, e as subsidiárias pagam
dividendos à controladora, não à União. Só somar as de controle direto.

**17 estatais dependentes** (vivem do orçamento): Ebserh, Embrapa, Hospital Conceição, Hospital de
Clínicas de Porto Alegre, Codevasf, Conab, CBTU, CPRM (Serviço Geológico), EBC, Amazul, Nuclep, Telebras,
Trensurb, Infra S.A., Imbel, EPE, Ceitec.

**O que o Tesouro pôs nelas** (subvenção, R$ bi): 23,9 / 27,1 / **30,9** em 2023 / 2024 / 2025. Em 2025:
Ebserh 13,7 (os hospitais universitários), Embrapa 4,5, Conceição 2,7, HCPA 2,0, Codevasf 1,7, Conab 1,3,
CBTU 1,3 e as outras dez somando 3,8. Mais AFAC (adiantamento para aumento de capital) de 2,8 / 2,0 / 1,7.

**O que as outras devolveram** (dividendos e JCP à União, R$ bi): 50,0 / 72,4 / **49,8**. Em 2025: BNDES
22,3, Petrobras 13,8, Caixa 4,2, Eletrobras 3,6 (a União ainda tem ações), BB 3,4, BNB 0,4, demais 2,1. No
1º semestre de 2026: 8,6, contra 22,4 no 1º semestre de 2025.

Aporte de capital nas não dependentes: 1,8 / 0,2 / 0,4 (BNB e Hemobrás em 2023).

A "conta das estatais" de 2025, então: entraram R$ 49,8 bi de dividendos e saíram R$ 30,9 bi de subvenção
e R$ 2,1 bi de capital. Mas as dependentes não são negócio: a Ebserh é hospital, a Embrapa é pesquisa. A
comparação serve para mostrar o tamanho, não para dizer que umas "dão lucro" e outras "dão prejuízo".

## Proposta

### Página nacional: /bndes

Uma página nova, ligada a partir de /impostos/empresas, /receitas e /divida. Título: **"BNDES e
estatais: o dinheiro que o governo empresta e o que ele põe nas empresas dele"**. Quatro partes:

1. **Quanto o BNDES emprestou**: a série de 2002 a 2026 (contratado), separando direto de indireto, e o
   desembolso total do ano (com a parte de pessoas físicas). Os blocos por setor e por programa.
2. **Com que juro**: as quatro faixas (abaixo do de mercado, TLP, mercado, doação), por ano.
3. **Quem recebeu**: os maiores do ano e uma busca por nome ou CNPJ, com a coluna "também tem benefício
   fiscal" (link para /impostos/empresas). Pessoas e MEI só somados.
4. **Quanto custa**: o custo estimado dos subsídios de crédito por programa (OSU) e o que o Tesouro pagou
   de equalização (RTN). Com o Plano Safra à parte.
5. **As estatais**: o que o Tesouro pôs nas 17 dependentes e o que as outras devolveram em dividendos, por
   empresa, desde 2016.
6. **O que esta conta não diz**.

Os dados da busca ficam no bucket público, como os benefícios fiscais (um parquet por cliente).

### Página da cidade

Uma seção nova, curta, depois da dívida ativa: **"Empréstimos do BNDES aqui"**. O total contratado no ano
com quem tem endereço ou projeto na cidade, quantos contratos, a parte com juro abaixo do de mercado, os
setores e as cinco maiores empresas. Pessoas físicas só somadas. Quando a cidade não tem nada, a seção
não aparece.

### Na ficha da empresa (/impostos/empresas)

Uma linha a mais: "Empréstimos do BNDES: R$ X contratados de 2020 a 2026, Y% com juro abaixo do de
mercado."

### As frases (rascunho)

Abertura de /bndes:

> Em 2025, o BNDES fechou **R$ 127,6 bilhões** em empréstimos. Não é dinheiro dado: a empresa devolve
> com juros. Mas parte saiu com juro mais baixo que o de um banco comum, e essa diferença alguém paga.

> **R$ 38,7 bilhões** foram com [juro abaixo do de mercado]ⓘ: dinheiro de fundos do governo (Fundo
> Clima, FUST) ou com o Tesouro cobrindo parte do juro. **R$ 62,5 bilhões** foram pela [TLP]ⓘ, que segue
> o juro que o próprio governo paga para pegar dinheiro emprestado. **R$ 23,9 bilhões** foram a juro de
> mercado. E **R$ 2,6 bilhões** foram doação, que não volta (Fundo Amazônia, Fundo Social).

> Quase três quartos do dinheiro direto foi para estradas, aeroportos, portos e energia. Os quatro
> maiores clientes de 2025 foram concessionárias de rodovias e de aeroportos.

Custo:

> O que custa para o Tesouro não é o valor emprestado. É a diferença de juros. Em 2025, o governo
> calculou esse custo em **R$ 79,6 bilhões** para todo o crédito com juro abaixo do de mercado, não só
> o do BNDES. A maior parte vem dos fundos regionais (FNE, FNO, FCO) e do dinheiro do FAT que fica no
> BNDES. Além disso, o Tesouro pagou R$ 16,9 bilhões em dinheiro aos bancos para baixar o juro do
> Plano Safra ([equalização]ⓘ).

Estatais:

> O governo federal tem empresas. Algumas dão dinheiro: em 2025, as estatais pagaram **R$ 49,8 bilhões**
> em dividendos à União, quase três quartos do BNDES e da Petrobras. Outras vivem do orçamento: as **17
> estatais dependentes** receberam **R$ 30,9 bilhões** do Tesouro, quase metade para a Ebserh, que cuida
> dos hospitais universitários.

Ligação com isenções:

> A mesma empresa pode pagar menos imposto e pegar dinheiro mais barato. Das 518 empresas que pegaram
> empréstimo direto do BNDES em 2024 e 2025, 286 também declararam benefício fiscal. Elas ficaram com
> 79% do dinheiro emprestado.

Cidade (João Pessoa como exemplo):

> Em 2025, empresas de João Pessoa fecharam **100 contratos** de empréstimo com o BNDES, somando
> **R$ 117 milhões**. R$ 45 milhões foram com juro abaixo do de mercado. A maior parte foi para comprar
> máquinas, ônibus e caminhões, pelos bancos da cidade. A maior foi da Copobras (embalagens), com
> R$ 34 milhões.
>
> Grandes obras que passam por várias cidades, como rodovias, não aparecem aqui: o BNDES não diz em
> que cidade elas ficam.

### O que esta conta não diz

- **Empréstimo não é gasto.** O dinheiro volta com juros. O que custa ao governo é o subsídio, a
  diferença de juros, e não o valor emprestado.
- **Não sabemos o subsídio de cada empresa.** O custo é calculado pelo governo por programa. A página
  diz quanto cada empresa pegou com juro abaixo do de mercado, não quanto ela "ganhou".
- **TLP não é juro de graça, mas também não é igual ao de um banco.** Segue o juro do governo, com prazo
  longo, que banco nenhum dá.
- **Nas operações indiretas, quem empresta é o banco.** O BNDES põe o dinheiro, o banco escolhe o
  cliente e fica com o risco.
- **Contratado não é liberado.** Parte do dinheiro sai em vários anos, e parte nunca sai.
- **O crédito rural para pessoas quase não está nos dados por contrato.** Em 2025, o BNDES liberou
  R$ 33,6 bilhões para pessoas físicas, quase todo para produtores rurais, mas eles não aparecem um a um.
  O Plano Safra é muito maior que o BNDES: a maior parte passa pelo Banco do Brasil e pelas cooperativas.
- **A cidade é onde está o projeto ou o cliente**, não necessariamente onde o dinheiro é gasto. E 73% do
  dinheiro direto de 2025 não tem cidade.
- **Estatal dependente não é "prejuízo".** Hospital e pesquisa não são feitos para dar lucro. Os
  dividendos também variam muito de um ano para outro, conforme o preço do petróleo e o lucro dos bancos.
- **O custo estimado (OSU) e o que foi pago (Tesouro) são contas diferentes** e não se somam. A
  metodologia do custo mudou em 2025.

### Pendências e decisões

- Nome da página: `/bndes` (proposta) ou dentro de `/impostos`.
- Plano Safra por cidade (Matriz do Banco Central): numa segunda etapa.
- Os setores vêm escritos de dois jeitos nos dois arquivos ("INFRAESTRUTURA" e "INFRA-ESTRUTURA"):
  normalizar.
- Os dados de 2026 vão só até setembro: a página usa 2025 como o ano fechado.

## Como os dados entram no site

`uv run bndes` (em `pipeline/`) baixa as operações do BNDES, o cadastro de CNPJ da Receita (os arquivos Empresas,
um por vez, apagados depois), o Orçamento de Subsídios, o Resultado do Tesouro e os dados da SEST, e grava
`site/public/data/bndes/{resumo,cidades,empresas}.json` com cópia em `pipeline/referencia/bndes*.json`. A publicação
diária só copia essas cópias (`bndes --sem-baixar`). O BNDES atualiza as operações todo mês; a carga é à mão.
