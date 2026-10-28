import asyncio
import json
from typing import Any

from conecta_conselho.main import app


def asgi_request(path: str) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    response_body = next(
        message["body"] for message in messages if message["type"] == "http.response.body"
    )
    return messages[0]["status"], json.loads(response_body)


def test_municipality_list_includes_synthetic_and_real_localities() -> None:
    status, body = asgi_request("/api/v1/municipalities")

    assert status == 200
    assert [item["municipality_code"] for item in body[:3]] == [
        "DEMO001",
        "DEMO002",
        "DEMO003",
    ]
    assert all(item["is_synthetic"] is True for item in body[:3])
    assert [item["municipality_code"] for item in body[3:]] == [
        "1302603",
        "2611606",
        "3550308",
    ]
    assert all(item["is_synthetic"] is False for item in body[3:])


def test_municipality_detail_returns_indicators_and_institutions() -> None:
    status, body = asgi_request("/api/v1/municipalities/DEMO003")

    assert status == 200
    assert body["name"] == "Município Demonstração C"
    assert body["indicators"]
    assert body["anchor_institutions"]
    unavailable_coverage = next(
        item for item in body["indicators"] if item["indicator"] == "reported_coverage_pct"
    )
    assert unavailable_coverage["value"] is None
    assert unavailable_coverage["kind"] == "unavailable"


def test_unknown_municipality_returns_404() -> None:
    status, body = asgi_request("/api/v1/municipalities/UNKNOWN")

    assert status == 404
    assert body["detail"] == "Localidade não encontrada"


def test_real_municipality_detail_exposes_population_provenance() -> None:
    status, body = asgi_request("/api/v1/municipalities/3550308")

    assert status == 200
    assert body["name"] == "São Paulo"
    assert body["is_synthetic"] is False
    population = next(
        item for item in body["indicators"] if item["indicator"] == "resident_population"
    )
    assert population["value"] == 11_451_999
    assert population["kind"] == "observed"
    assert population["reference_year"] == 2022
    assert population["source_url"].endswith("/n6/3550308/v/93/p/2022")
    assert population["source_license"]
    assert body["anchor_institutions"] == []
