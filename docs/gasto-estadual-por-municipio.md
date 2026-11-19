# Quanto o governo do estado gasta em cada município: o que cada estado publica

A prestação de contas dos estados ao Tesouro diz quanto cada um gastou por área, mas não em
qual cidade. Esta página resume uma pesquisa, feita em 19/11/2026, sobre quais estados publicam
esse dado por algum caminho: nota de empenho, folha de pagamento com lotação, obras, convênios,
orçamento regionalizado, Tribunais de Contas.

Não confundir com os **repasses do estado à prefeitura** (parte do ICMS e do IPVA, convênios):
esses já estão no site para todas as cidades, pela prestação de contas de quem recebe. O que
falta é o gasto que o estado faz ele mesmo na cidade: escola estadual, hospital regional,
polícia, estrada.

**Grau de confiança.** Paraíba e Minas Gerais foram conferidas baixando os dados e somando, e já
estão no site. Todo o resto vem dos quatro relatórios em
[pesquisa-gasto-estadual/](pesquisa-gasto-estadual/), que marcam cada achado como "verificado"
(o dado foi aberto e o campo, visto), "descrito mas não aberto" ou "não encontrado". Antes de
escrever o extrator de um estado, o primeiro passo é repetir a verificação.

## Os 27, do melhor ao pior

### Gasto inteiro por município (2)

| UF | Caminho | Observação |
|---|---|---|
| PB | API aberta, município em cada empenho | No site. A folha fica na sede do órgão |
| MG | Execução do plano plurianual por município, 2012+ | No site. Informado pelos órgãos; 2024 incompleto na fonte |

### Folha de pagamento com cidade ou unidade (9)

Salário é mais da metade do gasto estadual, então isso já responde boa parte da pergunta, e
chega no nível da escola e do hospital.

| UF | O que tem | Falta |
|---|---|---|
| PR | Folha com município e lotação (escola), desde 2012, em arquivo | Nada; é o caso mais limpo |
| SC | Folha por unidade e cidade, inclusive polícia e bombeiros; obras com rateio por município | Extrair a cidade do nome da unidade |
| SP | Município do servidor num arquivo; salário em outro | Cruzar os dois (não testado) |
| RJ | Folha por unidade, em API | Tabela unidade → município |
| ES | Folha de educação e saúde por escola e hospital; obras e convênios com município | Polícias só por órgão |
| BA | Folha por unidade, mês a mês desde 2019 | Tabela unidade → município; junção não testada |
| SE | Folha com lotação e obras com município, por API | Obras só de uma secretaria |
| AM | Folha por unidade (escola, saúde, quartel), em API; obras com valor por município | Tabela unidade → município |
| GO | Folha por unidade; mapa de obras de quase todos os órgãos; merenda por escola | Tabela unidade → município |

Onde falta a "tabela unidade → município", o caminho é casar o nome da escola com o Censo
Escolar e o do hospital com o cadastro do SUS (CNES).

### Só obras ou convênios com município (9)

| UF | O que tem |
|---|---|
| PE | Obras com município (2020+); repasses a hospitais geridos por organizações sociais |
| MA | Obras da Secretaria de Infraestrutura (27% com local genérico) |
| PI | Obras, com o município no texto; painel do TCE-PI com filtro por município |
| MT | Obras de infraestrutura (mesma API do AM); convênios |
| AC | Obras com município e valor pago |
| RR | Obras com município (só tela) |
| PA | Obras 2009–2024, com região e município (qualidade duvidosa) |
| RS | Convênios com prefeituras |
| RO | Convênios e transferências voluntárias |

### Quase nada (7)

| UF | Situação |
|---|---|
| CE | Região administrativa no empenho. Existe uma página "Investimentos por município" que não foi aberta: o portal bloqueou o acesso automatizado. Vale abrir num navegador comum |
| MS | Só emendas parlamentares estaduais por município |
| AL | Só região de planejamento (88% num código só) |
| DF | 3% do empenhado tem região administrativa; 94% é "Distrito Federal" |
| AP | Painel de obras sem coluna de município |
| RN | Nenhum caminho verificado |
| TO | Nenhum caminho encontrado |

## Campos que parecem servir e não servem

- **Município do credor**: em vários estados (RS, BA nas obras, PI nos contratos) o campo é a
  cidade de quem recebeu ou a sede do órgão, não onde o dinheiro foi aplicado.
- **Local de entrega** (AL, DF): texto livre, com endereços e siglas.
- **Região** (ES, AL, AM, DF): quase tudo cai no código "estado inteiro".

## E para os estados que não publicam: estimar

Nenhuma base nacional mede o gasto estadual por município, e a pesquisa não achou estudo que
já o tenha estimado para o país. Dá para estimar por partes
([detalhes](pesquisa-gasto-estadual/fontes-nacionais.md)):

| Parte do gasto estadual | Peso | Como repartir | Qualidade |
|---|---|---|---|
| Repasses às prefeituras | ~10% | O que cada prefeitura declara ter recebido | Medido (já no site) |
| Educação | 16% | Matrículas da rede estadual por município (Censo Escolar) | Boa estimativa |
| Saúde | 14% | Unidades estaduais por município (CNES) e produção hospitalar | Boa estimativa |
| Segurança | 10% | Não há efetivo por município publicado; só presídios | Fraca |
| Obras | ~7% | Só as com recurso federal estão em base nacional | Parcial |
| Justiça, administração e outros | 25% | Registros de emprego público, que concentram na capital | Fraca |
| Aposentadorias e dívida | 23% | Não distribuível | Sem método |

Estimativa razoável para cerca de 40% do gasto, fraca para 35%, nenhuma para 23%. Duas
decisões de método:

- **Não somar tudo num número só por cidade.** Cada parte aparece com o seu rótulo (medido,
  estimado, não distribuível).
- **Paraíba e Minas são a régua.** Onde existe o dado real, aplica-se a estimativa e mede-se o
  erro antes de usar nos outros estados.

Pista ainda não confirmada: uma base do FNDE (SIOPE) teria a remuneração de cada profissional
por escola, inclusive na rede estadual. Se existir, a folha da educação passa de estimada a
medida no país inteiro. O serviço estava fora do ar na pesquisa.

## O que fazer com isso

1. **Extratores, na ordem do retorno**: PR e SC (folha com cidade, sem cruzamento); GO, AM e MT
   (obras; AM e MT usam a mesma API); depois SE, ES, RJ, BA e SP, que pedem casar unidades com
   escolas e hospitais.
2. **Estimativa nacional** para educação e saúde, validada na Paraíba e em Minas.
3. **Página "quem publica onde gasta"**: os 27 estados nas quatro faixas acima. Mostra que
   é possível (dois fazem) e quem não faz.
4. **Pedidos pela Lei de Acesso à Informação**, só para o que não existe:
   - aos estados das duas últimas faixas, a despesa por município de aplicação e a folha somada
     por município de lotação, sem nomes;
   - a SP, RJ, BA, AM e GO, a tabela de unidades com o município de cada uma;
   - ao Ministério da Justiça, o efetivo policial por município, que já é coletado e só é
     publicado por estado;
   - ao FNDE, a remuneração por escola da rede estadual, somada.

## Cuidados

- Os arquivos de folha trazem o nome de cada servidor. O pipeline soma por cidade e por unidade
  e não guarda nem publica nomes, como já faz com o Bolsa Família.
- Vários portais bloqueiam acesso automatizado depois de poucas requisições (CE, GO) ou pedem
  captcha (MT na folha). Não contornamos bloqueio: onde não abre, fica registrado como não
  aberto.
