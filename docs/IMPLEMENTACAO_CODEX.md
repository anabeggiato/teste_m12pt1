# CONECTA CONSELHO — ESPECIFICAÇÃO DE IMPLEMENTAÇÃO PARA CODEX

**Versão:** 1.0 · **Idioma de trabalho:** português brasileiro · **Tipo:** prova de conceito (POC) · **Trilha:** Telecomunicações inteligentes — Fundação Telefônica / IBM AI Experiential Learning Lab 2026

> **INSTRUÇÃO PRINCIPAL AO AGENTE DE CÓDIGO:** Implemente este projeto incrementalmente, seguindo a ordem das fases. Antes de alterar arquivos, inspecione o repositório. Não substitua requisitos por suposições silenciosas. Não fabrique dados, não apresente projeções hipotéticas como fatos e não marque tarefas como concluídas sem executar os testes pertinentes. Priorize um MVP funcional, reproduzível, auditável e totalmente local.

---

## 0. Como utilizar este documento

Este arquivo é a fonte de verdade técnica do projeto. Salve-o como `docs/IMPLEMENTACAO_CODEX.md` no repositório. Crie também `AGENTS.md` na raiz, resumindo as regras da seção 2. Ao iniciar uma sessão do Codex, solicite: “Leia `docs/IMPLEMENTACAO_CODEX.md` e `AGENTS.md`; implemente somente a fase indicada, execute os testes, registre o que mudou e informe pendências”.

**Princípio de execução:** uma fase por pull request ou commit coerente; código + testes + documentação na mesma entrega. Não tentar gerar o sistema inteiro de uma só vez. O Codex deve solicitar confirmação apenas quando houver impedimento real (por exemplo, inexistência de dataset licenciado, falta de acesso a modelo ou alteração de escopo).

### 0.1 Distinção entre requisitos e decisões do projeto

**Requisitos do programa, conforme materiais fornecidos:** desenvolver uma solução de IA agêntica para problema real; usar IBM Bob IDE como componente central; exportar relatórios de sessões do Bob para o repositório; preparar POC funcional, descrição de problema/solução, declaração tecnológica e vídeo de demonstração de aproximadamente 3 minutos. O uso de watsonx Orchestrate é recomendado, mas o guia permite outras tecnologias. Os dados devem ter uso permitido, com origem registrada, sem dados pessoais ou confidenciais.

**Decisões de implementação desta especificação (propostas da equipe, não exigências da IBM):** Python + FastAPI + LangGraph + Ollama + SQLite + Streamlit; análise municipal com três municípios de demonstração; seis papéis de agentes; simulação de cenário com regras determinísticas; recomendações não vinculantes; modo mock para executar sem LLM.

**Pendências externas:** confirmar os municípios reais, a disponibilidade de IBM Bob, o hardware local e os conjuntos de dados permitidos. Não bloquear a implementação: usar fixtures explicitamente sintéticas até que dados reais sejam integrados.

---

## 1. Visão do produto

### 1.1 Problema

Operadoras precisam priorizar onde expandir conectividade, conciliando viabilidade comercial, restrições de infraestrutura, orçamento e benefício social. Uma análise isolada pode favorecer áreas rentáveis e ignorar localidades desassistidas. O Conecta Conselho reúne perspectivas especializadas e testa se instituições âncora (escolas, unidades de saúde e outros equipamentos públicos) poderiam melhorar o cenário de atendimento.

### 1.2 Usuário-alvo e decisão apoiada

Usuário principal: analista ou gerente de planejamento de expansão de uma operadora de telecomunicações. Usuários secundários: área de impacto social, equipe técnica e gestores de investimento. O sistema **apoia** a triagem de oportunidades, mas **não autoriza** obras, não calcula orçamento executivo e não substitui análise de campo, regulação ou negociação comercial.

### 1.3 Jornada obrigatória da demonstração

1. Usuário abre o dashboard e visualiza três municípios ou localidades pré-carregados.
2. Seleciona uma localidade e inspeciona indicadores com fontes e ano.
3. Define um teto de investimento hipotético e, opcionalmente, parâmetros de simulação identificados como estimativas.
4. Executa o Conselho.
5. Visualiza pareceres independentes dos agentes Financeiro, Social, Técnico e Orçamentário.
6. O Agente de Pontes identifica possíveis instituições âncora e sugere um cenário de articulação, sem presumir contratos firmados.
7. Motor determinístico compara cenário base e cenário com pontes.
8. O Guardião sintetiza convergências, divergências, incertezas e recomenda `INVESTIR`, `PILOTAR`, `AGUARDAR` ou `REVISAO_HUMANA`.
9. Usuário consulta evidências, limitações e trilha de auditoria; pode exportar relatório JSON.

### 1.4 Fora do escopo do MVP

Previsão precisa de ROI, CAPEX real, geoprocessamento de engenharia, negociação automática com escolas, integração em tempo real com sistemas de operadoras, contratação de serviços, classificação de pessoas, scraping irrestrito, RAG genérico, banco vetorial e deployment público obrigatório.

### 1.5 Critérios de sucesso observáveis

- Um comando inicia a API e outro inicia o frontend, com README reproduzível.
- Três localidades de demonstração com dados identificados como sintéticos ou oficiais.
- Pelo menos um fluxo ponta a ponta sem serviços pagos e sem credenciais externas.
- Pareceres de agentes exibem justificativa, dados usados, limitações e incertezas.
- Cenários base e pontes são calculados por funções Python testáveis, não por aritmética inventada pelo LLM.
- Recomendações possuem regras de segurança, rastreabilidade e revisão humana.
- Testes automatizados cobrem cálculos, contratos e orquestração em modo mock.

