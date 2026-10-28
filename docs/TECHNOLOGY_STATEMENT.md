# Declaração tecnológica

O Conecta Conselho é uma prova de conceito desenvolvida em Python, com FastAPI para API HTTP, Streamlit para interface, Pydantic para contratos, LangGraph para explicitar a sequência de papéis, SQLite para persistência local e pytest/ruff para validação. A integração opcional com LLM usa um adapter para mock local ou Ollama local.

No modo padrão `LLM_PROVIDER=mock`, os pareceres são templates determinísticos e não são gerados por um modelo de linguagem. Scores, cenários e bloqueios são calculados por funções Python determinísticas. A execução padrão não exige API externa, chave, serviço pago ou conexão de rede. Ollama é opcional e não foi validado nesta execução.

Dados reais integrados são agregados: população residente municipal do Censo 2022 via IBGE/SIDRA. Dados sintéticos e hipóteses são identificados separadamente. A aplicação não toma nem automatiza decisão de investimento; exige revisão humana.

Esta declaração descreve componentes encontrados no repositório e a configuração verificada. Não afirma uso de IBM Bob IDE, watsonx ou qualquer ferramenta sem evidência documental de execução.
