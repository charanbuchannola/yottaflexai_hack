"""Temporal sentiment shift detection engine (Rule BR-SHIFT-001)."""

from collections import defaultdict
from datetime import datetime
import math
from typing import Any

from voc_intel.core.identifiers import IDGenerator
from voc_intel.db.base import FeedbackSourceType, SenderRole, ShiftDirection


def _mean_and_var(vals: list[float]) -> tuple[float, float]:
    n = len(vals)
    if n == 0:
        return 0.0, 0.0
    mean = sum(vals) / n
    if n < 2:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in vals) / (n - 1)
    return mean, var


def detect_sentiment_shifts(
    feedback_bundle: dict[str, Any],
    sentiment_labels: list[dict[str, Any]],
    theme_assignments: list[dict[str, Any]],
    window_start: datetime,
    split_dt: datetime,
    anchor_dt: datetime,
    min_window_samples: int = 8,
) -> list[dict[str, Any]]:
    """Compute SentimentShift cohorts across (product_id, theme_id) strictly from source records."""
    sim_year = anchor_dt.year

    # Map parent record -> (product_id, timestamp, include_in_voc)
    record_meta: dict[tuple[str, str], tuple[str | None, datetime, bool]] = {}
    for r in feedback_bundle["survey_responses"]:
        record_meta[(FeedbackSourceType.SURVEY_RESPONSE.value, r["response_id"])] = (
            r["product_id"],
            r["submitted_at"],
            r["lifecycle_state"] != "QUARANTINED",
        )
    for rev in feedback_bundle["reviews"]:
        record_meta[(FeedbackSourceType.REVIEW.value, rev["review_id"])] = (
            rev["product_id"],
            rev["published_at"],
            rev["lifecycle_state"] != "QUARANTINED",
        )
    for msg in feedback_bundle["support_messages"]:
        record_meta[(FeedbackSourceType.SUPPORT_MESSAGE.value, msg["message_id"])] = (
            msg["product_id"],
            msg["sent_at"],
            msg["lifecycle_state"] != "QUARANTINED" and msg["sender_role"] == SenderRole.CUSTOMER.value,
        )

    # Map parent record -> sentiment_score
    sent_by_record: dict[tuple[str, str], float] = {}
    for sl in sentiment_labels:
        rec_id = sl["response_id"] or sl["review_id"] or sl["message_id"]
        sent_by_record[(sl["source_type"], rec_id)] = float(sl["sentiment_score"])

    # Bucket scores into baseline vs current window per (product_id, theme_id)
    cohort_scores: dict[tuple[str, str], tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))

    for asn in theme_assignments:
        if asn["theme_id"] is None:
            continue  # Skip out-of-taxonomy assignments when computing governed shifts
        rec_id = asn["response_id"] or asn["review_id"] or asn["message_id"]
        key = (asn["source_type"], rec_id)
        meta = record_meta.get(key)
        score = sent_by_record.get(key)
        if meta is None or score is None:
            continue
        prod_id, ts, include_flag = meta
        if not include_flag or prod_id is None:
            continue

        base_list, curr_list = cohort_scores[(prod_id, asn["theme_id"])]
        if ts < split_dt:
            base_list.append(score)
        else:
            curr_list.append(score)

    shifts: list[dict[str, Any]] = []
    shift_seq = 1
    for (prod_id, theme_id) in sorted(cohort_scores.keys()):
        base_vals, curr_vals = cohort_scores[(prod_id, theme_id)]
        n_base = len(base_vals)
        n_curr = len(curr_vals)
        if n_base < min_window_samples or n_curr < min_window_samples:
            continue

        base_mean, base_var = _mean_and_var(base_vals)
        curr_mean, curr_var = _mean_and_var(curr_vals)
        delta = curr_mean - base_mean
        se = math.sqrt((base_var / n_base) + (curr_var / n_curr) + 1e-6)
        z_score = delta / se

        is_sig = abs(delta) >= 0.30 and abs(z_score) >= 2.8
        if is_sig and delta < 0:
            direction = ShiftDirection.DECLINING.value
        elif is_sig and delta > 0:
            direction = ShiftDirection.IMPROVING.value
        else:
            direction = ShiftDirection.STABLE.value

        shifts.append(
            {
                "shift_id": IDGenerator.sentiment_shift_id(sim_year, shift_seq),
                "product_id": prod_id,
                "theme_id": theme_id,
                "channel_group": None,
                "baseline_start": window_start,
                "baseline_end": split_dt,
                "current_start": split_dt,
                "current_end": anchor_dt,
                "baseline_count": n_base,
                "current_count": n_curr,
                "baseline_avg_score": round(base_mean, 6),
                "current_avg_score": round(curr_mean, 6),
                "delta_score": round(delta, 6),
                "z_score": round(z_score, 4),
                "direction": direction,
                "is_significant": is_sig,
                "detected_at": anchor_dt,
            }
        )
        shift_seq += 1

    return shifts
