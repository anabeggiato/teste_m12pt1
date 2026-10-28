"""Agente Orçamentário: comparação preliminar com teto usando cenário determinístico."""

from conecta_conselho.agents.base import run_opinion_agent
from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import (
    AgentOpinion,
    Evidence,
    Municipality,
    SimulationParameters,
)
from conecta_conselho.domain.simulation import simulate_baseline
from conecta_conselho.llm.base import LLMClient


async def analyze_budget(
    municipality: Municipality,
    evidence_catalog: list[Evidence] | None = None,
    parameters: SimulationParameters | None = None,
    llm_client: LLMClient | None = None,
    settings: LLMSettings | None = None,
) -> AgentOpinion:
    """Produz parecer orçamentário sem estimar custos ausentes.

    A comparação de custo com teto é fornecida por ``simulate_baseline``;
    o agente não repete a regra de cálculo.
    """
    catalog = municipality.indicators if evidence_catalog is None else evidence_catalog
    baseline_context = None
    if parameters is not None:
        baseline_context = simulate_baseline(parameters).model_dump(mode="json")

    return await run_opinion_agent(
        role="budget",
        municipality=municipality,
        evidence_catalog=catalog,
        parameters=parameters,
        llm_client=llm_client,
        settings=settings,
        additional_context={"baseline_scenario": baseline_context},
    )
