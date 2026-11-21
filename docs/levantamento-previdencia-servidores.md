# Previdência dos servidores: o que o Ministério publica

Levantamento de 21/11/2026, para o bloco 3 do plano ("Riscos e qualidade do gasto"). A pergunta:
quanto falta no fundo de aposentadoria dos servidores (o regime próprio de previdência, RPPS) de cada
prefeitura e de cada estado, e que nota o Ministério da Previdência dá a ele.

## Quem tem fundo próprio

Todos os 26 estados e o Distrito Federal, e **2.106 das 5.569 prefeituras** (38%). As outras 3.463
põem os servidores no INSS, como qualquer empregador, e não têm esse rombo: pagam a contribuição de
patrão e o INSS paga a aposentadoria. Dessas, 34 estão fechando o fundo próprio (os servidores novos já
vão para o INSS, e a prefeitura continua pagando quem se aposentou pelo regime antigo) e 481 tiveram um
fundo e voltaram de vez ao INSS.

Ter fundo próprio é mais comum quanto maior a cidade: 29% das cidades com até 10 mil moradores, 45% das
de 20 a 50 mil, 77% das de 100 a 500 mil e todas as 43 com mais de 500 mil (as 26 capitais têm).

## As fontes

| O quê | Onde | Acesso |
|---|---|---|
| Índice de Situação Previdenciária (ISP-RPPS), resultado final | [página do ISP](https://www.gov.br/previdencia/pt-br/assuntos/rpps/indice-de-situacao-previdenciaria), planilha anual (`resultado-final-isp-2025-…xlsx`, 3,5 MB) | aberto, sem cadastro |
| Cadastro das unidades gestoras (qual ente tem RPPS, qual está extinguindo, qual voltou ao INSS) | [Estatísticas e informações dos RPPS](https://www.gov.br/previdencia/pt-br/assuntos/rpps/estatisticas-e-informacoes-dos-rpps-1/estatisticas-informacoes-dos-rpps), `cnpj-ente-cpnj-ug-…csv` (atualizado até 31/07/2025) | aberto |
| API do CADPREV (DRAA, DIPR, DAIR de cada ente) | `apicadprev.trabalho.gov.br` | **verificação anti-robô (AWS WAF)**: não usado |
| Consulta do CRP de cada ente no CADPREV | `cadprev.previdencia.gov.br/…/pesquisarEnteCrp.xhtml` | **reCAPTCHA**: não usado |
| Situação do CRP dos estados e das capitais | PDF mensal na página do CRP | aberto, mas só 53 entes |
| Anuário (suplemento dos RPPS), zip de estados e municípios | página de estatísticas | o link de 2026 respondeu 403 |

A planilha do ISP basta: além da nota, ela traz em cada aba os números usados na conta, ente por ente.

## O que a planilha do ISP 2025 traz

Publicada em 04/12/2025 (Portaria SRPC/MPS nº 2.416, de 1º/12/2025). Uma linha por ente com fundo
próprio: 2.133 (27 estados e DF, 2.106 prefeituras). Identifica pelo nome ("ABADIA DE GOIÁS - GO") e
pelo CNPJ, sem o código do IBGE; o nome bate com o do IBGE em todos os casos menos dez, que ficam numa
lista de apelidos no programa.

- **A nota final**, de A a D. Junta três notas: gestão e transparência (regularidade, envio de
  informações, certificação da gestão), finanças e liquidez (o que entra frente ao que sai, se o
  dinheiro guardado cresceu, se há plano para cobrir o rombo) e atuária (quanto do compromisso tem
  dinheiro guardado, o tamanho do compromisso frente à receita, se fez a reforma da previdência e criou
  a previdência complementar). Em 2025: 32 com A, 459 com B, 756 com C e 886 com D.
- **Provisões matemáticas** (aba COBERTURA): quanto o fundo calcula, na avaliação atuarial do ano (o
  DRAA, feito por um atuário contratado pelo próprio fundo, com data-base 31/12/2024), que precisaria
  ter hoje para pagar as aposentadorias e pensões já prometidas. Vêm separadas em plano previdenciário
  (o que deveria ter dinheiro guardado), plano financeiro e benefícios mantidos pelo Tesouro (pagos com
  o caixa de cada ano, sem fundo; costumam ser os servidores mais antigos).
- **Dinheiro aplicado** em 31/12/2024 (o DAIR).
- **Servidores ativos, aposentados e pensionistas** (aba GRUPOS).
- **O que entrou e saiu no ano** (aba SUFICIÊNCIA): contribuições e benefícios de 2024, do RREO ou do DIPR.
- **Receita corrente líquida** de 2024 (a aba SUSTENTABILIDADE traz 60% dela; confere com o RGF dos
  estados que o site já tem).

**Não traz** o déficit atuarial como o próprio DRAA o apresenta, com o plano de amortização descontado.
O site usa provisões menos dinheiro aplicado, a mesma conta do indicador de comprometimento atuarial do
ISP. É o rombo antes das contribuições extras que o fundo tenha aprovado para cobri-lo nas próximas décadas.

## Os buracos

- 429 entes ficaram sem as provisões de 2025 (não entregaram o DRAA, ou ele não foi aceito). Para 205
  deles há o DRAA de 2024, na planilha do ISP 2024, e o site usa esse, dizendo o ano. Ficam sem número
  224, entre eles os estados de **São Paulo, Minas Gerais e Rio Grande do Norte**, que não entregaram nem
  o de 2024 nem o de 2025.
- Em 5 prefeituras o dinheiro aplicado declarado passa de três anos de receita (Paranaguá declara
  R$ 5,8 bi aplicados com receita de R$ 1,1 bi): quase certamente erro de preenchimento. O site não
  calcula o rombo nesses casos. Em 9 a receita corrente líquida fica abaixo de R$ 1.500 por morador
  (declaração de parte do ano); o site não compara com a receita, a mesma regra do gasto com pessoal.
- O CRP de cada ente só sai pela consulta com captcha. A nota de regularidade do ISP cobre em parte.

## Os números (ISP 2025)

| | Com o número | Precisariam ter | Têm aplicado | Faltam |
|---|---|---|---|---|
| Estados e DF | 24 de 27 | R$ 1,75 tri | R$ 89 bi | R$ 1,66 tri |
| Prefeituras | 1.880 de 2.106 | R$ 1,42 tri | R$ 253 bi | R$ 1,17 tri |

Em anos de receita corrente líquida, a mediana das prefeituras com fundo é 1,2 ano (metade fica entre
0,7 e 1,9) e a dos estados, 1,8. Exemplos: cidade de São Paulo, R$ 141 bi (1,5 ano de receita, nota B);
Fortaleza, R$ 25 bi (2,2 anos, D); Campinas, R$ 20 bi (2,6 anos, C); Ariquemes (RO), R$ 137 mi
(3 meses, B); Rio Grande do Sul, R$ 111 bi (1,8 ano, B); Rio de Janeiro (estado), R$ 234 bi
(2,5 anos, C); Distrito Federal, R$ 180 bi (5 anos, C).

## Cuidados no texto

- O rombo é uma **projeção de décadas**, feita pelo próprio fundo com premissas (juros que o dinheiro
  vai render, crescimento dos salários, quanto tempo as pessoas vivem) que mudam muito o resultado.
- **Não somar à dívida.** A dívida consolidada é dinheiro já emprestado, com prazo e juros; o rombo é o
  valor de hoje de pagamentos futuros, ainda sem as contribuições que vão entrar.
- Boa parte do rombo dos estados e das capitais está no **plano financeiro**, um grupo que o governo já
  decidiu pagar com o caixa de cada ano, sem fundo. Ali, o rombo é esperado.

## Como atualizar

`uv run previdencia` acha na página do ISP as planilhas "resultado final" dos dois anos mais recentes
(a de 2026 deve sair no começo de dezembro de 2026) e o cadastro mais recente. Se o site do Ministério não
responder ou a planilha mudar de formato, a publicação usa a cópia em `pipeline/referencia/previdencia.json`.
