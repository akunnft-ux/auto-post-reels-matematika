# Architecture Document — Auto Post Reels Matematika

## 1. Architecture Overview

Bot Python monolitik (single script) untuk generate narasi soal matematika via Gemini AI, render video Reels 1080×1920 dengan MoviePy + Pillow, dan post ke Facebook Reels via Graph API. Dijadwalkan via GitHub Actions cron 3×/hari. Tidak ada database server — history disimpan di JSON file.

```
┌──────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Ubuntu)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Cron     │  │ Cron     │  │ Cron     │                       │
│  │ 06:00 UTC│  │ 10:00 UTC│  │ 13:00 UTC│                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
│       └─────────────┼──────────────┘                             │
│                     ▼                                             │
│         ┌─────────────────────────┐                              │
│         │       main.py           │                              │
│         │  (single script bot)    │                              │
│         └──┬──────┬───────┬──────┘                              │
└────────────┼──────┼───────┼──────────────────────────────────────┘
             │      │       │
    ┌────────┘      │       └──────────┐
    ▼               ▼                  ▼
┌────────┐   ┌──────────┐   ┌────────────────┐
│ Gemini │   │  MoviePy  │   │  Facebook      │
│ API    │   │ + Pillow  │   │  Graph API     │
│(narasi)│   │ (video)   │   │  (post Reels)  │
└────────┘   └──────────┘   └────────────────┘
                   │
             ┌─────┴─────┐
             │  history   │
             │  .json     │
             │  + audio/  │
             │  + fonts/  │
             └───────────┘
                    │ (committed back to repo)
                    ▼
             GitHub Repository
```

## 2. Context Diagram

```
┌──────────────┐     ┌─────────────────────────────────────┐     ┌──────────────┐
│   Admin      │     │         GitHub Actions               │     │   Audiens    │
│ (via Telegram)│────▶│  ┌──────────────┐  ┌─────────────┐ │────▶│ (Facebook)   │
│              │     │  │ Cron Trigger  │  │  main.py    │ │     │              │
│              │◀────│  └──────────────┘  └──────┬──────┘ │     │              │
└──────────────┘     └──────────────────────────┼─────────┘     └──────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
           ┌──────────────┐            ┌──────────────────┐         ┌──────────────────┐
           │  Gemini API   │            │  MoviePy/Pillow  │         │ Facebook Graph   │
           │  (Google)     │            │  (local render)  │         │ API (Meta)       │
           └──────────────┘            └──────────────────┘         └──────────────────┘
```

## 3. Module Architecture

Modular monolith dalam 1 file Python dengan fungsi terpisah per modul:

| Modul | Fungsi | Tanggung Jawab |
|---|---|---|
| **Narasi Generator** | `generate_narasi(topic, history)` | Panggil Gemini API, validasi JSON, retry logic |
| **Topic Manager** | `pick_topic(history)`, `get_used_topics_today(history)` | Pilih topik unik, rotasi harian |
| **Video Renderer** | `render_video(narasi, filename)` | Render 3-frame video 1080×1920 + BGM |
| **Facebook Poster** | `post_to_facebook(video_path, caption)` | Upload ke Facebook Reels, handle token expiry |
| **History Manager** | `load_history()`, `save_history(history)`, `is_duplicate(soal, history)` | Baca/tulis/cari duplikat di history.json |
| **Error Notifier** | `notify_telegram(message)` | Kirim notifikasi error ke Telegram |
| **Orchestrator** | `main()` | Koordinasi urutan eksekusi |

### Modul Dependencies

```
NarasiGenerator ───→ Gemini API (external)
TopicManager     ───→ HistoryManager (read)
VideoRenderer    ───→ NarasiGenerator (output)
VideoRenderer    ───→ fonts/, audio/ (local files)
FacebookPoster   ───→ VideoRenderer (output)
FacebookPoster   ───→ HistoryManager (save on success)
ErrorNotifier    ───→ Telegram API (external)
Orchestrator     ───→ semua modul di atas
```

## 4. Layer Architecture

| Layer | Components |
|---|---|
| **Presentation** | N/A (bot-only, no UI) |
| **Application** | `main()` — orchestrator |
| **Domain** | NarasiGenerator, TopicManager, VideoRenderer, FacebookPoster, HistoryManager |
| **Infrastructure** | Gemini client, Facebook Graph client, Telegram client, File I/O, FFmpeg |
| **Data** | history.json (file system) |

## 5. Feature Architecture

### Feature: Generate & Post Reels

| Aspek | Detail |
|---|---|
| Purpose | Satu siklus: generate → render → post → record |
| Inputs | Environment variables, history.json, fonts, BGM |
| Outputs | Video di Facebook Reels, entry baru di history.json |
| Dependencies | Gemini API, Facebook Graph API, FFmpeg (system) |
| Error Handling | Retry Gemini 3×, notif Telegram jika fatal, cleanup temp files |

### Feature: Anti-Duplikasi

| Aspek | Detail |
|---|---|
| Purpose | Cegah soal sama dalam 60 hari |
| Inputs | history.json, teks soal baru |
| Outputs | Boolean (duplicate or not) |
| Dependencies | HistoryManager |

