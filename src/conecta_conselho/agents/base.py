"""Validação comum e execução controlada de pareceres dos agentes."""

import logging
from importlib.resources import files
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import (
    AgentOpinion,
    Evidence,
    Municipality,
    SimulationParameters,
)
from conecta_conselho.llm.base import LLMClient, LLMClientError, create_llm_client

logger = logging.getLogger(__name__)
PROMPT_BASE_VERSION = "base-v1"
ModelT = TypeVar("ModelT", bound=BaseModel)


class AgentExecutionError(RuntimeError):
    """Falha explícita de chamada ou validação de um agente."""


class StructuredOutputError(AgentExecutionError):
    """A saída do provedor permaneceu incompatível com o schema após retry."""


class InvalidEvidenceReferenceError(AgentExecutionError):
    """O parecer citou um ID ausente do catálogo fornecido ao agente."""


class UntraceableOpinionError(AgentExecutionError):
    """O agente emitiu uma posição conclusiva sem evidência de suporte."""


class AgentContextError(AgentExecutionError):
    """O catálogo de evidências não pertence à localidade analisada."""


def read_prompt(prompt_name: str) -> str:
    return (
        files("conecta_conselho.agents.prompts")
        .joinpath(f"{prompt_name}.md")
        .read_text(encoding="utf-8")
    )


async def generate_validated(
    client: LLMClient,
    system_prompt: str,
    payload: dict[str, Any],
    schema: type[ModelT],
    *,
    prompt_version: str,
    max_retries: int,
) -> ModelT:
    """Valida cada retorno e permite no máximo um retry por erro de schema."""
    if not 0 <= max_retries <= 1:
        raise ValueError("max_retries deve estar entre 0 e 1")

    current_prompt = system_prompt
    last_error: ValidationError | None = None
    for attempt in range(max_retries + 1):
        logger.info(
            "Solicitando saída estruturada",
            extra={
                "llm_provider": client.provider_name,
                "llm_model": client.model_name,
                "prompt_version": prompt_version,
                "attempt": attempt + 1,
            },
        )
        raw_output = await client.generate_structured(current_prompt, payload, schema)
        try:
            return schema.model_validate(raw_output)
        except ValidationError as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            safe_errors = [
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors(
                    include_input=False,
                    include_url=False,
                    include_context=False,
                )
            ]
            current_prompt = (
                f"{system_prompt}\n\nA resposta anterior não passou pelo schema. "
                "Corrija somente os erros de formato abaixo e devolva JSON válido: "
                + "; ".join(safe_errors)
            )

    raise StructuredOutputError(
        f"O provedor {client.provider_name} retornou saída incompatível com "
        f"{schema.__name__} após {max_retries + 1} tentativa(s)."
    ) from last_error


def prepare_agent_payload(
    role: str,
    municipality: Municipality,
    evidence_catalog: list[Evidence],
    parameters: SimulationParameters | None,
    additional_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    municipality_evidence_ids = {item.evidence_id for item in municipality.indicators}
    provided_ids = [item.evidence_id for item in evidence_catalog]
    if len(provided_ids) != len(set(provided_ids)):
        raise AgentContextError("O catálogo fornecido ao agente contém evidence_id duplicado.")
    unknown_ids = set(provided_ids) - municipality_evidence_ids
    if unknown_ids:
        raise AgentContextError(
            f"O catálogo contém evidências que não pertencem à localidade: {sorted(unknown_ids)}"
        )

    payload = {
        "agent_role": role,
        "municipality": {
            "municipality_code": municipality.municipality_code,
            "name": municipality.name,
            "is_synthetic": municipality.is_synthetic,
        },
        "municipality_is_synthetic": municipality.is_synthetic,
        "indicators": [item.model_dump(mode="json") for item in evidence_catalog],
        "anchor_institutions": [
            item.model_dump(mode="json") for item in municipality.anchor_institutions
        ],
        "parameters": parameters.model_dump(mode="json") if parameters is not None else None,
    }
    if additional_context is not None:
        payload["additional_context"] = additional_context
    return payload


async def run_opinion_agent(
    *,
    role: str,
    municipality: Municipality,
    evidence_catalog: list[Evidence] | None,
    parameters: SimulationParameters | None,
    llm_client: LLMClient | None,
    settings: LLMSettings | None,
    additional_context: dict[str, Any] | None = None,
) -> AgentOpinion:
    provider_settings = settings or LLMSettings()
    client = llm_client or create_llm_client(provider_settings)
    catalog = municipality.indicators if evidence_catalog is None else evidence_catalog
    payload = prepare_agent_payload(
        role, municipality, catalog, parameters, additional_context
    )
    prompt = f"{read_prompt('base')}\n\n{read_prompt(role)}"

    try:
        opinion = await generate_validated(
            client,
            prompt,
            payload,
            AgentOpinion,
            prompt_version=f"{role}-v1+{PROMPT_BASE_VERSION}",
            max_retries=provider_settings.max_agent_retries,
        )
    except AgentExecutionError:
        raise
    except LLMClientError as exc:
        raise AgentExecutionError(f"Falha controlada no agente {role}: {exc}") from exc
    except Exception as exc:
        raise AgentExecutionError(
            f"Falha inesperada controlada no agente {role}; nenhum parecer foi aceito."
        ) from exc

    available_ids = {item.evidence_id for item in catalog}
    cited_ids = opinion.supporting_evidence_ids
    if opinion.position != "insufficient_data" and not cited_ids:
        raise UntraceableOpinionError(
            f"O agente {role} emitiu posição {opinion.position!r} sem evidência de suporte."
        )
    if len(cited_ids) != len(set(cited_ids)):
        raise InvalidEvidenceReferenceError(
            f"O agente {role} repetiu evidence_id no parecer."
        )
    unknown_evidence_ids = set(cited_ids) - available_ids
    if unknown_evidence_ids:
        raise InvalidEvidenceReferenceError(
            f"O agente {role} citou evidências inexistentes no catálogo: "
            f"{sorted(unknown_evidence_ids)}"
        )
    return opinion
