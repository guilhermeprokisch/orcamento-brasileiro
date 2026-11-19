# Gasto do governo estadual por município: Norte e Centro-Oeste

Estados: AM, PA, AC, RO, RR, AP, TO, GO, MT, MS e DF (no DF, Região Administrativa).
Pesquisa feita em 19/11/2026, abrindo os portais, APIs e arquivos. Complementa
`docs/levantamento-portais-estaduais.md`, que só olhou a nota de empenho.

## Como ler

Grau de verificação de cada achado:

- **verificado**: abri o dado, vi o nome do campo e um valor de exemplo.
- **descrito**: vi o campo no código do portal, no cabeçalho de uma tabela ou numa descrição, mas não abri um registro.
- **não encontrado**: procurei no portal e não achei. Não quer dizer que não exista.

Os sete caminhos pedidos: (1) folha com lotação, (2) obras, (3) orçamento regionalizado,
(4) convênios e transferências voluntárias, (5) Tribunal de Contas, (6) gasto por escola ou
hospital, (7) campo de localidade perdido no empenho.

Limites desta rodada:

- **Tribunais de Contas (caminho 5) ficaram quase sem cobertura.** Só vi os links do Geo-Obras do TCE-MT e do TCE-GO nos portais; não abri os dados. TCM-GO e TCM-PA não foram investigados.
- **LOA/PPA regionalizados (caminho 3)** só foram abertos no AM, DF e RO. Nos demais, não procurei os anexos em PDF das leis orçamentárias.
- A busca na web rendeu pouco; quase tudo veio de abrir os portais diretamente.
- Bloqueios encontrados: GO (o catálogo CKAN passa a devolver desafio anti-robô depois de poucas requisições por `curl`; li pelo navegador de busca), MT (consultas de pessoal com reCAPTCHA v3, não consultei), AM (API da SEFAZ com parâmetros cifrados, só pelo navegador), AP (folha deu 504), TO (certificado inválido com `www.`; sem `www.` abre no navegador).

## Tabela-resumo

| UF | Melhor caminho | O que cobre | Granularidade | Acesso | Verificação |
|---|---|---|---|---|---|
| GO | Mapa de Obras (SEINFRA) + merenda por escola + folha com unidade | Obras de vários órgãos (R$ 19,3 bi pagos), repasse de merenda, folha por unidade | Município (obras, merenda); unidade (folha) | JSON embutido na página + API; CKAN/datastore | Verificado |
| AM | Folha com lotação + e-Obras + convênios de saída | Folha por escola/unidade de saúde/quartel; obras com valor por município; convênios com prefeituras | Unidade (folha); município (obras, convênios); região (orçamento, 84% "Estado") | API REST aberta (folha, obras); tela (convênios, orçamento) | Verificado |
| AC | Obras com município | Obras (166 registros, valor e valor pago) | Município | JSON via POST com token da página | Verificado (obras); folha com "Lotação" só descrita |
| RR | Mapa de Obras | Obras (204, R$ 5,2 bi contratados) | Município | Só tela | Verificado na tela |
| PA | API de obras públicas | Obras 2009–2024 (2025 quase vazio) | Região de integração + município, no detalhe da obra | API REST aberta | Verificado, com dúvida de qualidade |
| MT | Mapa de obras da SINFRA + SIGCon | Obras de infraestrutura; convênios por proponente | Município (obras); beneficiário (convênios) | API REST aberta (obras); tela com exportação (convênios) | Verificado |
| RO | Convênios de saída + transferências voluntárias | Repasses a prefeituras e entidades | Beneficiário (prefeitura, com CNPJ) | Tela com POST e token | Verificado |
| MS | Emendas parlamentares estaduais | Emendas (valor por beneficiário) | Município | CSV no CKAN | Verificado |
| DF | Subtítulo do empenho | Cerca de 3% do empenhado tem RA; 94% é "Distrito Federal" | Região Administrativa | ZIP anual (CSV) | Verificado |
| AP | Painel de obras (Looker Studio) | Obras (R$ 389 mi contratados) | Sem coluna de município (só no texto do objeto) | Tela com download CSV | Verificado na tela |
| TO | Não achei caminho | — | — | Portal Vaadin, só tela | Não encontrado |

