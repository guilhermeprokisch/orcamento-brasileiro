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
- **O que não dá por posto:** a divisão por profissional (médico, enfermeiro, dentista…). Ela só existe no
  *Relatório de Produção* do SISAB, que vai no máximo até a cidade.

## As fontes olhadas

| Fonte | O que dá | Menor recorte | Formato | Acesso |
|---|---|---|---|---|
| SISAB, Relatório de Validação | registros por ficha (atendimento individual, odontológico, procedimentos, visita domiciliar, vacinação, atividade coletiva…), aprovados, duplicados ou reprovados | **CNES** e equipe (INE), por mês | .xlsx, .csv | aberto (JSF: abre a página, manda o formulário) |
| SISAB, Relatório de Produção | as mesmas fichas, com filtros e cruzamentos (profissional, tipo de atendimento, local, CID, procedimento…) | cidade, por mês | tela, .xlsx | aberto; a linha "Município" só sai com estado ou cidade escolhidos, não para o Brasil de uma vez |
| SISAB, Indicadores de desempenho (Previne Brasil) | 7 indicadores por cidade | cidade, quadrimestre | tela | aberto; descontinuado em 2025 |
| Relatórios da APS, `/cobertura/aps` | população, equipes (eSF, eAP 30h e 20h, ribeirinhas, de rua, prisionais), capacidade e cobertura | cidade, por mês | JSON | aberto (`relatorioaps-prd.saude.gov.br`) |
| SIA/SUS (o que o site já usa) | procedimentos ambulatoriais aprovados, com valor | CNES, por mês | .dbc no FTP | aberto |

Não achamos microdados abertos do e-SUS APS no OpenDataSUS nem nos Dados Abertos do Ministério.

## Como o relatório de validação funciona

É uma página JSF. Um `GET` dá o cookie da sessão e o `javax.faces.ViewState`; um `POST` com o formulário
devolve a planilha. Os campos que usamos:

- `unidGeo=brasil`, `periodo=producao` (pela data em que o atendimento aconteceu, não a do envio);
- `j_idt70=AAAAMM` (um mês por pedido);
- `colunas=ibge`, `colunas=cnes`, `colunas=tp_unidade`;
- `j_idt77=1%` (só aprovados) e `j_idt87=<ficha>` (4 atendimento individual, 5 odontológico, 7 procedimentos,
  8 visita domiciliar);
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
  parte sobre a referência que já existe.
- Cada unidade ganha quatro números no fim da lista (atendimentos, dentista, procedimentos, visitas) e cada
  cidade ganha `cobertura`.
- `SaudeUnidades.astro`: uma frase com a soma do SISAB das unidades da prefeitura, uma com a cobertura, a
  frase do SIA com o nome do sistema e, em cada posto, a linha do SISAB acima da do SIA.

## O que fica para depois

- Atendimentos por profissional (médico x enfermeiro) por cidade, pelo Relatório de Produção, pedindo
  estado por estado.
- Vacinação e atividades coletivas (as fichas 14 e 6 do mesmo relatório de validação).
- A série de anos anteriores (o relatório vai até 2013), para mostrar se o trabalho dos postos cresceu.
