"""Deterministic transactional feedback generator: SurveyResponses, Reviews, SupportTickets, SupportMessages."""

from datetime import datetime, timedelta
import hashlib
import random
from typing import Any

from voc_intel.core.config import ProfileConfig, settings
from voc_intel.core.identifiers import IDGenerator
from voc_intel.db.base import (
    ChannelGroup,
    FeedbackLifecycleState,
    FeedbackSourceType,
    SenderRole,
    SentimentPolarity,
    ShiftDirection,
    SurveyType,
    TicketLifecycleState,
    TicketPriority,
)
from voc_intel.features.generation.templates import (
    AMBIGUOUS_HEDGED_TEMPLATES,
    CHANNEL_PREFIXES,
    CONTRAST_CONNECTORS,
    SARCASTIC_NEGATIVE_TEMPLATES,
    SUPPORT_AGENT_REPLIES,
    THEME_BY_ID,
    THEME_CLAUSES,
    THEME_TAXONOMY,
)

# Documented planted temporal shifts for end-to-end shift detection verification.
# Key: (product_id, theme_id) -> (direction, baseline_neg_prob, current_neg_prob)
PLANTED_SHIFT_COHORTS: dict[tuple[str, str], tuple[str, float, float]] = {
    ("PROD-001", "THEME-000001"): (ShiftDirection.DECLINING.value, 0.12, 0.88),
    ("PROD-004", "THEME-000003"): (ShiftDirection.DECLINING.value, 0.14, 0.86),
    ("PROD-002", "THEME-000002"): (ShiftDirection.IMPROVING.value, 0.84, 0.10),
}

_POLARITY_SCORE_DEFAULTS: dict[str, float] = {
    SentimentPolarity.POSITIVE.value: 0.82,
    SentimentPolarity.NEGATIVE.value: -0.82,
    SentimentPolarity.NEUTRAL.value: 0.0,
    SentimentPolarity.MIXED.value: -0.08,
}


