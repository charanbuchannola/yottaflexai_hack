"use client";

import type { EvaluationMetricsReport, HealthResponse, ValidationReport } from "@/types/voc";

interface OverviewPanelProps {
  health: HealthResponse | null;
  evaluation: EvaluationMetricsReport | null;
  validation: ValidationReport | null;
}

export function OverviewPanel({ health, evaluation, validation }: OverviewPanelProps) {
  const counts = health?.record_counts ?? {};
  const totalFeedback =
    (counts.survey_responses ?? 0) + (counts.reviews ?? 0) + (counts.support_messages ?? 0);

  return (
    <section className="panel-grid">
      <div className="kpi-row">
        <article className="kpi-card">
          <span className="kpi-label">Total Multi-Channel Feedback</span>
          <strong className="kpi-value">{totalFeedback.toLocaleString()}</strong>
          <span className="kpi-sub">
            {(counts.survey_responses ?? 0).toLocaleString()} surveys ·{" "}
            {(counts.reviews ?? 0).toLocaleString()} reviews ·{" "}
            {(counts.support_messages ?? 0).toLocaleString()} support msgs
          </span>
        </article>

        <article className="kpi-card">
          <span className="kpi-label">Sentiment Macro-F1 (Holdout)</span>
          <strong className="kpi-value">
            {evaluation ? `${(evaluation.sentiment_metrics.macro_f1 * 100).toFixed(2)}%` : "—"}
          </strong>
          <span className="kpi-sub">
            {evaluation
              ? `${evaluation.evaluation_set_size.toLocaleString()} human-reviewed · Multilingual ${(
                  evaluation.sentiment_metrics.multilingual_accuracy * 100
                ).toFixed(1)}%`
              : "Evaluation report unavailable"}
          </span>
        </article>

        <article className="kpi-card">
          <span className="kpi-label">Theme Micro-F1 / Shift F1</span>
          <strong className="kpi-value">
            {evaluation
              ? `${(evaluation.theme_metrics.f1 * 100).toFixed(1)}% / ${(
                  evaluation.sentiment_shift_metrics.f1 * 100
                ).toFixed(0)}%`
              : "—"}
          </strong>
          <span className="kpi-sub">
            {evaluation
              ? `${evaluation.sentiment_shift_metrics.detected_significant_shifts}/${evaluation.sentiment_shift_metrics.expected_shifts} significant shifts detected`
              : "Run backend pipeline"}
          </span>
        </article>

        <article className="kpi-card">
          <span className="kpi-label">Validation & Anomaly Gate</span>
          <strong className={`kpi-value ${validation?.overall_passed ? "text-ok" : "text-warn"}`}>
            {validation ? (validation.overall_passed ? "PASS" : "FAIL") : "—"}
          </strong>
          <span className="kpi-sub">
            {validation
              ? `${validation.passed_checks}/${validation.total_checks} checks · Anomaly F1 ${
                  evaluation ? evaluation.anomaly_detection_metrics.overall.f1.toFixed(2) : "—"
                }`
              : "Validation report unavailable"}
          </span>
        </article>
      </div>

      {evaluation && (
        <div className="card">
          <div className="card-header">
            <h3>Measurable Model & Operations Benchmarks</h3>
            <span className="badge badge-info">Seed-Reproducible Metrics</span>
          </div>
          <div className="metrics-strip">
            <div>
              <span className="muted">Sentiment Accuracy</span>
              <p className="metric-num">{(evaluation.sentiment_metrics.accuracy * 100).toFixed(2)}%</p>
            </div>
            <div>
              <span className="muted">Sarcasm Detection</span>
              <p className="metric-num">
                {(evaluation.sentiment_metrics.sarcasm_accuracy * 100).toFixed(1)}% (n=
                {evaluation.sentiment_metrics.sarcasm_samples})
              </p>
            </div>
            <div>
              <span className="muted">Theme Precision / Recall</span>
              <p className="metric-num">
                {(evaluation.theme_metrics.precision * 100).toFixed(1)}% /{" "}
                {(evaluation.theme_metrics.recall * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <span className="muted">Evidence Reconciliation</span>
              <p className="metric-num">
                {(evaluation.service_priority_metrics.evidence_reconciliation_rate * 100).toFixed(0)}% (
                {evaluation.service_priority_metrics.total_evidence_links.toLocaleString()} links)
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

