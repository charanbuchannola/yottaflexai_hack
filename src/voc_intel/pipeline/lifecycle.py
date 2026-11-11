"""Finite State Machine (FSM) definitions and event-log state replay projection."""

from collections import defaultdict
from typing import Any

from voc_intel.models.base import (
    ActionLifecycleState,
    FeedbackLifecycleState,
    SurveyLifecycleState,
    TicketLifecycleState,
)

# Legal FSM transitions per entity_type: from_state -> allowed to_states
FSM_TRANSITIONS: dict[str, dict[str | None, frozenset[str]]] = {
    "SURVEY": {
        None: frozenset({SurveyLifecycleState.DRAFT.value}),
        SurveyLifecycleState.DRAFT.value: frozenset({SurveyLifecycleState.ACTIVE.value}),
        SurveyLifecycleState.ACTIVE.value: frozenset(
            {SurveyLifecycleState.CLOSED.value, SurveyLifecycleState.ARCHIVED.value}
        ),
        SurveyLifecycleState.CLOSED.value: frozenset({SurveyLifecycleState.ARCHIVED.value}),
    },
    "SURVEY_RESPONSE": {
        None: frozenset({FeedbackLifecycleState.SUBMITTED.value}),
        FeedbackLifecycleState.SUBMITTED.value: frozenset(
            {FeedbackLifecycleState.ANALYZED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.ANALYZED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.VERIFIED.value: frozenset(
            {FeedbackLifecycleState.FLAGGED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
        FeedbackLifecycleState.FLAGGED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
    },
    "REVIEW": {
        None: frozenset({FeedbackLifecycleState.SUBMITTED.value}),
        FeedbackLifecycleState.SUBMITTED.value: frozenset(
            {FeedbackLifecycleState.ANALYZED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.ANALYZED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.VERIFIED.value: frozenset(
            {FeedbackLifecycleState.FLAGGED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
        FeedbackLifecycleState.FLAGGED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
    },
    "SUPPORT_TICKET": {
        None: frozenset({TicketLifecycleState.OPEN.value}),
        TicketLifecycleState.OPEN.value: frozenset({TicketLifecycleState.TRIAGED.value}),
        TicketLifecycleState.TRIAGED.value: frozenset({TicketLifecycleState.IN_PROGRESS.value}),
        TicketLifecycleState.IN_PROGRESS.value: frozenset(
            {TicketLifecycleState.ESCALATED.value, TicketLifecycleState.RESOLVED.value}
        ),
        TicketLifecycleState.ESCALATED.value: frozenset({TicketLifecycleState.RESOLVED.value}),
        TicketLifecycleState.RESOLVED.value: frozenset({TicketLifecycleState.CLOSED.value}),
    },
    "SUPPORT_MESSAGE": {
        None: frozenset({FeedbackLifecycleState.SUBMITTED.value}),
        FeedbackLifecycleState.SUBMITTED.value: frozenset(
            {FeedbackLifecycleState.ANALYZED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.ANALYZED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.FLAGGED.value}
        ),
        FeedbackLifecycleState.VERIFIED.value: frozenset(
            {FeedbackLifecycleState.FLAGGED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
        FeedbackLifecycleState.FLAGGED.value: frozenset(
            {FeedbackLifecycleState.VERIFIED.value, FeedbackLifecycleState.QUARANTINED.value}
        ),
    },
    "ACTION_ITEM": {
        None: frozenset({ActionLifecycleState.IDENTIFIED.value}),
        ActionLifecycleState.IDENTIFIED.value: frozenset({ActionLifecycleState.TRIAGED.value}),
        ActionLifecycleState.TRIAGED.value: frozenset(
            {ActionLifecycleState.IN_PROGRESS.value, ActionLifecycleState.ESCALATED.value}
        ),
        ActionLifecycleState.ESCALATED.value: frozenset(
            {ActionLifecycleState.IN_PROGRESS.value, ActionLifecycleState.VERIFIED.value}
        ),
        ActionLifecycleState.IN_PROGRESS.value: frozenset({ActionLifecycleState.VERIFIED.value}),
        ActionLifecycleState.VERIFIED.value: frozenset({ActionLifecycleState.CLOSED.value}),
    },
}


def is_valid_transition(entity_type: str, from_state: str | None, to_state: str) -> bool:
    """Return True if the FSM permits transitioning from from_state to to_state."""
    rules = FSM_TRANSITIONS.get(entity_type)
    if rules is None:
        return False
    allowed = rules.get(from_state, frozenset())
    return to_state in allowed


def replay_entity_states(
    events: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], str], list[str]]:
    """Replay append-only lifecycle events in sequence order and report any violations."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for evt in events:
        grouped[(evt["entity_type"], evt["entity_id"])].append(evt)

    final_states: dict[tuple[str, str], str] = {}
    violations: list[str] = []

    for (entity_type, entity_id), chain in grouped.items():
        chain.sort(key=lambda e: (e["sequence_no"], e["event_timestamp"]))
        current_state: str | None = None
        prev_ts = None
        expected_seq = 1

        for evt in chain:
            if evt["sequence_no"] != expected_seq:
                violations.append(
                    f"{entity_type}:{entity_id} non-sequential sequence_no {evt['sequence_no']} != {expected_seq}"
                )
            if evt["from_state"] != current_state:
                violations.append(
                    f"{entity_type}:{entity_id} broken state chain from_state={evt['from_state']} != {current_state}"
                )
            if not is_valid_transition(entity_type, evt["from_state"], evt["to_state"]):
                violations.append(
                    f"{entity_type}:{entity_id} illegal FSM transition {evt['from_state']} -> {evt['to_state']}"
                )
            if prev_ts is not None and evt["event_timestamp"] < prev_ts:
                violations.append(
                    f"{entity_type}:{entity_id} non-monotonic event timestamp"
                )
            current_state = evt["to_state"]
            prev_ts = evt["event_timestamp"]
            expected_seq += 1

        if current_state is not None:
            final_states[(entity_type, entity_id)] = current_state

    return final_states, violations

