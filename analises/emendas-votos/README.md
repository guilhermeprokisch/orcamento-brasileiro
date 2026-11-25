# Os deputados mandam as emendas para onde tiveram voto?

Novembro de 2026. Cruzamos as emendas individuais e Pix pagas de 2023 a 2026 com os votos de cada deputado federal em
cada município e com a população de cada cidade.

**Resposta curta:** sim. O dinheiro segue o voto, não a população. Mas não é proporcional: cada voto da base recebe
menos que um voto de onde o deputado quase não teve voto. Onde a emenda dobrou, o deputado teve de 8% a 12% mais votos
na eleição de 2026. Isso é associação, não prova de compra de voto.

Todos os números abaixo saem de `uv run analise-emendas-votos` e ficam gravados em
`data/analises/emendas-votos/resultados.json`.

## Resultados

### 1. O dinheiro segue o voto, não a população

A comparação é entre os municípios do mesmo deputado. É uma regressão de Poisson (PPML) com efeito fixo de deputado e
erros agrupados por deputado.

| modelo | elasticidade a votos | elasticidade à população |
|---|---|---|
| só votos | 0,72 (ep 0,01) | — |
| só população | — | 0,69 (ep 0,01) |
| **votos + população** | **0,69 (ep 0,01)** | **0,05 (ep 0,01)** |

Com votos e população no mesmo modelo, a população quase some: ela só parecia importar porque cidade grande tem mais
voto. Entre duas cidades do mesmo tamanho, a que deu ao deputado 10% mais votos recebe cerca de 7% mais emenda dele.
Trocar a população pelo número de votos válidos não muda o resultado (0,68).

Para 78% dos deputados, a distribuição das emendas pelas cidades se parece mais com a dos votos do que com a da
população. A correlação mediana é de 0,70 com os votos e de 0,45 com a população.

Quando o deputado teve zero voto numa cidade, a chance de ela receber emenda dele é de 5%. Quando teve algum voto, é de
26%. As cidades sem voto ficam com menos de 1% do dinheiro.

### 2. Não é proporcional: o voto da base sai mais barato

Uma elasticidade abaixo de 1 quer dizer que a emenda cresce com o voto, mas mais devagar que ele.

| fatia dos votos do deputado que veio da cidade | chance de receber | R$ por voto |
|---|---|---|
| até 0,01% | 7% | 6.227 |
| 0,01–0,05% | 16% | 2.572 |
| 0,05–0,1% | 27% | 1.783 |
| 0,1–0,25% | 40% | 1.344 |
| 0,25–0,5% | 52% | 1.070 |
| 0,5–1% | 60% | 929 |
| 1–2% | 71% | 920 |
| 2–5% | 82% | 847 |
| mais de 5% | 91% | 617 |

As 10 cidades onde cada deputado foi mais votado concentram 55% dos votos dele e recebem 40% das emendas. O deputado
também espalha dinheiro por cidades onde teve pouco voto, provavelmente para fazer base nova ou atender prefeitos
aliados. E 23% das cidades que deram ao deputado ao menos 1% dos votos dele não receberam nenhuma emenda dele em
quatro anos.

### 3. Cidade pequena e cidade "do deputado" recebem mais por voto

| tamanho da cidade | R$ por voto |
|---|---|
| até 5 mil habitantes | 2.041 |
| 5–10 mil | 1.663 |
| 10–20 mil | 1.450 |
| 20–50 mil | 1.139 |
| 50–100 mil | 862 |
| 100–500 mil | 692 |
| mais de 500 mil | 531 |

| fatia que o deputado teve dos votos válidos da cidade | chance de receber | R$ por voto |
|---|---|---|
| menos de 1% | 15% | 1.842 |
| 1–3% | 36% | 804 |
| 3–5% | 50% | 758 |
| 5–10% | 59% | 707 |
| 10–20% | 68% | 701 |
| 20–30% | 81% | 742 |
| 30–50% | 95% | 1.070 |
| mais de 50% | 98% | 1.131 |

O R$ por voto cai à medida que o deputado fica mais forte na cidade, até ele ter cerca de um terço dos votos dela.
Depois, volta a subir. Onde ele é dominante, a cidade quase sempre recebe, e recebe mais por voto. É o desenho que se
espera de cidades amarradas a um deputado por meio do prefeito.

### 4. O preço médio do voto não serve para comparar deputados

Dividindo tudo o que cada deputado mandou pelos votos que teve, a mediana fica em R$ 1.117 por voto. O p10 é R$ 474 e
o p90, R$ 2.399. A diferença entre deputados é quase toda mecânica. A cota de emendas é igual para todos, mas em Roraima
e no Amapá se elege deputado com 6 a 11 mil votos, enquanto quem passa de 1 milhão de votos fica abaixo de R$ 50 por
voto. O que diz algo é a comparação entre as cidades de um mesmo deputado. Os valores por deputado estão em
`preco-por-deputado.csv`.

### 5. Os votos em 2026

Medimos a variação dos votos de 2022 para 2026, cidade por cidade, para os 334 deputados do painel que concorreram de
novo a deputado federal no mesmo estado. A regressão tem efeito fixo de deputado e de município, o que tira tendências
locais como o comparecimento e a onda partidária. Ela também controla os votos de 2022, o que tira a volta à média.

- A elasticidade dos votos de 2026 à emenda recebida é de 0,17 (ep 0,007) e de 0,12 (ep 0,005) só nas cidades em que o
  deputado teve 50 votos ou mais em 2022. Dobrar a emenda numa cidade vem junto com 8% a 12% mais votos ali.
