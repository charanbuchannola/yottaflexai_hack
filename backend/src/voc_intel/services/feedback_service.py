"""Service layer for system health counts and recurring theme summaries."""

from typing import Any

from voc_intel.repositories.analytics_repo import AnalyticsRepository
from voc_intel.repositories.feedback_repo import FeedbackRepository
from voc_intel.repositories.priority_repo import PriorityRepository


class FeedbackService:
    """Aggregates multi-channel feedback health metrics and recurring theme summaries."""

    def __init__(
        self,
        feedback_repo: FeedbackRepository,
        analytics_repo: AnalyticsRepository,
        priority_repo: PriorityRepository,
    ) -> None:
        self.feedback_repo = feedback_repo
        self.analytics_repo = analytics_repo
        self.priority_repo = priority_repo

    def get_health_counts(self) -> dict[str, int]:
        counts = self.feedback_repo.get_core_counts()
        counts["sentiment_shifts"] = self.analytics_repo.count_shifts()
        counts["action_items"] = self.priority_repo.count_action_items()
        return counts

    def get_theme_summaries(self) -> list[dict[str, Any]]:
        themes = self.feedback_repo.list_themes()
        assignments = self.analytics_repo.list_assigned_theme_mappings()
        labels = self.analytics_repo.list_sentiment_labels()

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

        results: list[dict[str, Any]] = []
        for t in themes:
            items = stats.get(t.theme_id, [])
            n = len(items)
            avg_s = round(sum(sc for _p, sc in items) / n, 4) if n else 0.0
            neg_c = sum(1 for pol, sc in items if pol == "NEGATIVE" or (pol == "MIXED" and sc < 0))
            results.append(
                {
                    "theme_id": t.theme_id,
                    "theme_code": t.theme_code,
                    "theme_name": t.theme_name,
                    "category": t.category,
                    "severity_weight": t.severity_weight,
                    "mention_count": n,
                    "avg_sentiment_score": avg_s,
                    "negative_count": neg_c,
                }
            )
        results.sort(key=lambda x: (-x["mention_count"], x["theme_id"]))
        return results

