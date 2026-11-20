# Receitas da União: de onde vêm os dados

Levantamento feito em novembro de 2026 para a página `/receitas`. Todas as fontes abaixo foram baixadas
de verdade; os números citados saíram desses arquivos.

## O que foi conferido

| Fonte | O que tem | Anos | Serve? |
|---|---|---|---|
| **Portal da Transparência (CGU), "Receitas"** — `dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/receitas/{ano}_Receitas.zip` | Cada receita do orçamento federal, com **previsto (atualizado)** e **realizado**, por órgão e unidade que arrecada, nos 4 níveis da natureza da receita (categoria, origem, espécie, detalhamento). Inclui operações de crédito, e o refinanciamento da dívida aparece separado no detalhamento. | 2014 a hoje (o ano corrente é atualizado de tempos em tempos) | **Sim: é a fonte usada.** Zip de ~2 MB por ano, CSV em latin-1 separado por `;`, sem captcha (é o mesmo servidor do orçamento da despesa). |
| **Tesouro: RREO da União** (Anexo 1, Balanço Orçamentário), pela API do SICONFI (`apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?…&id_ente=1`) | O relatório oficial: receita por origem e espécie (2 níveis), previsão inicial, atualizada e realizado, e o refinanciamento numa linha própria. | 2015 a hoje (2014 vem vazio) | **Para conferir.** Não desce até o tributo nem diz o órgão. O pipeline guarda o total oficial de cada ano fechado. |
| **Tesouro: Resultado do Tesouro Nacional** (Tesouro Transparente, `seriehistorica….xlsx`, ~4 MB) | Série mensal desde 1997 da receita **primária**: IR, IPI, Cofins, INSS, dividendos, royalties… e as transferências a estados e municípios. | 1997 a hoje | Não para esta página: fica de fora tudo o que é financeiro (operações de crédito, refinanciamento, juros recebidos), justamente o que o site quer mostrar. Bom para conferir tributos. |
| **Receita Federal: arrecadação por estado** (`gov.br/receitafederal/dados/arrecadacao-estado.csv`, já usada no mapa) | Arrecadação mensal por tributo e UF. | 2000 a hoje | Não: só os tributos que a Receita administra (sem royalties, dividendos, empréstimos); valores brutos. |
| Tesouro Transparente, "Receita Orçamentária da União" | CSV de 12 KB parado em 2018. | — | Não. |

## Conferência dos totais

Total arrecadado no ano (com o refinanciamento e as receitas intraorçamentárias), em R$ bilhões:

| Ano | Portal (soma do arquivo) | RREO (Tesouro) | Diferença | Refinanciamento (Portal) |
|---|---|---|---|---|
| 2015 | 2.665,7 | 2.662,3 | +0,1% | 775,5 |
| 2016 | 2.839,7 | 2.837,5 | +0,1% | 752,5 |
| 2017 | 2.558,0 | 2.583,7 | −1,0% | 506,3 |
| 2018 | 2.942,4 | 2.940,7 | +0,1% | 534,3 |
| 2019 | 2.991,6 | 2.990,9 | 0,0% | 374,9 |
| 2020 | 3.631,4 | 3.670,0 | −1,0% | 508,0 |
| 2021 | 4.080,2 | 4.280,2 | −4,7% | 1.609,9 |
| 2022 | 4.208,0 | 4.327,0 | −2,7% | 1.471,2 |
| 2023 | 4.305,7 | 4.380,7 | −1,7% | 1.378,0 |
| 2024 | 4.778,1 | 4.862,9 | −1,7% | 1.377,8 |
| 2025 | 5.614,1 | 5.719,4 | −1,8% | 1.752,4 |

- A **previsão atualizada** bate com o RREO em todos os anos (2024: 5.414,3 no Portal, 5.414,9 no RREO).
- O **refinanciamento** bate com o RREO (2024: 1.377,8 no Portal, 1.377,9 no RREO), menos em 2021 (1.609,9 contra 1.647,5).
- A diferença no realizado aparece de 2020 em diante e fica em impostos, contribuições e royalties (2024: impostos 983 no
  Portal contra 1.018 no RREO); os itens financeiros (dividendos, operações de crédito fora do refinanciamento, rendimento
  do caixa do Tesouro) batem. O arquivo do Portal parece não trazer parte dos lançamentos de ajuste desses tributos.
  A página mostra o total do RREO na nota de rodapé, ao lado da diferença.
- Conferência com o Resultado do Tesouro Nacional, 2024: dividendos e participações R$ 72,4 bi (RTN) contra
  R$ 72,6 bi (dividendos e juros sobre capital próprio no Portal); imposto de renda R$ 785 bi (RTN, bruto) contra R$ 757 bi.

## Como o arquivo do Portal vira a página

- Níveis para descer: **tipo** (origem: impostos, contribuições, operações de crédito…), **subtipo** (espécie),
  **receita** (o tributo: IRPJ, Cofins…) e **parcela** (valor principal, multas e juros, dívida ativa, parcelamentos).
  O detalhamento do Portal junta o tributo e a parcela num nome só ("IRPJ-LIQUIDA DE INCENTIVOS-MULTAS E JUROS"); o
  pipeline separa os dois pelo fim do nome. Também dá para dividir por **órgão** que arrecada e por **categoria**
  (corrente, de capital).
- O arquivo não traz os códigos da natureza da receita, só os nomes (cortados em 45 letras e abreviados no detalhamento).
  Cada item ganha um código curto calculado a partir do nome, o mesmo em todos os anos enquanto o nome não muda.
  Os nomes dos maiores itens foram reescritos à mão em português simples (`NOMES_ITENS` em
  `pipeline/src/orcamento_pipeline/receitas_uniao.py`); os outros passam por uma limpeza automática das abreviações.
- **Refinanciamento**: operações de crédito cujo detalhamento fala em refinanciamento da dívida
  ("TIT.RESP.TN-REFIN.DIV.PUB.FED…"), e não "exceto refinanciamento". É o espelho das subfunções 841 e 842 que o botão
  "Sem refinanciamento" do explorador de gastos já tira.
- Valores são líquidos: o arquivo já desconta restituições e outras deduções (há linhas negativas).
- De 2014 e 2015 o Portal só tem o valor do ano inteiro (uma data de lançamento); de 2016 em diante, dia a dia.

## Comandos

```
uv run --project pipeline receitas-uniao               # baixa o que falta (~25 MB de zips em data/raw/receitas-uniao/)
uv run --project pipeline receitas-uniao --sem-baixar  # só copia pipeline/referencia/receitas-uniao.json (publicação)
```
