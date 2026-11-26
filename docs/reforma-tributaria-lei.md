# Reforma tributária: o que diz o texto da lei

Só texto de lei, baixado do Planalto em 26/11/2026 (versão compilada):

- EC 132/2023 — https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc132.htm
- LC 214/2025 — https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm
- LC 227/2026 (13/01/2026; cria o Comitê Gestor do IBS e altera a LC 214) — https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp227.htm

Obs.: o Planalto derruba conexão HTTP/2 do curl; usar `curl --http1.1` com User-Agent de navegador. O HTML é windows-1252.

## Cronograma

| Ano | O que acontece | Onde está |
|---|---|---|
| 2026 | Ano de teste: CBS 0,9% e IBS 0,1% (estadual). O valor é descontado do PIS/Cofins devido; quem cumpre as obrigações acessórias fica dispensado de recolher. Simples Nacional fora. | ADCT art. 125 (EC 132); LC 214 arts. 343, 346, 348 |
| 2027 | CBS cobrada de verdade; **PIS e Cofins extintos**; **IPI com alíquota zero**, exceto produtos com industrialização incentivada na Zona Franca de Manaus; **Imposto Seletivo** começa. | ADCT art. 126; EC 132 art. 22, I |
| 2027–2028 | IBS a 0,05% estadual + 0,05% municipal; CBS reduzida em 0,1 ponto. A alíquota de referência da CBS sai de resolução do Senado. | ADCT art. 127; LC 214 arts. 344, 347, 349 |
| 2029–2032 | ICMS e ISS caem para 9/10, 8/10, 7/10 e 6/10 das alíquotas atuais (benefícios fiscais caem junto). | ADCT art. 128; LC 214 arts. 501 e 508 |
| 2033 | **ICMS e ISS extintos**; IBS cheio. LC 87/1996 (Kandir) e LC 116/2003 revogadas. | ADCT art. 129; EC 132 art. 22, II; LC 214 art. 543 |

Os artigos de transição não mexem em IR, INSS, CSLL, IOF, IPVA, ITCMD, IPTU e ITBI.

## Repartição (o que afeta o caminho dos impostos)

- FPE, FPM e fundos regionais: a base passa a ser IR + IPI + Imposto Seletivo (art. 159, I, na redação da EC 132).
- IPI-exportação: 10% do IPI **e do Imposto Seletivo** aos estados (art. 159, II).
- Cota-parte das prefeituras: 25% do ICMS (até 2032) e 25% do IBS que cabe ao estado (art. 158, IV, "b"). Critérios do IBS: 80% população, 10% educação, 5% meio ambiente, 5% partes iguais (art. 158, § 2º).

## O que muda no site (/impostos/)

- O nó "Cofins e PIS" vira CBS a partir dos dados de 2027.
- IPI quase some (só Zona Franca) e entra o Imposto Seletivo.
- ICMS e ISS encolhem de 2029 a 2032 e dão lugar ao IBS; somem em 2033.
- Textos do `SigaImposto` ("Nas compras", "Nos serviços") e do glossário em `site/src/lib/caminho-impostos.ts` (fpe, fpm, ipi-exportacao) citam IPI/PIS/Cofins/ICMS/ISS.
- Os dados de 2025 que o site mostra hoje continuam certos: a mudança vale para os anos novos.
