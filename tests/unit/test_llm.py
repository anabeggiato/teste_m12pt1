import asyncio
import json

import httpx
import pytest

from conecta_conselho.agents.base import StructuredOutputError, generate_validated
from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import AgentOpinion
from conecta_conselho.llm.base import (
    LLMClientError,
    LLMConfigurationError,
    create_llm_client,
)
from conecta_conselho.llm.mock import MockLLMClient
from conecta_conselho.llm.ollama import OllamaLLMClient


def test_default_provider_is_mock_and_does_not_need_ollama_model() -> None:
    settings = LLMSettings(_env_file=None)

    client = create_llm_client(settings)

    assert settings.llm_provider == "mock"
    assert isinstance(client, MockLLMClient)


def test_ollama_provider_requires_an_explicit_model_name() -> None:
    settings = LLMSettings(
        llm_provider="ollama",
        ollama_model=None,
        _env_file=None,
    )

    with pytest.raises(LLMConfigurationError, match="OLLAMA_MODEL"):
        create_llm_client(settings)


def test_ollama_provider_builds_local_adapter_when_model_is_configured() -> None:
    settings = LLMSettings(
        llm_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="locally-installed-model",
        _env_file=None,
    )

    client = create_llm_client(settings)

    assert isinstance(client, OllamaLLMClient)
    assert client.provider_name == "ollama"
    assert client.model_name == "locally-installed-model"


def test_ollama_adapter_sends_json_schema_and_parses_structured_content() -> None:
    response_object = {
        "agent_name": "financial",
        "position": "conditional",
        "summary": "Parecer estruturado.",
        "supporting_evidence_ids": [],
        "risks": [],
        "assumptions": [],
        "missing_data": [],
        "confidence_level": "low",
    }
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["body"] = json.loads(request.content)
        received["timeout"] = request.extensions.get("timeout")
        return httpx.Response(
            200,
            json={
                "model": "local-test-model",
                "message": {"role": "assistant", "content": json.dumps(response_object)},
            },
        )

    transport = httpx.MockTransport(handler)
    client = OllamaLLMClient(
        "http://localhost:11434/",
        "local-test-model",
        timeout_seconds=2,
        transport=transport,
    )

    output = asyncio.run(
        client.generate_structured("system", {"key": "value"}, AgentOpinion)
    )

    request_body = received["body"]
    assert received["url"] == "http://localhost:11434/api/chat"
    assert isinstance(request_body, dict)
    assert request_body["stream"] is False
    assert request_body["options"] == {"temperature": 0}
    assert request_body["format"] == AgentOpinion.model_json_schema()
    assert received["timeout"] == {
        "connect": 2.0,
        "read": 2.0,
        "write": 2.0,
        "pool": 2.0,
    }
    assert output == response_object
    assert client.model_name == "local-test-model"


def test_ollama_structured_output_is_validated_and_retried_once() -> None:
    valid = {
        "agent_name": "financial",
        "position": "conditional",
        "summary": "Parecer estruturado.",
        "supporting_evidence_ids": [],
        "risks": [],
        "assumptions": [],
        "missing_data": [],
        "confidence_level": "low",
    }
    invalid = {**valid, "position": "invest"}
    responses = [invalid, valid]
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        content = json.dumps(responses[len(requests) - 1])
        return httpx.Response(200, json={"message": {"content": content}})

    client = OllamaLLMClient(
        "http://localhost:11434",
        "test-model-from-simulated-provider",
        transport=httpx.MockTransport(handler),
    )

    output = asyncio.run(
        generate_validated(
            client,
            "system prompt",
            {"agent_role": "financial"},
            AgentOpinion,
            prompt_version="financial-test-v1",
            max_retries=1,
        )
    )

    assert isinstance(output, AgentOpinion)
    assert output.position == "conditional"
    assert len(requests) == 2
    assert all(request["format"] == AgentOpinion.model_json_schema() for request in requests)


def test_ollama_invalid_schema_fails_after_one_retry() -> None:
    invalid = {
        "agent_name": "financial",
        "position": "invest",
        "summary": "Saída incompatível.",
        "supporting_evidence_ids": [],
        "risks": [],
        "assumptions": [],
        "missing_data": [],
        "confidence_level": "low",
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(invalid)}},
        )

    client = OllamaLLMClient(
        "http://localhost:11434",
        "test-model-from-simulated-provider",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(StructuredOutputError, match="após 2 tentativa"):
        asyncio.run(
            generate_validated(
                client,
                "system prompt",
                {},
                AgentOpinion,
                prompt_version="financial-test-v1",
                max_retries=1,
            )
        )

    assert len(requests) == 2


def test_ollama_http_error_is_returned_as_controlled_failure() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"error": "model unavailable"})
    )
    client = OllamaLLMClient(
        "http://localhost:11434",
        "missing-model",
        transport=transport,
    )

    with pytest.raises(LLMClientError, match="HTTP 503"):
        asyncio.run(client.generate_structured("system", {}, AgentOpinion))


def test_ollama_connection_error_is_returned_as_controlled_failure() -> None:
    def connection_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection refusal", request=request)

    client = OllamaLLMClient(
        "http://localhost:11434",
        "local-test-model",
        transport=httpx.MockTransport(connection_error),
    )

    with pytest.raises(LLMClientError, match="Não foi possível conectar"):
        asyncio.run(client.generate_structured("system", {}, AgentOpinion))


def test_ollama_invalid_json_content_is_not_accepted() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"message": {"content": "not-json"}},
        )
    )
    client = OllamaLLMClient(
        "http://localhost:11434",
        "local-test-model",
        transport=transport,
    )

    with pytest.raises(LLMClientError, match="JSON estruturado"):
        asyncio.run(client.generate_structured("system", {}, AgentOpinion))


def test_ollama_timeout_is_controlled() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    client = OllamaLLMClient(
        "http://localhost:11434",
        "local-test-model",
        transport=httpx.MockTransport(timeout_handler),
    )

    with pytest.raises(LLMClientError, match="Tempo limite"):
        asyncio.run(client.generate_structured("system", {}, AgentOpinion))
