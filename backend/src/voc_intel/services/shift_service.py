"""Service layer for querying temporal sentiment shifts."""

from typing import Any, Optional

from voc_intel.repositories.analytics_repo import AnalyticsRepository


class ShiftService:
    """Provides filtered access to derived SentimentShift cohorts."""

    def __init__(self, analytics_repo: AnalyticsRepository) -> None:
        self.analytics_repo = analytics_repo

    def list_shifts(
        self,
        significant_only: bool = False,
        product_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = self.analytics_repo.list_shifts(
            significant_only=significant_only,
            product_id=product_id,
        )
        return [
            {
                "shift_id": r.shift_id,
                "product_id": r.product_id,
                "theme_id": r.theme_id,
                "baseline_count": r.baseline_count,
                "current_count": r.current_count,
                "baseline_avg_score": r.baseline_avg_score,
                "current_avg_score": r.current_avg_score,
                "delta_score": r.delta_score,
                "z_score": r.z_score,
                "direction": r.direction,
                "is_significant": r.is_significant,
            }
            for r in rows
        ]

