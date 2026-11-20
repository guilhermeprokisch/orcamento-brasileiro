# Para quem as prefeituras e os governos estaduais pagam: onde baixar

Levantamento de 20/11/2026. Em quais estados dá para baixar, de uma vez e sem cadastro, os gastos das prefeituras e do governo estadual com o nome (ou o CNPJ) de quem recebeu.

Hoje o site sabe **o que foi contratado** (PNCP). Isto aqui diz **quanto foi empenhado e pago, e a quem**, que é o dinheiro que de fato saiu, inclusive o que não passa por contrato publicado no PNCP.

## Resumo

- **Prefeituras, com download em massa e nome do credor:** PB, RS, SP, PR, ES. Somam 1.841 das 5.570 prefeituras (33%).
- **Prefeituras, por API (uma chamada por município e mês):** CE, AM e PE, com nome; RJ, RN e MA só com o CNPJ, sem o nome.
- **Governos estaduais com arquivo aberto:** RS, ES, PR, MG, MS, MT, GO, DF, BA, SC, PE, AL (até 2023) e AM.
- **Nada aproveitável encontrado:** prefeituras de MG (atrás de login com captcha), SC, MS, MT, GO, TO, BA (só tela), AL, SE, PA, AC, RO, RR e AP.

Parte do levantamento automático rodou fora do Brasil, e vários sites do Norte e do Nordeste recusaram o acesso. Retestado de um endereço brasileiro em 20/11/2026: o TCE-PE funciona (veja a tabela) e a API do TCE-RN responde; o TCE-RO continua recusando (403) e os sites do TCE-AL e do TCE-AP não respondem. AC, PA, RR, MA, PI e os portais estaduais que falharam ainda precisam ser revistos daqui.

## Estado por estado

"Credor" é quem recebeu o dinheiro. "Empenho" é a reserva do dinheiro para um gasto; depois vêm a liquidação (o serviço foi entregue) e o pagamento.

| UF | Prefeituras | Governo estadual | Observações |
|---|---|---|---|
| **PB** | **Sim.** TCE-PB, um ZIP por ano com todas as prefeituras: `download.tce.pb.gov.br/dados-abertos/dados-consolidados/despesas/despesas-{ANO}.zip`. 2003–2026. Nome, CPF/CNPJ, empenhado, liquidado e pago. 2025: 192 MB. | **Sim.** API em `api.dados.pb.gov.br` (campos não conferidos). | Conferido: o arquivo de 2025 baixa (HTTP 200, 192 MB). |
| **RS** | **Sim.** TCE-RS, um ZIP por ano: `dados.tce.rs.gov.br/dados/municipal/empenhos/{ANO}.csv.zip`. 2004–2026. Empenho, liquidação e pagamento em linhas separadas, com nome, CPF/CNPJ, elemento, histórico, licitação e contrato. | **Sim.** dados.rs.gov.br, `{ANO}-despesa-do-estado`, ZIP mensal, com favorecido e CNPJ. | Conferido: 2025 baixa (1,35 GB). O arquivo de um ano traz também empenhos de anos anteriores pagos naquele ano. |
| **SP** | **Sim.** TCE-SP (Audesp), um ZIP por ano: `transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ANO}.zip`. 2008–2025. Cada linha é uma fase (empenhado, liquidado ou pago), com nome e CPF/CNPJ. | **Parcial.** Só totais por credor, por um serviço SOAP da Fazenda. | Conferido: 2025 baixa (2,1 GB, atualizado em 18/11/2026). **Não inclui a capital**, que é do TCM-SP. |
| **PR** | **Sim.** TCE-PR (PIT), um ZIP por ano: `pit.tce.pr.gov.br/Arquivos/{ANO}_PIT_TodosArquivos.zip`. 2013–2026. Dentro, um ZIP por município, em XML; o empenho tem nome e CNPJ, o pagamento se liga ao empenho. Inclui Curitiba. | **Sim.** Fazenda-PR, CSV anual 2023–2026. | Conferido: 2025 baixa (1,4 GB). XML aninhado e com alguns campos trocados no arquivo de pagamentos; dá mais trabalho. |
| **ES** | **Sim.** TCE-ES no dados.es.gov.br, `tcees-empenho`: CSV, 2017–2026, com nome e CNPJ do credor e o saldo mensal de cada empenho. | **Sim.** dados.es.gov.br, `Despesas-{ANO}.csv`, 2004–2026, com favorecido e CPF/CNPJ. | Arquivos pequenos. |
| **CE** | **Sim, por API.** TCE-CE (SIM): `api-dados-abertos.tce.ce.gov.br/sim/notas_empenhos`, 2008–2026, com nome, CPF/CNPJ, valor e histórico. Pagamentos à parte, ligados pelo número do empenho. | Não confirmado (portal com bloqueio anti-robô). | Conferido: a API devolve os dados com o nome do credor. 1.000 registros por chamada, uma chamada por município e mês. |
| **AM** | **Sim, por API.** TCE-AM (eContas): empenhos e pagamentos por unidade e mês, com nome e CNPJ. Desde 2014. | **Sim.** A mesma API cobre os órgãos do estado. | Uma fonte para os dois níveis de governo. Uma chamada por unidade e mês. |
| **PE** | **Sim, por API.** TCE-PE: `sistemas.tcepe.tc.br/DadosAbertos/DespesasMunicipais!json?AnoReferencia={ANO}&MESREFERENCIA={MÊS}`. Uma linha por empenho, com `FORNECEDOR`, `CPF_CNPJ`, `TIPOCREDOR`, histórico, elemento e empenhado, liquidado e pago. | **Sim.** A mesma API (`DespesasEstaduais`) e o dados.pe.gov.br, "Despesas detalhadas", CSV anual 2008–2026. | Conferido em 20/11/2026: devolveu os dados de janeiro de 2025. Cada chamada traz no máximo 100 mil linhas (61 MB, 90 s), então é preciso fatiar por mês e por município. A API só aceita endereços do Brasil, então o robô de publicação (que roda fora do país) não alcança; baixar daqui e guardar no bucket. |
| **RJ** | **Parcial.** API do TCE-RJ (`dados.tcerj.tc.br/api/v1/empenho_municipio`), 2020–2026, com CNPJ mas **sem o nome**. | **Parcial.** Mesma API (`empenho_estado`), só CNPJ. | Não inclui a capital (TCM-RJ). O nome teria de vir do cadastro de CNPJ da Receita. |
| **RN** | **Parcial.** API do TCE-RN, com CNPJ e valor, sem o nome. Desde 2018. | Parcial (mesma API). | Uma chamada por unidade. |
| **MA** | **Parcial.** API do TCE-MA, 2023–2026, empenhos e pagamentos do estado inteiro, só com o CPF/CNPJ. | Não confirmado. | Pagina bem (5.000 por chamada). |
| **PI** | **Fraco.** Só o total do ano por nome de credor, sem CNPJ. | O mesmo tipo de total. | |
| **MG** | **Não confirmado.** Os dados abertos do TCE-MG pedem login com captcha. | **Sim.** dados.mg.gov.br, `portal_despesa_empenho`, 2022–2026, com razão social e CNPJ. | |
| **SC** | **Só tela** (painel do TCE-SC). | **Parcial.** dados.sc.gov.br, `empenhos`, 2021–2026, com nome e CNPJ. | |
| **MS** | Não encontrado. | **Sim.** dados.ms.gov.br, `despesas-por-credor-mensal`, 2012–2026. | |
| **MT** | Não (painel sem credor). | **Sim.** `consultas.transparencia.mt.gov.br/dados_abertos/despesa/Despesa_{ANO}.csv`, 2010–2026, com fase, nome e CPF/CNPJ. | |
| **GO** | Não (painel do TCM-GO). | **Sim.** dadosabertos.go.gov.br, `empenhos`, 2003–2026, com nome e CPF/CNPJ. | |
| **DF** | Não se aplica. | **Sim.** `transparencia.df.gov.br/arquivos/portal-dados-abertos/Despesa_{ANO}.zip`, 2009–2026. | |
| **BA** | Só tela (TCM-BA, exporta PDF, captcha). | **Sim.** dados.ba.gov.br, `empenhos.zip` e `pagamentos.zip`, com nome e CPF/CNPJ. | |
| **AL** | Não encontrado. | **Parcial.** Ordens bancárias com favorecido, só até 2023. | |
| **TO** | Só tela. | Só tela. | |
| **SE** | Não encontrado. | Não (só totais por classificação). | |
| **PA, AC, RO, RR, AP** | Não encontrado ou fora do ar daqui. | Não verificado. | Testar de um endereço brasileiro. |

