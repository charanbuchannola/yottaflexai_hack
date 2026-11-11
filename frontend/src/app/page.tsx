"use client";

import { useCallback, useEffect, useState } from "react";
import { AnomaliesAudit } from "@/features/anomalies/AnomaliesAudit";
import { OverviewPanel } from "@/features/overview/OverviewPanel";
import { PrioritiesWorkbench } from "@/features/priorities/PrioritiesWorkbench";
import { ShiftsMonitor } from "@/features/shifts/ShiftsMonitor";
import { ThemesExplorer } from "@/features/themes/ThemesExplorer";
import { vocApiClient } from "@/lib/api-client";
import type {
  ActionItem,
  DetectedAnomaly,
  EvaluationMetricsReport,
  HealthResponse,
  SentimentShiftItem,
  ThemeSummaryItem,
  ValidationReport,
} from "@/types/voc";

type TabId = "overview" | "themes" | "shifts" | "priorities" | "anomalies";

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [themes, setThemes] = useState<ThemeSummaryItem[]>([]);
  const [shifts, setShifts] = useState<SentimentShiftItem[]>([]);
  const [priorities, setPriorities] = useState<ActionItem[]>([]);
  const [anomalies, setAnomalies] = useState<DetectedAnomaly[]>([]);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationMetricsReport | null>(null);

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, t, s, p, a, v, e] = await Promise.all([
        vocApiClient.getHealth(),
        vocApiClient.getThemes(),
        vocApiClient.getShifts(),
        vocApiClient.getPriorities(),
        vocApiClient.getAnomalies(),
        vocApiClient.getValidationReport().catch(() => null),
        vocApiClient.getEvaluationReport().catch(() => null),
      ]);
      setHealth(h);
      setThemes(t);
      setShifts(s);
      setPriorities(p);
      setAnomalies(a);
      setValidation(v);
      setEvaluation(e);
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message}. Ensure the FastAPI backend is running (voc-intel serve).`
          : "Unable to connect to backend API."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>YottaFlex Voice of Customer Intelligence</h1>
          <p className="subtitle">
            3-Tier Architecture: Next.js Frontend → FastAPI Service/Repository Backend → Normalized Relational DB
          </p>
        </div>
        <div className="controls">
          <span className={`badge ${health?.status === "ok" ? "badge-ok" : "badge-warn"}`}>
            API: {health?.status === "ok" ? "CONNECTED" : "OFFLINE"}
          </span>
          <button type="button" className="btn-primary" onClick={() => void loadWorkspace()}>
            Refresh Data
          </button>
        </div>
      </header>

      <nav className="tabs" aria-label="Workspace Sections">
        {(
          [
            ["overview", "Overview & Metrics"],
            ["themes", `Themes (${themes.length})`],
            ["shifts", `Sentiment Shifts (${shifts.filter((s) => s.is_significant).length})`],
            ["priorities", `Service Priorities (${priorities.length})`],
            ["anomalies", `Exceptions & Quality (${anomalies.length})`],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`tab-btn ${activeTab === id ? "active" : ""}`}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {error && <div className="error-banner">{error}</div>}
      {loading && <p className="muted">Loading VoC workspace from FastAPI backend...</p>}

      {!loading && !error && (
        <>
          {activeTab === "overview" && (
            <OverviewPanel health={health} evaluation={evaluation} validation={validation} />
          )}
          {activeTab === "themes" && <ThemesExplorer themes={themes} />}
          {activeTab === "shifts" && <ShiftsMonitor shifts={shifts} />}
          {activeTab === "priorities" && (
            <PrioritiesWorkbench priorities={priorities} onTransitioned={loadWorkspace} />
          )}
          {activeTab === "anomalies" && (
            <AnomaliesAudit anomalies={anomalies} validation={validation} />
          )}
        </>
      )}
    </main>
  );
}

