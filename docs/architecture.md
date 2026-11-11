# System Architecture & Traceability Design

## 1. End-to-End Pipeline Architecture

```
  [Master Data: Customer, Product, Channel, Survey, Theme]
                         │
                         ▼
  [Multi-Source Feedback: SurveyResponse, Review, SupportTicket, SupportMessage]
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
  [Sanitized ModelInputFeature]    (Optional Edge-Case Injector)
        │                                 │
        ▼                                 ▼
  [Multilingual NLP Classifier]    [Segregated ground_truth.csv/json]
  (SentimentLabel + Theme N:M)     (Never joined into model inputs!)
        │
        ▼
  [Temporal Shift Detector (BR-SHIFT-001)]
        │
        ▼
  [Service Priority & ActionItem Engine (BR-PRIO-001)]
  (ActionItem + ActionItemEvidence N:M + Append-Only LifecycleEvents)
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
  [SQLite / SQLAlchemy] [CSV/JSON/SQL]  [Validation + Evaluation + FastAPI]
```

## 2. Primary Actors & Responsibilities

| Actor | Interaction Path | Primary Operations |
| :--- | :--- | :--- |
| **Customer / Prospect** | Survey channels, Web/App reviews, Support chat/email | Submits ratings, open-text feedback, and support ticket inquiries |
| **Marketing / Sales Ops** | `surveys`, `GET /api/v1/themes`, `GET /api/v1/shifts` | Launches survey waves, monitors cross-channel sentiment shifts and NPS trends |
| **Support Agent** | `support_tickets`, `support_messages` | Triages incoming tickets, logs responses, escalates urgent issues |
| **Analyst** | `GET /api/v1/priorities`, `GET /api/v1/priorities/{id}/traceability`, `evaluation_metrics.json` | Audits recurring theme priorities, verifies evidence traceability, reviews NLP/shift metrics |
| **System Administrator** | `voc-intel` CLI, `POST /api/v1/priorities/{id}/transition`, `GET /api/v1/anomalies` | Runs reproducible pipelines, inspects anomaly gates, advances ActionItem lifecycle states |