---

## 2. Regras permanentes para Codex / AGENTS.md

1. **Linguagem:** código, variáveis e endpoints em inglês técnico; mensagens, explicações e documentação do produto em pt-BR.
2. **Stack:** Python 3.11+; FastAPI; Pydantic v2; LangGraph; pandas; SQLite; Streamlit; pytest; ruff; httpx; Ollama opcional. Preferir bibliotecas livres e evitar dependências supérfluas.
3. **Execução offline:** toda funcionalidade de demonstração deve funcionar em `LLM_PROVIDER=mock`. `LLM_PROVIDER=ollama` é modo alternativo. Nenhuma chave paga obrigatória.
4. **Sem dados falsamente reais:** fixtures sintéticas devem conter `is_synthetic=true`, `source_name="Cenário sintético de demonstração"` e jamais ser apresentadas como dados oficiais.
5. **Dados externos:** registrar URL de origem, entidade responsável, ano de referência, data de coleta, licença/termos, granularidade e transformações. Não armazenar dados pessoais.
6. **LLM não faz contas finais:** cálculos de scores, orçamento e cenários são funções determinísticas; agentes interpretam indicadores e produzem pareceres estruturados.
7. **LLM não inventa evidência:** cada afirmação relevante deve referenciar `evidence_ids` existentes. Se faltar evidência, registrar ausência.
8. **Validação obrigatória:** toda saída de modelo passa por Pydantic; falha gera erro controlado ou fallback explicitamente sinalizado. Nunca converter saída inválida em parecer “confiável”.
9. **Não exagerar certeza:** `confidence_level` é classificação qualitativa de completude das evidências, nunca probabilidade calibrada de sucesso.
10. **Segurança:** sem execução de código originado de prompts, sem acesso irrestrito a filesystem por agentes, sem envio de dados a provedores externos por padrão, sem credenciais no Git.
11. **Determinismo:** simulações com fórmulas documentadas, valores limitados, unidades explícitas e testes de fronteira.
12. **Testes:** qualquer nova regra de negócio precisa de testes unitários; qualquer endpoint novo precisa de teste de contrato.
13. **Escopo:** não refatorar componentes alheios à fase atual sem justificativa; evitar abstrações prematuras.
14. **Observabilidade:** usar logging estruturado com `analysis_id`; não registrar prompts com conteúdo sensível.
15. **Documentação:** atualizar README, changelog e decisões arquiteturais ao modificar interfaces públicas.
16. **Final de cada fase:** executar lint e testes, reportar arquivos alterados, comandos executados, resultados, limitações e próxima fase.
17. **IBM Bob:** reservar e documentar tarefas efetivamente realizadas no Bob IDE; não inventar relatórios nem afirmar utilização do Bob caso não tenha ocorrido.

---

## 3. Arquitetura proposta

```text
┌───────────────────────┐
│ Streamlit dashboard   │
└───────────┬───────────┘
            │ HTTP JSON
┌───────────▼───────────┐
│ FastAPI               │
│ routes / schemas      │
└───────────┬───────────┘
            │
┌───────────▼────────────────────────────────────────────┐
│ Application service / LangGraph                        │
│ load evidence → independent reviewers                 │
│ → Bridges → deterministic scenario engine             │
│ → limited challenge round → Guardian → persistence    │
└──────┬───────────┬──────────────┬───────────────────────┘
       │           │              │
  SQLite       LLM adapter     Dataset repository
  audit        mock/ollama     curated CSV/JSON
```

**Por que LangGraph:** estado tipado e fluxo explícito; é possível testar nós individualmente e trocar o modelo. **Por que Streamlit:** entrega rápida de dashboard. **Por que SQLite:** persistência mínima e local. **Por que adapter de LLM:** alternar mock/Ollama sem alterar agentes.

### 3.1 Estrutura de arquivos obrigatória

```text
conecta-conselho/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── IMPLEMENTACAO_CODEX.md
│   ├── ARCHITECTURE.md
│   ├── DATA_CATALOG.md
│   ├── METHODOLOGY.md
│   ├── LIMITATIONS.md
│   ├── DEMO_SCRIPT.md
│   ├── IBM_BOB_USAGE.md
│   ├── adr/
│   │   ├── 0001-local-first.md
│   │   └── 0002-deterministic-scoring.md
│   └── bob-session-reports/.gitkeep
├── data/
│   ├── README.md
│   ├── fixtures/municipalities.synthetic.json
│   ├── curated/.gitkeep
│   └── raw/.gitkeep
├── scripts/
│   ├── validate_data.py
│   └── seed_demo.py
├── src/conecta_conselho/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── api/
│   │   ├── routes_health.py
│   │   ├── routes_municipalities.py
│   │   └── routes_analyses.py
│   ├── domain/
│   │   ├── enums.py
│   │   ├── models.py
│   │   ├── scoring.py
│   │   └── simulation.py
│   ├── data/
│   │   ├── repository.py
│   │   ├── fixtures.py
│   │   └── validation.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── mock.py
│   │   └── ollama.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── financial.py
│   │   ├── social.py
│   │   ├── technical.py
│   │   ├── budget.py
│   │   ├── bridges.py
│   │   ├── guardian.py
│   │   └── prompts/
│   │       ├── financial.md
│   │       ├── social.md
│   │       ├── technical.md
│   │       ├── budget.md
│   │       ├── bridges.md
│   │       └── guardian.md
│   ├── orchestration/
│   │   ├── state.py
│   │   ├── graph.py
│   │   └── nodes.py
│   ├── services/analysis_service.py
│   └── persistence/sqlite_store.py
├── frontend/
│   ├── app.py
│   └── api_client.py
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── e2e/
```

