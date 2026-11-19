# Levantamento das fontes de despesa municipal

Objetivo: decidir como obter a despesa nota a nota das 5.570 prefeituras. Há dois caminhos:
os Tribunais de Contas, que recebem a contabilidade de todas as prefeituras de um estado num
formato padronizado, e os portais de transparência das próprias prefeituras, que na maioria das
cidades pequenas são fornecidos por poucas empresas de software. Pesquisa feita em 19/11/2026,
visitando portais e APIs (sem baixar arquivos grandes). "Não verificado" quer dizer que a
informação não pôde ser confirmada na visita.

Dificuldade do extrator: **1** = arquivos ou API limpos · **5** = raspagem de tela com obstáculos.

## Resumo: quanto dá para cobrir pelos Tribunais de Contas

| Situação | Tribunais | Municípios |
|---|---|---|
| Nota a nota completo, sem login (dif. 1–2) | TCE-SP (644), TCE-PR (399), TCE-PB (223), TCE-CE (184), TCE-PE (184), TCE-TO (139) | **1.773** |
| Nota a nota com poucos campos | TCE-RJ (91), TCE-RN (167) | 258 |
| Nota a nota, mas exige token pedido ao tribunal | TCM-GO (246) | 246 |
| Só agregado | TCE-ES (78, sem credor), TCE-PI (224), TCE-MA (217) | 519 |
| Atrás de CAPTCHA ou login | TCE-MG (853), TCM-BA (417), TCE-SE (75), e-Contas e similares | ~1.400 |
| Bloqueado para a máquina usada (testar de IP brasileiro) | TCE-RS (497), TCE-MT (142), TCE-RO (52) | ~690 |
| Nada aberto | SC (só painéis), AL, AM, AP, MS, RR, AC, TCM-PA | ~720 |

Ou seja: com seis extratores simples dá para ter o nota a nota de **~1.800 prefeituras (um terço
do país)**, e ~2.300 com RJ, RN e o token do TCM-GO. As capitais São Paulo e Rio de Janeiro ficam
fora dos TCEs (têm tribunal próprio, que só publica painéis) e entram pelos portais das próprias
prefeituras. O resto do país fica com o SICONFI (agregado) e, onde valer a pena, com os portais
municipais pelo fornecedor de software (seção no fim).

Bônus para os estados: TCE-PE, TCE-RN e TCE-RJ publicam também a despesa do **governo estadual**,
o que cobre os buracos dos portais estaduais do RN e do RJ.

## Tribunais de Contas

### Sul e Sudeste

| Tribunal | Cobertura | Despesa nota a nota | Receita | Acesso | Anos | CNPJ do credor | Dif. |
|---|---|---|---|---|---|---|---|
| **TCE-SP** | 644 municípios (menos a capital), com câmaras e indireta | **Sim**: cada evento (empenhado, liquidado, pago, anulação) | Sim | ZIP/CSV anual com todos os municípios + API REST sem autenticação | 2008– (API 2014–) | Sim; CPF reduzido na API | **1** |
| **TCE-PR** | 399 municípios, todas as entidades | **Sim**: empenho, liquidação, pagamento, estornos, documento fiscal | Não verificado | ZIP/XML por município e ano, URL previsível, semanal | 2013– | Sim | 2 |
| **TCE-RJ** | 91 municípios (menos a capital) **+ governo do estado** | Sim, com poucos campos (sem nome do credor, elemento, programa, fonte) | Sim, mensal | API REST (OpenAPI), JSON ou CSV | 2020– | Sim; CPF mascarado | 2 |
| TCE-ES | 78 municípios + estado | Não: agregado mensal por dotação, **sem credor** | Sim | CKAN estadual, ZIP/CSV anual | 2013– | Não | 1 (agregado) |
| TCE-MG | 853 municípios (SICOM) + órgãos do estado | Provável (categoria "Empenho"), não verificado | Sim (categoria) | API atrás de token obtido por **reCAPTCHA** | 2014– | Não verificado | 5 |
| TCE-SC | 295 municípios + estado | Não: só painéis Qlik | Painel | API só de cadastro | — | — | 5 |
| TCE-RS | Municípios (SIAPC/LicitaCon) | Não verificado | Não verificado | CKAN anunciado, **inacessível** (timeout e Cloudflare) | — | — | 4–5? |
| TCM-SP | Só a capital | Não: painéis Qlik | Painel | — | — | — | 5 |
| TCM-RJ | Só a capital | Não: PDFs e Power BI | Boletins | — | 2018– | — | 5 |

