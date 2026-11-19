# Gasto do governo estadual por município: Sul e Sudeste (SP, RJ, MG, ES, PR, SC, RS)

Pesquisa feita em 19/11/2026. Pergunta: existe dado público que diga quanto o governo do estado
gasta em cada município (gasto direto: escolas, hospitais, polícia, obras), por caminhos que não
sejam o campo de município na nota de empenho (já coberto em `docs/levantamento-portais-estaduais.md`)?

Graus de verificação usados:

- **verificado**: abri o dado, vi o nome do campo e um valor de exemplo.
- **descrito**: a página ou o código do site diz que existe, mas não abri o dado.
- **não encontrado**: procurei e não achei. Quando nem procurei a fundo, digo "não investigado".

Limites da pesquisa: nenhum arquivo acima de ~30 MB foi baixado inteiro (li cabeçalho e amostras
por requisição parcial); nada de login, cadastro ou captcha. Os arquivos de folha trazem nome de
servidor (CPF mascarado): agregar por município antes de publicar qualquer coisa.

## Resumo

| UF | Melhor caminho | O que cobre | Granularidade | Acesso | Verificação |
|---|---|---|---|---|---|
| MG | Execução do PPAG por município (`ft_plan_acao_ppag`, dados.mg.gov.br) | Tudo (100% da despesa realizada, 2012–2026); ~17–25% cai em "Diversos municípios" e ~30% em Belo Horizonte | Município | CSV (11 MB compactado) | verificado (baixado e somado) |
| PR | Folha: `REMUNERACAO_RH.zip` + `REMUNERACAO-AAAA-MM.zip` | Folha inteira do Executivo desde 2012; mais convênios com código IBGE | Município + lotação (escola); segurança só município | ZIP/CSV com URL fixa | verificado (cabeçalho, layout e amostra) |
| SC | Folha: `Servidores-Ativos-AAAA-MM.xlsx`; obras: SICOP | Folha (inclui PM e bombeiros por pelotão), obras com % de custo por município, transferências | Unidade + município (no texto da unidade) | XLSX/CSV/ZIP | verificado |
| SP | Folha: "Relação de Servidores" (Fazenda, tem MUNICIPIO) cruzada com Remuneração (portal) | Folha da administração direta; educação por escola (sem valor); convênios só pelo nome da prefeitura | Município + unidade administrativa | Excel por órgão (postback) + CSV | verificado para 1 órgão; cruzamento não testado |
| RJ | API de remuneração (GESPERJ) com `lotacao` | Folha por unidade (escola, hospital, batalhão); sem município pronto | Unidade (precisa tabela unidade → município) | API REST JSON/CSV | verificado |
| ES | Folha: `Remuneracoes` + `VinculosServidores` (`NomeSetor`); obras e convênios com município | Folha de educação e saúde por setor; obras até ~2023; convênios | Setor (escola/hospital); município em obras e convênios | CSV | verificado |
| RS | Convênios e parcerias (`MunicipioConvenente`) | Só transferências voluntárias; folha e custeio não | Município | ZIP/CSV | verificado |

Em todos os sete a despesa de custeio comum (contratos, material, serviços) continua sem lugar,
exceto em MG, onde o próprio governo distribui toda a execução por município no monitoramento
do plano plurianual.

---

## MG — Minas Gerais

**1. Folha.** `remuneracao-servidores-ativos` (CGE), CSV mensal de 08/2012 a 09/2026, ~228 MB por mês
(li 1,5 MB). Campo **`unidade_exercicio`**: "EE PRES TANCREDO NEVES", "HOSPITAL JOAO XXIII - BELO
HORIZONTE - PORTE IV", "40ª S R E - UBERLANDIA- PORTE I". Polícia Militar, Polícia Civil, Bombeiros
e Sejusp vêm como "INF. SIGILOSA". Não há município: é preciso casar o nome da escola com o
cadastro de escolas (nomes se repetem entre cidades). `relacao_nominal_servidores` (Seplag) só
traz a instituição de lotação. **Verificado.**
https://dados.mg.gov.br/dataset/remuneracao-servidores-ativos ·
https://dados.mg.gov.br/dataset/relacao_nominal_servidores

