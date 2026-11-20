/**
 * Quem publica onde gasta: os 27 estados pela transparência do gasto em cada município.
 * Duas perguntas, de duas pesquisas:
 * - o governo do estado publica quanto gastou em cada cidade? (docs/gasto-estadual-por-municipio.md,
 *   pesquisa de 19/11/2026, com os relatórios em docs/pesquisa-gasto-estadual/)
 * - o Tribunal de Contas publica, para baixar, os pagamentos de todas as prefeituras do estado?
 *   (docs/levantamento-pagamentos-tce.md, 20/11/2026)
 * Tabela feita à mão. Ao refazer a pesquisa, atualizar aqui e a data em PESQUISA.
 */
import { ufsComPagamentos } from "./pagamentos";

export const PESQUISA = { estado: "19/11/2026", prefeituras: "20/11/2026", texto: "19 e 20 de novembro de 2026" };

export type Faixa = "inteiro" | "folha" | "obras" | "nada";
export type Prefeituras = "sim" | "parte" | "nao" | "nao-se-aplica";

/** `frase` completa "O governo do estado …", na página de cada estado. */
export const FAIXAS: { id: Faixa; nome: string; curto: string; explica: string; frase: string }[] = [
  { id: "inteiro", nome: "Publicam o gasto inteiro por município", curto: "Gasto inteiro por município", frase: "publica quanto gasta em cada município",
    explica: "Cada gasto do governo do estado vem com a cidade onde foi feito. Dá para somar e saber quanto o estado gastou em cada município." },
  { id: "folha", nome: "Publicam a folha de pagamento com a cidade ou a escola", curto: "Folha com cidade ou unidade", frase: "publica a folha de pagamento com a cidade ou a escola, mas não o gasto inteiro por município",
    explica: "O salário dos servidores vem com a escola, o hospital ou a cidade onde trabalham. Salário é mais da metade do gasto de um estado, então isso já mostra boa parte do caminho do dinheiro." },
  { id: "obras", nome: "Publicam só obras ou convênios por município", curto: "Só obras e convênios", frase: "publica só as obras ou os convênios de cada município, uma parte pequena do que gasta",
    explica: "Dá para ver as obras ou os convênios em cada cidade, mas isso é uma parte pequena do gasto do estado." },
  { id: "nada", nome: "Não publicam quase nada por município", curto: "Quase nada", frase: "não publica quase nada sobre quanto gasta em cada município",
    explica: "No máximo a região do estado, ou uma parte muito pequena do gasto. Não dá para saber quanto o estado gastou em cada cidade." },
];

export const PREFEITURAS: { id: Prefeituras; nome: string; explica: string }[] = [
  { id: "sim", nome: "Sim", explica: "O Tribunal de Contas publica os pagamentos de todas as prefeituras, com o nome de quem recebeu." },
  { id: "parte", nome: "Em parte", explica: "Publica, mas falta o nome de quem recebeu (só o CNPJ) ou só o total do ano." },
  { id: "nao", nome: "Não", explica: "Não publica, ou só atrás de captcha, login ou chave pedida ao tribunal." },
  { id: "nao-se-aplica", nome: "Não se aplica", explica: "O Distrito Federal não tem prefeituras." },
];

interface Fonte { nome: string; url?: string }

export interface Estado {
  uf: string;
  faixa: Faixa;
  /** O que o governo do estado publica por município. */
  publica: string;
  /** O que falta para chegar ao gasto por município, quando vale dizer. */
  falta?: string;
  fonte: Fonte;
  /** O site já mostra o gasto do estado em cada cidade com esse dado. */
  noSite?: boolean;
  prefeituras: {
    situacao: Prefeituras;
    texto: string;
    fonte?: Fonte;
    /** O site já mostra "para quem a prefeitura pagou" com esse dado. */
    noSite?: boolean;
  };
}