**TCE-SP.** Portal https://transparencia.tce.sp.gov.br/conjunto-de-dados; arquivos
`.../sites/default/files/conjunto-dados/despesas-{ano}.zip` e `receitas-{ano}.zip` (despesas 2025:
~2,1 GB, atualizado em 18/11/2026). CSV (`;`): IBGE do município, órgão, mês, tipo de evento
(empenhado/liquidado/pago), empenho, CNPJ e nome do credor, data, valor, função, subfunção,
programa, ação, fonte, código de aplicação, modalidade, elemento, **histórico**. API em `/apis`:
`/api/{json|xml}/despesas/{municipio}/{ano}/{mes}`, `/receitas/...`, `/municipios`. Também
licitações e contratos (municipais e estaduais), dívida ativa, alterações orçamentárias, PPA.

**TCE-PR.** Portal https://pit.tce.pr.gov.br; lista por POST em `/Dados/DadosConsulta/Pesquisa`
(`cdMunicipio`, `nrAno`); arquivos `https://pit.tce.pr.gov.br/Arquivos/{ano}/{ano}_{IBGE6}_{Tema}.zip`
com temas Despesa, Licitacao, Contrato, Convenio, **Obra**, Combustivel, Diarias. O Despesa.zip traz
XML de empenho (IBGE, entidade, CNPJ e nome do credor, fonte, natureza até detalhamento, órgão,
função, subfunção, programa, projeto/atividade, histórico, valores), liquidação, documento fiscal,
pagamento e estornos.

**TCE-RJ.** OpenAPI em https://dados.tcerj.tc.br/api/v1/openapi.json (41 endpoints): municipais
(`empenho_municipio`, `receitas_municipio`, `dotacao_municipio`, `contratos_municipio`,
`licitacoes`, `obras_paralisadas`, pessoal, saúde, educação) e estaduais (`empenho_estado`,
`receitas_estado`, `dotacao_estado`, `contratos_estado`). Cuidado: `jsonfull=true` ignora o limite e
devolve a base inteira.

**TCE-ES.** CKAN `https://dados.es.gov.br/api/3/action/package_show?id=despesas-municipios` e
`receitas-municipios` (ZIP por ano, 2013–2026; 2025: 650 MB de CSV): classificação completa e
valores, sem credor. Também `tcees-contratacoes` (contratos, itens, obras, 2021–2026).

**TCE-MG.** https://dadosabertos.tce.mg.gov.br/ (cadeia TLS incompleta): API
`arabiasaudita.tce.mg.gov.br:8443/.../dados-abertos/dadosAbertos/{pesquisar|buscarCategoriaDownload|baixarArquivoPct/{seq}|baixarDicionarioDeDados}`
responde 401 sem um token obtido por reCAPTCHA. Downloads em ZIP por município ou "todos", por
exercício. Uma pessoa consegue baixar manualmente; automação não.

**TCE-SC.** Só painéis Qlik (Farol); e-Sfinge pede login. **TCE-RS:** tentar de outra rede.
**Capitais:** usar os portais das prefeituras (dados.prefeitura.sp.gov.br; ContasRio) em vez dos
TCMs.

### Nordeste

