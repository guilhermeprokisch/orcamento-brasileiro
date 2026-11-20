# O que o governo federal gasta ele mesmo em cada cidade

Levantamento do item G do [plano de melhorias](plano-de-melhorias.md). O site já mostra o que a
União **repassa** à prefeitura e ao estado (camada "Dinheiro federal" do mapa, comando
`uv run federal`, conciliada em [conciliacao-federal.md](conciliacao-federal.md)) e os benefícios
pagos aos moradores (INSS, BPC, Bolsa Família). Falta o que ela **gasta direto**: universidades e
institutos federais, hospitais universitários, quartéis, superintendências da Polícia Federal, do
INSS, do IBGE, obras do DNIT.

Testado em 20/11/2026, com os dados de 2025.

## Resumo

- A única fonte aberta que cobre todo o gasto direto, em todas as cidades, é a **execução da
  despesa do Portal da Transparência**, cruzada com a **tabela de unidades do Compras.gov.br**, que
  dá a cidade de cada unidade que paga. É a que o site usa (`uv run gasto-federal 2025`).
- Em 2025, o gasto direto do Poder Executivo federal (pessoal da ativa, custeio e investimentos,
  sem benefícios a pessoas, aposentadorias de servidores, repasses e dívida) foi de
  **R$ 339,0 bilhões**.
- **Só 38% (R$ 127,6 bi) cai numa cidade que não é sede.** Metade (R$ 170,2 bi, 50%) está
  registrada em Brasília; R$ 19,1 bi (6%) são folhas de pagamento centrais sem cidade no cadastro
  (também em Brasília); R$ 17,2 bi (5%) são as folhas da Marinha e da Aeronáutica, pagas no Rio de
  Janeiro para militares do país todo; R$ 5,1 bi (1%) são unidades no exterior.
- 591 das 5.570 cidades têm alguma unidade federal que paga despesas. Nas demais, o que a União
  gasta (uma agência do INSS, um posto da Polícia Rodoviária, um campus) fica registrado na cidade
  da unidade que paga, em geral a capital ou Brasília.

## Fontes avaliadas

| Fonte | Aberta? | Tem a cidade? | Cobertura | Situação |
|---|---|---|---|---|
| Portal da Transparência, execução da despesa (mensal) | Sim, zip por mês, sem cadastro | Não direto: tem a unidade gestora (UG) e o "localizador" do orçamento | Todo o Executivo federal (SIAFI), 2014 a out/2026 | **Usada**, com a cidade da UG vinda do Compras.gov.br |
| Compras.gov.br, unidades (UASG) | Sim, API sem cadastro | Sim: município (código IBGE) de cada unidade | 45.963 unidades; casou 2.864 das 3.020 UGs que pagaram algo em 2025 (94% do valor) | **Usada** como tabela de apoio |
| Localizador do orçamento (no mesmo arquivo do Portal) | Sim | Só quando a ação é localizada "no município de…" | Município em R$ 4,1 bi (1%); só a UF em mais R$ 102,5 bi (30%); o resto é "nacional" | Não serve para cidade |
| Portal, despesas diárias (empenho, liquidação, pagamento) | Sim, zip por dia | Não: tem a UG e o favorecido | Igual à execução, documento a documento | Mesmo problema; a cidade do favorecido é onde fica o fornecedor, não onde o gasto acontece |
| Portal, API de dados (`recursos-recebidos`, `despesas/…`) | Pede chave, com cadastro pessoal no gov.br | Município do favorecido | — | Não usada: exige cadastro e mede onde o fornecedor está |
| Portal, servidores (SIAPE e militares, mensal) | Sim, ~80 MB por mês | Não: só a UF de exercício e a unidade (UORG) | Servidores civis do Executivo; militares em arquivo à parte | Não usada: sem cidade, e com nome e CPF parcial de cada servidor. Daria para chegar à cidade cruzando a UORG com o endereço do SIORG, unidade a unidade (trabalho grande, ver "Próximos passos") |
| Painel Estatístico de Pessoal (MGI) | Sim, painel | Por UF; não achamos recorte por município | Servidores civis | Não serve para cidade |
| Tesouro Gerencial (SIAFI) | Não: só servidores públicos cadastrados | Tem a UG e o município da UG | Todo o SIAFI | Fechado |
| Siga Brasil (Senado) | Sim, painel | Tem UG e localizador | Orçamento federal | Painel interativo, sem download automático; mesma base do SIAFI, mesmo problema da sede |

O arquivo de execução do Portal traz **só o Poder Executivo**: a Justiça Federal, a do Trabalho, a
Eleitoral, o Ministério Público da União, a Câmara e o Senado não aparecem nele. Os 35 "órgãos
superiores" presentes em 2025 são ministérios, a Presidência, a AGU, a CGU e o Banco Central.

## O que entra na conta

Do arquivo de execução de 2025 (valor pago no ano mais restos a pagar pagos):

- Só **aplicação direta** (modalidade 90). Os repasses a estados, municípios e entidades
  (modalidades 30 a 50) já estão na camada "Dinheiro federal". A modalidade 91 (pagamentos entre
  órgãos do próprio orçamento) contaria duas vezes.
- Só **pessoal, custeio e investimentos** (grupos 1, 3 e 4). Juros, amortização da dívida e
  inversões financeiras (grupos 2, 5 e 6) ficam de fora.
