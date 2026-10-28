"""Execução, recuperação e exportação de análises persistidas."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from conecta_conselho.config import LLMSettings
from conecta_conselho.domain.models import AnalysisRequest, AnalysisResult
from conecta_conselho.persistence.sqlite_store import PersistenceError
from conecta_conselho.services.analysis_service import AnalysisService

MAX_REQUEST_BYTES = 1_048_576


class LimitedBodyRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = bytearray()
            async for chunk in self.stream():
                body.extend(chunk)
                if len(body) > MAX_REQUEST_BYTES:
                    raise HTTPException(status_code=413, detail="Payload excede 1 MiB.")
            self._body = bytes(body)
        return self._body


class LimitedRequestRoute(APIRoute):
    """Rejeita corpos grandes antes da validação Pydantic da rota."""

    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def limited_handler(request: Request):
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > MAX_REQUEST_BYTES:
                        raise HTTPException(status_code=413, detail="Payload excede 1 MiB.")
                except ValueError as exc:
                    raise HTTPException(
                        status_code=400, detail="Content-Length inválido."
                    ) from exc
            limited_request = LimitedBodyRequest(request.scope, request.receive)
            await limited_request.body()
            return await original_handler(limited_request)

        return limited_handler


router = APIRouter(
    prefix="/api/v1/analyses",
    tags=["analyses"],
    route_class=LimitedRequestRoute,
)


async def get_analysis_service() -> AnalysisService:
    return AnalysisService(LLMSettings())


@router.post(
    "",
    response_model=AnalysisResult,
    responses={
        413: {"description": "Payload excede o limite de 1 MiB."},
        502: {
            "model": AnalysisResult,
            "description": "Saída do provedor inválida; análise degradada.",
        },
        503: {
            "model": AnalysisResult,
            "description": "LLM indisponível; análise degradada.",
        }
    },
)
async def create_analysis(
    request: AnalysisRequest,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResult | JSONResponse:
    try:
        state, result = await service.execute(request)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail="Falha ao persistir análise.") from exc
    if result is not None:
        if result.status == "degraded":
            provider_error_types = {"LLMClientError", "LLMConfigurationError", "TimeoutError"}
            has_provider_error = any(
                error.error_type in provider_error_types for error in result.errors
            )
            return JSONResponse(
                status_code=503 if has_provider_error else 502,
                content=result.model_dump(mode="json"),
            )
        return result

    errors = state.get("errors", [])
    if any(
        error.node == "load_municipality" and error.error_type == "LookupError"
        for error in errors
    ):
        raise HTTPException(status_code=404, detail="Localidade não encontrada")
    raise HTTPException(
        status_code=422,
        detail={
            "message": "Entrada da análise inválida.",
            "errors": [error.model_dump(mode="json") for error in errors],
        },
    )


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(
    analysis_id: str,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisResult:
    try:
        result = await service.get_analysis(analysis_id)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail="Falha ao recuperar análise.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return result


@router.get("/{analysis_id}/export", response_model=None)
async def export_analysis(
    analysis_id: str,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> JSONResponse:
    try:
        export_document = await service.get_export(analysis_id)
    except PersistenceError as exc:
        raise HTTPException(status_code=500, detail="Falha ao exportar análise.") from exc
    if export_document is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    safe_id = "".join(
        character for character in analysis_id if character.isalnum() or character in "-_"
    )
    return JSONResponse(
        content=export_document,
        headers={"Content-Disposition": f'attachment; filename="analysis-{safe_id}.json"'},
    )