O Nordeste é a região mais bem servida: **CE e PB** publicam o nota a nota de todas as prefeituras
em formato limpo, **PE** também (mais lento), e o **TCE-RN** publica inclusive os órgãos do
estado, o que cobre o buraco do portal estadual do RN. Na Bahia quem fiscaliza as prefeituras é o
TCM-BA, que só tem consulta com reCAPTCHA.

| Tribunal | Cobertura | Despesa nota a nota | Receita | Acesso | Anos | CNPJ do credor | Dif. |
|---|---|---|---|---|---|---|---|
| **TCE-CE** (SIM) | 184 municípios, todas as unidades; sem o estado | **Sim**: empenho, liquidação, pagamento, anulações, itens de nota fiscal | Sim | API REST (OpenAPI), 1000 por página | 2003– | Sim; CPF criptografado | **1** |
| **TCE-PB** (SAGRES) | 223 municípios, todas as unidades | **Sim**, com empenhado/liquidado/pago | Sim | ZIP com CSV por ano, consolidado ou por município; atualização diária | 2003– | Sim | **1** |
| **TCE-PE** (Tome Conta) | 184 municípios + câmaras **+ o estado** | **Sim**; liquidação e pagamento em endpoints próprios | Sim (municipal e estadual) | API HTTP JSON/XML, sem autenticação, até 100 mil registros | 2016– (2012–2014 vazios) | Sim; CPF mascarado | 2 |
| **TCE-RN** | 167 prefeituras + câmaras + autarquias **+ órgãos do estado** | Sim, com poucos campos (sem natureza, fonte nem nome do credor); liquidação e pagamento uma chamada por empenho | Só balanço orçamentário | API REST (Swagger) | 2025 confirmado | Só o documento | 3 |
| TCE-PI | 224 prefeituras + órgãos do estado | Não: agregados por função, natureza, elemento; credores só com nome e totais | Sim, detalhada | API REST (OpenAPI) | 2010– | Não | 2 (agregado) |
| TCE-MA | 217 municípios + estado | Não: só totais por função | Agregada | JSON não documentado de uma SPA; Swagger oficial fora do ar | 2021–2024 | Não | 4 |
| **TCM-BA** | 417 municípios | Sim, na tela | Sim, na tela | Só formulário com **reCAPTCHA v3** | 2010– | Filtro existe | 5 |
| TCE-BA | Só o próprio tribunal | — | — | — | — | — | n/a |
| TCE-SE | 75 municípios + estado | Não verificado | Não verificado | WebForms antigo (até 2016); relatórios pedem login | 2009–2016 | — | 5 |
| TCE-AL | — | Não encontrado | Não encontrado | Só Power BI do RREO | — | — | 5 |

**TCE-CE.** API em `https://api-dados-abertos.tce.ce.gov.br/sim` (especificação em
`.../sim/openapi_prod.yaml`; a antiga `api.tce.ce.gov.br` está obsoleta), com 160 endpoints:
`notas_empenhos`, `liquidacoes`, `notas_pagamentos`, `orcamento_receita`, `balancetes_*`,
`contratos`, `folhas_pagamentos`, `obras_municipais_servicos_engenharia`, `medicoes_obras_municipio`
e outros. Em `notas_empenhos` são obrigatórios `codigo_municipio` (código do TCE, 002–184; o
endpoint `/municipios` dá o IBGE), `exercicio_orcamento` no formato **AAAA00** e
`data_referencia_doc` (AAAAMM). Campos: órgão, unidade, função, subfunção, programa,
projeto/atividade, elemento, subelemento, fonte, histórico, contrato, licitação, credor. A spec
declara basicAuth, mas as chamadas funcionaram sem credencial.

**TCE-PB.** Downloads em
`https://download.tce.pb.gov.br/dados-abertos/dados-consolidados/{despesas|receitas|servidores|licitacoes}/{tipo}-{ano}.zip`
e `.../dados-por-municipio/{001-223}/{tipo}/{tipo}-{ano}.zip` (despesas 2024 consolidado: 192 MB;
João Pessoa: 3 MB, 37 MB descompactado). CSV com `;`, UTF-8 com BOM: unidade, empenho, data, mês,
CPF/CNPJ, credor, empenhado/liquidado/pago, UO, função, subfunção, programa, ação, natureza,
modalidade, elemento, subelemento, licitação, **número da obra**, histórico, fonte. Portal:
https://dados-abertos.tce.pb.gov.br/

