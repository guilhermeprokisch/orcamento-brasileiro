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

Saídas do pipeline:

- `data/out/orcamento_despesa.parquet`: todos os anos, nível de elemento de despesa (para o DuckDB-WASM no futuro).
- `site/public/data/explorer/{ano}.json`: agregado por ação × GND, com dicionários código → nome. O site faz o agrupamento no navegador.
- `site/public/data/explorer/anos.json`: totais por ano.
