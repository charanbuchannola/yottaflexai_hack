"""Database engine, session factory, and SQLite PRAGMA configuration."""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from voc_intel.core.config import settings
from voc_intel.db.base import Base


def build_engine(database_url: str | None = None) -> Engine:
    """Create SQLAlchemy engine with strict foreign-key enforcement."""
    url = database_url or settings.database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, echo=False, future=True, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _conn_record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()

    return engine


def reset_database(engine: Engine) -> None:
    """Drop and recreate all schema tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def init_database(engine: Engine) -> None:
    """Create all schema tables if absent."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session(engine: Engine) -> Iterator[Session]:
    """Provide a transactional SQLAlchemy session scope."""
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