**TCE-PE.** Métodos em `https://sistemas.tce.pe.gov.br/DadosAbertos/Exemplo!listar`; exemplo:
`.../DadosAbertos/DespesasMunicipais!json?ANOREFERENCIA=2024&MESREFERENCIA=1&CODIGO_MUNICIPIO=P001`.
Também `EmpenhoLiquidacao`, `EmpenhoPagamento`, `ReceitasMunicipais`, `ReceitasEstaduais`,
`DespesasEstaduais`, `Contratos`, `LicitacoesDetalhes`, `ListaServidores`, `Obras`. A
classificação vem como texto, sem código, e o encoding é misturado: normalizar. `ReceitasMunicipais`
deve ser filtrado por `ID_UNIDADE_GESTORA`. Chamadas lentas (algumas passam de 2 min). Dicionário:
`tcepe.tc.br/internet/docs/dadosabertos/TomeContaDicionarioDados.pdf`.

**TCE-RN.** Swagger em `https://apidadosabertos.tce.rn.gov.br/swagger`; unidades em
`/api/InformacoesBasicasApi/JurisdicionadosTCE/json` (923); empenhos em
`/api/EmpenhosLiquidacoesPagamentosApi/Empenhos/Json/{ano}/{idUnidade}`. Unidades grandes dão
timeout. Também contratos, licitações e balanço orçamentário.

**TCE-PI.** OpenAPI em `https://www.tcepi.tc.br/portaldacidadania/assets/dados-abertos/docs.json`;
base `https://sistemas.tce.pi.gov.br/api/portaldacidadania` (`/prefeituras`,
`/despesas/{id}/{ano}/porFuncao|porNatureza|porElemento`, `/receitas/{id}/{ano}`, `/credores/...`).
Bom para série histórica agregada.

**TCE-MA.** O Swagger oficial e o SACOP estavam fora do ar. Funciona a API do portal de controle
social (`https://controlesocial-api.apps.tcema.tc.br/ente/find-all`,
`/despesa-empenhada/find-by-funcao-governo?enteId=&ano=`), só com totais.

**TCM-BA.** `https://www.tcm.ba.gov.br/controle-social/consulta-de-despesas/` (filtros por
município, entidade, elemento, fonte, favorecido e fase), protegido por reCAPTCHA v3; não há dados
abertos. Caminho: pedido por Lei de Acesso à Informação.

**TCE-SE e TCE-AL.** Sem dados abertos atuais.

### Norte e Centro-Oeste

Só dois tribunais deste grupo publicam despesa municipal nota a nota de forma programática: o
**TCE-TO** (sem login) e o **TCM-GO** (API que exige token). TCE-RO (403 do Akamai) e TCE-MT (WAF
F5 com desafio anti-robô) bloquearam o acesso a partir da máquina usada; vale testar de um IP
brasileiro. Em PA e GO quem fiscaliza as prefeituras é o TCM; o TCE cuida só do estado.

