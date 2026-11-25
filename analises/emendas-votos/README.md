# Os deputados mandam as emendas para onde tiveram voto?

Novembro de 2026. Cruzamos as emendas individuais e Pix pagas de 2023 a 2026 com os votos de cada deputado federal em
cada município (2022 e 2026) e com a população de cada cidade.

**Resposta curta:** sim. Quanto mais forte o deputado numa cidade, mais emenda ela recebe dele. Sabendo quantos votos
ele teve ali, o tamanho da cidade não acrescenta nada. Onde a emenda chegou, o deputado também se saiu melhor em 2026,
mas os dados não permitem dizer que foi a emenda que trouxe o voto.

Todos os números abaixo saem de `uv run analise-emendas-votos` e ficam em `data/analises/emendas-votos/resultados.json`.
As exceções são os testes da revisão citados na seção 5 (votos de 2018, prefeitos de 2024 e dobradinhas), que ainda não estão no comando e por isso aparecem sem números.

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
posse dos prefeitos eleitos em 2024, mas isso é hipótese: não cruzamos com os prefeitos.

Os veteranos dão peso maior aos votos (0,73 contra 0,60). Para eles, parte dos votos de 2022 já é fruto de emenda antiga,
então o número "limpo", em que o voto vem antes de qualquer emenda, fica mais perto de 0,6.

### 5. E os votos de 2026?

São 334 deputados do painel que concorreram de novo a deputado federal no mesmo estado.

**Na soma, não há ganho visível.** Os votos deles cresceram 4,5% nas cidades para onde mandaram emenda e 6,3% nas outras.
As cidades com emenda tinham 75,6% dos votos deles em 2022 e 75,3% em 2026.

**Mas, entre cidades com o mesmo ponto de partida, as que receberam emenda foram bem melhor:**

| votos do deputado na cidade em 2022 | variação até 2026, com emenda | sem emenda |
|---|---|---|
| 201 a 1.000 | +23% | −7% |
| 1.001 a 5.000 | −8% | −23% |
| mais de 5.000 | −10% | −27% |

Os números de 2026 vêm de uma regressão de Poisson com efeito fixo de deputado e de município, que controla os votos de
2022. A correção é necessária: o voto volta à média, e onde o deputado teve muito voto ele tende a perder. Nessa
regressão, ter recebido emenda está associado a +84% de votos em 2026 (coeficiente 0,61, ep 0,03). A associação cresce
quanto mais perto da eleição a emenda foi paga:

| pago em | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| associação com os votos de 2026 | 0% | +22% | +52% | +65% |

**Por que isso não mostra que a emenda traz o voto.** O deputado manda emenda para onde a base é sólida (prefeito aliado,
cabo eleitoral), e base sólida perde menos voto com ou sem emenda. Um teste com os votos de 2018 reforça essa leitura.
Ele está na revisão do estudo e ainda não neste comando. No ciclo anterior (313 veteranos, votos de 2022 comparados aos
de 2018), a emenda paga *depois* da eleição, em 2023–26, acompanha o ganho de votos mais do que a emenda paga *antes*,
em 2019–22. O deputado manda dinheiro para onde cresceu. Os dados não separam "a emenda traz o voto" de "a emenda
acompanha a aliança que traz o voto".

Por isso não há aqui "R$ por voto a mais". A comparação é entre cidades do mesmo deputado e não dá um total de votos
ganhos.

**Duas medidas de aliança.** A revisão testou duas medidas de aliança que ainda não estão neste comando.
- **Prefeitos eleitos em 2024.** O dinheiro acompanha o prefeito: depois da posse, a cidade com prefeito do partido do
  deputado passa a receber mais que o dobro. Mas o partido do prefeito não explica por que o deputado vai melhor onde
  mandou emenda.
- **Dobradinhas com deputados estaduais.** Onde o deputado federal mandou emenda, o parceiro estadual também foi melhor
  em 2026, mas bem menos que o próprio federal. O ganho é do deputado, não do grupo. Esta medida vale só para os
  deputados com um parceiro estável no estado inteiro, uma minoria do painel.

As duas mostram que o dinheiro acompanha a aliança, mas nenhuma delas explica a associação entre emenda e voto. O canal
mais provável é o apoio pessoal do prefeito ao deputado, e ele não tem fonte pública. A causa continua em aberto.

**Próximos passos:**
- as planilhas do FNS de 2019–22, porque metade das emendas individuais daqueles anos aparece no Portal sem a cidade;
- levar para este comando os testes da revisão: votos de 2018, prefeitos de 2024 e dobradinhas;
- as emendas de 2027 em diante, quando existirem.