**2. Obras.** `portal_obras` (DER-MG): `contratos.csv` com campo **`municipios`** ("Obra 1 - Nova
Lima, Sabará"), `valor_total_do_contrato`, `total_medido`; `coordenadas.csv` com latitude e
longitude por obra. Parece cobrir só o DER (rodovias). **Verificado.**
https://dados.mg.gov.br/dataset/portal_obras

**3. Execução regionalizada — o achado principal.** Conjunto `planejamento-e-monitoramento` (CGE,
modelo dimensional do SIGPLAN). Tabela `ft_plan_acao_ppag.csv.gz` (11 MB, 1.156.745 linhas):
`id_orgao; id_programa; id_acao; id_funcao; id_territorio; **id_municipio**; ano_ppag; vr_ppag_loa;
**vr_realizado**`. Dimensão `dm_municipio_plan.csv.gz`: 871 linhas = 853 municípios + 18 "DIVERSOS
MUNICÍPIOS - <território>" (inclui "DIVERSOS MUNICÍPIOS - ESTADUAL"). Baixei e somei:

| Ano | Realizado | Municípios específicos (sem BH) | Belo Horizonte | "Diversos" |
|---|---|---|---|---|
| 2019 | R$ 117,2 bi | 50% | 30% | 20% |
| 2022 | R$ 121,1 bi | 48% | 27% | 25% |
| 2023 | R$ 98,6 bi | 52% | 27% | 21% |
| 2025 | R$ 140,8 bi | 52% | 31% | 17% |
| 2026 (parcial) | R$ 67,7 bi | 53% | 27% | 21% |

Anos cobertos: 2012–2026. Ressalvas: (a) 2024 aparece com só R$ 5,0 bi, claramente incompleto;
(b) a distribuição é informada pelos órgãos no monitoramento do PPAG, não sai do empenho, então
sede e inativos tendem a cair em Belo Horizonte; (c) os rótulos de `dm_territorio_plan` parecem
desalinhados entre versões do PPAG (2026 mostra "NOROESTE" com R$ 24 bi): usar `id_municipio`, não
o território; (d) inclui orçamento de investimento das estatais (`id_tipo_orcam` 5, ~R$ 9 bi em
2025). Há também `ft_plan_exec_of_territorio` (por território) e `ft_plan_prog_territorial` (meta
física e financeira por ação e território). **Verificado.**
https://dados.mg.gov.br/dataset/planejamento-e-monitoramento

**4. Convênios.** `portal_convenios_saida` (Segov): `convenio_saida.csv` (10,9 MB) com
**`municipio`** ("ITAPAGIPE"), `cnpj_proponente`, `razao_social_proponente`, `valor_concedente`,
`valor_despesa_paga`; arquivos de pagamentos por ano (2022–2026). `convenios-saida` (CGE) é o mesmo
tema em modelo dimensional, com `dm_municipio` e `cd_municipio_ibge`. Há ainda
`portal_emendas_estaduais` (não abri os campos). **Verificado.**
https://dados.mg.gov.br/dataset/portal_convenios_saida · https://dados.mg.gov.br/dataset/convenios-saida

**5. TCE-MG.** Não investigado a fundo; nada encontrado na busca.

**6. Unidades.** `funcionarios-fhemig`: `unidade;ano;mes;funcionarios` (contagem por hospital da
Fhemig, sem valor) — verificado. `termos-parceria-contratos-gestao`: sem localidade — verificado.
Repasses a caixas escolares por escola: **não encontrado** (não está no catálogo; a busca só
trouxe notícias).

**7. Outros campos.** O datapackage do `dados-armazem-siafi-2026` não tem campo de município nem
de território — verificado.

**Conclusão:** dá para saber ~100% do gasto estadual por município (com 17–25% em "diversos" e
viés para BH) pela execução do PPAG, 2012–2026; folha por escola/hospital e convênios servem de
conferência.

---

## PR — Paraná

**1. Folha — melhor caso junto com SC.** Página de downloads do portal (JSF; os links redirecionam
para URLs fixas):

- `https://www.transparencia.download.pr.gov.br/exportacao/REMUNERACAO_RH/REMUNERACAO_RH.zip`
  (31,7 MB, atualizado 16/11/2026), arquivo `TB_RH.csv`: `cod_vinculo; nome; sigla; instituicao;
  **lotacao**; **municipio**; cargo; dt_inicio; dt_fim; regime; quadro_funcional; ...;
  ult_remu_bruta`. Exemplos: `SEED; COL EST ALDO DALLAGO; IBAITI` · `ADAPAR; EL/ADAPAR DE CERRO
  AZUL; CERRO AZUL` · `SESP; ****; MARINGA` (segurança: lotação mascarada, município preenchido no
  arquivo; na tela do portal o município da PM aparece como "****").
- `https://www.transparencia.download.pr.gov.br/exportacao/REMUNERACAO/REMUNERACAO-2026-10.zip`
  (mensal, desde 2012; não abri o conteúdo, só o layout): `cod_vinculo; dt_remuneracao;
  vencimento; gratificacao; ...; remu_bruta; remu_efetiva; tipo_folha`. Junta com `TB_RH` por
  `cod_vinculo`.
- Layouts: `.../exportacao/REMUNERACAO_RH/LAYOUT-REMUNERACAO_RH.csv` e
  `.../exportacao/REMUNERACAO/LAYOUT-REMUNERACAO.csv`.

**Verificado** (cabeçalho e ~400 KB de amostra do `TB_RH`; layouts baixados). A lotação em
`TB_RH` é a atual/última do vínculo, não um histórico mês a mês.
https://www.transparencia.pr.gov.br/pte/assunto/8/129 · https://www.transparencia.pr.gov.br/pte/assunto/6/1

**2. Obras.** "Obras por Área de Governo" é um QlikView
(`http://bi.pr.gov.br/QvAJAXZfc/opendoc.htm?document=RealizacoesdeGoverno.qvw`), só tela — **descrito**.
"Acompanhamento de Obras - Secretaria das Cidades" abre
https://transparencia-obras.paranacidade.org.br/ (aplicativo que consulta um web service "WSSAM";
são obras municipais financiadas pelo estado) — **descrito**. "Obras Paralisadas" é uma planilha
no Google Drive (não aberta). "Paraná Interativo" é um mapa (https://paranainterativo.pr.gov.br/).

**3. Execução regionalizada.** **Não encontrado.**

**4. Convênios.** `https://www.transparencia.download.pr.gov.br/exportacao/CONVENIOS/CONVENIOS-2025.zip`
(1,5 MB; um por ano, 2007–2026; fonte TCE-PR/SIT, atualização semanal). Tabela
`TB_CONVENIO_EMPREENDIMENTO`: `concedente; tomador; **ibge**; objeto; situacao; total_repassado;
total_repasses; dt_vigencia_inicio...`. O `ibge` vem sem o prefixo 41 (ex.: `6902` = Curitiba,
4106902). **Verificado** (2025).
https://www.transparencia.pr.gov.br/pte/assunto/4/127

**5. TCE-PR.** O SIT (Sistema Integrado de Transferências) é a fonte dos convênios acima. Outros
portais do TCE-PR: não investigado.

**6. Unidades.** O portal aponta para a "Consulta Escolas" (página por escola com seção de
"Descentralização Financeira"/recursos financeiros). **Descrito**, não abri os valores.
https://www.transparencia.pr.gov.br/pte/assunto/10/56

**7. Outros campos.** O layout de "Gastos Públicos" (`.../exportacao/DESPESAS/LAYOUT-DESPESAS.csv`)
não tem município nem região — verificado.

**Conclusão:** dá para saber a folha inteira por município desde 2012 (com escola na educação) e
os convênios por município; custeio e obras diretas não.

---

## SC — Santa Catarina

**1. Folha.** `remuneracao-servidores` (SEA), 115 recursos de 2019 a 10/2026.
`Servidores-Ativos-2026-10.xlsx` (7,2 MB): `Nome; CPF; Cargo; OrgaoExercicio;
**UnidadeExercicio**; RegimeTrabalho; CargaHorariaCargo; CargaHorariaServidor; Situacao;
**ValorBruto**`. A unidade traz o município no fim do texto:
`769000934910 - EEB DR RENATO RAMOS DA SILVA - LAGUNA` ·
`3060942030 - 9BPM/4CIA/2PEL/3GP - SIDEROPOLIS` · `000081720000 - 2CBM/17BBM - SOMBRIO - 17BBM` ·
`114010009030 - CONV. APAE ARROIO TRINTA - ARROIO TRINTA`. 3.470 unidades distintas em 10/2026;
algumas não têm município no nome ("DIVISAO DE GESTAO DE FOLHA"). É o único dos sete em que a
Polícia Militar e os Bombeiros aparecem por unidade e cidade. **Verificado.**
https://dados.sc.gov.br/dataset/remuneracao-servidores

**2. Obras.** SICOP (Secretaria da Infraestrutura):
`https://www.sie.sc.gov.br/webdocs/sie/doc-tecnicos/portal-transparencia/dataset_obras.zip`
(375 MB, atualizado 21/09/2026; li o índice e os cabeçalhos sem baixar). Dentro:
`pacote_obra/OBRA.csv` (`CONTRATO; DESCRICAO_OBRA; TIPO_OBRA; **MUNICIPIO**; NOME_BEM_PUBLICO...`),
`pacote_obra/MUNICIPIO.csv` (`CONTRATO; NUMERO_OBRA; **MUNICIPIO**; **PERCENTUAL_CUSTO**` — rateio
da obra entre municípios), `pacote_contrato/CONTRATO.csv` (`CONTRATANTE; SETOR_BENEFICIADO;
CPFCNPJCONTRATADO; VALOR_INFORMADO_CONTRATADO...`), `pacote_medicao/MEDICAO.csv`. Exemplo:
`SR-26002/940094; DRAGAGEM DO RIO...; Major Vieira; 100`. Os arquivos grandes do pacote
(serviços e medições por item, até 2,2 GB) não são necessários. **Verificado.**
https://dados.sc.gov.br/dataset/obras-no-mapa-da-transparencia

**3. Execução regionalizada.** O catálogo aponta o monitoramento do PPA em
`http://www.acompanhamentofisico.sc.gov.br/`, que não respondeu. **Não encontrado.**

**4. Transferências.** `transferencias` (SEF): CSV de 2021 (66 MB) e 2022 (11 MB, até março):
`nuanoexercicio; **nmmunicipiocredor**; nmunidadegestora; nmcredor; nuidentificacao; nmfuncao;
nmprograma; nmacao; vlempenhado; vlliquidado; vlpagoorcamentario; nmtipotransferencia; deobjeto...`.
Exemplo: `2022; VARGEAO; Secretaria de Estado da Infraestrutura e Mobilidade; MUNICIPIO DE VARGEAO;
...; Transferências Voluntárias a Municípios`. **Verificado**, mas o conjunto parou em 2022. O
portal novo tem a página `/transferencias` e usa a API
`https://api-portal-transparencia.apps.sm.okd4.ciasc.sc.gov.br/api` (vista no código do site, não
consultada) — **descrito**. Consultas HTML do SCtransf por município
(`http://sistemas2.sc.gov.br/sef/sctransf/Pesquisa/porMunicipio`) — não abertas.
https://dados.sc.gov.br/dataset/transferencias · https://www.transparencia.sc.gov.br/

**5. TCE-SC.** **Não encontrado** (a busca só trouxe painéis de licitações e de escolas).

**6. Unidades.** A própria folha dá o gasto de pessoal por escola e por batalhão (item 1).
Contratos de gestão com organizações sociais da saúde: só o link da SES (não aberto).

**7. Outros campos.** `unidadesgestoras.csv` e `estrutura-organizacional.csv` não têm município —
verificado.

**Conclusão:** dá para saber a folha por unidade e município (inclusive segurança), as obras com
rateio por município e as transferências com município do credor (estas só até 2022 em arquivo).

---

## SP — São Paulo

**1. Folha.** Três fontes que se completam:

- **Remuneração (Portal da Transparência).**
  `https://www.transparencia.sp.gov.br/Remuneracao/Download?arquivo=RemuneracaoAtivos.csv` (119 MB;
  li só o início): `NOME; CPF; CARGO; ORGÃO; REMUNERAÇÃO DO MÊS; ...; TOTAL LIQUÍDO (R$); GRUPO;
  ...; JORNADA; INGRESSO; NOMEACAO`. **Não tem lotação nem município** (o dicionário cita
  "Lotação", mas a coluna não está no CSV). Verificado.
  https://www.transparencia.sp.gov.br/Remuneracaomensal/Index
- **Relação de Servidores do Poder Executivo (Fazenda).**
  https://www.fazenda.sp.gov.br/SigeoLei131/Paginas/DDPEEscolhaConsulta.aspx — um Excel por órgão
  da administração direta (Educação, Saúde, Segurança Pública, Administração Penitenciária etc.),
  gerado por postback ASP.NET que abre um arquivo em `/SigeoLei131/Paginas/Arquivos/`. Abri o da
  Controladoria (34 KB): `NOME; CARGO; TIPO DE VINCULO; CARGO EM COMISSAO; CARGO EM DESIGNACAO;
  JORNADA; SIT. FUNCIONAL; SECRETARIA; UNIDADE ORCAMENTARIA; UNIDADE GESTORA; **UNIDADE
  ADMINISTRATIVA**; **MUNICIPIO**`. Exemplo: `COORD.AUD.FINANC.CONT.PESSOAL; SAO PAULO`.
  **Verificado para um órgão.** Pontos em aberto: a página diz "Mês de Referência: 10/2026", mas o
  arquivo que abri tinha data de modificação de 15/09/2025; não abri Educação, Saúde nem
  Segurança; não tem valor nem CPF, então o cruzamento com a remuneração é por nome + cargo +
  órgão (não testado). Não cobre autarquias, fundações e universidades.
- **SEDUC, "Servidores ativos por Unidade".**
  https://dados.educacao.sp.gov.br/dataset/servidores-ativos-por-unidade — CSV mensal de 10/2018 a
  10/2026 (~78 MB; li o início e o dicionário): `NOMEDE_E; UA_E; **NOMEUA_E**; **MUNICIPIO_E**;
  NOMECAR_E; QUADRO_E; CATEG_E; JORNADA...`. Exemplo: `URE SOROCABA; EE FRANCISCO COCCARO
  PROFESSOR; SOROCABA; PROFESSOR EDUCACAO BASICA II`. Anonimizado: sem nome e sem salário, serve
  para contar servidores por escola e estimar com salário médio do cargo. **Verificado.**

**2. Obras.** No portal, "Obras Públicas" é um Power BI (só tela, não aberto) e "Obras
Paralisadas" aponta para o Painel de Obras do TCE-SP, que na visita devolveu "Indisponibilidade
Temporária – Painéis TCESP". Há conjuntos de obras do DER no catálogo estadual (`obras-der-sp`,
`licitacoes-de-obras`, `obras-emergenciais`), não abertos. **Descrito.**
https://www.transparencia.sp.gov.br/Obras/Menu · https://dadosabertos.sp.gov.br/

