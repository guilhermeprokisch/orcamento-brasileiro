# Pedidos de acesso à informação: quanto custa o mandato

Para os Tribunais de Contas e as Assembleias Legislativas que não publicam, em dado aberto, o salário e os gastos de
prefeitos, vereadores e deputados estaduais. Levantamento das fontes em
[`docs/levantamento-mandatos-locais.md`](../levantamento-mandatos-locais.md).

Por quê: queremos mostrar quanto cada eleito custa ao Estado (salário, verba de gabinete, assessores e benefícios),
como já fazemos para deputados federais e senadores. Hoje isso está aberto só em 4 tribunais (ES, PB, CE e MA, 702
municípios) e, para a verba nota a nota, em poucas Assembleias. Os outros órgãos já têm os dados: as prefeituras e as
Câmaras mandam a folha ao tribunal todo mês, e as Assembleias pagam e prestam contas da verba.

Como enviar: o pedido sai em nome de uma pessoa (nome, CPF e e-mail), pelo e-SIC do órgão ou por e-mail à ouvidoria
(canais na tabela de cada grupo, conferidos nos sites oficiais em 23/11/2026). Onde houver formulário, prefira o
formulário: o e-mail nem sempre vale como pedido formal, e no TCE-RS, TCE-PR e TCE-AM ele é só para dúvidas. Prazo legal: 20 dias, prorrogáveis por mais 10 (art. 11 da Lei 12.527/2011). Se
negarem, cabe recurso em 10 dias (art. 15).

Um pedido para cada órgão: o modelo serve para todos; troque o nome do órgão e do estado e acrescente, no fim, o
pedido específico da tabela (coluna "Acrescentar").

---

## 1. Tribunais de Contas: a folha das prefeituras e das Câmaras

### Texto do pedido

**Órgão:** [TRIBUNAL]
**Assunto:** Folha de pagamento dos municípios: prefeitos, vice-prefeitos, vereadores e servidores das Câmaras

Com base na Lei nº 12.527/2011 (Lei de Acesso à Informação), solicito os dados da folha de pagamento que este
Tribunal recebe dos municípios do Estado de [ESTADO], de janeiro de 2021 até o mês mais recente disponível, em formato
aberto e editável (CSV, ou acesso por API):

1. Para cada prefeitura e cada Câmara Municipal, a folha mensal com: município, órgão ou unidade (identificando a
   Câmara), nome, cargo, tipo de vínculo (efetivo, comissionado, eletivo etc.), lotação, mês de referência e os valores
   pagos, separados por rubrica (subsídio, verba de representação, gratificações, indenizações, 13º, férias) quando o
   Tribunal os receber assim, e o valor bruto e líquido.
2. Se o pedido completo for grande demais, peço ao menos os agentes políticos (prefeito, vice-prefeito e vereadores)
   e todos os servidores das Câmaras Municipais, com os mesmos campos.
3. Os pagamentos das Câmaras Municipais a título de verba indenizatória, verba de gabinete ou cota de atividade
   parlamentar dos vereadores (empenhos e pagamentos com o nome do vereador beneficiário, o fornecedor e o CNPJ, quando
   houver), no mesmo período.
4. O dicionário de dados (o que significa cada coluna e cada código).

Não peço o CPF: ele pode ser omitido ou mascarado. O nome, o cargo e a remuneração de agentes públicos são de
divulgação obrigatória (art. 8º da Lei 12.527/2011 e STF, ARE 652.777, Tema 483).

Se já houver um endereço público para baixar esses dados, peço que o informem. Caso alguma informação não exista na
forma pedida, peço que seja enviada na forma mais próxima disponível, com a explicação de cada coluna. Caso alguma
parte seja negada, peço a indicação do fundamento legal e da autoridade a quem cabe recurso.

As informações serão usadas no site orcamentobrasileiro.com.br, um projeto independente que mostra de forma simples
para onde vai o dinheiro público, com a citação da fonte.

### Para quem e o que acrescentar

