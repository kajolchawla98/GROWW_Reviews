# Phase 2 Evaluation — Core AI Analysis Agents

> **Phase**: 2 | **Status**: Not Started | **Eval Version**: 1.0

---

## Exit Criteria Checklist

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Theme Classification Agent clusters reviews into ≤5 meaningful themes | ⬜ | |
| 2 | Each theme has a human-readable name and AI summary | ⬜ | |
| 3 | Sentiment Agent classifies all reviews (positive/negative/neutral/mixed) | ⬜ | |
| 4 | Emotion labels assigned (anger, frustration, satisfaction, delight, confusion) | ⬜ | |
| 5 | All classifications include confidence scores (0–1) | ⬜ | |
| 6 | Theme and sentiment data persisted to database | ⬜ | |
| 7 | Agents 2 & 3 run in parallel in orchestrator | ⬜ | |
| 8 | API endpoints return theme and sentiment data | ⬜ | |

---

## Test Cases

### TC-2.1: Theme Clustering Quality
| Property | Detail |
|----------|--------|
| **Description** | Themes are coherent and distinct |
| **Steps** | 1. Run Theme Agent on 200+ reviews. 2. Review generated theme names |
| **Expected** | ≤5 themes, each with a clear name (e.g., "KYC Delays", "UPI Failures", "App Crashes"). No generic themes like "Other" containing >30% of reviews |
| **Pass/Fail** | ⬜ |

### TC-2.2: Theme Classification Confidence
| Property | Detail |
|----------|--------|
| **Description** | Confidence scores are meaningful |
| **Steps** | Verify confidence distribution across themes |
| **Expected** | Average confidence ≥ 0.7; no theme with confidence < 0.5 |
| **Pass/Fail** | ⬜ |

### TC-2.3: Theme-Review Mapping
| Property | Detail |
|----------|--------|
| **Description** | Every review is assigned to exactly one theme |
| **Steps** | Count total review-theme assignments vs total reviews |
| **Expected** | Every ingested review has a theme assignment; no orphaned reviews |
| **Pass/Fail** | ⬜ |

### TC-2.4: Sentiment Classification Accuracy
| Property | Detail |
|----------|--------|
| **Description** | Sentiment labels align with review content |
| **Steps** | Manually sample 20 reviews; compare LLM sentiment vs human judgment |
| **Expected** | ≥85% agreement between LLM classification and human judgment |
| **Pass/Fail** | ⬜ |

### TC-2.5: Sentiment Score Range
| Property | Detail |
|----------|--------|
| **Description** | Sentiment scores are within valid range |
| **Steps** | Query all sentiment scores |
| **Expected** | All scores in range [-1.0, 1.0]; negative reviews have score < 0; positive reviews > 0 |
| **Pass/Fail** | ⬜ |

### TC-2.6: Emotion Detection
| Property | Detail |
|----------|--------|
| **Description** | Emotion labels are assigned and meaningful |
| **Steps** | Sample reviews with strong emotions |
| **Test Data** | "This app is terrible! My money is stuck!" → should detect `anger` or `frustration` |
| **Expected** | Emotion labels from defined set; match human expectation for sampled reviews |
| **Pass/Fail** | ⬜ |

### TC-2.7: Parallel Execution
| Property | Detail |
|----------|--------|
| **Description** | Theme and Sentiment agents run concurrently |
| **Steps** | 1. Time sequential execution. 2. Time parallel execution |
| **Expected** | Parallel execution time ≈ max(theme_time, sentiment_time), not sum |
| **Pass/Fail** | ⬜ |

### TC-2.8: API Endpoints
| Property | Detail |
|----------|--------|
| **Description** | Theme and sentiment data accessible via API |
| **Steps** | Call `GET /api/v1/themes` and `GET /api/v1/themes/{id}/reviews` |
| **Expected** | Returns JSON with theme data including sentiment breakdown per theme |
| **Pass/Fail** | ⬜ |

### TC-2.9: Pydantic Schema Validation
| Property | Detail |
|----------|--------|
| **Description** | Agent outputs conform to defined schemas |
| **Steps** | Validate agent output against Pydantic models |
| **Expected** | No validation errors; all required fields present |
| **Pass/Fail** | ⬜ |

---

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Theme clustering (300 reviews) | < 45 seconds | |
| Sentiment analysis (300 reviews, batched) | < 60 seconds | |
| Parallel agent execution (both) | < 90 seconds | |
| LLM API calls per pipeline run | < 20 calls | |

---

## Definition of Done

- [ ] All 8 exit criteria marked ✅
- [ ] All 9 test cases pass
- [ ] Manual spot-check of 20 reviews confirms quality
- [ ] Performance benchmarks within target
- [ ] Code reviewed and committed