**3. Execução regionalizada.** A página "Investimentos" do portal oferece
`https://dworcamento.fazenda.sp.gov.br/DadosXML/2025_INVESTIMENTOS_EXECUCAO_ORCAMENTO.csv` (2011
em diante): órgão, projeto/atividade, grupo, dotação e liquidado, **sem localidade** — verificado.
Execução por região ou município: **não encontrado.**

**4. Convênios.** `https://www.transparencia.sp.gov.br/Dados%20Abertos/Convenios/convenio.zip`
(189 KB; 3.618 linhas, 2023–2026, todas "TRANSFERENCIA VOLUNTARIA"). O CSV não tem cabeçalho;
uma linha típica: `2024; TRANSFERENCIA VOLUNTARIA; SECRETARIA DE DESENVOLVIMENTO REGIONAL;
INFRAESTRUTURA URBANA; PREFEITURA MUNICIPAL DE MANDURI; ; 2024-07-10; 2024-07-10; ; 72112767.00`.
Não há campo de município nem CNPJ preenchido na amostra (o município sai do nome do
beneficiário), e a última coluna não parece valor em reais (R$ 72 milhões para Manduri não faz
sentido) — tratar com desconfiança. **Verificado.** No catálogo estadual há também "Convênios com
Municípios" (Secretaria de Governo, 2,3 MB): `Demandante` ("PREFEITURA MUNICIPAL DE CEDRAL"),
`Nome da Obra`, `Valor do estado`, `Ano`, `Escritório Regional`, `Origem da Demanda` — verificado
(cabeçalho e duas linhas).
https://www.transparencia.sp.gov.br/Convenios/Index ·
https://dadosabertos.sp.gov.br/dataset/convenios-com-municipios

