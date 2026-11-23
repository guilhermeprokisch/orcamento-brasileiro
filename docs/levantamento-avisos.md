# Levantamento: avisos nas páginas de cidade e de estado

Item E do [plano de melhorias](plano-de-melhorias.md). Levantamento feito em 23/11/2026.

Cada aviso precisa de três coisas: uma regra escrita, uma fonte que cubra o país inteiro no mesmo
formato e um texto que diga o que o dado mostra sem acusar ninguém.

## 1. Mínimo em saúde e em educação

A regra é da Constituição e da Lei Complementar 141/2012. Ela fala da receita de impostos, somada
às transferências que vêm de impostos (FPM, ICMS repassado, FPE etc.):

| | Prefeitura | Estado | DF |
|---|---:|---:|---:|
| Saúde (ações e serviços públicos de saúde) | 15% | 12% | 12% sobre a parte estadual e 15% sobre a municipal |
| Educação (manutenção e desenvolvimento do ensino) | 25% | 25% | 25% |

### As fontes possíveis

| Fonte | Cobre todas as cidades? | Tem a porcentagem oficial? | Como baixar |
|---|---|---|---|
| **SIOPS** (Ministério da Saúde) | sim | sim, é onde a conta da saúde é feita | consulta por estado em páginas do DATASUS, sem download nacional único |
| **SIOPE** (FNDE) | sim | sim, é onde a conta da educação é feita | painéis e planilhas por estado e por ano |
| RREO Anexo 12 (saúde) e Anexo 8 (educação), no SICONFI | sim | sim | **não estão na API do SICONFI**: testado em 2019, 2022 e 2025, para São Paulo (cidade e estado) e para uma cidade pequena. Os dois anexos são gerados pelo SIOPS e pelo SIOPE e não entram no banco de dados aberto do Tesouro |
| **RREO Anexo 14** (demonstrativo simplificado), no SICONFI | sim, para todos os entes que entregam o RREO, incluindo o "RREO Simplificado" das cidades pequenas | **sim**: repete o resultado dos anexos 12 e 8, na coluna "% Aplicado Até o Bimestre", ao lado do "% Mínimo a Aplicar no Exercício" | API do SICONFI, uma consulta por ente e por ano (a mesma usada em `rreo.py` e `pessoal.py`) |

**Escolha: RREO Anexo 14 do 6º bimestre** (o ano inteiro). É o número que o próprio governo apurou
e declarou, vem da mesma API que o pipeline já usa e cobre prefeituras, estados e DF no mesmo
formato. As duas linhas usadas:

- `AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude`: saúde;
- `MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimento…`: educação.

Pipeline: `uv run minimos` (estados, desde 2019) e `uv run minimos --prefeituras --anos …`.
Cache em `data/raw/siconfi/rreo-a14/{ano}.json.gz`.

### A lacuna do Anexo 14

Em parte das prefeituras o Anexo 14 vem **sem as linhas de saúde e de educação**: o relatório
existe, mas os dois percentuais não. Entre as 400 maiores cidades, em 2023, foram 72 (18%), entre
elas Guarulhos, Campinas, Osasco, Ribeirão Preto, Jundiaí, São Gonçalo e Campos dos Goytacazes. O
mesmo acontece em 2024 e 2025 para Guarulhos e Campinas. Sem a linha, não há aviso.

As fontes originais, testadas em 23/11/2026 para cobrir essa lacuna:

- SIOPE: a API de dados abertos do FNDE (`olinda-ide/servico/DADOS_ABERTOS_SIOPE`, entidade
  `Indicadores_Siope`) respondeu erro 500 a todas as consultas, até a página de documentação;
- SIOPS: a página `rel_perc_LC141.php` tem uma consulta por estado (`carregarDadosLC141.php`), mas
  para São Paulo em 2025 devolveu 144 MB de tabela vazia, sem nome de município.

Fica para uma segunda etapa: tentar de novo o SIOPE e, se der certo, usar como complemento onde o
Anexo 14 não traz a linha.

### Cuidados com o dado

- **Amapá** declara a porcentagem como fração (0,17 em vez de 17%) em 2021, 2024 e 2025, inclusive no
  mínimo (0,15 e 0,25). Prefeituras fazem o mesmo (Anápolis, GO, em 2023: 0,28 em educação e 0,26 em
  saúde; Japeri, RJ: 0,31 e 0,40). Um percentual acima de zero e abaixo de 1 é lido como fração e
  multiplicado por 100: aplicar menos de 1% em educação não é possível com o FUNDEB.
- Às vezes o valor em reais cai na coluna do mínimo (Ceará, 2021: "mínimo" de 2,8 bilhões). Por isso
  a comparação é sempre com o mínimo da Constituição (15%, 12%, 25%), não com o declarado.
