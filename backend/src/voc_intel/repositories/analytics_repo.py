"""Repository for analytical entities: SentimentLabel, FeedbackThemeAssignment, SentimentShift, ModelInputFeature."""

from typing import Optional, Sequence

from sqlalchemy import func, select

from voc_intel.db import (
    FeedbackThemeAssignment,
    ModelInputFeature,
    SentimentLabel,
    SentimentShift,
)
from voc_intel.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository):
    """Data-access methods for NLP predictions, theme assignments, shifts, and model inputs."""

    def count_shifts(self) -> int:
        return self.session.scalar(select(func.count()).select_from(SentimentShift)) or 0

    def list_assigned_theme_mappings(self) -> Sequence[FeedbackThemeAssignment]:
        return self.session.scalars(
            select(FeedbackThemeAssignment).where(FeedbackThemeAssignment.theme_id.is_not(None))
        ).all()

    def list_all_theme_assignments(self) -> Sequence[FeedbackThemeAssignment]:
        return self.session.scalars(select(FeedbackThemeAssignment)).all()

    def list_sentiment_labels(self) -> Sequence[SentimentLabel]:
        return self.session.scalars(select(SentimentLabel)).all()

    def get_labels_by_parent_ids(
        self,
        response_ids: list[str],
        review_ids: list[str],
        message_ids: list[str],
    ) -> tuple[dict[str, SentimentLabel], dict[str, SentimentLabel], dict[str, SentimentLabel]]:
        by_resp = (
            {
                s.response_id: s
                for s in self.session.scalars(
                    select(SentimentLabel).where(SentimentLabel.response_id.in_(response_ids))
                ).all()
                if s.response_id
            }
            if response_ids
            else {}
        )
        by_rev = (
            {
                s.review_id: s
                for s in self.session.scalars(
                    select(SentimentLabel).where(SentimentLabel.review_id.in_(review_ids))
                ).all()
                if s.review_id
            }
            if review_ids
            else {}
        )
        by_msg = (
            {
                s.message_id: s
                for s in self.session.scalars(
                    select(SentimentLabel).where(SentimentLabel.message_id.in_(message_ids))
                ).all()
                if s.message_id
            }
            if message_ids
            else {}
        )
        return by_resp, by_rev, by_msg

    def list_shifts(
        self,
        significant_only: bool = False,
        product_id: Optional[str] = None,
    ) -> Sequence[SentimentShift]:
        stmt = select(SentimentShift).order_by(SentimentShift.delta_score)
        if significant_only:
            stmt = stmt.where(SentimentShift.is_significant.is_(True))
        if product_id:
            stmt = stmt.where(SentimentShift.product_id == product_id)
        return self.session.scalars(stmt).all()

    def list_model_inputs(self) -> Sequence[ModelInputFeature]:
        return self.session.scalars(select(ModelInputFeature)).all()

