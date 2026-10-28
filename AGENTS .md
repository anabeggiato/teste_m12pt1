# AGENTS.md — Conecta Conselho

Leia `docs/IMPLEMENTACAO_CODEX.md` antes de qualquer implementação. A especificação é a fonte de verdade.

- Execute uma fase por vez; inspecione o repositório antes de editar.
- Python 3.11+, FastAPI, Pydantic v2, LangGraph, SQLite, Streamlit; Ollama opcional.
- O projeto deve funcionar sem serviços pagos em `LLM_PROVIDER=mock`.
- Dados sintéticos devem ser explicitamente identificados. Não invente evidências ou resultados.
- Cálculos numéricos e regras de bloqueio devem ser determinísticos e testados.
- Agentes retornam JSON validado por Pydantic e citam IDs de evidência existentes.
- Valores ausentes são `null`, nunca zero presumido.
- Decisões não são autorizações de investimento; aprovação humana obrigatória.
- Não coletar dados pessoais nem incluir segredos no Git.
- Sempre executar `ruff check .` e `pytest -q` ao fim da fase.
- Atualizar documentação e relatar arquivos alterados, testes reais, riscos e pendências.
- IBM Bob IDE é requisito do programa; documentar uso efetivo e anexar relatórios reais, sem fabricá-los.
