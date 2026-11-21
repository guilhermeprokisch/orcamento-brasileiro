/**
 * Gasto do governo estadual localizado em cada município, para os estados que publicam esse
 * dado: a Paraíba, empenho a empenho (pipeline/…/estado_pb.py), Minas Gerais, pela execução
 * do plano plurianual distribuída por município (estado_mg.py), e o Paraná e Santa Catarina,
 * só pela folha de pagamento com o lugar de trabalho (estado_pr.py, estado_sc.py).
 * Lido no build; sem os arquivos, tudo vem null.
 */
import { docCidades, type Cidade } from "./cidades";

interface DocEstadual {
  ano: number;
  ate_mes: number;
  fonte: string;
  /** Como dizer o que o número é, quando difere do padrão (ver GastoEstadualAqui.astro). */
  texto?: TextoEstadual;
  estado: { empenhado: number; pago: number; folha: number; sem_municipio: number };
  areas: Record<string, string>;
  mun: Record<string, {
    local: number;
    pago: number;
    folha: number;
    /** Repasses obrigatórios à prefeitura, dívida e aposentadorias atribuídos ao município (só MG). */
    operacoes?: number;
    areas: Record<string, number>;
    /** [credor, ação, órgão, valor] */
    maiores: [string, string, string, number][];
  }>;
}

/** O que dizer quando o número não é "empenhos sem a folha" (MG, PR, SC). */
interface TextoEstadual {
  resumo: string;
  onde: string;
  nota: string;
  /** Título da lista das maiores (PR e SC: as unidades com a maior folha). */
  maiores?: string;
  /** Frase depois da fonte. */
  aviso?: string;
}

const arquivos = import.meta.glob<DocEstadual>("../../public/data/estados/*/*.json", { import: "default" });

export interface GastoEstadual {
  ano: number;
  fonte: string;
  /** Empenhado no município, sem a folha de pagamento. */
  local: number;
  /** Folha de órgãos estaduais com sede no município (não é gasto "na cidade"). */
  folha: number;
  /** Texto próprio do estado, quando o número não é "empenhos sem a folha". */
  texto: TextoEstadual | null;
  areas: { nome: string; valor: number }[];
  maiores: { credor: string; acao: string; orgao: string; valor: number }[];
  /** Parte de todo o gasto localizado do estado que caiu neste município. */
  parteDoEstado: number;
}

const cache = new Map<string, Promise<DocEstadual | null>>();
function docDa(uf: string): Promise<DocEstadual | null> {
  if (!cache.has(uf)) {
    // O ano mais recente disponível para o estado.
    const caminho = Object.keys(arquivos).filter((k) => k.includes(`/estados/${uf.toLowerCase()}/`)).sort().at(-1);
    cache.set(uf, caminho ? arquivos[caminho]() : Promise.resolve(null));
  }
  return cache.get(uf)!;
}

const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e", "em", "a", "o", "ao", "para", "com"]);
/** "SECRETARIA DE ESTADO DA SAUDE" -> "Secretaria de Estado da Saude". Siglas curtas (SPE, R & H) ficam como estão. */
function nomeProprio(s: string): string {
  if (s !== s.toUpperCase()) return s;
  return s.split(" ").map((p, i) => {
    const min = p.toLowerCase();
    if (i > 0 && MINUSCULAS.has(min)) return min;
    return p.length <= 3 && !MINUSCULAS.has(min) ? p : p.charAt(0) + min.slice(1);
  }).join(" ");
}

/** O que o governo do estado gastou no município, se o estado publica esse dado. */
export async function gastoEstadualEm(c: Cidade): Promise<GastoEstadual | null> {
  const doc = await docDa(c.uf);
  const m = doc?.mun[String(c.ibge)];
  if (!doc || !m || m.local <= 0) return null;
  const localizado = Object.values(doc.mun).reduce((s, x) => s + x.local, 0);
  return {
    ano: doc.ano, fonte: doc.fonte, local: m.local, folha: m.folha, texto: doc.texto ?? null,
    // Os nomes das áreas são os do resto do site (com acento); a ordem é a do valor, porque
    // um objeto com chaves numéricas ("10", "12") não preserva a ordem do arquivo.
    areas: Object.entries(m.areas)
      .map(([cod, valor]) => ({ nome: docCidades?.funcoes[cod] ?? nomeProprio(doc.areas[cod] ?? cod), valor }))
      .sort((a, b) => b.valor - a.valor),
    maiores: m.maiores.map(([credor, acao, orgao, valor]) => ({ credor: nomeProprio(credor), acao: nomeProprio(acao), orgao: nomeProprio(orgao), valor })),
    parteDoEstado: m.local / localizado,
  };
}
