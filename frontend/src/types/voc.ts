/** TypeScript API contracts mirroring backend/src/voc_intel/api/schemas.py */

export interface HealthResponse {
  status: string;
  database_url: string;
  record_counts: Record<string, number>;
}

export interface ThemeSummaryItem {
  theme_id: string;
  theme_code: string;
  theme_name: string;
  category: string;
  severity_weight: number;
  mention_count: number;
  avg_sentiment_score: number;
  negative_count: number;
}

export interface SentimentShiftItem {
  shift_id: string;
  product_id: string | null;
  theme_id: string | null;
  baseline_count: number;
  current_count: number;
  baseline_avg_score: number;
  current_avg_score: number;
  delta_score: number;
  z_score: number;
  direction: "IMPROVING" | "DECLINING" | "STABLE";
  is_significant: boolean;
}

export interface ActionItem {
  action_id: string;
  product_id: string | null;
  theme_id: string;
  shift_id: string | null;
  title: string;
  recommended_action: string;
  owner_role: string;
  mention_count: number;
  negative_count: number;
  channel_breadth: number;
  negative_share: number;
  avg_sentiment_score: number;
  sentiment_delta: number;
  priority_score: number;
  priority_tier: "P0_CRITICAL" | "P1_HIGH" | "P2_MEDIUM" | "P3_LOW";
  lifecycle_state: string;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  evidence_id: string;
  source_type: string;
  source_record_id: string;
  contribution_weight: number;
  text_excerpt: string;
  sentiment_polarity: string | null;
  sentiment_score: number | null;
}

export interface LifecycleEvent {
  event_id: string;
  entity_type: string;
  entity_id: string;
  from_state: string | null;
  to_state: string;
  actor: string;
  reason: string;
  event_timestamp: string;
  sequence_no: number;
}

export interface ActionTraceabilityResponse {
  action_item: ActionItem;
  total_evidence_count: number;
  sample_evidence: EvidenceItem[];
  lifecycle_history: LifecycleEvent[];
}

export interface DetectedAnomaly {
  issue_type: string;
  rule_id: string;
  target_table: string;
  target_record_id: string;
  source_record_id: string;
}

export interface ValidationCheck {
  check_id: string;
  passed: boolean;
  [key: string]: unknown;
}

export interface ValidationReport {
  overall_passed: boolean;
  mode: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  checks: ValidationCheck[];
  detected_anomalies: DetectedAnomaly[];
}

export interface EvaluationMetricsReport {
  evaluation_set_size: number;
  sentiment_metrics: {
    accuracy: number;
    macro_f1: number;
    multilingual_accuracy: number;
    multilingual_samples: number;
    sarcasm_accuracy: number;
    sarcasm_samples: number;
  };
  theme_metrics: {
    precision: number;
    recall: number;
    f1: number;
    exact_match_rate: number;
  };
  sentiment_shift_metrics: {
    expected_shifts: number;
    detected_significant_shifts: number;
    precision: number;
    recall: number;
    f1: number;
  };
  service_priority_metrics: {
    action_items_count: number;
    p0_critical_count: number;
    p1_high_count: number;
    p2_medium_count: number;
    total_evidence_links: number;
    evidence_reconciliation_rate: number;
  };
  anomaly_detection_metrics: {
    expected_anomalies: number;
    detected_anomalies: number;
    overall: {
      precision: number;
      recall: number;
      f1: number;
    };
    by_issue_type: Record<
      string,
      { tp: number; fp: number; fn: number; precision: number; recall: number; f1: number }
    >;
  };
}

