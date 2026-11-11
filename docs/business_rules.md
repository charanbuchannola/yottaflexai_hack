# Business Rules, Derived Formulas & Exception Taxonomy

## 1. Normalized Survey Score (`BR-SCORE-001`)
- `NPS` (`0..10`): `normalized_score = round(rating_score / 10.0, 4)`
- `CSAT`, `CES`, `POST_ONBOARDING` (`1..5`): `normalized_score = round((rating_score - 1) / 4.0, 4)`

## 2. Temporal Sentiment Shift Detection (`BR-SHIFT-001`)
Feedback items (excluding quarantined records and support-agent replies) are grouped by `(product_id, theme_id)` and split into:
- **Baseline Window**: `[window_start, split_dt)` (first 2/3 of `simulation_days`)
- **Current Window**: `[split_dt, anchor_dt]` (final 1/3 of `simulation_days`)

For cohorts meeting `min_window_samples`:
- `delta_score = current_avg_score - baseline_avg_score`
- `z_score = delta_score / sqrt(var_base / n_base + var_curr / n_curr + 1e-6)`
- `is_significant = abs(delta_score) >= 0.30 and abs(z_score) >= 2.8`
- `direction = DECLINING` if significant & `delta_score < 0`, `IMPROVING` if significant & `delta_score > 0`, else `STABLE`.

## 3. Service Priority Formula (`BR-PRIO-001`)
For each recurring `(product_id, theme_id)` cohort (`mention_count >= min_mentions`):
```
priority_score = clamp(0.0, 100.0,
    min(1.0, mention_count / volume_anchor) * 25.0
  + negative_share * 30.0
  + min(1.0, max(0.0, -sentiment_delta) / 0.8) * 20.0
  + min(1.0, severity_weight / 1.6) * 15.0
  + min(1.0, channel_breadth / 3.0) * 10.0
)
```
Tier assignment:
- `>= 70.0`: `P0_CRITICAL`
- `>= 52.0`: `P1_HIGH`
- `>= 34.0`: `P2_MEDIUM`
- `< 34.0`: `P3_LOW`

Every `ActionItem` persists 1:1 `ActionItemEvidence` rows for all `mention_count` contributing records, guaranteeing complete traceability and arithmetic reconciliation.

## 4. Required Edge Cases & Negative Validation Rules
1. **`LABEL_TEXT_CONTRADICTION` (`VAL-ANOM-001`)**: Ingested `SentimentLabel` (`INGESTED_PROVIDER`, `rationale = NULL`) asserts opposite polarity (`POSITIVE` vs `NEGATIVE`) relative to high-confidence NLP classification and rating signal.
2. **`DUPLICATE_RESPONSE` (`VAL-ANOM-002`)**: Duplicate `(survey_id, customer_id, content_hash)` or `(product_id, customer_id, content_hash)` submission across distinct PKs.
3. **`CUSTOMER_IDENTITY_LEAKED` (`VAL-ANOM-003`)**: Synthetic decoy PII patterns (`.invalid` email, 555 phone, `CUST_KEY_`, named account leak) detected inside feedback text.
4. **`THEME_OUTSIDE_TAXONOMY` (`VAL-ANOM-004`)**: `FeedbackThemeAssignment` row with `theme_id = NULL` or `raw_theme_code` absent from active governed `themes`.
5. **`TEST_LABEL_IN_MODEL_INPUT` (`VAL-ANOM-005`)**: `ModelInputFeature` record exposing `split_partition = 'TEST'`, leaked gold text tokens, or ground-truth keys in `extra_features_json`.