Nenhum dos onze publica a folha com município de lotação. Em AM e GO a folha traz a unidade
(escola, hospital, delegacia), o que permite chegar ao município cruzando com INEP e CNES.

---

## Rondônia (RO)

**1. Folha.** `GET https://transparencia.ro.gov.br/Pessoal/Download?Ano=2026&MesInicial=9&ContentTypeFile=CSV`
(9,2 MB, 64.452 linhas; anos 2016–2026). Campos: `Servidor, SecretariaOrgao, CargoFuncaoEmprego, DataAdmissao, DataInativo, DataDesligamentoOuExoneracao, CargaHorariaSemanal, SalarioBruto, SalarioLiquido, Descontos`.
`SecretariaOrgao` tem 106 valores e mistura órgão com grupo de folha: "SEDUC - SEDUC/Fundeb-Efetivos" (11.978 linhas), "PM - POLICIA MILITAR". Só a saúde traz unidade: "SESAU - HOSPITAL REGIONAL DE CACOAL", "SESAU - HOSPITAL DE BASE". Sem município. **Verificado.**

**2. Obras.** A página inicial e o mapa do site do portal não têm seção de obras. Há um link para `https://infra.der.ro.gov.br/acessoainformacao`, que não abri. **Não encontrado.**

**3. Orçamento regionalizado: "Presença nos municípios".** `https://transparencia.ro.gov.br/despesa/presenca-municipios`, com `POST /despesa/filtrarpresencamunicipios` (campo `EXERCICIO` e o token anti-falsificação da própria página). Anos 2010–2024. Devolve 52 municípios com Empenhado, Liquidado, Pago; cada linha tem `data-cod-municipio` (ex.: 110001). O detalhe por função vem de `POST /Despesa/FiltrarPresencaMunicipiosPorFuncao` (`codMunicipio`, `ano`). **Verificado**, com três ressalvas:
- O total de 2023 é R$ 295 milhões empenhados, perto de 2% do orçamento estadual. Porto Velho aparece com R$ 462 mil. Não é o gasto do estado em cada cidade; parece ser só o que foi repassado ou localizado por município.
- Os valores de 2023 e 2024 são incoerentes (liquidado e pago negativos, "a liquidar" maior que o empenhado). 2016 é coerente.
- A página informa "última atualização de despesas dos municípios: 23/04/2024".

**4. Convênios.**
- `https://transparencia.ro.gov.br/convenios/convenios-de-saida` (`POST /convenios/filtrartransferencias`, 2017–2026, fonte: sistema PACTO): Beneficiário, Número/Instrumento, Objeto, Valor total previsto, Valor repassado/data, Vigência. Exemplo: "MUNICÍPIO DE BURITIS | CNV Nº 95/2023/PGE/DER-RO | R$ 200.000,00 repassado em 27/12/2023". **Verificado.**
- `https://transparencia.ro.gov.br/transferenciaintergovernamental` (`POST .../filtrointergovernamental`, 2018–2026, tipo Obrigatória ou Voluntária): Unidade Gestora, Favorecido com CNPJ, Nº Documento, Valor Mês. Exemplo: "04279238000159 - PREFEITURA MUNICIPAL DE JARU | 2025NL000892 | R$ 300.000,00". **Verificado.**

**5. TCE-RO.** Não investigado.

**6. Escolas e hospitais.** A página de educação aponta para `http://pactopelaaprendizagem.seduc.ro.gov.br/escolas` (escolas e matrículas; não abri). Não achei repasse por escola. **Não encontrado.**

**7. Empenho.** Nada novo.

**Conclusão:** dá para saber os repasses do estado a cada prefeitura (convênios e transferências voluntárias) e a folha de alguns hospitais; a página "presença nos municípios" não serve como gasto do estado por cidade.

## Amazonas (AM)

