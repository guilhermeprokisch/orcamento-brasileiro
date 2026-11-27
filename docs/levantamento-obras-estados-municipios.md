# Obras de estados e prefeituras: o que dá para trazer para /obras/todas

Levantamento de 27/11/2026. Hoje o explorador `/obras/todas` mostra as 32.292 obras com dinheiro
federal da lista do TCU (ver [levantamento-obras-paradas.md](levantamento-obras-paradas.md)). A
pergunta agora é se dá para pôr na mesma lista as obras pagas por estados e prefeituras: quantas
são, com que campos (cidade, valor, situação) e que limpeza pedem.

## Resumo

- **O Obrasgov.br quase não tem obra de estado e de prefeitura.** De 155.950 projetos, 9.371 não
  têm dinheiro federal, e 9.097 deles são do governo de São Paulo, que cadastra lá as suas obras.
  Fora de SP sobram umas 270, quase todas empréstimos para prefeituras que o Ministério das Cidades
  repassa. Ou seja, o Obrasgov.br é um cadastro do dinheiro federal, como já se sabia.
- **E as obras paulistas do Obrasgov.br não dizem se andaram.** 98,5% estão como "Cadastrada", e
  79% são pedidos de reforma de escola estadual da FDE, de R$ 290 mil em média. Não dá para dizer
  se cada uma está andando, parada ou pronta. **Não recomendo trazer.**
- **A fonte que serve é o Painel de Obras do TCE-SP.** Ele abre sem login e responde em JSON.
  Traz 8.029 obras em andamento (data-base 17/10/2026): 7.130 de prefeituras e 899 do estado,
  R$ 27,5 bilhões em contratos, em 535 das 645 cidades paulistas. Cada obra tem cidade, situação
  ("no prazo", "atrasada" ou "paralisada"), valor do contrato, empresa, órgão que contratou, ano
  e de onde vem o dinheiro.
- **Para os outros estados não há fonte aberta equivalente.** O TCE-PE tem API, mas só das obras
  que o tribunal auditou, e sem a situação. RS, MG, MT, PR, SC e CE bloquearam o acesso ou não
  têm consulta pública. O TCM-BA pede captcha. Não existe lista nacional de obras de estados e
  prefeituras.
- **Proposta**: trazer o TCE-SP para a lista, deixando claro na página que, por enquanto, as
  obras de estados e prefeituras são só as de São Paulo. Detalhes em "Proposta" no fim.

## Obrasgov.br

Baixei a lista inteira de `/projeto-investimento` (155.950 projetos, nenhum repetido) e de
`/geometria` (249.832 pontos com código IBGE) em 27/11/2026. A base diz ter sido atualizada em
25/11/2026.

> Nota técnica: a API fica muito lenta com páginas de 200 itens (20 s cada); com páginas de 50
> responde em 1 a 2 s. A lista inteira leva uns 40 minutos com 6 conexões.

### De onde vem o dinheiro

Cada projeto diz a fonte do investimento previsto (`investimentos_previstos[].desc_nome_fonte_recurso`):

| Fonte | Projetos |
|---|---|
| Só federal | 146.024 |
| Federal mais municipal ou estadual (contrapartida) | 556 |
| Outras combinações com federal | 6 |
| **Só estadual** | **9.051** |
| Empréstimo (só, ou com estadual) | 296 |
| Só municipal, ou estadual mais municipal | 17 |
| Privado ou sem fonte | 7 |

Os 9.371 projetos sem dinheiro federal:

- **9.097 vêm do cadastro direto (CIPI), e 9.101 são de SP.** O repassador é o próprio estado:
  Secretaria da Educação (7.151), DER (477), Fazenda (237). Os maiores órgãos são a FDE, que
  cuida das escolas estaduais (7.153), o DER (487), a USP (306), o Centro Paula Souza (241), a
  Secretaria de Agricultura (160) e o Tribunal de Justiça (142).
- **Os 274 restantes são empréstimos do Ministério das Cidades (SIMEC-MCID)** a prefeituras de
  vários estados, por exemplo para água e esgoto. O dinheiro é emprestado pela União (FGTS), então
  não é "obra paga pela prefeitura" no sentido que interessa.
- Fora de SP, as obras com fonte só estadual ou municipal no CIPI são umas 30 (22 de Dores do Rio
  Preto, ES).

### As obras paulistas do Obrasgov.br

