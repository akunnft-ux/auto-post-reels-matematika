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
| **Narasi Generator** | `generate_narasi(topic, history, content_type)` | Panggil Gemini API dengan prompt sesuai tipe konten (quiz/fakta/tips), validasi JSON, retry logic |
| **Content Strategist** | `pick_content_type()`, `get_hook_template(content_type)` | Pilih tipe konten (quiz/fakta/tips) dan hook template untuk maksimalkan engagement |
| **Caption Builder** | `build_caption(narasi, content_type, hook_template)` | Generate caption dengan hook + body + CTA + hashtags; compliance check sebelum output |
| **Topic Manager** | `pick_topic(history)`, `get_used_topics_today(history)` | Pilih topik unik, rotasi harian |
| **Video Renderer** | `render_video(narasi, filename, content_type)` | Render 3-frame video 1080×1920 + BGM; layout menyesuaikan content_type |
| **Facebook Poster** | `post_to_facebook(video_path, caption)` | Upload ke Facebook Reels, handle token expiry, return post_id |
| **Analytics Engine** | `fetch_analytics(post_id)`, `fetch_follower_count()` | Ambil views/likes/comments/shares dari Insights API; catat follower count harian |
| **Self-Learning** | `weekly_review(analytics, growth)` | Analisa performa 7 hari, rekomendasi format konten terbaik |
| **History Manager** | `load_history()`, `save_history(history)`, `is_duplicate(soal, history)` | Baca/tulis/cari duplikat di history.json |
| **Compliance Checker** | `compliance_check(caption)` → raise on violation | Cek engagement bait pattern, BLOCK posting jika terdeteksi (bukan log) |
| **Growth Tracker** | `record_growth(follower_count)` | Simpan follower count harian ke data/growth.json |
| **Error Notifier** | `notify_telegram(message)` | Kirim notifikasi error ke Telegram |
| **Orchestrator** | `main()` | Koordinasi urutan eksekusi |

### Modul Dependencies

```
NarasiGenerator    ───→ Gemini API (external)
ContentStrategist  ───→ config/content_types.json
CaptionBuilder     ───→ NarasiGenerator (output), ContentStrategist (output)
CaptionBuilder     ───→ ComplianceChecker (validation)
TopicManager       ───→ HistoryManager (read)
VideoRenderer      ───→ NarasiGenerator (output), fonts/, audio/ (local files)
FacebookPoster     ───→ VideoRenderer (output)
FacebookPoster     ───→ ComplianceChecker (re-run at posting time)
FacebookPoster     ───→ HistoryManager (save on success)
AnalyticsEngine    ───→ Facebook Insights API (external)
AnalyticsEngine    ───→ FacebookPoster (post_id input)
GrowthTracker      ───→ Facebook Graph API (external)
SelfLearning       ───→ AnalyticsEngine (data), GrowthTracker (data)
ComplianceChecker  ───→ references/platform-compliance.md rules
ErrorNotifier      ───→ Telegram API (external)
Orchestrator       ───→ semua modul di atas
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

### Feature: Content Hook & CTA

| Aspek | Detail |
|---|---|
| Purpose | Setiap caption punya hook (curiosity gap) + CTA (follow/comment) untuk maksimalkan engagement |
| Inputs | Narasi JSON, content_type (quiz/fakta/tips), hook template |
| Outputs | Caption string dengan format: hook\n\nbody\n\nCTA\n\nhashtags |
| Dependencies | ComplianceChecker (harus pass sebelum output) |
| Error Handling | Jika compliance fail → ganti hook/CTA, jangan post caption terlarang |

### Feature: Analytics & Growth Tracking

| Aspek | Detail |
|---|---|
| Purpose | Track performa setiap post dan follower growth harian |
| Inputs | Facebook post_id (dari posting), Facebook Page ID |
| Outputs | Analytics record (views, likes, comments, shares, source:"api"), Growth record (follower_count, daily_growth) |
| Dependencies | Facebook Insights API, Facebook Graph API |
| Error Handling | Jika API gagal → skip + log, tidak block posting |

### Feature: Self-Learning Loop

| Aspek | Detail |
|---|---|
| Purpose | Analisa performa 7 hari, rekomendasi format terbaik, iterasi 1 variable at a time |
| Inputs | Analytics records (7 hari, source:"api" only), Growth records |
| Outputs | Recommendations: format konten yang dipertahankan/dihentikan/diubah |
| Dependencies | AnalyticsEngine, GrowthTracker |
| Error Handling | Jika data <7 hari → skip loop |

### Feature: Token Management (dari social-media-growth-engine §4.1)

| Aspek | Detail |
|---|---|
| Purpose | Cek expiry Facebook token sebelum posting |
| Implementation | Panggil Graph API dengan token; jika 401 → notif admin + skip |
| Error Matrix | Token expired → BLOCKED_TOKEN_EXPIRED status, halt, alert admin |
| | Rate limited (429) → exponential backoff, max 3 retries |
| | Content rejected → log reason, human review required |

## 6. Data Flow

### Main Flow (Posting Cycle)

```
main()
  │
  ├─ 1. Load history.json ──────────────────────────────────────────┐
  │                                                                  │
  ├─ 2. pick_content_type() → content_type (quiz/fakta/tips)        │
  │     Rotasi: 40% quiz challenge, 30% fakta, 30% tips cepat       │
  │                                                                  │
  ├─ 3. pick_topic() → topic_id ← get_used_topics_today(history)    │
  │                                                                  │
  ├─ 4. get_hook_template(content_type) → hook_template              │
  │     Quiz: "90% orang salah jawab. Kamu?"                        │
  │     Fakta: "Ternyata selama ini kamu salah! Cek videonya..."    │
  │     Tips: "Hitung dalam 3 detik! Rahasia ini jarang diketahui"  │
  │                                                                  │
  ├─ 5. generate_narasi(topic, history, content_type)                │
  │     ├─ Call Gemini API with prompt sesuai content_type           │
  │     ├─ Parse JSON response                                       │
  │     ├─ Validate fields                                          │
  │     ├─ Check duplicate against full history                      │
  │     └─ Return narasi dict                                        │
  │                                                                  │
  ├─ 6. build_caption(narasi, content_type, hook_template)           │
  │     ├─ Hook (curiosity gap, 1-2 kalimat)                        │
  │     ├─ Body (soal/fakta/tips, 2-3 kalimat)                      │
  │     ├─ CTA ("Follow for daily soal CPNS + tips")                │
  │     ├─ Hashtags (5-8 relevant tags)                             │
  │     └─ Compliance check → BLOCK if bait detected                │
  │                                                                  │
  ├─ 7. render_video(narasi, filename, content_type)                 │
  │     ├─ Layout menyesuaikan content_type                          │
  │     ├─ Duraasi: 15-30 detik                                      │
  │     └─ Composite with BGM → MP4 (H.264, 1080×1920)              │
  │                                                                  │
  ├─ 8. post_to_facebook(video_path, caption)                        │
  │     ├─ Check token expiry (pre-emptive)                          │
  │     ├─ Compliance check (re-run at posting time, §4.3)           │
  │     ├─ POST to /{page_id}/videos (multipart)                    │
  │     └─ Return post_id on success                                 │
  │                                                                  │
  ├─ 9. save_history(narasi, topic, tanggal, content_type)           │
  │     ├─ Append new entry with content_type field                  │
  │     ├─ Cap at 180 entries                                        │
  │     └─ Write to history.json                                     │
  │                                                                  │
  └─ 10. Cleanup temp files
