"""Shared pytest fixtures for the VoC Intelligence test suite."""

from pathlib import Path

import pytest

from voc_intel.config import ProfileType
from voc_intel.pipeline.orchestrator import PipelineResult, run_full_pipeline


@pytest.fixture(scope="session")
def starter_pipeline(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, PipelineResult]:
    """Run a complete starter pipeline once for fast read-only integration & API tests."""
    root = tmp_path_factory.mktemp("starter_voc")
    d_dir = root / "data"
    e_dir = root / "exports"
    db_url = f"sqlite:///{(d_dir / 'voc_intelligence.db').as_posix()}"
    result = run_full_pipeline(
        profile=ProfileType.STARTER,
        seed=20261022,
        inject_anomalies=True,
        data_dir=d_dir,
        exports_dir=e_dir,
        database_url=db_url,
    )
    return root, result

