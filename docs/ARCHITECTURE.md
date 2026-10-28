# Arquitetura

## Componentes implementados

- **Dashboard:** Streamlit em `frontend/app.py`; usa o cliente HTTP para consultar a API, coletar premissas e exibir evidências, pareceres, simulações, decisão preliminar e auditoria.
- **API:** FastAPI em `src/conecta_conselho/main.py`; expõe health check, localidades e operações de análise, recuperação e exportação.
- **Domínio:** modelos Pydantic e validações em `domain/`; funções determinísticas de scores e cenários em `scoring.py` e `simulation.py`.
- **Dados:** repositório carrega três fixtures sintéticas e até três municípios com população observada em snapshots JSON. O catálogo documenta fontes e transformações.
- **Orquestração:** grafo LangGraph sequencial de pareceres, Pontes, cenários, contestação e Guardião. Um hard gate determinístico conserva a aprovação humana.
- **LLM:** adapter alterna entre templates mock locais e chamadas HTTP a um servidor Ollama opcional. Mock não é geração por IA. Ollama não foi validado nesta execução porque o executável não está disponível no ambiente.
- **Persistência:** análises e auditoria ficam em SQLite local, configurável por `DATABASE_URL`.

## Caminho de uma análise

```text
Streamlit → FastAPI → validação do request
                    → carregar município/evidências
                    → pareceres Financeiro, Social, Técnico e Orçamentário
                    → proposta de Pontes → cenários determinísticos
                    → contestação → Guardião e hard gates
                    → persistir resultado → resposta e exportação JSON
```

O caminho é síncrono por request e não mantém estado conversacional entre análises. Os modelos recebem evidências estruturadas e devem citar seus IDs; dados ausentes continuam nulos. O SQLite é local e não constitui sistema multiusuário ou serviço de produção.

## Execução e limites operacionais

A API e o dashboard são processos locais separados. O caminho padrão usa `LLM_PROVIDER=mock`, sem credenciais nem tráfego externo. O modo Ollama requer serviço e modelo instalados pelo usuário e não tem fallback silencioso para mock. Consulte [LLM_AGENTS.md](LLM_AGENTS.md) e [LIMITATIONS.md](LIMITATIONS.md).
