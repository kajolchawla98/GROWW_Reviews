# Phase 1 Evaluation — Data Ingestion & Storage Foundation

> **Phase**: 1 | **Status**: Not Started | **Eval Version**: 1.0

---

## Exit Criteria Checklist

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Review Ingestion Agent fetches ≥100 reviews from Play Store | ⬜ | |
| 2 | PII stripping removes all usernames, emails, phone numbers | ⬜ | |
| 3 | Deduplication prevents duplicate reviews across runs | ⬜ | |
| 4 | All reviews persisted to database with correct schema | ⬜ | |
| 5 | Vector store contains embeddings for all ingested reviews | ⬜ | |
| 6 | Pipeline run is logged in `pipeline_runs` table | ⬜ | |
| 7 | `POST /api/v1/pipeline/run` triggers ingestion successfully | ⬜ | |
| 8 | Environment config loads from `.env` without hardcoded secrets | ⬜ | |

---

## Test Cases

### TC-1.1: Review Fetching
| Property | Detail |
|----------|--------|
| **Description** | Fetch GROWW app reviews from Google Play Store |
| **Precondition** | Valid app ID configured (`com.nextbillion.groww`) |
| **Steps** | 1. Call `ingestion_agent.fetch_reviews(app_id, last_4_weeks)` |
| **Expected** | Returns `List[ReviewRecord]` with ≥100 reviews, each having: `review_id`, `text`, `rating (1-5)`, `date`, `language` |
| **Pass/Fail** | ⬜ |

### TC-1.2: PII Stripping
| Property | Detail |
|----------|--------|
| **Description** | Verify PII removal from review text |
| **Precondition** | Sample reviews with embedded PII |
| **Test Data** | `"Great app! Contact me at john@email.com or 9876543210 - John Smith"` |
| **Expected** | Output: `"Great app! Contact me at [EMAIL] or [PHONE] - [NAME]"` or similar anonymization |
| **Pass/Fail** | ⬜ |

### TC-1.3: Deduplication
| Property | Detail |
|----------|--------|
| **Description** | Running pipeline twice doesn't create duplicate reviews |
| **Steps** | 1. Run pipeline → note review count. 2. Run pipeline again. 3. Check total review count |
| **Expected** | No duplicate `review_id` entries in database |
| **Pass/Fail** | ⬜ |

### TC-1.4: Database Persistence
| Property | Detail |
|----------|--------|
| **Description** | All reviews stored with correct schema |
| **Steps** | Query `SELECT * FROM reviews LIMIT 10` |
| **Expected** | All columns populated: `id`, `review_text`, `rating`, `review_date`, `app_version`, `language`, `word_count`, `ingested_at` |
| **Pass/Fail** | ⬜ |

### TC-1.5: Vector Store Embeddings
| Property | Detail |
|----------|--------|
| **Description** | All reviews have corresponding embeddings |
| **Steps** | 1. Count reviews in DB. 2. Count embeddings in ChromaDB |
| **Expected** | Counts match; similarity search for "UPI payment failure" returns relevant reviews |
| **Pass/Fail** | ⬜ |

### TC-1.6: Pipeline Run Logging
| Property | Detail |
|----------|--------|
| **Description** | Pipeline execution is tracked |
| **Steps** | 1. Trigger pipeline. 2. Query `pipeline_runs` table |
| **Expected** | Entry with `started_at`, `completed_at`, `status='completed'`, `config` (JSON) |
| **Pass/Fail** | ⬜ |

### TC-1.7: API Endpoint
| Property | Detail |
|----------|--------|
| **Description** | Pipeline can be triggered via API |
| **Steps** | `POST /api/v1/pipeline/run` with `{"app_id": "com.nextbillion.groww"}` |
| **Expected** | Returns `202 Accepted` with `{"pipeline_run_id": "...", "status": "running"}` |
| **Pass/Fail** | ⬜ |

### TC-1.8: Error Handling
| Property | Detail |
|----------|--------|
| **Description** | Graceful handling of scraping failures |
| **Steps** | 1. Use invalid app ID. 2. Simulate network timeout |
| **Expected** | Pipeline logs error, sets `status='failed'`, returns meaningful error message |
| **Pass/Fail** | ⬜ |

---

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Review fetch time (500 reviews) | < 30 seconds | |
| Embedding generation (500 reviews) | < 60 seconds | |
| Database insert (500 reviews) | < 5 seconds | |
| Full pipeline run (ingestion only) | < 2 minutes | |

---

## Definition of Done

- [ ] All 8 exit criteria marked ✅
- [ ] All 8 test cases pass
- [ ] Performance benchmarks within target
- [ ] No hardcoded API keys or secrets
- [ ] Code reviewed and committed to repository
