"""Service priorities, traceability, and FSM lifecycle transition route handlers."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from voc_intel.api.deps import get_priority_service
from voc_intel.api.schemas import (
    ActionItemResponse,
    ActionTraceabilityResponse,
    LifecycleEventResponse,
    TransitionRequest,
)
from voc_intel.services.priority_service import PriorityService

router = APIRouter(prefix="/priorities", tags=["priorities"])


@router.get("", response_model=list[ActionItemResponse])
def list_action_priorities(
    tier: Optional[str] = Query(default=None),
    svc: PriorityService = Depends(get_priority_service),
) -> list[ActionItemResponse]:
    return [ActionItemResponse(**row) for row in svc.list_priorities(tier=tier)]


@router.get("/{action_id}/traceability", response_model=ActionTraceabilityResponse)
def get_action_traceability(
    action_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    svc: PriorityService = Depends(get_priority_service),
) -> ActionTraceabilityResponse:
    return ActionTraceabilityResponse(**svc.get_action_traceability(action_id=action_id, limit=limit))


@router.post("/{action_id}/transition", response_model=LifecycleEventResponse)
def transition_action_item(
    action_id: str,
    payload: TransitionRequest,
    svc: PriorityService = Depends(get_priority_service),
) -> LifecycleEventResponse:
    event = svc.transition_action_item(
        action_id=action_id,
        to_state=payload.to_state,
        actor=payload.actor,
        reason=payload.reason,
    )
    return LifecycleEventResponse(**event)

