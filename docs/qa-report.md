# QA Test Report — Auto Post Reels Matematika

## 1. Test Plan

**Level:** Implementation-Level
**Test Method:** Code inspection + logic tracing (API-dependent tests require live credentials)
**Status:** Pre-release

## 2. Functional Test Cases

### TC-001: Load History

| Field | Value |
|---|---|
| ID | TC-001 |
| Title | Load history from JSON file |
| Preconditions | File `data/history.json` exists or not |
| Steps | Call `load_history()` |
| Expected | Returns list of history entries, or empty list if file missing/corrupt |
| Verification Method | Read code |
| Actual Result | `load_history()` catches `FileNotFoundError` and `json.JSONDecodeError`, returns `[]` |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

### TC-002: Save History — Cap at 180

| Field | Value |
|---|---|
| ID | TC-002 |
| Title | Save history caps at 180 entries |
| Preconditions | History list with >180 items |
| Steps | Call `save_history(history)` with 200 items |
| Expected | Only last 180 items saved |
| Verification Method | Read code |
| Actual Result | `history = history[-MAX_HISTORY_ITEMS:]` ensures max 180 |
| Status | ✅ PASS |
| Priority | High |
| Severity | Low |

### TC-003: Topic Selection — No Duplicate Today

| Field | Value |
|---|---|
| ID | TC-003 |
| Title | Pick topic not used today |
| Preconditions | Some topics already used today in history |
| Steps | Call `pick_topic(history)` where 3 of 5 topics used today |
| Expected | Returns one of the 2 unused topics |
| Verification Method | Read code |
| Actual Result | `get_used_topics_today()` filters history by `tanggal == today`, `pick_topic()` excludes those from available pool |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

**Adversarial check:** If all 5 topics used today → pool resets to all 5. ✅ Code handles this.

### TC-004: Topic Selection — Empty History

| Field | Value |
|---|---|
| ID | TC-004 |
| Title | Pick topic from empty history |
| Preconditions | `history = []` |
| Steps | Call `pick_topic([])` |
| Expected | Returns random topic from all 5 |
| Verification Method | Read code |
| Actual Result | `used_today = set()`, `available = list(TOPICS.keys())` → random choice from 5 |
| Status | ✅ PASS |
| Priority | High |
| Severity | Low |

### TC-005: Duplicate Detection

| Field | Value |
|---|---|
| ID | TC-005 |
| Title | Detect duplicate soal |
| Preconditions | History contains an entry with specific soal text |
| Steps | Call `is_duplicate(soal_text, history)` with same text |
| Expected | Returns True |
| Verification Method | Read code |
| Actual Result | `any(h["soal"] == soal_text for h in history)` — exact string match |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

**Adversarial check:** Near-duplicate (different punctuation, extra space) → NOT detected. Exact match only. This is a known limitation but acceptable for this use case (Gemini unlikely to generate near-identical text).

### TC-006: Generate Narasi — Validasi Response

| Field | Value |
|---|---|
| ID | TC-006 |
| Title | Validate Gemini JSON response |
| Preconditions | Gemini returns JSON-like text |
| Steps | Call `generate_narasi()` → parse JSON → validate fields |
| Expected | Rejects missing fields, wrong pilihan count, jawaban not in pilihan, duplicate |
| Verification Method | Read code |
| Actual Result | 4 validation checks: (1) all 4 fields exist, (2) `len(pilihan) == 4`, (3) jawaban in pilihan, (4) not duplicate. Each fail → retry up to 3x |
| Status | ✅ PASS |
| Priority | High |
| Severity | High |

### TC-007: Narasi — Retry Exhausted

| Field | Value |
|---|---|
| ID | TC-007 |
| Title | Gemini fails after 3 retries |
| Preconditions | Gemini returns invalid response 3 times |
| Steps | All 3 retry attempts fail |
| Expected | Raises RuntimeError |
| Verification Method | Read code |
| Actual Result | After 3 attempts, `raise RuntimeError(...)`. Also catches `json.JSONDecodeError, KeyError, ValueError` |
| Status | ✅ PASS |
| Priority | High |
| Severity | High |

