"use client";

import type { ThemeSummaryItem } from "@/types/voc";

interface ThemesExplorerProps {
  themes: ThemeSummaryItem[];
}

export function ThemesExplorer({ themes }: ThemesExplorerProps) {
  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3>Recurring Theme Taxonomy & Multi-Channel Volume</h3>
          <p className="muted">
            Governed taxonomy themes aggregated across SurveyResponse, Review, and SupportMessage records.
          </p>
        </div>
        <span className="badge badge-neutral">{themes.length} Active Themes</span>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Theme ID</th>
              <th>Theme Name</th>
              <th>Category</th>
              <th className="num">Severity</th>
              <th className="num">Mentions</th>
              <th className="num">Negative</th>
              <th className="num">Avg Sentiment</th>
            </tr>
          </thead>
          <tbody>
            {themes.map((theme) => {
              const negRate =
                theme.mention_count > 0
                  ? ((theme.negative_count / theme.mention_count) * 100).toFixed(1)
                  : "0.0";
              return (
                <tr key={theme.theme_id}>
                  <td>
                    <code>{theme.theme_id}</code>
                  </td>
                  <td>
                    <strong>{theme.theme_name}</strong>
                    <div className="sub-code">{theme.theme_code}</div>
                  </td>
                  <td>
                    <span className="badge badge-neutral">{theme.category}</span>
                  </td>
                  <td className="num">{theme.severity_weight.toFixed(2)}x</td>
                  <td className="num">{theme.mention_count.toLocaleString()}</td>
                  <td className="num">
                    {theme.negative_count.toLocaleString()} ({negRate}%)
                  </td>
                  <td className="num">
                    <span className={theme.avg_sentiment_score < 0 ? "text-danger" : "text-ok"}>
                      {theme.avg_sentiment_score >= 0 ? "+" : ""}
                      {theme.avg_sentiment_score.toFixed(3)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

