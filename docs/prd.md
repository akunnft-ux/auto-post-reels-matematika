# Product Requirements Document — Auto Post Reels Matematika

## Document Control

### Document Version History
| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.1 | 2026-06-21 | Tech Lead | Initial draft |

### Approval / Sign-off
| Role | Name | Status | Date |
|---|---|---|---|
| Business Owner | TBD | Pending | |
| Technical Lead | TBD | Pending | |
| Security Reviewer | TBD | Pending | |

---

## 1. Executive Summary

**Project Name:** Auto Post Reels Matematika

**Project Overview:** Bot otomatis yang menghasilkan dan memposting video Reels edukasi matematika ke Facebook Page. Setiap video berisi soal matematika bergaya CPNS/TKA/SNBT dengan pilihan ganda dan pembahasan, di-render sebagai video pendek 15-30 detik dengan background music. Bot berjalan 3×/hari menggunakan GitHub Actions scheduler.

**Business Problem:** Membutuhkan konten Reels edukasi matematika yang konsisten setiap hari untuk pertumbuhan akun Facebook. Produksi video manual memakan waktu dan tidak scalable.

**Target Users:** Pengikut Facebook Page yang mencari konten edukasi matematika untuk persiapan CPNS/TKA/SNBT.

**Expected Outcomes:** 3 video Reels edukasi terposting otomatis setiap hari, growth engagement akun Facebook, audiens terbantu dengan soal latihan rutin.

**Success Definition:** Bot berjalan 3×/hari tanpa intervensi manual, video sukses terposting ke Facebook Reels, error rate <5% per bulan.

---

## 2. Business Objectives

| ID | Objective | Type | Success Metric |
|---|---|---|---|
| BO-001 | Mengotomatisasi produksi konten Reels edukasi matematika | Primary | 90 video/bulan tanpa campur tangan manual |
| BO-002 | Menjaga konsistensi posting 3×/hari | Operational | 100% jadwal terpenuhi setiap hari |
| BO-003 | Menghindari duplikasi konten | Operational | Tidak ada soal yang sama dalam 60 hari |
| BO-004 | Meminimalkan biaya operasional | Strategic | Semua komponen gratis/open source |
| BO-005 | Notifikasi error real-time ke admin | Secondary | Admin tahu dalam <5 menit jika bot gagal |

---

## 3. Project Scope

### In Scope
- Generate narasi soal matematika via Gemini AI (5 topik)
- Render video 1080×1920 portrait 15-30 detik
- Background music pada video
- Posting ke Facebook Reels via Graph API
- Scheduling 3×/hari via GitHub Actions cron
- History anti-duplikat berbasis JSON
- Rotasi topik harian
- Notifikasi error via Telegram
- Retry logic untuk Gemini API (3×)

### Out of Scope
- Dashboard admin / UI
- Multi-platform (TikTok, Instagram, YouTube Shorts)
- Analytics / statistik engagement
- User-generated content
- Komentar/feedback loop
- A/B testing konten

### Future Scope
- Cross-platform posting
- Dashboard monitoring
- Analytics engagement
- Multiple BGM randomisasi
- Efek transisi/animasi lebih kompleks

---

## 4. Stakeholders

| Stakeholder | Responsibilities | Expectations | Success Criteria |
|---|---|---|---|
| Admin (Pemilik Akun) | Setup kredensial, monitor error, maintain bot | Bot berjalan tanpa intervensi | Tidak perlu touch bot >1 minggu |
| Audiens (Pengikut FB) | Menonton, belajar, berinteraksi | Konten berkualitas, terjadwal | Engagement konsisten |
| Sistem (GitHub Actions) | Eksekusi script sesuai cron | 100% jadwal terpenuhi | No failed runs karena infrastruktur |

---

## 5. User Roles

| Role | Responsibilities | Permissions | Restrictions | Approval Authority | Reporting Access | Data Access Scope |
|---|---|---|---|---|---|---|
| Admin | Setup env vars, monitor Telegram, maintain | Manage secrets, trigger manual workflow | Cannot modify code via UI | N/A | GitHub Actions logs, Telegram | Full access to history.json |
| Bot (System) | Generate, render, post, record history | Read Gemini, write to FB, read/write history | Cannot modify secrets | N/A | N/A | history.json only |

