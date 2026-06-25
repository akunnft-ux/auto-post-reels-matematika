# PRD: Self-Learning Engine — Auto Post Reels Matematika

## Document Control

**Version History**

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.1 | 2026-06-25 | Tech Lead | Initial draft — self-learning feature addendum |

**Change Request Log**

| CR ID | Date | Description | Affected Sections |
|---|---|---|---|
| CR-SL-001 | 2026-06-25 | Add self-learning via CSV analytics to all 3 bots | All sections below |

## 1. Executive Summary

Add a closed-loop self-learning system to the existing auto-post bot that ingests Facebook performance data (via CSV export), classifies post performance (viral/good/bad), and automatically adjusts content generation parameters — topic weights, hook templates, CTA pool, hashtag pool, and posting schedule — to optimize engagement and accelerate account growth.

## 2. Business Objectives

| ID | Objective | Metric |
|---|---|---|
| BO-001 | Increase viral/good post ratio over time | Viral/good ratio trends up week-over-week |
| BO-002 | Eliminate manual parameter tuning | Zero manual edits to weights/hooks/CTA/hashtags after deployment |
| BO-003 | Make bot adapt to audience preferences autonomously | Content type distribution shifts toward what performs best |

## 3. Project Scope

**In Scope:**
- CSV parser for Facebook Insights export files
- Analytics storage (analytics.json, classification.json, learning_iteration.json)
- Performance classifier (2-phase viral/good/bad threshold)
- Learning engine that updates: CONTENT_TYPE_WEIGHTS, HOOK_TEMPLATES priority, CTA_POOL priority, HASHTAG_POOL priority
- learning_config.json as persistent config consumed by main.py
- Git persistence of all new data files
- Telegram notification on learning completion
- One-variable-at-a-time iteration logging

**Out of Scope (this phase):**
- Facebook Insights API integration (future)
- A/B testing framework
- Semantic deduplication
- Trend-signal integration
- Dashboard/UI

## 4. Functional Requirements

### FR-SL-001: CSV File Detection & Download (Core)

| Field | Value |
|---|---|
| Description | Bot detects CSV file uploads from authorized Telegram chat and downloads the file |
| Traces to | BO-001, BO-003 |
| Inputs | Telegram file upload event (document with .csv extension) |
| Outputs | Downloaded CSV file saved to temp directory |
| Validation | File extension must be .csv; sender must be TELEGRAM_CHAT_ID |
| Error Handling | Non-CSV file → ignore; unauthorized sender → ignore; download failure → notify Telegram |
| Acceptance Criteria | AC-SL-001 |

### FR-SL-002: CSV Parsing (Core)

| Field | Value |
|---|---|
| Description | Parse CSV columns into structured analytics records. Column detection is flexible (auto-detect headers, not position-dependent) |
| Traces to | BO-001 |
| Inputs | CSV file path |
| Outputs | Array of analytics_record objects |
| Validation | Each record must have at least: post_id/post_text, views, likes, comments, shares |
| Error Handling | Empty file → return empty array; missing columns → skip row and log |
| Acceptance Criteria | AC-SL-002 |

### FR-SL-003: Analytics Storage (Core)

| Field | Value |
|---|---|
| Description | Store parsed analytics records in data/analytics.json; merge with existing, deduplicate by post_id |
| Traces to | BO-001 |
| Inputs | Array of analytics_record objects |
| Outputs | Updated data/analytics.json |
| Validation | Max 500 records; deduplicate by post_id (keep latest) |
| Error Handling | Corrupt existing file → overwrite with new data |
| Acceptance Criteria | AC-SL-003 |

### FR-SL-004: Performance Classification (Core)