**1. Folha.** API aberta `https://www.transparencia.am.gov.br/wp-json/transparencia/v1/remuneracoes?ano=2026&mes=9&orgaoCodigo=25&page=1` (20 por página). Campos: `orgaoSigla, orgaoNome, competenciaAno, competenciaMes, lotacao, cargo, funcao, vinculo, cargaHoraria, remuneracaoLegalTotal, descontosLegais, liquidoDisponivel`. A `lotacao` é a unidade: "ESC.EST.OLGA FALCONE", "COORD.DISTRITAL DE EDUCACAO 07" (SEDUC, 32.764 registros em 09/2026); "UNID.P.ATEN.UPA 24-TABATINGA", "U.M. CAREIRO DA VARZEA" (SES, 18.432); "33.GBM - NOVO AIRAO", "7º GBM HUMAITA" (bombeiros). Códigos de órgão em `/orgaos`; data de carga em `/publico/atualizacao` (13/11/2026). Há exportação assíncrona em `POST /exportacoes`, que não testei. Sem campo de município: é preciso casar o nome da unidade com INEP e CNES. **Verificado.**

**2. Obras.** Mapa e-Obras da SEINFRA, `https://eobras.am.gov.br/obras-gov-map/#/map`. API aberta: `POST https://eobras.am.gov.br/obrasgov-map-backend/source/seinfra/contract/list` (o corpo é o filtro do mapa, com período e listas vazias). Para 2025–2026 devolveu 381 contratos somando R$ 7,3 bi. Campos: `name` (contrato), `description`, `address` (município: "Manaus" 107, "Itacoatiara" 22, "A Definir" 31; 61 valores), `amount`, `status`, `company`, `contractor` (órgão), `coordinates`. Detalhe em `/contract/{id}` (`originalValue`, `totalMeasuredValue`, `paidAmount`) e rateio em `/contract/{id}/municipios` (`nmMunicipio`, `vlMunicipio`). **Verificado.**

**3. Orçamento regionalizado (o "localizador").** CSV de execução em `https://sistemas.sefaz.am.gov.br/transparencia/dadosabertos/execucao` (2021–2026; o de 2026 tem 48 MB e 68.896 linhas). A API pede parâmetros cifrados (`ek`, `ed`) e responde 500 por `curl`; só funciona pelo navegador. Campos `codLocalizador` e `desLocalizador`, com 11 valores. Do empenhado de 2026 (R$ 32,8 bi): "0001 Estado" 83,7%, "0011 Região Metropolitana" 13,7%, e nove sub-regiões (Baixo Amazonas, Madeira, Alto Solimões etc.) com 0,1% a 0,7% cada. É região, não município, e quase tudo cai em "Estado". **Verificado** (li o arquivo na memória do navegador, sem salvar).

**4. Convênios.** `https://sistemas.sefaz.am.gov.br/transparencia/convenio/saida/execucao` (2010–2026; modalidade "Convênio com Prefeitura" ou "com ONG"; consulta por convenente; botão "Exportar Dados"). Exemplo de 2025: "04.329.736/0001-69 - PREFEITURA MUNICIPAL DE PARINTINS | empenhado 13.188.367,24 | pago 9.412.046,96". Só tela (mesma API cifrada). **Verificado na tela.** Há também `dadosabertos/emenda` (emendas parlamentares), que não abri.

**5. TCE-AM.** Não investigado.

**6. Escolas e hospitais.** Só pela lotação da folha (item 1). Não achei repasse por escola nem custo por hospital.

**7. Empenho.** A consulta de despesas tem o filtro "Localizador", com as mesmas 11 regiões do item 3.

**Conclusão:** dá para saber a folha por unidade (e daí por município, com cruzamento), as obras e os convênios com prefeituras por município; o orçamento geral só por região, com 84% em "Estado".

## Distrito Federal (DF)

