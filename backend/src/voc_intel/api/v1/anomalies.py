"""Anomaly audit route handler (delegates strictly to AnomalyService)."""

from fastapi import APIRouter, Depends

from voc_intel.api.deps import get_anomaly_service
from voc_intel.api.schemas import DetectedAnomalyResponse
from voc_intel.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[DetectedAnomalyResponse])
def list_detected_anomalies(
    svc: AnomalyService = Depends(get_anomaly_service),
) -> list[DetectedAnomalyResponse]:
    return [DetectedAnomalyResponse(**row) for row in svc.detect_live_anomalies()]

