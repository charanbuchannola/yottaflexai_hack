"""Service priority scoring and ActionItem + ActionItemEvidence generation (Rule BR-PRIO-001)."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from voc_intel.generators.identifiers import IDGenerator
from voc_intel.generators.templates import THEME_BY_ID
from voc_intel.models.base import (
    ActionLifecycleState,
    FeedbackSourceType,
    PriorityTier,
    SenderRole,
    SentimentPolarity,
    ShiftDirection,
)


def compute_priority_score(
    mention_count: int,
    volume_anchor: float,
    negative_share: float,
    sentiment_delta: float,
    severity_weight: float,
    channel_breadth: int,
) -> tuple[float, str]:
    """Deterministic documented formula BR-PRIO-001 returning (priority_score, priority_tier)."""
    vol_norm = min(1.0, mention_count / max(1.0, volume_anchor))
    decline_mag = min(1.0, max(0.0, -sentiment_delta) / 0.8)
    sev_norm = min(1.0, severity_weight / 1.6)
    breadth_norm = min(1.0, channel_breadth / 3.0)

    raw_score = (
        (vol_norm * 25.0)
        + (negative_share * 30.0)
        + (decline_mag * 20.0)
        + (sev_norm * 15.0)
        + (breadth_norm * 10.0)
    )
    score = round(min(100.0, max(0.0, raw_score)), 2)

    if score >= 70.0:
        tier = PriorityTier.P0_CRITICAL.value
    elif score >= 52.0:
        tier = PriorityTier.P1_HIGH.value
    elif score >= 34.0:
        tier = PriorityTier.P2_MEDIUM.value
    else:
        tier = PriorityTier.P3_LOW.value

    return score, tier


def generate_action_items(
    feedback_bundle: dict[str, Any],
    channels: list[dict[str, Any]],
    products: list[dict[str, Any]],
    sentiment_labels: list[dict[str, Any]],
    theme_assignments: list[dict[str, Any]],
    sentiment_shifts: list[dict[str, Any]],
    lifecycle_events: list[dict[str, Any]],
    anchor_dt: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Derive prioritized ActionItems and exact ActionItemEvidence rows from source records."""
    sim_year = anchor_dt.year
    chan_group_by_id = {c["channel_id"]: c["channel_group"] for c in channels}
    prod_name_by_id = {p["product_id"]: p["product_name"] for p in products}

    record_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for r in feedback_bundle["survey_responses"]:
        record_meta[(FeedbackSourceType.SURVEY_RESPONSE.value, r["response_id"])] = {
            "product_id": r["product_id"],
            "channel_group": chan_group_by_id[r["channel_id"]],
            "ts": r["submitted_at"],
            "include": r["lifecycle_state"] != "QUARANTINED",
            "fk_col": "response_id",
        }
    for rev in feedback_bundle["reviews"]:
        record_meta[(FeedbackSourceType.REVIEW.value, rev["review_id"])] = {
            "product_id": rev["product_id"],
            "channel_group": chan_group_by_id[rev["channel_id"]],
            "ts": rev["published_at"],
            "include": rev["lifecycle_state"] != "QUARANTINED",
            "fk_col": "review_id",
        }
    for msg in feedback_bundle["support_messages"]:
        record_meta[(FeedbackSourceType.SUPPORT_MESSAGE.value, msg["message_id"])] = {
            "product_id": msg["product_id"],
            "channel_group": chan_group_by_id[msg["channel_id"]],
            "ts": msg["sent_at"],
            "include": msg["lifecycle_state"] != "QUARANTINED" and msg["sender_role"] == SenderRole.CUSTOMER.value,
            "fk_col": "message_id",
        }

    sent_by_record: dict[tuple[str, str], tuple[str, float]] = {}
    for sl in sentiment_labels:
        rec_id = sl["response_id"] or sl["review_id"] or sl["message_id"]
        sent_by_record[(sl["source_type"], rec_id)] = (sl["polarity"], float(sl["sentiment_score"]))

    shift_by_cohort: dict[tuple[str, str], dict[str, Any]] = {
        (s["product_id"], s["theme_id"]): s
        for s in sentiment_shifts
        if s["product_id"] is not None and s["theme_id"] is not None
    }

    # Group unique contributing records per (product_id, theme_id)
    cohort_records: dict[tuple[str, str], list[tuple[str, str, dict[str, Any], str, float, float]]] = defaultdict(list)
    seen_cohort_rec: set[tuple[str, str, str, str]] = set()

    for asn in theme_assignments:
        if asn["theme_id"] is None:
            continue
        rec_id = asn["response_id"] or asn["review_id"] or asn["message_id"]
        key = (asn["source_type"], rec_id)
        meta = record_meta.get(key)
        sent = sent_by_record.get(key)
        if meta is None or sent is None or not meta["include"] or meta["product_id"] is None:
            continue
        cohort_key = (meta["product_id"], asn["theme_id"])
        dedup_key = (cohort_key[0], cohort_key[1], key[0], key[1])
        if dedup_key in seen_cohort_rec:
            continue
        seen_cohort_rec.add(dedup_key)
        polarity, score = sent
        cohort_records[cohort_key].append(
            (key[0], key[1], meta, polarity, score, float(asn["relevance_score"]))
        )

    total_items = max(1, len(record_meta))
    volume_anchor = max(30.0, total_items * 0.03)
    min_mentions = max(5, int(total_items * 0.004))

    action_items: list[dict[str, Any]] = []
    action_evidence: list[dict[str, Any]] = []
    new_events: list[dict[str, Any]] = list(lifecycle_events)

    act_seq = 1
    evid_seq = 1
    evt_seq = len(new_events) + 1

    candidates: list[tuple[float, tuple[str, str], dict[str, Any]]] = []
    for cohort_key, items in sorted(cohort_records.items()):
        prod_id, theme_id = cohort_key
        mention_count = len(items)
        if mention_count < min_mentions:
            continue

        neg_count = sum(
            1
            for _st, _rid, _m, pol, sc, _rel in items
            if pol == SentimentPolarity.NEGATIVE.value
            or (pol == SentimentPolarity.MIXED.value and sc < 0.0)
        )
        neg_share = round(neg_count / mention_count, 6)
        avg_sent = round(sum(sc for _st, _rid, _m, _pol, sc, _rel in items) / mention_count, 6)
        channel_groups = {m["channel_group"] for _st, _rid, m, _pol, _sc, _rel in items}
        channel_breadth = len(channel_groups)

        shift = shift_by_cohort.get(cohort_key)
        sent_delta = float(shift["delta_score"]) if shift else 0.0
        is_declining_shift = bool(
            shift and shift["is_significant"] and shift["direction"] == ShiftDirection.DECLINING.value
        )

        theme_spec = THEME_BY_ID[theme_id]
        prio_score, prio_tier = compute_priority_score(
            mention_count=mention_count,
            volume_anchor=volume_anchor,
            negative_share=neg_share,
            sentiment_delta=sent_delta,
            severity_weight=theme_spec.severity_weight,
            channel_breadth=channel_breadth,
        )

        # Emit actionable items for elevated risk/negative cohorts or significant negative shifts
        if prio_score >= 42.0 or is_declining_shift:
            max_evidence_ts = max(m["ts"] for _st, _rid, m, _pol, _sc, _rel in items)
            created_at = max(max_evidence_ts + timedelta(minutes=5), anchor_dt)
            candidates.append(
                (
                    prio_score,
                    cohort_key,
                    {
                        "prod_id": prod_id,
                        "theme_id": theme_id,
                        "shift_id": shift["shift_id"] if shift else None,
                        "mention_count": mention_count,
                        "negative_count": neg_count,
                        "channel_breadth": channel_breadth,
                        "negative_share": neg_share,
                        "avg_sentiment_score": avg_sent,
                        "sentiment_delta": sent_delta,
                        "priority_score": prio_score,
                        "priority_tier": prio_tier,
                        "created_at": created_at,
                        "items": items,
                    },
                )
            )

    # Sort descending by priority_score, then cohort key for deterministic ordering
    candidates.sort(key=lambda c: (-c[0], c[1][0], c[1][1]))

    for _score, cohort_key, data in candidates:
        prod_id, theme_id = cohort_key
        theme_spec = THEME_BY_ID[theme_id]
        prod_name = prod_name_by_id[prod_id]
        act_id = IDGenerator.action_item_id(sim_year, act_seq)
        act_seq += 1

        if data["priority_tier"] == PriorityTier.P0_CRITICAL.value:
            final_state = ActionLifecycleState.ESCALATED.value
        elif data["priority_tier"] == PriorityTier.P1_HIGH.value:
            final_state = ActionLifecycleState.IN_PROGRESS.value
        else:
            final_state = ActionLifecycleState.TRIAGED.value

        created_at = data["created_at"]
        updated_at = created_at + timedelta(minutes=30)

        action_items.append(
            {
                "action_id": act_id,
                "product_id": prod_id,
                "theme_id": theme_id,
                "shift_id": data["shift_id"],
                "title": f"[{data['priority_tier']}] {prod_name}: {theme_spec.theme_name}",
                "recommended_action": theme_spec.recommended_action,
                "owner_role": theme_spec.owner_role,
                "mention_count": data["mention_count"],
                "negative_count": data["negative_count"],
                "channel_breadth": data["channel_breadth"],
                "negative_share": data["negative_share"],
                "avg_sentiment_score": data["avg_sentiment_score"],
                "sentiment_delta": data["sentiment_delta"],
                "priority_score": data["priority_score"],
                "priority_tier": data["priority_tier"],
                "lifecycle_state": final_state,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        # Link EVERY contributing record so evidence reconciles 1:1 with mention_count
        for src_type, rec_id, meta, pol, _sc, rel_score in data["items"]:
            weight = round(min(1.0, max(0.1, rel_score * (1.0 if pol == SentimentPolarity.NEGATIVE.value else 0.6))), 4)
            action_evidence.append(
                {
                    "evidence_id": IDGenerator.action_evidence_id(evid_seq),
                    "action_id": act_id,
                    "source_type": src_type,
                    "response_id": rec_id if meta["fk_col"] == "response_id" else None,
                    "review_id": rec_id if meta["fk_col"] == "review_id" else None,
                    "message_id": rec_id if meta["fk_col"] == "message_id" else None,
                    "contribution_weight": weight,
                    "linked_at": created_at,
                }
            )
            evid_seq += 1

        # Append-only lifecycle events for ActionItem
        transitions: list[tuple[str | None, str, str, str, datetime]] = [
            (
                None,
                ActionLifecycleState.IDENTIFIED.value,
                "priority_engine",
                f"Derived from {data['mention_count']} mentions (priority={data['priority_score']})",
                created_at,
            ),
            (
                ActionLifecycleState.IDENTIFIED.value,
                ActionLifecycleState.TRIAGED.value,
                "product_ops",
                f"Routed to {theme_spec.owner_role}",
                created_at + timedelta(minutes=10),
            ),
        ]
        if final_state == ActionLifecycleState.ESCALATED.value:
            transitions.append(
                (
                    ActionLifecycleState.TRIAGED.value,
                    ActionLifecycleState.ESCALATED.value,
                    "system_admin",
                    "Escalated P0 critical priority item",
                    updated_at,
                )
            )
        elif final_state == ActionLifecycleState.IN_PROGRESS.value:
            transitions.append(
                (
                    ActionLifecycleState.TRIAGED.value,
                    ActionLifecycleState.IN_PROGRESS.value,
                    theme_spec.owner_role,
                    "Remediation workstream started",
                    updated_at,
                )
            )

        for seq_no, (f_st, t_st, actor, reason, ts) in enumerate(transitions, start=1):
            new_events.append(
                {
                    "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                    "entity_type": "ACTION_ITEM",
                    "entity_id": act_id,
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
        "action_items": action_items,
        "action_item_evidence": action_evidence,
        "lifecycle_events": new_events,
    }