**1. Folha.** `https://www.transparencia.df.gov.br/arquivos/portal-dados-abertos/Remuneracao_{2013..2026}.zip` (224–317 MB por ano; um CSV de ~92 MB por mês). Li o cabeçalho por requisição parcial: `NOME;CPF;[órgão];CARGO;FUNÇÃO;SITUAÇÃO;MÊS;ANO;CÓDIGO DO ÓRGÃO;MATRÍCULA;REMUNERAÇÃO BÁSICA;...;BRUTO;LÍQUIDO`. **Sem lotação (verificado).** A consulta na tela (`#/servidores/remuneracao`, total bruto de 09/2026: R$ 3,70 bi) tem uma coluna opcional "Lotação", definida no código do portal como "Setor do órgão onde o servidor está atuando". Não consegui abrir um valor. **Descrito.**

**2. Obras.** O portal não tem rota de obras. **Não encontrado.**

**3. Orçamento regionalizado.**
- **O painel por Região Administrativa não é o que parece.** `GET /api/v2/despesas-ras?exercicio=2026` devolve 31 linhas como "ADMINISTRAÇÃO REGIONAL DE CEILÂNDIA | empenhado 13.031.605,02". É a despesa de cada Administração Regional como unidade gestora (R$ 2,7 a 15,8 milhões cada), não o gasto do GDF naquela região. **Verificado** (resposta lida na página inicial do portal; a API exige o cabeçalho `x-client-id` gerado pelo navegador).
- **Subtítulo do empenho.** Em `Despesa_2026.zip`, arquivo `Despesa_Empenho_2026.csv` (81.687 empenhos, R$ 33,9 bi de valor inicial), a localidade é o final do campo `SUBTÍTULO`. Distribuição do valor: "DISTRITO FEDERAL" 93,6%; "PLANO PILOTO" 1,8%; sem sufixo 1,7%; "DF ENTORNO" 0,8%; demais RAs somadas (Vicente Pires, Águas Claras, Planaltina, Ceilândia etc.) perto de 1%. **Verificado.**

**4. Convênios.** O código do portal tem as rotas `/convenio/despesa` e `/convenio/entidades-beneficiadas`. Não abri. **Descrito.**

**5. TCDF.** Não investigado.

**6. Escolas e hospitais.** O menu tem "Escala dos Profissionais de Saúde" e a rota `/prestando-contas/organizacoes-sociais-saude`; não abri. Há subtítulos terminados em "PDAF" (241 empenhos, R$ 18,5 milhões em 2026), mas não achei o repasse do PDAF por escola. **Não encontrado.**

**7. Campo perdido no empenho.** `LOCAL ENTREGA`, endereço em texto livre, preenchido em 63% dos empenhos de 2026. Exemplo: "GRANJA DO TORTO, LOTE 04, 3º ANDAR - FAPDF". É o endereço de entrega do órgão, não necessariamente o lugar do gasto. **Verificado.**

**Conclusão:** só cerca de 3% do empenhado tem Região Administrativa identificada (94% é "Distrito Federal" e o resto são sufixos genéricos); o painel por RA do portal cobre apenas o orçamento das próprias administrações regionais.

## Goiás (GO)

O catálogo `dadosabertos.go.gov.br` bloqueia `curl` depois de poucas requisições (desafio anti-robô). Os dados abaixo foram lidos pela API `datastore_search` através da ferramenta de leitura de páginas.

**1. Folha.** Conjunto `folha-de-pagamento` (SEAD), CSV mensal de ~73 MB, 2012–2026, com API datastore. Outubro de 2026 tem 167.794 registros. Campos de lotação: `NOME_ORGAO_SEC`, `NOME_DEPTO_ORGAO`, `NOME_UNIDADE_ORGAO`; valores em `VALR_PROVENTO`, `VALR_LIQUIDO`. Exemplos de unidade: "coordenação regional de saúde pireneus - anápolis", "3ª delegacia regional de polícia civil de anápolis", "unidade local - uruaçu", "hospital de urgências de goiânia dr. valdemiro cruz". Inativos caem em "gerencia de folha de pagamento de benefícios". Sem campo de município. **Verificado.**
`https://dadosabertos.go.gov.br/dataset/folha-de-pagamento`

