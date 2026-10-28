# Conecta Conselho

Prova de conceito local para apoiar a triagem de oportunidades de expansão de conectividade. O sistema não autoriza investimentos nem substitui validação técnica, comercial ou de campo. As fases 0–10 entregam API de consulta/análise, dashboard, fluxo LangGraph, contratos, fixtures sintéticas e dados reais controlados, motor determinístico, pareceres independentes, Pontes, contestação, Guardião, persistência/exportação local em SQLite e documentação de demonstração. Pendências de evidência do IBM Bob estão declaradas e não são consideradas concluídas.

## Requisitos

- Python 3.11 ou superior.
- Nenhuma chave de API ou serviço pago é necessário para o modo padrão `LLM_PROVIDER=mock`.
- Ollama é opcional; somente necessário para `LLM_PROVIDER=ollama`.

## Preparar o ambiente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

## Iniciar a API

```bash
uvicorn conecta_conselho.main:app --reload
# em outro terminal, a partir da raiz:
streamlit run frontend/app.py
```

Verifique `http://localhost:8000/health`. A documentação interativa da API estará em `http://localhost:8000/docs`.

## Localidades de demonstração

`GET /api/v1/municipalities` lista três localidades sintéticas (`DEMO001`, `DEMO002`, `DEMO003`) e três municípios com população agregada observada no Censo 2022: Manaus, Recife e São Paulo. Cada evidência real expõe fonte, ano, data de coleta, termos e limitações; dados de cobertura, custos e instituições não foram ingeridos. O dashboard identifica localidades sintéticas e informa que os dados reais cobrem somente os indicadores exibidos. Consulte [data/README.md](data/README.md) e o [catálogo de dados](docs/DATA_CATALOG.md) antes de interpretar as entradas.

Os contratos Pydantic e seus JSON Schemas publicados estão em [docs/DOMAIN_SCHEMA.json](docs/DOMAIN_SCHEMA.json). Para regenerar o catálogo após alterações nos modelos, execute `python scripts/export_domain_schema.py` no ambiente virtual ativo.

O motor de scores e cenários está documentado em [docs/METHODOLOGY.md](docs/METHODOLOGY.md). Os scores são heurísticas explícitas de triagem; custos, receitas e limites não devem ser tratados como previsões ou orçamento operacional.

## Provedores e agentes

`LLM_PROVIDER=mock` é o padrão e funciona offline com templates determinísticos; não representa geração por IA. Os pareceres podem ser chamados em Python por `analyze_financial`, `analyze_social`, `analyze_technical`, `analyze_budget` e `analyze_bridges`. Cada saída passa por Pydantic, cita IDs presentes no catálogo e falha explicitamente se continuar inválida após no máximo um retry de schema. Pontes produz uma proposta qualitativa e simula apenas as âncoras selecionadas explicitamente; nenhuma parceria é presumida.

Para usar Ollama opcionalmente, primeiro confira `ollama list` e `GET http://localhost:11434/api/tags`; selecione e instale um modelo local compatível com saída estruturada e configure seu tag exato em `OLLAMA_MODEL`. Não é presumido nenhum nome ou versão, e o projeto não usa modelo cloud. O adapter chama a API local por HTTP, com timeout e JSON Schema; nenhuma instalação ou chamada ao Ollama é necessária para lint ou testes padrão. Consulte [docs/LLM_AGENTS.md](docs/LLM_AGENTS.md) para os comandos de instalação, validação e configuração.

## Verificações

```bash
ruff check .
pytest -q
```

## Materiais de apresentação e submissão

Arquitetura, metodologia, limitações, catálogo de dados, descrição do problema e solução, declaração tecnológica, roteiro de vídeo de aproximadamente três minutos e checklist estão em `docs/`. Para capturar exemplos A/B/C executados pela API local em modo mock, inicie a API conforme acima e execute:

```bash
LLM_PROVIDER=mock .venv/bin/python scripts/capture_demo_analyses.py
```

Os exemplos gravados em `docs/examples/` são gerados pelo fluxo da aplicação, mas usam somente localidades sintéticas e premissas hipotéticas. Veja [docs/SUBMISSION_CHECKLIST.md](docs/SUBMISSION_CHECKLIST.md) para o estado dos entregáveis. Uso efetivo do IBM Bob IDE e relatórios exportados continuam pendentes de evidência.

## API de análise e auditoria

`POST /api/v1/analyses` executa e persiste a análise. `GET /api/v1/analyses/{analysis_id}` recupera o resultado salvo e `GET /api/v1/analyses/{analysis_id}/export` baixa um JSON com request, resultado, fontes, hipóteses, erros e versões de prompts. A documentação OpenAPI está em `/docs`.

