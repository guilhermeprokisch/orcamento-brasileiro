# Quanto custa o mandato: deputados estaduais, prefeitos e vereadores

Levantamento de 23/11/2026. A pergunta: dá para mostrar, como já mostramos para deputados federais e senadores
(`docs/levantamento-parlamentar.md`), **quanto cada deputado estadual, prefeito e vereador custa**: o salário, a
verba do gabinete (o equivalente da cota parlamentar), os assessores e os benefícios?

Não existe base nacional com isso. Este levantamento procura as bases locais (Assembleias, Tribunais de Contas,
Câmaras das capitais) que, juntas, cobririam o país. Os endereços foram testados na data, sem login e sem passar por
CAPTCHA. A máquina saiu por IP do Brasil; alguns tribunais recusam IP de fora (ver cada caso).

## Resumo

| O que | Onde há dado aberto | Cobertura |
|---|---|---|
| **Custo total da Câmara Municipal** (salários, assessores, prédio) | Siconfi (Tesouro): DCA, função 01 "Legislativa"; RGF do Legislativo (pessoal) | **5.471 das 5.570 cidades** já no site (2025) |
| **Teto do salário do vereador e do gasto da Câmara** | Constituição, arts. 29 e 29-A, pela população | **Todas** |
| **Salário de cada prefeito, vice e vereador**, com nome | Folha dos municípios no TCE-ES, TCE-PB, TCE-CE e TCE-MA | **702 municípios** (MA só 2025–2026) |
| Salário médio do vereador, sem nome | TCE-RJ (agente político por Câmara); TCE-RS (empenho "subsídios / vereadores") | 91 + ~497 municípios |
| **Verba de gabinete de cada vereador**, nota a nota com CNPJ | Câmaras de São Paulo, Fortaleza, Manaus e Natal; na PB, pelas despesas da Câmara no TCE-PB | 4 capitais + 223 municípios da PB |
| **Subsídio do deputado estadual** | Todas as Assembleias que conferimos: R$ 34.774,64 (75% do deputado federal) | Todas |
| **Verba de cada deputado estadual**, nota a nota com CNPJ | Em arquivo ou API: CLDF, ALEGO, ALEMS, ALMG, ALERJ, ALEPE, ALECE; ALESP por fornecedor e mês; em tela HTML: ALERO, ALBA, ALEAM, ALAP | 12 das 28 Casas |
| **Assessores por gabinete** (quantos e, em várias, quanto custam) | CLDF, ALEGO, ALMT, ALESP, ALRS, ALEPE, ALPB, ALERO, ALEPA, ALERR | 10 das 28 |

O que **não** existe em lugar nenhum: o salário de cada prefeito e vereador do país num arquivo só. Na maior parte do
Norte, no RN, SE, AL, MS, SC, SP, PR, MG e na Bahia, a folha municipal não é publicada pelo tribunal, ou está atrás de
login, token ou CAPTCHA. Ali o caminho é pedido pela Lei de Acesso (LAI) ao tribunal.

## 1. O que vale para todas as cidades

### O teto do salário

O deputado federal ganha R$ 46.366,19 por mês desde fev/2025. O deputado estadual ganha no máximo 75% disso,
**R$ 34.774,64** (CF, art. 27, §2º), e todas as Assembleias que conferimos pagam esse valor. O vereador ganha no
máximo uma fração do deputado estadual, conforme a população (CF, art. 29, VI):

| População | % do deputado estadual | Teto do vereador |
|---|---|---|
| até 10 mil | 20% | R$ 6.954,93 |
| 10.001 a 50 mil | 30% | R$ 10.432,39 |
| 50.001 a 100 mil | 40% | R$ 13.909,86 |
| 100.001 a 300 mil | 50% | R$ 17.387,32 |
| 300.001 a 500 mil | 60% | R$ 20.864,78 |
| mais de 500 mil | 75% | R$ 26.080,98 |

O valor de cada cidade é fixado pela Câmara numa legislatura para valer na seguinte. A soma dos salários de todos os
vereadores não pode passar de 5% da receita do município (art. 29, VII). O prefeito ganha o que a lei municipal fixar,
e esse valor é o teto de salário da prefeitura (art. 37, XI).

### O teto do gasto da Câmara

