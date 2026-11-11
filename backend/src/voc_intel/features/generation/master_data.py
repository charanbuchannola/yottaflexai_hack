"""Deterministic master data generator: Channels, Products, Themes, Customers, Surveys."""

from datetime import datetime, timedelta
import json
import random
from typing import Any

from voc_intel.core.config import ProfileConfig, settings
from voc_intel.core.identifiers import IDGenerator
from voc_intel.db.base import (
    AccountTier,
    ChannelGroup,
    CustomerLifecycleState,
    CustomerSegment,
    LanguageCode,
    ProductCategory,
    ProductLifecycleState,
    Region,
    SurveyLifecycleState,
    SurveyType,
)
from voc_intel.features.generation.templates import THEME_TAXONOMY

CHANNEL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "channel_id": "CHN-001",
        "channel_code": "IN_APP_SURVEY",
        "channel_group": ChannelGroup.SURVEY.value,
        "is_public": False,
        "requires_moderation": False,
        "default_sla_hours": 48,
    },
    {
        "channel_id": "CHN-002",
        "channel_code": "EMAIL_SURVEY",
        "channel_group": ChannelGroup.SURVEY.value,
        "is_public": False,
        "requires_moderation": False,
        "default_sla_hours": 72,
    },
    {
        "channel_id": "CHN-003",
        "channel_code": "WEB_REVIEW",
        "channel_group": ChannelGroup.REVIEW.value,
        "is_public": True,
        "requires_moderation": True,
        "default_sla_hours": 24,
    },
    {
        "channel_id": "CHN-004",
        "channel_code": "APP_STORE",
        "channel_group": ChannelGroup.REVIEW.value,
        "is_public": True,
        "requires_moderation": True,
        "default_sla_hours": 24,
    },
    {
        "channel_id": "CHN-005",
        "channel_code": "SUPPORT_CHAT",
        "channel_group": ChannelGroup.SUPPORT.value,
        "is_public": False,
        "requires_moderation": False,
        "default_sla_hours": 4,
    },
    {
        "channel_id": "CHN-006",
        "channel_code": "SUPPORT_EMAIL",
        "channel_group": ChannelGroup.SUPPORT.value,
        "is_public": False,
        "requires_moderation": False,
        "default_sla_hours": 12,
    },
    {
        "channel_id": "CHN-007",
        "channel_code": "PHONE_TRANSCRIPT",
        "channel_group": ChannelGroup.SUPPORT.value,
        "is_public": False,
        "requires_moderation": False,
        "default_sla_hours": 8,
    },
)

PRODUCT_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "sku": "YF-CORE-40",
        "product_name": "YottaFlex Core Workspace",
        "category": ProductCategory.CORE_PLATFORM.value,
        "release_version": "4.3.0",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 8,
    },
    {
        "sku": "YF-ANLY-22",
        "product_name": "YottaFlex Analytics Suite",
        "category": ProductCategory.ANALYTICS_SUITE.value,
        "release_version": "2.8.1",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 12,
    },
    {
        "sku": "YF-MOB-31",
        "product_name": "YottaFlex Mobile Companion",
        "category": ProductCategory.MOBILE_APP.value,
        "release_version": "3.4.2",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 24,
    },
    {
        "sku": "YF-BILL-19",
        "product_name": "YottaFlex Billing & Invoicing",
        "category": ProductCategory.BILLING_ADDON.value,
        "release_version": "1.9.4",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 6,
    },
    {
        "sku": "YF-API-50",
        "product_name": "YottaFlex API Gateway",
        "category": ProductCategory.API_GATEWAY.value,
        "release_version": "5.1.0",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 4,
    },
    {
        "sku": "YF-CORE-LITE",
        "product_name": "YottaFlex Team Starter",
        "category": ProductCategory.CORE_PLATFORM.value,
        "release_version": "4.3.0",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 24,
    },
    {
        "sku": "YF-ANLY-RT",
        "product_name": "YottaFlex Real-Time Pulse",
        "category": ProductCategory.ANALYTICS_SUITE.value,
        "release_version": "1.2.0-beta",
        "lifecycle_state": ProductLifecycleState.BETA.value,
        "support_sla_hours": 12,
    },
    {
        "sku": "YF-MOB-TAB",
        "product_name": "YottaFlex Field Tablet",
        "category": ProductCategory.MOBILE_APP.value,
        "release_version": "2.1.0",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 16,
    },
    {
        "sku": "YF-BILL-TAX",
        "product_name": "YottaFlex Global Tax Sync",
        "category": ProductCategory.BILLING_ADDON.value,
        "release_version": "1.4.0",
        "lifecycle_state": ProductLifecycleState.GA.value,
        "support_sla_hours": 8,
    },
    {
        "sku": "YF-API-HOOK",
        "product_name": "YottaFlex Event Relay",
        "category": ProductCategory.API_GATEWAY.value,
        "release_version": "2.0.1",
        "lifecycle_state": ProductLifecycleState.SUNSETTING.value,
        "support_sla_hours": 8,
    },
)


