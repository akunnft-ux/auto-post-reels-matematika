# Architecture: Self-Learning Engine

## 1. Architecture Overview

**Pattern:** Modular monolith — self-contained `self_learning/` package inside each bot's existing codebase.

**Design principle:** The self-learning module is completely decoupled from the posting pipeline. It reads/writes files in `data/` and exposes a `learning_config.json` that `main.py` consumes. No direct function calls between the two systems at runtime.

```
┌─────────────────────────────────────────────────────┐
│                   main.py                           │
│  ┌──────────────────────────────────────────────┐   │
│  │  Posting Pipeline                             │   │
│  │  (existing: generate → render → post)        │   │
│  │                                              │   │
│  │  Reads: learning_config.json                  │   │
│  │  Writes: history.json                        │   │
│  └──────────────────────────────────────────────┘   │
│                         │ reads                     │
│                         ▼                           │
│  ┌──────────────────────────────────────────────┐   │
│  │  data/learning_config.json                   │   │
│  │  (written by self_learning module)           │   │
│  └──────────────────────────────────────────────┘   │
│                         ▲ writes                    │
│  ┌──────────────────────────────────────────────┐   │
│  │  self_learning/ (standalone module)          │   │
│  │  Triggered by Telegram CSV upload            │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 2. Context Diagram

```
┌──────────┐     CSV file (manual download)     ┌──────────────────┐
│   User   │ ──────────────────────────────────► │   Telegram Bot   │
│  (Admin) │                                     │  (poll getUpdates)│
│          │ ◄────────────────────────────────── │                  │
└──────────┘    Notification (learning summary)  └────────┬─────────┘
                                                          │
                                                          ▼
                                           ┌──────────────────────────┐
                                           │  self_learning/ module   │
                                           │                          │
                                           │  1. csv_parser.py        │
                                           │  2. analytics_store.py   │
                                           │  3. classifier.py        │
                                           │  4. learning_engine.py   │
                                           └──────────┬───────────────┘
                                                      │ writes
                                                      ▼
                                           ┌──────────────────────────┐
                                           │  data/                   │
                                           │  ├─ analytics.json       │
                                           │  ├─ classification.json  │
                                           │  ├─ learning_iteration   │
                                           │  │       .json           │
                                           │  ├─ learning_config.json │
                                           │  └─ history.json         │
                                           └──────────────────────────┘
                                                      │
                                                      ▼
                                           ┌──────────────────────────┐
                                           │  GitHub Actions          │
                                           │  git add data/*.json     │
                                           │  git commit + push       │
                                           └──────────────────────────┘
```

## 3. Module Architecture

### self_learning/ Package

| File | Purpose | Dependencies |
|---|---|---|
| `__init__.py` | Exposes `run_self_learning(csv_path)` orchestrator | All submodules |
| `csv_parser.py` | Parse Facebook Insights CSV → list of dicts | csv, io |
| `analytics_store.py` | Load/merge/save analytics.json + classification.json | os, json |
| `classifier.py` | Classify posts: viral/good/bad | math |
| `learning_engine.py` | Compute new weights/rankings, write learning_config.json | os, json, copy |
| `learning_config.json` | Output file — consumed by main.py | N/A |

### Module Responsibilities

#### csv_parser.py
- Accept CSV file path
- Auto-detect column headers (flexible position)
- Map to standard fields: post_id/post_text, views, likes, comments, shares, date
- If columns ambiguous, use Gemini AI to infer mapping (reuse existing `parse_csv_with_gemini` pattern from reels-matematika)
- Return list of `AnalyticsRecord` dicts

#### analytics_store.py
- Load existing `data/analytics.json`
- Merge new records: deduplicate by `post_id` (keep latest)
- Trim to max 500 records
- Load existing `data/classification.json` (append-only)
- Save both files

#### classifier.py
- Accept analytics records + current follower count
- Apply 2-phase threshold (social-media-growth-engine §5.1):
  - If followers < 100: VIRAL = views > 1000
  - Else: VIRAL = views > 10 × followers
  - GOOD = engagement_rate > niche_baseline AND NOT VIRAL
  - BAD = views < 50 OR engagement_rate < 1%
- `niche_baseline` = trailing 30-day median engagement rate (computed from analytics)
- Return classification_record per post

#### learning_engine.py
- Read current `learning_config.json` (or defaults)
- Determine which variable to change this iteration (rotation: weights → hooks → CTA → hashtags → repeat)
- Compute new value:
  - **Weights**: For each content type, viral_ratio = viral_count / total_count. Normalize to sum 1.0, clamp [0.1, 0.7].
  - **Hooks/CTA**: For each template, avg_engagement_rate. Sort descending.
  - **Hashtags**: For each hashtag, count appearances in viral posts. Sort descending.
- Write updated `learning_config.json`
- Append to `learning_iteration.json`

## 4. Data Layer

### File: data/analytics.json
```json
[
  {
    "post_id": "fb_post_12345",
    "platform": "facebook",
    "content_type": "quiz",
    "views": 1500,
    "likes": 120,
    "comments": 45,
    "shares": 30,
    "engagement_rate": 0.13,
    "source": "manual",
    "fetched_at": "2026-06-25T10:00:00Z"
  }
]
```

### File: data/classification.json
```json
[
  {
    "post_id": "fb_post_12345",
    "classification": "viral",
    "metric_triggered": "views=1500 > 10*followers(120)=1200",
    "follower_count_at_post": 120,
    "computed_at": "2026-06-25T10:05:00Z"
  }
]
```

### File: data/learning_config.json
```json
{
  "content_type_weights": {
    "quiz": 0.45,
    "fakta": 0.35,
    "tips": 0.20
  },
  "hook_templates": {
    "quiz": [
      "Kuis matematika... coba jawab!",
      "Kamu bisa jawab soal ini?"
    ],
    "fakta": [...],
    "tips": [...]
  },
  "cta_pool": [
    "Tulis jawabanmu di komentar!",
    "Share ke temanmu!"
  ],
  "hashtag_pool": [
    "#SoalMatematika",
    "#CPNS2026"
  ],
  "variable_rotation_index": 2,
  "updated_at": "2026-06-25T10:05:00Z"
}
```

### File: data/learning_iteration.json
```json
[
  {
    "id": "iter-001",
    "based_on_post_id": "fb_post_12345",
    "variable_changed": "content_type_weights",
    "previous_value": {"quiz": 0.4, "fakta": 0.3, "tips": 0.3},
    "new_value": {"quiz": 0.45, "fakta": 0.35, "tips": 0.20},
    "created_at": "2026-06-25T10:05:00Z"
  }
]
```

## 5. Integration Design

### Telegram CSV Upload Detection

The existing `check_telegram_mode()` function polls `getUpdates`. Extend this:

```python
# Pseudocode for extended handler
def check_telegram_updates():
    updates = poll_getUpdates(offset=last_update_id + 1)

    for update in updates:
        if update has document and document.mime_type == "text/csv":
            file_id = update.document.file_id
            csv_path = download_telegram_file(file_id)
            run_self_learning(csv_path)
        elif update is /mode command:
            # existing mode switching
            ...
        elif update is text message:
            # check if it's a command
            ...
```

**Key design decision:** The CSV handler is added to the bot that receives the CSV upload. Since all 3 bots share the same Telegram account, any one of them can detect and process the CSV. Alternatively, designate one bot (reels-matematika, which already has `download_telegram_file` + `parse_csv_with_gemini`) as the CSV processor.

**Recommended approach:** Add CSV handling to each bot independently. Each maintains its own analytics.json since they post different content. The user sends CSV → whichever bot runs next picks it up → processes only its own posts (filter by content pattern or post_id prefix).

### Git Persistence

After self-learning runs:
```
git add data/*.json
git commit -m "chore: update self-learning data [skip ci]"
git push
```

## 6. Security Design

| Concern | Approach |
|---|---|
| CSV upload auth | Only accept files from TELEGRAM_CHAT_ID |
| File validation | Accept only .csv extension, reject others |
| Error isolation | Self-learning failures never block posting (try/except around module call) |
| Secret management | Existing env vars unchanged |

## 7. Per-Bot Implementation Notes

### auto-post-reels-matematika

**Existing code to retain:**
- `download_telegram_file()` (line 752)
- `parse_csv_with_gemini()` (line 773) — reuse for CSV column inference
- `classify_performance()` (line 947) — align with new classifier
- `run_self_learning_review()` (line 988) — keep as reporting-only
- `analytics.json` format — normalize to new schema
- `growth.json` — keep as-is

**New code needed:**
- `self_learning/__init__.py` — orchestrator
- `self_learning/csv_parser.py` — wrap existing parse_csv_with_gemini
- `self_learning/analytics_store.py` — merge/dedup logic
- `self_learning/classifier.py` — aligned 2-phase threshold
- `self_learning/learning_engine.py` — new
- `self_learning/learning_config.json` — new
- Extend Telegram handler to detect CSV documents
- Update `main.py` to read learning_config.json at startup
- Update `pick_content_type()`, `get_hook()`, `get_cta()`, caption builder

### auto-post-soal-matematika

**New code needed (from scratch):**
- `self_learning/` full module (same files as above)
- Add `HOOK_TEMPLATES`, `CTA_POOL` to main.py (currently nonexistent)
- Extend Telegram handler for CSV detection
- Update `main()` to read learning_config.json
- Update GA workflow file list

### auto-post-reels-manim

**New code needed (from scratch):**
- `self_learning/` full module
- Add `HOOK_TEMPLATES` to main.py (currently nonexistent)
- Extend Telegram handler for CSV detection
- Update `main()` to read learning_config.json
- Update GA workflow file list + stash-rebase pattern

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| CSV format unknown/unexpected | Flexible header detection + Gemini fallback |
| Learning degrades content | One-variable-at-a-time + min data threshold (3 records) |
| Race condition on data files | Add concurrency group to GA workflows |
| learning_config.json corrupt | main.py falls back to hardcoded defaults |
| Too few analytics records | Learning engine skips if < 3 records |
