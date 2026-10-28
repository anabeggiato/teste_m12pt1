import pytest

from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.domain.scoring import (
    DEFAULT_SCORE_CONFIG,
    IndicatorRule,
    ScoreDefinition,
    normalize_min_max,
    score_municipality,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-10, 0.0), (-(10**500), 0.0), (0, 0.0), (50, 0.5), (100, 1.0), (110, 1.0), (10**500, 1.0)],
)
def test_normalize_min_max_saturates_and_normalizes(value: float, expected: float) -> None:
    assert normalize_min_max(value, 0, 100) == expected


def test_normalize_min_max_rejects_equal_or_reversed_limits() -> None:
    with pytest.raises(ValueError, match="upper"):
        normalize_min_max(5, 5, 5)
    with pytest.raises(ValueError, match="upper"):
        normalize_min_max(5, 10, 0)


def test_normalize_min_max_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finitos"):
        normalize_min_max(float("nan"), 0, 1)


def test_score_configuration_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="somar 1.0"):
        ScoreDefinition(
            name="invalid",
            rules=(IndicatorRule("one", weight=0.4, lower=0, upper=1),),
        )


def test_default_scores_use_declared_limits() -> None:
    municipality = municipality_repository.get_municipality("DEMO001")
    assert municipality is not None

    scores = score_municipality(municipality)

    assert scores["market_opportunity"].value == pytest.approx(0.86)
    assert scores["social_priority"].value == pytest.approx(0.18)
    assert scores["technical_feasibility"].value == pytest.approx(0.61)
    assert scores["market_opportunity"].evidence_ids == ["DEMO001-DEMAND-01"]


def test_score_with_missing_configured_indicator_is_null() -> None:
    municipality = municipality_repository.get_municipality("DEMO003")
    assert municipality is not None

    score = score_municipality(municipality)["technical_feasibility"]

    assert score.value is None
    assert score.missing_indicators == ["reported_coverage_pct"]
    assert "Score indisponível" in score.explanation


def test_score_config_has_unit_weights_for_each_dimension() -> None:
    assert all(
        sum(rule.weight for rule in definition.rules) == pytest.approx(1.0)
        for definition in DEFAULT_SCORE_CONFIG.values()
    )
