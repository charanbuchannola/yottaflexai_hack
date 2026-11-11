"""Sentiment shifts route handler (delegates strictly to ShiftService)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from voc_intel.api.deps import get_shift_service
from voc_intel.api.schemas import SentimentShiftResponse
from voc_intel.services.shift_service import ShiftService

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("", response_model=list[SentimentShiftResponse])
def list_sentiment_shifts(
    significant_only: bool = Query(default=False),
    product_id: Optional[str] = Query(default=None),
    svc: ShiftService = Depends(get_shift_service),
) -> list[SentimentShiftResponse]:
    rows = svc.list_shifts(significant_only=significant_only, product_id=product_id)
    return [SentimentShiftResponse(**row) for row in rows]

