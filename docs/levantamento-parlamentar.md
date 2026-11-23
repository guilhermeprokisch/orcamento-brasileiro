# Levantamento: a página do parlamentar (cota, salário, gabinete e emendas)

Levantado em 23/11/2026. Objetivo: a página de cada deputado federal e senador, que hoje só tem as emendas
(`/emendas/buscar?autor=…`), passar a mostrar também o que ele custa: a cota parlamentar, o salário e o gabinete.

## 1. Cota parlamentar da Câmara (CEAP)

- **Arquivo:** `https://www.camara.leg.br/cotas/Ano-AAAA.csv.zip`, um por ano, de 2008 até o ano corrente.
  Atualizado todo dia (o de 2025 foi regravado em 22/11/2026). Sem login, sem captcha.
- **Tamanho:** 2025 tem 6,9 MB zipado e 72 MB aberto, com 209 mil linhas. 2024: 7,5 MB. 2026 (até nov.): 4,8 MB.
- **Formato:** CSV com `;`, UTF-8 com BOM, tudo entre aspas.
- **Campos que usamos:**
  - `ideCadastro`: o id do deputado na API da Câmara (ex.: Tabata Amaral = 204534). **É a chave.**
    Atenção: `nuDeputadoId` (ex.: 3208) é outro número, interno da cota; não serve para a API nem para a foto.
  - `txNomeParlamentar` (nome parlamentar, com acento), `sgUF`, `sgPartido`;
  - `txtDescricao`: a categoria (21 em 2025: divulgação, locação de veículos, escritório, passagem, combustível...);
  - `txtFornecedor`, `txtCNPJCPF`: quem recebeu. 14 dígitos = empresa; 11 dígitos = pessoa física;
  - `vlrLiquido`: o valor reembolsado (já com glosa). Pode ser negativo (passagem devolvida, auxílio-moradia acertado);
  - `numMes`, `numAno`.
- **Campos que NÃO entram nunca:** `cpf` (o CPF do próprio deputado vem no arquivo), `txtPassageiro`, `urlDocumento`.
  A leitura escolhe as colunas pelo nome; o CPF não chega a ser carregado.
- **Linhas sem deputado:** as lideranças ("LIDERANÇA DO GOVERNO NA CÂMARA") têm `ideCadastro` vazio e `sgUF = NA`. Ficam fora.
- **Números de 2025:** R$ 240 milhões, 562 deputados (inclui suplentes que passaram pelo cargo). Por categoria:
  divulgação R$ 102 mi, locação de veículos R$ 42 mi, escritório R$ 34 mi, passagens R$ 27 mi, combustível R$ 23 mi.
  Pessoa física: 1.848 notas, R$ 8,3 milhões (quase todo aluguel de escritório).

### Teto da cota por estado (Câmara)

O teto é mensal e muda com o estado (passagem para o Norte custa mais). O saldo que sobra num mês passa para o
seguinte, dentro do mesmo ano; por isso um mês pode passar do teto e o ano não.