A Câmara pode gastar no total, contando os inativos, até um percentual da receita tributária mais as transferências
do ano anterior (art. 29-A): 7% até 100 mil habitantes; 6% de 100 a 300 mil; 5% de 300 a 500 mil; 4,5% de 500 mil a
3 milhões; 4% de 3 a 8 milhões; 3,5% acima de 8 milhões. Até 70% disso pode ir para a folha (§1º). Pela LRF (art. 20),
o Legislativo municipal gasta no máximo 6% da receita corrente líquida com pessoal.

### O custo real da Câmara, pelo Siconfi

- **Já no site:** a DCA (Anexo I-E) traz a despesa da função 01 "Legislativa" de 5.471 cidades em 2025. Exemplos:
  São Paulo R$ 1,37 bilhão, Campina Grande R$ 28,7 milhões, Serra da Saudade R$ 1,27 milhão.
  - Dividido pelo número de vereadores eleitos em 2024: ~R$ 25 milhões por vereador em São Paulo, ~R$ 1,2 milhão em
    Campina Grande, ~R$ 141 mil em Serra da Saudade. A divisão é uma média: inclui assessores, servidores e o prédio.
  - Em São Paulo e no Rio a função 01 traz também o Tribunal de Contas do Município (subfunção 032, controle
    externo): para a Câmara sozinha, usar a subfunção 031.
- **Pessoal do Legislativo:** o RGF (Anexo 1) do poder Legislativo de cada município, na API do Siconfi
  (`apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf?...&co_esfera=M&co_poder=L&id_ente=<ibge>`). São Paulo, 2025:
  R$ 480,7 milhões em 12 meses.
- Com as receitas da DCA (Anexo I-C) dá para calcular o teto do art. 29-A de cada cidade e mostrar quanto a Câmara
  gastou perto dele.

Esta parte sozinha já permite, em todas as cidades, uma seção "Quanto custa a Câmara": o gasto, o gasto por
vereador e por morador, a comparação com cidades do mesmo porte e o teto legal do salário do vereador.

## 2. Prefeitos e vereadores, pelos Tribunais de Contas

Os tribunais recebem a folha de todas as prefeituras e Câmaras. Poucos a publicam.

| Tribunal | Municípios | Folha com nome e valor? | Identifica os eleitos? | Rubricas separadas? | Verba do vereador | Obstáculos | Facilidade |
|---|---|---|---|---|---|---|---|
| **TCE-ES** | 78 | Sim: valores por unidade, cargo, vínculo e mês; nomes num arquivo à parte | Sim ("Eletivo"; PREFEITO, VICE PREFEITO, VEREADOR) | **Sim** (subsídio, alimentação, IR…) | Indenizações por rubrica; verba de gabinete não | Nenhum | **1** |
| **TCE-PB** | 223 | Sim, um valor por vínculo e mês | Sim ("Eletivos"; prefeito, vice, vereador, presidente) | Não | **Sim**, nas despesas da Câmara (elemento 93, credor = vereador, "VIAP") | Nenhum; já lido pelo projeto | **1** |
| **TCE-CE** | 184 | Sim, item a item | Sim (Câmara = órgão 01; cargo VEREADOR, PREFEITO, VICE) | **Sim**, com a marca do que conta para o teto | Provável pelas despesas; não confirmado | Só IP do Brasil; nome e valor em endpoints separados | **2** |
| **TCE-MA** | 217 | Sim (painel Metabase público, exporta CSV) | Sim, pelo cargo | Não (contribuição e bruto) | Não achada | **Só 2025 e 2026**; cobertura irregular | **2** |
| TCE-RJ | 91 | Só total por unidade e situação funcional | Em parte: "Agente Político" na Câmara = vereadores | Não | Não | Desde 2024 | 2 (média por vereador) |
| TCE-RS | ~497 | Não há folha; os empenhos da Câmara trazem "SUBSIDIOS / VEREADORES" (total) e as diárias com nome | Indireto | Não | Indenizações em total | Não é folha | 3 |
| TCM-GO | 246 | Sim, até a rubrica (COLARE) | Sim | Sim | ? | **Token** pedido ao tribunal | 3 |
| TCE-PE | 184 | Só cadastro, sem valor | Sim ("Eletivo") | — | Despesas nota a nota poderiam dar a verba | Valores só em painel | 4 |
| TCE-PI | 224 | Só cadastro, sem valor | Sim | — | — | — | 4 |
| TCE-SC | 295 | Lista nominal sem valor; pagamentos agregados | Filtro por cargo | — | — | Só painel Qlik | 4 |
| TCE-MG | 853 | Arquivo "Remuneração" do CAP-MG | Provável | ? | ? | API pede reCAPTCHA (401); só à mão | 4 |
| TCE-MT | 142 | Só agregado (Radar) | Filtro "ELETIVO" | — | — | WAF bloqueia scripts | 4 |
| TCE-SP | 644 | Não; "Mapa das Câmaras" traz custo, nº de vereadores e custo por vereador | — | — | — | Painel Pentaho | 4 |
| TCE-PR | 399 | Não (o PIT não tem pessoal) | — | — | Diárias com nome (não testado) | — | 4 |
| TCM-PA | 144 | Painel Power BI de vínculos | ? | ? | ? | API do Power BI 403 | 4–5 |
| TCM-BA | 417 | Sim, na tela, por entidade e mês | Provável | ? | ? | **reCAPTCHA em cada consulta** | 5 (LAI) |
| TCE-RN, TCE-TO | 167, 139 | Recebem a folha (SIAI-DP, SICAP-AP), não publicam | — | — | TO: verba talvez pelos empenhos da Câmara | — | 5 (LAI) |
| TCE-MS, TCE-AL, TCE-SE, TCE-AC, TCE-AM, TCE-AP, TCE-RO, TCE-RR | 79, 102, 75, 22, 62, 16, 52, 15 | Não achada | — | — | — | Fora do ar, login ou nada | 5 |