**5. TCE-SP.** Painéis fora do ar na visita; o levantamento anterior já registrou que o TCE-SP não
publica despesa estadual. **Não encontrado.**

**6. Unidades.** PDDE Paulista: https://pdde.educacao.sp.gov.br/transparencia/ diz publicar
"repasses por escola, município, diretoria de ensino e ano"; a página consome
`https://apiseduc.educacao.sp.gov.br/pddep/api` (rotas `/Escola` e
`/Repasses/GetBy/Municipio/{cd}/DE/{cd}/Escola/{cd}`, vistas no JavaScript), mas esse host não
resolveu no DNS a partir da máquina usada. **Descrito.** Repasses a organizações sociais por
hospital: **não encontrado.**

**7. Outros campos.** Nada novo.

**Conclusão:** dá para estimar a folha da administração direta por município (Relação de
Servidores + Remuneração; educação por escola) e as transferências voluntárias a prefeituras pelo
nome; custeio, obras e investimento diretos não têm lugar em dado aberto.

---

## RJ — Rio de Janeiro

**1. Folha.** Consulta de remuneração do GESPERJ, com API REST aberta (sem token):
`https://www.rj.gov.br/remuneracao/api/rest/remuneracoes?page=0&size=10&ano=2026&mes=10&empCodigo=1&subempCodigo=18&situacao=ATIVO`
devolve `{page, size, totalPages, totalElements, remuneracoes: [...]}` com `orgao; matriculaServidor;
nomeServidor; vinculo; funcaoCargo; totalVantagens; totalDescontos; valorLiquido; anoRef; mesRef;
folhaRef; cargaHoraria; **lotacao**`. Exemplos de `lotacao`: "CRIAAD VOLTA REDONDA", "HOSP EDUARDO
RABELLO 1 - IASERJ", "POSTO DE ASSISTÊNCIA MÉDICA - COELHO NETO", "1º BATALHÃO DE POLÍCIA
AMBIENTAL". Órgãos em `/api/rest/hades/empresas` (84; SEEDUC = 1/18, SES = 1/29, PM = 1/11).
Volume em 10/2026: 62.023 registros na SEEDUC, 6.783 na SES, 58.407 na PM (registro por folha; um
servidor pode aparecer em mais de uma). `size=4` devolve erro 400, `size=10` funciona. Há
exportação CSV com coluna "Lotação" (`/api/rest/remuneracoes/csv`, vista no código, não baixada).
Histórico na tela de 2016 a 2026. **Verificado.** Limite: `lotacao` é nome de unidade, sem
município: precisa de uma tabela unidade → município (escolas pelo Censo Escolar, batalhões e
hospitais à mão).
https://www.rj.gov.br/remuneracao/

