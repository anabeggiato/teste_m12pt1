import asyncio

from conecta_conselho.main import app


def test_health_reports_mock_mode_and_version(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    messages: list[dict[str, object]] = []
    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(app(scope, receive, send))

    assert messages[0]["status"] == 200
    assert messages[1]["body"] == (
        b'{"status":"ok","mode":"mock","version":"0.1.0"}'
    )
