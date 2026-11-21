# O caminho dos impostos: levantamento

Novembro de 2026, para o bloco 2 do plano ("O caminho dos impostos"). A pergunta: **eu pago imposto para quem, e
para onde vai?** O diagrama é do Brasil inteiro, todos os governos somados, em 2025 (o último ano fechado). Todos os
números abaixo saíram dos arquivos baixados; o comando que monta tudo é `uv run --project pipeline caminho-impostos`.

## O desenho

Três colunas, ligadas por fluxos de largura proporcional ao dinheiro:

1. **O que se paga**: cada imposto (imposto de renda, INSS, Cofins, ICMS, ISS…), mais os royalties do petróleo e da
   mineração, que não são imposto mas são divididos por lei do mesmo jeito.
2. **Quem cobra**: União, estados (com o Distrito Federal) e prefeituras.
3. **Quem fica com o dinheiro no fim**: os mesmos três, depois dos repasses, e os fundos regionais de crédito
   (FNE, FNO e FCO), que recebem uma parte fixa do imposto de renda e do IPI.

Entre a coluna 2 e a 3, cada repasse é uma ligação própria: FPE, FPM, IPI-exportação, ITR, royalties, salário-educação,
a parte da União no Fundeb, a cota das prefeituras no ICMS e no IPVA, a redistribuição do Fundeb dentro de cada
estado e os repasses para programas (SUS, merenda, convênios, emendas). A ligação de cada governo para ele mesmo
("fica com quem cobrou") é o que sobra depois de repassar.

Fora do diagrama principal, um galho **"o que deixa de entrar"**: os benefícios fiscais (isenções, regimes
especiais) que a Receita Federal estima no Demonstrativo dos Gastos Tributários e, nos estados, os incentivos de ICMS.

## Como cada real é contado (para não contar duas vezes)

- **Cada real entra uma vez só, na coluna 1**, no governo que cobra o imposto. O FPM, por exemplo, não é um imposto
  das prefeituras: é imposto de renda e IPI que a União cobrou. No diagrama ele é a ligação União → prefeituras.
- **Um repasse é sempre uma ligação, nunca um nó novo.** Por isso a soma da coluna 3 (quem fica) é igual à soma da
  coluna 1 (o que se pagou): R$ 4.224 bilhões em 2025.
- **O que fica** com cada governo = o que ele cobrou − o que repassou + o que recebeu. O programa confere que, em
  cada governo da coluna 2, o que entra é o que sai, e que o total pago é o total que fica (se não, ele para com erro).
- **Os repasses são brutos.** O FPE e o FPM chegam com 20% retidos para o Fundeb; a ligação mostra o valor inteiro, e
  a retenção aparece na redistribuição do Fundeb.
- **O Fundeb entra pelo efeito líquido.** Em cada estado, o governo estadual e as prefeituras põem 20% de vários
  impostos e repasses num fundo, e cada um tira de volta pelo número de alunos da sua rede. Em 2025 os estados
  puseram R$ 187 bi e tiraram R$ 109 bi; as prefeituras puseram R$ 94 bi e tiraram R$ 172 bi. Em todos os 26 estados
  o governo estadual perde e as prefeituras ganham (no DF, que não tem prefeituras, o que entra é o que sai). O
  diagrama mostra uma ligação estados → prefeituras de R$ 78 bi, a soma do que cada governo estadual pôs a mais do que
  tirou; pelo lado das prefeituras a soma dá R$ 79 bi. A parte que a União põe no Fundeb (R$ 60 bi) é outra ligação.
- **Um mesmo real pode atravessar dois governos sem aparecer duas vezes.** Os 25% do IPI-exportação que o estado
  passa às prefeituras saem da coluna "quem cobra" dos estados; o IPI-exportação inteiro entra como ligação União →
  estados. A conta de cada governo fecha do mesmo jeito.
