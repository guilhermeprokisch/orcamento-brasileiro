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

# 1b. estados e cidades (SICONFI): ~3h na primeira vez (1 consulta/s), depois usa o cache
uv run cidades

# 1c. opcional: histórico dos municípios e receitas a partir dos arquivos do FINBRA
#     (baixados à mão; ver pipeline/src/orcamento_pipeline/finbra.py)
uv run finbra ~/Downloads/finbra

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
| SICONFI (Tesouro Nacional) | [FINBRA](https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf), Anexos I-E e I-C | Histórico dos municípios (2013+) e receitas, um arquivo por ano com todos os municípios. O download tem captcha: os arquivos são baixados à mão e importados com `uv run finbra` |

Saídas do pipeline:

- `data/out/orcamento_despesa.parquet`: todos os anos, nível de elemento de despesa (para o DuckDB-WASM no futuro).
- `site/public/data/explorer/{ano}.json`: agregado por ação × GND, com dicionários código → nome. O site faz o agrupamento no navegador.
- `site/public/data/explorer/anos.json`: totais por ano.
- `site/public/data/cidades/municipios.json`: um registro por município (e o DF) com o gasto por função e subfunção do último ano entregue, a série histórica e a mediana per capita por faixa de população. Gera `/cidades` e `/cidades/{uf}/{cidade}`.
- `site/public/data/cidades/estados.json`: o mesmo para os 26 estados e o DF, com a mediana dos estados. Gera `/estados` e `/estados/{uf}`.
