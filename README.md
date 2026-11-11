# YottaFlex Voice of Customer (VoC) Intelligence Platform

An end-to-end, deterministic Python 3.12 + SQLAlchemy 2.0 + FastAPI platform that combines **survey responses**, **product reviews**, and **support messages** to identify recurring themes, detect temporal sentiment shifts, prioritize service action items with full source-record traceability, and enforce automated relational, lifecycle, privacy, and leakage validation.

---

## 1. Problem Scope & Primary Actors

- **Business Problem**: Combine multi-channel customer feedback (`SurveyResponse`, `Review`, `SupportMessage`) into governed theme taxonomies (`Theme`), calibrated sentiment assessments (`SentimentLabel`), statistical temporal shifts (`SentimentShift`), and prioritized remediation workflows (`ActionItem`).
- **Primary Actors**:
  - **Customer / Prospect**: Submits NPS/CSAT/CES survey responses, product reviews (authenticated or anonymous), and multi-turn support tickets.
  - **Marketing / Sales Operations**: Configures survey campaigns, monitors cross-channel themes and sentiment shift trajectories.
  - **Support Agent**: Triages support tickets, logs agent replies, and resolves escalated issues.
  - **Analyst**: Audits sentiment/theme metrics on the segregated evaluation set, inspects priority scores, and drills down to source evidence.
  - **System Administrator**: Executes reproducible generation runs, validates relational/FSM integrity, and advances `ActionItem` lifecycle transitions.

---

## 2. Relational Data Model & Nomenclature

### Deterministic ID Conventions
- `Customer`: `CUST-000001`
- `Product`: `PROD-001`
- `Channel`: `CHN-001`
- `Survey`: `SUR-2026-000001`
- `SurveyResponse`: `RESP-<survey-id>-001` (e.g., `RESP-SUR-2026-000001-001`)
- `Review`: `REV-2026-000001`
- `SupportTicket`: `TKT-2026-000001`
- `SupportMessage`: `MSG-<ticket-id>-001` (e.g., `MSG-TKT-2026-000001-001`)
- `Theme`: `THEME-000001`
- `SentimentLabel`: `SENT-000001` (`1:1` per feedback record via `UNIQUE` + exclusive `CHECK`)
- `FeedbackThemeAssignment`: `THM-ASN-000001` (`N:M` bridge table linking feedback records to themes)
- `SentimentShift`: `SHIFT-2026-000001`
- `ActionItem`: `ACT-2026-000001`
- `ActionItemEvidence`: `EVID-000001` (`N:M` bridge table tracing priorities back to every contributing source record)
- `ModelInputFeature`: `INP-000001` (sanitized operational feature table with zero ground-truth leakage)
- `LifecycleEvent`: `EVT-2026-000001` (append-only state transition journal)

