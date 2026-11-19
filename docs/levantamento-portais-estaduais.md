# Levantamento dos portais de transparência estaduais

Objetivo: decidir como obter a despesa nota a nota (empenho, liquidação, pagamento) de cada estado
e do DF, e se há o lugar onde a despesa foi aplicada. Pesquisa feita em 19/11/2026 visitando os
portais (APIs, catálogos, cabeçalhos de arquivos; sem baixar arquivos grandes). "Não verificado"
quer dizer que a informação não pôde ser confirmada na visita. Alguns sites recusaram acesso a
partir da máquina usada (possível bloqueio por IP ou geográfico): vale testar de novo de um IP
brasileiro antes de descartar uma fonte.

Dificuldade do extrator: **1** = arquivos ou API limpos · **5** = raspagem de tela com obstáculos.

## Resumo dos 27

| UF | Fonte principal | Acesso | Anos | Nota a nota | Credor (CNPJ) | Onde foi aplicado | Dif. |
|---|---|---|---|---|---|---|---|
| PB | api.dados.pb.gov.br | API REST aberta | 2015– | Empenho, liquidação, pagamento | Sim | **Município por nota** | 1 |
| RS | dados.rs.gov.br | CKAN, ZIP mensal | 2014– | Uma linha por fase | Sim | Campo `Municipio` em ~26% das linhas, parece ser do credor | 1 |
| ES | dados.es.gov.br | CKAN, CSV anual | 2004– | NE, NL, OB | Sim | **Microrregião** no subtítulo (83% "ESTADO") | 1 |
| PE | dados.pe.gov.br | CKAN, CSV/JSON anual | 2008– | Empenho e ordem bancária | Sim | Não | 1 |
| GO | dadosabertos.go.gov.br | CKAN, CSV mensal + API | 2003– | Empenho, liquidação, pagamento | Sim | Não | 1–2 |
| DF | transparencia.df.gov.br | ZIP anual (10 CSVs) | 2009– | NE, NL, OB ligados | Sim | Região Administrativa no subtítulo (muitas vezes genérica) | 1–2 |
| MG | dados.mg.gov.br | CKAN, CSV anual (2 conjuntos a juntar) | 2022– | Por empenho, com liquidado e pago | Sim | Não | 2 |
| SC | dados.sc.gov.br | CKAN, CSV/JSON anual | 2021– | Só empenho | Sim (**CPF sem máscara**) | Às vezes no nome da subação | 2 |
| MT | consultas.transparencia.mt.gov.br | CSV anual (até 1,4 GB) | 2010– | EMP/LIQ/PAG | Sim (**CPF sem máscara**) | Não | 2 |
| PA | api-notas-empenho.sistemas.pa.gov.br | API REST aberta | 2016– | Empenho, com pago e itens | Sim | Não | 2 |
| RR | api.transparencia.rr.gov.br | API REST + CSV/JSON | 2011– | Credor×UO×mês; NE/NL/OB por documento | Sim (**CPF sem máscara**) | Não | 2 |
| AC | transparencia.ac.gov.br | JSON via POST (CSRF) | 2015– | Empenho + liquidações e pagamentos | Sim | Não | 2 |
| RO | transparencia.ro.gov.br | CSV anual + consultas com token | 2016– | Empenho com liquidado e pago | Sim | Página agregada "presença nos municípios" | 2 |
| PI | api.transparencia.pi.gov.br | API REST (OpenAPI) + CSV | 2020– | Empenho com histórico de pagamentos | Sim (PF omitida) | Não | 2 |
| MA | dados.ma.gov.br | DKAN, CSV mensal | 2019– | Uma linha por fase | Sim | Não | 2 |
| AL | transparencia.al.gov.br | ZIP anual + API | 2000–2023 (2024+ dá 404) | NE, OB, lançamentos | Sim | Região de planejamento no subtítulo | 2 |
| CE | cearatransparente.ce.gov.br | CSV/XLSX anual | 2010– | Empenho com pago | **Não** (só nome) | **Região administrativa** | 2 |
| MS | dados.ms.gov.br | CKAN, CSV mensal | 2012– | Empenho/credor/mês com liquidado e pago | Sim | Não | 2–3 |
| RJ | API do TCE-RJ (`empenho_estado`) | REST JSON/CSV | 2022– | Por empenho | Sim | Não | 3 |
| PR | Fazenda PR, CSV de empenhos | CSV anual | 2023– | Por item de empenho | Sim | Não | 3 |
| BA | dados.ba.gov.br (FIPLAN) | ZIPs diários de 228–345 MB | 2013– | Agregado + ordem cronológica de pagamentos | Sim | **Território** (região orçamentária) | 3 |
| SE | API interna do portal | JSON paginado | 2023– | Empenho, liquidação, pagamento | Sim | Não | 3 |
| AM | sistemas.sefaz.am.gov.br | API com parâmetros cifrados (RSA+AES) | 2021– (CSV agregado) | Sim na interface | Não verificado | Localizador no CSV agregado | 4 |
| SP | SEFAZ: SOAP + formulários ASP.NET | Agregado; credor só por formulário | 2010– | Não em lote | Só via formulário | Localizador quase sempre "0000" | 4 |
| AP | transparencia.ap.gov.br | Formulários com reCAPTCHA | 2004– | Parcial | Não verificado | Não verificado | 5 |
| RN | transparencia.rn.gov.br | Só interface (consulta de empenhos dá erro 500) | 2019– | Não acessível | Sim (por favorecido) | Não | 5 |
| TO | transparencia.to.gov.br | Interface Vaadin, sem link de download | Não verificado | Não verificado | Não verificado | Não verificado | 5 |

