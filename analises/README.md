# Análises

Cada pasta aqui é uma análise do Orçamento Brasileiro: uma pergunta, o que os dados respondem, como chegamos lá e
como refazer. As contas ficam num comando do pipeline (`pipeline/src/orcamento_pipeline/analise_*.py`). O que ele
baixa e reduz vai para o espelho público (`dados.orcamentobrasileiro.com.br`), para que dê para refazer a análise sem
baixar as fontes de novo.

| Análise | Pergunta | Comando |
|---|---|---|
| [emendas-votos](emendas-votos/) | Os deputados mandam emendas para onde tiveram voto? | `uv run analise-emendas-votos` |

## Como refazer qualquer uma

Os comandos rodam de dentro de `pipeline/` e precisam do [uv](https://docs.astral.sh/uv/).

```bash
uv run analise-<nome> --do-espelho   # baixa os insumos já reduzidos do espelho e roda: minutos
uv run analise-<nome>                # baixa tudo das fontes originais e roda: pode levar horas
```

Os números saem em `data/analises/<nome>/resultados.json`. O texto de cada análise cita esses mesmos números.
