# Checklist de submissão

Atualizado em 2026-10-28. Estado baseado nos arquivos e verificações deste repositório.

## Implementação e qualidade local

- [x] API, dashboard e fluxo de análise executam no modo mock local.
- [x] Regras determinísticas, contratos, dados sintéticos e proveniência de dados reais estão documentados.
- [x] Exemplos de análise A/B/C capturados a partir da API em modo mock em `docs/examples/`.
- [x] `LLM_PROVIDER=mock .venv/bin/ruff check .` passou sem erros em 2026-10-28.
- [x] `LLM_PROVIDER=mock .venv/bin/pytest -q` passou: 124 testes em 2026-10-28.
- [x] Harness ASGI em mock retornou HTTP 200 para health, municípios (6), POST/GET/export dos casos A/B/C.
- [x] Dashboard exercitado com o `AppTest` de Streamlit incluído na suíte.
- [x] Exemplos e roteiro mantêm custos/receitas como hipóteses e deixam lacunas explícitas.

## Pendências antes de submissão externa

- [ ] Registrar uso efetivo do IBM Bob IDE e incluir relatórios de sessão exportados e verificáveis. **Pendente: não há evidência no repositório nem nesta sessão.**
- [ ] Verificar licença/termos específicos da tabela SIDRA antes de qualquer redistribuição que exija licença individual identificada.
- [ ] Se desejado, executar smoke de Ollama com servidor e modelo instalados; não disponível no ambiente desta validação.
- [ ] Executar smoke por portas TCP e revisão visual em navegador nesta sessão. A tentativa foi limitada pelo sandbox; a revisão anterior documentada no README é de 2026-10-27.
- [ ] Gravar e revisar vídeo de demonstração de aproximadamente 3 minutos usando `DEMO_SCRIPT.md`.
- [ ] Conferir materiais e critérios oficiais da trilha e preencher eventuais campos/formulários externos.
- [ ] Antes de uso fora da POC, obter dados locais de cobertura, custos e infraestrutura e realizar validação técnica, regulatória e de campo.

Este checklist não declara concluída nenhuma submissão externa. A aprovação humana continua obrigatória para qualquer decisão operacional.
