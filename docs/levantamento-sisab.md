# Levantamento: o trabalho dos postos de saúde (SISAB) e a cobertura da atenção básica

Novembro de 2026. Pergunta: que fonte pública e oficial dá o que cada posto de saúde (UBS) fez no ano, por
estabelecimento (CNES), para todas as cidades? E a cobertura da atenção básica de cada cidade?

## Resposta curta

- **Existe produção por posto, aberta.** O *Relatório de Validação* do SISAB
  (<https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/envio/RelValidacao.xhtml>, apesar do
  "acessoRestrito" no endereço é público) devolve, para o Brasil inteiro, quantos registros cada CNES mandou
  por mês e por tipo de ficha do e-SUS APS, e quantos foram aprovados. Sem login, sem captcha, em .xlsx.
- **A cobertura também.** A API do painel *Relatórios da APS* (<https://relatorioaps.saude.gov.br>, que
  substituiu os relatórios públicos do e-Gestor) devolve, numa chamada, a cobertura da atenção primária de
  todas as 5.569 cidades num mês, com as equipes e a população. JSON aberto, sem chave.
- **Quem atendeu, só por cidade:** a divisão por profissional (médico, enfermeiro, outros) só existe no
  *Relatório de Produção* do SISAB, que vai no máximo até a cidade e só dá as cidades estado por estado.
  O site pede os 27 estados e mostra, na página da cidade, a parte dos atendimentos com médico e com
  enfermeiro.

## As fontes olhadas

| Fonte | O que dá | Menor recorte | Formato | Acesso |
|---|---|---|---|---|
| SISAB, Relatório de Validação | registros por ficha (atendimento individual, odontológico, procedimentos, visita domiciliar, vacinação, atividade coletiva…), aprovados, duplicados ou reprovados | **CNES** e equipe (INE), por mês | .xlsx, .csv | aberto (JSF: abre a página, manda o formulário) |
| SISAB, Relatório de Produção | as mesmas fichas, com filtros e cruzamentos (profissional, tipo de atendimento, local, CID, procedimento…) | cidade, por mês | tela, .xlsx | aberto; a linha "Município" só sai com estado ou cidade escolhidos, não para o Brasil de uma vez |
| SISAB, Indicadores de desempenho (Previne Brasil) | 7 indicadores por cidade | cidade, quadrimestre | tela | aberto; descontinuado em 2025 |
| Relatórios da APS, `/cobertura/aps` | população, equipes (eSF, eAP 30h e 20h, ribeirinhas, de rua, prisionais), capacidade e cobertura | cidade, por mês | JSON | aberto (`relatorioaps-prd.saude.gov.br`) |
| SI-PNI, doses aplicadas (Rede Nacional de Dados em Saúde) | cada dose de vacina, com o estabelecimento, a vacina, a dose e a estratégia | **CNES**, por dia | .csv em .zip mensal (~1,6 GB) | aberto (OpenDataSUS) |
| SIA/SUS (o que o site já usa) | procedimentos ambulatoriais aprovados, com valor | CNES, por mês | .dbc no FTP | aberto |

Não achamos microdados abertos do e-SUS APS no OpenDataSUS nem nos Dados Abertos do Ministério.

## Como o relatório de validação funciona

É uma página JSF. Um `GET` dá o cookie da sessão e o `javax.faces.ViewState`; um `POST` com o formulário
devolve a planilha. Os campos que usamos:

- `unidGeo=brasil`, `periodo=producao` (pela data em que o atendimento aconteceu, não a do envio);
- `j_idt70=AAAAMM` (um mês por pedido);
- `colunas=ibge`, `colunas=cnes`, `colunas=tp_unidade`;
- `j_idt77=1%` (só aprovados) e `j_idt87=<ficha>` (4 atendimento individual, 5 odontológico, 7 procedimentos,
  8 visita domiciliar, 6 atividade coletiva);
- `j_idt99=j_idt99` (o botão que baixa o .xlsx).

Cada pedido leva de 5 a 30 segundos e devolve 1 a 2 MB, com 35 a 45 mil estabelecimentos. O ano inteiro, com
as quatro fichas, são 48 pedidos. Os nomes `j_idtNN` são gerados pelo JSF e podem mudar se o Ministério
mexer na página; o programa confere o cabeçalho da planilha e para se ele vier diferente.

O relatório respondeu deste Mac (IP do Brasil). Não testamos de fora do país; a publicação no GitHub Actions
não depende disso, porque usa a cópia em `pipeline/referencia/unidades-saude.json`.

