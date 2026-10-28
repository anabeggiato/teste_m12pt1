import importlib.util
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_SNAPSHOT = PROJECT_ROOT / "data/raw/ibge_sidra_censo_2022_population.json"
CURATED_SNAPSHOT = PROJECT_ROOT / "data/curated/municipalities.ibge.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts/ingest_ibge_census.py"
MODULE_SPEC = importlib.util.spec_from_file_location("ingest_ibge_census", SCRIPT_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
ingest = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(ingest)

TARGET_MUNICIPALITIES = ingest.TARGET_MUNICIPALITIES
IngestionError = ingest.IngestionError
curate_sidra_responses = ingest.curate_sidra_responses
validate_sidra_response = ingest.validate_sidra_response
write_datasets = ingest.write_datasets


def test_checked_in_curated_values_match_sidra_raw_rows_by_ibge_code() -> None:
    raw = json.loads(RAW_SNAPSHOT.read_text(encoding="utf-8"))
    curated = json.loads(CURATED_SNAPSHOT.read_text(encoding="utf-8"))

    assert set(raw["records_by_ibge_code"]) == set(TARGET_MUNICIPALITIES)
    assert {item["municipality_code"] for item in curated} == set(TARGET_MUNICIPALITIES)
    for municipality in curated:
        code = municipality["municipality_code"]
        sidra_record = validate_sidra_response(
            code, raw["records_by_ibge_code"][code]
        )
        evidence = municipality["indicators"][0]

        assert municipality["is_synthetic"] is False
        assert municipality["name"] == TARGET_MUNICIPALITIES[code]["name"]
        assert evidence["value"] == int(sidra_record["V"])
        assert evidence["kind"] == "observed"
        assert evidence["reference_year"] == raw["reference_year"] == 2022
        assert evidence["unit"] == "people"
        assert evidence["is_synthetic"] is False
        assert evidence["source_url"].endswith(f"/n6/{code}/v/93/p/2022")
        assert evidence["collected_at"] == raw["retrieved_at"]
        assert municipality["anchor_institutions"] == []


def test_sidra_ingestion_rejects_missing_wrong_or_non_numeric_values() -> None:
    code = "3550308"
    raw = json.loads(RAW_SNAPSHOT.read_text(encoding="utf-8"))
    good = raw["records_by_ibge_code"][code]

    with pytest.raises(IngestionError, match="registro"):
        validate_sidra_response(code, good[:1])

    wrong_code = json.loads(json.dumps(good))
    wrong_code[1]["D1C"] = "9999999"
    with pytest.raises(IngestionError, match="D1C"):
        validate_sidra_response(code, wrong_code)

    missing_value = json.loads(json.dumps(good))
    missing_value[1]["V"] = ""
    with pytest.raises(IngestionError, match="ausente ou inválido"):
        validate_sidra_response(code, missing_value)


def test_ingestion_requires_exact_target_set_and_is_rerunnable(tmp_path: Path) -> None:
    raw = json.loads(RAW_SNAPSHOT.read_text(encoding="utf-8"))
    responses = raw["records_by_ibge_code"]

    with pytest.raises(IngestionError, match="exatamente"):
        curate_sidra_responses(
            {"3550308": responses["3550308"]}, collected_at="2026-10-27T00:00:00+00:00"
        )

    write_datasets(tmp_path, responses)
    first_curated = (tmp_path / "curated/municipalities.ibge.json").read_text(
        encoding="utf-8"
    )
    write_datasets(tmp_path, responses)
    second_curated = json.loads(
        (tmp_path / "curated/municipalities.ibge.json").read_text(encoding="utf-8")
    )

    assert len(json.loads(first_curated)) == 3
    assert len(second_curated) == 3
    assert (tmp_path / "raw/ibge_sidra_censo_2022_population.json").is_file()
    assert {item["municipality_code"] for item in second_curated} == set(TARGET_MUNICIPALITIES)
