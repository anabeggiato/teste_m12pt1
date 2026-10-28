"""Estado tipado compartilhado pelos nós sequenciais do conselho."""

from typing import Literal, TypedDict

from conecta_conselho.domain.models import (
    AgentOpinion,
    AnalysisError,
    BridgeProposal,
    Disagreement,
    Evidence,
    GuardianDecision,
    Municipality,
    ScenarioComparison,
    ScenarioResult,
    SimulationParameters,
)


class CouncilState(TypedDict, total=False):
    analysis_id: str
    created_at: str
    municipality_code: str
    municipality: Municipality
    parameters: SimulationParameters
    evidence_catalog: list[Evidence]
    selected_anchor_ids: list[str]
    opinions: list[AgentOpinion]
    bridge_proposal: BridgeProposal
    baseline: ScenarioResult
    with_bridges: ScenarioResult
    comparison: ScenarioComparison
    disagreements: list[Disagreement]
    guardian_draft: GuardianDecision
    guardian_final: GuardianDecision
    warnings: list[str]
    errors: list[AnalysisError]
    status: Literal["pending", "running", "completed", "degraded", "failed"]
    mode: Literal["mock", "ollama"]

