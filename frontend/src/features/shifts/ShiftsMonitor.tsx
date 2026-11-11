"use client";

import { useMemo, useState } from "react";
import type { SentimentShiftItem } from "@/types/voc";

interface ShiftsMonitorProps {
  shifts: SentimentShiftItem[];
}

export function ShiftsMonitor({ shifts }: ShiftsMonitorProps) {
  const [significantOnly, setSignificantOnly] = useState(true);
  const [productFilter, setProductFilter] = useState<string>("ALL");

  const products = useMemo(() => {
    const ids = new Set(shifts.map((s) => s.product_id).filter((id): id is string => Boolean(id)));
    return ["ALL", ...Array.from(ids).sort()];
  }, [shifts]);

  const filtered = useMemo(() => {
    return shifts.filter((s) => {
      if (significantOnly && !s.is_significant) return false;
      if (productFilter !== "ALL" && s.product_id !== productFilter) return false;
      return true;
    });
  }, [shifts, significantOnly, productFilter]);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3>Temporal Sentiment Shift Monitor (BR-SHIFT-001)</h3>
          <p className="muted">
            Rolling baseline vs. current window score deltas tested with Welch two-sample z-scores.
          </p>
        </div>
        <div className="controls">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={significantOnly}
              onChange={(e) => setSignificantOnly(e.target.checked)}
            />
            Significant Only
          </label>
          <select
            className="select-input"
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            aria-label="Filter by product"
          >
            {products.map((p) => (
              <option key={p} value={p}>
                {p === "ALL" ? "All Products" : p}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Shift ID</th>
              <th>Product</th>
              <th>Theme</th>
              <th className="num">Base n / Curr n</th>
              <th className="num">Base Avg</th>
              <th className="num">Curr Avg</th>
              <th className="num">Delta</th>
              <th className="num">z-Score</th>
              <th>Direction</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <tr key={s.shift_id}>
                <td>
                  <code>{s.shift_id}</code>
                </td>
                <td>{s.product_id ?? "ALL"}</td>
                <td>
                  <code>{s.theme_id ?? "ALL"}</code>
                </td>
                <td className="num">
                  {s.baseline_count} / {s.current_count}
                </td>
                <td className="num">{s.baseline_avg_score.toFixed(3)}</td>
                <td className="num">{s.current_avg_score.toFixed(3)}</td>
                <td className="num">
                  <span className={s.delta_score < 0 ? "text-danger" : "text-ok"}>
                    {s.delta_score >= 0 ? "+" : ""}
                    {s.delta_score.toFixed(3)}
                  </span>
                </td>
                <td className="num">{s.z_score.toFixed(2)}</td>
                <td>
                  <span
                    className={`badge ${
                      s.direction === "DECLINING"
                        ? "badge-danger"
                        : s.direction === "IMPROVING"
                        ? "badge-ok"
                        : "badge-neutral"
                    }`}
                  >
                    {s.direction}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