| Field | Value |
|---|---|
| Description | Classify each post as viral/good/bad using 2-phase threshold (per social-media-growth-engine §5.1) |
| Traces to | BO-001, BO-003 |
| Inputs | Analytics records, follower count |
| Outputs | classification_record per post |
| Validation | Must meet 2-phase rule; engagement_rate = (likes+comments+shares)/views |
| Error Handling | Insufficient data (<3 records) → skip classification |
| Acceptance Criteria | AC-SL-004 |

### FR-SL-005: Learning Engine — Content Type Weights (Core)

| Field | Value |
|---|---|
| Description | Adjust CONTENT_TYPE_WEIGHTS based on viral/good ratio per content type. Increase weight for types with higher viral ratio, decrease for types with higher bad ratio |
| Traces to | BO-001, BO-002, BO-003 |
| Inputs | Classification records grouped by content_type |
| Outputs | Updated weight values in learning_config.json |
| Validation | Min weight 0.1, max 0.7; must sum to 1.0; require ≥3 classified posts to act |
| Error Handling | Insufficient data → keep current weights |
| Acceptance Criteria | AC-SL-005 |

### FR-SL-006: Learning Engine — Hook/CTA/Hashtag Ranking (Supporting)

| Field | Value |
|---|---|
| Description | Re-rank HOOK_TEMPLATES, CTA_POOL, HASHTAG_POOL by average engagement rate of posts that used each. Higher-ranked templates appear first in selection pool |
| Traces to | BO-001, BO-003 |
| Inputs | Analytics records with hook/cta/hashtag metadata per post |
| Outputs | Re-ranked lists in learning_config.json |
| Validation | Require ≥2 data points per template to re-rank; unchanged if insufficient |
| Acceptance Criteria | AC-SL-006 |

### FR-SL-007: Learning Config Consumption (Core)

| Field | Value |
|---|---|
| Description | main.py reads learning_config.json at startup; uses adjusted weights/rankings for content generation instead of hardcoded constants |
| Traces to | BO-002, BO-003 |
| Inputs | learning_config.json path |
| Outputs | Python constants replaced with values from config file |
| Validation | If file missing/corrupt → fall back to hardcoded defaults |
| Acceptance Criteria | AC-SL-007 |

### FR-SL-008: Git Persistence (Supporting)

| Field | Value |
|---|---|
| Description | All self-learning JSON files in data/ are committed and pushed to git after learning run, same pattern as history.json |
| Traces to | BO-002 |
| Inputs | Updated JSON files |
| Outputs | Git commit with updated files |
| Validation | Only files in data/ directory; [skip ci] in commit message |
| Acceptance Criteria | AC-SL-008 |

### FR-SL-009: One-Variable-at-a-Time Logging (Supporting)

| Field | Value |
|---|---|
| Description | Log each learning iteration: which variable was changed, previous value, new value, which post_id triggered it. Enforce one variable per iteration |
| Traces to | BO-003 |
| Outputs | data/learning_iteration.json — append-only log |
| Validation | Each entry has exactly one variable_changed field |
| Acceptance Criteria | AC-SL-009 |

### FR-SL-010: Telegram Notification (Peripheral)

| Field | Value |
|---|---|
| Description | Send Telegram message on learning completion with summary: records processed, classification counts, which weight changed |
| Traces to | BO-002 |
| Inputs | Learning results |
| Outputs | Telegram message |
| Validation | Message sent to TELEGRAM_CHAT_ID |
| Acceptance Criteria | AC-SL-010 |

## 5. Non-Functional Requirements

| ID | Requirement | Target | Traces to |
|---|---|---|---|
| NFR-SL-001 | Source field | All analytics records carry `source: "manual"` | BO-003 |
| NFR-SL-002 | Minimum data | Learning engine only activates when ≥3 analytics records exist | BO-003 |
| NFR-SL-003 | Zero disruption | Existing posting workflow must never fail if self-learning module errors | BO-002 |
| NFR-SL-004 | Persistence | All data files survive GitHub Actions ephemeral runners via git commit/push | BO-002 |

## 6. Data Requirements

### analytics_record

