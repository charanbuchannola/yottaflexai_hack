"""SHA-256 source manifest and provenance metadata generator."""

import hashlib
import json
from pathlib import Path
from typing import Any

from voc_intel.core.config import ProfileConfig, ProfileType, settings


def compute_sha256(file_path: Path) -> str:
    """Compute deterministic SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_source_manifest(
    record_counts: dict[str, int],
    profile: ProfileType,
    profile_cfg: ProfileConfig,
    seed: int,
    generator_command: str,
    inject_anomalies: bool,
    database_dir: Path | None = None,
    exports_dir: Path | None = None,
    output_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Compute SHA-256 digests across all exports, database DDL/seeds & ground truth."""
    db_dir = database_dir or settings.database_dir
    e_dir = exports_dir or settings.exports_dir
    manifest_target = output_path or (e_dir / "source_manifest.json")
    manifest_target.parent.mkdir(parents=True, exist_ok=True)

    tracked_dirs = (
        (e_dir / "csv", e_dir.parent),
        (e_dir / "json", e_dir.parent),
        (e_dir / "reports", e_dir.parent),
        (db_dir / "schema", db_dir.parent),
        (db_dir / "migrations", db_dir.parent),
        (db_dir / "seeds", db_dir.parent),
        (db_dir / "ground_truth", db_dir.parent),
    )

    files_manifest: dict[str, dict[str, Any]] = {}
    total_bytes = 0

    for tracked, base in tracked_dirs:
        if tracked.exists():
            for p in sorted(tracked.glob("*")):
                if p.is_file():
                    sha = compute_sha256(p)
                    size = p.stat().st_size
                    total_bytes += size
                    try:
                        rel_path = str(p.relative_to(base)).replace("\\", "/")
                    except ValueError:
                        rel_path = p.name
                    files_manifest[rel_path] = {
                        "sha256": sha,
                        "size_bytes": size,
                    }

    manifest_payload: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "schema_version": "1.0.0",
        "generator_version": "0.1.0",
        "generated_anchor_utc": settings.simulation_anchor.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": seed,
        "dataset_profile": profile.value,
        "inject_anomalies": inject_anomalies,
        "generator_command": generator_command,
        "lawful_provenance": {
            "source_type": "SYNTHETIC_DETERMINISTIC",
            "external_datasets_used": False,
            "pii_policy": "Strictly privacy-safe synthetic text; decoy PII exists only in labelled CUSTOMER_IDENTITY_LEAKED edge-case rows using RFC-2606 .invalid domains and 555 numbers.",
        },
        "configuration": {
            "customers_count": profile_cfg.customers_count,
            "products_count": profile_cfg.products_count,
            "surveys_count": profile_cfg.surveys_count,
            "survey_responses_count": profile_cfg.survey_responses_count,
            "reviews_count": profile_cfg.reviews_count,
            "support_tickets_count": profile_cfg.support_tickets_count,
            "simulation_days": profile_cfg.simulation_days,
        },
        "entity_counts": record_counts,
        "total_files": len(files_manifest),
        "total_bytes": total_bytes,
        "files": files_manifest,
    }

    with open(manifest_target, mode="w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest_payload, f, indent=2, sort_keys=True)

    return manifest_target, manifest_payload

