import sqlite3

import pytest

from conecta_conselho.persistence.sqlite_store import SQLiteAnalysisStore


def test_sqlite_store_applies_idempotent_initial_migration(tmp_path) -> None:
    database_path = tmp_path / "analysis.sqlite3"
    database_url = f"sqlite:///{database_path}"

    SQLiteAnalysisStore(database_url)
    SQLiteAnalysisStore(database_url)

    with sqlite3.connect(database_path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(analyses)").fetchall()
        }

    assert version == 1
    assert columns == {
        "analysis_id",
        "municipality_code",
        "created_at",
        "mode",
        "status",
        "request_json",
        "result_json",
        "model_name",
        "prompt_versions_json",
        "error_json",
    }


def test_store_clears_local_analysis_rows(tmp_path) -> None:
    database_path = tmp_path / "analysis.sqlite3"
    database_url = f"sqlite:///{database_path}"
    store = SQLiteAnalysisStore(database_url)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO analyses (
                analysis_id, municipality_code, created_at, mode, status,
                request_json, result_json, model_name, prompt_versions_json, error_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "test-id",
                "DEMO001",
                "2026-01-01T00:00:00Z",
                "mock",
                "completed",
                "{}",
                "{}",
                None,
                "{}",
                None,
            ),
        )

    assert store.clear_all() == 1

    with sqlite3.connect(database_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    assert row_count == 0
    assert store.clear_all() == 0


def test_store_rejects_non_sqlite_or_ephemeral_database_urls() -> None:
    with pytest.raises(ValueError, match="sqlite"):
        SQLiteAnalysisStore("postgres://localhost/db")
    with pytest.raises(ValueError, match="arquivo persistente"):
        SQLiteAnalysisStore("sqlite:///:memory:")
