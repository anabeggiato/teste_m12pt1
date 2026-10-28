# Provedores de LLM e agentes

## Modos

- `LLM_PROVIDER=mock` é o padrão. O cliente usa templates determinísticos para Financeiro, Social, Técnico, Orçamentário, Pontes e Guardião, sem chamar modelo generativo ou serviço externo.
- `LLM_PROVIDER=ollama` chama `POST /api/chat` no `OLLAMA_BASE_URL` configurado. `OLLAMA_MODEL` deve ser preenchido com um modelo instalado pelo usuário. A chamada envia JSON Schema, temperatura zero e timeout de 30 segundos.
- Erros de configuração, conexão, timeout e resposta malformada viram erros controlados. Não há fallback automático de Ollama para mock.

O adapter é HTTP direto usando `httpx`; não exige SDK Python do Ollama. A API local padrão é `http://localhost:11434`. A integração deste projeto não usa modelos cloud nem exige conta, chave ou serviço pago.

## Instalar e selecionar um modelo local

Primeiro verifique o que já existe, sem presumir versão ou nome de modelo:

```bash
ollama --version
ollama list
curl --fail --silent --show-error http://localhost:11434/api/tags
```

Se o comando Ollama não estiver instalado, no Linux/macOS a instrução oficial de instalação é:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

No Windows, use o instalador disponível na [página oficial de download](https://ollama.com/download). Depois da instalação, abra um terminal novo e repita `ollama --version` e `ollama list`. Se o serviço local não estiver ativo, inicie-o conforme as instruções da plataforma (`ollama serve` em instalações que usam execução manual) e confirme que `/api/tags` responde.

Escolha um tag de modelo local no [catálogo oficial](https://ollama.com/search), considerando recursos da máquina e se o modelo segue o JSON Schema solicitado. Substitua o valor abaixo pela tag exata escolhida; não use tags `:cloud`:

```bash
OLLAMA_MODEL='substitua-pela-tag-local-escolhida'
ollama pull "$OLLAMA_MODEL"
ollama list
```

Valide também a saída estruturada do modelo, usando exatamente o mesmo tag:

```bash
curl --fail --silent --show-error http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"'"$OLLAMA_MODEL"'","stream":false,"messages":[{"role":"user","content":"Retorne um objeto JSON com ok igual a true."}],"format":{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]}}'
```

Na resposta, confirme que `message.content` contém JSON com `ok: true`. A API Ollama documenta `format` como campo para JSON Schema e recomenda validar a saída com Pydantic; esta integração envia `schema.model_json_schema()` e valida novamente no agente.

Para habilitar Ollama apenas neste ambiente, edite `.env` (crie-o a partir de `.env.example` se necessário) e use o mesmo tag local:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tag-local-exato-escolhido
MAX_AGENT_RETRIES=1
```

Inicie a API e o dashboard como no README e execute uma análise de demonstração. Se o servidor, modelo ou formato estruturado falhar, a aplicação retorna erro/resultado degradado; não troca silenciosamente para mock. Para voltar ao modo padrão sem LLM, configure `LLM_PROVIDER=mock` e deixe `OLLAMA_MODEL` vazio.

Referências oficiais: [instalação Linux](https://ollama.com/download/linux), [saídas estruturadas](https://docs.ollama.com/capabilities/structured-outputs) e [API de chat](https://docs.ollama.com/api/chat).

O histórico de disponibilidade, modelos e timeouts observados neste projeto está em [OLLAMA_DIAGNOSTIC.md](OLLAMA_DIAGNOSTIC.md). Ele separa erros reais relatados pelo usuário dos testes do adapter com provedor simulado.

## Validação e evidências

As respostas são validadas com `AgentOpinion` do Pydantic. Um erro de schema permite no máximo um retry com feedback contendo apenas localização e descrição do erro, sem os valores de entrada. Se a resposta continuar inválida, o agente falha explicitamente. Posições conclusivas sem evidência de suporte e referências a `evidence_id` inexistente ou duplicado invalidam o parecer sem conversão para resultado confiável.

O prompt-base proíbe inventar evidências, contratos, cobertura ou resultados e lembra que `confidence_level` mede completude qualitativa, não probabilidade. Prompts específicos estão em `src/conecta_conselho/agents/prompts/` e suas versões (`base-v1`, `financial-v1`, `social-v1`, `technical-v1`, `budget-v1`, `bridges-v1`, `guardian-v1`) são registradas em log junto ao provedor e modelo, sem registrar prompt ou payload.

O Agente Financeiro não estima ARPU, preço, margem, adesão, clientes, payback, ROI ou receita. O Agente Social não transforma vulnerabilidade em demanda contratante nem atribui efeitos causais a conectividade. O Agente Técnico não presume fibra, espectro, torres, energia ou capacidade de rede e sinaliza survey de campo quando faltam dados críticos. O Agente Orçamentário recebe a comparação do cenário base calculada por `simulate_baseline`, não duplica a matemática e não trata premissas como orçamento aprovado. Os quatro mantêm premissas e lacunas em campos separados e não tomam decisões finais.

O Agente de Pontes ranqueia qualitativamente instituições cadastradas a partir do status de conectividade informado. IDs de instituição e evidência são validados contra a localidade e o catálogo. A seleção para simulação deve ser explícita; seleção omitida significa zero âncoras. Os cenários usam `simulate_baseline`, `simulate_with_bridges` e `compare_scenarios`; custos e receita permanecem premissas, e toda parceria continua `unverified`.

## API, persistência e limites

Os agentes Financeiro, Social, Técnico, Orçamentário e de Pontes são nós sequenciais de um grafo LangGraph acíclico. Uma única rodada de contestação confronta perspectivas social/financeira e técnica/orçamentária; Guardião produz decisão preliminar e `apply_decision_guards` aplica bloqueios. Falhas individuais retornam resultado parcial `degraded`, erros identificados e revisão humana. `POST /api/v1/analyses` executa e persiste o resultado em SQLite; `GET /api/v1/analyses/{analysis_id}` recupera o resultado e `/export` fornece JSON de auditoria. Os registros permanecem até limpeza explícita com `scripts/reset_demo_db.py --confirm`; o banco é local e configurável por `DATABASE_URL`. A API aceita corpos de até 1 MiB e limita cada análise a 20 IDs de âncora. O dashboard Streamlit consome essas rotas pela URL configurável `API_BASE_URL`; não há endpoint de listagem de análises anteriores. Testes do adapter Ollama usam transporte HTTP simulado e não comprovam disponibilidade de servidor ou modelo local instalado.
