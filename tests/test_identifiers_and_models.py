"""Tests for deterministic identifier conventions and relational ORM/SQLite constraints."""

from datetime import datetime
import sqlite3

import pytest
from sqlalchemy.exc import IntegrityError

from voc_intel.generators.identifiers import IDGenerator
from voc_intel.models import Channel, Customer, Product, SentimentLabel, Survey, SurveyResponse
from voc_intel.models.database import build_engine, get_session, init_database


def test_id_conventions_match_required_formats() -> None:
    sur = IDGenerator.survey_id(2026, 1)
    resp = IDGenerator.survey_response_id(sur, 1)
    rev = IDGenerator.review_id(2026, 1)
    tkt = IDGenerator.ticket_id(2026, 1)
    msg = IDGenerator.support_message_id(tkt, 1)
    thm = IDGenerator.theme_id(1)

    assert sur == "SUR-2026-000001"
    assert resp == "RESP-SUR-2026-000001-001"
    assert rev == "REV-2026-000001"
    assert msg == "MSG-TKT-2026-000001-001"
    assert thm == "THEME-000001"

    assert IDGenerator.validate_id("survey", sur)
    assert IDGenerator.validate_id("survey_response", resp)
    assert IDGenerator.validate_id("review", rev)
    assert IDGenerator.validate_id("support_message", msg)
    assert IDGenerator.validate_id("theme", thm)
    assert not IDGenerator.validate_id("survey", "SUR-26-1")


def test_sqlite_foreign_key_and_one_to_one_sentiment_constraints(tmp_path) -> None:
    db_file = tmp_path / "fk_test.db"
    engine = build_engine(f"sqlite:///{db_file.as_posix()}")
    init_database(engine)
    now = datetime(2026, 10, 22, 0, 0, 0)

    # Reject orphan Survey referencing missing Channel
    with pytest.raises(IntegrityError):
        with get_session(engine) as session:
            session.add(
                Survey(
                    survey_id="SUR-2026-000001",
                    product_id=None,
                    channel_id="CHN-999",
                    survey_type="NPS",
                    title="Invalid Survey",
                    question_prompt="Prompt",
                    lifecycle_state="ACTIVE",
                    target_response_count=10,
                    actual_response_count=0,
                    effective_from=now,
                    effective_to=now,
                )
            )

    # Valid insert + 1:1 SentimentLabel uniqueness enforcement
    with get_session(engine) as session:
        session.add(
            Channel(
                channel_id="CHN-001",
                channel_code="IN_APP_SURVEY",
                channel_group="SURVEY",
                is_public=False,
                requires_moderation=False,
                default_sla_hours=24,
                is_active=True,
                effective_from=now,
                effective_to=None,
            )
        )
        session.add(
            Customer(
                customer_id="CUST-000001",
                pseudonym_handle="acct_000001_1001",
                account_tier="PRO",
                segment="SMB",
                region="NA",
                preferred_language="en",
                lifecycle_state="ACTIVE",
                effective_from=now,
                effective_to=None,
                created_at=now,
            )
        )
        session.add(
            Product(
                product_id="PROD-001",
                sku="YF-CORE-40",
                product_name="Core Workspace",
                category="CORE_PLATFORM",
                release_version="4.3.0",
                lifecycle_state="GA",
                support_sla_hours=8,
                effective_from=now,
                effective_to=None,
            )
        )
        session.flush()
        session.add(
            Survey(
                survey_id="SUR-2026-000001",
                product_id="PROD-001",
                channel_id="CHN-001",
                survey_type="NPS",
                title="NPS Q4",
                question_prompt="Recommend?",
                lifecycle_state="ACTIVE",
                target_response_count=10,
                actual_response_count=1,
                effective_from=now,
                effective_to=now,
            )
        )
        session.flush()
        session.add(
            SurveyResponse(
                response_id="RESP-SUR-2026-000001-001",
                survey_id="SUR-2026-000001",
                customer_id="CUST-000001",
                product_id="PROD-001",
                channel_id="CHN-001",
                rating_score=9,
                normalized_score=0.9,
                response_text="Fast and reliable workflow",
                language="en",
                submitted_at=now,
                lifecycle_state="VERIFIED",
                content_hash="abc123",
            )
        )
        session.flush()
        session.add(
            SentimentLabel(
                label_id="SENT-000001",
                source_type="SURVEY_RESPONSE",
                response_id="RESP-SUR-2026-000001-001",
                review_id=None,
                message_id=None,
                polarity="POSITIVE",
                sentiment_score=0.85,
                confidence=0.92,
                labeling_method="AUTOMATED_NLP",
                rationale="Positive terms",
                labeled_at=now,
                lifecycle_state="VERIFIED",
            )
        )

    # Duplicate SentimentLabel on same response_id must violate UNIQUE 1:1 constraint
    with pytest.raises(IntegrityError):
        with get_session(engine) as session:
            session.add(
                SentimentLabel(
                    label_id="SENT-000002",
                    source_type="SURVEY_RESPONSE",
                    response_id="RESP-SUR-2026-000001-001",
                    review_id=None,
                    message_id=None,
                    polarity="NEGATIVE",
                    sentiment_score=-0.5,
                    confidence=0.8,
                    labeling_method="AUTOMATED_NLP",
                    rationale="Dup",
                    labeled_at=now,
                    lifecycle_state="VERIFIED",
                )
            )
    engine.dispose()


def test_exported_sql_ddl_and_seed_replay_into_fresh_sqlite(starter_pipeline, tmp_path) -> None:
    root, result = starter_pipeline
    schema_sql = (root / "exports" / "sql" / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (root / "exports" / "sql" / "seed.sql").read_text(encoding="utf-8")

    replay_db = tmp_path / "replay.db"
    conn = sqlite3.connect(replay_db)
    try:
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        fk_issues = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert fk_issues == []
        resp_count = conn.execute("SELECT COUNT(*) FROM survey_responses").fetchone()[0]
        assert resp_count == result.row_counts["survey_responses"]
    finally:
        conn.close()
