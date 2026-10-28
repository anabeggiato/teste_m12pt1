import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/capture_demo_analyses.py"
MODULE_SPEC = importlib.util.spec_from_file_location("capture_demo_analyses", SCRIPT_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
capture_script = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(capture_script)


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.body


class FakeAPIClient:
    def __init__(self, **_: Any) -> None:
        self.requests: list[dict[str, Any]] = []

    def __enter__(self) -> "FakeAPIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def get(self, path: str) -> FakeResponse:
        assert path == "/health"
        return FakeResponse({"mode": "mock"})

    def post(self, path: str, *, json: dict[str, Any]) -> FakeResponse:
        assert path == "/api/v1/analyses"
        self.requests.append(json)
        case_id = len(self.requests)
        return FakeResponse(
            {
                "analysis_id": f"analysis-{case_id}",
                "mode": "mock",
                "guardian": {"decision": "REVISAO_HUMANA"},
            }
        )


def test_capture_writes_three_mock_api_responses(monkeypatch, tmp_path: Path) -> None:
    clients: list[FakeAPIClient] = []

    def fake_client(**kwargs: Any) -> FakeAPIClient:
        client = FakeAPIClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(capture_script.httpx, "Client", fake_client)

    capture_script.capture("http://localhost:8000", tmp_path)

    assert len(clients[0].requests) == 3
    assert {path.name for path in tmp_path.iterdir()} == {
        "analysis_a.json",
        "analysis_b.json",
        "analysis_c.json",
    }
    for path in tmp_path.iterdir():
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["result"]["mode"] == "mock"
        assert document["request"]["municipality_code"].startswith("DEMO")


def test_capture_refuses_non_mock_provider(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    with pytest.raises(RuntimeError, match="LLM_PROVIDER=mock"):
        capture_script.capture("http://localhost:8000", tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_capture_refuses_non_local_api_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    with pytest.raises(ValueError, match="localhost"):
        capture_script.capture("https://api.example.com", tmp_path)

    assert list(tmp_path.iterdir()) == []
