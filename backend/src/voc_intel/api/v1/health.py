"""Health check route handler (delegates strictly to FeedbackService)."""

from fastapi import APIRouter, Depends, Request

from voc_intel.api.deps import get_feedback_service
from voc_intel.api.schemas import HealthResponse
from voc_intel.services.feedback_service import FeedbackService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    request: Request,
    svc: FeedbackService = Depends(get_feedback_service),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        database_url=str(request.app.state.database_url),
        record_counts=svc.get_health_counts(),
    )