| Tribunal | Cobertura | Despesa nota a nota | Receita | Acesso | Anos | CNPJ do credor | Dif. |
|---|---|---|---|---|---|---|---|
| **TCE-TO** (SICAP) | 139 municípios, todas as unidades (prefeitura, câmara, fundações) | **Sim**: empenho, liquidação, pagamento | Sim (RREO) | GET sem login; "XLS" (tabela HTML) por unidade/ano/remessa | 2013– | **Sim, sem máscara** | **2** |
| **TCM-GO** | 246 municípios | **Sim**: empenho com liquidação e OP | Sim (por rubrica, fonte, mês) | API REST; **token por serviço** | Não verificado | Sim (`cpfCnpj`) | 3 |
| TCE-AC | 22 municípios + estado | Não; só painéis | Painel | Qlik e Power BI | Não verificado | — | 4 |
| TCM-PA | 144 municípios | Não encontrado (e-Contas não é publicado) | Não | Painéis; licitações em grid com export | 2025– (obras) | — | 4–5 |
| TCE-RR | 15 municípios + estado | Não | Não | PDFs de contas; licitações em JSF | — | — | 4–5 |
| TCE-AM | 62 municípios + estado | Não (e-Contas exige login) | Não | PDFs | — | — | 5 |
| TCE-AP | 16 municípios + estado | Não | Não | Nada público | — | — | 5 |
| TCE-MS | 79 municípios + estado | Não encontrado (e-Sfinge em implantação) | Não | — | — | — | 5 |
| TCE-MT (APLIC) | 142 municípios + estado | Provável no "Radar" (não verificado) | Provável | **Bloqueado** (WAF); acesso remoto pede login | — | — | 5? |
| TCE-RO | 52 municípios + estado | Não verificado | Não verificado | **Bloqueado** (403 Akamai) | — | — | 5? |
| TCE-PA | Só o estado | — | — | — | — | — | n/a |
| TCE-GO | Só o estado | Painel de despesa empenhada estadual | Painel | Qlik Sense | — | — | 4 |

**TCE-TO.** Lista de unidades por município, sem autenticação:
`GET https://portaldocidadao.tceto.tc.br/estadomunicipios/getUnidades?municipio=<IBGE>&ajax=true`
(JSON com CNPJ e nome de cada unidade). Arquivos em
`https://www.tceto.tc.br/sicap/contabilx/relatorios/planilhas/{empenho|liquidacao|pagamento}.php?unidade=<CNPJ>&exercicio=<ano>&bimestre=<remessa>&status=1&conferencia=1`.
Apesar do nome "xls", são tabelas HTML em ISO-8859-1, com números no formato 1.234,56. Com o CNPJ
da prefeitura o arquivo vem consolidado. Colunas do empenho: unidade, exercício, remessa, órgão,
unidade orçamentária, função, subfunção, programa, projeto/atividade, natureza (16 dígitos), fonte,
**CNPJ do credor completo**, nome, nº e data do empenho, valor, **histórico**, modalidade de
licitação, processo, contrato, convênio e **nº da obra**. Servidor lento (mais de 60 s por
arquivo); é preciso iterar unidade × ano × remessa. Portal:
https://portaldocidadao.tceto.tc.br/estadomunicipios/index (até 2012:
https://www.tceto.tc.br/portalcidadao/).

**TCM-GO.** Catálogo público da API: `GET https://ws.tcmgo.tc.br/api/rest/servicoRest/all` (79
serviços; interface em https://ws.tcmgo.tc.br/api/). Interessam
`empenho-service/{token}/consultaAnoMesMunicipio/{ano}/{mes}/{municipio}` (órgão, unidade,
programa, função, subfunção, elemento, histórico, `cpfCnpj`, credor, fontes, empenho, liquidação e
OP com anulações), `receita-service`, balanços, detalhamento de documentos fiscais, COLARE
(contratos, licitações, folha) e `pessoal-service`. Sem token responde "Token inválido ou inativo";
os termos de uso pedem intervalo mínimo de 10 min entre usos do token e crédito ao TCM-GO. Como
pedir o token: não verificado (provavelmente por solicitação ao tribunal). O Portal do Cidadão usa
Power BI.

**TCE-AC.** Painéis Qlik (receita, despesa, despesa por função, emendas) e Power BI em
https://tceac.tc.br/site/inicio/acre-transparente/; portal de licitações em
https://externo.tceac.tc.br/portaldaslicitacoes/menu/. Não confirmado se o Qlik é anônimo.

**TCM-PA.** Painéis em https://www.tcmpa.tc.br/raio-x-dos-municipios/ (obras desde 2025, vínculos
de servidores, royalties, educação, emendas Pix) e mural de licitações com export CSV/JSON em
https://www.tcmpa.tc.br/portalsc/LISTAGEM_LICITACOES_CONTRATOS_GRID/. Os dados contábeis
(e-Contas) não são publicados.