- Nas cidades com 50 votos ou mais em 2022, agrupadas em quartis do R$ por voto que receberam (dentro de cada
  deputado), os votos mudaram assim de 2022 para 2026: sem emenda, −7%; 1º quartil, −17%; 2º, −4%; 3º, +18%;
  4º, +82%. Parte da alta do último quartil é volta à média, e a regressão desconta isso.

## Dados

| o quê | fonte | recorte |
|---|---|---|
| Emendas pagas, por autor e município | CGU, Portal da Transparência (emendas parlamentares, pagamentos por favorecido) | Individuais e Pix pagas de 2023 a 2026 |
| Emendas de saúde de 2023–24 | Fundo Nacional de Saúde, consulta de propostas | Uma planilha por UF e ano, com destino, parlamentar e valor pago |
| Votos por município | TSE, votação por candidato e município | Deputado federal, 2022 e 2026 |
| População | IBGE, Censo 2022 (tabela 4709) | Todos os municípios |
| Deputados | Câmara dos Deputados, dados abertos | Legislatura 57 (2023–2027) |

**Por que o FNS.** No Portal, R$ 19,5 bi das emendas individuais de saúde de 2023–24 aparecem pagos ao Banco do Brasil,
em Brasília, sem a cidade. O FNS publica cada proposta com o fundo de saúde de destino, o município, o parlamentar e o
valor pago. Os totais batem com o Portal: R$ 10,1 bi contra R$ 10,0 bi em 2023, e R$ 12,3 bi contra R$ 12,0 bi em 2024.
Por isso trocamos toda a saúde individual de 2023–24 do Portal pela do FNS, sem contar nada duas vezes. A partir de
2025, o próprio Portal já registra o fundo municipal.

**O painel.** O painel tem uma linha para cada deputado e cada município do estado dele: 559 deputados e 191 mil pares,
somando R$ 58,1 bi em emendas, dos quais R$ 13,7 bi vêm do FNS. Brasília fica de fora, porque lá o pagamento vai a
entidades com sede na capital.

**Casamento de nomes.**
- Deputados: cada deputado foi ligado ao candidato do TSE pelo nome e pela UF, e 656 dos 663 casaram. Ficaram sem par
  Augusto Puppio, Nivaldo Albuquerque, Paulo Folletto, Silvia Waiãpi, Sonize Barbosa, Yandra Moura e Zé Adriano.
- Municípios do TSE: casados com o IBGE pelo nome. Os 13 de grafia diferente (16 contando 2026) vêm de uma tabela
  pública de códigos TSE→IBGE, consultada durante a carga e nunca copiada para o repositório.

## Limites

1. **Associação, não prova de compra.** O deputado manda dinheiro para onde tem prefeito aliado (eleito em 2024),
   para onde já pretende fazer campanha e para onde espera crescer, e tudo isso também traz voto. Os dados mostram que
   emenda e voto andam juntos e com que intensidade. Não mostram se foi a emenda que trouxe o voto ou se os dois vêm da
   mesma aliança.
2. **Pagamento não é empenho.** Uma emenda indicada num ano pode ter sido paga em outro. O FNS dá o valor pago
   acumulado de cada proposta, sem o mês do pagamento.
3. **As emendas de 2023 são da legislatura anterior.** A LOA 2023 foi votada em dezembro de 2022, então as emendas de
   2023 de quem não voltou à Câmara ficam fora do painel.
4. **Ainda falta cerca de R$ 1 bi.** São pagamentos ao Banco do Brasil fora da saúde, sobretudo de assistência social,
   que continuam sem a cidade de destino.
5. **Boa Esperança do Norte (MT) não entra.** O município foi criado depois do Censo 2022: tem votos em 2026, mas não
   tem população nem dados de 2022.

## Como refazer

De dentro de `pipeline/`, com o [uv](https://docs.astral.sh/uv/):

```bash
uv run analise-emendas-votos --do-espelho
```

Baixa do espelho os insumos já reduzidos e roda a análise. Leva poucos minutos.

```bash
uv run analise-emendas-votos
```

Baixa tudo das fontes originais e roda a análise:
- uns 1 GB do TSE;
- 54 planilhas do FNS, que levam minutos cada e baixam três por vez;
- o Censo 2022 do IBGE e o cadastro da Câmara.

Também precisa de `data/publico/emendas-pagamentos.parquet`, que sai de `uv run explorador-emendas`. Se ele não
existir, o comando para e diz o que falta. Com `--do-espelho`, esse arquivo vem do espelho.

O que fica em `data/analises/emendas-votos/`:

| arquivo | o que tem |
|---|---|
| `insumos/votos-deputado-federal.parquet` | votos válidos de cada candidato a deputado federal por município, 2022 e 2026 |
| `insumos/fns-propostas.parquet` | propostas de emenda individual do FNS, 2023–24, com uma linha por proposta e parlamentar |
| `insumos/populacao-2022.csv` | população do Censo 2022 por município |
| `insumos/deputados.csv` | deputados da legislatura 57 |
| `painel.parquet` | deputado × município: emenda, votos de 2022 e de 2026, população |
| `resultados.json` | todos os números deste texto |
| `preco-por-deputado.csv` | R$ de emenda por voto de cada deputado |

No espelho, os mesmos arquivos ficam em
`https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/analises/emendas-votos/`.

O código está em [`pipeline/src/orcamento_pipeline/analise_emendas_votos.py`](../../pipeline/src/orcamento_pipeline/analise_emendas_votos.py).
