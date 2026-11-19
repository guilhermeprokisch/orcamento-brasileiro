# Gasto do governo estadual por município: Nordeste (BA, PE, CE, MA, PI, RN, AL, SE)

Pesquisa feita em 19/11/2026. Pergunta: existe dado público que permita saber quanto o **governo
estadual** gasta em cada município (gasto direto: escolas, hospitais, polícia, obras)? A Paraíba
ficou de fora (já resolvida pela API de empenhos com município). O levantamento anterior
(`docs/levantamento-portais-estaduais.md`) só olhou a nota de empenho; aqui foram testados os
outros sete caminhos.

## Como ler

Grau de verificação de cada achado:

- **verificado**: abri o dado (API, CSV ou cabeçalho do arquivo), vi o nome do campo e um valor.
- **descrito**: li numa página, dicionário, especificação da API ou mapa do site, mas não abri o dado.
- **não encontrado**: procurei e não achei.

Limites desta rodada:

- Arquivos acima de ~30 MB não foram baixados. Nos ZIPs grandes da Bahia li só o índice do ZIP e os
  primeiros kB de cada CSV (requisições HTTP parciais). Contagens desses arquivos são de amostra.
- **Ceará Transparente** respondeu 3 páginas e depois passou a devolver 403 e uma página de
  desafio JavaScript anti-robô. Não contornei. A API de dados abertos e os arquivos estáticos
  continuaram acessíveis. O que está só no portal ficou como "descrito".
- **dados.pe.gov.br** não respondeu (timeout) no dia. **transparencia.ba.gov.br** devolveu 503.
- O painel de obras do RN é Power BI: não foi aberto.
- A busca na web rendeu pouco; quase tudo abaixo veio de abrir os portais diretamente.
- dados.ba.gov.br e dados.ma.gov.br servem a cadeia TLS incompleta: é preciso acrescentar o
  certificado intermediário (Sectigo OV R36 na BA, Let's Encrypt YE1 no MA).

Um aviso que vale para todos: quando a folha traz "lotação" ou "unidade", o que vem é o **nome da
unidade** (escola, hospital, companhia da PM), não o código do município. Para chegar ao município
é preciso casar o nome com o Censo Escolar (INEP), o CNES ou extrair a cidade do próprio nome.

---

## BA — Bahia

**1. Folha com lotação — verificado. É o melhor achado do lote.**
- Conjunto "Dados de Servidores": https://dados.ba.gov.br/dataset/dados-de-servidores (fonte RH
  Bahia/SAEB, mensal, "a partir de 2019").
- `DadosServidores.zip` (355 MB): `SERVIDORES.csv` (2,4 GB) com
  `FK_ANO_MES;FK_Cargo_Permanente;FK_Cargo_Temporario;FK_Orgao;FK_Grupo;Carga Horária;matricula;nom_categoria;FK_ExoneracaoInativacao`
  (ex.: `"2019-01";…;"1006-10003289";…;"06566028";"ATIVO"`), e `ORGAO.csv` com
  `cod_orgao_empresa;nom_abreviado_orgao_empresa;nom_orgao_empresa;cod_unidade_organizacional;nom_unidade_organizacional`.
  Exemplos de unidade: `SEC | COLEGIO EST POLIVALENTE DE MIGUEL CALMON`, `P.CIVIL | DT DE SANTANA`,
  `SAEB | POSTO SAC BRUMADO`, `PM-BA | 3ACOMP/PELOT DE POLICIAMENTO 8OBPM`,
  `SESAB | HGRS - SERV. CTRL. INFEC. RELAC. A SAUDE`.
- `RemuneracaoServidores.zip` (692 MB): `REMUNERACAO_VALORES.csv` com
  `FK_Matricula_ANO_MES;Valor Bruto;…;Valor Líquido;Valores Indenizatórios`
  (ex.: `"92024197-2022-11";"2475,8400";…`) e `REMUNERACAO.csv` (órgão de exercício, matrícula,
  CPF mascarado, cargo).
- Junção esperada: `SERVIDORES.matricula + FK_ANO_MES` → `REMUNERACAO_VALORES.FK_Matricula_ANO_MES`;
  `SERVIDORES.FK_Orgao` (= órgão-unidade) → `ORGAO`. Vi os formatos das chaves, **não testei a
  junção inteira**.
