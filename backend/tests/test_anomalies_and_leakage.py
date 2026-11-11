"""Tests for baseline purity, all 5 required edge cases, and zero ground-truth leakage."""

import csv
import json

from voc_intel.core.config import ProfileType
from voc_intel.features.generation.anomalies import ANOMALY_TYPES
from voc_intel.services.pipeline_service import run_full_pipeline


def test_baseline_mode_has_zero_anomalies_and_zero_leakage(tmp_path) -> None:
    db_dir = tmp_path / "database"
    e_dir = tmp_path / "exports"
    res = run_full_pipeline(
        profile=ProfileType.STARTER,
        seed=20261022,
        inject_anomalies=False,
        responses_override=120,
        reviews_override=120,
        messages_override=120,
        database_dir=db_dir,
        exports_dir=e_dir,
        database_url=f"sqlite:///{(db_dir / 'baseline.db').as_posix()}",
    )
    assert res.validation_report["overall_passed"] is True
    assert res.validation_report["mode"] == "BASELINE"
    assert res.validation_report["detected_anomalies"] == []

    with open(e_dir / "csv" / "model_inputs.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        assert not (headers & {"ground_truth_id", "gold_polarity", "gold_themes", "issue_type"})
        for row in reader:
            assert row["split_partition"] != "TEST"
            assert "leaked_gold_sentiment" not in row["extra_features_json"]


def test_with_anomalies_detects_all_five_edge_cases_with_perfect_f1(starter_pipeline) -> None:
    root, res = starter_pipeline
    assert res.validation_report["overall_passed"] is True
    anom_metrics = res.evaluation_metrics["anomaly_detection_metrics"]
    assert anom_metrics["overall"]["precision"] == 1.0
    assert anom_metrics["overall"]["recall"] == 1.0
    assert anom_metrics["overall"]["f1"] == 1.0

    by_type = anom_metrics["by_issue_type"]
    for issue_type in ANOMALY_TYPES:
        assert issue_type in by_type
        assert by_type[issue_type]["precision"] == 1.0
        assert by_type[issue_type]["recall"] == 1.0

    gt_json = json.loads((root / "database" / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    categories = {row["record_category"] for row in gt_json}
    assert categories == {"EVALUATION_GOLD_LABEL", "INJECTED_ANOMALY", "EXPECTED_SHIFT"}

