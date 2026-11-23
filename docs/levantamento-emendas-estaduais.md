# Levantamento: emendas parlamentares estaduais

Levantado em 23/11/2026. Objetivo: saber, estado por estado, onde está o dinheiro que cada deputado estadual (ou
distrital) indica no orçamento do estado, para qual cidade ou entidade, para quê, e quanto foi pago. Serve para a
seção "Emendas dos deputados estaduais" na página da cidade e para a parte "Para onde mandou emendas" na página de
cada deputado em /politicos.

Legenda: **Verificado** = os dados foram abertos e contados · **Descrito** = só a página foi vista.
Dificuldade: **1** = arquivo ou API limpos · **5** = só tela, com bloqueio.

## Resumo dos 27

| UF | Fonte | Formato | Anos | Deputado | Cidade | Beneficiário | Valores | Emenda Pix estadual | Dif. | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| MG | dados.mg.gov.br `portal_emendas_estaduais` | CSV (CKAN) | 2021–2026 | sim (e blocos) | **código IBGE** | sim, com CNPJ e tipo | indicado, empenhado, liquidado, pago | sim, "Transferência especial" | 1 | Verificado |
| ES | dados.es.gov.br `portal-da-transparencia-emendas-parlamentares-do-estado` | CSV (CKAN) | 2021–2026 | sim | **código IBGE** (6 dígitos) | sim | previsto, empenhado, liquidado, pago | não (impositivas só em 2027) | 1 | Verificado |
| AC | planilha Google publicada pela Seplan | CSV | 2023–2026 | sim | nome | sim, com CNPJ | emenda, empenhado, liquidado, pago | sim | 1 | Verificado |
| MS | dados.ms.gov.br `emendas-parlamentares` | CSV 2024–26 (XLSX 2017–23 é outra base, só Educação) | 2024–2026 | sim (nome civil e político) | nome "Cidade - MS" | sim | **só o indicado** | não encontrada | 1 | Verificado |
| PA | api.emendas.seplad.pa.gov.br | API JSON/CSV | 2022–2026 | sim, com partido | nome | só o órgão executor | emenda, dotação, empenhado, liquidado, pago | não encontrada | 2 | Verificado |
| RJ | redeplan.planejamento.rj.gov.br (Seplag) | CSV/XLSX | 2024–2026 | sim | nome (~25% "Estado") | sim em 2025–26 | indicado; execução em arquivo à parte | sim, "Transferência especial" | 2 | Verificado |
| DF | API do portal da transparência do DF | JSON | 2016–2026 | sim (distritais) | o DF é uma cidade só | sim, por nota de empenho | aprovado, empenhado, liquidado, pago | não se aplica | 2 | Verificado |
| SC | painel Power BI da Fazenda | Power BI (API pública do painel) | 2023–2026 | sim | **código IBGE** | sim, com CNPJ | indicado, empenhado, liquidado, pago | sim (R$ 662 mi pagos em 2025) | 3 | Verificado |
| SP | painel Power BI do portal da transparência; PDFs da Alesp | Power BI; PDF | 2023–2025 | sim, com partido | nome | sim, com CNPJ | indicado e estágio, sem o pago em reais | na lei, mas o painel não separa | 3 | Verificado |
| PE | dados.pe.gov.br `emendasparlamentaresestaduais` | CSV/JSON (CKAN) | 2012–2026 (autor só em 2026) | só em 2026 | nome | sim, com CNPJ | orçamento, empenhado, liquidado, pago | sim, em 2026 | 1–2 | Verificado |
| AL | JSON da página do portal da transparência | JSON | só 2026 | sim, com partido | nome | sim | dotação, empenhado, liquidado, pago | sim | 2 | Verificado |
| MA | exportação do portal da transparência | CSV | só 2026 | sim | nome | sim, com CNPJ | solicitado, empenhado, liquidado, pago | na Constituição, sem marca nos dados | 2 | Verificado |
| SE | API do portal (2022–25) e painel de terceiros (2026) | JSON | 2022–2026 | sim (grafias diferentes nas duas fontes) | nome | sim | indicado e pago | sim, em 2026 | 2 | Verificado |
| PI | api.transparencia.pi.gov.br `emendas-estaduais` | API, CSV | 2021–2026 | sim | texto livre (2026); credor (2021–25) | sim | 2026 só indicado; 2021–25 empenhado e pago | sim (desde 2024) | 1–2 | Verificado |
| PB | api.dados.pb.gov.br `listagem_emendas` e `execucao_emendas` | API JSON | 2021–2026 | sim | só no texto do objeto | quase sempre vazio | indicado, empenhado, liquidado, pago | sim, em 2026 | 1 (cidade: 3) | Verificado |
| GO | dadosabertos.go.gov.br `emendas-parlamentares` (até 2023) e `transferencias-voluntarias` | CSV | 2019–2026 | sim (a partir de 2024 só no texto) | coluna até 2023; depois só no texto | sim (2022–23) | previsto, empenhado, pago | sim (Decreto 10.634/2025) | 2–3 | Verificado |
| AM | portal da Sefaz, `dadosabertos/emenda` | CSV por botão | 2020–2026 | sim (e bancadas) | só no texto (~38%) | não | cadastrado, empenhado, liquidado, pago | sim, no texto | 3 | Verificado |
| RO | transparencia.ro.gov.br/emenda | CSV/XLSX | 2023–2026 | sim | nome; ~46% "Estado de Rondônia" | texto, ~45% vazio | previsto; pago só em 2026 | sim | 2 | Verificado |
| RR | planilha Google do painel da Seplan | XLSX | 2023–2026 | sim | nome; ~72% "Roraima" | só o órgão | emenda, empenhado, liquidado, pago | sim | 2 | Verificado |
| TO | painel Shiny da Assembleia | CSV por botão | só 2026 | sim | texto | sim | indicado e pago | sim, no objeto | 3 | Verificado |
| AP | portal da transparência (SIGDOC) | CSV/XLSX | 2021–2024 | sim | só no texto (~metade) | não | previsto, empenhado, liquidado, pago | não encontrada | 2 | Verificado |
| MT | API da página da CGE | JSON | 2019–2026 | sim | só nos convênios (~26%) | só nos convênios | empenhado, liquidado, pago | sim (EC 89/2020) | 2 (cidade: 4) | Verificado |
| BA | dados.ba.gov.br `emendas-parlamentares` | ZIP com CSV | 2017–2026 | sim | **não tem**; só o credor | credor, sem CNPJ | orçado, empenhado, liquidado, pago | não | 2 (cidade: 4) | Verificado |
| RS | painel Power BI embutido no portal | Power BI com token | 2021–2026 | sim, com partido | nome; parte só no texto | credor | indicado, empenhado, liquidado, pago | não | 4 | Verificado |
| RN | painel Power BI do portal | Power BI | 2023–2026 | sim | nome padronizado | sim, com CNPJ | alocado; pago quase vazio | sim | 4 | Verificado |
| PR | Fazenda PR (só Desenvolvimento Social) | CSV | 2025–2026 | sim | nome | sim, OSCs | dotação, empenhado, liquidado, pago | não encontrada | 2, cobertura pequena | Verificado em parte |
| CE | portal Ceará Transparente | só tela | ? | sim (filtro) | região e prefeitura | prefeituras | ? | sim, "PCF" | 5 (bloqueio antirrobô) | Descrito |

### Quanto é, em 2025 (pago, quando o estado publica)

| UF | Linhas | Indicado | Pago |
|---|---|---|---|
| MG | 10.945 | R$ 2,30 bi | R$ 2,12 bi |
| SP | 5.617 | R$ 1,19 bi | R$ 1,06 bi "em Pagas" |
| SC | 4.161 | R$ 875 mi | R$ 765 mi |
| MT | 177 | — | R$ 603 mi |
| RR | — | — | R$ 554 mi (com coletivas e não impositivas) |
| AM | 1.009 | — | R$ 553 mi |
| DF | 656 | — | R$ 539 mi |
| GO | 2.657 pagamentos | — | R$ 494 mi |
| BA | 922 | R$ 572 mi | R$ 416 mi |
| RJ | — | R$ 203 mi | R$ 151 mi |
| PA | 677 | — | R$ 173 mi |
| PB | 821 | — | R$ 154 mi |
| PI | 883 empenhos | — | R$ 141 mi |
| ES | 2.430 | R$ 177 mi | R$ 96,5 mi |
| AC | 746 | — | R$ 90 mi |
| MS | 955 | R$ 83,6 mi | não publica |
| SE | 635 | R$ 72 mi | — |

## Cuidados que valem para vários estados

- **"Transferência especial" nem sempre é estadual.** BA, PE, RN, PB e AL têm conjuntos chamados "Transferências
  Especiais" ou "Emenda Pix" que são emendas **federais** recebidas pelo governo do estado (autores como Jaques
  Wagner e Otto Alencar, número no formato federal). Essas já estão nas emendas federais e não entram aqui.
- **Indicado não é pago.** A emenda é uma indicação. Ela só vira dinheiro quando o governo do estado empenha e paga.
  MS publica só o indicado; PI (2026), SP e RN quase não publicam o pago.
- **Blocos e bancadas.** Em MG os blocos partidários também indicam emendas (o maior, R$ 130 mi pagos em 2025); no AM
  e em RR há emendas de bancada e coletivas. Não são de um deputado só.
- **Cota igual.** Em MG cada deputado tem praticamente o mesmo valor (cerca de R$ 23,9 mi pagos em 2025). Comparar
  deputados pelo total diz pouco; o que muda é para onde mandaram.
- **CPF.** Os arquivos de ES (`CpfCnpjNis`), MG (execução) e o modelo do painel de SC trazem CPF de credor ou do
  parlamentar. O pipeline descarta essas colunas na leitura. Beneficiário pessoa física aparece só somado.