| Vigência | Ato | DF (menor) | RR (maior) | SP |
|---|---|---|---|---|
| fev/2023 a jan/2026 | [Ato da Mesa 270/2023, anexo I](https://www2.camara.leg.br/legin/int/atomes/2023/atodamesa-270-19-janeiro-2023-793708-anexo-cd-mesa.pdf) | 36.582,46 | 51.406,33 | 42.837,33 |
| desde fev/2026 | [Ato da Mesa 244/2026](https://www2.camara.leg.br/legin/int/atomes/2026/atodamesa-244-20-fevereiro-2026-798720-publicacaooriginal-178157-cd-mesa.html) (IPCA de fev/2023 a dez/2025); tabela na [página da Câmara](https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/cota-parlamentar) | 41.612,55 | 58.474,70 | 48.727,46 |

As duas tabelas inteiras (27 estados) vão como constante no pipeline, com a fonte.

## 2. Cota parlamentar do Senado (CEAPS)

- **API:** `https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/AAAA` (JSON, 9,5 MB em 2025).
  Tem `codSenador`, que a CSV antiga (`senado.leg.br/transparencia/LAI/verba/despesa_ceaps_AAAA.csv`, em Latin-1) não tem.
  Usamos a API.
- **Campos:** `codSenador` (**a chave**; Romário = 5322), `nomeSenador` (em maiúsculas), `tipoDespesa` (7 categorias),
  `cpfCnpj`, `fornecedor`, `valorReembolsado`, `ano`, `mes`.
- **CPF:** o Senado já publica mascarado (`586.***.***-53`). Mesmo assim, pessoa física entra só somada.
- **Estado do senador:** não vem na cota. Sai de `legis.senado.leg.br/dadosabertos/senador/lista/legislatura/57`
  (245 nomes na legislatura, inclusive suplentes que já saíram).
- **Números de 2025:** R$ 37,3 milhões, 83 senadores. Locomoção e combustível R$ 8,6 mi, divulgação R$ 7,6 mi,
  consultorias R$ 7,3 mi, passagens R$ 6,8 mi, aluguel de escritório R$ 5,3 mi.
- **Teto do Senado:** também varia por estado, mas não achei a tabela vigente em formato aberto. A comparação usa
  os colegas do mesmo estado, que não depende do teto.

## 3. Salário

- **Subsídio:** R$ 46.366,19 por mês desde 1º/2/2025, igual para deputado e senador (Decreto Legislativo 172/2022).
  Antes: R$ 44.008,52 (fev/2024) e R$ 41.650,92 (abr/2023). Mais 13º e terço de férias. Vai como constante.
- Os supersalários do Legislativo já estão em `/supersalarios` (#132); a página do parlamentar não repete, só linka.

## 4. Gabinete: verba e assessores

- **Câmara, verba de gabinete:** a página `camara.leg.br/deputados/{ideCadastro}/verba-gabinete?ano=AAAA` traz, mês a mês,
  o valor disponível e o gasto (2025: R$ 133.170,54 por mês). Não há arquivo aberto com isso; são 513 páginas por ano.
  O `robots.txt` da Câmara não bloqueia esse caminho. Exemplo 2025: Tabata Amaral gastou R$ 1,53 mi dos R$ 1,59 mi.
- **Câmara, assessores:** `dadosabertos.camara.leg.br/arquivos/funcionarios/csv/funcionarios.csv` (3,5 MB), a foto de hoje.
  A lotação diz o gabinete ("GAB. 4/848 - TABATA AMARAL"); contamos os `Secretário Parlamentar` de cada gabinete
  (o máximo é 25). Os nomes não são guardados.
- **Senado, assessores:** `adm.senado.gov.br/adm-dadosabertos/api/v1/servidores/servidores` (9,8 MB): quem está ATIVO
  em "Gabinete do Senador X" e nos "Escritório de Apoio ... do Senador X". Contamos; nomes não são guardados.
- **Senado, verba:** o senador não tem uma verba de gabinete em reais como o deputado; tem um limite de cargos. Fica só a contagem.

## 5. Como ligar a cota às emendas

As emendas (`data/publico/emendas-pagamentos.parquet`, da CGU) só têm o nome do autor, sem acento e com só a primeira
letra maiúscula ("Romario", "Acacio Favacho"). O site já faz o arquivo de cada autor pelo `slug` do nome
(`fichas_emendas.slug`).

- Teste com 2025: o `slug` do nome parlamentar da cota bate com um autor de emendas de 2023 em diante em
  **539 de 562 deputados** e **80 de 83 senadores**. Os que não batem são suplentes que passaram pouco tempo no cargo e
  não têm emenda própria (ex.: Renan Ferreirinha, José Lacerda). Nenhum nome repetido entre deputados e senadores em 2025.
- Regra: casar pelo `slug` do nome **e** conferir que é único no ano. Se dois parlamentares tiverem o mesmo nome, não
  liga (e fica anotado na saída do pipeline).
- A chave da página nova é a do Congresso (`ideCadastro` ou `codSenador`), e não o nome, para não misturar dois
  parlamentares com nome parecido.

## 6. Comparação justa

- **Medida:** gasto médio por mês em que teve despesa. Assim, o suplente que ficou 4 meses não parece "econômico".
- **Com quem:** a mediana dos colegas do mesmo estado na mesma Casa, com pelo menos 6 meses no ano.
  - Câmara: de 8 (estados menores) a 70 (SP) colegas. Medianas de 2025: de R$ 35,5 mil/mês (DF) a R$ 48,9 mil (AC).
  - Senado: são só 3 por estado, então a página mostra os três lado a lado, com o nome, em vez de uma mediana.
- **Também:** quanto do teto do estado foi usado no ano (só Câmara).

## 7. Cuidados com dado pessoal

- Fornecedor pessoa física (CPF): só o total do ano e a quantidade de notas. Nem nome nem CPF.
- Empresa (CNPJ): nome e CNPJ.
- **Microempreendedor individual:** tem CNPJ, mas o nome da empresa é o nome da pessoa e às vezes traz o CPF colado
  (o nome seguido dos 11 dígitos do CPF; achei um caso na cota do Romário). O pipeline apaga do nome qualquer sequência de 11 dígitos.
  Decidir com o Guilherme se o MEI aparece pelo nome (é CNPJ público) ou entra somado com as pessoas físicas.
- Assessores: só a contagem.

## 8. TSE: a base comum de todos os eleitos

Ampliação de 23/11/2026: a página passa a ser de cada político eleito, não só do parlamentar federal.

- **Fonte:** `https://cdn.tse.jus.br/estatistica/sead/odsele/<conjunto>/<conjunto>_<ano>.zip`, sem login. Um CSV por estado
  e um `_BRASIL`, em Latin-1, com `;`.

| Conjunto | 2022 (federal e estadual) | 2024 (municipal) | O que usamos |
|---|---|---|---|
| `consulta_cand` | 5 MB | 78 MB | cargo, partido, nome de urna, situação (eleito, eleito por QP, por média, suplente), `SQ_CANDIDATO` |
| `bem_candidato` | 5 MB | 44 MB | o total de bens declarados e o total por tipo (casa, apartamento, cotas de empresa...) |
| `prestacao_contas` (candidatos) | 500 MB | 1,3 GB | receitas de campanha por origem: fundo eleitoral, fundo partidário, partido, pessoa física, recursos próprios |
| `votacao_candidato_munzona` | 588 MB | 48 MB | votos de cada eleito (somados) |

- **Senadores em exercício hoje:** 27 eleitos em 2022 e 54 em 2018. Precisa também do TSE de 2018 (só senadores).
- **Eleitos em 2022:** 513 deputados federais, 27 senadores, 27 governadores, 1.035 deputados estaduais e 24 distritais.
  Em 2024: cerca de 5.570 prefeitos e 58 mil vereadores.

### O que nunca entra

- `NR_CPF_CANDIDATO`, `NR_TITULO_ELEITORAL_CANDIDATO`, `DS_EMAIL`, data de nascimento: não são guardados.
- A descrição de cada bem (`DS_BEM_CANDIDATO`): é texto livre e às vezes traz endereço. Só o tipo e o valor, somados.
- Doador pessoa física: só o total e a quantidade. Desde 2015 empresa não pode doar; partido e outro candidato aparecem
  com o nome.

### Como ligar o TSE à Câmara e ao Senado

- **Câmara:** pelo CPF, só na memória. A cota da Câmara traz o CPF do deputado. Os dois arquivos são lidos juntos,
  casados pelo CPF, e só sai o par `ideCadastro` ↔ `SQ_CANDIDATO`. Teste com a cota de 2025: **os 562 deputados casam**
  (490 eleitos em 2022, 70 suplentes). Pelo nome, só 484 casariam: 78 usam na Câmara um nome diferente do de urna.
- **Senado:** a cota do Senado não traz CPF. Casar pelo nome e pelo estado (81 casos, conferidos um a um na primeira carga).

### O endereço de cada político

- `/politicos/<uf>/<nome>` para cargos federais e estaduais (ex.: `/politicos/sp/tabata-amaral`, `/politicos/rj/romario`).
- `/politicos/<uf>/<cidade>/<nome>` para prefeitos e vereadores (depois).
- O nome é o parlamentar (o da Câmara ou do Senado), senão o de urna. Entre os eleitos de 2022, nenhum nome de urna se
  repete dentro do mesmo estado; em 5 casos ele se repete entre estados, por isso o estado vai no endereço.
- Se um dia dois nomes coincidirem no mesmo estado, o segundo ganha o cargo no fim (`-deputado-estadual`).

## 9. Deputados estaduais e governadores (eleitos em 2022)

Levantado em 23/11/2026. As notas completas (URLs testadas, campos e um exemplo por estado) ficaram fora do git, nas
notas da sessão; aqui vai o que decide o desenho.

### 9.1 Base comum: o TSE de 2022

- Os mesmos arquivos da seção 8. Eleitos: **27 governadores** (2 mulheres), **1.035 deputados estaduais** (186
  mulheres) e **24 distritais**.
- **A chave é `tse-<SQ_CANDIDATO>`**, o número da candidatura no TSE. O CPF não é guardado nem usado como chave.
- Para governador entram os votos dos dois turnos. Para todos os cargos estaduais entram as 5 cidades com mais votos
  (código do TSE, não o do IBGE) e a posição entre os eleitos do mesmo cargo e estado.
- **Nome:** o de urna, nenhum se repete no mesmo estado. Sete governadores usam só o primeiro nome ou o sobrenome
  ("Tarcísio", "Zema", "João", "Fábio", "Jerônimo", "Helder", "Clécio"); para eles fica uma tabela curta com o nome
  público (Tarcísio de Freitas, Romeu Zema...).
- **Ligar com a Câmara e o Senado:** por nome completo + estado, como em `ligar_mesma_pessoa`. São só 3 pessoas:
  Bruna Furlan (SP) e Ney Leprevost (PR), que saíram da Câmara em 2023, e Sargento Reginauro (CE), suplente no
  Senado desde ago/2026. Para conferir, contei também pelo CPF, só na memória: as mesmas 2 da Câmara.
  A regra do nome não perde ninguém.
- **Erro corrigido junto:** o zip de votos traz um CSV por estado e um `_BRASIL.csv` com todos. O código só pulava o
  `_BR.csv`, por isso **os votos das páginas federais estavam em dobro** (Tabata Amaral: 675.746 no site, 337.873
  no TSE).
- Bens: VGBL, ouro, terra nua e benfeitorias caíam em "Outros bens"; agora vão para "Dinheiro e aplicações" ou
  "Imóveis".
- **Fotos:** o divulgacandcontas devolve 403. O TSE publica as fotos de 2022 num zip por estado
  (`cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/fotos/foto_cand2022_<UF>_div.zip`; SP tem 90 MB, AC 15 MB).

### 9.2 Verba das Assembleias, estado por estado

"Verba" não é a mesma coisa em todo lugar. Há quatro tipos:
- **reembolso com nota fiscal**: dá para mostrar o fornecedor;
- **só o total por categoria**;
- **valor fixo por mês**, sem nota;
- **nada publicado**.

| UF | Fonte | Formato | Captcha | Fornecedor | Dá para automatizar |
|---|---|---|---|---|---|
| SP | ALESP, dados abertos: `www3.al.sp.gov.br/repositorio/dados-abertos/output/json/despesas.json` | JSON, um arquivo com tudo (161 MB), 2002–hoje | não | CNPJ | **sim, um download**. O certificado vem sem o intermediário (Let's Encrypt YE1): passar a cadeia com `--cacert`. O campo `cpf` (fornecedor pessoa física) não pode ser lido |
| MG | ALMG, API v2 `/api/v2/prestacao_contas/verbas_indenizatorias/deputados/{id}/{ano}/{mes}` | JSON, 2019–hoje | não | CNPJ | sim, deputado a deputado e mês a mês (~924 chamadas por ano). O CSV em lote está num caminho que o robots.txt bloqueia |
| GO | `transparencia.al.go.leg.br/api/transparencia/verbas_indenizatorias` | JSON, 2011–hoje | não | CNPJ | **sim**, a melhor API (traz até foto e partido) |
| MS | `transparencia2.al.ms.gov.br/ceap/notas/exportar-csv?ano=AAAA` | CSV por ano | não | CNPJ | **sim**; sem id do deputado, casa pelo nome |
| CE | Alece, `/despesas/verba-desempenho-parlamentar/csv?mes=MM&ano=AAAA` | CSV por mês, todos os deputados, 2021–hoje | não | CNPJ (27% das linhas com CPF, que é descartado) | **sim** |
| PE | Alepe, `verbaindenizatoria*.php` (API da página) | JSON, 2023–hoje | não | CNPJ | sim, deputado × mês; a lotação por gabinete está em `dadosabertos.alepe.pe.gov.br` |
| BA | ALBA, `/transparencia/verbas-idenizatorias-excel?ano=` + página de detalhe | XLSX do ano + HTML | não | CNPJ só no detalhe | sim, ~4.400 páginas por ano |
| AM | Aleam, Controle de Cota Parlamentar | HTML (POST), 2015–hoje | não | CNPJ | sim, deputado × mês; site lento |
| AP | Alap, CEAP | HTML, 2012–hoje | não | CNPJ | sim, deputado × mês |
| RO | `transparencia.al.ro.leg.br` › Verba Indenizatória | HTML, 2020–hoje | não | CNPJ | sim, deputado × mês. Valores altos (R$ 1,3 a 1,5 mi por ano); ler o Ato MD 015/2024 antes |
| TO | `al.to.leg.br/transparencia/verbaIndenizatoria` | PDF com texto, 2017–hoje | não | CNPJ (CPF sem máscara: descartar) | sim, devagar (robots pede 10 s: ~1,6 h por ano) |
| DF | CLDF, CKAN `dados.cl.df.gov.br`, `verbas-indenizatorias` | CSV/XLSX por ano | não | CNPJ | sim, mas as planilhas estão sujas (colunas deslocadas) e trazem o CPF do deputado |
| RJ | ALERJ, DOCIGP (`docigp.alerj.rj.gov.br/api/v1/...`) | JSON, 2019–hoje | não | CNPJ | o robots.txt bloqueia tudo: **pedir à ALERJ ou à LAI** |
| SC | ALESC, `transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/{ano}` | CSV por ano, 2011–hoje | não | só o nome, sem CNPJ | sim; o total inclui diárias e passagens de assessores |
| PB | ALPB, VIAP | ODS/XLSX por deputado e mês | não | nome; CNPJ mascarado | sim; o formato mudou em out/2025 |
| ES | ALES, `/Transparencia/Api/CotasParlamentaresNovoTable/...` | HTML | não | não | sim, só o total por categoria |
| RS | ALRS, `/parlamentares/gastos/pesquisa` | HTML | não | não | sim, total por categoria, com cota e saldo do mês |
| MA | Alema, CEAP | HTML (JSF) | não | não | sim, com trabalho; total por categoria |
| SE | Alese, PDF mensal com todos os deputados | PDF com texto | não | não | sim; competência é o mês anterior ao pagamento |
| PI | Alepi, grade ScriptCase | HTML com sessão | não (WAF Akamai) | não (as notas dão 403) | com trabalho |
| RR | `transparencia.al.rr.leg.br`, ODT/PDF por deputado e mês | só desde set/2025 | não | não | trabalhoso |
| AL | ALE-AL, VIAP | PDF escaneado | não | não | só com OCR |
| PA | Alepa, painel DevExpress (JSON) | valor fixo de R$ 35 mil/mês | não | não há nota | sim, uma chamada por ano |
| MT | não publica despesa; verba fixa (R$ 65 mil/mês, segundo a imprensa) | — | — | — | não |
| AC | não publica (só o regulamento, Res. 132/2018) | — | — | — | não |
| PR | ALEP, `consultas.assembleia.pr.leg.br/#/ressarcimento` | app | **pede captcha** de 2020 em diante | — | não: **LAI** |
| RN | `api-transparencia.al.rn.leg.br/verbas/despesas` | JSON/CSV | não | ? | a API pede um token, que está fixo no JS do site. Não usado: **decisão do Guilherme** |

Resumo: 13 Casas dão o fornecedor com CNPJ (SP, MG, GO, MS, CE, PE, BA, AM, AP, RO, TO, DF e RJ, esta com o robots
contra); 9 dão só o total ou um valor fixo; AC e MT não publicam; PR e RN estão travados.

Exemplos de 2025 (somados dos arquivos): Eduardo Suplicy (SP) R$ 254.201; Bruna Furlan (SP) R$ 111.727; mediana da
ALESP R$ 36,5 mil por mês (95 deputados com 6 meses ou mais); teto da ALESP 1.250 UFESPs por mês (≈ R$ 46 mil).

**Assessores por gabinete** (só a contagem): SP (`lotacoes.json`, 8 a 31 por gabinete), PE, DF, PA (com o valor em
R$), RO, RR, MT, ES e SC. MG pede captcha na folha; RJ publica em PDF sem a lotação.

**Subsídio do deputado estadual:** R$ 34.774,64 desde fev/2025 (75% do federal) na maioria dos estados, confirmado na
lei em SP (Lei 18.384/2025), MG, PE (Lei 18.138/2023), PA e GO. Exceções a conferir: RS (R$ 34.772,11), CE (a folha
mostra 15% a mais, um auxílio-saúde de 2025), MA (o valor cheio só desde fev/2026) e MT (a folha mostra R$ 41.729,57).

### 9.3 Salário do governador

O subsídio é fixado por lei estadual e muda muito de um estado para outro: de R$ 21.868,14 (RJ, desde 2015) a
R$ 46.366,19 (SE). Em 18 estados o valor foi conferido no texto da lei. A tabela com as leis e os valores desde
jan/2023 vai como constante no pipeline, com a fonte. Pendentes: AC e RN (lei não achada), RS (número da lei), MS (só
imprensa), AL, GO e MT (seguem a revisão geral dos servidores, sem lei própria).

- **A folha com o nome:** em lote só em ES, GO, MG, SP, PE, RJ, PB, PI e SC. Pedem captcha: AP, MT e o lote do PA.
  O CE bloqueia robôs. A BA não mostra nomes.
- **Troca de governador em 2026:** 11 dos 27 eleitos saíram do cargo (AC, AM, DF, ES, GO, MG, MT, PA, PB, RJ e RR),
  quase todos em março e abril, para concorrer. A página do eleito precisa dizer até quando ele ficou, e o salário
  de 2026 conta só esses meses.
- **Casos que não seguem a regra:** em PE a governadora aparece na folha como procuradora do Estado e recebe por esse
  cargo (há contestação no STF). No PI a folha tem R$ 800 por mês acima do subsídio. No MA há jeton de conselho.
