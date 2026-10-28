"""Nós síncronos ou assíncronos do fluxo do conselho, sem estado global mutável."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from conecta_conselho.agents.bridges import propose_bridges
from conecta_conselho.agents.budget import analyze_budget
from conecta_conselho.agents.financial import analyze_financial
from conecta_conselho.agents.guardian import generate_guardian_draft
from conecta_conselho.agents.social import analyze_social
from conecta_conselho.agents.technical import analyze_technical
from conecta_conselho.config import LLMSettings
from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.data.repository import MunicipalityRepository
from conecta_conselho.domain.enums import Decision
from conecta_conselho.domain.models import (
    AgentOpinion,
    AnalysisError,
    BridgeProposal,
    Disagreement,
    Evidence,
    GuardianDecision,
    SimulationParameters,
)
from conecta_conselho.domain.simulation import (
    apply_decision_guards,
    compare_scenarios,
    simulate_baseline,
    simulate_with_bridges,
)
from conecta_conselho.llm.base import LLMClient
from conecta_conselho.orchestration.state import CouncilState

AgentFunction = Callable[..., Any]
NODE_TIMEOUT_SECONDS = 65
logger = logging.getLogger(__name__)
OPPOSITION_PAIRS = (
    ("social", "financial", "social-impact-and-financial-viability"),
    ("technical", "budget", "technical-feasibility-and-budget"),
)


@dataclass(frozen=True)
class NodeDependencies:
    settings: LLMSettings
    repository: MunicipalityRepository = municipality_repository
    llm_client: LLMClient | None = None
    guardian_client: LLMClient | None = None


def _error_update(
    state: CouncilState,
    node: str,
    error: Exception,
) -> dict[str, Any]:
    root_error = error
    while root_error.__cause__ is not None:
        root_error = root_error.__cause__
    item = AnalysisError(
        node=node,
        error_type=type(root_error).__name__,
        message=str(error) or "Falha controlada sem mensagem adicional.",
    )
    logger.warning(
        "Falha em nó da análise",
        extra={
            "analysis_id": state.get("analysis_id"),
            "node": node,
            "error_type": item.error_type,
        },
    )
    return {
        "errors": [*state.get("errors", []), item],
        "warnings": [*state.get("warnings", []), f"{node}: {item.message}"],
    }


def _to_opposition(position: str) -> str:
    if position in {"favorable", "conditional"}:
        return "supportive"
    if position in {"unfavorable", "insufficient_data"}:
        return "cautious"
    return "unknown"


def detect_material_disagreements(
    opinions: list[AgentOpinion],
) -> list[Disagreement]:
    """Compara uma vez os pares social/financeiro e técnico/orçamentário."""
    by_role = {opinion.agent_name: opinion for opinion in opinions}
    disagreements: list[Disagreement] = []
    for left_role, right_role, topic in OPPOSITION_PAIRS:
        left = by_role.get(left_role)
        right = by_role.get(right_role)
        if left is None or right is None:
            continue
        if _to_opposition(left.position) == _to_opposition(right.position):
            continue
        disagreements.append(
            Disagreement(
                topic=topic,
                opinions=[
                    f"{left_role}: {left.position} — {left.summary}",
                    f"{right_role}: {right.position} — {right.summary}",
                ],
                resolution_status="requires_human_review",
                questions=[
                    "Que evidência adicional resolve a divergência entre "
                    f"{left_role} e {right_role}?",
                    "Quais premissas precisam de validação antes de uma decisão?",
                ],
            )
        )
    return disagreements


def make_nodes(dependencies: NodeDependencies) -> dict[str, Callable[..., Any]]:
    """Cria nós com dependências explícitas para testes e execução local."""

    async def validate_input(state: CouncilState) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        updates: dict[str, Any] = {
            "analysis_id": state.get("analysis_id") or str(uuid4()),
            "created_at": state.get("created_at") or now,
            "mode": dependencies.settings.llm_provider,
            "warnings": list(state.get("warnings", [])),
            "errors": list(state.get("errors", [])),
            "opinions": [],
            "status": "running",
        }
        try:
            if not state.get("municipality_code"):
                raise ValueError("municipality_code é obrigatório.")
            raw_parameters = state.get("parameters")
            if raw_parameters is None:
                raise ValueError("parameters são obrigatórios.")
            updates["parameters"] = SimulationParameters.model_validate(raw_parameters)
            selected_ids = list(state.get("selected_anchor_ids", []))
            if len(selected_ids) != len(set(selected_ids)):
                raise ValueError("selected_anchor_ids contém IDs duplicados.")
            updates["selected_anchor_ids"] = selected_ids
            updates["municipality_code"] = state["municipality_code"]
        except Exception as exc:
            updates.update(_error_update(state, "validate_input", exc))
            updates["status"] = "failed"
        return updates

    async def load_municipality(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        municipality = dependencies.repository.get_municipality(state["municipality_code"])
        if municipality is None:
            error = LookupError(
                f"Localidade não encontrada: {state['municipality_code']}."
            )
            return {**_error_update(state, "load_municipality", error), "status": "failed"}

        try:
            raw_catalog = state.get("evidence_catalog")
            catalog = (
                municipality.indicators
                if raw_catalog is None
                else [Evidence.model_validate(item) for item in raw_catalog]
            )
            available_ids = {item.evidence_id for item in municipality.indicators}
            catalog_ids = [item.evidence_id for item in catalog]
            if len(catalog_ids) != len(set(catalog_ids)):
                raise ValueError("evidence_catalog contém IDs duplicados.")
            if set(catalog_ids) - available_ids:
                raise ValueError("evidence_catalog contém IDs fora da localidade.")
            anchor_ids = {
                institution.institution_id for institution in municipality.anchor_institutions
            }
            unknown_selected_ids = set(state.get("selected_anchor_ids", [])) - anchor_ids
            if unknown_selected_ids:
                raise ValueError(
                    "selected_anchor_ids contém instituição fora da localidade: "
                    f"{sorted(unknown_selected_ids)}"
                )
        except Exception as exc:
            return {**_error_update(state, "load_municipality", exc), "status": "failed"}

        return {"municipality": municipality, "evidence_catalog": catalog}

    async def opinion_node(state: CouncilState, role: str, agent: AgentFunction) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        try:
            async with asyncio.timeout(NODE_TIMEOUT_SECONDS):
                opinion = await agent(
                    state["municipality"],
                    evidence_catalog=state["evidence_catalog"],
                    parameters=state["parameters"],
                    llm_client=dependencies.llm_client,
                    settings=dependencies.settings,
                )
            return {"opinions": [*state.get("opinions", []), opinion]}
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                exc = TimeoutError(f"Tempo limite de {NODE_TIMEOUT_SECONDS}s no agente {role}.")
            return _error_update(state, role, exc)

    async def financial(state: CouncilState) -> dict[str, Any]:
        return await opinion_node(state, "financial", analyze_financial)

    async def social(state: CouncilState) -> dict[str, Any]:
        return await opinion_node(state, "social", analyze_social)

    async def technical(state: CouncilState) -> dict[str, Any]:
        return await opinion_node(state, "technical", analyze_technical)

    async def budget(state: CouncilState) -> dict[str, Any]:
        return await opinion_node(state, "budget", analyze_budget)

    async def collect_opinions(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        roles = [opinion.agent_name for opinion in state.get("opinions", [])]
        if len(roles) != len(set(roles)):
            return _error_update(
                state,
                "collect_opinions",
                ValueError("Papéis de agentes duplicados no resultado."),
            )
        if len(roles) < 4:
            warning = "Uma ou mais opiniões não foram produzidas; análise parcial sinalizada."
            return {"warnings": [*state.get("warnings", []), warning]}
        return {}

    async def bridges(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        try:
            async with asyncio.timeout(NODE_TIMEOUT_SECONDS):
                proposal = await propose_bridges(
                    state["municipality"],
                    evidence_catalog=state["evidence_catalog"],
                    llm_client=dependencies.llm_client,
                    settings=dependencies.settings,
                )
            selected_ids = state.get("selected_anchor_ids", [])
            proposed_ids = {item.institution_id for item in proposal.candidates}
            if set(selected_ids) - proposed_ids:
                raise ValueError("selected_anchor_ids contém instituição ausente da proposta.")
            return {"bridge_proposal": proposal}
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                exc = TimeoutError(f"Tempo limite de {NODE_TIMEOUT_SECONDS}s no Agente de Pontes.")
            return {
                **_error_update(state, "bridges", exc),
                "bridge_proposal": BridgeProposal(
                    notes=["Proposta indisponível; nenhuma parceria foi presumida."]
                ),
                "selected_anchor_ids": [],
            }

    async def simulate_scenarios(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        baseline = simulate_baseline(state["parameters"])
        with_bridges = simulate_with_bridges(
            state["parameters"],
            state["municipality"],
            state.get("selected_anchor_ids", []),
        )
        return {
            "baseline": baseline,
            "with_bridges": with_bridges,
            "comparison": compare_scenarios(baseline, with_bridges),
        }

    async def challenge_round(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        return {"disagreements": detect_material_disagreements(state.get("opinions", []))}

    async def guardian(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        try:
            async with asyncio.timeout(NODE_TIMEOUT_SECONDS):
                draft = await generate_guardian_draft(
                    municipality=state["municipality"],
                    evidence_catalog=state["evidence_catalog"],
                    opinions=state.get("opinions", []),
                    disagreements=state.get("disagreements", []),
                    baseline=state["baseline"],
                    with_bridges=state["with_bridges"],
                    comparison=state["comparison"],
                    warnings=state.get("warnings", []),
                    llm_client=dependencies.guardian_client or dependencies.llm_client,
                    settings=dependencies.settings,
                )
            return {"guardian_draft": draft}
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                exc = TimeoutError(f"Tempo limite de {NODE_TIMEOUT_SECONDS}s no Guardião.")
            failure = _error_update(state, "guardian", exc)
            fallback = GuardianDecision(
                decision=Decision.HUMAN_REVIEW,
                rationale=(
                    "O Guardião não produziu uma síntese válida; esta resposta parcial exige "
                    "revisão humana e não é um parecer normal."
                ),
                conditions=["Reexecutar após corrigir a falha do Guardião."],
                blockers=["Síntese automatizada indisponível."],
                unresolved_questions=["As opiniões e cenários precisam de revisão humana."],
                cited_evidence_ids=[],
            )
            return {**failure, "guardian_draft": fallback}

    async def apply_guards(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        material_conflict = any(
            disagreement.resolution_status == "requires_human_review"
            for disagreement in state.get("disagreements", [])
        )
        final = apply_decision_guards(
            state["guardian_draft"],
            state["municipality"],
            state["with_bridges"],
            material_technical_financial_conflict=material_conflict,
        )
        if state.get("errors"):
            final = final.model_copy(
                update={
                    "decision": Decision.HUMAN_REVIEW,
                    "final_decision": Decision.HUMAN_REVIEW,
                    "original_decision": final.original_decision or final.decision,
                    "rationale": (
                        f"{final.rationale} A análise está degradada por falhas identificadas; "
                        "é necessária revisão humana."
                    ),
                    "guard_reasons": [
                        *final.guard_reasons,
                        "A análise contém erros e não pode ser tratada como completa.",
                    ],
                }
            )
        return {"guardian_final": final}

    async def finalize(state: CouncilState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        warnings = list(state.get("warnings", []))
        municipality = state["municipality"]
        if municipality.is_synthetic and not any("sintétic" in item.lower() for item in warnings):
            warnings.append("Dados sintéticos: esta análise é demonstrativa, não operacional.")
        return {
            "status": "degraded" if state.get("errors") else "completed",
            "warnings": warnings,
        }

    return {
        "validate_input": validate_input,
        "load_municipality": load_municipality,
        "financial": financial,
        "social": social,
        "technical": technical,
        "budget": budget,
        "collect_opinions": collect_opinions,
        "bridges": bridges,
        "simulate_scenarios": simulate_scenarios,
        "challenge_round": challenge_round,
        "guardian": guardian,
        "apply_guards": apply_guards,
        "finalize": finalize,
    }