**2. Obras.** `https://mapadeobras.seinfra.go.gov.br/mapas`: a página traz os dados embutidos (`var locations`) e tem `GET /api/filter`. São 2.961 projetos com `orgao`, `municipio`, `nome_projeto`, `situacao_obra`, `estagio_execucao_percentual`, `valor_total_do_projeto`, `valor_pago`, `area_tematica`, `latitude`, `longitude`. Somas: R$ 38,6 bi de valor total e R$ 19,3 bi pagos. 246 municípios (Goiânia 291, Aparecida de Goiânia 98, Anápolis 90). Órgãos: GOINFRA 1.260, SEDUC 1.026, AGEHAB 241, SANEAGO 89, Polícia Civil 40, UEG 38. **Verificado.** O portal também aponta um painel Power BI "Obras Públicas", que não abri.

**3. Orçamento regionalizado.** Há `https://ppa.go.gov.br/` e o conjunto `ppa-financeiro`; não abri. **Não encontrado.**

**4. Convênios.** Conjunto `transferencias-voluntarias` (CGE), CSV mensal, 2003–2026. Campos: `Unidade Orcamentaria`, `Modalidade de Aplicacao`, `Elemento Despesa`, `CPF/CNPJ`, `Nome/Razao Social do Credor`, `DESCRICAO`, `Data do Repasse`, `Valor do Pagamento (R$)`. Maio de 2026 tem 1.280 registros. O município aparece no texto da descrição nas emendas ("Emenda Parlamentar Impositiva número 64 Município GOIANIA ..."); fora isso, sai do CNPJ do credor. **Verificado.** A planilha "Convênios Concedidos" do portal é só um índice de links por órgão.

**5. Tribunais de Contas.** O portal aponta `https://geoobras.tce.go.gov.br/cidadao/`; não abri. TCM-GO não investigado. **Descrito.**

**6. Escolas e hospitais.** Conjunto `merenda-escolar` (SEDUC): `Ano, COORD. REGIONAL, MUNICIPIO, ESCOLA, CODIGO ESCOLA, FNDE, PROTEGE, TOTAL`; 3.778 registros. Exemplo: "2022 | CRE-ÁGUAS LINDAS | ÁGUAS LINDAS DE GOIÁS | COLÉGIO ESTADUAL PAULO FREIRE | 52077411 | R$ 356.579,32". **Verificado.** Existem ainda `transporte-escolar`, `cofinanciamento-da-atencao-primaria`, `cofinanciamento-estadual-da-assistencia-social-repasses-aos-municipios-2023-2024` e a página de Organizações Sociais (contratos de gestão dos hospitais); não abri.

**7. Empenho.** `empenhos` tem 13 campos, nenhum de localidade. **Verificado.**

**Conclusão:** dá para saber obras de quase todos os órgãos por município (R$ 19,3 bi pagos), merenda por escola e a folha por unidade; é o estado mais completo do lote.

## Mato Grosso (MT)

**1. Folha.** `https://consultas.transparencia.mt.gov.br/pessoal/servidores_ativos/` e páginas vizinhas usam reCAPTCHA v3; não consultei. **Não verificado.**

**2. Obras.** `https://sinfralog.sinfra.mt.gov.br/obras-gov-map/#/map`, o mesmo produto do AM. `POST https://sinfralog.sinfra.mt.gov.br/obrasgov-map-backend/source/sinfra/contract/list` devolveu 384 contratos para 2025–2026. O campo `address` traz o município ou a lista deles: "CUIABÁ" (42), "PEDRA PRETA, RONDONÓPOLIS", "CUIABÁ, VÁRZEA GRANDE". Só obras da SINFRA. **Verificado.** Outros caminhos vistos e não abertos: conjunto `listagem-de-obras` em `https://dadosabertos.mt.gov.br`, mapas ArcGIS em `mapas.sinfra.mt.gov.br` e `https://consultas.transparencia.mt.gov.br/compras/obras/`.

**3. Orçamento regionalizado.** O CSV de despesa (`.../dados_abertos/despesa/Despesa_2026.csv`) tem 42 campos e nenhum de localidade. **Verificado** pelo cabeçalho. **Não encontrado.**

