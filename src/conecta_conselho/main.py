"""Aplicação HTTP mínima do Conecta Conselho."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from conecta_conselho import __version__
from conecta_conselho.api.routes_analyses import router as analyses_router
from conecta_conselho.api.routes_municipalities import router as municipalities_router

app = FastAPI(title="Conecta Conselho", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(municipalities_router)
app.include_router(analyses_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Informa disponibilidade da API e o modo de provedor configurado."""
    return {
        "status": "ok",
        "mode": os.getenv("LLM_PROVIDER", "mock"),
        "version": __version__,
    }
