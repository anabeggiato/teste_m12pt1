"""Validação de unicidade e integridade referencial das localidades."""

from conecta_conselho.domain.models import Municipality


class DatasetValidationError(ValueError):
    """Indica inconsistência entre registros do conjunto de localidades."""


def validate_municipalities(municipalities: list[Municipality]) -> None:
    municipality_codes = [item.municipality_code for item in municipalities]
    if len(municipality_codes) != len(set(municipality_codes)):
        raise DatasetValidationError("municipality_code duplicado no conjunto de dados")

    evidence_ids: set[str] = set()
    institution_ids: set[str] = set()
    for municipality in municipalities:
        for evidence in municipality.indicators:
            if evidence.evidence_id in evidence_ids:
                raise DatasetValidationError(
                    f"evidence_id duplicado no conjunto de dados: {evidence.evidence_id}"
                )
            evidence_ids.add(evidence.evidence_id)
        for institution in municipality.anchor_institutions:
            if institution.institution_id in institution_ids:
                raise DatasetValidationError(
                    "institution_id duplicado no conjunto de dados: "
                    f"{institution.institution_id}"
                )
            institution_ids.add(institution.institution_id)
