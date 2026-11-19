# Orçamento Brasileiro

O orçamento federal brasileiro, explicado e explorável.

Projeto independente, sem vínculo com o Governo Federal.

## Estrutura

```
pipeline/   Python + DuckDB: baixa os dados brutos e gera Parquet + JSON
site/       Astro + Solid: páginas estáticas e o Explorer interativo
data/       (ignorado no git) arquivos brutos e Parquet gerados
```

## Rodando

Requer [uv](https://docs.astral.sh/uv/) e Node 22+.

```bash
# 1. dados: baixa 2014 até o ano corrente e gera site/public/data/explorer/*.json
cd pipeline && uv run orcamento

# 1b. estados e cidades (SICONFI). Primeiro traz o cache já pronto do release "dados-siconfi"
#     (precisa da CLI do GitHub, `gh`); sem ele são ~3h de consultas à API (1 por segundo)
uv run semente aplicar
uv run cidades

# 1c. opcional: histórico dos municípios e receitas a partir dos arquivos do FINBRA
#     (baixados à mão; ver pipeline/src/orcamento_pipeline/finbra.py)
uv run finbra ~/Downloads/finbra
#     depois de importar arquivos novos, publicar o cache no release para o CI usar:
uv run semente publicar

# 1d. dados da página /mapa (receita, tributos, áreas de gasto, malhas do IBGE)
uv run mapa
uv run federal 2025    # repasses e benefícios federais por município
uv run inss            # aposentadorias e pensões do INSS por município

# 2. site
cd ../site && npm install && npm run dev
```

`uv run orcamento --anos 2025 2026` limita os anos. O ano corrente é sempre baixado de novo.

## Dados

| Fonte | Conjunto | Uso |
|---|---|---|
| Portal da Transparência (CGU) | [Orçamento da Despesa](https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa) | Explorer: dotação inicial e atualizada, empenhado e realizado por órgão, UO, função, subfunção, programa, ação e natureza da despesa, 2014+ |
| SIOP (Ministério do Planejamento) | [Endpoint SPARQL](https://www1.siop.planejamento.gov.br/sparql/) | Nomes oficiais (com acentos e completos) de UOs, programas e ações, por ano. Cache em `data/raw/siop/`; se o SIOP falhar, ficam os nomes do Portal |
| IBGE | [SIDRA, tabela 1737](https://sidra.ibge.gov.br/tabela/1737) | IPCA (número-índice) para corrigir valores pela inflação |
| SICONFI (Tesouro Nacional) | [API de dados abertos](https://apidatalake.tesouro.gov.br/docs/siconfi/), DCA Anexo I-E | Páginas de estados e cidades: gasto de cada governo estadual e município por função e subfunção (empenhado e pago). Estados: 2014 em diante pela API. Municípios: os dois últimos exercícios pela API (uma consulta por ente; a API tem limite documentado de 1 requisição por segundo e responde HTTP 429 acima disso, então o pipeline segue esse ritmo). Cache em `data/raw/siconfi/`, um arquivo compactado por ano |
| SICONFI (Tesouro Nacional) | [FINBRA](https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf), Anexos I-E, I-C, I-D e I-AB | Histórico dos municípios (2013+): despesa por função, receitas, despesa por natureza (salários, custeio, obras, dívida) e balanço patrimonial (caixa e dívidas em 31/12), um arquivo por ano e por anexo com todos os municípios. O download tem captcha: os arquivos são baixados à mão e importados com `uv run finbra`. O cache importado fica no release `dados-siconfi` do GitHub (`uv run semente publicar` / `aplicar`), de onde o CI o traz |

| Portal da Transparência (CGU) | [Transferências](https://portaldatransparencia.gov.br/download-de-dados/transferencias), [Bolsa Família](https://portaldatransparencia.gov.br/download-de-dados/novo-bolsa-familia), [BPC](https://portaldatransparencia.gov.br/download-de-dados/bpc) | Mapa: dinheiro federal que chega a cada município. Os repasses são baixados pelo pipeline. Bolsa Família e BPC têm uma linha por beneficiário (~6,5 GB por ano) e o servidor bloqueia downloads em série com CAPTCHA: os zips são baixados à mão e somados com `uv run federal <ano> --beneficios <pasta>`; só a soma por município é guardada, em `pipeline/referencia/beneficios/` |
| Ministério da Previdência Social | [Estatísticas municipais](https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/estatisticas-municipais-2000-a-2022), benefícios emitidos por município | Mapa: aposentadorias, pensões e auxílios do INSS pagos em cada município, 2013+. Só os benefícios previdenciários (o BPC vem do Portal da Transparência). Valor líquido, pelo município da agência que paga, não o de residência |
| Receita Federal | [Arrecadação por estado](https://www.gov.br/receitafederal/dados/arrecadacao-estado.csv) | Mapa: impostos federais arrecadados em cada estado, base da estimativa do que cada cidade manda para a União |
| Tesouro Nacional | [Municípios do SIAFI](https://www.tesourotransparente.gov.br/ckan/dataset/lista-de-municipios-do-siafi) | Código SIAFI → código IBGE (o Portal da Transparência usa o SIAFI) |
| IBGE | [Malhas territoriais](https://servicodados.ibge.gov.br/api/docs/malhas) | Contornos de municípios e estados do mapa |

Saídas do pipeline:

- `data/out/orcamento_despesa.parquet`: todos os anos, nível de elemento de despesa (para o DuckDB-WASM no futuro).
- `site/public/data/explorer/{ano}.json`: agregado por ação × GND, com dicionários código → nome. O site faz o agrupamento no navegador.
- `site/public/data/explorer/anos.json`: totais por ano.
- `site/public/data/cidades/municipios.json`: um registro por município (e o DF) com o gasto por função e subfunção do último ano entregue, a série histórica e a mediana per capita por faixa de população. Gera `/cidades` e `/cidades/{uf}/{cidade}`.
- `site/public/data/cidades/estados.json`: o mesmo para os 26 estados e o DF, com a mediana dos estados. Gera `/estados` e `/estados/{uf}`.
- `site/public/data/mapa/`: dados da página `/mapa` (ver `pipeline/src/orcamento_pipeline/mapa.py` e `federal.py`): um arquivo por ano com despesa, receita, origem da receita e tributos de cada município e estado; áreas de gasto; série histórica; fatores do IPCA; arrecadação federal por estado; dinheiro federal por município; malhas. As páginas de cidade e de estado leem daqui, no build, a receita, o saldo do ano e os benefícios do INSS (`site/src/lib/contas.ts`); sem esses arquivos, essas seções não aparecem.

## Mapa (protótipo)

`/mapa` responde, para cada cidade e estado e por ano: o que se paga de imposto à prefeitura, quanto ela recebe e gasta, se sobrou ou faltou, de onde vem o dinheiro e o que chega do governo federal. A página é um documento independente do layout do site (`site/src/mapa/pagina.html`, servido por `site/src/pages/mapa.astro`).

Três coisas são **estimativas** e aparecem marcadas como tal: o IPVA pago na cidade (o dobro da cota que o estado devolve à prefeitura), o ICMS atribuído a ela (quatro vezes a cota-parte) e os impostos federais (o total arrecadado no estado, repartido pelo peso da cidade no ICMS). O imposto é registrado onde é recolhido, não onde mora quem paga.
