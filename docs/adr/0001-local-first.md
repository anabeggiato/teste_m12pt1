# ADR 0001 — Execução local como padrão

- **Status:** aceito
- **Contexto:** a prova de conceito deve ser reproduzível sem credenciais, serviços pagos ou dependência obrigatória de um modelo remoto.
- **Decisão:** manter `LLM_PROVIDER=mock` como padrão de configuração e executar a API localmente. Integrações opcionais não podem impedir o fluxo padrão.
- **Consequências:** a fase inicial inclui apenas configuração e health check; Ollama e demais integrações só entram nas fases previstas. O modo mock deve ser identificado honestamente e não descrito como raciocínio generativo.
