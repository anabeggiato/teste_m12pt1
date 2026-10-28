"""Construção e execução local do fluxo acíclico do conselho."""

import logging
from time import perf_counter
from typing import Any

from langgraph.graph import END, START, StateGraph

from conecta_conselho.config import LLMSettings
from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.data.repository import MunicipalityRepository
from conecta_conselho.domain.models import AnalysisResult, Evidence, SimulationParameters
from conecta_conselho.llm.base import LLMClient
from conecta_conselho.orchestration.nodes import NodeDependencies, make_nodes
from conecta_conselho.orchestration.state import CouncilState

logger = logging.getLogger(__name__)


def build_council_graph(
    *,
    settings: LLMSettings | None = None,
    repository: MunicipalityRepository = municipality_repository,
    llm_client: LLMClient | None = None,
    guardian_client: LLMClient | None = None,
) -> Any:
    """Compila LangGraph sequencial; cada execução tem uma única contestação."""
    dependencies = NodeDependencies(
        settings=settings or LLMSettings(),
        repository=repository,
        llm_client=llm_client,
        guardian_client=guardian_client,
    )
    graph = StateGraph(CouncilState)
    for node_name, node_function in make_nodes(dependencies).items():

        async def timed_node(
            state: CouncilState,
            *,
            node_name: str = node_name,
            node_function: Any = node_function,
        ) -> dict[str, Any]:
            started_at = perf_counter()
            output: dict[str, Any] = {}
            try:
                output = await node_function(state)
                return output
            finally:
                logger.info(
                    "Nó do conselho executado",
                    extra={
                        "analysis_id": state.get("analysis_id") or output.get("analysis_id"),
                        "node": node_name,
                        "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    },
                )

        graph.add_node(node_name, timed_node)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "load_municipality")
    graph.add_edge("load_municipality", "financial")
    graph.add_edge("financial", "social")
    graph.add_edge("social", "technical")
    graph.add_edge("technical", "budget")
    graph.add_edge("budget", "collect_opinions")
    graph.add_edge("collect_opinions", "bridges")
    graph.add_edge("bridges", "simulate_scenarios")
    graph.add_edge("simulate_scenarios", "challenge_round")
    graph.add_edge("challenge_round", "guardian")
    graph.add_edge("guardian", "apply_guards")
    graph.add_edge("apply_guards", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_council(
    *,
    municipality_code: str,
    parameters: SimulationParameters,
    selected_anchor_ids: list[str] | None = None,
    analysis_id: str | None = None,
    evidence_catalog: list[Evidence] | None = None,
    settings: LLMSettings | None = None,
    repository: MunicipalityRepository = municipality_repository,
    llm_client: LLMClient | None = None,
    guardian_client: LLMClient | None = None,
) -> tuple[CouncilState, AnalysisResult | None]:
    """Executa o grafo com limite de passos e retorna estado auditável e resultado."""
    compiled = build_council_graph(
        settings=settings,
        repository=repository,
        llm_client=llm_client,
        guardian_client=guardian_client,
    )
    initial_state: CouncilState = {
        "municipality_code": municipality_code,
        "parameters": parameters,
        "selected_anchor_ids": selected_anchor_ids or [],
    }
    if analysis_id is not None:
        initial_state["analysis_id"] = analysis_id
    if evidence_catalog is not None:
        initial_state["evidence_catalog"] = evidence_catalog

    state = await compiled.ainvoke(initial_state, config={"recursion_limit": 32})
    logger.info(
        "Fluxo do conselho finalizado",
        extra={
            "analysis_id": state.get("analysis_id"),
            "status": state.get("status"),
            "error_count": len(state.get("errors", [])),
        },
    )
    if state.get("status") == "failed":
        return state, None

    result = AnalysisResult(
        analysis_id=state["analysis_id"],
        created_at=state["created_at"],
        municipality=state["municipality"],
        opinions=state.get("opinions", []),
        bridge_proposal=state["bridge_proposal"],
        baseline=state["baseline"],
        with_bridges=state["with_bridges"],
        comparison=state.get("comparison"),
        disagreements=state.get("disagreements", []),
        guardian=state["guardian_final"],
        evidence_catalog=state["evidence_catalog"],
        warnings=state.get("warnings", []),
        errors=state.get("errors", []),
        status=state["status"],
        mode=state["mode"],
    )
    return state, result
