"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from voc_intel.api.routes import router
from voc_intel.config import settings
from voc_intel.models.database import build_engine, init_database


def create_app(
    database_url: str | None = None,
    exports_dir: Path | None = None,
) -> FastAPI:
    """Create configured FastAPI app bound to target SQLAlchemy engine."""
    db_url = database_url or settings.database_url
    engine = build_engine(db_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        init_database(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="YottaFlex Voice of Customer Intelligence API",
        version="0.1.0",
        description="End-to-end Theme, Sentiment Shift, Service Priority, and Anomaly Traceability API.",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.database_url = db_url
    app.state.exports_dir = exports_dir or settings.exports_dir
    app.state.session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    app.include_router(router)
    return app
