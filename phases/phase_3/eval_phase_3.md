# Phase 3 Evaluation — Intelligence & Scoring Agents

> **Phase**: 3 | **Status**: Not Started | **Eval Version**: 1.0

---

## Exit Criteria Checklist

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Trend Detection Agent identifies week-over-week changes | ⬜ | |
| 2 | Spike anomalies detected (>2σ threshold) | ⬜ | |
| 3 | Product Impact Scores generated for all themes (0–100) | ⬜ | |
| 4 | Priority labels (P0–P3) assigned correctly based on score | ⬜ | |
| 5 | PM Recommendations generated with evidence quotes | ⬜ | |
| 6 | Weekly Pulse document contains all required sections | ⬜ | |
| 7 | Full pipeline runs end-to-end (Agents 1–7) | ⬜ | |
| 8 | All results persisted to database | ⬜ | |

---

## Test Cases

### TC-3.1: Trend Detection — Volume Change
| Property | Detail |
|----------|--------|
| **Description** | Detects weekly review volume changes per theme |
| **Steps** | Run with 4+ weeks of data; check trend signals |
| **Expected** | Trend signals include `change_percent` and `trend_type` (rising/declining/stable) |
| **Pass/Fail** | ⬜ |

### TC-3.2: Trend Detection — Spike Anomaly
| Property | Detail |
|----------|--------|
| **Description** | Detects abnormal spikes in complaint volume |
| **Steps** | Inject synthetic spike (3x normal volume for a theme in one week) |
| **Expected** | Trend signal with `trend_type: "spike"` and description explaining the anomaly |
| **Pass/Fail** | ⬜ |

### TC-3.3: Trend Detection — Release Regression
| Property | Detail |
|----------|--------|
| **Description** | Correlates negative trend with app version release |
| **Steps** | Check if trend signals reference `related_version` when applicable |
| **Expected** | Signals like "UPI failure complaints +32% after v6.4 release" |
| **Pass/Fail** | ⬜ |

### TC-3.4: Impact Score Calculation
| Property | Detail |
|----------|--------|
| **Description** | Scores are computed using all 6 weighted factors |
| **Steps** | Verify `contributing_factors` in impact score output |
| **Expected** | All 6 weights present; sum to ~1.0; score between 0–100 |
| **Pass/Fail** | ⬜ |

### TC-3.5: Priority Assignment
| Property | Detail |
|----------|--------|
| **Description** | Priority labels match score ranges |
| **Steps** | Cross-check scores and priorities for all themes |
| **Expected** | P0: 90–100, P1: 70–89, P2: 40–69, P3: 0–39 |
| **Pass/Fail** | ⬜ |

### TC-3.6: PM Recommendations Quality
| Property | Detail |
|----------|--------|
| **Description** | Recommendations are actionable and evidence-based |
| **Steps** | Review generated recommendations manually |
| **Expected** | Each recommendation has: title, description, ≥1 evidence quote, priority. No generic advice like "improve the app" |
| **Pass/Fail** | ⬜ |

### TC-3.7: Weekly Pulse Completeness
| Property | Detail |
|----------|--------|
| **Description** | Pulse contains all required sections |
| **Steps** | Validate pulse JSON against schema |
| **Expected** | Contains: executive_summary, top_themes (3), trend_changes, user_quotes (3), impact_scores, recommendations, action_items (3) |
| **Pass/Fail** | ⬜ |

### TC-3.8: Full Pipeline E2E
| Property | Detail |
|----------|--------|
| **Description** | Complete pipeline runs without errors |
| **Steps** | `POST /api/v1/pipeline/run` → wait for completion |
| **Expected** | Pipeline status = `completed`; all 7 agents produce valid output; pulse generated |
| **Pass/Fail** | ⬜ |

---

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Trend detection (5 themes, 4 weeks) | < 15 seconds | |
| Impact scoring (5 themes) | < 10 seconds | |
| PM recommendation generation | < 30 seconds | |
| Pulse generation | < 20 seconds | |
| Full pipeline (Agents 1–7) | < 5 minutes | |

---

## Definition of Done

- [ ] All 8 exit criteria marked ✅
- [ ] All 8 test cases pass
- [ ] Full pipeline produces a coherent weekly pulse
- [ ] Manual review confirms recommendation quality
- [ ] Performance benchmarks within target
- [ ] Code reviewed and committed