- Falta a linha de saúde ou a de educação em alguns casos (São Paulo, estado, saúde em 2019). Sem a
  linha, não há aviso.
- **2020 e 2021, educação:** a Emenda Constitucional 119/2022 livrou de punição quem não aplicou os
  25% nesses anos por causa da pandemia, desde que completasse a diferença até 2023. Esses dois anos
  não geram aviso de educação.
- O percentual do RREO pode mudar depois, se o governo retificar o SIOPS ou o SIOPE, e o Tribunal de
  Contas pode chegar a outro número ao julgar as contas. O aviso diz isso.

### Primeiros números

Amostra de 2023, as 400 maiores prefeituras (a carga de 2025 está em andamento): 325 trazem o
percentual de educação e 322 o de saúde. Ficam abaixo do mínimo:

- educação: 16 (5%), por exemplo Betim (MG) 24,9%, Canoas (RS) 16,7%, Volta Redonda (RJ) 14,5%,
  Botucatu (SP) 13,3%, Guarapari (ES) 10,0%;
- saúde: 5 (1,6%), por exemplo Colombo (PR) 14,2%, Formosa (GO) 13,2%, Breves (PA) 11,0%,
  Itaituba (PA) 7,4%.

Itaituba e Paranaguá (PR) ficam abaixo nas duas áreas.

## 2. Vários anos seguidos gastando mais do que arrecada

Fonte: `mapa/serie.json`, que já está no site. É a despesa empenhada e a receita arrecadada da
prestação de contas anual (DCA), ano a ano.

Gastar mais do que arrecada num ano não é proibido: o governo pode usar dinheiro que sobrou em anos
anteriores. O que chama atenção é o padrão se repetir. Parte do empenho também vira resto a pagar
e é paga depois, então a conta não é o resultado contábil exato do ano.

Cortes testados (prefeituras com o último ano entregue em 2024 ou 2025):

| Anos seguidos, até o último entregue | Déficit em cada ano acima de | Prefeituras |
|---:|---:|---:|
| 3 | 0% | 462 |
| 3 | **2% da receita** | **192** |
| 3 | 5% | 50 |
| 4 | 2% | 84 |
| 5 | 2% | 32 |

Os anos marcados como dado suspeito (aviso 3) não contam e interrompem a sequência: um ano com
receita e despesa 35% diferentes não deve virar prova de déficit.

Nenhum estado cai na regra de 3 anos acima de 2%.

## 3. Dado com cara de erro

Fonte: a mesma `mapa/serie.json`. Aqui o aviso é sobre o dado, não sobre a prefeitura. Anos de 2016
em diante.

| Sinal | Regra | Prefeituras com pelo menos um ano | Casos (ente × ano) |
|---|---|---:|---:|
| Número repetido | despesa ou receita exatamente igual à do ano anterior | 35 (despesa) e 35 (receita), com sobreposição | 37 e 36 |
| Receita e despesa muito diferentes | diferença maior que 30% da receita | 656 | 836 |
| Ano faltando | sem prestação de contas num ano entre 2016 e 2025 | 117 | — |
| Fora da escala | despesa ou receita mais de 5 vezes acima ou abaixo da mediana da própria prefeitura | 129 | 164 |

No total, 785 prefeituras (14%) têm pelo menos um ano marcado desde 2016; 209 delas em 2023, 2024
ou 2025. Entre os estados, só o Paraná, em 2016 e 2017 (diferença acima de 30%).

O teste "fora da escala" pega o que o número repetido não pega. Varginha (MG) declarou R$ 8,3
bilhões de despesa em 2022 **e** em 2023, cerca de 20 vezes o normal dela: o repetido marca só 2023,
a escala marca os dois. Com fator 3 ele marcaria 554 prefeituras, muitas por crescimento real
(Maricá, com royalties); com fator 5, sobram sobretudo declarações parciais (valores perto de zero)
e erros de vírgula. Ainda pega booms de royalties duradouros, como Saquarema (RJ) de 2022 a 2025,
por isso o texto não chama de erro.

A diferença acima de 30% nem sempre é erro. São Gonçalo (RJ) recebeu em 2021 a outorga da concessão
da Cedae e gastou o dinheiro nos anos seguintes; Macaé (RJ) teve royalties de petróleo muito acima do
normal em 2021 e 2022. Por isso o texto diz "pode estar errado na origem ou ser um fato fora do
comum".

O número repetido, ao contrário, quase sempre é erro: Varginha (MG) declarou em 2023 despesa de
R$ 8,3 bilhões, igual à do ano anterior, para uma cidade de 137 mil moradores.
