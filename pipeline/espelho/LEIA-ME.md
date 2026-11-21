# Dados do Orçamento Brasileiro

Cópia pública de tudo o que o site [orcamentobrasileiro.com.br](https://orcamentobrasileiro.com.br) usa: os arquivos baixados das fontes oficiais, do jeito que vieram, e os arquivos já tratados que alimentam as páginas e o mapa. Serve para conferir qualquer número do site e refazer as contas.

Tudo aqui é cópia de dados abertos publicados pelo governo. **A fonte oficial manda**: se um órgão corrigir ou retirar um registro, a versão dele é a que vale. Cada arquivo guarda a data em que foi baixado (a data de modificação no bucket). Ao usar, cite a fonte original e, se quiser, o Orçamento Brasileiro.

O código que baixa e trata tudo está em [github.com/guilhermeprokisch/orcamento-brasileiro](https://github.com/guilhermeprokisch/orcamento-brasileiro), na pasta `pipeline/`.

## Como baixar

O bucket não deixa listar os arquivos sem uma chave, então há dois índices na raiz:

- **`indice.csv`**: o caminho, o tamanho e a data de envio de cada arquivo;
- **`indice.txt`**: o endereço de cada arquivo, um por linha.

Para baixar tudo (cerca de 3,5 GB), mantendo as pastas:

```bash
curl -s https://dados.orcamentobrasileiro.com.br/file/orcamento-brasileiro-dados/indice.txt | wget -x -nH --cut-dirs=2 -i -
```

Para baixar só o que o site usa, filtre as linhas de `tratados/` antes de passar para o `wget`.

## Pastas

- **`brutos/`** — os arquivos das fontes, sem mudança, ou as respostas das APIs guardadas como vieram (em `.json.gz`).
- **`tratados/`** — os JSONs que o site lê (a pasta `site/public/data` do repositório).
- **`referencia/`** — resumos das cargas que levam horas (dívida e pessoal das prefeituras, contratos, saúde…), versionados no repositório.

## De onde vem cada coisa (`brutos/`)

| Pasta | Fonte | O que é |
| --- | --- | --- |
| `siconfi/` | Tesouro Nacional, [SICONFI](https://siconfi.tesouro.gov.br) | Contas anuais (DCA) e relatórios fiscais (RGF, RREO) de estados e prefeituras, uma resposta da API por ente |
| `tesouro/` | Tesouro Nacional | Nota de capacidade de pagamento (CAPAG) e a tabela de municípios |
| `orcamento-despesa/` | CGU, [Portal da Transparência](https://portaldatransparencia.gov.br/download-de-dados) | Orçamento da despesa federal por ano |
| `portal-transparencia/` | CGU, Portal da Transparência | Transferências federais a municípios |
| `cgu/` | CGU, Portal da Transparência | Emendas parlamentares (pagamentos por favorecido) |
| `siop/` | Ministério do Planejamento, SIOP | Nomes de órgãos e programas do orçamento federal |
| `receita-federal/` | Receita Federal | Arrecadação federal por estado e município; Grandes Números do IRPF |
| `previdencia/` | Ministério da Previdência Social | Benefícios do INSS pagos por município |
| `pncp/` | [Portal Nacional de Contratações Públicas](https://pncp.gov.br) | Contratos publicados, um arquivo por dia de publicação, só prefeituras, câmaras e órgãos estaduais |
| `datasus/` | Ministério da Saúde, [OpenDataSUS](https://opendatasus.saude.gov.br) | Mortalidade (SIM) e nascidos vivos (SINASC), registro a registro, sem identificação |
| `inep/` | INEP | Ideb por município e rede; Sinopse do Censo Escolar |
| `ibge/` | IBGE | Malhas dos municípios e estados |
| `ipca/` | IBGE, SIDRA (tabela 1737) | IPCA, para corrigir pela inflação |
| `estados/` | Portais de transparência estaduais (MG, PB) | Dados de estados que publicam mais do que o Tesouro recebe |

Os contratos do PNCP trazem o nome do fornecedor como o portal publica, inclusive pessoas físicas e microempreendedores. No site esses nomes não aparecem; aqui ficam porque é a cópia fiel da fonte.
