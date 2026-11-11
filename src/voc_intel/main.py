"""Typer CLI entry point for generation, validation, evaluation, reproducibility, and API serving."""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
import typer
import uvicorn

from voc_intel.analytics.metrics import compute_evaluation_metrics
from voc_intel.analytics.reproducibility import verify_reproducibility
from voc_intel.config import ProfileType, settings
from voc_intel.exporters.relational import load_tables_from_db
from voc_intel.models.database import build_engine, reset_database
from voc_intel.pipeline.orchestrator import PipelineResult, run_full_pipeline
from voc_intel.validators.runner import run_all_validations

app = typer.Typer(
    name="voc-intel",
    help="YottaFlex Voice of Customer (VoC) Theme, Sentiment Shift & Priority Intelligence CLI.",
    no_args_is_help=True,
)
console = Console()


def _print_result_summary(result: PipelineResult) -> None:
    tbl = Table(title=f"VoC Intelligence Pipeline Summary ({result.profile.value}, seed={result.seed})")
    tbl.add_column("Metric / Entity", style="cyan")
    tbl.add_column("Value", justify="right", style="green")

    for name, cnt in result.row_counts.items():
        tbl.add_row(f"table:{name}", str(cnt))

    val = result.validation_report
    tbl.add_row("validation:overall_passed", str(val["overall_passed"]))
    tbl.add_row("validation:passed_checks", f"{val['passed_checks']}/{val['total_checks']}")

    ev = result.evaluation_metrics
    tbl.add_row("eval:sentiment_accuracy", str(ev["sentiment_metrics"]["accuracy"]))
    tbl.add_row("eval:sentiment_macro_f1", str(ev["sentiment_metrics"]["macro_f1"]))
    tbl.add_row("eval:theme_micro_f1", str(ev["theme_metrics"]["f1"]))
    tbl.add_row("eval:shift_f1", str(ev["sentiment_shift_metrics"]["f1"]))
    tbl.add_row("eval:anomaly_f1", str(ev["anomaly_detection_metrics"]["overall"]["f1"]))
    tbl.add_row("manifest:files", str(result.manifest["total_files"]))
    console.print(tbl)


@app.command()
def init(
    database_url: Optional[str] = typer.Option(None, help="Override SQLAlchemy database URL"),
) -> None:
    """Initialize empty schema tables and directory structure."""
    settings.ensure_directories()
    engine = build_engine(database_url)
    reset_database(engine)
    engine.dispose()
    console.print(f"[green]Initialized schema at {database_url or settings.database_url}[/green]")


