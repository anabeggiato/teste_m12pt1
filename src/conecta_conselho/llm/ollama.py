"""Adapter HTTP opcional para a API local de chat do Ollama."""

import json
from typing import Any

import httpx
from pydantic import BaseModel

from conecta_conselho.llm.base import LLMClient, LLMClientError


class OllamaLLMClient(LLMClient):
    """Envia saída estruturada a um servidor Ollama local, com timeout explícito."""

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model_name: str,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url do Ollama não pode ser vazia")
        if not model_name.strip():
            raise ValueError("model_name do Ollama não pode ser vazio")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds deve ser maior que zero")
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def generate_structured(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        schema: type[BaseModel],
    ) -> Any:
        body = {
            "model": self.model_name,
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=body)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMClientError("Tempo limite excedido ao chamar o Ollama.") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(
                f"Ollama respondeu com HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(
                "Não foi possível conectar ao servidor Ollama configurado."
            ) from exc

        try:
            response_payload = response.json()
            content = response_payload["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content não é texto")
            return json.loads(content)
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMClientError("Ollama retornou resposta sem JSON estruturado válido.") from exc