**4. Convênios.** `https://transp.sigcon.seplan.mt.gov.br/index_.php` (SIGCon, 2000–2026, com exportação CSV): Concedente, Proponente, Objeto, Processo, Número, Ação, Valor do Convênio, Vigência. Exemplo: "SEDEC | PREFEITURA MUNICIPAL DE JAURU | Realização da Cavalgada de Jauru 2026 | 671.672,00". **Verificado na tela.** O portal novo (`https://transparencia.cge.mt.gov.br/convenios`) usa uma API que exige chave (401).

**5. TCE-MT.** `https://geoobras.tce.mt.gov.br/cidadao` (Geo-Obras, obras do estado e dos municípios). A aplicação abriu; não li dados. **Descrito.**

**6. Escolas e hospitais.** **Não encontrado.**

**7. Empenho.** Nada novo. O CSV de despesa continua trazendo CPF sem máscara.

**Conclusão:** dá para saber as obras de infraestrutura por município e os convênios por prefeitura; folha e orçamento geral, não.

## Mato Grosso do Sul (MS)

**1. Folha.** Conjunto `folha-de-pagamento` em `https://www.dados.ms.gov.br` (CSV mensal de ~15 MB, 2018–2026): `Competência;Órgão;Situação;Nome;Cpf;Cargo;Rem. Base;Outras Verbas;REM. Após Deduções Obrigatórias;Vínculo;Matrícula;Data de Admissão;...`. Só órgão (ex.: "AGEPREV"). **Verificado.**

**2. Obras.** `https://www.transparencia.ms.gov.br/#/ContratoObras`: colunas Órgão, Processo, Contrato, Contratado, Fiscal, Vigência, Valor Contratado, Situação, Objeto. Sem município. Vi o modelo da tabela, não os registros. **Descrito.**

**3. Orçamento regionalizado.** **Não encontrado.** `despesas-anual` só tem órgão.

**4. Convênios e emendas.**
- Conjunto `emendas-parlamentares` (XLSX 2017–2023; CSV 2024, 2025, 2026): `Nº da emenda;Beneficiário(a);Município;Objeto;Órgão;Valor Emenda;Deputado(s);Nº do processo;Status`. Exemplo: "1034 | FUNDO MUNICIPAL DE SAÚDE DE FIGUEIRÃO | Figueirão - MS | R$ 100.000,00". **Verificado.**
- `#/Convenios` e `#/ConveniosSiafic`: Convênio, Unidade Gestora, Concedente, Convenente/Favorecido, Espécie, Valor Inicial. **Descrito.**
- `repasses-dos-municipios` é repasse constitucional (ICMS, IPVA), não gasto direto.

**5. TCE-MS.** Não investigado.

**6. Escolas e hospitais.** As emendas têm beneficiários como "APM DA EE 26 DE AGOSTO" (Campo Grande). Fora isso, **não encontrado.**

**7. Empenho.** Nada novo.

**Conclusão:** dá para saber só as emendas parlamentares por município e os convênios por beneficiário.

## Pará (PA)

O portal novo (`https://www.sistemas.pa.gov.br/portaltransparencia/`) usa várias APIs abertas em `*.sistemas.pa.gov.br`.

**1. Folha.** `GET https://api-servidores-publicos.sistemas.pa.gov.br/dados-transparencias/funcionarios/filtro?ano=2026&mes=9&quantidade=2&pagina=1` devolve `nome, orgao, cargo, tipo_vinculo, salario_bruto, salario_liquido` (ex.: órgão "ADEPARA"). Sem lotação. **Verificado.**

**2. Obras.** `GET https://api-obras-publicas.sistemas.pa.gov.br/obras-publicas?ano=2024&qtdRegistros=..&pagina=..` (aceita `municipio` e `orgao`; anos 2009–2025). Lista: `orgaoGestor, orgaoBeneficiario, valorPago, valorTotalObra, situacaoObra, codigoObra`. O detalhe, em `/obras-publicas/detalhes?codigoObra=`, traz `localExecucao` no formato "região de integração - município" (ex.: "GUAMÁ - SÃO JOÃO DA PONTA"), `objetoObra`, `contratada`. Totais em `/totais-por-ano`: 2022 com 1.179 obras e R$ 1,25 bi pagos; 2024 com 619 obras e R$ 879 mi; 2025 com apenas 2 obras (base atualizada em 03/08/2026). **Verificado**, com dúvida: a obra "Grupamento de Bombeiros em Xinguara" aparece com local "São João da Ponta".