### 3.2 Dependências e comandos de bootstrap

Criar `pyproject.toml` com dependências versionadas em faixas compatíveis e extras `dev` e `ollama`. Bibliotecas esperadas: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `langgraph`, `pandas`, `streamlit`, `plotly`, `httpx`; `langchain-ollama` apenas no extra `ollama`; `pytest`, `ruff`, `pytest-cov` no extra `dev`. Verificar versões reais disponíveis no ambiente, sem inventar pins.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python scripts/seed_demo.py
uvicorn conecta_conselho.main:app --reload
# outro terminal:
streamlit run frontend/app.py
# validação:
ruff check .
pytest -q
```

`.env.example` deve conter `LLM_PROVIDER=mock`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=` (preencher após verificar modelo instalado), `DATABASE_URL=sqlite:///./conecta_conselho.db`, `DATA_MODE=synthetic`, `API_BASE_URL=http://localhost:8000`, `LOG_LEVEL=INFO`, `MAX_AGENT_RETRIES=1`. Nunca exigir Ollama para testes padrão.

---

## 4. Modelo de dados e contratos

### 4.1 Princípio

Cada valor de entrada precisa ser classificado como **observado**, **estimado**, **hipotético** ou **indisponível**. `null` significa dado ausente; **zero não significa ausência de informação**. Todo indicador tem unidade e referência de fonte.

### 4.2 Tipos Pydantic a implementar

Implementar modelos com `Field` e validações adequadas:

```python
from enum import Enum
from pydantic import BaseModel, Field

class EvidenceKind(str, Enum):
    OBSERVED = 'observed'
    ESTIMATED = 'estimated'
    HYPOTHETICAL = 'hypothetical'
    UNAVAILABLE = 'unavailable'

class Evidence(BaseModel):
    evidence_id: str
    indicator: str
    value: float | int | str | None
    unit: str | None = None
    kind: EvidenceKind
    source_name: str
    source_url: str | None = None
    reference_year: int | None = None
    collected_at: str | None = None
    is_synthetic: bool = False
    limitations: list[str] = Field(default_factory=list)

class AnchorInstitution(BaseModel):
    institution_id: str
    name: str
    institution_type: str  # school, health_unit, other_public
    municipality_code: str
    evidence_ids: list[str] = Field(default_factory=list)
    connectivity_status: str = 'unknown'
    is_synthetic: bool = False

class Municipality(BaseModel):
    municipality_code: str  # IBGE code, 7 digits when official
    name: str
    state_code: str
    indicators: list[Evidence]
    anchor_institutions: list[AnchorInstitution]
    is_synthetic: bool

class AgentOpinion(BaseModel):
    agent_name: str
    position: str  # favorable, conditional, unfavorable, insufficient_data
    summary: str
    supporting_evidence_ids: list[str]
    risks: list[str]
    assumptions: list[str]
    missing_data: list[str]
    confidence_level: str  # low, medium, high (evidence quality only)

class SimulationParameters(BaseModel):
    budget_ceiling_brl: float = Field(ge=0)
    estimated_base_cost_brl: float | None = Field(default=None, ge=0)
    estimated_cost_per_anchor_brl: float | None = Field(default=None, ge=0)
    hypothetical_monthly_anchor_revenue_brl: float | None = Field(default=None, ge=0)
    scenario_horizon_months: int = Field(default=12, ge=1, le=120)

class ScenarioResult(BaseModel):
    scenario_name: str
    selected_anchor_ids: list[str]
    estimated_total_cost_brl: float | None
    hypothetical_anchor_revenue_brl: float | None
    hypothetical_net_balance_brl: float | None
    within_budget: bool | None
    calculation_notes: list[str]
    warnings: list[str]

class Decision(str, Enum):
    INVEST = 'INVESTIR'
    PILOT = 'PILOTAR'
    WAIT = 'AGUARDAR'
    HUMAN_REVIEW = 'REVISAO_HUMANA'
```

Criar adicionalmente `AnalysisRequest(municipality_code, parameters, selected_anchor_ids?)`, `AnalysisResult(analysis_id, created_at, municipality, opinions, bridge_proposal, baseline, with_bridges, disagreements, guardian, evidence_catalog, warnings, mode)` e `GuardianDecision(decision, rationale, conditions, blockers, unresolved_questions, cited_evidence_ids, requires_human_approval=True)`. Definir todos os campos explicitamente no código e publicar JSON Schema na documentação.

**Regras de validação:** IDs de evidência referenciados devem existir no catálogo; `municipality_code` não pode apontar para localidade desconhecida; instituições devem pertencer à localidade; valores monetários não negativos; status de conectividade `unknown` não pode ser interpretado como `unconnected`; entradas sintéticas não podem perder o sinalizador.

### 4.3 Fixtures sintéticas

Criar três localidades fictícias claramente nomeadas `Município Demonstração A/B/C`, com códigos internos `DEMO001/DEMO002/DEMO003` (não simular códigos oficiais do IBGE). Usar perfis contrastantes:

- **A:** maior potencial de demanda, menor déficit social, custo estimado moderado.
- **B:** maior déficit social, orçamento apertado, várias instituições âncora candidatas.
- **C:** restrição técnica mais severa, evidências incompletas, caso propício à revisão humana.

Para cada localidade, fornecer 8–12 indicadores com `evidence_id` estável e 2–4 instituições fictícias. Números de exemplo devem estar marcados como **hipotéticos**; não usar nomes de escolas ou hospitais reais com dados inventados. Documentar no `data/README.md` que são fixtures para testes e demo, sem validade empírica.

### 4.4 Catálogo de dados reais (fase opcional, posterior ao MVP)

