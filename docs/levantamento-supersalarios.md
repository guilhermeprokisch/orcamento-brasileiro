# Supersalários: quem ganha acima do teto, e com o quê

Levantamento de 22/11/2026, para o item "salários de servidores acima do teto" do
[plano de melhorias](plano-de-melhorias.md) ("Depois dos blocos"). A pergunta: em cada órgão,
quantos servidores recebem mais que o teto, quanto passa no total e de onde vem o que passa.

Hoje o site mostra a folha só somada: o gasto com pessoal frente ao limite da LRF, a previdência
dos servidores, a folha estadual de PR e SC por cidade e a folha federal na cidade. Nada aqui
muda isso: a proposta continua mostrando **só somas por órgão**, nunca uma pessoa.

## O teto

A Constituição (art. 37, XI) diz que ninguém no serviço público pode receber mais que um ministro
do STF. O subsídio do ministro é **R$ 46.366,19 por mês** desde fevereiro de 2025 (Lei 14.520/2023),
e é o valor que a folha federal ainda aplicava em setembro de 2026: dos 9.445 servidores que
tiveram corte pelo abate-teto, boa parte ficou em R$ 46.366,19 exatos.

Nos estados e prefeituras há subtetos menores (governador, desembargador, prefeito). Para não
discutir caso a caso, a conta usa sempre o teto nacional: é o critério mais generoso, e mesmo assim
os números abaixo são grandes.

O teto não vale para tudo. A própria Constituição (art. 37, § 11) tira dele as **parcelas
indenizatórias**, e leis e decisões foram ampliando a lista do que fica fora: auxílios, férias
vendidas, licenças convertidas em dinheiro, pagamentos atrasados. É por aí que passa quase todo o
"supersalário": não é o salário-base que fura o teto, é o que vem por cima dele, com nome de
indenização.

## As fontes

Testado em 22/11/2026: as linhas marcadas "baixado" foram baixadas de verdade, sem cadastro; as
outras foram vistas na página ou na documentação.