| | |
|---|---|
| Projetos | 9.097 (8.174 obras, 640 projetos, 542 "outros") |
| Valor previsto | R$ 40,0 bilhões, mas a mediana é R$ 289 mil, e cinco projetos somam R$ 11 bilhões |
| Cadastrados em | 2025 (4.612) e 2026 (4.456): o estado começou a cadastrar em 2025 |
| Com código IBGE | todos; 8.988 com uma cidade só; 620 cidades |
| **Situação** | **Cadastrada 8.963**, em execução 92, concluída 38, cancelada 2, paralisada 2 |
| Com data de início efetiva | 15 |

- **"Cadastrada" não diz nada sobre a obra.** É o estado inicial do cadastro, e quase ninguém o
  atualiza. Na lista, todas apareceriam como "andando" ou ficariam sem situação.
- **A maior parte é manutenção de escola.** 5.272 nomes têm "Pedido de intervenção" (por
  exemplo "Vicente Barbosa, EE - Pedido de intervenção - 2023/00578", R$ 254 mil). É obra de
  verdade, mas pequena, e encheria a lista de linhas parecidas.
- **Recomendação: deixar de fora** até o estado atualizar as situações. Vale olhar de novo em 2027.

### Limpeza que o Obrasgov.br pede (se um dia entrar o federal dele)

O pedido incluía medir os três problemas já conhecidos. Como as obras não federais do Obrasgov.br
não vão entrar, eles só importam se um dia quisermos somar ao TCU as obras federais do
Obrasgov.br. Medido na lista inteira:

| Problema | Tamanho | Como tirar |
|---|---|---|
| **FNDE com R$ 0,01** | 20.173 das 25.257 obras do SIMEC-FNDE têm valor de até R$ 1 | Não tem conserto no Obrasgov.br. O valor certo está no TCU, que traz as obras do FNDE pelo número da obra no SIMEC, ou na cópia da mesma obra vinda do Transferegov |
| **SUPRA não é obra** | 1.696 registros, R$ 203,5 bilhões. O nome é um número de contrato ou de ação ("02 00351/2026"), e todos dizem "Obra" | Tirar pelo `sistema_resp == "SUPRA"` |
| **Repetidas (SIMEC × Transferegov)** | Não dá para medir com segurança | O número da obra no SIMEC aparece no nome só em 5.117 das 25.257 do FNDE (por exemplo "656925 - Esc. Educ. Infantil - Tipo B - Riacho da Cruz/RN"). Nas outras, só daria para casar pelo nome e pela cidade, e o teste deu falso demais: em 23.124 casos há alguma escola, creche ou quadra do Transferegov na mesma cidade, sem ser a mesma obra |

Conclusão: misturar as obras federais do Obrasgov.br com as do TCU é trabalho grande e com erro.
O TCU já cobre o federal. **Não recomendo.**

## Painel de Obras do TCE-SP

Painel em `paineldeobras.tce.sp.gov.br`, feito em Pentaho. As consultas que o painel usa
respondem em JSON para o usuário anônimo que a própria página usa:

```
https://paineldeobras.tce.sp.gov.br/pentaho/plugin/cda/api/doQuery
  ?path=/public/Obra/painel_obras.cda&dataAccessId=obrasTabela
  &parampPeriodo=1&parampMunicipio=-1&parampSituacao=-1&parampFonteRecurso=-1
  &parampContratante=-1&parampContratado=-1&userid=anony&password=zero
```

Testado em 27/11/2026: **8.029 linhas** (7.982 diferentes; 47 linhas repetidas idênticas),
data-base **17/10/2026**. Só há uma data-base por vez (`selPeriodo`).

Colunas: cidade (`ds_municipio`), situação, esfera (MUNICIPAL ou ESTADUAL), valor do contrato
(`vl_ajuste`), empresa e CNPJ, órgão que contratou, ano do contrato, objeto. Sem código IBGE na
linha, mas a lista de cidades do filtro (`selMunicipio`) usa o código IBGE como id
(3500105 = Adamantina), então basta casar pelo nome.

| | Prefeituras | Estado | Total |
|---|---|---|---|
| Obras | 7.130 | 899 | 8.029 |
| Valor dos contratos | R$ 17,1 bi | R$ 10,4 bi | R$ 27,5 bi |
| Em execução, no prazo | 6.345 | 768 | 7.113 |
| Em execução, atrasada | 543 | 89 | 632 |
| **Paralisada** | **242** | **42** | **284** |

Ano do contrato: a maioria é de 2018 a 2025 (de 716 a 1.104 por ano).

**De onde vem o dinheiro** (filtro `parampFonteRecurso`; uma obra pode ter mais de uma fonte):