Fontes candidatas a verificar antes de importar: Anatel (indicadores e cobertura), IBGE (códigos municipais e indicadores demográficos), INEP (escolas), CNES/DATASUS (estabelecimentos de saúde), OpenStreetMap (geometria e pontos de interesse). O Codex **não deve presumir** que toda fonte mede “ausência de conectividade” ou que dados de municípios sejam comparáveis sem ajuste de ano/granularidade. Criar `docs/DATA_CATALOG.md` com: URL oficial, licença, data, colunas, unidades, período, granularidade, transformações e limitações. Dados de escolas/saúde são **candidatos a parceria**, não clientes confirmados. Não coletar nomes de responsáveis, CPF, telefones pessoais nem dados sensíveis.

---

## 5. Regras de negócio e cálculos

### 5.1 Separação entre observação e hipótese

`observed`: valor proveniente de fonte identificada; `estimated`: inferência calculada com método explícito; `hypothetical`: parâmetro escolhido para simulação; `unavailable`: informação não existente ou não verificável. Nenhum relatório pode omitir essa distinção.

### 5.2 Scores descritivos

Implementar `normalize_min_max(value, lower, upper)` com saturação [0,1], erro se `upper <= lower` e testes de fronteira. Os limites devem ser declarados em configuração de metodologia, **não inferidos silenciosamente dos três municípios**. Criar scores de `market_opportunity`, `social_priority`, `technical_feasibility` apenas se indicadores correspondentes estiverem disponíveis. Pesos configuráveis, soma 1.0, e documentação de que scores são **heurísticas de triagem**, não previsões validadas.

**Política de dados ausentes:** não imputar zero. Se faltarem indicadores críticos, devolver score `null`, explicar motivo e elevar recomendação para `REVISAO_HUMANA` ou `PILOTAR` conforme regras. Não gerar ranking definitivo se as bases forem incomparáveis.

### 5.3 Motor de cenários — fórmula ilustrativa

`baseline_cost = estimated_base_cost_brl` se fornecido, senão `null`.

`bridge_extra_cost = count(selected_anchor_ids) * estimated_cost_per_anchor_brl` somente se custo por âncora fornecido.

`with_bridges_cost = baseline_cost + bridge_extra_cost` somente se ambos conhecidos.

`anchor_revenue = count(selected_anchor_ids) * hypothetical_monthly_anchor_revenue_brl * scenario_horizon_months` somente se receita hipotética fornecida.

`hypothetical_net_balance = anchor_revenue - bridge_extra_cost` somente se ambos conhecidos. **Esse saldo incremental não é ROI, lucro, NPV, viabilidade econômica nem receita contratada.** Não calcular economia, adoção, receita residencial, subsídio ou redução de CAPEX sem premissas explicitadas.

`within_budget = total_cost <= budget_ceiling` se custo conhecido, senão `null`.

**Cenário base:** zero instituições âncora; custo base; receita âncora zero, com aviso de que não inclui outras receitas. **Cenário pontes:** somente instituições selecionadas e qualificadas como candidatas; comparação lado a lado. Exibir no dashboard o rótulo “Simulação hipotética — não representa proposta comercial ou orçamento de engenharia”.

### 5.4 Regras determinísticas de recomendação / segurança

O Guardião pode redigir a justificativa, mas o sistema deve aplicar *hard gates* antes de aceitar decisão:

1. Se evidência crítica ausente (ex.: nenhum indicador de conectividade ou custo de cenário desconhecido), impedir `INVESTIR` e sinalizar `REVISAO_HUMANA`.
2. Se `within_budget == False`, impedir `INVESTIR` no cenário correspondente; sugerir `PILOTAR` apenas se houver escopo reduzido e custo conhecido, caso contrário `AGUARDAR`/`REVISAO_HUMANA`.
3. Se existem divergências materiais entre parecer técnico e financeiro, exigir justificativa explícita e revisão humana.
4. Se qualquer agente usa ID de evidência inexistente, invalidar parecer e registrar erro, nunca aceitá-lo silenciosamente.
5. Se só existem dados sintéticos, decisões são **demonstrações**, nunca recomendações operacionais reais.
6. Se o LLM falhar, devolver resultado parcial com `status=degraded` e erros identificados; nunca fabricar um parecer “normal”.
7. Toda decisão contém `requires_human_approval=True`.

Criar função `apply_decision_guards()` isolada e unit-testable. Regras de decisão adicionais são heurísticas e precisam estar em `METHODOLOGY.md`.

---

## 6. Agentes especializados

### 6.1 Interface comum

Cada agente recebe `Municipality`, catálogo de evidências pertinente, parâmetros de cenário e (quando aplicável) opiniões anteriores. Cada agente devolve `AgentOpinion` validado. Não permitir que agentes modifiquem dados observados. Usar `LLMClient.generate_structured(system_prompt, payload, schema)` com adapters `MockLLMClient` e `OllamaLLMClient`. Preferir saída JSON validada; realizar no máximo um retry com feedback de erro de schema; se falhar, registrar falha controlada.

**Prompt base obrigatório para todos os agentes:**

```text
Você é um analista especializado em uma prova de conceito de expansão de conectividade.
Use EXCLUSIVAMENTE as evidências estruturadas recebidas. Não invente números,
fontes, contratos, cobertura ou resultados. Diferencie fatos, estimativas e
hipóteses. Cite IDs de evidência existentes. Se faltar informação, declare-a.
Sua tarefa é produzir JSON estritamente compatível com o schema fornecido.
Você não toma decisões finais nem executa ações externas.
```

### 6.2 Agente Financeiro (`financial.py`)

