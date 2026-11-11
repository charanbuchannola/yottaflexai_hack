"""Comprehensive validation runner verifying PK, FK, enums, dates, reconciliation, FSM, and anomalies."""

from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from voc_intel.config import settings
from voc_intel.generators.identifiers import IDGenerator
from voc_intel.models.base import (
    ActionLifecycleState,
    FeedbackLifecycleState,
    FeedbackSourceType,
    LabelingMethod,
    LanguageCode,
    PriorityTier,
    SentimentPolarity,
    ShiftDirection,
    SurveyType,
)
from voc_intel.pipeline.lifecycle import replay_entity_states
from voc_intel.pipeline.nlp import classify_sentiment, scan_model_input_leakage, scan_pii
from voc_intel.pipeline.priorities import compute_priority_score

FORBIDDEN_OPERATIONAL_KEYS = frozenset(
    {"ground_truth_id", "gold_polarity", "gold_themes", "issue_type", "expected_decision"}
)


def _check_unique_ids(
    rows: list[dict[str, Any]], pk_col: str, entity_key: str, label: str
) -> dict[str, Any]:
    seen: set[str] = set()
    dups = 0
    bad_fmt = 0
    for r in rows:
        pk = r[pk_col]
        if pk in seen:
            dups += 1
        seen.add(pk)
        if not IDGenerator.validate_id(entity_key, pk):
            bad_fmt += 1
    passed = dups == 0 and bad_fmt == 0
    return {
        "check_id": f"VAL-PK-{label.upper()}",
        "passed": passed,
        "count": len(rows),
        "duplicates": dups,
        "invalid_format": bad_fmt,
    }


