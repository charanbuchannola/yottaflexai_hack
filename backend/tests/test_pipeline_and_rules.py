"""Tests for multilingual NLP, sarcasm, mixed sentiment, priority scoring, shifts, and FSM."""

from datetime import datetime, timedelta

from voc_intel.features.lifecycle.fsm import is_valid_transition, replay_entity_states
from voc_intel.features.nlp.classifier import classify_sentiment, classify_themes, scan_pii
from voc_intel.features.priorities.engine import compute_priority_score
from voc_intel.features.shifts.detector import detect_sentiment_shifts


def test_multilingual_sarcasm_mixed_and_ambiguous_classification() -> None:
    pol_pos, score_pos, _c, _r = classify_sentiment(
        "Zero unexpected shutdowns or error 500 alerts on Core Workspace even under peak batch load.",
        "en",
        1.0,
    )
    assert pol_pos == "POSITIVE"
    assert score_pos > 0.5

    pol_es, *_ = classify_sentiment("La facturación fue exacta y sin cargos extra tras ajustar licencias.", "es")
    pol_fr, *_ = classify_sentiment("L'application a planté à répétition avec une erreur 500.", "fr")
    pol_de, *_ = classify_sentiment("Klares Design und intuitive Navigation machen das Dashboard sehr angenehm.", "de")
    assert pol_es == "POSITIVE"
    assert pol_fr == "NEGATIVE"
    assert pol_de == "POSITIVE"

    pol_sarc, score_sarc, *_ = classify_sentiment(
        "Oh fantastic, Analytics crashed right before our executive demo — truly love losing an hour of work.",
        "en",
        0.0,
    )
    assert pol_sarc == "NEGATIVE"
    assert score_sarc < -0.5

    pol_mix, _sc, _cf, _rat = classify_sentiment(
        "A knowledgeable and helpful agent resolved quickly what broke. However, severe latency caused dashboards to hit timeout errors.",
        "en",
        0.5,
    )
    assert pol_mix == "MIXED"
    themes = classify_themes(
        "A knowledgeable and helpful agent resolved quickly what broke. However, severe latency caused dashboards to hit timeout errors.",
        "en",
        max_themes=2,
    )
    theme_codes = {t[1] for t in themes}
    assert "SUPPORT_HELPFUL_RESOLUTION" in theme_codes
    assert "SLOW_PERFORMANCE_LATENCY" in theme_codes


def test_pii_scanner_clean_vs_leaked() -> None:
    assert scan_pii("Great clean design and smooth onboarding experience.") == []
    leaks = scan_pii("Reach me at user.demo@example.invalid or +1-555-014-9901 (CUST_KEY_90011).")
    assert "EMAIL_LEAK" in leaks
    assert "PHONE_LEAK" in leaks
    assert "CREDENTIAL_OR_ID_LEAK" in leaks


def test_priority_score_formula_and_tiers() -> None:
    p0_score, p0_tier = compute_priority_score(
        mention_count=120,
        volume_anchor=100.0,
        negative_share=0.9,
        sentiment_delta=-0.8,
        severity_weight=1.6,
        channel_breadth=3,
    )
    assert p0_score >= 95.0
    assert p0_tier == "P0_CRITICAL"

    p3_score, p3_tier = compute_priority_score(
        mention_count=5,
        volume_anchor=100.0,
        negative_share=0.1,
        sentiment_delta=0.1,
        severity_weight=0.85,
        channel_breadth=1,
    )
    assert p3_score < 34.0
    assert p3_tier == "P3_LOW"


def test_fsm_transitions_and_event_replay() -> None:
    assert is_valid_transition("ACTION_ITEM", "IDENTIFIED", "TRIAGED")
    assert not is_valid_transition("ACTION_ITEM", "IDENTIFIED", "CLOSED")

    t0 = datetime(2026, 10, 22, 0, 0, 0)
    valid_events = [
        {
            "entity_type": "ACTION_ITEM",
            "entity_id": "ACT-2026-000001",
            "from_state": None,
            "to_state": "IDENTIFIED",
            "event_timestamp": t0,
            "sequence_no": 1,
        },
        {
            "entity_type": "ACTION_ITEM",
            "entity_id": "ACT-2026-000001",
            "from_state": "IDENTIFIED",
            "to_state": "TRIAGED",
            "event_timestamp": t0,
            "sequence_no": 2,
        },
    ]
    states, violations = replay_entity_states(valid_events)
    assert violations == []
    assert states[("ACTION_ITEM", "ACT-2026-000001")] == "TRIAGED"

    illegal_events = valid_events + [
        {
            "entity_type": "ACTION_ITEM",
            "entity_id": "ACT-2026-000001",
            "from_state": "TRIAGED",
            "to_state": "CLOSED",
            "event_timestamp": t0,
            "sequence_no": 3,
        }
    ]
    _, bad_violations = replay_entity_states(illegal_events)
    assert len(bad_violations) == 1


def test_sentiment_shift_detector_declining_improving_stable() -> None:
    w_start = datetime(2026, 9, 1, 0, 0, 0)
    split_dt = datetime(2026, 9, 21, 0, 0, 0)
    anchor_dt = datetime(2026, 10, 1, 0, 0, 0)

    reviews = []
    sent_labels = []
    assignments = []
    seq = 1

    cohorts = (
        ("PROD-001", "THEME-000001", 0.8, -0.8),
        ("PROD-002", "THEME-000002", -0.8, 0.8),
        ("PROD-003", "THEME-000003", 0.2, 0.2),
    )
    for prod_id, theme_id, base_s, curr_s in cohorts:
        for i in range(10):
            rid = f"REV-2026-{seq:06d}"
            reviews.append({"review_id": rid, "product_id": prod_id, "published_at": w_start + timedelta(days=i), "lifecycle_state": "VERIFIED"})
            sent_labels.append({"source_type": "REVIEW", "response_id": None, "review_id": rid, "message_id": None, "sentiment_score": base_s + (0.02 if i % 2 == 0 else -0.02)})
            assignments.append({"source_type": "REVIEW", "response_id": None, "review_id": rid, "message_id": None, "theme_id": theme_id})
            seq += 1
        for i in range(10):
            rid = f"REV-2026-{seq:06d}"
            reviews.append({"review_id": rid, "product_id": prod_id, "published_at": split_dt + timedelta(hours=i + 1), "lifecycle_state": "VERIFIED"})
            sent_labels.append({"source_type": "REVIEW", "response_id": None, "review_id": rid, "message_id": None, "sentiment_score": curr_s + (0.02 if i % 2 == 0 else -0.02)})
            assignments.append({"source_type": "REVIEW", "response_id": None, "review_id": rid, "message_id": None, "theme_id": theme_id})
            seq += 1

    shifts = detect_sentiment_shifts(
        feedback_bundle={"survey_responses": [], "reviews": reviews, "support_messages": []},
        sentiment_labels=sent_labels,
        theme_assignments=assignments,
        window_start=w_start,
        split_dt=split_dt,
        anchor_dt=anchor_dt,
        min_window_samples=8,
    )
    by_prod = {s["product_id"]: s for s in shifts}
    assert by_prod["PROD-001"]["direction"] == "DECLINING"
    assert by_prod["PROD-001"]["is_significant"] is True
    assert by_prod["PROD-002"]["direction"] == "IMPROVING"
    assert by_prod["PROD-002"]["is_significant"] is True
    assert by_prod["PROD-003"]["direction"] == "STABLE"
    assert by_prod["PROD-003"]["is_significant"] is False

