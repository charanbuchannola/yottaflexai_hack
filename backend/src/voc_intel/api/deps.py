"""FastAPI dependency injection providers wiring Repositories into Services."""

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from voc_intel.core.config import settings
from voc_intel.repositories.analytics_repo import AnalyticsRepository
from voc_intel.repositories.feedback_repo import FeedbackRepository
from voc_intel.repositories.priority_repo import PriorityRepository
from voc_intel.services.anomaly_service import AnomalyService
from voc_intel.services.feedback_service import FeedbackService
from voc_intel.services.priority_service import PriorityService
from voc_intel.services.report_service import ReportService
from voc_intel.services.shift_service import ShiftService


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a transactional SQLAlchemy session from application state."""
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_feedback_service(db: Session = Depends(get_db_session)) -> FeedbackService:
    return FeedbackService(
        feedback_repo=FeedbackRepository(db),
        analytics_repo=AnalyticsRepository(db),
        priority_repo=PriorityRepository(db),
    )


def get_shift_service(db: Session = Depends(get_db_session)) -> ShiftService:
    return ShiftService(analytics_repo=AnalyticsRepository(db))


def get_priority_service(db: Session = Depends(get_db_session)) -> PriorityService:
    return PriorityService(
        priority_repo=PriorityRepository(db),
        feedback_repo=FeedbackRepository(db),
        analytics_repo=AnalyticsRepository(db),
    )


def get_anomaly_service(db: Session = Depends(get_db_session)) -> AnomalyService:
    return AnomalyService(
        feedback_repo=FeedbackRepository(db),
        analytics_repo=AnalyticsRepository(db),
    )


def get_report_service(request: Request) -> ReportService:
    exports_dir = getattr(request.app.state, "exports_dir", settings.exports_dir)
    return ReportService(exports_dir=exports_dir)