@app.command()
def generate(
    profile: ProfileType = typer.Option(ProfileType.STARTER, help="Dataset scale profile"),
    seed: int = typer.Option(20261022, help="Deterministic PRNG seed"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies", help="Inject labelled edge cases"),
    responses: Optional[int] = typer.Option(None, help="Override survey response count"),
    reviews: Optional[int] = typer.Option(None, help="Override review count"),
    messages: Optional[int] = typer.Option(None, help="Override support message count"),
) -> None:
    """Run parameterized end-to-end generation, NLP, shifts, priorities, validation, and export."""
    res = run_full_pipeline(
        profile=profile,
        seed=seed,
        inject_anomalies=anomalies,
        responses_override=responses,
        reviews_override=reviews,
        messages_override=messages,
    )
    _print_result_summary(res)
    if not res.validation_report["overall_passed"]:
        raise typer.Exit(code=1)


@app.command("generate-starter")
def generate_starter(
    seed: int = typer.Option(20261022, help="Deterministic PRNG seed"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies"),
) -> None:
    """Generate the fast starter dataset profile."""
    res = run_full_pipeline(
        profile=ProfileType.STARTER,
        seed=seed,
        inject_anomalies=anomalies,
        generator_command=f"voc-intel generate-starter --seed {seed}" + ("" if anomalies else " --no-anomalies"),
    )
    _print_result_summary(res)
    if not res.validation_report["overall_passed"]:
        raise typer.Exit(code=1)


@app.command("generate-full")
def generate_full(
    seed: int = typer.Option(20261022, help="Deterministic PRNG seed"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies"),
) -> None:
    """Generate the full required volume (50,000 reviews/responses + 20,000 support messages)."""
    res = run_full_pipeline(
        profile=ProfileType.FULL,
        seed=seed,
        inject_anomalies=anomalies,
        generator_command=f"voc-intel generate-full --seed {seed}" + ("" if anomalies else " --no-anomalies"),
    )
    _print_result_summary(res)
    if not res.validation_report["overall_passed"]:
        raise typer.Exit(code=1)


@app.command()
def reproduce(
    profile: ProfileType = typer.Option(ProfileType.STARTER, help="Profile to test reproducibility"),
    seed: int = typer.Option(20261022, help="Fixed seed for dual-run comparison"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies"),
    report_path: Path = typer.Option(Path("docs/reproducibility_report.md"), help="Output markdown report"),
) -> None:
    """Regenerate twice with identical seed and verify bitwise identical row counts & SHA-256 checksums."""
    summary = verify_reproducibility(
        profile=profile,
        seed=seed,
        inject_anomalies=anomalies,
        report_path=report_path,
    )
    console.print(
        f"[bold]{'PASS' if summary['reproducible'] else 'FAIL'}[/bold]: "
        f"{summary['matched_files']}/{summary['total_files_compared']} files matched bitwise "
        f"(seed={seed}, profile={profile.value})"
    )
    if not summary["reproducible"]:
        for m in summary["mismatches"]:
            console.print(f"[red]  - {m}[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate(
    database_url: Optional[str] = typer.Option(None, help="Override SQLAlchemy database URL"),
    ground_truth_path: Path = typer.Option(
        Path("data/ground_truth/ground_truth.json"), help="Path to segregated ground_truth.json"
    ),
    expect_anomalies: bool = typer.Option(
        True, "--anomalies/--no-anomalies", help="Validate anomaly coverage vs baseline purity"
    ),
    output_path: Optional[Path] = typer.Option(None, help="Output validation report JSON path"),
) -> None:
    """Run full relational, reconciliation, FSM, leakage, and anomaly validations against the database."""
    engine = build_engine(database_url)
    try:
        tables = load_tables_from_db(engine)
        gt_records = (
            json.loads(ground_truth_path.read_text(encoding="utf-8"))
            if ground_truth_path.exists()
            else []
        )
        report = run_all_validations(
            tables=tables,
            gt_records=gt_records,
            engine=engine,
            expect_anomalies=expect_anomalies,
            output_path=output_path,
        )
    finally:
        engine.dispose()

    tbl = Table(title=f"Validation Summary ({report['mode']})")
    tbl.add_column("Check ID", style="cyan")
    tbl.add_column("Passed", justify="center")
    for chk in report["checks"]:
        status = "[green]PASS[/green]" if chk["passed"] else "[red]FAIL[/red]"
        tbl.add_row(chk["check_id"], status)
    console.print(tbl)
    console.print(
        f"Overall: {'PASS' if report['overall_passed'] else 'FAIL'} "
        f"({report['passed_checks']}/{report['total_checks']} checks)"
    )
    if not report["overall_passed"]:
        raise typer.Exit(code=1)


@app.command()
def evaluate(
    database_url: Optional[str] = typer.Option(None, help="Override SQLAlchemy database URL"),
    ground_truth_path: Path = typer.Option(
        Path("data/ground_truth/ground_truth.json"), help="Path to segregated ground_truth.json"
    ),
    output_path: Optional[Path] = typer.Option(None, help="Output evaluation metrics JSON path"),
) -> None:
    """Compute and display measurable NLP, shift detection, priority, and anomaly metrics."""
    if not ground_truth_path.exists():
        console.print(f"[red]Ground truth file not found: {ground_truth_path}[/red]")
        raise typer.Exit(code=1)

    gt_records = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    engine = build_engine(database_url)
    try:
        tables = load_tables_from_db(engine)
    finally:
        engine.dispose()

    val_report = run_all_validations(
        tables=tables,
        gt_records=gt_records,
        expect_anomalies=any(g["record_category"] == "INJECTED_ANOMALY" for g in gt_records),
    )
    metrics = compute_evaluation_metrics(
        gt_records=gt_records,
        sentiment_labels=tables["sentiment_labels"],
        theme_assignments=tables["feedback_theme_assignments"],
        sentiment_shifts=tables["sentiment_shifts"],
        action_items=tables["action_items"],
        action_evidence=tables["action_item_evidence"],
        detected_anomalies=val_report["detected_anomalies"],
        output_path=output_path,
    )

    tbl = Table(title="VoC Evaluation Metrics")
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", justify="right", style="green")
    tbl.add_row("Evaluation Set Size", str(metrics["evaluation_set_size"]))
    tbl.add_row("Sentiment Accuracy", str(metrics["sentiment_metrics"]["accuracy"]))
    tbl.add_row("Sentiment Macro-F1", str(metrics["sentiment_metrics"]["macro_f1"]))
    tbl.add_row("Multilingual Accuracy", str(metrics["sentiment_metrics"]["multilingual_accuracy"]))
    tbl.add_row("Sarcasm Accuracy", str(metrics["sentiment_metrics"]["sarcasm_accuracy"]))
    tbl.add_row("Theme Micro-F1", str(metrics["theme_metrics"]["f1"]))
    tbl.add_row("Shift Detection F1", str(metrics["sentiment_shift_metrics"]["f1"]))
    tbl.add_row("Action Evidence Reconciliation", str(metrics["service_priority_metrics"]["evidence_reconciliation_rate"]))
    tbl.add_row("Anomaly Detection F1", str(metrics["anomaly_detection_metrics"]["overall"]["f1"]))
    console.print(tbl)


@app.command()
def serve(
    host: str = typer.Option(settings.api_host, help="API host"),
    port: int = typer.Option(settings.api_port, help="API port"),
) -> None:
    """Launch FastAPI REST server."""
    from voc_intel.api.app import create_app

    fastapi_app = create_app()
    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
