# Dados da demonstração

O repositório combina três localidades sintéticas para exercitar cenários e três localidades reais com uma única medida observada: população residente no Censo 2022. A aplicação lê os snapshots incluídos no repositório e funciona sem rede. A origem, termos, granularidade, códigos e transformações dos dados reais estão em [docs/DATA_CATALOG.md](../docs/DATA_CATALOG.md).

Para atualizar os dados reais, execute `LLM_PROVIDER=mock .venv/bin/python scripts/ingest_ibge_census.py` com acesso à API pública SIDRA. O script salva respostas brutas e catálogo tratado, valida os três códigos IBGE definidos e não preenche lacunas. Faça revisão dos arquivos gerados antes de incorporá-los.

`fixtures/municipalities.synthetic.json` contém três localidades inteiramente fictícias para testes e demonstração: `DEMO001`, `DEMO002` e `DEMO003`. Os nomes, identificadores, instituições e valores não descrevem localidades, equipamentos públicos, redes ou pessoas reais. `state_code="XX"` é um marcador interno, não uma UF.

Todos os indicadores com números ou categorias estão marcados como `kind="hypothetical"`, `is_synthetic=true` e `source_name="Cenário sintético de demonstração"`. Dados que não foram fornecidos permanecem `value: null` e `kind="unavailable"`; zero não é usado para representar ausência. A capacidade de conectividade das instituições fica como `unknown` e não é interpretada como desconectada.

Os perfis contrastam apenas para exercitar contratos e telas futuras: A tem proxy de demanda mais alto e menor lacuna hipotética; B tem maior lacuna, quatro instituições candidatas e teto hipotético de planejamento inferior ao custo base hipotético; C tem restrições técnicas mais severas e evidências incompletas. Esses números não têm validade empírica e não devem embasar decisão operacional.

Os municípios reais são Manaus (1302603), Recife (2611606) e São Paulo (3550308). Neles, somente a população municipal é observada; cobertura, custo, demanda, conectividade e instituições âncora continuam indisponíveis. Esses campos não devem ser interpretados como zero nem deduzidos a partir da população.
