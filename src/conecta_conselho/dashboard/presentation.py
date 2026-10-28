"""Formatação de dados exibidos sem substituir valores ausentes por zero."""

from typing import Any

KIND_LABELS = {
    "observed": "Observado",
    "estimated": "Estimado",
    "hypothetical": "Hipotético",
    "unavailable": "Indisponível",
}
INDICATOR_LABELS = {
    "population_estimate": "População estimada",
    "resident_population": "População residente (Censo 2022)",
    "demand_proxy_index": "Índice proxy de demanda",
    "social_access_gap_pct": "Lacuna de acesso social",
    "monthly_income_proxy_brl": "Renda mensal proxy",
    "reported_coverage_pct": "Cobertura reportada",
    "estimated_base_cost_brl": "Custo base estimado",
    "technical_constraint_level": "Nível de restrição técnica",
    "backhaul_capacity_mbps": "Capacidade de backhaul",
    "powered_sites_estimate": "Locais com energia (estimativa)",
    "electricity_availability": "Disponibilidade de energia",
    "planning_budget_ceiling_brl": "Teto orçamentário de planejamento",
}
UNIT_LABELS = {
    "people": "pessoas",
    "points (0-100)": "pontos (0–100)",
    "BRL/month": "R$/mês",
    "BRL": "R$",
    "category": "",
    "sites": "locais",
}
DISPLAY_LABELS = {
    "partial": "Parcial",
    "school": "Escola",
    "health_unit": "Unidade de saúde",
    "other_public": "Outro equipamento público",
    "favorable": "Favorável",
    "conditional": "Condicional",
    "unfavorable": "Desfavorável",
    "insufficient_data": "Dados insuficientes",
    "low": "Baixa",
    "medium": "Média",
    "high": "Alta",
    "connected": "Conectada",
    "unconnected": "Desconectada",
    "unknown": "Desconhecida",
    "completed": "Completa",
    "degraded": "Degradada",
}


def display_label(value: str) -> str:
    return DISPLAY_LABELS.get(value, value)


def format_value(value: object, unit: str | None = None) -> str:
    if value is None:
        return "Não disponível"
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if isinstance(value, (int, float)):
        rendered = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        rendered = display_label(str(value))
    localized_unit = UNIT_LABELS.get(unit, unit) if unit else None
    return f"{rendered} {localized_unit}" if localized_unit else rendered


def evidence_label(evidence: dict[str, Any]) -> str:
    key = evidence.get("indicator", "")
    indicator = INDICATOR_LABELS.get(key, str(key).replace("_", " ").capitalize())
    kind = KIND_LABELS.get(evidence.get("kind"), "Tipo não informado")
    return f"{indicator} · {kind}"


def format_brl(value: int | float | None) -> str:
    if value is None:
        return "Não disponível"
    rendered = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {rendered}"