- **O que fica de fora**, nos três governos:
  - receitas que não são impostos (dividendos das estatais, concessões, aluguéis, juros do caixa, empréstimos): o
    diagrama é do imposto pago, não de todo o dinheiro que o governo tem para gastar;
  - a contribuição dos servidores à previdência própria deles (na União, R$ 19 bi; nos estados e prefeituras, nas
    contas 1.2.1.5): não passa por repartição nenhuma, e a contribuição do governo como patrão é dinheiro que ele
    paga a si mesmo;
  - as restituições (o imposto devolvido): os valores já vêm sem elas;
  - os repasses entre prefeituras e de prefeituras para estados (menos de R$ 1 bi).

## Fontes

| O quê | Fonte | Lado | Serve? |
|---|---|---|---|
| Arrecadação federal por tributo e repasses por tipo | **Resultado do Tesouro Nacional** (RTN), série histórica, aba 2.2 (anual, R$ milhões correntes), no Tesouro Transparente. A mesma planilha de `/contas` (`contas_federal.py` acha o endereço do mês pela API do CKAN). | quem manda | **Sim.** |
| Impostos de estados e prefeituras e tudo o que cada um recebeu | **SICONFI, Declaração de Contas Anuais (DCA), Anexo I-C** (receitas orçamentárias), no cache `data/raw/siconfi/dca-ic/2025.json.gz` que o FINBRA e o mapa já mantêm. Traz o valor bruto e, em colunas à parte, as deduções para o Fundeb, as cotas das prefeituras e as restituições. | quem recebe | **Sim.** 26 estados, o DF e 5.510 prefeituras com a DCA de 2025; 49 das 60 que faltam entram com a de 2024; as 11 restantes têm 185 mil moradores e ficam de fora. |
| Receita Federal, arrecadação por estado (`arrecadacao-estado.csv`, já usada no mapa) | Arrecadação mensal por tributo e UF | — | Não aqui: não traz royalties nem salário-educação, e é bruta. Fica para a versão por cidade. |
| Transferências constitucionais por município e por tipo (Tesouro) | ver "Benefícios fiscais e fontes ainda a usar" | quem manda | Para a versão por cidade. |

O RTN conta a arrecadação já sem as restituições e o INSS pela arrecadação líquida para o Regime Geral (RTN 1.3). Os
impostos estaduais e municipais entram sem as "outras deduções" da DCA, que são as restituições. As deduções do Fundeb
e das cotas das prefeituras não saem do imposto: viram ligações.

O DF cobra também os impostos de prefeitura (ISS, IPTU, ITBI); entra na coluna dos estados, e as contas do ICMS e do
IPVA das prefeituras são feitas sem ele.

## Contas usadas

**União** (RTN, aba 2.2, 2025): imposto de renda (1.1.03) R$ 867 bi; INSS (1.3, arrecadação líquida do Regime Geral)
R$ 710 bi; Cofins e PIS (1.1.05 e 1.1.06) R$ 497 bi; CSLL R$ 178 bi; imposto de importação R$ 90 bi; IPI R$ 88 bi;
IOF R$ 86 bi; outros tributos federais (CIDE, outras receitas da Receita Federal e salário-educação) R$ 88 bi; royalties
e participações do petróleo e da mineração (1.4.4) R$ 139 bi. Total: R$ 2.745 bi.

**Estados e DF** (DCA, sem restituições): ICMS com o adicional dos fundos de combate à pobreza (1.1.1.4.50.1 e .2)
R$ 863 bi; IPVA R$ 94 bi; imposto sobre heranças e doações R$ 20 bi; imposto de renda retido dos próprios servidores
(1.1.1.3.03, que a Constituição deixa com o estado) R$ 91 bi; ISS, IPTU e ITBI do DF R$ 6 bi; taxas R$ 52 bi.
Total: R$ 1.125 bi.

**Prefeituras** (DCA, sem restituições): ISS R$ 154 bi; IPTU R$ 80 bi; ITBI R$ 27 bi; imposto de renda retido dos
servidores R$ 55 bi; taxas e contribuição de iluminação pública R$ 38 bi. Total: R$ 353 bi.

