import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
import pytest
from streamlit.testing.v1 import AppTest

import conecta_conselho.dashboard.api_client as dashboard_api
from conecta_conselho.dashboard.api_client import DashboardAPI, DashboardAPIError
from conecta_conselho.dashboard.presentation import (
    display_label,
    evidence_label,
    format_brl,
    format_value,
)
from conecta_conselho.data.fixtures import municipality_repository


def test_dashboard_client_uses_api_routes_and_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "mode": "mock"})
        if request.url.path == "/api/v1/municipalities":
            return httpx.Response(200, json=[{"municipality_code": "DEMO001"}])
        if request.url.path == "/api/v1/municipalities/DEMO001":
            return httpx.Response(200, json={"municipality_code": "DEMO001"})
        if request.url.path == "/api/v1/analyses":
            return httpx.Response(200, json={"analysis_id": "analysis-1"})
        if request.url.path.endswith("/export"):
            return httpx.Response(200, content=b'{"analysis_id":"analysis-1"}')
        return httpx.Response(404, json={"detail": "not found"})

    api = DashboardAPI("http://local.test/", transport=httpx.MockTransport(handler))
    payload = {"municipality_code": "DEMO001", "parameters": {"budget_ceiling_brl": 0}}
    try:
        assert api.health()["mode"] == "mock"
        assert api.list_municipalities()[0]["municipality_code"] == "DEMO001"
        assert api.get_municipality("DEMO001")["municipality_code"] == "DEMO001"
        assert api.create_analysis(payload)["analysis_id"] == "analysis-1"
        assert json.loads(api.export_analysis("analysis-1")) == {
            "analysis_id": "analysis-1"
        }
    finally:
        api.close()

    assert json.loads(requests[3].content) == payload


def test_dashboard_client_reports_api_error_status_and_detail() -> None:
    api = DashboardAPI(
        "http://local.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, json={"detail": "Análise não encontrada"})
        ),
    )
    try:
        with pytest.raises(DashboardAPIError, match="Análise não encontrada") as error:
            api.get_municipality("missing")
    finally:
        api.close()
    assert error.value.status_code == 404


def test_dashboard_client_preserves_partial_result_from_degraded_response() -> None:
    partial_result = {"analysis_id": "analysis-degraded", "status": "degraded"}
    api = DashboardAPI(
        "http://local.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, json=partial_result)
        ),
    )
    try:
        with pytest.raises(DashboardAPIError) as error:
            api.create_analysis({})
    finally:
        api.close()
    assert error.value.status_code == 503
    assert error.value.payload == partial_result


def test_dashboard_client_reports_connection_failure() -> None:
    api = DashboardAPI("http://127.0.0.1:1", timeout=0.1)
    try:
        with pytest.raises(DashboardAPIError, match="Verifique se ela está iniciada"):
            api.health()
    finally:
        api.close()


def test_presentation_preserves_missing_values_and_provenance_labels() -> None:
    assert format_value(None, "%") == "Não disponível"
    assert format_value(12.5, "%") == "12,50 %"
    assert format_brl(None) == "Não disponível"
    assert format_brl(1234.5) == "R$ 1.234,50"
    assert evidence_label({"indicator": "coverage", "kind": "unavailable"}) == (
        "Coverage · Indisponível"
    )
    assert evidence_label({"indicator": "demand_proxy_index", "kind": "hypothetical"}) == (
        "Índice proxy de demanda · Hipotético"
    )
    assert format_value(18, "people") == "18,00 pessoas"
    assert format_value("partial", "category") == "Parcial"
    assert display_label("school") == "Escola"


