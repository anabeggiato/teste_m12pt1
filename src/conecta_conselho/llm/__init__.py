"""Adapters de provedores de linguagem."""

from conecta_conselho.llm.base import LLMClient, LLMClientError, create_llm_client
from conecta_conselho.llm.mock import MockLLMClient
from conecta_conselho.llm.ollama import OllamaLLMClient

__all__ = [
    "LLMClient",
    "LLMClientError",
    "MockLLMClient",
    "OllamaLLMClient",
    "create_llm_client",
]
