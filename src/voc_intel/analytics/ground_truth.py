"""Segregated Ground Truth builder and exporter (zero leakage into operational features)."""

import csv
from datetime import datetime
import json
from pathlib import Path
import random
from typing import Any

from voc_intel.config import settings
from voc_intel.generators.feedback import PLANTED_SHIFT_COHORTS
from voc_intel.models.base import FeedbackSourceType


def build_ground_truth_records(
    rng: random.Random,
    gold_annotations: list[dict[str, Any]],
    anomaly_records: list[dict[str, Any]],
    excluded_eval_ids: set[str],
    eval_sample_size: int,
    available_product_ids: set[str],
    anchor_dt: datetime,
) -> list[dict[str, Any]]:
    """Construct unified segregated ground-truth dataset (Evaluation Labels + Injected Anomalies + Expected Shifts)."""
    rows: list[dict[str, Any]] = []

    # 1. Stratified human-reviewed evaluation subset across source_type & polarity
    eligible = [
        g
        for g in gold_annotations
        if g["evaluatable"] and g["record_id"] not in excluded_eval_ids
    ]
    by_bucket: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for g in eligible:
        by_bucket.setdefault((g["source_type"], g["gold_polarity"]), []).append(g)

    selected_eval: list[dict[str, Any]] = []
    buckets = sorted(by_bucket.keys())
    per_bucket = max(1, eval_sample_size // max(1, len(buckets)))
    remainder = max(0, eval_sample_size - per_bucket * len(buckets))

    for idx, bkey in enumerate(buckets):
        pool = list(by_bucket[bkey])
        rng.shuffle(pool)
        take = per_bucket + (1 if idx < remainder else 0)
        selected_eval.extend(pool[:take])

    selected_eval.sort(key=lambda r: (r["source_type"], r["record_id"]))

    table_map = {
        FeedbackSourceType.SURVEY_RESPONSE.value: "survey_responses",
        FeedbackSourceType.REVIEW.value: "reviews",
        FeedbackSourceType.SUPPORT_MESSAGE.value: "support_messages",
    }

    for idx, g in enumerate(selected_eval, start=1):
        rows.append(
            {
                "ground_truth_id": f"GT-EVAL-{idx:06d}",
                "record_category": "EVALUATION_GOLD_LABEL",
                "issue_type": "NONE",
                "target_table": table_map[g["source_type"]],
                "target_record_id": g["record_id"],
                "source_record_id": g["record_id"],
                "expected_decision": f"POLARITY={g['gold_polarity']}",
                "expected_rule": "EVAL-GOLD-001",
                "details_json": json.dumps(
                    {
                        "source_type": g["source_type"],
                        "language": g["language"],
                        "gold_polarity": g["gold_polarity"],
                        "gold_score": g["gold_score"],
                        "gold_themes": sorted(g["gold_themes"]),
                        "is_sarcastic": g["is_sarcastic"],
                        "is_ambiguous": g["is_ambiguous"],
                        "reviewer_id": f"HUMAN-REV-{(idx % 5) + 1:02d}",
                        "reviewed_at": anchor_dt.isoformat() + "Z",
                    },
                    sort_keys=True,
                ),
            }
        )

    # 2. Injected edge-case anomalies
    rows.extend(anomaly_records)

    # 3. Planted expected temporal sentiment shifts
    shift_seq = 1
    for (prod_id, theme_id), (direction, base_neg, curr_neg) in sorted(PLANTED_SHIFT_COHORTS.items()):
        if prod_id not in available_product_ids:
            continue
        rows.append(
            {
                "ground_truth_id": f"GT-SHIFT-{shift_seq:06d}",
                "record_category": "EXPECTED_SHIFT",
                "issue_type": f"SHIFT_{direction}",
                "target_table": "sentiment_shifts",
                "target_record_id": f"{prod_id}:{theme_id}",
                "source_record_id": f"{prod_id}:{theme_id}",
                "expected_decision": f"DETECT_{direction}_SHIFT",
                "expected_rule": "BR-SHIFT-001",
                "details_json": json.dumps(
                    {
                        "product_id": prod_id,
                        "theme_id": theme_id,
                        "expected_direction": direction,
                        "baseline_neg_prob": base_neg,
                        "current_neg_prob": curr_neg,
                    },
                    sort_keys=True,
                ),
            }
        )
        shift_seq += 1

    return rows


def export_ground_truth(
    gt_records: list[dict[str, Any]],
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write segregated ground_truth.csv and ground_truth.json outside operational exports."""
    gt_dir = output_dir or (settings.data_dir / "ground_truth")
    gt_dir.mkdir(parents=True, exist_ok=True)

    csv_path = gt_dir / "ground_truth.csv"
    json_path = gt_dir / "ground_truth.json"

    fieldnames = [
        "ground_truth_id",
        "record_category",
        "issue_type",
        "target_table",
        "target_record_id",
        "source_record_id",
        "expected_decision",
        "expected_rule",
        "details_json",
    ]
    sorted_rows = sorted(gt_records, key=lambda r: (r["record_category"], r["ground_truth_id"]))

    with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_rows)

    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump(sorted_rows, f, indent=2, ensure_ascii=False, sort_keys=True)

    return csv_path, json_path

