"""FastAPI application factory with CORS middleware and domain exception handlers."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from voc_intel.api.v1.health import router as health_router
from voc_intel.api.v1.router import api_v1_router
from voc_intel.core.config import settings
from voc_intel.core.database import build_engine, init_database
from voc_intel.core.exceptions import InvalidStateTransitionError, ResourceNotFoundError


def create_app(
    database_url: str | None = None,
    exports_dir: Path | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create configured FastAPI app decoupled from database queries and frontend assets."""
    db_url = database_url or settings.database_url
    engine = build_engine(db_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        init_database(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="YottaFlex Voice of Customer Intelligence API",
        version="0.2.0",
        description="Enterprise REST Backend for Theme, Sentiment Shift, Priority Traceability & Exception Auditing.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ResourceNotFoundError)
    async def _not_found_handler(_request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidStateTransitionError)
    async def _invalid_transition_handler(
        _request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.state.engine = engine
    app.state.database_url = db_url
    app.state.exports_dir = exports_dir or settings.exports_dir
    app.state.session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix="/api/v1")
    return app