**3. Orçamento regionalizado.** Existe `https://api-planejamento.sistemas.pa.gov.br` (programas e ações). Não vi região de integração nos caminhos da API. **Não verificado.**

**4. Convênios.** A tela `/convenio-transferencias` tem as colunas Tipo de Instrumento, Número/Ano, Nome Concedente, Nome do Beneficiário, Descrição do Objeto, Valor Total Previsto e Concedido, Vigência. **Descrito** (código do portal). `GET https://api-transferencia-recursos.sistemas.pa.gov.br/transferencia-recursos/totais-por-ano?ano=2025` devolveu R$ 5,35 bi empenhados em 4.114 notas; o detalhamento por credor não abri.

**5. TCE-PA e TCM-PA.** Uma matéria de O Liberal cita uma ferramenta do TCE-PA para acompanhar transferências voluntárias a municípios e entidades; não abri. **Descrito.**
`https://www.oliberal.com/estudio/modulo-transferencias-voluntarias-completa-um-ano-e-reforca-o-controle-dos-recursos-publicos-1.1140216`

**6. Escolas e hospitais.** **Não encontrado.**

**7. Empenho.** Não reabri.

**Conclusão:** dá para saber as obras por município até 2024 (com conferência de qualidade) e, provavelmente, os convênios por beneficiário.

## Acre (AC)

**1. Folha.** `https://transparencia.ac.gov.br/servidores` (2013–2026): a tabela tem as colunas Nome, Órgão, Cargo, **Lotação**, Carga Horária, Total Bruto, Total Líquido. O `POST /servidores/listar` devolveu erro 500 ou lista vazia com os parâmetros que tentei, então não vi um valor de lotação. **Descrito.**

**2. Obras.** `https://transparencia.ac.gov.br/conteudo/obras`, com `POST /conteudo/obras/listar` (token CSRF e cookie da própria página). 166 obras. Campos: `entidade, contrato, objeto, empresa, municipio, data_inicio, valor_obra, valor_pago, situacao, data_entrega`. Exemplo: "SESACRE | 716/2022 | Reforma do Hospital Dr. Marinho Monte | PLÁCIDO DE CASTRO | 1.547.033,05 | pago 168.096,07". Municípios: Rio Branco 95, Cruzeiro do Sul 23, Sena Madureira 9. Entidades: SEOP 109, SESACRE 20, SEINFRA 8. **Verificado.**

**3, 5, 6, 7.** **Não encontrado.**

**4. Convênios.** O menu tem "Convênios e Instrumentos Congêneres" (aponta para convênios federais), "Repasse aos Municípios" e "Emendas Parlamentares Estaduais"; não abri. Há também `https://dados.ac.gov.br/`, que não abri. **Descrito.**

**Conclusão:** dá para saber as obras por município; a folha tem lotação na tela, a confirmar.

## Roraima (RR)

**1. Folha.** `https://www.transparencia.rr.gov.br/remuneracoes` (2007–2026). O filtro "Órgão" lista unidades, não só secretarias: "CIRETRAN ALTO ALEGRE", "CIRETRAN PACARAIMA", "COLEGIO MILITAR", "ACADEMIA DE POLICIA MILITAR". Vi a lista do filtro, não os registros. **Descrito.**

**2. Obras.** `https://www.transparencia.rr.gov.br/obras` (Mapa de Obras, fontes SIAC e SEI): 204 obras, 14 órgãos contratantes, R$ 5.205.996.254,47 contratados, R$ 2.995.993.596,14 atestados, 16 "municípios beneficiados". A lista tem Processo, Objeto, Situação, Datas, Valor do Contrato, % Atestado, Grupo, Origem e **Município**, com filtro "Município Beneficiado". Não identifiquei a API. **Verificado na tela.**

