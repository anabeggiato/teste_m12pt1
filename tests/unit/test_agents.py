import asyncio

import pytest
from pydantic import ValidationError

from conecta_conselho.agents.base import (
    AgentContextError,
    AgentExecutionError,
    InvalidEvidenceReferenceError,
    StructuredOutputError,
    UntraceableOpinionError,
)
from conecta_conselho.agents.bridges import (
    InvalidAnchorSelectionError,
    InvalidBridgeReferenceError,
    analyze_bridges,
)
from conecta_conselho.agents.budget import analyze_budget
from conecta_conselho.agents.financial import analyze_financial
from conecta_conselho.agents.social import analyze_social
from conecta_conselho.agents.technical import analyze_technical
from conecta_conselho.config import LLMSettings
from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.domain.enums import ConnectivityStatus, EvidenceKind
from conecta_conselho.domain.models import SimulationParameters
from conecta_conselho.llm.base import LLMClientError
from conecta_conselho.llm.mock import MockLLMClient


def settings(*, retries: int = 1) -> LLMSettings:
    return LLMSettings(llm_provider="mock", max_agent_retries=retries, _env_file=None)


def opinion_response(**overrides: object) -> dict[str, object]:
    response: dict[str, object] = {
        "agent_name": "financial",
        "position": "conditional",
        "summary": "Parecer de teste com evidência existente.",
        "supporting_evidence_ids": ["DEMO001-DEMAND-01"],
        "risks": [],
        "assumptions": [],
        "missing_data": [],
        "confidence_level": "low",
    }
    response.update(overrides)
    return response


def test_mock_financial_agent_returns_valid_cited_conditional_opinion() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    client = MockLLMClient()

    opinion = asyncio.run(
        analyze_financial(municipality, llm_client=client, settings=settings())
    )

    assert opinion.agent_name == "financial"
    assert opinion.position == "conditional"
    assert "ROI" in " ".join(opinion.risks)
    assert opinion.supporting_evidence_ids == ["DEMO001-DEMAND-01", "DEMO001-COST-01"]
    assert client.provider_name == "mock"
    assert "demand_proxy_index" in str(client.requests[0][1])


def test_financial_agent_reports_missing_cost_and_commercial_inputs() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None

    opinion = asyncio.run(
        analyze_financial(municipality, llm_client=MockLLMClient(), settings=settings())
    )

    assert opinion.position == "conditional"
    assert "custo estimado do cenário" in opinion.missing_data
    assert "preço e taxa de adesão" in opinion.missing_data
    assert "DEMO003-DEMAND-01" in opinion.supporting_evidence_ids


