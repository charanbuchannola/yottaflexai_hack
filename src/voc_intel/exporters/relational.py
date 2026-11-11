"""Canonical database persistence and deterministic CSV / JSON / SQL exporters."""

import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import insert
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable

from voc_intel.config import settings
from voc_intel.models import (
    ActionItem,
    ActionItemEvidence,
    Channel,
    Customer,
    FeedbackThemeAssignment,
    LifecycleEvent,
    ModelInputFeature,
    Product,
    Review,
    SentimentLabel,
    SentimentShift,
    SupportMessage,
    SupportTicket,
    Survey,
    SurveyResponse,
    Theme,
)
from voc_intel.models.database import get_session, reset_database

# Strict dependency-ordered table manifest: (table_name, ORM_class, pk_col)
TABLE_REGISTRY: tuple[tuple[str, type[Any], str], ...] = (
    ("channels", Channel, "channel_id"),
    ("products", Product, "product_id"),
    ("themes", Theme, "theme_id"),
    ("customers", Customer, "customer_id"),
    ("surveys", Survey, "survey_id"),
    ("survey_responses", SurveyResponse, "response_id"),
    ("reviews", Review, "review_id"),
    ("support_tickets", SupportTicket, "ticket_id"),
    ("support_messages", SupportMessage, "message_id"),
    ("model_inputs", ModelInputFeature, "input_id"),
    ("sentiment_labels", SentimentLabel, "label_id"),
    ("feedback_theme_assignments", FeedbackThemeAssignment, "assignment_id"),
    ("sentiment_shifts", SentimentShift, "shift_id"),
    ("action_items", ActionItem, "action_id"),
    ("action_item_evidence", ActionItemEvidence, "evidence_id"),
    ("lifecycle_events", LifecycleEvent, "event_id"),
)


def _format_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%dT%H:%M:%SZ")
    return val


def _sql_literal(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return repr(val)
    if isinstance(val, datetime):
        return "'" + val.strftime("%Y-%m-%d %H:%M:%S") + "'"
    s = str(val).replace("'", "''")
    return f"'{s}'"


def persist_tables_to_db(
    engine: Engine,
    tables: dict[str, list[dict[str, Any]]],
    batch_size: int = 5000,
) -> dict[str, int]:
    """Reset schema and bulk-insert all operational tables in dependency order."""
    reset_database(engine)
    counts: dict[str, int] = {}
    with get_session(engine) as session:
        for tbl_name, orm_cls, _pk in TABLE_REGISTRY:
            rows = tables.get(tbl_name, [])
            counts[tbl_name] = len(rows)
            for start in range(0, len(rows), batch_size):
                chunk = rows[start : start + batch_size]
                if chunk:
                    session.execute(insert(orm_cls), chunk)
    return counts


def export_canonical_artifacts(
    engine: Engine,
    tables: dict[str, list[dict[str, Any]]],
    exports_dir: Path | None = None,
) -> dict[str, Any]:
    """Export deterministic CSV, JSON, schema.sql, and seed.sql artifacts."""
    out_dir = exports_dir or settings.exports_dir
    csv_dir = out_dir / "csv"
    json_dir = out_dir / "json"
    sql_dir = out_dir / "sql"
    for d in (csv_dir, json_dir, sql_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Schema DDL SQL
    schema_path = sql_dir / "schema.sql"
    ddl_parts: list[str] = [
        "-- YottaFlex Voice of Customer Intelligence Platform DDL",
        "PRAGMA foreign_keys = ON;",
        "",
    ]
    for _tbl_name, orm_cls, _pk in TABLE_REGISTRY:
        ddl_stmt = str(CreateTable(orm_cls.__table__).compile(engine)).strip()
        ddl_parts.append(f"{ddl_stmt};")
        ddl_parts.append("")
    schema_path.write_text("\n".join(ddl_parts), encoding="utf-8")

    # 2. CSV, JSON, and batched multi-row SQL seed
    seed_path = sql_dir / "seed.sql"
    exported_files: list[Path] = [schema_path, seed_path]
    row_counts: dict[str, int] = {}

    with open(seed_path, mode="w", encoding="utf-8", newline="\n") as sql_f:
        sql_f.write("-- Deterministic Seed Data\nPRAGMA foreign_keys = ON;\nBEGIN TRANSACTION;\n\n")

        for tbl_name, orm_cls, pk_col in TABLE_REGISTRY:
            cols = [c.name for c in orm_cls.__table__.columns]
            rows = sorted(tables.get(tbl_name, []), key=lambda r: r[pk_col])
            row_counts[tbl_name] = len(rows)

            # CSV
            csv_path = csv_dir / f"{tbl_name}.csv"
            with open(csv_path, mode="w", encoding="utf-8", newline="") as cf:
                writer = csv.DictWriter(cf, fieldnames=cols)
                writer.writeheader()
                for row in rows:
                    writer.writerow({c: _format_value(row.get(c)) for c in cols})
            exported_files.append(csv_path)

            # JSON
            json_path = json_dir / f"{tbl_name}.json"
            serializable = [{c: _format_value(row.get(c)) for c in cols} for row in rows]
            with open(json_path, mode="w", encoding="utf-8", newline="\n") as jf:
                json.dump(serializable, jf, indent=2, ensure_ascii=False, sort_keys=True)
            exported_files.append(json_path)

            # SQL multi-row inserts (250 rows per statement for fast SQLite execution)
            if rows:
                col_list = ", ".join(cols)
                for start in range(0, len(rows), 250):
                    batch = rows[start : start + 250]
                    tuples_sql = ",\n  ".join(
                        "(" + ", ".join(_sql_literal(r.get(c)) for c in cols) + ")"
                        for r in batch
                    )
                    sql_f.write(f"INSERT INTO {tbl_name} ({col_list}) VALUES\n  {tuples_sql};\n")
                sql_f.write("\n")

        sql_f.write("COMMIT;\n")

    return {
        "row_counts": row_counts,
        "exported_files": exported_files,
        "schema_path": schema_path,
        "seed_path": seed_path,
    }

