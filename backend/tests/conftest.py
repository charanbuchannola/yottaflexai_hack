"""Shared pytest fixtures for the Enterprise VoC Intelligence Backend test suite."""

from pathlib import Path

import pytest

from voc_intel.core.config import ProfileType
from voc_intel.services.pipeline_service import PipelineResult, run_full_pipeline


@pytest.fixture(scope="session")
def starter_pipeline(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, PipelineResult]:
    """Run a complete starter pipeline once for fast read-only integration & API tests."""
    root = tmp_path_factory.mktemp("starter_voc")
    db_dir = root / "database"
    e_dir = root / "exports"
    db_url = f"sqlite:///{(db_dir / 'voc_intelligence.db').as_posix()}"
    result = run_full_pipeline(
        profile=ProfileType.STARTER,
        seed=20261022,
        inject_anomalies=True,
        database_dir=db_dir,
        exports_dir=e_dir,
        database_url=db_url,
    )
    return root, result

