# Dinheiro federal: o Portal e as prefeituras contam igual?

O mapa usa duas fontes para o dinheiro que a União manda às prefeituras:

- o **Portal da Transparência** (CGU), que registra o que a União pagou, por programa;
- a **prestação de contas anual** (DCA, Anexo I-C), em que cada prefeitura declara o que recebeu.

Em algumas cidades os dois números ficam longe um do outro (em Afuá, PA, R$ 169 mi no Portal
contra R$ 213 mi declarados em 2025). Esta página registra por quê. Para refazer a conta:
`uv run conciliar 2025` (em `pipeline/`).

## Resultado de 2025

5.501 municípios com os dois lados. Razão = Portal / declarado.

| Comparação | Portal (R$ bi) | Declarado (R$ bi) | Razão | p10 | Mediana | p90 | Cidades a ±5% |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPM x declarado bruto | 169,6 | 237,8 | 0,71 | 0,71 | 0,71 | 0,71 | 0% |
| FPM x declarado sem a retenção do FUNDEB | 169,6 | 195,4 | 0,87 | 0,87 | 0,87 | 0,87 | 1% |
| SUS | 124,6 | 125,0 | 1,00 | 0,95 | 0,98 | 1,30 | 66% |
| Royalties e compensações | 36,4 | 34,8 | 1,05 | 0,99 | 1,00 | 1,02 | 89% |
| Assistência social (FNAS) | 4,1 | 3,8 | 1,10 | 0,91 | 0,98 | 1,54 | 64% |
| Educação e outros repasses | 37,7 | 44,8 | 0,84 | 0,57 | 0,93 | 1,17 | 27% |
| FUNDEB x complementação da União | 101,8 | 48,8 | 2,09 | 1,43 | 3,47 | 15,63 | 0% |
| FUNDEB x complementação + fundo | 101,8 | 220,9 | 0,46 | 0,15 | 0,30 | 0,77 | 0% |

## O que explica cada diferença

**SUS, royalties e assistência social batem.** No total, a diferença é de 0,4%, 4,5% e 10%.
Cidade a cidade há dispersão (um repasse de dezembro contado em janeiro, um fundo regional
registrado na cidade-sede), mas sem viés.

**FPM: o Portal mostra 71% do valor bruto, igual em todas as cidades.** A razão não varia
(p10 = mediana = p90), então é regra, não erro de declaração. Duas coisas a explicam:

1. O Portal registra o FPM já sem os 20% retidos para o FUNDEB. Isso é verificado: a prefeitura
   declara o FPM bruto e a dedução em colunas separadas.
2. Mesmo sem a retenção sobram 13% de diferença, também uniforme. O tamanho bate com as três
   parcelas extras de 1% do FPM (julho, setembro e dezembro), que são cerca de 12% do fundo e
   não sofrem a retenção. No arquivo do Portal não há pico em julho nem linha separada para
   elas. **Isto é uma hipótese consistente com os números, não confirmada em documentação.**

Consequência: a linha "FPM" do mapa, que vem do Portal, é menor do que o FPM que a prefeitura
declara. Os R$ 24 bi a R$ 28 bi das parcelas extras não aparecem no dinheiro federal do mapa.

**FUNDEB: são dois dinheiros diferentes com o mesmo nome.** O Portal soma duas ações:

- a complementação da União (R$ 48,1 bi), que bate com os R$ 48,8 bi que as prefeituras
  declaram como complementação. Na prestação de contas ela entra em "repasses da União",
  não em "FUNDEB";
- a transferência ao FUNDEB (R$ 55,0 bi), que é a parte do fundo formada por tributos federais
  (os 20% retidos do FPM, do FPE e de outros).

O que as prefeituras declaram como FUNDEB (R$ 172 bi) inclui também a parte formada por ICMS e
IPVA, que é dinheiro estadual e não passa pelo Portal. Por isso o "FUNDEB" do Portal e o da
prefeitura não são comparáveis linha a linha.

**Educação e outros repasses: 16% a menos no Portal, com bastante dispersão.** É o grupo mais
heterogêneo (FNDE, salário-educação, convênios, transferências especiais). Não foi investigado
conta a conta.

## O caso de Afuá

| | Portal | Declarado |
|---|---:|---:|
| FPM | 33,8 | 47,5 bruto; 39,0 sem a retenção |
| SUS | 23,8 | 24,4 |
| Royalties | 0,8 | 0,8 |
| Assistência social | 0,9 | 1,0 |
| Educação e outros | 20,0 | 20,7 |
| FUNDEB | 90,1 | 66,7 de complementação + 60,1 do fundo |

Em R$ milhões, 2025. Tirando FPM e FUNDEB, que seguem as regras acima, os valores coincidem.

## O que o mapa faz com isso

- A pergunta "O que vem do governo federal" usa o Portal (inclui benefícios pagos às pessoas).
- O cartão "O que volta para cá" usa a prestação de contas da prefeitura.
- As duas listas não são somadas nem comparadas linha a linha; as notas do cartão dizem de
  onde vem cada número.