O endpoint `situacao_funcional_estado` do TCE-RJ é agregado por unidade gestora, sem localidade
— verificado.

**2. Obras.** "Relatório de Obras" da CGE (https://dashboards.cge.rj.gov.br/relatorio-obras/,
Streamlit): 5.955 notas de empenho, R$ 17,7 bi empenhados de 2016 a 2026; filtros Ano, Nota de
Empenho, Unidade Gestora e Empresa; exporta CSV e Excel. **Sem município** nos filtros — verificado
em tela (não baixei o CSV). `obras_paralisadas_estado` e `contrato_estadual` do TCE-RJ também não
têm localidade — verificado.
https://www.transparencia.rj.gov.br/obras/

**3. Execução regionalizada.** O portal aponta PPA e LOA em
`https://www.redeplan.planejamento.rj.gov.br/PPA/programacao.html` e
`https://www.redor.planejamento.rj.gov.br/ploa.html` (não abertos). A consulta livre de despesa
da Fazenda (`https://tfe.fazenda.rj.gov.br/tfe/web/despesagenerica`) abriu desta vez, e o HTML
inicial não menciona município nem região (verificação superficial). **Não encontrado.**

**4. Convênios.** O portal manda para o CONVERJ
(`http://www.converj.rj.gov.br/converj/servlet/adconsultawebconvenios`), formulário GeneXus não
consultado — **descrito**. `convenios_estado` do TCE-RJ tem `UnidadeGestora; NumeroConvenio; Objeto;
Valor; datas`, **sem convenente nem município** — verificado. O catálogo dadosabertos.rj.gov.br só
tem planilhas avulsas por órgão.