| Field | Type | Description |
|---|---|---|
| post_id | string | Facebook post ID or text identifier |
| platform | string | "facebook" |
| content_type | string | "quiz", "fakta", or "tips" (mapped from post) |
| views | int | Post views |
| likes | int | Post likes |
| comments | int | Post comments |
| shares | int | Post shares |
| engagement_rate | float | (likes+comments+shares)/views |
| source | string | Always "manual" (CSV import) |
| fetched_at | string | ISO8601 timestamp |

### classification_record

| Field | Type | Description |
|---|---|---|
| post_id | string | Matches analytics_record.post_id |
| classification | string | "viral", "good", or "bad" |
| metric_triggered | string | Which metric caused this classification |
| follower_count_at_post | int | Follower count when posted |
| computed_at | string | ISO8601 timestamp |

### learning_iteration

| Field | Type | Description |
|---|---|---|
| id | string | UUID |
| based_on_post_id | string | The post that triggered this iteration |
| variable_changed | string | "content_type_weights", "hook_ranking", "cta_ranking", or "hashtag_ranking" |
| previous_value | any | Value before change |
| new_value | any | Value after change |
| created_at | string | ISO8601 timestamp |

### learning_config

| Field | Type | Description |
|---|---|---|
| content_type_weights | dict | {quiz: float, fakta: float, tips: float} summing to 1.0 |
| hook_templates | list | Re-ranked list of hook strings |
| cta_pool | list | Re-ranked list of CTA strings |
| hashtag_pool | list | Re-ranked list of hashtag strings |
| updated_at | string | ISO8601 timestamp |

## 7. Business Rules

| Rule | Description |
|---|---|
| BR-SL-001 | One variable changed per learning iteration. Rotate: weights → hooks → CTA → hashtags → repeat |
| BR-SL-002 | Minimum 3 classified posts before any learning action |
| BR-SL-003 | Weights capped at 0.1 (min) and 0.7 (max) per content type |
| BR-SL-004 | Weights must sum to 1.0 after adjustment |
| BR-SL-005 | Template re-ranking requires ≥2 data points for that template |
| BR-SL-006 | Fall back to hardcoded defaults if learning_config.json is missing or corrupt |

## 8. Workflow

**Self-Learning Workflow (Manual Trigger via CSV Upload):**

```
User downloads CSV from Facebook Insights
        │
User sends CSV file to Telegram chat
        │
Bot detects file document in getUpdates
        │
Bot downloads file via Telegram File API
        │
Bot parses CSV → analytics records (flexible column detection)
        │
Bot merges into data/analytics.json (dedup by post_id)
        │
Bot classifies each post (viral/good/bad)
        │
Bot saves data/classification.json
        │
Bot runs learning engine:
  │
  ├─ Check variable rotation order
  ├─ Read current learning_config.json
  ├─ Compute new value for current variable
  └─ Write updated learning_config.json
        │
Bot saves data/learning_iteration.json
        │
Bot runs git add + commit + push
        │
Bot sends Telegram summary notification
```

**Alternate Flow:** CSV has no new records → bot notifies "no new data, learning skipped"
**Failure Flow:** CSV parse fails → bot notifies "CSV parsing failed: <reason>"

**Daily Post Workflow (Consumption):**

```
Bot starts (GA run)
        │
Bot loads learning_config.json
        │
Bot falls back to hardcoded defaults if missing
        │
Bot generates content using adjusted parameters
        │
Bot posts normally (existing flow unchanged)
```

## 9. Acceptance Criteria