---

## 6. Assumption Log

| ID | Description | Reason | Impact | Status | Linked Risk |
|---|---|---|---|---|---|
| ASM-001 | Facebook Graph API `/videos` endpoint mendukung upload Reels | Dokumentasi Meta | Critical jika salah | Inferred | RISK-001 |
| ASM-002 | MoviePy bisa render video 1080×1920 dengan teks+BGM di GitHub Actions runner | MoviePy cross-platform | High | Inferred | RISK-002 |
| ASM-003 | Gemini 2.5 Flash bisa output JSON narasi sesuai format | Terbukti di project sebelumnya | High | Confirmed | |
| ASM-004 | GitHub Actions Ubuntu runner cukup kuat render video <5 menit | Runner spec: 2-core CPU, 7GB RAM | Medium | Inferred | RISK-003 |
| ASM-005 | BGM bundle MP3 bebas royalti aman untuk konten edukasi | Banyak sumber music free | Medium | Confirmed | |
| ASM-006 | H.264 codec compatible dengan Facebook Reels | Standar industri | High | Confirmed | |

---

## 7. User Stories

| ID | As a | I want | So that | Realized By |
|---|---|---|---|---|
| US-001 | Admin | Bot otomatis generate soal+video+post | Saya tidak perlu membuat konten manual | FR-001, FR-002, FR-003 |
| US-002 | Admin | Bot tidak post soal yang sama | Konten tetap fresh untuk audiens | FR-005 |
| US-003 | Admin | Notifikasi jika bot gagal | Saya bisa segera troubleshoot | FR-006 |
| US-004 | Admin | Topik berganti setiap sesi | Variasi konten setiap hari | FR-007, FR-008 |
| US-005 | Audiens | Video pendek dengan soal dan pembahasan | Belajar matematika dengan cepat | FR-009, FR-010 |

---

## 8. Functional Requirements

### FR-001: Generate Narasi Soal (Core)

| Field | Value |
|---|---|
| Description | Bot memanggil Gemini API untuk menghasilkan narasi soal matematika dalam format JSON |
| Business Purpose | Konten dibuat oleh AI, bukan manual |
| Traces to | BO-001 |
| Inputs | Topic ID, last 20 history items (for context anti-duplicate) |
| Outputs | JSON: {soal, pilihan: [4], jawaban, penjelasan} |
| Validation Rules | Semua field wajib ada; jawaban harus salah satu dari pilihan; soal tidak duplicate |
| Permissions | Gemini API key dari env var |
| Error Handling | Retry 3× dengan topic berbeda; jika semua gagal → Telegram notif + exit |
| Acceptance Criteria | AC-001 |
| Dependencies | GEMINI_API_KEY environment variable |

Edge cases:
- EC-001: Gemini return JSON tidak valid → retry
- EC-002: Gemini return soal duplicate → retry
- EC-003: Gemini API timeout → retry dengan exponential backoff
- EC-004: Semua topik sudah terpakai hari ini → reset pool

### FR-002: Render Video (Core)

| Field | Value |
|---|---|
| Description | Render video 1080×1920 dari narasi soal menggunakan MoviePy + Pillow |
| Business Purpose | Mengubah teks jadi visual video yang siap posting |
| Traces to | BO-001, BO-004 |
| Inputs | Narasi JSON (FR-001 output), font files, BGM file |
| Outputs | File video MP4 (H.264, 1080×1920, 15-30 detik) |
| Validation Rules | File video harus ada dan tidak corrupt; durasi antara 15-30 detik |
| Permissions | Write access ke folder temp/output |
| Error Handling | Jika render gagal → Telegram notif; cleanup temp files |
| Acceptance Criteria | AC-002 |
| Dependencies | fonts/, audio/, MoviePy, Pillow, FFmpeg (system) |

Edge cases:
- EC-005: Teks terlalu panjang untuk satu frame → auto word-wrap + multiple frame
- EC-006: Font tidak ditemukan → fallback ke default system font
- EC-007: BGM file corrupt → skip BGM, render tanpa audio
- EC-008: Disk space habis saat render → cleanup + error notif

### FR-003: Post ke Facebook Reels (Core)

