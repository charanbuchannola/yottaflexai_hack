import type {
  ActionItem,
  ActionTraceabilityResponse,
  DetectedAnomaly,
  EvaluationMetricsReport,
  HealthResponse,
  LifecycleEvent,
  SentimentShiftItem,
  ThemeSummaryItem,
  ValidationReport,
} from "@/types/voc";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const payload = (await res.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Fallback to status message when body is non-JSON
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export const vocApiClient = {
  getHealth: () => requestJson<HealthResponse>("/health"),
  getThemes: () => requestJson<ThemeSummaryItem[]>("/api/v1/themes"),
  getShifts: (opts?: { significantOnly?: boolean; productId?: string }) => {
    const params = new URLSearchParams();
    if (opts?.significantOnly) params.set("significant_only", "true");
    if (opts?.productId) params.set("product_id", opts.productId);
    const qs = params.toString();
    return requestJson<SentimentShiftItem[]>(`/api/v1/shifts${qs ? `?${qs}` : ""}`);
  },
  getPriorities: (tier?: string) => {
    const qs = tier ? `?tier=${encodeURIComponent(tier)}` : "";
    return requestJson<ActionItem[]>(`/api/v1/priorities${qs}`);
  },
  getActionTraceability: (actionId: string, limit = 15) =>
    requestJson<ActionTraceabilityResponse>(
      `/api/v1/priorities/${encodeURIComponent(actionId)}/traceability?limit=${limit}`
    ),
  transitionActionItem: (
    actionId: string,
    payload: { to_state: string; actor: string; reason: string }
  ) =>
    requestJson<LifecycleEvent>(
      `/api/v1/priorities/${encodeURIComponent(actionId)}/transition`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),
  getAnomalies: () => requestJson<DetectedAnomaly[]>("/api/v1/anomalies"),
  getValidationReport: () => requestJson<ValidationReport>("/api/v1/reports/validation"),
  getEvaluationReport: () => requestJson<EvaluationMetricsReport>("/api/v1/reports/evaluation"),
};

