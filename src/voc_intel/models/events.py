"""Append-only lifecycle state event ledger ORM model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from voc_intel.models.base import Base


class LifecycleEvent(Base):
    """Immutable append-only state transition record preserving full audit history."""

    __tablename__ = "lifecycle_events"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('SURVEY', 'SURVEY_RESPONSE', 'REVIEW', 'SUPPORT_TICKET', 'SUPPORT_MESSAGE', 'ACTION_ITEM')",
            name="ck_evt_entity_type",
        ),
        CheckConstraint("sequence_no >= 1", name="ck_evt_seq"),
    )

    event_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    from_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)

