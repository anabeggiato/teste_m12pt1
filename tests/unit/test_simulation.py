import pytest
from pydantic import ValidationError

from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.domain.enums import Decision, EvidenceKind
from conecta_conselho.domain.models import (
    AnchorInstitution,
    Evidence,
    GuardianDecision,
    Municipality,
    SimulationParameters,
)
from conecta_conselho.domain.simulation import (
    apply_decision_guards,
    compare_scenarios,
    simulate_baseline,
    simulate_with_bridges,
)


def parameters(
    *,
    budget: float = 500_000,
    base_cost: float | None = 350_000,
    anchor_cost: float | None = 20_000,
    monthly_revenue: float | None = 2_500,
    horizon: int = 12,
) -> SimulationParameters:
    return SimulationParameters(
        budget_ceiling_brl=budget,
        estimated_base_cost_brl=base_cost,
        estimated_cost_per_anchor_brl=anchor_cost,
        hypothetical_monthly_anchor_revenue_brl=monthly_revenue,
        scenario_horizon_months=horizon,
    )


def guardian_decision(decision: Decision = Decision.INVEST) -> GuardianDecision:
    return GuardianDecision(decision=decision, rationale="Parecer preliminar para teste.")


def municipality_with_observed_connectivity() -> Municipality:
    """Fixture unitária para testar gates sem depender de dados reais externos."""
    return Municipality(
        municipality_code="TEST001",
        name="Localidade de teste",
        state_code="XX",
        indicators=[
            Evidence(
                evidence_id="TEST001-COVERAGE",
                indicator="reported_coverage_pct",
                value=75,
                unit="%",
                kind=EvidenceKind.OBSERVED,
                source_name="Registro observado de teste",
            )
        ],
        anchor_institutions=[],
        is_synthetic=False,
    )


def test_simulate_baseline_cost_equal_to_budget_is_within_budget() -> None:
    baseline = simulate_baseline(parameters(budget=350_000, base_cost=350_000))

    assert baseline.estimated_total_cost_brl == 350_000
    assert baseline.hypothetical_anchor_revenue_brl == 0
    assert baseline.within_budget is True


def test_simulate_baseline_unknown_cost_preserves_null_budget_status() -> None:
    baseline = simulate_baseline(parameters(base_cost=None))

    assert baseline.estimated_total_cost_brl is None
    assert baseline.within_budget is None


def test_zero_anchors_returns_the_baseline_scenario_unchanged() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    with_bridges = simulate_with_bridges(parameters(), municipality, [])

    assert with_bridges == baseline


def test_one_and_multiple_anchors_have_deterministic_costs_and_revenue() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    selected = ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]

    result = simulate_with_bridges(parameters(), municipality, selected)

    assert result.estimated_total_cost_brl == 390_000
    assert result.hypothetical_anchor_revenue_brl == 60_000
    assert result.hypothetical_net_balance_brl == 20_000
    assert result.within_budget is True
    assert result.selected_anchor_ids == selected
    assert any("sintéticas" in warning for warning in result.warnings)


def test_with_bridges_cost_equal_to_budget_is_within_budget() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    result = simulate_with_bridges(
        parameters(budget=390_000), municipality, ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]
    )

    assert result.within_budget is True


def test_with_bridges_cost_above_budget_is_outside_budget() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    result = simulate_with_bridges(
        parameters(budget=389_999), municipality, ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]
    )

    assert result.estimated_total_cost_brl == 390_000
    assert result.within_budget is False


def test_missing_anchor_cost_keeps_total_cost_balance_and_budget_unknown() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    result = simulate_with_bridges(
        parameters(anchor_cost=None), municipality, ["DEMO002-SCHOOL-01"]
    )

    assert result.estimated_total_cost_brl is None
    assert result.hypothetical_anchor_revenue_brl == 30_000
    assert result.hypothetical_net_balance_brl is None
    assert result.within_budget is None


def test_missing_base_cost_is_not_imputed() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    result = simulate_with_bridges(
        parameters(base_cost=None), municipality, ["DEMO002-SCHOOL-01"]
    )

    assert result.estimated_total_cost_brl is None
    assert result.within_budget is None