Avalia sinais de demanda potencial e sustentabilidade econômica **sem afirmar ROI**. Examina população, indicadores socioeconômicos, proxy de demanda, custos hipotéticos e lacunas de preço/taxa de adesão. Produz posição `favorable/conditional/unfavorable/insufficient_data`, riscos, premissas e perguntas para diligência. **Proibido:** inventar ARPU, margem, market share, clientes ou payback.

**Aceite:** dado ausente gera `missing_data`; qualquer conclusão tem evidência rastreável; testes incluem demanda promissora com custo desconhecido.

### 6.3 Agente Social (`social.py`)

Analisa déficit de acesso, relevância para educação/saúde, possíveis efeitos distributivos e riscos de exclusão. Distingue indicadores de vulnerabilidade de prova de demanda contratante. Não usar atributos pessoais. **Aceite:** valor social alto pode coexistir com risco financeiro alto; não força `INVESTIR`.

### 6.4 Agente Técnico (`technical.py`)

Avalia cobertura declarada, restrições geográficas e informações sobre infraestrutura disponíveis. Sem medições de rede, sinalizar necessidade de survey de campo e capacidade de backhaul. **Proibido:** afirmar disponibilidade de fibra, espectro, torres ou custos técnicos sem evidência. **Aceite:** falta de dados técnicos críticos gera posição condicional ou insuficiente.

### 6.5 Agente Orçamentário (`budget.py`)

Compara custo hipotético e teto informado por meio do motor determinístico. Não recalcula valores por texto livre. Sugere priorização e alternativas de piloto, sem afirmar aprovação orçamentária. **Aceite:** `within_budget=null` não é interpretado como “cabe no orçamento”.

### 6.6 Agente de Pontes (`bridges.py`)

Identifica instituições âncora **candidatas**, com base na lista de instituições do município. Para cada sugestão devolver `institution_id`, `rationale`, `evidence_ids`, `assumptions`, `partnership_status="unverified"`, `priority` e `caveats`. Não criar instituições que não estejam no dataset. Não afirmar conectividade ausente quando status é desconhecido. O agente **não calcula receita**: envia lista de candidatos para o simulador. O usuário pode incluir/remover instituições antes de recalcular cenário.

**Aceite:** seleção só aceita IDs existentes; se não há instituições, retorna lista vazia e nota; cenário sem pontes é idêntico ao base.

### 6.7 Rodada de contestação (`challenge_round`)

Após simulação, executar **uma única rodada** para evitar loops e custo computacional. Confrontar ao menos dois pares de perspectivas (ex.: social vs financeiro, técnico vs orçamento). Implementação mínima: função determinística detecta divergências com base em posições e evidências, produz `Disagreement(topic, opinions, resolution_status, questions)`. Opcionalmente pedir ao LLM síntese textual, mas sem alterar números. Não fazer agentes conversarem indefinidamente.

### 6.8 Guardião (`guardian.py`)

Recebe todas as opiniões, divergências, cenários e avisos. Produz decisão preliminar estruturada com racional, condições, bloqueios, questões pendentes e evidências. Em seguida `apply_decision_guards` pode ajustar/bloquear a decisão; registrar `original_decision`, `final_decision` e `guard_reasons` quando houver intervenção. A explicação final deve reconhecer conflito entre impacto social e custo/risco técnico. **Aceite:** teste comprova que decisão insegura proposta pelo mock é bloqueada.

---

## 7. Orquestração LangGraph

### 7.1 Estado

Criar `CouncilState` (`TypedDict` ou Pydantic compatível com LangGraph) com campos: `analysis_id`, `municipality`, `parameters`, `evidence_catalog`, `opinions`, `bridge_proposal`, `selected_anchor_ids`, `baseline`, `with_bridges`, `disagreements`, `guardian_draft`, `guardian_final`, `warnings`, `errors`, `status`. Evitar mutação compartilhada fora do contrato de estado; usar reducers apropriados se nós paralelos atualizarem `opinions`.

### 7.2 Grafo

```text
START
  → validate_input
  → load_municipality
  → [financial, social, technical, budget]  (paralelos quando seguro)
  → collect_opinions
  → bridges
  → simulate_scenarios
  → challenge_round
  → guardian
  → apply_guards
  → persist_result
  → END
```

**Implementação incremental:** inicialmente executar revisores sequencialmente se paralelismo dificultar teste; evoluir depois para `Send`/reducers. O grafo precisa ter limite de execução, timeout por chamada LLM e tratamento de exceções. `persist_result` não pode registrar análise incompleta como `completed`. O endpoint pode ser síncrono no MVP; não adicionar filas/Redis sem necessidade.

### 7.3 Modos

- `mock`: respostas coerentes e determinísticas com base em evidências, usando funções e templates; **não** alegar que esse modo demonstra raciocínio de IA generativa.
- `ollama`: modelo local instalado pelo usuário; prompt versionado, temperatura baixa quando suportada, validação Pydantic, timeout, retry limitado. Exibir nome do modelo usado.

**Demonstração honesta:** testar o sistema com Ollama antes da apresentação; manter mock como contingência operacional, informando o modo exibido.

---

## 8. API HTTP — contrato obrigatório

`GET /health` → `{ "status": "ok", "mode": "mock", "version": "..." }`.

`GET /api/v1/municipalities` → lista resumida `{ municipality_code, name, state_code, is_synthetic }`.

`GET /api/v1/municipalities/{code}` → `Municipality` completo com evidências e instituições.

`POST /api/v1/analyses` → recebe `AnalysisRequest`, executa grafo e retorna `AnalysisResult`. Resposta 422 para input inválido, 404 para localidade desconhecida, 503 quando provedor LLM indisponível e fallback desabilitado. Se usar fallback, retornar modo e `status=degraded`.

