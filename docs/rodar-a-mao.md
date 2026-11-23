# O que rodar à mão

Este documento lista as cargas de dados que nenhum workflow do GitHub roda sozinho. A publicação diária
(`publicar.yml`, que chama `.github/scripts/dados.sh`) só copia o resultado delas, guardado em
`pipeline/referencia/`. Se ninguém rodar, o site continua no ar, mas com os números da última carga.

Elas ficam fora do GitHub por um destes motivos: a fonte pede captcha, só responde a endereços do Brasil (o robô
do GitHub roda fora do país) ou o download é grande demais.

No fim há também a lista do que já roda sozinho, para ficar claro o que não precisa lembrar.

Todos os comandos rodam da raiz do repositório.

## Resumo

| O quê | Quando | Comando |
| --- | --- | --- |
| [Acima do teto: Executivo federal](#acima-do-teto-executivo-federal) | todo mês | `uv run --project pipeline supersalarios-federal` |
| [Dívida ativa da União](#dívida-ativa-da-união) | a cada 3 meses | `uv run --project pipeline divida-ativa` |
| [Benefícios fiscais por empresa](#benefícios-fiscais-por-empresa) | a cada 6 meses | `uv run --project pipeline beneficios-fiscais` |
| [Explorador de emendas](#explorador-de-emendas) | sem data definida | `uv run --project pipeline explorador-emendas` |
| [Receitas da União](#receitas-da-união) | sem data definida | `uv run --project pipeline receitas-uniao` |
| [Pagamentos das prefeituras](#pagamentos-das-prefeituras-12-estados) | uma vez por ano | `uv run --project pipeline pagamentos --uf XX` |
| [Bolsa Família e BPC](#bolsa-família-e-bpc) | uma vez por ano | `uv run --project pipeline federal 2025 --beneficios ~/Downloads` |
| [Folha estadual do PR e de SC](#folha-estadual-do-pr-e-de-sc) | uma vez por ano | `uv run --project pipeline estado-pr 2025` e `estado-sc 2025` |
| [Postos e hospitais](#postos-e-hospitais) | uma vez por ano | `uv run --project pipeline unidades-saude` |
| [Caminho dos impostos](#caminho-dos-impostos) | uma vez por ano | `uv run --project pipeline caminho-impostos` |
| [Políticos: a parte das eleições](#políticos-a-parte-das-eleições-pr-142) | depois de cada eleição | `uv run --project pipeline politicos --tse` |
| [Histórico do FINBRA](#histórico-do-finbra) | raramente | `uv run --project pipeline finbra ~/Downloads/finbra` |
| [Enviar ao bucket](#enviar-ao-bucket-espelho) | depois das cargas que gravam Parquet | `uv run --project pipeline espelho --sem-brutos` |

Quase toda carga termina igual: conferir os números, fazer commit da cópia em `pipeline/referencia/` e abrir um
PR. A publicação seguinte põe no ar.

### Regras para quem roda (pessoa ou Claude)

- **Captcha:** quem resolve é o Guilherme, no navegador. Um Claude para, avisa e diz qual página abrir. Ninguém
  contorna o captcha (troca de endereço, de navegador falso etc.).
- **"Só responde do Brasil":** rodar de uma máquina no Brasil. A máquina de casa que já roda o CE, o AL e o PI (ver
  `.github/scripts/fora-do-github/`) serve. Não usar proxy.
- **Bucket B2:** enviar ao bucket público (`uv run espelho`) é publicar. Um Claude pede o OK do Guilherme antes.
- **Disco:** algumas cargas baixam vários GB. A maioria lê o arquivo e apaga em seguida, mas precisa de espaço livre
  durante a leitura.

---

## Acima do teto: Executivo federal

```bash
uv run --project pipeline supersalarios-federal
```

- **O que baixa:** a folha dos servidores civis (SIAPE, ~80 MB por mês) e os honorários e jetons, do Portal da
  Transparência (CGU). Guarda só as somas por órgão; os zips são apagados.
- **Quando:** uma vez por mês. O dia não está definido. Os outros "acima do teto" rodam sozinhos entre os dias 20 e 25.
- **Cuidados:** depois de alguns downloads seguidos, o Portal pede captcha. Aí o comando para e monta a saída com os
  meses que já tem. Rodar de novo outro dia completa o resto. Só baixa os meses que faltam.
- **Depois:** commit de `pipeline/referencia/supersalarios-federal.json`.

## Dívida ativa da União

```bash
uv run --project pipeline divida-ativa
```

- **O que baixa:** a dívida ativa da PGFN do último trimestre (~1,5 GB) e o cadastro de CNPJ da Receita (~6,7 GB),
  para achar a cidade de cada empresa. Cada arquivo é lido e apagado.
- **Quando:** uma vez por trimestre, quando a PGFN publica o trimestre novo. Para escolher o trimestre e o mês do
  cadastro: `--trimestre 2026_trimestre_03 --receita 2026-11`.
- **Cuidados:** a PGFN às vezes só responde do Brasil. Se falhar de fora, rodar de uma máquina no Brasil.
- **Depois:** commit de `pipeline/referencia/divida-ativa.json`.

## Benefícios fiscais por empresa

```bash
uv run --project pipeline beneficios-fiscais
```

- **O que baixa:** a Dirbi da Receita (~1,6 GB por três anos) e o cadastro de CNPJ (~1,3 GB). Cruza com a dívida
  ativa e, se existirem no computador, com os Parquet dos contratos e das emendas.
- **Quando:** a cada atualização semestral da Dirbi (duas vezes por ano). Rodar depois da
  [dívida ativa](#dívida-ativa-da-união), com o mesmo trimestre: ela usa os zips da PGFN.
- **Cuidados:** grava dois Parquet em `data/publico/`, que a página `/impostos/empresas` lê do bucket.
- **Depois:** commit de `pipeline/referencia/beneficios-fiscais.json` e [enviar ao bucket](#enviar-ao-bucket-espelho)
  (pede o OK do Guilherme).

## Explorador de emendas

```bash
uv run --project pipeline emendas
uv run --project pipeline explorador-emendas
```

- **O que baixa:** o primeiro comando baixa o arquivo "Emendas Parlamentares" da CGU. O segundo lê esse arquivo e
  monta os Parquet da página `/emendas` (pagamentos e textos) e as fichas prontas da busca.
- **Quando:** não tem data definida. A CGU atualiza as emendas ao longo do ano, e a busca de `/emendas` fica parada na
  última carga até alguém rodar. A página de cada político (PR #142) também lê esse Parquet do bucket.
- **Cuidados:** os Parquet vão para `data/publico/` e precisam ir para o bucket.
- **Depois:** commit de `pipeline/referencia/emendas-explorador-resumo.json` e
  [enviar ao bucket](#enviar-ao-bucket-espelho) (pede o OK do Guilherme).

## Receitas da União

```bash
uv run --project pipeline receitas-uniao
```

- **O que baixa:** o arquivo "Receitas" do Portal da Transparência, um zip por ano (~25 MB no total). Só baixa o que
  falta; `--forcar` baixa tudo de novo.
- **Quando:** não tem data definida. O ano em andamento fica parado na última carga até alguém rodar.
- **Depois:** commit de `pipeline/referencia/receitas-uniao.json`.

## Pagamentos das prefeituras (12 estados)

Para quem cada prefeitura pagou, pelos dados dos tribunais de contas. Um comando por estado:

```bash
uv run --project pipeline pagamentos            # Paraíba (TCE-PB)
uv run --project pipeline pagamentos --uf AC
uv run --project pipeline pagamentos --uf AM
uv run --project pipeline pagamentos --uf CE
uv run --project pipeline pagamentos --uf ES
uv run --project pipeline pagamentos --uf MG
uv run --project pipeline pagamentos --uf PE
uv run --project pipeline pagamentos --uf PR
uv run --project pipeline pagamentos --uf RS
uv run --project pipeline pagamentos --uf SC
uv run --project pipeline pagamentos --uf SP
uv run --project pipeline pagamentos --uf TO
```

| Estado | O que baixa | Do Brasil? | Observação |
| --- | --- | --- | --- |
| PB | ZIP do TCE-PB, ~190 MB | não precisa | |
| AC | painel do TCE-AC | **sim** | |
| SC | painel do TCE-SC | **sim** | horas (~3 milhões de empenhos) |
| PE | API do TCE-PE | **sim** | ~2 horas |
| SP | TCE-SP (2,1 GB) e TCM-SP (180 MB) | **sim** | |
| RS | ZIP do TCE-RS, 1,35 GB (14,7 GB por dentro) | **sim** | |
| AM | API do TCE-AM | não conferido | ~20 min; feito do Brasil |
| TO | planilhas do TCE-TO | não conferido | ~30 min; feito do Brasil |
| CE | API do TCE-CE | não conferido | algumas horas; feito do Brasil |
| ES | arquivos do TCE-ES, ~145 MB | não conferido | feito do Brasil |
| PR | pacote do TCE-PR, 1,4 GB | não conferido | sem captcha |
| MG | pacote "Empenhos" do TCE-MG, ~585 MB | — | **download à mão no navegador** (ver abaixo) |

- **MG:** o site do TCE-MG faz uma verificação anti-robô e não deixa baixar por programa. O Guilherme abre
  `dadosabertos.tce.mg.gov.br` → Jurisdicionado → Downloads, escolhe o ano e baixa "Empenhos". O arquivo sai como
  `{ano}-empenho.zip`; pode ficar em `~/Downloads` ou em `data/raw/tce-mg/`. Depois, `pagamentos --uf MG` lê o arquivo.
- **Quando:** uma vez por ano, para o ano fechado. O ano padrão é 2025; para outro, `--ano 2026`. Não está definido
  se vale rodar de novo no meio do ano para pegar correções dos tribunais.
- **Depois:** commit de `pipeline/referencia/pagamentos*.json` (um arquivo por estado; a PB é `pagamentos.json`).

## Bolsa Família e BPC

```bash
uv run --project pipeline federal 2025 --beneficios ~/Downloads
```

- **O que baixa:** nada. Os zips do Novo Bolsa Família e do BPC (um por mês, ~6,5 GB por ano) são baixados à mão no
  Portal da Transparência (página de download de dados), porque o Portal pede captcha em downloads seguidos. O comando
  lê os zips da pasta e guarda só a soma por cidade.
- **Quando:** uma vez por ano, quando o ano fecha. Hoje só tem 2025. Para 2026, baixar os 12 meses de cada um e trocar
  o ano no comando.
- **Cuidados:** quem baixa é o Guilherme, no navegador (captcha).
- **Depois:** commit de `pipeline/referencia/beneficios/*.csv`. A publicação diária roda `federal 2025` e lê essas
  somas.

## Folha estadual do PR e de SC

```bash
uv run --project pipeline estado-pr 2025
uv run --project pipeline estado-sc 2025
```

- **O que baixa:** a folha de pagamento do governo estadual, mês a mês. PR: ~32 MB de cadastro mais ~12 MB por mês.
  SC: ~22 MB por mês, e cada mês leva uns 45 segundos para sair do portal.
- **Quando:** uma vez por ano, para o ano fechado. 2025 já está feito e não muda.
- **Cuidados:** o servidor do PR para de responder por alguns minutos depois de alguns downloads. O comando espera e
  tenta de novo.
- **Depois:** commit de `pipeline/referencia/estado-pr.json` e `estado-sc.json`. Num ano novo, trocar também o ano
  em `.github/scripts/dados.sh`.

## Postos e hospitais

```bash
uv run --project pipeline unidades-saude
```

- **O que baixa:** do Ministério da Saúde: CNES, SIH (~1,1 GB), SIA (~28 GB por ano, lido na memória, sem ficar no
  disco), SISAB, vacinas do SI-PNI (~1,6 GB por mês) e a cobertura da atenção primária. É a carga mais pesada.
- **Quando:** uma vez por ano. O ano padrão é o último fechado. Os dados do DATASUS chegam com meses de atraso, então
  não há uma data certa. Para refazer só a atenção básica: `--so-atencao-basica`.
- **Depois:** commit de `pipeline/referencia/unidades-saude.json`.

## Caminho dos impostos

```bash
uv run --project pipeline semente aplicar
uv run --project pipeline caminho-impostos
```

- **O que baixa:** pouco. Usa o cache das contas anuais (DCA) de estados e prefeituras, que vem do
  `semente aplicar`, e a planilha do Resultado do Tesouro.
- **Quando:** uma vez por ano, depois que estados e prefeituras entregam a DCA do ano (as prefeituras até 30 de
  abril, os estados até 31 de maio). O ano está fixo em 2025 no código; para outro, `--ano 2026`.
- **Depois:** commit de `pipeline/referencia/caminho-impostos.json`.

## Políticos: a parte das eleições (PR #142)

> Ainda não está na `main`: vem com o PR #142 (página de cada político), em rascunho.

```bash
uv run --project pipeline politicos --tse
```

- **O que baixa:** os dados abertos do TSE de 2018 e 2022 (candidaturas, bens, receitas de campanha e votos), uns 2 GB.
- **Quando:** depois de uma eleição nova, ou quando um suplente novo assume o mandato. O resto (cota, gabinete,
  assessores, emendas) roda sozinho no workflow `politicos.yml`, todo dia 5.
- **Atenção, eleição de 2026:** o código lê só 2018 e 2022 e a legislatura 57 (2023 a 2027). Para a legislatura que
  começa em fevereiro de 2027, o código precisa mudar antes de rodar o `--tse`.
- **Depois:** commit de `pipeline/referencia/politicos.json`. O workflow do dia 5 tira a parte do TSE dessa cópia.
  (Isso vale enquanto o release `dados-politicos` não tiver um `tse.json`; se tiver, ele tem prioridade.)
- **Natureza jurídica dos fornecedores (`--natureza`, ~1,3 GB da Receita):** não roda à mão. O workflow já roda
  em janeiro, abril, julho e outubro. Fora disso, dá para pedir no botão "Run workflow" do `politicos.yml`, com a
  opção marcada. Se a Receita falhar, a carga segue com o cache.

## Histórico do FINBRA

```bash
uv run --project pipeline finbra ~/Downloads/finbra
uv run --project pipeline semente publicar
```

- **O que baixa:** nada. Os arquivos do FINBRA (contas anuais de todas as prefeituras, por ano e anexo) são baixados à
  mão em `siconfi.tesouro.gov.br` (consulta FINBRA), porque o site tem captcha. O comando lê os arquivos da pasta.
- **Quando:** raramente. Só para trazer anos antigos ou refazer o cache. Os anos recentes já vêm da API do SICONFI,
  sozinhos.
- **Cuidados:** quem baixa é o Guilherme, no navegador (captcha). O `semente publicar` envia o cache para o release
  `dados-siconfi` do GitHub; dá para mandar só os anexos que mudaram (`semente publicar dca-id dca-iab`).
- **Depois:** nada no git. A publicação pega o cache do release.

## Enviar ao bucket (espelho)

```bash
uv run --project pipeline espelho --sem-brutos
```

- **O que faz:** envia ao bucket público do Backblaze B2 os Parquet de `data/publico/`, os JSONs do site e as cópias
  de referência. Só manda o que mudou de tamanho; nada é apagado lá.
- **Quando:** depois do [explorador de emendas](#explorador-de-emendas) e dos
  [benefícios fiscais](#benefícios-fiscais-por-empresa). A publicação diária também roda o espelho, mas o computador
  do GitHub não tem esses Parquet.
- **Cuidados:**
  - é publicar: um Claude pede o OK do Guilherme antes;
  - precisa da chave do B2 no computador (`b2 account authorize`);
  - use `--sem-brutos` no seu computador. Sem ele, o comando envia **toda** a pasta `data/raw` local, que pode ter
    arquivos baixados à mão que não deveriam ser públicos.
- **Depois:** limpar o cache da Cloudflare. Os nomes dos Parquet são fixos e a borda guarda cada um por 30 dias; sem a
  limpeza, a busca pode ler pedaços do arquivo velho misturados com o novo. O jeito simples: rodar o workflow
  "Publicar" na `main` (botão "Run workflow"), que limpa o cache no fim. A limpeza só roda se os segredos
  `CF_PURGE_TOKEN` e `CF_ZONE_ID` estiverem gravados.

---

## Cópias de reserva

Algumas fontes rodam todo dia na publicação, mas, se falharem, o site usa uma cópia guardada em
`pipeline/referencia/`. Essa cópia não se atualiza sozinha. Não tem data certa: vale renovar de vez em quando,
rodando o comando no computador e fazendo commit.

- Estes comandos já regravam a própria cópia ao rodar: `divida-federal`, `contas-federal`, `ideb`, `escolas`,
  `matriculas`, `saneamento`, `previdencia`, `gasto-federal 2025`, `saude`, `seguranca`, `populacao`.
- Estes não regravam: CAPAG, emendas, imposto de renda por cidade e gasto de MG. Depois de rodar `capag`, `emendas`,
  `irpf` ou `estado-mg 2025`, copie o resultado à mão:

```bash
cp site/public/data/indicadores/capag.json pipeline/referencia/capag.json
cp site/public/data/indicadores/emendas.json pipeline/referencia/emendas.json
cp site/public/data/mapa/irpf-res.json pipeline/referencia/irpf-res.json
cp site/public/data/estados/mg/2025.json pipeline/referencia/estado-mg-2025.json
```

## Quando o ano vira

Vários comandos têm o ano 2025 escrito. Quando o ano de 2026 fechar, além das cargas anuais acima, trocar o ano em:

- `.github/scripts/dados.sh`: `estado-pb`, `estado-mg`, `estado-pr`, `estado-sc`, `gasto-federal`, `fluxo` e
  `federal` (no `publicar.yml`, quem chama é o `dados.sh`);
- `pipeline/src/orcamento_pipeline/pagamentos.py` (ano padrão do `--ano`);
- `pipeline/src/orcamento_pipeline/caminho_impostos.py` (`ANO`).

Esta lista saiu de uma leitura do código em 23/11/2026; pode faltar algum.

---

## O que já roda sozinho

Não precisa lembrar destes. Os que abrem um PR em rascunho só pedem para você conferir e mesclar.

| Workflow | Quando | O que faz | O que você faz |
| --- | --- | --- | --- |
| `publicar.yml` | todo dia, 6h de Brasília, e a cada push na `main` | roda o `dados.sh`, gera e publica o site, envia ao bucket e limpa o cache | nada |
| `bimestral.yml` | dias 1 e 31, e toda segunda | relatório bimestral (RREO) das prefeituras, no release `dados-siconfi` | nada |
| `rgf-prefeituras.yml` | toda segunda de março a julho; dia 1 nos outros meses | dívida e gasto com pessoal das prefeituras, no release `dados-siconfi` | nada |
| `contratos.yml` | toda segunda de janeiro a abril | contratos do PNCP do último ano fechado; envia os Parquet ao bucket | conferir e mesclar o PR |
| `supersalarios.yml` | dia 20 | juízes e promotores acima do teto (DadosJusBr) | conferir e mesclar o PR |
| `supersalarios-legislativo.yml` | dia 22 | Câmara, Senado e TCU acima do teto | conferir e mesclar o PR |
| `supersalarios-municipios.yml` | dia 23 | prefeituras da Paraíba acima do teto (TCE-PB) | conferir e mesclar o PR |
| `supersalarios-estados.yml` | dia 25 | Executivo de cada estado acima do teto | conferir e mesclar o PR |
| `politicos.yml` (PR #142) | dia 5 | cota, gabinete, assessores e emendas dos parlamentares; natureza jurídica em jan, abr, jul e out | conferir e mesclar o PR |
| `testar-fontes.yml` | só pelo botão | testa se as fontes das cargas à mão respondem de fora do Brasil | nada |

Fora do GitHub, mas também sozinho: no dia 24, a máquina de casa baixa a folha do CE, do AL e do PI, que recusam o
GitHub (timer `supersalarios-ce-al-pi`, cópia em `.github/scripts/fora-do-github/`). Se a máquina estiver desligada
no dia, o timer roda quando ela voltar. O workflow do dia 25 junta esses estados aos outros.