| Fonte | Obras | Contratos |
|---|---|---|
| Tesouro (dinheiro próprio) | 4.396 | R$ 13,0 bi |
| Transferências e convênios estaduais | 1.339 | R$ 2,4 bi |
| Transferências e convênios federais | 990 | R$ 2,4 bi |
| Outras fontes | 940 | R$ 5,1 bi |
| Recursos próprios da administração indireta | 545 | R$ 5,5 bi |
| Operações de crédito | 291 | R$ 3,3 bi |
| Fundos especiais | 111 | R$ 0,3 bi |
| Emendas parlamentares individuais | 64 | R$ 0,1 bi |

- 1.044 obras têm algum dinheiro federal, e **402 têm só dinheiro federal** (R$ 0,71 bi). Essas
  podem já estar na lista do TCU. Não há número de convênio para casar uma com a outra.
- 1.419 obras não têm fonte informada.

**O que falta no TCE-SP:**

- **Não há obra pronta nem cancelada.** O painel só acompanha obra em andamento: quando acaba,
  sai da lista. A lista não serve para contar quantas ficaram prontas.
- **O valor é o do contrato**, não o custo previsto da obra nem quanto já foi pago. Não há
  percentual feito.
- **Não há um código da obra** na tabela; a linha se identifica pelo conjunto
  (cidade, órgão, empresa, ano, objeto, valor). Para acompanhar a obra entre uma data-base e
  outra, é com essa chave.
- O painel tem outras consultas (endereço, motivo do atraso ou da paralisação, histórico,
  classificação por tipo de obra), mas pedem outros parâmetros. Não testei. O tipo de obra
  (`selClassificacao`, 42 classes, por exemplo "Energia - combustíveis e derivados") é o que
  daria o filtro "tipo de obra" do explorador.

## Os outros estados

Testado em 27/11/2026, a partir desta máquina (o bloqueio pode ser do IP; vale tentar RS e MG de
novo no navegador do Mac):

| Fonte | Situação da obra? | Acesso | Dá para automatizar? |
|---|---|---|---|
| TCE-PE, API de dados abertos (`sistemas.tcepe.tc.br/DadosAbertos`) | Não. 2.591 obras **auditadas** pelo tribunal, com valores e datas; 74 com prazo de paralisação | JSON aberto | Sim, mas não responde à pergunta |
| TCE-RS (LicitaCon, `dados.tcers.tc.br`) | Não verificado | Desafio da Cloudflare, até na API | Não daqui |
| TCE-MG (`dadosabertos.tce.mg.gov.br`) | Não verificado | Erro de certificado | Não daqui |
| TCE-PR (Portal Informação para Todos) | A imprensa fala em 1.958 paralisadas | Endereços testados deram erro | Não verificado |
| Geo-Obras (TCE-MT, RN, PI, AC) | Não verificado | Bloqueado ou sem consulta pública | Não |
| TCM-BA (obras dos municípios) | Sim | Captcha por cidade | Não |
| TCE-SC | Não verificado | Bloqueado. E o projeto já decidiu não usar o TCE-SC no site | Não |
| TCE-CE, TCM-GO | Não verificado | Sem consulta encontrada | Não |
| PNCP (nacional) | Não: contratos de todas as esferas, com código IBGE e valor, mas sem situação da obra | API aberta | Serve para contratos, não para obras |

## Proposta: como entrar na lista

1. **Fonte nova: TCE-SP.** Um comando no pipeline (`obras-estaduais`, ou dentro de
   `obras-paradas`) baixa a tabela do painel, tira as 47 linhas repetidas e casa a cidade com o
   código IBGE pela lista do próprio painel. A carga é automática; o painel publica uma data-base
   nova de tempos em tempos.
2. **O que entra:** as 7.982 obras, menos as 402 que têm só dinheiro federal (para não contar duas
   vezes o que o TCU já mostra). Ficam **7.580 obras**, R$ 26,7 bilhões em contratos.
3. **Como cada obra aparece na lista que já existe:**
   - situação: "no prazo" e "atrasada" viram "andando" (com a marca "atrasada"); "paralisada"
     vira "parada". Não há "pronta" nem "cancelada";
   - "quem paga": **Prefeitura** ou **Governo do estado**, no lugar do ministério;
   - valor: "contrato" (não é "custaria"). Sem "liberado" e sem "% feita";
   - tipo de obra: pela classificação do TCE-SP, se a consulta de classificação funcionar; senão,
     "não identificado".
4. **Dados:** os arquivos por estado continuam (`site/public/data/obras/SP.json`). Cada linha
   ganha a origem (TCU ou TCE-SP), e o índice ganha a lista de origens. Só o `SP.json` cresce
   (de 2.256 para cerca de 9.800 obras).
