"""Analytical, bridge, derived priority, and model-input ORM models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from voc_intel.models.base import (
    ActionLifecycleState,
    Base,
    ChannelGroup,
    FeedbackLifecycleState,
    FeedbackSourceType,
    LabelingMethod,
    LanguageCode,
    PriorityTier,
    SentimentPolarity,
    ShiftDirection,
)

_EXACT_ONE_FEEDBACK_CK = (
    "(CASE WHEN response_id IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN review_id IS NOT NULL THEN 1 ELSE 0 END + "
    "CASE WHEN message_id IS NOT NULL THEN 1 ELSE 0 END) = 1"
)


class SentimentLabel(Base):
    """1:1 operational sentiment assessment attached to each feedback record."""

    __tablename__ = "sentiment_labels"
    __table_args__ = (
        CheckConstraint(_EXACT_ONE_FEEDBACK_CK, name="ck_sent_exact_one_parent"),
        CheckConstraint(
            f"source_type IN ({','.join(repr(e.value) for e in FeedbackSourceType)})",
            name="ck_sent_source_type",
        ),
        CheckConstraint(
            f"polarity IN ({','.join(repr(e.value) for e in SentimentPolarity)})",
            name="ck_sent_polarity",
        ),
        CheckConstraint("sentiment_score >= -1.0 AND sentiment_score <= 1.0", name="ck_sent_score"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_sent_conf"),
        CheckConstraint(
            f"labeling_method IN ({','.join(repr(e.value) for e in LabelingMethod)})",
            name="ck_sent_method",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in FeedbackLifecycleState)})",
            name="ck_sent_state",
        ),
    )

    label_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    response_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("survey_responses.response_id"), unique=True, nullable=True
    )
    review_id: Mapped[Optional[str]] = mapped_column(
        String(24), ForeignKey("reviews.review_id"), unique=True, nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("support_messages.message_id"), unique=True, nullable=True
    )
    polarity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    labeling_method: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labeled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False)


class FeedbackThemeAssignment(Base):
    """N:M bridge table linking feedback records to Themes."""

    __tablename__ = "feedback_theme_assignments"
    __table_args__ = (
        CheckConstraint(_EXACT_ONE_FEEDBACK_CK, name="ck_thm_asn_exact_one_parent"),
        CheckConstraint(
            f"source_type IN ({','.join(repr(e.value) for e in FeedbackSourceType)})",
            name="ck_thm_asn_source_type",
        ),
        CheckConstraint(
            "relevance_score >= 0.0 AND relevance_score <= 1.0", name="ck_thm_asn_rel"
        ),
        CheckConstraint(
            f"assignment_method IN ({','.join(repr(e.value) for e in LabelingMethod)})",
            name="ck_thm_asn_method",
        ),
    )

    assignment_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    response_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("survey_responses.response_id"), nullable=True, index=True
    )
    review_id: Mapped[Optional[str]] = mapped_column(
        String(24), ForeignKey("reviews.review_id"), nullable=True, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("support_messages.message_id"), nullable=True, index=True
    )
    theme_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("themes.theme_id"), nullable=True, index=True
    )
    raw_theme_code: Mapped[str] = mapped_column(String(64), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    assignment_method: Mapped[str] = mapped_column(String(24), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SentimentShift(Base):
    """Derived temporal sentiment shift cohort computed strictly from source records."""

    __tablename__ = "sentiment_shifts"
    __table_args__ = (
        CheckConstraint(
            f"channel_group IS NULL OR channel_group IN ({','.join(repr(e.value) for e in ChannelGroup)})",
            name="ck_shift_channel_group",
        ),
        CheckConstraint(
            f"direction IN ({','.join(repr(e.value) for e in ShiftDirection)})",
            name="ck_shift_dir",
        ),
        CheckConstraint("baseline_end >= baseline_start", name="ck_shift_base_dates"),
        CheckConstraint("current_end >= current_start", name="ck_shift_curr_dates"),
        CheckConstraint("current_start >= baseline_start", name="ck_shift_order"),
        CheckConstraint("baseline_count >= 0 AND current_count >= 0", name="ck_shift_counts"),
    )

    shift_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    product_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=True, index=True
    )
    theme_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("themes.theme_id"), nullable=True, index=True
    )
    channel_group: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    baseline_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    baseline_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    baseline_count: Mapped[int] = mapped_column(Integer, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_avg_score: Mapped[float] = mapped_column(Float, nullable=False)
    current_avg_score: Mapped[float] = mapped_column(Float, nullable=False)
    delta_score: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    is_significant: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ActionItem(Base):
    """Service priority action item derived deterministically from recurring themes & shifts."""

    __tablename__ = "action_items"
    __table_args__ = (
        CheckConstraint(
            f"priority_tier IN ({','.join(repr(e.value) for e in PriorityTier)})",
            name="ck_act_tier",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in ActionLifecycleState)})",
            name="ck_act_state",
        ),
        CheckConstraint("priority_score >= 0.0 AND priority_score <= 100.0", name="ck_act_prio"),
        CheckConstraint("mention_count >= 1", name="ck_act_mentions"),
        CheckConstraint("negative_count >= 0 AND negative_count <= mention_count", name="ck_act_neg"),
        CheckConstraint("updated_at >= created_at", name="ck_act_dates"),
    )

    action_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    product_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=True, index=True
    )
    theme_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("themes.theme_id"), nullable=False, index=True
    )
    shift_id: Mapped[Optional[str]] = mapped_column(
        String(24), ForeignKey("sentiment_shifts.shift_id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(64), nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_breadth: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_share: Mapped[float] = mapped_column(Float, nullable=False)
    avg_sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_delta: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    priority_tier: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ActionItemEvidence(Base):
    """N:M traceability bridge table linking ActionItems back to exact source feedback records."""

    __tablename__ = "action_item_evidence"
    __table_args__ = (
        CheckConstraint(_EXACT_ONE_FEEDBACK_CK, name="ck_evid_exact_one_parent"),
        CheckConstraint(
            f"source_type IN ({','.join(repr(e.value) for e in FeedbackSourceType)})",
            name="ck_evid_source_type",
        ),
        CheckConstraint("contribution_weight > 0.0 AND contribution_weight <= 1.0", name="ck_evid_wt"),
    )

    evidence_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    action_id: Mapped[str] = mapped_column(
        String(24), ForeignKey("action_items.action_id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    response_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("survey_responses.response_id"), nullable=True, index=True
    )
    review_id: Mapped[Optional[str]] = mapped_column(
        String(24), ForeignKey("reviews.review_id"), nullable=True, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("support_messages.message_id"), nullable=True, index=True
    )
    contribution_weight: Mapped[float] = mapped_column(Float, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ModelInputFeature(Base):
    """Sanitized operational feature table fed into NLP/scoring models (zero ground-truth leakage)."""

    __tablename__ = "model_inputs"
    __table_args__ = (
        CheckConstraint(_EXACT_ONE_FEEDBACK_CK, name="ck_inp_exact_one_parent"),
        CheckConstraint(
            f"source_type IN ({','.join(repr(e.value) for e in FeedbackSourceType)})",
            name="ck_inp_source_type",
        ),
        CheckConstraint(
            f"language IN ({','.join(repr(e.value) for e in LanguageCode)})",
            name="ck_inp_lang",
        ),
        CheckConstraint(
            "split_partition IN ('TRAIN', 'INFERENCE', 'TEST')",
            name="ck_inp_split",
        ),
        UniqueConstraint("response_id", name="uq_inp_resp"),
        UniqueConstraint("review_id", name="uq_inp_rev"),
        UniqueConstraint("message_id", name="uq_inp_msg"),
    )

    input_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    response_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("survey_responses.response_id"), nullable=True
    )
    review_id: Mapped[Optional[str]] = mapped_column(
        String(24), ForeignKey("reviews.review_id"), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("support_messages.message_id"), nullable=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    text_payload: Mapped[str] = mapped_column(Text, nullable=False)
    rating_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    split_partition: Mapped[str] = mapped_column(String(16), nullable=False)
    extra_features_json: Mapped[str] = mapped_column(Text, nullable=False)

