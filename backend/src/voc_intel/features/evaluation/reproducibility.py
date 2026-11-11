"""Reproducibility verifier: executes two independent runs with identical seed and compares checksums."""

from pathlib import Path
import tempfile
from typing import Any

from voc_intel.core.config import ProfileType, settings
from voc_intel.services.pipeline_service import run_full_pipeline


def verify_reproducibility(
    profile: ProfileType = ProfileType.STARTER,
    seed: int = 20261022,
    inject_anomalies: bool = True,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Run generation twice into clean temp directories and verify bitwise identical checksums & counts."""
    target_report = report_path if report_path is not None else (settings.docs_dir / "reproducibility_report.md")
    with tempfile.TemporaryDirectory() as tmp_root:
        root = Path(tmp_root)
        run1_dir = root / "run1"
        run2_dir = root / "run2"

        res1 = run_full_pipeline(
            profile=profile,
            seed=seed,
            inject_anomalies=inject_anomalies,
            database_dir=run1_dir / "database",
            exports_dir=run1_dir / "exports",
            database_url=f"sqlite:///{(run1_dir / 'database' / 'voc_intelligence.db').as_posix()}",
        )
        res2 = run_full_pipeline(
            profile=profile,
            seed=seed,
            inject_anomalies=inject_anomalies,
            database_dir=run2_dir / "database",
            exports_dir=run2_dir / "exports",
            database_url=f"sqlite:///{(run2_dir / 'database' / 'voc_intelligence.db').as_posix()}",
        )

        counts_match = res1.row_counts == res2.row_counts
        files1 = res1.manifest["files"]
        files2 = res2.manifest["files"]

        all_keys = sorted(set(files1.keys()) | set(files2.keys()))
        mismatches: list[str] = []
        matched_files = 0

        for rel in all_keys:
            f1 = files1.get(rel)
            f2 = files2.get(rel)
            if f1 is None or f2 is None:
                mismatches.append(f"{rel}: missing in one run")
            elif f1["sha256"] != f2["sha256"]:
                mismatches.append(f"{rel}: sha256 mismatch ({f1['sha256']} != {f2['sha256']})")
            else:
                matched_files += 1

        is_reproducible = counts_match and len(mismatches) == 0

        summary = {
            "reproducible": is_reproducible,
            "profile": profile.value,
            "seed": seed,
            "inject_anomalies": inject_anomalies,
            "counts_match": counts_match,
            "total_files_compared": len(all_keys),
            "matched_files": matched_files,
            "mismatches": mismatches,
            "row_counts": res1.row_counts,
            "files": files1,
        }

        if target_report is not None:
            target_report.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "# Reproducibility Verification Report",
                "",
                f"- **Profile**: `{profile.value}`",
                f"- **Fixed Seed**: `{seed}`",
                f"- **Anomalies Included**: `{inject_anomalies}`",
                f"- **Row Counts Identical**: `{counts_match}`",
                f"- **Files Bitwise Matched**: `{matched_files}/{len(all_keys)}`",
                f"- **Overall Status**: `{'PASS' if is_reproducible else 'FAIL'}`",
                "",
                "## Table Row Counts (Run 1 == Run 2)",
                "",
                "| Table | Run 1 Count | Run 2 Count | Match |",
                "| :--- | ---: | ---: | :---: |",
            ]
            for tbl in sorted(res1.row_counts.keys()):
                c1 = res1.row_counts[tbl]
                c2 = res2.row_counts[tbl]
                lines.append(f"| `{tbl}` | {c1} | {c2} | {'PASS' if c1 == c2 else 'FAIL'} |")

            lines.extend(
                [
                    "",
                    "## SHA-256 File Checksum Comparison",
                    "",
                    "| Artifact Path | Size (Bytes) | SHA-256 (Run 1 == Run 2) |",
                    "| :--- | ---: | :--- |",
                ]
            )
            for rel in all_keys:
                info = files1.get(rel, {})
                lines.append(f"| `{rel}` | {info.get('size_bytes', 0)} | `{info.get('sha256', 'MISSING')}` |")

            if mismatches:
                lines.extend(["", "## Mismatches", ""] + [f"- {m}" for m in mismatches])

            target_report.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return summary