| Field | Value |
|---|---|
| Description | Upload video ke Facebook Page sebagai Reels via Graph API |
| Business Purpose | Mempublikasikan konten ke audiens |
| Traces to | BO-001 |
| Inputs | Video MP4 file, caption text |
| Outputs | Facebook API response (post ID) |
| Validation Rules | File size < 100MB; durasi 15-30 detik; format H.264 |
| Permissions | FB_PAGE_ID, FB_ACCESS_TOKEN dengan scope pages_manage_posts |
| Error Handling | Jika upload gagal → Telegram notif; jangan simpan history jika gagal |
| Acceptance Criteria | AC-003 |
| Dependencies | FB_PAGE_ID, FB_ACCESS_TOKEN |

Edge cases:
- EC-009: Token expired (401) → Telegram notif, jangan simpan history
- EC-010: Video format tidak didukung → log error detail
- EC-011: Rate limit Facebook API → exponential backoff
- EC-012: Network failure saat upload → retry 1×, lalu fail

### FR-004: Scheduling 3×/Hari (Core)

| Field | Value |
|---|---|
| Description | GitHub Actions cron triggers bot di 06:00, 10:00, 13:00 UTC |
| Business Purpose | Posting konsisten setiap hari |
| Traces to | BO-002 |
| Inputs | None (trigger-based) |
| Outputs | Bot execution |
| Validation Rules | Setiap trigger harus menjalankan 1 siklus penuh |
| Permissions | GitHub Actions workflow permissions: contents: write |
| Error Handling | Jika satu sesi gagal, sesi berikutnya tetap jalan |
| Acceptance Criteria | AC-004 |
| Dependencies | GitHub Actions, repository push access |

### FR-005: Anti-duplikasi Soal (Core)

| Field | Value |
|---|---|
| Description | Mencegah soal yang sama dipost dalam 60 hari menggunakan history.json |
| Business Purpose | Konten tetap fresh, tidak membosankan |
| Traces to | BO-003 |
| Inputs | history.json, soal baru |
| Outputs | Boolean: duplicate or not |
| Validation Rules | Exact string match terhadap seluruh history |
| Permissions | Read/write ke data/history.json |
| Error Handling | Jika file corrupt → backup + reset |
| Acceptance Criteria | AC-005 |
| Dependencies | None |

### FR-006: Notifikasi Error Telegram (Supporting)

| Field | Value |
|---|---|
| Description | Kirim pesan ke Telegram chat saat bot mengalami error fatal |
| Business Purpose | Admin bisa segera merespon masalah |
| Traces to | BO-005 |
| Inputs | Error message string |
| Outputs | Telegram message |
| Validation Rules | Message harus mengandung timestamp + error detail |
| Permissions | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |
| Error Handling | Jika Telegram gagal → log ke stdout (fire-and-forget) |
| Acceptance Criteria | AC-006 |
| Dependencies | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |

### FR-007: Multiple Topik (Supporting)

| Field | Value |
|---|---|
| Description | 5 topik soal: deret_angka, aritmatika_aljabar, peluang_statistika, geometri, fungsi_grafik |
| Business Purpose | Variasi konten |
| Traces to | BO-001 |
| Inputs | Topic list (hardcoded) |
| Outputs | Selected topic |
| Validation Rules | Topic harus dari daftar yang valid |
| Permissions | None |
| Error Handling | Jika topic tidak dikenal → fallback random |
| Acceptance Criteria | AC-007 |
| Dependencies | None |

### FR-008: Rotasi Topik Harian (Supporting)

| Field | Value |
|---|---|
| Description | Tidak boleh topik yang sama dalam 1 hari |
| Business Purpose | Variasi harian |
| Traces to | BO-002 |
| Inputs | history.json (topik + tanggal) |
| Outputs | Unique topic for this session |
| Validation Rules | Topic belum pernah dipakai hari ini |
| Permissions | Read history.json |
| Error Handling | Jika semua topik sudah terpakai → reset (allow repeat) |
| Acceptance Criteria | AC-008 |
| Dependencies | FR-007 |

### FR-009: Background Music (Supporting)