**Somando:** com nome e valor, **702 municípios** (ES 78, PB 223, CE 184, MA 217). Com a média por vereador, mais 91
(RJ); com o total do ano, mais ~497 (RS); com o token do TCM-GO, mais 246. Sabendo só quem é eleito, sem valor: PE e
PI (408).

Pedidos de LAI que mais rendem: TCM-BA (417), TCE-MG (853, a mesma base do CAP-MG), TCE-RN (167), TCE-TO (139),
TCE-SC (295) e o token do TCM-GO (246).

## 3. As Câmaras das capitais

Salário do vereador pela folha oficial, quando a lei não foi achada. Facilidade de 1 (fácil) a 5 (impossível).

| Capital | Vereador (R$/mês) | Prefeito / vice | Verba do vereador: teto | Granularidade · formato | Assessores por gabinete | Facilidade |
|---|---|---|---|---|---|---|
| **São Paulo** | 26.080,98 (Res. 10/2024) | 35.462,00 / 31.915,80 (Lei 17.543/2020) | AEGG, ~36 mil/mês | **Nota a nota com CNPJ** · JSON, desde 2015 | XML com nº do gabinete | **1** |
| **Fortaleza** | 26.080,98 (folha) | ~22,9 mil / ~20,6 mil (notícia) | SDP, teto não achado | **Nota a nota com CNPJ** · API JSON, 2023– | Não (lotação genérica) | **1** |
| **Manaus** | 26.080,98 (folha) | ~27 mil (notícia) | CEAP, 33.085,85/mês | **Nota a nota com CNPJ** · JSON, 2024– | Sim, API JSON | **1** |
| **Natal** | 26.000 (notícia) | 41.600 / 20.800 (notícia) | 22 mil | **Nota a nota com CNPJ** · HTML/PDF, 2017– | Sim, "GAB. VER. X" | **1** |
| Porto Alegre | 23.428,64 (Lei 13.575/2023) | 34.900,00 / 23.428,64 | QBM, 13.903,32/mês | Lançamento a lançamento, sem CNPJ · API JSON, 2010– | Sim | 2 |
| Porto Velho | 20.864,78 (Res. 679/2023) | 37.366,93 / 29.613,79 (Lei 3.238/2024) | 47 mil (Res. 761/2026) | Notas em texto livre na tela; JSON só com total | Sim, API JSON | 2 |
| Palmas | 20.864,78 (folha) | não achado | CODAP, ~38 mil | Nota a nota em PDF escaneado | Sim, API JSON | 2 |
| Belém | 24.754,79 (folha) | não achado | **Não tem verba** | — | Sim, API JSON | 2 |
| Vitória | 17.681,99 | 19.217,12 (notícia) | **Não tem verba** | — | PDF por gabinete + API | 2 |
| Maceió | 18.991,68 (folha) | não achado | VIAP, 20.500 | Total anual em CSV; notas escaneadas | Sim, PDF por gabinete | 2 |
| Curitiba | 21.398,56 (Lei 16.449/2024) | 37.068,57 / 16.711,44 (Lei 16.643/2025) | **Não tem verba** | — | Sim (Betha), até 7 cargos, 82,5 mil/gabinete | 3 |
| Belo Horizonte | 18.402,02 (Lei 11.016/2016) | não achado | Extinta em 2017; "custeio parlamentar" por categoria | HTML | CSV só com nomes | 3 |
| Goiânia | ~20,7 mil + 6,9 mil de representação (notícia) | 37.562,77 / 28.171,90 (notícia) | ~15,5 mil | Linha mensal + PDF nota a nota com CNPJ | Sim | 3 |
| Cuiabá | bruto 38.339,04 na folha (inclui outras verbas) | não achado | 26.406,99 fixos/mês | Total por vereador · PDF + JSON | ? | 3 |
| Boa Vista | 20.864,78 (Res. 253/2023) | 24.789,20 / 23.412,02 (notícia) | 40 mil | Por categoria, sem CNPJ · PDF por vereador/mês, 2013– | XLS com gabinete | 3 |
| São Luís | 15.031,76 (folha) | Lei 7.729/2025: 38 mil | VIEP, 20 mil | Total por vereador · PDF | Sim, JSON | 3 |
| Teresina | 24.754,79 (folha) | 26.080,98 / 20.864,78 (TCE-PI) | ~25 mil | Total mensal · JSF | Não | 3 |
| João Pessoa | 26.000 (notícia) | não achado | VIAP, ~14 mil | Total mensal + PDF da NFS-e | Não | 3 |
| Salvador | ~26 mil (notícia) | não confirmado | 34 a 39 mil (Lei 9.828/2025) | Total mensal · HTML | Sim, PDF (até dez/2025) | 3 |
| Rio de Janeiro | líquido 19.127,52 (bruto não achado) | 33.828,87 / 27.063,09 (Lei 8.227/2023) | Cota fragmentada; teto não achado | Total por tipo · XLS | JSON + de-para do gabinete | 4 |
| Recife | ~25,3 mil (notícia, não verificado) | ~25 mil (notícia) | CEAP, 16 mil | Por rubrica, sem CNPJ | não testado | 4 (reCAPTCHA) |
| Aracaju | 22.865,16 (folha) | não achado | VAEP, 17 mil | PDF escaneado, 2015– | Não | 4 |
| Rio Branco | 20.864,78 (Res. 22/2023) | 35.000 / 32.000 (Lei 2.512/2024) | não achada | — | até out/2024 | 4 |
| Macapá | 19.317,60 (tabela) | não achado | não achada | — | genérica | 4 |
| Florianópolis | 26.080,98 (notícia) | não achado | não achada | — | — | 5 (bot verification) |
| Campo Grande | 26.080,98 (notícia) | 35.462,27 (notícia) | ~25 mil (notícia) | — | — | 5 (bot verification) |