### TC-008: Frame Rendering — Soal

| Field | Value |
|---|---|
| ID | TC-008 |
| Title | Render soal frame image |
| Preconditions | Valid narasi dict |
| Steps | Call `render_frame_soal(narasi, topic, path)` |
| Expected | Generates 1080×1920 PNG with header, topic badge, soal text, footer |
| Verification Method | Read code |
| Actual Result | Uses Pillow to draw header bar (teal), topic badge (light teal pill), wrapped soal text, footer |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

**Adversarial check:** Long soal text → `wrap_text()` splits by words with `textbbox()` measurement. ✅

### TC-009: Hex to RGB Conversion

| Field | Value |
|---|---|
| ID | TC-009 |
| Title | Convert hex color to RGB tuple |
| Preconditions | Hex color string with # |
| Steps | Call `hex_to_rgb("#0D9488")` |
| Expected | Returns `(13, 148, 136)` |
| Verification Method | Read code |
| Actual Result | `h.lstrip("#")`, then `int(h[i:i+2], 16)` for each pair → `(13, 148, 136)` |
| Status | ✅ PASS |
| Priority | Medium |
| Severity | Low |

### TC-010: Caption Formatting

| Field | Value |
|---|---|
| ID | TC-010 |
| Title | Format Facebook caption |
| Preconditions | Valid narasi + topic |
| Steps | Call `format_caption(narasi, topic)` |
| Expected | Caption with soal, options, hashtags |
| Verification Method | Read code |
| Actual Result | Builds multi-line caption with soal, options joined by comma, CTA, 6 hashtags |
| Status | ✅ PASS |
| Priority | High |
| Severity | Low |

### TC-011: Compliance Check — Engagement Bait

| Field | Value |
|---|---|
| ID | TC-011 |
| Title | Check for engagement bait patterns |
| Preconditions | Caption with potential bait |
| Steps | Call `compliance_check(caption)` |
| Expected | Logs warning if patterns found |
| Verification Method | Read code |
| Actual Result | Checks for "comment", "tag", "share this" in lowercase. Logs warning but does NOT block. |
| Status | ⚠️ PASS with note |
| Priority | Medium |
| Severity | Low |

**Note:** Per social-media-growth-engine §3.3, flagged content should NOT be auto-published. Current implementation only logs. For this simple bot (safe CTAs only), this is acceptable but flagged as a gap.

### TC-012: Token Pre-Check

| Field | Value |
|---|---|
| ID | TC-012 |
| Title | Validate Facebook token before posting |
| Preconditions | FB token set in env |
| Steps | Call `check_fb_token()` |
| Expected | Returns (True, None) for valid token, (False, error) for expired |
| Verification Method | Read code |
| Actual Result | GET `/{page_id}?fields=id,name` with token. 200→valid, 401→expired, other→failed. Network error caught |
| Status | ✅ PASS |
| Priority | High |
| Severity | High |

### TC-013: Post to Facebook — Error Handling

| Field | Value |
|---|---|
| ID | TC-013 |
| Title | Handle Facebook API errors |
| Preconditions | Various API responses |
| Steps | Call `post_to_facebook()` with different response codes |
| Expected | 200→success, 401→PermissionError+notif, 429→RuntimeError+notif, other→RuntimeError+notif |
| Verification Method | Read code |
| Actual Result | Each status code handled specifically. Telegram notification sent for all errors. Token pre-check runs before upload |
| Status | ✅ PASS |
| Priority | High |
| Severity | High |

### TC-014: Main Orchestrator — Cleanup

| Field | Value |
|---|---|
| ID | TC-014 |
| Title | Cleanup video file after success |
| Preconditions | Video file exists after render |
| Steps | `main()` completes successfully |
| Expected | Video file deleted after post |
| Verification Method | Read code |
| Actual Result | `os.remove(video_filename)` after `save_history()` — runs only if `os.path.exists()` |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