def test_streamlit_dashboard_completes_mock_journey(monkeypatch) -> None:
    municipality = municipality_repository.get_municipality("DEMO001").model_dump(mode="json")
    result = {
        "analysis_id": "analysis-dashboard-test",
        "created_at": "2026-10-27T00:00:00Z",
        "municipality": municipality,
        "opinions": [
            {
                "agent_name": name,
                "position": "conditional",
                "summary": "Parecer de demonstração.",
                "supporting_evidence_ids": [],
                "risks": [],
                "assumptions": [],
                "missing_data": [],
                "confidence_level": "medium",
            }
            for name in ("Financeiro", "Social", "Técnico", "Orçamentário")
        ],
        "bridge_proposal": {"candidates": [], "notes": []},
        "baseline": {
            "estimated_total_cost_brl": None,
            "hypothetical_anchor_revenue_brl": 0,
            "hypothetical_net_balance_brl": 0,
            "within_budget": None,
            "selected_anchor_ids": [],
        },
        "with_bridges": {
            "estimated_total_cost_brl": None,
            "hypothetical_anchor_revenue_brl": None,
            "hypothetical_net_balance_brl": None,
            "within_budget": None,
            "selected_anchor_ids": [],
        },
        "comparison": {"warnings": []},
        "guardian": {"decision": "REVISAO_HUMANA", "rationale": "Revisão necessária."},
        "evidence_catalog": [],
        "warnings": [],
        "errors": [],
        "disagreements": [],
        "status": "completed",
        "mode": "mock",
    }
    captured_payloads: list[dict[str, Any]] = []

    class FakeDashboardAPI:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def health(self) -> dict[str, Any]:
            return {"status": "ok", "mode": "mock", "version": "test"}

        def list_municipalities(self) -> list[dict[str, Any]]:
            return municipality_repository.list_municipalities()

        def get_municipality(self, municipality_code: str) -> dict[str, Any]:
            return municipality_repository.get_municipality(municipality_code).model_dump(
                mode="json"
            )

        def create_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
            captured_payloads.append(payload)
            analysis_result = deepcopy(result)
            selected_municipality = municipality_repository.get_municipality(
                payload["municipality_code"]
            )
            analysis_result["municipality"] = selected_municipality.model_dump(mode="json")
            institution_id = selected_municipality.anchor_institutions[0].institution_id
            analysis_result["bridge_proposal"]["candidates"] = [
                {
                    "institution_id": institution_id,
                    "rationale": "Candidata sintética para teste de interface.",
                    "priority": "medium",
                    "assumptions": [],
                    "caveats": [],
                }
            ]
            analysis_result["with_bridges"]["selected_anchor_ids"] = payload[
                "selected_anchor_ids"
            ]
            return analysis_result

        def export_analysis(self, analysis_id: str) -> bytes:
            return json.dumps(
                {
                    "analysis_id": analysis_id,
                    "request": {},
                    "hypotheses": {},
                    "model_name": None,
                    "prompt_versions": {"base": "base-v1"},
                }
            ).encode()

        def close(self) -> None:
            pass

    monkeypatch.setattr(dashboard_api, "DashboardAPI", FakeDashboardAPI)
    app_path = Path(__file__).resolve().parents[2] / "frontend" / "app.py"
    app = AppTest.from_file(app_path, default_timeout=30).run()
    assert not app.exception
    assert len(app.selectbox[0].options) == 6
    assert any(
        item.label == "Índice proxy de demanda · Hipotético" for item in app.metric
    )
    assert any(item.value == "Parcial" for item in app.metric)
    app.selectbox[0].select("São Paulo (3550308)").run()
    assert not app.exception
    assert any("somente para os indicadores exibidos" in item.value for item in app.info)
    assert any(
        item.label == "População residente (Censo 2022) · Observado"
        for item in app.metric
    )
    app.selectbox[0].select("DEMO003").run()
    assert not app.exception
    assert any(item.value == "Não disponível" for item in app.metric)

    app.number_input[0].set_value(500_000.0)
    app.checkbox[0].check()
    app.button[0].click().run()

    assert not app.exception
    assert len(captured_payloads) == 1
    assert captured_payloads[0]["parameters"]["budget_ceiling_brl"] == 500_000
    assert captured_payloads[0]["parameters"]["estimated_base_cost_brl"] is None
    assert len(captured_payloads[0]["selected_anchor_ids"]) == 1
    assert any("Parceria não verificada" in item.value for item in app.caption)
    assert app.session_state["analysis_result"]["status"] == "completed"
    assert any(item.label == "Baixar relatório JSON" for item in app.get("download_button"))


def test_streamlit_dashboard_shows_api_offline_state(monkeypatch) -> None:
    class UnavailableDashboardAPI:
        def __init__(self, base_url: str) -> None:
            pass

        def health(self) -> dict[str, Any]:
            raise DashboardAPIError("Não foi possível conectar à API.")

    monkeypatch.setattr(dashboard_api, "DashboardAPI", UnavailableDashboardAPI)
    app_path = Path(__file__).resolve().parents[2] / "frontend" / "app.py"
    app = AppTest.from_file(app_path, default_timeout=30).run()
    assert not app.exception
    assert any("Não foi possível carregar o dashboard" in item.value for item in app.error)
