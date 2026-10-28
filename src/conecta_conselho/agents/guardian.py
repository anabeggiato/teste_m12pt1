"""Síntese preliminar estruturada; hard gates são aplicados depois deste agente."""

from typing import Any

from conecta_conselho.agents.base import AgentExecutionError, generate_validated, read_prompt
from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import (
    AgentOpinion,
    Disagreement,
    Evidence,
    GuardianDecision,
    Municipality,
    ScenarioComparison,
    ScenarioResult,
)
from conecta_conselho.llm.base import LLMClient, LLMClientError, create_llm_client


class GuardianExecutionError(AgentExecutionError):
    """Falha controlada ao gerar ou validar a síntese preliminar do Guardião."""


class InvalidGuardianEvidenceError(GuardianExecutionError):
    """O Guardião citou evidência inexistente ou duplicada."""


async def generate_guardian_draft(
    *,
    municipality: Municipality,
    evidence_catalog: list[Evidence],
    opinions: list[AgentOpinion],
    disagreements: list[Disagreement],
    baseline: ScenarioResult,
    with_bridges: ScenarioResult,
    comparison: ScenarioComparison,
    warnings: list[str],
    llm_client: LLMClient | None = None,
    settings: LLMSettings | None = None,
) -> GuardianDecision:
    """Gera decisão preliminar; a saída nunca contorna ``apply_decision_guards``."""
    provider_settings = settings or LLMSettings()
    client = llm_client or create_llm_client(provider_settings)
    payload: dict[str, Any] = {
        "municipality": municipality.model_dump(mode="json"),
        "opinions": [opinion.model_dump(mode="json") for opinion in opinions],
        "disagreements": [item.model_dump(mode="json") for item in disagreements],
        "baseline": baseline.model_dump(mode="json"),
        "with_bridges": with_bridges.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
        "warnings": warnings,
        "evidence_catalog": [item.model_dump(mode="json") for item in evidence_catalog],
    }
    try:
        draft = await generate_validated(
            client,
            f"{read_prompt('base')}\n\n{read_prompt('guardian')}",
            payload,
            GuardianDecision,
            prompt_version="guardian-v1+base-v1",
            max_retries=provider_settings.max_agent_retries,
        )
    except AgentExecutionError:
        raise
    except LLMClientError as exc:
        raise GuardianExecutionError(f"Falha controlada no Guardião: {exc}") from exc
    except Exception as exc:
        raise GuardianExecutionError(
            "Falha inesperada controlada no Guardião; decisão preliminar não aceita."
        ) from exc

    available_ids = {item.evidence_id for item in evidence_catalog}
    cited_ids = draft.cited_evidence_ids
    if len(cited_ids) != len(set(cited_ids)):
        raise InvalidGuardianEvidenceError("O Guardião repetiu evidence_id.")
    unknown_ids = set(cited_ids) - available_ids
    if unknown_ids:
        raise InvalidGuardianEvidenceError(
            f"O Guardião citou evidências inexistentes: {sorted(unknown_ids)}"
        )
    return draft