- Não há coluna de município: sai do nome da unidade. Inativos aparecem em unidades do FUNPREV.
- Acesso: CSV dentro de ZIP, atualização mensal. Precisa de processamento em fluxo (arquivos de GB).

**2. Obras — verificado, com ressalva forte.**
- https://dados.ba.gov.br/dataset/obras, `Obras.zip` (50 MB, FIPLAN, diário): `VW_INSTRUMENTO_DESPESA.csv`
  (contratos de obra), `VW_PAGAMENTOS_NOTA_ORDEM_BANCARIA.csv`, aditivos, anexos.
- Há colunas `des_localidade`, `Município` e `Municipio`, mas na amostra (703 primeiras linhas)
  `des_localidade` veio **vazia** e `Municipio` trouxe `MONTES CLAROS, MG, BRASIL`, `SAO PAULO, SP,
  BRASIL`, `IBIPORA, PR, BRASIL`: é o **município do credor**, não o da obra. Não serve para
  localizar a obra. O local só aparece no texto de `des_objeto`.

**3. Orçamento regionalizado — verificado só até território.**
- Dicionário de `Despesas.zip` confirma `COD_REGIAO_ORCAMENTO / NOM_REGIAO_ORCAMENTO` ("região ou
  território de identidade"). Nada mais fino encontrado. Portal transparencia.ba.gov.br: 503.

**4. Convênios — verificado.**
- https://dados.ba.gov.br/dataset/convenios-e-parcerias, `ConveniosParcerias.zip` (12 MB):
  `VW_INSTRUMENTO_DESPESA.csv` com `des_localidade` **preenchida** (texto livre; 410 valores
  distintos em 556 linhas: `Salvador`, `ESTADO DA BAHIA`, `Ilhéus`, `Uauá`), `Município` do
  convenente (218 distintos na amostra), `CNPJ_CPF Formatado`, `Val_Inst_Atual`, `val_pago`;
  mais `VW_PAGAMENTOS_NOTA_ORDEM_BANCARIA.csv`. Exercícios de 2013 em diante.
- Também existem `TransferenciasEspeciais.zip` e `EmendasParlamentares.zip` (não abertos).
  "Repasses a municípios" é só ICMS/IPVA/IPI (transferência constitucional).

**5. TCE-BA / TCM-BA — descrito.** O site do TCE-BA tem "Obras e Serviços de Engenharia" e
"Convênios" na área de prestação de informações (voltada a jurisdicionados) e uma página de dados
abertos; não abri. TCM-BA cuida só de municípios; não investigado.

**6. Gasto por unidade — verificado para pessoal** (item 1: folha por escola, hospital, delegacia).
Repasses a escolas: o resultado de busca cita o sistema "Transparência na Escola" da SEC (não
aberto). Contratos de gestão de hospitais estariam em `Contratos.zip` (714 MB, não aberto).

**7. Outros campos de localidade — verificado: não há.** `Empenhos.csv` tem 22 colunas, nenhuma de
local; a cidade aparece às vezes no texto de "Objeto do PED" (ex.: "…JULHO/2023 (BARREIRAS)").

**Conclusão BA:** dá para saber a **folha por unidade** (escola, hospital, unidade policial), mês a
mês desde 2019, e os **convênios** com localidade; obras e o resto só por território de identidade.

---

## PE — Pernambuco

O portal usa painéis Pentaho com uma camada de dados aberta, sem login:
`https://api.pentaho.transparencia.pe.gov.br/pentaho/plugin/cda/api/doQuery?path=/public/OpenReports/Portal_Producao/<Painel>/<Painel>.cda&dataAccessId=<consulta>&outputType=json&param<nome>=<valor>`
(`listParameters` no lugar de `doQuery` lista os parâmetros). É "API" de fato, não documentada.

**1. Folha — verificado: só órgão.**
- Painel de Remunerações (`Painel_Remuneracao`, consulta `sql_jndi`): colunas `r_instituicao,
  r_cpf, r_matricula, r_nome, …, r_cargo, r_funcao, r_remuneracao, …, r_valor_liquido`. Sem lotação.
- Painel de Cadastro dos Servidores (`Painel_cadastro_servidores`): filtro "lotação" tem 22
  valores, todos órgãos (`SECRETARIA DE EDUCACAO`, `POLICIA MILITAR DE PERNAMBUCO`…); há coluna
  `nome_setor`, vazia na amostra.
- TCE-PE `ListaServidores`: só unidade jurisdicionada (descrito).

**2. Obras — verificado.**
- Painel de Obras (ObrasPE): https://transparencia.pe.gov.br/despesas/obras/painel-de-obras-obraspe/
  → `Painel_Obras_Estaduais`, consulta `sql_tabela_principal`. Colunas: descrição, **`municipio_obra`**,
  `orgao_responsavel`, `situacao_obra`, `percentual_medido_obra`, `valor_global_atualizado_obra`,
  `nome_fornecedor`. Ex.: `CRECHE VICÊNCIA | VICÊNCIA | SECRETARIA DE EDUCAÇÃO | ANDAMENTO | 25,09 |
  4.585.845,08`. Anos 2020–2026; 409 obras em 2025; 131 municípios no filtro; atualizado em 01/11/2026.
  Há consultas de detalhe (contrato, serviços, paralisação).
- TCE-PE: `https://sistemas.tce.pe.gov.br/DadosAbertos/Obras!json?Municipio=Garanhuns` devolve
  `Municipio`, `UG`, `LocalExecucao`, `Titulo`, `AnoInicial`; inclui órgãos estaduais (DER,
  Secretaria de Educação): 46 obras, 4 de órgãos do estado. É a base de obras fiscalizadas, não o
  universo. Há também `Remessa_Obra`, `Remessa_ObraExecucao`, `Remessa_ObraGeometria` (descrito).
- "Painel de Obras (TransfereGov)" é Looker Studio (não aberto).

**3. Orçamento regionalizado — não encontrado.** Não achei LOA/execução por região no portal;
dados.pe.gov.br fora do ar no dia.

**4. Convênios — verificado (por credor).**
- "Repasses Financeiros" (`Painel_Convenios_Despesas/Painel_Convenios.cda`, `sql_tabela`): colunas
  `ug_ds_ug, num_emp, nm_credor, cd_credor, classificacao, obs, tipo, vlr_liq, dt_ult_liquidacao`;
  anos 2011–2026. Sem coluna de município: sai do CNPJ do convenente. (Vi as colunas; minha
  consulta de teste voltou sem linhas.)
- FEM (`Painel_Fem`): tem filtro e gráfico por município e região (repasse a prefeituras).
- Painel de Convênios e Painel de Parcerias são Looker Studio; e-Fisco GTV tem consulta de
  parcerias (não abertos). TCE-PE `Convenios` não traz convenente (descrito).

**5. TCE-PE — verificado** (item 2). `DespesasEstaduais` não tem localidade (descrito).

**6. Gasto por unidade — verificado para hospitais.**
- "Repasse para OSS e Unidades de Saúde" (`Painel_Repasse_OSS`, `select_tabela_repasses`): colunas
  `num_ordem_bancaria, finalidade_ordem_bancaria, cd_sigla_nm_credor_planilha_vinculada_oss,
  cd_nm_credor, cd_ds_fonte_recurso, dt_lancamento, vlr_ordem_bancaria`. Ex.:
  `2025OB000257 | 10583920000133 - HTRI | 10583920001024 - HOSPITAL REGIONAL EMÍLIA CÂMARA |
  2025-01-08 | 484873.26`. 34 unidades em 2025 (UPAEs, hospitais regionais); anos 2008–2026.
  Município pelo CNPJ da filial ou pelo nome.
- Repasse a escolas: não encontrado.

**7. Outros campos — verificado: não há.** O painel de despesas detalhadas não tem parâmetro de local.

**Conclusão PE:** dá para saber **obras por município** (2020+) e **repasses a hospitais geridos
por OSS por unidade** (2008+); convênios pelo CNPJ; folha só por órgão.

---

## CE — Ceará

**1. Folha — verificado: só órgão.**
- API oficial: `https://api-dados-abertos.cearatransparente.ce.gov.br/transparencia/servidores/salarios?year=2025&month=6&page=1`
  (Swagger em `/api-docs/v1/swagger.yaml`). Campos: `nome_servidor, total_proventos,
  proventos_liquidos, dsc_cargo, codigo_orgao, descricao_orgao, sigla, situacao_funcional`.
  185.849 registros em 06/2025, 100 por página. Sem lotação.
- O inventário de dados abertos lista "Informações dos Servidores 2015–2025" (SEPLAG); não abri
  (portal bloqueado).

**2. Obras — descrito.** O mapa do site tem `/portal-da-transparencia/obras/edificacoes` e
`/obras/rodoviarias`. Não abri (403/desafio anti-robô).

**3. Orçamento regionalizado — descrito; é a pista mais forte do estado.** O mapa do site tem
**`/portal-da-transparencia/investimentos-municipio`** e `/investimentos-macrorregioes`, além de
`/ppa`. A página existe pelo menos desde 2022 (há cópia no Internet Archive de 02/08/2022, que não
consegui ler daqui). Não vi colunas nem valores. Precisa de um navegador comum.

**4. Convênios — verificado (por credor).**
- `…/transparencia/contratos/convenios?page=1&data_assinatura_inicio=01/01/2025&data_assinatura_fim=31/01/2025`:
  122 convênios no mês. Campos: `descricao_nome_credor` (`PREF MUNIC DE HORIZONTE`),
  `plain_cpf_cnpj_financiador`, `descricao_objeto` ("…Município de HORIZONTE"),
  `valor_atualizado_concedente`, `calculated_valor_empenhado`, `calculated_valor_pago`,
  `cod_gestora`. Sem campo de município: sai do CNPJ ou do texto.
- O mapa do site tem ainda páginas de transferências a municípios, a consórcios e a entidades.

**5. TCE-CE — descrito.** A API de dados abertos (`api-dados-abertos.tce.ce.gov.br/sim/`) é a base
municipal herdada do TCM. Não achei despesa estadual por localidade.

**6. Gasto por unidade — descrito.** Existe `/portal-da-transparencia/contratos/contratos-de-gestao`
(hospitais geridos por OS); não aberto. Notícia do MPCE cita um portal de manutenção e reforma das
escolas estaduais (não aberto).

**7. Outros campos — verificado: não há** na API de contratos (`cod_gestora`, `cod_orgao`, credor).

**Conclusão CE:** verificado só convênios pelo CNPJ e a região administrativa do empenho; o portal
anuncia "investimentos por município" e obras, que ficaram **sem abrir** por bloqueio anti-robô.

---

## MA — Maranhão

**1. Folha — verificado: só órgão.**
- https://dados.ma.gov.br/?q=dataset/folha-de-pagamento-2026 → `FOLHA_2026_10.csv` (16,6 MB):
  `ano_pagamento;mes_pagamento;orgao;nome;cpf;cargo;funcao;natureza;total_vantagens;…;situacaofuncional`.
- Portal (`/app/v2/pessoal/remuneracao`, 2018–2026, exporta CSV/XLSX): mesmas colunas, por órgão.

**2. Obras — verificado.**
- `https://transparencia.ma.gov.br/app/v2/obras/export?exportTipo=csv&ano=all&ug=all&localidade=all&contratada=all&status=all`
  (1,3 MB). Colunas: `Ug, Codigo da UG, **Localidade**, CNPJ Contratada, Contratada, Objeto do
  Contrato, Nº do Contrato, Ordem de Serviço, Contrato + Aditivo, Valor Medido, Saldo, Progresso,
  Data de Inicio, Previsão de Entrega, Status…`.
- 4.135 obras, R$ 16,3 bi em contratos; 213 localidades. **Só uma UG: Secretaria da Infraestrutura.**
  1.111 linhas têm localidade genérica `MARANHÃO` (conservação de rodovias); depois `SÃO LUÍS` (580),
  `PAÇO DO LUMIAR` (185), `IMPERATRIZ` (117). Início concentrado em 2022–2026. Dados até 20/10/2026.

**3. Orçamento regionalizado — não encontrado.** O mapa "Presença do Estado" da página inicial
mostra serviços (hospitais etc.), não despesa.

**4. Convênios — descrito.** `/app/v2/transferencia` (recebidas/realizadas) é formulário dinâmico;
não abri o resultado. TCE-MA tem "Convênio Web" (não aberto).

**5. TCE-MA — descrito.** `https://tce-api.apps.tcema.tc.br/v3/api-docs` lista 307 caminhos
(`sincfolha`, `sincfiscal`, `empenhocontrato`…), todos com cabeçalho `Authorization`: exige
credencial, não testei. "Obras Paralisadas" (`finger.apps.tcema.tc.br`) não aberto.

**6. Gasto por unidade — não encontrado.**

**7. Outros campos — não encontrado.**

**Conclusão MA:** dá para saber **obras da Secretaria da Infraestrutura por município** (CSV);
folha só por órgão; o resto não achei.

---

## PI — Piauí

API documentada: https://api.transparencia.pi.gov.br/docs/ (especificação em `/schema/`).

**1. Folha — verificado: só órgão.** `/api/v2/servidores/2026/9/`: 140.404 registros; campos
`orgao_nome, cargo_nome, categoria, remuneracao_bruta…`. Sem lotação.

**2. Obras — verificado, sem campo de município.**
- `/api/v1/obras/2025/1/12`: 638 obras; exercícios 2023–2026. Campos: `unidade_gestora,
  objeto_siafe, contrato_siafe, contratado_cnpj, execucao_fisica, status, data_da_os…`;
  `/api/v1/obras/{id_acao}/detalhamento` traz medições (`mensurado`, `realizado`) por atividade.
- O município só aparece no texto: `"PAVIMENTAÇÃO EM PARALELEPÍPEDO NO MUNICIPIO DE VÁRZEA GRANDE -
  PI (7.382,25M²)"`. Dá para extrair por expressão regular, com erro.
- TCE-PI ObrasWeb (mural público): https://sistemas.tce.pi.gov.br/obrasweb/mural/ tem filtros
  "tipo de órgão" (Estadual/Municipal) e **Município** (225), e colunas `Órgão/UG, Executante,
  Descrição, Dt Início, Valor Previsto, Valor Pago, Situação`. Vi a primeira página (órgãos
  estaduais presentes); é tela JSF, não achei exportação.

**3. Orçamento regionalizado — não encontrado** (não pesquisei a fundo a LOA por território).

**4. Convênios — verificado (por credor).**
- `/api/v1/transferencias-realizadas/2025/`: 78 termos; `nome_proponente, cnpj_proponente,
  nome_concedente, valor_total, tipo_termo, objeto`. Sem município.
- `/api/v1/emendas-estaduais/2026/`: 1.438 emendas com `localidade_beneficiada` em texto livre
  (`"MUNICÍPIO DE ALTO LONGÁ - PI E REGIÕES ADJACENTES"`, `"Estado do Piauí"`).

**5. TCE-PI — verificado em tela** (ObrasWeb, item 2).

**6. Gasto por unidade — não encontrado.**

**7. Outros campos — verificado: enganoso.** `/api/v1/contratos/…` tem campo `municipio`, mas veio
`Teresina` em 100 de 100 registros da amostra: é a sede do órgão.

**Conclusão PI:** dá para saber **obras** com município por texto (API) ou por filtro (tela do
TCE-PI) e **emendas** com localidade em texto; folha só por órgão.

---

## RN — Rio Grande do Norte

Atenção ao endereço: `https://www.transparencia.rn.gov.br/` funciona; sem `www` o certificado não
confere.

**1. Folha — descrito: só órgão.** https://remuneracao.rn.gov.br/ (API em
`api.remuneracao.rn.gov.br`, com `ObterPorOrgao` e `ExportarPorOrgao`). O dicionário oficial
(PDF da SEAD) lista `Nome, Órgão, Cargo/Função, Carga Horária, Remuneração do Mês…`. A chamada de
teste devolveu erro 500; não vi dado.

