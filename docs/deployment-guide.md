# Deployment Guide — Auto Post Reels Matematika

## 1. Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 GitHub Repository                            │
│  auto-post-reels-matematika/                                 │
│  ├─ main.py                    (bot logic)                  │
│  ├─ requirements.txt           (Python deps)                │
│  ├─ .github/workflows/         (CI/CD pipeline)             │
│  │   └─ auto-post.yml          (scheduler + executor)       │
│  ├─ fonts/*.ttf                (rendering fonts)            │
│  ├─ audio/bgm.mp3              (background music)           │
│  ├─ data/history.json          (post history)               │
│  └─ docs/                      (documentation)              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions (ubuntu-latest)                  │
│  Steps: checkout → setup-python → install ffmpeg →          │
│         pip install → python main.py → commit+push history  │
│                                                             │
│  Schedule: 06:00, 10:00, 13:00 UTC (3×/hari)               │
└─────────────────────────────────────────────────────────────┘
```

## 2. Environment Variables (GitHub Secrets)

| Variable | Source | Required | Notes |
|---|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) | ✅ | Free tier sudah cukup (3 calls/day) |
| `FB_PAGE_ID` | Facebook Page → About → Page ID | ✅ | |
| `FB_ACCESS_TOKEN` | Facebook Graph API → System User Token | ✅ | **Rekomendasi: System User Token** (tidak expire 60 hari seperti Page Token biasa) |
| `TELEGRAM_BOT_TOKEN` | Telegram @BotFather | ✅ | Untuk notifikasi error |
| `TELEGRAM_CHAT_ID` | Telegram @userinfobot | ✅ | Chat ID admin |

### Cara Setup Secrets di GitHub:
1. Repository → Settings → Secrets and variables → Actions
2. "New repository secret"
3. Tambahkan satu per satu: `GEMINI_API_KEY`, `FB_PAGE_ID`, `FB_ACCESS_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## 3. Pre-Deployment Checklist

### Required Files
- [x] `main.py` — Bot logic
- [x] `requirements.txt` — Python dependencies
- [x] `.github/workflows/auto-post.yml` — GitHub Actions workflow
- [x] `fonts/DejaVuSans-Bold.ttf` — Font file
- [x] `fonts/DejaVuSans.ttf` — Font file
- [ ] `audio/bgm.mp3` — **Harus ditambahkan!** File MP3 bebas royalti (CC0)

### BGM Source Recommendations (Free / Royalty-Free)
- [Pixabay Music](https://pixabay.com/music/) — Free for commercial use
- [Free Music Archive](https://freemusicarchive.org/) — Check license per track
- [YouTube Audio Library](https://www.youtube.com/audiolibrary) — Free when logged in

Rekomendasi: Pilih BGM instrumental, durasi minimal 30 detik, tempo medium (tidak terlalu cepat untuk konten edukasi).

## 4. Deployment Steps

### Step 1: Push to GitHub
```bash
cd /home/master/Downloads/automasi/auto-post-reels-matematika
git init
git add .
git commit -m "init: auto post reels matematika"
git remote add origin https://github.com/{username}/auto-post-reels-matematika.git
git push -u origin main
```

### Step 2: Configure Secrets
Tambahkan 5 secrets di GitHub Settings → Secrets and variables → Actions.

### Step 3: Add BGM
Tambahkan file `audio/bgm.mp3` (MP3, durasi minimal 30 detik).

### Step 4: Test with Manual Trigger
1. GitHub → Repository → Actions → "Auto Post Reels Matematika"
2. Klik "Run workflow" → "Run workflow"
3. Monitor execution log
4. Verify post appears on Facebook Page

### Step 5: Verify Cron Schedule
Setelah sukses manual, cron akan otomatis aktif:
- 06:00 UTC (13:00 WIB)
- 10:00 UTC (17:00 WIB)
- 13:00 UTC (20:00 WIB)

## 5. Monitoring

### Method: GitHub Actions
- **URL:** `https://github.com/{username}/auto-post-reels-matematika/actions`
- **What to check:**
  - Workflow run status (✅/❌)
  - Execution logs (expand each step)
  - history.json commit history

### Error Notification
- Bot akan kirim pesan ke Telegram jika error fatal
- Format: `[ERROR] YYYY-MM-DD HH:MM:SS - {message}`
- Jika tidak terima notifikasi → bot sukses

## 6. Rollback Strategy

| Skenario | Action |
|---|---|
| History.json corrupt | `git checkout HEAD~1 -- data/history.json` → push |
| Bug di main.py | Commit fix → push → otomatis dipakai sesi berikutnya |
| FB token expired | Generate token baru → update GitHub Secret → trigger manual |
| Gemini API key revoked | Generate key baru → update GitHub Secret |

### Rollback Steps (if needed):
```bash
git revert HEAD
git push origin main
```

## 7. Maintenance

### Token Refresh
- **Facebook Token:** Cek setiap bulan. System User Token lebih stabil.
- **Gemini API Key:** Tidak expire unless revoked.

### History Cleanup
- Otomatis: file di-cap 180 entries
- Manual jika perlu: edit `data/history.json` → delete entries → commit

## 8. Release Approval

| Check | Status |
|---|---|
| Build syntax valid | ✅ `python -m py_compile main.py` |
| Dependencies listed | ✅ requirements.txt |
| Secrets documented | ✅ .env.example + docs |
| Workflow configured | ✅ auto-post.yml |
| Rollback defined | ✅ Git revert |
| BGM pending | ⚠️ `audio/bgm.mp3` perlu ditambahkan |
| Deploy target | GitHub + GitHub Actions |

**Status:** ✅ READY FOR DEPLOYMENT (after BGM file added)
