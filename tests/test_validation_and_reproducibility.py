"""Tests for parameterized scale, evaluation measurability, negative checks, CLI, and reproducibility."""

import copy
from datetime import timedelta

from typer.testing import CliRunner

from voc_intel.analytics.reproducibility import verify_reproducibility
from voc_intel.config import ProfileType
from voc_intel.exporters.relational import load_tables_from_db
from voc_intel.main import app as cli_app
from voc_intel.models.database import build_engine
from voc_intel.pipeline.orchestrator import run_full_pipeline
from voc_intel.validators.runner import run_all_validations


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


def test_negative_validations_catch_corruption(starter_pipeline, tmp_path) -> None:
    root, _res = starter_pipeline
    engine = build_engine(f"sqlite:///{(root / 'data' / 'voc_intelligence.db').as_posix()}")
    try:
        tables = load_tables_from_db(engine)
    finally:
        engine.dispose()

    corrupted = copy.deepcopy(tables)
    # 1. Inject orphan FK on a review
    corrupted["reviews"][0]["product_id"] = "PROD-999"
    # 2. Inject date ordering violation on a ticket
    corrupted["support_tickets"][0]["resolved_at"] = corrupted["support_tickets"][0]["opened_at"] - timedelta(hours=1)
    # 3. Inject reconciliation mismatch on a survey count
    corrupted["surveys"][0]["actual_response_count"] += 99
    # 4. Inject FSM projection drift
    corrupted["reviews"][0]["lifecycle_state"] = "QUARANTINED"

    rep = run_all_validations(
        tables=corrupted,
        gt_records=[],
        engine=None,
        expect_anomalies=False,
        output_path=tmp_path / "corrupt_val.json",
    )
    assert rep["overall_passed"] is False
    by_id = {c["check_id"]: c["passed"] for c in rep["checks"]}
    assert by_id["VAL-FK-INTEGRITY"] is False
    assert by_id["VAL-DATE-ORDER"] is False
    assert by_id["VAL-RECONCILIATION"] is False
    assert by_id["VAL-FSM-REPLAY"] is False


def test_cli_validate_and_evaluate_commands(starter_pipeline, tmp_path) -> None:
    root, _res = starter_pipeline
    db_url = f"sqlite:///{(root / 'data' / 'voc_intelligence.db').as_posix()}"
    gt_path = root / "data" / "ground_truth" / "ground_truth.json"

    runner = CliRunner()
    val_res = runner.invoke(
        cli_app,
        [
            "validate",
            "--database-url",
            db_url,
            "--ground-truth-path",
            str(gt_path),
            "--output-path",
            str(tmp_path / "cli_val.json"),
        ],
    )
    assert val_res.exit_code == 0, val_res.output
    assert "23/23 checks" in val_res.output

    eval_res = runner.invoke(
        cli_app,
        [
            "evaluate",
            "--database-url",
            db_url,
            "--ground-truth-path",
            str(gt_path),
            "--output-path",
            str(tmp_path / "cli_eval.json"),
        ],
    )
    assert eval_res.exit_code == 0, eval_res.output
    assert "Evaluation Set Size" in eval_res.output