@pytest.mark.parametrize(
    "values",
    [
        {"budget_ceiling_brl": -1},
        {"budget_ceiling_brl": 1, "estimated_base_cost_brl": -1},
        {"budget_ceiling_brl": 1, "estimated_cost_per_anchor_brl": -1},
        {"budget_ceiling_brl": 1, "hypothetical_monthly_anchor_revenue_brl": -1},
    ],
)
def test_negative_monetary_values_are_rejected(values: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        SimulationParameters(**values)


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_non_finite_monetary_values_are_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        SimulationParameters(budget_ceiling_brl=value)


def test_duplicate_anchor_ids_are_rejected() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    with pytest.raises(ValueError, match="duplicados"):
        simulate_with_bridges(
            parameters(), municipality, ["DEMO002-SCHOOL-01", "DEMO002-SCHOOL-01"]
        )


def test_unknown_anchor_id_is_rejected() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None

    with pytest.raises(ValueError, match="inexistentes"):
        simulate_with_bridges(parameters(), municipality, ["NOT-A-REAL-ID"])


def test_scenario_comparison_preserves_unknowns_and_reports_incremental_values() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    baseline = simulate_baseline(parameters())
    with_bridges = simulate_with_bridges(
        parameters(), municipality, ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"]
    )

    comparison = compare_scenarios(baseline, with_bridges)

    assert comparison.baseline_cost_brl == 350_000
    assert comparison.with_bridges_cost_brl == 390_000
    assert comparison.incremental_cost_brl == 40_000
    assert comparison.incremental_hypothetical_revenue_brl == 60_000
    assert comparison.hypothetical_net_balance_brl == 20_000


def test_scenario_comparison_does_not_impute_missing_costs_or_revenue() -> None:
    municipality = municipality_repository.get_municipality("DEMO002")
    assert municipality is not None
    params = parameters(base_cost=None, anchor_cost=None, monthly_revenue=None)
    baseline = simulate_baseline(params)
    with_bridges = simulate_with_bridges(params, municipality, ["DEMO002-SCHOOL-01"])

    comparison = compare_scenarios(baseline, with_bridges)

    assert comparison.baseline_cost_brl is None
    assert comparison.with_bridges_cost_brl is None
    assert comparison.incremental_cost_brl is None
    assert comparison.incremental_hypothetical_revenue_brl is None
    assert comparison.hypothetical_net_balance_brl is None
    assert comparison.within_budget is None


def test_guard_blocks_investment_when_cost_is_unknown() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters(base_cost=None))

    guarded = apply_decision_guards(guardian_decision(), municipality, baseline)

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert guarded.original_decision == Decision.INVEST
    assert guarded.final_decision == Decision.HUMAN_REVIEW
    assert any("Custo" in reason for reason in guarded.guard_reasons)
    assert "Salvaguardas aplicadas" in guarded.rationale


def test_guard_requires_review_when_connectivity_evidence_is_missing() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    guarded = apply_decision_guards(guardian_decision(), municipality, baseline)

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert any("conectividade" in reason for reason in guarded.guard_reasons)


def test_guard_changes_over_budget_investment_to_wait() -> None:
    municipality = municipality_with_observed_connectivity()
    over_budget = simulate_baseline(parameters(budget=349_999))

    guarded = apply_decision_guards(guardian_decision(), municipality, over_budget)

    assert guarded.decision == Decision.WAIT
    assert any("ultrapassa o teto" in reason for reason in guarded.guard_reasons)


def test_guard_requires_review_for_material_technical_financial_conflict() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    guarded = apply_decision_guards(
        guardian_decision(),
        municipality,
        baseline,
        material_technical_financial_conflict=True,
    )

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert any("Divergência material" in reason for reason in guarded.guard_reasons)


def test_guard_blocks_investment_based_only_on_synthetic_data() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    guarded = apply_decision_guards(guardian_decision(), municipality, baseline)

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert any("Dados sintéticos" in reason for reason in guarded.guard_reasons)


def test_guard_blocks_operational_pilot_based_only_on_synthetic_data() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    guarded = apply_decision_guards(guardian_decision(Decision.PILOT), municipality, baseline)

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert guarded.original_decision == Decision.PILOT
    assert any("Dados sintéticos" in reason for reason in guarded.guard_reasons)


def test_guard_blocks_investment_using_a_synthetic_selected_anchor() -> None:
    municipality = municipality_with_observed_connectivity().model_copy(
        update={
            "anchor_institutions": [
                AnchorInstitution(
                    institution_id="TEST001-SCHOOL-01",
                    name="Escola de teste sintética",
                    institution_type="school",
                    municipality_code="TEST001",
                    is_synthetic=True,
                )
            ]
        }
    )
    scenario = simulate_with_bridges(
        parameters(), municipality, ["TEST001-SCHOOL-01"]
    )

    guarded = apply_decision_guards(guardian_decision(), municipality, scenario)

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert any("instituição selecionada é sintética" in reason for reason in guarded.guard_reasons)


def test_guard_requires_review_for_preliminary_wait_when_evidence_is_missing() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None
    baseline = simulate_baseline(parameters())

    guarded = apply_decision_guards(
        guardian_decision(Decision.WAIT), municipality, baseline
    )

    assert guarded.decision == Decision.HUMAN_REVIEW
    assert any("conectividade" in reason for reason in guarded.guard_reasons)
    assert guarded.original_decision == Decision.WAIT
    assert guarded.final_decision == Decision.HUMAN_REVIEW