**2. Obras — descrito.** `/obras-e-execucao` é um relatório Power BI embutido. Não abri.

**3. Orçamento regionalizado — não encontrado.** dados.rn.gov.br (CKAN) tem 0 conjuntos (verificado).

**4. Convênios — descrito.** http://convenios.control.rn.gov.br/conveniorelsite.aspx: formulário
com filtros por CNPJ, nome, "beneficiários municípios / não municípios", órgão e situação, e botão
"Download em CSV". Vi o formulário, não enviei.

**5. TCE-RN — descrito.** `https://apidadosabertos.tce.rn.gov.br/swagger/docs/v1`: 11 caminhos
(empenhos, liquidações, pagamentos, contratos e licitações por unidade jurisdicionada). Sem obras
e sem campo de local. `/Transparencia/ListaSiaiObras` lista obras sem coluna de município.

**6. Gasto por unidade — não encontrado.**

**7. Outros campos — não encontrado.**

**Conclusão RN:** **não achei caminho verificado.** Candidatos a testar com navegador: CSV de
convênios concedidos e o painel Power BI de obras.

---

## AL — Alagoas

A API pede o cabeçalho `X-Requested-With: XMLHttpRequest`. Leiautes em
`/portal/download-de-dados/…`; arquivos em `/media/arquivo/<tabela>-<ano>.zip`.