const ESTADOS: Estado[] = [
  // Gasto inteiro por município
  { uf: "PB", faixa: "inteiro", noSite: true,
    publica: "Cada nota de empenho, numa API aberta, diz em que município o dinheiro foi gasto.",
    falta: "A folha de pagamento aparece na cidade da sede do órgão, não onde o servidor trabalha.",
    fonte: { nome: "Dados abertos da Paraíba (API)", url: "https://api.dados.pb.gov.br" },
    prefeituras: { situacao: "sim", noSite: true, texto: "Um arquivo por ano com todas as 223 prefeituras, de 2003 a 2026, com o nome de quem recebeu.", fonte: { nome: "TCE-PB", url: "https://tce.pb.gov.br" } } },
  { uf: "MG", faixa: "inteiro", noSite: true,
    publica: "A execução do plano plurianual distribuída por município, desde 2012.",
    falta: "Quem informa a cidade são os próprios órgãos; 2024 está incompleto na fonte.",
    fonte: { nome: "Dados abertos de Minas Gerais", url: "https://dados.mg.gov.br/dataset/planejamento-e-monitoramento" },
    prefeituras: { situacao: "sim", texto: "Um arquivo por ano com as 853 prefeituras, com o nome de quem recebeu. O download só funciona pelo navegador.", fonte: { nome: "TCE-MG", url: "https://dadosabertos.tce.mg.gov.br" } } },

  // Folha com cidade ou unidade
  { uf: "PR", faixa: "folha",
    publica: "A folha de pagamento com o município e o local de trabalho (a escola, por exemplo), desde 2012, para baixar.",
    falta: "Nada: é o caso mais completo depois de PB e MG.",
    fonte: { nome: "Portal da Transparência do Paraná", url: "https://www.transparencia.pr.gov.br/pte/assunto/8/129" },
    prefeituras: { situacao: "sim", texto: "Um arquivo por ano com as 399 prefeituras, inclusive Curitiba, com o nome de quem recebeu.", fonte: { nome: "TCE-PR", url: "https://pit.tce.pr.gov.br/" } } },
  { uf: "SC", faixa: "folha",
    publica: "A folha por unidade e cidade, inclusive polícia e bombeiros; obras com a parte de cada município.",
    falta: "Tirar a cidade do nome da unidade.",
    fonte: { nome: "Dados abertos de Santa Catarina", url: "https://dados.sc.gov.br/dataset/remuneracao-servidores" },
    prefeituras: { situacao: "sim", noSite: true, texto: "O painel do tribunal tem os pagamentos das 295 prefeituras, com o nome de quem recebeu, de 2023 a 2026.", fonte: { nome: "TCE-SC", url: "https://paineistransparencia.tce.sc.gov.br" } } },
  { uf: "SP", faixa: "folha",
    publica: "A cidade de cada servidor num arquivo e o salário em outro.",
    falta: "Cruzar os dois arquivos (ainda não testado).",
    fonte: { nome: "Portal da Transparência de São Paulo", url: "https://www.transparencia.sp.gov.br/Remuneracaomensal/Index" },
    prefeituras: { situacao: "sim", texto: "Um arquivo por ano com 644 prefeituras, com o nome de quem recebeu. A capital fica de fora (é de outro tribunal, o TCM-SP).", fonte: { nome: "TCE-SP", url: "https://transparencia.tce.sp.gov.br/" } } },
  { uf: "RJ", faixa: "folha",
    publica: "A folha por unidade, numa API aberta.",
    falta: "Uma tabela que diga em que cidade fica cada unidade.",
    fonte: { nome: "Remuneração dos servidores do RJ", url: "https://www.rj.gov.br/remuneracao/" },
    prefeituras: { situacao: "parte", texto: "Os gastos de todas as prefeituras, mas só com o CNPJ de quem recebeu, sem o nome. A capital publica à parte, com o nome.", fonte: { nome: "TCE-RJ", url: "https://dados.tcerj.tc.br/" } } },
  { uf: "ES", faixa: "folha",
    publica: "A folha da educação e da saúde por escola e hospital; obras e convênios com o município.",
    falta: "A polícia aparece só por órgão.",
    fonte: { nome: "Dados abertos do Espírito Santo", url: "https://dados.es.gov.br/dataset/portal-da-transparencia-pessoal" },
    prefeituras: { situacao: "sim", texto: "Os gastos de todas as prefeituras, de 2017 a 2026, com o nome de quem recebeu.", fonte: { nome: "TCE-ES", url: "https://dados.es.gov.br/dataset/tcees-empenho" } } },
  { uf: "BA", faixa: "folha",
    publica: "A folha por unidade, mês a mês desde 2019.",
    falta: "Uma tabela que diga em que cidade fica cada unidade.",
    fonte: { nome: "Dados abertos da Bahia", url: "https://dados.ba.gov.br/dataset/dados-de-servidores" },
    prefeituras: { situacao: "nao", texto: "O tribunal tem os gastos de todos os municípios, mas a consulta pede captcha.", fonte: { nome: "TCM-BA", url: "https://www.tcm.ba.gov.br" } } },
  { uf: "SE", faixa: "folha",
    publica: "A folha com o local de trabalho e as obras com o município, numa API aberta.",
    falta: "As obras são de uma secretaria só.",
    fonte: { nome: "Obras do governo de Sergipe", url: "https://sedurbi.se.gov.br/transparencia/obras/" },
    prefeituras: { situacao: "nao", texto: "O tribunal recebe os dados das prefeituras, mas só mostra painéis.", fonte: { nome: "TCE-SE", url: "https://www.tce.se.gov.br" } } },
  { uf: "AM", faixa: "folha",
    publica: "A folha por unidade (escola, saúde, quartel), numa API aberta; obras com o valor por município.",
    falta: "Uma tabela que diga em que cidade fica cada unidade.",
    fonte: { nome: "Portal da Transparência do Amazonas", url: "https://www.transparencia.am.gov.br" },
    prefeituras: { situacao: "sim", texto: "Uma API com os pagamentos de cada prefeitura, mês a mês, com o nome de quem recebeu.", fonte: { nome: "TCE-AM", url: "https://transparencia.tce.am.gov.br" } } },
  { uf: "GO", faixa: "folha",
    publica: "A folha por unidade; um mapa com as obras de quase todos os órgãos; a merenda por escola.",
    falta: "Uma tabela que diga em que cidade fica cada unidade.",
    fonte: { nome: "Dados abertos de Goiás", url: "https://dadosabertos.go.gov.br/dataset/folha-de-pagamento" },
    prefeituras: { situacao: "nao", texto: "O tribunal tem uma API com os pagamentos, mas ela pede uma chave que ele mesmo fornece. Pedimos a chave em 20/11/2026.", fonte: { nome: "TCM-GO", url: "https://www.tcmgo.tc.br" } } },

  // Só obras ou convênios
  { uf: "PE", faixa: "obras",
    publica: "As obras com o município, desde 2020, e os repasses a hospitais geridos por organizações sociais.",
    fonte: { nome: "Painel de obras de Pernambuco", url: "https://transparencia.pe.gov.br/despesas/obras/painel-de-obras-obraspe/" },
    prefeituras: { situacao: "sim", texto: "Uma API com os gastos de cada prefeitura, com o nome de quem recebeu. Só responde a endereços do Brasil.", fonte: { nome: "TCE-PE", url: "https://sistemas.tce.pe.gov.br/DadosAbertos/Exemplo!listar" } } },
  { uf: "MA", faixa: "obras",
    publica: "As obras da Secretaria de Infraestrutura; em 27% delas o local é genérico.",
    fonte: { nome: "Portal da Transparência do Maranhão", url: "https://transparencia.ma.gov.br" },
    prefeituras: { situacao: "parte", texto: "Os gastos de todas as prefeituras, desde 2023, mas só com o CPF ou CNPJ de quem recebeu, sem o nome.", fonte: { nome: "TCE-MA", url: "https://www.tcema.tc.br" } } },
  { uf: "PI", faixa: "obras",
    publica: "As obras, com o município escrito na descrição; o Tribunal de Contas tem um painel de obras com filtro por município.",
    fonte: { nome: "API da Transparência do Piauí", url: "https://api.transparencia.pi.gov.br/docs/" },
    prefeituras: { situacao: "parte", texto: "Só o total do ano por nome de quem recebeu, sem o CNPJ e sem cada gasto.", fonte: { nome: "TCE-PI", url: "https://sistemas.tce.pi.gov.br" } } },
  { uf: "MT", faixa: "obras",
    publica: "As obras de infraestrutura, num mapa com API aberta, e os convênios.",
    fonte: { nome: "Mapa de obras de Mato Grosso", url: "https://sinfralog.sinfra.mt.gov.br/obras-gov-map/" },
    prefeituras: { situacao: "nao", texto: "O painel do tribunal não mostra quem recebeu; os dados brutos pedem ofício e senha.", fonte: { nome: "TCE-MT", url: "https://www.tce.mt.gov.br" } } },
  { uf: "AC", faixa: "obras",
    publica: "As obras com o município e o valor pago.",
    fonte: { nome: "Portal da Transparência do Acre", url: "https://transparencia.ac.gov.br/conteudo/obras" },
    prefeituras: { situacao: "sim", noSite: true, texto: "O painel do tribunal tem os gastos dos 22 municípios, com o nome de quem recebeu, de 2022 a 2026.", fonte: { nome: "TCE-AC", url: "https://qlik.tceac.tc.br" } } },
  { uf: "RR", faixa: "obras",
    publica: "As obras com o município, só na tela.",
    fonte: { nome: "Mapa de obras de Roraima", url: "https://www.transparencia.rr.gov.br/obras" },
    prefeituras: { situacao: "nao", texto: "As prestações de contas das prefeituras são só PDFs e balancetes.", fonte: { nome: "TCE-RR", url: "https://www.tcerr.tc.br" } } },
  { uf: "PA", faixa: "obras",
    publica: "As obras de 2009 a 2024, com a região e o município; a qualidade é duvidosa.",
    fonte: { nome: "Portal da Transparência do Pará", url: "https://www.sistemas.pa.gov.br/portaltransparencia/" },
    prefeituras: { situacao: "nao", texto: "A consulta dos gastos das prefeituras pede captcha.", fonte: { nome: "TCM-PA", url: "https://www.tcm.pa.gov.br" } } },
  { uf: "RS", faixa: "obras",
    publica: "Os convênios com as prefeituras.",
    falta: "A cidade que aparece nos gastos é a de quem recebeu, não a de onde o dinheiro foi aplicado.",
    fonte: { nome: "Dados abertos do Rio Grande do Sul", url: "https://dados.rs.gov.br/dataset/convenios-do-estado" },
    prefeituras: { situacao: "sim", texto: "Um arquivo por ano com as 497 prefeituras, de 2004 a 2026, com o nome de quem recebeu.", fonte: { nome: "TCE-RS", url: "https://dados.tce.rs.gov.br/" } } },
  { uf: "RO", faixa: "obras",
    publica: "Os convênios e as transferências voluntárias.",
    fonte: { nome: "Portal da Transparência de Rondônia", url: "https://transparencia.ro.gov.br/convenios/convenios-de-saida" },
    prefeituras: { situacao: "nao", texto: "O portal do tribunal pede login.", fonte: { nome: "TCE-RO", url: "https://tcero.tc.br" } } },

  // Quase nada
  { uf: "CE", faixa: "nada",
    publica: "Só a região administrativa em cada gasto. Existe uma página de investimentos por município que a pesquisa não conseguiu abrir.",
    fonte: { nome: "Ceará Transparente", url: "https://cearatransparente.ce.gov.br" },
    prefeituras: { situacao: "sim", texto: "Uma API com os gastos de cada prefeitura, de 2008 a 2026, com o nome de quem recebeu.", fonte: { nome: "TCE-CE", url: "https://api-dados-abertos.tce.ce.gov.br/" } } },
  { uf: "MS", faixa: "nada",
    publica: "Só as emendas dos deputados estaduais, com o município.",
    fonte: { nome: "Dados abertos de Mato Grosso do Sul", url: "https://www.dados.ms.gov.br" },
    prefeituras: { situacao: "nao", texto: "O site do tribunal não tem os gastos das prefeituras.", fonte: { nome: "TCE-MS", url: "https://www.tce.ms.gov.br" } } },
  { uf: "AL", faixa: "nada",
    publica: "Só a região de planejamento, e 88% dos gastos caem num código só.",
    fonte: { nome: "Portal da Transparência de Alagoas", url: "https://transparencia.al.gov.br" },
    prefeituras: { situacao: "nao", texto: "O sistema antigo do tribunal saiu do ar; o site novo só tem um painel de totais.", fonte: { nome: "TCE-AL", url: "https://tceal.tc.br" } } },
  { uf: "DF", faixa: "nada",
    publica: "Só 3% do gasto vem com a região administrativa; 94% diz apenas \"Distrito Federal\".",
    fonte: { nome: "Portal da Transparência do DF", url: "https://www.transparencia.df.gov.br" },
    prefeituras: { situacao: "nao-se-aplica", texto: "O Distrito Federal não tem prefeituras." } },
  { uf: "AP", faixa: "nada",
    publica: "Um painel de obras, mas sem a coluna do município.",
    fonte: { nome: "Portal da Transparência do Amapá", url: "https://transparencia.ap.gov.br" },
    prefeituras: { situacao: "nao", texto: "O tribunal publica um PDF por prefeitura e mês, sem dados abertos.", fonte: { nome: "TCE-AP" } } },
  { uf: "RN", faixa: "nada",
    publica: "A pesquisa não achou caminho que funcionasse.",
    fonte: { nome: "Portal da Transparência do RN", url: "https://www.transparencia.rn.gov.br/" },
    prefeituras: { situacao: "parte", texto: "Os gastos das prefeituras, desde 2018, mas só com o CNPJ de quem recebeu, sem o nome.", fonte: { nome: "TCE-RN", url: "https://apidadosabertos.tce.rn.gov.br/swagger" } } },
  { uf: "TO", faixa: "nada",
    publica: "A pesquisa não achou nenhum caminho.",
    fonte: { nome: "Portal da Transparência do Tocantins", url: "https://transparencia.to.gov.br/PortalTransparencia/" },
    prefeituras: { situacao: "sim", texto: "Uma planilha por município e ano, de 2013 a 2026, com o nome de quem recebeu.", fonte: { nome: "TCE-TO", url: "https://portaldocidadao.tceto.tc.br" } } },
];

// Se o build tem o arquivo de pagamentos de um estado, o site já usa o dado do tribunal
// (assim um estado novo, como PE, aparece como "no site" sem mexer nesta tabela).
const comPagamentos = new Set(ufsComPagamentos());
for (const e of ESTADOS) if (comPagamentos.has(e.uf)) e.prefeituras.noSite = true;

export const QUEM_PUBLICA: Estado[] = ESTADOS;
export const estadoDe = (uf: string) => ESTADOS.find((e) => e.uf === uf.toUpperCase()) ?? null;
export const faixaDe = (f: Faixa) => FAIXAS.find((x) => x.id === f)!;
export const prefeiturasDe = (p: Prefeituras) => PREFEITURAS.find((x) => x.id === p)!;
export const porFaixa = (f: Faixa) => ESTADOS.filter((e) => e.faixa === f);
