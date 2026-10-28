"""Simulações locais, hipotéticas e reproduzíveis de cenários."""

from conecta_conselho.domain.enums import ConnectivityStatus, Decision, EvidenceKind
from conecta_conselho.domain.models import (
    GuardianDecision,
    Municipality,
    ScenarioComparison,
    ScenarioResult,
    SimulationParameters,
)

SIMULATION_WARNING = (
    "Simulação hipotética; não representa proposta comercial nem orçamento de engenharia."
)


def simulate_baseline(parameters: SimulationParameters) -> ScenarioResult:
    """Calcula o cenário base sem instituições âncora."""
    cost = parameters.estimated_base_cost_brl
    within_budget = None if cost is None else cost <= parameters.budget_ceiling_brl
    return ScenarioResult(
        scenario_name="Base",
        selected_anchor_ids=[],
        estimated_total_cost_brl=cost,
        hypothetical_anchor_revenue_brl=0.0,
        hypothetical_net_balance_brl=0.0,
        within_budget=within_budget,
        calculation_notes=[
            "Custo base informado como premissa estimada/hipotética.",
            "Receita de âncoras é zero no cenário base; outras receitas não estão incluídas.",
        ],
        warnings=[SIMULATION_WARNING],
    )


def simulate_with_bridges(
    parameters: SimulationParameters,
    municipality: Municipality,
    selected_anchor_ids: list[str],
) -> ScenarioResult:
    """Calcula custos e receita hipotética apenas para IDs candidatos existentes."""
    if len(selected_anchor_ids) != len(set(selected_anchor_ids)):
        raise ValueError("selected_anchor_ids contém IDs duplicados")

    known_anchor_ids = {item.institution_id for item in municipality.anchor_institutions}
    unknown_anchor_ids = set(selected_anchor_ids) - known_anchor_ids
    if unknown_anchor_ids:
        raise ValueError(f"instituições inexistentes: {sorted(unknown_anchor_ids)}")

    baseline = simulate_baseline(parameters)
    if not selected_anchor_ids:
        return baseline

    anchor_count = len(selected_anchor_ids)
    extra_cost = (
        anchor_count * parameters.estimated_cost_per_anchor_brl
        if parameters.estimated_cost_per_anchor_brl is not None
        else None
    )
    total_cost = (
        baseline.estimated_total_cost_brl + extra_cost
        if baseline.estimated_total_cost_brl is not None and extra_cost is not None
        else None
    )
    anchor_revenue = (
        anchor_count
        * parameters.hypothetical_monthly_anchor_revenue_brl
        * parameters.scenario_horizon_months
        if parameters.hypothetical_monthly_anchor_revenue_brl is not None
        else None
    )
    net_balance = (
        anchor_revenue - extra_cost
        if anchor_revenue is not None and extra_cost is not None
        else None
    )
    within_budget = (
        None if total_cost is None else total_cost <= parameters.budget_ceiling_brl
    )
    warnings = [SIMULATION_WARNING]
    if extra_cost is None:
        warnings.append("Custo por instituição não informado; custo total com pontes indisponível.")
    if anchor_revenue is None:
        warnings.append("Receita mensal hipotética por instituição não informada.")
    only_synthetic_inputs = municipality.is_synthetic or (
        bool(municipality.indicators)
        and all(evidence.is_synthetic for evidence in municipality.indicators)
    )
    if only_synthetic_inputs:
        warnings.append(
            "Localidade e evidências são sintéticas; resultado é apenas demonstrativo."
        )

    return ScenarioResult(
        scenario_name="Com Pontes",
        selected_anchor_ids=selected_anchor_ids,
        estimated_total_cost_brl=total_cost,
        hypothetical_anchor_revenue_brl=anchor_revenue,
        hypothetical_net_balance_brl=net_balance,
        within_budget=within_budget,
        calculation_notes=[
            f"Custo adicional = {anchor_count} instituição(ões) × custo estimado por instituição.",
            "Receita hipotética considera instituições selecionadas e horizonte informado.",
            "Saldo não é ROI, lucro, NPV, viabilidade ou receita contratada.",
        ],
        warnings=warnings,
    )


