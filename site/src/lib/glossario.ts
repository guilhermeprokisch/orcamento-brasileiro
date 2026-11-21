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
  { id: "resultado-primario", termo: "Resultado primário", definicao: "Receitas menos despesas do governo, sem contar os juros da dívida. Quando é positivo, chama-se superávit primário; quando é negativo, déficit primário." },
  { id: "arcabouco-fiscal", termo: "Arcabouço fiscal", definicao: "Nome popular do Regime Fiscal Sustentável (Lei Complementar 200/2023), que substituiu o teto de gastos: limita o crescimento da despesa e fixa metas de resultado primário." },
  { id: "regra-de-ouro", termo: "Regra de ouro", definicao: "Regra da Constituição que proíbe o governo de se endividar para pagar despesas correntes, como salários e custeio, salvo com autorização específica do Congresso." },
  { id: "ipca", termo: "IPCA", definicao: "Índice de preços ao consumidor medido pelo IBGE, usado como a inflação oficial do país. O site usa o IPCA para corrigir valores de anos diferentes." },
  { id: "tcu", termo: "TCU", definicao: "Tribunal de Contas da União. Órgão que auxilia o Congresso a fiscalizar o uso do dinheiro federal: julga contas, faz auditorias e emite parecer sobre as contas do presidente." },
  { id: "lai", termo: "Lei de Acesso à Informação", definicao: "Lei 12.527/2011. Garante a qualquer pessoa o direito de pedir informações a órgãos públicos, sem precisar justificar o pedido." },
  { id: "emenda-parlamentar", termo: "Emenda parlamentar", definicao: "Mudança proposta por deputados e senadores no projeto da LOA, em geral para destinar recursos a obras e serviços em estados e municípios." },
  { id: "receita-corrente-liquida", termo: "Receita corrente líquida", definicao: "A receita do dia a dia de um governo (impostos, repasses, contribuições), tirando o que ele só repassa adiante, como a parte dos impostos que vai para as prefeituras. É a base dos limites da Lei de Responsabilidade Fiscal." },
  { id: "lrf", termo: "Lei de Responsabilidade Fiscal", definicao: "Lei Complementar 101/2000. Fixa limites para o gasto com pessoal e para a dívida de União, estados e prefeituras, e obriga a publicar relatórios das contas a cada quatro meses." },
  { id: "divida-consolidada-liquida", termo: "Dívida consolidada líquida", definicao: "Tudo o que um governo deve a prazo maior que um ano (empréstimos, precatórios, parcelamentos), menos o dinheiro que tem em caixa e aplicações." },
  { id: "precatorio", termo: "Precatório", definicao: "Dívida de um governo reconhecida pela Justiça, depois de uma ação que ele perdeu. Entra numa fila e é paga pelo orçamento dos anos seguintes." },
  { id: "limite-prudencial", termo: "Limite prudencial", definicao: "95% do limite de gasto com pessoal. Quem passa dele não pode dar aumento, criar cargos nem contratar, com exceções como a reposição de professores e profissionais de saúde." },
  { id: "capag", termo: "CAPAG", definicao: "Capacidade de pagamento: a nota que o Tesouro Nacional dá às contas de estados e prefeituras, de A a D. Com nota A ou B, o governo pode pegar empréstimo com a União como garantidora." },
  { id: "fpm", termo: "FPM", definicao: "Fundo de Participação dos Municípios: a parte do imposto de renda e do IPI arrecadados pela União que a Constituição manda dividir entre as prefeituras. É a maior fonte de dinheiro de muitas cidades pequenas." },
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
  { id: "mediana", termo: "Mediana", definicao: "O valor do meio: metade das cidades (ou dos estados) fica acima dele e metade abaixo. Diferente da média, não é puxada por uns poucos casos muito altos ou muito baixos." },
  { id: "titulo-publico", termo: "Título público", definicao: "Papel que o governo vende para pegar dinheiro emprestado. Quem compra empresta ao governo e recebe o valor de volta, com juros, numa data marcada: o vencimento." },
  { id: "divida-publica-federal", termo: "Dívida pública federal", definicao: "Tudo o que o governo federal deve a quem lhe emprestou: os títulos públicos vendidos no país e no exterior e os contratos com bancos e organismos internacionais. Não conta os títulos que estão com o Banco Central." },
  { id: "dbgg", termo: "Dívida bruta do governo geral", definicao: "Conta do Banco Central que soma as dívidas do governo federal, dos estados e das prefeituras, mais os títulos que o Banco Central usa para controlar os juros. É a medida usada para comparar países." },
  { id: "selic", termo: "Selic", definicao: "A taxa básica de juros da economia, decidida pelo Banco Central a cada 45 dias. Quando ela sobe, o crédito fica mais caro e a parte da dívida federal ligada a ela passa a pagar mais juros." },
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