| ID | FR | Given | When | Then |
|---|---|---|---|---|
| AC-SL-001 | FR-SL-001 | A CSV file is sent to the Telegram chat | Bot polls getUpdates | Bot downloads file to temp directory |
| AC-SL-002 | FR-SL-002 | A valid Facebook Insights CSV is downloaded | Bot parses it | Array of analytics_record objects is produced with correct field mapping |
| AC-SL-003 | FR-SL-003 | Parsed analytics records are ready | Bot saves them | analytics.json contains merged records with no duplicate post_ids |
| AC-SL-004 | FR-SL-004 | Analytics records exist for ≥3 posts | Bot classifies each | Classification records show viral/good/bad with metric_triggered field |
| AC-SL-005 | FR-SL-005 | Classification records exist across content types | Learning engine runs | Weights in learning_config.json are adjusted within [0.1, 0.7] and sum to 1.0 |
| AC-SL-006 | FR-SL-006 | Templates have ≥2 data points each | Learning engine runs | Re-ranked lists are written to learning_config.json |
| AC-SL-007 | FR-SL-007 | main.py starts | Bot reads learning_config.json | Content generation uses adjusted parameters |
| AC-SL-008 | FR-SL-008 | Self-learning completes | Git commit/push runs | All data/*.json files are pushed to remote |
| AC-SL-009 | FR-SL-009 | Learning engine changes a variable | Iteration is logged | learning_iteration.json has one entry per run |
| AC-SL-010 | FR-SL-010 | Learning completes or fails | Bot sends message | Telegram chat receives summary notification |

## 10. Traceability Matrix

| BO | FR/NFR | AC | Risk |
|---|---|---|---|
| BO-001 | FR-SL-001, FR-SL-002, FR-SL-003, FR-SL-004, FR-SL-005, FR-SL-006 | AC-SL-001 through AC-SL-006 | RISK-SL-001 |
| BO-002 | FR-SL-005, FR-SL-007, FR-SL-008, FR-SL-010, NFR-SL-003, NFR-SL-004 | AC-SL-005, AC-SL-007, AC-SL-008, AC-SL-010 | RISK-SL-002 |
| BO-003 | FR-SL-001, FR-SL-004, FR-SL-005, FR-SL-006, FR-SL-009, NFR-SL-001, NFR-SL-002 | AC-SL-001, AC-SL-004, AC-SL-005, AC-SL-006, AC-SL-009 | RISK-SL-003 |

## 11. Risk Assessment

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RISK-SL-001 | CSV format incompatible with parser | Medium | High | Use Gemini AI to flexibly map columns; fall back to manual mapping |
| RISK-SL-002 | Learning degrades performance | Low | Medium | One-variable-at-a-time logging enables revert; min data threshold prevents premature learning |
| RISK-SL-003 | Git conflicts from concurrent GA runs | Low | Medium | Add concurrency group to workflow; stash-rebase pattern already in use |

## 12. Release Strategy

| Phase | Scope |
|---|---|
| Phase 1 (this PRD) | CSV parsing + classification + learning engine + config consumption + git persistence |
| Phase 2 (future) | Facebook Insights API integration for source: "api" |
| Phase 3 (future) | Schedule optimization based on best posting times |

## 13. Effort Estimate

| Component | Effort (hours) |
|---|---|
| CSV parser + analytics storage | 2 |
| Performance classifier | 1 |
| Learning engine | 2 |
| main.py integration (read config) | 1 |
| Git workflow updates | 0.5 |
| Total per bot | 6.5 |
| **Total (3 bots)** | **~19.5 hours** |

## 14. Per-Bot Differences

| Aspect | auto-post-reels-matematika | auto-post-soal-matematika | auto-post-reels-manim |
|---|---|---|---|
| Existing analytics | ✅ Has analytics.json, growth.json, classify_performance(), run_analytics_batch() | ❌ None | ❌ None |
| Content types | quiz, fakta, tips | quiz only | quiz, fakta, tips |
| Learning scope | weights + hooks + CTA + hashtags | weights N/A (only quiz); hooks/CTA/hashtags only | weights + hooks + CTA + hashtags |
| Strategy | Keep existing analytics code; add CSV parser + learning engine alongside | Build self_learning/ from scratch | Build self_learning/ from scratch |
