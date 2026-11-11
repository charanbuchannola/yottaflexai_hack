"""Validation and evaluation report route handler (delegates strictly to ReportService)."""

from typing import Any

from fastapi import APIRouter, Depends

from voc_intel.api.deps import get_report_service
from voc_intel.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_name}")
def get_report(
    report_name: str,
    svc: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    return svc.get_report(report_name)

