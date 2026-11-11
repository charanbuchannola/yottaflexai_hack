# Data Dictionary & Relational Schema Specification

## 1. Entity Relationship & Cardinality Overview

| Parent Entity | Child / Related Entity | Cardinality | Optionality & Notes | Bridge / Join Mechanism |
| :--- | :--- | :---: | :--- | :--- |
| `Product` | `Survey` | `1:N` | Optional (`Survey.product_id` may be `NULL` for cross-product NPS waves) | `surveys.product_id -> products.product_id` |
| `Channel` | `Survey` | `1:N` | Required | `surveys.channel_id -> channels.channel_id` |
| `Survey` | `SurveyResponse` | `1:N` | Required | `survey_responses.survey_id -> surveys.survey_id` |
| `Customer` | `SurveyResponse` | `1:N` | Required | `survey_responses.customer_id -> customers.customer_id` |
| `Customer` | `Review` | `1:N` | Optional (`Review.customer_id` is `NULL` for anonymous web reviews) | `reviews.customer_id -> customers.customer_id` |
| `Product` | `Review` | `1:N` | Required | `reviews.product_id -> products.product_id` |
| `Customer` | `SupportTicket` | `1:N` | Required | `support_tickets.customer_id -> customers.customer_id` |
| `SupportTicket` | `SupportMessage` | `1:N` | Required | `support_messages.ticket_id -> support_tickets.ticket_id` |
| `Theme` | `Theme` | `1:N` | Optional self-referential hierarchy (`parent_theme_id` nullable) | `themes.parent_theme_id -> themes.theme_id` |
| `SurveyResponse / Review / SupportMessage` | `SentimentLabel` | `1:1` | Required per feedback item (enforced via `UNIQUE` + exact-1 `CHECK`) | `sentiment_labels.{response_id, review_id, message_id}` |
| `SurveyResponse / Review / SupportMessage` | `ModelInputFeature` | `1:1` | Required per feedback item (sanitized features, zero GT leakage) | `model_inputs.{response_id, review_id, message_id}` |
| `SurveyResponse / Review / SupportMessage` | `Theme` | `N:M` | Bridge table (`feedback_theme_assignments`); `theme_id` nullable only for unmapped out-of-taxonomy anomaly rows | `feedback_theme_assignments` |
| `Product / Theme` | `SentimentShift` | `1:N` | Optional dimensions (`product_id` / `theme_id` / `channel_group`) | `sentiment_shifts.{product_id, theme_id}` |
| `SentimentShift` | `ActionItem` | `1:N` | Optional (`ActionItem.shift_id` nullable if triggered by high priority score alone) | `action_items.shift_id -> sentiment_shifts.shift_id` |
| `ActionItem` | `SurveyResponse / Review / SupportMessage` | `N:M` | Bridge table (`action_item_evidence`) preserving 100% traceability | `action_item_evidence` |
| Tracked Entities | `LifecycleEvent` | `1:N` | Append-only event journal (`entity_type`, `entity_id`, `sequence_no`) | Polymorphic ledger with FSM validation |

---

## 2. Master & Taxonomy Entities

### 2.1 `customers` (`Customer`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | `VARCHAR(20)` | Required | `^CUST-\d{6}$` | Identifier | `PK` | Must match regex and be globally unique |
| `pseudonym_handle` | `VARCHAR(32)` | Required | `acct_<seq>_<rand>` (zero PII) | Handle | `UNIQUE` | Non-empty pseudonym; no email/name/phone |
| `account_tier` | `VARCHAR(20)` | Required | `FREE`, `PRO`, `ENTERPRISE` | Enum | Non-unique | `CHECK` enum constraint |
| `segment` | `VARCHAR(20)` | Required | `CONSUMER`, `SMB`, `MID_MARKET`, `ENTERPRISE` | Enum | Non-unique | `CHECK` enum constraint |
| `region` | `VARCHAR(16)` | Required | `NA`, `EMEA`, `APAC`, `LATAM` | Enum | Non-unique | `CHECK` enum constraint |
| `preferred_language` | `VARCHAR(8)` | Required | `en`, `es`, `fr`, `de` | ISO-639-1 | Non-unique | `CHECK` enum constraint |
| `lifecycle_state` | `VARCHAR(20)` | Required | `PROSPECT`, `ACTIVE`, `AT_RISK`, `CHURNED` | State | Non-unique | `CHECK` enum constraint |
| `effective_from` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_from <= effective_to` |
| `effective_to` | `DATETIME` | Optional | UTC ISO-8601 or `NULL` | Timestamp (UTC) | Non-unique | `NULL` if active; `>= effective_from` if set |
| `created_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Valid UTC timestamp |