"Notícia" quer dizer que o valor veio da imprensa e não foi conferido numa fonte oficial. A lei da legislatura
2025–2028 não foi achada em cerca de metade das capitais; o subsídio do prefeito, em cerca de 12. Essas leis estão no
SAPL ou no diário oficial de cada cidade.

## 4. Assembleias Legislativas

O subsídio é **R$ 34.774,64** em todas as Casas que conferimos (75% do deputado federal). A ALRS mostra R$ 34.772,11
bruto na folha de ago/2026; a diferença não foi explicada.

### Sul, Sudeste, Centro-Oeste e DF

| Casa | Verba do deputado: teto mensal | Granularidade · formato · desde | Assessores por gabinete | Outros benefícios por deputado | Obstáculos | Facilidade |
|---|---|---|---|---|---|---|
| **CLDF** | R$ 20.864,78 | **Nota a nota com CNPJ** · CSV/XLSX (CKAN) · 2013 | **Sim**, CSV mensal com lotação e remuneração | Auxílios na folha; diárias e passagens | Codificação mista | **1** |
| **ALEGO** | não achado (maiores reembolsos 41–49 mil) | **Nota a nota com CNPJ** · JSON/CSV · 2011 | **Sim**, filtro por gabinete (só 2026) | "Indenizações" e "auxílios" na folha; diárias | — | **1–2** |
| **ALEMS** | não confirmado | **Nota a nota com CNPJ** e link do comprovante · CSV anual · 2012 | Não (sem lotação) | Plano médico de R$ 13.425,82/mês por deputado (folha em PDF) | Folha em PDF | **1** (verba) |
| **ALMG** | ~R$ 36,2 mil (6.253,8 Ufemg) | **Nota a nota com CNPJ** · API JSON · fev/2019 | Não (folha escaneada) | Só o total da Casa | CSV quebrado; usar a API | **2** |
| **ALESP** | ~R$ 48 mil (1.250 UFESPs) | Por fornecedor (com CNPJ) e mês · JSON · 2002 | **Sim**, juntando duas bases pelo nome | Sem diárias | Portal mudou em 19/11/2026 | **2** |
| **ALERJ** | R$ 31.165,33 | **Nota a nota com CNPJ** · JSON (DOCIGP) · jul/2019 | Não (folha em PDF sem lotação) | Auxílio-moradia R$ 3.189,75 (PDF) | Quase tudo PDF; a API expõe dados internos (usar só os gastos) | **3** |
| **ALRS** | R$ 27.140,91 | Só total por categoria · JSON · 2011 | **Sim**, 9 cargos, R$ 112 mil/mês | Diárias | Uma chamada por servidor | **2** |
| **ALESC** | fórmula, sem valor em reais | Lançamento a lançamento, **sem CNPJ** · CSV · 2011 | Lista com lotação (HTML) | Diárias e passagens | Contracheque só no navegador | **1** (sem CNPJ) |
| **ALES** | até ~R$ 20 mil | Só total por rubrica · HTML/xlsx · 2010 | Sim, por matrícula | Na cota | CSVs com erro | **3** |
| **ALMT** | não confirmado | **Não sai por deputado** (credor "DEPUTADOS") | **Sim**, API JSON com lotação e remuneração | Auxílio-saúde R$ 6.954,93/mês; diárias | Cabeçalhos especiais na API | **2** (folha) / **5** (verba) |
| **ALEP** | não confirmado | Por deputado e mês, com comprovantes | Atrás de reCAPTCHA | Tabela de auxílios aberta | **reCAPTCHA em tudo**, até na API | **4** |