**5. TCE-RJ.** Li a lista de 40 endpoints (`https://dados.tcerj.tc.br/api/v1/openapi.json`) e
amostrei os estaduais: nenhum traz município. **Verificado (negativo).**

**6. Unidades.** Não investigado (contratos de gestão da saúde e repasses a escolas).

**7. Outros campos.** Nada novo.

**Conclusão:** dá para saber a folha por unidade de lotação via API (falta converter unidade em
município); para o resto, não achei caminho.

---

## ES — Espírito Santo

**1. Folha.** `portal-da-transparencia-pessoal` (Seger): 215 arquivos mensais
`Remuneracoes-MM_AAAA.csv` (82–93 MB; uma linha por rubrica): `Orgao; NumFunc; NumVinc; Nome;
CentroCusto; MesFolha; Cargo; Situacao_Folha; Rubrica; VantagemDesconto; Valor`. O `CentroCusto` é
o órgão, não a unidade. O lugar vem de `VinculosServidores.csv` (442 MB; li amostras): `NumFunc;
NumVinc; Orgao; Cargo; Situacao; **SiglaSetor**; **NomeSetor**...`, que junta por `NumFunc` +
`NumVinc`. Exemplos de `NomeSetor`: "EEEFM PROF FILOMENA QUITIBA", "SRE VILA VELHA", "UNIDADE
TRABALHO DE CLINICA CIRURGICA-HINSG", "GERENCIA LOCAL DE CACHOEIRO DE ITAPEMIRIM". Polícia
Militar, Civil, Penal e Sejus aparecem só no nível do órgão. Sem município: casar escola com o
cadastro (`informacoes-referentes-as-unidades-escolares-da-rede-estadual`). **Verificado por
amostra.** O setor em `VinculosServidores` é o atual, não histórico.
https://dados.es.gov.br/dataset/portal-da-transparencia-pessoal