`GET /api/v1/analyses/{analysis_id}` → resultado persistido ou 404.

`GET /api/v1/analyses/{analysis_id}/export` → JSON com resultados, fontes, hipóteses e data de execução; `Content-Disposition` de download.

**Segurança básica:** validar tamanho de payload, limitar número de instituições por análise, usar timeouts, CORS restrito ao frontend local e não aceitar comandos de shell no input. Documentar exemplos de request/response em `README.md` e usar `/docs` gerado pelo FastAPI.

### 8.1 Exemplo de request

```json
{
  "municipality_code": "DEMO002",
  "parameters": {
    "budget_ceiling_brl": 500000,
    "estimated_base_cost_brl": 350000,
    "estimated_cost_per_anchor_brl": 20000,
    "hypothetical_monthly_anchor_revenue_brl": 2500,
    "scenario_horizon_months": 12
  },
  "selected_anchor_ids": ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]
}
```

**Atenção:** todos os valores do exemplo são arbitrários e exclusivamente hipotéticos.

---

## 9. Frontend Streamlit

### 9.1 Páginas / seções

**A. Introdução:** propósito, caráter demonstrativo, diferença entre dados oficiais e sintéticos.

**B. Seleção:** `selectbox` de municípios; cartões de indicadores com fonte, ano, unidade, natureza da evidência e alertas.

**C. Parâmetros:** formulário com teto orçamentário e premissas de custo/receita hipotéticas; `number_input` com mínimos e ajuda contextual; aviso permanente de simulação.

**D. Conselho:** botão “Executar análise”; indicador de carregamento; mostrar modo mock/ollama; apresentar quatro pareceres em cartões expansíveis.

**E. Pontes:** lista de instituições sugeridas, tipo, justificativa e status “parceria não verificada”; permitir selecionar instituições e executar nova análise (ou recalcular cenário via endpoint dedicado se implementado posteriormente).

**F. Comparação:** tabela lado a lado `Base` × `Com Pontes`, exibindo custo, saldo incremental hipotético, orçamento e alertas. `null` deve aparecer como “Não disponível”, nunca 0.

**G. Guardião:** recomendação em destaque, condições, divergências, riscos, motivos de revisão humana e links internos para evidências.

**H. Auditoria:** tabela de fontes, hipóteses, data, modelo e ID de análise; botão “Exportar JSON”.

### 9.2 Estados de interface

Tratar loading, ausência de município, validação, API offline, LLM offline, resultado degradado e falha de exportação. Nunca esconder erros atrás de mensagem de sucesso. Usar acessibilidade básica: labels claros, cores acompanhadas de texto, contraste e unidades visíveis.

---

## 10. Persistência e auditoria

SQLite com tabela `analyses`: `analysis_id TEXT PRIMARY KEY`, `municipality_code TEXT`, `created_at TEXT`, `mode TEXT`, `status TEXT`, `request_json TEXT`, `result_json TEXT`, `model_name TEXT NULL`, `prompt_versions_json TEXT`, `error_json TEXT NULL`. Usar queries parametrizadas e serialização Pydantic. Não persistir dados pessoais. Gerar UUID para `analysis_id`. Documentar política de limpeza de dados de demonstração. Registrar tempos de execução por nó em log quando possível.

---

## 11. Plano de implementação fase a fase

### Fase 0 — Inspeção, ADRs e ambiente

**Objetivo:** estabelecer projeto executável sem depender de LLM.

**Passos para Codex:** (1) inspecionar arquivos existentes e preservar trabalho; (2) criar estrutura; (3) configurar `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`; (4) criar `AGENTS.md`; (5) registrar ADRs de arquitetura local-first e cálculos determinísticos; (6) criar endpoint `/health`; (7) configurar ruff/pytest; (8) executar comandos e registrar resultado.

**Aceite:** `pytest -q` e `ruff check .` passam; `/health` responde; nenhum segredo versionado.

### Fase 1 — Domínio, fixtures e validação

**Passos:** (1) implementar enums/modelos; (2) criar fixtures A/B/C sintéticas; (3) criar loader e repository; (4) validar unicidade de IDs, integridade referencial e tipos; (5) implementar listagem/detalhe de municípios; (6) documentar schema e fixture; (7) testes unitários e HTTP.

**Aceite:** três municípios aparecem na API; referências inválidas rejeitadas; indicador ausente continua `null`; nenhuma fixture se apresenta como dado oficial.

### Fase 2 — Motor determinístico

**Passos:** (1) implementar normalização e scores com configuração explícita; (2) implementar `simulate_baseline` e `simulate_with_bridges`; (3) criar comparação; (4) criar `apply_decision_guards`; (5) escrever testes de números, `null`, teto exato, teto ultrapassado, zero âncoras, âncoras duplicadas, valores negativos e orçamento desconhecido; (6) documentar metodologia.

**Aceite:** cálculo reproduzível e idêntico para mesma entrada; sem divisão por zero; sem extrapolar significado de saldo hipotético.

### Fase 3 — Adapter LLM e agentes iniciais

**Passos:** (1) interface abstrata LLM; (2) adapter mock determinístico; (3) adapter Ollama opcional com timeout/JSON/validação; (4) prompt base; (5) implementar Financeiro e Social; (6) testes de schema, IDs inexistentes, resposta inválida, timeout e ausência de evidências; (7) logar provider e versão de prompt.

**Aceite:** ambos os agentes produzem JSON válido em mock; falha de Ollama não vira sucesso silencioso.

### Fase 4 — Agentes Técnico e Orçamentário

