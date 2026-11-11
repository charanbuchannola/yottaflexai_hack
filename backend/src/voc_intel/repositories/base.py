"""Shared repository base class holding an injected SQLAlchemy Session."""

from sqlalchemy.orm import Session


class BaseRepository:
    """Base database repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