**2. Obras.** `portal-da-transparencia-obras` (Secont, origem Geo-Obras): `Obras-AAAA.csv` de 2009
a 2024 com `SIGLA_ORGAO; **MUN_NOME**; Nome` (microrregião)`; BEMPUBLICO; OBJETO; VALORINICIAL;
VALORADITADO; VALORMEDICOES; ULTIMA_SITUACAO; EMPRESACONTRATADA`. Exemplo: `SEDU; Alegre; Sul;
EEEFM SIRENA REZENDE FONSECA; 1.444.448,22; medido 1.781.941,63`. O arquivo de 2024 tem 1 KB: a
série parece ter parado. O TCE-ES publica `obras-publicas` (Geo-Obras até 24/01/2024) com
`Municipio; UnidadeGestora; Esfera; ValorInicial; ValorMedido`, misturando estado e prefeituras.
**Verificado.**
https://dados.es.gov.br/dataset/portal-da-transparencia-obras · https://dados.es.gov.br/dataset/obras-publicas

**3. Execução regionalizada.** Só a microrregião no subtítulo (já no levantamento anterior). O CSV
da LOA (`despesa-lei-orcamentaria-anual`) não tem localidade — verificado.

**4. Convênios e transferências.** `portal-da-transparencia-convenios-do-estado` (Sefaz, 55
arquivos): `Convenios-AAAA.csv` com `nomeConcedenteConvenente; cnpjConcedenteConvenente;
valorConcessao; objeto; **codIBGEMunicipio**; **nomeMunicipio**` — nas duas linhas de 2026 que vi o
município veio "SEM MUNICÍPIO INFORMADO" (99999), então a cobertura do campo precisa ser medida.
`ConveniosExecucaoOrcamentaria-AAAA.csv` traz pagamento por convênio com `Favorecido; CpfCnpjNis;
ValorPago; Subtitulo` (microrregião). `portal-da-transparencia-transferencias-para-municipios`:
`CodMunicipio` (IBGE)`; NomeMunicipio; Icms; Ipva...` de 2010 a 2026 (transferências
constitucionais). **Verificado.**
https://dados.es.gov.br/dataset/portal-da-transparencia-convenios-do-estado

