"""Deterministic zero-padded identifier generation and format validation."""

import re

ID_PATTERNS: dict[str, re.Pattern[str]] = {
    "customer": re.compile(r"^CUST-\d{6}$"),
    "product": re.compile(r"^PROD-\d{3}$"),
    "channel": re.compile(r"^CHN-\d{3}$"),
    "survey": re.compile(r"^SUR-\d{4}-\d{6}$"),
    "survey_response": re.compile(r"^RESP-SUR-\d{4}-\d{6}-\d{3,}$"),
    "review": re.compile(r"^REV-\d{4}-\d{6}$"),
    "support_ticket": re.compile(r"^TKT-\d{4}-\d{6}$"),
    "support_message": re.compile(r"^MSG-TKT-\d{4}-\d{6}-\d{3,}$"),
    "theme": re.compile(r"^THEME-\d{6}$"),
    "sentiment_label": re.compile(r"^SENT-\d{6}$"),
    "theme_assignment": re.compile(r"^THM-ASN-\d{6}$"),
    "sentiment_shift": re.compile(r"^SHIFT-\d{4}-\d{6}$"),
    "action_item": re.compile(r"^ACT-\d{4}-\d{6}$"),
    "action_evidence": re.compile(r"^EVID-\d{6}$"),
    "model_input": re.compile(r"^INP-\d{6}$"),
    "lifecycle_event": re.compile(r"^EVT-\d{4}-\d{6}$"),
}


class IDGenerator:
    """Deterministic zero-padded identifier builders matching strict domain conventions."""

    @staticmethod
    def customer_id(seq: int) -> str:
        return f"CUST-{seq:06d}"

    @staticmethod
    def product_id(seq: int) -> str:
        return f"PROD-{seq:03d}"

    @staticmethod
    def channel_id(seq: int) -> str:
        return f"CHN-{seq:03d}"

    @staticmethod
    def survey_id(year: int, seq: int) -> str:
        return f"SUR-{year:04d}-{seq:06d}"

    @staticmethod
    def survey_response_id(survey_id: str, seq: int) -> str:
        return f"RESP-{survey_id}-{seq:03d}"

    @staticmethod
    def review_id(year: int, seq: int) -> str:
        return f"REV-{year:04d}-{seq:06d}"

    @staticmethod
    def ticket_id(year: int, seq: int) -> str:
        return f"TKT-{year:04d}-{seq:06d}"

    @staticmethod
    def support_message_id(ticket_id: str, seq: int) -> str:
        return f"MSG-{ticket_id}-{seq:03d}"

    @staticmethod
    def theme_id(seq: int) -> str:
        return f"THEME-{seq:06d}"

    @staticmethod
    def sentiment_label_id(seq: int) -> str:
        return f"SENT-{seq:06d}"

    @staticmethod
    def theme_assignment_id(seq: int) -> str:
        return f"THM-ASN-{seq:06d}"

    @staticmethod
    def sentiment_shift_id(year: int, seq: int) -> str:
        return f"SHIFT-{year:04d}-{seq:06d}"

    @staticmethod
    def action_item_id(year: int, seq: int) -> str:
        return f"ACT-{year:04d}-{seq:06d}"

    @staticmethod
    def action_evidence_id(seq: int) -> str:
        return f"EVID-{seq:06d}"

    @staticmethod
    def model_input_id(seq: int) -> str:
        return f"INP-{seq:06d}"

    @staticmethod
    def lifecycle_event_id(year: int, seq: int) -> str:
        return f"EVT-{year:04d}-{seq:06d}"

    @staticmethod
    def validate_id(entity_key: str, value: str) -> bool:
        pattern = ID_PATTERNS.get(entity_key)
        if pattern is None:
            raise ValueError(f"Unknown entity_key '{entity_key}'")
        return bool(pattern.match(value))

