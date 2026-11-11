"""Transactional feedback entities: SurveyResponse, Review, SupportTicket, SupportMessage."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from voc_intel.db.base import (
    Base,
    FeedbackLifecycleState,
    LanguageCode,
    SenderRole,
    TicketLifecycleState,
    TicketPriority,
)


class SurveyResponse(Base):
    """Customer survey response linked to a Survey, Customer, optional Product, and Channel."""

    __tablename__ = "survey_responses"
    __table_args__ = (
        CheckConstraint(
            f"language IN ({','.join(repr(e.value) for e in LanguageCode)})",
            name="ck_resp_lang",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in FeedbackLifecycleState)})",
            name="ck_resp_state",
        ),
        CheckConstraint("rating_score >= 0 AND rating_score <= 10", name="ck_resp_rating"),
        CheckConstraint(
            "normalized_score >= 0.0 AND normalized_score <= 1.0", name="ck_resp_norm"
        ),
    )

    response_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    survey_id: Mapped[str] = mapped_column(
        String(24), ForeignKey("surveys.survey_id"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=True, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False, index=True
    )
    rating_score: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class Review(Base):
    """Public or store product review (customer_id optional for anonymous web reviews)."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            f"language IN ({','.join(repr(e.value) for e in LanguageCode)})",
            name="ck_rev_lang",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in FeedbackLifecycleState)})",
            name="ck_rev_state",
        ),
        CheckConstraint("star_rating >= 1 AND star_rating <= 5", name="ck_rev_stars"),
        CheckConstraint("helpful_votes >= 0", name="ck_rev_votes"),
    )

    review_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("customers.customer_id"), nullable=True, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False, index=True
    )
    star_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False)
    helpful_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class SupportTicket(Base):
    """Parent support ticket container ensuring full referential integrity for MSG-<ticket-id>-001."""

    __tablename__ = "support_tickets"
    __table_args__ = (
        CheckConstraint(
            f"priority IN ({','.join(repr(e.value) for e in TicketPriority)})",
            name="ck_tkt_priority",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in TicketLifecycleState)})",
            name="ck_tkt_state",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= opened_at",
            name="ck_tkt_dates",
        ),
        CheckConstraint("message_count >= 0", name="ck_tkt_msg_count"),
    )

    ticket_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SupportMessage(Base):
    """Individual support message belonging to a SupportTicket."""

    __tablename__ = "support_messages"
    __table_args__ = (
        CheckConstraint(
            f"sender_role IN ({','.join(repr(e.value) for e in SenderRole)})",
            name="ck_msg_sender",
        ),
        CheckConstraint(
            f"language IN ({','.join(repr(e.value) for e in LanguageCode)})",
            name="ck_msg_lang",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in FeedbackLifecycleState)})",
            name="ck_msg_state",
        ),
        CheckConstraint("sequence_no >= 1", name="ck_msg_seq"),
    )

    message_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(24), ForeignKey("support_tickets.ticket_id"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False, index=True
    )
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