### Norte e Nordeste

O subsídio de R$ 34.774,64 foi confirmado na fonte em PE (Lei 18.138/2023), PB, PA e CE; na BA, só por notícia. No
CE, a folha mostra R$ 39.993,14 bruto (o subsídio mais, pela conta, um auxílio-saúde de R$ 5.218,50). No AP, o
contracheque traz "subsídio fixo" de R$ 33.448,48, GFE de R$ 18.396,66 e auxílio-alimentação de R$ 2.500. Na PB, a
folha dos eletivos traz uma "Indenizatória" de R$ 19.126,05 além do subsídio.

| Casa | Verba do deputado: teto mensal | Granularidade · formato · desde | Assessores por gabinete | Outros benefícios por deputado | Obstáculos | Facilidade |
|---|---|---|---|---|---|---|
| **ALEPE (PE)** | teto por rubrica (imóveis R$ 25.326; consultorias R$ 41.939,86) | **Nota a nota com CNPJ** · JSON · 2015 | **Sim**, API com lotação "GAB.DEP. X" (49 gabinetes); salário só por cargo | Ajuda de custo igual ao subsídio no início e no fim da legislatura | — | **1** |
| **ALECE (CE)** | não confirmado (VDP, Res. 762/2023) | **Nota a nota com CNPJ** · CSV mensal · 2021 | Folha nominal em CSV com salário, **sem gabinete** | Auxílio-saúde na folha; diárias em CSV | Mês com zero à esquerda | **1–2** |
| **ALPB (PB)** | R$ 50.000 (VIAP, Res. 1885/2020) | Nota a nota, **CNPJ mascarado** · XLSX por deputado e mês · 2022 | **Sim**, ODS mensal com lotação "GAB DEP X" | "Indenizatória" de R$ 19.126,05 na folha | — | **2** |
| **ALERO (RO)** | não confirmado | **Nota a nota com CNPJ** · HTML · 2020 | **Sim**, API JSON com lotação (sem salário) | Diárias; "saúde" dentro da verba | Remuneração exige cadastro de visitante | **2** |
| **ALBA (BA)** | ~R$ 32 mil (notícia) | **Nota a nota**, CNPJ e PDF da nota no detalhe · HTML e Excel · 2015 | Não (os secretários parlamentares não aparecem por nome) | Diárias (não confirmado se de deputados) | — | **2** |
| ALEAM (AM) | R$ 49.849,65 | **Nota a nota com CNPJ** · HTML (POST) · 2015 | Consulta só por nome | Diárias e passagens | Só tela | 3 |
| ALAP (AP) | ~R$ 45,5 mil | **Nota a nota com CNPJ** no detalhe · HTML (POST) · 2012 | Consulta por lotação, não confirmada | GFE e auxílio-alimentação no contracheque; diárias | latin-1 | 3 |
| ALEMA (MA) | não mostrado | Total por rubrica, sem fornecedor · HTML/JSF · 2019 | Folha nominal **sem lotação** | Verba de assistência à saúde | ids em JSF | 3 |
| ALEPA (PA) | R$ 35.000 + auxílio-transporte R$ 5.846,75 | Só o total mensal · painel com exportação | **Sim**, nº de assessores e custo por gabinete (~R$ 123,5 mil) | Diárias | Painel em JS | 3 |
| ALERR (RR) | R$ 50.000 (Res. 036/2021) | Total por item, sem fornecedor · ODT/PDF por deputado e mês · set/2025 | **Sim**, XLSX com setor (sem valor) | Diárias e passagens | Histórico até ago/2025 com erro 500 | 3 |
| ALRN (RN) | não confirmado | Com **CNPJ** e fornecedor · API com export CSV/JSON/XLSX | Remuneração com setor | Diárias | A API pede um token embutido no JS do site (não usado: decodifica para login e senha) | 3 |
| ALEPI (PI) | não confirmado | Por subcota, sem fornecedor · CSV · 2023 | Remuneração nominal desde 2017 | Viagens | Akamai recusa scripts (403) | 3–4 |
| ALETO (TO) | não confirmado | PDF de texto por deputado e mês · 2017 | Folha sem lotação | Diárias | hCaptcha na folha | 4 |
| ALEAL (AL) | não confirmado (VIAP) | **PDF escaneado** por deputado e mês · 2019 | Folha nominal sem lotação | Diárias e passagens | Precisa de OCR | 4 |
| ALESE (SE) | não confirmado | PDF mensal consolidado · 2016 | Não achada | Diárias e passagens | Atualizado até abr/2026 | 4 |
| ALEAC (AC) | não achado | Seção fora do ar (404) | Lotação só "GABINETE" | — | — | 4–5 |

