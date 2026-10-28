"""Agentes especializados com opiniões estruturadas."""

from conecta_conselho.agents.bridges import analyze_bridges
from conecta_conselho.agents.budget import analyze_budget
from conecta_conselho.agents.financial import analyze_financial
from conecta_conselho.agents.social import analyze_social
from conecta_conselho.agents.technical import analyze_technical

__all__ = [
    "analyze_bridges",
    "analyze_budget",
    "analyze_financial",
    "analyze_social",
    "analyze_technical",
]
