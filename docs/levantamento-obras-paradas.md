# Obras paradas: o que dá para mostrar, e de onde

Levantamento de 23/11/2026, para o item "Obras paradas" do bloco 3 ("Riscos e qualidade do gasto")
do [plano de melhorias](plano-de-melhorias.md). A pergunta: quais obras feitas com dinheiro federal
estão paradas ou foram abandonadas, em que cidade, quanto custariam, quanto já foi pago e desde
quando estão paradas.

## Resumo

- **Não existe uma lista única.** Cada órgão marca a situação da obra no seu sistema, com o seu
  critério. O TCU junta nove dessas bases num painel; o governo federal junta outras no Obrasgov.br.
  As duas listas se cruzam pouco.
- **O painel do TCU é a lista mais completa**: 4.215 obras paralisadas em abril de 2026, que
  custariam R$ 16,2 bilhões e já receberam R$ 8,0 bilhões. Tem cidade, valor previsto, valor já
  liberado, causa da parada e quanto da obra foi feito. Não tem a data da parada. É um Power BI
  sem arquivo para baixar; a tabela obra a obra só sai exportando à mão, duas vezes por ano.
- **O Obrasgov.br é a única fonte que dá para automatizar**: API aberta, sem cadastro, atualizada
  todo dia, com código IBGE da cidade e data de cada mudança de situação. Mas marca só 832 obras
  como "Paralisada" e 1.029 como "Inacabada", e as 556 obras de escolas e creches do FNDE que estão
  lá vêm com valor de R$ 0,01.
- **O FNDE (escolas, creches, quadras) é o maior grupo de obras paradas** (1.803 das 4.215 do TCU).
  O painel do FNDE pede captcha para pesquisar e para baixar.
- **O Transferegov não diz se a obra parou.** Ele tem os convênios, com cidade e valores, mas a
  situação da obra fica na Caixa (que o TCU já traz) ou no Obrasgov.br.
- Entre abril de 2025 e abril de 2026, o número do TCU caiu de 11.469 para 4.215. A maior parte
  da queda é mudança de critério, não obra retomada (ver "A mudança de critério de 2025").

## As fontes

Testado em 23/11/2026. "Baixado" quer dizer que os dados foram lidos de verdade, sem cadastro;
o resto foi visto na página ou na documentação.