**5. TCE-ES.** Além das obras acima, nada por localidade para o estado. Não investigado a fundo.

**6. Unidades.** Não investigado além da folha por setor.

**7. Outros campos.** Nada novo.

**Conclusão:** dá para saber a folha de educação e saúde por escola/hospital, as obras por
município até ~2023 e os convênios; o resto fica na microrregião do subtítulo.

---

## RS — Rio Grande do Sul

**1. Folha.** O portal mostra um painel Power BI embutido ("Pessoal do Poder Executivo"). Colunas
na tela: Ano, Mês, CPF, Nome, Órgão, Situação, Remuneração Bruta, Descontos, Remuneração Líquida;
no detalhe, Tipo de Vínculo, Data de Ingresso, Cargo, Carga Horária, Gratificação. **Sem lotação
nem município** — verificado em tela. O catálogo dados.rs.gov.br não tem conjunto de servidores.
**Não achei caminho.**
https://www.transparencia.rs.gov.br/servidores-aposentados-e-pensionistas/pessoal-do-poder-executivo-gov-rs/dados/

**2. Obras.** O portal aponta o mapa `https://sider.daer.rs.gov.br/obras-gov-map/#/map` (mesma
plataforma do SICOP catarinense; não consultei o backend) — **descrito**. Em dados.rs.gov.br há
`contratos-de-obras.zip` (409 KB), que deu timeout na visita — não verificado.
https://www.transparencia.rs.gov.br/obras/mapa-de-obras/dados/ · https://dados.rs.gov.br/dataset/contratos-do-estado

**3. Execução regionalizada.** **Não encontrado** (o campo `Municipio` do arquivo de despesa é do
credor, como já registrado).

**4. Convênios.** `convenios-do-estado` (CAGE): `ConveniosDespesa-RS.csv` (49,8 MB descompactado,
desde 2003): `Orgao; NomeConcedente; ValorConcedente; NomeConvenente; **MunicipioConvenente**;
ValorPago; Objeto; TipoTransferencia; cnpj_convenente`. Exemplo: `MUNICIPIO DE AUGUSTO PESTANA;
AUGUSTO PESTANA; 30000,00`. `Parcerias-RS.csv`: `OrganizacaoParceira; **Municipio**; ValorPago;
UF`. **Verificado.** O portal tem ainda a seção "Municípios" com repasses tributários.
https://dados.rs.gov.br/dataset/convenios-do-estado · https://www.transparencia.rs.gov.br/municipios/

**5. TCE-RS.** O portal aponta https://dados.tce.rs.gov.br/ (não aberto). Não investigado.

**6. Unidades.** **Não encontrado.**

**7. Outros campos.** Nada novo.

**Conclusão:** só as transferências voluntárias (convênios e parcerias) saem por município; para
folha e custeio, não achei caminho.

---

## Observações gerais

- **Folha é o caminho mais promissor fora de MG.** PR e SC entregam município direto; SP entrega
  município num arquivo separado da remuneração; RJ, MG e ES entregam o nome da unidade, que precisa
  ser convertido em município (para escolas, o Censo Escolar resolve a maior parte).
- **Segurança pública** só aparece com lugar em SC (unidade e cidade), PR (cidade) e RJ (batalhão).
  MG e ES ocultam.
- **Convênios com município** existem em MG, ES, PR, SC e RS; em SP só pelo nome da prefeitura;
  no RJ não achei arquivo.
- **Pendências que valem um segundo olhar:** abrir os Excel de Educação, Saúde e Segurança da
  "Relação de Servidores" de SP e testar o cruzamento por nome; conferir por que o PPAG de MG tem
  2024 quase vazio; tentar a API do PDDE Paulista de um IP brasileiro; medir quanto do
  `nomeMunicipio` dos convênios do ES vem preenchido; consultar a API de transferências do portal
  novo de SC.