**Passos:** (1) implementar prompts e funções; (2) reutilizar funções de score/cenário, sem duplicar matemática; (3) criar testes com evidências técnicas insuficientes e orçamento desconhecido; (4) documentar limites de cada análise.

**Aceite:** quatro pareceres independentes, com riscos e evidências, sem métricas inventadas.

### Fase 5 — Agente de Pontes e simulação

**Passos:** (1) implementar ranking qualitativo de instituições candidatas; (2) validar IDs e município; (3) aplicar seleção de âncoras; (4) simular base e pontes; (5) comparar custos e receita hipotética incremental; (6) documentar premissas; (7) testar 0, 1 e várias instituições e duplicidades.

**Aceite:** demonstração B apresenta comparação antes/depois; nenhuma parceria tratada como firmada.

### Fase 6 — Contestação, Guardião e LangGraph

**Passos:** (1) criar `CouncilState`; (2) implementar nós; (3) montar grafo acíclico; (4) implementar divergências e síntese; (5) integrar Guardião e hard gates; (6) registrar estado final e erros; (7) testar fluxo completo em mock; (8) testar decisão `INVESTIR` bloqueada por ausência de custo e conflito técnico.

**Aceite:** `POST /analyses` produz resultado consistente; estado auditável; sem loops; nenhuma decisão de investimento irrestrita.

### Fase 7 — API completa e persistência

**Passos:** (1) service de análise; (2) endpoints POST/GET/export; (3) SQLite e migração inicial simples; (4) schemas OpenAPI; (5) códigos HTTP e exceções; (6) testes de integração; (7) logs com `analysis_id`.

**Aceite:** resultado persistido pode ser recuperado e exportado; reinício da API não apaga análises; dados de demo podem ser resetados por script.

### Fase 8 — Dashboard

**Passos:** (1) cliente HTTP; (2) seleção de município; (3) cards de evidências; (4) formulário de premissas; (5) botão de execução; (6) quatro pareceres; (7) Pontes; (8) cenários; (9) Guardião; (10) auditoria/exportação; (11) estados de erro; (12) smoke test manual documentado.

**Aceite:** jornada da seção 1.3 executável sem terminal após serviços iniciarem.

### Fase 9 — Dados reais controlados (somente após MVP estável)

**Passos:** (1) selecionar até três municípios reais; (2) baixar dados apenas de fontes com licença adequada; (3) documentar fonte, ano e granularidade; (4) criar scripts de ingestão reexecutáveis; (5) validar join por código IBGE; (6) tratar dados ausentes; (7) comparar valores amostrais com fonte; (8) diferenciar real de hipótese na interface.

**Aceite:** nenhum valor real sem fonte; se dados não forem suficientes, manter demonstração sintética e declarar limitação. **Não bloquear a entrega pela fase 9.**

### Fase 10 — Qualidade, apresentação e submissão

**Passos:** (1) rodar testes/lint; (2) realizar smoke test mock e, se possível, Ollama; (3) capturar exemplos de análises A/B/C; (4) revisar linguagem de certeza; (5) completar `ARCHITECTURE`, `METHODOLOGY`, `LIMITATIONS`, `DATA_CATALOG`; (6) criar `DEMO_SCRIPT.md` para vídeo de 3 minutos; (7) registrar efetivamente uso do IBM Bob IDE e exportar relatórios de sessão; (8) redigir declaração tecnológica e problema/solução; (9) validar checklist de submissão.

**Aceite:** repositório reproduzível; demo sem dependências pagas; relatórios Bob reais presentes; entregáveis documentados.

---

## 12. Matriz mínima de testes

| ID | Tipo | Caso | Resultado esperado |
|---|---|---|---|
| T01 | Unitário | Normalização abaixo/acima do limite | Saturação 0/1 |
| T02 | Unitário | Limites iguais | Erro explícito |
| T03 | Unitário | Custo ausente | `within_budget=null` |
| T04 | Unitário | Custo igual ao teto | `within_budget=true` |
| T05 | Unitário | Custo acima do teto | `within_budget=false` |
| T06 | Unitário | Nenhuma âncora selecionada | Cenário igual ao base |
| T07 | Unitário | ID de âncora inexistente | Erro de validação |
| T08 | Unitário | ID duplicado | Rejeição ou deduplicação documentada |
| T09 | Unitário | Evidência inexistente citada | Parecer inválido |
| T10 | Unitário | Só dados sintéticos | Aviso de demo obrigatório |
| T11 | Unitário | Guardião sugere investir sem custo | Decisão bloqueada |
| T12 | Unitário | Guardião ignora conflito técnico | Revisão humana obrigatória |
| T13 | Integração | Análise completa mock | Resultado validado |
| T14 | Integração | Ollama indisponível | Erro/fallback sinalizado |
| T15 | API | Município inexistente | HTTP 404 |
| T16 | API | Payload inválido | HTTP 422 |
| T17 | API | Criar, recuperar e exportar | JSON consistente |
| T18 | Persistência | Reiniciar API | Análise preservada |
| T19 | E2E manual | Dashboard B com pontes | Comparação visível |
| T20 | E2E manual | API fora do ar | Erro legível |

Executar `pytest --cov=conecta_conselho --cov-report=term-missing`; buscar boa cobertura de `domain/` e regras críticas, sem impor porcentagem arbitrária que incentive testes superficiais.

---

## 13. Ordem de prioridade em caso de prazo curto

**P0 (indispensável):** domínio/fixtures, motor de cenários, 4 agentes em mock, Pontes, Guardião com hard gates, endpoint de análise, dashboard mínimo, testes essenciais, README, evidência real de uso do IBM Bob.

