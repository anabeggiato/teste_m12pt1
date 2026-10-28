"""Agente de Pontes e composição determinística de cenários com instituições."""

import logging
from typing import Any

from conecta_conselho.agents.base import (
    AgentExecutionError,
    generate_validated,
    read_prompt,
)
from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import (
    BridgeProposal,
    BridgeScenarioAnalysis,
    Evidence,
    Municipality,
    SimulationParameters,
)
from conecta_conselho.domain.simulation import (
    compare_scenarios,
    simulate_baseline,
    simulate_with_bridges,
)
from conecta_conselho.llm.base import LLMClient, LLMClientError, create_llm_client

logger = logging.getLogger(__name__)


class BridgeAgentError(AgentExecutionError):
    """Falha controlada ao produzir ou validar a proposta de pontes."""


class InvalidBridgeReferenceError(BridgeAgentError):
    """A proposta cita instituição ou evidência fora do contexto recebido."""


class InvalidAnchorSelectionError(BridgeAgentError):
    """A seleção contém IDs repetidos ou não propostos pelo agente."""


def prepare_bridge_payload(
    municipality: Municipality,
    evidence_catalog: list[Evidence],
) -> dict[str, Any]:
    """Valida o contexto antes de enviá-lo ao ranqueador estruturado."""
    if any(
        institution.municipality_code != municipality.municipality_code
        for institution in municipality.anchor_institutions
    ):
        raise InvalidBridgeReferenceError(
            "Há instituição âncora que não pertence à localidade informada."
        )
    evidence_by_id = {item.evidence_id: item for item in municipality.indicators}
    provided_ids = [item.evidence_id for item in evidence_catalog]
    if len(provided_ids) != len(set(provided_ids)):
        raise InvalidBridgeReferenceError("Catálogo de evidências contém IDs duplicados.")
    if set(provided_ids) - set(evidence_by_id):
        raise InvalidBridgeReferenceError(
            "Catálogo contém evidência que não pertence à localidade."
        )
    provided_id_set = set(provided_ids)
    institutions = []
    for institution in municipality.anchor_institutions:
        institution_payload = institution.model_dump(mode="json")
        institution_payload["evidence_ids"] = [
            evidence_id
            for evidence_id in institution.evidence_ids
            if evidence_id in provided_id_set
        ]
        institutions.append(institution_payload)

    return {
        "municipality": {
            "municipality_code": municipality.municipality_code,
            "name": municipality.name,
            "is_synthetic": municipality.is_synthetic,
        },
        "municipality_is_synthetic": municipality.is_synthetic,
        "indicators": [item.model_dump(mode="json") for item in evidence_catalog],
        "anchor_institutions": institutions,
    }


