"""Contrato e erros comuns dos clientes de LLM."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from conecta_conselho.config import LLMSettings


class LLMClientError(RuntimeError):
    """Falha controlada de configuração, transporte ou resposta do provedor."""


class LLMConfigurationError(LLMClientError):
    """Configuração inválida para o provedor selecionado."""


class LLMClient(ABC):
    """Interface assíncrona comum para saídas estruturadas."""

    provider_name: str
    model_name: str | None

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        schema: type[BaseModel],
    ) -> Any:
        """Gera uma resposta estruturada; a validação Pydantic ocorre na camada de agente."""


def create_llm_client(settings: LLMSettings | None = None) -> LLMClient:
    """Seleciona explicitamente mock (padrão) ou Ollama local."""
    provider_settings = settings or LLMSettings()
    if provider_settings.llm_provider == "mock":
        from conecta_conselho.llm.mock import MockLLMClient

        return MockLLMClient()

    if provider_settings.llm_provider == "ollama":
        if not provider_settings.ollama_model:
            raise LLMConfigurationError(
                "OLLAMA_MODEL precisa indicar um modelo instalado para usar Ollama."
            )
        if not provider_settings.ollama_base_url.strip():
            raise LLMConfigurationError("OLLAMA_BASE_URL não pode ser vazia para Ollama.")
        from conecta_conselho.llm.ollama import OllamaLLMClient

        return OllamaLLMClient(
            base_url=provider_settings.ollama_base_url,
            model_name=provider_settings.ollama_model,
        )

    raise LLMConfigurationError("LLM_PROVIDER deve ser 'mock' ou 'ollama'.")
