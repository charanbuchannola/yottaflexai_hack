"""Repository for bulk dataset persistence and full-snapshot loading."""

from typing import Any

from sqlalchemy.engine import Engine

from voc_intel.features.export.relational import load_tables_from_db, persist_tables_to_db


class DatasetRepository:
    """Encapsulates engine-level bulk table persistence and full snapshot loading."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save_all_tables(self, tables: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
        return persist_tables_to_db(self.engine, tables)

    def load_all_tables(self) -> dict[str, list[dict[str, Any]]]:
        return load_tables_from_db(self.engine)

