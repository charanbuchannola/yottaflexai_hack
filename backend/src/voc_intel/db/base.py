"""Declarative Base and domain enumerations."""

from enum import Enum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base class."""


class AccountTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class CustomerSegment(str, Enum):
    CONSUMER = "CONSUMER"
    SMB = "SMB"
    MID_MARKET = "MID_MARKET"
    ENTERPRISE = "ENTERPRISE"


class Region(str, Enum):
    NA = "NA"
    EMEA = "EMEA"
    APAC = "APAC"
    LATAM = "LATAM"


class LanguageCode(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"


class CustomerLifecycleState(str, Enum):
    PROSPECT = "PROSPECT"
    ACTIVE = "ACTIVE"
    AT_RISK = "AT_RISK"
    CHURNED = "CHURNED"


class ProductCategory(str, Enum):
    CORE_PLATFORM = "CORE_PLATFORM"
    ANALYTICS_SUITE = "ANALYTICS_SUITE"
    MOBILE_APP = "MOBILE_APP"
    BILLING_ADDON = "BILLING_ADDON"
    API_GATEWAY = "API_GATEWAY"


class ProductLifecycleState(str, Enum):
    BETA = "BETA"
    GA = "GA"
    SUNSETTING = "SUNSETTING"
    DEPRECATED = "DEPRECATED"


class ChannelGroup(str, Enum):
    SURVEY = "SURVEY"
    REVIEW = "REVIEW"
    SUPPORT = "SUPPORT"


class SurveyType(str, Enum):
    NPS = "NPS"
    CSAT = "CSAT"
    CES = "CES"
    POST_ONBOARDING = "POST_ONBOARDING"


class SurveyLifecycleState(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class FeedbackLifecycleState(str, Enum):
    SUBMITTED = "SUBMITTED"
    ANALYZED = "ANALYZED"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"
    QUARANTINED = "QUARANTINED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketLifecycleState(str, Enum):
    OPEN = "OPEN"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SenderRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    SYSTEM_BOT = "SYSTEM_BOT"


class ThemeCategory(str, Enum):
    PERFORMANCE_RELIABILITY = "PERFORMANCE_RELIABILITY"
    BILLING_PRICING = "BILLING_PRICING"
    SUPPORT_EXPERIENCE = "SUPPORT_EXPERIENCE"
    UX_ONBOARDING = "UX_ONBOARDING"
    PRODUCT_QUALITY = "PRODUCT_QUALITY"
    INTEGRATIONS = "INTEGRATIONS"
    SECURITY_PRIVACY = "SECURITY_PRIVACY"


class FeedbackSourceType(str, Enum):
    SURVEY_RESPONSE = "SURVEY_RESPONSE"
    REVIEW = "REVIEW"
    SUPPORT_MESSAGE = "SUPPORT_MESSAGE"


class SentimentPolarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class LabelingMethod(str, Enum):
    AUTOMATED_NLP = "AUTOMATED_NLP"
    INGESTED_PROVIDER = "INGESTED_PROVIDER"


class PriorityTier(str, Enum):
    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_MEDIUM = "P2_MEDIUM"
    P3_LOW = "P3_LOW"


class ActionLifecycleState(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class ShiftDirection(str, Enum):
    IMPROVING = "IMPROVING"
    DECLINING = "DECLINING"
    STABLE = "STABLE"

