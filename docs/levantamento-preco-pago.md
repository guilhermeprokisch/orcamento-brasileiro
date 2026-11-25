# Preço pago comparado: o mesmo remédio, em cidades diferentes

Levantamento de 23/11/2026, para o item "Preço pago comparado" do bloco 3 ("Riscos e qualidade do
gasto") do [plano de melhorias](plano-de-melhorias.md). As perguntas são duas: quanto cada
prefeitura e cada governo estadual pagou pelo mesmo item, e quantas empresas disputaram cada compra.
O levantamento começa pelos remédios, porque eles têm código de catálogo, unidade clara (comprimido,
ampola, frasco) e muita gente comprando a mesma coisa.

## As fontes

Testado em 23/11/2026. As linhas marcadas **baixado** foram baixadas de verdade, sem cadastro; as
outras foram vistas na página ou na documentação.

| Fonte | Quem cobre | Item e unidade | Código IBGE da cidade? | Número de propostas ou de empresas? | Lote |
|---|---|---|---|---|---|
| **Pesquisa de preço do Compras.gov.br** ([API](https://dadosabertos.compras.gov.br/swagger-ui/index.html), módulo `modulo-pesquisa-preco`). É a base do Painel de Preços. **Baixado** | As compras feitas no sistema Compras.gov.br: governo federal, parte dos estados e as prefeituras que usam o sistema federal | Código CATMAT, unidade padronizada (`COMPR`, `CAPS`, `AMP`…), quantidade, preço unitário, marca e fornecedor (CNPJ) | **Sim** (`codigoMunicipio` é o código IBGE de 7 dígitos) | Não | Por código CATMAT, até 500 linhas por página, de 2 a 10 s por página |
| **Itens e resultados das contratações do PNCP** (`/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens` e `…/itens/{n}/resultados`). **Baixado** | Todas as compras publicadas no portal, de qualquer plataforma (BNC, BLL, Portal de Compras Públicas, Compras.gov.br…) e de qualquer esfera | Descrição livre ("DIPIRONA 500MG/ML"), unidade livre ("AMP", "CP", "COMP", "UN", "CX"), quantidade, preço estimado; no resultado, o preço homologado e o fornecedor. O campo de catálogo (`catalogoCodigoItem`) quase sempre vem vazio fora do Compras.gov.br | **Sim** (`unidadeOrgao.codigoIbge`, o mesmo que o site já usa nos contratos) | **Não**: o resultado traz só quem ganhou | Uma chamada por compra para os itens e **uma por item** para o resultado |
| Itens e resultados do PNCP no Compras.gov.br (`modulo-contratacoes/2_…` e `3_…`) | Só as compras da Lei 14.133 feitas no Compras.gov.br (a da Tacima-PB, feita na BNC, não aparece) | Como o PNCP, com o CATMAT | Não direto (vem a UASG) | Não | Em lote, por dia (6,5 mil resultados num dia de setembro) |
| OCDS do Compras.gov.br (`modulo-ocds/1_releases`) | O mesmo do anterior | Itens e valores | Não | **Não**: o campo de lances (`bids`) vem vazio | Por órgão e mês |
| Página pública "Acompanhar Contratação" do Compras.gov.br | Compras feitas no Compras.gov.br | — | — | **Sim**, mostra as propostas de cada item, mas cada consulta passa por um captcha. Não serve para coleta | — |
| **LicitaCon, do TCE-RS** ([dados abertos](https://dados.tce.rs.gov.br), `licitacon/licitacao/ano/2026.csv.zip`, 281 MB, atualizado todo dia). **Baixado** | Todos os órgãos do Rio Grande do Sul: 497 prefeituras, consórcios, estado | Descrição livre, unidade, preço estimado e homologado por item | Não (código do órgão no TCE; dá para ligar pelo nome) | **Sim**: `licitante.csv` (quem participou), `proposta.csv` e `item_prop.csv` (cada proposta, item por item) | Um zip por ano |
| **Banco de Preços em Saúde (BPS)**, bases anuais compiladas ([página](https://www.gov.br/saude/pt-br/acesso-a-informacao/banco-de-precos/bases-anuais-compiladas)). **Baixado** (2023-2024) | Compras de saúde que as instituições cadastraram no BPS | Código CATMAT ("Código BR"), unidade de fornecimento, genérico ou não, fabricante | Não: só o nome da cidade e a UF | Não | Uma planilha por ano, **a última é de 2024**; só 37,5 mil linhas em 2023 e 24,6 mil em 2024 |
| BPS, sistema e Painel de Preços da Saúde | O mesmo, com consulta mais recente | O mesmo | Não | Não | Consulta na tela, sem lote |

Nenhuma fonte de preço traz CPF. O pipeline guarda só o CNPJ (ou a raiz dele) de empresas, como já
faz nos contratos. Nos arquivos do TCE-RS, o documento de quem participou pode ser um CPF: o
pipeline só **conta** quantos documentos diferentes há, sem guardar nenhum deles.

### O que cada uma resolve

- **Preço por cidade, com o item certo**: a pesquisa de preço do Compras.gov.br é a única que já
  vem limpa (CATMAT, unidade padronizada e código IBGE). Mas só cobre quem compra pelo sistema
  federal.
- **Preço em mais cidades**: os itens do PNCP cobrem todas as plataformas. O custo é ler a
  descrição livre ("LOSARTANA POTÁSSICA 50MG COMPRIMIDO", "LOSARTAN 50MG", "LOSARTANA POT. 50 MG")
  e fazer uma chamada por item para saber o preço final.
- **Quantas empresas disputaram**: só o LicitaCon do RS publica isso em lote. Para o resto do
  país não há fonte aberta: o PNCP não guarda os perdedores, e o Compras.gov.br mostra as
  propostas atrás de um captcha.
- **O BPS** fica de fora como fonte principal: parou em 2024, é pequeno e não tem o código da
  cidade. Serve para conferir a ordem de grandeza.

## O que as amostras mostraram

### Sete remédios no Compras.gov.br, 2026

Sete remédios da farmácia básica, pelo código CATMAT, com as compras de 1º/01 a 22/11/2026 (pesquisa
de preço do Compras.gov.br). Preço por comprimido, cápsula ou ampola. A "faixa" vai do preço que
um quarto das compras pagou ou menos ao preço que três quartos pagaram ou menos.

| Remédio (CATMAT) | Compras | Compradores | Mediana | Faixa | Prefeituras (mediana) | Federal (mediana) |
|---|---|---|---|---|---|---|
| Losartana 50 mg, comprimido (268856) | 249 | 198 | R$ 0,050 | R$ 0,040 a 0,060 | R$ 0,043 | R$ 0,060 |
| Metformina 850 mg, comprimido (267691) | 188 | 144 | R$ 0,116 | R$ 0,095 a 0,140 | R$ 0,100 | R$ 0,135 |
| Dipirona 500 mg/ml injetável, ampola (268252) | 328 | 249 | R$ 0,56 | R$ 0,48 a 0,64 | R$ 0,51 | R$ 0,59 |
| Amoxicilina 500 mg, cápsula (271089) | 290 | 126 | R$ 0,21 | R$ 0,19 a 0,24 | R$ 0,19 | R$ 0,23 |
| Omeprazol 20 mg, cápsula (267712) | 293 | 160 | R$ 0,075 | R$ 0,070 a 0,082 | R$ 0,070 | R$ 0,080 |
| Sinvastatina 20 mg, comprimido (267747) | 199 | 161 | R$ 0,070 | R$ 0,060 a 0,090 | R$ 0,063 | R$ 0,080 |
| Paracetamol 500 mg, comprimido (267778) | 227 | 182 | R$ 0,070 | R$ 0,059 a 0,080 | R$ 0,060 | R$ 0,070 |

O que se vê:

- **A faixa é estreita.** Para remédio genérico comprado em pregão, metade das compras fica a
  menos de 20% da mediana. Por isso um preço 3, 5 ou 8 vezes maior chama atenção de verdade.
- **Quem compra mais paga menos, mas pouco.** Na losartana, a mediana cai de R$ 0,060 (até 16 mil
  comprimidos) para R$ 0,040 (acima de 380 mil). Na amoxicilina, de R$ 0,23 para R$ 0,195. A
  diferença de quantidade explica uns 30% a 50%, não 5 vezes.
- **O Norte paga um pouco mais**: R$ 0,060 na losartana, contra R$ 0,047 no Sul; R$ 0,68 na
  dipirona, contra R$ 0,54 no Nordeste. Frete e distância contam, mas de novo na casa dos 20% a 30%.
- **As prefeituras pagam menos que os órgãos federais** nos sete. Os órgãos federais compram
  pouco (um quartel, um hospital universitário), e as prefeituras compram para a cidade toda.
- **Os erros de unidade são poucos e grosseiros**: de 3 a 6 compras por remédio passam de 10
  vezes a mediana. Losartana a R$ 9,99 o comprimido é o preço da caixa. Mas nem todo preço 10
  vezes maior é erro: Acará (PA) pagou R$ 0,80 o comprimido de paracetamol (11 vezes a mediana)
  na mesma compra em que pagou 9,5 vezes a mediana na sinvastatina e 6,8 vezes na dipirona. O
  corte de erro de unidade tem de ficar mais alto (30 vezes), e o que fica entre 10 e 30 vezes vai
  com aviso.
- **O preço alto vem em bloco.** As cidades que pagaram caro num remédio pagaram caro em vários,
  na mesma compra e com a mesma empresa:

| Cidade | Compra | Empresa | Losartana | Metformina | Sinvastatina | Paracetamol |
|---|---|---|---|---|---|---|
| São Miguel do Guamá (PA) | pregão de registro de preço, 10/04/2026 | Polymedh Ltda | R$ 0,31 (7,8 vezes) | R$ 0,47 (5,2 vezes) | R$ 0,43 (7,2 vezes) | R$ 0,37 (6,2 vezes) |
| Dom Basílio (BA) | pregão de registro de preço, 06/03/2026 | Medisil Medicamentos Ltda | R$ 0,50 (8,3 vezes) | R$ 0,24 (1,7 vez) | R$ 0,36 (4,2 vezes) | — |
| Acará (PA) | pregões de registro de preço, março e julho de 2026 | A. F. A. Comércio / AFA Hospitalar | R$ 0,13 (2,5 vezes) | — | R$ 0,76 (9,5 vezes) | R$ 0,80 (11,4 vezes) |

("vezes" = quantas vezes a mediana das compras de quantidade parecida.) Só na losartana, São
Miguel do Guamá registrou 840 mil comprimidos a R$ 0,31: R$ 227 mil a mais que a mediana, **se**
comprar tudo. Num registro de preço a prefeitura fixa o preço e a quantidade máxima, e compra
conforme precisa.

O preço alto também não é destino: Dom Basílio pagou R$ 1,51 a cápsula de amoxicilina em março
(7,2 vezes a mediana) e R$ 0,23 em julho (1,1 vez), com outra empresa.

Do outro lado, Casimiro de Abreu (RJ), Marmeleiro (PR) e Formosa do Oeste (PR) pagaram de metade a
dois terços da mediana em vários itens.

**Cobertura:** só **148 cidades** compraram em 2026 algum dos sete pelo Compras.gov.br (108 delas
compraram três ou mais), além de órgãos de 17 estados. É pouco para pôr uma seção em todas as
páginas de cidade. As outras prefeituras compram por plataformas privadas e só aparecem no PNCP,
com descrição livre.

### Quantas empresas disputaram: Rio Grande do Sul, 2026

No LicitaCon de 2026 (até 23/11) há 2.394 licitações de remédio de órgãos gaúchos: 853 pregões
eletrônicos, 1.040 dispensas e o resto em outras modalidades.

- Nos pregões com participantes informados (706), a mediana é **2 empresas** por pregão. Isso é
  baixo demais para ser verdade em pregão de remédio, e o motivo aparece quando se olha órgão por
  órgão.
- Contando os pregões de qualquer coisa, dos 546 órgãos com 20 itens ou mais, **256 quase nunca
  mostram mais de uma empresa num item** (menos de 10% dos itens), e 137 mostram mais de uma em
  quase todos (90% ou mais). Quase não há meio-termo. O mais provável é que metade dos órgãos
  informe ao TCE só a proposta vencedora.
- Então "licitação com uma empresa só" **só vale para os órgãos que informam as propostas
  perdedoras**. Num órgão que informa só a vencedora, "uma empresa" não quer dizer nada.
- Nos **230 órgãos que informam as perdedoras** (mais de uma empresa em pelo menos metade dos
  itens), há 206 pregões de remédio em 2026, com 17.060 itens. Só **837 itens (4,9%)** tiveram uma
  empresa só, e 15 pregões tiveram uma empresa só em todos os itens. O maior é o de Alvorada:
  remédios injetáveis, registro de preço homologado em 27/03/2026, R$ 2,6 milhões, 54 itens, cada
  um com uma proposta só.
- O filtro "objeto com MEDICAMENTO" pega coisa que não é remédio (câmara de vacina, serviço
  veterinário, farmácia contratada); a lista final tem de sair dos itens, não do objeto.

A losartana 50 mg aparece em 88 itens com preço homologado no RS. Ela confirma a faixa do
Compras.gov.br: R$ 0,030 a 0,050 o comprimido, com Caxias do Sul a R$ 0,03 (7,2 milhões de
comprimidos) e o consórcio Granpal a R$ 0,039 (35 milhões). A unidade é escrita de seis jeitos
("COM", "UN", "CAP", "CX", "ENV", "SEMAN"), e o "CX", o "ENV" e o "SEMAN" ficam de fora.

### Os itens do PNCP, todas as plataformas

Três dias de setembro de 2026 (15 a 17/09): 4.973 pregões eletrônicos publicados, **263 de
remédio** (5%): 142 de prefeituras, 97 de órgãos estaduais. Nos 40 primeiros, 3.188 itens (80 por
compra), de dez plataformas diferentes (Compras.gov.br em 17, e Licitanet, Licitar Digital,
ECustomize, BNC, BLL, Elotech e outras no resto).

- **Nenhum item trouxe o código CATMAT**, nem os do Compras.gov.br. O PNCP não repassa o
  catálogo. O casamento tem de ser pela descrição.
- A descrição casa bem: com o princípio ativo, a dosagem e uma lista de exclusão (associações,
  xarope, gotas), os sete remédios apareceram em 45 itens de 8 compras, com erros que dá para
  corrigir ("AMOXICILINACLAVULONATO", sem espaço, e "ESCOPOLAMINA + DIPIRONA" passaram).
- A unidade vem escrita de mais de 30 jeitos ("UNIDADE", "COMPRIMIDO", "CP", "COMP", "CPR", "CMP",
  "UNID", "CAIXA", "FRASCO ML"…). "CAIXA" aparece em 196 dos 3.188 itens e fica de fora.
- Compra publicada ainda não tem preço final: os 45 itens tinham só o preço estimado (o
  resultado sai semanas depois). A coleta tem de voltar às compras de meses antes.
- E o resultado tem erro de unidade também: em Pains (MG), a losartana estimada a R$ 0,04 o
  comprimido saiu homologada a R$ 30,41, que é o preço da caixa.

**Custo.** Uns 88 pregões de remédio por dia útil, uns 22 mil por ano, de 80 itens em média. São
22 mil chamadas para os itens e uma chamada de resultado por item casado: com 40 remédios, algo
como 25 itens por compra, ou 550 mil chamadas por ano. No ritmo que o portal aceita (1 por
segundo por linha), são uns 2 dias com 4 linhas. Dá para fazer, guardando os brutos no bucket e
baixando só o que falta, como já se faz com os contratos.

### O sinal se repete de um ano para o outro?

Das cidades com três compras ou mais dos sete remédios no Compras.gov.br nos dois anos (52), a
razão típica "preço ÷ mediana das compras parecidas" de 2025 e a de 2026 andam juntas
(correlação de postos de **0,63**). Ou seja, quem paga mais tende a pagar mais de novo, e isso
não é ruído. Mas quase nenhuma cidade paga caro **em tudo**: a razão típica de 2026 vai de 0,78
(o décimo mais barato) a 1,31 (o décimo mais caro), e só uma cidade ficou acima de 1,5 vez nos
dois anos. O preço muito alto aparece em **compras** isoladas (São Miguel do Guamá em abril,
Dom Basílio em março), não como marca da cidade. Por isso a seção mostra compras e itens, e não
dá nota nem ranking de cidade.

## Como comparar de forma justa

As regras abaixo valem para qualquer fonte. Elas seguem o que o teste de 20/11/2026 mostrou
sobre "gastar mal" (comparar dentro do grupo parecido, preferir regra simples a resíduo
estatístico, não julgar onde o número é ruído).

1. **Mesmo item.** O item é o código CATMAT (losartana 50 mg é 268856; a de 100 mg e a associada
   com hidroclorotiazida são outros códigos). Na descrição livre do PNCP e do TCE-RS, o item só
   entra quando o texto tem o princípio ativo **e** a dosagem **e** a forma, sem outro princípio
   ativo junto ("LOSARTANA POTÁSSICA 50 MG + HIDROCLOROTIAZIDA" fica de fora). Começa com uma
   lista fechada de uns 40 remédios da farmácia básica, conferida à mão.
2. **Mesma unidade.** Preço por comprimido, cápsula ou ampola; frasco só com o mesmo volume. Fica
   de fora a unidade que não é a do item ("CX", "ENV", "BLISTER", "KIT", "SEMAN"), e a unidade
   vazia.
3. **Mesmo período.** Compras do mesmo ano, pela data da compra (no RS, a da homologação). Remédio muda pouco de preço em
   um ano, mas a comparação nunca mistura 2025 com 2026.
4. **Mediana e faixa, não média.** A referência de cada item é a mediana nacional do ano. A faixa
   vai do primeiro ao terceiro quarto das compras. Uma compra só aparece como "mais cara" se
   passar de **duas vezes** a mediana: dentro disso cabem a diferença de quantidade e de frete.
5. **Porte e quantidade à parte.** A mediana de referência é a das compras de **quantidade
   parecida** (as compras do item divididas em três grupos: pequenas, médias e grandes). Quem
   compra 5 mil comprimidos não é comparado com quem compra 5 milhões. A mediana da região vai ao
   lado, para mostrar quanto é frete.
6. **Unidade errada e valor absurdo.** Acima de 30 vezes ou abaixo de 1/30 da mediana: erro de
   unidade (preço da caixa no lugar do comprimido), fica de fora e é contado à parte. Entre 10 e
   30 vezes: entra, com o aviso "pode ser erro de digitação; confira na compra".
7. **Mínimo para mostrar.** Um item só tem mediana se houver pelo menos **20 compras de 10
   compradores diferentes** no ano. Uma cidade só aparece em "pagou mais caro" com pelo menos
   R$ 1.000 a mais no item (multiplicando a diferença pela quantidade), para não destacar
   centavos.
8. **Registro de preço é teto, não gasto.** Quase todas as compras de remédio são registro de
   preço: a prefeitura fixa preço e quantidade máxima e compra aos poucos. O "a mais" é calculado
   sobre a quantidade registrada e sempre diz "se comprar tudo".
9. **Disputa só onde ela é informada.** "Uma empresa só" vale apenas para os órgãos do RS que
   informam as propostas perdedoras (os que mostram mais de uma empresa em pelo menos metade dos
   itens dos seus pregões). Nos outros estados não há dado aberto, e o site diz isso.

## O que esta conta não diz

Um preço maior não prova desperdício nem desvio. Mudam o preço, sem culpa de ninguém:

- **frete e distância**: cidade longe de distribuidora paga mais pela entrega;
- **quantidade**: quem compra pouco paga mais por unidade;
- **prazo**: entrega parcelada, em prazo curto ou com estoque garantido custa mais;
- **compra emergencial**: falta de remédio, licitação deserta ou fracassada e compra às pressas,
  por dispensa;
- **marca e embalagem**: embalagem hospitalar, comprimido revestido ou marca exigida pelo
  protocolo;
- **registro de preço**: o preço registrado é o máximo; a prefeitura pode comprar menos, ou nada.

O que a conta mostra é onde vale olhar de perto: a compra, a pesquisa de preço que a prefeitura
fez antes, e se outras empresas tentaram vender.

## Proposta

**Fase 1 (este PR).** Usa as duas fontes que já vêm prontas para comparar:

- a **pesquisa de preço do Compras.gov.br**, com uma lista de uns 40 remédios da farmácia básica
  pelo CATMAT, de 2025 e 2026: dá a mediana nacional de cada remédio (com faixa, região e
  quantidade) e o preço de cada cidade e estado que compra pelo sistema federal;
- o **LicitaCon do RS**: preço e número de empresas por item, para os 497 municípios gaúchos, só
  nos órgãos que informam as propostas perdedoras.

Comando `uv run precos` no pipeline, que gera:

- `site/public/data/indicadores/precos.json`: por remédio, a mediana nacional, a faixa, as
  medianas por quantidade e por região e o número de compras. Por cidade (`mun`) e por estado
  (`uf`): os itens em que pagou mais de duas vezes a mediana (preço, mediana, quantidade, quanto
  a mais se comprar tudo, data, modalidade, empresa e o link da compra) e os itens em que pagou
  perto ou abaixo dela (só a contagem). Para o RS: os pregões de remédio com uma empresa só por
  item.
- `site/public/data/precos/{codigo}.json`, um por remédio, para a página nacional.

**Fase 2 (outro PR).** Os itens do PNCP, de todas as plataformas, casados pela descrição, para
chegar às cidades que não usam o Compras.gov.br. Precisa da coleta de 2 dias, do casamento de
texto conferido à mão e de um workflow como o dos contratos.

**No site:**

- Na página da cidade e na do estado, no grupo "Em que gasta", depois dos contratos, a seção
  **"O preço dos remédios"**, com: "Pagou mais caro que as outras cidades em quais remédios" e,
  no RS, "Licitações de remédio com uma empresa só". Só aparece quando a cidade tem compra nas
  fontes; quando não tem, uma frase diz por quê.
- A página nacional **/precos**, com a lista dos remédios, a mediana de cada um e, ao clicar,
  todas as compras do ano, da mais cara à mais barata, com filtro por estado.
- O texto "O que esta conta não diz", na seção e na página nacional.

## O que entrou na fase 1 (23/11/2026)

- `uv run precos` (pipeline/src/orcamento_pipeline/precos.py): 45 remédios, 2025 e 2026. Compras.gov.br para todo o
  país, menos as prefeituras do RS, que vêm do LicitaCon (casadas pela descrição; testes em
  pipeline/tests/test_precos.py). Na primeira carga: 45 remédios com mediana, 26,6 mil compras comparadas, 471 cidades e
  21 estados com compra, 517 compras de prefeitura acima do dobro das parecidas com pelo menos R$ 1.000 a mais.
- O casamento pela descrição bate com o Compras.gov.br: nas prefeituras do RS, a razão típica de cada remédio fica entre
  0,75 e 1,0 da mediana nacional (o RS compra um pouco mais barato).
- Entre 10 e 30 vezes a mediana, a compra aparece com o aviso "pode ser erro de unidade". O caso que levou a isso:
  Campinas registrou em 30/09/2025 losartana a R$ 0,86 o comprimido (1,05 milhão), enquanto o hospital municipal Mário
  Gatti, na mesma cidade, pagou R$ 0,032. Pelos dados não dá para saber se é o preço da caixa.
- O workflow precos.yml roda todo dia 5 e abre um pull request com as cópias de referência; a publicação diária só copia
  (`--sem-baixar`).
- Fica para a fase 2: os itens do PNCP (as outras ~5 mil cidades), e o número de empresas fora do RS.

## Fase 2: os pregões do PNCP (23/11/2026)

`uv run precos-pncp` (pipeline/src/orcamento_pipeline/precos_pncp.py) baixa, dia a dia, os pregões eletrônicos
publicados no PNCP; o `precos` junta os de remédio às outras fontes.

**Como a coleta foi desenhada, e por quê:**

- A busca textual do portal (`/api/search`) daria só os pregões de remédio, 100 por página, mas começou a recusar a
  conexão depois de umas dezenas de pedidos, e não dá para depender dela. A lista vem da API de consulta, que exige a
  modalidade e devolve 50 compras por página em ~10 s: uns 1.700 pregões eletrônicos por dia útil, ou 34 páginas.
- Com 12 downloads ao mesmo tempo e sem pausa, o portal respondeu 429 (muitos pedidos) por vários minutos. Com 4 e
  1 s de pausa, passa.
- Itens e resultados são rápidos (0,1 a 0,4 s), mas não há resultado em lote: uma chamada por item casado. Numa amostra
  de três dias de setembro (233 pregões de remédio), deu uns 5 itens casados por pregão.
- Tudo fica guardado em data/raw/precos/pncp/ (no Actions, no cache) e cada execução continua de onde parou. Compra
  publicada há menos de 120 dias com item sem resultado é consultada de novo depois de 14 dias.

**O que fica de fora:** as compras feitas no Compras.gov.br (já estão na pesquisa de preço), as das prefeituras do RS
(vêm do LicitaCon), as dispensas e os pregões presenciais, e os pregões ainda sem resultado.

**Erros que a amostra mostrou, e a regra para cada um:**

- Preço homologado da caixa com o estimado por comprimido (Pains-MG: losartana estimada a R$ 0,04, homologada a
  R$ 30,41; hidroclorotiazida, furosemida e amitriptilina no mesmo pregão). No pregão o preço final não pode passar do
  estimado; acima de 3 vezes o estimado, a compra fica de fora.
- Descrições que o casamento deixava passar: "AMOXICILINA CLAV." (com clavulanato), "OMEPRAZOL MAGNÉSIO… JUDICIAL
  MARCA LOSEC MUPS" (compra de marca por ordem judicial), "AAS TAMPONADO" (outro código). Entraram nos testes.
- O resto bate: na amostra, a razão típica do preço do PNCP sobre a mediana do Compras.gov.br foi 1,15 (as cidades que
  compram por plataformas privadas pagam um pouco mais), sem nenhum preço abaixo de 0,3 vez a mediana.

**Primeira carga (25/11/2026), com os pregões publicados de 24/06 a 22/11/2026.** O resto de 2026 está sendo baixado e
2025 fica para o workflow semanal:

- 8.521 compras do PNCP aceitas, de 464 cidades; 17 tiradas por passar de 3 vezes o estimado.
- A comparação passa de 471 para 920 cidades com compra, e de 517 para 1.234 compras de prefeitura acima do dobro.
- O casamento bate com o Compras.gov.br: a razão típica do preço do PNCP sobre a mediana do Compras.gov.br é 1,0, e
  nenhum remédio fica com razão típica fora de 0,6 a 1,8.
- Para ganhar tempo, só as prefeituras de fora do Compras.gov.br e do RS têm itens e preços baixados (`interessa`); a
  lista de cada dia fica inteira, para buscar os órgãos estaduais depois. Mesmo assim, são uns 5 minutos por dia de
  publicação, com 3 downloads ao mesmo tempo.
- O Norte aparece mais caro nas compras destacadas (São Paulo de Olivença, Novo Aripuanã, Jutaí, Coari, no Amazonas):
  é onde o frete pesa mais, e a mediana da região vai ao lado na página de cada remédio.
