import pytest
from pydantic import ValidationError

from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.domain.enums import ConnectivityStatus, Decision, EvidenceKind
from conecta_conselho.domain.models import (
    SYNTHETIC_SOURCE_NAME,
    AgentOpinion,
    AnalysisResult,
    AnchorInstitution,
    BridgeProposal,
    Evidence,
    GuardianDecision,
    Municipality,
    ScenarioResult,
    SimulationParameters,
)


def test_synthetic_fixtures_have_expected_shapes_and_provenance() -> None:
    municipalities = [
        municipality_repository.get_municipality(code)
        for code in ("DEMO001", "DEMO002", "DEMO003")
    ]

    assert all(municipality is not None for municipality in municipalities)
    for municipality in municipalities:
        assert municipality is not None
        assert municipality.is_synthetic is True
        assert 8 <= len(municipality.indicators) <= 12
        assert 2 <= len(municipality.anchor_institutions) <= 4
        assert all(item.is_synthetic for item in municipality.indicators)
        assert all(item.is_synthetic for item in municipality.anchor_institutions)
        assert all(item.source_name == SYNTHETIC_SOURCE_NAME for item in municipality.indicators)


def test_unavailable_indicator_remains_null_and_unknown_connectivity_is_not_unconnected() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")

    assert municipality is not None
    missing_income = next(
        item for item in municipality.indicators if item.indicator == "monthly_income_proxy_brl"
    )
    assert missing_income.value is None
    assert missing_income.kind == EvidenceKind.UNAVAILABLE
    assert municipality.anchor_institutions[0].connectivity_status == ConnectivityStatus.UNKNOWN


def test_unavailable_evidence_cannot_contain_a_value() -> None:
    with pytest.raises(ValidationError, match="value=null"):
        Evidence(
            evidence_id="E-1",
            indicator="missing_measurement",
            value=0,
            kind=EvidenceKind.UNAVAILABLE,
            source_name=SYNTHETIC_SOURCE_NAME,
            is_synthetic=True,
        )


def test_synthetic_evidence_requires_synthetic_source_name() -> None:
    with pytest.raises(ValidationError, match="source_name"):
        Evidence(
            evidence_id="E-1",
            indicator="hypothetical_measurement",
            value=1,
            kind=EvidenceKind.HYPOTHETICAL,
            source_name="Fonte oficial",
            is_synthetic=True,
        )


def test_monetary_parameters_reject_negative_values() -> None:
    with pytest.raises(ValidationError):
        SimulationParameters(budget_ceiling_brl=-1)


def test_municipality_rejects_unknown_evidence_reference() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    raw = municipality.model_dump(mode="json")
    raw["anchor_institutions"][0]["evidence_ids"] = ["MISSING-EVIDENCE"]

    with pytest.raises(ValidationError, match="evidências inexistentes"):
        Municipality.model_validate(raw)


def test_municipality_rejects_institution_from_another_locality() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    raw = municipality.model_dump(mode="json")
    raw["anchor_institutions"][0]["municipality_code"] = "DEMO002"

    with pytest.raises(ValidationError, match="pertence a outra localidade"):
        Municipality.model_validate(raw)


def test_institution_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError, match="institution_type"):
        AnchorInstitution(
            institution_id="DEMO001-UNKNOWN-01",
            name="Instituição Demonstração",
            institution_type="private_company",
            municipality_code="DEMO001",
        )


def test_analysis_result_rejects_nonexistent_cited_evidence_id() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    scenario = ScenarioResult(
        scenario_name="Base",
        estimated_total_cost_brl=100,
        hypothetical_anchor_revenue_brl=0,
        hypothetical_net_balance_brl=0,
        within_budget=True,
    )

    with pytest.raises(ValidationError, match="evidências inexistentes"):
        AnalysisResult(
            analysis_id="analysis-test",
            created_at="2026-01-01T00:00:00Z",
            municipality=municipality,
            opinions=[
                AgentOpinion(
                    agent_name="financeiro",
                    position="conditional",
                    summary="Parecer de teste.",
                    supporting_evidence_ids=["UNKNOWN-EVIDENCE"],
                    confidence_level="low",
                )
            ],
            bridge_proposal=BridgeProposal(),
            baseline=scenario,
            with_bridges=scenario,
            guardian=GuardianDecision(
                decision=Decision.WAIT,
                rationale="Decisão de teste.",
            ),
            evidence_catalog=municipality.indicators,
            mode="mock",
        )
