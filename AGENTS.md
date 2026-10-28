# Instruções para agentes — Conecta Conselho

Leia `docs/IMPLEMENTACAO_CODEX.md` antes de implementar. Ele é a fonte de verdade técnica.

- Trabalhe em uma fase por vez e inspecione o repositório antes de editar.
- Use Python 3.11+, FastAPI, Pydantic v2, LangGraph, SQLite e Streamlit; Ollama é opcional.
- A demonstração deve funcionar offline em `LLM_PROVIDER=mock`, sem serviços pagos.
- Identifique dados sintéticos, não invente evidências e não transforme valores ausentes em zero.
- Mantenha cálculos determinísticos fora do LLM; valide as saídas estruturadas.
- Não colete dados pessoais nem inclua segredos no repositório.
- Execute `ruff check .` e `pytest -q` ao final de cada fase.
- Atualize a documentação pertinente e relate resultados reais, riscos e pendências.
- Só documente uso do IBM Bob IDE e relatórios quando houver evidência de uso efetivo.