## O que isso significa para o projeto

- **Dá para cobrir a maioria.** 18 estados têm arquivos ou API com dificuldade 1–2. Com eles já
  há uma parte grande do país; SP, a maior despesa estadual, é o caso difícil.
- **"Onde foi aplicado" é raro.** Só a PB traz município por nota. ES, CE, BA, AL e DF trazem
  região (microrregião, território, região administrativa). Nos demais, a geografia vai sair de
  duas pistas: transferências a municípios (modalidade de aplicação 40, ou credor "Município de
  X", casado pelo CNPJ da prefeitura) e, com cuidado, o endereço do CNPJ do credor.
- **Proteção de dados.** MT, RR e SC publicam CPF de pessoa física sem máscara. O pipeline tem
  que mascarar na ingestão e nunca publicar o número completo.
- **Conferência.** A soma do nota a nota de cada estado tem que bater com o total que ele
  declarou ao Tesouro (SICONFI, que já baixamos). A MSC do SICONFI (saldos mensais por órgão,
  função e natureza) serve de alternativa para os estados sem nota a nota.
- **Onde o portal falha:** RJ (TCE-RJ resolve a partir de 2022), RN (TCE-RN recebe os dados, mas
  não publica; pedido por Lei de Acesso à Informação), AP e TO (automação de navegador ou LAI).

## Ordem sugerida

1. **Prova de conceito com PB e ES:** fontes limpas e com geografia (município e microrregião).
2. **Grandes e limpos:** RS, PE, GO, MG, DF.
3. **APIs de dificuldade 2:** PA, RR, PI, MA, AL, CE, SC, MT, AC, RO, MS.
4. **Médios:** RJ (via TCE-RJ), PR, BA, SE.
5. **Difíceis:** SP (formulários), AM (cifra no cliente), AP, RN, TO (navegador ou LAI).

## Notas por estado

### Sul e Sudeste

**RS.** Arquivos mensais `despesas-do-estado-AAAAMM.zip` (antes `gasto-rs-AAAAMM.zip`), ~660 MB
por mês descompactado. Cada linha é um evento (`FaseGasto`) com números de empenho, liquidação e
pagamento, favorecido, CNPJ (CPF trocado por 000.000.000-00), órgão, UO, função, subfunção,
programa, projeto, ação, elemento, rubrica, recurso e `Cod_Municipio;Municipio`. Esse município
parece ser do credor, não do lugar da despesa (uma linha da "Pref Mun de Aceguá" aparece com Porto
Alegre). Agosto e setembro de 2026 vieram quase vazios. Receita em `receita-rs.zip`.
https://dados.rs.gov.br/dataset/2026-despesa-do-estado · https://dados.rs.gov.br/dataset/layouts-dos-arquivos

**ES.** CSV anual do SIGEFES, 1,3–1,5 GB por ano (redireciona para S3 com URL assinada): CPF/CNPJ
mascarado, favorecido, documento (NE, NL, OB), órgão, UG, função, subfunção, programa, ação,
elemento, subelemento, fonte, modalidade, contrato, licitação e **`Subtitulo`**: "ESTADO" (83%) ou
uma das 10 microrregiões. O TCE-ES publica ZIPs de despesas e receitas estaduais de 2016 a 2026.
https://dados.es.gov.br/dataset/portal-da-transparencia-despesas-execucao-orcamentaria-e-financeira ·
https://dados.es.gov.br/dataset/receitas-e-despesas-estaduais

**MG.** `empenho{AAAA}.csv` (credor, CPF/CNPJ mascarado, UO, elemento, fonte, processo, licitação,
contrato, empenhado/liquidado/pago) precisa ser juntado com `execucao.csv.gz` do armazém SIAFI
(função, subfunção, programa, ação por empenho) por UO + nº do empenho. Só 2022 em diante; o
conjunto antigo "Despesa pública" (2002+) está praticamente vazio.
https://dados.mg.gov.br/dataset/portal_despesa_empenho · https://dados.mg.gov.br/dataset/dados-armazem-siafi-2026

**SC.** `empenhos-AAAA.csv/json/xlsx` (2021–2026): empenho, CPF/CNPJ (**CPF aparentemente sem
máscara**), credor, órgão, UG, função, subfunção, programa, ação, **subação**, fonte, subelemento,
valor. Liquidações só de 2022; o histórico tem quebras de linha dentro do CSV.
https://dados.sc.gov.br/dataset/empenhos

**RJ.** A SEFAZ (TFE) bloqueou por IP. A API do TCE-RJ tem `GET /api/v1/empenho_estado?ano=`
(unidade, mês, empenho, CPF/CNPJ, função, empenhado, liquidado, pago), só de 2022 em diante e sem
programa nem natureza; também `receitas_estado`, `dotacao_estado`, `contratos_estado`.
https://dados.tcerj.tc.br/api/v1/openapi.json · https://dadosabertos.rj.gov.br/dataset/tfe-despesa (agregado)

**PR.** CSV anual "Empenhos_AAAA_publico.csv" (2023–2026, semanal): UG, empenho, data, CPF/CNPJ,
credor, item, quantidade, valor, modalidade, processo. Sem função, programa nem natureza; o resto
está em FlexPortal e Power BI. https://www.fazenda.pr.gov.br/Pagina/Consulta-Detalhada-do-Empenho

**SP.** Web service SOAP `TransparenciaServico.asmx` (ConsultarDespesas, ConsultarReceitas;
2010+, diário) devolve só valores agregados por classificação, sem credor; a cadeia TLS do serviço
vem incompleta. Credor e ordem bancária só no formulário ASP.NET `ConsultaDespesaAno.aspx`
(ViewState). Não há download em lote nem dados estaduais no TCE-SP.
https://portal.fazenda.sp.gov.br/acessoinformacao/Paginas/Web-Services.aspx

### Nordeste

**PB.** O melhor caso. API `https://api.dados.pb.gov.br/api/v1/despesas/...` (Swagger em
`/swagger/`): `notas_empenho`, `liquidacoes`, `autorizacoes_pagamento`, `execucao_orcamentaria`,
com classificação completa, `cpfCnpj` e **`codigoMunicipio`/`nomeMunicipio`**. Paginação até 1000,
`mes` obrigatório, GET funciona sem token. Receita em `api.dadosabertos.codata.pb.gov.br`.

**PE.** CKAN `todas-despesas-detalhadas` (CSV/JSON por ano, 2008–2026, latin-1, dicionário em
JSON): empenho, UG, credor ("CNPJ - nome", CPF mascarado), classificação completa com subação,
empenhado/liquidado/pago. `all-pagamentos` traz as ordens bancárias. A API do TCE-PE
(`sistemas.tce.pe.gov.br/DadosAbertos/`) tem DespesasEstaduais, EmpenhoResumo e ReceitasEstaduais.

**PI.** API `https://api.transparencia.pi.gov.br/api/v2/despesas/{ano}/{mes_de}/{mes_ate}/` (2020+),
detalhe por empenho e `historico-financeiro/`, download CSV/XLSX. Credor PF vem nulo. Sem região.

**MA.** DKAN `despesa-2019` a `despesa-2026`: CSV mensal (21–88 MB) com fase, empenho, liquidação,
pagamento, CNPJ do credor e classificação. A coluna `grupo_elemento` parece trocada em parte das
linhas. Cadeia TLS incompleta (incluir o certificado intermediário).

**AL.** ZIPs `/media/arquivo/{tipo}-{ano}.zip` (2000–2023; 2024–2026 dão 404): nota de empenho com
"Código PI - Localizador", credor, local de entrega; "lançamento pago" com **subtítulo** = região
de planejamento (a maior parte do valor em "TODO ESTADO"). API agregada em
`/despesa/json-despesa-avancada-filtro/`.

**CE.** `cearatransparente.ce.gov.br/files/downloads/integration/expenses/neds/{ano}/notas_de_empenho_{ano}.csv|.xlsx`
(formato muda por ano): classificação completa e **região administrativa**, mas o credor vem só
pelo nome, sem CPF/CNPJ. O catálogo dados.ce.gov.br deu 403.

**BA.** dados.ba.gov.br (SEFAZ/FIPLAN, diário, cadeia TLS incompleta): `despesas.zip` (228 MB;
`VW_PAINEL_DESPESA.csv` de 2,4 GB, agregado por dotação e mês, com **região orçamentária**) e
`ordemcronologicapagamentos.zip` (345 MB; contratos, liquidações e ordens bancárias com CPF/CNPJ).
O portal transparencia.ba.gov.br deu 503.

**SE.** A API oficial é agregada e exige UG. O portal usa uma API interna não documentada,
`https://api.transparencia.se.gov.br/api/relatorios/{empenho|liquidacao|pagamento}?ano=&mes=`, com
dados de 2023 em diante.

**RN.** Catálogo vazio; a consulta de empenhos dá erro 500; só a visão por favorecido funciona,
em HTML paginado com links criptografados. O TCE-RN recebe empenhos, liquidações e pagamentos
(SIAI), mas não publica. Caminho provável: pedido por Lei de Acesso à Informação.

### Norte

**PA.** API aberta `https://api-notas-empenho.sistemas.pa.gov.br/notas-empenho?ano=&pagina=&qtdRegistros=1000`
(número, data, órgão, credor, CPF/CNPJ, empenhado, pago) e `/notas-empenho/detalhe?idNE=` (função,
subfunção, programa, ação, natureza, fonte, licitação, itens). Sem região de integração; liquidação
não aparece separada. O domínio antigo do portal está com certificado expirado.

**AM.** Sistema da SEFAZ em React com API (`/transparencia/api/pagamentos`, `/documento/ne|nl|ob`)
cujos parâmetros são cifrados no navegador (AES + chave RSA pública). O CSV aberto
`/transparencia/api/dadosabertos/execucao?exercicio=` (2021+) é agregado, sem credor, mas traz
**localizador**.

**AC.** `POST /despesas/listar` (DataTables, com CSRF e cookie): empenho, credor com CNPJ,
natureza, função, subfunção, fonte, histórico, empenhado/liquidado/pago; detalhe de liquidação e
pagamento por empenho. Sem programa/ação na listagem.

**AP.** Formulários PHP com reCAPTCHA e export por consulta; cadeia TLS incompleta; respostas de
até 50 s. Credor, município e receitas não verificados.

**RO.** `GET /Despesa/DonwloadEmpenhos?Ano=&ContentTypeFile=CSV` (~24 MB/ano): data, empenho,
unidade, credor, licitação, histórico, empenhado/liquidado/pago. A classificação só vem nas
consultas com token anti-forgery. Página "presença nos municípios" agregada até 2024.

**RR.** API aberta `https://api.transparencia.rr.gov.br/api/v1/portal/transparencia/despesa-detalhada/listagem-filtrada`
(2011+): UO, credor, **CPF sem máscara**, função, ação, fonte, natureza, valores; download CSV/JSON;
detalhe NE/NL/OB por documento.

**TO.** Portal Vaadin renderizado no servidor; a página de dados abertos lista "Despesas
detalhadas – CSV/XLS" sem link funcional. Só com navegador automatizado ou pedido por LAI.

### Centro-Oeste

**GO.** CKAN https://dadosabertos.go.gov.br: `empenhos` (CSV mensal, ZIP anual desde 2003),
`liquidacoes`, `pagamentos`, `execucao-orcamentaria-funcional` (classificação por empenho). O nº do
empenho vem em formatos diferentes entre os conjuntos (com e sem pontos): normalizar no join.
Receita: `receitas-detalhadas` (2006+).

**MT.** `https://consultas.transparencia.mt.gov.br/dados_abertos/despesa/Despesa_{ANO}.csv`
(0,7–1,4 GB): empenho, documento, UO/UG, credor, CPF/CNPJ (**sem máscara**), classificação completa
até subelemento, valor, histórico. Processar em streaming. Receita em `/dados_abertos/receita/`.

**MS.** https://www.dados.ms.gov.br/dataset/despesas-por-credor-mensal (2012–2026, ~14 MB/mês):
órgão, natureza, programa, função, subfunção, ação, CPF/CNPJ, credor, empenho, empenhado/liquidado/
pago no mês. Sem data da despesa; folha agregada como "VENCIMENTOS". O portal tem a seção de dados
abertos quebrada.

**DF.** `https://www.transparencia.df.gov.br/arquivos/portal-dados-abertos/Despesa_{2009..2026}.zip`
(37–67 MB, separador `¨`): empenho, liquidação, pagamento e as ligações entre eles; o empenho traz
**subtítulo** (localizador). Há um painel por Região Administrativa (`/api/v2/despesas-ras`) e o
GeoJSON das RAs (`/assets/delimitacao_ras.json`). A RA vem no texto do subtítulo e muitas vezes é
genérica: precisa de uma tabela subtítulo → RA.