### As 28 Casas, juntas

- **Verba nota a nota com CNPJ, em arquivo ou API:** CLDF, ALEGO, ALEMS, ALMG, ALERJ, ALEPE, ALECE (7); por
  fornecedor e mês, ALESP. Em tela HTML, também com CNPJ: ALERO, ALBA, ALEAM, ALAP (4). Com CNPJ mascarado: ALPB.
- **Assessores por gabinete** (quantos, e em várias o custo): CLDF, ALEGO, ALMT, ALESP, ALRS, ALEPE, ALPB, ALERO,
  ALEPA, ALERR.
- **Benefícios por deputado** aparecem em poucas: plano médico (MS, R$ 13.425,82), auxílio-saúde (MT, R$ 6.954,93; CE,
  pela conta, R$ 5.218,50), "indenizatória" na folha (PB, R$ 19.126,05), GFE e auxílio-alimentação (AP),
  auxílio-moradia (RJ, R$ 3.189,75).
- **Difíceis:** ALEP (reCAPTCHA em tudo), ALMT (verba não sai por deputado), ALEAL (PDF escaneado), ALETO (hCaptcha),
  ALEPI (Akamai), ALEAC (fora do ar).

## 5. Ordem sugerida

1. **Todas as cidades, sem coleta nova:** a seção "Quanto custa a Câmara" na página da cidade, com a função
   Legislativa do Siconfi (já no site), o RGF do Legislativo e o teto legal do salário do vereador pela população.
2. **Salário de cada prefeito e vereador:** PB (a folha já é lida em `supersalarios_municipios.py`; falta separar os
   eletivos e a Câmara), ES (CKAN, rubricas), CE (API, rubricas; rodar de IP do Brasil) e MA (Metabase, 2025–2026).
   São 702 municípios.
