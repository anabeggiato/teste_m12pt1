# Catálogo de dados

## Dados reais controlados: população do Censo 2022

| Campo | Descrição |
|---|---|
| Entidade responsável | Instituto Brasileiro de Geografia e Estatística (IBGE), via Sistema IBGE de Recuperação Automática (SIDRA) |
| Fonte | [SIDRA, tabela 4709](https://sidra.ibge.gov.br/tabela/4709), variável 93 — População residente |
| Consulta da API | `https://apisidra.ibge.gov.br/values/t/4709/n6/{código IBGE}/v/93/p/2022` |
| Referência | 2022, Censo Demográfico |
| Granularidade | Município (nível territorial 6); uma contagem agregada por município |
| Coleta registrada | 2026-10-27; horário exato está em `retrieved_at` no snapshot bruto |
| Licença/termos | Dado estatístico público do IBGE. A política federal de dados abertos define reutilização e atribuição; não foi identificada licença Creative Commons específica para esta tabela. Atribuir ao IBGE e conferir os termos da fonte ao redistribuir. |
| Transformação | Resposta JSON SIDRA preservada em `data/raw/ibge_sidra_censo_2022_population.json`; código IBGE usado como chave de junção; campo `V` convertido para inteiro; unidade normalizada para `people`; nenhum valor ausente é preenchido. |
| Ingestão | `LLM_PROVIDER=mock .venv/bin/python scripts/ingest_ibge_census.py` (requer acesso à internet para coletar novamente); a aplicação usa os snapshots locais sem rede. |

Os três municípios controlados e a comparação entre o dado de origem e o catálogo tratado são:

| Código IBGE | Município/UF | População residente | Unidade |
|---|---|---:|---|
| 1302603 | Manaus/AM | 2.063.689 | pessoas |
| 2611606 | Recife/PE | 1.488.920 | pessoas |
| 3550308 | São Paulo/SP | 11.451.999 | pessoas |

Os testes offline em `tests/unit/test_ingest_ibge_census.py` repetem a validação da resposta SIDRA e comparam cada valor tratado com a linha bruta de mesmo código IBGE. A ingestão rejeita consulta com código, período, variável, unidade ou município incompatível, registro ausente e valor não numérico ou não positivo.

População é somente contexto demográfico. Não é proxy de demanda de telecomunicações, cobertura, receita ou custo. Para esses três municípios, cobertura, custos, instituições âncora e conectividade permanecem ausentes; não são representados por zero nem inferidos. As instituições fictícias e seus dados continuam restritos às localidades `DEMO001`–`DEMO003`.

Os dados são agregados e não contêm dados pessoais. A documentação do [IBGE sobre dados abertos](https://www.ibge.gov.br/acesso-informacao/dados-abertos.html) e a definição federal de [dados abertos](https://www.gov.br/acessoainformacao/pt-br/lai-para-sic/transparencia-ativa/copy_of_guia-de-transparencia-ativa/textos-complementares/formato-aberto) orientam o registro de origem e atribuição. A licença específica da tabela não foi identificada separadamente, por isso a atribuição é mantida e a ausência de identificador de licença é declarada.

## Dados sintéticos de demonstração

`data/fixtures/municipalities.synthetic.json` contém `DEMO001`, `DEMO002` e `DEMO003`. São localidades inteiramente fictícias; consulte [data/README.md](../data/README.md). Cada evidência sintética e hipótese permanece identificada no modelo e na interface.