### 2.2 `products` (`Product`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR(16)` | Required | `^PROD-\d{3}$` | Identifier | `PK` | Must match regex and be globally unique |
| `sku` | `VARCHAR(32)` | Required | Alphanumeric SKU code | SKU | `UNIQUE` | Globally unique SKU |
| `product_name` | `VARCHAR(120)` | Required | Non-empty string | Text | Non-unique | Length 1..120 |
| `category` | `VARCHAR(40)` | Required | `CORE_PLATFORM`, `ANALYTICS_SUITE`, `MOBILE_APP`, `BILLING_ADDON`, `API_GATEWAY` | Enum | Non-unique | `CHECK` enum constraint |
| `release_version` | `VARCHAR(24)` | Required | SemVer string | Version | Non-unique | Non-empty version string |
| `lifecycle_state` | `VARCHAR(20)` | Required | `BETA`, `GA`, `SUNSETTING`, `DEPRECATED` | State | Non-unique | `CHECK` enum constraint |
| `support_sla_hours` | `INTEGER` | Required | `> 0` | Hours | Non-unique | `CHECK (support_sla_hours > 0)` |
| `effective_from` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_from <= effective_to` |
| `effective_to` | `DATETIME` | Optional | UTC ISO-8601 or `NULL` | Timestamp (UTC) | Non-unique | `NULL` or `>= effective_from` |

### 2.3 `channels` (`Channel`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | `PK` | Globally unique |
| `channel_code` | `VARCHAR(40)` | Required | `IN_APP_SURVEY`, `EMAIL_SURVEY`, `WEB_REVIEW`, `APP_STORE`, `SUPPORT_CHAT`, `SUPPORT_EMAIL`, `PHONE_TRANSCRIPT` | Code | `UNIQUE` | Globally unique channel code |
| `channel_group` | `VARCHAR(20)` | Required | `SURVEY`, `REVIEW`, `SUPPORT` | Enum | Non-unique | `CHECK` enum constraint |
| `is_public` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | Boolean |
| `requires_moderation` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | Boolean |
| `default_sla_hours` | `INTEGER` | Required | `> 0` | Hours | Non-unique | `CHECK (default_sla_hours > 0)` |
| `is_active` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | Boolean |
| `effective_from` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_from <= effective_to` |
| `effective_to` | `DATETIME` | Optional | UTC ISO-8601 or `NULL` | Timestamp (UTC) | Non-unique | `NULL` or `>= effective_from` |

