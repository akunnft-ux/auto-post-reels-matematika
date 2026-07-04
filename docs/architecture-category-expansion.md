# Architecture Expansion — Multi-Category Content

## Overview

Add a **category** dimension to the existing content generation pipeline. Currently the bot selects:
- **Topic** (5 matematika subjects)
- **Content type** (quiz/fakta/tips)

Now also selects:
- **Category** (7 exam types: CPNS, Olimpiade SD/SMP/SMA, Ujian SD/SMP/SMA)

Category is orthogonal to topic and content type — all combinations are valid.

---

## Architecture Decision: Module Change

The existing `main.py` as a single module is sufficient. The category system does not warrant splitting into separate modules.

**Change:** Add `CATEGORIES` dict + `pick_category()` function + modify existing functions to accept category parameter.

---

## Data Flow (Updated)

```
Start
  ↓
pick_category()   ← NEW — random from 7, equal weight
  ↓
pick_topic()       ← unchanged
  ↓
pick_content_type() ← unchanged
  ↓
generate_narasi(topic, history, content_type, category)  ← MODIFIED — prompt includes category context
  ↓
build_caption(narasi, topic, content_type, hook, category) ← MODIFIED — hashtags from category pool
  ↓
render_video(...) ← MODIFIED — header shows category label
  ↓
post → save_history(entry with category field) ← MODIFIED
```

---

## Category Selection

```python
CATEGORY_KEYS = ["cpns", "olimpiade_sd", "olimpiade_smp", "olimpiade_sma",
                 "ujian_sd", "ujian_smp", "ujian_sma"]
CATEGORY_WEIGHTS = {k: 1/7 for k in CATEGORY_KEYS}  # equal weight

def pick_category():
    return random.choices(CATEGORY_KEYS, weights=[CATEGORY_WEIGHTS[k] for k in CATEGORY_KEYS], k=1)[0]
```

No repeat-prevention per category — unlike topics (which prevent same topic in 1 day), categories can repeat.

---

## Category Data Dictionary

```python
CATEGORIES = {
    "cpns": {
        "label": "CPNS",
        "sub_label": "CPNS • TKA • SNBT",
        "hashtag_pool": [...],
        "prompt_context": "soal matematika untuk persiapan CPNS/TKA/SNBT...",
    },
    "olimpiade_sd": {
        "label": "Olimpiade SD",
        "sub_label": "Olimpiade Matematika SD",
        "hashtag_pool": [...],
        "prompt_context": "soal olimpiade matematika tingkat SD...",
    },
    # ... (6 more)
}
```

**Self-learning compatibility:** Category weights CAN be overridden by `learning_config.json` via `load_and_apply_learning_config()`. Add `category_weights` key.

---

## History Schema Change

**Before:**
```json
{
  "soal": "...",
  "jawaban": "...",
  "topik": "deret_angka",
  "tanggal": "2026-07-03",
  "content_type": "quiz"
}
```

**After:**
```json
{
  "soal": "...",
  "jawaban": "...",
  "topik": "deret_angka",
  "tanggal": "2026-07-03",
  "content_type": "quiz",
  "category": "olimpiade_sd"    // NEW
}
```

Legacy entries without `category` default to `"cpns"` at read time.

---

## Affected Functions

| Function | Change |
|---|---|
| `pick_category()` | **NEW** — select category from 7 with weights |
| `generate_narasi()` | Add `category` param; prompt includes `CATEGORIES[category].prompt_context` |
| `build_caption()` | Add `category` param; hashtags from `CATEGORIES[category].hashtag_pool` |
| `render_frame_soal()` | `sub_label` from `CATEGORIES[category].sub_label` instead of hardcoded "CPNS • TKA • SNBT" |
| `main()` | Call `pick_category()`; pass category through pipeline; save to history |
| `load_and_apply_learning_config()` | Add support for `category_weights` override |
| `get_hook()` | (unchanged) — hooks are per content_type, not per category |
| `get_cta()` | (unchanged) — CTAs are generic |
| `compliance_check()` | (unchanged) |
| `post_to_facebook/telegram()` | (unchanged) |

---

## Architecture Decision Records

### ADR-015: Categories as In-Memory Dict, Not File-Based

- **Decision:** `CATEGORIES` defined as Python dict in `main.py`, not loaded from JSON file
- **Reason:** Categories are static. Adding a file would add complexity without benefit. If user wants to add/remove categories later, they modify the dict directly.
- **Alternatives considered:** JSON config file — rejected as over-engineering for 7 static categories.

### ADR-016: Category Rotation Permits Same-Day Repeats

- **Decision:** Unlike topics, categories can repeat within the same day
- **Reason:** 7 categories with equal probability already provides sufficient variety. Preventing same-day repeats would require tracking state across sessions (GitHub Actions runs are independent). Topics already handle the "no repeat today" rule.

---

## Risks

| Risk | Mitigation |
|---|---|
| Prompt quality varies across categories | Retry 3×; fallback to CPNS prompt if category-specific prompt fails |
| Hashtag mismatch (wrong category hashtags) | Runtime validation: compare hashtags against allowed pool for selected category |
| Legacy history entries lack category field | Default to "cpns" at read time (backward compatible) |

---

## Validation

- Category appears in history entry ✓
- Prompt changes per category ✓
- Hashtags change per category ✓
- Video header shows correct category ✓
- Legacy data backward compatible ✓
- Self-learning can adjust category weights ✓
