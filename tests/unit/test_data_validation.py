import pytest

from conecta_conselho.data.fixtures import municipality_repository
from conecta_conselho.data.validation import DatasetValidationError, validate_municipalities
from conecta_conselho.domain.models import Municipality


def test_fixture_repository_has_globally_unique_ids() -> None:
    municipalities = [
        municipality_repository.get_municipality(code)
        for code in ("DEMO001", "DEMO002", "DEMO003")
    ]
    assert all(item is not None for item in municipalities)
    validate_municipalities(municipalities)


def test_dataset_rejects_duplicate_evidence_ids_across_municipalities() -> None:
    first = municipality_repository.get_municipality("DEMO001")
    second = municipality_repository.get_municipality("DEMO002")
    assert first is not None and second is not None

    second_data = second.model_dump(mode="json")
    second_data["indicators"][0]["evidence_id"] = first.indicators[0].evidence_id
    second_data["anchor_institutions"] = []
    duplicate = Municipality.model_validate(second_data)

    with pytest.raises(DatasetValidationError, match="evidence_id duplicado"):
        validate_municipalities([first, duplicate])


def test_dataset_rejects_duplicate_institution_ids_across_municipalities() -> None:
    first = municipality_repository.get_municipality("DEMO001")
    second = municipality_repository.get_municipality("DEMO002")
    assert first is not None and second is not None

    second_data = second.model_dump(mode="json")
    second_data["anchor_institutions"][0]["institution_id"] = (
        first.anchor_institutions[0].institution_id
    )
    duplicate = Municipality.model_validate(second_data)

    with pytest.raises(DatasetValidationError, match="institution_id duplicado"):
        validate_municipalities([first, duplicate])


def test_dataset_rejects_duplicate_municipality_codes() -> None:
    first = municipality_repository.get_municipality("DEMO001")
    assert first is not None

    with pytest.raises(DatasetValidationError, match="municipality_code duplicado"):
        validate_municipalities([first, first.model_copy(deep=True)])