### 2.4 `surveys` (`Survey`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | `VARCHAR(24)` | Required | `^SUR-\d{4}-\d{6}$` | Identifier | `PK` | Matches `SUR-2026-000001` convention |
| `product_id` | `VARCHAR(16)` | Optional | `^PROD-\d{3}$` or `NULL` | Identifier | Non-unique | FK -> `products.product_id` when non-null |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | Non-unique | FK -> `channels.channel_id` |
| `survey_type` | `VARCHAR(24)` | Required | `NPS`, `CSAT`, `CES`, `POST_ONBOARDING` | Enum | Non-unique | `CHECK` enum constraint |
| `title` | `VARCHAR(160)` | Required | Non-empty string | Text | Non-unique | Length 1..160 |
| `question_prompt` | `TEXT` | Required | Non-empty string | Text | Non-unique | Non-empty prompt |
| `lifecycle_state` | `VARCHAR(20)` | Required | `DRAFT`, `ACTIVE`, `CLOSED`, `ARCHIVED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `target_response_count` | `INTEGER` | Required | `>= 0` | Responses | Non-unique | `CHECK (>= 0)` |
| `actual_response_count` | `INTEGER` | Required | `>= 0` | Responses | Non-unique | Derived count == `COUNT(survey_responses)` |
| `effective_from` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_to >= effective_from` |
| `effective_to` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_to >= effective_from` |

### 2.5 `themes` (`Theme`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `theme_id` | `VARCHAR(20)` | Required | `^THEME-\d{6}$` | Identifier | `PK` | Matches `THEME-000001` convention |
| `theme_code` | `VARCHAR(64)` | Required | Uppercase snake code | Code | `UNIQUE` | Globally unique governed theme code |
| `theme_name` | `VARCHAR(120)` | Required | Human-readable label | Text | Non-unique | Non-empty |
| `parent_theme_id` | `VARCHAR(20)` | Optional | `^THEME-\d{6}$` or `NULL` | Identifier | Non-unique | Self-FK -> `themes.theme_id` |
| `category` | `VARCHAR(40)` | Required | `PERFORMANCE_RELIABILITY`, `BILLING_PRICING`, `SUPPORT_EXPERIENCE`, `UX_ONBOARDING`, `PRODUCT_QUALITY`, `INTEGRATIONS`, `SECURITY_PRIVACY` | Enum | Non-unique | `CHECK` enum constraint |
| `severity_weight` | `FLOAT` | Required | `(0.0, 2.5]` | Multiplier | Non-unique | `CHECK (> 0.0 AND <= 2.5)` |
| `keywords_json` | `TEXT` | Required | JSON dictionary by language | JSON | Non-unique | Valid JSON map `{lang: [keywords]}` |
| `is_active` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | Active taxonomy flag |
| `effective_from` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `effective_to IS NULL OR effective_to >= effective_from` |
| `effective_to` | `DATETIME` | Optional | UTC ISO-8601 or `NULL` | Timestamp (UTC) | Non-unique | `NULL` or `>= effective_from` |

---

## 3. Transactional Feedback Entities

### 3.1 `survey_responses` (`SurveyResponse`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `response_id` | `VARCHAR(40)` | Required | `^RESP-SUR-\d{4}-\d{6}-\d{3,}$` | Identifier | `PK` | Matches `RESP-<survey-id>-001` convention |
| `survey_id` | `VARCHAR(24)` | Required | `^SUR-\d{4}-\d{6}$` | Identifier | Non-unique | FK -> `surveys.survey_id` |
| `customer_id` | `VARCHAR(20)` | Required | `^CUST-\d{6}$` | Identifier | Non-unique | FK -> `customers.customer_id` |
| `product_id` | `VARCHAR(16)` | Optional | `^PROD-\d{3}$` or `NULL` | Identifier | Non-unique | FK -> `products.product_id` when non-null |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | Non-unique | FK -> `channels.channel_id` |
| `rating_score` | `INTEGER` | Required | `[0..10]` (NPS) or `[1..5]` (CSAT/CES) | Points | Non-unique | `CHECK (rating_score BETWEEN 0 AND 10)` |
| `normalized_score` | `FLOAT` | Required | `[0.0, 1.0]` | Ratio | Non-unique | Derived strictly from `rating_score` & `survey_type` |
| `response_text` | `TEXT` | Required | Non-empty privacy-safe string | Text | Non-unique | Scanned for PII (`VAL-ANOM-003`) |
| `language` | `VARCHAR(8)` | Required | `en`, `es`, `fr`, `de` | ISO-639-1 | Non-unique | `CHECK` enum constraint |
| `submitted_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Within `[Survey.effective_from, Survey.effective_to]` |
| `lifecycle_state` | `VARCHAR(20)` | Required | `SUBMITTED`, `ANALYZED`, `VERIFIED`, `FLAGGED`, `QUARANTINED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `content_hash` | `VARCHAR(64)` | Required | SHA-256 hex digest | Hash | Non-unique | Duplicate check `(survey_id, customer_id, content_hash)` |

### 3.2 `reviews` (`Review`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `review_id` | `VARCHAR(24)` | Required | `^REV-\d{4}-\d{6}$` | Identifier | `PK` | Matches `REV-2026-000001` convention |
| `customer_id` | `VARCHAR(20)` | Optional | `^CUST-\d{6}$` or `NULL` | Identifier | Non-unique | FK -> `customers.customer_id` (`NULL` for anonymous) |
| `product_id` | `VARCHAR(16)` | Required | `^PROD-\d{3}$` | Identifier | Non-unique | FK -> `products.product_id` |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | Non-unique | FK -> `channels.channel_id` |
| `star_rating` | `INTEGER` | Required | `[1..5]` | Stars | Non-unique | `CHECK (star_rating BETWEEN 1 AND 5)` |
| `title` | `VARCHAR(200)` | Required | Non-empty string | Text | Non-unique | Length 1..200 |
| `review_text` | `TEXT` | Required | Non-empty privacy-safe string | Text | Non-unique | Scanned for PII (`VAL-ANOM-003`) |
| `language` | `VARCHAR(8)` | Required | `en`, `es`, `fr`, `de` | ISO-639-1 | Non-unique | `CHECK` enum constraint |
| `verified_purchase` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | Boolean |
| `helpful_votes` | `INTEGER` | Required | `>= 0` | Votes | Non-unique | `CHECK (helpful_votes >= 0)` |
| `published_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Valid UTC timestamp |
| `lifecycle_state` | `VARCHAR(20)` | Required | `SUBMITTED`, `ANALYZED`, `VERIFIED`, `FLAGGED`, `QUARANTINED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `content_hash` | `VARCHAR(64)` | Required | SHA-256 hex digest | Hash | Non-unique | SHA-256 of normalized `review_text` |

### 3.3 `support_tickets` (`SupportTicket`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ticket_id` | `VARCHAR(24)` | Required | `^TKT-\d{4}-\d{6}$` | Identifier | `PK` | Globally unique parent ticket ID |
| `customer_id` | `VARCHAR(20)` | Required | `^CUST-\d{6}$` | Identifier | Non-unique | FK -> `customers.customer_id` |
| `product_id` | `VARCHAR(16)` | Required | `^PROD-\d{3}$` | Identifier | Non-unique | FK -> `products.product_id` |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | Non-unique | FK -> `channels.channel_id` |
| `subject` | `VARCHAR(200)` | Required | Non-empty string | Text | Non-unique | Length 1..200 |
| `priority` | `VARCHAR(16)` | Required | `LOW`, `MEDIUM`, `HIGH`, `URGENT` | Enum | Non-unique | `CHECK` enum constraint |
| `lifecycle_state` | `VARCHAR(20)` | Required | `OPEN`, `TRIAGED`, `IN_PROGRESS`, `ESCALATED`, `RESOLVED`, `CLOSED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `message_count` | `INTEGER` | Required | `>= 0` | Messages | Non-unique | Reconciled == `COUNT(support_messages)` |
| `opened_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `resolved_at IS NULL OR resolved_at >= opened_at` |
| `resolved_at` | `DATETIME` | Optional | UTC ISO-8601 or `NULL` | Timestamp (UTC) | Non-unique | `NULL` if open/escalated; `>= opened_at` otherwise |

