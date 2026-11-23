# Plano de melhorias

O objetivo do projeto: qualquer pessoa conseguir ver, para a sua cidade e o seu estado, quanto
dinheiro público entra, de onde vem, quanto sai e para onde vai, e ter elementos para julgar se
está sendo bem usado.

Este documento lista o que está em andamento e o que vem depois. A ordem dentro de cada bloco
é a ordem sugerida. "Fonte" indica de onde o dado viria; onde está escrito **a confirmar**, o
acesso ainda não foi testado.

Atualizado em 21/11/2026.

## Em andamento

| # | Melhoria | Situação |
|---|---|---|
| 1 | O ano em andamento (2026) no mapa e nas páginas | Feito para estados e municípios (relatório bimestral, atualizado pelo `bimestral.yml`) |
| 2 | Dívida oficial e limites fiscais (RGF do SICONFI) | Feito: dívida dos estados (#22) e das prefeituras (#42), gasto com pessoal frente ao limite (#71) |
| 3 | Conciliar o dinheiro federal: Portal da Transparência x prefeituras | Feito ([conciliacao-federal.md](conciliacao-federal.md)) |
| 4 | Bolsa Família e BPC de outros anos | Depende de download manual (o Portal pede captcha); hoje só 2025 |
| 5 | Gasto do estado em cada cidade | Feito para a Paraíba e para Minas Gerais. Demais estados: ver o item H |
| 6 | ICMS medido por cidade (hoje estimado pela cota-parte × 4) | Nenhum estado pesquisado publica em formato aberto e atualizado. Pedidos de LAI enviados a SP e MG em 19/11/2026 ([pedidos-lai/icms-por-municipio.md](pedidos-lai/icms-por-municipio.md)); resposta até 09/12/2026 |

## Feito em novembro de 2026

| O quê | Onde | PR |
|---|---|---|
| Seletor de ano nas páginas de cidade e estado (a página inteira muda) | páginas | #18 |
| Imposto federal por cidade medido pela Receita Federal, não estimado | mapa | #19 |
| Imposto de renda pela cidade onde a pessoa mora (Grandes Números do IRPF) | mapa, cidades, estados | #27, #30 |
| Gasto em educação por aluno (matrículas do Censo Escolar) | cidades, estados | #20, #21 |
| Dívida dos estados frente ao limite da LRF, ano a ano | estados | #22 |
| Nota de capacidade de pagamento (CAPAG) | cidades, estados | #23 |
| Mortalidade infantil ao lado do gasto em saúde, com série de 2015 a 2025 | cidades, estados | #24, #29 |
| Homicídios ao lado do gasto em segurança, com taxa ano a ano e marca nos anos subcontados | estados, cidades acima de 100 mil hab. | #25, #31, #34, #35 |
| Água e esgoto na rede (Censo 2022) ao lado do gasto em saneamento | cidades, estados | #28 |
| "Com o quê gasta": a frase cita a maior fatia e explica serviços e materiais | cidades, estados | #26 |
| Lista "Nesta página" e seções em grupos (em que gasta, contas, o que chega e sai, como está) | cidades, estados | #32, #33 |
| Bloco "Como está a cidade" no mapa (mortalidade, homicídios, água, esgoto) | mapa | #36 |
| Emendas parlamentares que chegam a cada cidade e estado, e no mapa por morador | cidades, estados, mapa | #38, #41, #59 |
| Explorador de emendas (/emendas) | página nova | #53, #55, #56 |
| Contratos das prefeituras e dos estados (PNCP) e o explorador de contratos, com o governo federal | cidades, estados, /contratos | #43, #47, #52, #54, #57, #76, #77 |
| As escolas da prefeitura, uma a uma | cidades | #49 |
| Os postos e hospitais: internações (SIH) e procedimentos, exames e cirurgias sem internação (SIA) | cidades | #51, #70 |
| Para quem a prefeitura pagou (tribunais de contas da PB, do AC e de SC) | cidades | #66, #73, #75 |
| Gasto com pessoal frente ao limite da LRF | cidades, estados | #71 |
| Comparar duas cidades ou dois estados (/comparar) | página nova | #64, #72 |
| De onde vem o dinheiro da União (/receitas) | página nova | #65 |
| A dívida pública federal (/divida) | página nova | #63 |
| O que o governo federal gasta ele mesmo em cada cidade (universidades, quartéis, superintendências) | cidades | #80 |
| Cópia pública dos dados (Backblaze B2) e a página "Os dados" | /dados | #46, #48 |
| Menu em quatro grupos, balões nas palavras técnicas, trilha e botões para voltar nos exploradores | todo o site | #50, #60, #61, #68 |
| Publicação em quatro filas: de cerca de 15 para 7 a 8 minutos | GitHub | #69, #74 |
| O que o governo federal gasta ele mesmo em cada cidade | cidades | #80 |
| "Quem publica onde gasta": os 27 estados em mapas, por faixa | página nova | #79, #81, #84 |
| Folha estadual por cidade no Paraná e em Santa Catarina | cidades | #83 |
| O que cada posto de saúde lançou no SISAB e a cobertura da atenção básica | cidades | #82 |

## Os próximos blocos

Combinado em 21/11/2026. O site já responde quanto entra, de onde vem, para onde vai e quem
recebeu. O que falta é o que explica por que o gasto é assim e o que daria para mudar. Quatro
blocos, cada um respondendo a uma pergunta, nesta ordem: 1, 2, a previdência do 3, o resto do 3
e o 4.

### 1. As contas fecham?

- **Dívida bruta do governo geral**, a conta do Banco Central que soma União, estados,
  prefeituras e os títulos que o Banco Central usa para os juros (perto de 78% do PIB). Já
  aparece em /divida, numa frase; passa a ter gráfico e série, ao lado da dívida federal.
- **Resultado primário e nominal**: arrecadou menos do que gastou sem contar os juros (o que a
  regra fiscal persegue) e contando os juros (o que faz a dívida crescer). Série desde os anos
  2000. Fontes: Banco Central (necessidade de financiamento do setor público, no SGS) e
  Resultado do Tesouro Nacional.
- **Quanto está amarrado**: a parte do gasto obrigatória por lei (aposentadorias, salários, mínimos
  de saúde e educação, juros) e a parte que o governo escolhe. Na União, perto de 90% é
  obrigatório; o orçamento federal marca cada despesa. Em estados e prefeituras, montar com o que
  o site já tem (pessoal, previdência, mínimos).
- **Estados e prefeituras no azul ou no vermelho**, com receita e despesa que o site já tem.
- Talvez: o orçado contra o pago e os restos a pagar (o que fica para o ano seguinte).
- Onde: /divida vira uma página mais larga, ou uma página irmã.

### 2. O caminho dos impostos

- Um diagrama de fluxos: o imposto pago → quem arrecada (a União fica com uns dois terços) → o
  que é repassado por obrigação (FPE, FPM, cota do ICMS, Fundeb) → quem gasta. Primeiro o Brasil
  inteiro; depois por cidade ("saiu daqui R$ X em impostos federais, voltou R$ Y"; o mapa já tem
  metade disso).
- **Benefícios fiscais** como um galho do diagrama, "o que deixa de entrar": o que a Receita
  Federal deixa de arrecadar com isenções e regimes especiais (Demonstrativo dos Gastos
  Tributários, da ordem de R$ 500 bi por ano) e, nos estados, os incentivos de ICMS dos anexos das
  leis de diretrizes orçamentárias.
- Cuidado: não contar duas vezes o dinheiro que passa de um governo para outro.
- Em aberto: mais explicativo (a história contada rolando a página) ou mais exploratório (um
  gráfico em que se clica); Brasil primeiro ou cidade primeiro.

### 3. Riscos e qualidade do gasto

- **Previdência dos servidores**: o rombo do fundo de aposentadoria de cada cidade e estado e a
  nota da situação dele (Ministério da Previdência). Ao lado da dívida e do gasto com pessoal. É o
  mais fácil do bloco.
- **Preço pago comparado**: o mesmo item entre cidades, a começar pelos remédios (Banco de Preços
  em Saúde), e quantas empresas disputaram cada licitação. Usa os contratos que já temos. Cuidado
  com o que é só diferença de porte ou ruído.
- **Obras paradas**: **feito**. As obras com dinheiro federal paradas, com cidade e valor, pela lista do
  TCU: página `/obras-paradas` e seção nas cidades e nos estados. Ver `docs/levantamento-obras-paradas.md`.

### 4. Quanto eu pago e como volta

O simulador do item I: o caminho dos impostos aplicado ao salário da pessoa, e o que é amarrado.
Por último, porque usa os blocos 1 e 2.

### Depois dos blocos

Estatais e crédito subsidiado (BNDES, Plano Safra); salários de servidores acima do teto.

## Os outros itens, na ordem sugerida

### A. Gasto contra resultado

Colocar ao lado do gasto o que ele produziu. É o que transforma número em pergunta: "por que
gastamos mais e temos menos?".

- Educação: **feito**. Ideb por município e rede, gasto por aluno com as matrículas do Censo
  Escolar, e a rede estadual nas páginas de estado. Falta o gasto por aluno mudar com o ano
  escolhido na página (hoje só o ano mais recente).
- Saúde: **feito** com a mortalidade infantil (DATASUS, SINASC e SIM, 2015 a 2025). Falta a
  cobertura da atenção básica.
- Saneamento: **feito** com água e esgoto na rede (IBGE, Censo 2022). Falta o esgoto tratado,
  que o Censo não mede. Fonte possível: SINISA — a confirmar.
- Segurança: **feito** com os homicídios (DATASUS, SIM) nos estados e nas cidades com mais de
  100 mil habitantes, em taxa ano a ano com a população do IBGE.
- Contas: **feito** com a nota CAPAG, nas cidades e nos estados.
- Critério para entrar: existir para todas as cidades, medir resultado para a população, ser
  dado oficial e aberto, e corresponder a um gasto que o site já mostra. Rankings de consultorias
  e índices que só cobrem cidades grandes ficam de fora.
- Feito quando: a página de cada cidade mostra os dois números juntos, com a mediana das
  cidades do mesmo porte.

### B. Hospitais e escolas

A promessa original do projeto: chegar na unidade.

- Hospitais e postos: **feito** (#51, #70, #82), com o que o SUS pagou pela tabela a cada unidade e,
  nos postos de saúde, o que lançaram no SISAB (atendimentos, dentista, visitas às casas).
- Escolas: **feito** (#49), uma a uma, com o dinheiro direto do FNDE.
- Limite já conhecido: salários, merenda e contratos são pagos pela secretaria, não pela
  unidade. O que dá para mostrar é um pedaço do gasto, e a página precisa dizer isso.

### D. Emendas parlamentares

**Feito** (#38, #41, #53): quanto cada deputado e senador mandou para cada cidade, e para quê.

### F. Comparar duas cidades lado a lado

**Feito** (#64, #72): /comparar, duas cidades ou dois estados lado a lado.

### G. O que o governo federal gasta direto na cidade

**Feito** (#80): o que a União gasta ela mesma em cada cidade (universidades e institutos
federais, hospitais universitários, quartéis, superintendências), na página de cada cidade, para
2025: execução da despesa do Portal da Transparência pela cidade da unidade que paga
([levantamento-gasto-federal-direto.md](levantamento-gasto-federal-direto.md)). Metade do valor
fica registrada em Brasília, onde estão as sedes; só 38% cai numa cidade que não é sede. Falta a
folha por cidade de exercício (servidores × endereço da unidade no SIORG) e o Judiciário.

### H. Gasto do estado em cada cidade, para mais estados

Paraíba, Minas Gerais, Paraná e Santa Catarina (#83) já estão no site. A pesquisa em
[gasto-estadual-por-municipio.md](gasto-estadual-por-municipio.md) mostrou que mais nove estados
publicam a folha de pagamento com cidade ou unidade e outros nove, obras ou convênios com
município. Ordem sugerida:

1. PR e SC: **feito** (#83), folha com cidade.
2. GO, AM e MT: obras com município (AM e MT usam a mesma API). RN e TO também têm painéis de
   obras, com o município em parte delas.
3. SE, ES, RJ, BA e SP: folha por unidade, casando escola e hospital com o Censo Escolar e o CNES.
4. Estimativa nacional de educação e saúde para os demais, validada na Paraíba e em Minas.

### H2. Página "quem publica onde gasta"

**Feito** (#79, #81, #84): /quem-publica, com os 27 estados em mapas, pela faixa do governo do
estado e pelo que o Tribunal de Contas publica.

### H3. Pedidos pela Lei de Acesso à Informação

Para o que não existe em lugar nenhum: despesa por município de aplicação nos estados das
faixas de baixo, tabela de unidades com município (SP, RJ, BA, AM, GO), efetivo policial por
município (Ministério da Justiça) e remuneração por escola (FNDE). Os pedidos são redigidos no
projeto; o envio depende de cadastro pessoal. Os primeiros enviados: ICMS por município a SP e MG
([pedidos-lai/](pedidos-lai/)).

### I. "Quanto eu pago?"

Calculadora: a pessoa informa salário e cidade e vê uma estimativa do que vai em imposto para
a prefeitura, o estado e a União. É estimativa e precisa ser apresentada assim: boa parte do
imposto está embutida nos preços. Combinado em 20/11/2026: fica no plano, sem data para começar.
Em 21/11/2026 virou o bloco 4 de "Os próximos blocos": vem depois do caminho dos impostos.

O que dá para mostrar com o que o site já tem:

- Imposto de renda e INSS descontados do salário: calculados pelas tabelas oficiais do ano.
  É a parte exata.
- Impostos nas compras (ICMS, PIS/Cofins, IPI, ISS): estimados pela parte da renda que costuma
  ir para consumo, por faixa de renda (POF do IBGE), e pelo peso desses impostos nos preços. É a
  parte que precisa ser apresentada como estimativa, com a conta à vista.
- Para quem vai cada parte (União, estado, prefeitura) e o que cada um faz com esse dinheiro,
  usando as áreas de gasto e o "Com o quê gasta" da cidade e do estado da pessoa.
- O que volta: repasses, benefícios do INSS e serviços, por morador, para a pessoa comparar.

Como é uma página nova e lida com a renda da pessoa, começa por um rascunho visual. A renda
digitada fica só no navegador: não é enviada nem guardada.

### J. Quem recebe o dinheiro das prefeituras

Os maiores fornecedores de cada prefeitura. É o mais trabalhoso: depende dos portais
municipais, que são milhares e cada um num formato
([levantamento](levantamento-portais-municipais.md)). Começar pelos Tribunais de Contas que
publicam os dados de todos os municípios do estado num formato só.
O levantamento estado por estado está em [levantamento-pagamentos-tce.md](levantamento-pagamentos-tce.md);
feitos: Paraíba (#66), Acre e Santa Catarina (#73, #75). Em andamento (21/11/2026, uma sessão
cada): Pernambuco, Ceará e Espírito Santo, Amazonas e Tocantins, São Paulo (o TCE-SP e, para a
capital, o TCM-SP). Depois: MG, PR e RS, que também publicam. Goiás (TCM-GO) depende de uma
chave pedida com cadastro pessoal.

### K. De onde vem o dinheiro do governo federal

**Feito** (#65, /receitas). O plano original:

- Quanto entrou em cada ano e de onde: imposto de renda, contribuições à Previdência, Cofins,
  IPI, IOF, royalties do petróleo, dividendos das estatais e o dinheiro emprestado (venda de
  títulos da dívida).
- Um mapa de blocos igual ao do Explorer, por tipo de receita, com a série desde 2014 e o
  previsto contra o arrecadado.
- Deixar claro o peso do refinanciamento: boa parte da "receita" é dívida nova que paga dívida
  velha, o mesmo bloco que aparece como gasto do Ministério da Fazenda no Explorer.

Fontes: Portal da Transparência (receitas previstas e realizadas por ano, em CSV), Tesouro
Nacional (Resultado do Tesouro Nacional) e Receita Federal (arrecadação mensal por tributo).

### L. A dívida pública federal

**Feito** (#63, /divida). O plano original:

- Quanto é, em reais e em relação ao PIB, e como cresceu.
- Quem empresta: bancos, fundos de investimento, fundos de previdência, seguradoras,
  estrangeiros e o próprio governo.
- De que tipo: com juros fixos, atrelada à Selic, à inflação ou ao dólar.
- Quando vence: quanto vence nos próximos 12 meses e o prazo médio.
- Quanto custa: os juros pagos por ano, comparados com o gasto em saúde e em educação.

Fontes: Tesouro Nacional (Relatório Mensal da Dívida e os dados abertos no Tesouro
Transparente, com a tabela de detentores) e Banco Central (dívida bruta do governo geral e
juros nominais).

## Para depois

### C. Resumo e imagem para compartilhar

Um dia, para testar; não é prioridade.


- A lista "Nesta página" já ajuda a navegar (#32, #33); o resumo ainda não existe.
- Três frases no topo de cada cidade, escritas a partir dos números ("A prefeitura depende
  83% de repasses; de cada R$ 100, R$ 36 vão para salários…").
- Uma imagem com os números da cidade, para WhatsApp e redes.
- Busca por CEP ou localização, em vez de digitar o nome.

### E. Alertas automáticos

Útil, mas depois: antes é preciso definir com cuidado o que conta como anormal (a métrica, e
como separar erro de declaração de gasto ruim) e deixar os dados de todas as fontes
consolidados e estáveis.


Marcar na página, com a regra escrita ao lado:

- gasto com pessoal acima do limite legal (depende do item 2, RGF Anexo 1);
- mínimo constitucional em saúde e em educação não aplicado. Fonte: RREO, anexos de saúde e
  educação — a confirmar;
- vários anos seguidos gastando mais do que recebe (já temos o dado);
- declaração com cara de erro: números repetidos de um ano para o outro, diferença de mais de
  30% entre receita e despesa. Hoje esses casos aparecem como se fossem fato.
- Já existem dois avisos parecidos: a cor da dívida perto e acima do limite, e a marca † nos
  anos de homicídio com mais mortes violentas sem causa definida do que homicídios.

## Base (não aparece para o usuário, mas sustenta o resto)

- Testar o layout de celular num aparelho de verdade; até agora, só em emulação.
- Tirar a dependência de arquivos baixados à mão: o histórico do SICONFI já está num release do
  GitHub; os benefícios federais ainda dependem de download manual.
- Atualização automática do relatório bimestral dos municípios: feita pelo workflow
  `bimestral.yml` (dias 1 e 31 e toda segunda-feira). Falta estender à comparação com o mesmo
  período do ano anterior e ao relatório de dívida (RGF).
- Testes automáticos do pipeline: hoje a conferência é feita à mão a cada mudança.
- Valores digitados errado nos contratos: o corte de "metade do orçamento" não pega tudo nos
  estaduais (ex.: R$ 5,9 bi do Governo do Pará para reformar uma escola) nem nos federais abaixo
  de R$ 5 bi (ex.: R$ 468 mi de carro-pipa a uma pessoa física em Sergipe).

## Como decidir a ordem

Três perguntas, nesta ordem: responde algo que a pessoa quer saber sobre a própria cidade? O
dado existe para o país inteiro num formato só? Dá para dizer com clareza o que o número não
cobre? As melhorias A, B e C passam nas três. A J falha na segunda, por isso fica por último.
