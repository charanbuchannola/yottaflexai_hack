"""End-to-end pipeline service orchestrating generation, NLP, shifts, priorities, validation, and export."""

from dataclasses import dataclass
from pathlib import Path
import random
from typing import Any

from voc_intel.core.config import PROFILES, ProfileConfig, ProfileType, settings
from voc_intel.core.database import build_engine
from voc_intel.features.evaluation.ground_truth import (
    build_ground_truth_records,
    export_ground_truth,
)
from voc_intel.features.evaluation.metrics import compute_evaluation_metrics
from voc_intel.features.export.manifest import generate_source_manifest
from voc_intel.features.export.relational import export_canonical_artifacts
from voc_intel.features.generation.anomalies import inject_edge_case_anomalies
from voc_intel.features.generation.feedback import generate_feedback_records
from voc_intel.features.generation.master_data import generate_master_data
from voc_intel.features.nlp.classifier import build_model_inputs_and_run_nlp
from voc_intel.features.priorities.engine import generate_action_items
from voc_intel.features.shifts.detector import detect_sentiment_shifts
from voc_intel.features.validation.runner import run_all_validations
from voc_intel.repositories.dataset_repo import DatasetRepository


@dataclass
class PipelineResult:
    """Structured summary returned by run_full_pipeline."""

    profile: ProfileType
    seed: int
    inject_anomalies: bool
    database_url: str
    row_counts: dict[str, int]
    validation_report: dict[str, Any]
    evaluation_metrics: dict[str, Any]
    manifest_path: Path
    manifest: dict[str, Any]


