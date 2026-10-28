"""Scores descritivos configuráveis, reproduzíveis e não preditivos."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isclose, isfinite
from types import MappingProxyType

from conecta_conselho.domain.enums import EvidenceKind
from conecta_conselho.domain.models import Municipality, ScoreResult


def normalize_min_max(value: int | float, lower: float, upper: float) -> float:
    """Normaliza um número para [0, 1], saturando fora dos limites declarados."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("value deve ser numérico")
    if (isinstance(value, float) and not isfinite(value)) or not all(
        isfinite(bound) for bound in (lower, upper)
    ):
        raise ValueError("value e limites devem ser números finitos")
    if upper <= lower:
        raise ValueError("upper deve ser maior que lower")
    if value <= lower:
        return 0.0
    if value >= upper:
        return 1.0
    return min(1.0, max(0.0, (value - lower) / (upper - lower)))


@dataclass(frozen=True)
class IndicatorRule:
    indicator: str
    weight: float
    lower: float | None = None
    upper: float | None = None
    reverse: bool = False
    category_scores: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.indicator:
            raise ValueError("indicator não pode ser vazio")
        if not isfinite(self.weight) or not 0 <= self.weight <= 1:
            raise ValueError("weight deve ser finito e estar entre 0 e 1")
        if self.category_scores:
            if self.lower is not None or self.upper is not None:
                raise ValueError("regra categórica não deve declarar limites numéricos")
            if any(not isfinite(score) or not 0 <= score <= 1 for _, score in self.category_scores):
                raise ValueError("category_scores deve conter valores entre 0 e 1")
            categories = [name for name, _ in self.category_scores]
            if len(categories) != len(set(categories)):
                raise ValueError("category_scores não pode repetir categorias")
        elif (
            self.lower is None
            or self.upper is None
            or not isfinite(self.lower)
            or not isfinite(self.upper)
            or self.upper <= self.lower
        ):
            raise ValueError("regra numérica precisa de limites finitos com upper > lower")


@dataclass(frozen=True)
class ScoreDefinition:
    name: str
    rules: tuple[IndicatorRule, ...]

    def __post_init__(self) -> None:
        if not self.rules:
            raise ValueError("score precisa de ao menos uma regra")
        if not isclose(sum(rule.weight for rule in self.rules), 1.0, abs_tol=1e-9):
            raise ValueError(f"pesos de {self.name} devem somar 1.0")
        indicator_names = [rule.indicator for rule in self.rules]
        if len(indicator_names) != len(set(indicator_names)):
            raise ValueError(f"indicadores de {self.name} não podem se repetir")


# Limites são parâmetros explícitos desta heurística demonstrativa, não inferidos
# a partir das três fixtures. Alterações precisam ser documentadas e testadas.
DEFAULT_SCORE_CONFIG: Mapping[str, ScoreDefinition] = MappingProxyType({
    "market_opportunity": ScoreDefinition(
        name="market_opportunity",
        rules=(IndicatorRule("demand_proxy_index", weight=1.0, lower=0, upper=100),),
    ),
    "social_priority": ScoreDefinition(
        name="social_priority",
        rules=(IndicatorRule("social_access_gap_pct", weight=1.0, lower=0, upper=100),),
    ),
    "technical_feasibility": ScoreDefinition(
        name="technical_feasibility",
        rules=(
            IndicatorRule("reported_coverage_pct", weight=0.5, lower=0, upper=100),
            IndicatorRule(
                "technical_constraint_level",
                weight=0.5,
                category_scores=(("baixa", 1.0), ("moderada", 0.5), ("severa", 0.0)),
            ),
        ),
    ),
})


def _score_rule(
    rule: IndicatorRule,
    raw_value: float | int | str,
) -> float | None:
    if rule.category_scores:
        if not isinstance(raw_value, str):
            return None
        return dict(rule.category_scores).get(raw_value.casefold())
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        return None
    assert rule.lower is not None and rule.upper is not None
    value = normalize_min_max(raw_value, rule.lower, rule.upper)
    return 1.0 - value if rule.reverse else value


def score_municipality(
    municipality: Municipality,
    config: Mapping[str, ScoreDefinition] | None = None,
) -> dict[str, ScoreResult]:
    """Calcula scores disponíveis; dado configurado ausente deixa o score null."""
    score_config = DEFAULT_SCORE_CONFIG if config is None else config
    evidence_by_indicator = {item.indicator: item for item in municipality.indicators}
    results: dict[str, ScoreResult] = {}

    for name, definition in score_config.items():
        weighted_values: list[tuple[float, float]] = []
        evidence_ids: list[str] = []
        missing_indicators: list[str] = []

        for rule in definition.rules:
            evidence = evidence_by_indicator.get(rule.indicator)
            if evidence is None:
                missing_indicators.append(rule.indicator)
                continue
            evidence_ids.append(evidence.evidence_id)
            if evidence.kind == EvidenceKind.UNAVAILABLE or evidence.value is None:
                missing_indicators.append(rule.indicator)
                continue
            normalized = _score_rule(rule, evidence.value)
            if normalized is None:
                missing_indicators.append(rule.indicator)
                continue
            weighted_values.append((normalized, rule.weight))

        if missing_indicators:
            value = None
            explanation = (
                "Score indisponível: faltam indicadores configurados: "
                + ", ".join(missing_indicators)
                + ". Nenhum valor ausente foi imputado."
            )
        else:
            value = sum(score * weight for score, weight in weighted_values)
            explanation = (
                "Média ponderada determinística dos indicadores configurados; "
                "heurística de triagem sem validação preditiva."
            )

        results[name] = ScoreResult(
            score_name=name,
            value=value,
            evidence_ids=evidence_ids,
            missing_indicators=missing_indicators,
            explanation=explanation,
        )
    return results