**1. Folha — verificado: só órgão.** `/pessoal/json-servidores/?limit=3&offset=0&mes=6&ano=2026`:
46.210 ativos; campos `codigo_orgao, descricao_orgao, nome, total`. O leiaute do arquivo
(`servidor-ativo`) tem CNPJ do órgão, vínculo, cargo, função; sem lotação.

**2. Obras — verificado: não é por município.** `/obras/json-obras-publicas/` devolve empenhado,
liquidado e pago em obras **por unidade gestora** (16 UGs em 2025). A URL da documentação
(`/licitacao/json-obras-publicas`) dá 404.

**3. Orçamento regionalizado — verificado só até região.** No `documento_ne-2023.zip` (3 MB,
107.208 notas) a coluna `PI` (localizador) tem 11 códigos; `000210` responde por 94.107 notas e
`000204` por 13.002. É a região de planejamento que o levantamento anterior já apontou.

**4. Convênios — descrito (por credor).** Leiaute de `convenios`: CNPJ do concedente, CNPJ e
descrição do beneficiado, tipo do beneficiado, valor, partida e contrapartida. Sem município.

**5. TCE-AL — descrito.** O site tem página de obras e painéis Power BI; não abri.

**6. Gasto por unidade — não encontrado.**

**7. Outros campos — verificado: não serve.** `LOCAL_ENTREGA` da nota de empenho é texto livre:
1.934 valores distintos em 2023; os mais comuns são vazio (18.214), `IMA` (9.933), `Maceió`
(9.274), `MACEIÓ` (7.930), `FOLHA` (3.199), siglas de órgãos e endereços. É o local de entrega no
órgão, não o lugar do gasto.