### 3.4 `support_messages` (`SupportMessage`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `message_id` | `VARCHAR(40)` | Required | `^MSG-TKT-\d{4}-\d{6}-\d{3,}$` | Identifier | `PK` | Matches `MSG-<ticket-id>-001` convention |
| `ticket_id` | `VARCHAR(24)` | Required | `^TKT-\d{4}-\d{6}$` | Identifier | Non-unique | FK -> `support_tickets.ticket_id` |
| `customer_id` | `VARCHAR(20)` | Required | `^CUST-\d{6}$` | Identifier | Non-unique | FK -> `customers.customer_id` |
| `product_id` | `VARCHAR(16)` | Required | `^PROD-\d{3}$` | Identifier | Non-unique | FK -> `products.product_id` |
| `channel_id` | `VARCHAR(16)` | Required | `^CHN-\d{3}$` | Identifier | Non-unique | FK -> `channels.channel_id` |
| `sender_role` | `VARCHAR(20)` | Required | `CUSTOMER`, `SUPPORT_AGENT`, `SYSTEM_BOT` | Enum | Non-unique | `CHECK` enum constraint |
| `sequence_no` | `INTEGER` | Required | `>= 1` | Order | Non-unique | Sequential turn index within ticket |
| `message_text` | `TEXT` | Required | Non-empty privacy-safe string | Text | Non-unique | Scanned for PII (`VAL-ANOM-003`) |
| `language` | `VARCHAR(8)` | Required | `en`, `es`, `fr`, `de` | ISO-639-1 | Non-unique | `CHECK` enum constraint |
| `sent_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Must satisfy `sent_at >= ticket.opened_at` |
| `lifecycle_state` | `VARCHAR(20)` | Required | `SUBMITTED`, `ANALYZED`, `VERIFIED`, `FLAGGED`, `QUARANTINED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `content_hash` | `VARCHAR(64)` | Required | SHA-256 hex digest | Hash | Non-unique | SHA-256 of normalized `message_text` |

---

## 4. Analytical, Bridge, Derived Priority & Audit Entities

