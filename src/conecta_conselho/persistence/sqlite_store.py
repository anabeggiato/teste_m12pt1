"""Store SQLite local com migração inicial e serialização dos contratos Pydantic."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from conecta_conselho.domain.models import AnalysisRequest, AnalysisResult

SCHEMA_VERSION = 1


class PersistenceError(RuntimeError):
    """Falha ao ler, gravar ou migrar o banco local."""


class SQLiteAnalysisStore:
    """Armazena análises completas ou degradadas em SQLite local."""

    def __init__(self, database_url: str = "sqlite:///./conecta_conselho.db") -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL deve usar o esquema sqlite:///.")
        database_path = database_url.removeprefix("sqlite:///")
        if not database_path:
            raise ValueError("DATABASE_URL precisa apontar para um arquivo SQLite.")
        if database_path == ":memory:":
            raise ValueError("DATABASE_URL deve apontar para arquivo persistente, não :memory:.")

        self._lock = RLock()
        self._path = str(Path(database_path).expanduser())
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = sqlite3.connect(self._path, timeout=5)
            connection.row_factory = sqlite3.Row
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def _migrate(self) -> None:
        try:
            with self._connection() as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version < 1:
                    connection.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS analyses (
                            analysis_id TEXT PRIMARY KEY,
                            municipality_code TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            mode TEXT NOT NULL,
                            status TEXT NOT NULL,
                            request_json TEXT NOT NULL,
                            result_json TEXT NOT NULL,
                            model_name TEXT NULL,
                            prompt_versions_json TEXT NOT NULL,
                            error_json TEXT NULL
                        );
                        PRAGMA user_version = 1;
                        """
                    )
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível preparar o banco SQLite.") from exc

    def save_analysis(
        self,
        request: AnalysisRequest,
        result: AnalysisResult,
        *,
        model_name: str | None,
        prompt_versions: dict[str, str],
    ) -> None:
        errors = [error.model_dump(mode="json") for error in result.errors]
        values = (
            result.analysis_id,
            result.municipality.municipality_code,
            result.created_at,
            result.mode,
            result.status,
            request.model_dump_json(),
            result.model_dump_json(),
            model_name,
            json.dumps(prompt_versions, ensure_ascii=False, separators=(",", ":")),
            json.dumps(errors, ensure_ascii=False, separators=(",", ":")) if errors else None,
        )
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO analyses (
                        analysis_id, municipality_code, created_at, mode, status,
                        request_json, result_json, model_name,
                        prompt_versions_json, error_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível persistir a análise.") from exc

    def get_analysis(self, analysis_id: str) -> AnalysisResult | None:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT result_json FROM analyses WHERE analysis_id = ?",
                    (analysis_id,),
                ).fetchone()
            if row is None:
                return None
            return AnalysisResult.model_validate_json(row["result_json"])
        except (sqlite3.Error, ValueError) as exc:
            raise PersistenceError("Não foi possível recuperar a análise persistida.") from exc

    def get_export(self, analysis_id: str) -> dict[str, Any] | None:
        try:
            with self._connection() as connection:
                row = connection.execute(
                    """
                    SELECT analysis_id, municipality_code, created_at, mode, status,
                           request_json, result_json, model_name,
                           prompt_versions_json, error_json
                    FROM analyses WHERE analysis_id = ?
                    """,
                    (analysis_id,),
                ).fetchone()
            if row is None:
                return None
            request = json.loads(row["request_json"])
            result = json.loads(row["result_json"])
            opinions = result.get("opinions", [])
            return {
                "analysis_id": row["analysis_id"],
                "municipality_code": row["municipality_code"],
                "created_at": row["created_at"],
                "mode": row["mode"],
                "status": row["status"],
                "model_name": row["model_name"],
                "prompt_versions": json.loads(row["prompt_versions_json"]),
                "request": request,
                "result": result,
                "sources": result.get("evidence_catalog", []),
                "hypotheses": {
                    "parameters": request.get("parameters", {}),
                    "agent_assumptions": [
                        {
                            "agent_name": opinion.get("agent_name"),
                            "assumptions": opinion.get("assumptions", []),
                            "missing_data": opinion.get("missing_data", []),
                        }
                        for opinion in opinions
                    ],
                    "scenario_calculation_notes": {
                        "baseline": result.get("baseline", {}).get(
                            "calculation_notes", []
                        ),
                        "with_bridges": result.get("with_bridges", {}).get(
                            "calculation_notes", []
                        ),
                    },
                },
                "errors": json.loads(row["error_json"]) if row["error_json"] else [],
            }
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise PersistenceError("Não foi possível exportar a análise persistida.") from exc

    def clear_all(self) -> int:
        """Remove análises para reset local explícito de dados de demonstração."""
        try:
            with self._connection() as connection:
                cursor = connection.execute("DELETE FROM analyses")
                return cursor.rowcount
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível limpar as análises locais.") from exc
