"""Limpa análises salvas no SQLite local após confirmação explícita."""

import argparse

from conecta_conselho.config import LLMSettings
from conecta_conselho.persistence.sqlite_store import SQLiteAnalysisStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirma a remoção de todas as análises persistidas no DATABASE_URL atual",
    )
    arguments = parser.parse_args()
    if not arguments.confirm:
        parser.error("nenhum dado removido; use --confirm para limpar a base local")

    settings = LLMSettings()
    deleted_count = SQLiteAnalysisStore(settings.database_url).clear_all()
    print(f"Análises removidas: {deleted_count}")


if __name__ == "__main__":
    main()
