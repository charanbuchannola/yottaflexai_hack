# YottaFlex Voice of Customer (VoC) Intelligence Platform

An enterprise 3-tier **Next.js + FastAPI + SQLAlchemy/SQLite** platform that combines **survey responses**, **product reviews**, and **support messages** to identify recurring themes, detect statistical temporal sentiment shifts, prioritize service action items with full source-record traceability, and enforce automated relational, lifecycle, privacy, and data-leakage validation.

---

## 1. Business Context, Objectives & Primary Actors

- **Business Problem**: Combine multi-channel customer feedback (`SurveyResponse`, `Review`, `SupportMessage`) into governed theme taxonomies (`Theme`), calibrated sentiment assessments (`SentimentLabel`), statistical temporal shifts (`SentimentShift`), and prioritized remediation workflows (`ActionItem`).
- **Objectives**:
  - Expose key analytical decisions, priority scoring weights, and data-quality exceptions transparently.
  - Preserve full end-to-end traceability from every trend and `ActionItem` back to its exact contributing source records (`ActionItemEvidence`) and append-only state history (`LifecycleEvent`).
  - Produce measurable evaluation metrics on a segregated human-reviewed evaluation holdout set with zero feature leakage.
- **Primary Actors & Interactions**:
  - **Customer / Prospect**: Submits NPS/CSAT/CES survey responses, product reviews (authenticated or anonymous), and multi-turn support tickets.
  - **Marketing / Sales Operations**: Launches survey waves, monitors cross-channel themes and sentiment shifts via Next.js (`Themes`, `Sentiment Shifts`) and `GET /api/v1/themes`, `GET /api/v1/shifts`.
  - **Support Agent**: Triages support tickets (`OPEN -> TRIAGED -> IN_PROGRESS -> ESCALATED -> RESOLVED -> CLOSED`), records messages (`MSG-<ticket-id>-001`), and tracks escalations.
  - **Analyst**: Audits holdout sentiment/theme/shift metrics, inspects `ActionItem` rankings and contributing source evidence (`GET /api/v1/priorities/{action_id}/traceability`), and verifies zero ground-truth leakage.
  - **System Administrator**: Runs deterministic CLI workflows (`generate-starter`, `generate-full`, `validate`, `evaluate`, `reproduce`), audits live anomaly gates (`GET /api/v1/anomalies`), and executes FSM transitions (`POST /api/v1/priorities/{action_id}/transition`).

---

## 2. Enterprise 3-Tier Architecture

```text
+-------------------------------------------------------------------------+
|                    FRONTEND TIER (frontend/ - Next.js 15)               |
|  App Router (TypeScript) · Feature Modules: OverviewPanel,              |
|  ThemesExplorer, ShiftsMonitor, PrioritiesWorkbench, AnomaliesAudit     |
|  HTTP-only Typed REST Client -> /api/backend/* proxy rewrite            |
+-------------------------------------------------------------------------+
                                    |  HTTP / JSON (CORS + /api/backend)
                                    v
+-------------------------------------------------------------------------+
|                 BACKEND TIER (backend/ - Python 3.12 + FastAPI)         |
|  1. Presentation : api/v1/ (Thin Routers + DI, zero ORM/SQL) & cli/     |
|  2. Services     : services/ (Business Rules, FSM, Orchestration)       |
|  3. Features     : features/ (generation, nlp, shifts, priorities,      |
|                    lifecycle, validation, evaluation, export)           |
|  4. Repositories : repositories/ (All SQLAlchemy Session/Queries)       |
|  5. Persistence  : db/ (16 Normalized SQLAlchemy 2.0 ORM Tables)        |
+-------------------------------------------------------------------------+
                                    |  SQLAlchemy 2.0 + FK Enforcement
                                    v
+-------------------------------------------------------------------------+
|               DATABASE TIER (database/ - Relational & GT)               |
|  schema/schema.sql · migrations/001_initial_schema.sql · seeds/seed.sql |
|  voc_intelligence.db · ground_truth/ground_truth.{csv,json} (isolated)  |
+-------------------------------------------------------------------------+
```

- **Strict Layer Boundaries (Statically Verified)**: Route handlers in `backend/src/voc_intel/api/v1/` never import SQLAlchemy, ORM models, or repositories; all persistence flows through `repositories/` and business rules through `services/`. The Next.js frontend never touches SQLite or `database/` files directly.

---

## 3. Relational Data Model, Cardinality & Nomenclature