| Field | Value |
|---|---|
| Description | Video memiliki BGM dari file MP3 yang di-bundle |
| Business Purpose | Meningkatkan engagement dan watch time |
| Traces to | BO-001 |
| Inputs | MP3 file from audio/ directory |
| Outputs | Video dengan audio track |
| Validation Rules | Audio harus ada di output video |
| Permissions | Read audio/ |
| Error Handling | Jika file audio tidak ada → render tanpa audio |
| Acceptance Criteria | AC-009 |
| Dependencies | audio/bgm.mp3 |

### FR-010: Layout Video 3 Frame (Supporting)

| Field | Value |
|---|---|
| Description | Video terdiri dari 3 frame: soal, pilihan, pembahasan |
| Business Purpose | Informasi tersaji secara bertahap, mudah dicerna |
| Traces to | BO-001 |
| Inputs | Narasi JSON |
| Outputs | Video frames |
| Validation Rules | Setiap frame harus visible minimal 3 detik |
| Permissions | None |
| Error Handling | Jika frame kosong → skip frame |
| Acceptance Criteria | AC-010 |
| Dependencies | FR-002 |

---

## 9. Non-Functional Requirements

| ID | Requirement | Target | Measurement | Traces to |
|---|---|---|---|---|
| NFR-001 | Durasi video | 15-30 detik | MoviePy duration check | BO-001 |
| NFR-002 | Resolusi video | 1080×1920 (9:16 portrait) | ffprobe check | BO-001 |
| NFR-003 | Eksekusi <5 menit | 100% run <300 detik | GitHub Actions duration | BO-002 |
| NFR-004 | Error rate | <5% per bulan | Log analysis | BO-005 |
| NFR-005 | Gratis/open source | 0 biaya lisensi | Dependency audit | BO-004 |
| NFR-006 | History retention | Minimal 60 hari | history.json length cap | BO-003 |

---

## 10. Data Requirements

### Entity: Video Record

| Field | Type | Required | Description |
|---|---|---|---|
| soal | String | Yes | Teks soal matematika |
| pilihan | String[] | Yes | 4 pilihan jawaban |
| jawaban | String | Yes | Jawaban benar |
| penjelasan | String | Yes | Pembahasan jawaban |
| topik | String | Yes | Topic ID |
| tanggal | Date | Yes | Tanggal post (YYYY-MM-DD) |
| video_path | String | No | Path file video (untuk debugging) |

### Entity: History Entry

| Field | Type | Required | Description |
|---|---|---|---|
| soal | String | Yes | Teks soal (used for dedup) |
| jawaban | String | Yes | Jawaban benar |
| topik | String | Yes | Topic ID |
| tanggal | String | Yes | Tanggal post |

Retention: Max 180 entries (~60 days at 3/day). Oldest entries auto-purged.

---

## 11. Database Requirements

No database server. Single JSON file (`data/history.json`) sebagai persistent store.

### Entities

**history_entry**
- soal: string (unique dalam file)
- jawaban: string
- topik: string (enum: 5 topics)
- tanggal: string (YYYY-MM-DD)

### Constraints
- Array max 180 items
- Tidak ada foreign key (single file)
- Tidak ada index (linear scan untuk dedup, array <200 items)

---

## 12. ERD (Text)

```
[Gemini API] ──→ narasi JSON ──→ [main.py] ──→ video MP4 ──→ [Facebook Graph API]
                                      │
                                      ├── reads/writes ──→ history.json
                                      │
                                      └── reads ──→ audio/bgm.mp3
                                                  fonts/*.ttf
```

---

## 13. Business Rules

| Rule | Description |
|---|---|
| BR-01 | Satu eksekusi = satu soal = satu video = satu post |
| BR-02 | Topik tidak boleh sama dalam 1 hari (kecuali pool habis) |
| BR-03 | Soal tidak boleh duplikat terhadap seluruh history |
| BR-04 | History dipotong ke 180 item saat nambah entry baru |
| BR-05 | Jika post gagal, jangan simpan history |
| BR-06 | Jika Gemini gagal 3×, skip sesi, notifikasi admin |
| BR-07 | File temporary dihapus setelah selesai (sukses/gagal) |

---

## 14. Workflows

### Main Flow: Auto Post Reels