def generate_master_data(
    rng: random.Random,
    profile_cfg: ProfileConfig,
    anchor: datetime | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Generate deterministic parent/master records in dependency order."""
    anchor_dt = (anchor or settings.simulation_anchor).replace(tzinfo=None)
    effective_base = anchor_dt - timedelta(days=365)
    window_start = anchor_dt - timedelta(days=profile_cfg.simulation_days)
    sim_year = anchor_dt.year

    # 1. Channels
    channels: list[dict[str, Any]] = []
    for ch in CHANNEL_CATALOG:
        channels.append(
            {
                **ch,
                "is_active": True,
                "effective_from": effective_base,
                "effective_to": None,
            }
        )

    # 2. Products
    products: list[dict[str, Any]] = []
    for idx in range(profile_cfg.products_count):
        spec = PRODUCT_CATALOG[idx % len(PRODUCT_CATALOG)]
        products.append(
            {
                "product_id": IDGenerator.product_id(idx + 1),
                "sku": spec["sku"] if idx < len(PRODUCT_CATALOG) else f"{spec['sku']}-{idx + 1}",
                "product_name": spec["product_name"],
                "category": spec["category"],
                "release_version": spec["release_version"],
                "lifecycle_state": spec["lifecycle_state"],
                "support_sla_hours": spec["support_sla_hours"],
                "effective_from": effective_base,
                "effective_to": None,
            }
        )

    # 3. Themes (governed taxonomy)
    themes: list[dict[str, Any]] = []
    for spec in THEME_TAXONOMY:
        themes.append(
            {
                "theme_id": spec.theme_id,
                "theme_code": spec.theme_code,
                "theme_name": spec.theme_name,
                "parent_theme_id": spec.parent_theme_id,
                "category": spec.category.value,
                "severity_weight": spec.severity_weight,
                "keywords_json": json.dumps(spec.keywords_by_lang, ensure_ascii=False, sort_keys=True),
                "is_active": True,
                "effective_from": effective_base,
                "effective_to": None,
            }
        )

    # 4. Customers (pseudonymized, zero PII)
    tiers = [AccountTier.FREE.value, AccountTier.PRO.value, AccountTier.ENTERPRISE.value]
    tier_weights = [0.35, 0.45, 0.20]
    segments = [
        CustomerSegment.CONSUMER.value,
        CustomerSegment.SMB.value,
        CustomerSegment.MID_MARKET.value,
        CustomerSegment.ENTERPRISE.value,
    ]
    regions = [Region.NA.value, Region.EMEA.value, Region.APAC.value, Region.LATAM.value]
    langs = [LanguageCode.EN.value, LanguageCode.ES.value, LanguageCode.FR.value, LanguageCode.DE.value]
    lang_weights = [0.80, 0.08, 0.06, 0.06]
    cust_states = [
        CustomerLifecycleState.PROSPECT.value,
        CustomerLifecycleState.ACTIVE.value,
        CustomerLifecycleState.AT_RISK.value,
        CustomerLifecycleState.CHURNED.value,
    ]
    cust_state_weights = [0.10, 0.72, 0.13, 0.05]

    customers: list[dict[str, Any]] = []
    for idx in range(1, profile_cfg.customers_count + 1):
        cust_id = IDGenerator.customer_id(idx)
        created_offset_days = rng.randint(1, 360)
        created_at = anchor_dt - timedelta(days=created_offset_days, hours=rng.randint(0, 23))
        state = rng.choices(cust_states, weights=cust_state_weights, k=1)[0]
        eff_to = (
            created_at + timedelta(days=rng.randint(30, 180))
            if state == CustomerLifecycleState.CHURNED.value
            else None
        )
        if eff_to is not None and eff_to > anchor_dt:
            eff_to = anchor_dt
        customers.append(
            {
                "customer_id": cust_id,
                "pseudonym_handle": f"acct_{idx:06d}_{rng.randrange(1000, 9999)}",
                "account_tier": rng.choices(tiers, weights=tier_weights, k=1)[0],
                "segment": rng.choice(segments),
                "region": rng.choice(regions),
                "preferred_language": rng.choices(langs, weights=lang_weights, k=1)[0],
                "lifecycle_state": state,
                "effective_from": created_at,
                "effective_to": eff_to,
                "created_at": created_at,
            }
        )

    # 5. Surveys (each survey covers the simulation window; some product-specific, some cross-product NULL)
    survey_channels = [c["channel_id"] for c in channels if c["channel_group"] == ChannelGroup.SURVEY.value]
    survey_types = [
        SurveyType.NPS.value,
        SurveyType.CSAT.value,
        SurveyType.CES.value,
        SurveyType.POST_ONBOARDING.value,
    ]
    surveys: list[dict[str, Any]] = []
    lifecycle_events: list[dict[str, Any]] = []
    evt_seq = 1

    target_per_survey = max(1, profile_cfg.survey_responses_count // profile_cfg.surveys_count)
    for idx in range(1, profile_cfg.surveys_count + 1):
        survey_id = IDGenerator.survey_id(sim_year, idx)
        # Every 5th survey is cross-product (product_id=None) to exercise optional relationship
        product_id = None if idx % 5 == 0 else products[(idx - 1) % len(products)]["product_id"]
        channel_id = survey_channels[(idx - 1) % len(survey_channels)]
        s_type = survey_types[(idx - 1) % len(survey_types)]
        eff_from = window_start - timedelta(days=5)
        eff_to = anchor_dt + timedelta(days=5)

        surveys.append(
            {
                "survey_id": survey_id,
                "product_id": product_id,
                "channel_id": channel_id,
                "survey_type": s_type,
                "title": f"{s_type} Pulse Wave {idx:02d}" + (f" ({product_id})" if product_id else " (Platform-Wide)"),
                "question_prompt": (
                    "How likely are you to recommend YottaFlex and what shaped your experience?"
                    if s_type == SurveyType.NPS.value
                    else "How satisfied are you with your recent workflow experience?"
                ),
                "lifecycle_state": SurveyLifecycleState.ACTIVE.value,
                "target_response_count": target_per_survey,
                "actual_response_count": 0,  # Reconciled from generated child responses
                "effective_from": eff_from,
                "effective_to": eff_to,
            }
        )
        # Record survey lifecycle events: DRAFT -> ACTIVE
        lifecycle_events.append(
            {
                "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                "entity_type": "SURVEY",
                "entity_id": survey_id,
                "from_state": None,
                "to_state": SurveyLifecycleState.DRAFT.value,
                "actor": "marketing_ops",
                "reason": "Survey campaign drafted",
                "event_timestamp": eff_from - timedelta(days=2),
                "sequence_no": 1,
            }
        )
        evt_seq += 1
        lifecycle_events.append(
            {
                "event_id": IDGenerator.lifecycle_event_id(sim_year, evt_seq),
                "entity_type": "SURVEY",
                "entity_id": survey_id,
                "from_state": SurveyLifecycleState.DRAFT.value,
                "to_state": SurveyLifecycleState.ACTIVE.value,
                "actor": "marketing_ops",
                "reason": "Survey campaign published to target channel",
                "event_timestamp": eff_from,
                "sequence_no": 2,
            }
        )
        evt_seq += 1

    return {
        "channels": channels,
        "products": products,
        "themes": themes,
        "customers": customers,
        "surveys": surveys,
        "lifecycle_events": lifecycle_events,
    }

