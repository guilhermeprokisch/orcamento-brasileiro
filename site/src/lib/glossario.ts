/** Termos do orçamento, usados na página Glossário e na "palavra do dia". */
export interface Termo {
  id: string;
  termo: string;
  definicao: string;
}

export const GLOSSARIO: Termo[] = [
  { id: "dotacao", termo: "Dotação", definicao: "Valor autorizado na Lei Orçamentária para uma despesa. A dotação inicial é a aprovada pelo Congresso; a atualizada inclui os créditos e cortes feitos ao longo do ano." },
  { id: "empenho", termo: "Empenho", definicao: "Primeira fase da despesa: o governo reserva parte da dotação para um gasto específico, como um contrato ou convênio. Garante que o dinheiro existe antes de contratar." },
  { id: "liquidacao", termo: "Liquidação", definicao: "Fase em que o governo confere que o bem foi entregue ou o serviço foi prestado, conforme o empenho. Só depois disso a despesa pode ser paga." },
  { id: "pagamento", termo: "Pagamento", definicao: "Última fase da despesa: o dinheiro sai da conta do Tesouro para quem prestou o serviço ou entregou o bem." },
  { id: "restos-a-pagar", termo: "Restos a pagar", definicao: "Despesas empenhadas e não pagas até 31 de dezembro, que passam para o ano seguinte. São processados quando já foram liquidadas e não processados quando ainda não." },
  { id: "loa", termo: "LOA", definicao: "Lei Orçamentária Anual. Aprovada pelo Congresso, estima as receitas e fixa as despesas da União para o ano: nenhum gasto pode ser feito sem estar previsto nela." },
  { id: "credito-adicional", termo: "Crédito adicional", definicao: "Autorização para gastar além do previsto na LOA. Pode ser suplementar (reforça uma dotação), especial (cria uma nova) ou extraordinário (urgências, como calamidades)." },
  { id: "contingenciamento", termo: "Contingenciamento", definicao: "Bloqueio temporário de parte das despesas não obrigatórias, feito quando a arrecadação fica abaixo do previsto, para cumprir as metas fiscais." },
  { id: "gnd", termo: "Grupo de natureza da despesa", definicao: "Classificação que diz em que tipo de gasto o dinheiro vai: pessoal, juros da dívida, outras despesas correntes, investimentos, inversões financeiras ou amortização." },
  { id: "unidade-orcamentaria", termo: "Unidade orçamentária", definicao: "Parte de um órgão que recebe dotações próprias no orçamento. O Fundo Nacional de Saúde, por exemplo, é uma unidade do Ministério da Saúde." },
  { id: "funcao", termo: "Função e subfunção", definicao: "Classificam a despesa pela área de governo. A função é o nível mais amplo (saúde, educação); a subfunção detalha (atenção básica, ensino superior)." },
  { id: "refinanciamento", termo: "Refinanciamento da dívida", definicao: "Emissão de títulos novos para pagar títulos que estão vencendo. Aparece como despesa no orçamento, mas é a rolagem da dívida, não um gasto novo." },
  { id: "reserva-de-contingencia", termo: "Reserva de contingência", definicao: "Dotação sem destino específico, guardada para cobrir riscos fiscais e despesas imprevistas ao longo do ano." },
  { id: "ppa", termo: "PPA", definicao: "Plano Plurianual. Lei que define os programas e objetivos do governo para quatro anos, do segundo ano de um mandato até o primeiro ano do mandato seguinte." },
  { id: "ldo", termo: "LDO", definicao: "Lei de Diretrizes Orçamentárias. Aprovada todo ano antes da LOA, fixa as metas fiscais e as regras para elaborar e executar o orçamento do ano seguinte." },
  { id: "programa", termo: "Programa", definicao: "Conjunto de ações com um objetivo comum, definido no PPA. O Bolsa Família e a Atenção Primária à Saúde são programas." },
  { id: "acao", termo: "Ação orçamentária", definicao: "Menor nível da programação do orçamento: a atividade, projeto ou operação concreta que recebe a dotação, como um benefício, uma obra ou a manutenção de um órgão." },
  { id: "despesa-obrigatoria", termo: "Despesa obrigatória", definicao: "Gasto que o governo tem de fazer por força da Constituição ou de uma lei, como aposentadorias, salários de servidores e transferências a estados e municípios." },
  { id: "despesa-discricionaria", termo: "Despesa discricionária", definicao: "Gasto que o governo pode escolher fazer ou não, e em que valor, como investimentos e boa parte do custeio. É onde caem os contingenciamentos." },
  { id: "despesa-financeira", termo: "Despesa financeira", definicao: "Gasto que fica fora da conta do resultado primário: os juros e as parcelas da dívida pública, a rolagem dela (o refinanciamento) e os empréstimos que o governo faz e depois recebe de volta, como o Fies." },
  { id: "identificador-resultado-primario", termo: "Identificador de resultado primário", definicao: "Marca que cada linha do orçamento federal recebe para dizer se a despesa é obrigatória, discricionária (escolha do governo), emenda parlamentar ou financeira. É com ela que se separa o que o governo pode cortar do que a lei manda pagar." },
  { id: "resultado-primario", termo: "Resultado primário", definicao: "Receitas menos despesas do governo, sem contar os juros da dívida. Quando é positivo, chama-se superávit primário; quando é negativo, déficit primário." },
  { id: "arcabouco-fiscal", termo: "Arcabouço fiscal", definicao: "Nome popular do Regime Fiscal Sustentável (Lei Complementar 200/2023), que substituiu o teto de gastos: limita o crescimento da despesa e fixa metas de resultado primário." },
  { id: "regra-de-ouro", termo: "Regra de ouro", definicao: "Regra da Constituição que proíbe o governo de se endividar para pagar despesas correntes, como salários e custeio, salvo com autorização específica do Congresso." },
  { id: "ipca", termo: "IPCA", definicao: "Índice de preços ao consumidor medido pelo IBGE, usado como a inflação oficial do país. O site usa o IPCA para corrigir valores de anos diferentes." },
  { id: "tcu", termo: "TCU", definicao: "Tribunal de Contas da União. Órgão que auxilia o Congresso a fiscalizar o uso do dinheiro federal: julga contas, faz auditorias e emite parecer sobre as contas do presidente." },
  { id: "lai", termo: "Lei de Acesso à Informação", definicao: "Lei 12.527/2011. Garante a qualquer pessoa o direito de pedir informações a órgãos públicos, sem precisar justificar o pedido." },
  { id: "emenda-parlamentar", termo: "Emenda parlamentar", definicao: "Mudança proposta por deputados e senadores no projeto da LOA, em geral para destinar recursos a obras e serviços em estados e municípios." },
  { id: "emenda-individual", termo: "Emenda individual", definicao: "A cota de cada deputado e senador no orçamento: todos têm o mesmo valor e escolhem para onde vai. Pela Constituição, metade tem de ir para a saúde, e o governo é obrigado a pagar." },
  { id: "emenda-de-bancada", termo: "Emenda de bancada", definicao: "Emenda que os deputados e senadores de um mesmo estado indicam juntos, em geral para obras maiores no próprio estado. Também é de pagamento obrigatório." },
  { id: "emenda-de-comissao", termo: "Emenda de comissão", definicao: "Emenda indicada por uma comissão da Câmara ou do Senado (de saúde, de agricultura…). Não é de pagamento obrigatório e cresceu muito a partir de 2024, depois do fim das emendas de relator." },
  { id: "emenda-de-relator", termo: "Emenda de relator", definicao: "Emenda feita pelo relator-geral do orçamento. De 2020 a 2022 virou um caminho para deputados e senadores mandarem dinheiro sem aparecer o nome de quem pediu, o “orçamento secreto”. O Supremo a proibiu nesse formato em dezembro de 2022." },
  { id: "emenda-pix", termo: "Emenda Pix", definicao: "Nome popular da transferência especial: uma emenda individual que cai direto no caixa da prefeitura ou do estado, sem um convênio que diga em que será gasta. Existe desde 2020; o Supremo passou a exigir um plano de uso e a prestação de contas." },
  { id: "emenda-impositiva", termo: "Emenda impositiva", definicao: "Emenda que o governo é obrigado a pagar, salvo um impedimento técnico. Valem assim as individuais (desde 2015) e as de bancada (desde 2019), até um limite ligado à receita corrente líquida da União." },
  { id: "receita-corrente-liquida", termo: "Receita corrente líquida", definicao: "A receita do dia a dia de um governo (impostos, repasses, contribuições), tirando o que ele só repassa adiante, como a parte dos impostos que vai para as prefeituras. É a base dos limites da Lei de Responsabilidade Fiscal." },
  { id: "lrf", termo: "Lei de Responsabilidade Fiscal", definicao: "Lei Complementar 101/2000. Fixa limites para o gasto com pessoal e para a dívida de União, estados e prefeituras, e obriga a publicar relatórios das contas a cada quatro meses." },
  { id: "divida-consolidada-liquida", termo: "Dívida consolidada líquida", definicao: "Tudo o que um governo deve a prazo maior que um ano (empréstimos, precatórios, parcelamentos), menos o dinheiro que tem em caixa e aplicações." },
  { id: "precatorio", termo: "Precatório", definicao: "Dívida de um governo reconhecida pela Justiça, depois de uma ação que ele perdeu. Entra numa fila e é paga pelo orçamento dos anos seguintes." },
  { id: "limite-prudencial", termo: "Limite prudencial", definicao: "95% do limite de gasto com pessoal. Quem passa dele não pode dar aumento, criar cargos nem contratar, com exceções como a reposição de professores e profissionais de saúde." },
  { id: "capag", termo: "CAPAG", definicao: "Capacidade de pagamento: a nota que o Tesouro Nacional dá às contas de estados e prefeituras, de A a D. Com nota A ou B, o governo pode pegar empréstimo com a União como garantidora." },
  { id: "rpps", termo: "Regime próprio de previdência", definicao: "O fundo que uma prefeitura ou um estado mantém para pagar a aposentadoria e a pensão dos seus servidores concursados, em vez de deixá-los no INSS. Recebe a contribuição dos servidores e do governo e deveria guardar dinheiro para os benefícios futuros. Todos os estados e pouco mais de 2.100 das 5.569 prefeituras têm um." },
  { id: "deficit-atuarial", termo: "Déficit atuarial", definicao: "Quanto falta no fundo de aposentadoria dos servidores para pagar tudo o que já foi prometido: o valor de hoje das aposentadorias e pensões futuras, menos o dinheiro guardado. É uma projeção de décadas, feita por um atuário com premissas (os juros que o dinheiro vai render, os salários, quanto tempo as pessoas vivem) que mudam bastante o resultado." },
  { id: "isp", termo: "ISP", definicao: "Índice de Situação Previdenciária: a nota, de A a D, que o Ministério da Previdência dá todo ano ao fundo de aposentadoria dos servidores de cada prefeitura e estado. Junta a gestão e a transparência, as finanças (o que entra, o que sai e o que fica guardado) e a situação atuarial." },
  { id: "teto-constitucional", termo: "Teto constitucional", definicao: "O máximo que alguém pode receber no serviço público por mês, pela Constituição (art. 37, XI): o salário de um ministro do Supremo Tribunal Federal, R$ 46.366,19 desde fevereiro de 2025. O que passa disso deveria ser cortado no contracheque (o abate-teto), mas as verbas chamadas de indenizatórias ficam fora da conta." },
  { id: "subsidio", termo: "Subsídio", definicao: "O salário fixo, numa parcela só, de juízes, promotores, procuradores, ministros e outros cargos do topo do serviço público. A Constituição proíbe somar a ele gratificações e adicionais, mas permite as verbas indenizatórias." },
  { id: "verba-indenizatoria", termo: "Verba indenizatória", definicao: "Pagamento que, pela lei, devolve um gasto ou compensa um direito não usado (um auxílio, férias não tiradas, uma licença convertida em dinheiro), e não é salário. Por isso não paga imposto de renda e fica fora do teto constitucional. É por ela que passa quase todo o pagamento acima do teto." },
  { id: "licenca-compensatoria", termo: "Licença compensatória", definicao: "Folga dada a juízes e promotores por acumular trabalho (um acervo grande, plantões, mais de uma vara). Quase sempre a folga não é tirada e vira dinheiro, pago como indenização e, por isso, fora do teto." },
  { id: "plano-financeiro", termo: "Plano financeiro", definicao: "Parte do fundo de aposentadoria dos servidores em que não se guarda dinheiro: as aposentadorias de cada ano saem das contribuições e do caixa do governo do mesmo ano. Costuma reunir os servidores mais antigos, quando o governo separa os grupos para juntar dinheiro só para os mais novos." },
  { id: "fpm", termo: "FPM", definicao: "Fundo de Participação dos Municípios: a parte do imposto de renda e do IPI arrecadados pela União que a Constituição manda dividir entre as prefeituras. É a maior fonte de dinheiro de muitas cidades pequenas." },
  { id: "fpe", termo: "FPE", definicao: "Fundo de Participação dos Estados: a parte do imposto de renda e do IPI arrecadados pela União (21,5%) que a Constituição manda dividir entre os estados e o Distrito Federal, mais para os do Norte, do Nordeste e do Centro-Oeste." },
  { id: "fundos-regionais", termo: "Fundos regionais", definicao: "Os fundos constitucionais do Norte (FNO), do Nordeste (FNE) e do Centro-Oeste (FCO), que recebem 3% do imposto de renda e do IPI. Não são governos: bancos públicos emprestam esse dinheiro, com juros menores, a empresas e produtores dessas regiões." },
  { id: "royalties", termo: "Royalties", definicao: "O que as empresas pagam ao país para tirar petróleo, gás e minérios. Não é imposto, mas a lei manda dividir o dinheiro entre a União, os estados e as cidades onde há produção." },
  { id: "beneficio-fiscal", termo: "Benefício fiscal", definicao: "Imposto que o governo deixa de cobrar de propósito, com isenções, deduções e regimes especiais, como o Simples Nacional e a Zona Franca de Manaus. A Receita Federal chama de gasto tributário: é como uma despesa que não passa pelo orçamento." },
  { id: "fundeb", termo: "FUNDEB", definicao: "Fundo da educação básica. Junta parte dos impostos de estados e prefeituras e redistribui pelo número de alunos de cada rede; a União completa onde o valor por aluno fica abaixo do mínimo." },
  { id: "icms", termo: "ICMS", definicao: "Imposto estadual embutido no preço das mercadorias, da luz, do combustível e de alguns serviços. Um quarto do que o estado arrecada vai para as prefeituras." },
  { id: "ipva", termo: "IPVA", definicao: "Imposto estadual sobre carros e motos, pago pelo dono todo ano. Metade fica com a prefeitura da cidade onde o veículo está registrado." },
  { id: "iss", termo: "ISS", definicao: "Imposto sobre serviços, cobrado pela prefeitura de empresas e profissionais que prestam serviços na cidade." },
  { id: "iptu", termo: "IPTU", definicao: "Imposto sobre imóveis urbanos, cobrado pela prefeitura do dono de casas, apartamentos, lojas e terrenos na cidade." },
  { id: "itbi", termo: "ITBI", definicao: "Imposto que a prefeitura cobra quando um imóvel é vendido, pago por quem compra." },
  { id: "pdde", termo: "PDDE", definicao: "Programa Dinheiro Direto na Escola: dinheiro federal que vai direto para o conselho ou a caixa escolar de cada escola pública, sem passar pela prefeitura, para pequenas compras, reparos e projetos." },
  { id: "ideb", termo: "Ideb", definicao: "Índice de Desenvolvimento da Educação Básica, do INEP. Junta a nota dos alunos numa prova nacional com a taxa de aprovação, numa escala de 0 a 10. Sai a cada dois anos." },
  { id: "pncp", termo: "PNCP", definicao: "Portal Nacional de Contratações Públicas, onde União, estados e prefeituras devem publicar licitações e contratos desde a nova lei de licitações (Lei 14.133/2021)." },
  { id: "credenciamento", termo: "Credenciamento", definicao: "Contratação em que o governo aceita todos os fornecedores que cumprem as condições, como clínicas para exames. O valor publicado é o máximo que se pode gastar, não o gasto." },
  { id: "cota-parlamentar", termo: "Cota parlamentar", definicao: "Dinheiro para os gastos do mandato, como passagens, combustível, aluguel de escritório e divulgação. É um reembolso: o deputado ou senador gasta, apresenta a nota fiscal e a Casa devolve, até um teto mensal que muda de estado para estado. O nome oficial é CEAP na Câmara e CEAPS no Senado." },
  { id: "verba-de-gabinete", termo: "Verba de gabinete", definicao: "Dinheiro que cada deputado federal tem para pagar os secretários parlamentares, os assessores que ele mesmo escolhe, até 25 pessoas. Não vai para o bolso do deputado: é a folha de pagamento do gabinete." },
  { id: "eleito-por-qp", termo: "Eleito por QP", definicao: "Eleito pelo quociente partidário. Nas eleições para deputado, cada partido ganha um número de cadeiras conforme os votos de todos os seus candidatos. Quem é eleito por QP ocupou uma dessas cadeiras por ter estado entre os mais votados do partido." },
  { id: "eleito-por-media", termo: "Eleito por média", definicao: "Eleito na divisão das sobras. Depois de distribuir as cadeiras pelo quociente partidário, as que sobram vão aos partidos com as maiores médias de votos por cadeira. Quem é eleito por média ficou com uma dessas cadeiras." },
  { id: "fundo-eleitoral", termo: "Fundo eleitoral", definicao: "Dinheiro público para as campanhas, criado em 2017 depois que as empresas foram proibidas de doar. O nome oficial é Fundo Especial de Financiamento de Campanha (FEFC). Cada partido recebe uma parte e decide quanto vai para cada candidato." },
  { id: "fundo-partidario", termo: "Fundo partidário", definicao: "Dinheiro público que os partidos recebem todo ano para se manter. Parte dele pode ir para as campanhas dos candidatos." },
  { id: "mediana", termo: "Mediana", definicao: "O valor do meio: metade das cidades (ou dos estados) fica acima dele e metade abaixo. Diferente da média, não é puxada por uns poucos casos muito altos ou muito baixos." },
  { id: "titulo-publico", termo: "Título público", definicao: "Papel que o governo vende para pegar dinheiro emprestado. Quem compra empresta ao governo e recebe o valor de volta, com juros, numa data marcada: o vencimento." },
  { id: "divida-publica-federal", termo: "Dívida pública federal", definicao: "Tudo o que o governo federal deve a quem lhe emprestou: os títulos públicos vendidos no país e no exterior e os contratos com bancos e organismos internacionais. Não conta os títulos que estão com o Banco Central." },
  { id: "dbgg", termo: "Dívida bruta do governo geral", definicao: "Conta do Banco Central que soma as dívidas do governo federal, dos estados e das prefeituras, mais os títulos que o Banco Central usa para controlar os juros. É a medida usada para comparar países." },
  { id: "selic", termo: "Selic", definicao: "A taxa básica de juros da economia, decidida pelo Banco Central a cada 45 dias. Quando ela sobe, o crédito fica mais caro e a parte da dívida federal ligada a ela passa a pagar mais juros." },
  { id: "bpc", termo: "BPC", definicao: "Benefício de Prestação Continuada: um salário mínimo por mês, pago pelo governo federal a idosos com 65 anos ou mais e a pessoas com deficiência de família pobre, mesmo sem nunca terem contribuído para o INSS." },
  { id: "pib", termo: "PIB", definicao: "Produto Interno Bruto: o valor de tudo o que o país produz em um ano. Dividir a dívida pelo PIB mostra o tamanho dela frente à economia, sem o efeito da inflação." },
  { id: "prefixado", termo: "Título prefixado", definicao: "Título com juros combinados na venda, que não mudam até o vencimento. Quem compra sabe desde o começo quanto vai receber." },
  { id: "tesouro-direto", termo: "Tesouro Direto", definicao: "Programa do Tesouro Nacional que vende títulos públicos a pessoas, pela internet, por meio de bancos e corretoras." },
  { id: "prazo-medio", termo: "Prazo médio da dívida", definicao: "Quanto tempo falta, em média, para a dívida vencer. Um prazo longo dá mais tempo ao governo e o deixa menos exposto a momentos de juros altos." },
  { id: "custo-medio", termo: "Custo médio da dívida", definicao: "Os juros que a dívida rendeu a quem emprestou nos últimos 12 meses, em porcentagem do valor devido: a taxa média que o governo paga." },
  { id: "juros-nominais", termo: "Juros nominais", definicao: "Todos os juros que a dívida acumulou no período, pagos ou não, inclusive a parte que só repõe a inflação. É a conta do Banco Central para o custo da dívida." },
  { id: "resultado-nominal", termo: "Resultado nominal", definicao: "Receitas menos despesas do governo, contando os juros da dívida. Quando é negativo (déficit nominal), o governo precisa pegar emprestado a diferença, e a dívida cresce." },
  { id: "setor-publico-consolidado", termo: "Setor público consolidado", definicao: "A conta do Banco Central que junta o governo federal, os estados, as prefeituras e as estatais (menos Petrobras, Eletrobras e os bancos públicos), sem contar duas vezes o dinheiro que passa de um para outro." },
  { id: "governo-central", termo: "Governo central", definicao: "O governo federal (Tesouro Nacional e INSS) junto com o Banco Central. É a parte do setor público que segue a meta de resultado primário do arcabouço fiscal." },
  { id: "balanco-patrimonial", termo: "Balanço patrimonial", definicao: "O retrato das contas no último dia do ano: o que o governo tem (dinheiro, aplicações, imóveis) e o que deve (fornecedores, empréstimos, aposentadorias futuras)." },
  { id: "obra-paralisada", termo: "Obra paralisada", definicao: "Obra que começou e não anda: ficou sem medição, foi abandonada pela empresa, teve o contrato rompido ou foi declarada parada por quem a acompanha. O TCU junta as obras com dinheiro federal das bases do governo e aplica um critério próprio, que nem sempre é o do órgão." },
  { id: "valor-liberado", termo: "Valor liberado", definicao: "O dinheiro federal que já saiu para a obra (o TCU chama de valor desbloqueado). Parte dele pode ter virado obra que ainda dá para terminar; parte pode ser devolvida." },
  { id: "execucao-fisica", termo: "Execução física", definicao: "Quanto da obra já foi construído, em percentual, segundo a última medição informada por quem a acompanha. Não é o mesmo que o dinheiro já pago." },
  { id: "pacto-retomada", termo: "Pacto de retomada", definicao: "Lei de 2023 (Lei 14.719) que permite à prefeitura ou ao estado repactuar com o governo federal obras paradas de educação e saúde, com valores atualizados, para terminá-las." },
  { id: "convenio", termo: "Convênio", definicao: "Acordo em que o governo federal passa dinheiro a uma prefeitura, um estado ou uma entidade para fazer uma obra ou um serviço. Quando é a Caixa que acompanha a obra, chama-se contrato de repasse. O dinheiro vai para uma conta da obra e sai dela conforme a obra anda." },
  { id: "saldo-em-conta", termo: "Saldo em conta", definicao: "O dinheiro que está parado na conta bancária do convênio: o que a União depositou e ainda não foi gasto, mais a parte da prefeitura (a contrapartida) e os rendimentos. Numa obra parada, é dinheiro que não virou obra." },
  { id: "divida-ativa", termo: "Dívida ativa", definicao: "O que empresas e pessoas devem ao governo e não pagaram no prazo, depois de esgotada a cobrança comum. Na União, a Procuradoria-Geral da Fazenda Nacional inscreve a dívida numa lista e passa a cobrá-la, inclusive na Justiça. Boa parte é de empresas que já fecharam e nunca vai ser paga." },
  { id: "tlp", termo: "TLP", definicao: "Taxa de Longo Prazo, o juro básico da maior parte dos empréstimos do BNDES desde 2018. Segue o juro que o próprio governo paga quando pega dinheiro emprestado por muitos anos (o título do Tesouro corrigido pela inflação). Substituiu a TJLP, que era fixada pelo governo abaixo desse custo." },
  { id: "tjlp", termo: "TJLP", definicao: "Taxa de Juros de Longo Prazo, o juro dos empréstimos do BNDES até 2017. Era fixada pelo governo, quase sempre abaixo do que o Tesouro pagava para se financiar; a diferença era um subsídio. Foi trocada pela TLP em 2018." },
  { id: "equalizacao", termo: "Equalização de juros", definicao: "Quando o banco empresta a juro baixo (no Plano Safra, por exemplo) e o Tesouro paga ao banco a diferença até o juro de mercado. É dinheiro que sai do orçamento todo ano, enquanto o empréstimo durar." },
  { id: "subsidio-crediticio", termo: "Subsídio de crédito", definicao: "O custo, para o governo, de emprestar mais barato do que ele mesmo paga para pegar dinheiro. Não é o valor emprestado, que volta com juros: é a diferença de juros. O Ministério do Planejamento calcula esse custo todo ano no Orçamento de Subsídios da União." },
  { id: "estatal-dependente", termo: "Estatal dependente", definicao: "Empresa do governo que precisa do dinheiro do Tesouro para pagar salários e o dia a dia, como a Ebserh (hospitais universitários) e a Embrapa (pesquisa). Entra no orçamento como um órgão. As outras estatais, como Petrobras e Banco do Brasil, vivem da própria receita e pagam dividendos à União." },
  { id: "operacao-indireta", termo: "Operação indireta", definicao: "Empréstimo do BNDES que passa por um banco (Itaú, Bradesco, Banco do Brasil, cooperativas, bancos de montadora). O BNDES põe o dinheiro; o banco escolhe o cliente, cobra a parte dele e fica com o risco de não receber." },
];

