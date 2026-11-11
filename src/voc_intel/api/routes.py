"""FastAPI API routes exposing VoC priorities, shifts, traceability, anomalies, and lifecycle transitions."""

from datetime import datetime, timezone
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from voc_intel.config import settings
from voc_intel.generators.identifiers import IDGenerator
from voc_intel.models import (
    ActionItem,
    ActionItemEvidence,
    Channel,
    Customer,
    FeedbackThemeAssignment,
    LifecycleEvent,
    ModelInputFeature,
    Product,
    Review,
    SentimentLabel,
    SentimentShift,
    SupportMessage,
    SupportTicket,
    Survey,
    SurveyResponse,
    Theme,
)
from voc_intel.pipeline.lifecycle import is_valid_transition
from voc_intel.schemas.api import (
    ActionItemResponse,
    ActionTraceabilityResponse,
    DetectedAnomalyResponse,
    EvidenceItemResponse,
    HealthResponse,
    LifecycleEventResponse,
    SentimentShiftResponse,
    ThemeSummaryItem,
    TransitionRequest,
)
from voc_intel.validators.runner import detect_anomalies_in_dataset

router = APIRouter()


def get_db(request: Request) -> Session:
    """Yield a scoped SQLAlchemy session from app state."""
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


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request, db: Session = Depends(get_db)) -> HealthResponse:
    counts = {
        "customers": db.scalar(select(func.count()).select_from(Customer)) or 0,
        "products": db.scalar(select(func.count()).select_from(Product)) or 0,
        "surveys": db.scalar(select(func.count()).select_from(Survey)) or 0,
        "survey_responses": db.scalar(select(func.count()).select_from(SurveyResponse)) or 0,
        "reviews": db.scalar(select(func.count()).select_from(Review)) or 0,
        "support_messages": db.scalar(select(func.count()).select_from(SupportMessage)) or 0,
        "sentiment_shifts": db.scalar(select(func.count()).select_from(SentimentShift)) or 0,
        "action_items": db.scalar(select(func.count()).select_from(ActionItem)) or 0,
    }
    return HealthResponse(
        status="ok",
        database_url=str(request.app.state.database_url),
        record_counts=counts,
    )


@router.get("/api/v1/themes", response_model=list[ThemeSummaryItem])
def list_themes_summary(db: Session = Depends(get_db)) -> list[ThemeSummaryItem]:
    themes = db.scalars(select(Theme).order_by(Theme.theme_id)).all()
    assignments = db.scalars(
        select(FeedbackThemeAssignment).where(FeedbackThemeAssignment.theme_id.is_not(None))
    ).all()
    labels = db.scalars(select(SentimentLabel)).all()

    sent_map: dict[tuple[str, str], tuple[str, float]] = {}
    for sl in labels:
        rid = sl.response_id or sl.review_id or sl.message_id
        if rid:
            sent_map[(sl.source_type, rid)] = (sl.polarity, sl.sentiment_score)

    stats: dict[str, list[tuple[str, float]]] = {t.theme_id: [] for t in themes}
    for asn in assignments:
        rid = asn.response_id or asn.review_id or asn.message_id
        if rid and asn.theme_id in stats:
            sent = sent_map.get((asn.source_type, rid))
            if sent:
                stats[asn.theme_id].append(sent)

    results: list[ThemeSummaryItem] = []
    for t in themes:
        items = stats.get(t.theme_id, [])
        n = len(items)
        avg_s = round(sum(sc for _p, sc in items) / n, 4) if n else 0.0
        neg_c = sum(1 for pol, sc in items if pol == "NEGATIVE" or (pol == "MIXED" and sc < 0))
        results.append(
            ThemeSummaryItem(
                theme_id=t.theme_id,
                theme_code=t.theme_code,
                theme_name=t.theme_name,
                category=t.category,
                severity_weight=t.severity_weight,
                mention_count=n,
                avg_sentiment_score=avg_s,
                negative_count=neg_c,
            )
        )
    results.sort(key=lambda x: (-x.mention_count, x.theme_id))
    return results


