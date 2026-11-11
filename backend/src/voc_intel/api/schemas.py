"""Pydantic v2 request and response contracts for the VoC Intelligence API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database_url: str
    record_counts: dict[str, int]


class ThemeSummaryItem(BaseModel):
    theme_id: str
    theme_code: str
    theme_name: str
    category: str
    severity_weight: float
    mention_count: int
    avg_sentiment_score: float
    negative_count: int


class SentimentShiftResponse(BaseModel):
    shift_id: str
    product_id: Optional[str]
    theme_id: Optional[str]
    baseline_count: int
    current_count: int
    baseline_avg_score: float
    current_avg_score: float
    delta_score: float
    z_score: float
    direction: str
    is_significant: bool


class ActionItemResponse(BaseModel):
    action_id: str
    product_id: Optional[str]
    theme_id: str
    shift_id: Optional[str]
    title: str
    recommended_action: str
    owner_role: str
    mention_count: int
    negative_count: int
    channel_breadth: int
    negative_share: float
    avg_sentiment_score: float
    sentiment_delta: float
    priority_score: float
    priority_tier: str
    lifecycle_state: str
    created_at: datetime
    updated_at: datetime


class EvidenceItemResponse(BaseModel):
    evidence_id: str
    source_type: str
    source_record_id: str
    contribution_weight: float
    text_excerpt: str
    sentiment_polarity: Optional[str]
    sentiment_score: Optional[float]


class LifecycleEventResponse(BaseModel):
    event_id: str
    entity_type: str
    entity_id: str
    from_state: Optional[str]
    to_state: str
    actor: str
    reason: str
    event_timestamp: datetime
    sequence_no: int


class ActionTraceabilityResponse(BaseModel):
    action_item: ActionItemResponse
    total_evidence_count: int
    sample_evidence: list[EvidenceItemResponse]
    lifecycle_history: list[LifecycleEventResponse]


class TransitionRequest(BaseModel):
    to_state: str = Field(..., description="Target lifecycle state")
    actor: str = Field(..., min_length=2, max_length=64)
    reason: str = Field(..., min_length=3, max_length=500)


class DetectedAnomalyResponse(BaseModel):
    issue_type: str
    rule_id: str
    target_table: str
    target_record_id: str
    source_record_id: str