```
Start (GitHub Actions trigger)
  ↓
1. Load history.json → history list
  ↓
2. Pilih topik unik untuk hari ini
  ↓
3. Call Gemini API → generate narasi soal (JSON)
  ↓         ↻ retry 3× jika gagal
  ↓
4. Validasi narasi (field lengkap, no duplicate)
  ↓
5. Render video 1080×1920:
   ├─ Frame 1 (5-8 dtk): Header "SOAL MATEMATIKA" + teks soal
   ├─ Frame 2 (5-8 dtk): 4 pilihan jawaban
   └─ Frame 3 (5-10 dtk): Jawaban benar + pembahasan
   └─ Tambah BGM sepanjang video
  ↓
6. Post video ke Facebook Reels via Graph API
  ↓
7. Simpan {soal, jawaban, topik, tanggal} ke history.json
  ↓
8. Cleanup file temporary
  ↓
End (GitHub Actions commit + push history.json)
```

### Alternate Flow: Skip Sesi

```
Step 3 gagal 3× → Telegram notif → exit → history unchanged
Step 6 gagal → Telegram notif → exit → history unchanged (jangan record)
```

### Failure Flow: Total Failure

```
Gemini fail + retry habis → Telegram notif → exit code 1
Video render fail → cleanup → Telegram notif → exit code 1
Upload fail → cleanup → Telegram notif → exit code 1
```

---

## 15. API Requirements

| ID | Method | Path | Purpose | Auth | Rate Limit |
|---|---|---|---|---|---|
| API-001 | POST | https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent | Generate narasi soal | API Key | 60 RPM (free tier) |
| API-002 | POST | https://graph.facebook.com/v22.0/{FB_PAGE_ID}/videos | Upload video Reels | Page Access Token | 200 calls/6h/user |
| API-003 | POST | https://api.telegram.org/bot{TOKEN}/sendMessage | Kirim notifikasi error | Bot Token | 30 msg/sec |

### API-001 Request
```json
{
  "contents": [{"parts": [{"text": "prompt..."}]}],
  "generationConfig": {"responseMimeType": "application/json"}
}
```

### API-001 Response
```json
{
  "soal": "...",
  "pilihan": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "jawaban": "A. ...",
  "penjelasan": "..."
}
```

### API-002 Request
Multipart POST: video file + caption + access_token

### API-002 Response
```json
{
  "id": "video_post_id"
}
```

### API-003 Request
```json
{
  "chat_id": "...",
  "text": "ERROR: ..."
}
```

---

## 16. Integration Requirements

| Integration | Purpose | Trigger | Data Flow | Failure Handling |
|---|---|---|---|---|
| Google Gemini | Generate narasi soal | Step 3 workflow | prompt → JSON | Retry 3×, then skip + notif |
| Facebook Graph | Upload video Reels | Step 6 workflow | video + caption → post ID | Notif admin, jangan simpan history |
| Telegram Bot | Error notification | Any failure | error msg → chat | Fire-and-forget (log warning if fail) |

---

## 17. UI Requirements

N/A — Bot-only project. Tidak ada user interface.

---

## 18. Reporting Requirements

| Report | Description | Trigger | Method |
|---|---|---|---|
| Error Report | Error message + timestamp | Setiap error fatal | Telegram message |
| Execution Log | Full log each run | Setiap eksekusi | GitHub Actions log |

---

## 19. Notification Requirements

| Notification | Trigger | Recipient | Content | Failure Handling |
|---|---|---|---|---|
| Error Telegram | Bot gagal eksekusi | Admin (Chat ID) | `[ERROR] YYYY-MM-DD HH:MM:SS - {error_message}` | Log to stdout, jangan blocking |

---

## 20. Audit Requirements

| Audited Action | Data Captured | Retention |
|---|---|---|
| Setiap post sukses | {soal, jawaban, topik, tanggal} | 60 hari (di history.json) |
| Setiap error | Timestamp + error message | GitHub Actions logs (90 hari) |
| History mutation | File commit di git | Forever (git history) |

---

## 21. Security Requirements

| Requirement | Implementation |
|---|---|
| Authentication | GitHub Actions secrets (5 env vars) |
| Credential Storage | GitHub encrypted secrets, never in code |
| API Key Protection | Env var only, .gitignore untuk .env |
| Facebook Token | Minimum scope: pages_manage_posts |
| No PII stored | Hanya teks soal, jawaban, topik, tanggal |
| Git exposure | .env example tanpa nilai real |