**Conclusão AL:** **não achei caminho por município**; só a região de planejamento do empenho e
os convênios pelo CNPJ do beneficiado.

---

## SE — Sergipe

**1. Folha com lotação — verificado.**
- API que o portal usa: `https://api.transparencia.se.gov.br/api/recursos-humanos/remuneracao-servidores-ativos?ano=2025&mes=3&idOrgao=217&page=1&limit=10`
  (`idOrgao` ou `cnpj` obrigatório; lista em `…/remuneracao-servidores-ativos/orgaos`, 46 órgãos;
  há `…/export`).
- Campos: `nomeServidor, cargoServidor, tipoVinculo, orgaoNome, **lotacaoServidor**, dataAdmissao,
  cargaHoraria, regimeServidor, valorBruto, valorDescontos, valorLiquido`.
- Exemplos de lotação na SEED: `C.E. SAO JOSE - POCO VERDE`, `E.E. JOAO RIBEIRO - LARANJEIRAS`,
  `C.E. FREI INOCENCIO - N. SRA. DO SOCORRO`, `DIRETORIA REGIONAL DE EDUCACAO - DR-02`,
  `ESC EST ELEITE CEZAR FONTES PRATA` (nem toda lotação traz a cidade).
- SEED, 03/2025: 10.945 servidores, R$ 70.686.990,61 de valor bruto. Anos 2022–2026 na tela.
- A API documentada (`https://api.v1.transparencia.se.gov.br/openapi.json`,
  `/v1/recursos-humanos/folha-pagamento`) tem `lotacaoServidor` no esquema, mas respondeu 422
  (banco ocupado) nas três tentativas.

