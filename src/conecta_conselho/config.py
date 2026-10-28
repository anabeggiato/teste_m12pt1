"""Configuração validada da aplicação e do provedor de LLM."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: Literal["mock", "ollama"] = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    max_agent_retries: int = Field(default=1, ge=0, le=1)
    database_url: str = "sqlite:///./conecta_conselho.db"

    @field_validator("ollama_model", mode="before")
    @classmethod
    def normalize_empty_model(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value