def test_promising_demand_proxy_with_missing_cost_stays_conditional() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    relevant_catalog = [
        evidence
        for evidence in municipality.indicators
        if evidence.indicator != "estimated_base_cost_brl"
    ]

    opinion = asyncio.run(
        analyze_financial(
            municipality,
            evidence_catalog=relevant_catalog,
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert opinion.position == "conditional"
    assert "custo estimado do cenário" in opinion.missing_data
    assert opinion.supporting_evidence_ids == ["DEMO001-DEMAND-01"]
    assert "ROI" in " ".join(opinion.risks)


def test_social_agent_does_not_convert_a_high_gap_into_investment() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    opinion = asyncio.run(
        analyze_social(municipality, llm_client=MockLLMClient(), settings=settings())
    )

    assert opinion.agent_name == "social"
    assert opinion.position == "conditional"
    assert opinion.supporting_evidence_ids == ["DEMO002-GAP-01"]
    assert "não comprova demanda contratante" in opinion.risks[0]
    assert "não descreve população real" in opinion.assumptions[0]
    assert opinion.confidence_level == "low"


def test_agents_report_insufficient_data_when_relevant_catalog_is_empty() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None
    client = MockLLMClient()

    financial = asyncio.run(
        analyze_financial(
            municipality,
            evidence_catalog=[],
            llm_client=client,
            settings=settings(),
        )
    )
    social = asyncio.run(
        analyze_social(
            municipality,
            evidence_catalog=[],
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert financial.position == "insufficient_data"
    assert "proxy de demanda" in financial.missing_data
    assert financial.supporting_evidence_ids == []
    assert social.position == "insufficient_data"
    assert social.supporting_evidence_ids == []


def test_agent_context_rejects_evidence_from_another_municipality() -> None:
    first = municipality_repository.get_municipality("DEMO001")
    second = municipality_repository.get_municipality("DEMO002")
    assert first is not None and second is not None

    with pytest.raises(AgentContextError, match="não pertencem à localidade"):
        asyncio.run(
            analyze_financial(
                first,
                evidence_catalog=[second.indicators[0]],
                llm_client=MockLLMClient(),
                settings=settings(),
            )
        )


def test_agent_rejects_nonexistent_evidence_citation() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    response = opinion_response(supporting_evidence_ids=["NOT-IN-CATALOG"])

    with pytest.raises(InvalidEvidenceReferenceError, match="evidências inexistentes"):
        asyncio.run(
            analyze_financial(
                municipality,
                llm_client=MockLLMClient([response]),
                settings=settings(),
            )
        )


def test_agent_rejects_conclusion_without_supporting_evidence() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    response = opinion_response(supporting_evidence_ids=[])

    with pytest.raises(UntraceableOpinionError, match="sem evidência de suporte"):
        asyncio.run(
            analyze_financial(
                municipality,
                llm_client=MockLLMClient([response]),
                settings=settings(),
            )
        )


def test_technical_agent_marks_missing_critical_infrastructure_as_insufficient() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None
    technical_catalog = [
        evidence
        for evidence in municipality.indicators
        if evidence.indicator in {"reported_coverage_pct", "backhaul_capacity_mbps"}
    ]

    opinion = asyncio.run(
        analyze_technical(
            municipality,
            evidence_catalog=technical_catalog,
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert opinion.agent_name == "technical"
    assert opinion.position == "insufficient_data"
    assert "survey de campo" in opinion.summary
    assert "capacidade de backhaul verificada" in opinion.missing_data
    assert "DEMO003-COVERAGE-01" in opinion.supporting_evidence_ids
    assert "DEMO003-BACKHAUL-01" in opinion.supporting_evidence_ids
    assert "fibra" in " ".join(opinion.risks).lower()


def test_technical_agent_keeps_hypothetical_values_as_conditional_triage() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    opinion = asyncio.run(
        analyze_technical(municipality, llm_client=MockLLMClient(), settings=settings())
    )

    assert opinion.position == "conditional"
    assert "não comprovam infraestrutura" in opinion.summary
    assert "DEMO002-BACKHAUL-01" in opinion.supporting_evidence_ids
    assert opinion.confidence_level == "low"


def test_budget_agent_reuses_baseline_and_marks_unknown_cost_insufficient() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None
    parameters = SimulationParameters(budget_ceiling_brl=500_000)
    client = MockLLMClient()

    opinion = asyncio.run(
        analyze_budget(
            municipality,
            parameters=parameters,
            llm_client=client,
            settings=settings(),
        )
    )

    assert opinion.agent_name == "budget"
    assert opinion.position == "insufficient_data"
    assert opinion.supporting_evidence_ids == []
    assert "custo" in " ".join(opinion.missing_data)
    assert client.requests[0][1]["additional_context"]["baseline_scenario"][
        "estimated_total_cost_brl"
    ] is None


def test_budget_agent_reports_hypothetical_cost_over_budget_without_inventing_metrics() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    parameters = SimulationParameters(
        budget_ceiling_brl=400_000,
        estimated_base_cost_brl=450_000,
    )

    opinion = asyncio.run(
        analyze_budget(
            municipality,
            parameters=parameters,
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert opinion.position == "unfavorable"
    assert opinion.supporting_evidence_ids == ["DEMO002-COST-01"]
    assert "excede o teto" in opinion.summary
    assert "orçamento formal aprovado" in opinion.missing_data
    assert "ROI" not in opinion.summary


def test_bridge_agent_ranks_demo_candidates_without_claiming_partnership(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    client = MockLLMClient()

    analysis = asyncio.run(
        analyze_bridges(
            municipality,
            SimulationParameters(
                budget_ceiling_brl=500_000,
                estimated_base_cost_brl=350_000,
                estimated_cost_per_anchor_brl=20_000,
                hypothetical_monthly_anchor_revenue_brl=2_500,
            ),
            selected_anchor_ids=[
                institution.institution_id
                for institution in municipality.anchor_institutions
            ],
            llm_client=client,
            settings=settings(),
        )
    )

    assert len(analysis.proposal.candidates) == 4
    assert all(item.partnership_status == "unverified" for item in analysis.proposal.candidates)
    assert all(item.priority == "medium" for item in analysis.proposal.candidates)
    assert analysis.baseline.estimated_total_cost_brl == 350_000
    assert analysis.with_bridges.estimated_total_cost_brl == 430_000
    assert analysis.comparison.incremental_cost_brl == 80_000
    assert analysis.with_bridges.hypothetical_anchor_revenue_brl == 120_000
    assert analysis.comparison.incremental_hypothetical_revenue_brl == 120_000
    assert analysis.comparison.hypothetical_net_balance_brl == 40_000
    assert "não representa proposta comercial" in analysis.with_bridges.warnings[0]
    assert any(
        getattr(record, "prompt_version", None) == "bridges-v1+base-v1"
        for record in caplog.records
    )


def test_bridge_agent_with_zero_selected_anchors_returns_baseline_comparison() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    analysis = asyncio.run(
        analyze_bridges(
            municipality,
            SimulationParameters(budget_ceiling_brl=500_000, estimated_base_cost_brl=350_000),
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert analysis.selected_anchor_ids == []
    assert analysis.with_bridges == analysis.baseline
    assert analysis.comparison.incremental_cost_brl == 0
    assert analysis.comparison.incremental_hypothetical_revenue_brl == 0


def test_bridge_agent_orders_qualitative_priorities_high_to_low() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    statuses = [
        ConnectivityStatus.CONNECTED,
        ConnectivityStatus.UNCONNECTED,
        ConnectivityStatus.UNKNOWN,
        ConnectivityStatus.CONNECTED,
    ]
    ranked_municipality = municipality.model_copy(
        update={
            "anchor_institutions": [
                institution.model_copy(update={"connectivity_status": status})
                for institution, status in zip(
                    municipality.anchor_institutions, statuses, strict=True
                )
            ]
        }
    )

    analysis = asyncio.run(
        analyze_bridges(
            ranked_municipality,
            SimulationParameters(budget_ceiling_brl=500_000),
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert [item.priority for item in analysis.proposal.candidates] == [
        "high",
        "medium",
        "low",
        "low",
    ]


def test_bridge_agent_allows_one_explicit_candidate_selection() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    anchor_id = municipality.anchor_institutions[0].institution_id

    analysis = asyncio.run(
        analyze_bridges(
            municipality,
            SimulationParameters(
                budget_ceiling_brl=500_000,
                estimated_base_cost_brl=350_000,
                estimated_cost_per_anchor_brl=20_000,
                hypothetical_monthly_anchor_revenue_brl=2_500,
            ),
            selected_anchor_ids=[anchor_id],
            llm_client=MockLLMClient(),
            settings=settings(),
        )
    )

    assert analysis.selected_anchor_ids == [anchor_id]
    assert analysis.with_bridges.estimated_total_cost_brl == 370_000
    assert analysis.comparison.incremental_cost_brl == 20_000


def test_bridge_agent_rejects_duplicate_selection() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    anchor_id = municipality.anchor_institutions[0].institution_id

    with pytest.raises(InvalidAnchorSelectionError, match="duplicados"):
        asyncio.run(
            analyze_bridges(
                municipality,
                SimulationParameters(budget_ceiling_brl=500_000),
                selected_anchor_ids=[anchor_id, anchor_id],
                llm_client=MockLLMClient(),
                settings=settings(),
            )
        )


def test_bridge_agent_rejects_selection_not_in_validated_proposal() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    with pytest.raises(InvalidAnchorSelectionError, match="ausentes da proposta"):
        asyncio.run(
            analyze_bridges(
                municipality,
                SimulationParameters(budget_ceiling_brl=500_000),
                selected_anchor_ids=["UNKNOWN-INSTITUTION"],
                llm_client=MockLLMClient(),
                settings=settings(),
            )
        )


def test_bridge_agent_rejects_nonexistent_candidate_and_evidence_ids() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    invalid_proposal = {
        "candidates": [
            {
                "institution_id": "UNKNOWN-INSTITUTION",
                "rationale": "Teste",
                "evidence_ids": ["UNKNOWN-EVIDENCE"],
                "assumptions": [],
                "partnership_status": "unverified",
                "priority": "low",
                "caveats": [],
            }
        ],
        "notes": [],
    }

    with pytest.raises(InvalidBridgeReferenceError, match="Instituição inexistente"):
        asyncio.run(
            analyze_bridges(
                municipality,
                SimulationParameters(budget_ceiling_brl=500_000),
                llm_client=MockLLMClient([invalid_proposal]),
                settings=settings(),
            )
        )


def test_bridge_agent_rejects_evidence_outside_the_provided_catalog() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    valid_institution_id = municipality.anchor_institutions[0].institution_id
    invalid_proposal = {
        "candidates": [
            {
                "institution_id": valid_institution_id,
                "rationale": "Teste",
                "evidence_ids": ["UNKNOWN-EVIDENCE"],
                "assumptions": [],
                "partnership_status": "unverified",
                "priority": "low",
                "caveats": [],
            }
        ],
        "notes": [],
    }

    with pytest.raises(InvalidBridgeReferenceError, match="fora do catálogo"):
        asyncio.run(
            analyze_bridges(
                municipality,
                SimulationParameters(budget_ceiling_brl=500_000),
                llm_client=MockLLMClient([invalid_proposal]),
                settings=settings(),
            )
        )


def test_bridge_agent_rejects_evidence_not_linked_to_candidate_institution() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    institution_id = municipality.anchor_institutions[0].institution_id
    unlinked_evidence_id = "DEMO002-COST-01"
    invalid_proposal = {
        "candidates": [
            {
                "institution_id": institution_id,
                "rationale": "Teste",
                "evidence_ids": [unlinked_evidence_id],
                "assumptions": [],
                "partnership_status": "unverified",
                "priority": "low",
                "caveats": [],
            }
        ],
        "notes": [],
    }

    with pytest.raises(InvalidBridgeReferenceError, match="não associadas"):
        asyncio.run(
            analyze_bridges(
                municipality,
                SimulationParameters(budget_ceiling_brl=500_000),
                llm_client=MockLLMClient([invalid_proposal]),
                settings=settings(),
            )
        )


def test_schema_validation_retries_once_with_error_feedback() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    invalid = opinion_response(position="invest")
    client = MockLLMClient([invalid, opinion_response()])

    opinion = asyncio.run(
        analyze_financial(municipality, llm_client=client, settings=settings(retries=1))
    )

    assert opinion.position == "conditional"
    assert len(client.requests) == 2
    assert "não passou pelo schema" in client.requests[1][0]


def test_invalid_schema_after_retry_fails_without_trusted_fallback() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    invalid = opinion_response(position="invest")
    client = MockLLMClient([invalid, invalid])

    with pytest.raises(StructuredOutputError, match="após 2 tentativa"):
        asyncio.run(
            analyze_financial(municipality, llm_client=client, settings=settings(retries=1))
        )

    assert len(client.requests) == 2


def test_provider_failure_is_controlled_and_does_not_fall_back_to_mock() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    client = MockLLMClient([LLMClientError("tempo limite simulado")])

    with pytest.raises(AgentExecutionError, match="Falha controlada"):
        asyncio.run(
            analyze_financial(municipality, llm_client=client, settings=settings())
        )

    assert len(client.requests) == 1


def test_agent_confidence_is_qualitative_and_mock_never_claims_generation() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    opinion = asyncio.run(
        analyze_social(municipality, llm_client=MockLLMClient(), settings=settings())
    )

    assert opinion.confidence_level in {"low", "medium", "high"}
    assert "probabilidade" not in opinion.summary.casefold()
    assert all(
        item.kind in {EvidenceKind.HYPOTHETICAL, EvidenceKind.UNAVAILABLE}
        for item in municipality.indicators
    )


def test_agent_response_is_validated_as_pydantic_model() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    response = opinion_response(confidence_level="certain")

    with pytest.raises(StructuredOutputError):
        asyncio.run(
            analyze_financial(
                municipality,
                llm_client=MockLLMClient([response, response]),
                settings=settings(retries=1),
            )
        )


def test_agent_does_not_mutate_municipality_evidence() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    before = [evidence.model_dump(mode="json") for evidence in municipality.indicators]

    asyncio.run(
        analyze_financial(municipality, llm_client=MockLLMClient(), settings=settings())
    )

    assert [evidence.model_dump(mode="json") for evidence in municipality.indicators] == before


def test_settings_disallow_more_than_one_agent_retry() -> None:
    with pytest.raises(ValidationError):
        LLMSettings(llm_provider="mock", max_agent_retries=2, _env_file=None)


def test_prompt_version_is_attached_to_llm_log_records(caplog: pytest.LogCaptureFixture) -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None

    with caplog.at_level("INFO", logger="conecta_conselho.agents.base"):
        asyncio.run(
            analyze_financial(municipality, llm_client=MockLLMClient(), settings=settings())
        )

    record = next(
        record for record in caplog.records if record.message == "Solicitando saída estruturada"
    )
    assert record.llm_provider == "mock"
    assert record.llm_model is None
    assert record.prompt_version == "financial-v1+base-v1"
