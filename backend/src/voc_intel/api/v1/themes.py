"""Themes route handler (delegates strictly to FeedbackService)."""

from fastapi import APIRouter, Depends

from voc_intel.api.deps import get_feedback_service
from voc_intel.api.schemas import ThemeSummaryItem
from voc_intel.services.feedback_service import FeedbackService

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("", response_model=list[ThemeSummaryItem])
def list_themes_summary(
    svc: FeedbackService = Depends(get_feedback_service),
) -> list[ThemeSummaryItem]:
    return [ThemeSummaryItem(**item) for item in svc.get_theme_summaries()]

