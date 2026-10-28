"""Baixa e prepara população municipal do Censo 2022 via API oficial SIDRA."""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

SIDRA_BASE_URL = "https://apisidra.ibge.gov.br/values"
TABLE_CODE = "4709"
VARIABLE_CODE = "93"
REFERENCE_YEAR = "2022"
SOURCE_NAME = "IBGE/SIDRA — Censo Demográfico 2022, Tabela 4709"
SOURCE_LICENSE = (
    "Dados estatísticos públicos; reutilização com atribuição ao IBGE conforme "
    "política federal de dados abertos. Nenhuma licença CC específica foi identificada."
)
TARGET_MUNICIPALITIES = {
    "1302603": {"name": "Manaus", "state_code": "AM"},
    "2611606": {"name": "Recife", "state_code": "PE"},
    "3550308": {"name": "São Paulo", "state_code": "SP"},
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class IngestionError(ValueError):
    """Dados SIDRA ausentes, duplicados ou incompatíveis com a consulta esperada."""


def sidra_url(municipality_code: str) -> str:
    return (
        f"{SIDRA_BASE_URL}/t/{TABLE_CODE}/n6/{municipality_code}"
        f"/v/{VARIABLE_CODE}/p/{REFERENCE_YEAR}"
    )


def validate_sidra_response(
    municipality_code: str,
    payload: list[dict[str, str]],
) -> dict[str, str]:
    """Confere tabela, variável, período e geocódigo antes de aceitar um valor."""
    target = TARGET_MUNICIPALITIES.get(municipality_code)
    if target is None:
        raise IngestionError(f"Código IBGE não autorizado para esta ingestão: {municipality_code}")
    if not payload or payload[0].get("D1C") != "Município (Código)":
        raise IngestionError("Resposta SIDRA sem cabeçalho esperado.")
    records = payload[1:]
    if len(records) != 1:
        raise IngestionError(
            f"Esperado um único registro para {municipality_code}; recebidos {len(records)}."
        )
    record = records[0]
    expected = {
        "NC": "6",
        "NN": "Município",
        "D1C": municipality_code,
        "D1N": f"{target['name']} ({target['state_code']})",
        "D2C": VARIABLE_CODE,
        "D2N": "População residente",
        "D3C": REFERENCE_YEAR,
        "D3N": REFERENCE_YEAR,
        "MN": "Pessoas",
    }
    for key, expected_value in expected.items():
        if record.get(key) != expected_value:
            raise IngestionError(
                f"Resposta SIDRA incompatível em {key}: esperado {expected_value!r}, "
                f"recebido {record.get(key)!r}."
            )
    value = record.get("V", "")
    if not re.fullmatch(r"[0-9]+", value):
        raise IngestionError(f"Valor populacional ausente ou inválido para {municipality_code}.")
    if int(value) <= 0:
        raise IngestionError(f"Valor populacional deve ser positivo para {municipality_code}.")
    return record


def curate_sidra_responses(
    responses: dict[str, list[dict[str, str]]],
    *,
    collected_at: str,
) -> list[dict[str, Any]]:
    """Cria registros de domínio por junção estrita pelo código oficial IBGE."""
    if set(responses) != set(TARGET_MUNICIPALITIES):
        raise IngestionError("A ingestão precisa conter exatamente os três códigos IBGE previstos.")

    municipalities = []
    for municipality_code, target in TARGET_MUNICIPALITIES.items():
        record = validate_sidra_response(municipality_code, responses[municipality_code])
        municipalities.append(
            {
                "municipality_code": municipality_code,
                "name": target["name"],
                "state_code": target["state_code"],
                "indicators": [
                    {
                        "evidence_id": (
                            f"sidra-{TABLE_CODE}-{VARIABLE_CODE}-{REFERENCE_YEAR}-"
                            f"{municipality_code}"
                        ),
                        "indicator": "resident_population",
                        "value": int(record["V"]),
                        "unit": "people",
                        "kind": "observed",
                        "source_name": SOURCE_NAME,
                        "source_url": sidra_url(municipality_code),
                        "source_license": SOURCE_LICENSE,
                        "reference_year": int(REFERENCE_YEAR),
                        "collected_at": collected_at,
                        "is_synthetic": False,
                        "limitations": [
                            (
                                "Contagem censitária total; não mede cobertura, demanda, "
                                "custo ou receita."
                            ),
                            (
                                "Indicadores de conectividade e instituições não foram "
                                "ingeridos nesta fase."
                            ),
                        ],
                    }
                ],
                "anchor_institutions": [],
                "is_synthetic": False,
            }
        )
    return municipalities


def fetch_sidra_responses(client: httpx.Client) -> dict[str, list[dict[str, str]]]:
    responses = {}
    for municipality_code in TARGET_MUNICIPALITIES:
        response = client.get(sidra_url(municipality_code))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise IngestionError(f"Resposta não tabular para {municipality_code}.")
        responses[municipality_code] = payload
    return responses


def write_datasets(output_dir: Path, responses: dict[str, list[dict[str, str]]]) -> None:
    collected_at = datetime.now(UTC).isoformat(timespec="seconds")
    curated = curate_sidra_responses(responses, collected_at=collected_at)
    raw = {
        "source_name": SOURCE_NAME,
        "table_code": TABLE_CODE,
        "variable_code": VARIABLE_CODE,
        "reference_year": int(REFERENCE_YEAR),
        "retrieved_at": collected_at,
        "records_by_ibge_code": responses,
    }
    raw_dir = output_dir / "raw"
    curated_dir = output_dir / "curated"
    raw_dir.mkdir(parents=True, exist_ok=True)
    curated_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "ibge_sidra_censo_2022_population.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (curated_dir / "municipalities.ibge.json").write_text(
        json.dumps(curated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data",
        help="diretório de saída com subpastas raw/ e curated/",
    )
    arguments = parser.parse_args()
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        responses = fetch_sidra_responses(client)
    write_datasets(arguments.output_dir, responses)
    print(
        "Ingestão concluída: "
        f"{len(TARGET_MUNICIPALITIES)} municípios; tabela {TABLE_CODE}, "
        f"variável {VARIABLE_CODE}, referência {REFERENCE_YEAR}."
    )


if __name__ == "__main__":
    main()
