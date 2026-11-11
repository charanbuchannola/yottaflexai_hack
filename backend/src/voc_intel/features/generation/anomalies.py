"""Controlled injection of the 5 required negative edge-case scenarios with zero silent corruption."""

from datetime import timedelta
import json
import random
from typing import Any

from voc_intel.core.identifiers import IDGenerator
from voc_intel.db.base import (
    FeedbackLifecycleState,
    FeedbackSourceType,
    LabelingMethod,
    SentimentPolarity,
)
from voc_intel.features.generation.feedback import compute_content_hash

ANOMALY_TYPES: tuple[str, ...] = (
    "LABEL_TEXT_CONTRADICTION",
    "DUPLICATE_RESPONSE",
    "CUSTOMER_IDENTITY_LEAKED",
    "THEME_OUTSIDE_TAXONOMY",
    "TEST_LABEL_IN_MODEL_INPUT",
)


def inject_edge_case_anomalies(
    rng: random.Random,
    surveys: list[dict[str, Any]],
    feedback_bundle: dict[str, Any],
    nlp_outputs: dict[str, list[dict[str, Any]]],
    anomalies_per_type: int,
    sim_year: int,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Inject all 5 required labelled edge cases cleanly and return (anomaly_gt_records, excluded_eval_ids)."""
    if anomalies_per_type <= 0:
        return [], set()

    survey_responses = feedback_bundle["survey_responses"]
    reviews = feedback_bundle["reviews"]
    support_messages = feedback_bundle["support_messages"]
    lifecycle_events = feedback_bundle["lifecycle_events"]

    model_inputs = nlp_outputs["model_inputs"]
    sentiment_labels = nlp_outputs["sentiment_labels"]
    theme_assignments = nlp_outputs["feedback_theme_assignments"]

    # Index operational collections by record_id for O(1) lookup
    sl_by_rec: dict[str, dict[str, Any]] = {}
    for sl in sentiment_labels:
        rid = sl["response_id"] or sl["review_id"] or sl["message_id"]
        sl_by_rec[rid] = sl

    mi_by_rec: dict[str, dict[str, Any]] = {}
    for mi in model_inputs:
        rid = mi["response_id"] or mi["review_id"] or mi["message_id"]
        mi_by_rec[rid] = mi

    asn_by_rec: dict[str, dict[str, Any]] = {}
    for asn in theme_assignments:
        rid = asn["response_id"] or asn["review_id"] or asn["message_id"]
        if rid not in asn_by_rec:
            asn_by_rec[rid] = asn

    survey_by_id = {s["survey_id"]: s for s in surveys}
    used_record_ids: set[str] = set()
    anomaly_records: list[dict[str, Any]] = []
    anomaly_seq = 1

    # 1. LABEL_TEXT_CONTRADICTION: invert SentimentLabel without rationale on clear negative reviews
    neg_reviews = [
        rev
        for rev in reviews
        if rev["star_rating"] == 1
        and sl_by_rec[rev["review_id"]]["polarity"] == SentimentPolarity.NEGATIVE.value
        and sl_by_rec[rev["review_id"]]["confidence"] >= 0.78
    ]
    for rev in neg_reviews[:anomalies_per_type]:
        rid = rev["review_id"]
        used_record_ids.add(rid)
        sl = sl_by_rec[rid]
        orig_polarity = sl["polarity"]
        sl["polarity"] = SentimentPolarity.POSITIVE.value
        sl["sentiment_score"] = 0.91
        sl["labeling_method"] = LabelingMethod.INGESTED_PROVIDER.value
        sl["rationale"] = None

        anomaly_records.append(
            {
                "ground_truth_id": f"GT-ANOM-{anomaly_seq:06d}",
                "record_category": "INJECTED_ANOMALY",
                "issue_type": "LABEL_TEXT_CONTRADICTION",
                "target_table": "sentiment_labels",
                "target_record_id": sl["label_id"],
                "source_record_id": rid,
                "expected_decision": "FLAG_CONTRADICTORY_LABEL",
                "expected_rule": "VAL-ANOM-001",
                "details_json": json.dumps(
                    {
                        "original_polarity": orig_polarity,
                        "corrupted_polarity": sl["polarity"],
                        "star_rating": rev["star_rating"],
                    },
                    sort_keys=True,
                ),
            }
        )
        anomaly_seq += 1

    # 2. DUPLICATE_RESPONSE: clone existing SurveyResponses with new PK and same customer/survey/content_hash
    resp_seq_by_survey: dict[str, int] = {
        s["survey_id"]: s["actual_response_count"] for s in surveys
    }
    dup_candidates = [r for r in survey_responses if r["response_id"] not in used_record_ids]
    next_inp_seq = len(model_inputs) + 1
    next_sent_seq = len(sentiment_labels) + 1
    next_asn_seq = len(theme_assignments) + 1
    next_evt_seq = len(lifecycle_events) + 1

    for orig in dup_candidates[:anomalies_per_type]:
        sid = orig["survey_id"]
        resp_seq_by_survey[sid] += 1
        dup_id = IDGenerator.survey_response_id(sid, resp_seq_by_survey[sid])
        dup_ts = orig["submitted_at"] + timedelta(seconds=45)

        used_record_ids.add(orig["response_id"])
        used_record_ids.add(dup_id)

        survey_responses.append(
            {
                **orig,
                "response_id": dup_id,
                "submitted_at": dup_ts,
            }
        )
        survey_by_id[sid]["actual_response_count"] += 1

        # Clone associated ModelInputFeature, SentimentLabel, ThemeAssignment & LifecycleEvents to preserve FK/1:1/FSM invariants
        orig_mi = mi_by_rec[orig["response_id"]]
        model_inputs.append(
            {
                **orig_mi,
                "input_id": IDGenerator.model_input_id(next_inp_seq),
                "response_id": dup_id,
                "event_timestamp": dup_ts,
            }
        )
        next_inp_seq += 1

        orig_sl = sl_by_rec[orig["response_id"]]
        sentiment_labels.append(
            {
                **orig_sl,
                "label_id": IDGenerator.sentiment_label_id(next_sent_seq),
                "response_id": dup_id,
                "labeled_at": dup_ts,
            }
        )
        next_sent_seq += 1

        orig_asn = asn_by_rec[orig["response_id"]]
        theme_assignments.append(
            {
                **orig_asn,
                "assignment_id": IDGenerator.theme_assignment_id(next_asn_seq),
                "response_id": dup_id,
                "assigned_at": dup_ts,
            }
        )
        next_asn_seq += 1

        for seq_no, (f_st, t_st, actor, reason, offset) in enumerate(
            (
                (None, FeedbackLifecycleState.SUBMITTED.value, "customer_portal", "Duplicate webhook retry submitted", 0),
                (FeedbackLifecycleState.SUBMITTED.value, FeedbackLifecycleState.ANALYZED.value, "nlp_pipeline", "Sentiment and theme inference completed", 15),
                (FeedbackLifecycleState.ANALYZED.value, FeedbackLifecycleState.VERIFIED.value, "quality_gate", "Ingested prior to duplicate audit", 30),
            ),
            start=1,
        ):
            lifecycle_events.append(
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, next_evt_seq),
                    "entity_type": FeedbackSourceType.SURVEY_RESPONSE.value,
                    "entity_id": dup_id,
                    "from_state": f_st,
                    "to_state": t_st,
                    "actor": actor,
                    "reason": reason,
                    "event_timestamp": dup_ts + timedelta(seconds=offset),
                    "sequence_no": seq_no,
                }
            )
            next_evt_seq += 1

        anomaly_records.append(
            {
                "ground_truth_id": f"GT-ANOM-{anomaly_seq:06d}",
                "record_category": "INJECTED_ANOMALY",
                "issue_type": "DUPLICATE_RESPONSE",
                "target_table": "survey_responses",
                "target_record_id": dup_id,
                "source_record_id": orig["response_id"],
                "expected_decision": "DEDUPLICATE_AND_QUARANTINE",
                "expected_rule": "VAL-ANOM-002",
                "details_json": json.dumps(
                    {
                        "original_response_id": orig["response_id"],
                        "customer_id": orig["customer_id"],
                        "content_hash": orig["content_hash"],
                    },
                    sort_keys=True,
                ),
            }
        )
        anomaly_seq += 1

    # 3. CUSTOMER_IDENTITY_LEAKED: inject synthetic non-routable decoy PII into reviews
    pii_candidates = [rev for rev in reviews if rev["review_id"] not in used_record_ids]
    for idx, rev in enumerate(pii_candidates[:anomalies_per_type], start=1):
        rid = rev["review_id"]
        used_record_ids.add(rid)
        leak_snippet = (
            f" Account holder: Jordan Vance, contact jordan.vance.{idx:02d}@example.invalid "
            f"or +1-555-014-{1000 + idx:04d} (CUST_KEY_{90000 + idx})."
        )
        rev["review_text"] = f"{rev['review_text']}{leak_snippet}"
        rev["content_hash"] = compute_content_hash(rev["review_text"])
        mi_by_rec[rid]["text_payload"] = rev["review_text"]

        anomaly_records.append(
            {
                "ground_truth_id": f"GT-ANOM-{anomaly_seq:06d}",
                "record_category": "INJECTED_ANOMALY",
                "issue_type": "CUSTOMER_IDENTITY_LEAKED",
                "target_table": "reviews",
                "target_record_id": rid,
                "source_record_id": rid,
                "expected_decision": "REDACT_PII_AND_QUARANTINE",
                "expected_rule": "VAL-ANOM-003",
                "details_json": json.dumps(
                    {"synthetic_decoy_pii": ["EMAIL_LEAK", "PHONE_LEAK", "CREDENTIAL_OR_ID_LEAK", "NAMED_ACCOUNT_LEAK"]},
                    sort_keys=True,
                ),
            }
        )
        anomaly_seq += 1

    # 4. THEME_OUTSIDE_TAXONOMY: assign unmapped raw_theme_code with theme_id=None
    tax_candidates = [
        asn
        for asn in theme_assignments
        if (asn["response_id"] or asn["review_id"] or asn["message_id"]) not in used_record_ids
    ]
    for idx, asn in enumerate(tax_candidates[:anomalies_per_type], start=1):
        parent_rid = asn["response_id"] or asn["review_id"] or asn["message_id"]
        used_record_ids.add(parent_rid)
        orig_code = asn["raw_theme_code"]
        asn["theme_id"] = None
        asn["raw_theme_code"] = f"UNMAPPED_LEGACY_TAG_{idx:02d}"
        asn["assignment_method"] = LabelingMethod.INGESTED_PROVIDER.value

        anomaly_records.append(
            {
                "ground_truth_id": f"GT-ANOM-{anomaly_seq:06d}",
                "record_category": "INJECTED_ANOMALY",
                "issue_type": "THEME_OUTSIDE_TAXONOMY",
                "target_table": "feedback_theme_assignments",
                "target_record_id": asn["assignment_id"],
                "source_record_id": parent_rid,
                "expected_decision": "REJECT_UNMAPPED_THEME",
                "expected_rule": "VAL-ANOM-004",
                "details_json": json.dumps(
                    {"original_theme_code": orig_code, "invalid_theme_code": asn["raw_theme_code"]},
                    sort_keys=True,
                ),
            }
        )
        anomaly_seq += 1

    # 5. TEST_LABEL_IN_MODEL_INPUT: contaminate selected ModelInputFeature rows with TEST partition & gold label leak
    msg_candidates = [
        msg
        for msg in support_messages
        if msg["message_id"] not in used_record_ids and msg["sender_role"] == "CUSTOMER"
    ]
    for msg in msg_candidates[:anomalies_per_type]:
        mid = msg["message_id"]
        used_record_ids.add(mid)
        mi = mi_by_rec[mid]
        sl = sl_by_rec[mid]

        mi["split_partition"] = "TEST"
        mi["text_payload"] = f"{mi['text_payload']} [TEST_GOLD_LABEL={sl['polarity']}]"
        extra = json.loads(mi["extra_features_json"])
        extra["leaked_gold_sentiment"] = sl["polarity"]
        extra["is_eval_holdout"] = True
        mi["extra_features_json"] = json.dumps(extra, sort_keys=True)

        anomaly_records.append(
            {
                "ground_truth_id": f"GT-ANOM-{anomaly_seq:06d}",
                "record_category": "INJECTED_ANOMALY",
                "issue_type": "TEST_LABEL_IN_MODEL_INPUT",
                "target_table": "model_inputs",
                "target_record_id": mi["input_id"],
                "source_record_id": mid,
                "expected_decision": "BLOCK_FEATURE_LEAKAGE",
                "expected_rule": "VAL-ANOM-005",
                "details_json": json.dumps(
                    {"split_partition": "TEST", "leaked_keys": ["leaked_gold_sentiment", "is_eval_holdout"]},
                    sort_keys=True,
                ),
            }
        )
        anomaly_seq += 1

    return anomaly_records, used_record_ids