| Fonte | O que cobre | Anos | Código IBGE? | Valor | Situação | Data da parada? | Automatizável? |
|---|---|---|---|---|---|---|---|
| **Obrasgov.br**, API nova ([documentação](https://api-publica.obrasgov.gestao.gov.br/obras/docs)). **Baixado** | Projetos de investimento com dinheiro federal que os órgãos cadastram ou que vêm de outros sistemas (SIMEC-FNDE, Transferegov, SISMOB, SUPRA, OPUS) | Cadastro desde 2021; obras contratadas desde 2008 | Sim, em `/geometria` | Previsto (`investimentos_previstos`); empenhado, liquidado e pago em `/empenho`; contrato em `/contrato` | Cadastrada, Em execução, Paralisada, Inacabada, Concluída, Cancelada | Sim, `/historico-situacao-cancelada-paralisada` | Sim, JSON aberto, atualizado todo dia |
| **Painel de Obras Paralisadas do TCU** ([painel](https://paineis.tcu.gov.br/obrasparalisadas)). Visto na tela | Nove bases: Caixa (transferências voluntárias), Codevasf, DNIT, Funasa, SESu e Setec (universidades e institutos), SIMEC (FNDE), SIMEC-Outros, SISMOB (saúde) | Fotografias semestrais desde ago/2022; a última é abr/2026, publicada em 30/07/2026 | Não: nome da cidade e UF ("Carnaubal/CE"). Obras do DNIT só têm a UF | Previsto e "desbloqueado" (o federal já liberado) | Em execução, Paralisada, Concluída, Cancelada; mais a causa da parada | Não | Não: Power BI sem arquivo. A tabela diz ser "exportável" |
| **SIMEC, Painel de Obras do FNDE** ([painel](https://simec.mec.gov.br/painelObras/)). Visto na tela | Escolas, creches do Proinfância e quadras pagas pelo FNDE | Desde 2007 | Pelo nome do município | Previsto e repassado, obra a obra | Planejamento, licitação, contratação, execução, paralisada, inacabada, concluída, cancelada, em reformulação | Só o estado atual (a Transparência Brasil já apontou isso) | Não: pesquisa e download pedem captcha |
| **Transferegov.br**, API de discricionárias ([documentação](https://api-publica.transferegov.gestao.gov.br/discricionarias/docs)). Visto na documentação; amostra lida em outro levantamento | Propostas, convênios e contratos de repasse | Desde 2008 | Sim (`cod_munic_ibge`, do proponente) | Global, repasse e contrapartida | Só a situação da proposta e do convênio, não da obra | Não | Sim, mas não responde à pergunta |

### Obrasgov.br

A API nova fica em `https://api-publica.obrasgov.gestao.gov.br/obras`. A antiga
(`api.obrasgov.gestao.gov.br/obrasgov/api`) ainda respondia em 23/11/2026, embora a página oficial
diga que seria mantida só até 31/08/2026. A nova é a que serve: filtra por situação, pagina de 200
em 200 e diz o total de itens.

Contagem por situação em 23/11/2026 (todas as naturezas, não só obra):

| Situação | Projetos |
|---|---|
| Cadastrada | 84.176 |
| Em execução | 21.141 |
| Concluída | 44.761 |
| Cancelada | 3.930 |
| **Paralisada** | **832** |
| **Inacabada** | **1.029** |

De onde vêm as paralisadas e inacabadas (`sistema_resp`):

| Sistema | Paralisada | Inacabada |
|---|---|---|
| SIMEC-FNDE (escolas, creches, quadras) | 556 | 0 |
| CIPI (cadastro direto no Obrasgov) | 132 | 165 |
| Transferegov.br | 68 | 737 |
| SUPRA | 10 | 126 |
| SIMEC-MCID, SISMOB, OPUS | 66 | 1 |

O que encontrei nos dados:

- **As obras do FNDE vêm sem valor.** 541 das 832 paralisadas têm valor previsto de até R$ 1
  (o FNDE manda R$ 0,01). E vêm com tipo errado: uma quadra escolar em Carnaubal (CE) aparece como
  "Dragagem, Derrocamento e Associações". O nome e a cidade estão certos.
- **Os registros do SUPRA não são obras.** São ações do orçamento (por exemplo
  "26.782.2087.10IX.0031", uma ação do DNIT em MG) com valores de bilhões. Somados, levariam as
  inacabadas a R$ 39 bilhões. Precisam sair da conta.
- **"Inacabada" no Transferegov não quer dizer abandonada há anos.** Muitas foram cadastradas em
  2022 e 2023 e tinham término previsto para 2025 ou 2026. Parece ser o convênio encerrado sem a
  obra pronta, mas a documentação não define. Vale perguntar ao MGI antes de chamar de "abandonada".
- **A data da parada existe**, em `/historico-situacao-cancelada-paralisada`. No caso da quadra de
  Carnaubal, o registro é de 03/05/2026, mas a obra estava prevista para terminar em 2020: a data é
  a de quando o sistema registrou a situação, não necessariamente a de quando a obra parou.
- O motivo da parada vem em `/execucao-fisica` ("Revisão de projeto básico", "Falta de recursos de
  contrapartida"), junto com o percentual executado.

Baixei os detalhes das 1.861 paralisadas e inacabadas (cinco chamadas por obra). Tirando as 146 do
SUPRA, que não são obras:

| | Paralisada (822) | Inacabada (903) |
|---|---|---|
| Com uma cidade (código IBGE) | 811 | 883 |
| Com mais de uma cidade | 10 | 17 |
| Com empenho cadastrado | 142 | 771 |
| **Com algum valor pago** | **44** (R$ 166 milhões) | **22** (R$ 52 milhões) |
| Com contrato cadastrado | 37 | 15 |
| Com histórico de situação | 782 | 0 |
| Com percentual executado e motivo | 820 | 903 |

- **Quase toda obra tem um código IBGE** (99% têm uma cidade só), mas ele nem sempre é o certo:
  ver a comparação de João Pessoa abaixo.
- **Quanto já foi pago, não dá para saber pelo Obrasgov.br**: só as obras cadastradas direto
  (CIPI e OPUS) trazem pagamento. FNDE e Transferegov não trazem.
- **A data do histórico não é a data da parada.** Nas paralisadas, o registro mais antigo é de 2026
  em 354 obras e de 2025 em 174, embora muitas estivessem previstas para terminar anos antes.
  É a data em que o sistema registrou a situação.
- Há valores errados que distorcem a soma: um pavilhão de manutenção de viaturas do Exército em
  Cáceres (MT) aparece com R$ 1,6 bilhão previsto.
- Por estado, a ordem não bate com a do TCU: o Obrasgov.br tem 106 paralisadas no MA (TCU: 442),
  88 em MG (321), 83 no PA (406), 57 na BA (391).

### Painel do TCU

O painel é um relatório Power BI embutido em `paineis.tcu.gov.br/pub`. Abre sem login. Tem uma
página "Tabela de dados" com uma linha por obra e estas colunas: data-base, base de dados,
empreendimento, número do instrumento, situação, local (cidade/UF), execução física, execução
financeira, valor do investimento, valor desbloqueado, setor, repassador, causa da paralisação,
se é obra do PAC e se entrou no Pacto de retomada.

Números da data-base abr/2026:

- 22.414 obras ativas, 4.215 paralisadas (18,8%);
- R$ 150,9 bilhões previstos em todas as ativas, R$ 16,2 bilhões nas paralisadas;
- R$ 70,6 bilhões de recurso federal já aplicado em todas, **R$ 8,0 bilhões nas paralisadas**;
- por repassador: FNDE 1.803, Ministério da Saúde 693, Funasa 540, Cidades 404, MEC 299, MIDR 157;
- por estado: MA 442, PA 406, BA 391, MG 321, RS 257, CE 235, PB 214, PI 212, RN 200;
- por cidade: Natal 47, João Pessoa 45, Belém 32, Porto Alegre 25, Rio Branco 22.

O que falta:

- **Não há arquivo para baixar.** A home diz que a tabela é "filtrável e exportável", o que no
  Power BI quer dizer "Exportar dados" no menu da tabela, à mão. Não consegui abrir esse menu pela
  automação do navegador. O painel entrega a qualquer visitante um token do Power BI
  (`/getembedinfo?painel=obrasparalisadas`), e com ele daria para ler a tabela direto do servidor
  da Microsoft, como o site já faz com os painéis Qlik dos tribunais. Tentei, e o controle de
  permissões desta sessão bloqueou a chamada; não sei se funcionaria.
- O filtro "Data base" vai de ago/2022 a abr/2026. Não conferi se as datas antigas trazem as mesmas
  colunas.
- **Não tem código IBGE.** O local vem como "Carnaubal/CE". Dá para casar pelo nome, com a mesma
  normalização que o site já usa. Obras do DNIT vêm só com a UF.
- **Não tem data da parada** nem data prevista de término.
- Sai duas vezes por ano (abril e outubro, publicadas uns três meses depois).

### FNDE (SIMEC)

O painel do FNDE passa pela verificação da Cloudflare no navegador sem pedir nada. Mas a pesquisa
por estado e o botão de baixar (`/painelObras/download.php`) pedem um reCAPTCHA. Não testei o
download. O FNDE cadastra a situação de cada obra; a Transparência Brasil já mostrou que o arquivo
tem só a situação atual, sem histórico, e que há obras sem endereço ou sem número de convênio.

O TCU já traz as obras do FNDE (base "SIMEC", 3.640 ativas, 1.803 paralisadas), com o número da
obra no SIMEC no nome, por exemplo "(1004938) PAC 2 - Construção de Quadra Escolar Coberta
003/2013 - Carnaubal - CE".

### Transferegov.br

A API de discricionárias tem propostas e convênios com o código IBGE do proponente e os valores
(global, repasse, contrapartida), mas nenhum campo diz se a obra está parada. A situação da obra
dos contratos de repasse fica com a Caixa, que o TCU já traz (base "CAIXA", 9.588 obras ativas), e
uma parte chega ao Obrasgov.br como "Transferegov.br". O antigo repositório de arquivos do SICONV
(`repositorio.dados.gov.br/seges/detru`) não responde mais; os arquivos agora ficam em
`api-publica.transferegov.gestao.gov.br/downloads/dadosgov/` (ver a seção seguinte).

## As fontes primárias que o TCU usa

O TCU recebe nove bases dos órgãos. Testei cada uma para ver se dá para ir direto nela.
"Paralisadas" é o que a própria fonte mostra, comparado com o que o TCU atribui a ela em abr/2026.

| Base | Fonte pública | Acesso | Paralisadas na fonte | No TCU | Cidade | Veredito |
|---|---|---|---|---|---|---|
| SIMEC (FNDE) | [Painel de Obras](https://simec.mec.gov.br/painelObras/) | reCAPTCHA na pesquisa e no download | — | 1.803 (repassador FNDE) | Nome | Não automatizável |
| SESu e Setec (MEC) | Nenhuma: todo o simec.mec.gov.br e o dadosabertos.mec.gov.br dão desafio da Cloudflare; o TCU recebeu essas bases por requisição | — | — | parte das 299 do MEC | — | Não automatizável |
| Caixa (BD Gestores) | Nenhuma: a página da Caixa sobre obras paralisadas é só texto | — | — | maior parte das 404 de Cidades e de parte da Saúde | — | Não automatizável |
| Funasa | Nenhuma: só PDFs do plano de dados abertos; o antigo Sismoc não responde | — | — | 540 | — | Não automatizável |
| SISMOB (Saúde) | [SISMOB Cidadão](https://sismobcidadao.saude.gov.br), API JSON da própria página. **Baixado** | Aberto, atualizado todo dia | **84** de 45.946 obras | 693 (repassador Saúde, que inclui obras da Caixa) | Nome e UF | Automatizável, mas mostra poucas paradas |
| DNIT (SIAC) | [Dados abertos do DNIT](https://servicos.dnit.gov.br/dadosabertos), CSV "acompanhamento de contratos". **Baixado** | Aberto, mas o arquivo é de 12/02/2025 | **79** de 11.357 contratos, só 6 de construção | 73 | Não (só a superintendência no número) | Automatizável, desatualizado |
| Codevasf (SIGEC) | [CSV de contratos](https://www.gov.br/codevasf/pt-br/acesso-a-informacao/licitacoes-e-contratos/contratos/contratos-codevasf.csv/@@download/file). **Baixado** | Aberto, atualizado em 02/11/2026 | **66** obras de engenharia (R$ 423 mi; R$ 187 mi já faturados) | — (a Codevasf entra em MIDR, 157) | Só no texto do objeto | Automatizável, sem cidade |

E duas fontes que não são de obra, mas ajudam a completar:

- **Transferegov, arquivos diários** (`api-publica.transferegov.gestao.gov.br/downloads/dadosgov/`).
  **Baixado.** `siconv_convenio` tem os 289 mil convênios e contratos de repasse com o mesmo número
  que o TCU mostra para a Caixa e a Funasa (6 dígitos), e os valores global, empenhado e
  desembolsado; `siconv_proposta` tem o código IBGE. A situação física da obra só existe para
  31.685 obras, das quais 94 paralisadas: a da Caixa não está aí (o contrato 780189, primeiro da
  lista do TCU, não aparece).
- **DNIT no Obrasgov.br**: no SUPRA, o nome do registro é o número do contrato do DNIT, o mesmo
  do TCU. As 139 "Inacabadas" do DNIT no Obrasgov.br são quase todas contratos "RESCINDIDOS" no
  SIAC (102). Isso explica o "Inacabada": contrato rescindido antes de a obra acabar.

**Conclusão**: para os grupos maiores (FNDE, Caixa, Funasa, universidades), a situação
"paralisada" só é pública pelo painel do TCU, que recebe as bases internas. As fontes primárias
abertas (SISMOB, DNIT, Codevasf) somam pouco mais de 200 paradas e cada uma tem um problema
(poucas paradas, arquivo velho, sem cidade). Construir extratores para elas não troca o TCU.
O que vale a pena é usar o Transferegov para completar as linhas do TCU da Caixa e da Funasa
pelo número do convênio: código IBGE certo e valor desembolsado atualizado todo dia.

## As fontes batem?

Comparei a cidade de Carnaubal (CE) nas duas listas.

| | TCU (abr/2026) | Obrasgov.br (23/11/2026) |
|---|---|---|
| Obras paralisadas | 4, todas do FNDE (uma creche e três quadras) | 1, a quadra abaixo |
| Quadra coberta 003/2013 | Paralisada, 83% feita, R$ 621.773,70 previstos, R$ 397.305,34 liberados, causa "Falha na execução de serviços" | Paralisada, 87,54% feita, valor R$ 0,01, motivo "Revisão de projeto básico", situação registrada em 03/05/2026 |

Depois comparei João Pessoa obra a obra: as 45 paralisadas do TCU (lidas na tabela do painel)
contra as 967 obras e projetos que o Obrasgov.br liga ao código IBGE da cidade (2507507).

| Base no TCU | Paralisadas no TCU | No Obrasgov.br |
|---|---|---|
| SIMEC (FNDE, creches) | 15 | 12 como Paralisada; 2 como **Concluída** (Escola do Alto do Mateus, 98% feita no TCU; Mumbaba, 97%); 1 só como proposta "Cadastrada" (creche Mucumagro) |
| Funasa (esgoto e água) | 13 | Nenhuma reconhecível |
| SESu (UFPB) | 10 | 1, como "Em execução" (prédio do LAVID); as outras 9 não estão lá |
| Caixa | 6 | 2 como Paralisada (esgoto do Valentina, ETA de Gramame); 2 como "Cadastrada" (Rio Jaguaribe, Porto do Capim); 2 não estão |
| Setec (IFPB) | 1 | Como "Cadastrada" |

- **Tudo o que o Obrasgov.br marca como paralisado em João Pessoa também está no TCU.** O
  contrário não vale: o TCU tem 31 obras paradas a mais.
- **O Obrasgov.br repete obras.** Cada creche do FNDE aparece duas vezes: uma vinda do SIMEC
  (Paralisada, R$ 0,01) e outra vinda do Transferegov (Cadastrada, com o valor certo:
  R$ 8.522.296 para a creche Gramame 1, o mesmo do TCU). Quem soma sem cuidado conta a obra duas
  vezes.
- **O código IBGE do Obrasgov.br nem sempre é da cidade da obra.** Das 18 paralisadas que ele liga
  a João Pessoa, 4 são de outras cidades da Paraíba (Picuí, Tavares, Pombal, Bonito de Santa Fé),
  provavelmente porque o ponto no mapa ficou na capital.

No total:

- **FNDE**: 1.803 paralisadas no TCU, 556 no Obrasgov.br.
- **Todas as bases**: 4.215 paralisadas no TCU; 832 paralisadas e 1.029 inacabadas no Obrasgov.br,
  das quais 136 são do SUPRA e não são obras.
- **Percentual feito e motivo** mudam entre as duas, porque cada uma pega o dado num dia diferente
  e com um cadastro diferente.

## A mudança de critério de 2025

O TCU contava 11.469 obras paralisadas em abril de 2025 e 4.215 em abril de 2026. Em dezembro de
2025 uma portaria tirou o critério que considerava parada a obra sem boletim de medição havia 90
dias; pela imprensa, a maioria das obras saiu da lista por reclassificação, não porque foi
retomada. O próprio TCU avisa que a comparação entre datas tem ressalvas. O site não deve mostrar
"caiu 63%" sem explicar isso.

## O que esta conta não diz

Para a seção do site:

- **Não é a lista de todas as obras paradas do país.** Só obras com dinheiro federal, e só as que
  estão nos sistemas que o TCU ou o Obrasgov.br juntam. Obra paga só pela prefeitura ou pelo estado
  não aparece.
- **A situação pode estar velha.** Quem atualiza é a prefeitura ou o órgão; muitos não atualizam.
  Uma obra marcada como "em execução" pode estar parada há anos, e uma "paralisada" pode ter
  voltado.
- **O valor não é o custo final.** É o valor previsto no convênio ou contrato. A obra pode ter
  outras fontes de dinheiro (contrapartida da prefeitura, outro convênio, emenda) que não entram.
- **"Liberado" não é "desperdiçado".** Parte do dinheiro virou obra que ainda pode ser terminada;
  parte pode ser devolvida.
- Os números de anos diferentes não se comparam direto, porque o critério mudou.

## O que foi feito

Combinado com o Guilherme em 23/11/2026: o TCU como fonte; as fontes primárias e o Obrasgov.br ficam de fora
da primeira versão.

- **Carga**: as cinco datas-base (ago/2022, abr/2023, abr/2024, abr/2025, abr/2026) foram exportadas do
  painel em 23/11/2026, com a Situação em "Todos", e salvas em `data/raw/tcu-obras/`. O comando
  `uv run obras-paradas` lê as tabelas e grava `site/public/data/obras-paradas/obras-paradas.json` e a cópia
  em `pipeline/referencia/`. A publicação roda `obras-paradas --sem-baixar`.
- **Como exportar** (uma vez por ano, quando o TCU publicar a data-base nova): na "Tabela de dados" do
  painel, escolher a data-base, clicar na linha de total da tabela, apertar Esc, abrir o menu "…" no canto
  da tabela, "Exportar dados", "Dados com layout atual", xlsx. Cada obra tem um ID que se mantém entre as
  datas-base (por exemplo `CAIXA-1002189`), e é ele que dá o "desde quando".
- **Cidade**: casada pelo nome com o cadastro do SICONFI. Só 6 obras não casaram de primeira (nomes
  antigos, como Januário Cicco, hoje Boa Saúde); estão em `APELIDOS`. 164 obras têm só a UF.
- **Achado**: o TCU chama de "Paralisada" obras que o órgão informa de outro jeito ("Situação origem" na
  tabela): 532 em licitação, 506 canceladas, 446 em cancelamento, 105 inacabadas. O site mostra as duas.
- **Achado**: das 11.469 paradas de abr/2025, em abr/2026 3.357 tinham sido canceladas, 3.049 continuavam
  paradas, 2.040 voltaram a andar, 1.930 ficaram prontas e 1.093 saíram da lista.

**Nomes no site**: "parada" (com balão "Obra paralisada"), "custaria" (valor previsto), "liberado" (com
balão; o TCU chama de valor desbloqueado), "% feita" (com balão "Execução física"), "Por quê" (a causa) e
"No órgão" (a situação que o órgão informa, quando difere). "Inacabada" e "abandonada" não aparecem como
situação nossa.

**Páginas**: seção "Obras federais paradas" na página de cada cidade e de cada estado (grupo "O que chega e o
que sai daqui") e a página `/obras-paradas`, no menu "Contratos e emendas".

**Transferegov** (feito na segunda etapa, no mesmo PR): o número que o TCU mostra para a Caixa, a Funasa e
parte do FNDE é procurado em `siconv_convenio`; o convênio só vale se o estado de quem o assinou
(`siconv_proposta`) for o da obra. Resultado em 23/11/2026:

- 2.042 obras paradas têm número de convênio; 1.165 acharam um convênio com o mesmo número, e 91 foram
  descartadas porque o convênio era de outro estado (o número existe em outro sistema). Ficaram **1.074 obras
  ligadas**. As outras são contratos de antes de 2008 (anteriores ao SICONV, como os de João Pessoa) ou
  termos de compromisso que não estão no Transferegov.
- Nelas, a União já depositou **R$ 2,0 bilhões**, e **R$ 826,8 milhões** estão parados na conta das obras
  (o saldo inclui a contrapartida e os rendimentos). O "desembolsado" do Transferegov não é o "desbloqueado"
  do TCU: um é o que entrou na conta da obra, o outro o que saiu dela para pagar a obra.
- A cidade do Transferegov bate com a do TCU em 94% dos casos; só uma obra sem cidade no TCU ganhou a cidade.
- Cada obra ligada mostra o número do convênio, o ano da assinatura, o fim do prazo, quanto a União depositou
  e o saldo em conta. A publicação roda `obras-paradas --atualizar`, que baixa o `siconv_convenio` do dia
  (~18 MB) e troca só esses valores; o `siconv_proposta` (~200 MB) só é lido na carga à mão.