**3 a 7.** O portal tem as rotas `/quadrodetalhamentodespesa`, `/repasse-municipios` e `/projetossociais`; não abri. Convênios de saída: **não encontrado.**

**Conclusão:** dá para saber as obras por município (R$ 5,2 bi contratados), por enquanto só raspando a tela.

## Amapá (AP)

**1. Folha.** O portal lista "Folha de Pagamento por Servidor" (`https://transparencia.ap.gov.br/consulta/3/41/pessoa/folha-por-servidor`) e "por Órgão"; a página deu 504. **Não verificado.**

**2. Obras.** Painel "OBRAS GEA" no Looker Studio (`https://lookerstudio.google.com/reporting/d8e7bedd-4c34-42e5-9d7e-c37dd46744e9`), fonte `siga.ap.gov.br/sigacontrato`, atualizado em 01/11/2026, com download CSV e XLSX. Colunas: Unidade Gestora, Número do Contrato, CNPJ, Empresa Contratada, Objeto da Obra, Datas, Situação Atual, Tipo de Obra, Valor Contratual (total R$ 388.905.993,39), Valor Aditivado, Valor Global, Percentual de execução, Link Obra (Google Maps). **Não há coluna de município**; ele aparece no texto do objeto ("... em Macapá-AP") e no link do mapa. **Verificado na tela.**

**4. Convênios.** Painel "Termos de Convênios" (`https://lookerstudio.google.com/s/kNUw66YegiY`); não abri. **Descrito.**

**3, 5, 6, 7.** **Não encontrado.**

**Conclusão:** só as obras, e o município precisa ser extraído do texto.

## Tocantins (TO)

O portal é `https://transparencia.to.gov.br/PortalTransparencia/` (com `www.` o certificado é inválido).

**1. Folha.** `#!servidores`: filtros Órgão, Nome, Matrícula, Cargo efetivo, Exercício (exige dois). Sem filtro de lotação ou município; não abri resultados. **Descrito.**

**2. Obras.** `#!obras` lista "Painel de Obras", "Conservações de Rodovias - TAG (em fase de desenvolvimento)" e "Obras Paralisadas". Não consegui abrir o destino dos links. Uma matéria de 16/06/2026 noticia o lançamento dos painéis de obras, contratos e licitações. **Descrito.**
`https://conexaoto.com.br/2026/06/16/governo-do-tocantins-lanca-paineis-digitais-para-monitoramento-de-obras-contratos-e-licitacoes`

**4. Convênios.** O menu tem "Convênios e Parcerias" e "Transferências Municipais"; não abri. **Descrito.**

**3, 5, 6, 7.** **Não encontrado.**

**Conclusão:** não achei caminho verificado; o Painel de Obras é o primeiro a testar com navegador automatizado.

---

## Observações para o extrator

- **Um extrator serve a vários estados.** AM (`eobras.am.gov.br`) e MT (`sinfralog.sinfra.mt.gov.br`) usam o mesmo produto de mapa de obras ("Obras.gov"), com a mesma API: `GET /obrasgov-map-backend/source/app/configuration?dns=<host>` devolve o `tenantId`; depois `GET .../source/<tenant>/app/filters` e `POST .../source/<tenant>/contract/list`. O código do mapa cita outros clientes: DER-PR, DER-MG, DAER-RS, DER-BA, DER-DF e GOINFRA. Não localizei as URLs desses.
- **Proteção de dados.** As APIs de folha de AM e PA devolvem nome completo; o CSV de MT traz CPF sem máscara. Mascarar na ingestão.
- **Folha por unidade exige uma tabela de unidades.** Em AM e GO, o nome da escola ou do hospital precisa ser casado com o cadastro do INEP e do CNES para virar município. Aposentados e pensionistas não têm lotação útil.
- **Repasse não é gasto direto.** Convênios e transferências a prefeituras (RO, AM, MT, GO, MS) mostram dinheiro entregue ao município, não o que o estado gastou lá com escola, hospital ou polícia. Convém mostrar separado.
