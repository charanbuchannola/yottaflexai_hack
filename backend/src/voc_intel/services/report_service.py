"""Service layer for serving generated validation & evaluation JSON reports."""

import json
from pathlib import Path
from typing import Any

from voc_intel.core.exceptions import ResourceNotFoundError


class ReportService:
    """Reads generated operational validation and evaluation reports."""

    _ALLOWED_REPORTS = {
        "validation": "validation_report.json",
        "evaluation": "evaluation_metrics.json",
    }

    def __init__(self, exports_dir: Path) -> None:
        self.exports_dir = exports_dir

    def get_report(self, report_name: str) -> dict[str, Any]:
        filename = self._ALLOWED_REPORTS.get(report_name)
        if filename is None:
            raise ResourceNotFoundError("Report not found; use 'validation' or 'evaluation'")
        path = self.exports_dir / "reports" / filename
        if not path.exists():
            raise ResourceNotFoundError(f"Report '{path}' has not been generated yet")
        return json.loads(path.read_text(encoding="utf-8"))