def validate_bridge_proposal(
    proposal: BridgeProposal,
    municipality: Municipality,
    evidence_catalog: list[Evidence],
) -> None:
    """Rejeita IDs repetidos ou fora da localidade e do catálogo recebido."""
    anchor_by_id = {item.institution_id: item for item in municipality.anchor_institutions}
    evidence_ids = {item.evidence_id for item in evidence_catalog}
    candidate_ids = [item.institution_id for item in proposal.candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise InvalidBridgeReferenceError("A proposta repetiu institution_id.")
    for candidate in proposal.candidates:
        institution = anchor_by_id.get(candidate.institution_id)
        if institution is None:
            raise InvalidBridgeReferenceError(
                f"Instituição inexistente na localidade: {candidate.institution_id}."
            )
        if institution.municipality_code != municipality.municipality_code:
            raise InvalidBridgeReferenceError(
                f"Instituição fora da localidade: {candidate.institution_id}."
            )
        if len(candidate.evidence_ids) != len(set(candidate.evidence_ids)):
            raise InvalidBridgeReferenceError(
                f"A candidata {candidate.institution_id} repetiu evidence_id."
            )
        unknown_evidence_ids = set(candidate.evidence_ids) - evidence_ids
        if unknown_evidence_ids:
            raise InvalidBridgeReferenceError(
                f"A candidata {candidate.institution_id} citou evidências fora do catálogo: "
                f"{sorted(unknown_evidence_ids)}"
            )
        unlinked_evidence_ids = set(candidate.evidence_ids) - set(institution.evidence_ids)
        if unlinked_evidence_ids:
            raise InvalidBridgeReferenceError(
                f"A candidata {candidate.institution_id} citou evidências não associadas "
                f"à instituição: {sorted(unlinked_evidence_ids)}"
            )


async def analyze_bridges(
    municipality: Municipality,
    parameters: SimulationParameters,
    selected_anchor_ids: list[str] | None = None,
    evidence_catalog: list[Evidence] | None = None,
    llm_client: LLMClient | None = None,
    settings: LLMSettings | None = None,
) -> BridgeScenarioAnalysis:
    """Ranqueia candidatas, valida seleção explícita e compara cenários.

    Quando nenhuma seleção é passada, o cenário com pontes contém zero âncoras.
    A função não assume parcerias nem seleciona instituições automaticamente.
    """
    catalog = municipality.indicators if evidence_catalog is None else evidence_catalog
    proposal = await propose_bridges(
        municipality,
        evidence_catalog=catalog,
        llm_client=llm_client,
        settings=settings,
    )
    provider_settings = settings or LLMSettings()
    client = llm_client or create_llm_client(provider_settings)
    selected_ids = [] if selected_anchor_ids is None else list(selected_anchor_ids)
    if len(selected_ids) != len(set(selected_ids)):
        raise InvalidAnchorSelectionError("selected_anchor_ids contém IDs duplicados.")
    proposed_ids = {candidate.institution_id for candidate in proposal.candidates}
    unknown_selected_ids = set(selected_ids) - proposed_ids
    if unknown_selected_ids:
        raise InvalidAnchorSelectionError(
            "A seleção contém instituições ausentes da proposta: "
            f"{sorted(unknown_selected_ids)}"
        )

    baseline = simulate_baseline(parameters)
    with_bridges = simulate_with_bridges(parameters, municipality, selected_ids)
    comparison = compare_scenarios(baseline, with_bridges)
    logger.info(
        "Proposta de pontes validada",
        extra={
            "llm_provider": client.provider_name,
            "llm_model": client.model_name,
            "prompt_version": "bridges-v1+base-v1",
            "municipality_code": municipality.municipality_code,
            "selected_anchor_count": len(selected_ids),
        },
    )
    return BridgeScenarioAnalysis(
        municipality=municipality,
        proposal=proposal,
        selected_anchor_ids=selected_ids,
        baseline=baseline,
        with_bridges=with_bridges,
        comparison=comparison,
    )


async def propose_bridges(
    municipality: Municipality,
    evidence_catalog: list[Evidence] | None = None,
    llm_client: LLMClient | None = None,
    settings: LLMSettings | None = None,
) -> BridgeProposal:
    """Produz e valida candidatas sem selecionar âncoras ou executar cenários."""
    catalog = municipality.indicators if evidence_catalog is None else evidence_catalog
    payload = prepare_bridge_payload(municipality, catalog)
    provider_settings = settings or LLMSettings()
    client = llm_client or create_llm_client(provider_settings)
    try:
        proposal = await generate_validated(
            client,
            f"{read_prompt('base')}\n\n{read_prompt('bridges')}",
            payload,
            BridgeProposal,
            prompt_version="bridges-v1+base-v1",
            max_retries=provider_settings.max_agent_retries,
        )
    except AgentExecutionError:
        raise
    except LLMClientError as exc:
        raise BridgeAgentError(f"Falha controlada no Agente de Pontes: {exc}") from exc
    except Exception as exc:
        raise BridgeAgentError(
            "Falha inesperada controlada no Agente de Pontes; proposta não aceita."
        ) from exc

    validate_bridge_proposal(proposal, municipality, catalog)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    proposal.candidates.sort(key=lambda item: priority_order[item.priority])
    return proposal
