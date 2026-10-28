"""Agente Financeiro: sinais de demanda e lacunas de viabilidade econômica."""

from conecta_conselho.agents.base import run_opinion_agent
from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import (
    AgentOpinion,
    Evidence,
    Municipality,
    SimulationParameters,
)
from conecta_conselho.llm.base import LLMClient


async def analyze_financial(
    municipality: Municipality,
    evidence_catalog: list[Evidence] | None = None,
    parameters: SimulationParameters | None = None,
    llm_client: LLMClient | None = None,
    settings: LLMSettings | None = None,
) -> AgentOpinion:
    """Produz parecer financeiro sem calcular ROI ou inventar dados comerciais."""
    return await run_opinion_agent(
        role="financial",
        municipality=municipality,
        evidence_catalog=evidence_catalog,
        parameters=parameters,
        llm_client=llm_client,
        settings=settings,
    )
