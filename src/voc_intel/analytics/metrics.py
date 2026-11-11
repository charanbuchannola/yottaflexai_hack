"""Measurable evaluation metrics: Sentiment F1, Theme F1, Shift detection, Priorities, and Anomaly matrix."""

from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from voc_intel.config import settings
from voc_intel.models.base import PriorityTier, SentimentPolarity


def _prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def compute_evaluation_metrics(
    gt_records: list[dict[str, Any]],
    sentiment_labels: list[dict[str, Any]],
    theme_assignments: list[dict[str, Any]],
    sentiment_shifts: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    action_evidence: list[dict[str, Any]],
    detected_anomalies: list[dict[str, Any]],
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate NLP, shift detection, action priority traceability, and anomaly detection."""
    pred_sent_by_rec: dict[str, str] = {}
    for sl in sentiment_labels:
        rid = sl["response_id"] or sl["review_id"] or sl["message_id"]
        pred_sent_by_rec[rid] = sl["polarity"]

    pred_themes_by_rec: dict[str, set[str]] = defaultdict(set)
    for asn in theme_assignments:
        if asn["theme_id"] is not None:
            rid = asn["response_id"] or asn["review_id"] or asn["message_id"]
            pred_themes_by_rec[rid].add(asn["theme_id"])

    # 1. Human-reviewed Sentiment & Theme evaluation
    eval_rows = [g for g in gt_records if g["record_category"] == "EVALUATION_GOLD_LABEL"]
    polarities = [p.value for p in SentimentPolarity]
    class_counts: dict[str, dict[str, int]] = {
        p: {"tp": 0, "fp": 0, "fn": 0} for p in polarities
    }

    sent_correct = 0
    sarcastic_total = 0
    sarcastic_correct = 0
    non_en_total = 0
    non_en_correct = 0

    theme_tp = 0
    theme_fp = 0
    theme_fn = 0
    theme_exact = 0

    for g in eval_rows:
        rid = g["target_record_id"]
        details = json.loads(g["details_json"])
        gold_pol = details["gold_polarity"]
        pred_pol = pred_sent_by_rec.get(rid, "NEUTRAL")

        if pred_pol == gold_pol:
            sent_correct += 1
        if details.get("is_sarcastic"):
            sarcastic_total += 1
            if pred_pol == gold_pol:
                sarcastic_correct += 1
        if details.get("language") != "en":
            non_en_total += 1
            if pred_pol == gold_pol:
                non_en_correct += 1

        for p in polarities:
            if pred_pol == p and gold_pol == p:
                class_counts[p]["tp"] += 1
            elif pred_pol == p and gold_pol != p:
                class_counts[p]["fp"] += 1
            elif pred_pol != p and gold_pol == p:
                class_counts[p]["fn"] += 1

        gold_themes = set(details["gold_themes"])
        pred_themes = pred_themes_by_rec.get(rid, set())
        tp_i = len(gold_themes & pred_themes)
        fp_i = len(pred_themes - gold_themes)
        fn_i = len(gold_themes - pred_themes)
        theme_tp += tp_i
        theme_fp += fp_i
        theme_fn += fn_i
        if gold_themes == pred_themes:
            theme_exact += 1

    per_class_sentiment = {
        p: _prf(c["tp"], c["fp"], c["fn"]) for p, c in class_counts.items()
    }
    macro_f1 = round(
        sum(v["f1"] for v in per_class_sentiment.values()) / max(1, len(per_class_sentiment)),
        4,
    )
    eval_n = len(eval_rows)

    # 2. Shift detection evaluation
    expected_shifts = {
        (json.loads(g["details_json"])["product_id"], json.loads(g["details_json"])["theme_id"]): json.loads(
            g["details_json"]
        )["expected_direction"]
        for g in gt_records
        if g["record_category"] == "EXPECTED_SHIFT"
    }
    detected_sig_shifts = {
        (s["product_id"], s["theme_id"]): s["direction"]
        for s in sentiment_shifts
        if s["is_significant"] and s["product_id"] and s["theme_id"]
    }
    sh_tp = sum(
        1 for k, d in detected_sig_shifts.items() if expected_shifts.get(k) == d
    )
    sh_fp = sum(
        1 for k, d in detected_sig_shifts.items() if expected_shifts.get(k) != d
    )
    sh_fn = sum(
        1 for k, d in expected_shifts.items() if detected_sig_shifts.get(k) != d
    )

    # 3. Anomaly detection confusion matrix
    gt_anomalies = {
        (g["issue_type"], g["target_record_id"])
        for g in gt_records
        if g["record_category"] == "INJECTED_ANOMALY"
    }
    pred_anomalies = {
        (a["issue_type"], a["target_record_id"]) for a in detected_anomalies
    }
    anom_tp = len(gt_anomalies & pred_anomalies)
    anom_fp = len(pred_anomalies - gt_anomalies)
    anom_fn = len(gt_anomalies - pred_anomalies)

    per_anomaly_type: dict[str, dict[str, Any]] = {}
    all_types = sorted({t for t, _ in gt_anomalies} | {t for t, _ in pred_anomalies})
    for atype in all_types:
        gt_sub = {rid for t, rid in gt_anomalies if t == atype}
        pr_sub = {rid for t, rid in pred_anomalies if t == atype}
        per_anomaly_type[atype] = _prf(
            len(gt_sub & pr_sub), len(pr_sub - gt_sub), len(gt_sub - pr_sub)
        )

    # 4. Priority & traceability summary
    evid_by_action: dict[str, int] = defaultdict(int)
    for ev in action_evidence:
        evid_by_action[ev["action_id"]] += 1

    reconciled_actions = sum(
        1 for act in action_items if evid_by_action[act["action_id"]] == act["mention_count"]
    )

    report = {
        "evaluation_set_size": eval_n,
        "sentiment_metrics": {
            "accuracy": round(sent_correct / eval_n, 4) if eval_n else 0.0,
            "macro_f1": macro_f1,
            "sarcasm_accuracy": round(sarcastic_correct / sarcastic_total, 4) if sarcastic_total else 0.0,
            "sarcasm_samples": sarcastic_total,
            "multilingual_accuracy": round(non_en_correct / non_en_total, 4) if non_en_total else 0.0,
            "multilingual_samples": non_en_total,
            "per_class": per_class_sentiment,
        },
        "theme_metrics": {
            **_prf(theme_tp, theme_fp, theme_fn),
            "exact_match_rate": round(theme_exact / eval_n, 4) if eval_n else 0.0,
        },
        "sentiment_shift_metrics": {
            "expected_shifts": len(expected_shifts),
            "detected_significant_shifts": len(detected_sig_shifts),
            **_prf(sh_tp, sh_fp, sh_fn),
        },
        "service_priority_metrics": {
            "action_items_count": len(action_items),
            "p0_critical_count": sum(1 for a in action_items if a["priority_tier"] == PriorityTier.P0_CRITICAL.value),
            "p1_high_count": sum(1 for a in action_items if a["priority_tier"] == PriorityTier.P1_HIGH.value),
            "p2_medium_count": sum(1 for a in action_items if a["priority_tier"] == PriorityTier.P2_MEDIUM.value),
            "total_evidence_links": len(action_evidence),
            "evidence_reconciliation_rate": (
                round(reconciled_actions / len(action_items), 4) if action_items else 1.0
            ),
        },
        "anomaly_detection_metrics": {
            "expected_anomalies": len(gt_anomalies),
            "detected_anomalies": len(pred_anomalies),
            "overall": _prf(anom_tp, anom_fp, anom_fn),
            "by_issue_type": per_anomaly_type,
        },
    }

    target = output_path or (settings.exports_dir / "reports" / "evaluation_metrics.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    return report

