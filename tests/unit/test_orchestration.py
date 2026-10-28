import asyncio
from typing import Any

from pydantic import BaseModel

from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import AgentOpinion, GuardianDecision, SimulationParameters
from conecta_conselho.llm.base import LLMClient, LLMClientError
from conecta_conselho.llm.mock import MockLLMClient
from conecta_conselho.orchestration.graph import build_council_graph, run_council
from conecta_conselho.orchestration.nodes import detect_material_disagreements


def mock_settings() -> LLMSettings:
    return LLMSettings(llm_provider="mock", max_agent_retries=1, _env_file=None)


def unsafe_investment() -> dict[str, object]:
    return GuardianDecision(
        decision="INVESTIR",
        rationale="Teste de proposta preliminar insegura.",
        requires_human_approval=True,
    ).model_dump(mode="json")


class FailingRoleClient(LLMClient):
    provider_name = "mock"
    model_name = None

    def __init__(self, failing_role: str) -> None:
        self.failing_role = failing_role
        self.delegate = MockLLMClient()

    async def generate_structured(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        schema: type[BaseModel],
    ) -> Any:
        if payload.get("agent_role") == self.failing_role:
            raise LLMClientError("falha simulada do agente")
        return await self.delegate.generate_structured(system_prompt, payload, schema)


class ConflictingReviewClient(LLMClient):
    provider_name = "mock"
    model_name = None

    def __init__(self) -> None:
        self.delegate = MockLLMClient()

    async def generate_structured(
        self,
        system_prompt: str,
        payload: dict[str, Any],
        schema: type[BaseModel],
    ) -> Any:
        role = payload.get("agent_role")
        if schema is AgentOpinion and role in {"financial", "social"}:
            return {
                "agent_name": role,
                "position": "unfavorable" if role == "financial" else "favorable",
                "summary": f"Parecer de teste {role}.",
                "supporting_evidence_ids": [
                    "DEMO002-DEMAND-01" if role == "financial" else "DEMO002-GAP-01"
                ],
                "risks": [],
                "assumptions": [],
                "missing_data": [],
                "confidence_level": "low",
            }
        return await self.delegate.generate_structured(system_prompt, payload, schema)


def test_graph_runs_four_reviewers_bridge_simulation_challenge_and_guardian() -> None:
    parameters = SimulationParameters(
        budget_ceiling_brl=500_000,
        estimated_base_cost_brl=450_000,
        estimated_cost_per_anchor_brl=20_000,
        hypothetical_monthly_anchor_revenue_brl=2_500,
    )
    selected = ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]

    state, result = asyncio.run(
        run_council(
            municipality_code="DEMO002",
            parameters=parameters,
            selected_anchor_ids=selected,
            settings=mock_settings(),
        )
    )

    assert result is not None
    assert state["status"] == "completed"
    assert state["analysis_id"]
    assert len(result.opinions) == 4
    assert {item.agent_name for item in result.opinions} == {
        "financial",
        "social",
        "technical",
        "budget",
    }
    assert result.with_bridges.selected_anchor_ids == selected
    assert result.baseline.estimated_total_cost_brl == 450_000
    assert result.with_bridges.estimated_total_cost_brl == 490_000
    assert result.comparison.incremental_cost_brl == 40_000
    assert result.comparison.incremental_hypothetical_revenue_brl == 60_000
    assert result.status == "completed"
    assert result.guardian.requires_human_approval is True
    assert result.guardian.decision == "REVISAO_HUMANA"
    assert result.mode == "mock"


def test_graph_is_one_pass_and_invalid_municipality_fails_without_analysis() -> None:
    graph = build_council_graph(settings=mock_settings())
    assert list(graph.get_graph().nodes).count("challenge_round") == 1

    state, result = asyncio.run(
        run_council(
            municipality_code="UNKNOWN",
            parameters=SimulationParameters(budget_ceiling_brl=1),
            settings=mock_settings(),
        )
    )

    assert result is None
    assert state["status"] == "failed"
    assert state["errors"][0].node == "load_municipality"


def test_failed_llm_agent_returns_degraded_partial_result_without_fake_opinion() -> None:
    state, result = asyncio.run(
        run_council(
            municipality_code="DEMO002",
            parameters=SimulationParameters(
                budget_ceiling_brl=500_000,
                estimated_base_cost_brl=450_000,
            ),
            settings=mock_settings(),
            llm_client=FailingRoleClient("social"),
        )
    )

    assert result is not None
    assert state["status"] == "degraded"
    assert result.status == "degraded"
    assert len(result.opinions) == 3
    assert "social" not in {item.agent_name for item in result.opinions}
    assert any(error.node == "social" for error in result.errors)
    assert result.guardian.decision == "REVISAO_HUMANA"
    assert result.guardian.requires_human_approval is True


def test_guardian_investment_is_blocked_when_scenario_cost_is_unknown() -> None:
    _, result = asyncio.run(
        run_council(
            municipality_code="DEMO003",
            parameters=SimulationParameters(budget_ceiling_brl=500_000),
            settings=mock_settings(),
            guardian_client=MockLLMClient([unsafe_investment()]),
        )
    )

    assert result is not None
    assert result.with_bridges.estimated_total_cost_brl is None
    assert result.guardian.decision == "REVISAO_HUMANA"
    assert result.guardian.original_decision == "INVESTIR"
    assert any("Custo ou comparação" in reason for reason in result.guardian.guard_reasons)


def test_guardian_investment_is_blocked_on_material_technical_financial_conflict() -> None:
    _, result = asyncio.run(
        run_council(
            municipality_code="DEMO002",
            parameters=SimulationParameters(
                budget_ceiling_brl=500_000,
                estimated_base_cost_brl=450_000,
            ),
            settings=mock_settings(),
            llm_client=ConflictingReviewClient(),
            guardian_client=MockLLMClient([unsafe_investment()]),
        )
    )

    assert result is not None
    assert result.disagreements
    assert result.guardian.decision == "REVISAO_HUMANA"
    assert result.guardian.original_decision == "INVESTIR"
    assert any("Divergência material" in reason for reason in result.guardian.guard_reasons)


def test_challenge_round_detects_social_financial_opposition_once() -> None:
    opinions = [
        AgentOpinion(
            agent_name="social",
            position="favorable",
            summary="Há prioridade social.",
            supporting_evidence_ids=["SOCIAL-01"],
            confidence_level="low",
        ),
        AgentOpinion(
            agent_name="financial",
            position="unfavorable",
            summary="Persistem riscos financeiros.",
            supporting_evidence_ids=["FINANCIAL-01"],
            confidence_level="low",
        ),
    ]

    disagreements = detect_material_disagreements(opinions)

    assert len(disagreements) == 1
    assert disagreements[0].resolution_status == "requires_human_review"
    assert "social-impact-and-financial-viability" in disagreements[0].topic