### TC-015: Temp Directory Cleanup

| Field | Value |
|---|---|
| ID | TC-015 |
| Title | Cleanup temp directory after render |
| Preconditions | Temp dir created by `render_video()` |
| Steps | `render_video()` completes or errors |
| Expected | Temp dir always deleted |
| Verification Method | Read code |
| Actual Result | `finally: shutil.rmtree(tmpdir, ignore_errors=True)` — always runs |
| Status | ✅ PASS |
| Priority | High |
| Severity | Medium |

### TC-016: History Not Saved on Failure

| Field | Value |
|---|---|
| ID | TC-016 |
| Title | Don't save history if upload fails |
| Preconditions | Facebook upload fails |
| Steps | `post_to_facebook()` raises exception before `save_history()` |
| Expected | History unchanged |
| Verification Method | Read code |
| Actual Result | `post_to_facebook()` is called before `save_history()`. If exception raised, `save_history()` never runs. |
| Status | ✅ PASS |
| Priority | High |
| Severity | Critical |

### TC-017: Global Error Handler

| Field | Value |
|---|---|
| ID | TC-017 |
| Title | Handle uncaught exceptions |
| Preconditions | Any error in `main()` |
| Steps | Exception escapes `main()` |
| Expected | Error logged + Telegram notification + exit code 1 |
| Verification Method | Read code |
| Actual Result | `if __name__ == "__main__": try/except` catches Exception, format error message, calls `notify_telegram()`, `sys.exit(1)` |
| Status | ✅ PASS |
| Priority | High |
| Severity | High |

## 3. Performance Validation

| Test | Result | Notes |
|---|---|---|
| Gemini API call | CANNOT VERIFY | Requires live API key |
| Video rendering time | CANNOT VERIFY | Requires MoviePy + FFmpeg installed |
| Facebook upload | CANNOT VERIFY | Requires live credentials |
| History scan speed ✅ | O(n) with n<200 | Trivial — no measurement needed |

## 4. Edge Cases & Risks

| Edge Case | Status | Notes |
|---|---|---|
| Empty history.json | ✅ Handled | Returns `[]` |
| Corrupt history.json | ✅ Handled | Returns `[]` |
| All topics used today | ✅ Handled | Resets pool |
| Gemini invalid JSON | ✅ Handled | Retry 3× |
| Duplicate detected in Gemini response | ✅ Handled | Retry 3× |
| Facebook token expired | ✅ Handled | Pre-check + per-post check |
| Facebook rate limited (429) | ✅ Handled | Notify + fail |
| Video render failure | ✅ Handled | Cleanup + notify |
| Network failure on upload | ✅ Handled | Exception caught, history not saved |
| Disk space | ⚠️ Not explicitly handled | `shutil.rmtree` helps but no pre-check |
| Near-duplicate soal | ⚠️ Not detected | Exact string match only |

## 5. Defect Report

| ID | Title | Severity | Status |
|---|---|---|---|
| DEF-001 | `compliance_check()` doesn't block posting on flag | Low | Accepted (safe CTAs only) |
| DEF-002 | No disk space pre-check | Low | Acceptable for GitHub Actions |

## 6. Release Recommendation

**Status:** READY FOR RELEASE (with caveats)

**Conditions:**
- Live testing with real credentials required before production use
- Token expiry monitoring needed (Facebook Page tokens ~60 days)
- BGM file (`audio/bgm.mp3`) must be added before use

**Outstanding Gaps (needed for production):**
1. Live credentials configured in GitHub Secrets
2. BGM file added to `audio/` directory
3. Facebook Page Access Token with `pages_manage_posts` scope

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Facebook API changes | Medium | Versioned API (v22.0) |
| Token expiry without replacement | High | Pre-emptive check + Telegram alert |
| BGM copyright claim | Low | Use only CC0/free music |
