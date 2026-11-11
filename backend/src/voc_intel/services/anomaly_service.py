"""Service layer for live anomaly and policy-violation detection."""

from typing import Any

from voc_intel.features.validation.runner import detect_anomalies_in_dataset
from voc_intel.repositories.analytics_repo import AnalyticsRepository
from voc_intel.repositories.feedback_repo import FeedbackRepository


class AnomalyService:
    """Runs deterministic exception & anomaly detectors over repository data."""

    def __init__(
        self,
        feedback_repo: FeedbackRepository,
        analytics_repo: AnalyticsRepository,
    ) -> None:
        self.feedback_repo = feedback_repo
        self.analytics_repo = analytics_repo

    def detect_live_anomalies(self) -> list[dict[str, Any]]:
        tables: dict[str, list[dict[str, Any]]] = {
            "themes": [
                {"theme_id": t.theme_id, "theme_code": t.theme_code, "is_active": t.is_active}
                for t in self.feedback_repo.list_themes()
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
                for r in self.feedback_repo.list_all_survey_responses()
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
                for rev in self.feedback_repo.list_all_reviews()
            ],
            "support_messages": [
                {
                    "message_id": m.message_id,
                    "message_text": m.message_text,
                    "language": m.language,
                }
                for m in self.feedback_repo.list_all_support_messages()
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
                for s in self.analytics_repo.list_sentiment_labels()
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
                for a in self.analytics_repo.list_all_theme_assignments()
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
                for mi in self.analytics_repo.list_model_inputs()
            ],
        }
        return detect_anomalies_in_dataset(tables)