---

## 22. Performance Requirements

| Metric | Target |
|---|---|
| Gemini API call | <10 detik |
| Video rendering | <60 detik |
| Facebook upload | <30 detik |
| Total execution | <5 menit |
| Script startup | <5 detik |

---

## 23. Scalability Requirements

| Aspect | Current | Growth (12 bulan) |
|---|---|---|
| Posts per day | 3 | 3 (stable) |
| History items | 180 max | 180 max |
| Storage (video) | ~10MB per run | ~10MB (temporary, deleted) |
| Storage (history) | ~50KB | ~50KB |

No scalability concerns. Single-threaded sequential execution.

---

## 24. Multi-Tenancy Considerations

N/A — Single Facebook Page, single user.

---

## 25. Data Retention Policy

| Data | Retention | Deletion |
|---|---|---|
| history.json entries | 60 hari (180 entries max) | Auto-purge oldest saat nambah baru |
| Generated video files | Sesi berakhir | Deleted after upload/error |
| GitHub Actions logs | 90 hari (GitHub policy) | Automatic |

---

## 26. Edge Cases

| ID | Edge Case | Related FR | Handling |
|---|---|---|---|
| EC-001 | Gemini return invalid JSON | FR-001 | Retry 3×, final fail → skip |
| EC-002 | Token Facebook expired | FR-003 | Telegram notif, jangan simpan history |
| EC-003 | Disk space habis | FR-002 | Catch exception, cleanup, notif |
| EC-004 | Network failure upload | FR-003 | Retry 1×, fail → notif |
| EC-005 | Semua topik terpakai hari ini | FR-008 | Reset pool, allow repeat |
| EC-006 | History file corrupt | FR-005 | Backup .corrupt, start fresh |
| EC-007 | BGM file missing | FR-009 | Render tanpa audio |
| EC-008 | Font file missing | FR-002 | Fallback ke Pillow default |

---

## 27. Risk Assessment

| ID | Risk | Likelihood | Impact | Mitigation | Linked Assumption |
|---|---|---|---|---|---|
| RISK-001 | Facebook API endpoint berubah | Low | High | Gunakan versioned API (v22.0) | ASM-001 |
| RISK-002 | MoviePy tidak kompatibel di Ubuntu runner | Low | High | Test di ubuntu-latest sebelum deploy | ASM-002 |
| RISK-003 | Video rendering melebihi 5 menit | Medium | Medium | Optimasi resolusi/frame count | ASM-004 |
| RISK-004 | Gemini rate limit harian | Low | Medium | 3 panggilan/hari, well within limit | |
| RISK-005 | Facebook token 60-day expiry | Medium | High | Gunakan System User token (long-lived) | |
| RISK-006 | Git conflict history.json (concurrent runs) | Low | Low | Sequential cron, 1 run at a time | |

---

## 28. Acceptance Criteria

| ID | Related FR | Given | When | Then |
|---|---|---|---|---|
| AC-001 | FR-001 | Gemini API key valid | Bot memanggil Gemini | Menerima JSON valid dengan semua field |
| AC-002 | FR-002 | Narasi valid | Bot render video | File MP4 1080×1920, durasi 15-30 detik |
| AC-003 | FR-003 | Video valid + token valid | Bot upload ke Facebook | Response berisi post ID |
| AC-004 | FR-004 | Waktu cron tiba | Workflow trigger | Script main.py tereksekusi |
| AC-005 | FR-005 | Soal sudah ada di history | Bot deteksi duplikat | Tolak soal, generate ulang |
| AC-006 | FR-006 | Error terjadi | Bot kirim Telegram | Admin terima pesan error |
| AC-007 | FR-007 | Semua topik | Bot pilih salah satu | Topik valid dari 5 daftar |
| AC-008 | FR-008 | Topik hari ini sudah dipakai | Bot pilih topik lain | Topik unik untuk hari ini |
| AC-009 | FR-009 | BGM tersedia | Bot render video | Video memiliki audio track |
| AC-010 | FR-010 | Video selesai | Inspeksi frame | 3 frame visible |