def compare_scenarios(
    baseline: ScenarioResult,
    with_bridges: ScenarioResult,
) -> ScenarioComparison:
    """Compara os valores conhecidos sem substituir ausências por zero."""
    incremental_cost = (
        with_bridges.estimated_total_cost_brl - baseline.estimated_total_cost_brl
        if baseline.estimated_total_cost_brl is not None
        and with_bridges.estimated_total_cost_brl is not None
        else None
    )
    incremental_revenue = (
        with_bridges.hypothetical_anchor_revenue_brl
        - baseline.hypothetical_anchor_revenue_brl
        if baseline.hypothetical_anchor_revenue_brl is not None
        and with_bridges.hypothetical_anchor_revenue_brl is not None
        else None
    )
    warnings = list(dict.fromkeys([*baseline.warnings, *with_bridges.warnings]))
    return ScenarioComparison(
        baseline_cost_brl=baseline.estimated_total_cost_brl,
        with_bridges_cost_brl=with_bridges.estimated_total_cost_brl,
        incremental_cost_brl=incremental_cost,
        incremental_hypothetical_revenue_brl=incremental_revenue,
        hypothetical_net_balance_brl=with_bridges.hypothetical_net_balance_brl,
        within_budget=with_bridges.within_budget,
        warnings=warnings,
    )


def apply_decision_guards(
    draft: GuardianDecision,
    municipality: Municipality,
    scenario: ScenarioResult,
    *,
    material_technical_financial_conflict: bool = False,
) -> GuardianDecision:
    """Aplica hard gates antes de aceitar uma decisão preliminar."""
    final_decision = draft.decision
    reasons: list[str] = []
    only_synthetic_inputs = municipality.is_synthetic or (
        bool(municipality.indicators)
        and all(evidence.is_synthetic for evidence in municipality.indicators)
    )
    selected_synthetic_anchor = any(
        institution.is_synthetic
        and institution.institution_id in scenario.selected_anchor_ids
        for institution in municipality.anchor_institutions
    )

    if material_technical_financial_conflict:
        final_decision = Decision.HUMAN_REVIEW
        reasons.append(
            "Divergência material entre as perspectivas técnica e financeira requer revisão humana."
        )

    has_connectivity_evidence = any(
        evidence.indicator == "reported_coverage_pct"
        and evidence.value is not None
        and evidence.kind in {EvidenceKind.OBSERVED, EvidenceKind.ESTIMATED}
        for evidence in municipality.indicators
    ) or any(
        institution.connectivity_status != ConnectivityStatus.UNKNOWN
        for institution in municipality.anchor_institutions
    )
    if not has_connectivity_evidence:
        final_decision = Decision.HUMAN_REVIEW
        reasons.append("Não há evidência crítica disponível sobre conectividade.")

    if scenario.estimated_total_cost_brl is None or scenario.within_budget is None:
        final_decision = Decision.HUMAN_REVIEW
        reasons.append("Custo ou comparação com o teto orçamentário está indisponível.")
    elif scenario.within_budget is False and final_decision in {
        Decision.INVEST,
        Decision.PILOT,
    }:
        final_decision = Decision.WAIT
        reasons.append(
            "O cenário ultrapassa o teto informado e não há escopo reduzido com custo validado."
        )

    if only_synthetic_inputs and draft.decision in {Decision.INVEST, Decision.PILOT}:
        final_decision = Decision.HUMAN_REVIEW
        reasons.append("Dados sintéticos só permitem demonstração, não recomendação operacional.")
    elif selected_synthetic_anchor and draft.decision == Decision.INVEST:
        final_decision = Decision.HUMAN_REVIEW
        reasons.append(
            "A instituição selecionada é sintética e não pode embasar investimento real."
        )

    changed = final_decision != draft.decision
    rationale = draft.rationale
    if reasons:
        rationale = f"{rationale} Salvaguardas aplicadas: {'; '.join(reasons)}"
    return GuardianDecision.model_validate(
        {
            **draft.model_dump(mode="python"),
            "decision": final_decision,
            "rationale": rationale,
            "original_decision": draft.decision if changed else None,
            "final_decision": final_decision if changed else None,
            "guard_reasons": reasons,
        }
    )