- **Nome do deputado.** Cada estado escreve de um jeito: nome de urna (MG, AC, RJ), nome civil (PA, MS traz os dois),
  "Dep. Fulano" (ES), "código - nome" (PI). O casamento com o TSE de 2022 usa a mesma regra de /politicos
  (`politicos_estaduais.tokens`): em MG, 65 dos 77 eleitos casam direto pelo nome; os outros 12 ("Doutor Jean
  Freire", "Professor Cleiton") precisam da regra de nomes contidos.
- **Cidade por nome.** Onde não há código IBGE, o nome é casado com a lista de municípios do estado. "Estado de X",
  "Roraima" ou "várias regiões" ficam como "o estado inteiro", fora da página da cidade.

## Por onde começar

1. **Primeira leva (arquivo aberto, com deputado, cidade e pago):** MG, ES, AC, PA, RJ, DF, e MS (só indicado).
2. **Segunda leva (painel Power BI ou só 2026):** SC e SP (painéis), PE, AL, MA e SE (2026 com cidade).
3. **Terceira leva (cidade só no texto ou no credor):** PI, PB, GO, AM, RO, RR, TO, AP, MT, BA.
4. **Difíceis:** RS e RN (Power BI com token ou pago vazio), PR (cobertura pequena), CE (bloqueio; pedir por LAI ou
   exportar no navegador).

---

# Notas por estado

As notas abaixo são as de cada região, com as URLs exatas, as colunas, os exemplos e o que não abriu.

## Emendas parlamentares estaduais: Norte e Centro-Oeste

Levantamento feito em 23/11/2026. Estados: MS, GO, MT, DF, AM, AC, PA, RO, RR, AP, TO.
MS, GO, MT, AM e AC foram levantados direto nesta sessão. PA, RO e RR (e AP, TO e DF) foram levantados por dois ajudantes; as seções deles estão no fim deste arquivo, copiadas de `parte-pa-ro-rr.md` e `parte-ap-to-df.md`.

Legenda de status: **Verificado** = abri os dados. **Descrito** = só vi a página. **Não encontrado**.

## Resumo

| UF | Fonte principal | Formato | Anos | Deputado | Cidade | Beneficiário | Valores | Emenda Pix | Dificuldade | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| MS | CKAN www.dados.ms.gov.br `emendas-parlamentares` | CSV (2024–26) + XLSX (2017–23, só Educação) | 2017–2026 | sim (nome completo + nome político; às vezes vários) | nome "Cidade - MS" (79 municípios, casa com o IBGE) | sim | só "Valor Emenda" (status sempre FINALIZADO) | não encontrada | 1 | Verificado |
| GO | CKAN dadosabertos.go.gov.br `emendas-parlamentares` (SERINT) + `transferencias-voluntarias` (CGE) | CSV/ZIP (XLSX) | 2019–2023 (emendas) / 2003–2026 (pagamentos) | sim (coluna até 2023; depois só no texto) | coluna em 2021 e 2023; depois só no texto | sim (2022–23; credor nos pagamentos) | 2022–23: previsto, empenhado, liquidado, pago; pagamentos: valor pago | sim (art. 111-A da Constituição de GO, Decreto 10.634/2025) | 2 até 2023; 3 a partir de 2024 | Verificado |
| MT | API da CGE-MT (transparencia-api.cge.mt.gov.br), que a página `consolidacao-emendas` chama | JSON | 2019–2026 | sim | só quando há convênio (proponente); fundo a fundo vem sem município | só em convênios (cerca de 26% das linhas) | empenhado, liquidado, pago (NOB) | sim (art. 164-A, EC 89/2020; Lei 12.127/2023) | 2 (3 para ter a cidade) | Verificado |
| AM | Sefaz-AM, Dados Abertos → Emenda Parlamentar Impositiva Estadual | CSV (por botão; a API usa parâmetros cifrados) | 2020–2026 | sim | só no texto do objeto (cerca de 38%) | não tem coluna | cadastrado, solicitado, autorizado, empenhado, liquidado, pago | sim, aparece no objeto (35 emendas, R$ 24,8 mi em 2025) | 3 | Verificado |
| AC | Planilha Google publicada que a página "Portal de Emendas Estaduais" da Seplan lê | CSV | 2023–2026 | sim | sim, nome (22 municípios + "Estado do Acre") com latitude/longitude | sim (nome + CNPJ) | valor emenda, empenhado, liquidado, pago, repassado | sim (modalidade "Transferência a Município (Transferência Especial)") | 1 | Verificado |
| PA | API da Seplad usada pelo portal (`api.emendas.seplad.pa.gov.br`) | JSON e CSV (API com chave pública no JS) | 2022–2026 | sim (nome completo + partido) | nome do município (texto padronizado, 1 por linha) | só o órgão estadual executor; entidade final só no texto do objeto | valor da emenda, dotação, empenhado, liquidado, pago | não aparece nos dados (nenhuma forma de repasse "transferência especial") | 2 | Verificado |
| RO | Portal da Transparência RO, `/emenda` (endpoints internos `/Emenda/Filtrar`, `/Emenda/GerarArquivo`) | JSON e CSV/XLSX (exportação do portal) | 2023–2026 | sim (nome curto + código) | "Município - RO" (texto) ou "Estado de Rondônia" (~46%) | campo texto extraído do histórico; ~45% "Não informado" | "valor previsto" (valor do empenho/pré-empenho), empenhado/liquidado/pago só preenchidos em 2026 | sim — aba "Transferências Especiais" (art. 135-A da Constituição de RO) | 2 | Verificado |
| RR | Painel Seplan-RR (Streamlit) → planilha Google pública + diretório de arquivos SECONV | XLSX (export do Google Sheets); CSV/XLSX/ODS no diretório | 2023–2026 | sim (nome; também comissões/coletivas) | nome do município ("Região de planejamento") ou "Roraima" (~72%) | só o órgão destino (SEINF, SESAU, OE…); entidade final no texto do objeto | valor da emenda, empenhado, liquidado, pago, a pagar | sim — tipo "Impositiva Transferência Especial" (art. 113-A da Constituição de RR) | 2 | Verificado |
| DF | API JSON do Portal da Transparência do DF | JSON paginado (API interna da página) | 2016–2026 | sim | RA só em texto livre (subtítulo) ou pelo órgão "Administração Regional de X" | sim, via nota de empenho (credor + CNPJ) | aprovado, autorizado, empenhado, liquidado, pago | não se aplica (sem municípios) | 2 | Verificado |
| TO | Painel Shiny da Assembleia (Aleto) | CSV pelo botão do painel | 2026 (o painel diz 2025–2026, mas o CSV só tem números /2026) | sim | nome em texto ("PREFEITURA MUNICIPAL DE X", "FUNDO MUNICIPAL DE SAÚDE DE X") | sim (proponente) | indicado (valor_destinado) e pago; empenhado só no total do painel | sim, na prática: 294 indicações com "TRANSFERÊNCIA ESPECIAL" no objeto (R$ 52,0 mi) | 3 | Verificado |
| AP | Portal da Transparência do AP → pastas no SIGDOC | CSV/XLSX/PDF, um arquivo por ano | 2021–2024 (sem 2025/2026) | sim | só em texto livre no objeto (cerca de metade das linhas cita município) | não há coluna; só órgão estadual executor e objeto | previsto, dotação, empenhado, liquidado, pago, restos a pagar | não encontrado | 2 (com problema de certificado TLS) | Verificado |

(Linhas PA, RO, RR, DF, TO e AP vêm das notas dos ajudantes; colunas na mesma ordem.)

---

### MS — Mato Grosso do Sul

**Status: Verificado.** Dificuldade: **1**.

#### Onde está
- CKAN: https://www.dados.ms.gov.br/dataset/emendas-parlamentares
- API: `https://www.dados.ms.gov.br/api/3/action/package_show?id=emendas-parlamentares`
- Observação: o endereço sem "www" (`dados.ms.gov.br`) **não resolve no DNS**. Use sempre `www.dados.ms.gov.br`.
- Recursos (atualizados em 17/03/2026):
  - 2017–2023 (XLSX): `https://www.dados.ms.gov.br/dataset/18d18201-7912-408d-ac98-8eb90737cf95/resource/9db1c1b5-5dc1-4805-ab64-54d79843dc0e/download/emendas-parlamentares-2017-a-2023.xlsx`
  - 2024 (CSV): `.../resource/86b71a17-f10e-4822-946b-0fed57c42afd/download/emendas_resumo_2024.csv`
  - 2025 (CSV): `.../resource/9931aa9b-b3dc-43a4-9672-9f0075176355/download/emendas_resumo_2025-1.csv`
  - 2026 (CSV): `.../resource/024c1105-d80e-4885-b7e0-a377e18ec4a5/download/emendas_resumo_2026.csv`
  - Dicionário (PDF, 1 página; descreve só o XLSX antigo): `.../resource/d23f1f22-e82d-460f-92b9-812adad43b2b/download/dicionario-de-dados-tfo25.pdf`

### CSV 2024–2026
- Formato: `;`, UTF-8, campos entre aspas.
- Cabeçalho: `"Nº da emenda";"Beneficiário(a)";"Município";"Objeto";"Órgão";"Valor Emenda";"Responsável Beneficiária";"Deputado(s)";"Nomes(s) Político(s)";"Nº do processo";"Status";"Última atualização"`
  - A lista de colunas da pista estava incompleta: também existem `Responsável Beneficiária` (nome de uma pessoa, o responsável pela entidade) e `Nomes(s) Político(s)` (nome de urna).
- **Deputado:** `Deputado(s)` traz o nome civil completo e `Nomes(s) Político(s)` o nome político. Quando a emenda é coletiva, vêm vários nomes separados por **vírgula + espaço**, na mesma ordem nas duas colunas.
  - 2024: 2 linhas coletivas. 2025: 9. 2026: 2.
  - Em 2025, a emenda 281 (Fundação Pio XII, Dourados, R$ 1,6 mi) tem 16 deputados.
  - O valor não vem dividido por deputado. Para atribuir o valor, é preciso dividir em partes iguais ou marcar a emenda como coletiva.
- **Município:** formato `"Laguna Carapã - MS"`, com acento. São 79 nomes distintos em 2024 e 2025, ou seja, todos os municípios de MS; nenhuma linha vazia. Basta tirar o " - MS" para casar pelo nome com o IBGE. Não há código IBGE.
- **Beneficiário:** nome da entidade (fundo municipal de saúde, APM de escola, associação, hospital).
- **Status:** é sempre `FINALIZADO` (903/903, 955/955, 454/454). Ou seja, o arquivo só lista as emendas já concluídas.
- **Valor:** só há `Valor Emenda` (ex.: `"R$ 80.000,00"`). Não há colunas de empenhado ou pago. Como todas as linhas estão finalizadas, o valor é, na prática, o executado (conveniado ou repassado), mas o portal não diz isso. Não há execução orçamentária.
- **Órgão:** em 2025, SES 569, SED 181, SEAD 101, Fundesporte 57 etc.

| Ano | Linhas | Soma "Valor Emenda" | Deputados (nome político) |
|---|---|---|---|
| 2024 | 903 | R$ 70.543.000 | 26 |
| 2025 | 955 | R$ 83.605.000 | 32 |
| 2026 (até março) | 454 | R$ 28.060.000 | 25 |

Exemplos reais:
- 2024, emenda 2: Pedro Kemp, Laguna Carapã - MS, Fundo Municipal de Saúde de Laguna Carapã, "Custeio – Ações e Serviços em Saúde", R$ 80.000,00.
- 2024, emenda 821: Paulo Corrêa, Água Clara - MS, Fundo Municipal de Saúde de Água Clara, R$ 150.000,00.
- 2025: Marcio Fernandes, Iguatemi - MS, APM da EEPSG Marcílio Augusto Pinto, ar-condicionado e datashow, R$ 50.000,00.

### XLSX 2017–2023
- É outra base: parece ser só das emendas executadas pela **Secretaria de Educação** (tem "Quantidade de alunos", "Educação Básica"). Há uma linha por item comprado.
- Colunas: `Número do termo, Número do processo, Status da solicitação, Processo de reformulação, Ano, Nome do deputado, Município, Instituição, Endereço, Telefone, Ação a ser financiada, Descrição Sintética do Objeto, Justificativa, Quantidade de alunos, Valor total da solicitação, Descrição da ação, Contrapartida, Total da ação, Descrição da subação, Valor total da subação, Descrição do item, Quantidade, Valor por unidade`
- Tamanho: 1.179 linhas de itens e 206 processos. Em 73 processos o deputado está vazio. 202 dos 206 beneficiários são prefeituras.
- Somas por processo (valor solicitado):

| Ano | Processos | Soma |
|---|---|---|
| 2017 | 59 | R$ 2,50 mi |
| 2020 | 44 | R$ 2,35 mi |
| 2021 | 43 | R$ 2,77 mi |
| 2022 | 28 | R$ 2,39 mi |
| 2023 | 19 | R$ 1,47 mi |

- Status: Celebrada, Com pendência, Aguardando Assinatura etc.
- Município sem "- MS" e sem código IBGE.
- Conclusão: para 2017–2023 não há base completa de MS; esta cobre só Educação.

#### Emenda Pix
**Não encontrada.** As emendas de deputado estadual em MS não parecem ser impositivas por regra constitucional: são negociadas com o governo, com valores anunciados de cerca de R$ 2 mi por deputado em 2023. Uma notícia do Midiamax de 2026 diz que a Assembleia "enterrou" as emendas individuais na LDO. Também não achei o termo "transferência especial" para as emendas estaduais de MS.

#### Dificuldade 1
Três CSVs limpos e um XLSX pelo CKAN. Só é preciso separar os nomes de deputados por vírgula.

---

### GO — Goiás

**Status: Verificado** (emendas 2019–2023 e pagamentos 2025). EmendasGo (2025–2026) ficou só **Descrito**, porque tem reCAPTCHA.

**Acesso:** o `dadosabertos.go.gov.br` devolve uma página "Acesso Negado" ao curl desta máquina. Não tentei contornar. Baixei pelo WebFetch, que guarda o binário: o ZIP de 2025 e o ZIP 2019–2023. Para automatizar será preciso rodar de outro lugar ou testar a liberação.

### 1) Conjunto `emendas-parlamentares` (SERINT) — base específica de emendas
- Página: https://dadosabertos.go.gov.br/dataset/emendas-parlamentares (Secretaria de Relações Institucionais). Criado em 2022; "Última atualização" em 23/11/2026, mas o recurso mais novo é de 2023.
- Recursos:
  - ZIP 2019–2023: `https://dadosabertos.go.gov.br/dataset/74a44295-f948-4f71-a91c-cc7cd0eabc2c/resource/d1f86df4-e80e-420a-81b9-181c71de5f28/download/emendasparlamentares_2019_2023.zip`
  - CSVs anuais: `.../resource/{f3079186…(2019), e53ba784…(2020), b2386964…(2021), 166a6e86…(2022), d0e4f464…(2023)}/download/emendasparlamentares_AAAA.csv`
  - Dicionário: `.../resource/2759dde5-a5d0-47e6-a722-1d4155c9231f/download/dicionario_dados_emendas-parlamentares.pdf`
- Formato dos arquivos: `;`, Latin-1. **O layout muda todo ano.**

| Ano | Linhas | Colunas | Soma |
|---|---|---|---|
| 2019 | 694 | `EMENDA; VALOR; DEPUTADO; NOME (órgão); OBJETO`. Cidade só no objeto. | R$ 114,0 mi |
| 2020 | 1.391 | `Nº EMENDA; VALOR; DEPUTADO AUTOR; UNIDADE RESPONSÁVEL; OBJETO` ("…da cidade de Acreúna-GO") | R$ 571,3 mi |
| 2021 | 2.022 | `DEPUTADO(A); Área; Tipo; EMENDA NÚMERO; PRODUTO; MUNICÍPIO; VALOR R$`. Município é coluna: 248 nomes, 12 vazios. | R$ 403,2 mi |
| 2022 | 2.845 | `Emenda; TIPO DE EMENDA; VALOR DA EMENDA; DEPUTADO AUTOR; SECRETARIA RESPONSÁVEL; OBJETO ORIGINAL DA EMENDA; Beneficiário (CPF/CNPJ); Beneficiário (Nome); Número do Processo; Sequencial Empenho; Empenhado; Liquidado; Pago; Liquidado Não Pago; Não Liquidado e Não Pago; Saldo a Pagar` | valor R$ 387,0 mi; empenhado R$ 341,9 mi; pago R$ 106,9 mi |
| 2023 | 1.927 | `Ano Emenda; Orgão; Nº Processo; Função (Área); Subfunção; Nº Emenda; Autor da Emenda; Objeto; Município; Beneficiário; CNPJ do Beneficiário; Valor Previsto (R$); Valor Empenho (R$); Valor Liquidado (R$); Valor Pago (R$)`. 247 municípios. | previsto R$ 864,7 mi; pago R$ 822,7 mi |

- Alguns arquivos têm linhas quebradas (o pandas pulou algumas linhas). Os totais são aproximados.
- O deputado vem como "DEP. JÚLIO PINA", "Ze Da Imperial" etc. A grafia muda de ano para ano, então é preciso normalizar.
- Exemplos reais:
  - 2023: Ze Da Imperial, SANTA TEREZINHA DE GOIAS, Fundo Municipal de Saúde, custeio, previsto, empenhado e pago R$ 300.000.
  - 2021: Álvaro Guimarães, ITUMBIARA, Saúde/Impositiva, "CUSTEIO - CIRURGIAS ELETIVAS", R$ 800.000.
  - 2022: Dep. Júlio Pina, FES, "custeio na saúde do município de Montividiu do Norte", R$ 180.000.

### 2) Conjunto `transferencias-voluntarias` (CGE) — pagamentos, inclusive de emendas
- Página: https://dadosabertos.go.gov.br/dataset/transferencias-voluntarias
- Recursos:
  - Mensais em 2026: `.../dataset/d95472ce-e543-4e5e-8472-cd73cd966e40/resource/61913e99-0aef-4e51-9d2e-68e1e540b815/download/transferencias-voluntarias-202605.csv` (e 202601 a 202604)
  - ZIP anual 2021–2025, por exemplo 2025: `.../resource/2223f483-fbf2-44e7-b9c2-4bc1348ac629/download/transferencias-voluntarias-2025.zip` (dentro vem um XLSX)
  - ZIP 2011–2020 e ZIP 2003–2010.
- Colunas: `Unidade Orçamentária; Modalidade de Aplicação; Elemento Despesa; Sub Elemento; Formalidade; CPF/CNPJ; Nome/Razão Social do Credor; Numero Processo; Numero de Processo; DESCRICAO; Data do Repasse; Fonte de Recursos; Valor do Pagamento (R$)`
- **É uma base de pagamentos:** cada linha é um repasse pago.
- 2025: 8.771 linhas (R$ 12,4 bi no total). Delas, **2.657 linhas citam "emenda" na DESCRICAO, somando R$ 494,2 mi pagos**.
- O deputado e o município aparecem **só no texto livre** da DESCRICAO, em vários modelos. Exemplos:
  - "Emenda Parlamentar Impositiva número 1172.1 Município PORTEIRAO Deputado (a) TALLES ALVES BARRETO. Objeto da emenda…"
  - "EMENDA PARLAMENTAR IMPOSITIVA Nº 1313 DO DEPUTADO ESTADUAL ANDERSON TEODORO, PARA DESTINAÇÃO DE RECURSOS AO FUNDO MUNICIPAL DE SAÚDE DE FORMOSA - GO"
- Com uma regex simples: deputado extraído em 2.620 das 2.657 linhas; município em 2.191. É preciso tratar o modelo "FUNDO MUNICIPAL DE SAÚDE DE X - GO". O nome do deputado aparece ora completo ("MAURO RUBEM DE MENEZES JONAS"), ora curto ("BIA DE LIMA" / "MARIA EUZEBIA DE LIMA"), então precisa de uma tabela de apelidos.
- Beneficiário: `Nome/Razão Social do Credor` (há CPF/CNPJ na base; não copiei).
- Modalidade, entre as linhas de emenda de 2025: fundo a fundo 1.050; transferências a municípios 872; entidades sem fins lucrativos 725.
- 31 descrições citam "Transferência Especial" (R$ 7,13 mi).
- Exemplos reais (2025):
  - Charles Bento, Aragoiânia, aquisição de grade e plantadeira, "Transferência Especial".
  - Jamil Sebba Calife, Araçu, reforma da Escola Municipal Cantinho do Saber.
  - Júlio Pina, Goiânia, Associação de Incentivo ao Esporte Amigos da Vila Pedroso, R$ 100.000 (pago em 27/05/2026).

### 3) Outros
- Conjunto `emendas-impositivas-via-transferencia-especial` (UEG): só as emendas recebidas pela universidade. Recurso: `https://dadosabertos.go.gov.br/dataset/05025f34-29b7-4731-8a6b-26befdb82465/resource/d21554b1-2d86-4532-b16c-b9d36fb38115/download/emendas-impositivas-via-transferencia-especial.csv`. Descrito; não abri.
- **EmendasGo** (indicações de 2025 e 2026): https://sislog.go.gov.br/EmendasParlamentares/RelatorioIndicacaoAlteracao, linkado em https://transparencia.go.gov.br/emendas-parlamentares-de-goias/
  - A tabela tem as colunas Ano, Processo, Emenda, Situação, Área, GND, Parlamentar, Partido, Valor Emenda, Beneficiário, Tipo Benef., Local, Objeto, Forma de Repasse (Modalidade), Nº do Ajuste, Valor Beneficiário (Previsto), Valor Empenhado, Empenho, Valor Liquidado, Valor Pago, Datas e Prestação de Contas. É o mais completo.
  - Mas a consulta usa **reCAPTCHA** (`captcha.execute(...)`). Não usei.
- A página do portal diz que o painel de execução (empenhado e pago desde 2021) existe, mas não carregou no que vi.

#### Emenda Pix
**Sim.** O art. 111-A da Constituição de GO e o Decreto 10.634/2025 regulam as emendas individuais impositivas. As páginas dos órgãos citam expressamente "transferências especiais (emendas pix)", e as descrições de pagamento usam "Transferência Especial".

#### Dificuldade
- 2019–2023: **2** (CSV aberto, mas o layout muda todo ano).
- 2024 em diante: **3**, porque é preciso tirar deputado e município do texto dos pagamentos; o EmendasGo tem captcha.
- Mais o bloqueio do dadosabertos para robô.

---

### MT — Mato Grosso

**Status: Verificado** (API da CGE, 2025 inteiro).

#### Onde está
- Página no portal: https://www.transparencia.mt.gov.br/?c=79521669 ("Emendas Parlamentares"). Ela leva a três lugares:
  1. **Consolidação de emendas (CGE-MT):** https://transparencia.cge.mt.gov.br/consolidacao-emendas. É um app React que chama a API `https://transparencia-api.cge.mt.gov.br/api/v1/sigcon/...`.
     - A API pede o cabeçalho `X-API-Key`. A chave é pública e está no JS da própria página (`/assets/index-*.js`); pode mudar quando o site for atualizado.
     - Endpoints úteis:
       - `consolidacao-emendas/anos` → [2019…2026]
       - `consolidacao-emendas?ano=2025&limit=1000&offset=N` (paginado; o `limit=1000` funciona)
       - `consolidacao-emendas/export`
       - `total-emendas?ano=2025`
       - `parlamentares`
       - `emendas/fiplan?ano=` (empenho, liquidação e NOB por emenda)
       - `emendas/fiplan/empenhos`, `emendas/fiplan/nobs`
       - `convenios/listagem`
  2. **Despesa por emenda (Sefaz):** https://consultas.transparencia.mt.gov.br/despesa/emendas_parlamentares/. Tem filtros por ano (2018–2026), autor, órgão e função, e exporta CSV, Excel e PDF. Os totais de 2026 mostrados na página: empenhado R$ 1.241.897.786,17; liquidado R$ 1.108.471.509,71; pago R$ 952.953.059,17. A página usa **reCAPTCHA v3**, que redireciona para 404 se a validação falhar. Não usei os downloads dela.
  3. **SIGCON (convênios):** https://transp.sigcon.seplan.mt.gov.br/index_.php. Filtro por parlamentar e nº da emenda; mostra concedente, proponente, objeto, valor e "Val. Utilizada Emenda". É HTML paginado.
- dados.mt.gov.br e dadosabertos.mt.gov.br: nada sobre emendas (a busca no CKAN deu 0).

#### Campos (`consolidacao-emendas`)
`conv_id, emenda, parlamentar, concedente_cnpj, concedente, proponente, proponente_cnpj, objeto, processo, numero_convenio, vlr_total_convenio, val_utilizado_emenda, cd_exercicio_processo_fiplan, numr_processo_fiplan, ano_emenda_parlamentar_fiplan, numr_emenda_parlamentar_fiplan, emenda_fiplan, origem_fiplan, ds_iduso_fiplan, cd_modalidade_aplicacao_fiplan, ds_modalidade_aplicacao_fiplan, total_valr_emp_bruto, total_est_emp, valr_emp_liquido, total_valr_liq, total_valr_nob`

- Deputado: sim (`parlamentar`, por exemplo "Dep. Gilberto Cattani"). Também aparecem "Lideranças Partidárias" e "Comissão de Fiscalização".
- Beneficiário e cidade: só quando há convênio no SIGCON (`proponente`). Isso vale para 568 das 2.161 linhas de 2025.
- Nas transferências fundo a fundo para municípios (941 linhas), o município **não aparece**: só o órgão de origem (FES). Para ter a cidade será preciso:
  - cruzar o empenho/NOB com o credor em outra fonte (a despesa da Sefaz, que tem captcha), ou
  - usar a despesa geral por favorecido, filtrando o uso "EMENDAS PARLAMENTARES IMPOSITIVAS".
- Valores: empenhado bruto, estorno, empenhado líquido, liquidado e pago (NOB). Não há "valor indicado" separado.

#### 2025
- `total-emendas`: 177 emendas, 874 repasses; empenhado R$ 619,5 mi, liquidado R$ 605,4 mi, pago R$ 602,7 mi.
- A listagem tem 2.161 linhas (uma por processo FIPLAN × convênio), 50 grafias de parlamentar e 1.846 processos distintos.
- Somando as linhas há dupla contagem quando um processo tem vários convênios: dá R$ 622,1 mi empenhado e R$ 602,8 mi pago, contra R$ 543,8 mi e R$ 527,1 mi deduplicando por processo. É preciso entender melhor a chave antes de somar.
- Modalidades:
  - Instituições privadas sem fins lucrativos: 1.054
  - Municípios fundo a fundo: 941
  - Transferências a Municípios: 145
  - Aplicação direta: 16
- O nome do parlamentar aparece com e sem "Dep." (por exemplo "Dep. Gilberto Cattani" e "Gilberto Cattani"), então precisa normalizar.

Exemplos reais (2025):
- Gilberto Cattani, emenda 100/2025, SEAF → Instituto Carvalho Assis (convênio 3469-2025, aquaponia), R$ 30.000 pagos.
- Gilberto Cattani, emenda 100/2025, Fundo Estadual de Saúde, fundo a fundo a município (não diz qual), R$ 50.000 empenhados e pagos.
- SIGCON 2026: Valdir Barranco, emenda 130/2026, SEDEC → Câmara de Comércio Italiana de SP, R$ 100.000. Fabinho, emenda 178, SEDEC → Instituto Vale do Rio Cuiabá (Natal em Alto Paraguai), R$ 527.000.

#### Emenda Pix
**Sim, prevista em lei.** O art. 164-A da Constituição de MT, incluído pela EC 89/2020 (com regras na EC 102/2021), autoriza repassar recursos estaduais a municípios por emenda. A Lei 10.587/2017, alterada pela Lei 12.127/2023, admite transferência especial para as emendas impositivas. Nos dados, não há um rótulo "transferência especial"; as 145 linhas de "Transferências a Municípios" (modalidade 40) são as candidatas.

#### Dificuldade
- **2** para deputado e valores (API JSON paginada).
- **3–4** para ter a cidade nas transferências fundo a fundo: falta o credor na API e a fonte que tem o credor usa captcha.

---

### AM — Amazonas

**Status: Verificado** (CSV 2025 aberto no navegador embutido).

#### Onde está
- Portal: https://sistemas.sefaz.am.gov.br/transparencia/ (app React).
  - Dados abertos: https://sistemas.sefaz.am.gov.br/transparencia/dadosabertos/emenda. Tem o bloco "Emenda Parlamentar Impositiva Estadual" (anos 2020–2026) e o bloco "Emenda Parlamentar Federal" (2024–2026), cada um com botão "Exportar dados" que gera um CSV.
  - Consulta detalhada: https://sistemas.sefaz.am.gov.br/transparencia/emendas-parlamentares. Tem janelas de detalhe com convênio e pagamentos.
- **Não é arquivo direto.** O botão chama `GET /transparencia/api/dadosabertos/emenda/estadual?ek=…&ed=…`. Os parâmetros (`{exercicio: 2025}`) vão cifrados com AES, e a chave AES vai cifrada com a chave RSA pública que o servidor entrega. Há também um token de acesso no localStorage.
  - Dá para reproduzir em script: a chave pública vem do servidor e o algoritmo está no JS. Mas é mais frágil; o caminho fácil é um navegador automatizado clicando no botão.
  - Para esta amostra, capturei o blob do CSV no navegador.
- Dicionário (PDF): `https://sistemas.sefaz.am.gov.br/transparencia/static/media/dicionario_dados_emenda_estadual.b09830f5f7c06538dc15.pdf`

#### Campos (CSV, `;`, Windows-1252)
`"tipo";"autor";"orgao";"numero";"ano";"programatrabalho";"objeto";"vacadastrado";"vasolicitado";"vaautorizado";"vaempenhado";"valiquidado";"vapago"`

- Deputado: sim (`autor`, nome civil completo). Nas emendas de bancada vem o nome da bancada, por exemplo "Bancada PT/PV/MDB".
- Cidade: **não tem coluna.** Aparece só no texto do `objeto` ("…FUNDO A FUNDO PARA O MUNICÍPIO DE ALVARÃES…"), em cerca de 381 das 1.009 linhas de 2025. O resto é órgão estadual, unidade de saúde ou Manaus implícito.
- Beneficiário: não tem coluna; só o órgão estadual executor e o objeto.
- Valores: cadastrado (indicado), solicitado, autorizado, empenhado, liquidado e pago.

#### 2025
- 1.009 linhas: 630 individuais e 379 de bancada; 32 autores.
- Somas:

| Valor | Soma |
|---|---|
| Cadastrado | R$ 585,0 mi |
| Autorizado | R$ 584,7 mi |
| Empenhado | R$ 581,7 mi |
| Liquidado | R$ 559,9 mi |
| Pago | R$ 553,2 mi |

- Órgãos que mais aparecem: Fundo Estadual de Saúde 267, Secretaria de Cultura 155, Fundo de Assistência Social 148.

Exemplos reais (2025):
- Abdala Habib Fraxe Junior, FES, fundo a fundo para o município de Alvarães (mutirão de cirurgias eletivas), R$ 500.000 cadastrados e pagos.
- Abdala Habib Fraxe Junior, Sedecti, "através de transferência especial, para Prefeitura Municipal de Nhamundá" (reforma do matadouro), R$ 500.000 pagos.
- Bancada PT/PV/MDB, Seduc, convênio com a Prefeitura de Manacapuru, R$ 2.000.000 empenhados e R$ 0 pagos.

#### Emenda Pix
**Sim, de fato.** 35 objetos de 2025 dizem "através de transferência especial, para Prefeitura Municipal de …", somando R$ 24,8 mi cadastrados. Não li a base legal na Constituição do AM.

#### Dificuldade 3
O CSV é bom, mas só sai pelo botão (com parâmetros cifrados), e a cidade só existe no texto livre.

---

### AC — Acre

**Status: Verificado.** Dificuldade: **1**.

#### Onde está
- Portal da Transparência: https://transparencia.ac.gov.br/conteudo/emendas-parlamentares-estaduais. Só mostra, num iframe (`/conteudo/emendas-parlamentares-estaduais/proxy`), a página da Seplan.
- Seplan, "Portal de Emendas Estaduais": https://seplan.ac.gov.br/gestao-estrategica-de-recursos/convenios/portal-de-emendas-estaduais/ (também em `/gestao-de-recursos/convenios/emendas-parlamentares-estaduais/`). Tem as abas Emendas (tabela com filtros e Excel/PDF), Painel (Power BI "Painel de Atuação Parlamentar": `https://app.powerbi.com/view?r=eyJrIjoiZmE0ZTllNjAtNWJmOS00MDYwLWI5ZWMtYWQxODVmMGQ2MWRlIiwidCI6IjU3ZjkyMjQxLTcxZDktNGU3OC05YTYwLWVhYjZiM2I1ZmZiOSJ9`) e Editais (PDFs com listas de beneficiários por edital).
- **A tabela lê uma planilha Google publicada, em CSV direto:** `https://docs.google.com/spreadsheets/d/e/2PACX-1vRzbV0AT43iRHZEQ4ovc5jbywcxI2De6p_dYftLPkuV3ZsiemRCdhjbhHE8pk_f_FnzHi9rM67PqyYh/pub?gid=1271042240&single=true&output=csv`
  - O endereço está no HTML da página (`const csvUrl = …`).
  - Baixado com um GET: 3,8 MB, 2.894 linhas.
- dados.ac.gov.br (CKAN): a busca por "emenda" deu 0.

#### Campos (CSV com vírgula, UTF-8)
`N° Emenda, Ano, Parlamentar, Descrição Modalidade Aplicacao Estadual, Municípios, Latitude, Longitude, Objeto da Emenda, Concedente, CNPJ Concedente, CNPJ Entidade Beneficiada, Nome Entidade Beneficiada, Valor Emenda, Situação, Número SEI, Link SEI, Situação de Plano de Trabalho, Área Temática, Observações, Número do Instrumento de Repasse, Data do Repasse, Valor Repassado, Valor do Instrumento de Repasse, Observação do Instrumento de Repasse, Início/Término da Vigência, Situação do Instrumento de Repasse, Situação da Prestação de Contas, Data do recebimento da prestação de contas, Banco, Agência, Conta Corrente, Reduzido Funcional, Órgão, Órgão/Unidade, Descrição Projeto Atividade, Elemento de Despesa, Ini+Sup+Cor-Red, Empenhado, Liquidado, A Liquidar, Pago, A Pagar, Disponível, Diagnóstico da Execução, Data da Atualização no SICAF, Espelho de Emenda, Notificação da Prefeitura, Parecer de Aprovação, Plano de trabalho aprovado, Termo de Instrumento de Repasse`

- Deputado: sim (`Parlamentar`, 36 nomes).
- Cidade: sim (`Municípios`, nome com acento, mais latitude e longitude). São 22 municípios mais "Estado do Acre" (446 linhas). Casa pelo nome com o IBGE. Não há código IBGE.
- Beneficiário: sim (nome e CNPJ). Não vi CPF (nenhum documento com 11 dígitos).
- Valores: valor da emenda (indicado), dotação, empenhado, liquidado, pago, a pagar e valor repassado.
- Cuidado com números: há formatos misturados ("300.000,00", "100000", "100000,00"). A soma do "Valor Repassado" de 2026 saiu absurda (R$ 2×10¹³) por causa disso, então é preciso tratar o formato célula a célula.
- Situação: Pago 1.553; Não Executado/Impedimento Técnico 616; Valor Disponível 567; Executado parcialmente 108; Restos a pagar 40.
  - Muitas linhas com impedimento técnico têm Valor Emenda 0.
- Três números de emenda aparecem duplicados.

| Ano | Linhas | Valor emenda | Empenhado | Pago |
|---|---|---|---|---|
| 2023 | 550 | R$ 48,0 mi | R$ 46,1 mi | R$ 44,5 mi |
| 2024 | 514 | R$ 76,8 mi | R$ 75,5 mi | R$ 69,5 mi |
| 2025 | 746 | R$ 95,95 mi | R$ 93,9 mi | R$ 90,0 mi |
| 2026 | 1.084 | R$ 115,2 mi | R$ 81,6 mi | R$ 55,7 mi |

Os anos 2024 e 2025 batem com uma cota de cerca de R$ 3,2 mi e R$ 4 mi por deputado (24 deputados).

Exemplos reais:
- 2023: André Vale, Brasiléia, Município de Brasiléia (convênio, Deracre), combustível para ramais, R$ 300.000, Pago.
- 2025: Nicolau Junior, Porto Walter, Município de Porto Walter, R$ 100.000 pagos.
- 2025: Afonso Fernandes, Rio Branco, Associação Mãos Criativas do Acre (Amacre), capacitação em gastronomia, R$ 120.000 pagos.
- 2025: Chico Viga, Cruzeiro do Sul, Conselho Escolar Nonata Cacheiro, R$ 20.000 pagos.

#### Emenda Pix
**Sim.** A modalidade "Transferência a Município (Transferência Especial)" aparece nos dados:

| Ano | Linhas | Valor | Pago |
|---|---|---|---|
| 2024 | 56 | R$ 12,65 mi | (tudo pago) |
| 2025 | 43 | R$ 12,2 mi | (tudo pago) |
| 2026 | 84 | R$ 18,9 mi | R$ 12,4 mi |

#### Dificuldade 1
Um CSV único e completo num GET. É a melhor fonte da região, mas depende de uma planilha Google (o link pode mudar sem aviso).

---

## Seções dos ajudantes (PA, RO, RR, DF, TO, AP)


### PA — Pará

**Status: Verificado** (baixei JSON de 2022 a 2026 e CSV de 2025).

#### Onde está
- Página da ALEPA "Emendas Parlamentares Estaduais" (`https://alepa.pa.gov.br/Transparencia/Page/EmendasParlamentaresEstaduais`) só redireciona para o portal do Executivo:
  `https://www.sistemas.pa.gov.br/portaltransparencia/emendas-parlamentares-estaduais` (SPA em Vue).
- O JS da página (`/portaltransparencia/assets/publicEmendasService.1531586f.js`) chama a API da Seplad:
  - Base: `https://api.emendas.seplad.pa.gov.br/api/v1/transparencia`
  - Cabeçalho `X-API-KEY` com uma chave **pública, fixa, embutida no próprio JS** (não é credencial de usuário; pegar do arquivo JS citado).
  - `GET /emendas/opcoes` → anos disponíveis (2022, 2023, 2024, 2025, 2026), lista de parlamentares, partidos, órgãos, municípios (144 + "Diversos"), regiões de integração, funções, tipos de instrumento.
  - `GET /emendas?ano=2025` → JSON `{"data":[...]}` com todas as emendas do ano (sem paginação).
  - `GET /emendas?ano=2025&formato=csv` (Accept: text/csv) → CSV com as mesmas colunas (instrumentos e cronograma achatados em texto).
  - Parâmetro opcional `q` = busca geral.
- `transparencia.pa.gov.br` (portal antigo): **certificado TLS expirado** — nem curl nem WebFetch abrem. `dados.pa.gov.br` não respondeu (timeout). Não precisou: a API acima resolve.
- Normas: Portaria 492/2026-CCG obriga registro das emendas no módulo "Emendas Parlamentares" do SIGPLAN; Resolução TCE-PA 19.800/2025 exige plataforma unificada a partir de 01/01/2026.

#### Campos (cabeçalho do CSV)
`objeto, codigo, tipo_emenda, cancelada, municipios, regioes, ano, valor, parlamentar, partido, orgao_sigla, orgao_descricao, forma_repasse, funcao_governo, numero_empenho, dotacao, empenhado, liquidado, pago, instrumentos, cronograma_execucao`

- Deputado: `parlamentar` (nome civil completo, ex.: "Carlos Alberto Barros Bordalo") + `partido`. Não traz o nome de urna.
- Cidade: `municipios` = nome do município (texto padronizado, sem código IBGE; 1 município por linha nas amostras; poucas linhas "Diversos": 6 em 2024, 3 em 2025, 4 em 2026). `regioes` = região de integração.
- Beneficiário: a tela chama `orgao_sigla` de "Beneficiário ou Credor", mas é o **órgão estadual executor** (FES, Fundação ParáPaz, SEEL, SEASTER, FUNTELPA…). Entidade/prefeitura final aparece só no `objeto` e nos `instrumentos` (tipo, número, link para PDF no Google Drive).
- Objeto: `objeto` (texto curto).
- `tipo_emenda`: só "individual". `forma_repasse` quase sempre vazio (2025: 639 vazios, 35 "Termo de fomento", 3 "Fundo a fundo").

#### Valores
- `valor` (valor da emenda), `dotacao`, `empenhado`, `liquidado`, `pago`. Todos numéricos.
- Execução muito alta: parece que o painel lista emendas já executadas/em execução.

| Ano | Linhas | Valor emendas | Empenhado | Pago | Deputados |
|---|---|---|---|---|---|
| 2022 | 298 | R$ 71,9 mi | R$ 71,4 mi | R$ 71,4 mi | 41 |
| 2023 | 345 | R$ 74,2 mi | R$ 74,6 mi | R$ 74,6 mi | 42 |
| 2024 | 564 | R$ 139,8 mi | R$ 140,9 mi | R$ 140,9 mi | 41 |
| 2025 | 677 | R$ 183,0 mi | R$ 173,5 mi | R$ 173,3 mi | 42 |
| 2026 | 747 | R$ 263,5 mi | R$ 241,1 mi | R$ 240,2 mi | 41 |

(2025: mediana de R$ 4,74 mi por deputado, teto R$ 4,75 mi — bate com cota individual.)

#### Exemplos reais (2025)
- Carlos Alberto Barros Bordalo (PT) | Belém | SEEL (Termo de fomento 07/2025) | "I CIRCUITO DE MMA AMADOR" | valor R$ 550.000, pago R$ 550.000.
- Antonio Gomes De Lima (PL) | Capitão Poço | FES | "CUSTEIO FUNDO A FUNDO PARA ATENÇÃO BÁSICA…" | R$ 1.500.000, pago R$ 1.500.000.
- Aveilton Silva de Souza | Itupiranga | SEASTER | custeio fundo a fundo municipal de assistência social | R$ 200.000, pago R$ 200.000.

#### Emenda Pix
Não encontrada. Nos dados não há forma de repasse "transferência especial"; os repasses a municípios aparecem como "fundo a fundo" (saúde/assistência) via FES/SEASTER. Não consegui abrir a Constituição do Pará no site da ALEPA (download deu erro 500) para confirmar se existe o art. equivalente ao 166-A. Há notícia (O Liberal, 2026) de PEC que sobe a emenda individual impositiva de 1,2% para 1,55% da RCL.

#### Dificuldade: 2
API JSON/CSV limpa, um pedido por ano. O único cuidado: precisa do cabeçalho `X-API-KEY` tirado do JS público (pode mudar quando o front for reconstruído). Município vem por nome (precisa casar com IBGE).

Arquivos: `baixados/PA/emendas_2022.json` … `emendas_2026.json`, `emendas_2025.csv`.

---

### RO — Rondônia

**Status: Verificado** (baixei JSON 2024/2025 das duas abas e o CSV completo 2023–2026).

#### Onde está
- Portal da Transparência do Executivo (CGE-RO): `https://transparencia.ro.gov.br/emenda` — título "Emendas Parlamentares Recebidas do Estado de Rondônia", com duas abas: **Outras Emendas Estaduais** e **Transferências Especiais**. Fonte declarada: COGES-RO. "Última atualização: 25/03/2026" na tela (mas 2026 já tem dados de execução).
- Endpoints internos usados pela página (POST, com cookie + `__RequestVerificationToken` do formulário):
  - `POST /Emenda/Filtrar` (DataTables server-side: `draw, start, length` + filtros `Exercicio, MesInicial, MesFinal, CodDocumento, NomeFonteDetalhada, TipoEmenda, Descricao`) → JSON.
  - `POST /Emenda/FiltrarEspeciais` → idem, só transferências especiais.
  - `POST /Emenda/GerarArquivo` com `ContentTypeFile=1` (CSV) ou `2` (XLSX) → **arquivo único com todos os anos (2023–2026) e as duas abas juntas** (5.007 linhas, 4,4 MB; o filtro de ano não foi aplicado na exportação).
- Anos: 2023, 2024, 2025, 2026.
- `dados.ro.gov.br` (CKAN) devolve "Internal Server Error" em tudo, inclusive `/api/3/action/package_search`. `ale.ro.leg.br` não resolve DNS (o site da Assembleia é `al.ro.leg.br`/`transparencia.al.ro.leg.br`; não olhei a fundo).

#### Campos (cabeçalho do CSV)
`Exercicio, Data_emissao, Nome_unidade, Unidade, Cod_documento, Nome_fonte_detalhada, Descricao, Empenhado, Liquidado, Pago, Empenhar, Maior_empenhar, Codigo_funcao, Descricao_funcao, Nome_fonte, Cod_fonte_detalhada, Cod_documento_pe, Cod_natureza, Instrumento, Cod_emenda, Domicilio_bancario, ProcessoAdministrativo, FaseTransferencia, LocalidadeBeneficiada, CronogramaExecucao, ExecucaoFisica, OrigemRecurso, TipoEmenda, FormaRepasse, Beneficiario`

- Cada linha é um **empenho/pré-empenho** (NE/PE), não uma emenda. O parlamentar vem da fonte de recurso detalhada (`Cod_fonte_detalhada` 070NN = deputado NN).
- Deputado: `Nome_fonte_detalhada` (nome curto/de urna: "Alex Redano", "Marcelo Cruz", "Ieda Pacheco Chaves"…), 24 deputados.
- Cidade: `LocalidadeBeneficiada` = "Município - RO" (texto) — mas ~46% das linhas vêm como "Estado de Rondônia" (não identificado). Sem IBGE. Parece extraído automaticamente do histórico.
- Beneficiário: `Beneficiario` = texto extraído do histórico (ex.: "A PREFEITURA DE PIMENTA BUENO", "MUNICÍPIO DE ALTO PARAÍSO (CNPJ: …)"); ~45% "Não informado (verificar descrição)". O texto bruto completo está em `Descricao`. `Domicilio_bancario` aparece igual em quase tudo (conta do Estado?).
- `TipoEmenda`: só "Individual" (apesar do filtro oferecer Bancada/Comissão). `FormaRepasse`: Fundo a Fundo / Outros (3.145), Convênio (1.088), Termo de Fomento (702), Transferência Especial (70), Termo de Colaboração (2).
- `FaseTransferencia`: quase tudo "Proposta".

#### Valores
- `Maior_empenhar` (rótulo "Valor previsto" na tela) — é o único valor preenchido para 2023–2025.
- `Empenhado`, `Liquidado`, `Pago`: **zerados em 2023, 2024 e 2025** (2024 tem R$ 1.424 empenhado no total). Só 2026 tem execução (empenhado R$ 14,0 mi, liquidado R$ 13,0 mi, pago R$ 10,4 mi). Ou seja: para anos fechados o portal não mostra quanto foi pago — ponto fraco.

| Ano | Linhas (CSV, inclui especiais) | Soma "valor previsto" |
|---|---|---|
| 2023 | 1.161 | R$ 224,1 mi |
| 2024 | 1.565 | R$ 384,2 mi |
| 2025 | 1.942 | R$ 515,7 mi |
| 2026 | 339 | R$ 137,5 mi |

Na API, 2025 = 1.905 linhas "outras emendas" (R$ 488,9 mi) + 37 transferências especiais (R$ 26,8 mi). 2024 = 1.555 + 10 (R$ 5,8 mi).
Atenção: pode haver dupla contagem PE × NE (pré-empenho e empenho do mesmo valor); não verifiquei.

#### Exemplos reais
- 2025 | Marcelo Cruz | São Miguel do Guaporé - RO | Fundo Municipal de Saúde (no texto; campo beneficiário "Não informado") | Repasse Fundo a Fundo - Saúde, aquisição de medicamentos | valor previsto R$ 4.000.000.
- 2025 | Claudia de Jesus | Alta Floresta - RO | Fundo Municipal de Saúde de Alta Floresta do Oeste (texto) | R$ 120.000.
- 2025 (transferência especial) | Pedro Fernandes | Rolim de Moura - RO | "Prefeitura Municipal de Rolim de Moura" | instrumento "Transf. Esp. aos Mun. Const. Estadual" | R$ 60.000.
- 2024 (transferência especial) | Laerte Gomes | Pimenta Bueno - RO | "A PREFEITURA DE PIMENTA BUENO" | aquisição de veículo utilitário | R$ 140.000.

#### Emenda Pix
**Sim.** Constituição de RO, art. 135-A (emendas individuais impositivas podem ir a municípios por "transferência especial" ou com finalidade definida); regulamentado por decreto (70% em despesa de capital; não integra a receita do município); TCE-RO Nota Técnica 01/2024 sobre o tema. No portal há aba própria "Transferências Especiais" (`/Emenda/FiltrarEspeciais`): 4 linhas em 2023, 10 em 2024, 37 em 2025 (R$ 26,8 mi), 19 em 2026.

#### Dificuldade: 2
Exportação CSV de tudo num POST só (precisa pegar cookie + token antiforgery da página). Dados sujos: cidade e beneficiário extraídos de texto livre, metade sem cidade, e execução (pago) zerada nos anos anteriores a 2026.

Arquivos: `baixados/RO/emendas_estaduais_todos_anos_GerarArquivo.csv`, `Filtrar_2024.json`, `Filtrar_2025.json`, `FiltrarEspeciais_2024.json`, `FiltrarEspeciais_2025.json`.

---

### RR — Roraima

**Status: Verificado** (baixei a planilha Google inteira em XLSX).

#### Onde está
- O Portal da Transparência do Executivo (`https://transparencia.rr.gov.br`, SPA com API `https://api.transparencia.rr.gov.br/api/v1/portal/menus`) não tem tela própria: o menu "Convênios e Emendas parlamentares - Despesas" → "Emendas Parlamentares Estaduais" leva para:
  - **Painel Seplan-RR (Streamlit)**: `https://emendas.seplan.net.br/` (páginas Geral, Detalhes, Instrumentos). Rodapé: "Elaborado por CGPRE/SEPLAN-RR; Dados fornecidos por SECONV-RR (Extraído do FIPLAN-RR)"; atualizado em 18/11/2026. Painel 2026: 397 emendas, valor total R$ 858,9 mi, empenhado R$ 633,2 mi, liquidado R$ 474,6 mi, pago R$ 441,1 mi.
  - Botão "Acessar Base de Dados" → **planilha Google pública** `https://docs.google.com/spreadsheets/d/18oIHhc-BPJ-YNLtT-TNwFlAxT7t4mZorfzXy5nbWkMU`; baixa direto com `/export?format=xlsx` (886 KB). Aba "DATA FECHAMENTO" = 23/11/2026.
  - Botão "Link Permanente para Arquivos da Base de Dados" → `https://dados-emendas.seconvrr.net.br/` — diretório com `emendas.csv/xlsx/ods/tsv/pdf`, `emendas_anteriores_a_2026.*` (CSV ~1 MB), `empenhos.*`, `liquidacoes.*`, `pagamentos.*`, `movimentacoes.*`, `processos.*`, `estornos.*`, `agencias.*`, `guias_credito_verba.*`. **Tem verificação anti-robô** ("Verificação de segurança", tipo proof-of-work): curl recebe 403 "Verificação necessária. Abra esta página no navegador." No navegador a verificação passou sozinha e mostrou a lista de arquivos, mas não baixei nada de lá (a planilha Google tem o mesmo conteúdo).
- ALE-RR: `https://transparencia.al.rr.leg.br/planejamento-e-prestacao-de-contas-intro/lei-orcamentaria-anual/emendas-parlamentares-ao-orcamento/` — só dois PDFs grandes ("Emendas Individuais" 44 MB, "Emendas de Comissão" 83 MB), provavelmente os textos das emendas à LOA. Descrito, não aberto.
- Seplan-RR tem documento "Emendas Parlamentares ao Orçamento do Estado de Roraima – Aspectos Normativos" (`https://seplan.rr.gov.br/wp-content/uploads/2024/03/Emendas-Parlamentares-ao-Orcamento-do-Estado-de-Roraima-Aspectos-Normativos.pdf`).

#### Campos (planilha Google)
Abas: `OPÇÕES`, `MAPA EMENDAS GERAL` (2023–2025, uma linha por empenho), `GERAL`, `EMENDAS` (2026: emenda, autoria, indicação, valor), `DESCRIÇÃO`, `PROCESSOS E AGÊNCIAS`, `EMPENHOS`, `MOVIMENTAÇÕES` (2026: versões da emenda com destino, região, natureza, funcional, valor, objeto), `LIQUIDAÇÕES`, `PAGAMENTOS` (tem coluna CPF/CNPJ do credor — pode conter pessoa física; não copiei), `DATA FECHAMENTO`.

Cabeçalho de `MAPA EMENDAS GERAL`:
`EMENDA, EXERCÍCIO, AUTORIA, TIPO, INDICAÇÃO, VALOR DA EMENDA, DESTINO, REGIÃO DE PLANEJAMENTO, NATUREZA DE DESPESA, EMPENHO, DATA EMISSÃO, VALOR EMPENHADO, DOTAÇÃO ORÇAMENTÁRIA, VALOR LIQUIDADO, VALOR PAGO, VALOR A PAGAR, PROCESSO SEI ORIGINAL, PROCESSO SEI TCE/RR, TIPO DE INSTRUMENTO, AGÊNCIA, CONTA CORRENTE, OBJETO DA EMENDA, HISTÓRICO DO EMPENHO`

- Deputado: `INDICAÇÃO` (nome, ex.: "Ângela Águida Portella", "Chico Mozart", "Catarina Guerra"; também comissões, ex.: "Comissão de Orçamento, Fiscalização Financeira, Tributação e Controle"). 36 nomes distintos.
- `AUTORIA`: Individual / Coletiva. `TIPO`: Impositiva / Não Impositiva / Impositiva Transferência Especial.
- Cidade: `REGIÃO DE PLANEJAMENTO` = nome do município (15 municípios de RR) ou "Roraima" (~72% das linhas = estadual/sem município). Sem IBGE, mas são só 15 nomes, fácil de casar.
- Beneficiário: `DESTINO` = órgão estadual (SEINF, SESAU, SECULT, SEED, DETRAN, UERR, ADERR…; "OE" = operações especiais, usado nas transferências a municípios). Entidade final (associação, instituto, com CNPJ) aparece só no texto do `OBJETO DA EMENDA`.
- Objeto: `OBJETO DA EMENDA` + `HISTÓRICO DO EMPENHO`.

#### Valores
Valor da emenda, empenhado, liquidado, pago, a pagar (todos numéricos).

| Ano | Linhas | Emendas distintas | Valor | Empenhado | Pago |
|---|---|---|---|---|---|
| 2023 | 342 | 178 | R$ 234,9 mi | R$ 197,9 mi | R$ 197,9 mi |
| 2024 | 499 | 241 | R$ 390,2 mi | R$ 340,8 mi | R$ 339,3 mi |
| 2025 | 992 | 341 | R$ 684,9 mi | R$ 576,7 mi | R$ 554,2 mi |
| 2026 (painel) | — | 397 | R$ 858,9 mi | R$ 633,2 mi | R$ 441,1 mi |

Obs.: no MAPA GERAL o "valor da emenda" parece vir rateado por empenho (a emenda nº 1/2023 aparece em 3 linhas com valores iguais aos empenhos). Os totais incluem emendas coletivas e não impositivas (só ~1/3 das linhas é "Individual").

#### Exemplos reais
- 2023 | emenda 14 | Catarina Guerra | Iracema | OE (transferência especial) | "Construção de calçadas na Sede do município de Iracema" | R$ 1.551.617, pago R$ 1.551.617.
- 2023 | emenda 1 | Ângela Águida Portella | Roraima (estadual) | ADERR | aquisição de veículo para a Agência de Defesa Agropecuária | R$ 106.970 empenhado e pago.
- 2025 | emenda 47 | Dr. Cláudio Cirurgião | Mucajaí | SESAU | ampliação do posto de saúde Pirilândia | R$ 10.433,28, nada empenhado.
- 2025 | emenda 162 | Comissão de Orçamento (coletiva) | Cantá | SEINF | manutenção de vicinais, Lote V | R$ 1.000.000 pago.

#### Emenda Pix
**Sim.** Constituição de RR, art. 113-A (EC 71/2020): emendas individuais impositivas podem ir a município por "transferência especial" ou com finalidade definida; regulamento Decreto 31.620-E/2022. Nos dados: TIPO = "Impositiva Transferência Especial" — 20 linhas/R$ 20,4 mi em 2023, 68/R$ 54,2 mi em 2024, 59/R$ 55,4 mi em 2025. Há também acordo TCE-RR + Governo + ALE sobre transparência das "emendas Pix" (prazo out/2026).

#### Dificuldade: 2
Planilha Google pública baixa inteira num GET (`/export?format=xlsx`), com município por nome. Cuidados: formato de 2026 está em abas separadas (EMENDAS + MOVIMENTAÇÕES + EMPENHOS…) diferente de 2023–2025 (MAPA EMENDAS GERAL); o diretório "permanente" de arquivos tem verificação anti-robô; a planilha é editável por quem mantém, pode mudar de forma sem aviso.

Arquivos: `baixados/RR/base_gsheet.xlsx`, `baixados/RR/menus.json`.


---

### DF — Distrito Federal

**Status: Verificado** (abri e baixei os dados de 2016, 2024 e 2025 pela API).

#### Onde está
- Tela: https://www.transparencia.df.gov.br/#/despesas/emendas-parlamentares (Portal da Transparência do DF, aplicação Angular).
- Dados: a própria página chama uma API JSON em `https://www.transparencia.df.gov.br/api/...`. A API exige um cabeçalho `x-client-id`. **Não é segredo**: o JavaScript do portal (`scripts/app.min.js`) gera um UUID aleatório e manda nesse cabeçalho. Fiz o mesmo (um UUID qualquer gerado com `uuidgen`).
- Endpoints (todos GET, com cabeçalho `x-client-id: <uuid>`):
  - `/api/despesa/emendas-parlamentares/anos` → `[2026,2025,...,2016]`
  - `/api/despesa/emendas-parlamentares?anoExercicio=2025&page=0&size=500` → JSON paginado (`content`, `totalElements`, `totalPages`, `last`). O servidor parece limitar a página em uns 150 itens; 2025 veio em 5 páginas.
  - `/api/despesa/emendas-parlamentares/filtros?exercicio=2025` (listas de autores, órgãos etc.)
  - `/api/despesa/emendas-parlamentares/nota-empenho?codigoFuncao=..&codigoSubfuncao=..&codigoPrograma=..&codigoProjeto=..&codigoSubtitulo=..&codigoNatureza=..&codigoFonteRecurso=..&codigoEsfera=..&codigoUnidadeOrcamentaria=..&codigoUnidadeGestora=..&codigoGestao=..&anoNotaEmpenho=2025&page=0&size=..` → notas de empenho daquela linha, **com credor**.
  - Existem também `/nota-lancamento` (liquidação) e `/ordem-bancaria` (pagamento) para emendas, e `/api/despesa/execucao-emendas/{ano}/{UG}`.
  - Exportação CSV (`/api/despesa/relatorio/emendas-parlamentares?tipo=csv&...`) deu erro 500 ("Objeto nulo") sem o parâmetro `colunas` montado como a tela monta. Não insisti, o JSON resolve.
- dados.df.gov.br não é mais CKAN (virou Liferay, `/api/3/action/package_search` → 404). Não achei conjunto de emendas lá.
- Existe também o SISCONEP (Sistema de Controle de Emendas Parlamentares, da Secretaria de Governo do DF) citado pelo TCDF como fonte de "valores, locais beneficiados e autor". Não abri.

#### Campos (linha da consulta principal, uma linha por autor × programa de trabalho × natureza × fonte)
`codigoUnidadeGestora, codigoGestao, codigoGrupoNatureza, codigoFonte, codigoEsfera, codigoUnidadeOrcamentaria, possuiDetalhamento, nomeTipoEmenda, nomePrograma, nomeUnidadeGestora, dotacaoInicial, valorDespesaAutorizadaEmendas, valorEmpenhadoEmendas, valorLiquidadoEmendas, valorEmpenhoPago, nomeGestao, nomeModalidade, nomeFuncao, nomeSubfuncao, nomeAcao, nomeCategoria, nomeGrupo, nomeElemento, nomeFonte, codigoFuncao, codigoSubfuncao, codigoPrograma, codigoProjeto, codigoSubtitulo, anoExercicio, nomeProgramaTrabalho, nomeAutor, nomeSubtitulo, alteracao, bloqueado, movimentacao`

- **Deputado**: `nomeAutor` (nome parlamentar, ex.: "MAX MACIEL"). 28 autores em 2025.
- **Lugar (RA)**: não há coluna. A região administrativa aparece às vezes no texto do subtítulo/programa de trabalho (ex.: "... REGIÃO ADMINISTRATIVA DE SÃO SEBASTIÃO (RA-XIV)", "... - BRAZLÂNDIA") ou no órgão ("ADMINISTRAÇÃO REGIONAL DO PARK WAY"). Em 2025: 53 de 656 linhas citam uma RA no texto; 425 dizem só "DISTRITO FEDERAL"; 178 sem local. Ou seja, mapear por RA é parcial.
- **Beneficiário**: não está na linha principal (só o órgão executor e a modalidade, ex.: "TRANSFERÊNCIAS A INST PRIVADAS SEM FINS LUCRATIVOS"). Fica nas notas de empenho (`codigoCredor` = CNPJ/CPF, `nomeCredor`, `valorNeFinal`, `dataEmissao`, `numeroNotaEmpenho`, `numeroProcesso`). Existem credores pessoa física (não anotei documentos). Atenção: o filtro da nota de empenho é por programa de trabalho/UG/natureza/fonte, não por autor; quando dois deputados usam o mesmo programa de trabalho, as notas se misturam. Muitos subtítulos têm as iniciais do deputado (ex.: "PDAF NAS ESCOLAS - GM", "... PP NO DISTRITO FEDERAL"), o que ajuda a separar.
- **Objeto**: `nomeProgramaTrabalho` / `nomeSubtitulo` / `nomeAcao` (texto do orçamento).
- **Tipo**: `nomeTipoEmenda` ("Emenda Parlamentar Individual - EPI", "Emendas à Execução - EPE"; em 2016 também "Emendas Parlamentares - EP").

#### Valores
Aprovado (`dotacaoInicial`), alteração, movimentação, bloqueado, autorizado (`valorDespesaAutorizadaEmendas`), empenhado, liquidado, pago (`valorEmpenhoPago`). O "pago" parece incluir restos a pagar de anos anteriores: há linhas com empenhado 0 e pago 1.000.000 (ex.: MARTINS MACHADO, PDPAS, 2025). Cuidado ao somar.

#### Emenda Pix
Não se aplica do jeito estadual: o DF não tem municípios. Na Lei Orgânica (art. 150, §§ 15–17, segundo apresentação do SISCONEP) as emendas individuais são impositivas até 2% da RCL. Não achei "transferência especial" para o DF; não consegui abrir o texto da LOA 2025 (certificado TLS inválido no site do TCDF).

#### Exemplos reais (2025)
- DAYSE AMARILIO | programa 14.422.6211.9107.0448 "APOIO A PROJETOS DE JUSTIÇA E CIDADANIA" | Secretaria de Justiça e Cidadania | aprovado R$ 12.850.000, empenhado R$ 11.691.435, pago R$ 11.254.378,44. Notas de empenho: 13, ex.: 2025NE01035, credor FUNDAÇÃO PROCURADOR PEDRO JORGE DE MELO E SILVA, R$ 300.000.
- GABRIEL MAGNO | "PDAF NAS ESCOLAS - GM" | Secretaria de Educação | R$ 10.879.000 aprovado = empenhado = pago. 236 notas de empenho para caixas escolares (ex.: "CAIXA ESCOLAR DO CENTRO DE ENSINO DE 1º GRAU 20 DE...", R$ 100.000).
- JAQUELINE SILVA | "REFORMA DA FEIRA PERMANENTE DA REGIÃO ADM. DE SANTA MARIA - RA XIII - JS" | NOVACAP | aprovado R$ 500.000, empenhado R$ 500.000, pago R$ 255.509,48.

#### Totais
| Ano | Linhas | Aprovado | Empenhado | Pago |
|---|---|---|---|---|
| 2025 | 656 | R$ 593.520.987,16 | R$ 547.729.883,25 | R$ 538.864.548,24 |
| 2024 | 702 | R$ 603.669.995,00 | R$ 540.108.897,09 | R$ 535.307.692,83 |
| 2016 | 1.031 | R$ 365.399.000,00 | 0 (!) | R$ 76.437.123,78 |

Nos anos antigos (pelo menos 2016) os campos empenhado/liquidado vêm zerados, então a série boa começa em algum ano entre 2017 e 2024 (não testei todos).

#### Dificuldade: 2
API JSON limpa, paginada, sem captcha; só precisa do cabeçalho `x-client-id` com um UUID qualquer. Beneficiário exige uma chamada extra por linha (656 chamadas por ano). RA é texto livre e quase sempre ausente.

---

### TO — Tocantins

**Status: Verificado** (painel da Assembleia, CSV baixado). Painel do Executivo: **bloqueado** (403).

#### Onde está
1. **Assembleia Legislativa (Aleto)**: página de transparência https://www.al.to.leg.br/transparencia → link "Emendas Parlamentares – Acompanhamento das emendas impositivas" → painel Shiny https://aletocantins.shinyapps.io/emendasimpositivas/ (lançado em dez/2025, segundo o Conexão Tocantins).
   - Abas: Capa, Início (filtros: Parlamentar, Órgão (UG), Situação, Categoria, Ano, Mês do pagamento; cartões; gráficos; "Base de Indicações", "Base de Pagamentos (com 'parlamentar' via CHAVE)", diagnóstico de cruzamento), "Indicações + Pagamentos".
   - Na aba "Indicações + Pagamentos" há o botão **"Baixar CSV (Indicações + Total Pago)"**. O link é por sessão do Shiny (`.../_w_<id>/session/<id>/download/down_ind_rel?w=<id>`), então para baixar em lote é preciso abrir o painel num navegador (ou falar o protocolo do Shiny) e pegar o link da sessão. Com o link em mãos, `curl` baixa direto (testei).
   - As tabelas "Base de Indicações" e "Base de Pagamentos" (que teriam situação, empenho, ordem bancária) não renderizaram para mim na aba Início; não consegui ver as colunas delas.
2. **Executivo**: https://transparencia.to.gov.br/PortalTransparencia/ (Vaadin) → "Emendas Parlamentares" → "Emendas Parlamentares - Estaduais" abre um painel em `https://dados.lab63.to.gov.br/pagina/painel.xhtml?painel_uuid=01b6e491-b707-4e77-ac29-22585a745552`, que respondeu **403 Forbidden** (openresty) para mim. Pode ser bloqueio geográfico; não tentei contornar. `dados.to.gov.br` não resolve no DNS. O certificado de `www.transparencia.to.gov.br` não bate com o nome; `sapl.al.to.leg.br` entrega um certificado de firewall Fortinet (não abri).

#### Campos do CSV (`indicacoes_total_pago.csv`)
`Emenda, parlamentar, orgao, proponente, objeto, valor_destinado, total_pago, n_pagamentos`
- **Deputado**: `parlamentar` (24 deputados).
- **Cidade**: não há coluna nem código IBGE. Dá para tirar o nome do município do `proponente` quando é prefeitura ou fundo municipal ("PREFEITURA MUNICIPAL DE PORTO NACIONAL", "FUNDO MUNICIPAL DE SAUDE DE ANANÁS"): 832 linhas com "PREFEITURA" e 284 com "FUNDO MUNICIPAL", de 1.465. Para entidades (institutos, associações) só às vezes o objeto cita a cidade. Nomes sem acento padronizado ("NAZARE", "ANANAS").
- **Beneficiário**: `proponente` (prefeitura, fundo municipal, entidade privada, ou a própria secretaria estadual quando ela executa).
- **Objeto**: `objeto` (texto livre).
- **Órgão**: `orgao` (828 linhas no "FUNDO DE RECURSOS DE EMENDA PARLAMENTAR INDIVIDUAL"; depois Saúde 303, Turismo 168, Esportes 58).
- `Emenda` é um número tipo `010405.00158/2026` (os 6 primeiros dígitos parecem identificar o deputado).

#### Valores
- No CSV: `valor_destinado` (indicado) e `total_pago` (soma das ordens bancárias ligadas à emenda), `n_pagamentos`.
- No painel (cartões, filtro padrão 2025–2026): 1.465 indicações, destinado R$ 259.246.586, **empenhado R$ 204.308.349**, pago R$ 184.112.193. O empenhado não vem no CSV por emenda.
- O próprio painel avisa que o cruzamento pagamento × indicação é feito por texto ("extraídas de observacao com fallback em indicacao_2") e lista pagamentos sem emenda reconhecida. Há casos de pago > destinado (ex.: EDUARDO FORTES, van para São Valério: destinado R$ 275.000, pago R$ 550.000).

#### Emenda Pix
Na prática, sim: 294 indicações têm "TRANSFERÊNCIA ESPECIAL" no objeto, somando R$ 52.007.733 destinados, quase todas para prefeituras via "Fundo de Recursos de Emenda Parlamentar Individual" (Lei estadual 3.585/2019 criou o fundo; repasse como "cota parlamentar" na fonte 0104, segundo notícias). Não consegui abrir a Constituição estadual/EC 59/2025 para confirmar a base legal da "transferência especial" (certificado TLS inválido no SAPL). Status desse item: **Descrito** (visto nos dados, base legal não verificada).

#### Exemplos reais (CSV, emendas /2026)
- CLEITON CARDOSO | Fundo de Recursos de Emenda Parlamentar Individual | PREFEITURA MUNICIPAL DE PORTO NACIONAL | fomento à cultura e turismo | destinado R$ 1.500.000, pago R$ 1.500.000.
- IVORY DE LIRA | Fundo de Recursos de Emenda Parlamentar Individual | PREFEITURA MUNICIPAL DE ANANAS | "TRANSFERÊNCIA ESPECIAL: destinada ao custeio das atividades administrativas..." | R$ 800.000 / pago R$ 800.000.
- NILTON FRANCO | Secretaria do Turismo | INSTITUTO CENTRUS | temporada de praia 2026 de Lagoa da Confusão | R$ 1.000.000 / pago R$ 1.000.000.

#### Totais
1.465 linhas (todas com número /2026), destinado R$ 259.246.586, pago R$ 183.366.700 (soma do CSV; o cartão do painel diz R$ 184.112.193, diferença de pagamentos sem emenda reconhecida). Pagamentos de abr a out/2026 no gráfico mensal. Não achei 2025 nem anos anteriores no painel, apesar do filtro de ano começar em 2025.

#### Dificuldade: 3
Dados bons (deputado + beneficiário + objeto + destinado + pago), mas só por painel Shiny com link de download por sessão; sem API estável, sem código IBGE, um ano só. O painel do Executivo deu 403.

---

### AP — Amapá

**Status: Verificado** (baixei os CSVs de 2021 a 2024).

#### Onde está
- Portal da Transparência do Executivo: https://www.transparencia.ap.gov.br/consulta_estatica/6/528/outras-informações/emendas-parlamentares-estaduais (no menu: Outras Informações → Emendas Parlamentares → Estaduais). Página diz "Atualização: 11/2026" e lista só **2021, 2022, 2023 e 2024**, cada um com link para uma pasta pública do SIGDOC:
  - 2021: https://sigdoc.ap.gov.br/public/verPasta.jsf?token=5bf254054e5d48ddb49ba246e2bf3119
  - 2022: https://sigdoc.ap.gov.br/public/verPasta.jsf?token=1c085e7e71b95b833bf0dc11e08208b1
  - 2023: https://sigdoc.ap.gov.br/public/verPasta.jsf?token=d077793c7fd0a9d3ef16f054d8e44cc1
  - 2024: https://sigdoc.ap.gov.br/public/verPasta.jsf?token=89a174f18b2710fdbc3bf0094dec93aa
- Cada pasta tem "Emendas Estaduais - Portal da Transparência - <ano>" em .csv, .pdf e .xlsx. O link de download direto é `https://sigdoc.ap.gov.br/public/arquivo/<uuid>/download`, achado dentro da página `verArquivo.jsf?token=..&tid=..`. Os que usei:
  - 2021 CSV: https://sigdoc.ap.gov.br/public/arquivo/4f131616-8515-4584-864d-f2887390807b/download
  - 2022 CSV: https://sigdoc.ap.gov.br/public/arquivo/2c1dec29-40a6-48e8-b735-711654dc804a/download
  - 2023 CSV: https://sigdoc.ap.gov.br/public/arquivo/07fb8f48-a188-4e18-b568-afceb1dfa44d/download
  - 2024 CSV: https://sigdoc.ap.gov.br/public/arquivo/d092c30b-c6a5-4cd5-ae7a-94ea2d0f6d0a/download
- Produzido pela "Coordenadoria de Ações Estratégicas / Observatório da Despesa Pública".
- Problema técnico: os servidores `www.transparencia.ap.gov.br` e `sigdoc.ap.gov.br` não mandam o certificado intermediário (Sectigo DV R36). Resolvi baixando o intermediário pelo endereço oficial do próprio certificado (http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt) e passando com `--cacert`; sem isso, `curl` falha.
- Assembleia (https://www.al.ap.leg.br/transparencia/): não tem seção de emendas parlamentares (só CEAP, despesas, convênios etc.). `dados.ap.gov.br` e `seplan.ap.gov.br` não responderam.

#### Campos (CSV `;`, Latin-1, 7 linhas de cabeçalho antes da tabela, números no formato 1.234,56)
`Ano; Unidade Gestora; Emenda; Objeto; Autor Emenda; Função; Sub-função; Valor Previsto; Dotação Atualizada; Despesas Empenhadas; Despesas Liquidadas; Despesas do Exercício Pagas; Restos a Pagar`
- **Deputado**: `Autor Emenda` (ex.: "Aldilene Souza", "Jack Jk"; às vezes com espaço sobrando no fim). 23–31 autores por ano.
- **Cidade**: não há coluna. O município aparece no `Objeto` em cerca de metade das linhas (2024: 162 de 310), ex.: "...FUNDO MUNICIPAL DE SAÚDE DE SERRA DO NAVIO...".
- **Beneficiário**: não há coluna. `Unidade Gestora` é sempre o órgão estadual executor (Fundo Estadual de Saúde, Secretaria de Cultura etc.); nenhuma UG é prefeitura. Às vezes o objeto cita a entidade (e até CNPJ).
- **Objeto**: `Objeto` (texto, começa pelo código da emenda, ex.: "I0336 - TRANSFERÊNCIA AO FUNDO MUNICIPAL DE SAÚDE DE SERRA DO NAVIO...").
- Várias linhas por emenda (uma por empenho/execução); o `Valor Previsto` aparece numa linha e as outras vêm com 0,00.

#### Valores
Previsto, dotação atualizada, empenhado, liquidado, pago no exercício, restos a pagar. Em 2021–2023 a coluna "Restos a Pagar" é idêntica a "Pagas", o que parece erro de montagem da planilha. Em 2021 o "Valor Previsto" está todo zerado.

#### Emenda Pix
Não encontrado. Nenhum objeto cita "transferência especial"; transferências a municípios passam por fundos estaduais (ex.: Fundo Estadual de Saúde → fundo municipal). Não achei emenda à Constituição do Amapá criando essa modalidade (busca na web sem resultado; não li a Constituição inteira).

#### Exemplos reais
- 2024 | Diogo Senior | 300301 - FUNDO ESTADUAL DE SAÚDE | I0336 - "TRANSFERÊNCIA AO FUNDO MUNICIPAL DE SAÚDE DE SERRA DO NAVIO, PARA AQUISIÇÃO DE EQUIPAMENTOS E INSUMOS..." | empenhado 0,00 (nessa linha).
- 2022 | Jory Oeiras | 380101 - SECRETARIA DE ESTADO DA CULTURA | I0092 - "FOMENTO DA CADEIRA CULTURAL NO MUNICIPIO DE SANTANA" | empenhado R$ 100.000, pago R$ 100.000.
- 2024 | Aldilene Souza | 130203 - ESCOLA DE ADMINISTRAÇÃO PÚBLICA DO AMAPÁ | I0033 - custeio de estágio remunerado | empenhado R$ 177.027,33, pago R$ 177.027,33.

#### Totais
| Ano | Linhas | Emendas distintas | Previsto | Dotação atualizada | Empenhado | Pago no exercício |
|---|---|---|---|---|---|---|
| 2021 | 157 | 78 | 0 (vazio) | R$ 11.258.790 | R$ 10.155.144,85 | R$ 5.700.547,00 |
| 2022 | 425 | 231 | R$ 35.049.335 | R$ 29.783.621 | R$ 28.533.516,13 | R$ 10.343.622,61 |
| 2023 | 289 | 187 | R$ 48.355.920 | R$ 33.501.042 | R$ 32.651.073,12 | R$ 22.072.513,21 |
| 2024 | 310 | 245 | R$ 70.333.745 | R$ 70.333.745 | R$ 21.753.595,68 | R$ 8.913.912,68 |

#### Dificuldade: 2
Um CSV por ano com link direto (depois de achar o UUID na página do SIGDOC); precisa contornar a falta do certificado intermediário (de forma legítima). Mas faltam 2025 e 2026, não há beneficiário nem município em coluna, e a planilha tem colunas suspeitas.


---

## Emendas parlamentares estaduais — Nordeste (PI, BA, PE, CE, MA, RN, PB, AL, SE)


Legenda de status: **Verificado** = abri e contei os dados; **Descrito** = só vi a página; **Não encontrado**.

Cuidado geral: em vários estados existe uma página ou um arquivo de "transferências especiais" ou "emenda Pix" que trata das emendas **federais** (deputado federal ou senador) que o **governo do estado** recebe. Isso não é emenda estadual. Isso vale para BA, PE, RN, PB e AL (detalhes em cada seção).

---

### PI — Piauí — Verificado (dificuldade 1)

**Fonte:** API oficial da CGE-PI, sem chave. OpenAPI em `https://api.transparencia.pi.gov.br/schema/` (YAML) e `?format=json`; Swagger em `https://api.transparencia.pi.gov.br/docs/`.

São duas bases, com formatos diferentes.

#### A) 2026 em diante (fonte: SIGRP, o sistema de repasses; nível de indicação)
- Anos: `GET /api/v1/emendas-estaduais/exercicios/` → `[2028, 2026]`. O ano de 2028 tem 1 linha de teste.
- Lista: `GET /api/v1/emendas-estaduais/2026/?page=N`, paginada no estilo DRF (`count`, `next`, `previous`, `results`). Hoje são 1.443 registros (a pista dizia 1.438; a base cresceu).
- CSV direto (todas as linhas): `https://api.transparencia.pi.gov.br/api/v1/emendas-estaduais/2026/download/?filetype=csv` (ou `xlsx`). O arquivo tem 472 KB, vem em UTF-8 com BOM e usa `;` como separador.
- Colunas do CSV: `Valor da Emenda (R$);Status;Número da Emenda;Parlamentar;Partido do Parlamentar;Modalidade da Emenda;Beneficiário;Localidade Beneficiada;Objetivo;Modalidade`
- Detalhe de cada emenda: `GET /api/v1/emendas-estaduais/{id}/detalhamento/`. Traz processo SEI, `emenda_valor_disponivel`, ação orçamentária, função, `objeto_despesa`, justificativa, plano de trabalho, uma lista `execucao` (repasses com valor), `credores` e `celebracoes` (termos de fomento), entre outros campos. Esse detalhe também traz o nome do servidor que lançou o registro; não precisamos dele.
- Metadados: `/modalidades/` → Convênios (Municípios), Execução Direta, Fundo a Fundo (Município), Modalidade a definir, Parceria (OSC), **Transferência Especial (Município)**. `/status/` → Aprovada, Atualizada, Cancelada, Pendente de análise.
- Números de 2026: 1.443 linhas somando **R$ 371,65 mi** (todas as situações juntas: 878 aprovadas, 527 canceladas, 37 pendentes); 30 parlamentares.
  - Por modalidade: Execução Direta 791, Modalidade a definir 376, Parceria (OSC) 124, **Transferência Especial (Município) 102, que somam R$ 25,31 mi**, Fundo a Fundo 49, Convênio 1.
- Cidade: só **texto livre**, em 844 grafias diferentes ("TERESINA", "Teresina", "TERESINA-PI", "Município de Teresina", "MUNICÍPIO DE ALTO LONGÁ - PI E REGIÕES ADJACENTES", "Estado do Piauí"…). Não há código IBGE; vai precisar de normalização.
- Valores: só o **valor indicado** (`emenda_valor`) e o `emenda_valor_disponivel`. O empenhado e o pago não aparecem na lista; ficam espalhados no detalhe (`execucao`).
- Exemplos:
  - WILSON BRANDÃO (PP) | SÃO FELIX DO PIAUÍ | ENCARGOS GERAIS DO ESTADO | R$ 90.000 | Transferência Especial (Município)
  - WILSON BRANDÃO (PP) | FRANCISCO AYRES | ENCARGOS GERAIS DO ESTADO | R$ 100.000 | Transferência Especial (Município)
  - WILSON BRANDÃO (PP) | "MUNICÍPIO DE ALTO LONGÁ - PI E REGIÕES ADJACENTES" | CENDFOL (coordenadoria estadual) | R$ 300.000 | Parceria (OSC): vaquejada

#### B) 2021 a 2025 (fonte: SEFAZ-PI; nível de nota de empenho)
- Anos: `GET /api/v1/emendas-estaduais/2025-e-anteriores/exercicios/` → 2021 a 2025.
- CSV: `https://api.transparencia.pi.gov.br/api/v1/emendas-estaduais/2025-e-anteriores/download/{ano}/?filetype=csv`
- Colunas: `Exercício;Autor da Emenda;Unidade Gestora;Função;Subfunção;Ação;Nota de Empenho;Credor;Tipo de Licitação;Descrição;Valor Empenhado (R$);Valor Liquidado (R$);Valor Pago (R$)`
- O autor vem como "27 - Fábio Novo" (código e nome). O credor vem como "CNPJ - nome". Não achei credor com 11 dígitos (CPF).
- Cidade: não há campo próprio. Ela aparece no nome do credor ("MUNICÍPIO DE BATALHA", "FUNDO MUNICIPAL DE SAÚDE DE PARNAGUÁ") ou na descrição. Pelo CNPJ da prefeitura dá para ligar ao código IBGE.
- Linhas e somas por ano:

| ano | linhas | empenhado | pago |
|---|---|---|---|
| 2021 | 417 | R$ 49,0 mi | R$ 41,6 mi |
| 2022 | 546 | R$ 66,9 mi | R$ 65,9 mi |
| 2023 | 652 | R$ 74,3 mi | R$ 72,1 mi |
| 2024 | 773 | R$ 122,0 mi | R$ 120,7 mi |
| 2025 | 883 | R$ 152,7 mi | R$ 141,1 mi |

- **Emenda Pix estadual:** existe desde 2024, na ação `0918 - TRANSFERÊNCIAS ESPECIAIS` da UG `240101 - ENCARGOS GERAIS DO ESTADO`. A descrição diz "EMENDA IMPOSITIVA NA MODALIDADE TRANSFERÊNCIA ESPECIAL… AUTORIA DO DEPUTADO X". Em 2024 foram 244 empenhos, R$ 33,3 mi pagos; em 2025, 236 empenhos, R$ 31,4 mi pagos. O objetivo da ação em 2026 cita a "EC 58/2021" (emenda à Constituição do PI).
- Exemplos de 2025: 44 - Henrique Pires | MUNICÍPIO DE BATALHA | R$ 50.000 pago (transferência especial); 27 - Fábio Novo | INSTITUTO PRESENTE | R$ 75.000 pago (educação).
- O que mais aparece como credor são produtoras de eventos e shows (K S L LIMITADA, ALIANZA PRODUCOES…).

---

### BA — Bahia — Verificado (dificuldade 2)

**Fonte:** CKAN `https://dados.ba.gov.br`.
- O certificado TLS do servidor vem com a cadeia incompleta: falta o intermediário "Sectigo Public Server Authentication CA OV R36". O curl falha com erro 60. Resolvi baixando o intermediário da própria Sectigo (`http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt`) e passando `--cacert` com o pacote do sistema mais esse intermediário. Não desliguei a verificação.
- A API também é lenta (cerca de 10 s por chamada).

#### A) Emendas Parlamentares Estaduais (deputados estaduais) — conjunto `emendas-parlamentares`
- ZIP: `https://dados.ba.gov.br/dataset/1436b3e7-6594-4683-bfa5-b2e3a6c69e07/resource/2d284f2e-79cc-4e3c-a45b-6fc903a6e2d0/download/emendasparlamentares.zip` (2,6 MB; atualizado em 23/11/2026; 14 MB depois de descompactar).
- Diagrama do relacionamento: `.../resource/f463ff7d-569c-4b48-b1d3-c80f017779df/download/emendas-parlamentares-relacionamento_views.png`
- O ZIP traz 5 CSVs, todos com `;` como separador, UTF-8 com BOM e decimal com vírgula:
  - `VW_PAINEL_EMENDAS_PARLAMENTARES_DESPESAS.csv` (5.709 linhas): `Ano Exercício;Órgão;sgl_orgao_orcamento;Unidade Orçamentária;nom_res_unidade_orcamentaria;Ação do Programa de Governo;cod_subfonte_recurso;Deputado;Nome do Deputado;num_codigo;Valor Orçado Inicial.;Valor Orçado Atual.;Valor Empenhado.;Valor Liquidado.;Valor Pago.`
  - `VW_PAINEL_EMENDAS_PARLAMENTARES_PAGAMENTOS.csv` (21.905 pagamentos): `num_pagto_nob;Nº do Pagamento Formatado;RazaoSocialCredorPagamento;Data do Pagamento;val_pagto_nob;Pagamento_Efetivado;val_GCV;Objeto;num_empenho;num_codigo_exec`. **Não traz CNPJ do credor**, só a razão social.
  - `..._CENTRALIZACAO_DESCENTRALIZACAO.csv` (liga `num_codigo` a `num_codigo_exec` e `num_codigo_liqu`), `..._LIQUIDACAO_ORCAMENTO.csv` (liquidações com data) e `VW_PROCESSO_SEI.csv` (empenho → processo SEI).
- Anos: 2017 a 2026. Há 59 a 63 deputados por ano (a ALBA tem 63).

| ano | linhas | orçado atual | empenhado | pago |
|---|---|---|---|---|
| 2017 | 249 | R$ 78,3 mi | R$ 26,4 mi | R$ 15,4 mi |
| 2020 | 542 | R$ 103,5 mi | R$ 74,0 mi | R$ 18,1 mi |
| 2023 | 547 | R$ 147,1 mi | R$ 122,7 mi | R$ 96,8 mi |
| 2024 | 846 | R$ 386,6 mi | R$ 369,9 mi | R$ 310,3 mi |
| 2025 | 922 | R$ 571,9 mi | R$ 542,2 mi | R$ 415,9 mi |
| 2026 | 955 | R$ 641,3 mi | R$ 365,1 mi | R$ 331,5 mi |

- Cidade: **não há campo de município**. A linha de despesa só tem órgão, ação e deputado. O município só aparece de forma indireta: no credor do pagamento (381 credores do tipo "MUNICIPIO DE X" ou "PREFEITURA MUNICIPAL DE X") ou no texto do `Objeto`. Grande parte é compra feita pelo próprio estado (ambulâncias, ônibus escolares) e entregue ao município, e nesse caso o credor é o fornecedor (MANUPA, RENAULT…).
- As ações mais comuns: Ampliação da Frota de Ambulância, Aparelhamento de Unidade Escolar, Aparelhamento de Unidade de Saúde, Oferta de Transporte Escolar Município.
- Exemplos de 2025 (despesa ligada ao pagamento):
  - Eduardo Salles | PREFEITURA MUNICIPAL DE MORRO DO CHAPEU | R$ 1.271,69 | Abastecimento de água com perfuração de poços
  - Júnior Nascimento | PREFEITURA MUNICIPAL DE CAMPO FORMOSO | R$ 17.500 | Apoio à Realização de Evento (show no São João)
- **Para ter o município com o valor indicado**: a SEPLAN publica PDFs anexos à LOA, por exemplo `https://www.ba.gov.br/seplan/sites/site-seplan/files/2026-01/LOA-2026-Anexo-III-Emendas-Parlamentares-Individuais-por-Municipio-Demonstrativo-Complementar.pdf` e `...LOA-2026-Anexo-I-Emendas-Parlamentares-Individuais-por-Autor-e-Area-Tematica...pdf` (há versões de 2025). Esses PDFs não foram abertos (Descrito).

#### B) "Transferências Especiais" — conjunto `transferencias-especiais` → **são emendas FEDERAIS**
- ZIP: `https://dados.ba.gov.br/dataset/f2ecd7fa-24ce-4be2-80d5-08e2c11e3e1c/resource/809f9b7d-c252-482d-9c92-f2169d48c29c/download/transferenciasespeciais.zip` (0,5 MB).
- O CSV `VW_PAINEL_TRANSFERENCIA_ESPECIAL_DESPESA.csv` traz as colunas `Ministério de Origem da Emenda`, `Número da Emenda Parlamentar` (no formato federal, por exemplo 91910004) e `Ano da Emenda`. Os autores são parlamentares federais (Jaques Wagner, Otto Alencar, Zé Neto, Waldenor Pereira, Alice Portugal…). A fonte é a 6xxxxx (recurso federal); nas emendas estaduais é a 5xxxxx.
- Ou seja, são as **emendas Pix federais recebidas pelo governo da Bahia**, não Pix estadual. Anos 2020 a 2026; em 2025 foram 286 linhas, R$ 256,6 mi orçados e R$ 73,2 mi pagos.
- Emenda Pix **estadual** na BA: **não encontrada**. Pela Lei 14.634/2023, as emendas impositivas destinadas a municípios são executadas **por convênio**.

---

### PE — Pernambuco — Verificado (dificuldade 1 para 2026; 2 para 2012–2025)

**Fonte:** CKAN `https://dados.pe.gov.br`, conjunto `emendasparlamentaresestaduais` (`https://dados.pe.gov.br/dataset/emendasparlamentaresestaduais`), atualizado todo dia (o último em 23/11/2026).

#### 2026: três "tabelas completas", uma por forma de execução
Base de todas as URLs: `https://dados.pe.gov.br/dataset/7c721673-6f32-467b-853f-297ec1399705/resource/`
- PIX (transferência especial): `2ad1df94-50cb-4612-ba1b-51c7e11377a2/download/tabela_completa_pix.csv`
- DIRETA (execução pelo próprio estado): `fbadd887-5110-406c-887a-2427c3cac8b1/download/tabela_completa_direta.csv`
- GTV (convênio ou parceria pelo sistema GTV): `8a102499-016e-4b02-8714-fcb2757cfe2f/download/tabela_completa_gtv.csv`
- Também há, para cada uma, os arquivos de notas de liquidação, ordens bancárias, anulações e reforços, além de um dicionário de dados (`f4e35cf3-.../dicionario_dados_emendas_parlamentares_ckan.json`).
- Colunas (separador `;`): `ano;dt_lancamento;autor;nome_ug;categoria;codigo_alepe;municipio;[acao;subacao;]grupo_despesa;modalidade_despesa;objeto;numero_empenho;nome_credor;modalidade_empenho;tipo_licitacao;observacao_empenho;pt;ug;ciclo_emenda;ato_normativo;fonte;beneficiario;tematica;resumo_objeto;tipo;sei;status_resolucao_tce;detalhamento_lc_573;classificacao_emenda;legislacao;condicao_saneamento_impedimento_tecnico;status_documental_fisico;valor_empenhado;valor_liquidado;valor_pago;valor_rp_pago;valor_dot_inicial;orcamento_atual;num_processo_licitacao[;link_prestacao_de_contas_transf_especiais]`
- O campo `autor` traz o deputado. O `municipio` vem como **nome em maiúsculas, sem acento** ("TORITAMA", "JABOATAO DOS GUARARAPES"); não há código IBGE. O `nome_credor` vem como "CNPJ - nome". A tabela PIX ainda traz o **link para a prestação de contas no portal do município**.

| tabela 2026 | linhas | autores | municípios | orçamento atual | empenhado | pago |
|---|---|---|---|---|---|---|
| PIX | 379 | 50 | 138 | R$ 116,0 mi | R$ 73,1 mi | R$ 28,4 mi |
| DIRETA | 283 | 41 | 37 | R$ 54,4 mi | R$ 23,7 mi | R$ 12,9 mi |
| GTV | 1.746 | 49 | 178 | R$ 262,2 mi | R$ 123,8 mi | R$ 80,7 mi |

- Exemplos:
  - Joel da Harpa | CARPINA | MUNICIPIO DE CARPINA | R$ 500.000 pago | transferência especial
  - Adalto Santos | TORITAMA | MUNICIPIO DE TORITAMA | R$ 1.000.000 empenhado e pago | transferência especial (viaturas da guarda municipal)
  - Adalto Santos | ARARIPINA | INSTITUTO SOCIAL DAS MEDIANEIRAS DA PAZ | R$ 100.000 pago | GTV, insumos hospitalares
- **Emenda Pix estadual: SIM.** A transferência especial é regulamentada por decreto desde 2025, e a Lei 19.073/2025 obriga a divulgação no portal.

#### 2012–2025 (arquivo anual, um CSV ou JSON por ano, nível de empenho)
- Exemplo: 2024 em `cd00b3dd-4437-46a7-955c-9f9b3c7003aa/download/emendas_parlamentares_2024_.csv`; 2025 só em JSON, `0d344e7d-8f65-4900-b67a-11942149ba9d/download/emendas_parlamentares_2025_.json`, que é um retrato de ago/2025 com 774 linhas e R$ 92,7 mi pagos.
- Colunas: `numero_empenho;unidade_gestora;credor;cd_nm_funcao;cd_nm_subfuncao;cd_nm_prog;cd_nm_acao;cd_nm_subacao;ds_modalidade_empenho;ds_tp_licitacao;obs;ds_tp_desp;cd_ds_fonte_recurso;cd_nm_categoria;cd_nm_grupo;cd_nm_modalidade;cd_nm_elemento;cd_nm_item_vlrliquidado;vlrempenhado;vlrliquidado;vlrtotalpago`
- **Não traz o autor.** Só aparece o número da emenda, na subação ("EH66 - EMENDA PARLAMENTAR NO.558/2019"). A cidade só aparece no nome do credor (CNPJ + "FUNDO MUNICIPAL DE SAUDE DE X"). Em 2024 foram 1.330 empenhos, R$ 182,4 mi empenhados e R$ 119,9 mi pagos.
- Para saber o autor desses anos seria preciso cruzar com a ALEPE (o `codigo_alepe` só existe em 2026).

Atenção: os conjuntos `emendas-especiais-pix-recebimento`, `emendas-especiais-pix-execucao` e `emendas-individuais-de-bancada` também estão no CKAN de PE, mas são **federais** (DANIEL COELHO, WOLNEY QUEIROZ… recebidos pelo estado).

---

### CE — Ceará — Descrito (dificuldade 5: bloqueio antirrobô)

- Página: `https://cearatransparente.ce.gov.br/portal-da-transparencia/despesas/emendas-parlamentares?locale=pt-BR` ("Emendas Parlamentares Estaduais", última atualização em 02/10/2026). Há também uma "base histórica" em `/portal-da-transparencia/paginas/emendas-parlamentares`.
- A **primeira** requisição devolveu o HTML de verdade. Ele traz os filtros: Exercício; Parlamentar (lista com os 46 deputados); Região (as 14 regiões de planejamento); **Beneficiário (prefeituras, como "PREF MUNIC DE ABAIARA"…)**; Função; **Tipo de Emenda: PCF - INDIVIDUAL, PCF - COLETIVA, GERAL - INDIVIDUAL, GERAL - COLETIVA**. A tabela é carregada depois, por AJAX ("Carregando…"), e a exportação acontece no navegador (TableExport/xlsx).
- Todas as requisições seguintes (`.json`, `.csv`, XHR e a página histórica) voltaram com uma **página de desafio em JavaScript** (antirrobô, com cerca de 250 KB de script ofuscado). Não tentei contornar. O WebFetch também voltou vazio.
- `https://dados.ce.gov.br` respondeu **403 "Acesso Negado"** a tudo, inclusive à API CKAN.
- **Emenda Pix estadual: na prática, sim**, mas com outro nome. O "PCF" é o Programa de Cooperação Federativa (LC 234/2021): o recurso passa a ser do município no momento da transferência. Pela imprensa (Diário do Nordeste), o CE era um dos 4 estados sem emenda impositiva para deputados.
- Próximo passo: abrir a página num navegador comum, operado pelo próprio usuário, e exportar; ou pedir o arquivo por LAI à CGE-CE.

---

### MA — Maranhão — Verificado (dificuldade 2)

- Página: `https://www.transparencia.ma.gov.br/app/v2/emendasestaduais`
- **Exportação direta**: `https://www.transparencia.ma.gov.br/app/v2/emendasestaduais/export?ano=2026&formato=csv` (também aceita `xlsx` e `pdf`). Sai um CSV com vírgula como separador, de 522 KB. Os filtros da busca são `ano, parlamentar, tipo, ug, modalidade, busca, limite`.
- **Só há o ano de 2026.** O seletor de ano só oferece 2026, e pedir `ano=2025`, `2024` ou `2023` devolve o mesmo arquivo de 2026. Os anos anteriores talvez estejam nos portais antigos ("Transparência 2015-2022") ou na despesa geral; não achei.
- Colunas: `Solicitação, Número Emenda, Exercício, Parlamentar, Tipo, Modalidade, UG, Nome UG, Empenhos, Entidade Beneficiada, Localizador de Gasto, Objeto, Função, Subfunção, Ação, Subação, Valor Solicitado, Valor Repasse, Valor Pré-Empenhado, Valor Empenhado, Valor Liquidado, Valor Pago, Código Favorecido, Última Atualização`
- Cidade: `Localizador de Gasto` traz o **nome do município** (175 diferentes; "SÃO LUÍS" tem 206 linhas). O `Código Favorecido` é o CNPJ (não achei CPF).
- Números de 2026: 941 linhas, 42 parlamentares. Valor solicitado R$ 512,1 mi, repasse R$ 357,8 mi, empenhado R$ 473,0 mi, pago **R$ 338,6 mi**.
- Por modalidade: 50 - entidades privadas sem fins lucrativos 368, 90 - aplicação direta 285, 41 - fundo a fundo para município 223, 40 - transferência a município 65.
- Exemplos:
  - GLALBERT CUTRIM | FEIRA NOVA DO MARANHÃO | (prefeitura, CNPJ) | R$ 200.000 pago | festa "Lava-Pratos: Feira Folia 2026"
  - DAVI BRANDÃO | BACABAL | ASSOCIAÇÃO FOLCLÓRICA BOI ENCANTO DO OLHO D'ÁGUA | R$ 500.000 pago
  - CLÁUDIO CUNHA | SERRANO DO MARANHÃO | associação comunitária | R$ 500.000 pago
- **Emenda Pix estadual:** a Constituição do MA a prevê (art. 137-A, incluído pela EC 93/2023: transferência especial e transferência com finalidade definida). Nos dados de 2026, porém, não há modalidade nem texto marcado como "transferência especial" (só existem as modalidades 40 e 41). Se a Pix foi usada, está escondida dentro da modalidade 40.
- `https://dados.ma.gov.br` (CKAN) não respondeu: a conexão TLS fica sem resposta até estourar o tempo, mesmo com 90 s.

---

### RN — Rio Grande do Norte — Verificado pela API do Power BI (dificuldade 4)

- Página: `https://www.transparencia.rn.gov.br/emendas-estado`. Atenção: o endereço sem `www` dá erro de certificado; com `www` funciona. A página só embute um Power BI público: `https://app.powerbi.com/view?r=eyJrIjoiODJmNjFjZjctYWJmNy00NTMyLTg5YmUtOTY1ODI2YWJmNzlkIiwidCI6IjY5ZGRiNzgyLTljZGQtNDM3MC1iNzQ4LTI3MGRjNDE2NDU0ZCJ9`
- `/emendas-pix` redireciona para o Transferegov **federal**. `dados.rn.gov.br` (CKAN) está **vazio** (`package_list` = []). A API do SIPAC (`api.sipac.rn.gov.br/transparencia`) só tem contratos.
- Li o relatório pela mesma API interna que a página usa (`wabi-brazil-south-d-primary-api.analysis.windows.net/public/reports/...`, cabeçalho `X-PowerBI-ResourceKey: 82f61cf7-abf7-4532-89be-965826abf79d`, modelId 382447). O relatório se chama "Emendas_Parlamentares_OGE_NOVO3" e foi atualizado em 23/11/2026.
- Colunas da tabela "Emendas Parlamentares": Exercicio, Codigo Emenda, Tipo de autoria, Tipo de Emenda, Nome Deputado Padronizado, Partido, Orgao, Unidade Gestora, Origem (Fonte), Descrição, **Beneficiário (CNPJ + nome)**, **Localidade beneficiada ("IPUEIRA/RN")**, Natureza da Despesa, Area temática, Subação, Processo SEI, Objeto da Despesa, datas, Banco/Conta/Agência, Contrato, Nota fiscal, **Valor alocado**, % Execução, NE/NL/OB, **Valor empenhado, liquidado e pago (Execução)**, Status da Emenda, Instrumento, Plano de Trabalho.
- Anos: 2023 a 2026; 1.953 pares (ano, código de emenda) e 238 localidades diferentes.

| ano | Finalidade definida | **Transferências Especiais** | Fundo a Fundo |
|---|---|---|---|
| 2023 | R$ 143,4 mi | R$ 38,1 mi | R$ 61,8 mi |
| 2024 | R$ 42,8 mi | R$ 59,9 mi | R$ 73,8 mi |
| 2025 | R$ 149,2 mi | R$ 70,2 mi | R$ 201,6 mi |
| 2026 | R$ 247,6 mi | R$ 32,1 mi | R$ 71,4 mi (mais R$ 20 mi sem tipo) |

  Esses são valores alocados. O **pago dentro do painel quase não aparece**: R$ 0,35 mi em 2024 e R$ 10,5 mi de TE em 2026. A execução parece não estar preenchida ou não estar ligada à tabela.
- A localidade às vezes vem como "EM PROCESSO DE COLETA DE INFORMAÇÕES".
- Exemplos de 2026, transferência especial:
  - Adjuto Dias | IPUEIRA/RN | MUNICÍPIO DE IPUEIRA | R$ 100.000
  - Adjuto Dias | JARDIM DE PIRANHAS/RN | MUNICIPIO DE JARDIM DE PIRANHAS | R$ 340.000
  - Coronel Azevedo | CARNAÚBA DOS DANTAS/RN | MUNICIPIO DE CARNAUBA DOS DANTAS | R$ 100.000
- **Emenda Pix estadual: SIM** ("Transferências Especiais"). A Portaria SEI nº 575/2026 publicou as emendas pagas por transferência especial.
- A dificuldade é 4 porque só existe o Power BI. Dá para baixar em lote pela API `querydata` com consultas DAX semânticas (meu script está em `scripts/pbi_query.py`), mas o caminho é frágil (o cluster e a chave podem mudar).

---

### PB — Paraíba — Verificado (dificuldade 1)

- API oficial: `https://api.dados.pb.gov.br/api/v1` (Swagger em `https://api.dados.pb.gov.br/swagger/`, especificação em `/api/v1/swagger.json`). Não precisa de chave; a paginação usa `page` e `per_page` (aceita até 500).
- **`GET /orcamento/listagem_emendas?ano=`** (indicação). Campos: `ano, emenda ("0399/2025"), prioridade, nomeDeputado, tipo, secretaria, objeto, retificacaoObjeto, beneficiarioFinal, tipoEntidade, valor, dataEnvio`, além dos pareceres e datas da SEPLAG e da SEFAZ. Esses pareceres trazem nomes de servidores; não precisamos deles.
- **`GET /orcamento/execucao_emendas?ano=`** (execução). Campos: `ano, codigoOrgao, nomeOrgao, nomeAutor, emenda, unidadeOrcamentaria, funcao, subfuncao, programa, acao, naturezaDespesa, fonteRecurso, categoriaEconomica, grupoDespesa, modalidadeAplicacao, elementoDespesa, valorEmenda, valorEmpenhado, valorLiquidado, valorPago`. As duas tabelas se ligam pelo número da `emenda` (816 de 821 casam em 2025).
- Também existe `/despesas/notas_empenho` com o filtro `numeroEmenda`, que leva ao credor.
- Anos: 2021 a 2026. Em 2019 e 2020 a API responde 404. Linhas da listagem por ano: 2021 = 252, 2022 = 424, 2023 = 532, 2024 = 848, 2025 = 821, 2026 = 686.
- Números de 2025: 821 emendas, todas "IMPOSITIVA", 36 deputados, R$ 166,7 mi indicados. Na execução, valor da emenda R$ 167,8 mi, empenhado R$ 158,7 mi e **pago R$ 154,2 mi**. Por modalidade: transferência a municípios 418, entidades privadas sem fins lucrativos 352, aplicação direta 58.
- Cidade: **só no texto livre do `objeto`** ("Transferir os recursos para a Prefeitura Municipal de PATOS-PB…"). O campo `beneficiarioFinal` quase sempre vem vazio (24 de 821 preenchidos).
- Exemplos:
  - FRANCISCA MOTTA | Patos (pelo texto) | Prefeitura Municipal de Patos | R$ 300.000 indicado e pago | ambulância (2025)
  - TANILSON SOARES | Instituto Visão Para T… | R$ 400.000 pago (2025)
  - SILVIA BENJAMIN | UMBUZEIRO | município | R$ 300.000 | tipo "Especial" (2026)
- **Emenda Pix estadual: SIM a partir de 2026.** Em 2026 o `tipo` passa a ser "Especial" (301 + 9 "ESPECIAL", somando R$ 107,9 mi), "Convênio/Parceria" (348, R$ 60,2 mi) ou "Execução Própria" (28). Até 2025 era tudo "IMPOSITIVA".
- `/convenios/uniao_estado/transferencias_especiais` também existe, mas é **federal**.

---

### AL — Alagoas — Verificado (dificuldade 2)

- Página: `https://transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais/`
- **JSON interno da página**: `https://transparencia.al.gov.br/despesa/json-emendas-parlamentares/?limit=1000&offset=0`, que devolve `total`, `rows` e as somas. O filtro `ano=2025` devolve 0 linhas, porque **só existe 2026** (391 linhas).
- Campos: `ano, parlamentar, partido, partido_completo, unid_parlamentar, codigo_identificador_emenda ("I0015"), localidade, municipio, ato_normativo, forma_repasse, modalidade, objeto_despesa, beneficiario, cronograma_execucao_inicio/fim, orgao_entidade_executora, valor_dotacao_inicial, valor_dotacao_atualizado, valor_empenhado, valor_liquidado, valor_pago, restos_a_pagar, percentual_execucao, numero_convenio`. Os valores vêm como texto no formato "338.029,26".
- Cidade: `municipio` com o **nome normal** ("Marechal Deodoro"); 67 municípios diferentes.
- Números de 2026: 391 linhas, 27 parlamentares. Dotação R$ 281,2 mi (desconfie: a dotação inicial parece estar repetida por deputado), empenhado R$ 211,4 mi, **pago R$ 201,1 mi**.
- `forma_repasse`: Termo de Fomento 194, Portaria SESAU 81, **Transferência Especial 71 (R$ 43,6 mi pagos)**, Aplicação Direta 18…
- Exemplos:
  - Cabo Bebeto | Campo Alegre | PREF MUNI CAMPO ALEGRE | R$ 400.000 pago | Transferência Especial
  - Cabo Bebeto | Coruripe | PREF MUNI CORURIPE | R$ 300.000 pago | Transferência Especial
  - ALEXANDRE AYRES (MDB) | Marechal Deodoro | FUNDO MUNI SAUDE MARECHAL DEODORO | R$ 338.029,26 pago | fundo a fundo (SESAU)
- **Emenda Pix estadual: SIM** ("Emenda Individual - Transferência Especial").
- O CKAN `https://dados.al.gov.br/catalogo` tem apenas os **manuais** das emendas impositivas (PDFs de 2022 a 2026), sem dados.
- A página de AL também tem links para o Transferegov e o Portal da Transparência federal; esses tratam de emendas federais.

---

### SE — Sergipe — Verificado (dificuldade 2)

São duas fontes.

#### A) 2022–2025: API do portal, `https://api.transparencia.se.gov.br/api`
- Página: `https://www.transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais`
- `GET /api/emendas-estaduais/anos` → `[2025, 2024, 2023, 2022]`
- `GET /api/emendas-estaduais?ano=2025&page=1&limit=100` → `{data, total, page, limit, totalPages}` (o `limit` vai até 100).
- Campos: `exercicio, orgaoProcessador, parlamentar, descricaoObjeto, executor (nome + CNPJ em texto), localidade, acao, gnd, valorIndicado (" 200.000 "), valorPago`
- Cidade: `localidade` com o nome em maiúsculas ("PORTO DA FOLHA"). A qualidade é irregular: às vezes o `executor` traz o texto do objeto.

| ano | linhas | indicado | pago | deputados |
|---|---|---|---|---|
| 2022 | 520 | R$ 36,0 mi | R$ 33,6 mi | 24 |
| 2023 | 442 | R$ 44,7 mi | R$ 39,2 mi | 24 |
| 2024 | 605 | R$ 58,1 mi | R$ 55,6 mi | 24 |
| 2025 | 635 | R$ 72,2 mi | R$ 33,8 mi (só 158 com pago preenchido) | 24 |

- Exemplos de 2024: GEORGEO PASSOS | SIRIRI | PREFEITURA MUNICIPAL DE SIRIRI | R$ 18.500 indicado e pago; KAKA SANTOS | TOBIAS BARRETO | PREFEITURA MUNICIPAL DE TOBIAS BARRETO | R$ 56.000 indicado e pago.

#### B) 2026 em diante: "Painel de Monitoramento das Emendas Parlamentares Estaduais" (ADPF 854), `https://sergipeemendasparlamentares.plataformatarget.com.br/`
- Esse painel é hospedado numa plataforma privada (Target), e o portal oficial aponta para ele.
- `GET /api/filtros` traz os anos 2026, 2027 e 2028, os autores (nomes civis completos dos deputados), áreas, órgãos e localidades.
- `GET /api/emendas?page=1&limit=200` (o `limit` vai até 200).
- **`GET /api/emendas/export?` devolve tudo de uma vez em JSON** (668 linhas, 1 MB).
- Campos: `uuid_emenda, n_emenda ("145.0045.2026-0124"), autor, objeto, valor, tipo_emenda, modalidade_da_emenda, area, orgao_executor, monitoramento, empenho, liquidacao, pagamento, dotacao, gnd, numero_empenho/data, numero_liquidacao/data, numero_pagamento/data, restos a pagar, tipo_instrumento, municipio, localidade, beneficiario, cnpj, detalhamento_objeto, metas, cronograma, situacao_atual, aplicacao, fonte_recurso, cd_funcao…`. Há também `/api/plano-trabalho/{uuid}` e `/api/expediente-encaminhado/{uuid}`.
- Números de 2026: 668 linhas, 27 autores, 74 municípios (nome normal, "Barra dos Coqueiros"). Valor indicado R$ 83,9 mi, empenhado R$ 32,5 mi, **pago R$ 28,0 mi**.
- `tipo_instrumento`: TERMO DE FOMENTO 356, REPASSE FUNDO A FUNDO 145, **TRANSFERÊNCIA ESPECIAL 62 (R$ 12,5 mi indicados)**, TERMO DE CONVÊNIO 38, EXECUÇÃO DIRETA 25, PROFIN 28.
- Exemplos:
  - ADAILTON MARTINS DE OLIVEIRA FILHO | Maruim | PREFEITURA MUNICIPAL | R$ 300.000 | TRANSFERÊNCIA ESPECIAL
  - ADAILTON MARTINS DE OLIVEIRA FILHO | Santana do São Francisco | PREFEITURA MUNICIPAL | R$ 330.000 | TRANSFERÊNCIA ESPECIAL
  - ADAILTON MARTINS DE OLIVEIRA FILHO | Barra dos Coqueiros | MUNICÍPIO DE BARRA DOS COQUEIROS | R$ 360.000 | termo de fomento (saúde)
- **Emenda Pix estadual: SIM em 2026.** A área aparece rotulada, por erro de digitação, como "Transparência Especial". Nos dados de 2022–2025 não há marcação de TE.
- Atenção: as duas fontes escrevem o nome do deputado de jeitos diferentes ("MARCOS OLIVEIRA" contra "MARCOS VINICIUS LIMA DE OLIVEIRA"), e o painel de 2026 tem nomes duplicados com e sem acento. Vai precisar de uma tabela de correspondência.
- `https://dados.se.gov.br` não respondeu.

## Emendas parlamentares estaduais — Sul e Sudeste (MG, SP, RJ, ES, PR, SC, RS)

Levantamento feito em 23/11/2026. Amostras baixadas em

Legenda de status: **Verificado** = abri os dados e contei linhas/valores; **Descrito** = só vi a página; **Não encontrado**.

Nota sobre Power BI: vários estados usam painel Power BI público (`app.powerbi.com/view?r=...`).
O próprio painel chama uma API interna (`wabi-brazil-south-b-primary-api.analysis.windows.net/public/reports/...`,
cabeçalho `X-PowerBI-ResourceKey` = a chave `k` que vem em base64 no `r=`). Com ela dá para ler o esquema
(`/public/reports/conceptualschema`) e fazer consultas (`/public/reports/querydata`), sem login. Foi assim que
abri SP, SC e o painel federal do PR. Dá para baixar em lote, mas é trabalhoso (limite de linhas por consulta,
formato comprimido "DSR"). O RS usa Power BI "embedded" com token que a própria página pede em
`/umbraco/Surface/PowerBI/Report` — mesma ideia, um passo a mais.

---

### MG — Minas Gerais — **Verificado**

**Fonte principal (dados abertos, CKAN):** https://dados.mg.gov.br/dataset/portal_emendas_estaduais
(API: `https://dados.mg.gov.br/api/3/action/package_show?id=portal_emendas_estaduais`; precisa mandar User-Agent,
senão vem resposta vazia). Criado em 23/09/2026, atualização semanal, licença não definida (`isopen: false`).

Recursos (CSV `;`, UTF-8 com BOM, decimal com vírgula):
- **Emendas Estaduais - Indicações** — `.../resource/d85d9a92-dd8e-473d-bcb4-a4f3d13309b1/download/vw_sg_v2_ep_indic_recursos_tw.csv` (42 MB, 53.978 linhas, 2021–2026). **É o arquivo que interessa.**
- Emendas Estaduais - Execução — `.../resource/55a1c9a5-2647-4c6f-a4e8-e98249009e13/download/vw_sg_v2_ep_ce_indicacao_tw.csv` (18 MB; controle de execução por indicação: processo de compra, doação de bens, empenhos, valores).
- Execução 2022 … 2026 — `.../download/execucao2022.csv` etc. (1,5–2,5 MB cada; nível empenho: credor, CNPJ/CPF do credor, elemento, fonte, empenhado/liquidado/pago; **sem deputado e sem município** — liga por `numero_siafi`). Atenção: coluna `cnpj_cpf_credor_formatado` pode ter CPF.
- datapackage.json (esquema, sem descrições úteis).

Colunas do arquivo de Indicações (principais): `numero_indicacao; tipo_inciso; numero_inciso; ano_exercicio; indicador_impositividade; uo; uo_sigla; uo_descricao; responsavel; tipo_indicacao; status_indicacao; municipio; municipio_ibge; beneficiario_nome; beneficiario_cnpj; beneficiario_tipo; acao_numero; acao_nome; funcao_descricao; minimo; tipo_aplicacao_descricao; descricao_indicacao; valor_indicacao; valor_utilizado; valor_empenhado; valor_liquidado; valor_executado; valor_pago; proposta_*; plano_*; instrumento_*; numero_siafi; classificacao_resp_descricao; valor_empenhado_ano; valor_liquidado_ano; valor_pago_ano; valor_restos_pagar; agencia; conta; justificativa_reprovacao; cnes; numero_convenio` (77 colunas).

- Deputado: **sim** (`responsavel`; `classificacao_resp_descricao` = PARLAMENTAR ESTADUAL / BLOCO / BANCADA — ~10 mil linhas são de blocos).
- Cidade: **sim, código IBGE de 7 dígitos** (`municipio_ibge`, vem como "3106200,0" — tirar o ",0"), mais nome. ~90% das linhas têm IBGE.
- Beneficiário: **sim** (nome, CNPJ, tipo: MUNICÍPIO, FUNDO MUNICIPAL DE SAÚDE, OSC, CAIXA ESCOLAR, órgão público, consórcio).
- Objeto: `descricao_indicacao`, `tipo_aplicacao_descricao`, `acao_nome`.
- Valores: indicado (`valor_indicacao`), empenhado, liquidado, pago (acumulado e do ano), restos a pagar.
- Só impositivas (`indicador_impositividade` = S em 100%). Status: APROVADO / ENVIADA PARA SEE / REPROVADO PELO ÓRGÃO (com justificativa).

**Emenda Pix: sim.** `tipo_indicacao` = "TRANSFERÊNCIA ESPECIAL" (18.985 linhas no total). 2025: 3.782 indicações, R$ 792 mi indicados, R$ 785 mi pagos.

Totais por ano (todas as linhas, inclusive reprovadas):

| ano | linhas | indicado | pago |
|---|---|---|---|
| 2021 | 8.004 | R$ 923 mi | R$ 430 mi |
| 2022 | 8.444 | R$ 1,15 bi | R$ 552 mi |
| 2023 | 7.181 | R$ 1,32 bi | R$ 1,15 bi |
| 2024 | 8.191 | R$ 1,75 bi | R$ 1,63 bi |
| 2025 | 10.945 | R$ 2,30 bi | R$ 2,12 bi |
| 2026 | 11.213 | R$ 2,65 bi | R$ 1,12 bi (em andamento) |

2025 só APROVADO: 9.469 linhas, R$ 2,07 bi indicados, 80 responsáveis.
Obs.: em 2021–2022 a transferência especial e os convênios aparecem com pago = 0 (provável lacuna do arquivo nesses anos).

Exemplos reais (2025):
- ZÉ GUILHERME → Cachoeira Dourada (IBGE 3109808) → MUNICIPIO DE CACHOEIRA DOURADA — TRANSFERÊNCIA ESPECIAL — R$ 100.000 indicado / R$ 100.000 pago.
- MARLI RIBEIRO → Riachinho (3154457) → FUNDO MUNICIPAL DE SAUDE DE RIACHINHO — RESOLUÇÃO SES, "VEÍCULO 7 LUGARES" — R$ 150.000 / pago R$ 150.000.
- BEATRIZ CERQUEIRA → Belo Horizonte (3106200) → FUNDACAO EDUCACIONAL LUCAS MACHADO FELUMA (OSC) — custeio saúde — R$ 500.000 / pago R$ 500.000.

Outras fontes (Descrito): página da ALMG https://www.almg.gov.br/atividade-parlamentar/emendas-parlamentares/inicial/ (consulta por deputado/município, tela); portal emendas.mg.gov.br (Segov). `dadosabertos.almg.gov.br` não respondeu daqui. Não precisei deles: o CKAN já tem tudo.

**Dificuldade: 1.** CSV limpo, com IBGE, deputado, beneficiário e valores.

---

### SP — São Paulo — **Verificado (via API do painel Power BI)**

**Onde está:** Portal da Transparência SP, https://www.transparencia.sp.gov.br/home/emendasparlamentares
- Painel "LOA - 2025 - Emendas Impositivas" (Power BI, chave `c53a54e7-9c63-4d84-be1a-5111bf2756d8`)
- Painel "LOA - 2024 - Emendas Impositivas" (chave `7ae99f38-6898-461b-8d93-aeee788c318a`)
- Painel "Emendas individuais 2023" (chave `f7243798-e16d-47bf-a76d-587c0fc94501`)
- PDFs 2020–2022 (saúde / outros): `https://www.transparencia.sp.gov.br/EmendasImpositivas/2022_Saude_30_01_25.pdf`, `..._2022_ExcetoSaude_30_01_25.pdf`, idem 2021 e 2020 (~1 MB cada).
- Alesp: https://al.sp.gov.br/leis/orcamento/emendas-impositivas/ — PDFs por ano `https://www.al.sp.gov.br/arquivos/leis/orcamento/emendas-impositivas/2019.pdf` … `2026.pdf` (2026 = 2,7 MB; é a lista aprovada na LOA).
- Não achei painel de 2026 no portal. O site da SGRI (`www.governo.sp.gov.br/emendas-individuais-impositivas/`) bloqueia robô (Incapsula, "Request unsuccessful") — não abri.
- `dadosabertos.al.sp.gov.br` (dados abertos da Alesp): certificado TLS incompleto, não abri. Não há CSV de emendas no CKAN do estado que eu tenha achado.

Colunas do modelo Power BI (tabela `Total`, igual em 2024 e 2025): `MUNICÍPIO, OBJETO, ANO, CÓDIGO, Primeira Fase Substituídas, VALOR DECISÃO, VALOR REMANEJADO, ÓRGÃO PROCESSADOR, PARLAMENTAR, PARTIDO, BENEFICIÁRIO, DATA PAGAMENTO, FUNÇÃO DE GOVERNO, ESTÁGIO, TIPO EMENDA, CNPJ BENEFICIÁRIO, CNPJ Formatado`.

- Deputado: **sim** (nome + partido).
- Cidade: **nome** (sem IBGE).
- Beneficiário: **sim** (nome e CNPJ; prefeitura aparece como "PREF. MUNICIPAL").
- Objeto: texto livre curto ("CUSTEIO", "AQUISICAO DE EQUIPAMENTOS"…).
- Valores: **valor da decisão (indicado)** + **estágio** (Pagas / Empenhado-Convênio / Em processamento-Sem empenho / Impedida tecnicamente) e data de pagamento. Não tem empenhado/pago em reais separados — o estágio diz se foi pago.

Totais:
- 2025: 5.617 emendas, R$ 1,19 bi; Pagas R$ 1,055 bi; Empenhado/Convênio R$ 70,7 mi; Em processamento R$ 28,7 mi; Impedida 2ª fase R$ 36,0 mi.
- 2024: 5.389 emendas, R$ 1,03 bi; Pagas R$ 959 mi.

**Emenda Pix:** existe na lei (Constituição SP, art. 175-A, EC 50/2021: "transferência especial" e "com finalidade definida"; a Alesp citou R$ 109 mi em transferências especiais em 2023). No painel, `TIPO EMENDA` só vale "EMENDA LOA" — **não separa** a transferência especial.

Exemplos reais (2025, painel):
- AGENTE FEDERAL DANILO BALAS (PL) → Alambari → PREF. MUNICIPAL — CUSTEIO — R$ 250.000 — Pagas.
- AGENTE FEDERAL DANILO BALAS → Alumínio → PREF. MUNICIPAL — AQUISICAO DE EQUIPAMENTOS — R$ 140.000 — Pagas.
- AGENTE FEDERAL DANILO BALAS → Araçoiaba da Serra → ASSOCIAÇÃO DE CONVIVÊNCIA NOVO TEMPO — obra/reforma — R$ 132.500 — Pagas.

**Dificuldade: 3.** Sem arquivo; dá para extrair 2023–2025 pela API do Power BI (5–6 mil linhas por ano, cabe). 2020–2022 só PDF; 2026 só PDF da Alesp (lista da LOA, sem execução).

---

### RJ — Rio de Janeiro — **Verificado**

**Onde está:** Redeplan (Secretaria de Planejamento) https://www.redeplan.planejamento.rj.gov.br/demaisprocessos/emendas.html
— página com CSV/XLSX para baixar direto (base `https://www.redeplan.planejamento.rj.gov.br/img/docs/emendas/`):
- `base_EmendasImpositivas2024_govrj19122024.csv` (ISO-8859-1) — 779 linhas, R$ 181,9 mi
- `base_EmendasImpositivas2025_govrj29122025.csv` (UTF-8) — 856 linhas, R$ 203,0 mi, 70 autores
- `2026/base_detalhamento_emendas_impositivas_2026_govrj_15012026.csv` — 1.182 linhas, R$ 221,8 mi; também `..._09042026_1fase.csv` e `2026/base_DetalhamentoEmendasImpositivas2026_govrj06112026 - 2fase.csv`
- Execução: `relatorio_execucao_orcamentaria_financeira_emendas _impositivas_3_quadri_2025.csv` (com espaço no nome), `2026/4bi_Relatório de Execução Orçamentária e Financeira das Emendas Impositivas 2026.csv`, e 2024 (1º/2º e 3º quadrimestre).
- `2026/ProcessosSEI2026emendas_impositivas_govrj06112026.csv` (número do processo SEI por emenda).
- Também: Portal da Transparência RJ https://www.transparencia.rj.gov.br/emendas-parlamentares/ → painel Qlik `https://qlik.rj.gov.br/public/sense/app/a3cfd25a-0fc6-46d8-be87-52fb6e29f066/...` (não abri). CKAN `dadosabertos.rj.gov.br` não tem emendas estaduais. API do TCE-RJ (`dados.tcerj.tc.br/api/v1`) **não tem** endpoint de emendas.

Colunas (base 2025): `Emenda; Identificador; Autor; Valor; UP; UO; Ação; Função; Subfunção; GG; GD; Objeto; Justificativa; Beneficiário; Município; CNPJ; Converj; Modalidade; Categoria; Observações/justificativa; Fluxo`.
(2024 é mais pobre: `Número Emenda; Autor; Valor; UP; UO; Nome emenda; Justificativa; Ação; Grupo de gasto; Grupo de despesa; Função; Subfunção; Município` — sem beneficiário nem modalidade.)

Colunas (execução): `Posição; Sigla UO; Cod Ação; Tit Ação; Ano Fonte; Fonte RJ; Fonte STN; Deputado; Cod. Emenda; Nº Empenho; Descrição; Dotação Inicial; Empenhado; Liquidado; Pago` — formato de relatório (linhas de subtotal, células vazias repetidas), liga com a base pelo `Identificador` = `Cod. Emenda`.

- Deputado: **sim** (`Autor`).
- Cidade: **nome** (sem IBGE); ~25% das linhas dizem "Estado" (sem município).
- Beneficiário: sim em 2025–2026 (nome + CNPJ); não em 2024.
- Valores: indicado (`Valor`) na base; dotação/empenhado/liquidado/pago no relatório de execução. 2025 (3º quadrimestre): dotação R$ 203,0 mi, empenhado R$ 166,8 mi, liquidado R$ 156,3 mi, pago R$ 151,2 mi.

**Emenda Pix: sim.** `Modalidade` = "2 - Transferência Especial" (2025: 58 emendas, R$ 19,7 mi; 2026: 86, R$ 12,5 mi). Outras modalidades: Execução Direta, Finalidade Definida, Fundo a Fundo, OSC. Base legal: EC 75/2019 e EC 97/2023 (arts. 209/210 da Constituição RJ), LC 219/2024.

Exemplos reais:
- 2025 — Bruno Boaretto → São Fidélis → PREFEITURA MUNICIPAL DE SÃO FIDÉLIS — Transferência Especial — obra em orla de rio — R$ 200.000.
- 2025 — Carlinhos BNH → São Pedro da Aldeia → FUNDO MUNICIPAL DE SAUDE DE SÃO PEDRO DA ALDEIA — Fundo a Fundo — reforma de unidade — R$ 269.853.
- 2026 — Giovani Ratinho → Mendes → PREFEITURA MUNICIPAL DE MENDES — Transferência Especial — reforma de quadra — R$ 400.000.

**Dificuldade: 2.** CSV direto, pequeno; mas nomes de arquivo mudam a cada publicação, encoding varia, município só por nome, execução em formato de relatório. Montante pequeno (~R$ 3 mi por deputado/ano).

---

### ES — Espírito Santo — **Verificado**

**Fonte (dados abertos, CKAN):** https://dados.es.gov.br/dataset/portal-da-transparencia-emendas-parlamentares-do-estado
(org. Sefaz; atualizado em 23/11/2026). Downloads redirecionam para S3 (`one.s3.es.gov.br`), usar `curl -L`.
- `Emendas-Estaduais-2021.csv` … `Emendas-Estaduais-2026.csv` (0,7–1,6 MB) — cadastro + execução por emenda
- `Emendas-Estaduais-Execucao-2021.csv` … `-2026.csv` (4–6 MB) — nível empenho/pagamento (tem `CpfCnpjNis` e `CargoFuncao`; pode ter PF)
- `Emendas-Estaduais-Convenios.csv`, `-Contratos.csv`, `-AditivosContratos.csv` (convênios têm `codIBGEMunicipio`)

Colunas (arquivo anual): `CodAutor; NomeAutor; AnoEmenda; NumeroEmenda; ObjetoFinalidade; AcaoPPA; DescricaoAcaoPPA; RegiaoBeneficiada; DescricaoRegiaoBeneficiada; OrgaoExecutor; DescricaoOrgaoExecutor; ValorPrevisto; IdtElemento; NomeElemento; TipoEmenda; CodigoModalidade; Modalidade; CodigoConvenio; CodigoContrato; NumeroInstrumento; CpfCnpjNis; Favorecido; ValorEmpenho; ValorLiquidado; ValorPago; ValorRap; CodigoGrupoDespesa; GrupoDespesa; Esfera; DescricaoEsfera; CodigoFuncao; Funcao; CodigoSubFuncao; SubFuncao; CodigoMunicipio; Municipio; DotacaoAtualizada; Id`.

- Deputado: **sim** (`NomeAutor`, "Dep. Fulano"; 30 autores).
- Cidade: **sim, código IBGE de 6 dígitos (sem dígito verificador)** — ex.: Vitória `320530` (= IBGE 3205309). Mais o nome. Cuidado: às vezes o município não bate com o favorecido (ex.: emenda com Município=Vila Velha e Favorecido=Prefeitura de Nova Venécia).
- Beneficiário: **sim** (`Favorecido` + CPF/CNPJ). Não achei CPF no arquivo anual de 2025; o de execução pode ter.
- Objeto: `ObjetoFinalidade` (texto livre, longo).
- Valores: previsto, empenhado, liquidado, pago, RAP. Uma emenda pode ter várias linhas (uma por favorecido/empenho) — o `ValorPrevisto` se repete; somar por `NumeroEmenda` único.

Totais:
- 2025: 2.430 linhas, 1.346 emendas; previsto R$ 176,8 mi; empenhado R$ 105,8 mi; pago R$ 96,5 mi.
- 2026: 2.528 linhas, 1.684 emendas; previsto R$ 275,5 mi; pago R$ 171,5 mi.
- 2024: previsto R$ 181,2 mi, mas só R$ 45,3 mi pagos no arquivo (talvez execução registrada em outro ano).

**Tipo:** todas "Individual com finalidade definida **não impositiva**". A Ales aprovou em out/2026 a PEC 04/2026 tornando as emendas impositivas a partir da LOA 2027 (R$ 3 mi → R$ 14,5 mi por deputado, segundo A Gazeta).
**Emenda Pix estadual: não encontrada** (as "transferências especiais" que a Sefaz-ES publica são as federais recebidas). Não confirmei se a PEC 04/2026 cria transferência especial.

Exemplos reais (2025):
- Dep. Raquel Lessa → Aracruz (320060) → ARCA-ASSOCIACAO RECREATIVA E CULTURAL DE ARACRUZ — eventos esportivos — previsto R$ 20.000 / pago R$ 19.999,50.
- Dep. Vandinho Leite → Brejetuba (320115) → INSTITUTO SUSTENTABILIDADE BRASIL - ISB — apoio à comercialização — R$ 70.000 / pago R$ 70.000.
- Dep. Capitão Assumção → (Município=Vila Velha) → PREFEITURA MUNICIPAL DE NOVA VENÉCIA — transferência a município — previsto R$ 1.000.000 / pago R$ 100.000.

**Dificuldade: 1.** CSV limpo por ano, com IBGE (6 dígitos) e valores. Montante pequeno (~R$ 6–9 mi/deputado).

---

### PR — Paraná — **Verificado (parcial)**

**Onde está:**
- Fazenda PR, "Execução de Emendas Parlamentares": https://www.fazenda.pr.gov.br/Pagina/Execucao-de-Emendas-Parlamentares
  - CSV: `https://www.documentador.pr.gov.br/documentador/pub.do?action=d&uuid=@gtf-escriba-sefa@69521a9d-77b2-4a6b-b61f-72e9857161fb` (1,4 MB, cp1252)
  - XLSX: `...uuid=@gtf-escriba-sefa@30dba98a-de46-475b-9891-d5cafbe31a35`
  - Cobre **2025 e 2026**.
- Fazenda PR, "Emendas Parlamentares" (LOA): https://www.fazenda.pr.gov.br/Pagina/Emendas-Parlamentares — XLS `...uuid=@gtf-escriba-sefa@3c9a647e-e9d3-4f36-adf4-53680d02c123` ("Relatório Execução das Emendas LOA 2024", 201 linhas, com código IBGE do município, sem deputado).
- Painel da Sedef (anunciado em jun/2026): https://www.social.pr.gov.br/emendas — **não abriu daqui** (conexão recusada / timeout; provável bloqueio de IP). Não tentei contornar.
- Cuidado: o painel Power BI em https://www.fazenda.pr.gov.br/Pagina/Consulta-de-Emendas-Parlamentares é de **emendas federais** recebidas pelo estado (deputados federais/senadores), não estaduais. Idem "Emendas Parlamentares PIX" e "Recebidas" no portal da transparência.

Colunas (CSV de execução): `Exercício; Emenda Parlamentar; Autor (Parlamentar); Beneficiário / Credor; CNPJ / CPF; Descrição da Despesa (Objeto); Nº do Empenho; Órgão; Unidade Orçamentária; Ação; Município; Dotação Inicial (R$); Dotação Atualizada (R$); Despesas Empenhadas (R$); Despesas Liquidadas (R$); Despesas Pagas (R$)`.

- Deputado: **sim** (55 autores).
- Cidade: **nome** (no CSV); código IBGE só no XLS da LOA 2024 (que não tem deputado).
- Beneficiário: **sim** (OSC + CNPJ; não vi CPF).
- Valores: dotação inicial/atualizada, empenhado, liquidado, pago.
- **Limitação grande:** 100% das linhas são da Secretaria do Desenvolvimento Social e Família, ação "Projetos Estratégicos Integrados", objeto padrão "OSCs beneficiadas com recurso financeiro…". Parece ser só o programa de emendas a OSCs.

Totais: 2025 — 1.528 linhas, 1.475 emendas, dotação inicial R$ 81,0 mi, empenhado R$ 15,0 mi, pago R$ 5,8 mi. 2026 — 2.031 linhas, dotação R$ 108,0 mi, empenhado R$ 21,8 mi, pago R$ 19,7 mi.

Não achei emendas impositivas estaduais no PR nem "transferência especial" estadual. Gazeta do Povo: governo do PR teve nota zero em transparência de emendas (2025). TCE-PR IN 200/2025 exige rastreabilidade a partir de 2026.

Exemplos reais (2026, pagas):
- CRISTINA SILVESTRI → Guarapuava → ASSOCIAÇÃO GUARAPUAVANA MUNDO AZUL — R$ 50.000 / pago R$ 50.000.
- ANA JULIA → Mandirituba → ASSOCIACAO BRASILEIRA DE AMPARO A INFANCIA — R$ 50.000 / pago R$ 49.933,80.
- PROFESSOR LEMOS → Nova Fátima → APAE DE NOVA FÁTIMA — R$ 25.000 / pago R$ 24.656,72.

**Dificuldade: 2** para o arquivo (CSV direto), mas cobertura duvidosa (só Sedef/OSC, só 2025–2026). Painel da Sedef inacessível daqui.

---

### SC — Santa Catarina — **Verificado (via API do painel Power BI)**

**Onde está:** SEF-SC https://www.sef.sc.gov.br/transparencias/emendas-parlamentares-estaduais — painéis Power BI:
- "Emendas Parlamentares Estaduais – 2023 em diante" (chave `cd153507-3216-4721-9c42-b900a95507d9`, modelo 7942771, atualizado 23/11/2026). Páginas: Visão Consolidada, Objetos, Conferência LOA, **Visão Transf. Especiais**, Visão Pagamentos.
- Painéis separados 2018, 2019, 2020, 2021, 2022 (links na mesma página; não abri).
- Portarias de transferências especiais: `https://www.sef.sc.gov.br/transparencia/relatorio/117`.
- CKAN `dados.sc.gov.br`: nada de emendas.

Tabelas do modelo: `CadastroEmendasParlamentares` (`num_ano, num_emenda_parlamentar, dsc_objeto, dsc_justificativa, nom_parlamentar, nom_beneficiario, num_documento_beneficiario, nom_tipo_beneficiario, cod_localidade, nom_localidade, Código IBGE, nom_subacao, val_emenda_parlamentar, val_emenda_atualizado, dsc_situacao, Pagamentos, Modalidade Final, Unidade Orçamentária, SGPe, Link SGPe…`) e `ExecucaoEmendasParlamentares` (nível empenho/liquidação/ordem bancária: credor, `val_empenhado`, `val_liquidado`, `val_pago_orcamentario`, município do credor). O modelo também carrega CPF do parlamentar e dados bancários — não copiei.

- Deputado: **sim**.
- Cidade: **sim, código IBGE de 7 dígitos** (`Código IBGE`, ex.: Araranguá 4201406) + nome.
- Beneficiário: **sim** (nome, CNPJ, tipo: Prefeituras/Municípios, Entidade Privada Sem Fins Lucrativos, órgão estadual).
- Valores: indicado (`val_emenda_parlamentar`), atualizado, pago (`Pagamentos`); empenhado/liquidado/pago na tabela de execução.

**Emenda Pix: sim.** `Modalidade Final` = "Município/Transf. Especial" (as outras: Entidade, Órgão Estadual). Impositivas, limite de 1% da RCL (Constituição SC).

Totais (cadastro):

| ano | emendas | indicado | pago | das quais Transf. Especial |
|---|---|---|---|---|
| 2023 | 1.834 | R$ 400 mi | R$ 373 mi | 1.411 / R$ 305 mi |
| 2024 | 2.520 | R$ 459 mi | R$ 425 mi | 1.793 / R$ 333 mi |
| 2025 | 4.161 | R$ 875 mi | R$ 765 mi | 3.075 / R$ 662 mi |
| 2026 | 4.422 | R$ 945 mi | R$ 661 mi | 3.216 / R$ 696 mi |

Exemplos reais (2023):
- Ada Faraco de Luca → Araranguá (4201406) → MUNICIPIO DE ARARANGUA — Transf. Especial — R$ 140.000.
- Ada Faraco de Luca → Balneário Gaivota (4202073) → MUNICIPIO DE BALNEARIO GAIVOTA — Transf. Especial — R$ 140.000.
- Ada Faraco de Luca → Concórdia (4204301) → BENEFICENCIA CAMILIANA DO SUL — Entidade — R$ 3.442.713,01.

**Dificuldade: 3.** Dados ricos (IBGE, deputado, beneficiário, pago, Pix separado), mas só por Power BI; extração em lote pela API pública do painel (~4 mil linhas/ano). 2018–2022 em painéis antigos.

---

### RS — Rio Grande do Sul — **Verificado (via API interna do portal)**

**Onde está:** Portal da Transparência RS https://www.transparencia.rs.gov.br/emendas-parlamentares/emendas-parlamentares-estaduais/dados/
— Power BI embutido (workspace `48138f86-653d-4a67-98d5-4cf00cdbcf4a`, report `a3378ba6-ece3-4d53-80da-f255cf398cba`, atualizado 23/11/2026). A página pede o token em `POST https://www.transparencia.rs.gov.br/umbraco/Surface/PowerBI/Report` (form `workspaceId`, `reportId`) e o painel consulta `wabi-brazil-south-redirect.analysis.windows.net/explore/...` com `Authorization: EmbedToken`. Funcionou sem login.
- `dados.rs.gov.br` (CKAN): **nenhum** conjunto de emendas.
- Os PDFs "emendas Pix" do governo RS (`estado.rs.gov.br/upload/arquivos/202510/balanco-emendas-pix.pdf`, `.../202602/2-relatorio-transferencias-especiais-emendas-pix.pdf`) são sobre **emendas Pix federais**.

Tabelas: `vwEmendasParlamentares` (`Ano, Corede, Orgao, NomeProjeto, Subtitulo, Municipio, CodMunicipio, Valor, Produto, Complemento, Emenda, Deputado, Partido, Obs, CPF/CNPJ, Número Processo, Empenho2…`) e `vwEmendasParlamentaresTrans2` (transações: `TipoTransacaoDesc` = Empenhado/Liquidado/Valor Pago/estornos, `ValorTransacao`, `Credor`, `CNPJ`, `Forma de Repasse` = Convênio/Fundo a Fundo/Parceria/Outros, `URLConvenio`, `DataLancamento`…).

- Deputado: **sim** (+ partido).
- Cidade: **nome**, mas `CodMunicipio` é código interno do estado (ex.: Aceguá = 468), **não IBGE**. R$ 146 mi / 1.710 emendas sem `Municipio` preenchido — nesses o nome da cidade vem no texto de `NomeProjeto` ("Emenda Parlamentar 2021 de Arroio do Tigre"). Há também `Corede` (região).
- Beneficiário: credor na tabela de transações (vi credor com nome de pessoa — existe pessoa física; não anotei).
- Valores: indicado (`Valor`); empenhado, liquidado e pago nas transações.

Totais (indicado, `vwEmendasParlamentares`): 2021 R$ 42,2 mi (370 emendas); 2022 R$ 51,9 mi (681); 2023 R$ 52,0 mi (659); 2024 R$ 110,0 mi (1.196); 2025 R$ 110,0 mi (1.184); 2026 R$ 220,0 mi (2.512). Em 2026 são R$ 4 mi por deputado (55 deputados).
Pago acumulado (todas as emendas, transações "Valor Pago"): ~R$ 404 mi.

**Não impositivas** (há proposta de PEC de impositividade em 2026, não confirmei votação). **Emenda Pix estadual: não encontrada.**

Exemplos reais:
- 2021 — Adolfo Brito (PP) → "Emenda Parlamentar 2021 de Arroio do Tigre" (município só no texto) — emenda 175 — R$ 100.000.
- 2021 — Adolfo Brito → Aceguá aparece na lista de municípios (cod. interno 468; 7 emendas, R$ 700 mil no total da cidade).
- 2022 — Adolfo Brito → credor pessoa física → R$ 50.000 (Forma de Repasse "Outros").
(Não consegui linhas completas deputado+município+beneficiário numa só consulta; precisa juntar as duas tabelas pela `Chave`.)

**Dificuldade: 4.** Só Power BI com token; município sem IBGE e às vezes só no texto; precisa juntar duas tabelas.

---

## O que não consegui abrir
- SP: site da SGRI (Incapsula) e dados abertos da Alesp (TLS); painel 2026 não existe no portal.
- RJ: painel Qlik (não tentei; os CSVs bastam).
- PR: painel da Sedef `social.pr.gov.br/emendas` (conexão recusada/timeout daqui).
- SC: painéis 2018–2022 (existem, não abri).
- MG: `dadosabertos.almg.gov.br` não respondeu (não fez falta).
- ES: não confirmei se a PEC 04/2026 cria transferência especial.
