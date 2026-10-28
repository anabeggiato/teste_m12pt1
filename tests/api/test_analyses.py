import asyncio
import json
from typing import Any

from conecta_conselho.main import app


def api_request(
    method: str,
    path: str,
    body: dict[str, Any] | bytes | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
    include_content_length: bool = True,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    messages: list[dict[str, Any]] = []
    encoded_body = (
        body
        if isinstance(body, bytes)
        else json.dumps(body).encode()
        if body is not None
        else b""
    )
    headers = (
        [(b"content-length", str(len(encoded_body)).encode())]
        if include_content_length
        else []
    )
    if encoded_body:
        headers.append((b"content-type", b"application/json"))
    headers.extend(
        (key.lower().encode(), value.encode())
        for key, value in (extra_headers or {}).items()
    )
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("test", 1),
        "server": ("test", 80),
    }
    received_request = False

    async def receive() -> dict[str, Any]:
        nonlocal received_request
        if received_request:
            return {"type": "http.disconnect"}
        received_request = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    response_body = next(
        message["body"] for message in messages if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in messages[0].get("headers", [])
    }
    return messages[0]["status"], json.loads(response_body), response_headers


def post_analysis(body: dict[str, Any] | bytes) -> tuple[int, dict[str, Any]]:
    status, response_body, _ = api_request("POST", "/api/v1/analyses", body)
    return status, response_body


def configure_database(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'analyses.sqlite3'}")


def test_post_analysis_runs_the_council_in_mock_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)
    request = {
        "municipality_code": "DEMO002",
        "parameters": {
            "budget_ceiling_brl": 500_000,
            "estimated_base_cost_brl": 450_000,
            "estimated_cost_per_anchor_brl": 20_000,
            "hypothetical_monthly_anchor_revenue_brl": 2_500,
        },
        "selected_anchor_ids": ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"],
    }

    status, body = post_analysis(request)

    assert status == 200
    assert body["status"] == "completed"
    assert body["mode"] == "mock"
    assert len(body["opinions"]) == 4
    assert body["with_bridges"]["estimated_total_cost_brl"] == 490_000
    assert body["guardian"]["requires_human_approval"] is True
    assert body["guardian"]["decision"] == "REVISAO_HUMANA"


def test_post_analysis_returns_404_for_unknown_municipality(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)

    status, body = post_analysis(
        {
            "municipality_code": "UNKNOWN",
            "parameters": {"budget_ceiling_brl": 100_000},
        }
    )

    assert status == 404
    assert body["detail"] == "Localidade não encontrada"


def test_post_analysis_returns_422_for_anchor_from_another_municipality(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)

    status, body = post_analysis(
        {
            "municipality_code": "DEMO002",
            "parameters": {"budget_ceiling_brl": 100_000},
            "selected_anchor_ids": ["DEMO001-SCHOOL-01"],
        }
    )

    assert status == 422
    assert body["detail"]["message"] == "Entrada da análise inválida."
    assert body["detail"]["errors"][0]["node"] == "load_municipality"


def test_post_analysis_returns_partial_degraded_result_when_ollama_is_unconfigured(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "")
    configure_database(monkeypatch, tmp_path)

    status, body = post_analysis(
        {
            "municipality_code": "DEMO002",
            "parameters": {"budget_ceiling_brl": 500_000},
        }
    )

    assert status == 503
    assert body["status"] == "degraded"
    assert body["mode"] == "ollama"
    assert body["errors"]
    assert body["guardian"]["decision"] == "REVISAO_HUMANA"


def test_analysis_can_be_retrieved_and_exported_after_new_store_instances(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'analyses.sqlite3'}")
    request = {
        "municipality_code": "DEMO002",
        "parameters": {
            "budget_ceiling_brl": 500_000,
            "estimated_base_cost_brl": 450_000,
        },
    }

    post_status, created = post_analysis(request)
    analysis_id = created["analysis_id"]
    get_status, recovered, _ = api_request("GET", f"/api/v1/analyses/{analysis_id}")
    export_status, exported, headers = api_request(
        "GET", f"/api/v1/analyses/{analysis_id}/export"
    )

    assert post_status == 200
    assert get_status == 200
    assert recovered["analysis_id"] == analysis_id
    assert recovered["status"] == "completed"
    assert export_status == 200
    assert headers["content-disposition"] == f'attachment; filename="analysis-{analysis_id}.json"'
    assert exported["request"]["municipality_code"] == "DEMO002"
    assert exported["sources"]
    assert exported["hypotheses"]["parameters"]["estimated_base_cost_brl"] == 450_000
    assert exported["model_name"] is None
    assert exported["prompt_versions"]["guardian"] == "guardian-v1"


def test_get_and_export_unknown_analysis_return_404(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)

    get_status, get_body, _ = api_request("GET", "/api/v1/analyses/missing-id")
    export_status, export_body, _ = api_request(
        "GET", "/api/v1/analyses/missing-id/export"
    )

    assert get_status == 404
    assert get_body["detail"] == "Análise não encontrada"
    assert export_status == 404
    assert export_body["detail"] == "Análise não encontrada"


def test_analysis_request_payload_over_one_mib_is_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)

    status, body, _ = api_request(
        "POST",
        "/api/v1/analyses",
        b" " * (1_048_576 + 1),
        include_content_length=False,
    )

    assert status == 413
    assert body["detail"] == "Payload excede 1 MiB."


def test_analysis_request_limits_selected_anchor_count(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    configure_database(monkeypatch, tmp_path)

    status, body = post_analysis(
        {
            "municipality_code": "DEMO002",
            "parameters": {"budget_ceiling_brl": 100_000},
            "selected_anchor_ids": [f"ANCHOR-{index}" for index in range(21)],
        }
    )

    assert status == 422
    assert body["detail"][0]["type"] == "too_long"


def test_cors_allows_only_local_frontend_origins() -> None:
    allowed_status, _, allowed_headers = api_request(
        "GET",
        "/health",
        extra_headers={"Origin": "http://localhost:8501"},
    )
    blocked_status, _, blocked_headers = api_request(
        "GET",
        "/health",
        extra_headers={"Origin": "https://example.invalid"},
    )

    assert allowed_status == blocked_status == 200
    assert allowed_headers["access-control-allow-origin"] == "http://localhost:8501"
    assert "access-control-allow-origin" not in blocked_headers
