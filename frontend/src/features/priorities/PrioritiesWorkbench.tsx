"use client";

import { useEffect, useState } from "react";
import { vocApiClient } from "@/lib/api-client";
import type { ActionItem, ActionTraceabilityResponse } from "@/types/voc";

interface PrioritiesWorkbenchProps {
  priorities: ActionItem[];
  onTransitioned: () => Promise<void>;
}

const NEXT_ALLOWED_STATES: Record<string, string[]> = {
  IDENTIFIED: ["TRIAGED"],
  TRIAGED: ["IN_PROGRESS", "ESCALATED"],
  ESCALATED: ["IN_PROGRESS", "VERIFIED"],
  IN_PROGRESS: ["VERIFIED"],
  VERIFIED: ["CLOSED"],
  CLOSED: [],
};

export function PrioritiesWorkbench({ priorities, onTransitioned }: PrioritiesWorkbenchProps) {
  const [selectedId, setSelectedId] = useState<string | null>(priorities[0]?.action_id ?? null);
  const [trace, setTrace] = useState<ActionTraceabilityResponse | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);
  const [submittingState, setSubmittingState] = useState(false);

  useEffect(() => {
    if (!selectedId && priorities.length > 0) {
      setSelectedId(priorities[0].action_id);
    }
  }, [priorities, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setLoadingTrace(true);
    setTransitionError(null);
    vocApiClient
      .getActionTraceability(selectedId, 12)
      .then((res) => {
        if (active) setTrace(res);
      })
      .catch((err: Error) => {
        if (active) setTransitionError(err.message);
      })
      .finally(() => {
        if (active) setLoadingTrace(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  async function handleTransition(targetState: string) {
    if (!selectedId) return;
    setSubmittingState(true);
    setTransitionError(null);
    try {
      await vocApiClient.transitionActionItem(selectedId, {
        to_state: targetState,
        actor: "web_analyst",
        reason: `Transitioned to ${targetState} from Next.js Priorities Workbench`,
      });
      const updated = await vocApiClient.getActionTraceability(selectedId, 12);
      setTrace(updated);
      await onTransitioned();
    } catch (err) {
      setTransitionError(err instanceof Error ? err.message : "Failed to update lifecycle state");
    } finally {
      setSubmittingState(false);
    }
  }

  const nextStates = trace
    ? NEXT_ALLOWED_STATES[trace.action_item.lifecycle_state] ?? []
    : [];

  return (
    <section className="split-layout">
      <div className="card">
        <div className="card-header">
          <div>
            <h3>Service Priorities (BR-PRIO-001)</h3>
            <p className="muted">Select an action item to audit source evidence and FSM history.</p>
          </div>
          <span className="badge badge-neutral">{priorities.length} Action Items</span>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Tier</th>
                <th className="num">Score</th>
                <th className="num">Mentions</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {priorities.map((item) => (
                <tr
                  key={item.action_id}
                  className={item.action_id === selectedId ? "row-selected" : "row-clickable"}
                  onClick={() => setSelectedId(item.action_id)}
                >
                  <td>
                    <strong>{item.title}</strong>
                    <div className="sub-code">
                      {item.action_id} · Owner: {item.owner_role}
                    </div>
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        item.priority_tier === "P0_CRITICAL"
                          ? "badge-danger"
                          : item.priority_tier === "P1_HIGH"
                          ? "badge-warn"
                          : "badge-info"
                      }`}
                    >
                      {item.priority_tier}
                    </span>
                  </td>
                  <td className="num">{item.priority_score.toFixed(1)}</td>
                  <td className="num">{item.mention_count.toLocaleString()}</td>
                  <td>
                    <span className="badge badge-neutral">{item.lifecycle_state}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3>Traceability & Append-Only Lifecycle</h3>
            <p className="muted">
              {trace
                ? `${trace.action_item.action_id} · Reconciled to ${trace.total_evidence_count.toLocaleString()} source records`
                : "Select an action item"}
            </p>
          </div>
        </div>

        {loadingTrace && <p className="muted">Loading source evidence...</p>}
        {transitionError && <p className="error-banner">{transitionError}</p>}

        {trace && !loadingTrace && (
          <div className="trace-stack">
            <div className="callout">
              <strong>Recommended Action ({trace.action_item.owner_role})</strong>
              <p>{trace.action_item.recommended_action}</p>
              <div className="action-bar">
                <span className="muted">Current FSM State: {trace.action_item.lifecycle_state}</span>
                <div className="btn-group">
                  {nextStates.map((st) => (
                    <button
                      key={st}
                      type="button"
                      className="btn-primary"
                      disabled={submittingState}
                      onClick={() => handleTransition(st)}
                    >
                      Transition → {st}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <h4>Contributing Source Records (Sample {trace.sample_evidence.length})</h4>
              <ul className="evidence-list">
                {trace.sample_evidence.map((ev) => (
                  <li key={ev.evidence_id} className="evidence-item">
                    <div className="evidence-meta">
                      <code>{ev.source_record_id}</code>
                      <span className="badge badge-neutral">{ev.source_type}</span>
                      <span className="badge badge-info">
                        {ev.sentiment_polarity ?? "UNKNOWN"} (
                        {ev.sentiment_score !== null ? ev.sentiment_score.toFixed(2) : "—"})
                      </span>
                    </div>
                    <p>{ev.text_excerpt}</p>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4>Append-Only Event History ({trace.lifecycle_history.length} events)</h4>
              <ul className="history-list">
                {trace.lifecycle_history.map((evt) => (
                  <li key={evt.event_id}>
                    <code>#{evt.sequence_no}</code> {evt.from_state ?? "INIT"} →{" "}
                    <strong>{evt.to_state}</strong> by <em>{evt.actor}</em> — {evt.reason}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

