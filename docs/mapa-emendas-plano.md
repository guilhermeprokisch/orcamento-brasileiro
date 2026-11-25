# Emendas no mapa: do protótipo ao /mapa/

Plano para levar ao Mapa do Orçamento o que o protótipo `/prototipo-emendas/` (novembro de 2026)
ajudou a decidir: bolhas por município, retratos dos parlamentares em chamadas laterais, e o clique
na cidade abrindo as emendas dela uma a uma. Os mocks aprovados estão no Claude Design
([Emendas no mapa · retratos](https://claude.ai/artifact/Auz3EuvihDK29zXWKuCfn5)): artboard **A**
(chamadas) e **D** (clicou na bolha).

**Decisão de 24/11/2026:** antes de qualquer coisa disto, o protótipo entra no site **como está**, como um
mapa próprio da seção de emendas (`/emendas/mapa/`, quarta aba), com os dados gerados por `uv run
emendas-mapa` e servidos pelo bucket. O `/mapa/` não muda. Misturar os dois é para depois, com mock e
calma — é o que este plano descreve.

Regra de ouro: o `/mapa/` de produção é a referência. Cada etapa é um ajuste pequeno sobre ele, num PR
próprio, e só a etapa seguinte começa depois que a anterior estiver no ar. Onde o desenho muda, o mock
vem antes do código.

## O que o site já tem (e o protótipo refez sem precisar)

| No site hoje | Onde | O que o protótipo fazia por fora |
|---|---|---|
| A pergunta **Emendas parlamentares** no mapa: coropleta por morador (ou total), do último ano fechado, com as linhas de dinheiro saindo de Brasília para cada estado ou cidade | `site/src/mapa/pagina.html`, medida `emd`; `COM_FLUXO` | O mapa inteiro |
| O cartão da cidade com "Emendas parlamentares": total, para quem (prefeitura / entidades / estado), **quem mandou mais**, mediana das cidades de porte parecido, link para a página da cidade | `detalhe(id)` | O cartão de hover |
| `indicadores/emendas.json` (4 MB, só no build): por município e estado, **todos os anos** desde 2016, com total, prefeitura, entidades, estado; os 5 maiores autores e as 3 maiores áreas dos dois últimos anos | `pipeline/…/emendas.py` → `lib/indicadores.ts` `emendasParaMapa()` → `/data/mapa/emendas.json` (só o último ano vai ao navegador) | `prototipo-emendas.json` |
| A **ficha de cada município**: por ano, resumo, autores, favorecidos, áreas e a lista de emendas; 5.593 arquivos, servidos em `explorador/fichas/<versão>/lugar/<ibge>.json` pela Cloudflare | `pipeline/…/fichas_emendas.py`; é o que `/emendas/buscar?ente=<ibge>` lê | `prototipo-mun/<ibge>.json` (67 MB) |
| Nomes legíveis de autores, bancadas e comissões | `lib/autores-emendas.ts` (o mapa tem cópia; mudou um, muda o outro) | — |
| População por município e ano | `/data/mapa/anos/<ano>.json` | Carregava o mesmo arquivo |
| Página da cidade com a seção `#emendas`; buscador com filtro por lugar e por autor | `/cidades/<uf>/<cidade>/#emendas`, `/emendas/buscar?ente=…`, `?autor=…` | Links para eles |

## O que falta de verdade

1. **Série por tipo de emenda** (individual, bancada, relator, comissão, Pix) por município e ano. Hoje
   o `emendas.json` não reparte por tipo. É uma coluna a mais no `emendas.py`.
2. **Os maiores parlamentares (pessoas) por município**, separados dos colegiados. O `autores` de hoje
   mistura relator, comissão e bancada com gente — e em 137 dos 160 maiores municípios o maior autor é
   um colegiado. Para retratos, precisa dos três maiores *parlamentares* por município e ano.
3. **Retratos**: foto, casa, partido e UF de cada parlamentar. Não existe no pipeline. Vem das APIs
   abertas da Câmara (`dadosabertos.camara.leg.br`, legislaturas 55–57) e do Senado
   (`legis.senado.leg.br`), casadas por nome normalizado (sem acento, sem "Dep./Sen.", nome de urna e
   nome civil). No protótipo casaram 1.293 de 1.478 autores-pessoa, 96% do valor; os que faltam são
   suplentes e gente de antes de 2015. As fotos têm de ser **espelhadas** (bucket, `tratados/fotos/`),
   nunca servidas direto da Câmara.
4. **Série anual no navegador.** Hoje só o último ano fechado chega ao mapa. Bolhas por ano pedem a
   série inteira, mas o `emendas.json` de 4 MB não pode ir como está: um arquivo novo, enxuto, carregado
   só quando a pergunta é "Emendas".
5. **O que a emenda é.** Hoje a única descrição é o "objeto" dos textos do TransfereGov, que nem toda
   emenda tem. O CSV da CGU traz, por emenda, função, subfunção, programa, ação e plano orçamentário
   ("Estruturação de unidades de atenção especializada em saúde", por exemplo): entram no `emendas.py` e
   na ficha por emenda. O número da emenda deve ser sempre um link para a ficha no buscador
   (`/emendas/buscar?emenda=…`) e para o Portal da Transparência.
6. **O seletor de ano**: o protótipo começou com um slider; é um seletor, como o menu de anos da frase do
   `/mapa/`. Um slider só faz sentido para a animação ("passar os anos").
7. Conferir o **corte** da lista de emendas na ficha por lugar (a de Petrópolis em 2025 traz poucas das
   37). Se houver corte, decidir o tamanho ou paginar.

## As etapas

Cada linha é um PR. Tamanho: P (um dia), M (dois ou três), G (uma semana).

### 0. Combinar antes de começar (conversa, não código)

- **Anos**: o `/mapa/` mostra emendas do último ano fechado, para casar com as contas das prefeituras.
  As bolhas seguem o mesmo ano, com o controle de ano do mapa, ou ganham "todos os anos" como no
  protótipo? Proposta: seguem o ano do mapa (coerência), e "todos os anos" fica para a página `/emendas`.
- **Bolha × coropleta**: a pergunta "Emendas" tem duas unidades, "por morador" e "no total". Proposta:
  **"no total" vira bolhas** (é o que o total pede: onde está mais dinheiro) e "por morador" continua
  coropleta. Não se cria pergunta nova nem modo novo.
- **Brasília**: fora das bolhas, sempre, com a explicação em "Como ler" e a mesma exceção que o
  `/mapa/` já faz para o DF nas linhas. Sem controle.
- **Retratos e o cartão da cidade**: o `/mapa/` tem o cartão de detalhe à direita. As colunas de chamadas
  (A) ocupam os dois lados. Decidir: as chamadas aparecem só quando não há cidade selecionada, e o cartão
  toma o lugar da coluna da direita ao selecionar? É o que o mock D sugere.
- **Fotos**: confirmar o uso das fotos oficiais da Câmara e do Senado (são públicas, uso jornalístico), e o
  que fazer com quem não casou (monograma, como no protótipo).

### 1. Pipeline (M)

- `emendas.py`: acrescentar, por município e ano, (a) o valor por tipo de emenda e (b) os três maiores
  parlamentares-pessoa. Saída no mesmo `indicadores/emendas.json`.
- Novo comando `uv run parlamentares`: baixa Câmara e Senado, casa os nomes com os autores do
  `emendas-pagamentos.parquet`, baixa as fotos para `data/raw/parlamentares/`, e grava
  `site/public/data/indicadores/parlamentares.json` (`{nome: {foto, casa, partido, uf}}`). O espelho
  leva as fotos para o bucket; o site aponta para lá.
- `lib/indicadores.ts`: `emendasParaMapa()` passa a emitir também um `/data/mapa/emendas-serie.json`
  (município → série anual por tipo, R$ mil, só o que as bolhas usam) e os três parlamentares por
  município do ano. Medir o tamanho; alvo < 1,5 MB.

### 2. Bolhas na pergunta "Emendas" (M) — ajuste, sem mock novo

- Em `pagina.html`, quando `medida === "emd"` e `un === "total"`: em vez de pintar os polígonos, desenhar
  círculos no centróide (área ∝ valor, raiz; zoom com raiz do fator, piso clicável — como no protótipo).
  Os polígonos ficam em cinza-claro embaixo.
- Legenda de bolhas (três círculos de referência) no lugar da escala de cores.
- Brasília fora, com a nota.
- O clique na bolha faz o que o clique no polígono já faz: `selecionar(id)` e o cartão.
- Celular: igual ao desktop, sem retratos.

### 3. Retratos em chamadas (G) — mock A aprovado

- Nova camada só na pergunta "Emendas", telas ≥ 1100 px, sem cidade selecionada: oito chamadas, quatro
  de cada lado, com os parlamentares que mais mandaram para os municípios à vista; linha da borda do
  cartão ao maior município de cada um; recalcula ao fim do zoom.
- Clicar numa chamada filtra o mapa pelo parlamentar. Isso é um estado novo no mapa (`estado.autor`) e
  um item novo na frase ("de [todos os autores ▾]"), com busca. Os dados por autor
  (`prototipo-autores-mapa.json`, 3,6 MB) precisam de um formato enxuto ou de um arquivo por autor.
- A frase e a legenda explicam: "os retratos são dos 8 que mais mandaram para o que está na tela".

### 4. O clique na cidade abre as emendas (M) — mock D aprovado

- No cartão de detalhe, na pergunta "Emendas": a lista de emendas uma a uma lida da **ficha por lugar**
  que já existe (autor com retrato, objeto, favorecido, área, número, valor), com busca por texto,
  filtro por tipo e "baixar CSV". Os links para a página da cidade e para o buscador já estão lá.
- O mapa centra na cidade e esmaece as outras, como no protótipo. O número no alto passa a ser o dela.
- Se a lista da ficha for cortada, ou paginar ou aumentar o corte (item 5 acima).

### 5. Acabamento (P)

- "Como ler este mapa": os parágrafos sobre município favorecido × endereço da obra, Brasília e
  colegiados sem rosto.
- Celular: sem chamadas; o cartão da cidade com a lista vira folha por cima do mapa.
- Página `/emendas`: link para o mapa na pergunta certa.

### 6. Apagar o protótipo (P)

`site/src/pages/prototipo-emendas.astro`, `site/src/prototipo/`, `site/public/data/prototipo-*` e os
scripts que os geravam (ficaram na pasta temporária da sessão; o que vale está descrito aqui).

## Para depois: os moradores conferem

Ideia do Guilherme (24/11/2026), para quando a lista de emendas por cidade estiver no ar: a descrição
da emenda diz o que era e, muitas vezes, onde ("pavimentação de vias no perímetro urbano de Tucano",
"UPA do bairro X"). Dá para localizar isso na cidade e perguntar a quem mora lá se foi feito — uma
enquete ou uma avaliação por emenda, com foto, aberta aos moradores. É participação, não só leitura.
Depende de: descrição boa (item 5 acima), identidade mínima de quem avalia, moderação, e um lugar para
guardar as respostas. Não entra nas seis etapas; fica aqui para não se perder.

## 25/11/2026: de A para C

Com o A no ar, a leitura foi "confuso, informação demais". O mapa passou ao desenho C: de longe, os
municípios vizinhos viram um grupo (célula fixa em pixels, refeita a cada zoom), com o retrato de quem
mais mandou para eles e o número de municípios; aproximar ou clicar abre o grupo até cada município
ficar sozinho. As colunas de chamadas saíram, e com elas a única parte que não cabia no celular. O
clique na cidade (D) continua igual.

## O que o protótipo testou e foi descartado

- Rosto dentro de cada bolha (uma foto por município): vira textura, ninguém reconhece ninguém.
- Chamadas laterais (A): foram ao ar e saíram em dois dias — oito cartões, oito linhas e o mapa no meio
  é informação demais numa tela só.
- Bolha repartida em fatias (uma por parlamentar), iguais ou proporcionais: pior ainda.
- Um botão "esconder/mostrar Brasília": é decisão de edição, não do leitor.
- Escala das bolhas no cabeçalho: é coisa de legenda.

## Riscos e limites que o texto do mapa precisa dizer

- O dado é o **município do favorecido**, não o endereço da obra. Entidade com sede em Brasília conta
  como Brasília (R$ 112 bi, 40% de tudo).
- Nos maiores municípios o maior autor é relator, comissão ou bancada: os retratos não contam a
  história inteira, e o texto tem de dizer isso.
- Desempenho: 5.566 círculos mais 8 retratos é leve; evitar um `<pattern>` por autor para milhares.
- `pagina.html` tem 1.837 linhas. Cada etapa deve entrar como função nova chamada de um ponto só,
  não espalhada pelos `if (estado.medida === "emd")` que já existem.
