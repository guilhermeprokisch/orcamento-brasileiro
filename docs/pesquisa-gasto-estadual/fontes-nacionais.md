# Fontes nacionais para estimar o gasto estadual por município

Pesquisa feita em 19/11/2026. Só fontes federais ou nacionais (um formato para o país inteiro). Portais estaduais ficaram de fora de propósito.

## Resumo

Nenhuma base nacional mede o gasto de um governo estadual por município. O que existe são três tipos de dado:

1. **Uma parte medida de verdade**: o que o estado transfere às prefeituras, visto pelo lado de quem recebe (SICONFI, DCA Anexo I-C e MSC). Conferido ao vivo.
2. **Cadastros nacionais de unidades estaduais com município**: escolas (Censo Escolar), estabelecimentos de saúde (CNES), internações pagas por hospital (SIH), presídios (SISDEPEN). Servem como chave de rateio do gasto da área correspondente, não como medida do gasto.
3. **Vínculos de trabalho estaduais por município** (RAIS, natureza jurídica 102-3 e afins). Servem para ratear a folha, com uma fraqueza séria de localização.

Não encontrei estudo nacional que tenha estimado o gasto estadual por município. O próprio IBGE, no PIB dos Municípios, reparte o valor adicionado do governo estadual pela população residente, sem dado de localização.

### Graus de verificação usados

- **Verificado**: abri o dado, o dicionário ou a definição da API e vi o campo.
- **Verificado em espelho**: vi o campo no esquema da Base dos Dados (basedosdados.org), não no arquivo original do órgão.
- **Descrito mas não aberto**: li numa descrição, num estudo ou numa página, sem ver o campo.
- **Não encontrado**: procurei e não achei.

## Tamanho de cada área no gasto estadual

Calculei com a DCA 2023 dos 27 estados e do DF (API do SICONFI, Anexos I-D e I-E, despesa empenhada). Base: R$ 1.205,0 bilhões, sem as despesas intraorçamentárias. Verificado (cálculo próprio sobre a API).

| Função | R$ bi | % |
|---|---|---|
| Previdência Social | 218,5 | 18,1 |
| Educação | 197,3 | 16,4 |
| Encargos Especiais (dívida e transferências a municípios) | 188,4 | 15,6 |
| Saúde | 162,9 | 13,5 |
| Segurança Pública | 118,6 | 9,8 |
| Judiciária | 63,5 | 5,3 |
| Transporte | 58,8 | 4,9 |
| Administração | 48,6 | 4,0 |
| Essencial à Justiça | 31,7 | 2,6 |
| Legislativa | 24,1 | 2,0 |
| Direitos da Cidadania (inclui sistema prisional em vários estados) | 17,8 | 1,5 |
| Urbanismo | 15,0 | 1,2 |
| Demais funções | cerca de 60 | cerca de 5 |

Pela natureza da despesa (Anexo I-D, total geral de R$ 1.297,9 bi, com intraorçamentárias):

- Pessoal e encargos (grupo 3.1, inclui inativos): R$ 679,6 bi, 52%.
- Investimentos (grupo 4.4): R$ 92,8 bi, 7%.
- Juros e amortização da dívida: R$ 63,8 bi, 5%.
- Transferências a municípios registradas como despesa (modalidades 40, 41, 42 e 45): R$ 119,2 bi, 9%. Parte dos estados registra a cota-parte de ICMS e IPVA como dedução de receita, então esse número subestima o repasse total.

---

## 1. Educação

### 1.1 Censo Escolar (INEP)

- **URL**: página dos microdados https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar . Arquivos no padrão `https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_ANO.zip` (o de 2025 tem um `_` antes de `.zip`). Sinopses por ano em https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-basica .
- **Acesso**: ZIP com CSV e dicionário. Tamanho: 33,8 MB (2024) e 32,1 MB (2023). Sem API oficial.
- **Anos**: a página lista de 1995 a 2025.
- **Campos**: no espelho da Base dos Dados (conjunto `censo_escolar`), a tabela `turma` (2009 a 2024) tem `id_escola`, `id_municipio` (IBGE 7 dígitos), `rede` e `quantidade_matriculas`. A tabela `escola` cobre 2007 a 2025. `matricula` e `docente` param em 2020, porque o INEP deixou de publicar o registro individual.
- **Grau**: verificado em espelho. Não abri o dicionário oficial: o servidor `download.inep.gov.br` apresenta uma cadeia de certificado que não valida nesta máquina, e não contornei a verificação. O conteúdo das Sinopses (matrícula por município e dependência) ficou como descrito mas não aberto.
- **O que permite afirmar**: quantas escolas e matrículas a rede estadual tem em cada município. **Permite estimar por rateio** o gasto estadual em educação básica. Não mede gasto.