| Fonte | Quem cobre | Formato e lote | Separa as parcelas? | Corte pelo teto? |
|---|---|---|---|---|
| **Portal da Transparência federal**, servidores ([download](https://portaldatransparencia.gov.br/download-de-dados/servidores)) | Executivo federal: civis (SIAPE, ~515 mil ativos), militares (~343 mil), Banco Central; arquivos à parte de honorários de sucumbência e jetons | Zip mensal, ~80 MB (civis), desde 2013; o mês sai uns 20 dias depois; honorários vêm com um mês de atraso. **Baixado** | Sim: salário-base, 13º, férias, "outras eventuais", indenizações (total) | Sim, `ABATE-TETO` |
| **DadosJusBr** ([api.dadosjusbr.org](https://api.dadosjusbr.org)) | 124 órgãos: 27 TJs, 27 TREs, 24 TRTs, 6 TRFs, 5 superiores, 3 militares, 30 MPs, CNJ e CJF. Só membros (juízes, promotores) | Zip por órgão e mês, 2018 a 2026, licença CC-BY. **Baixado** | Sim, rubrica por rubrica, com uma classificação padronizada (auxílio-saúde, licença compensatória, acúmulo, retroativos…) | Sim, como desconto |
| CNJ, [remuneração dos magistrados](https://www.cnj.jus.br/transparencia-cnj/remuneracao-dos-magistrados/) | 92 órgãos do Judiciário, desde 2017 | Painel Qlik, exporta planilha aba por aba na tela; **sem lote nem API** (o DadosJusBr automatiza isso) | Sim: subsídio, vantagens pessoais, indenizações, eventuais | Sim |
| CNMP e portais dos MPs | 30 MPs | O nacional é Power BI, sem download; cada MP publica no seu portal (planilha ou consulta). Até set/2026 havia exigência de identificação e captchas | Sim, mas junta "verbas indenizatórias e outras remunerações temporárias" | Sim |
| Câmara dos Deputados ([remuneração](https://www2.camara.leg.br/transparencia/recursos-humanos/remuneracao)) | Servidores e deputados, 2012 a 2026 | CSV mensal (3 MB); endereços irregulares, precisa ler o índice de cada ano | Sim: vantagens pessoais, eventuais, diárias, auxílios, indenizatórias | Sim, "Redutor Constitucional" |
| Senado ([API](https://adm.senado.gov.br/adm-dadosabertos/swagger-ui/index.html)) | Servidores, 2015 a 2026 | CSV ou JSON por mês pela API (2 MB) | Sim, como a Câmara | Sim, "Reversão Teto Constitucional" |
| Paraná (`estado_pr.py`) | Executivo, Tribunal de Contas e parte do pessoal do TJ, MP e Assembleia | Zip mensal, 11 MB. **Baixado** | Em parte: vencimento, gratificação, retroativos, "outros", auxílio transporte e alimentação, 13º e férias | Sim, `redutor` |
| Santa Catarina (`estado_sc.py`) | Executivo | CSV mensal pela API (22 MB) | **Não**: só o bruto | **Não** |
| SP, MG, GO, DF | Executivo | CSV ou zip em lote (SP parou em maio/2026; MG barra robôs) | Pouco (DF tem "benefícios"; nos outros as indenizações vão em "eventual") | Sim |
| RS, BA, RJ | Executivo | Painel Power BI ou consulta nominal; sem lote confirmado | — | — |

Nenhuma fonte traz o CPF completo; algumas trazem o CPF com parte escondida, e quase todas trazem o
nome. O pipeline não lê nem guarda nenhum dos dois.

**Uma mudança em 2026 que corta a série ao meio.** Em 25/03/2026 o STF fixou que juízes e
promotores (e, por extensão, defensores, advogados públicos e conselheiros de tribunais de contas)
só podem receber auxílios previstos em lei federal, e que as parcelas por cima do subsídio ficam
limitadas a 70% do teto: 35% por tempo de serviço e 35% de indenizações (o auxílio-saúde fica de
fora desse limite). Vale desde os salários de abril de 2026. Em maio e junho, o CNJ e o CNMP criaram
um contracheque único, com a mesma lista de rubricas para todos. Antes e depois de abril de 2026 são
duas séries diferentes.

## O que a amostra mostrou

Quatro medições, só com somas (os arquivos com nome ficaram numa pasta temporária, fora do repositório,
e foram apagados depois).

### Poder Executivo federal (Portal da Transparência, agosto de 2026)

514,5 mil servidores civis ativos do Executivo (SIAPE), mais os honorários de sucumbência e os
jetons de conselhos do mesmo mês. A conta vai em camadas: cada linha soma uma parte a mais do que a
pessoa recebeu no mês.

| O que entra na conta | Acima do teto | O que passa do teto, somado |
|---|---:|---:|
| Só o que conta para o teto (salário-base menos o corte do abate-teto) | 422 | R$ 0,8 mi |
| + pagamentos eventuais (exceto 13º e férias) | 2.926 | R$ 10 mi |
| + honorários de sucumbência e jetons | 10.310 | R$ 90 mi |
| + indenizações (auxílio-alimentação, creche, transporte) | 13.002 | R$ 108 mi |
| + 13º e férias | 13.465 | R$ 115 mi |

Setembro deu quase o mesmo (13.213 acima, R$ 109 mi), então não é coisa de um mês só: são cerca de
**13 mil pessoas (2,5% dos servidores) e R$ 1,3 bilhão por ano** acima do teto. Um estudo feito para
a República.org chegou a 12,2 mil pessoas no Executivo federal, com número de pessoas parecido mas
valor maior (R$ 4,3 bi em 12 meses); a reportagem não diz como contou, e vale entender a diferença
antes de publicar.

- **Os honorários de sucumbência explicam a maior parte.** São o dinheiro que a parte que perde um
  processo contra a União paga, dividido entre os advogados públicos (procuradores federais, da
  Fazenda Nacional, advogados da União). R$ 166 mi em agosto, para 7.667 pessoas. Quase todos esses
  advogados têm subsídio de R$ 35 mil; com os honorários, a mediana vai a R$ 58 mil. Em 2020 o STF
  (ADI 6053) decidiu que subsídio mais honorários tem de respeitar o teto, mas o arquivo mostra o
  corte do abate-teto pequeno (R$ 320, em geral) e nenhum corte nos honorários. Pode haver um limite
  aplicado fora do que o Portal mostra: **é a primeira coisa a perguntar à AGU antes de publicar.**
  A decisão do STF de março de 2026 também vale para a advocacia pública, e o quadro de agosto de
  2026 é este mesmo.
- Por órgão: Advocacia-Geral da União (4.109 de 6.863 servidores acima do teto, R$ 50 mi por mês),
  Ministério da Fazenda (5.268 de 19.573, R$ 34 mi: procuradores da Fazenda, pelos honorários, e auditores
  fiscais, pelos pagamentos eventuais e pelos auxílios), Trabalho e Emprego (591), Presidência (129),
  CGU (115). No resto, dezenas por órgão.
- Quem passa do teto só pelo auxílio-alimentação passa por pouco: 2.692 pessoas. Contar ou não as
  indenizações muda bastante o número de pessoas e pouco o valor.
- **Militares** (agosto; setembro saiu vazio): 558 acima do teto entre 343 mil, quase todos por
  indenizações que são de uma vez só (a mediana deles passa de R$ 129 mil no mês, típico de quem vai
  para a reserva e recebe licenças não tiradas). Não é salário que se repete; o texto tem que dizer.

### Judiciário e Ministério Público (DadosJusBr, setembro de 2025)

Juízes, desembargadores, procuradores e promotores (os "membros"; os servidores comuns desses
órgãos não entram) de 107 órgãos: 25 tribunais de justiça, 20 MPs, 24 tribunais do trabalho, 5
federais, os superiores, os militares e 23 eleitorais. 38,6 mil pessoas. Setembro de 2025 é o mês
recente com mais órgãos; em 2026 a coleta tem buracos (quase todos os MPs pararam em 2025).

| O que entra na conta | Acima do teto | % | O que passa do teto, somado |
|---|---:|---:|---:|
| Só o subsídio, menos a retenção pelo teto | 98 | 0,3% | R$ 0,5 mi |
| + vantagens pessoais (tempo de serviço, abono de permanência) | 4.300 | 11% | R$ 41 mi |
| + direitos eventuais (acúmulo de funções, licença compensatória, férias vendidas, retroativos) | 24.635 | 64% | R$ 948 mi |
| + indenizações (auxílios) | 30.632 | 79% | R$ 1.270 mi |
| + 13º e 1/3 de férias | 30.711 | 80% | R$ 1.517 mi |

Março de 2025 (117 órgãos) deu o mesmo desenho: 81% acima, R$ 1.258 mi passando do teto no mês.
Se os outros meses forem parecidos, foi **da ordem de R$ 15 bilhões em 2025** só nos membros desses
órgãos. Bate com o que outros mediram: a Transparência Brasil e a República.org chegaram a
R$ 10,7 bi acima do teto nos TJs em 2025 (aqui, R$ 834 mi por mês nos TJs, cerca de R$ 10 bi no ano).

Os eleitorais quase não aparecem porque pagam só a gratificação eleitoral (R$ 6 mil) a juízes que
recebem o salário em outro tribunal. Tirando eles, **quatro em cada cinco juízes e promotores
recebem acima do teto em um mês comum.** A mediana de um membro de tribunal de justiça estadual
foi de R$ 94 mil no mês; no TJSP, R$ 129 mil; no MPRJ, R$ 145 mil.

| Tipo de órgão | Órgãos | Membros | Acima do teto | Passa do teto no mês |
|---|---:|---:|---:|---:|
| Tribunais de justiça estaduais | 25 | 16.822 | 87% | R$ 834 mi |
| Ministérios Públicos | 20 | 10.625 | 95% | R$ 302 mi |
| Justiça do Trabalho | 24 | 5.553 | 70% | R$ 81 mi |
| Justiça Federal | 5 | 1.879 | 93% | R$ 40 mi |
| Tribunais superiores | 5 | 504 | 28% | R$ 9 mi |
| Justiça Militar | 3 | 68 | 97% | R$ 4 mi |

De onde vem o dinheiro, em setembro de 2025, nos órgãos não eleitorais (R$ 3,1 bi pagos no mês,
sem 13º e férias):

| Parcela | R$ mi no mês |
|---|---:|
| Subsídio | 1.358 |
| Retroativos e rubricas que não dizem o que são | 678 |
| Acúmulo de funções, plantão, licença compensatória | 455 |
| Auxílios (saúde, alimentação, creche…) | 169 |
| Férias e licença-prêmio vendidas | 136 |
| Vantagens pessoais | 125 |

O extra passa da metade do que se paga: para cada R$ 1 de subsídio, mais R$ 1,15 vem por fora.
A maior parte do extra não se deixa ver: R$ 678 mi estão em rubricas como "pagamentos retroativos"
ou "outras verbas remuneratórias, legais ou judiciais", sem dizer a que se referem.

Os órgãos com mais dinheiro acima do teto no mês: TJSP (R$ 272 mi; 96% dos 3.597 juízes), TJMG
(R$ 138 mi), MPRJ (R$ 92 mi; todos os 893 membros), TJPR (R$ 83 mi), TJRS (R$ 57 mi), MPSP
(R$ 52 mi), TJPE (R$ 37 mi), TJMA (R$ 34 mi), MPF (R$ 32 mi), MPMG (R$ 31 mi), TJSC (R$ 31 mi).

### Depois da decisão do STF (DadosJusBr, agosto de 2026)

Agosto de 2026 tem 79 órgãos no DadosJusBr (quase todos os TJs e TRTs; só 5 MPs). Comparando os
mesmos órgãos com setembro de 2025, sem 13º e férias:

| Mesmos órgãos | Membros | Acima do teto | Passa do teto no mês | Mediana do mês |
|---|---:|---:|---:|---:|
| 21 TJs, set/2025 | 13.887 | 86% | R$ 658 mi | R$ 91 mil |
| 21 TJs, ago/2026 | 13.668 | **96%** | **R$ 333 mi** | R$ 70 mil |
| 21 TRTs, set/2025 | 5.302 | 70% | R$ 76 mi | R$ 62 mil |
| 21 TRTs, ago/2026 | 5.266 | 89% | R$ 135 mi | R$ 64 mil |

Nos TJs, o dinheiro acima do teto caiu à metade (no TJSP, de R$ 272 mi para R$ 108 mi), mas **mais
juízes** passaram do teto: o limite de 70% virou o alvo, e quase todos foram para perto de
R$ 79 mil (o teto mais 70%). Na Justiça do Trabalho, que pagava menos, o extra subiu. Mesmo assim,
5.078 dos 25,9 mil membros com dados em agosto receberam mais que o teto mais 70%. É um mês só, e
com cobertura menor, mas é exatamente o tipo de comparação que o site pode fazer: o antes e o depois
de uma decisão, órgão por órgão.

### Executivo do Paraná (Portal da Transparência do PR, agosto de 2026)

O mesmo arquivo que `estado_pr.py` já baixa traz, além do bruto, as partes: vencimento,
gratificação, retroativos, "outros", auxílio transporte e alimentação, 13º e férias, e o redutor
(o corte pelo teto). 308 mil vínculos (não pessoas: quem tem dois cargos conta duas vezes).

| O que entra na conta | Acima do teto | O que passa do teto, somado |
|---|---:|---:|
| Vencimento e gratificação, menos o redutor | 92 | R$ 0,2 mi |
| + "outros" | 1.187 | R$ 6,1 mi |
| + retroativos | 1.472 | R$ 12,6 mi |
| + auxílios | 1.532 | R$ 13,5 mi |
| + 13º e férias | 1.615 | R$ 14,9 mi |

Quase metade dos vínculos da Receita Estadual (483 de 1.001) passa do teto, quase tudo pela coluna
"outros", que o arquivo não detalha. Depois vêm o Tribunal de Contas (292 de 527), a Procuradoria
do Estado (221 de 626), a Segurança Pública (137, por retroativos) e o pessoal do TJ e do MP pago
por essa folha (123 e 63; os juízes e promotores não estão nela, estão no DadosJusBr). Na educação e
na saúde, quase ninguém.

## O que os dados sustentam e o que não sustentam

Sustentam:

- **Contar, por órgão, quantos passam do teto e quanto passa no total**, com a regra dita na tela
  (o que entra na conta). As medições dão números estáveis de um mês para o outro.
- **Dizer de onde vem o extra**, em poucas famílias (vantagens pessoais, acúmulo e plantão, férias e
  licenças vendidas, auxílios, retroativos). O DadosJusBr já padroniza as rubricas de cada tribunal e
  MP; no Executivo federal, o Portal separa abate-teto, eventuais, indenizações e honorários.
- **Comparar órgãos do mesmo tipo**: TJ com TJ, MP com MP. Todos pagam o mesmo subsídio, então a
  diferença está no que vem por cima.
- **Mostrar o tamanho do que não se explica**: quanto de cada órgão está em rubricas opacas. É um
  número útil por si: diz quem presta contas pior.

Não sustentam:

- **Dizer que é ilegal.** Quase tudo que passa do teto tem uma lei, uma resolução ou uma decisão por
  trás que o tira da conta (a decisão do STF de 2026 derrubou parte disso, mas só daí para a
  frente). O site pode dizer "acima do teto" e "fora do teto por ser indenização"; não pode dizer
  "irregular". A palavra "supersalário" fica no título e na explicação, não no rótulo
  de cada órgão.
- **Somar o que uma pessoa recebe em dois lugares.** Sem CPF não há como juntar o salário do juiz no
  tribunal com a gratificação dele no TRE, ou o servidor cedido com o órgão de origem. A conta é por
  folha, e erra para menos.
- **Tratar um mês como salário.** Retroativos, licenças vendidas e indenizações de passagem para a
  reserva caem de uma vez. O certo é somar o ano: quanto passou do teto em 12 meses e quantos
  passaram em pelo menos um mês (e em quantos meses).
- **Comparar Judiciário com Executivo como se fosse a mesma coisa.** No Judiciário e no MP a conta é
  só dos membros (juízes, promotores); no Executivo, de todos os servidores. Os percentuais não se
  comparam; os valores, sim.
- **Mostrar as camadas dos MPs com a mesma precisão dos tribunais.** O formato do CNMP junta
  "verbas indenizatórias e outras remunerações temporárias" numa categoria só; só a rubrica, item a
  item, diz o que é cada coisa.
- **Cobrir tudo.** Faltam os servidores (não membros) dos tribunais e MPs, os tribunais de contas,
  as defensorias, o Legislativo, as estatais e quase todos os estados e prefeituras. A tela tem de
  dizer o que ficou de fora.
- **Números de 2026 para o Judiciário inteiro.** A coleta do DadosJusBr em 2026 tem buracos (só 5
  MPs chegam a 2026; 6 não têm nem 2025); para os meses que faltam, a fonte é a planilha de cada
  órgão ou o painel do CNJ, que não tem download em lote.
- **Juntar 2025 e 2026 numa série só.** A decisão do STF e o contracheque único mudam as regras e as
  rubricas a partir de abril de 2026. O site mostra os dois períodos lado a lado, não uma linha só.
- **Usar o teto nacional para dizer que um servidor estadual passou do teto dele.** No Executivo dos
  estados o limite é o salário do governador (ou o do desembargador, onde o estado adotou o subteto
  único). A conta com o teto nacional mostra quem passa do maior limite possível; o texto tem de
  dizer isso.

## Como mostrar

O mesmo princípio do resto do site: somas, não pessoas.

1. **Uma frase de abertura**, com o número do país e a regra: "Em 2025, 4 de cada 5 juízes e
   promotores receberam acima do teto de R$ 46.366,19 num mês comum. O que passou do teto somou cerca
   de R$ 1,3 bilhão por mês. Quase nada disso vem do salário: vem de auxílios, indenizações e
   pagamentos atrasados, que a lei deixava fora do teto. Desde abril de 2026, uma decisão do STF
   limita esse extra; o dinheiro acima do teto nos tribunais de justiça caiu à metade."
2. **A escada do teto**: as camadas das tabelas acima, uma barra por camada, para o leitor ver em que
   degrau o número explode. É a explicação de "como é possível passar do teto se existe teto".
3. **A tabela por órgão**, ordenável: membros (ou servidores), quantos passam do teto, que parte
   isso é, quanto passa no total no ano, e a mediana do que recebem no mês. Cada linha com uma barra
   empilhada de onde vem o extra (as famílias de rubricas), e a parte opaca em destaque.
4. **Faixas, não nomes**: quantos ficam até R$ 10 mil acima, de R$ 10 a 50 mil, mais de R$ 50 mil.
   Uma faixa com menos de 5 pessoas não aparece (a mesma regra da folha estadual).
5. **O ano, não o mês**: o número principal é a soma de 12 meses; o mês serve para o leitor sentir o
   tamanho ("a mediana do TJSP foi R$ 129 mil em setembro de 2025").
6. **Texto de cuidado** fixo: o que fica fora do teto por lei, que a conta é por folha (erra para
   menos), que há meses com pagamentos de uma vez só, de onde vêm os dados e o que falta.

Regras de privacidade, as mesmas do resto do pipeline: nenhum nome, CPF (nem parte dele) ou
matrícula sai do download; o arquivo bruto é lido e apagado, e o cache guarda só somas por órgão e
por faixa. Órgão com menos de 5 pessoas acima do teto mostra "menos de 5" e não mostra valor.

## Onde entra no site

Três lugares, em ordem:

1. **Página própria, `/supersalarios`** (ou dentro de `/dados`): a frase de abertura, a escada do
   teto e a tabela de todos os órgãos medidos, com filtro por tipo (TJ, MP, Trabalho, Federal,
   Executivo federal). É onde cabe a explicação longa do que fica fora do teto.
2. **Na página de cada estado (`/estados/[uf]`), ao lado de `PessoalResultado`**: um bloco curto,
   "Acima do teto no estado", com o TJ e o MP daquele estado (todos têm, pelo DadosJusBr) e, onde
   houver, o Executivo estadual. O gasto com pessoal mostra quanto pesa a folha; este bloco mostra
   uma das razões. Liga para a página própria.
3. **Na página de órgão federal (`/orgaos/[cod]`)**: AGU, Fazenda e os outros do Executivo, pelo
   Portal; e os da Justiça e do MP da União (TRFs, TRTs, MPF, MPT), que já têm página pelo orçamento,
   pelo DadosJusBr.

Não entra na página da cidade: os dados são por órgão, e a lotação não diz onde a pessoa trabalha.

Ordem sugerida de trabalho:

1. **Judiciário e MP pelo DadosJusBr**: 2025 inteiro (o ano com mais cobertura) e 2026 desde
   maio (a decisão valeu desde abril, mas o corte só apareceu nos pagamentos de maio), lado a lado, com cópia em `pipeline/referencia/` como nos outros comandos. É onde está
   quase todo o dinheiro (R$ 1,3 bi no mês em 2025, contra R$ 0,1 bi no Executivo federal), a fonte
   já vem padronizada, e o antes e depois da decisão do STF é a notícia.
2. **Executivo federal pelo Portal**, depois de perguntar à AGU (por LAI) se há corte nos honorários
   que o Portal não mostra.
3. **Executivo do PR**, reusando o download de `estado_pr.py`, que já separa as partes. O de SC só
   tem o bruto: dá para contar quem passa do teto, não de onde vem o extra.
4. Os outros estados e o Legislativo, conforme as fontes da tabela acima permitirem.

## O que decidir

- Mostrar por órgão e por faixa, como acima, ou também os cargos (procurador federal, auditor
  fiscal, desembargador)? Cargo com muita gente não identifica ninguém e explica muito.
- Começar pelo Judiciário e MP (onde está o dinheiro) ou pelo Executivo federal (fonte oficial,
  mas com a dúvida dos honorários)?
- Página própria primeiro, ou o bloco na página de estado primeiro?

## Como atualizar (feito em 22/11/2026)

O primeiro passo da ordem acima está no ar como `uv run supersalarios` (página `/supersalarios` e bloco
"Juízes e promotores acima do teto" na página de cada estado). O comando baixa do DadosJusBr os meses
que faltam desde janeiro de 2025, lê só o `remuneracao.csv` de cada pacote (o arquivo com os nomes nunca
é aberto) e guarda em `data/raw/supersalarios/` só as somas de cada órgão no mês. A primeira carga leva
uns 20 minutos; as seguintes, só os meses novos. A publicação usa a cópia em
`pipeline/referencia/supersalarios.json` (`--sem-baixar`): rodar à mão uma vez por mês.

Quando o DadosJusBr não classifica uma rubrica (comum em 2026, com o contracheque único), a família sai
do nome da rubrica (tempo de serviço, folga compensatória, férias, auxílio) e, para as vantagens
pessoais, da categoria do CNJ; o resto fica em "atrasados e rubricas opacas".

Três regras vieram da conferência dos dados:

- **Os tribunais superiores ficam de fora.** No STJ, 194 dos 313 contracheques de setembro de 2025 eram de
  juízes temporários, auxiliares ou convocados (que recebem o salário no tribunal de origem), e os
  "ministros" eram 64 para 33 cadeiras; no TST, 52 "ministros" para 27 cadeiras e 26 pensionistas. Os
  arquivos misturam ativos, aposentados, pensionistas e convocados.
- **Só conta quem recebeu subsídio do órgão no mês.** Nos TJs e MPs são poucos os outros (8 de 893 no
  MPRJ, 14 de 198 no TJPI), mas sem subsídio não dá para dizer que é membro na ativa daquele órgão.
- **"Um mês típico" é a mediana dos meses**, não a média: no STF, por exemplo, ninguém passava do teto na
  maior parte dos meses e todos passavam em um, o que dava "49% num mês típico". A tabela mostra também em
  quantos meses houve pelo menos 5 acima do teto.

O TJBA parece estranho (pagava pouco além do subsídio em 2025 e passou a pagar perto do limite de 70%
depois da decisão do STF), mas os metadados do DadosJusBr dão os dois anos como completos e detalhados:
o site mostra o que os dados dizem.

Conferência: os 27 TJs somam R$ 10,6 bi acima do teto em 2025, perto dos R$ 10,7 bi da Transparência
Brasil e da República.org.

O segundo passo também: `uv run supersalarios-federal` (seção "No Executivo federal" em `/supersalarios` e
bloco "Acima do teto" na página de cada órgão federal). Lê, de dentro dos zips do Portal da Transparência,
a remuneração e o cadastro dos servidores civis (SIAPE) e os arquivos de honorários e jetons do mês
seguinte (eles saem com um mês de atraso), soma por órgão de exercício e apaga os zips. Depois de alguns
downloads seguidos, o Portal passa a pedir captcha: o comando para e monta a saída com os meses do cache, e
completa os 12 meses em outras rodadas. Na primeira carga (22/11/2026) entraram julho e agosto de 2026; na segunda,
no mesmo dia, sem captcha, o resto: setembro de 2025 a agosto de 2026, R$ 1,3 bi acima do teto em 12 meses.
O pedido de informação à AGU sobre o teto nos honorários está em `docs/pedidos-lai/honorarios-agu-teto.md`.

## Quanto isso custa (feito em 22/11/2026)

A página mostra também o custo, em duas contas que não se somam (se o teto fosse cumprido, o dinheiro nem
seria pago):

- **O gasto acima do teto, por quem paga.** TJs, MPs e justiças militares dos estados estão no orçamento do
  estado; Justiça Federal, do Trabalho, MP da União, TJDFT e MPDFT, no da União. No bloco do estado, o que
  passou do teto no TJ e no MP aparece por morador e como parte de tudo o que o governo estadual gastou
  no ano (comparar com uma área pequena, como saneamento, inflaria a impressão).
- **O imposto de renda que deixa de entrar.** Para cada contracheque, o comando soma o IR descontado (sem o
  do 13º e das férias, cobrado à parte) e calcula o que seria descontado se tudo o que conta fosse salário:
  27,5% do que sobra depois da previdência, menos a parcela a deduzir (R$ 896,00 até abril de 2025, R$ 908,73
  depois). A diferença é um teto da estimativa: trata como salário também o que é indenização de verdade.
  Órgãos cujo arquivo não traz o desconto do IR (o TJMT, por exemplo) ficam fora dessa conta.

Quem perde: o IR que um estado desconta dos seus servidores é do próprio estado (Constituição, art. 157, I)
e entra na base dos mínimos de educação (25%) e saúde (12%). O da União é repartido (art. 159, I): 25,5%
para o FPM, 21,5% para o FPE e 3% para os fundos regionais. A amostra de setembro de 2025 deu até R$ 309 mi
por mês nos estados e R$ 59 mi na União.

## Executivo do Paraná (feito em 22/11/2026)

`uv run supersalarios-estados` lê a mesma folha do Paraná que `estado_pr.py` (os 12 meses mais recentes, até
outubro de 2026), tira aposentados e pensionistas pelo cadastro de vínculos e deixa de fora o TJ, o MP e a
Assembleia, que aparecem no arquivo só em parte. O Tribunal de Contas aparece só com aposentados e pensionistas
(a amostra do começo deste levantamento, que dava 292 acima do teto no TCE, os incluía por engano). Soma por órgão as camadas (vencimento e gratificação menos o
redutor, "outros", retroativos, auxílios) e o imposto de renda, como no Judiciário. Aparece no bloco do estado
(página do Paraná) e na seção "Nos governos estaduais" de `/supersalarios`. A conta é por vínculo e usa o teto
nacional (no Executivo estadual o limite é o salário do governador). Os próximos candidatos estão na tabela dos 27
estados, abaixo.

## A folha do Executivo nos 27 estados (levantamento de 22/11/2026)

Juízes e promotores de todos os estados já estão na página, pelo DadosJusBr. Esta tabela é do Executivo
(secretarias, polícias, professores). Testado de verdade, com download ou chamada à API (inclusive a API interna
que a própria página pública chama), sem resolver captcha nem contornar bloqueio anti-robô. Dificuldade: **1** =
arquivo limpo · **5** = só consulta nome a nome ou bloqueado.

| UF | Fonte e método | Lote? | Separa as partes? | Corte pelo teto? | Meses | Dif. |
|---|---|---|---|---|---|---|
| **PR** | Zip mensal do Portal da Transparência | Sim | Em parte ("outros" sem detalhe) | Sim (`redutor`) | 2012– | 1 (**no site**) |
| **ES** | CKAN, CSV mensal (82 MB) | Sim | **Rubrica a rubrica** | Sim (`ABATE TETO EC 41`) | 2009-01 a 2026-10 | 1 |
| **PE** | CKAN, CSV/JSON mensal, ativos e inativos separados | Sim | Em parte | Sim (`r_desconto_excedente`) | 2012-01 a 2026-10 | 1 |
| **DF** | Zip anual (224 MB) | Sim | Sim (benefícios, eventuais, judiciais, licença-prêmio) | Sim (`TETO REDUTOR`) | 2013 a 2026-09 | 1 |
| **PB** | API documentada, 1.000 por página | Sim | Parte fixa e variável | Sim (`valorRedutor`) | 2021-01 a 2026-09 | 1–2 |
| **RN** | API interna: lista de órgãos + CSV por órgão (46 por mês) | Sim | Pouco | Sim (`RedutorArt.37/CF`) | 2010 a 2026-09 | 1–2 |
| **GO** | CKAN, CSV mensal (73 MB) | Sim | Não tem coluna de indenizações (há a lista de rubricas) | Sim (`VALR_CORTE_TETO`) | 2012 a 2026-10 | 2 |
| **MS** | CKAN, CSV mensal | Sim | Base e "outras verbas" | Não | 2018-01 a 2026-10 | 1 (**no site, só bruto**) |
| **MA** | DKAN, CSV mensal | Sim | Total, 13º, férias | Não | 2019 a 2026-10 | 1–2 (**no site, só bruto**) |
| **SC** | API interna: lista ordenada pelo bruto (20 por página) + contracheque de cada um (o CSV passou a vir vazio) | Sim | Sim, no contracheque (atrasados, indenizações, 13º, férias) | Não | 2016– | 2 (**no site, só bruto**) |
| **AL** | API interna: lista do mês (só o líquido) + histórico de cada servidor (as partes do bruto) | Sim | Sim | Sim (`teto_redutor`) | 2012 a 2026-10 (set/2026 vazio) | 2 (**no site**) |
| **CE** | CSV mensal estático, sem cabeçalho | Sim | Só no detalhe por servidor (que tem desafio anti-robô) | Sim (a 6ª coluna, conferida na página do servidor) | 2013-02 a 2026-09 | 2 (**no site**) |
| **PI** | API OpenAPI, 100 por página; CSV de até 50 mil linhas | Sim, com filtros | Básica, variável, eventual | Não | 2022 a 2026-10 | 2 (**no site, só bruto**) |
| **RO** | CSV mensal por POST, com token do próprio formulário | Sim | Só no detalhe | Não visto | 2016 a 2026-10 | 2 (**no site, só bruto**) |
| **SP** | CSV corrente + histórico em RAR | Sim | Em parte (indenizações junto com o abono) | Sim (`REDUTOR SALARIAL`) | 2012 a 2026-03 (parado desde maio) | 2 |
| **MG** | CKAN, CSV mensal | Sim, mas o servidor recusa download por script (403) | Indenizações misturadas em "eventual" | Sim (`teto`) | 2012 a 2026-09 | 2 / 4 |
| **RR** | API interna: CSV de bruto e líquido + JSON com as rubricas (lento) | CSV, sim | Sim, no JSON | Não achei nenhuma rubrica de teto | 2011 a 2026-09 | 2–3 |
| **PA** | API interna, 1.000 por página (o export pede captcha) | Sim | Só no detalhe | Não visto | 2016 a 2026-10 | 2–3 |
| **AC** | Tabela da página por POST, com o token do formulário | Sim | Só no detalhe | Junto com "outros descontos" | 2015 a 2026-07 | 3 |
| **SE** | API interna por órgão, 50 por página; inativos em PDF | Lento | Só os proventos | Não (desconto único) | 2021-12 a 2026-10 | 3 |
| **RS** | Painel Power BI, com botão de download sem endereço direto | Parcial | Não (indenizações fora da folha) | ? | — | 3 |
| **TO** | Tela Vaadin, exige 2 filtros; botão "Exportar" só pelo navegador | Não confirmado | ? | ? | — | 4 |
| **AM** | Sem folha consolidada; cada um dos 99 órgãos publica a sua, quase sempre em PDF | Não | Não | No formato padrão (`DESC.TETO`) | Varia | 4–5 |
| **BA** | Só painel Power BI | Não | ? | ? | — | 4 |
| **RJ** | Consulta nominal; o portal não abriu nos testes | Não confirmado | ? | ? | — | ? |
| **MT** | Consulta com reCAPTCHA v3; nenhum dado aberto de folha | — | — | — | 2010–2026 na tela | **Bloqueado** |
| **AP** | As três consultas de folha têm reCAPTCHA v2 | — | — | — | — | **Bloqueado** |

O que isso quer dizer:

- **Prontos para entrar como o Paraná (arquivo em lote com o corte pelo teto):** ES (o melhor caso, todas as
  rubricas), PE, DF, PB, RN e GO. Depois, AL e CE (feitos; ver abaixo).
- **Em lote, mas só com o bruto:** SC, MS, MA, PI, RO. Dá para contar quem passa do teto, não de onde vem o extra.
  Em AC, PA, RR e SE dá para baixar a lista do mês e pedir o detalhe só de quem passa do teto (umas poucas
  centenas de chamadas por mês), que é o que a própria página faz ao abrir cada servidor.
- **Precisam de navegador, de download à mão ou de pedido por LAI:** TO e RS (painéis), MG (o servidor recusa
  scripts; dá para o usuário baixar no navegador), AM (consolidar 99 órgãos) e BA. **MT e AP** só têm a folha
  atrás de captcha, numa consulta por vez: resolver o captcha à mão não leva ao arquivo inteiro, então o caminho é
  o pedido por LAI do arquivo completo (MT: SEPLAG-MT ou TCE-MT; AP: Secretaria de Administração).
- **RR** paga vencimentos de R$ 58 a 65 mil sem nenhuma rubrica de corte pelo teto no arquivo: vale perguntar
  ao estado.

### Feito em 22/11/2026: ES, PE, PB, GO e DF

`uv run supersalarios-estados` passou a ler, além do Paraná, o Espírito Santo, Pernambuco, a Paraíba, Goiás e o
Distrito Federal (12 meses cada; Goiás, 10, porque os meses de 2025 só estão num arquivo anual consolidado). O Rio
Grande do Norte já tem o leitor, mas a API do estado limita os pedidos e a carga leva horas: entra quando tiver pelo
menos 6 meses (o comando não publica estado com menos).

Regras que vieram da conferência:
- **Empresas estatais ficam de fora** (Caesb, BRB e Terracap no DF; Cagepa na PB; Celepar e Cohapar no PR…). O teto
  só vale para a estatal que recebe dinheiro do Tesouro para pagar pessoal (Constituição, art. 37, § 9º), e os arquivos
  não dizem quais recebem. Com elas, o DF dava R$ 94 mi acima do teto em 12 meses; sem elas, R$ 38 mi.
- **13º e férias**: no DF eles vêm dentro das verbas eventuais, com nomes como "DEC TERCEIRO-ATIVO"; o detalhamento por
  rubrica diz quanto tirar (antes da correção, dezembro de 2025 tinha 7.351 acima do teto; depois, 683).
- **ES**: o arquivo vem rubrica a rubrica, com estornos lançados como desconto (um "SUBSÍDIO" do lado do desconto);
  pagamento de competência dois meses ou mais antes da folha conta como atrasado. "ABATE TETO RGPS" é o teto do regime
  geral, para a contribuição, e não entra.
- **Goiás** não publica o imposto de renda nem separa as partes: dá para contar quem passa do teto, não de onde vem.

Resultado (12 meses, órgãos sem as estatais): Pernambuco R$ 101 mi (Secretaria da Fazenda, 606 de 960 vínculos acima
do teto num mês típico), Goiás R$ 68 mi em 10 meses (a fiscalização da Receita e a Defensoria), Paraná R$ 65 mi, DF
R$ 38 mi (a Procuradoria-Geral, 197 de 682), Paraíba R$ 20 mi e Espírito Santo R$ 4,5 mi (18 vínculos num mês típico:
o abate-teto do ES corta de verdade).

### Feito em 22/11/2026: CE e AL

**Ceará.** O CSV mensal não tem cabeçalho; as colunas foram conferidas com a página de um servidor, que mostra as
mesmas contas com nome: descontos totais, **abatimento pelo teto**, outros descontos (previdência, imposto e
consignados juntos), bruto, líquido e diárias. A conta é bruto menos o abatimento. O arquivo não separa as partes,
nem as férias, nem o imposto (fica sem a conta do imposto, como Goiás). Dois cuidados:
- **novembro fica de fora**: o 13º sai na folha de novembro, dentro do bruto (em 2025, 3.171 vínculos acima do teto,
  contra uns 1.300 nos outros meses; a página de um professor mostra "DECIMO TERCEIRO SALARIO" naquele mês);
- o arquivo do mês corrente aparece antes de completo (outubro de 2026 tinha 689 vínculos): mês com menos de 50 mil
  vínculos ativos não entra.
Abril de 2026 também salta (R$ 42 mi acima do teto, contra uns R$ 9 mi), espalhado por vários órgãos: parece
pagamento atrasado ou bônus, e fica, como os atrasados dos outros estados. Resultado (set/2025 a set/2026, sem
novembro): R$ 130 mi acima do teto; a **Secretaria da Fazenda tem 972 de 1.066 vínculos acima do teto** num mês
típico, depois de o estado aplicar o próprio abatimento (o "prêmio por desempenho fiscal" e o adicional de férias
passam por fora do corte). De setembro a outubro de 2025 eram uns 660 vínculos acima do teto; a partir de dezembro,
uns 1.300.

**Alagoas.** Os zips anuais param em 2023. A página de pessoal chama duas APIs: a lista do mês (uma linha por
vínculo, só com o líquido, ordenável) e o histórico de cada servidor, com remuneração base, comissão, benefícios,
eventuais, horas extras, judiciais, teto redutor, imposto e previdência mês a mês. O líquido é o bruto menos imposto e
previdência; numa amostra de 60 vínculos entre R$ 18 mil e R$ 25 mil líquidos, o maior bruto foi R$ 36,5 mil. Então
só se busca o histórico de quem tem líquido de R$ 25 mil ou mais (uma vez por servidor, serve para todos os meses);
os outros entram só na contagem. "Eventuais" ficam fora (é onde aparece o terço de férias), o mês 13 (o 13º) também.
Setembro de 2026 veio vazio na API.

### Feito em 22/11/2026: os só-bruto (MS, MA, PI, RO, SC)

Nenhum dos cinco mostra o corte pelo teto. O valor é o bruto, e parte do que passa do teto pode ter sido descontada
depois: em MS, os descontos obrigatórios dos auditores da Fazenda passam muito do imposto e da previdência, sinal de
um abate que o arquivo não mostra. Por isso o site os põe numa lista à parte ("Só o salário bruto", com barra
listrada) e não os soma aos estados com o corte; na página de cada estado o texto diz "salário bruto acima do teto".
Também não há a conta do imposto (vem somado à previdência ou sobre tudo).

- **MS**: CSV mensal (CKAN). Remuneração base + "outras verbas", que junta tudo; não separa 13º e férias (nenhum mês
  salta). Janeiro de 2026 veio com 40 mil vínculos, contra uns 56 mil nos outros.
- **MA**: CSV mensal (DKAN), com o certificado sem o intermediário: o pipeline recebe o YE1 e a raiz nova "Root YE"
  (assinada pela ISRG Root X2) da própria Let's Encrypt, sem desligar a verificação. As **férias vêm dentro** do total
  de vantagens (conferido mês contra mês: a diferença no total é igual à coluna de férias) e são tiradas. O **13º de
  junho vem só na coluna própria**, fora do total (o total de junho não muda); o de **dezembro vem dentro do total, com
  a coluna zerada** (o total dos ativos vai de uns R$ 530 mi a R$ 982 mi): dezembro fica de fora.
- **PI**: o CSV da API em faixas de bruto (a API recusa mais de 50 mil linhas). Básica + variável; a "eventual" (13º,
  férias) fica fora. O mês não publicado responde HTTP 400.
- **RO**: o CSV do botão da página (POST com o token do formulário). Só o bruto; junho e dezembro ficam de fora (as
  parcelas do 13º: 587 e 627 acima do teto, contra uns 450).
- **SC**: o CSV de exportação passou a vir vazio. A página chama a lista dos ativos ordenada pelo bruto (20 por
  página) e o contracheque de cada um, que separa atrasados, verbas indenizatórias, 13º e férias. Só se busca o
  contracheque de quem tem bruto acima do teto; os outros vínculos entram na contagem pelo total de cada órgão.


**RN** entrou com 6 meses (mai a out/2026): a API do estado limita os pedidos, e daqui a carga levou mais de 4 horas
para 6 meses; no Actions (teste de 22/11/2026), o mesmo mês saiu em minutos. Os meses que faltam entram pela carga mensal.
O topo da página soma os estados com o que cada um tem (até 12 meses: RN com 6, GO com 10).

## Legislativo federal: Câmara, Senado e TCU (feito em 23/11/2026)

`uv run supersalarios-legislativo` lê as três folhas (o levantamento completo, com o Legislativo estadual e as
prefeituras, está nas notas da sessão, `legislativo-prefeituras.md`):

- **Câmara**: um CSV por mês nos relatórios consolidados da transparência, sem nome e sem CPF. O endereço do mês varia
  (`outubro-de-2026-csv`, `fevereiro-de-2026-1`): o leitor lê os links da página do ano e fica com o que é CSV.
  Ativos pelo grupo funcional (deputados, efetivos, natureza especial, secretários parlamentares, estagiários).
- **Senado**: a API de dados abertos administrativos. A remuneração não diz quem é ativo, e o `sequencial` dela não casa
  com o cadastro; casa pelo nome com as listas de ativos e inativos da mesma API (só na memória). Quem se aposentou
  depois do mês conta como ativo.
- **TCU**: a API da consulta de remuneração, servidores ativos e autoridades ativas (ministros, ministros-substitutos e
  procuradores do MP junto ao TCU, no formato do contracheque nacional). O sinal do abate-teto muda de um grupo para
  outro: vale o valor absoluto.

A conta é por pessoa no mês (folha normal e complementar somadas; a complementar conta como atrasado), só ativos, sem
13º, terço de férias, abono de permanência e diárias. Resultado (nov/2025 a out/2026): Câmara R$ 117 mi (2.031 de
2.597 efetivos acima do teto num mês típico), Senado R$ 91 mi (1.292 de 2.245 efetivos), TCU R$ 90 mi (1.284 de 2.228
servidores e os 19 ministros e procuradores; os servidores, quase todos pelos auxílios: o salário chega ao teto e o auxílio-alimentação e o ressarcimento do plano de
saúde passam dele). Deputados e senadores só passam pelos auxílios e indenizações (98 de 529 deputados e 7 de 79 senadores num mês típico).

**Mudança em meados de 2026**: a partir de jul/ago, na Câmara e no Senado, centenas de servidores passam do teto só com
o salário, as vantagens pessoais e a função, mesmo depois do corte (a Câmara corta 2.071 linhas exatamente em
R$ 46.366,19 em out/2026, mas centenas ficam em valores fixos acima, como R$ 56.058,87 e R$ 51.429,54). A folha não diz
por quê; vale perguntar às duas Casas.

No Actions (`supersalarios-legislativo.yml`, todo dia 22), com o cache no release `dados-supersalarios-legislativo`.

### CE, AL e PI fora do GitHub (23/11/2026)

Os três recusam os servidores do GitHub e também um servidor de casa na Europa (CE com HTTP 403; AL e PI sem aceitar a
conexão), mas respondem de uma máquina com conexão residencial que eles aceitam: tudo indica que só aceitam endereços
do Brasil. A carga mensal deles roda nessa máquina, no dia 24, pela conexão normal, sem proxy
(`.github/scripts/fora-do-github/`: o script e o timer do systemd). Ela baixa do release o cache dos três, roda a
carga e, se entrou mês novo, sobe o cache de volta; no dia 25, o `supersalarios-estados.yml` monta o arquivo com eles e
abre o pull request. Não se passa por proxy nem se troca de endereço para chegar aos portais.

## Prefeituras: piloto na Paraíba (feito em 23/11/2026)

`uv run supersalarios-municipios` lê a folha dos 223 municípios no ZIP anual do TCE-PB (Sagres; o ano passado e o
atual, uns 180 MB, lidos direto do ZIP e apagados). No município, o teto é o **subsídio do prefeito** (art. 37, XI), que
sai da própria folha (eletivos, cargo com "PREFEIT" e sem "VICE", pela mediana dos meses; 10 municípios não o têm e
ficam de fora). Os procuradores seguem o do **desembargador** (90,25% do STF; RE 663.696).

O arquivo traz um valor só por vínculo e mês, sem separar 13º, férias e indenizações, e sem o corte pelo teto. A conta
usa o **valor típico** de cada vínculo, a mediana dos meses em que aparece (pelo menos 3), e não o de cada mês; o que
passou é (típico − teto) × meses. Fica fora dezembro, além dos eleitos, aposentados e pensionistas. É um máximo, porque
o valor típico pode trazer indenizações.

Resultado (set/2025 a set/2026): **172 vínculos acima do salário do prefeito** num mês típico, em 44 dos 213 municípios
com o prefeito na folha, R$ 10,1 mi em 12 meses: médicos (86), auditores e fiscais (51), procuradores (20, todos em João
Pessoa, acima do desembargador), professores (7). João Pessoa tem 60 (prefeito R$ 34 mil), R$ 4,8 mi.

O site mostra os números de um município só com pelo menos 5 acima do teto (e os grupos dentro dele, como os
procuradores, também só com 5); abaixo disso, diz "menos de 5". Carga mensal no Actions (`supersalarios-municipios.yml`,
dia 23): o TCE-PB responde de fora do Brasil. O próximo seria o TCE-CE, que separa as rubricas e traz o subsídio do
prefeito em cada folha (mas só aceita IP do Brasil: teria de rodar na máquina de casa).

