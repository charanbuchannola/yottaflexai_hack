"""Centralized configuration, profiles, and scale parameterization."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        default="sqlite:///data/voc_intelligence.db",
        description="SQLAlchemy database connection string",
    )
    simulation_anchor: datetime = Field(
        default=datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc),
        description="Deterministic reference end-of-window timestamp in UTC",
    )
    data_dir: Path = Field(default=Path("data"), description="Base data directory")
    exports_dir: Path = Field(default=Path("exports"), description="Base exports directory")
    api_host: str = Field(default="127.0.0.1", description="FastAPI bind host")
    api_port: int = Field(default=8000, description="FastAPI bind port")

    @property
    def sim_year(self) -> int:
        """Return reference simulation year."""
        return self.simulation_anchor.year

    @property
    def active_profile(self) -> ProfileConfig:
        """Return active ProfileConfig."""
        return PROFILES[self.profile]

    def ensure_directories(self) -> None:
        """Ensure required output directories exist."""
        for sub in (
            self.data_dir,
            self.data_dir / "ground_truth",
            self.exports_dir / "csv",
            self.exports_dir / "json",
            self.exports_dir / "sql",
            self.exports_dir / "reports",
        ):
            sub.mkdir(parents=True, exist_ok=True)


settings = Settings()