```

### Analytics Cycle (di sesi terpisah / setiap H+1)

```
analytics_batch()
  │
  ├─ 1. Load history → get all post_ids tanpa analytics              │
  │                                                                  │
  ├─ 2. For each post_id:                                            │
  │     ├─ Call Facebook Insights API (views, likes, comments, shares)
  │     ├─ Record ke data/analytics.json dengan source:"api"         │
  │     └─ Jika post <24 jam → skip, coba lagi besok                │
  │                                                                  │
  ├─ 3. fetch_follower_count()                                       │
  │     ├─ Call Graph API /{page_id}?fields=followers_count          │
  │     └─ Record ke data/growth.json                                │
  │                                                                  │
  └─ 4. Jika hari ke-7 → panggil self_learning_review()              │

### Self-Learning Cycle (setiap hari ke-7)

```
self_learning_review()
  │
  ├─ 1. Load analytics (7 hari terakhir, source:"api" only)          │
  │                                                                  │
  ├─ 2. Klasifikasi post per content_type (per §5.1 thresholds):    │
  │     IF follower_count < 100: VIRAL = views > 1000               │
  │     ELSE: VIRAL = views > 10 * follower_count                   │
  │     GOOD = engagement_rate > baseline AND NOT VIRAL              │
  │     BAD = views < 50                                            │
  │                                                                  │
  ├─ 3. Report: top 3 best, top 3 worst                              │
  │                                                                  │
  ├─ 4. Recommendation (per §6):                                     │
  │     IF VIRAL → clone format, 5 variasi                           │
  │     IF BAD → change only ONE variable (hook/format/CTA/topic)    │
  │                                                                  │
  └─ 5. Kirim ringkasan ke Telegram admin                            │
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
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent` |
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

### Facebook Insights API

| Aspek | Detail |
|---|---|
| Endpoint | `GET https://graph.facebook.com/v22.0/{post_id}/insights?metric=post_impressions,post_engaged_users,post_reactions_like_total,post_comments,post_shares` |
| Auth | `FB_ACCESS_TOKEN` (sama dengan posting) |
| Request | GET dengan access_token + metric params |
| Response | JSON array of metric objects with values |
| Use | Mengambil views, likes, comments, shares untuk analytics (FR-012) |
| Error Handling | Jika 401 → token expired alert; jika data unavailable → skip, coba H+1 |
| Rate Limit | 200 calls/6h/user — well within untuk 5 post/hari |

### Follower Count API