**Repasses da União** (DCA, lado de quem recebe, bruto): FPE R$ 205 bi; FPM R$ 240 bi (com as três parcelas extras de
1%); IPI-exportação R$ 9 bi; ITR R$ 4 bi; salário-educação R$ 21 bi; a parte da União no Fundeb R$ 60 bi; outros
obrigatórios (CIDE, IOF-ouro, Lei Complementar 176 no lugar da Lei Kandir e a compensação da Lei Complementar 194 pelo
corte do ICMS dos combustíveis) R$ 8 bi; royalties R$ 70 bi (ver abaixo); fundos regionais R$ 29 bi (RTN 2.2.1,
o repasse total). **Programas**: tudo o mais que estados e prefeituras declararam ter recebido da União (contas 1.7.1
e 2.4.1 menos as de cima): R$ 58 bi para os estados e R$ 158 bi para as prefeituras, a maior parte do SUS.

**Repasses dos estados às prefeituras** (DCA das prefeituras): um quarto do ICMS R$ 209 bi; metade do IPVA R$ 46 bi;
a parte do IPI-exportação, da CIDE e dos royalties do estado R$ 6 bi; Fundeb R$ 78 bi; programas (SUS estadual,
convênios, transporte escolar) R$ 47 bi.

## As pontas fecham?

Cada repasse contado pelos dois lados, 2025, R$ bilhões:

| Repasse | Quem manda diz | Quem recebe declarou | Diferença |
|---|---|---|---|
| FPE, FPM e IPI-exportação | 454,7 (RTN 2.1) | 453,4 | −0,3% |
| Salário-educação | 21,4 (RTN 2.3) | 21,3 | −0,5% |
| Fundeb, a parte da União | 59,7 (RTN 4.3.10) | 59,6 | −0,2% |
| Um quarto do ICMS | 209,1 (25% do ICMS dos estados, sem o DF) | 208,7 | −0,2% |
| Metade do IPVA | 46,0 (50% do IPVA, sem o DF) | 45,8 | −0,4% |
| Fundeb, o que entra e o que sai do fundo | 281,8 (o que estados e prefeituras põem) | 282,2 (o que tiram) | +0,1% |
| Royalties | 70,2 (RTN 2.4) | 41,9 | −40% |
| Royalties, com o lançamento do Rio | 70,2 | 68,2 | −2,8% |

A cota do ICMS bate também estado por estado: as prefeituras de cada estado declararam entre 23,9% (Acre) e 25,5%
(Bahia) do ICMS do estado.

**Royalties**: o governo do Rio de Janeiro, que recebe a maior parte dos royalties dos estados, não lança o dinheiro
como repasse (conta 1.7.1.2), e sim como "demais receitas patrimoniais" (1.3.9, R$ 26 bi em 2025). Por isso a
ligação União → estados usa o lado do Tesouro: o total do RTN 2.4 menos o que as prefeituras declararam (R$ 35 bi),
o que dá R$ 35 bi para os estados.

## Resultado (2025)

| | Cobra | Repassa | Recebe | Fica com | Parte do que se paga: cobra → fica |
|---|---|---|---|---|---|
| União | 2.745 | 860 | — | 1.885 | 65% → 45% |
| Estados e DF | 1.125 | 386 | 331 | 1.070 | 27% → 25% |
| Prefeituras | 353 | — | 886 | 1.240 | 8% → 29% |
| Fundos regionais | — | — | 29 | 29 | — → 1% |