### Feature: Token Management (dari social-media-growth-engine §4.1)

| Aspek | Detail |
|---|---|
| Purpose | Cek expiry Facebook token sebelum posting |
| Implementation | Panggil Graph API dengan token; jika 401 → notif admin + skip |
| Error Matrix | Token expired → BLOCKED_TOKEN_EXPIRED status, halt, alert admin |
| | Rate limited (429) → exponential backoff, max 3 retries |
| | Content rejected → log reason, human review required |

## 6. Data Flow

### Main Flow

```
main()
  │
  ├─ 1. Load history.json ──────────────────────────────────────────┐
  │                                                                  │
  ├─ 2. pick_topic() → topic_id ← get_used_topics_today(history)    │
  │                                                                  │
  ├─ 3. generate_narasi(topic, history)                              │
  │     ├─ Call Gemini API with prompt + last 20 history             │
  │     ├─ Parse JSON response                                       │
  │     ├─ Validate fields: soal, pilihan[4], jawaban, penjelasan    │
  │     ├─ Check duplicate against full history                      │
  │     └─ Return narasi dict                                        │
  │                                                                  │
  ├─ 4. render_video(narasi, filename)                               │
  │     ├─ Frame 1 (5-8s): Header "SOAL MATEMATIKA" + teks soal     │
  │     ├─ Frame 2 (5-8s): 4 pilihan jawaban dengan aksen           │
  │     ├─ Frame 3 (5-10s): Jawaban benar + pembahasan              │
  │     └─ Composite with BGM → MP4 (H.264, 1080×1920, 15-30s)     │
  │                                                                  │
  ├─ 5. post_to_facebook(video_path, caption)                        │
  │     ├─ Check token expiry (pre-emptive)                          │
  │     ├─ POST to /{page_id}/video_reels (multipart)               │
  │     └─ Return post_id on success                                 │
  │                                                                  │
  ├─ 6. save_history(narasi, topic, tanggal)                         │
  │     ├─ Append new entry                                          │
  │     ├─ Cap at 180 entries                                        │
  │     └─ Write to history.json                                     │
  │                                                                  │
  └─ 7. Cleanup temp files
```

### Failure Flow

```
Step 3 fails (Gemini 3× retry exhausted)
  → notify_telegram("Gemini API failed after 3 retries")
  → exit(1)
  → history unchanged

Step 4 fails (render error)
  → cleanup temp files
  → notify_telegram("Video render failed: {error}")
  → exit(1)

Step 5 fails (Facebook API error)
  → cleanup temp files
  → If token expired: notify_telegram("FB token expired — re-auth needed")
  → If rate limited: retry with backoff, else notify
  → exit(1)
  → JANGAN simpan history
```

## 7. Integration Design

### Gemini API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` |
| Auth | `GEMINI_API_KEY` in URL query param |
| Request | JSON with prompt + responseMimeType: application/json |
| Retry | 3 attempts, different topic on retry |
| Timeout | 30 seconds |
| Error Handling | Non-JSON response → retry; API error → retry; 429 → backoff |

### Facebook Graph API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://graph.facebook.com/v22.0/{FB_PAGE_ID}/video_reels` |
| Auth | `FB_ACCESS_TOKEN` (Page Access Token) |
| Request | Multipart: video file + description + access_token |
| Pre-check | RUN token validation before posting (social-media-growth-engine §4.1) |
| Error Handling | 401 → BLOCKED_TOKEN_EXPIRED, halt, alert |
| | 429 → exponential backoff 1×, then defer |
| | 403 (content policy) → log, require human review |
| Timeout | 60 seconds |

### Telegram Bot API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://api.telegram.org/bot{TOKEN}/sendMessage` |
| Auth | Bot Token in URL path |
| Request | JSON: chat_id, text |
| Error Handling | Fire-and-forget (log warning on failure, jangan blocking) |
| Timeout | 10 seconds |

## 8. Authorization Design

| Resource | Authentication | Authorization |
|---|---|---|
| Gemini API | API Key (env var) | N/A (single key) |
| Facebook Page | Page Access Token (env var) | Scope: pages_manage_posts |
| Telegram Chat | Bot Token + Chat ID (env vars) | N/A |
| history.json | File system (repo) | Git-tracked, no auth |

## 9. Audit Design

| Action | Data Captured | Storage |
|---|---|---|
| Post sukses | {soal, jawaban, topik, tanggal} | history.json |
| Error fatal | Timestamp + error message + step | GitHub Actions log + Telegram |
| Token expiry | Timestamp + platform | GitHub Actions log |

## 10. Observability Design

| Aspect | Implementation |
|---|---|
| Application Logs | print() statements dengan timestamp, visible di GitHub Actions |
| Error Logs | Telegram notification + stdout |
| Execution Status | GitHub Actions workflow run status (success/failure) |
| History Health | history.json — mudah diinspeksi |

## 11. Security Design

| Concern | Implementation |
|---|---|
| Secret Management | GitHub Actions encrypted secrets (5 env vars) |
| .env file | .gitignore, .env.example tanpa nilai real |
| Facebook Token | Long-lived Page Access Token, pre-emptive expiry check |
| No PII | Hanya teks soal, jawaban, topik — tidak ada data user |
| File Permissions | GitHub token scope: contents:write minimal |

