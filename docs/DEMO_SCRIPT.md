# Roteiro da demonstração — aproximadamente 3 minutos

## Preparação

Em dois terminais, na raiz do repositório:

```bash
source .venv/bin/activate
LLM_PROVIDER=mock uvicorn conecta_conselho.main:app
```

```bash
source .venv/bin/activate
LLM_PROVIDER=mock streamlit run frontend/app.py
```

Abra a URL local apresentada pelo Streamlit. O roteiro não requer Ollama, credenciais ou serviços pagos.

## Narração e ações

**0:00–0:30 — Problema e escopo.** Apresente o Conecta Conselho como apoio à triagem de expansão, não como autorização de investimento. Mostre que há localidades sintéticas e três municípios com população oficial; explique que os indicadores reais não equivalem a cobertura de telecomunicações.

**0:30–1:00 — Evidências.** Selecione São Paulo e mostre população residente, fonte IBGE/SIDRA e ano 2022. Aponte o aviso de que outros dados ausentes não são presumidos. Depois selecione `DEMO002` e destaque o aviso de cenário sintético.

**1:00–1:40 — Premissas e análise.** Com `DEMO002`, informe teto hipotético de R$ 500.000, custo base hipotético de R$ 450.000, custo por âncora de R$ 20.000 e receita mensal hipotética de R$ 2.500. Selecione uma escola e uma unidade de saúde; execute o Conselho.

**1:40–2:20 — Perspectivas e cenários.** Mostre os pareceres Financeiro, Social, Técnico e Orçamentário, suas premissas e lacunas. Mostre Pontes como candidatas não verificadas e compare cenários base e com âncoras selecionadas. Reforce que a aritmética é determinística e os parâmetros continuam hipotéticos.

**2:20–2:50 — Guardião e auditoria.** Mostre divergências, bloqueios e revisão humana obrigatória. Abra o catálogo de evidências e, se houver tempo, baixe o JSON de auditoria.

**2:50–3:00 — Limite e próximos passos.** Encerre com a necessidade de dados locais de cobertura/custos e validação técnica. Informe que o modo mock é uma demonstração determinística e que evidências de uso IBM Bob ainda estão pendentes.

## Cuidados durante a gravação

- Não apresente premissas de custo ou receita como dados reais.
- Não descreva população como demanda ou cobertura.
- Não afirme parceria firmada com instituições.
- Não descreva o modo mock como resultado de um LLM.
- Não alegue uso de IBM Bob sem relatório de sessão verificável.
