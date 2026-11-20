/**
 * Nome legível de quem mandou uma emenda. A CGU traz tudo em maiúsculas e sem acento
 * ("BANCADA DO CEARA", "COM. ASSUNTOS SOCIAIS"): bancadas e comissões têm o nome escrito aqui; os
 * nomes de deputados e senadores só mudam de caixa ("CID GOMES" → "Cid Gomes").
 * O mapa (src/mapa/pagina.html) tem uma cópia desta lista: mudou aqui, mude lá.
 */
export const COLETIVOS: Record<string, string> = {
  "BANCADA DA BAHIA": "Bancada da Bahia", "BANCADA DA PARAIBA": "Bancada da Paraíba", "BANCADA DE ALAGOAS": "Bancada de Alagoas",
  "BANCADA DE GOIAS": "Bancada de Goiás", "BANCADA DE MINAS GERAIS": "Bancada de Minas Gerais", "BANCADA DE PERNAMBUCO": "Bancada de Pernambuco",
  "BANCADA DE RONDONIA": "Bancada de Rondônia", "BANCADA DE RORAIMA": "Bancada de Roraima", "BANCADA DE SANTA CATARINA": "Bancada de Santa Catarina",
  "BANCADA DE SAO PAULO": "Bancada de São Paulo", "BANCADA DE SERGIPE": "Bancada de Sergipe", "BANCADA DE TOCANTINS": "Bancada do Tocantins",
  "BANCADA DO ACRE": "Bancada do Acre", "BANCADA DO AMAPA": "Bancada do Amapá", "BANCADA DO AMAZONAS": "Bancada do Amazonas",
  "BANCADA DO CEARA": "Bancada do Ceará", "BANCADA DO DISTRITO FEDERAL": "Bancada do Distrito Federal", "BANCADA DO ESPIRITO SANTO": "Bancada do Espírito Santo",
  "BANCADA DO MARANHAO": "Bancada do Maranhão", "BANCADA DO MATO GROSSO": "Bancada de Mato Grosso", "BANCADA DO MATO GROSSO DO SUL": "Bancada de Mato Grosso do Sul",
  "BANCADA DO PARA": "Bancada do Pará", "BANCADA DO PARANA": "Bancada do Paraná", "BANCADA DO PIAUI": "Bancada do Piauí",
  "BANCADA DO RIO DE JANEIRO": "Bancada do Rio de Janeiro", "BANCADA DO RIO GRANDE DO NORTE": "Bancada do Rio Grande do Norte",
  "BANCADA DO RIO GRANDE DO SUL": "Bancada do Rio Grande do Sul",
  "COM. AGRICULTURA E REFORMA AGRARIA": "Comissão de Agricultura e Reforma Agrária",
  "COM. AGRICULTURA PEC ABAST D. RURAL": "Comissão de Agricultura, Pecuária, Abastecimento e Desenvolvimento Rural",
  "COM. ASSUNTOS SOCIAIS": "Comissão de Assuntos Sociais", "COM. CONST. JUSTICA E CIDADANIA": "Comissão de Constituição, Justiça e Cidadania",
  "COM. CULTURA": "Comissão de Cultura", "COM. DA SAUDE": "Comissão de Saúde",
  "COM. DE INTEGRACAO NACIONAL E DES. REGIONAL": "Comissão de Integração Nacional e Desenvolvimento Regional",
  "COM. DE PREVI., ASSIS. SOCI, INFAN., ADOL. E FAMIL": "Comissão de Previdência, Assistência Social, Infância, Adolescência e Família",
  "COM. DEFESA DOS DIREITOS DA MULHER": "Comissão de Defesa dos Direitos da Mulher", "COM. DESENV REGIONAL E TURISMO": "Comissão de Desenvolvimento Regional e Turismo",
  "COM. DESENV. URBANO": "Comissão de Desenvolvimento Urbano", "COM. DIREITOS HUMANOS E MINORIAS": "Comissão de Direitos Humanos e Minorias",
  "COM. EDUCACAO": "Comissão de Educação", "COM. EDUCACAO, CULTURA E ESPORTE": "Comissão de Educação, Cultura e Esporte", "COM. ESPORTE": "Comissão do Esporte",
  "COM. MISTA, PLAN.ORC.E FISCALIZACAO": "Comissão Mista de Orçamento", "COM. RELACOES EXT E DEFESA NACIONAL": "Comissão de Relações Exteriores e Defesa Nacional",
  "COM. SEG. PUBLICA E COMB. CRIME ORG": "Comissão de Segurança Pública e Combate ao Crime Organizado",
  "COM. SERV.DE INFRA-ESTRUTURA": "Comissão de Serviços de Infraestrutura", "COM. TURISMO": "Comissão de Turismo", "RELATOR GERAL": "Relator-geral do Orçamento",
};

const pequenas = new Set(["de", "da", "do", "das", "dos", "e"]);

/** "BANCADA DO CEARA" → "Bancada do Ceará"; "CID GOMES" → "Cid Gomes". */
export function nomeAutor(s: string): string {
  const t = s.trim();
  if (COLETIVOS[t]) return COLETIVOS[t];
  if (/^com\. /i.test(t)) return "Comissão de " + t.slice(5).toLowerCase();   // uma comissão nova, ainda sem nome escrito
  return t.toLowerCase().split(" ").map((p, i) => (i > 0 && pequenas.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1))).join(" ");
}

/** Bancadas, comissões e o relator são emendas coletivas. */
export const ehColetivo = (s: string) => /^(com\.|bancada|relator)/i.test(s.trim());
