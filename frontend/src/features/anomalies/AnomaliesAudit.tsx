"use client";

import { useMemo } from "react";
import type { DetectedAnomaly, ValidationReport } from "@/types/voc";

interface AnomaliesAuditProps {
  anomalies: DetectedAnomaly[];
  validation: ValidationReport | null;
}

export function AnomaliesAudit({ anomalies, validation }: AnomaliesAuditProps) {
  const countsByType = useMemo(() => {
    const map: Record<string, number> = {};
    for (const a of anomalies) {
      map[a.issue_type] = (map[a.issue_type] ?? 0) + 1;
    }
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
  }, [anomalies]);

  return (
    <section className="panel-grid">
      <div className="card">
        <div className="card-header">
          <div>
            <h3>Live Exception & Data-Leakage Audit</h3>
            <p className="muted">
              Detects contradictions, duplicate responses, leaked identity PII, out-of-taxonomy themes, and test-label leakage.
            </p>
          </div>
          <span className="badge badge-warn">{anomalies.length} Detected Exceptions</span>
        </div>

        <div className="chip-row">
          {countsByType.map(([issue, count]) => (
            <span key={issue} className="badge badge-info">
              {issue}: {count}
            </span>
          ))}
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule ID</th>
                <th>Issue Type</th>
                <th>Target Table</th>
                <th>Target Record ID</th>
                <th>Source Record ID</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.slice(0, 100).map((anom, idx) => (
                <tr key={`${anom.rule_id}-${anom.target_record_id}-${idx}`}>
                  <td>
                    <code>{anom.rule_id}</code>
                  </td>
                  <td>
                    <span className="badge badge-warn">{anom.issue_type}</span>
                  </td>
                  <td>
                    <code>{anom.target_table}</code>
                  </td>
                  <td>
                    <code>{anom.target_record_id}</code>
                  </td>
                  <td>
                    <code>{anom.source_record_id}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {validation && (
        <div className="card">
          <div className="card-header">
            <h3>Automated Validation Gate ({validation.mode})</h3>
            <span className={`badge ${validation.overall_passed ? "badge-ok" : "badge-danger"}`}>
              {validation.passed_checks}/{validation.total_checks} Passed
            </span>
          </div>
          <div className="chip-row">
            {validation.checks.map((chk) => (
              <span
                key={chk.check_id}
                className={`badge ${chk.passed ? "badge-ok" : "badge-danger"}`}
              >
                {chk.check_id}: {chk.passed ? "PASS" : "FAIL"}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