## 12. Performance Strategy

| Operation | Target | Strategy |
|---|---|---|
| Gemini API call | <10s | 30s timeout, retry 3× |
| Video render | <60s | Resolusi tetap 1080×1920, frame count minimal |
| Facebook upload | <30s | File <10MB, koneksi stabil |
| Total execution | <5 menit | Sequential, no parallelism needed |

## 13. Scalability Strategy

| Aspect | Approach |
|---|---|
| Current scale | 3 posts/day |
| Growth (12mo) | Same (stable requirement) |
| History cap | 180 entries (~60 days), auto-purge |
| Scaling approach | Vertical (not needed — current scale trivial) |

## 14. Deployment Architecture

```
┌─────────────────────────────────────────────┐
│           GitHub Repository                  │
│  auto-post-reels-matematika/                 │
│  ├─ main.py                                  │
│  ├─ requirements.txt                         │
│  ├─ .env.example                             │
│  ├─ data/history.json                        │
│  ├─ fonts/*.ttf                              │
│  ├─ audio/*.mp3                              │
│  ├─ docs/*.md                                │
│  └─ .github/workflows/auto-post.yml          │
└─────────────────┬───────────────────────────┘
                  │ push
                  ▼
┌─────────────────────────────────────────────┐
│         GitHub Actions (ubuntu-latest)        │
│  ┌─ Checkout repo                            │
│  ├─ Setup Python 3.12                        │
│  ├─ pip install -r requirements.txt          │
│  ├─ sudo apt-get install ffmpeg              │
│  ├─ python main.py                           │
│  └─ git commit + push history.json           │
└─────────────────────────────────────────────┘
```

### Environment Variables (GitHub Secrets)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `FB_PAGE_ID` | Facebook Page ID |
| `FB_ACCESS_TOKEN` | Facebook Page Access Token (long-lived) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for error notif |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for admin notif |

## 15. Architecture Decision Records

### ADR-001: Single Python Script

| Aspek | Detail |
|---|---|
| Decision | Maintain bot as single `main.py` file |
| Reason | <500 lines, <10 functions, no benefit from modules |
| Alternatives | Split into `narasi.py`, `video.py`, `poster.py` |
| Tradeoff | Slightly harder to test in isolation, much simpler to deploy |
| Chosen | Single file (same pattern as existing project) |

### ADR-002: JSON File Instead of Database

| Aspek | Detail |
|---|---|
| Decision | `data/history.json` as persistent store |
| Reason | Max 180 records, single writer (no concurrency), git-tracked |
| Alternatives | SQLite, Supabase, PostgreSQL |
| Tradeoff | No query capability, linear scan for dedup (OK for <200 items) |
| Chosen | JSON file |

### ADR-003: GitHub Actions as Scheduler

| Aspek | Detail |
|---|---|
| Decision | GitHub Actions cron triggers |
| Reason | Free, built-in secrets, auto commit/push history |
| Alternatives | Cron di VPS, AWS Lambda, Cloud Scheduler |
| Tradeoff | Terbatas 3 triggers per workflow, harus push history via action |
| Chosen | GitHub Actions (proven in existing project) |

### ADR-004: MoviePy + Pillow for Video

| Aspek | Detail |
|---|---|
| Decision | MoviePy for video compositing, Pillow for frame rendering |
| Reason | Free, Python-native, proven, sufficient for slideshow-style video |
| Alternatives | FFmpeg directly (complex), Adobe Premiere API (paid), Manim (heavy) |
| Tradeoff | No 3D/advanced effects; cukup untuk text+image slideshow |
| Chosen | MoviePy + Pillow |

### ADR-005: Pre-emptive Token Expiry Check

| Aspek | Detail |
|---|---|
| Decision | Validate Facebook token before posting (per social-media-growth-engine §4.1) |
| Reason | Mencegah skipped posts tanpa notifikasi |
| Alternatives | Only catch error on post failure |
| Tradeoff | Extra API call before upload |
| Chosen | Pre-emptive check |

## 16. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Facebook API changes | Low | High | Use versioned API (v22.0), monitor changelog |
| Facebook token expiry | Medium | High | Pre-emptive check, alert admin, document refresh procedure |
| Gemini API rate limit | Low | Medium | Only 3 calls/day, well within free tier |
| Video rendering timeout | Medium | Medium | Keep frame count low, test on ubuntu-latest |
| GitHub Actions runner instability | Low | Medium | Retry on workflow level |
| BGM copyright claim | Low | Medium | Use only CC0/free music, no copyrighted tracks |

## 17. Recommendations

1. **Gunakan format video H.264** — compatible dengan Facebook Reels
2. **BGM dari Pixabay/Free Music Archive** — bebas royalti
3. **Token Facebook: System User Token** — long-lived (tidak expire 60 hari)
4. **Testing: jalankan workflow_dispatch** sebelum andalkan cron
5. **Monitoring: pantau GitHub Actions** untuk failed runs
