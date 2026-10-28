"""Coordena a execução LangGraph, persistência e métricas por análise."""

import logging
from time import perf_counter

from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import AnalysisRequest, AnalysisResult
from conecta_conselho.orchestration.graph import run_council
from conecta_conselho.orchestration.state import CouncilState
from conecta_conselho.persistence.sqlite_store import PersistenceError, SQLiteAnalysisStore

logger = logging.getLogger(__name__)
PROMPT_VERSIONS = {
    "base": "base-v1",
    "financial": "financial-v1",
    "social": "social-v1",
    "technical": "technical-v1",
    "budget": "budget-v1",
    "bridges": "bridges-v1",
    "guardian": "guardian-v1",
}


class AnalysisService:
    """Serviço de análise e auditoria local sem dependência de serviços pagos."""

    def __init__(
        self,
        settings: LLMSettings,
        store: SQLiteAnalysisStore | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or SQLiteAnalysisStore(settings.database_url)

    async def execute(
        self,
        request: AnalysisRequest,
    ) -> tuple[CouncilState, AnalysisResult | None]:
        started_at = perf_counter()
        state, result = await run_council(
            municipality_code=request.municipality_code,
            parameters=request.parameters,
            selected_anchor_ids=request.selected_anchor_ids,
            settings=self.settings,
        )
        duration_ms = (perf_counter() - started_at) * 1000
        analysis_id = state.get("analysis_id")
        logger.info(
            "Execução da análise concluída",
            extra={
                "analysis_id": analysis_id,
                "status": state.get("status"),
                "duration_ms": round(duration_ms, 2),
            },
        )
        if result is None:
            return state, None

        try:
            self.store.save_analysis(
                request,
                result,
                model_name=(self.settings.ollama_model if result.mode == "ollama" else None),
                prompt_versions=PROMPT_VERSIONS,
            )
        except PersistenceError:
            logger.exception(
                "Falha ao persistir análise concluída",
                extra={"analysis_id": result.analysis_id},
            )
            raise
        return state, result

    async def get_analysis(self, analysis_id: str) -> AnalysisResult | None:
        return self.store.get_analysis(analysis_id)

    async def get_export(self, analysis_id: str) -> dict[str, object] | None:
        return self.store.get_export(analysis_id)