### 1.2 SIOPE, remuneração dos profissionais da educação (FNDE)

- **URL**: serviço OData `https://www.fnde.gov.br/olinda-ide/servico/DADOS_ABERTOS_SIOPE/versao/v1/odata`, entidade `Remuneracao_Siope` com parâmetros `Ano_Declaracao`, `Num_Peri` (bimestre), `Mes_Exercicio` e `Sig_UF`. Vi o endereço e os parâmetros no código do pacote R `tesouror` (https://rdrr.io/cran/tesouror/src/R/siope.R), que também mostra o filtro `DS_TIPO` com os valores "Estado" e "Município".
- **Acesso**: API OData. **Estava fora do ar no dia da pesquisa**: três tentativas, três respostas HTTP 500, inclusive na raiz do serviço.
- **Campos**: o relatório do Centro de Estatística Aplicada da USP (https://repositorio.usp.br/bitstreams/91f2597e-104b-4bee-9fe1-9f107c678ed2), que recebeu a base pelo LabContas do TCU, descreve cada linha como a remuneração mensal de um profissional em uma escola, com "Código Escola: código INEP da escola", código do município, carga horária, categoria, situação (efetivo, temporário, cedido), salário base e remuneração total. Arquivos separados para rede estadual e municipal, de 2017 a 2022. Obrigações patronais não entram no valor.
- **Grau**: descrito mas não aberto. Não confirmei que a API pública devolve o código da escola. O pacote R fala em 19 colunas sem listá-las.
- **O que permite afirmar, se o campo de escola estiver na API**: seria a única fonte nacional que **mede** uma parte do gasto estadual por município, a folha da educação básica, pela escola onde o profissional trabalha. É dado declaratório, preenchido pelo próprio estado. Vale a pena testar de novo quando o serviço voltar.

### 1.3 SIOPE, despesas e indicadores do estado

- **URL**: mesmo serviço OData, entidades `Despesas_Siope`, `Despesas_Funcao_Educacao_Siope`, `Indicadores_Siope`, `Receita_Siope`, `Dados_Gerais_Siope` (parâmetros `Ano_Consulta`, `Num_Peri`, `Sig_UF`). No espelho da Base dos Dados (conjunto `fundeb`, "Indicadores do SIOPE") há `indicador_estadual` e `indicador_municipal`.
- **Grau**: descrito mas não aberto (serviço fora do ar).
- **O que permite afirmar**: a despesa do estado em educação por etapa e subfunção, para o estado inteiro. Não achei nenhuma indicação de abertura por escola ou município nessas entidades.

### 1.4 FUNDEB por rede

- **Grau**: não encontrado como dado por município da rede estadual. O Fundeb é distribuído a cada ente (o governo estadual é um ente só). O que chega a cada prefeitura aparece na DCA dela (conta 1.7.5.1, verificado), mas isso é dinheiro da rede municipal.
- **O que permite afirmar**: nada sobre a localização do gasto estadual. Os fatores de ponderação do Fundeb por etapa e jornada podem refinar o rateio pelas matrículas do Censo Escolar.

### 1.5 Censo da Educação Superior (INEP)

- **Campos**: no espelho da Base dos Dados (`censo_educacao_superior`), a tabela `curso` (2009 a 2024) tem `id_municipio` do local de oferta do curso, e a tabela `ies` tem o município da reitoria e a quantidade de docentes.
- **Grau**: verificado em espelho. Não vi a coluna de categoria administrativa (a consulta ao esquema corta em 100 colunas).
- **O que permite afirmar**: **permite estimar por rateio** o gasto com universidades estaduais, que pesa na função Educação de SP, PR, BA, CE e outros.

## 2. Saúde

### 2.1 CNES (DATASUS)

- **URL**: https://apidadosabertos.saude.gov.br/cnes/estabelecimentos
- **Acesso**: API JSON aberta, sem chave. Aceita `codigo_uf`, `codigo_municipio`, `status`, `limit`, `offset`.
- **Campos (vistos na resposta)**: `codigo_cnes`, `codigo_municipio` (IBGE 6 dígitos), `descricao_natureza_juridica_estabelecimento` (código, por exemplo `1023` para órgão do Executivo estadual e `1244` para município), `tipo_gestao` (E, M, D), `descricao_esfera_administrativa`, tipo de unidade, latitude e longitude.
- **Cuidado que apareceu na amostra**: `descricao_esfera_administrativa` repete a gestão, não o dono. Em Campina Grande, laboratórios privados (natureza 2062) vieram como esfera "MUNICIPAL". Para saber se a unidade é do estado, use a natureza jurídica. Na mesma amostra de 60 estabelecimentos havia 3 de natureza 1023, entre eles o Hospital de Clínicas de Campina Grande.
- **Leitos e profissionais**: no espelho da Base dos Dados (`cnes`), `leito` tem `quantidade_total` e `quantidade_sus`, e `profissional` tem carga horária ambulatorial e hospitalar, CBO e tipo de vínculo, todos com `id_municipio`, de 2005 a 2026. `estabelecimento` tem `id_natureza_juridica`.
- **Grau**: verificado (API de estabelecimentos); verificado em espelho (leitos e profissionais).
- **O que permite afirmar**: onde o estado tem unidade de saúde, com quantos leitos e quantas horas de profissionais. **Permite estimar por rateio** o gasto com a rede própria. Sozinho, só indica presença.

### 2.2 SIH/SUS e SIA/SUS

- **Campos**: no espelho da Base dos Dados (`sih`, tabela `aihs_reduzidas`, 2008 a 2026): `id_estabelecimento_cnes`, `id_municipio_estabelecimento`, `id_municipio_paciente`, `natureza_juridica_estabelecimento`, `tipo_gestao_estabelecimento`, `valor_aih`.
- **Grau**: verificado em espelho. Não abri os arquivos do FTP do DATASUS nem o SIA.
- **O que permite afirmar**: o valor que o SUS aprovou por hospital, pela tabela SUS. **Não é o gasto do estado** com o hospital, que costuma ser várias vezes maior. Serve de peso para o rateio. Tem uma vantagem rara: o município de residência do paciente, que deixa repartir o gasto por quem foi atendido e não só por onde fica o prédio.

### 2.3 SIOPS

- **URL**: https://www.gov.br/saude/pt-br/acesso-a-informacao/siops/demonstrativos-e-dados-informados/dados-informados/municipios , que aponta para consultas em PHP como `http://siops.datasus.gov.br/valoresinformados.php` (anos-base a partir de 2018).
- **Acesso**: só tela. Não achei API nem arquivo aberto.
- **Grau**: descrito mas não aberto. Não abri os formulários.
- **O que permite afirmar**: não encontrei nenhuma consulta de despesa estadual por município ou por região de saúde. O lado municipal declara as transferências do SUS vindas do estado, mas o mesmo valor já está na DCA e na MSC (item 6), em formato muito melhor.

### 2.4 Fundo Estadual de Saúde para Fundos Municipais

- **Fonte**: não há base nacional do lado do estado. Do lado do município, a conta `1.7.2.3.00.0.0 - Transferências de Recursos do Sistema Único de Saúde – SUS` (dentro de "Transferências dos Estados") aparece na DCA, e a natureza `17235001` aparece na MSC mensal.
- **Grau**: verificado (Campina Grande, 2023 e dezembro de 2024).
- **O que permite afirmar**: **mede** o repasse estadual de saúde recebido por cada prefeitura.

## 3. Pessoal

### 3.1 RAIS (MTE)

- **URL**: microdados públicos em `ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/` (pastas 1985 a 2025; listei 2023 e 2024). Layout em `.../RAIS/Layouts/vínculos/RAIS_vinculos_layout2020.xls`. Espelho: https://basedosdados.org/dataset/3e7c4d58-96ba-448e-b053-d385a829ef00 .
- **Acesso**: FTP, arquivos `.7z` por região, de 186 MB a 1 GB cada (não baixei). Na Base dos Dados, por BigQuery.
- **Campos (layout oficial de 2020, aberto)**: `NAT JURIDICA`, com as categorias `POD EXEC FE 1015`, `POD EXEC ES 1023`, `POD EXEC MU 1031`; `MUNICIPIO` (localização do estabelecimento); `MUN TRAB` (onde o empregado trabalha, desde 2002); remuneração média e de dezembro. No espelho: `natureza_juridica`, `id_municipio`, `id_municipio_trabalho`, `valor_remuneracao_media`, `tipo_vinculo`, `cbo_2002`.
- **Naturezas jurídicas estaduais** (lista da metodologia do Atlas do Estado Brasileiro, https://www.ipea.gov.br/atlasestado/quem/12/metodologia): 102-3 Executivo, 105-8 Legislativo, 108-2 Judiciário, 111-2 autarquia, 114-7 fundação de direito público, 117-1 órgão autônomo, 123-6 Estado ou DF, 126-0 fundação de direito privado. Empresas estatais (201-1, 203-8) não distinguem a esfera.
- **Anos**: 1985 a 2024 com microdado público. O comunicado do MTE de 30/12/2025 diz que os microdados de 2024 já incluem a administração pública e mudaram de formato (`.7z`, arquivos `.comt`, nomes de variáveis novos com tabela de-para).
- **Grau**: verificado (layout e listagem do FTP); verificado em espelho (colunas).
- **Três fraquezas**:
  1. **O município de trabalho acabou em 2023.** A descrição da coluna na Base dos Dados diz que a fonte passou a enviar `999999` e que o campo está preenchido em menos de 0,4% das linhas de 2023 em diante.
  2. **O município que sobra é o do CNPJ declarante.** Um órgão estadual que declara todos os servidores no CNPJ da sede joga a folha inteira na capital. Não medi o tamanho disso, porque exigiria baixar os microdados. A nota do IPEA sobre a RAIS do setor público (https://repositorio.ipea.gov.br/bitstream/11058/9885/1/bmt_65_03_nota1_o_que_pode.pdf) trata natureza jurídica e endereço do estabelecimento como as variáveis que identificam o órgão, e aponta problemas de declaração.
  3. **Quebra de série em 2022 e 2023**, com a migração para o eSocial. O MTE recomenda não comparar com anos anteriores e avisa que nem todos os entes públicos concluíram a transição (sumário executivo da RAIS 2023, https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2023/sumario-executivo_rais-2023.pdf).
- **O que permite afirmar**: **permite estimar por rateio** a folha de ativos do estado por município, melhor até 2022 (com `MUN TRAB`). Não cobre inativos nem terceirizados.

### 3.2 Atlas do Estado Brasileiro (IPEA)

- **URL**: https://www.ipea.gov.br/atlasestado/
- **Grau**: verificado para a metodologia; não encontrado para dado estadual por município. As séries listadas são por nível federativo e por poder. Não achei download municipal nem documentação de API.
- **O que permite afirmar**: serve como referência de método (quais naturezas jurídicas contar). Não traz o recorte que queremos.

## 4. Segurança

### 4.1 Pesquisa Perfil das Instituições de Segurança Pública (Senasp/MJSP)

- **URL**: https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/pesquisaperfil , bases em `.../pesquisaperfil/base-de-dados`, ciclo de 2026 em `.../pesquisaperfil/2026`.
- **O que é coletado**: no ciclo de 2026 (ano-base 2025) a Senasp pediu a cada estado um "questionário do detalhamento do efetivo por município" para PM, PC, CBM e perícia. Abri a planilha em branco da PM da Paraíba (`questionario_municipios_pisp_2026_pb_pm.xlsx`): uma linha por município, com `Cod_IBGE`, e colunas de quantidade e efetivo de batalhões, batalhões especializados, companhias independentes e outras subunidades. O ofício da Senasp liga a resposta ao rateio do Fundo Nacional de Segurança Pública.
- **O que é publicado**: baixei `anos_base_2020_2025.zip` (5,9 MB). A base da PM de 2025 tem uma linha por UF e 1.263 colunas. O recorte territorial publicado é só "Capital ou DF", "Região Metropolitana" e "Interior" (166 colunas com esse corte). Não há linha por município. A página da pesquisa diz que a divulgação é por unidade da federação.
- **Grau**: verificado (formulário e base publicada).
- **O que permite afirmar**: o dado por município existe dentro do MJSP e não está publicado. Vale um pedido pela Lei de Acesso à Informação. O que está público dá três totais de controle por estado (capital, região metropolitana, interior).

### 4.2 MUNIC (IBGE)

- **URL**: https://ftp.ibge.gov.br/Perfil_Municipios/2019/Base_de_Dados/Base_MUNIC_2019_20210817.xlsx (24 MB, baixado). Existe também `Base_MUNIC_2023.xlsx` na pasta de 2023 (não abri).
- **Campos (dicionário de 2019, aba "Segurança pública")**: `MSEG161` Delegacia de Polícia Civil, `MSEG162` a `MSEG1610` delegacias especializadas, `MSEG17` Instituto Médico Legal, `MSEG19` Unidade do Corpo de Bombeiros. Respostas Sim ou Não, com código IBGE de 7 dígitos.
- **Grau**: verificado (2019).
- **O que permite afirmar**: **só indica presença**. Não tem efetivo, nem unidade da PM.

### 4.3 ESTADIC (IBGE), Anuário do FBSP e SINESP

- **ESTADIC**: efetivo das polícias por estado. Descrito mas não aberto. Nível UF.
- **Anuário Brasileiro de Segurança Pública (FBSP)**: no espelho da Base dos Dados (`absp`), a tabela `municipio` (2016 a 2021) só tem contagem de crimes e mortes, e a tabela `uf` (2007 a 2021) tem `despesa_empenhada_seguranca_publica`. Verificado em espelho. Nada de efetivo ou gasto por município.
- **SINESP**: no espelho (`sinesp`, tabela `municipio_mes`, 2015 a 2026) há ocorrências e vítimas por município e mês. Verificado em espelho. Não é presença nem gasto.

### 4.4 SISDEPEN (Senappen), sistema prisional

- **URL**: https://www.gov.br/senappen/pt-br/servicos/sisdepen/bases-de-dados . Arquivo por ciclo em XLSX e CSV, por exemplo `.../bases-de-dados/2025/19o-ciclo-base-de-dados-2025-2-semestre.csv/@@download/file`.
- **Anos**: 2014 a 2025, semestral desde 2016.
- **Campos (cabeçalho do CSV do 2º semestre de 2025, lido parcialmente)**: `Âmbito` (Estadual ou Federal), `UF`, `Município`, `Código IBGE`, capacidade por regime, `1.4 Gestão do estabelecimento`, `3.1 Quantidade de Servidores que atuam no Sistema Prisional` por cargo. São 1.737 colunas.
- **Grau**: verificado.
- **O que permite afirmar**: **permite estimar por rateio** o gasto com administração penitenciária, por servidores ou por capacidade de cada unidade. É a melhor chave de rateio que achei fora de educação e saúde.

## 5. Obras

### 5.1 Obrasgov.br (CIPI)

- **URL**: documentação em https://api-publica.obrasgov.gestao.gov.br/obras/docs , definição em `https://api-publica.obrasgov.gestao.gov.br/obras/openapi.json`. A API antiga (`api.obrasgov.gestao.gov.br`) devolveu erro 500, e a página oficial diz que ela seria mantida só até 31/08/2026.
- **Acesso**: API JSON aberta. Endpoints: `/projeto-investimento`, `/geometria`, `/empenho`, `/contrato`, `/execucao-fisica`.
- **Campos (vistos na definição e em amostra da Paraíba)**: no projeto, listas `executores` (`organizacao_executor`, `cnpj_executor`), `tomadores`, `repassadores` e `investimentos_previstos` (`vl_investimento_previsto`, `desc_nome_fonte_recurso`); em `/geometria`, `cod_ibge` e `no_municipio` por projeto. Não há campo de esfera: o estado se identifica pelo nome ou CNPJ do executor (na amostra, "ESTADO DA PARAIBA" em 9 de 100 projetos). A Paraíba tem 5.268 projetos e 7.778 geometrias.
- **Escopo**: a própria API se descreve como plataforma das "obras públicas financiadas com recursos federais".
- **Grau**: verificado.
- **O que permite afirmar**: **mede a parte federalmente financiada** das obras executadas pelo estado, com município. Não cobre obra paga com recurso próprio ou operação de crédito do estado.

### 5.2 Transferegov.br (convênios e contratos de repasse)

- **URL**: https://api-publica.transferegov.gestao.gov.br , módulo `/discricionarias` (definição em `/discricionarias/openapi.json`).
- **Campos (vistos em amostra)**: em `/propostas`, `natureza_juridica` (com o valor "Administração Pública Estadual ou do Distrito Federal"), `uf_proponente`, `munic_proponente`, `cod_munic_ibge`, `vl_global_prop`. Em `/meta-crono-fisico`, `uf_meta`, `municipio_meta` (nome, sem código IBGE), `endereco_meta`, `vl_meta`.
- **O que a amostra mostrou**: a Paraíba tem 1.368 propostas de proponente estadual. Nas 50 primeiras, o município do proponente é João Pessoa em 39 e Campina Grande em 10, ou seja, é a sede do órgão. O local de execução está na meta: uma proposta do "ESTADO DA PARAIBA" com sede em João Pessoa tinha meta em Areia. Há metas sem município preenchido.
- **Grau**: verificado.
- **O que permite afirmar**: o mesmo que o Obrasgov, incluindo convênios que não são obra. Só recurso federal mais contrapartida.

### 5.3 PNCP (Portal Nacional de Contratações Públicas)

- **URL**: https://pncp.gov.br/api/consulta/v1/contratos (parâmetros `dataInicial`, `dataFinal`, `pagina`, `tamanhoPagina`).
- **Campos (vistos)**: `orgaoEntidade.esferaId` (F, E, M, D), `unidadeOrgao.codigoIbge` e `municipioNome`, `valorGlobal`, `objetoContrato`, `identificadorCipi`.
- **O que a amostra mostrou**: nos 2.000 primeiros contratos publicados de 10 a 14/03/2025 (de 36.537), 306 eram de órgãos estaduais. Desses, 231 (75%) eram de unidades sediadas em capitais, com 98% do valor (R$ 79,8 milhões de R$ 81,6 milhões). `identificadorCipi` veio vazio em todos. A amostra é pequena e não aleatória.
- **Grau**: verificado.
- **O que permite afirmar**: o município é o da unidade compradora, não o de execução. **Só indica presença** de unidades gestoras no interior (presídios e hospitais de SP apareceram). Para repartir custeio ou obras, não serve.

### 5.4 Painel de obras do TCU

- **Grau**: descrito mas não aberto. Pelas notícias do TCU (por exemplo https://portal.tcu.gov.br/imprensa/noticias/painel-digital-consolida-dados-de-obras-publicas-federais), o painel consolida bases federais (Caixa, PAC, MEC, DNIT, Funasa) de obras com recurso federal. Não achei dado aberto para download. Não acrescenta nada ao Obrasgov para o nosso fim.

## 6. Transferências do estado aos municípios, pelo lado de quem recebe

### 6.1 DCA, Anexo I-C (SICONFI)

- **URL**: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio=2023&no_anexo=DCA-Anexo I-C&id_ente=2504009`
- **Contas vistas (Campina Grande, 2023, receitas brutas realizadas)**:
  - `1.7.2.0.00.0.0` Transferências dos Estados e do DF: R$ 339,0 milhões
  - `1.7.2.1.50.0.0` Cota-Parte do ICMS: R$ 268,2 milhões
  - `1.7.2.1.51.0.0` Cota-Parte do IPVA: R$ 55,4 milhões
  - `1.7.2.1.52.0.0` Cota-Parte do IPI-Municípios e `1.7.2.1.53.0.0` Cota-Parte da CIDE
  - `1.7.2.2.51.0.0` Cota-parte da CFEM
  - `1.7.2.3.00.0.0` Transferências de Recursos do SUS (do estado): R$ 3,8 milhões
  - `1.7.2.9.53.0.0` compensação das perdas de ICMS da LC 194/2022 e `1.7.2.9.99.0.0` outras
  - `2.4.2.0.00.0.0` transferências de capital dos estados: R$ 0,8 milhão
- **Grau**: verificado.

### 6.2 MSC (SICONFI)

- **URL**: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria` com `id_ente`, `an_referencia`, `me_referencia`, `co_tipo_matriz=MSCC`, `classe_conta=6`, `id_tv`.
- **Naturezas de receita vistas (Campina Grande, dezembro de 2024)**: `17215001` ICMS, `17215101` IPVA, `17215201` IPI, `17215301` CIDE, `17225101` CFEM, `17235001` SUS, `17299901` outras. Mensal, com fonte de recursos.
- **Grau**: verificado.

### 6.3 Detalhamento melhor que esse?

- **CONFAZ ou Tesouro com cota-parte por município**: não encontrado. A busca só devolveu portais das secretarias de fazenda estaduais (SP, MG, PR, PA), que estão fora do escopo.
- **Banco do Brasil, demonstrativo de distribuição da arrecadação**: a página https://demonstrativos.apps.bb.com.br/arrecadacao-federal abre, mas é um aplicativo em JavaScript e não consegui ver o conteúdo. Descrito mas não aberto. Se listar ICMS e IPVA por prefeitura, cobre só os estados que usam o BB como agente.
- **O que permite afirmar**: DCA e MSC **medem** a transferência recebida, com abertura por tributo. É o melhor que existe em formato nacional. A fraqueza é ser autodeclarado por cada prefeitura (omissões, atrasos e classificação errada entre contas).

## 7. Contas regionais e estudos

### 7.1 PIB dos Municípios (IBGE)

- **URL**: https://ftp.ibge.gov.br/Pib_Municipios/2010/srmpibmunicipios.pdf (Série Relatórios Metodológicos, v. 29) e https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRef2010.pdf .
- **O que os dois documentos dizem**: o valor adicionado de "Administração, educação e saúde públicas, defesa e seguridade social" junta as três esferas. Para reparti-lo entre municípios, a regra é: "Esferas federal e estadual: População residente" (fonte: estimativa populacional do IBGE); "Esfera municipal: Despesa realizada com pessoal" (FINBRA e tribunais de contas). Está no Anexo 1 do relatório (p. 32) e no quadro da nota de referência 2010 (p. 5).
- **Grau**: verificado.
- **O que permite afirmar**: a coluna de administração pública do PIB municipal **não serve** para medir presença estadual. A parte estadual dela é um rateio por população. Também mostra que o IBGE não dispõe de dado melhor.

### 7.2 Estudos

- **Estimativa nacional do gasto estadual por município**: não encontrado, em duas buscas (uma delas estendida).
- **O que apareceu de próximo**:
  - IPEA, TD 2089 (https://repositorio.ipea.gov.br/bitstream/11058/4366/1/td_2089.pdf): padrões regionais da despesa municipal, não estadual. Descrito mas não aberto.
  - "Regionalização das Transações do Setor Público" do IBGE (1991 a 2000) e série anterior da FGV (1970 a 1985), citadas em caderno do Fórum Fiscal dos Estados. Nível estadual. Descrito mas não aberto.
  - Monografia do Senado sobre regionalização do orçamento federal (https://www2.senado.leg.br/bdsf/bitstream/handle/id/162779/Regionalizacao%20do%20Orcamento%20-%20Fernando%20Lucas%20Pinto.pdf). Trata do gasto federal. Descrito mas não aberto.
  - Um artigo sobre o Rio Grande do Sul (Braatz, Gonçalves e Fochezatto, 2019) que relaciona gasto estadual e renda dos municípios gaúchos. Um estado só. Descrito mas não aberto.
- **Boletim de Finanças dos Entes Subnacionais (Tesouro)**: não abri. Pelo que conheço, trabalha por ente, sem abertura municipal do gasto estadual. Descrito mas não aberto.

## 8. Outras bases nacionais

- **CNPJ (Receita Federal)**: no espelho da Base dos Dados (`cnpj`), `empresas.natureza_juridica` e `estabelecimentos.id_municipio`, de 2021 a 2026. Verificado em espelho. Lista os estabelecimentos de órgãos estaduais por município. **Só indica presença**, e só de quem tem CNPJ de filial.
- **Censo SUAS, SIMEC (obras do FNDE), SISMOB (obras de saúde), CNJ (comarcas e unidades judiciárias por município)**: não pesquisados a fundo. O CNJ seria a chave natural para a função Judiciária (5,3% do gasto).

---

## Proposta: como repartir cada área do gasto estadual por município

Percentuais sobre a despesa empenhada dos 27 entes em 2023 (R$ 1.205 bi sem intraorçamentárias).

| Área | Peso | Melhor forma nacional | Tipo | Principal fraqueza |
|---|---|---|---|---|
| **Transferências a municípios** | cerca de 10% ou mais | Usar o que cada prefeitura declara ter recebido do estado: DCA Anexo I-C (contas 1.7.2 e 2.4.2) e MSC (naturezas 172x). | **Medido** | Autodeclarado. Prefeitura que não entrega a DCA some. Não distingue o que é obrigação constitucional do que é escolha do governo, a não ser pela conta. |
| **Educação** | 16,4% | Ratear pelas matrículas da rede estadual em cada município (Censo Escolar), ponderadas pelos fatores do Fundeb por etapa e jornada. Ensino superior estadual à parte, pelo município de oferta dos cursos (Censo da Educação Superior). Se a API do SIOPE voltar e trouxer o código da escola, trocar o rateio da folha pela remuneração declarada por escola. | Rateio (folha possivelmente medida) | Supõe custo igual por aluno. Erra onde há escola pequena e cara, transporte escolar e administração central. O SIOPE é declaratório e não confirmei o campo de escola. |
| **Saúde** | 13,5% | Três fatias. (a) Repasse a fundos municipais: medido pela DCA e MSC (conta 1.7.2.3). (b) Rede própria: ratear pelos estabelecimentos de natureza jurídica estadual no CNES, com peso pela carga horária de profissionais ou pelo valor aprovado no SIH e no SIA. (c) O resto (medicamentos, regulação, administração): população. Mostrar também a versão por município de residência do paciente (SIH). | Rateio, com uma fatia medida | O valor do SIH é tabela SUS, não custo. Hospital estadual gerido por organização social pode estar no CNES com a natureza jurídica da entidade privada. O prédio fica na cidade-polo e atende a região. |
| **Segurança** | 9,8% | Hoje: ratear pelos vínculos da RAIS de natureza jurídica estadual em ocupações policiais, por município, respeitando os totais de capital, região metropolitana e interior da Pesquisa Perfil. Para o sistema prisional, ratear pelos servidores de cada unidade no SISDEPEN. Pedir à Senasp, pela LAI, o detalhamento do efetivo por município que ela já coleta. | Rateio fraco | Não há efetivo por município publicado. A RAIS localiza pelo CNPJ declarante e perdeu o município de trabalho em 2023. A MUNIC só diz se há delegacia. |
| **Obras e investimentos** | cerca de 7% (corte por natureza da despesa; se sobrepõe às funções das outras linhas) | Somar, por município, as obras com executor ou proponente estadual no Obrasgov (`/geometria`) e no Transferegov (`municipio_meta`). | **Medido, mas parcial** | Só entra obra com recurso federal. A maior parte do investimento estadual (recurso próprio e operação de crédito) não está em nenhuma base nacional. O recorte é enviesado para onde há convênio federal. |
| **Demais** (Judiciário, Ministério Público, Legislativo, administração, transporte e outras; cerca de 25%) | cerca de 25% | Folha de ativos pela RAIS (naturezas 102-3, 105-8, 108-2, 111-2, 114-7, 117-1, 123-6, 126-0), por município do estabelecimento, de preferência com o município de trabalho até 2022. Custeio e o resto: sem chave nacional. | Rateio fraco | Concentra na capital por construção. O teste com o PNCP deu 98% do valor contratado em unidades de capitais. |
| **Previdência e dívida** | cerca de 23% | Não ratear. Mostrar como "não distribuível por município". | Sem método | Não achei base nacional com o município de residência dos inativos estaduais. Ratear por população inventaria um número. |

### O que isso cobre no total

- **Medido de fato**: transferências a municípios (cerca de 10% do gasto, mais onde a cota-parte é dedução de receita), a parte federal das obras, e talvez a folha da educação básica se o SIOPE confirmar a escola.
- **Rateio com chave setorial defensável**: educação, saúde e sistema prisional, cerca de 30% do gasto.
- **Rateio fraco**: segurança e demais funções, cerca de 35%.
- **Não distribuível**: previdência e dívida, cerca de 23%.

Ou seja: com bases nacionais dá para apresentar uma estimativa razoável para algo como 40% do gasto estadual, e uma estimativa fraca ou nenhuma para o resto. Em nenhum caso o resultado é comparável ao que a Paraíba publica. No site, convém mostrar cada fatia com o seu rótulo ("medido", "estimado por matrículas", "não distribuído") em vez de um total único por município.

### Como validar

A Paraíba publica o município em cada despesa. Aplicar os rateios acima à Paraíba e comparar com o dado real dá o erro de cada método, por função. Esse teste diz quais rateios merecem ir ao ar para os outros 26.

---

## Pendências e limites desta pesquisa

- **SIOPE (FNDE)**: serviço OData respondendo HTTP 500. A existência do código da escola na API pública não foi confirmada. É a verificação que mais muda a proposta.
- **INEP**: não baixei os microdados nem as sinopses, porque o certificado de `download.inep.gov.br` não validou aqui. Os campos vieram do espelho da Base dos Dados.
- **RAIS**: não medi quanto da folha estadual cai na capital, porque os arquivos passam de 30 MB.
- **SIOPS, Banco do Brasil, TCU, Boletim do Tesouro, ESTADIC, Sinopses do INEP, MUNIC 2023**: não abertos.
- **CNJ, Censo SUAS, SIMEC, SISMOB**: não pesquisados.
- **Base dos Dados**: a consulta ao esquema devolve no máximo 100 colunas por tabela, então listas de colunas de tabelas grandes estão incompletas.

## Arquivos baixados (pasta de trabalho desta pesquisa)

Em `/private/tmp/claude-502/-Users-guilherme-prokisch-Projects-orcamento-br/b76ddc94-fa87-43c6-b2af-0278d8ef0d4b/scratchpad/pesquisa-estados/`:

- `dl/rais/layout2020.xls` e `dl/rais/comunicado2024.htm` (layout e comunicado da RAIS)
- `dl/pisp/bases_2020_2025.zip` e `dl/pisp/q.xlsx` (Pesquisa Perfil: base publicada e formulário por município)
- `dl/munic/munic2019.xlsx` (MUNIC 2019)
- `dl/ibge/ref2010.pdf` (nota metodológica do PIB dos Municípios)
- `work/dca/` (DCA 2023 dos 27 entes, Anexos I-D e I-E), `work/obras_openapi.json`, `work/tgov_disc.json`, `work/pncp_p1.json` a `pncp_p4.json`, `work/cnes_api.json`, `work/msc.json`, `work/dca_cg.json`
- `tools/` (scripts usados para ler PDF, planilhas e o esquema da Base dos Dados)
