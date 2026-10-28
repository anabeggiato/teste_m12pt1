# ADR 0002 — Cálculos determinísticos

- **Status:** aceito
- **Contexto:** estimativas e decisões de triagem precisam ser reproduzíveis e auditáveis; texto gerado por modelo não é fonte confiável para aritmética.
- **Decisão:** quando o domínio e os cenários forem implementados, cálculos de scores, orçamento e simulação serão funções determinísticas em Python, com parâmetros e limites documentados. LLMs poderão interpretar evidências, mas não definir os resultados numéricos.
- **Consequências:** fórmulas, valores ausentes e limites terão testes próprios. Esta ADR registra a decisão arquitetural; a implementação do motor pertence à fase 2.
