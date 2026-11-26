# Os deputados mandam as emendas para onde tiveram voto?

Novembro de 2026. Cruzamos as emendas individuais e Pix pagas de 2023 a 2026 com os votos de cada deputado federal em
cada município (2018, 2022 e 2026), com a população de cada cidade, com os prefeitos eleitos em 2024 e com os votos dos
deputados estaduais.

**Resposta curta:** sim. Quanto mais forte o deputado numa cidade, mais emenda ela recebe dele. Sabendo quantos votos
ele teve ali, o tamanho da cidade não acrescenta nada. Onde a emenda chegou, o deputado também se saiu melhor em 2026,
mas os dados não permitem dizer que foi a emenda que trouxe o voto.

Todos os números abaixo saem de `uv run analise-emendas-votos` e ficam em [`resultados.json`](resultados.json), ao
lado deste texto. A versão para quem não é da área está no site:
[orcamentobrasileiro.com.br/analises/emendas-votos](https://orcamentobrasileiro.com.br/analises/emendas-votos).

## Resultados

### 1. O dinheiro segue o voto

O método é uma regressão de Poisson (PPML) que compara os municípios de um mesmo deputado (efeito fixo de deputado),
com erros agrupados por deputado.

| modelo | elasticidade a votos | elasticidade à população |
|---|---|---|
| só votos | 0,72 (ep 0,01) | — |
| só população | — | 0,69 (ep 0,01) |
| **votos + população** | **0,69 (ep 0,01)** | **0,05 (ep 0,01)** |

Entre duas cidades do mesmo tamanho, a que deu ao deputado 10% mais votos recebe cerca de 7% mais emenda dele. Com os
votos no modelo, a população quase some.

**Isso não quer dizer que cidade grande recebe o mesmo que cidade pequena.** Os votos de um deputado numa cidade são o
tamanho dela vezes a força dele ali. Separando as duas coisas, a emenda cresce com o tamanho da cidade (0,74, medido
pelos votos válidos) e com a força do deputado nela (0,67, a fatia dos votos da cidade que foi dele), quase na mesma
medida. O que a primeira tabela diz é que, sabendo os votos, a população não acrescenta informação.

O resultado resiste aos recortes:

| recorte | votos | população |
|---|---|---|
| sem o que foi pago a governos e fundos estaduais (R$ 4,2 bi) | 0,70 | −0,06 |
| sem as capitais | 0,70 | −0,07 |
| só veteranos (estavam na Câmara em 2019–22) | 0,73 | |
| só novatos | 0,60 | |

O dinheiro pago a governos e fundos estaduais aparece no município da sede, a capital, mas pode ser gasto em qualquer
cidade do estado. Tirando esse dinheiro, ou tirando as capitais, a população passa a ter sinal negativo. O pouco peso
que ela tinha vinha das capitais.

### 2. O "dono" da cidade manda muito mais

Esta tabela compara cidades do mesmo tamanho (controlando os votos válidos) e olha que fatia dos votos da cidade ficou
com o deputado. A base de comparação é a faixa de 1–3%, que vale 1.

| fatia dos votos da cidade que foi do deputado | emenda (vezes) | chance de receber |
|---|---|---|
| zero voto | 0,2 | 5% |
| menos de 1% | 0,4 | 15% |
| 1–3% | 1 | 36% |
| 3–5% | 1,7 | 50% |
| 5–10% | 2,6 | 59% |
| 10–20% | 4,8 | 68% |
| 20–30% | 9,6 | 81% |
| 30–50% | 19 | 95% |
| mais de 50% | 31 | 98% |

### 3. Mas não é proporcional

- **O deputado mediano manda dinheiro para 62 dos 246 municípios do estado** (27%). A emenda vem em blocos.
- **Para a emenda de um deputado ficar proporcional aos votos dele, metade do dinheiro teria de mudar de cidade**
  (mediana de 50%). Para ficar proporcional à população, 68%. Está mais perto dos votos, mas longe dos dois.
- **As 10 cidades onde cada deputado foi mais votado** concentram 55% dos votos dele e recebem 40% das emendas.
- **Onde o deputado teve zero voto**, a chance de a cidade receber emenda dele é de 5%. Onde teve algum voto, é de 26%.
- **23% das cidades que deram ao deputado ao menos 1% dos votos dele** não receberam nenhuma emenda dele em quatro anos.

Não usamos "R$ de emenda por voto" como medida. Como a emenda vem em blocos, uma emenda de R$ 300 mil numa cidade onde o
deputado teve 30 votos dá R$ 10 mil por voto, e isso não é um preço. Pelo mesmo motivo, a conta por deputado
(`preco-por-deputado.csv`, mediana de R$ 1.117 por voto) é mecânica. A cota de emendas é igual para todos, e em Roraima
se elege deputado com 6 mil votos. Ela fica nos arquivos só para consulta.

### 4. Ao longo do mandato, o dinheiro se afasta do mapa de 2022

Elasticidade a votos de 2022, por ano de pagamento:

| | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| veteranos | 0,89 | 0,76 | 0,67 | 0,62 |
| novatos | — | 0,68 | 0,57 | 0,54 |

No começo do mandato, o deputado paga o mapa que o elegeu. Perto da eleição seguinte, espalha. Os novatos não aparecem
em 2023 porque as emendas daquele ano foram indicadas pela legislatura anterior. A queda de 2024 para 2025 coincide com a
posse dos prefeitos eleitos em 2024, e a seção 6 mostra que o dinheiro de fato acompanha o prefeito.

Os veteranos dão peso maior aos votos (0,73 contra 0,60). Para eles, parte dos votos de 2022 já é fruto de emenda antiga,
então o número "limpo", em que o voto vem antes de qualquer emenda, fica mais perto de 0,6.

### 5. E os votos de 2026?

São 421 deputados do painel que concorreram de novo a deputado federal no mesmo estado.

**Na soma, não há ganho visível.** Os votos deles cresceram 6,5% nas cidades para onde mandaram emenda e 6,9% nas outras.
As cidades com emenda tinham 75,1% dos votos deles em 2022 e 75,0% em 2026.

**Mas, entre cidades com o mesmo ponto de partida, as que receberam emenda foram bem melhor:**

| votos do deputado na cidade em 2022 | variação até 2026, com emenda | sem emenda |
|---|---|---|
| 201 a 1.000 | +25% | −6% |
| 1.001 a 5.000 | −6% | −22% |
| mais de 5.000 | −8% | −29% |

Os números de 2026 vêm de uma regressão de Poisson com efeito fixo de deputado e de município, que controla os votos de
2022. A correção é necessária: o voto volta à média, e onde o deputado teve muito voto ele tende a perder. Nessa
regressão, ter recebido emenda está associado a +84% de votos em 2026 (coeficiente 0,61, ep 0,03). A associação cresce
quanto mais perto da eleição a emenda foi paga:

| pago em | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| associação com os votos de 2026 | +1% | +21% | +51% | +70% |

**Isso não mostra que a emenda traz o voto.** O deputado pode mandar emenda justamente para onde tem um aliado, e é o
aliado que traz o voto. A comparação também é entre cidades do mesmo deputado e não dá um total de votos ganhos. Por
isso não há aqui "R$ por voto a mais".

### 6. A emenda traz o voto ou acompanha a aliança?

Três medidas tentam separar as duas leituras. As três mostram que o dinheiro acompanha a aliança. Nenhuma explica a
associação entre emenda e voto.

**Votos de 2018: não é a base antiga.** Se a emenda só marcasse a base fiel do deputado, que os votos de 2022 medem com
ruído, controlar também os votos de 2018 derrubaria a associação. Entre os 255 deputados que concorreram em 2018, 2022 e
2026, ela não muda: o coeficiente vai de 0,60 para 0,61. A emenda de 2023–26 segue os votos de 2022 e quase ignora os de
2018 (elasticidades de 0,70 e 0,03).

**Mas a emenda paga depois da eleição acompanha o ganho de votos mais do que a paga antes.** No mandato anterior, para os
314 veteranos, olhamos os votos de 2022 dados os de 2018:

| emenda considerada | votos de 2022 |
|---|---|
| só a paga em 2019–22, antes da eleição | +103% |
| só a paga em 2023–26, depois da eleição | +161% |
| as duas juntas: a de 2019–22 | +61% |
| as duas juntas: a de 2023–26 | +130% |

A emenda que veio depois da eleição não pode ter trazido aquele voto. Ela acompanha o ganho porque o deputado manda
dinheiro para onde cresceu. O mesmo aparece entre os 26 novatos que tinham concorrido em 2018 sem mandato, e portanto
sem emenda: a emenda de 2023–26 foi para onde eles tinham crescido (+28%). O calendário também se repete no mandato
anterior: a emenda paga em 2019 e 2020 quase não tem relação com os votos de 2022 (0% e +13%), e a paga em 2021 e 2022
tem (+62% e +72%).

**Prefeitos eleitos em 2024: o dinheiro acompanha o prefeito.** Emenda recebida em relação a cidades onde o partido do
deputado não teve candidato nem estava na coligação vencedora, com os mesmos votos de 2022 e a mesma população:

| situação em 2024 | paga em 2023–24 | paga em 2025–26 |
|---|---|---|
| prefeito eleito é do partido do deputado | +65% | +133% |
| partido do deputado na coligação vencedora | +31% | +54% |
| partido disputou e perdeu | +3% | +10% |

A cidade já recebia mais antes da eleição, sinal de que a aliança é anterior. Depois da posse, a diferença dobra. Nas
cidades onde o partido do deputado disputou a prefeitura, comparando cada par deputado–cidade consigo mesmo, ganhar vem
com 42% mais emenda em 2025–26 do que em 2023–24 (ep de 7 pontos). Perder não muda nada.

O partido do prefeito, porém, não explica o voto. Onde o prefeito eleito é do partido do deputado, ele teve 53% mais
votos em 2026 do que em cidades de mesmo ponto de partida. Com emenda e prefeito na mesma conta, o prefeito cai para
+28% e a emenda fica onde estava: de +84% para +82%.

**Dobradinhas com deputado estadual: o ganho é do deputado, não do grupo.** Tratamos como parceiro o candidato a
estadual cuja votação por cidade, em 2022, acompanha a do federal (a regra está em "Limites"). São 289 pares, para 143
deputados; a lista está em `dobradinhas.csv`.
- Com os mesmos votos e a mesma população, a cidade onde os parceiros tiveram 10% ou mais dos votos para estadual recebe
  37% mais emenda do federal.
- Entre os 85 deputados que concorreram de novo e têm parceiro que também concorreu, receber emenda vem com +45% de votos
  em 2026. Controlando os votos dos parceiros em 2022 e em 2026, fica em +43%.
- Onde o federal mandou emenda, os parceiros estaduais foram 13% melhor em 2026. O próprio federal, 45%. Se a emenda só
  marcasse onde o grupo local está forte, o estadual do grupo ganharia junto na mesma medida.

**O que fica.** As três medidas enfraquecem a leitura "a emenda só acompanha a aliança", mas não a derrubam. Nenhuma
mede o apoio pessoal do prefeito ao deputado, que é o canal mais provável e não tem fonte pública. Os dados não separam
"a emenda traz o voto" de "a emenda acompanha a aliança que traz o voto".

## Dados

| o quê | fonte | recorte |
|---|---|---|
| Emendas pagas, por autor e município | CGU, Portal da Transparência (emendas parlamentares, pagamentos por favorecido) | Individuais e Pix, pagas de 2019 a 2026 (o painel usa 2023–26; 2019–22 entra só na seção 6) |
| Emendas de saúde de 2019–24 | Fundo Nacional de Saúde, consulta de propostas | Uma planilha por UF e ano, com destino, parlamentar e valor pago |
| Votos por município | TSE, votação por candidato e município | Deputado federal em 2018, 2022 e 2026; deputado estadual em 2022 e 2026 |
| Prefeitos | TSE, candidatos de 2024 | Quem disputou a prefeitura: partido, coligação e resultado |
| População | IBGE, Censo 2022 (tabela 4709) | Todos os municípios |
| Deputados | Câmara dos Deputados, dados abertos | Legislatura 57 (2023–2027); veterano = também na 56 |

**Por que o FNS.** Até 2024, o Portal registra quase toda emenda individual de saúde como paga ao Banco do Brasil, em
Brasília, sem a cidade: R$ 19,0 bi de 2019 a 2022 e R$ 19,5 bi em 2023–24. O FNS publica cada proposta com o fundo de
saúde de destino, o município, o parlamentar e o valor pago. Os totais dos dois ficam próximos:

| emendas individuais de saúde, R$ bi | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| FNS | 4,3 | 4,9 | 4,6 | 5,3 | 10,1 | 12,3 |
| Portal | 5,0 | 5,2 | 4,9 | 5,8 | 10,5 | 12,0 |
| do Portal, pago ao Banco do Brasil | 4,5 | 4,7 | 4,5 | 5,4 | 10,0 | 9,5 |

Por isso trocamos toda a saúde individual de 2019 a 2024 do Portal pela do FNS, sem contar nada duas vezes. A partir de
2025, o próprio Portal já registra o fundo municipal.

**O painel.** Uma linha por deputado e município do estado dele: 559 deputados e 191 mil pares, somando R$ 58,1 bi em
emendas, dos quais R$ 13,7 bi vêm do FNS. Brasília fica de fora, porque lá o pagamento vai a entidades com sede na
capital.

**Casamento de nomes.**
- Deputados: cada um foi ligado ao candidato do TSE pelo nome e pela UF, e 656 dos 663 casaram. Ficaram sem par
  Augusto Puppio, Nivaldo Albuquerque, Paulo Folletto, Silvia Waiãpi, Sonize Barbosa, Yandra Moura e Zé Adriano.
- A mesma pessoa em 2018, 2022 e 2026: pelo nome civil sem acento e pela UF, só quando o par é único. O TSE grafa o
  mesmo nome com e sem acento conforme o ano; comparar com acento deixava de fora 87 deputados do painel que concorreram de novo.
- Municípios do TSE: casados com o IBGE pelo nome. Os 13 com grafia diferente (16 contando 2026) vêm de uma tabela
  pública de códigos TSE→IBGE, consultada durante a carga e nunca copiada para o repositório.

## Limites

1. **Associação, não prova de compra de voto.** Os dados mostram que emenda e voto andam juntos e com que intensidade.
   Não mostram qual dos dois puxa o outro.
2. **Pagamento não é empenho.** Uma emenda indicada num ano pode ter sido paga em outro. O FNS dá o valor pago acumulado
   de cada proposta, sem o mês do pagamento.
3. **As emendas de 2023 são da legislatura anterior.** A LOA 2023 foi votada em dezembro de 2022, então as emendas de
   2023 de quem não voltou à Câmara ficam fora do painel.
4. **Ainda falta cerca de R$ 1 bi.** São pagamentos ao Banco do Brasil fora da saúde, sobretudo de assistência social,
   que continuam sem a cidade de destino.
5. **Boa Esperança do Norte (MT) fica de fora.** O município foi criado depois do Censo 2022: tem votos em 2026, mas não
   tem população nem votos de 2022.
6. **O partido do deputado é o de 2022.** Para comparar com o do prefeito de 2024 consideramos as fusões (PTB e Patriota
   viraram PRD, PSC entrou no Podemos, PROS no Solidariedade) e as federações. Quem trocou de partido depois de 2022 fica
   classificado pelo antigo. E partido é uma medida pobre de aliança: prefeito apoia deputado de outro partido.
7. **A dobradinha é uma aproximação.** Parceiro é o candidato a estadual com 3 mil votos ou mais cuja fatia dos votos de
   cada cidade, em 2022, tem correlação de 0,6 ou mais com a do federal, e de 0,5 ou mais mesmo sem as três cidades que
   mais pesam (para não pegar quem só é da mesma cidade). A regra só enxerga parceria estável no estado inteiro: pega bem
   família e igreja, e pega mal o deputado que tem um estadual diferente em cada região. Só 143 dos 559 deputados têm
   parceiro por essa regra.

## Como refazer

De dentro de `pipeline/`, com o [uv](https://docs.astral.sh/uv/):

```bash
uv run analise-emendas-votos --do-espelho
```

Baixa do espelho os insumos já reduzidos e roda a análise. Leva poucos minutos.

```bash
uv run analise-emendas-votos
```

Baixa tudo das fontes originais e roda:
- uns 1,5 GB do TSE (votos de 2018, 2022 e 2026 e candidatos de 2024);
- 162 planilhas do FNS (27 UFs, de 2019 a 2024), que levam minutos cada e baixam três por vez: são horas;
- o Censo do IBGE;
- o cadastro da Câmara.

Também precisa de `data/publico/emendas-pagamentos.parquet`, que sai de `uv run explorador-emendas`. Se ele não existir,
o comando para e diz o que falta. Com `--do-espelho`, nada disso é preciso: os insumos, inclusive o recorte do Portal,
vêm do espelho.

Arquivos em `data/analises/emendas-votos/`:

| arquivo | o que tem |
|---|---|
| `insumos/emendas-portal.parquet` | o recorte do Portal da Transparência: emendas individuais e Pix pagas de 2019 a 2026 |
| `insumos/votos-deputado-federal.parquet` | votos válidos de cada candidato a deputado federal, por município, em 2018, 2022 e 2026 |
| `insumos/votos-deputado-estadual.parquet` | o mesmo para deputado estadual, em 2022 e 2026 |
| `insumos/prefeitos-2024.csv` | quem disputou cada prefeitura em 2024: partido, coligação e resultado, sem nomes |
| `insumos/fns-propostas.parquet` | propostas de emenda individual do FNS de 2019 a 2024, uma linha por proposta e parlamentar |
| `insumos/populacao-2022.csv` | população do Censo 2022 por município |
| `insumos/deputados.csv` | deputados da legislatura 57, com a marca de veterano |
| `painel.parquet` | deputado × município: emenda (total, por ano, Pix, FNS, estadual), emenda de 2019–22, votos de 2018, 2022 e 2026, população, prefeito de 2024, votos dos parceiros estaduais |
| `resultados.json` | todos os números deste texto |
| `preco-por-deputado.csv` | R$ de emenda por voto de cada deputado (mecânico; ver a seção 3) |
| `dobradinhas.csv` | os pares deputado federal × deputado estadual tratados como parceiros, com as correlações |

No espelho, os arquivos ficam numa pasta com a versão dos dados, por exemplo
`https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/analises/emendas-votos/f37d999678/`.
A versão vem do conteúdo dos insumos. Dados novos vão para outra pasta, e a antiga continua lá. O arquivo
[`espelho.json`](espelho.json), ao lado deste texto, diz qual versão o texto cita, e é a que o `--do-espelho` baixa. Ele
confere se os arquivos baixados batem com essa versão.

O código está em [`pipeline/src/orcamento_pipeline/analise_emendas_votos.py`](../../pipeline/src/orcamento_pipeline/analise_emendas_votos.py).
