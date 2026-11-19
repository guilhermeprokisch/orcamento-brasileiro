# Plano de melhorias

O objetivo do projeto: qualquer pessoa conseguir ver, para a sua cidade e o seu estado, quanto
dinheiro público entra, de onde vem, quanto sai e para onde vai, e ter elementos para julgar se
está sendo bem usado.

Este documento lista o que está em andamento e o que vem depois. A ordem dentro de cada bloco
é a ordem sugerida. "Fonte" indica de onde o dado viria; onde está escrito **a confirmar**, o
acesso ainda não foi testado.

Atualizado em 19/11/2026.

## Em andamento

| # | Melhoria | Situação |
|---|---|---|
| 1 | O ano em andamento (2026) no mapa | Feito para os estados. Municípios: download do relatório bimestral em curso |
| 2 | Dívida oficial e limites fiscais (RGF do SICONFI) | Não começou; usa a mesma API do item 1, que aceita uma consulta por segundo |
| 3 | Conciliar o dinheiro federal: Portal da Transparência x prefeituras | Feito ([conciliacao-federal.md](conciliacao-federal.md)) |
| 4 | Bolsa Família e BPC de outros anos | Depende de download manual (o Portal pede captcha); hoje só 2025 |
| 5 | Gasto do estado em cada cidade | Feito para a Paraíba e para Minas Gerais. Demais estados: ver o item H |

## Próximas, na ordem sugerida

### A. Gasto contra resultado

Colocar ao lado do gasto o que ele produziu. É o que transforma número em pergunta: "por que
gastamos mais e temos menos?".

- Educação: gasto por aluno ao lado da nota no Ideb. Fonte: INEP (Ideb e Censo Escolar, por
  município) — a confirmar.
- Saúde: gasto por habitante ao lado de mortalidade infantil e cobertura da atenção básica.
  Fonte: DATASUS — a confirmar.
- Feito quando: a página de cada cidade mostra os dois números juntos, com a mediana das
  cidades do mesmo porte.

### B. Hospitais e escolas

A promessa original do projeto: chegar na unidade.

- Quanto o SUS pagou a cada hospital. Fonte: DATASUS (SIH/SIA, pelo código CNES) — a confirmar.
- Dinheiro federal que vai direto a cada escola. Fonte: FNDE (PDDE) — a confirmar.
- Limite já conhecido: salários, merenda e contratos são pagos pela secretaria, não pela
  unidade. O que dá para mostrar é um pedaço do gasto, e a página precisa dizer isso.

### C. Resumo e imagem para compartilhar

- Três frases no topo de cada cidade, escritas a partir dos números ("A prefeitura depende
  83% de repasses; de cada R$ 100, R$ 36 vão para salários…").
- Uma imagem com os números da cidade, para WhatsApp e redes.
- Busca por CEP ou localização, em vez de digitar o nome.

### D. Emendas parlamentares

Quanto cada deputado e senador mandou para cada cidade, e para quê. Fonte: Portal da
Transparência e Transferegov — a confirmar (o Portal bloqueia downloads em série com captcha).

### E. Alertas automáticos

Marcar na página, com a regra escrita ao lado:

- gasto com pessoal acima do limite legal (depende do item 2, RGF);
- mínimo constitucional em saúde e em educação não aplicado. Fonte: RREO, anexos de saúde e
  educação — a confirmar;
- vários anos seguidos gastando mais do que recebe (já temos o dado);
- declaração com cara de erro: números repetidos de um ano para o outro, diferença de mais de
  30% entre receita e despesa. Hoje esses casos aparecem como se fossem fato.

### F. Comparar duas cidades lado a lado

Hoje a comparação é só com a mediana das cidades do mesmo porte. Escolher duas (ou a cidade e a
capital) e ver tudo em duas colunas.

### G. O que o governo federal gasta direto na cidade

O mapa mostra o que a União repassa, não o que ela mesma gasta ali (universidades federais,
hospitais federais, quartéis, agências). Fonte: Portal da Transparência, despesas por
localidade — a confirmar. Atenção: o gasto costuma ser registrado na sede do órgão, o mesmo
problema da folha de pagamento na Paraíba.

### H. Gasto do estado em cada cidade, para mais estados

Paraíba e Minas Gerais já estão no site. A pesquisa em
[gasto-estadual-por-municipio.md](gasto-estadual-por-municipio.md) mostrou que mais nove estados
publicam a folha de pagamento com cidade ou unidade e outros nove, obras ou convênios com
município. Ordem sugerida:

1. PR e SC: folha com cidade, sem cruzamento.
2. GO, AM e MT: obras com município (AM e MT usam a mesma API).
3. SE, ES, RJ, BA e SP: folha por unidade, casando escola e hospital com o Censo Escolar e o CNES.
4. Estimativa nacional de educação e saúde para os demais, validada na Paraíba e em Minas.

### H2. Página "quem publica onde gasta"

Os 27 estados em quatro faixas: gasto inteiro por município, folha com cidade, só obras e
convênios, quase nada. Os dados já estão no documento da pesquisa.

### H3. Pedidos pela Lei de Acesso à Informação

Para o que não existe em lugar nenhum: despesa por município de aplicação nos estados das
faixas de baixo, tabela de unidades com município (SP, RJ, BA, AM, GO), efetivo policial por
município (Ministério da Justiça) e remuneração por escola (FNDE). Os pedidos são redigidos no
projeto; o envio depende de cadastro pessoal.

### I. "Quanto eu pago?"

Calculadora: a pessoa informa salário e cidade e vê uma estimativa do que vai em imposto para
a prefeitura, o estado e a União. É estimativa e precisa ser apresentada assim: boa parte do
imposto está embutida nos preços.

### J. Quem recebe o dinheiro das prefeituras

Os maiores fornecedores de cada prefeitura. É o mais trabalhoso: depende dos portais
municipais, que são milhares e cada um num formato
([levantamento](levantamento-portais-municipais.md)). Começar pelos Tribunais de Contas que
publicam os dados de todos os municípios do estado num formato só.

## Base (não aparece para o usuário, mas sustenta o resto)

- Testar o layout de celular num aparelho de verdade; até agora, só em emulação.
- Tirar a dependência de arquivos baixados à mão: o histórico do SICONFI já está num release do
  GitHub; os benefícios federais ainda dependem de download manual.
- Atualização automática do relatório bimestral dos municípios: feita pelo workflow
  `bimestral.yml` (dias 1 e 31 e toda segunda-feira). Falta estender à comparação com o mesmo
  período do ano anterior e ao relatório de dívida (RGF).
- Testes automáticos do pipeline: hoje a conferência é feita à mão a cada mudança.

## Como decidir a ordem

Três perguntas, nesta ordem: responde algo que a pessoa quer saber sobre a própria cidade? O
dado existe para o país inteiro num formato só? Dá para dizer com clareza o que o número não
cobre? As melhorias A, B e C passam nas três. A J falha na segunda, por isso fica por último.