### Deterministic ID Conventions
| Entity | Table | ID Format / Example | Key Cardinality & Notes |
| :--- | :--- | :--- | :--- |
| `Customer` | `customers` | `CUST-000001` | `1:N` to `SurveyResponse`, `Review` (optional), `SupportTicket`; zero PII pseudonym handle |
| `Product` | `products` | `PROD-001` | `1:N` to `Survey` (optional), `Review`, `SupportTicket`, `SentimentShift`, `ActionItem` |
| `Channel` | `channels` | `CHN-001` | `1:N` across `SURVEY`, `REVIEW`, `SUPPORT` channel groups |
| `Survey` | `surveys` | `SUR-2026-000001` | `product_id` nullable (`NULL` for cross-product NPS); `actual_response_count` reconciled from children |
| `SurveyResponse` | `survey_responses` | `RESP-SUR-2026-000001-001` | `RESP-<survey-id>-001`; `submitted_at` bounded by survey effective dates |
| `Review` | `reviews` | `REV-2026-000001` | Optional `customer_id` (`NULL` for anonymous web reviews); star rating `1..5` |
| `SupportTicket` | `support_tickets` | `TKT-2026-000001` | Parent ticket container ensuring referential integrity for messages; `message_count` reconciled |
| `SupportMessage` | `support_messages` | `MSG-TKT-2026-000001-001` | `MSG-<ticket-id>-001`; `sender_role` in `CUSTOMER`, `SUPPORT_AGENT`, `SYSTEM_BOT` |
| `Theme` | `themes` | `THEME-000001` | 12 governed themes across 7 categories; optional hierarchical `parent_theme_id` self-FK |
| `SentimentLabel` | `sentiment_labels` | `SENT-000001` | **1:1** per feedback item (`UNIQUE` + exclusive parent `CHECK`) |
| `FeedbackThemeAssignment` | `feedback_theme_assignments` | `THM-ASN-000001` | **N:M** bridge table linking feedback records to `Theme`; `theme_id=NULL` flagged for out-of-taxonomy anomalies |
| `SentimentShift` | `sentiment_shifts` | `SHIFT-2026-000001` | Derived rolling baseline vs. current window Welch z-score statistics |
| `ActionItem` | `action_items` | `ACT-2026-000001` | Derived service priorities (`P0_CRITICAL`, `P1_HIGH`, `P2_MEDIUM`, `P3_LOW`) |
| `ActionItemEvidence` | `action_item_evidence` | `EVID-000001` | **N:M** traceability bridge linking every `ActionItem` back to 100% of contributing source records |
| `ModelInputFeature` | `model_inputs` | `INP-000001` | **1:1** sanitized model input payload scrubbed of ground truth & evaluation holdout labels |
| `LifecycleEvent` | `lifecycle_events` | `EVT-2026-000001` | Append-only FSM state transition audit ledger across tracked entities |