def compute_content_hash(text: str) -> str:
    """Compute canonical SHA-256 hash of normalized feedback text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def derive_survey_rating(
    rng: random.Random, survey_type: str, polarity: str, is_sarcastic: bool
) -> tuple[int, float]:
    """Derive rating_score and normalized_score deterministically from polarity & survey scale."""
    if survey_type == SurveyType.NPS.value:
        if polarity == SentimentPolarity.POSITIVE.value:
            raw = rng.choice((9, 10))
        elif polarity == SentimentPolarity.NEGATIVE.value:
            raw = 1 if is_sarcastic else rng.randint(0, 5)
        else:
            raw = rng.randint(6, 8)
        return raw, round(raw / 10.0, 4)

    # 1..5 scale for CSAT, CES, POST_ONBOARDING
    if polarity == SentimentPolarity.POSITIVE.value:
        raw = rng.choice((4, 5))
    elif polarity == SentimentPolarity.NEGATIVE.value:
        raw = 1 if is_sarcastic else rng.choice((1, 2))
    else:
        raw = 3
    return raw, round((raw - 1) / 4.0, 4)


def derive_review_stars(rng: random.Random, polarity: str, is_sarcastic: bool) -> int:
    """Derive 1-5 star rating deterministically from sentiment polarity."""
    if polarity == SentimentPolarity.POSITIVE.value:
        return rng.choice((4, 5))
    if polarity == SentimentPolarity.NEGATIVE.value:
        return 1 if is_sarcastic else rng.choice((1, 2))
    return 3


def _compose_feedback_text(
    rng: random.Random,
    channel_group: str,
    product_name: str,
    lang: str,
    polarity: str,
    primary_theme_code: str,
    secondary_theme_code: str | None,
    is_sarcastic: bool,
    is_ambiguous: bool,
    seen_hashes: set[str],
    disambig_token: str,
) -> tuple[str, str]:
    """Build realistic multilingual synthetic text and guarantee unique baseline content_hash."""
    prefix = rng.choice(CHANNEL_PREFIXES[channel_group][lang])

    if is_sarcastic and primary_theme_code in SARCASTIC_NEGATIVE_TEMPLATES:
        lang_bank = SARCASTIC_NEGATIVE_TEMPLATES[primary_theme_code]
        pool = lang_bank.get(lang) or lang_bank["en"]
        body = rng.choice(pool).format(product=product_name)
    elif is_ambiguous:
        pool = AMBIGUOUS_HEDGED_TEMPLATES.get(lang, AMBIGUOUS_HEDGED_TEMPLATES["en"])
        body = rng.choice(pool).format(product=product_name)
    elif polarity == SentimentPolarity.MIXED.value and secondary_theme_code is not None:
        pos_pool = THEME_CLAUSES[primary_theme_code]["POSITIVE"][lang]
        neg_pool = THEME_CLAUSES[secondary_theme_code]["NEGATIVE"][lang]
        conn = rng.choice(CONTRAST_CONNECTORS[lang])
        body = f"{rng.choice(pos_pool).format(product=product_name)}{conn}{rng.choice(neg_pool).format(product=product_name)}"
    else:
        mode = polarity if polarity in ("POSITIVE", "NEGATIVE", "NEUTRAL") else "NEUTRAL"
        pool = THEME_CLAUSES[primary_theme_code][mode][lang]
        body = rng.choice(pool).format(product=product_name)

    text = f"{prefix}{body}".strip()
    content_hash = compute_content_hash(text)
    if content_hash in seen_hashes:
        text = f"{text} ({disambig_token})"
        content_hash = compute_content_hash(text)
    seen_hashes.add(content_hash)
    return text, content_hash


def _pick_polarity_for_context(
    rng: random.Random,
    product_id: str | None,
    theme_id: str,
    event_ts: datetime,
    split_dt: datetime,
) -> str:
    """Select sentiment polarity respecting balanced baseline + planted temporal shifts."""
    if product_id is not None and (product_id, theme_id) in PLANTED_SHIFT_COHORTS:
        _direction, base_neg_p, curr_neg_p = PLANTED_SHIFT_COHORTS[(product_id, theme_id)]
        neg_p = curr_neg_p if event_ts >= split_dt else base_neg_p
        roll = rng.random()
        if roll < neg_p:
            return SentimentPolarity.NEGATIVE.value
        if roll < neg_p + (1.0 - neg_p) * 0.72:
            return SentimentPolarity.POSITIVE.value
        return SentimentPolarity.NEUTRAL.value

    # Balanced distribution across 4 sentiment classes
    return rng.choices(
        (
            SentimentPolarity.POSITIVE.value,
            SentimentPolarity.NEGATIVE.value,
            SentimentPolarity.NEUTRAL.value,
            SentimentPolarity.MIXED.value,
        ),
        weights=(0.28, 0.28, 0.22, 0.22),
        k=1,
    )[0]


def generate_feedback_records(
    rng: random.Random,
    master_data: dict[str, list[dict[str, Any]]],
    profile_cfg: ProfileConfig,
    responses_override: int | None = None,
    reviews_override: int | None = None,
    messages_override: int | None = None,
    anchor: datetime | None = None,
) -> dict[str, Any]:
    """Generate SurveyResponses, Reviews, SupportTickets, SupportMessages, and internal gold metadata."""
    anchor_dt = (anchor or settings.simulation_anchor).replace(tzinfo=None)
    window_start = anchor_dt - timedelta(days=profile_cfg.simulation_days)
    split_dt = window_start + timedelta(days=int(profile_cfg.simulation_days * 2 / 3))
    sim_year = anchor_dt.year

    customers = master_data["customers"]
    products = master_data["products"]
    channels = master_data["channels"]
    surveys = master_data["surveys"]

    prod_by_id = {p["product_id"]: p for p in products}
    review_channels = [c["channel_id"] for c in channels if c["channel_group"] == ChannelGroup.REVIEW.value]
    support_channels = [c["channel_id"] for c in channels if c["channel_group"] == ChannelGroup.SUPPORT.value]
    theme_ids = [t.theme_id for t in THEME_TAXONOMY]

    n_responses = responses_override if responses_override is not None else profile_cfg.survey_responses_count
    n_reviews = reviews_override if reviews_override is not None else profile_cfg.reviews_count
    n_messages_target = (
        messages_override
        if messages_override is not None
        else round(profile_cfg.support_tickets_count * profile_cfg.avg_messages_per_ticket)
    )
    n_tickets = max(1, round(n_messages_target / profile_cfg.avg_messages_per_ticket))

    seen_hashes: set[str] = set()
    survey_responses: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    support_tickets: list[dict[str, Any]] = []
    support_messages: list[dict[str, Any]] = []
    lifecycle_events: list[dict[str, Any]] = list(master_data["lifecycle_events"])
    evt_seq = len(lifecycle_events) + 1

    # Internal generation ground truth (NEVER written to operational DB tables)
    gold_annotations: list[dict[str, Any]] = []

    total_window_secs = max(3600, int((anchor_dt - window_start).total_seconds()))

    def _random_ts_in_survey(survey: dict[str, Any], force_recent: bool = False) -> datetime:
        s_start = max(window_start, survey["effective_from"])
        s_end = min(anchor_dt, survey["effective_to"])
        if force_recent and s_end > split_dt:
            s_start = max(s_start, split_dt)
        span = max(60, int((s_end - s_start).total_seconds()))
        return s_start + timedelta(seconds=rng.randint(0, span))

    # 1. Generate SurveyResponses
    survey_counters: dict[str, int] = {s["survey_id"]: 0 for s in surveys}
    for idx in range(1, n_responses + 1):
        survey = surveys[(idx - 1) % len(surveys)]
        survey_id = survey["survey_id"]
        survey_counters[survey_id] += 1
        resp_id = IDGenerator.survey_response_id(survey_id, survey_counters[survey_id])

        cust = rng.choice(customers)
        lang = cust["preferred_language"]
        # Cross-product surveys still link response to a product (or ~10% remain platform-level None)
        prod_id = survey["product_id"] or (
            None if idx % 10 == 0 else rng.choice(products)["product_id"]
        )
        prod_name = prod_by_id[prod_id]["product_name"] if prod_id else "YottaFlex Platform"

        primary_theme_id = rng.choice(theme_ids)
        # Boost volume on planted shift cohorts so statistical power is high even at starter scale
        if idx % 10 == 0:
            cohort_prod, cohort_theme = rng.choice(list(PLANTED_SHIFT_COHORTS.keys()))
            if survey["product_id"] is None or survey["product_id"] == cohort_prod:
                prod_id = cohort_prod
                prod_name = prod_by_id[prod_id]["product_name"]
                primary_theme_id = cohort_theme

        submitted_at = _random_ts_in_survey(survey)
        polarity = _pick_polarity_for_context(rng, prod_id, primary_theme_id, submitted_at, split_dt)
        primary_spec = THEME_BY_ID[primary_theme_id]

        secondary_theme_id: str | None = None
        if polarity == SentimentPolarity.MIXED.value:
            other_choices = [tid for tid in theme_ids if tid != primary_theme_id]
            secondary_theme_id = rng.choice(other_choices)

        is_sarcastic = (
            polarity == SentimentPolarity.NEGATIVE.value
            and primary_spec.theme_code in SARCASTIC_NEGATIVE_TEMPLATES
            and rng.random() < 0.08
        )
        is_ambiguous = (
            polarity == SentimentPolarity.NEUTRAL.value
            and not is_sarcastic
            and rng.random() < 0.16
        )

        rating_score, normalized_score = derive_survey_rating(
            rng, survey["survey_type"], polarity, is_sarcastic
        )
        text, content_hash = _compose_feedback_text(
            rng=rng,
            channel_group=ChannelGroup.SURVEY.value,
            product_name=prod_name,
            lang=lang,
            polarity=polarity,
            primary_theme_code=primary_spec.theme_code,
            secondary_theme_code=THEME_BY_ID[secondary_theme_id].theme_code if secondary_theme_id else None,
            is_sarcastic=is_sarcastic,
            is_ambiguous=is_ambiguous,
            seen_hashes=seen_hashes,
            disambig_token=f"ref {idx:05d}",
        )

        survey_responses.append(
            {
                "response_id": resp_id,
                "survey_id": survey_id,
                "customer_id": cust["customer_id"],
                "product_id": prod_id,
                "channel_id": survey["channel_id"],
                "rating_score": rating_score,
                "normalized_score": normalized_score,
                "response_text": text,
                "language": lang,
                "submitted_at": submitted_at,
                "lifecycle_state": FeedbackLifecycleState.VERIFIED.value,
                "content_hash": content_hash,
            }
        )
        lifecycle_events.extend(
            (
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                    "entity_type": FeedbackSourceType.SURVEY_RESPONSE.value,
                    "entity_id": resp_id,
                    "from_state": None,
                    "to_state": FeedbackLifecycleState.SUBMITTED.value,
                    "actor": "customer_portal",
                    "reason": "Survey response submitted",
                    "event_timestamp": submitted_at,
                    "sequence_no": 1,
                },
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 1),
                    "entity_type": FeedbackSourceType.SURVEY_RESPONSE.value,
                    "entity_id": resp_id,
                    "from_state": FeedbackLifecycleState.SUBMITTED.value,
                    "to_state": FeedbackLifecycleState.ANALYZED.value,
                    "actor": "nlp_pipeline",
                    "reason": "Sentiment and theme inference completed",
                    "event_timestamp": submitted_at + timedelta(seconds=15),
                    "sequence_no": 2,
                },
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 2),
                    "entity_type": FeedbackSourceType.SURVEY_RESPONSE.value,
                    "entity_id": resp_id,
                    "from_state": FeedbackLifecycleState.ANALYZED.value,
                    "to_state": FeedbackLifecycleState.VERIFIED.value,
                    "actor": "quality_gate",
                    "reason": "Passed schema and privacy checks",
                    "event_timestamp": submitted_at + timedelta(seconds=30),
                    "sequence_no": 3,
                },
            )
        )
        evt_seq += 3

        gold_themes = [primary_theme_id] + ([secondary_theme_id] if secondary_theme_id else [])
        gold_annotations.append(
            {
                "source_type": FeedbackSourceType.SURVEY_RESPONSE.value,
                "record_id": resp_id,
                "product_id": prod_id,
                "channel_id": survey["channel_id"],
                "language": lang,
                "event_timestamp": submitted_at,
                "gold_polarity": polarity,
                "gold_score": _POLARITY_SCORE_DEFAULTS[polarity],
                "gold_themes": gold_themes,
                "is_sarcastic": is_sarcastic,
                "is_ambiguous": is_ambiguous,
                "evaluatable": True,
            }
        )

    # Reconcile Survey.actual_response_count from source child counts
    for s in surveys:
        s["actual_response_count"] = survey_counters[s["survey_id"]]

    # 2. Generate Reviews
    for idx in range(1, n_reviews + 1):
        rev_id = IDGenerator.review_id(sim_year, idx)
        # ~15% anonymous web reviews (customer_id=None) to exercise optional FK
        is_anonymous = idx % 7 == 0
        cust = None if is_anonymous else rng.choice(customers)
        lang = rng.choice(("en", "es", "fr", "de")) if cust is None else cust["preferred_language"]
        if cust is None and rng.random() < 0.75:
            lang = "en"

        # Guarantee strong coverage of planted shift cohorts as well as uniform themes
        if idx % 10 == 0:
            prod_id, primary_theme_id = rng.choice(list(PLANTED_SHIFT_COHORTS.keys()))
            if prod_id not in prod_by_id:
                prod_id = products[(idx - 1) % len(products)]["product_id"]
        else:
            prod_id = products[(idx - 1) % len(products)]["product_id"]
            primary_theme_id = rng.choice(theme_ids)

        prod_name = prod_by_id[prod_id]["product_name"]
        channel_id = rng.choice(review_channels)
        published_at = window_start + timedelta(seconds=rng.randint(0, total_window_secs))
        polarity = _pick_polarity_for_context(rng, prod_id, primary_theme_id, published_at, split_dt)
        primary_spec = THEME_BY_ID[primary_theme_id]

        secondary_theme_id = None
        if polarity == SentimentPolarity.MIXED.value:
            secondary_theme_id = rng.choice([tid for tid in theme_ids if tid != primary_theme_id])

        is_sarcastic = (
            polarity == SentimentPolarity.NEGATIVE.value
            and primary_spec.theme_code in SARCASTIC_NEGATIVE_TEMPLATES
            and rng.random() < 0.09
        )
        is_ambiguous = (
            polarity == SentimentPolarity.NEUTRAL.value
            and not is_sarcastic
            and rng.random() < 0.16
        )

        star_rating = derive_review_stars(rng, polarity, is_sarcastic)
        text, content_hash = _compose_feedback_text(
            rng=rng,
            channel_group=ChannelGroup.REVIEW.value,
            product_name=prod_name,
            lang=lang,
            polarity=polarity,
            primary_theme_code=primary_spec.theme_code,
            secondary_theme_code=THEME_BY_ID[secondary_theme_id].theme_code if secondary_theme_id else None,
            is_sarcastic=is_sarcastic,
            is_ambiguous=is_ambiguous,
            seen_hashes=seen_hashes,
            disambig_token=f"review {idx:05d}",
        )
        title_map = {
            SentimentPolarity.POSITIVE.value: f"Strong experience with {prod_name}",
            SentimentPolarity.NEGATIVE.value: f"Issues encountered in {prod_name}",
            SentimentPolarity.NEUTRAL.value: f"Overview of {prod_name}",
            SentimentPolarity.MIXED.value: f"Pros and cons for {prod_name}",
        }

        reviews.append(
            {
                "review_id": rev_id,
                "customer_id": cust["customer_id"] if cust else None,
                "product_id": prod_id,
                "channel_id": channel_id,
                "star_rating": star_rating,
                "title": title_map[polarity],
                "review_text": text,
                "language": lang,
                "verified_purchase": not is_anonymous,
                "helpful_votes": rng.randint(0, 25),
                "published_at": published_at,
                "lifecycle_state": FeedbackLifecycleState.VERIFIED.value,
                "content_hash": content_hash,
            }
        )
        lifecycle_events.extend(
            (
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                    "entity_type": FeedbackSourceType.REVIEW.value,
                    "entity_id": rev_id,
                    "from_state": None,
                    "to_state": FeedbackLifecycleState.SUBMITTED.value,
                    "actor": "review_ingestion",
                    "reason": "Public review ingested",
                    "event_timestamp": published_at,
                    "sequence_no": 1,
                },
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 1),
                    "entity_type": FeedbackSourceType.REVIEW.value,
                    "entity_id": rev_id,
                    "from_state": FeedbackLifecycleState.SUBMITTED.value,
                    "to_state": FeedbackLifecycleState.ANALYZED.value,
                    "actor": "nlp_pipeline",
                    "reason": "Sentiment and theme inference completed",
                    "event_timestamp": published_at + timedelta(seconds=15),
                    "sequence_no": 2,
                },
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 2),
                    "entity_type": FeedbackSourceType.REVIEW.value,
                    "entity_id": rev_id,
                    "from_state": FeedbackLifecycleState.ANALYZED.value,
                    "to_state": FeedbackLifecycleState.VERIFIED.value,
                    "actor": "quality_gate",
                    "reason": "Passed moderation and privacy checks",
                    "event_timestamp": published_at + timedelta(seconds=30),
                    "sequence_no": 3,
                },
            )
        )
        evt_seq += 3

        gold_themes = [primary_theme_id] + ([secondary_theme_id] if secondary_theme_id else [])
        gold_annotations.append(
            {
                "source_type": FeedbackSourceType.REVIEW.value,
                "record_id": rev_id,
                "product_id": prod_id,
                "channel_id": channel_id,
                "language": lang,
                "event_timestamp": published_at,
                "gold_polarity": polarity,
                "gold_score": _POLARITY_SCORE_DEFAULTS[polarity],
                "gold_themes": gold_themes,
                "is_sarcastic": is_sarcastic,
                "is_ambiguous": is_ambiguous,
                "evaluatable": True,
            }
        )

    # 3. Generate SupportTickets & exact target count of SupportMessages
    # Distribute n_messages_target deterministically across n_tickets (>=1 msg per ticket)
    if n_messages_target <= 0:
        n_tickets = 0
        base_per_tkt = 0
        remainder = 0
    else:
        if n_messages_target < n_tickets:
            n_tickets = n_messages_target
        base_per_tkt = n_messages_target // n_tickets
        remainder = n_messages_target % n_tickets

    for t_idx in range(1, n_tickets + 1):
        tkt_id = IDGenerator.ticket_id(sim_year, t_idx)
        cust = rng.choice(customers)
        lang = cust["preferred_language"]

        if t_idx % 8 == 0:
            prod_id, primary_theme_id = rng.choice(list(PLANTED_SHIFT_COHORTS.keys()))
            if prod_id not in prod_by_id:
                prod_id = products[(t_idx - 1) % len(products)]["product_id"]
        else:
            prod_id = products[(t_idx - 1) % len(products)]["product_id"]
            primary_theme_id = rng.choice(theme_ids)

        prod_name = prod_by_id[prod_id]["product_name"]
        channel_id = rng.choice(support_channels)
        opened_at = window_start + timedelta(seconds=rng.randint(0, max(60, total_window_secs - 7200)))

        msg_count = base_per_tkt + (1 if t_idx <= remainder else 0)
        primary_spec = THEME_BY_ID[primary_theme_id]
        cust_polarity = _pick_polarity_for_context(rng, prod_id, primary_theme_id, opened_at, split_dt)

        tkt_priority = (
            TicketPriority.URGENT.value
            if cust_polarity == SentimentPolarity.NEGATIVE.value and primary_spec.severity_weight >= 1.4
            else (
                TicketPriority.HIGH.value
                if cust_polarity == SentimentPolarity.NEGATIVE.value
                else TicketPriority.MEDIUM.value
            )
        )
        is_resolved = t_idx % 6 != 0
        final_tkt_state = (
            TicketLifecycleState.CLOSED.value
            if (is_resolved and t_idx % 2 == 0)
            else (
                TicketLifecycleState.RESOLVED.value
                if is_resolved
                else TicketLifecycleState.ESCALATED.value
            )
        )

        last_msg_ts = opened_at
        for m_seq in range(1, msg_count + 1):
            msg_id = IDGenerator.support_message_id(tkt_id, m_seq)
            sent_at = opened_at + timedelta(minutes=(m_seq - 1) * rng.randint(15, 90))
            last_msg_ts = sent_at

            if m_seq == 1 or m_seq == 3:
                sender_role = SenderRole.CUSTOMER.value
                msg_polarity = cust_polarity
                secondary_theme_id = (
                    rng.choice([tid for tid in theme_ids if tid != primary_theme_id])
                    if msg_polarity == SentimentPolarity.MIXED.value
                    else None
                )
                is_sarcastic = (
                    msg_polarity == SentimentPolarity.NEGATIVE.value
                    and primary_spec.theme_code in SARCASTIC_NEGATIVE_TEMPLATES
                    and rng.random() < 0.07
                )
                is_ambiguous = (
                    msg_polarity == SentimentPolarity.NEUTRAL.value
                    and not is_sarcastic
                    and rng.random() < 0.14
                )
                text, content_hash = _compose_feedback_text(
                    rng=rng,
                    channel_group=ChannelGroup.SUPPORT.value,
                    product_name=prod_name,
                    lang=lang,
                    polarity=msg_polarity,
                    primary_theme_code=primary_spec.theme_code,
                    secondary_theme_code=(
                        THEME_BY_ID[secondary_theme_id].theme_code if secondary_theme_id else None
                    ),
                    is_sarcastic=is_sarcastic,
                    is_ambiguous=is_ambiguous,
                    seen_hashes=seen_hashes,
                    disambig_token=f"ticket {t_idx:05d}-{m_seq}",
                )
                msg_themes = [primary_theme_id] + ([secondary_theme_id] if secondary_theme_id else [])
            else:
                sender_role = SenderRole.SUPPORT_AGENT.value
                msg_polarity = SentimentPolarity.POSITIVE.value
                is_sarcastic = False
                is_ambiguous = False
                reply_pool = SUPPORT_AGENT_REPLIES.get(lang, SUPPORT_AGENT_REPLIES["en"])
                raw_reply = rng.choice(reply_pool).format(product=prod_name)
                content_hash = compute_content_hash(raw_reply)
                if content_hash in seen_hashes:
                    raw_reply = f"{raw_reply} (Case {t_idx:05d})"
                    content_hash = compute_content_hash(raw_reply)
                seen_hashes.add(content_hash)
                text = raw_reply
                msg_themes = ["THEME-000006"]  # SUPPORT_HELPFUL_RESOLUTION

            support_messages.append(
                {
                    "message_id": msg_id,
                    "ticket_id": tkt_id,
                    "customer_id": cust["customer_id"],
                    "product_id": prod_id,
                    "channel_id": channel_id,
                    "sender_role": sender_role,
                    "sequence_no": m_seq,
                    "message_text": text,
                    "language": lang,
                    "sent_at": sent_at,
                    "lifecycle_state": FeedbackLifecycleState.VERIFIED.value,
                    "content_hash": content_hash,
                }
            )
            lifecycle_events.extend(
                (
                    {
                        "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                        "entity_type": FeedbackSourceType.SUPPORT_MESSAGE.value,
                        "entity_id": msg_id,
                        "from_state": None,
                        "to_state": FeedbackLifecycleState.SUBMITTED.value,
                        "actor": "support_gateway",
                        "reason": f"Message {m_seq} captured on {tkt_id}",
                        "event_timestamp": sent_at,
                        "sequence_no": 1,
                    },
                    {
                        "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 1),
                        "entity_type": FeedbackSourceType.SUPPORT_MESSAGE.value,
                        "entity_id": msg_id,
                        "from_state": FeedbackLifecycleState.SUBMITTED.value,
                        "to_state": FeedbackLifecycleState.ANALYZED.value,
                        "actor": "nlp_pipeline",
                        "reason": "Sentiment and theme inference completed",
                        "event_timestamp": sent_at + timedelta(seconds=10),
                        "sequence_no": 2,
                    },
                    {
                        "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq + 2),
                        "entity_type": FeedbackSourceType.SUPPORT_MESSAGE.value,
                        "entity_id": msg_id,
                        "from_state": FeedbackLifecycleState.ANALYZED.value,
                        "to_state": FeedbackLifecycleState.VERIFIED.value,
                        "actor": "quality_gate",
                        "reason": "Passed privacy and schema checks",
                        "event_timestamp": sent_at + timedelta(seconds=20),
                        "sequence_no": 3,
                    },
                )
            )
            evt_seq += 3

            gold_annotations.append(
                {
                    "source_type": FeedbackSourceType.SUPPORT_MESSAGE.value,
                    "record_id": msg_id,
                    "product_id": prod_id,
                    "channel_id": channel_id,
                    "language": lang,
                    "event_timestamp": sent_at,
                    "gold_polarity": msg_polarity,
                    "gold_score": _POLARITY_SCORE_DEFAULTS[msg_polarity],
                    "gold_themes": msg_themes,
                    "is_sarcastic": is_sarcastic,
                    "is_ambiguous": is_ambiguous,
                    "evaluatable": sender_role == SenderRole.CUSTOMER.value,
                }
            )

        resolved_at = (
            last_msg_ts + timedelta(minutes=rng.randint(10, 180)) if is_resolved else None
        )
        support_tickets.append(
            {
                "ticket_id": tkt_id,
                "customer_id": cust["customer_id"],
                "product_id": prod_id,
                "channel_id": channel_id,
                "subject": f"{primary_spec.theme_name} - {prod_name}",
                "priority": tkt_priority,
                "lifecycle_state": final_tkt_state,
                "message_count": msg_count,
                "opened_at": opened_at,
                "resolved_at": resolved_at,
            }
        )
        # Ticket lifecycle events
        tkt_transitions = [
            (None, TicketLifecycleState.OPEN.value, "customer_portal", "Ticket opened", opened_at),
            (
                TicketLifecycleState.OPEN.value,
                TicketLifecycleState.TRIAGED.value,
                "support_router",
                "Ticket routed by product & priority",
                opened_at + timedelta(minutes=5),
            ),
            (
                TicketLifecycleState.TRIAGED.value,
                TicketLifecycleState.IN_PROGRESS.value,
                "support_agent",
                "Agent started investigation",
                opened_at + timedelta(minutes=12),
            ),
        ]
        if final_tkt_state == TicketLifecycleState.ESCALATED.value:
            tkt_transitions.append(
                (
                    TicketLifecycleState.IN_PROGRESS.value,
                    TicketLifecycleState.ESCALATED.value,
                    "support_agent",
                    "Escalated to engineering tier",
                    last_msg_ts + timedelta(minutes=5),
                )
            )
        else:
            tkt_transitions.append(
                (
                    TicketLifecycleState.IN_PROGRESS.value,
                    TicketLifecycleState.RESOLVED.value,
                    "support_agent",
                    "Resolution confirmed",
                    resolved_at,
                )
            )
            if final_tkt_state == TicketLifecycleState.CLOSED.value:
                tkt_transitions.append(
                    (
                        TicketLifecycleState.RESOLVED.value,
                        TicketLifecycleState.CLOSED.value,
                        "system_sla",
                        "Ticket closed post-resolution",
                        resolved_at + timedelta(minutes=5),
                    )
                )

        for seq_no, (f_st, t_st, actor, reason, ts) in enumerate(tkt_transitions, start=1):
            lifecycle_events.append(
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                    "entity_type": "SUPPORT_TICKET",
                    "entity_id": tkt_id,
                    "from_state": f_st,
                    "to_state": t_st,
                    "actor": actor,
                    "reason": reason,
                    "event_timestamp": ts,
                    "sequence_no": seq_no,
                }
            )
            evt_seq += 1

    return {
        "survey_responses": survey_responses,
        "reviews": reviews,
        "support_tickets": support_tickets,
        "support_messages": support_messages,
        "lifecycle_events": lifecycle_events,
        "gold_annotations": gold_annotations,
        "split_dt": split_dt,
        "window_start": window_start,
        "anchor_dt": anchor_dt,
    }
