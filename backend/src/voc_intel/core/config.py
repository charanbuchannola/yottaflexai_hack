"""Centralized configuration, scale profiles, and cross-tier directory resolution."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_repo_root() -> Path:
    """Resolve monorepo root containing database/, backend/, and frontend/."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "backend").is_dir() and (parent / "docs").is_dir():
            return parent
    return Path.cwd()


class ProfileType(str, Enum):
    """Supported dataset scale profiles."""

    STARTER = "STARTER"
    FULL = "FULL"


class ProfileConfig(NamedTuple):
    """Scale parameters for synthetic generation."""

    customers_count: int
    products_count: int
    surveys_count: int
    survey_responses_count: int
    reviews_count: int
    support_tickets_count: int
    avg_messages_per_ticket: float
    simulation_days: int
    eval_sample_size: int
    anomalies_per_type: int


PROFILES: dict[ProfileType, ProfileConfig] = {
    ProfileType.STARTER: ProfileConfig(
        customers_count=250,
        products_count=5,
        surveys_count=6,
        survey_responses_count=600,
        reviews_count=600,
        support_tickets_count=240,
        avg_messages_per_ticket=2.5,  # 600 support messages
        simulation_days=30,
        eval_sample_size=300,
        anomalies_per_type=3,
    ),
    ProfileType.FULL: ProfileConfig(
        customers_count=5000,
        products_count=10,
        surveys_count=50,
        survey_responses_count=25000,
        reviews_count=25000,  # 25,000 responses + 25,000 reviews = 50,000
        support_tickets_count=8000,
        avg_messages_per_ticket=2.5,  # 20,000 support messages
        simulation_days=90,
        eval_sample_size=2500,
        anomalies_per_type=10,
    ),
}


_DEFAULT_ROOT = _detect_repo_root()


class Settings(BaseSettings):
    """Application settings configurable via environment variables or CLI."""

    model_config = SettingsConfigDict(
        env_prefix="VOC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    seed: int = Field(default=20261022, description="Fixed deterministic PRNG seed")
    profile: ProfileType = Field(default=ProfileType.STARTER, description="Dataset scale profile")
    database_url: str = Field(
        default=f"sqlite:///{(_DEFAULT_ROOT / 'database' / 'voc_intelligence.db').as_posix()}",
        description="SQLAlchemy database connection string",
    )
    simulation_anchor: datetime = Field(
        default=datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc),
        description="Deterministic reference end-of-window timestamp in UTC",
    )
    database_dir: Path = Field(
        default=_DEFAULT_ROOT / "database",
        description="Database tier directory (schema, migrations, seeds, ground truth)",
    )
    exports_dir: Path = Field(
        default=_DEFAULT_ROOT / "exports",
        description="Canonical analytical export directory (CSV, JSON, reports, manifest)",
    )
    docs_dir: Path = Field(
        default=_DEFAULT_ROOT / "docs",
        description="Documentation directory",
    )
    api_host: str = Field(default="127.0.0.1", description="FastAPI bind host")
    api_port: int = Field(default=8000, description="FastAPI bind port")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed Next.js frontend origins for CORS",
    )

    @property
    def sim_year(self) -> int:
        """Return reference simulation year."""
        return self.simulation_anchor.year

    @property
    def active_profile(self) -> ProfileConfig:
        """Return active ProfileConfig."""
        return PROFILES[self.profile]

    def ensure_directories(self) -> None:
        """Ensure required database and export subdirectories exist."""
        for sub in (
            self.database_dir,
            self.database_dir / "schema",
            self.database_dir / "migrations",
            self.database_dir / "seeds",
            self.database_dir / "ground_truth",
            self.exports_dir / "csv",
            self.exports_dir / "json",
            self.exports_dir / "reports",
        ):
            sub.mkdir(parents=True, exist_ok=True)


settings = Settings()