R$ 4.224 bi no total, perto de R$ 19.800 por morador (213 milhões em 2025). A frase do plano ("a União fica com uns
dois terços") vale para quem **cobra**; depois dos repasses a União fica com menos da metade, e as prefeituras, que
cobram 8 de cada 100 reais, ficam com 29.

O "fica com" da União inclui o INSS, que volta quase todo como aposentadoria e pensão do Regime Geral (R$ 1.027 bi
pagos em 2025, mais do que a arrecadação). E o que a União gasta também passa pelo que ela pega emprestado: o
diagrama é só do imposto.

## O que deixa de entrar (benefícios fiscais)

Fica num galho à parte, nunca somado ao que se pagou: é dinheiro que não foi cobrado.

- **União: R$ 569 bi em 2025** (4,5% do PIB), no **Demonstrativo dos Gastos Tributários "bases efetivas" de 2023, com a
  série 2021 a 2026** (Receita Federal, agosto de 2026,
  [planilha](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/renuncia/gastos-tributarios-bases-efetivas/dgt-bases-efetivas-2023-serie-2021-a-2026-quadros.xlsx),
  quadro XXVI). É a estimativa mais nova de 2025: o efetivo vai até 2023 e 2024 a 2026 são projeção. Ainda não há DGT
  "efetivo" de 2025. O DGT que acompanhou o projeto de orçamento de 2025 dava R$ 544 bi (sem a desoneração da folha,
  que ainda estava em votação); o do projeto de 2026 só traz 2026 (R$ 613 bi).
  - Por imposto: imposto de renda R$ 230 bi; Cofins e PIS R$ 156 bi; INSS R$ 98 bi; CSLL R$ 34 bi; IPI R$ 31 bi;
    IOF R$ 11 bi; importação R$ 8 bi. O programa confere que os tributos somam o total do quadro.
  - Os maiores: Simples Nacional R$ 121 bi; cesta básica R$ 42 bi; despesas médicas no imposto de renda R$ 32 bi;
    Zona Franca de Manaus R$ 29 bi; aposentadoria de quem tem doença grave R$ 27 bi; entidades filantrópicas
    (previdência) R$ 23 bi.
- **Estados: R$ 258 bi de ICMS em 2025**, a renúncia que os próprios estados projetam, no **Boletim de Finanças dos
  Entes Subnacionais 2025** do Tesouro (fevereiro de 2026, planilha de tabelas, aba "Gráfico 12": R$ 183 bi por tempo
  determinado e R$ 75 bi por tempo indeterminado). Não inclui Paraná e Maranhão. Em 2024 foram R$ 258,9 bi, perto de
  23% do ICMS. O boletim não dá o valor por estado (só a taxa de 2024, de 56% no Amazonas a menos de 10% em outros).
  Fica como número fixo no programa (`ICMS_RENUNCIA`), com a fonte.
  - Conferido com as leis de diretrizes de três estados: São Paulo prevê R$ 66 bi de ICMS para 2025; Minas, perto de
    R$ 20 bi; Rio Grande do Sul, R$ 12 bi. Somar as 27 leis à mão daria o valor por estado, mas cada uma usa um
    formato e nem todas são fáceis de achar: fica para depois.
  - Um estudo da Fenafisco a partir das LDOs dá R$ 267 bi para 2025, mas só foi visto pela imprensa e o valor de São
    Paulo não bate com a lei paulista: não é usado.

## Fontes para a versão por cidade (depois)

- **Transferências constitucionais da União por estado e por município** (Tesouro Transparente, CKAN,
  `transferencias-constitucionais-para-estados` e `…-para-municipios`): um CSV por mês, `;`, latin-1, por decêndio,
  com FPE, FPM, IPI-exportação, ITR, royalties de cada tipo, a parte da União no Fundeb e a retenção do Fundeb. Os
  municípios vêm só com o nome (sem código do IBGE). O nome de cada arquivo está um mês adiantado em relação ao
  conteúdo. O FPE e o FPM vêm já sem os 20% do Fundeb: somando de volta, dá R$ 205 bi de FPE e R$ 215 bi de FPM
  (sem as parcelas extras de 1%, que vêm numa linha à parte desde julho de 2025; com elas, R$ 241 bi). A DCA dá
  R$ 205 bi e R$ 240 bi.
- O salário-educação não está ali (é do FNDE).

## Para a versão por cidade (depois)

- O lado de quem recebe já está pronto: a DCA de cada prefeitura diz quanto recebeu de cada repasse.
- O lado do imposto federal pago em cada cidade: a arrecadação da Receita Federal por município (`rfb`, camada do
  mapa) e o imposto de renda por cidade de residência (`irpf`).
- Cuidado: a arrecadação federal é registrada onde fica a sede da empresa que paga, não onde mora quem consome. Por
  isso São Paulo, Rio e Brasília "pagam" muito mais do que a renda de quem mora lá; o mapa já avisa disso.