Detailed field types, nullability, allowed enums, units, uniqueness, effective dates, and validation rules are documented in:
- [`docs/data_dictionary.md`](docs/data_dictionary.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/business_rules.md`](docs/business_rules.md)
- [`docs/reproducibility_report.md`](docs/reproducibility_report.md)

---

## 4. Documented Business Rules & Derived Formulas

- **Normalized Survey Score (`BR-SCORE-001`)**: `NPS` (`0..10`) maps to `rating_score / 10.0`; `CSAT`/`CES`/`POST_ONBOARDING` (`1..5`) maps to `(rating_score - 1) / 4.0`.
- **Temporal Sentiment Shifts (`BR-SHIFT-001`)**: Splits feedback by `(product_id, theme_id)` across baseline (`[window_start, split_dt)`) vs. current (`[split_dt, anchor_dt]`) windows and flags significant drift when `|delta_score| >= 0.30` and Welch `|z_score| >= 2.8`.
- **Service Priority Score (`BR-PRIO-001`)**: Computes `priority_score` (`0..100`) deterministically from mention volume, negative share, negative shift delta, theme severity weight, and cross-channel breadth (`SURVEY`, `REVIEW`, `SUPPORT`), emitting `ActionItem`s + `ActionItemEvidence` links + append-only `LifecycleEvent`s.
- **Finite State Machines (FSM)**: Enforces strict state transitions (`is_valid_transition`) and verifies zero projection drift via full event-log replay (`replay_entity_states`).

---

## 5. Repository Layout

```text
├── frontend/                        # FRONTEND TIER (Next.js 15 App Router + TypeScript)
│   ├── next.config.ts               # Proxy rewrites (/api/backend -> FastAPI backend)
│   ├── package.json                 # Next.js, React 19, TypeScript, lucide-react
│   └── src/
│       ├── app/                     # Root layout, global styles, workspace shell
│       ├── features/                # overview/, themes/, shifts/, priorities/, anomalies/
│       ├── lib/api-client.ts        # Strict HTTP-only typed REST client
│       └── types/voc.ts             # TypeScript API contracts
├── backend/                         # BACKEND TIER (Python 3.12 + FastAPI + SQLAlchemy 2.0)
│   ├── pyproject.toml               # Package & `voc-intel` CLI definition
│   ├── src/voc_intel/
│   │   ├── core/                    # Config, DB engine/pragmas, exceptions, IDGenerator
│   │   ├── db/                      # 16 normalized SQLAlchemy ORM models
│   │   ├── repositories/            # Exclusive SQLAlchemy queries & persistence layer
│   │   ├── services/                # Business logic, FSM enforcement, pipeline orchestration
│   │   ├── features/                # generation/, nlp/, shifts/, priorities/, lifecycle/, validation/, evaluation/, export/
│   │   ├── api/                     # Thin REST v1 routers + DI + CORS middleware
│   │   └── cli/main.py              # Typer CLI entrypoint (`voc-intel`)
│   └── tests/                       # 17 Pytest unit, integration, boundary, SQL & API tests
├── database/                        # DATABASE TIER (DDL, Migrations, Seeds & Ground Truth)
│   ├── schema/schema.sql            # Canonical SQL DDL
│   ├── migrations/                  # Baseline migration (`001_initial_schema.sql`)
│   ├── seeds/                       # Multi-row SQL seed (`seed.sql`, regenerated via CLI)
│   └── ground_truth/                # Segregated `ground_truth.csv` and `ground_truth.json`
├── docs/                            # Data dictionary, architecture, business rules, reproducibility report
└── exports/                         # Canonical CSV/JSON exports, validation & evaluation reports, SHA-256 manifest
```

> **Note on GitHub Artifact Size Limits**: Large generated runtime artifacts (`database/*.db*`, `database/seeds/seed.sql` at `123.5 MB`, `exports/csv/*.csv`, `exports/json/*.json`) are excluded in `.gitignore` and reproduced byte-for-byte via `voc-intel generate-full --seed 20261022`. `database/schema/schema.sql`, `database/migrations/001_initial_schema.sql`, `database/ground_truth/ground_truth.{csv,json}`, `exports/reports/*`, `exports/source_manifest.json`, and `docs/*` are tracked directly in Git.

---

## 6. Setup & Running Instructions

### Prerequisites
- Python 3.12+
- Node.js 20+ & `pnpm`

### Clone & Install
```powershell
git clone https://github.com/charanbuchannola/yottaflexai_hack.git
cd yottaflexai_hack

# 1. Backend setup
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".\backend[dev]"

# 2. Frontend setup
cd frontend
pnpm install
cd ..
```

### Generate Datasets (Fixed Seed `20261022` & Parameterized Scale)
```powershell
# Starter dataset (fast dev: 600 responses, 600 reviews, 600 support messages)
voc-intel generate-starter --seed 20261022

# Full required volume (50,000 reviews/responses + 20,000 support messages)
voc-intel generate-full --seed 20261022

# Pure baseline mode (zero injected anomalies)
voc-intel generate --profile starter --seed 20261022 --no-anomalies

# Custom parameterized scale
voc-intel generate --profile starter --seed 20261022 --responses 500 --reviews 500 --messages 400
```

### Run Validation, Evaluation & Reproducibility Checks
```powershell
voc-intel validate
voc-intel evaluate
voc-intel reproduce --profile FULL --seed 20261022
```

### Run Automated Tests & Frontend Build
```powershell
# Backend unit, integration, AST architecture boundary, SQL replay, CLI & API tests
pytest backend/tests --cov=voc_intel --cov-report=term-missing

# Frontend TypeScript check & production Next.js build
cd frontend
pnpm typecheck
pnpm build
cd ..
```

### Run Full-Stack Application (Backend API + Next.js Frontend)
```powershell
# Terminal 1: Start FastAPI backend on http://127.0.0.1:8000
voc-intel serve --host 127.0.0.1 --port 8000

# Terminal 2: Start Next.js frontend on http://localhost:3000
cd frontend
pnpm dev
```

#### Backend REST Endpoints
- `GET /health` — database connection health & core table counts
- `GET /api/v1/themes` — recurring themes sorted by volume, negative count, and avg sentiment
- `GET /api/v1/shifts?significant_only=true&product_id=PROD-001` — temporal sentiment shift cohorts
- `GET /api/v1/priorities?tier=P0_CRITICAL` — prioritized `ActionItem`s
- `GET /api/v1/priorities/{action_id}/traceability` — contributing source records (`ActionItemEvidence`) & FSM event history
- `POST /api/v1/priorities/{action_id}/transition` — append-only validated FSM state transition
- `GET /api/v1/anomalies` — live detection across all 5 anomaly/leakage rules
- `GET /api/v1/reports/{validation|evaluation}` — persisted validation & evaluation summaries

---

## 7. Segregated Ground Truth, Required Edge Cases & Lawful Provenance

- **Ground Truth Segregation**: Human-reviewed evaluation gold labels (`EVALUATION_GOLD_LABEL`), planted shift cohorts (`EXPECTED_SHIFT`), and labelled anomalies (`INJECTED_ANOMALY`) reside exclusively in [`database/ground_truth/ground_truth.csv`](database/ground_truth/ground_truth.csv) and [`database/ground_truth/ground_truth.json`](database/ground_truth/ground_truth.json), never entering operational tables or `model_inputs`.
- **5 Labelled Negative Edge Cases** (all verified at `Precision = 1.0`, `Recall = 1.0`):
  1. `LABEL_TEXT_CONTRADICTION` (`VAL-ANOM-001`) — ingested `SentimentLabel` contradicts unambiguous text + rating without rationale.
  2. `DUPLICATE_RESPONSE` (`VAL-ANOM-002`) — duplicate `(survey_id, customer_id, content_hash)` submission across distinct PKs.
  3. `CUSTOMER_IDENTITY_LEAKED` (`VAL-ANOM-003`) — synthetic decoy PII patterns detected inside text.
  4. `THEME_OUTSIDE_TAXONOMY` (`VAL-ANOM-004`) — unmapped `raw_theme_code` with `theme_id = NULL` outside governed `Theme` taxonomy.
  5. `TEST_LABEL_IN_MODEL_INPUT` (`VAL-ANOM-005`) — `ModelInputFeature` exposing `split_partition = 'TEST'`, gold tokens, or leaked target metadata keys.
- **Lawful Use & Privacy**: 100% synthetic, privacy-safe multilingual text (`en`, `es`, `fr`, `de`) generated deterministically from domain templates with zero external dataset redistribution; decoy PII uses exclusively RFC-2606 `.invalid` domains and fictional `555` numbers.

---

## 8. Verified Full-Scale Results (`FULL` Profile, Seed `20261022`)

- **Generated Volume**: `25,010` `survey_responses` (`25,000` baseline + `10` injected duplicate anomalies), `25,000` `reviews` (`50,010` total reviews/responses), `8,000` `support_tickets`, `20,000` `support_messages`, `80,326` `feedback_theme_assignments`, `244,810` append-only `lifecycle_events`.
- **Validation Gate (`voc-intel validate`)**: **`23/23` checks passed** (`overall_passed: true`, `0` PK, FK, enum, date-ordering, arithmetic reconciliation, FSM replay, or leakage errors).
- **Evaluation Set (`2,500` stratified human-reviewed samples via `voc-intel evaluate`)**:
  - Sentiment Accuracy: **`0.9396`** | Macro-F1: **`0.9397`** (`multilingual_accuracy: 0.9507` across `527` non-English samples, `sarcasm_accuracy: 1.0` across `20` sarcastic samples)
  - Theme Micro-F1: **`0.8965`** (`precision: 0.9078`, `recall: 0.8854`)
  - Sentiment Shift Detection F1: **`1.0`** (`3/3` expected shifts detected, `0` FP, `0` FN)
  - Service Priority Evidence Reconciliation: **`1.0`** (`5` action items linked to `13,465` source evidence rows)
  - Anomaly Detection F1: **`1.0`** (`50/50` injected edge cases detected across all 5 categories, `0` FP, `0` FN)
- **Automated Tests & Build Verification**:
  - Backend Pytest (`pytest backend/tests --cov=voc_intel`): **`17 passed` in `22.45s` (`95%` coverage across `2,533` statements)**
  - Frontend (`pnpm typecheck && pnpm build`): **`0` errors (`4/4` pages built)**
  - Live 3-Tier Smoke Check (`Next.js :3000` -> `FastAPI :8000` -> `SQLite`): `HTTP 200`, `reviews=25000`, `priorities=5`, `significant_shifts=3`
- **Bitwise Reproducibility (`voc-intel reproduce --profile FULL --seed 20261022`)**: **`39/39` files matched identical SHA-256 checksums** across two isolated full-scale runs ([`docs/reproducibility_report.md`](docs/reproducibility_report.md)).