3. **Verba de cada vereador:** as 4 capitais com nota a nota (São Paulo, Fortaleza, Manaus, Natal) e a PB pelas
   despesas da Câmara.
4. **Deputados estaduais:** a página por deputado igual à do federal começa pelas Casas com verba nota a nota com CNPJ
   em arquivo ou API e assessores por gabinete: CLDF, ALEPE, ALEGO; depois ALECE, ALEMS, ALMG, ALESP e ALERJ.
5. **LAI:** TCM-BA, TCE-MG, TCE-RN, TCE-TO, TCE-SC e o token do TCM-GO.

## 6. Cuidados

- **CPF:** algumas fontes oficiais publicam o CPF completo dos vereadores (Goiânia, São Luís; Teresina na folha) ou os
  consignados dos servidores (Fortaleza). Nada disso entra no site. O TCE-CE troca o CPF por um código; o TCE-ES e o
  TCE-MA mascaram parte.
- **Assessores:** como hoje, só a contagem e o custo por gabinete, nunca o nome.
- **Fornecedor pessoa física na verba:** só somado, como na cota federal.
- **Um valor só por mês** (PB, MA): inclui 13º, férias e indenizações. Usar o valor típico (a mediana dos meses), como
  já faz o piloto da PB.
- **Vereador presidente** recebe mais (representação). **Prefeito de licença** e **suplente** aparecem na folha: o
  eleito de 2024 e o que está no cargo podem ser pessoas diferentes.
- **Valores de imprensa** divergem das folhas em várias capitais: só como pista.

## 7. Endereços que funcionaram

Tribunais de Contas:
- **TCE-ES:** `https://dados.es.gov.br/api/3/action/package_show?id=area-tematica-pessoal` (vantagens e descontos
  `vantagens-descontos-{ano}_{1|2}.zip` desde 2019; vínculos `vinculo-{ano}-{trimestre}.csv`). CSV `;`, latin-1.
- **TCE-PB:** `https://download.tce.pb.gov.br/dados-abertos/dados-por-municipio/{001-223}/servidores/servidores-{ano}.zip`
  e o consolidado `.../dados-consolidados/servidores/servidores-{ano}.zip` (2013–); verba do vereador em
  `.../dados-por-municipio/{nnn}/despesas/despesas-{ano}.zip` (elemento 93, credor = vereador).
- **TCE-CE:** `https://api-dados-abertos.tce.ce.gov.br/sim/agentes_publicos_folha`, `/agentes_publicos_municipais`,
  `/itens_remuneratorios`, `/orgaos`, `/folhas_pagamentos` (por `codigo_municipio`, `exercicio_orcamento`,
  `data_referencia_doc`).
- **TCE-MA:** painéis Metabase públicos (2026: `metabase.apps.tcema.tc.br/public/dashboard/2ff81b82-7741-4464-987a-49df968abada`;
  2025: `.../739f0682-739f-4d2b-bcd9-3003d2f5de1d`); CSV por `POST /api/public/dashboard/{uuid}/dashcard/{d}/card/{c}/csv`
  com o filtro do ente (o JSON corta em 2.000 linhas; o CSV não).
- **TCE-RJ:** `https://dados.tcerj.tc.br/api/v1/situacao_funcional?ano={ano}&municipio={NOME}&jsonfull=true`.
- **TCE-RS:** `https://dados.tce.rs.gov.br/dados/municipal/empenhos/{ano}/{codigo}.csv.zip` (arquivos `-cm-` da Câmara).
- **TCM-GO:** catálogo `https://ws.tcmgo.tc.br/api/rest/servicoRest/all` (serviços 18, 29, 64, 69 e 78, com token).

Siconfi:
- RGF do Legislativo: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf?an_exercicio=2025&in_periodicidade=Q&nr_periodo=3&co_tipo_demonstrativo=RGF&co_esfera=M&co_poder=L&id_ente={ibge}`.
- DCA por função: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio={ano}&no_anexo=DCA-Anexo%20I-E&id_ente={ibge}`.

Capitais:
- **São Paulo:** `POST https://sisgvconsulta.saopaulo.sp.leg.br/ws/Servicos.asmx/ObterDebitoVereadorJSON` (`ano`, `mes`);
  folha `https://www.saopaulo.sp.leg.br/static/transparencia/funcionarios/CMSP-XML-Funcionarios.xml`.
