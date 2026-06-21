# Discovery Report — Auto Post Reels Matematika

## 1. Executive Summary

Proyek ini adalah bot auto-posting untuk Facebook Reels dengan konten edukasi matematika (soal CPNS/TKA/SNBT). Bot akan menghasilkan naskah soal via Gemini AI, merender video pendek (15-30 detik) menggunakan MoviePy + Pillow + gTTS (BGM only), dan memposting ke Facebook Reels via Graph API. Dijadwalkan 3x/hari via GitHub Actions.

## 2. Problem Statement

Membutuhkan konten Reels edukasi matematika yang konsisten 3x/hari secara otomatis untuk pertumbuhan akun Facebook. Pembuatan video manual tidak scalable.

## 3. Stakeholders

| Stakeholder | Role |
|---|---|
| Pemilik akun Facebook | Admin & Operator |
| Audiens (pengikut Facebook) | End Users |

## 4. User Roles

| Role | Responsibilities |
|---|---|
| Admin | Mengatur jadwal, memonitor error via Telegram, mengelola kredensial |
| Sistem (Bot) | Generate narasi, render video, posting, catat history |

## 5. Core Workflows

### Workflow: Auto Post Reels

```
GitHub Actions Cron Trigger (06:00 / 10:00 / 13:00 UTC)
  ↓
Load history.json
  ↓
Pilih topik (5 topik: deret_angka, aritmatika_aljabar, peluang_statistika, geometri, fungsi_grafik)
  ↓
Call Gemini API → generate narasi video (soal + pilihan + jawaban + pembahasan)
  ↓
Render video 1080×1920 (9:16) dengan Pillow + MoviePy:
  - Frame 1: Header + Soal (3-5 detik)
  - Frame 2: Pilihan jawaban (3-5 detik)
  - Frame 3: Pembahasan + jawaban benar (5-8 detik)
  - Tambah BGM background
  - Durasi total: 15-30 detik
  ↓
Post ke Facebook Reels via Graph API /videos endpoint
  ↓
Simpan history ke history.json
  ↓
Commit & push history ke repo
```

## 6. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Bot harus generate narasi soal matematika via Gemini API | MUST |
| FR-02 | Bot harus render video 9:16 (1080×1920) dari narasi | MUST |
| FR-03 | Bot harus posting ke Facebook Reels via Graph API | MUST |
| FR-04 | Bot harus berjalan 3x/hari via cron | MUST |
| FR-05 | Bot harus mencegah duplikasi soal (history.json) | MUST |
| FR-06 | Bot harus kirim notifikasi error via Telegram | MUST |
| FR-07 | Bot harus support multiple topik (5 topik) | MUST |
| FR-08 | Bot harus rotasi topik agar tidak sama dalam 1 hari | MUST |
| FR-09 | Video harus punya background music (BGM) | MUST |
| FR-10 | Video harus punya teks soal, pilihan, dan pembahasan | MUST |
| FR-11 | Bot harus support retry jika API gagal (3x) | SHOULD |

## 7. Non-Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-01 | Durasi video 15-30 detik | MUST |
| NFR-02 | Video resolusi 1080×1920 portrait | MUST |
| NFR-03 | Bot harus selesai dalam <5 menit per eksekusi | MUST |
| NFR-04 | History retention minimal 60 hari | SHOULD |
| NFR-05 | Semua dependency gratis / open source | MUST |

## 8. Reporting Requirements

| Report | Description | Priority |
|---|---|---|
| Error notification | Telegram message saat bot gagal | MUST |
| GitHub Actions logs | Visible di dashboard GitHub Actions | SHOULD |

## 9. Integration Requirements

| Integration | Purpose | Authentication |
|---|---|---|
| Google Gemini API | Generate narasi soal | API Key |
| Facebook Graph API | Post video ke Facebook Reels | Page Access Token |
| Telegram Bot API | Kirim notifikasi error | Bot Token |

## 10. Assumption Log

| # | Assumption | Reason | Impact | Status |
|---|---|---|---|---|
| A-01 | Facebook Graph API /videos endpoint mendukung upload Reels | Berdasarkan dokumentasi Meta | Critical jika salah | Inferred |
| A-02 | MoviePy bisa render video 1080×1920 dengan teks + BGM | MoviePy support arbitrary resolutions | High | Confirmed |
| A-03 | Gemini 2.5 Flash bisa generate narasi dalam format JSON | Sama dengan project sebelumnya | High | Confirmed |
| A-04 | GitHub Actions runner cukup kuat untuk render video | Ubuntu runner punya resource cukup | Medium | Inferred |
| A-05 | Background music bisa dari file MP3 yang di-bundle | Tidak royalty issue untuk akun edukasi | Medium | Inferred |
| A-06 | Format video H.264 compatible dengan Facebook Reels | Standar industri | High | Inferred |

## 11. Gap Analysis

| Gap | Description | Action |
|---|---|---|
| Belum ada library text-to-video dipilih | MoviePy + Pillow akan digunakan | Confirm di arsitektur |
| Belum ada strategi BGM | Akan bundle beberapa MP3 gratis | Tentukan sumber BGM |
| Belum ada template video design | Perlu desain layout tiap frame | Tentukan di arsitektur |

## 12. Open Questions

| # | Question | Answer |
|---|---|---|
| Q-01 | Apakah perlu efek transisi antar frame? | (Pending - default: simple crossfade) |
| Q-02 | Bahasa konten? Indonesia seperti project sebelumnya | Diasumsikan Indonesia |
| Q-03 | Font tetap DejaVu Sans? Support Indonesia | Ya, DejaVu Sans cukup |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Facebook Graph API berubah | Low | High | Gunakan versioned API, monitoring |
| Gemini API rate limit | Low | Medium | Retry logic + backoff |
| Video rendering terlalu lama | Medium | Medium | Optimasi resolusi/durasi |
| Disk space habis di runner | Low | Medium | Hapus temp files setelah render |
| BGM copyright | Low | Medium | Gunakan music bebas royalti |

## 14. Feature Prioritization

| Feature | Priority |
|---|---|
| Generate narasi + render video + post ke Facebook | MUST |
| Rotasi topik + anti duplicate | MUST |
| Error notification Telegram | MUST |
| Background music | MUST |
| Efek transisi antar frame | COULD |
| Multiple BGM random | COULD |
| Analytics dashboard | FUTURE |
| Cross-platform (TikTok/IG) | FUTURE |

## 15. Recommendation

Lanjut ke Phase 2 (PRD). Stack: Python + Gemini + MoviePy + Pillow + gTTS + Facebook Graph API + GitHub Actions. Tidak perlu UI/UX (bot-only).
