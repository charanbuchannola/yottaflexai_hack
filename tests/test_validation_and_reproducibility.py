"""Tests for parameterized scale, evaluation measurability, and fixed-seed reproducibility."""

from voc_intel.analytics.reproducibility import verify_reproducibility
from voc_intel.config import ProfileType
from voc_intel.pipeline.orchestrator import run_full_pipeline


def test_parameterized_custom_scale_generation(tmp_path) -> None:
    d_dir = tmp_path / "data"
    e_dir = tmp_path / "exports"
    res = run_full_pipeline(
        profile=ProfileType.STARTER,
        seed=998877,
        inject_anomalies=True,
        responses_override=150,
        reviews_override=180,
        messages_override=160,
        data_dir=d_dir,
        exports_dir=e_dir,
        database_url=f"sqlite:///{(d_dir / 'custom.db').as_posix()}",
    )
    assert res.validation_report["overall_passed"] is True
    # 150 baseline + 3 injected duplicates = 153
    assert res.row_counts["survey_responses"] == 153
    assert res.row_counts["reviews"] == 180
    assert res.row_counts["support_messages"] == 160
    assert res.evaluation_metrics["sentiment_metrics"]["accuracy"] >= 0.80
    assert res.evaluation_metrics["service_priority_metrics"]["evidence_reconciliation_rate"] == 1.0


def test_fixed_seed_double_run_reproducibility(tmp_path) -> None:
    report_path = tmp_path / "repro.md"
    summary = verify_reproducibility(
        profile=ProfileType.STARTER,
        seed=20261022,
        inject_anomalies=True,
        report_path=report_path,
    )
    assert summary["reproducible"] is True
    assert summary["counts_match"] is True
    assert summary["mismatches"] == []
    assert summary["matched_files"] == summary["total_files_compared"]
    assert report_path.exists()

