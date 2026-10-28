"""Repositório local de localidades demonstrativas."""

import json
from pathlib import Path

from conecta_conselho.data.validation import validate_municipalities
from conecta_conselho.domain.models import Municipality

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "fixtures" / "municipalities.synthetic.json"
)
CURATED_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "curated" / "municipalities.ibge.json"
)


class MunicipalityRepository:
    """Carrega as fixtures locais e permite consultas por código interno."""

    def __init__(
        self,
        fixture_path: Path = FIXTURE_PATH,
        curated_path: Path = CURATED_PATH,
    ) -> None:
        raw_records = json.loads(fixture_path.read_text(encoding="utf-8"))
        curated_records = (
            json.loads(curated_path.read_text(encoding="utf-8"))
            if curated_path.is_file()
            else []
        )
        self._municipalities = [
            Municipality.model_validate(record)
            for record in [*raw_records, *curated_records]
        ]
        validate_municipalities(self._municipalities)
        self._by_code = {item.municipality_code: item for item in self._municipalities}

    def list_municipalities(self) -> list[dict[str, str | bool]]:
        return [
            {
                "municipality_code": item.municipality_code,
                "name": item.name,
                "state_code": item.state_code,
                "is_synthetic": item.is_synthetic,
            }
            for item in self._municipalities
        ]

    def get_municipality(self, municipality_code: str) -> Municipality | None:
        return self._by_code.get(municipality_code)