| Tribunal | Municípios | O que hoje está aberto | Acrescentar no fim do pedido | Canal |
|---|---|---|---|---|
| TCE-MG | 853 | O arquivo "Remuneração" do CAP-MG existe, mas só baixa à mão (a API pede reCAPTCHA) | "O arquivo REMUNERACAO-MUNICIPIO do CAP-MG já existe no portal de dados abertos; peço um endereço de download direto (sem verificação anti-robô) ou o envio do arquivo de 2021 em diante." || [Fale com o TCE](https://crtce.tce.mg.gov.br/) (nome, CPF, e-mail) · crtce@tce.mg.gov.br |
| TCE-SP | 644 | Nada de folha; só o "Mapa das Câmaras" (custo total) | — || [e-SIC](https://www4.tce.sp.gov.br/chamados/open.php?1lid=15) (conta TCESP ou gov.br) · ouvidoria@tce.sp.gov.br |
| TCE-RS | 497 | Nada de folha; os empenhos da Câmara trazem os subsídios dos vereadores somados | — || [SIC](https://tcers.tc.br/sic/) (CPF, RG e cópia do documento); o e-mail é só para dúvidas |
| TCM-BA | 417 | A folha está na tela, com reCAPTCHA em cada consulta e em cada exportação | "A consulta de pessoal do portal de controle social já mostra esses dados, um município e um mês por vez; peço o arquivo completo." || [SIC](https://www.tcm.ba.gov.br/acesso-a-informacao/servico-de-informacao-ao-cidadao-sic/) · sic@tcm.ba.gov.br |
| TCE-PR | 399 | Nada de folha (o PIT não tem pessoal) | — || [Pedido de acesso](https://servicos.tce.pr.gov.br/TCEPR/Tribunal/Ouvidoria/Atendimentos/Atendimento/PedidoAcessoInformacao) (CPF); o e-mail é só para orientações |
| TCE-SC | 295 | Lista nominal sem valores; pagamentos só agregados (painel "Pessoal On-line") | "O painel Pessoal On-line já mostra os agentes e os pagamentos agregados; peço os valores por pessoa e mês." || [Formulário](https://ouvidoria.tce.sc.gov.br/ouvidoria/orgaos/809/comunicacao_acesso_informacao.php) (nome, e-mail, CPF) · sic@tcesc.tc.br |
| TCM-GO | 246 | A API COLARE já tem a folha por rubrica, com token | "Peço também que a chave de acesso à API (pedida em 20/11/2026) inclua os serviços de pessoal e folha (remuneração por agente, quadro de pessoal e folha detalhada por rubrica)." || [Ouvidoria](https://www.tcmgo.tc.br/ouvidoria/) (cadastro) · ouvidoria@tcmgo.tc.br |
| TCE-PI | 224 | Cadastro com vínculo "Eletivo", sem valores | "A API do Portal da Cidadania já traz o cadastro dos servidores; peço os valores pagos." || [Central do Cidadão](https://www.tcepi.tc.br/transparencia/ouvidoria/central-do-cidadao/?tipo=3) (nome, CPF, e-mail) · ouvidoria@tcepi.tc.br |
| TCE-PE | 184 | Cadastro com vínculo "Eletivo", sem valores (valores só no painel "Mapa dos Servidores") | "O método ListaServidores dos Dados Abertos já traz o cadastro; peço os valores pagos, por pessoa e mês." || [SIC](https://ouvidoria.tcepe.tc.br/servico-de-acesso-a-informacao-2/) (cadastro) · ouvidoria@tcepe.tc.br |
| TCE-RN | 167 | Nada (a folha chega pelo SIAI-DP e não é publicada) | — || [SIC](https://www.tce.rn.gov.br/Ouvidoria/ManifestacaoSIC) (leva ao Fala.BR/Informa.BR) · ouvidoria@tce.rn.gov.br |
| TCM-PA | 144 | Painel Power BI de vínculos | — || [e-SIC](https://www.tcmpa.tc.br/eouvidoria/solicitacao_informacao) (nome, CPF) · ouvidoria@tcm.pa.gov.br |
| TCE-MT | 142 | Só agregado (Radar Pessoal) | — || [SIC](https://servicos.tce.mt.gov.br/sic/minhas-solicitacoes) (Conta TCE, CPF) · ouvidoria@tce.mt.gov.br |
| TCE-TO | 139 | Nada (a folha chega pelo SICAP-AP e não é publicada) | — || [Ouvidoria](https://tceto.omd.com.br/ouvidoria/externo/cadastro.do), tipo "Pedido de Acesso à informação" (nome, CPF) · ouvidoria@tceto.tc.br |
| TCE-AL | 102 | Nada | — || [e-LAI](https://portalouvidoria.tceal.tc.br/elai-portal/client/product/app/portal-tceal/#/cadastrar-manifestacao/solicitar-informacoes) (conta) · ouvidoria@tceal.tc.br |
| TCE-RJ | 91 | Só o total por unidade e situação funcional (API) | "A API situacao_funcional já traz o total por unidade; peço os valores por pessoa." || [SIC](https://eouve.com.br/#/sic) (nome, CPF, nascimento) · ouv@tcerj.tc.br |
| TCE-MS | 79 | Nada | — || [e-SIC](https://esic.tce.ms.gov.br/) (login) · ouvidoria@tce.ms.gov.br (aceita pedido por e-mail) |
| TCE-SE | 75 | Nada | — || [e-SIC](https://www.tce.se.gov.br/SitePages/esic.aspx) (CPF, nascimento, endereço) · ouvidoria@tce.se.gov.br |
| TCE-AM | 62 | Nada (e-Contas com login) | — || Só pelo [SEI, usuário externo](https://sei.tce.am.gov.br/sei/controlador_externo.php?acao=usuario_externo_logar&id_orgao_acesso_externo=0) (cadastro com análise de documentos); e-mail só para dúvidas |
| TCE-RO | 52 | Nada | — || [Solicitar informação](https://www.tce.ro.gov.br/acessoainformacao) (login) · ouvidoria@tce.ro.gov.br |
| TCE-AC | 22 | Só painel agregado ("Gastos com Pessoal") | — || [Formulário do SIC](https://externo.tceac.tc.br/ouvidoria2/formulario_sic/) (nome, CPF, e-mail) · ouvidoria@tceac.tc.br |
| TCE-AP | 16 | Nada | — || [e-SIC](https://www.tce.ap.gov.br/servicos/esic) (nome, CPF, e-mail; tipo "Solicitação") · ouvidoria@tce.ap.gov.br |
| TCE-RR | 15 | Nada | — || [SEI, Ouvidoria](https://sei.tcerr.tc.br/sei/controlador_externo.php?acao=ouvidoria&acao_origem=ouvidoria&id_orgao_acesso_externo=0), tipo "Pedido de Acesso à Informação" (nome, CPF, RG, e-mail) · ouvidoria@tcerr.tc.br |

Fora da lista: TCE-ES, TCE-PB, TCE-CE e TCE-MA, que já publicam. As capitais São Paulo e Rio de Janeiro têm tribunal
próprio (TCM-SP e TCM-RJ), que não publica a folha: o caminho ali são as próprias Câmaras.

Em 20/11/2026 já saiu um pedido pela LAI aos tribunais de BA, SC, PA, MT, AL, MS, RO, AP, RR e SE, e a chave da API do
TCM-GO, mas sobre a **despesa** (empenhos e pagamentos), não sobre a folha
([`levantamento-pagamentos-tce.md`](../levantamento-pagamentos-tce.md)). Este é um pedido novo.

---

## 2. Assembleias Legislativas: a verba e os gabinetes dos deputados

### Texto do pedido

**Órgão:** Assembleia Legislativa do Estado de [ESTADO]
**Assunto:** Verba indenizatória, gabinetes e benefícios dos deputados estaduais

Com base na Lei nº 12.527/2011 (Lei de Acesso à Informação), solicito as seguintes informações, de fevereiro de 2023
(início da legislatura) até o mês mais recente disponível, em formato aberto e editável (CSV, XLSX, ODS ou acesso por
API):

1. **Verba indenizatória** (ou cota, ou verba de gabinete) de cada deputado: cada despesa reembolsada ou paga, com o
   nome do deputado, a data, o tipo de despesa, o nome e o CNPJ ou CPF do fornecedor, o número do documento fiscal e o
   valor; e o teto mensal da verba, com a norma que o fixa.
2. **Pessoal dos gabinetes:** a relação dos servidores lotados no gabinete de cada deputado, com nome, cargo, lotação
   (o gabinete) e a remuneração bruta mensal.
3. **Pagamentos aos deputados:** por deputado e mês, o subsídio e cada outro valor pago (auxílio-moradia,
   auxílio-saúde ou plano de saúde, auxílio-alimentação, verba de representação, ajuda de custo, 13º, diárias e
   passagens), com a norma que fixa cada um.
4. O dicionário de dados (o que significa cada coluna e cada código).

Não peço CPF de deputados nem de servidores: ele pode ser omitido ou mascarado. O nome, o cargo e a remuneração de
agentes públicos são de divulgação obrigatória (art. 8º da Lei 12.527/2011 e STF, ARE 652.777, Tema 483).

Se parte disso já estiver publicada em formato aberto, peço que informem o endereço. Caso alguma informação não exista
na forma pedida, peço que seja enviada na forma mais próxima disponível, com a explicação de cada coluna. Caso alguma
parte seja negada, peço a indicação do fundamento legal e da autoridade a quem cabe recurso.

As informações serão usadas no site orcamentobrasileiro.com.br, um projeto independente que mostra de forma simples
para onde vai o dinheiro público, com a citação da fonte.

### Para quem e o que acrescentar

Fora da lista: CLDF, ALEPE, ALEGO e ALESP, que já publicam a verba e os gabinetes em formato aberto.

| Casa | O que falta (itens do pedido) | Acrescentar no fim do pedido | Canal |
|---|---|---|---|
| ALEP (PR) | 1, 2, 3 | "As consultas do portal da transparência exigem reCAPTCHA, inclusive a API; peço os arquivos completos." || [Acesso à informação](https://alep.sisgop.pr.gov.br/cidadao/acesso-informacao/1) (nome, e-mail, RG, CPF, endereço) · ouvidoria@assembleia.pr.leg.br |
| ALMT (MT) | 1 | "Hoje a verba aparece paga a um credor único, 'DEPUTADOS'; peço o gasto de cada deputado, despesa a despesa." || [Pedido de informação](https://www.al.mt.gov.br/transparencia/pedido-informacao/) (conta ALMT) · ouvidoria@al.mt.gov.br |
| ALEAL (AL) | 1, 2, 3 | "A prestação de contas da VIAP está publicada em PDF escaneado; peço os dados em planilha." || [Ouvidoria](https://www.al.al.leg.br/ouvidoria) (botão só com login) ou [SIC presencial](https://www.al.al.leg.br/transparencia/acesso-a-informacao-1/sic-presencial); e-mail não achado. Os pedidos listados no site estão pendentes desde jun/2026 |
| ALETO (TO) | 1, 2, 3 | "A verba está em PDF por deputado e mês; peço os dados em planilha." || [SIC](https://www.al.to.leg.br/loginExterno/sic) (conta) · ouvidoria@al.to.leg.br |
| ALEPI (PI) | 1 (fornecedor), 2, 3 | — || Fala.BR (indicado em [al.pi.leg.br/servicos/ouvidoria](https://www.al.pi.leg.br/servicos/ouvidoria)) · ouvidoria@al.pi.leg.br |
| ALEAC (AC) | 1, 2, 3 | "A seção de verbas indenizatórias do portal da transparência está fora do ar." || Fala.BR (indicado em [al.ac.leg.br](https://www.al.ac.leg.br/?page_id=41640)) · ouvidoria@al.ac.leg.br |
| ALESE (SE) | 1, 2, 3 | — || [e-SIC](https://al.se.leg.br/sic-ouvidoria/e-sic/): o formulário está quebrado; usar sic@al.se.leg.br |
| ALEMA (MA) | 1 (fornecedor), 2, 3 | — || [Ouvidoria](https://sistemas.al.ma.leg.br/ouvidoria/public/cadastro.html) (sem CPF) · ouvidoria@al.ma.leg.br |
| ALEPA (PA) | 1 | "Hoje a verba aparece só como total mensal por deputado." || [Ouvidoria](https://ouvidoria.alepa.pa.gov.br/manifestacao.php?tipo=4), tipo "Informação" · ouvidoria@alepa.pa.gov.br |
| ALERR (RR) | 1 (fornecedor), 3 | — || [Solicitação de Informação](http://grp.al.rr.leg.br/grp/acessoexterno/programaAcessoExterno.faces?codigo=68000) (CPF, e-mail) · ouvidoria@al.rr.leg.br |
| ALRN (RN) | 1, 2 | "A API do portal da transparência pede um token de acesso; peço um endereço público ou os arquivos." || [LAI](https://transparencia.al.rn.leg.br/ouvidoria/nova-demanda?lai=true) (CPF, documento de identidade e certidão de quitação eleitoral) · ouvidoriageral@al.rn.leg.br |
| ALRS (RS) | 1 (fornecedor), 3 | — || [SIC](https://ouvidoriageral.al.rs.gov.br/encaminhe-seu-pedido) (gov.br; só pelo formulário) |
| ALES (ES) | 1 (fornecedor), 3 | — || [e-SIC](http://esic.al.es.gov.br/sistema/site/index.html) (conta) · sic@al.es.gov.br |
| ALESC (SC) | 1 (CNPJ do fornecedor), 3 | — || [SIC](https://www.alesc.sc.gov.br/sic/) (formulário simples) · ci@alesc.sc.gov.br |
| ALEAM (AM) | 1 (em planilha), 2, 3 | — || Informa.BR (indicado em [aleam.gov.br/transparencia/sic](https://www.aleam.gov.br/transparencia/sic/)) · ouvidoria@aleam.gov.br |
| ALAP (AP) | 1 (em planilha), 2 | — || [e-Cidadão, e-SIC](https://www.al.ap.leg.br/ecidadao/) (login com CPF); e-mail não achado |
| ALBA (BA) | 2, 3 | "Os secretários parlamentares pagos pela verba de gabinete não aparecem por nome no portal de RH." || [e-SIC](https://atendimento.al.ba.gov.br/e-sic/home/pedido) (CPF, e-mail) · ouvidoria@alba.ba.gov.br |
| ALECE (CE) | 2 (a lotação de cada assessor) | — || [LAI](https://canalalece.al.ce.gov.br/manifestacao/nova?tipo=acesso-a-informacao-lai) (CPF, e-mail) · ouvidoria@al.ce.gov.br |
| ALEMS (MS) | 2, 3 (em planilha) | — || [Manifestação](https://transparencia2.al.ms.gov.br/transparencia-manifesto) (CPF, RG, endereço) · ouvidoria@al.ms.gov.br |
| ALMG (MG) | 2, 3 | "A folha de pagamento está publicada em PDF escaneado, sem a lotação." || [Fale com a Assembleia](https://www.almg.gov.br/apps/fale-com/assembleia) (CPF); e-mail não achado |
| ALERJ (RJ) | 2, 3 (em planilha) | "A folha está em PDF, sem a lotação." || [Formulário da LAI](http://www2.alerj.rj.gov.br/leideacesso/formulario-2016.asp) (CPF, nascimento); e-mail não achado |
| ALPB (PB) | 1 (CNPJ sem máscara), 3 | — || [SIC](https://www.al.pb.leg.br/sic/open.php) (CPF, nascimento, endereço) · ouvidoria@al.pb.leg.br |
| ALERO (RO) | 3 | "A remuneração exige cadastro de visitante no portal." || Fala.BR (indicado em [transparencia.al.ro.leg.br/ouvidoria](https://transparencia.al.ro.leg.br/ouvidoria/)) · ouvidoria@ale.ro.gov.br |

Quando faltar só parte, o pedido pode levar só os itens da coluna "O que falta"; tire os outros do texto.

---

## Acompanhamento

| Órgão | Enviado em | Canal | Protocolo | Prazo | Resposta |
|---|---|---|---|---|---|
| | | | | | |
