"""Schemas Pydantic dos dados e contratos do Conecta Conselho."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from conecta_conselho.domain.enums import (
    ConnectivityStatus,
    Decision,
    EvidenceKind,
    InstitutionType,
)

SYNTHETIC_SOURCE_NAME = "Cenário sintético de demonstração"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Evidence(DomainModel):
    evidence_id: str = Field(min_length=1)
    indicator: str = Field(min_length=1)
    value: float | int | str | None
    unit: str | None = None
    kind: EvidenceKind
    source_name: str = Field(min_length=1)
    source_url: str | None = None
    source_license: str | None = None
    reference_year: int | None = None
    collected_at: str | None = None
    is_synthetic: bool = False
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "Evidence":
        if self.kind == EvidenceKind.UNAVAILABLE and self.value is not None:
            raise ValueError("evidência indisponível deve ter value=null")
        if self.is_synthetic and self.source_name != SYNTHETIC_SOURCE_NAME:
            raise ValueError(
                f"evidência sintética deve usar source_name={SYNTHETIC_SOURCE_NAME!r}"
            )
        return self


class AnchorInstitution(DomainModel):
    institution_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    institution_type: InstitutionType
    municipality_code: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    connectivity_status: ConnectivityStatus = ConnectivityStatus.UNKNOWN
    is_synthetic: bool = False


class Municipality(DomainModel):
    municipality_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    state_code: str = Field(min_length=1)
    indicators: list[Evidence]
    anchor_institutions: list[AnchorInstitution]
    is_synthetic: bool

    @model_validator(mode="after")
    def validate_local_integrity(self) -> "Municipality":
        evidence_ids = [item.evidence_id for item in self.indicators]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_id duplicado na localidade")

        institution_ids = [item.institution_id for item in self.anchor_institutions]
        if len(institution_ids) != len(set(institution_ids)):
            raise ValueError("institution_id duplicado na localidade")

        known_evidence_ids = set(evidence_ids)
        for institution in self.anchor_institutions:
            if institution.municipality_code != self.municipality_code:
                raise ValueError(
                    f"instituição {institution.institution_id} pertence a outra localidade"
                )
            unknown_ids = set(institution.evidence_ids) - known_evidence_ids
            if unknown_ids:
                raise ValueError(
                    f"instituição {institution.institution_id} cita evidências inexistentes: "
                    f"{sorted(unknown_ids)}"
                )
            if self.is_synthetic and not institution.is_synthetic:
                raise ValueError("instituição sintética não pode perder is_synthetic=true")

        if self.is_synthetic and any(not item.is_synthetic for item in self.indicators):
            raise ValueError("evidência sintética não pode perder is_synthetic=true")
        return self


class AgentOpinion(DomainModel):
    agent_name: str = Field(min_length=1)
    position: Literal["favorable", "conditional", "unfavorable", "insufficient_data"]
    summary: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    confidence_level: Literal["low", "medium", "high"]


class SimulationParameters(DomainModel):
    budget_ceiling_brl: float = Field(ge=0)
    estimated_base_cost_brl: float | None = Field(default=None, ge=0)
    estimated_cost_per_anchor_brl: float | None = Field(default=None, ge=0)
    hypothetical_monthly_anchor_revenue_brl: float | None = Field(default=None, ge=0)
    scenario_horizon_months: int = Field(default=12, ge=1, le=120)


class ScenarioResult(DomainModel):
    scenario_name: str = Field(min_length=1)
    selected_anchor_ids: list[str] = Field(default_factory=list)
    estimated_total_cost_brl: float | None = Field(default=None, ge=0)
    hypothetical_anchor_revenue_brl: float | None = Field(default=None, ge=0)
    hypothetical_net_balance_brl: float | None = None
    within_budget: bool | None
    calculation_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_budget_status(self) -> "ScenarioResult":
        if self.estimated_total_cost_brl is None and self.within_budget is not None:
            raise ValueError("within_budget deve ser null quando o custo é desconhecido")
        return self


class ScenarioComparison(DomainModel):
    baseline_cost_brl: float | None = Field(default=None, ge=0)
    with_bridges_cost_brl: float | None = Field(default=None, ge=0)
    incremental_cost_brl: float | None = Field(default=None, ge=0)
    incremental_hypothetical_revenue_brl: float | None = Field(default=None, ge=0)
    hypothetical_net_balance_brl: float | None = None
    within_budget: bool | None
    warnings: list[str] = Field(default_factory=list)


class AnalysisRequest(DomainModel):
    municipality_code: str = Field(min_length=1)
    parameters: SimulationParameters
    selected_anchor_ids: list[str] | None = Field(default=None, max_length=20)


class BridgeCandidate(DomainModel):
    institution_id: str = Field(min_length=1)
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    partnership_status: Literal["unverified"] = "unverified"
    priority: Literal["low", "medium", "high"]
    caveats: list[str] = Field(default_factory=list)


class BridgeProposal(DomainModel):
    candidates: list[BridgeCandidate] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BridgeScenarioAnalysis(DomainModel):
    municipality: Municipality
    proposal: BridgeProposal
    selected_anchor_ids: list[str] = Field(default_factory=list)
    baseline: ScenarioResult
    with_bridges: ScenarioResult
    comparison: ScenarioComparison

    @model_validator(mode="after")
    def validate_bridge_references(self) -> "BridgeScenarioAnalysis":
        institution_ids = {
            institution.institution_id for institution in self.municipality.anchor_institutions
        }
        candidate_ids = [candidate.institution_id for candidate in self.proposal.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("institution_id duplicado na proposta de pontes")
        unknown_candidate_ids = set(candidate_ids) - institution_ids
        if unknown_candidate_ids:
            raise ValueError(
                f"candidatas inexistentes na localidade: {sorted(unknown_candidate_ids)}"
            )
        evidence_ids = {evidence.evidence_id for evidence in self.municipality.indicators}
        candidate_evidence_ids = {
            evidence_id
            for candidate in self.proposal.candidates
            for evidence_id in candidate.evidence_ids
        }
        unknown_evidence_ids = candidate_evidence_ids - evidence_ids
        if unknown_evidence_ids:
            raise ValueError(
                f"evidências inexistentes na proposta: {sorted(unknown_evidence_ids)}"
            )
        if len(self.selected_anchor_ids) != len(set(self.selected_anchor_ids)):
            raise ValueError("selected_anchor_ids contém IDs duplicados")
        unknown_selected_ids = set(self.selected_anchor_ids) - set(candidate_ids)
        if unknown_selected_ids:
            raise ValueError(
                f"instituições selecionadas não estão na proposta: {sorted(unknown_selected_ids)}"
            )
        if self.with_bridges.selected_anchor_ids != self.selected_anchor_ids:
            raise ValueError("cenário com pontes diverge da seleção informada")
        if self.baseline.selected_anchor_ids:
            raise ValueError("cenário base não pode conter instituições âncora")
        return self


class Disagreement(DomainModel):
    topic: str = Field(min_length=1)
    opinions: list[str] = Field(default_factory=list)
    resolution_status: str = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)


class GuardianDecision(DomainModel):
    decision: Decision
    original_decision: Decision | None = None
    final_decision: Decision | None = None
    guard_reasons: list[str] = Field(default_factory=list)
    rationale: str
    conditions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    requires_human_approval: Literal[True] = True


class AnalysisError(DomainModel):
    node: str = Field(min_length=1)
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class AnalysisResult(DomainModel):
    analysis_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    municipality: Municipality
    opinions: list[AgentOpinion] = Field(default_factory=list)
    bridge_proposal: BridgeProposal
    baseline: ScenarioResult
    with_bridges: ScenarioResult
    comparison: ScenarioComparison | None = None
    disagreements: list[Disagreement] = Field(default_factory=list)
    guardian: GuardianDecision
    evidence_catalog: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[AnalysisError] = Field(default_factory=list)
    status: Literal["completed", "degraded"] = "completed"
    mode: Literal["mock", "ollama"]

    @model_validator(mode="after")
    def validate_references(self) -> "AnalysisResult":
        if self.status == "degraded" and not self.errors:
            raise ValueError("análise degraded deve registrar ao menos um erro")
        if self.errors and self.status != "degraded":
            raise ValueError("análise com erros deve ter status degraded")
        evidence_ids = [item.evidence_id for item in self.evidence_catalog]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_id duplicado no catálogo da análise")
        available_evidence_ids = set(evidence_ids)
        institution_ids = {
            item.institution_id for item in self.municipality.anchor_institutions
        }

        referenced_evidence_ids = [
            *(
                evidence_id
                for opinion in self.opinions
                for evidence_id in opinion.supporting_evidence_ids
            ),
            *(
                evidence_id
                for candidate in self.bridge_proposal.candidates
                for evidence_id in candidate.evidence_ids
            ),
            *self.guardian.cited_evidence_ids,
        ]
        unknown_evidence_ids = set(referenced_evidence_ids) - available_evidence_ids
        if unknown_evidence_ids:
            raise ValueError(
                f"referências a evidências inexistentes: {sorted(unknown_evidence_ids)}"
            )

        selected_institution_ids = {
            *(
                candidate.institution_id
                for candidate in self.bridge_proposal.candidates
            ),
            *self.baseline.selected_anchor_ids,
            *self.with_bridges.selected_anchor_ids,
        }
        unknown_institution_ids = selected_institution_ids - institution_ids
        if unknown_institution_ids:
            raise ValueError(
                f"referências a instituições inexistentes: {sorted(unknown_institution_ids)}"
            )
        return self


class ScoreResult(DomainModel):
    score_name: Literal["market_opportunity", "social_priority", "technical_feasibility"]
    value: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_indicators: list[str] = Field(default_factory=list)
    explanation: str