def run_full_pipeline(
    profile: ProfileType = ProfileType.STARTER,
    seed: int = 20261022,
    inject_anomalies: bool = True,
    responses_override: int | None = None,
    reviews_override: int | None = None,
    messages_override: int | None = None,
    database_dir: Path | None = None,
    exports_dir: Path | None = None,
    database_url: str | None = None,
    generator_command: str | None = None,
) -> PipelineResult:
    """Execute end-to-end deterministic generation, NLP, shifts, priorities, validation, and export."""
    base_cfg = PROFILES[profile]
    eff_cfg = ProfileConfig(
        customers_count=base_cfg.customers_count,
        products_count=base_cfg.products_count,
        surveys_count=base_cfg.surveys_count,
        survey_responses_count=(
            responses_override if responses_override is not None else base_cfg.survey_responses_count
        ),
        reviews_count=reviews_override if reviews_override is not None else base_cfg.reviews_count,
        support_tickets_count=base_cfg.support_tickets_count,
        avg_messages_per_ticket=base_cfg.avg_messages_per_ticket,
        simulation_days=base_cfg.simulation_days,
        eval_sample_size=base_cfg.eval_sample_size,
        anomalies_per_type=base_cfg.anomalies_per_type,
    )

    db_dir = database_dir or settings.database_dir
    e_dir = exports_dir or settings.exports_dir
    for sub in (
        db_dir,
        db_dir / "schema",
        db_dir / "migrations",
        db_dir / "seeds",
        db_dir / "ground_truth",
        e_dir / "csv",
        e_dir / "json",
        e_dir / "reports",
    ):
        sub.mkdir(parents=True, exist_ok=True)

    db_url = database_url or f"sqlite:///{(db_dir / 'voc_intelligence.db').as_posix()}"
    anchor = settings.simulation_anchor
    rng = random.Random(seed)

    # Step 1: Master Data
    master_data = generate_master_data(rng=rng, profile_cfg=eff_cfg, anchor=anchor)

    # Step 2: Baseline Transactional Feedback
    feedback_bundle = generate_feedback_records(
        rng=rng,
        master_data=master_data,
        profile_cfg=eff_cfg,
        responses_override=responses_override,
        reviews_override=reviews_override,
        messages_override=messages_override,
        anchor=anchor,
    )

    # Step 3: Sanitized Model Inputs + Deterministic NLP (Sentiment & Theme Inference)
    nlp_outputs = build_model_inputs_and_run_nlp(
        feedback_bundle=feedback_bundle,
        channels=master_data["channels"],
    )

    # Step 4: Controlled Injection of the 5 Labelled Edge Cases (optional baseline vs anomaly mode)
    anomaly_records: list[dict[str, Any]] = []
    excluded_eval_ids: set[str] = set()
    if inject_anomalies:
        anomaly_records, excluded_eval_ids = inject_edge_case_anomalies(
            rng=rng,
            surveys=master_data["surveys"],
            feedback_bundle=feedback_bundle,
            nlp_outputs=nlp_outputs,
            anomalies_per_type=eff_cfg.anomalies_per_type,
            sim_year=anchor.year,
        )

    # Step 5: Temporal Sentiment Shift Detection (BR-SHIFT-001)
    min_shift_n = 8 if profile == ProfileType.STARTER else 40
    sentiment_shifts = detect_sentiment_shifts(
        feedback_bundle=feedback_bundle,
        sentiment_labels=nlp_outputs["sentiment_labels"],
        theme_assignments=nlp_outputs["feedback_theme_assignments"],
        window_start=feedback_bundle["window_start"],
        split_dt=feedback_bundle["split_dt"],
        anchor_dt=feedback_bundle["anchor_dt"],
        min_window_samples=min_shift_n,
    )

    # Step 6: Service Priority Scoring & ActionItem + Evidence Derivation (BR-PRIO-001)
    action_outputs = generate_action_items(
        feedback_bundle=feedback_bundle,
        channels=master_data["channels"],
        products=master_data["products"],
        sentiment_labels=nlp_outputs["sentiment_labels"],
        theme_assignments=nlp_outputs["feedback_theme_assignments"],
        sentiment_shifts=sentiment_shifts,
        lifecycle_events=feedback_bundle["lifecycle_events"],
        anchor_dt=feedback_bundle["anchor_dt"],
    )

    tables: dict[str, list[dict[str, Any]]] = {
        "channels": master_data["channels"],
        "products": master_data["products"],
        "themes": master_data["themes"],
        "customers": master_data["customers"],
        "surveys": master_data["surveys"],
        "survey_responses": feedback_bundle["survey_responses"],
        "reviews": feedback_bundle["reviews"],
        "support_tickets": feedback_bundle["support_tickets"],
        "support_messages": feedback_bundle["support_messages"],
        "model_inputs": nlp_outputs["model_inputs"],
        "sentiment_labels": nlp_outputs["sentiment_labels"],
        "feedback_theme_assignments": nlp_outputs["feedback_theme_assignments"],
        "sentiment_shifts": sentiment_shifts,
        "action_items": action_outputs["action_items"],
        "action_item_evidence": action_outputs["action_item_evidence"],
        "lifecycle_events": action_outputs["lifecycle_events"],
    }

    # Step 7: Persist via DatasetRepository
    engine = build_engine(db_url)
    dataset_repo = DatasetRepository(engine)
    row_counts = dataset_repo.save_all_tables(tables)

    # Step 8: Segregated Ground Truth Export (never stored in operational tables)
    gt_records = build_ground_truth_records(
        rng=rng,
        gold_annotations=feedback_bundle["gold_annotations"],
        anomaly_records=anomaly_records,
        excluded_eval_ids=excluded_eval_ids,
        eval_sample_size=eff_cfg.eval_sample_size,
        available_product_ids={p["product_id"] for p in master_data["products"]},
        anchor_dt=feedback_bundle["anchor_dt"],
    )
    export_ground_truth(gt_records, output_dir=db_dir / "ground_truth")

    # Step 9: Validation Suite
    validation_report = run_all_validations(
        tables=tables,
        gt_records=gt_records,
        engine=engine,
        expect_anomalies=inject_anomalies,
        output_path=e_dir / "reports" / "validation_report.json",
    )

    # Step 10: Evaluation Metrics
    evaluation_metrics = compute_evaluation_metrics(
        gt_records=gt_records,
        sentiment_labels=tables["sentiment_labels"],
        theme_assignments=tables["feedback_theme_assignments"],
        sentiment_shifts=tables["sentiment_shifts"],
        action_items=tables["action_items"],
        action_evidence=tables["action_item_evidence"],
        detected_anomalies=validation_report["detected_anomalies"],
        output_path=e_dir / "reports" / "evaluation_metrics.json",
    )

    # Step 11: Canonical CSV / JSON / SQL DDL & Seed Exports
    export_canonical_artifacts(
        engine=engine,
        tables=tables,
        exports_dir=e_dir,
        database_dir=db_dir,
    )
    engine.dispose()

    # Step 12: Source Manifest with SHA-256 Checksums
    cmd_str = generator_command or (
        f"voc-intel generate --profile {profile.value.lower()} --seed {seed}"
        + ("" if inject_anomalies else " --no-anomalies")
    )
    manifest_path, manifest = generate_source_manifest(
        record_counts=row_counts,
        profile=profile,
        profile_cfg=eff_cfg,
        seed=seed,
        generator_command=cmd_str,
        inject_anomalies=inject_anomalies,
        database_dir=db_dir,
        exports_dir=e_dir,
        output_path=e_dir / "source_manifest.json",
    )

    return PipelineResult(
        profile=profile,
        seed=seed,
        inject_anomalies=inject_anomalies,
        database_url=db_url,
        row_counts=row_counts,
        validation_report=validation_report,
        evaluation_metrics=evaluation_metrics,
        manifest_path=manifest_path,
        manifest=manifest,
    )