- Fora, por seguirem quem recebe e não a unidade que paga: aposentadorias e benefícios do INSS
  (Fundo do Regime Geral), BPC, Bolsa Família, seguro-desemprego e abono salarial (FAT) e outros
  auxílios a pessoas — **R$ 1.364,0 bi**. Os três primeiros já aparecem na página da cidade.
- Fora também: aposentadorias e pensões de servidores civis e militares (R$ 158,4 bi; o inativo
  mora onde quiser), subvenções econômicas a bancos (R$ 25,2 bi: Pronaf, Plano Safra) e sentenças
  judiciais (R$ 3,2 bi).

Sobram R$ 339,0 bi: R$ 161,2 bi de salários da ativa, R$ 143,0 bi de serviços, materiais e contas,
R$ 34,8 bi de obras e equipamentos.

## Quanto vai para a cidade certa e quanto fica na sede

Cada despesa vai para a cidade da unidade gestora que pagou.

| Onde ficou registrado | R$ bi | % |
|---|---:|---:|
| Brasília (inclui R$ 13,1 bi do Fundo Constitucional do DF, que paga a polícia e parte da saúde e da educação do DF) | 170,2 | 50,2% |
| Sem cidade no cadastro: folhas de pagamento centrais dos ministérios ("FOLHA DE PAGAMENTO - MF", "- MGI", "- MPS"…), todas em Brasília | 19,1 | 5,6% |
| Exterior (comissões militares, embaixadas) | 5,1 | 1,5% |
| Folha central fora do DF: Pagadoria de Pessoal da Marinha e Subdiretoria de Pagamento da Aeronáutica, no Rio | 17,2 | 5,1% |
| **Nas outras 590 cidades, pelas unidades locais** | **127,6** | **37,6%** |

O que fica em Brasília sem ser de Brasília, pelos maiores casos:

- **Folha de pagamento.** Metade dos salários da ativa (R$ 81 bi de R$ 161 bi) está no DF ou sem
  cidade. O Centro de Pagamento do Exército (R$ 18,2 bi) paga daqui os militares do país todo; a
  folha da Polícia Federal, da Polícia Rodoviária, da Receita, do INSS, do Ministério da Saúde e dos
  hospitais universitários (Ebserh, R$ 8,5 bi) também é paga de Brasília. Na Paraíba, por exemplo,
  a superintendência da Polícia Federal em João Pessoa aparece com só R$ 18 milhões, o custeio: os
  salários dos agentes estão em Brasília. É o mesmo problema da folha do governo da Paraíba.
- **Compras centralizadas.** O Departamento de Logística em Saúde do Ministério da Saúde
  (R$ 22,1 bi) compra os remédios e as vacinas distribuídos a todos os estados.
- **Obras.** O DNIT registra R$ 14,4 bi na unidade de Brasília, embora as obras sejam nas estradas.
  Pelo localizador, ao menos R$ 3,6 bi disso são obras indicadas em outros estados.

Universidades e institutos federais são o caso bom: pagam os próprios servidores e aparecem na
cidade da reitoria. O campus de outra cidade, quando tem unidade própria, aparece só com o custeio
(Patos, na Paraíba: R$ 4,6 milhões do Instituto Federal e da UFCG); quando não tem, some na reitoria.

O localizador do orçamento confirma o retrato no nível do estado: das despesas com UF indicada fora
do DF (R$ 83 bi), 93% foram pagas por uma unidade no próprio estado e 6% por uma unidade em Brasília.
Mas só 31% do gasto tem UF no localizador; o resto é "nacional".

## O que o site mostra

Na página de cada cidade, no grupo "O que chega e o que sai daqui", o bloco "O que o governo
federal gastou aqui": o total de 2025, por morador, dividido em salários, contas do dia a dia e
obras, os órgãos que mais gastaram e o aviso sobre a sede. Quando a cidade paga daqui a folha de
outras (Rio de Janeiro, Brasília), o bloco diz quanto. Nas cidades sem unidade federal, o bloco
explica por que não há valor.

Não fizemos camada no mapa: com unidade federal em só 591 cidades e metade do valor em Brasília, o
mapa ficaria quase vazio e passaria a ideia errada de onde o dinheiro é gasto.

## Como rodar

```bash
uv run --project pipeline gasto-federal 2025
```

Baixa os 12 zips do ano (~80 MB, em `data/raw/portal-transparencia/despesas-execucao/`) e as
~95 páginas da tabela de unidades (`data/raw/compras/`), e grava
`site/public/data/federal/gasto-direto.json` e a cópia `pipeline/referencia/gasto-federal-direto.json`.
Na publicação (`.github/scripts/dados.sh`, fila independente), se o Portal pedir captcha ou o
Compras.gov.br não responder fora do Brasil, o comando usa a cópia. `--sem-baixar` só copia.

## Próximos passos possíveis

- **Folha por cidade de exercício.** Cruzar a unidade de exercício (UORG) do arquivo de servidores
  com o endereço da unidade no SIORG daria a cidade de cada servidor civil, inclusive dos que são
  pagos de Brasília (Polícia Federal, INSS, Receita). Só a soma por cidade seria guardada, como no
  Bolsa Família. Não cobre militares.
- **Judiciário e Ministério Público da União.** Os tribunais publicam a própria execução; a Justiça
  Federal e a do Trabalho têm varas em centenas de cidades.
- **Outros anos.** O Portal tem a execução mensal desde janeiro de 2014.
