"""Service layer for prioritized ActionItems, evidence traceability, and FSM transitions."""

from datetime import datetime, timezone
from typing import Any, Optional

from voc_intel.core.exceptions import InvalidStateTransitionError, ResourceNotFoundError
from voc_intel.features.lifecycle.fsm import is_valid_transition
from voc_intel.repositories.analytics_repo import AnalyticsRepository
from voc_intel.repositories.feedback_repo import FeedbackRepository
from voc_intel.repositories.priority_repo import PriorityRepository


class PriorityService:
    """Manages prioritized remediation actions, evidence drill-down, and append-only state changes."""

    def __init__(
        self,
        priority_repo: PriorityRepository,
        feedback_repo: FeedbackRepository,
        analytics_repo: AnalyticsRepository,
    ) -> None:
        self.priority_repo = priority_repo
        self.feedback_repo = feedback_repo
        self.analytics_repo = analytics_repo

    def list_priorities(self, tier: Optional[str] = None) -> list[dict[str, Any]]:
        rows = self.priority_repo.list_action_items(tier=tier)
        return [
            {
                "action_id": a.action_id,
                "product_id": a.product_id,
                "theme_id": a.theme_id,
                "shift_id": a.shift_id,
                "title": a.title,
                "recommended_action": a.recommended_action,
                "owner_role": a.owner_role,
                "mention_count": a.mention_count,
                "negative_count": a.negative_count,
                "channel_breadth": a.channel_breadth,
                "negative_share": a.negative_share,
                "avg_sentiment_score": a.avg_sentiment_score,
                "sentiment_delta": a.sentiment_delta,
                "priority_score": a.priority_score,
                "priority_tier": a.priority_tier,
                "lifecycle_state": a.lifecycle_state,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            for a in rows
        ]

    def get_action_traceability(self, action_id: str, limit: int = 20) -> dict[str, Any]:
        act = self.priority_repo.get_action_item(action_id)
        if act is None:
            raise ResourceNotFoundError(f"ActionItem '{action_id}' not found")

        total_evid = self.priority_repo.count_evidence(action_id)
        evid_rows = self.priority_repo.list_evidence(action_id, limit=limit)

        resp_ids = [ev.response_id for ev in evid_rows if ev.response_id]
        rev_ids = [ev.review_id for ev in evid_rows if ev.review_id]
        msg_ids = [ev.message_id for ev in evid_rows if ev.message_id]

        resp_texts = self.feedback_repo.get_response_texts_by_ids(resp_ids)
        rev_texts = self.feedback_repo.get_review_texts_by_ids(rev_ids)
        msg_texts = self.feedback_repo.get_message_texts_by_ids(msg_ids)

        sl_by_resp, sl_by_rev, sl_by_msg = self.analytics_repo.get_labels_by_parent_ids(
            response_ids=resp_ids,
            review_ids=rev_ids,
            message_ids=msg_ids,
        )

        sample_evidence: list[dict[str, Any]] = []
        for ev in evid_rows:
            rid = ev.response_id or ev.review_id or ev.message_id or ""
            if ev.response_id:
                text_val = resp_texts.get(ev.response_id, "")
                sl = sl_by_resp.get(ev.response_id)
            elif ev.review_id:
                text_val = rev_texts.get(ev.review_id, "")
                sl = sl_by_rev.get(ev.review_id)
            else:
                text_val = msg_texts.get(ev.message_id or "", "")
                sl = sl_by_msg.get(ev.message_id or "")

            sample_evidence.append(
                {
                    "evidence_id": ev.evidence_id,
                    "source_type": ev.source_type,
                    "source_record_id": rid,
                    "contribution_weight": ev.contribution_weight,
                    "text_excerpt": text_val[:220],
                    "sentiment_polarity": sl.polarity if sl else None,
                    "sentiment_score": sl.sentiment_score if sl else None,
                }
            )

        events = self.priority_repo.list_lifecycle_events("ACTION_ITEM", action_id)
        return {
            "action_item": {
                "action_id": act.action_id,
                "product_id": act.product_id,
                "theme_id": act.theme_id,
                "shift_id": act.shift_id,
                "title": act.title,
                "recommended_action": act.recommended_action,
                "owner_role": act.owner_role,
                "mention_count": act.mention_count,
                "negative_count": act.negative_count,
                "channel_breadth": act.channel_breadth,
                "negative_share": act.negative_share,
                "avg_sentiment_score": act.avg_sentiment_score,
                "sentiment_delta": act.sentiment_delta,
                "priority_score": act.priority_score,
                "priority_tier": act.priority_tier,
                "lifecycle_state": act.lifecycle_state,
                "created_at": act.created_at,
                "updated_at": act.updated_at,
            },
            "total_evidence_count": total_evid,
            "sample_evidence": sample_evidence,
            "lifecycle_history": [
                {
                    "event_id": e.event_id,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "from_state": e.from_state,
                    "to_state": e.to_state,
                    "actor": e.actor,
                    "reason": e.reason,
                    "event_timestamp": e.event_timestamp,
                    "sequence_no": e.sequence_no,
                }
                for e in events
            ],
        }

    def transition_action_item(
        self,
        action_id: str,
        to_state: str,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        act = self.priority_repo.get_action_item(action_id)
        if act is None:
            raise ResourceNotFoundError(f"ActionItem '{action_id}' not found")

        if not is_valid_transition("ACTION_ITEM", act.lifecycle_state, to_state):
            raise InvalidStateTransitionError(
                f"Illegal FSM transition from '{act.lifecycle_state}' to '{to_state}'"
            )

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        evt = self.priority_repo.append_action_transition_event(
            action=act,
            to_state=to_state,
            actor=actor,
            reason=reason,
            event_ts=now_utc,
        )
        return {
            "event_id": evt.event_id,
            "entity_type": evt.entity_type,
            "entity_id": evt.entity_id,
            "from_state": evt.from_state,
            "to_state": evt.to_state,
            "actor": evt.actor,
            "reason": evt.reason,
            "event_timestamp": evt.event_timestamp,
            "sequence_no": evt.sequence_no,
        }