@router.get("/api/v1/shifts", response_model=list[SentimentShiftResponse])
def list_sentiment_shifts(
    significant_only: bool = Query(default=False),
    product_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SentimentShiftResponse]:
    stmt = select(SentimentShift).order_by(SentimentShift.delta_score)
    if significant_only:
        stmt = stmt.where(SentimentShift.is_significant.is_(True))
    if product_id:
        stmt = stmt.where(SentimentShift.product_id == product_id)
    rows = db.scalars(stmt).all()
    return [
        SentimentShiftResponse(
            shift_id=r.shift_id,
            product_id=r.product_id,
            theme_id=r.theme_id,
            baseline_count=r.baseline_count,
            current_count=r.current_count,
            baseline_avg_score=r.baseline_avg_score,
            current_avg_score=r.current_avg_score,
            delta_score=r.delta_score,
            z_score=r.z_score,
            direction=r.direction,
            is_significant=r.is_significant,
        )
        for r in rows
    ]


@router.get("/api/v1/priorities", response_model=list[ActionItemResponse])
def list_action_priorities(
    tier: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ActionItemResponse]:
    stmt = select(ActionItem).order_by(ActionItem.priority_score.desc(), ActionItem.action_id)
    if tier:
        stmt = stmt.where(ActionItem.priority_tier == tier)
    rows = db.scalars(stmt).all()
    return [
        ActionItemResponse(
            action_id=a.action_id,
            product_id=a.product_id,
            theme_id=a.theme_id,
            shift_id=a.shift_id,
            title=a.title,
            recommended_action=a.recommended_action,
            owner_role=a.owner_role,
            mention_count=a.mention_count,
            negative_count=a.negative_count,
            channel_breadth=a.channel_breadth,
            negative_share=a.negative_share,
            avg_sentiment_score=a.avg_sentiment_score,
            sentiment_delta=a.sentiment_delta,
            priority_score=a.priority_score,
            priority_tier=a.priority_tier,
            lifecycle_state=a.lifecycle_state,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in rows
    ]


@router.get("/api/v1/priorities/{action_id}/traceability", response_model=ActionTraceabilityResponse)
def get_action_traceability(
    action_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ActionTraceabilityResponse:
    act = db.get(ActionItem, action_id)
    if act is None:
        raise HTTPException(status_code=404, detail=f"ActionItem '{action_id}' not found")

    total_evid = (
        db.scalar(
            select(func.count())
            .select_from(ActionItemEvidence)
            .where(ActionItemEvidence.action_id == action_id)
        )
        or 0
    )
    evid_rows = db.scalars(
        select(ActionItemEvidence)
        .where(ActionItemEvidence.action_id == action_id)
        .order_by(ActionItemEvidence.contribution_weight.desc(), ActionItemEvidence.evidence_id)
        .limit(limit)
    ).all()

    resp_ids = [ev.response_id for ev in evid_rows if ev.response_id]
    rev_ids = [ev.review_id for ev in evid_rows if ev.review_id]
    msg_ids = [ev.message_id for ev in evid_rows if ev.message_id]

    resp_texts = (
        {r.response_id: r.response_text for r in db.scalars(select(SurveyResponse).where(SurveyResponse.response_id.in_(resp_ids))).all()}
        if resp_ids
        else {}
    )
    rev_texts = (
        {r.review_id: r.review_text for r in db.scalars(select(Review).where(Review.review_id.in_(rev_ids))).all()}
        if rev_ids
        else {}
    )
    msg_texts = (
        {m.message_id: m.message_text for m in db.scalars(select(SupportMessage).where(SupportMessage.message_id.in_(msg_ids))).all()}
        if msg_ids
        else {}
    )

    sl_by_resp = (
        {s.response_id: s for s in db.scalars(select(SentimentLabel).where(SentimentLabel.response_id.in_(resp_ids))).all()}
        if resp_ids
        else {}
    )
    sl_by_rev = (
        {s.review_id: s for s in db.scalars(select(SentimentLabel).where(SentimentLabel.review_id.in_(rev_ids))).all()}
        if rev_ids
        else {}
    )
    sl_by_msg = (
        {s.message_id: s for s in db.scalars(select(SentimentLabel).where(SentimentLabel.message_id.in_(msg_ids))).all()}
        if msg_ids
        else {}
    )

    sample_evidence: list[EvidenceItemResponse] = []
    for ev in evid_rows:
        rid = ev.response_id or ev.review_id or ev.message_id or ""
        if ev.response_id:
            text_val = resp_texts.get(ev.response_id, "")
            sl = sl_by_resp.get(ev.response_id)
        elif ev.review_id:
            text_val = rev_texts.get(ev.review_id, "")
            sl = sl_by_rev.get(ev.review_id)
        else:
            text_val = msg_texts.get(ev.message_id or "", "")
            sl = sl_by_msg.get(ev.message_id or "")

        sample_evidence.append(
            EvidenceItemResponse(
                evidence_id=ev.evidence_id,
                source_type=ev.source_type,
                source_record_id=rid,
                contribution_weight=ev.contribution_weight,
                text_excerpt=text_val[:220],
                sentiment_polarity=sl.polarity if sl else None,
                sentiment_score=sl.sentiment_score if sl else None,
            )
        )

    events = db.scalars(
        select(LifecycleEvent)
        .where(
            LifecycleEvent.entity_type == "ACTION_ITEM",
            LifecycleEvent.entity_id == action_id,
        )
        .order_by(LifecycleEvent.sequence_no)
    ).all()

    return ActionTraceabilityResponse(
        action_item=ActionItemResponse(
            action_id=act.action_id,
            product_id=act.product_id,
            theme_id=act.theme_id,
            shift_id=act.shift_id,
            title=act.title,
            recommended_action=act.recommended_action,
            owner_role=act.owner_role,
            mention_count=act.mention_count,
            negative_count=act.negative_count,
            channel_breadth=act.channel_breadth,
            negative_share=act.negative_share,
            avg_sentiment_score=act.avg_sentiment_score,
            sentiment_delta=act.sentiment_delta,
            priority_score=act.priority_score,
            priority_tier=act.priority_tier,
            lifecycle_state=act.lifecycle_state,
            created_at=act.created_at,
            updated_at=act.updated_at,
        ),
        total_evidence_count=total_evid,
        sample_evidence=sample_evidence,
        lifecycle_history=[
            LifecycleEventResponse(
                event_id=e.event_id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                from_state=e.from_state,
                to_state=e.to_state,
                actor=e.actor,
                reason=e.reason,
                event_timestamp=e.event_timestamp,
                sequence_no=e.sequence_no,
            )
            for e in events
        ],
    )


@router.post("/api/v1/priorities/{action_id}/transition", response_model=LifecycleEventResponse)
def transition_action_item(
    action_id: str,
    payload: TransitionRequest,
    db: Session = Depends(get_db),
) -> LifecycleEventResponse:
    """Append a validated FSM state transition event for an ActionItem without overwriting history."""
    act = db.get(ActionItem, action_id)
    if act is None:
        raise HTTPException(status_code=404, detail=f"ActionItem '{action_id}' not found")

    if not is_valid_transition("ACTION_ITEM", act.lifecycle_state, payload.to_state):
        raise HTTPException(
            status_code=422,
            detail=f"Illegal FSM transition from '{act.lifecycle_state}' to '{payload.to_state}'",
        )

    existing_events = db.scalars(
        select(LifecycleEvent)
        .where(
            LifecycleEvent.entity_type == "ACTION_ITEM",
            LifecycleEvent.entity_id == action_id,
        )
        .order_by(LifecycleEvent.sequence_no.desc())
    ).all()
    next_seq = (existing_events[0].sequence_no + 1) if existing_events else 1
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing_events and now_utc < existing_events[0].event_timestamp:
        now_utc = existing_events[0].event_timestamp

    prefix = f"EVT-{now_utc.year:04d}-"
    max_evt_id = db.scalar(
        select(func.max(LifecycleEvent.event_id)).where(LifecycleEvent.event_id.like(f"{prefix}%"))
    )
    next_evt_num = (int(max_evt_id.split("-")[-1]) + 1) if max_evt_id else 1

    new_evt = LifecycleEvent(
        event_id=IDGenerator.lifecycle_event_id(now_utc.year, next_evt_num),
        entity_type="ACTION_ITEM",
        entity_id=action_id,
        from_state=act.lifecycle_state,
        to_state=payload.to_state,
        actor=payload.actor,
        reason=payload.reason,
        event_timestamp=now_utc,
        sequence_no=next_seq,
    )
    act.lifecycle_state = payload.to_state
    act.updated_at = now_utc
    db.add(new_evt)
    db.flush()

    return LifecycleEventResponse(
        event_id=new_evt.event_id,
        entity_type=new_evt.entity_type,
        entity_id=new_evt.entity_id,
        from_state=new_evt.from_state,
        to_state=new_evt.to_state,
        actor=new_evt.actor,
        reason=new_evt.reason,
        event_timestamp=new_evt.event_timestamp,
        sequence_no=new_evt.sequence_no,
    )


@router.get("/api/v1/anomalies", response_model=list[DetectedAnomalyResponse])
def list_detected_anomalies(db: Session = Depends(get_db)) -> list[DetectedAnomalyResponse]:
    """Run live anomaly detectors against database tables and expose exceptions."""
    tables = {
        "themes": [
            {"theme_id": t.theme_id, "theme_code": t.theme_code, "is_active": t.is_active}
            for t in db.scalars(select(Theme)).all()
        ],
        "survey_responses": [
            {
                "response_id": r.response_id,
                "survey_id": r.survey_id,
                "customer_id": r.customer_id,
                "response_text": r.response_text,
                "language": r.language,
                "normalized_score": r.normalized_score,
                "submitted_at": r.submitted_at,
                "content_hash": r.content_hash,
            }
            for r in db.scalars(select(SurveyResponse)).all()
        ],
        "reviews": [
            {
                "review_id": rev.review_id,
                "product_id": rev.product_id,
                "customer_id": rev.customer_id,
                "review_text": rev.review_text,
                "language": rev.language,
                "star_rating": rev.star_rating,
                "published_at": rev.published_at,
                "content_hash": rev.content_hash,
            }
            for rev in db.scalars(select(Review)).all()
        ],
        "support_messages": [
            {
                "message_id": m.message_id,
                "message_text": m.message_text,
                "language": m.language,
            }
            for m in db.scalars(select(SupportMessage)).all()
        ],
        "sentiment_labels": [
            {
                "label_id": s.label_id,
                "response_id": s.response_id,
                "review_id": s.review_id,
                "message_id": s.message_id,
                "polarity": s.polarity,
                "labeling_method": s.labeling_method,
                "rationale": s.rationale,
            }
            for s in db.scalars(select(SentimentLabel)).all()
        ],
        "feedback_theme_assignments": [
            {
                "assignment_id": a.assignment_id,
                "response_id": a.response_id,
                "review_id": a.review_id,
                "message_id": a.message_id,
                "theme_id": a.theme_id,
                "raw_theme_code": a.raw_theme_code,
            }
            for a in db.scalars(select(FeedbackThemeAssignment)).all()
        ],
        "model_inputs": [
            {
                "input_id": mi.input_id,
                "response_id": mi.response_id,
                "review_id": mi.review_id,
                "message_id": mi.message_id,
                "split_partition": mi.split_partition,
                "text_payload": mi.text_payload,
                "extra_features_json": mi.extra_features_json,
            }
            for mi in db.scalars(select(ModelInputFeature)).all()
        ],
    }
    findings = detect_anomalies_in_dataset(tables)
    return [DetectedAnomalyResponse(**f) for f in findings]


@router.get("/api/v1/reports/{report_name}")
def get_report(report_name: str, request: Request) -> dict[str, Any]:
    allowed = {
        "validation": "validation_report.json",
        "evaluation": "evaluation_metrics.json",
    }
    if report_name not in allowed:
        raise HTTPException(status_code=404, detail="Report not found; use 'validation' or 'evaluation'")
    exports_dir = getattr(request.app.state, "exports_dir", settings.exports_dir)
    path = exports_dir / "reports" / allowed[report_name]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Report '{path}' has not been generated yet")
    return json.loads(path.read_text(encoding="utf-8"))