See full schema, types, constraints, cardinalities, optional relationships, effective dates, and lifecycle states in:
- [`docs/data_dictionary.md`](docs/data_dictionary.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/business_rules.md`](docs/business_rules.md)
- [`docs/reproducibility_report.md`](docs/reproducibility_report.md)

---

## 3. Repository Layout (Enterprise 3-Tier Separation)

```text
├── frontend/                        # FRONTEND TIER (Next.js App Router + TypeScript)
│   ├── next.config.ts               # Server-side proxy rewrites (/api/backend -> FastAPI)
│   └── src/
│       ├── app/                     # Root layout, styles & workspace shell
│       ├── features/                # Feature modules: overview, themes, shifts, priorities, anomalies
│       ├── lib/api-client.ts        # Strict HTTP-only typed REST client
│       └── types/voc.ts             # TypeScript API contracts
├── backend/                         # BACKEND TIER (Python 3.12 + FastAPI + SQLAlchemy 2.0)
│   ├── pyproject.toml               # Package & CLI definition (`voc-intel`)
│   ├── src/voc_intel/
│   │   ├── core/                    # Config, DB engine, exceptions, deterministic identifiers
│   │   ├── db/                      # 16 normalized SQLAlchemy ORM models
│   │   ├── repositories/            # Exclusive SQLAlchemy queries & persistence layer
│   │   ├── services/                # Business logic, FSM transition validation, pipeline orchestration
│   │   ├── features/                # generation, nlp, shifts, priorities, lifecycle, validation, evaluation, export
│   │   ├── api/                     # Thin REST v1 routers + DI + CORS middleware (zero ORM/SQL imports)
│   │   └── cli/main.py              # Typer CLI entrypoint (`voc-intel`)
│   └── tests/                       # Pytest suite (architecture boundaries, models, rules, anomalies, API, CLI)
├── database/                        # DATABASE TIER (DDL, Migrations, Seeds & Ground Truth)
│   ├── schema/schema.sql            # Canonical SQL DDL
│   ├── migrations/                  # Versioned migration baseline (`001_initial_schema.sql`)
│   ├── seeds/                       # Batched multi-row SQL seed (`seed.sql`)
│   └── ground_truth/                # Segregated `ground_truth.csv` and `ground_truth.json` (zero leakage)
├── docs/                            # Architecture, data dictionary, business rules, reproducibility report
└── exports/                         # Canonical CSV, JSON, validation/evaluation reports, SHA-256 manifest
```

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.12+
- Node.js 20+ & `pnpm` (for the Next.js frontend)

### Backend Installation
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".\backend[dev]"
```

### Frontend Installation
```powershell
cd frontend
pnpm install
cd ..
```

### Generate Datasets (Fixed Seed `20261022`)
- **Starter profile** (fast development & testing: 600 responses, 600 reviews, 600 support messages):
  ```powershell
  voc-intel generate-starter --seed 20261022
  ```
- **Full required profile** (**50,000** reviews/responses + **20,000** support messages):
  ```powershell
  voc-intel generate-full --seed 20261022
  ```
- **Pure baseline mode** (0 injected anomalies):
  ```powershell
  voc-intel generate --profile starter --seed 20261022 --no-anomalies
  ```
- **Custom parameterized scale**:
  ```powershell
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
# Backend unit, integration, boundary, and API tests
pytest backend/tests

# Frontend typecheck & production Next.js build
cd frontend
pnpm typecheck
pnpm build
cd ..
```

### Start Full-Stack Application (Backend + Next.js Frontend)
```powershell
# Terminal 1: Start FastAPI backend on http://127.0.0.1:8000
voc-intel serve --host 127.0.0.1 --port 8000

# Terminal 2: Start Next.js frontend on http://localhost:3000
cd frontend
pnpm dev
```
Key Backend REST endpoints:
- `GET /health`
- `GET /api/v1/themes`
- `GET /api/v1/shifts?significant_only=true`
- `GET /api/v1/priorities`
- `GET /api/v1/priorities/{action_id}/traceability`
- `POST /api/v1/priorities/{action_id}/transition`
- `GET /api/v1/anomalies`
- `GET /api/v1/reports/validation`
- `GET /api/v1/reports/evaluation`

---

## 5. Segregated Ground Truth, Edge Cases & Lawful Provenance

- **Ground Truth Segregation**: Human-reviewed evaluation gold labels (`EVALUATION_GOLD_LABEL`), planted shifts (`EXPECTED_SHIFT`), and labelled anomalies (`INJECTED_ANOMALY`) are written exclusively to `database/ground_truth/ground_truth.csv` and `database/ground_truth/ground_truth.json` and are never included in operational tables or model input features.
- **Injected Edge Cases** (all 5 verified in `validation_report.json` & `evaluation_metrics.json`):
  1. `LABEL_TEXT_CONTRADICTION`
  2. `DUPLICATE_RESPONSE`
  3. `CUSTOMER_IDENTITY_LEAKED`
  4. `THEME_OUTSIDE_TAXONOMY`
  5. `TEST_LABEL_IN_MODEL_INPUT`
- **Lawful Use & Privacy**: 100% synthetic, privacy-safe text generated deterministically from domain templates across `en`, `es`, `fr`, and `de`. External datasets are not redistributed; synthetic decoy PII in `CUSTOMER_IDENTITY_LEAKED` rows strictly uses RFC-2606 `.invalid` domains and fictional `555` phone ranges.

---

## 6. Verified Full-Scale Results (`FULL` Profile, Seed `20261022`)

- **Volume**: `25,010` survey responses (`25,000` baseline + `10` injected duplicate anomalies), `25,000` reviews (`50,010` total reviews/responses), `8,000` support tickets, `20,000` support messages, `244,810` append-only lifecycle events.
- **Validation**: `23/23` checks passed (`overall_passed: true`, `0` FK/PK/Enum/Date/Reconciliation/FSM/Leakage violations).
- **Evaluation Set (`2,500` human-reviewed stratified samples)**:
  - Sentiment Accuracy: `0.9396`, Macro-F1: `0.9397` (`multilingual_accuracy: 0.9507` across `527` non-English samples, `sarcasm_accuracy: 1.0` across `20` sarcastic samples)
  - Theme Micro-F1: `0.8965` (`precision: 0.9078`, `recall: 0.8854`)
  - Sentiment Shift Detection F1: `1.0` (`3/3` expected shifts detected, `0` FP, `0` FN)
  - Service Priority Evidence Reconciliation: `1.0` (`5` action items linked to `13,465` source records)
  - Anomaly Detection F1: `1.0` (`50/50` injected edge cases detected across all 5 categories, `0` FP, `0` FN)
- **Bitwise Reproducibility**: `39/39` exported files matched identical SHA-256 checksums across two isolated full-scale runs (`docs/reproducibility_report.md`).