/** Termo do dia, escolhido pela data (o site é gerado de novo todo dia). */
export function palavraDoDia(data = new Date()): Termo {
  const dia = Math.floor(data.getTime() / 86_400_000);
  return GLOSSARIO[dia % GLOSSARIO.length];
}

const PORID = new Map(GLOSSARIO.map((t) => [t.id, t]));
/** O termo pelo id; erro no build se o id não existir, para não sair um balão vazio. */
export function termoPorId(id: string): Termo {
  const t = PORID.get(id);
  if (!t) throw new Error(`glossário: termo "${id}" não existe`);
  return t;
}

const ESC: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ESC[c]);
/**
 * O mesmo balão do componente Termo.astro, como HTML, para os textos montados em string
 * (lib/ficha-html.ts). `texto` é o que aparece sublinhado; o padrão é o nome do termo.
 */
let contador = 0;
/** Um id único para cada balão da página (o mesmo termo pode aparecer em mais de uma seção). */
export const idBalao = (id: string) => `balao-${id}-${++contador}`;

export function termoHtml(id: string, texto?: string): string {
  const t = termoPorId(id), b = idBalao(id);
  return `<span class="termo" tabindex="0" aria-describedby="${b}">${esc(texto ?? t.termo)}<span class="balao" role="tooltip" id="${b}"><strong>${esc(t.termo)}.</strong> ${esc(t.definicao)} <a href="/glossario#${esc(id)}">Glossário →</a></span></span>`;
}