### 4.1 `sentiment_labels` (`SentimentLabel`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `label_id` | `VARCHAR(24)` | Required | `^SENT-\d{6}$` | Identifier | `PK` | Globally unique |
| `source_type` | `VARCHAR(24)` | Required | `SURVEY_RESPONSE`, `REVIEW`, `SUPPORT_MESSAGE` | Enum | Non-unique | Matches populated FK column |
| `response_id` | `VARCHAR(40)` | Optional | FK -> `survey_responses.response_id` | Identifier | `UNIQUE` | Exactly one of `{response_id, review_id, message_id}` non-null |
| `review_id` | `VARCHAR(24)` | Optional | FK -> `reviews.review_id` | Identifier | `UNIQUE` | Exactly one parent FK non-null |
| `message_id` | `VARCHAR(40)` | Optional | FK -> `support_messages.message_id` | Identifier | `UNIQUE` | Exactly one parent FK non-null |
| `polarity` | `VARCHAR(16)` | Required | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED` | Enum | Non-unique | Checked against text/rating consistency (`VAL-ANOM-001`) |
| `sentiment_score` | `FLOAT` | Required | `[-1.0, +1.0]` | Polarity Score | Non-unique | `CHECK (>= -1.0 AND <= 1.0)` |
| `confidence` | `FLOAT` | Required | `[0.0, 1.0]` | Probability | Non-unique | `CHECK (>= 0.0 AND <= 1.0)` |
| `labeling_method` | `VARCHAR(24)` | Required | `AUTOMATED_NLP`, `INGESTED_PROVIDER` | Enum | Non-unique | `CHECK` enum constraint |
| `rationale` | `TEXT` | Optional | Decision explanation or `NULL` | Text | Non-unique | Required for overrides; missing rationale + contradiction flagged |
| `labeled_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Valid UTC timestamp |
| `lifecycle_state` | `VARCHAR(20)` | Required | `FeedbackLifecycleState` | State | Non-unique | Matches feedback item state |