**P1 (diferencial):** LangGraph completo, Ollama funcionando, divergências, persistência, exportação, três municípios comparáveis.

**P2 (não sacrificar P0/P1):** ingestão automatizada de dados reais, mapas, gráficos sofisticados, ranking entre municípios, paralelismo de agentes, deployment público.

**Estratégia de corte:** se o prazo apertar, manter Financeiro + Social + Pontes + Guardião, preservando simulação e revisão humana. Não cortar validação, provenance nem testes críticos.

---

## 14. Prompts prontos para executar no Codex

### Prompt de início (colar na primeira sessão)

```text
Você atuará como engenheiro de software responsável pelo projeto Conecta Conselho.
Leia integralmente docs/IMPLEMENTACAO_CODEX.md e AGENTS.md. Antes de codificar:
1. Inspecione o repositório e informe o que já existe.
2. Identifique a fase atual e dependências pendentes.
3. Proponha um plano curto de alterações para a fase indicada.
4. Implemente somente essa fase, sem introduzir funcionalidades futuras.
5. Crie ou atualize testes, execute ruff e pytest e corrija falhas.
6. Atualize a documentação pertinente.
7. Responda com: resumo, arquivos alterados, testes executados/resultados,
   riscos, pendências e próximo prompt recomendado.
Restrições: tudo deve funcionar em LLM_PROVIDER=mock; não invente dados;
não faça alegações sobre uso do IBM Bob sem evidência; não use serviços pagos.
Comece pela FASE 0.
```

### Prompt de continuação (usar a cada fase)

```text
Leia docs/IMPLEMENTACAO_CODEX.md e AGENTS.md. Implemente a FASE [NOME/NÚMERO]
seguindo exatamente passos e critérios de aceite. Preserve as interfaces
existentes, execute testes de regressão, registre quaisquer divergências
entre implementação e especificação, e não avance para a fase seguinte.
Ao final, informe comandos executados e seus resultados reais.
```

### Prompt de revisão arquitetural

```text
Faça uma revisão de código sem modificar arquivos inicialmente. Verifique:
separação domínio/LLM, validação Pydantic, integridade de evidências,
tratamento de null, cálculos determinísticos, decisões bloqueadas por hard
gates, ausência de dados pessoais, modo mock, erros HTTP, testes e aderência
a docs/IMPLEMENTACAO_CODEX.md. Classifique achados por severidade,
indique arquivos/linhas e proponha correções mínimas. Aguarde autorização
antes de refatorações amplas.
```

### Prompt de integração Ollama

```text
Implemente ou valide o adapter Ollama opcional. Primeiro verifique se o
servidor local e um modelo compatível estão disponíveis; não presuma nome
ou versão. Preserve mock como padrão. Garanta timeout, JSON estruturado,
validação Pydantic, retry limitado, erros explícitos e testes com provider
simulado. Documente comandos de instalação sem exigir serviços pagos.
```

### Prompt de preparação da demo

```text
Execute a checklist da FASE 10. Não declare sucesso sem testar. Produza
um roteiro de demonstração de 3 minutos que mostre o problema, usuário,
quatro perspectivas, Pontes, cenários, Guardião, incertezas e tecnologia.
Liste os artefatos obrigatórios ainda pendentes, inclusive relatórios
reais do IBM Bob IDE, sem inventá-los.
```

---

## 15. Checklist de aceite final

- [ ] Ambiente criado a partir do README em máquina limpa.
- [ ] `/health`, listagem de municípios e análise respondem.
- [ ] Três localidades sintéticas claramente rotuladas.
- [ ] Quatro pareceres independentes e rastreáveis.
- [ ] Pontes identifica apenas instituições existentes e não presume parceria.
- [ ] Cenários base/pontes calculados determinísticamente.
- [ ] Guardião expõe conflitos e bloqueia decisões inseguras.
- [ ] Todas as saídas incluem hipóteses, fontes e limitações.
- [ ] Modo mock funciona offline; modo Ollama é opcional e documentado.
- [ ] Testes e lint executados com resultado registrado.
- [ ] Dashboard completo e exportação JSON funcionando.
- [ ] Nenhum dado pessoal/confidencial ou segredo no Git.
- [ ] README, arquitetura, metodologia e limitações atualizados.
- [ ] Uso efetivo do IBM Bob IDE documentado, com relatórios de sessão exportados.
- [ ] Declaração de problema/solução, declaração tecnológica e vídeo de 3 minutos preparados.

---

## 16. Referências de origem e limitações desta especificação

**Materiais oficiais fornecidos pela equipe:**

1. `2026 AI Experiential Learning Lab with Bob - Industry Challenges_Portuguese.pdf` — Trilha 3, “Telecomunicações inteligentes com Fundação Telefônica”, problema de expansão da conectividade e uso de dados geoespaciais, demográficos, socioeconômicos e de rede.
2. `2H26 GuideBob_IBM SkillsBuild_AI Experiential Learning Lab BR.pdf` — regras de tecnologia, IBM Bob IDE obrigatório, relatórios de sessões, cuidados com dados, entregáveis e orientação de submissão.

**Elementos propostos especificamente para o Conecta Conselho:** seis agentes, Agente de Pontes, Guardião, cenário hipotético, arquitetura Python/LangGraph/Ollama/Streamlit, contratos JSON, fórmulas de simulação e critérios de aceite. Essas escolhas **não são prescritas** pelos PDFs oficiais; são decisões de projeto para construir um MVP viável.

**Limitação metodológica:** dados públicos agregados e indicadores municipais não bastam para decidir investimento real em infraestrutura. A POC é ferramenta de priorização e discussão; decisões operacionais exigem medições, validação de campo, estudo econômico e aprovação humana.