As linhas de PB, RS, SP, PR e CE foram conferidas por mim, baixando ou consultando de verdade. As demais vêm de dois agentes que abriram os arquivos ou as APIs. MS, MT e os governos estaduais de GO, BA, MG e DF não foram conferidos de novo.

## Por onde começar

1. **Paraíba.** Um arquivo de 192 MB por ano já traz as 223 prefeituras, com nome, CNPJ e os três valores. É o mais barato de trazer e serve para desenhar como isso aparece no site.
2. **Rio Grande do Sul.** As 497 prefeituras, com o vínculo à licitação e ao contrato, e o governo estadual no mesmo estado. Permite cruzar com os contratos do PNCP.
3. **São Paulo.** 644 prefeituras (todas menos a capital): a maior cobertura de uma vez só. O arquivo tem 2 GB por ano, então o processamento tem de ser em partes.

Depois: PR (XML, dá mais trabalho), ES (pequeno) e as APIs do CE e do AM. Com PB, RS, SP, PR e ES, o site cobriria um terço das prefeituras do país.

## O que isso permite no site

- Na página da cidade: "Para quem a prefeitura mais pagou", com o valor pago em 2025 e a empresa. Hoje só mostramos o que foi contratado no PNCP.
- No explorador de contratos: ao lado do valor do contrato, quanto já foi pago a aquela empresa.
- Comparar o que foi contratado com o que foi pago, e achar quem recebe muito sem contrato publicado.

## Cuidados

- **CPF.** Esses arquivos trazem o CPF de pessoas físicas (servidores em diárias, autônomos, aluguéis). Seguindo a regra do projeto, o CPF não entra nos dados tratados nem no site. O nome pode aparecer, como já acontece nos contratos.
- **Folha de pagamento e repasses.** Boa parte do valor pago vai para o INSS, para o regime próprio de previdência, para bancos (consignados) e para a própria folha. Para falar de fornecedores, é preciso separar esses credores, como já fazemos com as categorias que "não são gasto" nos contratos.
- **Fases.** Somar empenhado, liquidado e pago juntos conta o mesmo dinheiro três vezes. Usar o **pago** como número principal.
- **Tamanho.** Os arquivos de RS, SP e PR têm de 1,3 a 2,1 GB por ano. Os brutos vão para o bucket, e o site lê só um resumo ou um Parquet já tratado, como nos exploradores.
