# Enterprise 3-Tier Architecture & Traceability Design

## 1. Tier Separation Overview

```
+-------------------------------------------------------------------------+
|                    FRONTEND TIER (frontend/ - Next.js)                  |
|  App Router (TypeScript) · Feature Modules (Overview, Themes, Shifts,  |
|  Priorities/Traceability, Anomalies) · Typed HTTP Client + Rewrite     |
+-------------------------------------------------------------------------+
                                    |  HTTP / JSON (CORS + /api/backend)
                                    v
+-------------------------------------------------------------------------+
|                 BACKEND TIER (backend/ - Python + FastAPI)              |
|  1. Presentation Layer : api/v1/ (Thin Routers + DI) & cli/ (Typer)     |
|  2. Service Layer      : services/ (Business Rules, Orchestration, FSM) |
|  3. Feature Engines    : features/ (generation, nlp, shifts,            |
|                          priorities, lifecycle, validation, eval, exp)  |
|  4. Repository Layer   : repositories/ (All SQLAlchemy Session/Queries) |
|  5. Persistence Models : db/ (16 Normalized SQLAlchemy 2.0 Tables)      |
+-------------------------------------------------------------------------+
                                    |  SQLAlchemy 2.0 + FK Enforcement
                                    v
+-------------------------------------------------------------------------+
|               DATABASE TIER (database/ - Relational & GT)               |
|  schema/schema.sql · migrations/001_initial_schema.sql · seeds/seed.sql |
|  voc_intelligence.db · ground_truth/ground_truth.{csv,json} (isolated)  |
+-------------------------------------------------------------------------+
```

## 2. Layer Responsibilities & Enforced Boundaries

1. **Frontend (`frontend/`)**:
   - Strictly isolated Next.js App Router + TypeScript UI organized by domain feature (`src/features/{overview,themes,shifts,priorities,anomalies}`).
   - Zero direct database access; all reads and mutations flow exclusively over HTTP via [`api-client.ts`](../frontend/src/lib/api-client.ts).
2. **Backend API & CLI (`backend/src/voc_intel/api/`, `cli/`)**:
   - Thin transport handlers delegating exclusively to injected Services via `deps.py`.
   - Verified statically by `test_architecture_boundaries.py`: route files in `api/v1/` import zero SQLAlchemy or repository modules.
3. **Backend Services (`backend/src/voc_intel/services/`)**:
   - Own domain validation, aggregations, FSM transition checks, exception raising (`ResourceNotFoundError`, `InvalidStateTransitionError`), and end-to-end pipeline orchestration.
4. **Backend Repositories (`backend/src/voc_intel/repositories/`)**:
   - Exclusive home for SQLAlchemy `Session` queries, batched evidence hydration, and atomic append-only `LifecycleEvent` persistence.
5. **Backend Feature Modules (`backend/src/voc_intel/features/`)**:
   - Modular, pure domain engines for `generation`, `nlp`, `shifts`, `priorities`, `lifecycle`, `validation`, `evaluation`, and `export`.
6. **Database Tier (`database/`)**:
   - Houses canonical DDL (`schema/schema.sql`), baseline migrations (`migrations/001_initial_schema.sql`), deterministic SQL seeds (`seeds/seed.sql`), SQLite runtime database, and physically segregated `ground_truth/` evaluation artifacts.

## 3. Primary Actors & Responsibilities

| Actor | Interaction Path | Primary Operations |
| :--- | :--- | :--- |
| **Customer / Prospect** | Survey channels, Web/App reviews, Support chat/email | Submits ratings, open-text feedback, and support ticket inquiries |
| **Marketing / Sales Ops** | Next.js Themes/Shifts views, `GET /api/v1/themes`, `GET /api/v1/shifts` | Monitors cross-channel themes and sentiment shift trajectories |
| **Support Agent** | `support_tickets`, `support_messages` | Triages incoming tickets, logs responses, escalates urgent issues |
| **Analyst** | Next.js Priorities Workbench, `GET /api/v1/priorities/{id}/traceability` | Audits recurring theme priorities, inspects source evidence, reviews metrics |
| **System Administrator** | `voc-intel` CLI, Next.js Exceptions tab, `POST /api/v1/priorities/{id}/transition` | Runs reproducible pipelines, audits anomaly gates, advances FSM states |
