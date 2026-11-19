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
];

/** Termo do dia, escolhido pela data (o site é gerado de novo todo dia). */
export function palavraDoDia(data = new Date()): Termo {
  const dia = Math.floor(data.getTime() / 86_400_000);
  return GLOSSARIO[dia % GLOSSARIO.length];
}
