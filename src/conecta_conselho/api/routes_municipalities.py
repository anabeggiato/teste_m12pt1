"""Endpoints de consulta às localidades de demonstração."""

from fastapi import APIRouter, HTTPException

from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.domain.models import Municipality

router = APIRouter(prefix="/api/v1/municipalities", tags=["municipalities"])


@router.get("")
async def list_municipalities() -> list[dict[str, str | bool]]:
    return municipality_repository.list_municipalities()


@router.get("/{municipality_code}", response_model=Municipality)
async def get_municipality(municipality_code: str) -> Municipality:
    municipality = municipality_repository.get_municipality(municipality_code)
    if municipality is None:
        raise HTTPException(status_code=404, detail="Localidade não encontrada")
    return municipality
