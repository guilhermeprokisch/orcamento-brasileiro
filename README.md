# Orçamento Brasileiro

De onde vem e para onde vai o dinheiro público da sua cidade, do seu estado e do país: impostos, repasses, gastos, dívidas e o que eles produzem.

**Site:** [orcamentobrasileiro.com.br](https://orcamentobrasileiro.com.br) · **Dados abertos:** [orcamentobrasileiro.com.br/dados](https://orcamentobrasileiro.com.br/dados)

Projeto independente, sem vínculo com o governo.

## O que tem no site

- **Cidades e estados** (`/cidades/{uf}/{cidade}`, `/estados/{uf}`): uma página para cada prefeitura e governo estadual, em quatro partes:
  1. *Em que gasta*: o gasto por área e por tipo (salários, serviços, obras), os contratos publicados no PNCP;
  2. *As contas fecham*: de onde vem o dinheiro, o que sobrou, a dívida e o gasto com pessoal frente aos limites da Lei de Responsabilidade Fiscal, a nota do Tesouro (CAPAG), o ano em andamento;
  3. *O que chega e o que sai*: aposentadorias do INSS, imposto de renda dos moradores, emendas parlamentares, o gasto do estado na cidade;
  4. *Como está a cidade*: educação (Ideb), mortalidade infantil, homicídios, água e esgoto, sempre ao lado do gasto na área.
- **Contratos** (`/contratos`): busca nos contratos publicados no PNCP, por lugar, empresa ou palavra, consultando no navegador (DuckDB) um Parquet guardado no bucket público.
- **Mapa** (`/mapa`): compara todas as cidades ou estados numa pergunta por vez (gasto, receita, saldo, dependência de repasses, dinheiro federal, emendas, impostos, situação), com as linhas de dinheiro saindo de Brasília. É um documento independente do layout do site (`site/src/mapa/pagina.html`).
- **Explorer, Órgãos, Aprenda e Glossário**: o orçamento federal por órgão, programa e ação, de 2014 em diante, e as explicações.

## Os dados

Tudo vem de dados abertos oficiais. Os arquivos das fontes, como vieram, e os JSONs que o site usa ficam numa cópia pública no Backblaze B2 ([LEIA-ME](https://f005.backblazeb2.com/file/orcamento-brasileiro-dados/LEIA-ME.md), [índice](https://f005.backblazeb2.com/file/orcamento-brasileiro-dados/indice.csv)), atualizada a cada publicação.

| Fonte | O que vem dela | Comando |
|---|---|---|
| Portal da Transparência (CGU) | Orçamento da despesa federal; transferências, Bolsa Família e BPC por município; emendas parlamentares | `orcamento`, `federal`, `emendas` |
| SIOP (Planejamento) | Nomes oficiais de órgãos, programas e ações | `orcamento` |
| SICONFI (Tesouro) | Contas anuais (DCA) de estados e prefeituras; relatórios fiscais (RGF: dívida e pessoal; RREO: o ano em andamento) | `cidades`, `mapa`, `divida`, `rreo` |
| FINBRA (Tesouro) | Histórico das prefeituras desde 2013 (baixado à mão por causa do captcha) | `finbra`, `semente` |
| Tesouro Nacional | Nota CAPAG; tabela de municípios do SIAFI | `capag` |
| PNCP | Contratos publicados por prefeituras, estados e União; o explorador `/contratos` | `contratos`, `explorador-contratos` |
| Receita Federal | Arrecadação por estado e município; IR por município de residência | `rfb`, `irpf` |
| Previdência Social | Benefícios do INSS pagos em cada município | `inss` |
| DATASUS | Mortalidade (SIM) e nascidos vivos (SINASC) | `saude`, `seguranca` |
| INEP | Ideb; matrículas do Censo Escolar | `ideb`, `matriculas` |
| IBGE | População, Censo 2022 (água e esgoto), IPCA, malhas | `populacao`, `saneamento`, `mapa` |
| Governos de MG e PB | Gasto estadual por município | `estado-mg`, `estado-pb` |

Cada comando é um arquivo em `pipeline/src/orcamento_pipeline/`, com a explicação da fonte, das escolhas e dos cuidados no começo.

Algumas coisas são **estimativas** e aparecem marcadas como tal no site: o ICMS e o IPVA pagos em cada cidade (a partir das cotas que o estado devolve) e, quando falta o dado da Receita, os impostos federais. Valores que as prefeituras declaram com erro evidente (receita de parte do ano, contratos maiores que o orçamento) ficam de fora e são avisados.

## Rodando

Requer [uv](https://docs.astral.sh/uv/) e Node 22+.

```bash
cd pipeline
uv run orcamento            # orçamento federal (Explorer), 2014 até o ano corrente
uv run semente aplicar      # traz o cache do SICONFI do release "dados-siconfi" (precisa do gh); sem ele, ~3h de consultas
uv run cidades              # estados e prefeituras
uv run mapa                 # dados do mapa
uv run <comando>            # os demais, da tabela acima

cd ../site && npm install && npm run dev
```

Algumas cargas levam horas (a API do SICONFI aceita uma consulta por segundo; o PNCP limita os pedidos): a dívida e o pessoal das prefeituras, os contratos e o histórico do FINBRA. O resultado delas fica em `pipeline/referencia/`, e a publicação automática só copia de lá.

## Publicação

- **`.github/workflows/publicar.yml`**: a cada mudança na `main`, roda os pipelines (com o cache de `data/raw` e o release `dados-siconfi`), confere os tipos, gera o site, publica no Cloudflare Pages e atualiza a cópia pública dos dados no B2 (`uv run espelho`).
- **`.github/workflows/bimestral.yml`**: baixa o relatório bimestral das prefeituras para o ano em andamento.

## Estrutura

```
pipeline/   Python: baixa, confere e trata os dados (um comando por fonte)
site/       Astro: as páginas, geradas no build a partir de site/public/data
data/       (fora do git) os arquivos brutos e o Parquet do orçamento federal
docs/       plano de melhorias, levantamentos e pedidos pela Lei de Acesso
```

O que está em andamento e o que vem depois: [docs/plano-de-melhorias.md](docs/plano-de-melhorias.md).

## Licença

O código deste repositório está sob a licença MIT (ver [LICENSE](LICENSE)). Contribuições são bem-vindas.

Os dados vêm de fontes públicas oficiais e seguem as licenças de cada fonte; a de Minas Gerais, por exemplo, é CC-BY 4.0.