- **Fortaleza:** `https://api.cmfor.ce.gov.br/transparencia/transparencia/sdp?ano={ano}&page=1` e `.../sdp/{ano}/{mes}/{NOME}`.
- **Manaus:** `POST https://www.cmm.am.gov.br/wp-admin/admin-ajax.php` (`action=cmm_cotas_ceap_parlamentares`, depois
  `cmm_cotas_ceap_fetch`); folha `https://www.cmm.am.gov.br/wp-json/cmm-transparencia/v1/remuneracao-nominal-servidores`.
- **Natal:** `https://www.cmnat.rn.gov.br/consulta/consultar_vereador/?mes_id={m}&ano={a}` e `POST /consulta/verbas_geral`.
- **Porto Alegre:** `https://portal-api.camarapoa.rs.gov.br/v1/lancamentos.json?mes={M}%2F{AAAA}&setor_id={id}`.
- **Porto Velho:** `https://cmportovelho-ro.portaltp.com.br/api/transparencia.asmx/json_liquidacoes?ano=&mes=` e `json_servidores`.

Assembleias:
- **CLDF:** `https://dados.cl.df.gov.br/api/3/action/package_show?id=verbas-indenizatorias` (2013–2026) e a folha
  `qdp-{ano}-{mes}.csv` no mesmo portal.
- **ALEGO:** `https://transparencia.al.go.leg.br/api/transparencia/verbas_indenizatorias.csv?ano=&mes=&todos=true`,
  `.../verbas_indenizatorias/exibir?deputado_id=&ano=&mes=`, `.../remuneracoes.csv?todos=true&ano=&mes=`.
- **ALEMS:** `https://transparencia2.al.ms.gov.br/ceap/notas/exportar-csv?ano={ano}` (2012–).
- **ALMG:** `https://dadosabertos.almg.gov.br/api/v2/prestacao_contas/verbas_indenizatorias/deputados/{id}/{ano}/{mes}?formato=json`.
- **ALESP:** `https://foundry.al.sp.gov.br/services/SAEG/prestacao-contas-fornecedores?ano=&mes=&matricula=` e
  `https://foundry.al.sp.gov.br/services/RH_API/servidor-todos?Situacao=Ativo`.
- **ALERJ:** `https://docigp.alerj.rj.gov.br/api/v1/congressmen/{id}/legislatures/{l}/budgets/{b}/entries`.
- **ALESC:** `https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/csv/{ano}` (2011–).
- **ALRS:** `https://transparencia.al.rs.gov.br/ajax-gastosParlamentaresListarGabinete?ano=&mes=`.
- **ALMT:** `https://almt.eloweb.net/portaltransparencia-api/api/servidores?exercicio=&mes=&page=0&size=2000`
  (cabeçalhos `entidade: 1` e `exercicio: <ano>`).
- **ALEPE:** `https://www.alepe.pe.gov.br/servicos/transparencia/adm/verbaindenizatoria.php?dep={id}&ano=&mes=`, depois
  `.../verbaindenizatorianotas.php?docid={docid}`; servidores em `https://dadosabertos.alepe.pe.gov.br/api/v1/servidores?formato=json`.
- **ALECE:** `https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar/csv?mes=09&ano=2026` e
  `https://transparencia.al.ce.gov.br/gestao-de-pessoas/pessoal/csv?mes=10&ano=2026`.
- **ALPB:** `https://www.al.pb.leg.br/transparencia/deputados/viap-v2?tipo_viap=deputados&ano_viap=&mes_viap=&deputado={id}`
  (link do XLSX na página) e `https://www.al.pb.leg.br/transparencia/recursos-humanos/remuneracoes?mes=&ano=` (ODS).
- **ALERO:** `https://transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/?ano=&mes=&gabinete={id}` e
  `https://transparencia.al.ro.leg.br/api/servidores`.
- **ALBA:** `https://al.ba.gov.br/transparencia/verbas-idenizatorias?deputado={id}&ano=` (Excel em `verbas-idenizatorias-excel`).

Bases que já reúnem algo: o "Mapa das Câmaras" do TCE-SP (custo das 644 Câmaras paulistas); o levantamento do TCE-PI
da fixação dos subsídios 2025–2028 por município (PDF de dez/2024); o acompanhamento do TCE-RN (PDF de 24 MB, não
aberto).
