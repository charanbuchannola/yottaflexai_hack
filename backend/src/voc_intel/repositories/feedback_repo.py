"""Repository for master/feedback entities: Customer, Product, Survey, SurveyResponse, Review, SupportMessage, Theme."""

from typing import Sequence

from sqlalchemy import func, select

from voc_intel.db import (
    Customer,
    Product,
    Review,
    SupportMessage,
    Survey,
    SurveyResponse,
    Theme,
)
from voc_intel.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository):
    """Data-access methods for master catalog and multi-channel feedback records."""

    def get_core_counts(self) -> dict[str, int]:
        return {
            "customers": self.session.scalar(select(func.count()).select_from(Customer)) or 0,
            "products": self.session.scalar(select(func.count()).select_from(Product)) or 0,
            "surveys": self.session.scalar(select(func.count()).select_from(Survey)) or 0,
            "survey_responses": self.session.scalar(select(func.count()).select_from(SurveyResponse)) or 0,
            "reviews": self.session.scalar(select(func.count()).select_from(Review)) or 0,
            "support_messages": self.session.scalar(select(func.count()).select_from(SupportMessage)) or 0,
        }

    def list_themes(self) -> Sequence[Theme]:
        return self.session.scalars(select(Theme).order_by(Theme.theme_id)).all()

    def get_response_texts_by_ids(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        rows = self.session.scalars(
            select(SurveyResponse).where(SurveyResponse.response_id.in_(ids))
        ).all()
        return {r.response_id: r.response_text for r in rows}

    def get_review_texts_by_ids(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        rows = self.session.scalars(select(Review).where(Review.review_id.in_(ids))).all()
        return {r.review_id: r.review_text for r in rows}

    def get_message_texts_by_ids(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        rows = self.session.scalars(
            select(SupportMessage).where(SupportMessage.message_id.in_(ids))
        ).all()
        return {m.message_id: m.message_text for m in rows}

    def list_all_survey_responses(self) -> Sequence[SurveyResponse]:
        return self.session.scalars(select(SurveyResponse)).all()

    def list_all_reviews(self) -> Sequence[Review]:
        return self.session.scalars(select(Review)).all()

    def list_all_support_messages(self) -> Sequence[SupportMessage]:
        return self.session.scalars(select(SupportMessage)).all()

