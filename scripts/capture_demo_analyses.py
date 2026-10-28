"""Captura respostas A/B/C reais da API em modo mock para documentação."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "docs" / "examples"
CASES: dict[str, dict[str, Any]] = {
    "A": {
        "municipality_code": "DEMO001",
        "parameters": {
            "budget_ceiling_brl": 500_000,
            "estimated_base_cost_brl": 350_000,
            "estimated_cost_per_anchor_brl": 40_000,
            "hypothetical_monthly_anchor_revenue_brl": 1_200,
            "scenario_horizon_months": 12,
        },
        "selected_anchor_ids": ["DEMO001-SCHOOL-01"],
        "note": "Um equipamento âncora; todos os números monetários são premissas hipotéticas.",
    },
    "B": {
        "municipality_code": "DEMO002",
        "parameters": {
            "budget_ceiling_brl": 500_000,
            "estimated_base_cost_brl": 450_000,
            "estimated_cost_per_anchor_brl": 20_000,
            "hypothetical_monthly_anchor_revenue_brl": 2_500,
            "scenario_horizon_months": 12,
        },
        "selected_anchor_ids": ["DEMO002-SCHOOL-01", "DEMO002-HEALTH-01"],
        "note": "Duas âncoras selecionadas; todos os números monetários são premissas hipotéticas.",
    },
    "C": {
        "municipality_code": "DEMO003",
        "parameters": {"budget_ceiling_brl": 500_000},
        "selected_anchor_ids": [],
        "note": "Custos opcionais ausentes e nenhuma âncora selecionada.",
    },
}


def capture(api_base_url: str, output_dir: Path) -> None:
    if os.environ.get("LLM_PROVIDER", "mock").lower() != "mock":
        raise RuntimeError("A captura documentada deve ser executada com LLM_PROVIDER=mock.")
    parsed_url = urlsplit(api_base_url)
    if parsed_url.scheme not in {"http", "https"} or parsed_url.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("A captura só pode enviar requests para uma API em localhost.")

    output_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=api_base_url.rstrip("/"), timeout=60.0) as client:
        health = client.get("/health")
        health.raise_for_status()
        health_body = health.json()
        if health_body.get("mode") != "mock":
            raise RuntimeError("A API não informou mode=mock; nenhum exemplo foi gravado.")

        for case_id, case in CASES.items():
            request_body = {
                key: value for key, value in case.items() if key != "note"
            }
            response = client.post("/api/v1/analyses", json=request_body)
            response.raise_for_status()
            result = response.json()
            if result.get("mode") != "mock":
                raise RuntimeError(f"A análise {case_id} não foi executada em modo mock.")
            document = {
                "case_id": case_id,
                "description": case["note"],
                "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "request": request_body,
                "result": result,
            }
            path = output_dir / f"analysis_{case_id.lower()}.json"
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Exemplo {case_id} salvo em {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("API_BASE_URL", "http://localhost:8000"),
        help="URL local da API em modo mock",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    arguments = parser.parse_args()
    capture(arguments.api_base_url, arguments.output_dir)


if __name__ == "__main__":
    main()