def detect_anomalies_in_dataset(
    tables: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Run all 5 deterministic anomaly/edge-case detectors across operational tables."""
    findings: list[dict[str, Any]] = []

    themes = tables["themes"]
    active_theme_codes = {t["theme_code"] for t in themes if t["is_active"]}

    resp_by_id = {r["response_id"]: r for r in tables["survey_responses"]}
    rev_by_id = {r["review_id"]: r for r in tables["reviews"]}
    msg_by_id = {m["message_id"]: m for m in tables["support_messages"]}

    # 1. VAL-ANOM-001: LABEL_TEXT_CONTRADICTION
    for sl in tables["sentiment_labels"]:
        if sl["labeling_method"] != LabelingMethod.INGESTED_PROVIDER.value or sl["rationale"] is not None:
            continue
        if sl["response_id"]:
            parent = resp_by_id[sl["response_id"]]
            txt = parent["response_text"]
            lang = parent["language"]
            rating_sig = float(parent["normalized_score"])
            src_id = sl["response_id"]
        elif sl["review_id"]:
            parent = rev_by_id[sl["review_id"]]
            txt = parent["review_text"]
            lang = parent["language"]
            rating_sig = (parent["star_rating"] - 1) / 4.0
            src_id = sl["review_id"]
        else:
            parent = msg_by_id[sl["message_id"]]
            txt = parent["message_text"]
            lang = parent["language"]
            rating_sig = None
            src_id = sl["message_id"]

        pred_pol, _score, conf, _rat = classify_sentiment(txt, lang, rating_sig)
        opposite = (
            (sl["polarity"] == SentimentPolarity.POSITIVE.value and pred_pol == SentimentPolarity.NEGATIVE.value)
            or (sl["polarity"] == SentimentPolarity.NEGATIVE.value and pred_pol == SentimentPolarity.POSITIVE.value)
        )
        rating_agrees_with_text = (
            rating_sig is None
            or (pred_pol == SentimentPolarity.NEGATIVE.value and rating_sig <= 0.35)
            or (pred_pol == SentimentPolarity.POSITIVE.value and rating_sig >= 0.65)
        )
        if opposite and conf >= 0.72 and rating_agrees_with_text:
            findings.append(
                {
                    "issue_type": "LABEL_TEXT_CONTRADICTION",
                    "rule_id": "VAL-ANOM-001",
                    "target_table": "sentiment_labels",
                    "target_record_id": sl["label_id"],
                    "source_record_id": src_id,
                }
            )

    # 2. VAL-ANOM-002: DUPLICATE_RESPONSE
    resp_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in tables["survey_responses"]:
        resp_groups[(r["survey_id"], r["customer_id"], r["content_hash"])].append(r)

    for _k, grp in resp_groups.items():
        if len(grp) > 1:
            grp_sorted = sorted(grp, key=lambda x: (x["submitted_at"], x["response_id"]))
            for dup in grp_sorted[1:]:
                findings.append(
                    {
                        "issue_type": "DUPLICATE_RESPONSE",
                        "rule_id": "VAL-ANOM-002",
                        "target_table": "survey_responses",
                        "target_record_id": dup["response_id"],
                        "source_record_id": grp_sorted[0]["response_id"],
                    }
                )

    rev_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rev in tables["reviews"]:
        if rev["customer_id"] is not None:
            rev_groups[(rev["product_id"], rev["customer_id"], rev["content_hash"])].append(rev)
    for _k, grp in rev_groups.items():
        if len(grp) > 1:
            grp_sorted = sorted(grp, key=lambda x: (x["published_at"], x["review_id"]))
            for dup in grp_sorted[1:]:
                findings.append(
                    {
                        "issue_type": "DUPLICATE_RESPONSE",
                        "rule_id": "VAL-ANOM-002",
                        "target_table": "reviews",
                        "target_record_id": dup["review_id"],
                        "source_record_id": grp_sorted[0]["review_id"],
                    }
                )

    # 3. VAL-ANOM-003: CUSTOMER_IDENTITY_LEAKED
    for r in tables["survey_responses"]:
        if scan_pii(r["response_text"]):
            findings.append(
                {
                    "issue_type": "CUSTOMER_IDENTITY_LEAKED",
                    "rule_id": "VAL-ANOM-003",
                    "target_table": "survey_responses",
                    "target_record_id": r["response_id"],
                    "source_record_id": r["response_id"],
                }
            )
    for rev in tables["reviews"]:
        if scan_pii(rev["review_text"]):
            findings.append(
                {
                    "issue_type": "CUSTOMER_IDENTITY_LEAKED",
                    "rule_id": "VAL-ANOM-003",
                    "target_table": "reviews",
                    "target_record_id": rev["review_id"],
                    "source_record_id": rev["review_id"],
                }
            )
    for msg in tables["support_messages"]:
        if scan_pii(msg["message_text"]):
            findings.append(
                {
                    "issue_type": "CUSTOMER_IDENTITY_LEAKED",
                    "rule_id": "VAL-ANOM-003",
                    "target_table": "support_messages",
                    "target_record_id": msg["message_id"],
                    "source_record_id": msg["message_id"],
                }
            )

    # 4. VAL-ANOM-004: THEME_OUTSIDE_TAXONOMY
    for asn in tables["feedback_theme_assignments"]:
        if asn["theme_id"] is None or asn["raw_theme_code"] not in active_theme_codes:
            parent_rid = asn["response_id"] or asn["review_id"] or asn["message_id"]
            findings.append(
                {
                    "issue_type": "THEME_OUTSIDE_TAXONOMY",
                    "rule_id": "VAL-ANOM-004",
                    "target_table": "feedback_theme_assignments",
                    "target_record_id": asn["assignment_id"],
                    "source_record_id": parent_rid,
                }
            )

    # 5. VAL-ANOM-005: TEST_LABEL_IN_MODEL_INPUT
    for mi in tables["model_inputs"]:
        if scan_model_input_leakage(mi):
            parent_rid = mi["response_id"] or mi["review_id"] or mi["message_id"]
            findings.append(
                {
                    "issue_type": "TEST_LABEL_IN_MODEL_INPUT",
                    "rule_id": "VAL-ANOM-005",
                    "target_table": "model_inputs",
                    "target_record_id": mi["input_id"],
                    "source_record_id": parent_rid,
                }
            )

    return findings


def run_all_validations(
    tables: dict[str, list[dict[str, Any]]],
    gt_records: list[dict[str, Any]] | None = None,
    engine: Engine | None = None,
    expect_anomalies: bool = True,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Execute full relational, enum, date, reconciliation, FSM, leakage, and anomaly validation suite."""
    checks: list[dict[str, Any]] = []

    # 1. PK & ID Format Checks
    pk_specs = (
        ("customers", "customer_id", "customer"),
        ("products", "product_id", "product"),
        ("channels", "channel_id", "channel"),
        ("surveys", "survey_id", "survey"),
        ("themes", "theme_id", "theme"),
        ("survey_responses", "response_id", "survey_response"),
        ("reviews", "review_id", "review"),
        ("support_tickets", "ticket_id", "support_ticket"),
        ("support_messages", "message_id", "support_message"),
        ("sentiment_labels", "label_id", "sentiment_label"),
        ("feedback_theme_assignments", "assignment_id", "theme_assignment"),
        ("sentiment_shifts", "shift_id", "sentiment_shift"),
        ("action_items", "action_id", "action_item"),
        ("action_item_evidence", "evidence_id", "action_evidence"),
        ("model_inputs", "input_id", "model_input"),
        ("lifecycle_events", "event_id", "lifecycle_event"),
    )
    for tbl, pk_col, e_key in pk_specs:
        checks.append(_check_unique_ids(tables[tbl], pk_col, e_key, tbl))

    # 2. Foreign-Key Integrity Checks (Python + SQLite PRAGMA foreign_key_check)
    cust_ids = {r["customer_id"] for r in tables["customers"]}
    prod_ids = {r["product_id"] for r in tables["products"]}
    chan_ids = {r["channel_id"] for r in tables["channels"]}
    surv_ids = {r["survey_id"] for r in tables["surveys"]}
    theme_ids = {r["theme_id"] for r in tables["themes"]}
    resp_ids = {r["response_id"] for r in tables["survey_responses"]}
    rev_ids = {r["review_id"] for r in tables["reviews"]}
    tkt_ids = {r["ticket_id"] for r in tables["support_tickets"]}
    msg_ids = {r["message_id"] for r in tables["support_messages"]}
    shift_ids = {r["shift_id"] for r in tables["sentiment_shifts"]}
    act_ids = {r["action_id"] for r in tables["action_items"]}

    fk_orphans = 0
    for s in tables["surveys"]:
        if s["product_id"] is not None and s["product_id"] not in prod_ids:
            fk_orphans += 1
        if s["channel_id"] not in chan_ids:
            fk_orphans += 1
    for r in tables["survey_responses"]:
        if r["survey_id"] not in surv_ids or r["customer_id"] not in cust_ids or r["channel_id"] not in chan_ids:
            fk_orphans += 1
        if r["product_id"] is not None and r["product_id"] not in prod_ids:
            fk_orphans += 1
    for rev in tables["reviews"]:
        if (rev["customer_id"] is not None and rev["customer_id"] not in cust_ids) or rev["product_id"] not in prod_ids or rev["channel_id"] not in chan_ids:
            fk_orphans += 1
    for tkt in tables["support_tickets"]:
        if tkt["customer_id"] not in cust_ids or tkt["product_id"] not in prod_ids or tkt["channel_id"] not in chan_ids:
            fk_orphans += 1
    for msg in tables["support_messages"]:
        if msg["ticket_id"] not in tkt_ids or msg["customer_id"] not in cust_ids or msg["product_id"] not in prod_ids or msg["channel_id"] not in chan_ids:
            fk_orphans += 1

    for child_tbl in ("sentiment_labels", "feedback_theme_assignments", "action_item_evidence", "model_inputs"):
        for row in tables[child_tbl]:
            non_null = int(row["response_id"] is not None) + int(row["review_id"] is not None) + int(row["message_id"] is not None)
            if non_null != 1:
                fk_orphans += 1
            if row["response_id"] is not None and row["response_id"] not in resp_ids:
                fk_orphans += 1
            if row["review_id"] is not None and row["review_id"] not in rev_ids:
                fk_orphans += 1
            if row["message_id"] is not None and row["message_id"] not in msg_ids:
                fk_orphans += 1
            if child_tbl == "feedback_theme_assignments" and row["theme_id"] is not None and row["theme_id"] not in theme_ids:
                fk_orphans += 1
            if child_tbl == "action_item_evidence" and row["action_id"] not in act_ids:
                fk_orphans += 1

    for act in tables["action_items"]:
        if (act["product_id"] is not None and act["product_id"] not in prod_ids) or act["theme_id"] not in theme_ids:
            fk_orphans += 1
        if act["shift_id"] is not None and act["shift_id"] not in shift_ids:
            fk_orphans += 1

    sqlite_fk_violations = 0
    if engine is not None:
        with engine.connect() as conn:
            sqlite_fk_violations = len(conn.execute(text("PRAGMA foreign_key_check")).fetchall())

    checks.append(
        {
            "check_id": "VAL-FK-INTEGRITY",
            "passed": fk_orphans == 0 and sqlite_fk_violations == 0,
            "orphan_references": fk_orphans,
            "sqlite_pragma_violations": sqlite_fk_violations,
        }
    )

    # 3. Enum and Bound Checks
    valid_langs = {e.value for e in LanguageCode}
    valid_pols = {e.value for e in SentimentPolarity}
    valid_tiers = {e.value for e in PriorityTier}
    enum_errors = 0
    for r in tables["survey_responses"]:
        if r["language"] not in valid_langs or not (0 <= r["rating_score"] <= 10) or not (0.0 <= r["normalized_score"] <= 1.0):
            enum_errors += 1
    for rev in tables["reviews"]:
        if rev["language"] not in valid_langs or not (1 <= rev["star_rating"] <= 5):
            enum_errors += 1
    for sl in tables["sentiment_labels"]:
        if sl["polarity"] not in valid_pols or not (-1.0 <= sl["sentiment_score"] <= 1.0) or not (0.0 <= sl["confidence"] <= 1.0):
            enum_errors += 1
    for act in tables["action_items"]:
        if act["priority_tier"] not in valid_tiers or not (0.0 <= act["priority_score"] <= 100.0):
            enum_errors += 1

    checks.append(
        {
            "check_id": "VAL-ENUM-BOUNDS",
            "passed": enum_errors == 0,
            "violations": enum_errors,
        }
    )

    # 4. Date Ordering Checks
    surv_by_id = {s["survey_id"]: s for s in tables["surveys"]}
    tkt_by_id = {t["ticket_id"]: t for t in tables["support_tickets"]}
    date_errors = 0
    for s in tables["surveys"]:
        if s["effective_to"] < s["effective_from"]:
            date_errors += 1
    for r in tables["survey_responses"]:
        s = surv_by_id[r["survey_id"]]
        if not (s["effective_from"] <= r["submitted_at"] <= s["effective_to"]):
            date_errors += 1
    for tkt in tables["support_tickets"]:
        if tkt["resolved_at"] is not None and tkt["resolved_at"] < tkt["opened_at"]:
            date_errors += 1
    for msg in tables["support_messages"]:
        tkt = tkt_by_id[msg["ticket_id"]]
        if msg["sent_at"] < tkt["opened_at"]:
            date_errors += 1
    for sh in tables["sentiment_shifts"]:
        if not (sh["baseline_start"] <= sh["baseline_end"] <= sh["current_start"] <= sh["current_end"]):
            date_errors += 1
    for act in tables["action_items"]:
        if act["updated_at"] < act["created_at"]:
            date_errors += 1

    checks.append(
        {
            "check_id": "VAL-DATE-ORDER",
            "passed": date_errors == 0,
            "violations": date_errors,
        }
    )

    # 5. Arithmetic Reconciliation Checks
    recon_errors = 0
    resp_counts: dict[str, int] = defaultdict(int)
    for r in tables["survey_responses"]:
        resp_counts[r["survey_id"]] += 1
        s_type = surv_by_id[r["survey_id"]]["survey_type"]
        exp_norm = round(r["rating_score"] / 10.0, 4) if s_type == SurveyType.NPS.value else round((r["rating_score"] - 1) / 4.0, 4)
        if abs(r["normalized_score"] - exp_norm) > 1e-4:
            recon_errors += 1
    for s in tables["surveys"]:
        if s["actual_response_count"] != resp_counts[s["survey_id"]]:
            recon_errors += 1

    msg_counts: dict[str, int] = defaultdict(int)
    for m in tables["support_messages"]:
        msg_counts[m["ticket_id"]] += 1
    for tkt in tables["support_tickets"]:
        if tkt["message_count"] != msg_counts[tkt["ticket_id"]]:
            recon_errors += 1

    for sh in tables["sentiment_shifts"]:
        if abs(sh["delta_score"] - (sh["current_avg_score"] - sh["baseline_avg_score"])) > 1e-4:
            recon_errors += 1

    theme_by_id = {t["theme_id"]: t for t in tables["themes"]}
    total_record_items = max(
        1,
        len(tables["survey_responses"]) + len(tables["reviews"]) + len(tables["support_messages"]),
    )
    volume_anchor = max(30.0, total_record_items * 0.03)

    evid_by_act: dict[str, int] = defaultdict(int)
    for ev in tables["action_item_evidence"]:
        evid_by_act[ev["action_id"]] += 1
    for act in tables["action_items"]:
        if evid_by_act[act["action_id"]] != act["mention_count"]:
            recon_errors += 1
        exp_neg_share = round(act["negative_count"] / act["mention_count"], 6)
        if abs(act["negative_share"] - exp_neg_share) > 1e-4:
            recon_errors += 1
        exp_prio, exp_tier = compute_priority_score(
            mention_count=act["mention_count"],
            volume_anchor=volume_anchor,
            negative_share=act["negative_share"],
            sentiment_delta=act["sentiment_delta"],
            severity_weight=theme_by_id[act["theme_id"]]["severity_weight"],
            channel_breadth=act["channel_breadth"],
        )
        if abs(act["priority_score"] - exp_prio) > 1e-2 or act["priority_tier"] != exp_tier:
            recon_errors += 1

    checks.append(
        {
            "check_id": "VAL-RECONCILIATION",
            "passed": recon_errors == 0,
            "mismatches": recon_errors,
        }
    )

    # 6. Lifecycle FSM & Event Replay Verification
    replayed_states, fsm_violations = replay_entity_states(tables["lifecycle_events"])
    state_drift = 0
    for s in tables["surveys"]:
        if replayed_states.get(("SURVEY", s["survey_id"])) != s["lifecycle_state"]:
            state_drift += 1
    for r in tables["survey_responses"]:
        if replayed_states.get((FeedbackSourceType.SURVEY_RESPONSE.value, r["response_id"])) != r["lifecycle_state"]:
            state_drift += 1
    for rev in tables["reviews"]:
        if replayed_states.get((FeedbackSourceType.REVIEW.value, rev["review_id"])) != rev["lifecycle_state"]:
            state_drift += 1
    for tkt in tables["support_tickets"]:
        if replayed_states.get(("SUPPORT_TICKET", tkt["ticket_id"])) != tkt["lifecycle_state"]:
            state_drift += 1
    for msg in tables["support_messages"]:
        if replayed_states.get((FeedbackSourceType.SUPPORT_MESSAGE.value, msg["message_id"])) != msg["lifecycle_state"]:
            state_drift += 1
    for act in tables["action_items"]:
        if replayed_states.get(("ACTION_ITEM", act["action_id"])) != act["lifecycle_state"]:
            state_drift += 1

    checks.append(
        {
            "check_id": "VAL-FSM-REPLAY",
            "passed": len(fsm_violations) == 0 and state_drift == 0,
            "fsm_violations": len(fsm_violations),
            "projection_drift": state_drift,
            "events_replayed": len(tables["lifecycle_events"]),
        }
    )

    # 7. Zero Ground-Truth Column Leakage in Operational Tables
    schema_leak_count = 0
    for tbl_name, rows in tables.items():
        if rows:
            bad_cols = set(rows[0].keys()) & FORBIDDEN_OPERATIONAL_KEYS
            if bad_cols:
                schema_leak_count += len(bad_cols)
    checks.append(
        {
            "check_id": "VAL-ZERO-GT-COLUMN-LEAK",
            "passed": schema_leak_count == 0,
            "leaked_columns": schema_leak_count,
        }
    )

    # 8. Anomaly Detection & Ground-Truth Reconciliation
    detected_anomalies = detect_anomalies_in_dataset(tables)
    if expect_anomalies:
        gt_anoms = {
            (g["issue_type"], g["target_record_id"])
            for g in (gt_records or [])
            if g["record_category"] == "INJECTED_ANOMALY"
        }
        pred_anoms = {(a["issue_type"], a["target_record_id"]) for a in detected_anomalies}
        anom_passed = len(gt_anoms) > 0 and gt_anoms == pred_anoms
        checks.append(
            {
                "check_id": "VAL-ANOMALY-COVERAGE",
                "passed": anom_passed,
                "mode": "WITH_ANOMALIES",
                "expected_count": len(gt_anoms),
                "detected_count": len(pred_anoms),
                "false_positives": len(pred_anoms - gt_anoms),
                "false_negatives": len(gt_anoms - pred_anoms),
            }
        )
    else:
        checks.append(
            {
                "check_id": "VAL-BASELINE-PURITY",
                "passed": len(detected_anomalies) == 0,
                "mode": "BASELINE",
                "unexpected_anomalies": len(detected_anomalies),
            }
        )

    overall_passed = all(c["passed"] for c in checks)
    report = {
        "overall_passed": overall_passed,
        "mode": "WITH_ANOMALIES" if expect_anomalies else "BASELINE",
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks if c["passed"]),
        "failed_checks": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
        "detected_anomalies": detected_anomalies,
    }

    target = output_path or (settings.exports_dir / "reports" / "validation_report.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)

    return report