5. **Na página:** um filtro "Quem paga: União / Governo do estado / Prefeitura". Um aviso, onde a
   pessoa escolhe outro estado: "Obras de estados e prefeituras: por enquanto só temos as de São
   Paulo, que o Tribunal de Contas do estado publica." E a explicação de que as obras de SP somem
   da lista quando acabam.
6. **Obrasgov.br: não entra agora.** As obras sem dinheiro federal são quase todas pedidos de
   reforma de escolas de SP, sem situação; as federais já vêm do TCU.
7. **Depois:** tentar RS e MG pelo navegador do Mac; o TCE-PE só se aceitarmos uma lista sem
   situação ("obras que o tribunal auditou").

Antes do código: mock da mudança no explorador (filtro "quem paga", aviso de "só SP", obra de
prefeitura numa linha) no Claude Design, para o Guilherme aprovar.

## O que esta conta não diz

- **Não é a lista de todas as obras de SP.** É o que as prefeituras e o estado informam ao
  TCE-SP, e só as que estão em andamento.
- **Uma obra "no prazo" pode estar parada de fato**, se o órgão não atualizou a situação.
- **As 402 obras só com dinheiro federal saem por precaução**, não porque se confirmou que estão
  no TCU.

## O que foi feito

Aprovado pelo Guilherme em 27/11/2026, com o mock no Claude Design
([Obras: estados e prefeituras](https://claude.ai/artifact/GMJPHBHYQk8KYXV933nKFN)).

- **Carga**: `uv run obras-tcesp` (`pipeline/src/orcamento_pipeline/obras_tcesp.py`) baixa o painel do TCE-SP
  (a tabela inteira e a mesma tabela filtrada por cada fonte de dinheiro), grava o que veio em
  `data/raw/tcesp-obras/painel.json` e a cópia de referência em `pipeline/referencia/obras-tcesp.json`, e refaz os
  arquivos do explorador juntando as obras ao `SP.json`. `--sem-baixar` só refaz os arquivos. A carga é
  **à mão, no Mac**: na primeira publicação (27/11/2026) o painel respondeu vazio aos servidores do GitHub, nas
  quatro tentativas. A publicação só usa a cópia de referência, que o `obras-paradas --atualizar` já junta ao
  `SP.json`. Quando o painel mostrar uma data-base nova, rodar `uv run obras-tcesp` e mandar a cópia pelo git.
- **Resultado em 27/11/2026** (data-base 17/10/2026): 7.580 obras, 894 do estado e 6.686 das prefeituras; 268 paradas
  e 601 atrasadas; R$ 26,7 bilhões em contratos. Ficaram de fora 47 linhas repetidas e 402 obras pagas só com dinheiro
  federal.
- **Cidade**: casada pelo nome com o SICONFI e com a lista do painel (a do painel só tem parte das cidades). Um
  apelido: Florínea, que o SICONFI escreve Florínia. Todas as obras ficaram com código IBGE.
- **Nome da obra**: o objeto do contrato, que vem em maiúsculas, vira texto normal. Sai o começo burocrático
  ("Contratação de empresa especializada em serviços de engenharia para…", "Constitui objeto do presente
  contrato…"), as siglas (EMEF, UBS, SABESP…) ficam em maiúsculas e os nomes depois de "rua", "bairro", "escola"…
  e o da cidade da obra ganham iniciais maiúsculas. Nome próprio solto no meio do texto continua em minúsculas.
  580 obras vêm sem objeto e aparecem como "Obra sem descrição, contratada com" e o nome da empresa.
- **Tipo de obra**: o painel tem uma classificação (42 tipos), mas a consulta dela não responde fora da página;
  as obras do TCE-SP ficam como "Sem tipo identificado".
- **Na página**: botões "De quem é o dinheiro" (União, Governo do estado, Prefeitura); o campo de ministério só
  vale para a União. Nas obras do TCE-SP: a marca "atrasada", "o TCE-SP não informa" no lugar do quanto foi feito,
  "contrato de 2023" debaixo do valor e um traço em "já liberado". Escolher estado ou prefeitura fora de SP mostra
  o aviso de que só SP tem essa lista. A planilha ganhou as colunas de esfera, órgão, atrasada, ano do contrato,
  o que é o valor e a fonte.
- **A conferir**: valores de contrato que parecem altos demais para o objeto (uma obra de Mauá tem R$ 412 milhões
  para remanejar uma rede de água numa rua). O painel não diz o valor de cada parte do contrato.
