# Diagnóstico do Ollama no Conecta Conselho

**Atualizado em:** 2026-10-28  
**Escopo:** registrar modelos e erros observados, separar testes reais de testes simulados e indicar próximos experimentos sem tratar hipóteses como resultados.

## Resumo

O adapter Ollama do projeto foi exercitado por testes automatizados com transporte HTTP simulado. Ainda não há evidência de uma análise completa bem-sucedida com um modelo Ollama real.

Foram relatados dois problemas diferentes:

1. `ollama run lfm3` falhou durante a obtenção do manifesto com `this model requires MLX support, but the MLX runtime is not available`.
2. Uma análise da API com `qwen3.5:2b` terminou `degraded`; os seis nós que chamam o modelo falharam com `ReadTimeout`. Nenhum parecer foi produzido e a seleção de âncoras foi removida do resultado parcial.

`qwen3.5:4b` foi recomendado como opção, mas **não há registro de que tenha sido testado**. O modo `mock` continua sendo o padrão e os testes simulados do adapter não comprovam compatibilidade com servidor/modelo real.

## Registro de execuções

| Modelo/configuração | Evidência | Resultado | Interpretação limitada |
|---|---|---|---|
| LFM3 via `ollama run lfm3` | Erro colado pelo usuário no terminal | Falha ao baixar/carregar o manifesto: exige runtime MLX indisponível | Compatibilidade de plataforma/instalação, não erro do contrato Pydantic do Conecta Conselho. |
| `qwen3.5:2b` via API Conecta Conselho | Exportação real de análise fornecida pelo usuário; `mode=ollama`, `status=degraded`, `model_name=qwen3.5:2b` | `ReadTimeout` em Financeiro, Social, Técnico, Orçamentário, Pontes e Guardião; zero pareceres; revisão humana | O modelo/servidor não respondeu dentro do limite de leitura configurado. Não é uma análise válida nem prova de saída estruturada incompatível. |
| `qwen3.5:4b` | Somente recomendação baseada no hardware visto no ambiente de trabalho | Não testado | Não declarar como compatível ou incompatível até executar no Ollama do usuário. |
| Adapter Ollama nos testes | `httpx.MockTransport` e clientes simulados na suíte pytest | Casos simulados passam | Verifica montagem de JSON Schema, parsing, timeout, erros HTTP/conexão e retry Pydantic limitado. Não chama Ollama real. |

O export `qwen3.5:2b` mostra que a API conseguiu concluir o fluxo e persistir uma resposta parcial. Como todos os seis nós falharam, o Guardião devolveu `REVISAO_HUMANA`, sem opiniões. As âncoras informadas no request não aparecem no cenário final porque a proposta de Pontes falhou. Esse resultado não deve ser apresentado como parecer do Conselho.

## Configuração observada no ambiente

Na inspeção do ambiente de trabalho, a CLI informou Ollama `0.40.12`; o sistema reportou Linux x86_64 e processador Intel i5-1335U. `nvidia-smi` não estava disponível. Essa leitura não prova que não exista outra GPU, nem garante que seja a mesma instalação/daemon acessada pelo processo do usuário. O endpoint local do Ollama não pôde ser consultado a partir do sandbox do agente; por isso a lista local de modelos não foi verificada aqui.

As notas oficiais do Ollama v0.40.12 dizem que LFM3 era suportado em hardware Apple nessa versão e que suporte a Linux/Windows viria depois. Isso é consistente com o erro MLX observado em Linux; instalar `mlx` no virtualenv Python do projeto não adiciona o runtime MLX ao binário Ollama. Confira a [nota oficial v0.40.12](https://github.com/ollama/ollama/releases/tag/v0.40.12) antes de novas tentativas, pois suporte e versões podem mudar.

## Limites de timeout implementados

- O adapter HTTP usa timeout de leitura de **30 segundos** (`timeout_seconds=30.0` em `src/conecta_conselho/llm/ollama.py`). Não há variável `.env` para alterá-lo atualmente.
- Cada nó de agente tem limite de **65 segundos** (`NODE_TIMEOUT_SECONDS` em `src/conecta_conselho/orchestration/nodes.py`). Aumentar somente o timeout HTTP acima desse valor não ajuda: o limite do nó interrompe a chamada primeiro.
- O cliente Streamlit espera até **600 segundos** pela requisição completa de análise (`src/conecta_conselho/dashboard/api_client.py`). Como os nós são executados sequencialmente, múltiplas respostas lentas podem atingir esse limite total.
- O retry de até uma vez é para resposta que não passa pela validação Pydantic. Erros de conexão e timeout são reportados; não há fallback automático para mock.

## Possíveis soluções e como validar

### LFM3

1. Não repetir a tag `lfm3` nessa instalação até confirmar suporte da plataforma e da versão do Ollama. No v0.40.12, o requisito MLX restringia LFM3 a hardware Apple conforme as notas oficiais.
2. Em Linux/Windows, aguardar suporte numa versão oficial compatível ou escolher outro modelo Ollama cuja tag não exija MLX. Não remover o sufixo `-mlx` às cegas: valide a tag e o manifesto na página oficial.
3. Em hardware Apple compatível, atualizar/usar a distribuição oficial suportada e confirmar que o CLI e o daemon pertencem à mesma instalação antes de repetir `ollama list` e `ollama run lfm3`.

### `qwen3.5:2b` e respostas lentas

1. Verificar no mesmo terminal do usuário o servidor/modelo e medir uma resposta curta:

   ```bash
   ollama --version
   ollama list
   ollama ps
   time ollama run qwen3.5:2b "Responda somente: OK"
   ```

   Se a resposta simples também demorar muito ou falhar, resolver primeiro a execução/recursos do Ollama. Se ela responder rapidamente, isso ainda não prova que o modelo consegue produzir os pareceres estruturados completos.

2. Testar um modelo/tag menor ou mais rápido que esteja disponível para a plataforma. Isso pode reduzir latência, mas pode piorar a qualidade dos pareceres; compatibilidade e qualidade precisam ser medidas, não presumidas.
3. Se a resposta curta funcionar, mas os pareceres ultrapassarem 30 segundos, implementar timeout configurável no adapter e limite coordenado por nó. Um experimento, por exemplo, poderia usar 90 s no HTTP e 100 s no nó, mantendo a chamada total do dashboard abaixo de 600 s. Esses valores são **proposta para teste**, não solução já validada. Como os seis papéis são sequenciais, aumentar limites pode tornar uma análise completa longa.
4. Depois da mudança, testar com o provedor real um ciclo completo: health em `mode=ollama`, análise `status=completed`, quatro opiniões, proposta de Pontes e Guardião. Erro degradado ou ausência de opinião deve continuar visível; não aceitar fallback silencioso para mock.

O Ollama documenta saída estruturada por JSON Schema no campo `format`; o projeto ainda valida a resposta com Pydantic. A compatibilidade de uma tag específica deve ser confirmada com uma chamada real e, em seguida, com a análise completa. Referência: [saídas estruturadas do Ollama](https://docs.ollama.com/capabilities/structured-outputs).

## Comandos de referência do projeto

Após confirmar que servidor e tag estão funcionais:

```bash
LLM_PROVIDER=ollama OLLAMA_MODEL=TAG_LOCAL_EXATA \
  .venv/bin/uvicorn conecta_conselho.main:app --reload
```

No terminal do dashboard:

```bash
.venv/bin/streamlit run frontend/app.py
```

Para manter o caminho padrão offline, omita `LLM_PROVIDER=ollama` ou use `LLM_PROVIDER=mock`. Nenhuma dessas verificações exige serviço pago.