**TCE-RR, TCE-AM, TCE-AP, TCE-MS.** Nada aberto de despesa municipal. Os layouts de envio servem
de dicionário: tabelas do SAGRES no Roraicontas (https://roraicontas.tcerr.tc.br/cidadao/index.xhtml)
e o layout do e-Contas 2025 do TCE-AM
(https://www2.tce.am.gov.br/wp-content/uploads/2024/12/layout_econtas_2025_v1.pdf). O TCE-MS
implantou o e-Sfinge para as contas de 2025.

**TCE-MT e TCE-RO.** Bloqueados para a máquina usada. O TCE-MT tem o "Radar de Controle Público"
(Portaria 021/2025, módulos de receita, despesa, licitações, contratos e pessoal, alimentados pelo
APLIC). Testar de um IP brasileiro.

**Para estes estados**, onde o tribunal não publica: SICONFI/MSC (agregado) e os portais das
próprias prefeituras, pelo fornecedor.

## Fornecedores de portal municipal

Fonte de alcance: contagem de domínios nos links de avaliação das prefeituras do Programa Nacional
de Transparência Pública (PNTP/Atricon) 2024, feita por um notebook de terceiros
(`emdemor/deeplearning-assets`, `data/hub/analise-erps-transparencia.ipynb`) e **não recalculada
aqui**. Contagem de *links* não é contagem de *municípios*. Os dados brutos estão em
https://pntp.atricon.org.br/dados-abertos/ (zips de 212–339 MB) e são a melhor fonte para
classificar o fornecedor de cada prefeitura pelo domínio.

| Fornecedor | Como reconhecer | Alcance | Acesso à despesa | Dif. |
|---|---|---|---|---|
| **PortalTP** (empresa não identificada) | `{cidade}-{uf}.portaltp.com.br` (ASP.NET) | Não verificado; vistos em ES, MG, BA, GO, PA, SP | **API JSON aberta e listada**: `/api/transparencia.asmx` com ~90 operações (`json_empenhos`, `json_liquidacoes`, `json_pagamentos`, `json_restos_pagar`, `json_orcamento_despesas`), `?ano=&mes=`; export CSV/XLS/PDF/XML | **1** |
| **Pública Informática (e-Publica)** | `transparencia.e-publica.net/epublica-portal/#/{cidade}/portal` ou `/epublica-portal/` em domínio próprio | PNTP: 631 links; forte em SC | REST `/epublica-portal/rest/{cidade}/api/v1/despesa?periodo_inicial=MM/AAAA&periodo_final=MM/AAAA&codigo_unidade=` (JSON) | 2 |
| **Elotech (Oxy / Eloweb)** | `{cidade}.oxy.elotech.com.br/portaltransparencia/` ou `{x}.eloweb.net/portaltransparencia/` (React) | PNTP: oxy 32, eloweb 103; forte no PR | REST sem autenticação (`/portaltransparencia-api/api/entidades`, `/empenhos/lista`, `/api/liquidacoes/pagas`); formato dos filtros não acertado; reCAPTCHA invisível condicional; possível limite após ~10 chamadas | 2–3 |
| **Fiorilli (SCPI)** | `host:8079/transparencia/`, muitas vezes IP da própria prefeitura | PNTP: 876 links com `:8079`; SP, MG, RJ | API JSON `/Transparencia/VersaoJson/Despesas/?Listagem=DespesasGerais` (e por fornecedor, restos a pagar), documentada por projetos de terceiros; os hosts testados não responderam | 2–3 |
| **Betha (Transparência Fly)** | `transparencia.betha.cloud/#/{id}` (Vue) | ~850–900 municípios segundo a imprensa (não verificado para o portal); forte no Sul | REST `api.transparencia.betha.cloud/transparencia/api/consulta/...` com token OAuth anônimo + header `App-Context`; o bundle carrega chave reCAPTCHA (em quais ações: não verificado) | 3–4 |
| **Agili (ÁGILIBlue)** | `transparencia.agilicloud.com.br/{cidade}/` (Angular) | PNTP: 49; MT | Endpoints não verificados | 3? |
| **Governo Transparente** | `governotransparente.com.br/transparencia/{id}/...` | PNTP: 817 links | `/app/portal/api/v1/json/despesa/consolidada/empenho/{id}` respondeu 403 | 4 |
| **IPM Sistemas (Atende.Net)** | `{cidade}.atende.net/transparencia/...` | PNTP: 147 prefeituras; SC, PR, RS | JSON interno atrás de **CAPTCHA obrigatório** (`EXIGE_CAPTCHA = true`) | **5** (não contornar: usar o TCE) |
| Equiplano | `{cidade}{uf}.equiplano.com.br:74xx/transparencia/` | PNTP: 2.263 links; PR | Não verificado (cadeia TLS incompleta) | ? |
| Megasoft | `{cidade}.megasofttransparencia.com.br` | PNTP: 56; GO, TO | Não verificado | ? |
| CR2 | `portal.cr2.co/...?entidade={cidade}` | PNTP: 142; PA, SP | Não verificado | ? |
| Top Solutions RN | `pm{cidade}rn.transparencia.topsolutionsrn.com.br` | PNTP: 53; RN | Não verificado | ? |
| Inga Digital, SMARAPD, GOVBR, Abase | `ingadigital`, `smarapd.com.br`, `govbr.cloud`, `transparencia.abase.com.br` | Inga 77 (PR); SMARAPD 17 (SP); GOVBR 1.402 links | Não verificado | ? |

Não foram encontrados portais de transparência de Portal Fácil, Sonner, Aspec, Embras, Thema,
Siplan e Centi (só sistemas de NFS-e ou tributários).

**Campos.** O PortalTP (Colatina-ES, março/2025, ~1 MB de JSON) traz por empenho: unidade
gestora, data, número, tipo, natureza completa, função, subfunção, programa, fonte, grupo,
CPF/CNPJ e nome do favorecido, valor; liquidações e pagamentos em endpoints separados. Os campos
dos demais não foram verificados.

**Cuidados.** Um subdomínio existir não prova que a prefeitura é cliente: `santos-sp.portaltp.com.br`
mostra "PREFEITURA MUNICIPAL DEMONSTRAÇÃO", e outros redirecionam para "portal não encontrado".
Repositórios de terceiros são indício, não fato (um deles atribui o atende.net à Betha; é IPM).

**Prioridade sugerida:** PortalTP → e-Publica → Elotech → Fiorilli → Betha. Para IPM (CAPTCHA) e
para fornecedores sem acesso aberto, usar os dados que as prefeituras mandam ao Tribunal de Contas
ou o SICONFI.

### Bases que já agregam portais e fornecedores

- **PNTP/Atricon, dados abertos 2022–2025:** link avaliado por item para cada entidade.
  https://pntp.atricon.org.br/dados-abertos/ · painel: https://radardatransparencia.atricon.org.br/
- **TCE-PR, Manual de Critérios do ITP:** cita as plataformas Betha (Fly), Equiplano e Elotech/Oxy.
- **Querido Diário (Open Knowledge Brasil):** raspadores por plataforma de diário oficial e o
  Censo (https://queridodiario.org.br/censo). Cobre diários oficiais, não despesa, mas ajuda a
  identificar fornecedores.
- **Projetos com extratores por fornecedor:** `maistransparencia/transparencia` (Fiorilli e
  outros), `ygorazambuja/transparencia-mcp` (Fiorilli), `hypeneural/investiga` (IPM).