## O que cada número conta

- **Atendimento individual**: uma pessoa atendida por um profissional de nível superior (médico, enfermeiro,
  psicólogo, nutricionista, fisioterapeuta…). É o mais perto de "consulta".
- **Atendimento odontológico**: uma pessoa atendida pelo dentista.
- **Procedimento**: cada coisa feita (medir a pressão, curativo, injeção, teste rápido, retirada de pontos).
  Um atendimento pode ter vários.
- **Visita domiciliar**: a ida de um agente comunitário (quase sempre) ou de outro profissional a uma casa.

Usamos só os registros aprovados: em dezembro de 2025, dos 32,3 milhões de atendimentos individuais
enviados, 27,3 milhões foram aprovados e 4,7 milhões eram duplicados; o resto foi reprovado por profissional,
equipe ou CNES fora do cadastro.

Esses números não têm valor em reais. O SUS paga a atenção básica pelo número de pessoas cadastradas e de
equipes, não por consulta; por isso o SIA (que tem valor pela tabela) quase não tem os postos.

## Conferência

Dezembro de 2025, Brasil, registros aprovados:

| Ficha | Validação (soma dos CNES) | Relatório de Produção | Validação / Produção |
|---|---:|---:|---:|
| Atendimento individual | 27.290.431 | 29.377.427 | 93% |
| Atendimento odontológico | 3.668.006 | 4.043.548 | 91% |
| Procedimentos | 49.344.722 | 51.150.855 | 96% |
| Visita domiciliar | 53.855.700 | 59.948.985 | 90% |

O ano de 2025 inteiro:

| Ficha | Validação (soma dos CNES) | Relatório de Produção | Validação / Produção |
|---|---:|---:|---:|
| Atendimento individual | 380.337.293 | 414.551.864 | 92% |
| Atendimento odontológico | 51.030.345 | 56.875.660 | 90% |
| Procedimentos | 680.104.068 | 703.292.001 | 97% |
| Visita domiciliar | 699.021.321 | 784.895.827 | 89% |

A validação fica de 3% a 11% abaixo. A diferença parece vir do recorte: a validação conta pela data do
atendimento só o que foi aprovado, e o Relatório de Produção conta pela competência em que o registro entrou.
Para o site, a validação é o número mais conservador e o único que existe por posto. Das unidades da
prefeitura saem 375 dos 380 milhões de atendimentos individuais (99%): a atenção básica é quase toda municipal.
Dos 50.014 postos e unidades básicas da prefeitura no CNES, 45.099 têm produção no SISAB em 2025; os outros
4.915 estão sem nenhum registro aprovado. Podem ser postos de apoio sem equipe própria, ou que lançam a
produção no CNES de outra unidade; não conferimos um a um.

## Quem atendeu (médico, enfermeiro, outros)

O Relatório de Produção
(<https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/RelSauProducao.xhtml>) cruza a
ficha de atendimento individual com a categoria do profissional. A linha "Município" só sai com um recorte
geográfico menor que o Brasil, então pedimos um estado por vez:

1. `GET` na página (cookie e `javax.faces.ViewState`);
2. o pedido AJAX que a página faz quando se escolhe "Estado" (`unidGeo=estado`, `javax.faces.partial.ajax=true`,
   `javax.faces.partial.render=regioes script`); sem ele o campo `estados` não é aceito;
3. o `POST` com `estados=UF`, os 12 meses em `j_idt76`, `selectLinha=MUN.CO_MUNICIPIO_IBGE`,
   `selectcoluna=CO_CATEGORIA_PROFISSIONAL`, `tpProducao=4` (atendimento individual), todas as 26 categorias em
   `categoriaProfissional` (é obrigatório escolher pelo menos uma) e `j_idt192=j_idt192`, que devolve um .csv.

Cada estado leva de 5 a 30 segundos; os 27 juntos, cerca de 2 minutos. O programa confere no cabeçalho do
.csv o estado, o tipo de produção e os meses antes de usar.

2025, Brasil: **259 milhões de atendimentos com médico (62%), 124 milhões com enfermeiro (30%) e 32 milhões
com outros profissionais (8%)**: psicólogo, nutricionista, fisioterapeuta, assistente social. A soma (414,5
milhões) bate com o total do Relatório de Produção na tabela acima. Na metade das cidades a parte do médico
fica entre 52% e 70%; a mediana é 61%. Nas pontas há cidades com 11% (o enfermeiro faz quase tudo) e com 99%.