### 4.2 `feedback_theme_assignments` (`FeedbackThemeAssignment` — N:M Bridge)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `VARCHAR(24)` | Required | `^THM-ASN-\d{6}$` | Identifier | `PK` | Globally unique |
| `source_type` | `VARCHAR(24)` | Required | `SURVEY_RESPONSE`, `REVIEW`, `SUPPORT_MESSAGE` | Enum | Non-unique | Matches populated FK column |
| `response_id` | `VARCHAR(40)` | Optional | FK -> `survey_responses.response_id` | Identifier | Non-unique | Exactly one parent FK non-null |
| `review_id` | `VARCHAR(24)` | Optional | FK -> `reviews.review_id` | Identifier | Non-unique | Exactly one parent FK non-null |
| `message_id` | `VARCHAR(40)` | Optional | FK -> `support_messages.message_id` | Identifier | Non-unique | Exactly one parent FK non-null |
| `theme_id` | `VARCHAR(20)` | Optional | FK -> `themes.theme_id` | Identifier | Non-unique | `NULL` only on injected `THEME_OUTSIDE_TAXONOMY` anomalies |
| `raw_theme_code` | `VARCHAR(64)` | Required | Theme code string | Code | Non-unique | Must match active `themes.theme_code` (`VAL-ANOM-004`) |
| `relevance_score` | `FLOAT` | Required | `[0.0, 1.0]` | Score | Non-unique | `CHECK (>= 0.0 AND <= 1.0)` |
| `assignment_method` | `VARCHAR(24)` | Required | `AUTOMATED_NLP`, `INGESTED_PROVIDER` | Enum | Non-unique | `CHECK` enum constraint |
| `assigned_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Valid UTC timestamp |

### 4.3 `sentiment_shifts` (`SentimentShift`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shift_id` | `VARCHAR(24)` | Required | `^SHIFT-\d{4}-\d{6}$` | Identifier | `PK` | Globally unique |
| `product_id` | `VARCHAR(16)` | Optional | FK -> `products.product_id` | Identifier | Non-unique | `NULL` for cross-product rollup |
| `theme_id` | `VARCHAR(20)` | Optional | FK -> `themes.theme_id` | Identifier | Non-unique | `NULL` for overall product rollup |
| `channel_group` | `VARCHAR(20)` | Optional | `SURVEY`, `REVIEW`, `SUPPORT` or `NULL` | Enum | Non-unique | `CHECK` enum constraint |
| `baseline_start` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `baseline_start <= baseline_end` |
| `baseline_end` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `baseline_end <= current_start` |
| `current_start` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `current_start <= current_end` |
| `current_end` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `>= current_start` |
| `baseline_count` | `INTEGER` | Required | `>= 0` | Records | Non-unique | Derived count of baseline items |
| `current_count` | `INTEGER` | Required | `>= 0` | Records | Non-unique | Derived count of current items |
| `baseline_avg_score` | `FLOAT` | Required | `[-1.0, +1.0]` | Polarity Score | Non-unique | Derived mean of baseline `sentiment_score` |
| `current_avg_score` | `FLOAT` | Required | `[-1.0, +1.0]` | Polarity Score | Non-unique | Derived mean of current `sentiment_score` |
| `delta_score` | `FLOAT` | Required | `[-2.0, +2.0]` | Score Delta | Non-unique | Reconciled == `current_avg_score - baseline_avg_score` |
| `z_score` | `FLOAT` | Required | Real float | Std Devs | Non-unique | Welch two-sample z-statistic |
| `direction` | `VARCHAR(16)` | Required | `IMPROVING`, `DECLINING`, `STABLE` | Enum | Non-unique | Derived from `delta_score` & `is_significant` |
| `is_significant` | `BOOLEAN` | Required | `true` / `false` | Flag | Non-unique | `abs(delta_score) >= 0.30 AND abs(z_score) >= 2.8` |
| `detected_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Anchor detection timestamp |

### 4.4 `action_items` (`ActionItem`)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `action_id` | `VARCHAR(24)` | Required | `^ACT-\d{4}-\d{6}$` | Identifier | `PK` | Globally unique |
| `product_id` | `VARCHAR(16)` | Optional | FK -> `products.product_id` | Identifier | Non-unique | Target product or `NULL` |
| `theme_id` | `VARCHAR(20)` | Required | FK -> `themes.theme_id` | Identifier | Non-unique | Target governed theme |
| `shift_id` | `VARCHAR(24)` | Optional | FK -> `sentiment_shifts.shift_id` | Identifier | Non-unique | Associated shift if present |
| `title` | `VARCHAR(200)` | Required | `[TIER] Product: Theme` | Text | Non-unique | Non-empty |
| `recommended_action` | `TEXT` | Required | Actionable remediation text | Text | Non-unique | Derived from theme remediation playbook |
| `owner_role` | `VARCHAR(64)` | Required | Owning team name | Role | Non-unique | Derived from theme owner |
| `mention_count` | `INTEGER` | Required | `>= 1` | Mentions | Non-unique | Reconciled == `COUNT(action_item_evidence)` |
| `negative_count` | `INTEGER` | Required | `0 <= negative_count <= mention_count` | Mentions | Non-unique | Derived count of negative/neg-mixed evidence |
| `channel_breadth` | `INTEGER` | Required | `[1..3]` | Channel Groups | Non-unique | Distinct channel groups in evidence |
| `negative_share` | `FLOAT` | Required | `[0.0, 1.0]` | Ratio | Non-unique | Reconciled == `negative_count / mention_count` |
| `avg_sentiment_score` | `FLOAT` | Required | `[-1.0, +1.0]` | Polarity Score | Non-unique | Derived mean over evidence items |
| `sentiment_delta` | `FLOAT` | Required | `[-2.0, +2.0]` | Score Delta | Non-unique | Linked shift delta or `0.0` |
| `priority_score` | `FLOAT` | Required | `[0.0, 100.0]` | Priority Points | Non-unique | Reconciled with `BR-PRIO-001` formula |
| `priority_tier` | `VARCHAR(16)` | Required | `P0_CRITICAL`, `P1_HIGH`, `P2_MEDIUM`, `P3_LOW` | Enum | Non-unique | Derived strictly from `priority_score` |
| `lifecycle_state` | `VARCHAR(20)` | Required | `IDENTIFIED`, `TRIAGED`, `IN_PROGRESS`, `VERIFIED`, `CLOSED`, `ESCALATED` | State | Non-unique | Reconciled with `lifecycle_events` FSM |
| `created_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `updated_at >= created_at` |
| `updated_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | `>= created_at` |

### 4.5 `action_item_evidence` (`ActionItemEvidence` — N:M Traceability Bridge)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `evidence_id` | `VARCHAR(24)` | Required | `^EVID-\d{6}$` | Identifier | `PK` | Globally unique |
| `action_id` | `VARCHAR(24)` | Required | FK -> `action_items.action_id` | Identifier | Non-unique | Parent action item |
| `source_type` | `VARCHAR(24)` | Required | `SURVEY_RESPONSE`, `REVIEW`, `SUPPORT_MESSAGE` | Enum | Non-unique | Matches populated FK |
| `response_id` | `VARCHAR(40)` | Optional | FK -> `survey_responses.response_id` | Identifier | Non-unique | Exactly one feedback FK non-null |
| `review_id` | `VARCHAR(24)` | Optional | FK -> `reviews.review_id` | Identifier | Non-unique | Exactly one feedback FK non-null |
| `message_id` | `VARCHAR(40)` | Optional | FK -> `support_messages.message_id` | Identifier | Non-unique | Exactly one feedback FK non-null |
| `contribution_weight` | `FLOAT` | Required | `(0.0, 1.0]` | Weight | Non-unique | `CHECK (> 0.0 AND <= 1.0)` |
| `linked_at` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Valid UTC timestamp |

### 4.6 `model_inputs` (`ModelInputFeature` — Leakage-Safe Input View)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `input_id` | `VARCHAR(24)` | Required | `^INP-\d{6}$` | Identifier | `PK` | Globally unique |
| `source_type` | `VARCHAR(24)` | Required | `SURVEY_RESPONSE`, `REVIEW`, `SUPPORT_MESSAGE` | Enum | Non-unique | Matches populated FK |
| `response_id` / `review_id` / `message_id` | `VARCHAR` | Optional | Parent feedback FKs | Identifier | `UNIQUE` | Exactly one non-null; 1:1 with source record |
| `product_id` | `VARCHAR(16)` | Optional | FK -> `products.product_id` | Identifier | Non-unique | Nullable |
| `channel_id` | `VARCHAR(16)` | Required | FK -> `channels.channel_id` | Identifier | Non-unique | Non-null |
| `language` | `VARCHAR(8)` | Required | `en`, `es`, `fr`, `de` | ISO-639-1 | Non-unique | `CHECK` enum |
| `event_timestamp` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Source timestamp |
| `text_payload` | `TEXT` | Required | Text without gold tokens | Text | Non-unique | Checked by `VAL-ANOM-005` leakage scanner |
| `rating_signal` | `FLOAT` | Optional | `[0.0, 1.0]` or `NULL` | Ratio | Non-unique | Normalized rating if available |
| `split_partition` | `VARCHAR(16)` | Required | `TRAIN`, `INFERENCE`, `TEST` | Enum | Non-unique | `TEST` partition blocked in inference inputs (`VAL-ANOM-005`) |
| `extra_features_json` | `TEXT` | Required | JSON metadata | JSON | Non-unique | Must not contain gold/ground-truth keys |

### 4.7 `lifecycle_events` (`LifecycleEvent` — Append-Only State History)
| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | `VARCHAR(24)` | Required | `^EVT-\d{4}-\d{6}$` | Identifier | `PK` | Globally unique |
| `entity_type` | `VARCHAR(24)` | Required | `SURVEY`, `SURVEY_RESPONSE`, `REVIEW`, `SUPPORT_TICKET`, `SUPPORT_MESSAGE`, `ACTION_ITEM` | Enum | Non-unique | `CHECK` enum constraint |
| `entity_id` | `VARCHAR(48)` | Required | Entity PK | Identifier | Non-unique | Targets tracked entity |
| `from_state` | `VARCHAR(32)` | Optional | Previous FSM state or `NULL` | State | Non-unique | `NULL` only when `sequence_no == 1` |
| `to_state` | `VARCHAR(32)` | Required | Target FSM state | State | Non-unique | Must be permitted by `FSM_TRANSITIONS` |
| `actor` | `VARCHAR(64)` | Required | Actor/system identifier | Role | Non-unique | Non-empty |
| `reason` | `TEXT` | Required | Audit justification | Text | Non-unique | Non-empty |
| `event_timestamp` | `DATETIME` | Required | UTC ISO-8601 | Timestamp (UTC) | Non-unique | Monotonically non-decreasing per entity |
| `sequence_no` | `INTEGER` | Required | `>= 1` | Order | Non-unique | Contiguous `1, 2, ...` per `(entity_type, entity_id)` |

