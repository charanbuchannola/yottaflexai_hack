"""Repository for ActionItem, ActionItemEvidence, and append-only LifecycleEvent persistence."""

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select

from voc_intel.core.identifiers import IDGenerator
from voc_intel.db import ActionItem, ActionItemEvidence, LifecycleEvent
from voc_intel.repositories.base import BaseRepository


class PriorityRepository(BaseRepository):
    """Data-access methods for service priorities, source evidence, and lifecycle audit events."""

    def count_action_items(self) -> int:
        return self.session.scalar(select(func.count()).select_from(ActionItem)) or 0

    def list_action_items(self, tier: Optional[str] = None) -> Sequence[ActionItem]:
        stmt = select(ActionItem).order_by(ActionItem.priority_score.desc(), ActionItem.action_id)
        if tier:
            stmt = stmt.where(ActionItem.priority_tier == tier)
        return self.session.scalars(stmt).all()

    def get_action_item(self, action_id: str) -> Optional[ActionItem]:
        return self.session.get(ActionItem, action_id)

    def count_evidence(self, action_id: str) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(ActionItemEvidence)
                .where(ActionItemEvidence.action_id == action_id)
            )
            or 0
        )

    def list_evidence(self, action_id: str, limit: int) -> Sequence[ActionItemEvidence]:
        return self.session.scalars(
            select(ActionItemEvidence)
            .where(ActionItemEvidence.action_id == action_id)
            .order_by(ActionItemEvidence.contribution_weight.desc(), ActionItemEvidence.evidence_id)
            .limit(limit)
        ).all()

    def list_lifecycle_events(self, entity_type: str, entity_id: str) -> Sequence[LifecycleEvent]:
        return self.session.scalars(
            select(LifecycleEvent)
            .where(
                LifecycleEvent.entity_type == entity_type,
                LifecycleEvent.entity_id == entity_id,
            )
            .order_by(LifecycleEvent.sequence_no)
        ).all()

    def append_action_transition_event(
        self,
        action: ActionItem,
        to_state: str,
        actor: str,
        reason: str,
        event_ts: datetime,
    ) -> LifecycleEvent:
        existing_events = self.list_lifecycle_events("ACTION_ITEM", action.action_id)
        next_seq = (existing_events[-1].sequence_no + 1) if existing_events else 1
        effective_ts = (
            existing_events[-1].event_timestamp
            if existing_events and event_ts < existing_events[-1].event_timestamp
            else event_ts
        )

        prefix = f"EVT-{effective_ts.year:04d}-"
        max_evt_id = self.session.scalar(
            select(func.max(LifecycleEvent.event_id)).where(
                LifecycleEvent.event_id.like(f"{prefix}%")
            )
        )
        next_evt_num = (int(max_evt_id.split("-")[-1]) + 1) if max_evt_id else 1

        new_evt = LifecycleEvent(
            event_id=IDGenerator.lifecycle_event_id(effective_ts.year, next_evt_num),
            entity_type="ACTION_ITEM",
            entity_id=action.action_id,
            from_state=action.lifecycle_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            event_timestamp=effective_ts,
            sequence_no=next_seq,
        )
        action.lifecycle_state = to_state
        action.updated_at = effective_ts
        self.session.add(new_evt)
        self.session.flush()
        return new_evt

