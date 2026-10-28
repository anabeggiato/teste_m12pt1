# Metodologia inicial de triagem

## Escopo

Os scores são heurísticas descritivas para exercitar uma prova de conceito. Não são previsões validadas, probabilidades de sucesso, ranking definitivo, decisão de investimento ou estimativa de ROI. Os limites abaixo são constantes explícitas da configuração inicial; não são ajustados às três localidades sintéticas. Indicadores das fixtures são hipotéticos e não têm validade empírica.

## Normalização e scores

Para um valor `x` com limites `lower` e `upper`, calcula-se `min(1, max(0, (x - lower) / (upper - lower)))`. Valores abaixo/acima dos limites saturam em 0/1. `upper <= lower` e valores não finitos são rejeitados. Um score composto é a soma ponderada dos indicadores normalizados; os pesos de cada score devem somar 1.0.

| Score | Indicador | Limites / transformação | Peso |
|---|---|---:|---:|
| `market_opportunity` | `demand_proxy_index` | 0 a 100, crescente | 1.0 |
| `social_priority` | `social_access_gap_pct` | 0 a 100, crescente | 1.0 |
| `technical_feasibility` | `reported_coverage_pct` | 0 a 100, crescente | 0.5 |
| `technical_feasibility` | `technical_constraint_level` | baixa=1.0; moderada=0.5; severa=0.0 | 0.5 |

`market_opportunity` usa somente o proxy de demanda definido no contrato da fixture; não estima clientes, ARPU ou receita. Uma categoria técnica sem mapeamento explícito não é convertida em número. Se qualquer indicador configurado estiver ausente, indisponível ou tiver tipo inesperado, o score inteiro é `null`; os pesos não são renormalizados. `missing_indicators` e `evidence_ids` registram a lacuna e as evidências consultadas. Nenhum dado ausente vira zero.

## Cenários

- Base: custo igual a `estimated_base_cost_brl`; sem instituições, receita atribuível a âncoras e saldo incremental iguais a zero. O aviso declara que outras receitas não estão incluídas.
- Com pontes: custo adicional = número de IDs selecionados × `estimated_cost_per_anchor_brl`; custo total só é calculado se custo base e custo por âncora forem conhecidos.
- Receita hipotética das âncoras = número selecionado × receita mensal hipotética por âncora × horizonte. Sem a premissa mensal, o resultado permanece `null`.
- Saldo hipotético incremental = receita hipotética das âncoras − custo adicional. Esse valor não é ROI, lucro, NPV, viabilidade econômica ou receita contratada.
- `within_budget` só é calculado quando custo total é conhecido e usa `total_cost <= budget_ceiling_brl`; o teto exato é considerado dentro do orçamento.

IDs desconhecidos e IDs duplicados são rejeitados. Zero instituições retorna exatamente o cenário base. Custos e receita são entradas hipotéticas/estimadas fornecidas ao motor, não valores inferidos das fixtures.

## Hard gates preliminares

`apply_decision_guards` exige indicador de conectividade observado/estimado (ou status institucional explicitamente conhecido) e custo/teto comparável; valores apenas hipotéticos não satisfazem essa exigência. Se faltar qualquer um, força `REVISAO_HUMANA`. Uma divergência material entre perspectivas também força revisão. Se o cenário ultrapassa o teto, decisões `INVESTIR` ou `PILOTAR` viram `AGUARDAR`, pois ainda não há escopo reduzido com custo validado. Decisões operacionais `INVESTIR` ou `PILOTAR` baseadas somente em dados sintéticos, ou investimento que selecione instituição sintética, viram `REVISAO_HUMANA`. Toda decisão mantém `requires_human_approval=true`; quando houver intervenção, o resultado registra decisão original, final e razões.

Estes hard gates são regras de segurança iniciais da POC e exigem revisão humana antes de uso operacional. O Guardião produz apenas uma decisão preliminar; a decisão final passa por `apply_decision_guards`. Se um nó LLM falha, o fluxo registra erro por nó, omite o parecer não produzido, finaliza como `degraded` e força `REVISAO_HUMANA`.

## Pontes e comparação de cenários

O agente de pontes ranqueia os registros de instituições segundo o status de conectividade cadastrado: `unconnected` recebe prioridade qualitativa alta, `unknown` média e `connected` baixa. Essa regra é apenas uma ordenação de triagem, não um score técnico ou indicação de parceria. A justificativa informa que o status precisa ser confirmado localmente; as candidatas permanecem com `partnership_status="unverified"`.

A seleção de instituições usada pela simulação é fornecida explicitamente pelo chamador. Sem seleção, o conjunto é vazio e o cenário com pontes equivale ao cenário base. IDs selecionados precisam constar na proposta validada e na localidade. O motor existente calcula cenário base e cenário com pontes e os compara, sem duplicação de fórmula pelo agente. Receita hipotética, custo por âncora e custo base permanecem nulos quando não informados; os saldos não representam ROI, receita contratada ou orçamento aprovado. Dados da demonstração B são sintéticos e a comparação antes/depois é somente ilustrativa.

## Contestação e síntese

O fluxo faz uma única passagem sequencial: pareceres independentes, proposta de pontes, simulação, contestação, Guardião e hard gates. A contestação é determinística e confronta os pares Social/Financeiro e Técnico/Orçamentário; divergência entre posições de apoio e cautela gera `Disagreement` e exige revisão humana. Não há diálogo recursivo entre agentes. O estado registra `analysis_id`, entradas, pareceres, cenários, divergências, decisão, avisos, erros e status. A API persiste resultados completos e degradados em SQLite, permite recuperação por `analysis_id` e exporta JSON de auditoria; detalhes operacionais estão no README.

## Exemplos A/B/C

O script `scripts/capture_demo_analyses.py` envia três requests à API local configurada em `LLM_PROVIDER=mock` e grava as respostas reais em `docs/examples/`. A usa uma âncora e parâmetros financeiros hipotéticos; B usa duas âncoras e parâmetros hipotéticos; C omite custos e não seleciona âncoras. Os três usam somente localidades `DEMO` sintéticas. Os arquivos são artefatos de demonstração, não fatos de localidades reais. Reexecute o script após iniciar a API para atualizar respostas, IDs e timestamps.