Exemplo de request (valores arbitrários, exclusivamente hipotéticos):

```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -H 'Content-Type: application/json' \
  -d '{"municipality_code":"DEMO002","parameters":{"budget_ceiling_brl":500000,"estimated_base_cost_brl":350000,"estimated_cost_per_anchor_brl":20000,"hypothetical_monthly_anchor_revenue_brl":2500,"scenario_horizon_months":12},"selected_anchor_ids":["DEMO002-SCHOOL-01","DEMO002-HEALTH-01"]}'
```

Use o `analysis_id` retornado para consultar ou exportar:

```bash
curl http://localhost:8000/api/v1/analyses/ANALYSIS_ID
curl -OJ http://localhost:8000/api/v1/analyses/ANALYSIS_ID/export
```

Os requests têm limite de 1 MiB e aceitam até 20 IDs de âncora; cada ID ainda precisa pertencer à localidade. O CORS permite somente `http://localhost:8501` e `http://127.0.0.1:8501`. O SQLite padrão é `./conecta_conselho.db`, configurável por `DATABASE_URL`; as análises permanecem disponíveis após reiniciar a API. Os registros são locais e ficam retidos até limpeza explícita. Para apagar todas as análises da base configurada, execute `python scripts/reset_demo_db.py --confirm`. Sem `--confirm`, nada é removido.

## Dashboard Streamlit

Com a API iniciada em um terminal, execute `streamlit run frontend/app.py` na raiz do projeto em outro. Configure `API_BASE_URL` se a API estiver em outro endereço (padrão `http://localhost:8000`). A tela permite escolher uma das seis localidades, consultar evidências e proveniência, preencher premissas hipotéticas, selecionar explicitamente instituições candidatas, executar o Conselho, revisar pareceres/cenários/Guardião e baixar a auditoria JSON. Os valores opcionais não informados permanecem ausentes; zero não é usado para preencher lacunas. O dashboard mostra falhas de conexão, validação, provedor, resultados degradados e exportação. Não há opção de procurar análises anteriores: a API atual não oferece endpoint de listagem.

A especificação cita Plotly entre bibliotecas esperadas da stack. A FASE 8 pede cards e comparação de cenários, sem visualização gráfica; por isso a interface usa os componentes nativos do Streamlit e não adiciona uma dependência Plotly sem uso.

### Smoke test manual do dashboard

1. Ative o ambiente e inicie `uvicorn conecta_conselho.main:app --reload`.
2. Em outro terminal, execute `LLM_PROVIDER=mock streamlit run frontend/app.py`.
3. Abra o endereço local apresentado pelo Streamlit e confirme que a API está marcada como disponível e que as três localidades `DEMO` e Manaus, Recife e São Paulo aparecem no seletor.
4. Selecione `DEMO003`; confirme o rótulo sintético e que a evidência indisponível continua como “Não disponível”. Selecione São Paulo e confirme o rótulo observado, a fonte/ano e o aviso de que só há população oficial.
5. Preencha o teto hipotético, deixe ao menos um custo opcional sem informar, selecione zero ou mais instituições e execute o Conselho.
6. Revise os quatro pareceres, Pontes, cenários, decisão preliminar, trilha de evidências e eventuais erros; confirme que valores ausentes não foram exibidos como zero.
7. Baixe o JSON de auditoria e confirme que o navegador oferece `analysis-<analysis_id>.json`.
8. Para verificar o estado de erro, pare a API e recarregue a tela; o dashboard deve informar que não conseguiu conectar.

O `AppTest` automatizado exercita a seleção de localidade, campos do formulário, seleção de âncora, renderização do resultado e download. O smoke HTTP também inicia a API em mock e o Streamlit headless, consulta as rotas de análise/exportação e verifica os endpoints HTTP dos dois serviços. Em 2026-10-27, Chrome headless em viewport 1440×1000 foi usado para revisar visualmente o cabeçalho, cards, ausência de dados e formulário. A apresentação pós-execução foi verificada pelo AppTest e pelo smoke HTTP de análise/exportação; não foi feita interação manual com navegador gráfico.

## Estado e limitações

Os endpoints implementados são `GET /health`, consultas de localidades e análise/recuperação/exportação em `/api/v1/analyses`. Falha de provedor retorna HTTP 503 com resultado parcial `status=degraded` e erros explícitos. O arquivo `AGENTS .md`, recebido com espaço no nome, foi preservado; `AGENTS.md` contém as instruções canônicas da raiz.

O uso do IBM Bob IDE e a exportação de relatórios de sessão são pendências de evidência: este repositório não registra uso efetivo da ferramenta.
