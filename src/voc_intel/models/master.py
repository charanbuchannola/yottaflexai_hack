"""Master and taxonomy relational ORM models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voc_intel.models.base import (
    AccountTier,
    Base,
    ChannelGroup,
    CustomerLifecycleState,
    CustomerSegment,
    LanguageCode,
    ProductCategory,
    ProductLifecycleState,
    Region,
    SurveyLifecycleState,
    SurveyType,
    ThemeCategory,
)


class Customer(Base):
    """Pseudonymized customer/prospect master entity (zero PII)."""

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            f"account_tier IN ({','.join(repr(e.value) for e in AccountTier)})",
            name="ck_customer_tier",
        ),
        CheckConstraint(
            f"segment IN ({','.join(repr(e.value) for e in CustomerSegment)})",
            name="ck_customer_segment",
        ),
        CheckConstraint(
            f"region IN ({','.join(repr(e.value) for e in Region)})",
            name="ck_customer_region",
        ),
        CheckConstraint(
            f"preferred_language IN ({','.join(repr(e.value) for e in LanguageCode)})",
            name="ck_customer_lang",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in CustomerLifecycleState)})",
            name="ck_customer_state",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_customer_dates",
        ),
    )

    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    pseudonym_handle: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    account_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    segment: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(8), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Product(Base):
    """Product catalog entity."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            f"category IN ({','.join(repr(e.value) for e in ProductCategory)})",
            name="ck_product_category",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in ProductLifecycleState)})",
            name="ck_product_state",
        ),
        CheckConstraint("support_sla_hours > 0", name="ck_product_sla"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_product_dates",
        ),
    )

    product_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    release_version: Mapped[str] = mapped_column(String(24), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False)
    support_sla_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Channel(Base):
    """Feedback intake channel taxonomy entity."""

    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint(
            f"channel_group IN ({','.join(repr(e.value) for e in ChannelGroup)})",
            name="ck_channel_group",
        ),
        CheckConstraint("default_sla_hours > 0", name="ck_channel_sla"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_channel_dates",
        ),
    )

    channel_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    channel_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    channel_group: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_moderation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_sla_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Survey(Base):
    """Survey campaign definition entity."""

    __tablename__ = "surveys"
    __table_args__ = (
        CheckConstraint(
            f"survey_type IN ({','.join(repr(e.value) for e in SurveyType)})",
            name="ck_survey_type",
        ),
        CheckConstraint(
            f"lifecycle_state IN ({','.join(repr(e.value) for e in SurveyLifecycleState)})",
            name="ck_survey_state",
        ),
        CheckConstraint("target_response_count >= 0", name="ck_survey_target"),
        CheckConstraint("actual_response_count >= 0", name="ck_survey_actual"),
        CheckConstraint("effective_to >= effective_from", name="ck_survey_dates"),
    )

    survey_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    product_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("products.product_id"), nullable=True, index=True
    )
    channel_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("channels.channel_id"), nullable=False, index=True
    )
    survey_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    question_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False)
    target_response_count: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    product: Mapped[Optional["Product"]] = relationship()
    channel: Mapped["Channel"] = relationship()


class Theme(Base):
    """Governed feedback theme taxonomy with optional hierarchical parent."""

    __tablename__ = "themes"
    __table_args__ = (
        CheckConstraint(
            f"category IN ({','.join(repr(e.value) for e in ThemeCategory)})",
            name="ck_theme_category",
        ),
        CheckConstraint("severity_weight > 0.0 AND severity_weight <= 2.5", name="ck_theme_weight"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_theme_dates",
        ),
    )

    theme_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    theme_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    theme_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_theme_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("themes.theme_id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity_weight: Mapped[float] = mapped_column(Float, nullable=False)
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

