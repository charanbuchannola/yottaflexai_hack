"""Composite API v1 router aggregating feature-level route modules."""

from fastapi import APIRouter

from voc_intel.api.v1 import anomalies, priorities, reports, shifts, themes

api_v1_router = APIRouter()
api_v1_router.include_router(themes.router)
api_v1_router.include_router(shifts.router)
api_v1_router.include_router(priorities.router)
api_v1_router.include_router(anomalies.router)
api_v1_router.include_router(reports.router)

