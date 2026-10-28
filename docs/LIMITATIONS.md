# Limitações conhecidas

## Dados

- `DEMO001`–`DEMO003` são localidades e indicadores inteiramente fictícios; não descrevem lugares, instituições, pessoas ou redes reais.
- Manaus, Recife e São Paulo têm somente população municipal agregada do Censo 2022. População não é medida de cobertura, demanda, receita, custo ou viabilidade de expansão.
- Cobertura, custos, conectividade, demanda e instituições âncora para os municípios reais continuam ausentes. A interface os deixa ausentes; não os estima nem preenche com zero.
- Para a tabela SIDRA usada, a documentação registra origem, referência e atribuição, mas não identificou uma licença Creative Commons específica. A adequação dos termos deve ser revista antes de redistribuição comercial.

## Método e modelos

- Scores são heurísticas de triagem sem calibração ou validação empírica. Não são probabilidades, previsões ou ranking operacional.
- Custos, teto, receita e horizonte informados nos exemplos A/B são premissas hipotéticas. Não são orçamento, contrato, ARPU, ROI ou previsão comercial.
- `LLM_PROVIDER=mock` gera templates determinísticos; não demonstra capacidade generativa. A resposta ainda passa por validação de schema, e os hard gates são determinísticos.
- Ollama não foi testado nesta fase porque não há executável `ollama` disponível no ambiente. Os testes do adapter simulam HTTP e não provam compatibilidade com um modelo local específico.
- Saída de LLM pode ser incompleta ou incorreta. As referências e contratos reduzem alguns erros, mas não substituem revisão técnica ou de campo.

## Uso e operação

- Decisões são preliminares e sempre exigem aprovação humana; a POC não autoriza investimento nem substitui planejamento regulatório, comercial ou de engenharia.
- A aplicação foi verificada localmente em modo mock, sem garantia de segurança, disponibilidade, desempenho ou controle de acesso para uso público ou multiusuário.
- Evidência de uso do IBM Bob IDE e relatórios exportados permanecem pendentes. Nenhum uso foi declarado sem evidência verificável.