Esse relatório conta todas as unidades da cidade, também as do estado, e pela competência do registro; por
isso a página mostra só as proporções, não os números, ao lado da soma das unidades da prefeitura tirada do
relatório de validação. Nas cidades que conferimos as duas somas diferem em até 6% (São Paulo 1%, Cacoal 3%, Conceição do Araguaia 6%).

## Atividades coletivas

Por posto, a ficha 6 do relatório de validação dá quantas atividades coletivas cada CNES registrou (8,6
milhões nas unidades da prefeitura em 2025). Ela não separa o tipo, e as reuniões da própria equipe entram
na conta; por isso a linha de cada posto diz "atividades em grupo" e o aviso explica que inclui as reuniões.

Por cidade, o relatório de atividade coletiva
(<https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/RelSauAtivColetiva.xhtml>)
separa os sete tipos e dá o número de participantes. Funciona como o de produção: estado por estado, com o
mesmo pedido AJAX, os 12 meses em `j_idt72`, todos os tipos em `tipoAtividade`, `selectLinha=MUN.CO_MUNICIPIO_IBGE`,
`selectcoluna=tpat`, `j_idt83=qtac` (quantidade de atividades) ou `ndp` (participantes) e `j_idt134=j_idt134`
(.csv). São dois pedidos por estado.

2025, Brasil:

| Tipo | Atividades | Participações |
|---|---:|---:|
| Atendimento em grupo | 4.112.551 | 48.035.354 |
| Avaliação ou procedimento coletivo (escovação supervisionada, medir peso e altura nas escolas…) | 1.854.678 | 37.775.973 |
| Educação em saúde | 1.638.283 | 43.917.646 |
| Mobilização social | 122.903 | 4.114.423 |
| **Com os moradores** | **7.728.415** | **133.843.396** |
| Reunião de equipe, com outras equipes ou intersetorial | 993.561 | 9.916.140 |

A página da cidade mostra as atividades com os moradores, as participações (uma pessoa que vai a cinco
encontros conta cinco vezes) e, à parte, as reuniões da equipe. Como o relatório de produção, esse conta
todas as unidades da cidade.

## Vacinação: pelo SI-PNI, não pelo SISAB

A ficha de vacinação (14) existe no relatório de validação do SISAB, mas não serve para dizer o que cada
posto fez:

- O SISAB não valida a vacinação (ela vai para a Rede Nacional de Dados em Saúde). Não há nenhum registro
  "Aprovado"; os de dezembro de 2025 vêm como "Não Aplicado" (2,7 milhões), "Duplicado" (621 mil) e
  "Pendente" (178 mil). No ano, 65 milhões de registros "Não Aplicado".
- Muitas cidades e estados lançam as vacinas direto no sistema nacional, sem passar pelo e-SUS APS. Em
  dezembro de 2025, São Paulo, Fortaleza, Belo Horizonte e Vitória tinham zero registros nas unidades da
  prefeitura; o Espírito Santo inteiro, 354. Por mil moradores no mês, o estado vai de 0,1 (ES), 3,4 (RJ) e
  5,9 (SP) a 39 (AM) e 42 (TO), e 1.176 das 5.566 cidades ficam abaixo de 5.

A fonte certa é o **SI-PNI**: o conjunto "Doses aplicadas pelo Programa Nacional de Imunizações (PNI) – 2025"
do Portal de Dados Abertos do SUS (<https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2025>),
com os microdados da Rede Nacional de Dados em Saúde, que recebe as vacinas de todos os sistemas (e-SUS APS,
VaciVida, SIGA, Vacina e Confia ES, prontuários próprios das cidades). Um .zip por mês
(`https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv/vacinacao_<mes>_2025_csv.zip`, de 1,5 a 1,8 GB),
com um .csv de 56 colunas e **uma linha por dose aplicada**: o estabelecimento (`co_cnes_estabelecimento`), a
cidade dele (`co_municipio_estabelecimento`), a vacina, a dose, a estratégia (rotina, campanha, serviço
privado…), a situação do registro e a data em que foi apagado, se foi. O dicionário está em
<https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/dbbni/Dicionario_tb_ria_rotina.pdf>.

Os 12 arquivos somam ~20 GB e não cabem no disco junto com o resto, então o programa não os grava: lê cada
.zip enquanto baixa, descompacta o deflate na hora (o cabeçalho local do zip diz onde os dados começam) e
guarda só o total por estabelecimento e por cidade em `data/raw/datasus/pni/AAAAMM.json`. Quatro meses ao
mesmo tempo levam ~20 minutos. Ficam de fora os registros apagados e os que não estão na situação "final";
nenhuma linha veio fora do formato.

