"""Exporta os schemas Pydantic dos contratos do domínio para documentação."""

import json
from pathlib import Path

from conecta_conselho.domain.models import (
    AgentOpinion,
    AnalysisError,
    AnalysisRequest,
    AnalysisResult,
    AnchorInstitution,
    BridgeCandidate,
    BridgeProposal,
    BridgeScenarioAnalysis,
    Disagreement,
    Evidence,
    GuardianDecision,
    Municipality,
    ScenarioComparison,
    ScenarioResult,
    ScoreResult,
    SimulationParameters,
)

DOMAIN_MODELS = (
    Evidence,
    AnchorInstitution,
    Municipality,
    AgentOpinion,
    SimulationParameters,
    ScenarioResult,
    ScenarioComparison,
    ScoreResult,
    AnalysisRequest,
    AnalysisError,
    BridgeCandidate,
    BridgeProposal,
    BridgeScenarioAnalysis,
    Disagreement,
    GuardianDecision,
    AnalysisResult,
)


def build_schema_catalog() -> dict[str, object]:
    definitions: dict[str, object] = {}
    model_names = [model.__name__ for model in DOMAIN_MODELS]
    for model in DOMAIN_MODELS:
        model_schema = model.model_json_schema(ref_template="#/$defs/{model}")
        definitions.update(model_schema.pop("$defs", {}))
        definitions[model.__name__] = model_schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Conecta Conselho — catálogo de schemas do domínio",
        "oneOf": [{"$ref": f"#/$defs/{name}"} for name in model_names],
        "$defs": definitions,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "docs" / "DOMAIN_SCHEMA.json"
    schema_path.write_text(
        json.dumps(build_schema_catalog(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Schema exportado para {schema_path.relative_to(project_root)}")


if __name__ == "__main__":
    main()