| Aspek | Detail |
|---|---|
| Endpoint | `GET https://graph.facebook.com/v22.0/{page_id}?fields=followers_count` |
| Auth | `FB_ACCESS_TOKEN` |
| Request | GET dengan access_token |
| Response | `{ "followers_count": 1234, "id": "page_id" }` |
| Use | Tracking follower growth harian (FR-013) |
| Error Handling | Jika 401 → alert; jika error → pakai nilai terakhir |

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

### ADR-006: Content Type Rotation (Quiz/Fakta/Tips)

| Aspek | Detail |
|---|---|
| Decision | Rotasi 3 tipe konten: quiz challenge (40%), fakta matematika (30%), tips cepat (30%) |
| Reason | Soal-only terlalu monoton; variasi meningkatkan shareability dan follow conversion |
| Alternatives | Soal-only, fakta-only, random |
| Tradeoff | Lebih kompleks dalam prompt Gemini + layout video |
| Chosen | Rotasi 3 tipe (terbukti meningkatkan engagement di platform edukasi) |

### ADR-007: Compliance Check BLOCK (Bukan Log)

| Aspek | Detail |
|---|---|
| Decision | Compliance check HARUS raise exception dan block posting jika engagement bait terdeteksi |
| Reason | Shadow ban atau account restriction akan menghancurkan growth; lebih baik skip 1 post daripada kehilangan akun |
| Alternatives | Log warning only (current), auto-fix caption |
| Tradeoff | Risiko false positive → skip sesi |
| Chosen | Block on violation (per social-media-growth-engine §3.3) |

### ADR-008: Facebook Insights API untuk Analytics (Source: API)

| Aspek | Detail |
|---|---|
| Decision | Analytics diambil dari Facebook Insights API resmi, bukan estimasi/scraping |
| Reason | Self-learning hanya boleh bertindak pada data source:"api" (social-media-growth-engine §5) |
| Alternatives | Scrape halaman, estimasi manual, skip analytics |
| Tradeoff | Tergantung ketersediaan Insights API (butuh page scope) |
| Chosen | Insights API (source:"api" — satu-satunya yang valid untuk self-learning) |

### ADR-009: Satu Variable Per Iterasi Self-Learning

| Aspek | Detail |
|---|---|
| Decision | Self-learning loop hanya mengubah SATU variable per iterasi (hook, format, CTA, atau topik — tidak bersamaan) |
| Reason | Tidak bisa atribusi improvement jika multiple variables berubah sekaligus (social-media-growth-engine §6) |
| Alternatives | Multiple variables, random change |
| Tradeoff | Lebih lambat konvergensi, tapi hasil terukur |
| Chosen | One variable at a time |

### ADR-010: Gradual Posting Frequency Ramp

| Aspek | Detail |
|---|---|
| Decision | Mulai 3×/hari minggu 1, naik ke 5×/hari minggu 2+ |
| Reason | Mencegah Facebook flag sebagai spam akibat volume mendadak; beri waktu algoritma kenali akun |
| Alternatives | Langsung 5×/hari dari awal |
| Tradeoff | Lebih lambat mencapai volume optimal |
| Chosen | Gradual ramp (3 → 5) |

## 16. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Facebook API changes | Low | High | Use versioned API (v22.0), monitor changelog |
| Facebook token expiry | Medium | High | Pre-emptive check, alert admin, document refresh procedure |
| Gemini API rate limit | Low | Medium | Only 3-5 calls/day, well within free tier |
| Video rendering timeout | Medium | Medium | Keep frame count low, test on ubuntu-latest |
| GitHub Actions runner instability | Low | Medium | Retry on workflow level |
| BGM copyright claim | Low | Medium | Use only CC0/free music, no copyrighted tracks |
| Target 5.000 followers tidak tercapai | High | High | Content mix optimization; jika gagal evaluasi platform mix bulan ke-2 |
| Facebook flag spam (volume tinggi) | Medium | High | Gradual ramp 3→5 post/hari, compliance check ketat |
| Engagement bait → shadow ban | Medium | Critical | Compliance block, re-run check saat posting time |
| Insights API rate limit | Low | Medium | 1 call/post/hari, well within limit |

## 17. Recommendations

1. **Gunakan format video H.264** — compatible dengan Facebook Reels
2. **BGM dari Pixabay/Free Music Archive** — bebas royalti
3. **Token Facebook: System User Token** — long-lived (tidak expire 60 hari)
4. **Content rotation: 40% quiz, 30% fakta, 30% tips** — maksimalkan shareability
5. **Hook + CTA di setiap caption** — curiosity gap untuk view, ajakan follow untuk konversi
6. **Compliance check BLOCK (bukan log)** — lindungi akun dari shadow ban
7. **Gradual posting ramp: 3→5 post/hari** — hindari spam flag
8. **Analytics H+1 via Insights API** — data source:"api" untuk self-learning
9. **Testing: jalankan workflow_dispatch** sebelum andalkan cron
10. **Monitoring: pantau GitHub Actions** untuk failed runs