2025: **178 milhões de doses** em 50.316 estabelecimentos; o mês mais cheio é maio (33 milhões, a campanha
da gripe). As unidades da prefeitura aplicaram 160 milhões (90%); 38.772 dos 50.014 postos têm alguma dose
(nem todo posto tem sala de vacina). Por cidade, sem as doses do serviço privado (vacinas pagas em clínicas),
são 172 milhões, ou 0,81 dose por morador; na metade das cidades fica entre 0,72 e 0,93. São Paulo, que
tinha zero no SISAB, tem 10,5 milhões (0,86 por morador); Fortaleza 2,4 milhões; Belo Horizonte 2,2 milhões.
As pontas são cidades que atendem gente de fora: Pacaraima (RR, fronteira com a Venezuela) passa de 13 doses
por morador.

Na página: a frase da cidade (doses na cidade, quantas nas unidades da prefeitura, doses por morador e a do
Brasil) e "N doses de vacina" na linha de cada posto.

## Comparação com o SIA

O SIA mede outra coisa: procedimentos que o SUS paga pela tabela, sobretudo de UPAs, policlínicas, CAPS e
centros de especialidades. Os postos aparecem lá só quando fazem algo pago por procedimento (as AMA de São
Paulo, que juntam pronto atendimento e UBS, são o caso mais comum). Por isso a página mostra os dois, cada um
com o seu nome: "atendimentos" e "visitas" do SISAB; "procedimentos", "exames" e o valor pela tabela do SIA.
Um mesmo posto pode ter as duas linhas, e elas não se somam.

## Cobertura

A cobertura "potencial" da nota técnica nº 2/2025 (SAPS/MS) é a capacidade das equipes dividida pela
população do IBGE. Pelas contas que conferimos nos dados: 3.500 pessoas por equipe de saúde da família (eSF),
2.625 por equipe de atenção primária de 30 horas e 1.750 pela de 20 horas, mais as pessoas cadastradas nas
equipes ribeirinhas, de consultório na rua e prisionais. Em muitas cidades pequenas a conta passa de 100%; a
página mostra "todos os moradores". Dezembro de 2025: 83,2% no Brasil (176,9 milhões de 212,6 milhões de pessoas, contando no máximo a população de cada cidade); São Paulo 59,5%, Fortaleza 75,7%, Belo Horizonte 91,9%, Sorocaba 33,1%; 4.782 cidades chegam a 100%.

## No site

- `pipeline/src/orcamento_pipeline/unidades_saude.py`: `sisab()` baixa as 48 planilhas, guarda só o total
  por CNES em `data/raw/datasus/sisab/AAAAMM-ficha.json` e soma o ano; `cobertura()` guarda a resposta da API
  em `data/raw/datasus/sisab/cobertura-AAAA12.json`. `uv run unidades-saude --so-atencao-basica` refaz só essa
  parte sobre a referência que já existe. `profissionais()` pede o Relatório de Produção estado por estado e
  guarda cada um em `data/raw/datasus/sisab/profissionais-AAAA-UF.json`; `coletivas_estado()` faz o mesmo com o
  relatório de atividade coletiva (`coletivas-AAAA-UF.json`).
- Cada unidade ganha cinco números no fim da lista (atendimentos, dentista, procedimentos, visitas,
  atividades coletivas) e cada cidade ganha `cobertura`, `profissionais` (atendimentos com médico, com
  enfermeiro, com outros) e `coletivas` (atividades com os moradores, participações, reuniões da equipe).
- `pni()` lê os 12 meses do SI-PNI; cada unidade ganha as doses do ano como último número e cada cidade, `vacinas`.
- `SaudeUnidades.astro`: uma frase com a soma do SISAB das unidades da prefeitura, uma com a parte dos
  atendimentos com médico e com enfermeiro (e a do Brasil), uma com as atividades em grupo, uma com as doses
  de vacina, uma com a cobertura, a
  frase do SIA com o nome do sistema e, em cada posto, a linha do SISAB acima da do SIA.

## O que fica para depois

- A série de anos anteriores (o relatório vai até 2013), para mostrar se o trabalho dos postos cresceu.
- As doses por vacina e por idade (o SI-PNI tem as duas), para comparar com o calendário e a cobertura vacinal.