**2. Obras — verificado.**
- `https://api.sedurbs.se.gov.br/obras` (página pública: https://sedurbi.se.gov.br/transparencia/obras/).
  Campos: **`Municipio`**, `Objeto`, `empresa`, `VlrOriginalContrato`, `VlrAtualContrato`,
  `VlrFaturado`, `VlrPago`, `latitude`, `longitude`, `status_obra`, `medicoes`, `financeiros`.
  Ex.: `Poço Verde | reforma do Ginásio de Esportes… | R$ 2.881.182,08`. 24 páginas de 8
  (cerca de 190 obras). **Só obras da SEDURBI.**

**3. Orçamento regionalizado — não encontrado.**

**4. Convênios — descrito.** `/Convenios/Realizadas` no portal; não abri o dado.

**5. TCE-SE — descrito.** Há uma API (`/visualizadorRelatorios/swagger`), especificação mínima;
não explorei.

**6. Gasto por unidade — verificado para pessoal** (item 1: folha por escola e unidade).

**7. Outros campos — descrito: não há.** Os esquemas de empenho, pagamento e contrato da API v1 não
têm localidade.

**Conclusão SE:** dá para saber a **folha por unidade de lotação** (2022+, API) e as **obras da
SEDURBI por município**, com coordenadas.

---

## Tabela-resumo

| UF | Melhor caminho | O que cobre | Granularidade | Acesso | Verificação |
|---|---|---|---|---|---|
| BA | dados.ba.gov.br "Dados de Servidores" (SERVIDORES + ORGAO + REMUNERACAO_VALORES); convênios com `des_localidade` | Folha (2019+); convênios (2013+) | Unidade (escola, hospital, unidade policial), sem código de município; convênio com localidade em texto | CSV em ZIP (355 MB + 692 MB) | Verificado por amostra (cabeçalhos e primeiras linhas; junção não testada) |
| SE | API de remuneração com `lotacaoServidor`; API de obras da SEDURBI | Folha (2022+); obras de uma secretaria | Unidade de lotação (muitas com a cidade no nome); município e coordenadas nas obras | API JSON | Verificado |
| PE | Painéis Pentaho (CDA): ObrasPE com `municipio_obra`; repasses a OSS por unidade de saúde; TCE-PE `Obras` | Obras (2020+); hospitais sob OSS (2008+) | Município (obras); unidade de saúde com CNPJ | API JSON não documentada | Verificado |
| MA | Exportação CSV de obras com `Localidade` | Obras da Sec. de Infraestrutura (4.135 obras, R$ 16,3 bi) | Município (27% das linhas genéricas, "MARANHÃO") | CSV | Verificado |
| PI | API de obras (município no texto do objeto); TCE-PI ObrasWeb com filtro de município; emendas com localidade | Obras (2023+); emendas | Município por texto livre (API) ou por filtro (tela) | API JSON; tela (TCE) | Verificado (API); tela vista na 1ª página |
| CE | Convênios pela API (CNPJ da prefeitura). Página "Investimentos por município" existe, não aberta | Convênios; investimentos e obras a confirmar | Credor (convênios); região administrativa (empenho) | API JSON; portal só com navegador | Convênios verificado; investimentos e obras só descritos (bloqueio anti-robô) |
| AL | Nenhum por município. Região de planejamento no empenho; convênios pelo CNPJ | Tudo, só por região | Região (88% das notas num código só) | ZIP anual + API | Verificado que folha, obras e `LOCAL_ENTREGA` não servem |
| RN | Nenhum verificado. Candidatos: CSV de convênios concedidos, Power BI de obras | — | — | Formulário ASP.NET; Power BI | Só descrito |

Folha por órgão apenas (sem lotação), verificado: CE, PE, MA, PI, AL. No RN, descrito pelo dicionário.