---

## 28a. Traceability Matrix

| BO | FR/NFR | AC | Risk |
|---|---|---|---|
| BO-001 | FR-001, FR-002, FR-003, FR-007, FR-009, FR-010 | AC-001, AC-002, AC-003, AC-007, AC-009, AC-010 | RISK-001, RISK-002 |
| BO-002 | FR-004, FR-008 | AC-004, AC-008 | |
| BO-003 | FR-005 | AC-005 | |
| BO-004 | NFR-005 | — | |
| BO-005 | FR-006 | AC-006 | |
| | NFR-001, NFR-002, NFR-003, NFR-004, NFR-006 | — | |
| | NFR-001 | — | |
| | NFR-002 | — | |
| | NFR-003 | — | RISK-003 |
| | NFR-004 | — | |
| | NFR-006 | — | |

---

## 29. Release Strategy

| Phase | Scope | Timeline |
|---|---|---|
| Phase 1 (MVP) | Single script: generate → render → post → history | Day 1 |
| Phase 1a | GitHub Actions workflow + cron | Day 1 |
| Phase 2 | Testing live di Facebook Page | Day 2 |
| Future | Multiple BGM, efek transisi, multi-platform | TBD |

---

## 30. Future Enhancements

- Multiple BGM files dipilih random tiap sesi
- Efek transisi antar frame (crossfade, slide)
- Statistik jumlah post per topik
- Post ke Instagram Reels + TikTok
- Variasi template layout
- Generate video dengan voiceover AI

---

## 31. Technical Recommendations

| Layer | Recommendation | Justification |
|---|---|---|
| Language | Python 3.12 | Sama dengan project sebelumnya, terbukti |
| AI | Gemini 2.5 Flash | Gratis, fast, JSON mode support |
| Video | MoviePy ≥2.0 + Pillow | Open source, Python-native |
| TTS (future) | gTTS | Gratis, Google TTS |
| BGM | Bundled MP3 (free license) | No streaming dependency |
| Scheduler | GitHub Actions cron | Gratis, built-in secrets |
| Persistence | JSON file | Cukup untuk 180 entries |
| Error Notif | Telegram Bot API | Gratis, real-time |

---

## 32. Effort & Resource Estimation

| Feature Group | Estimated Effort | Roles Required | Critical Path |
|---|---|---|---|
| Narasi + Validasi | 0.5 day | 1 engineer | FR-001 → FR-005 |
| Video Rendering | 1 day | 1 engineer | FR-002, FR-009, FR-010 |
| Facebook Upload | 0.5 day | 1 engineer | FR-003 |
| Scheduling + History | 0.5 day | 1 engineer | FR-004, FR-008 |
| Error Handling | 0.5 day | 1 engineer | FR-006 |
| Testing + Debug | 0.5 day | 1 engineer | All |

**Total: ~3.5 days (single engineer full-time)**

Estimates are indicative based on project complexity, not committed.

---

## 33. Glossary

| Term | Definition |
|---|---|
| Gemini | Google AI model (gemini-3.1-flash-lite) untuk generate teks |
| Reels | Format video pendek portrait di Facebook |
| MoviePy | Library Python untuk video editing |
| Pillow | Library Python untuk image processing |
| Graph API | Facebook API untuk akses halaman dan konten |
| BGM | Background Music |
| FFmpeg | Multimedia framework (backend MoviePy) |
| GitHub Actions | CI/CD platform untuk automation |

---

## 34. Final Validation Summary

| Checklist Item | Status |
|---|---|
| Stakeholders defined | ✓ |
| User roles defined | ✓ |
| Workflows defined (+ alternate + failure) | ✓ |
| Permissions defined | ✓ |
| Validations defined | ✓ |
| Reports defined | ✓ |
| Notifications defined | ✓ |
| Integrations defined | ✓ |
| Audit requirements defined | ✓ |
| Security requirements defined | ✓ |
| Performance targets defined | ✓ |
| Retention policy defined | ✓ |
| Risks documented | ✓ |
| Assumptions documented | ✓ |
| Acceptance criteria defined | ✓ |
| Traceability matrix complete | ✓ |

**Outstanding Gaps:** None