## Dados

| o quê | fonte | recorte |
|---|---|---|
| Emendas pagas, por autor e município | CGU, Portal da Transparência (emendas parlamentares, pagamentos por favorecido) | Individuais e Pix, pagas de 2023 a 2026 |
| Emendas de saúde de 2023–24 | Fundo Nacional de Saúde, consulta de propostas | Uma planilha por UF e ano, com destino, parlamentar e valor pago |
| Votos por município | TSE, votação por candidato e município | Deputado federal, 2022 e 2026 |
| População | IBGE, Censo 2022 (tabela 4709) | Todos os municípios |
| Deputados | Câmara dos Deputados, dados abertos | Legislatura 57 (2023–2027); veterano = também na 56 |

**Por que o FNS.** No Portal, R$ 19,5 bi das emendas individuais de saúde de 2023–24 aparecem como pagos ao Banco do
Brasil, em Brasília, sem a cidade. O FNS publica cada proposta com o fundo de saúde de destino, o município, o
parlamentar e o valor pago. Os totais batem: R$ 10,1 bi contra R$ 10,0 bi em 2023, e R$ 12,3 bi contra R$ 12,0 bi em
2024. Por isso trocamos toda a saúde individual de 2023–24 do Portal pela do FNS, sem contar nada duas vezes. A partir de
2025, o próprio Portal já registra o fundo municipal.

**O painel.** Uma linha por deputado e município do estado dele: 559 deputados e 191 mil pares, somando R$ 58,1 bi em
emendas, dos quais R$ 13,7 bi vêm do FNS. Brasília fica de fora, porque lá o pagamento vai a entidades com sede na
capital.

**Casamento de nomes.**
- Deputados: cada um foi ligado ao candidato do TSE pelo nome e pela UF, e 656 dos 663 casaram. Ficaram sem par
  Augusto Puppio, Nivaldo Albuquerque, Paulo Folletto, Silvia Waiãpi, Sonize Barbosa, Yandra Moura e Zé Adriano.
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

## Como refazer

De dentro de `pipeline/`, com o [uv](https://docs.astral.sh/uv/):

```bash
uv run analise-emendas-votos --do-espelho
```

Baixa do espelho os insumos já reduzidos e roda a análise. Leva cerca de um minuto.

```bash
uv run analise-emendas-votos
```

Baixa tudo das fontes originais e roda:
- uns 1 GB do TSE;
- 54 planilhas do FNS, que levam minutos cada e baixam três por vez;
- o Censo do IBGE;
- o cadastro da Câmara.

Também precisa de `data/publico/emendas-pagamentos.parquet`, que sai de `uv run explorador-emendas`. Se ele não existir,
o comando para e diz o que falta. Com `--do-espelho`, nada disso é preciso: os insumos, inclusive o recorte do Portal,
vêm do espelho.

Arquivos em `data/analises/emendas-votos/`:

| arquivo | o que tem |
|---|---|
| `insumos/emendas-portal.parquet` | o recorte do Portal da Transparência: emendas individuais e Pix pagas de 2023 a 2026 |
| `insumos/votos-deputado-federal.parquet` | votos válidos de cada candidato a deputado federal, por município, em 2022 e 2026 |
| `insumos/fns-propostas.parquet` | propostas de emenda individual do FNS de 2023–24, uma linha por proposta e parlamentar |
| `insumos/populacao-2022.csv` | população do Censo 2022 por município |
| `insumos/deputados.csv` | deputados da legislatura 57, com a marca de veterano |
| `painel.parquet` | deputado × município: emenda (total, por ano, Pix, FNS, estadual), votos de 2022 e 2026, população |
| `resultados.json` | todos os números deste texto, exceto o teste de 2018 |
| `preco-por-deputado.csv` | R$ de emenda por voto de cada deputado (mecânico; ver a seção 3) |

No espelho, os arquivos ficam numa pasta com a versão dos dados, por exemplo
`https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/analises/emendas-votos/91543d3e5f/`.
A versão vem do conteúdo dos insumos. Dados novos vão para outra pasta, e a antiga continua lá. O arquivo
[`espelho.json`](espelho.json), ao lado deste texto, diz qual versão o texto cita, e é a que o `--do-espelho` baixa. Ele
confere se os arquivos baixados batem com essa versão.

O código está em [`pipeline/src/orcamento_pipeline/analise_emendas_votos.py`](../../pipeline/src/orcamento_pipeline/analise_emendas_votos.py).
