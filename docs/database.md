# Database Design — Auto Post Reels Matematika

## 1. Database Overview

**Approach:** JSON file (`data/history.json`) sebagai persistent store. Tidak ada database server.

**Justification:** Proyek ini hanya menyimpan riwayat posting (~180 records max). Single writer (GitHub Actions sequential cron). Tidak perlu query engine, report, atau concurency. JSON file + git tracking adalah solusi paling sederhana.

**File path:** `data/history.json` (history), `data/analytics.json` (analytics), `data/growth.json` (follower growth)

## 2. Entity List

| Entity | Description | Records Max | Persistence |
|---|---|---|---|
| history_entry | Riwayat setiap soal yang pernah dipost | 180 | JSON array |
| analytics_record | Data performa per post (views, likes, comments, shares) | 180 | JSON array |
| growth_record | Daily follower count tracking | 90 | JSON array |

## 3. Entity Definitions

### history_entry

| Field | Type | Required | Description |
|---|---|---|---|
| soal | string | Yes | Teks soal matematika (used for dedup key) |
| jawaban | string | Yes | Jawaban yang benar |
| topik | string | Yes | Topic ID dari 5 topik |
| tanggal | string | Yes | Tanggal post format YYYY-MM-DD |

**Example entry:**
```json
{
  "soal": "Nilai dari 2 + 3 × 4 adalah...",
  "jawaban": "C. 14",
  "topik": "aritmatika_aljabar",
  "tanggal": "2026-06-21"
}
```

### analytics_entry (NEW)

| Field | Type | Required | Description |
|---|---|---|---|
| post_id | string | Yes | Facebook post ID |
| post_date | string | Yes | Tanggal post (YYYY-MM-DD) |
| views | integer | Yes | View count dari Insights API |
| likes | integer | Yes | Like count |
| comments | integer | Yes | Comment count |
| shares | integer | Yes | Share count |
| source | string | Yes | Must be "api" |
| content_type | string | Yes | quiz/fakta/tips |
| hook_template | string | No | Template hook yang digunakan |
| fetched_at | string | Yes | ISO8601 timestamp |

### growth_entry (NEW)

| Field | Type | Required | Description |
|---|---|---|---|
| date | string | Yes | YYYY-MM-DD |
| follower_count | integer | Yes | Total followers |
| source | string | Yes | Always "api" |
| daily_growth | integer | Yes | follower_count - previous_day |
| fetched_at | string | Yes | ISO8601 timestamp |

## 4. Relationship Map

Tidak ada relationship. Tiga flat array terpisah: history, analytics, growth.

## 5. ERD

```
┌─────────────────────────────────┐
│         history.json            │
│  ┌───────────────────────────┐  │
│  │ history_entry[0]          │  │
│  │ ├─ soal: string           │  │
│  │ ├─ jawaban: string        │  │
│  │ ├─ topik: string          │  │
│  │ └─ tanggal: string        │  │
│  ├───────────────────────────┤  │
│  │ history_entry[1...179]    │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

## 6. Table Definitions

N/A (JSON file, not a database table). Representasi dalam kode Python:

```python
# Type hint
history_entry: dict = {
    "soal": str,
    "jawaban": str,
    "topik": Literal["deret_angka", "aritmatika_aljabar", "peluang_statistika", "geometri", "fungsi_grafik"],
    "tanggal": str  # YYYY-MM-DD
}

# File structure
history: list[history_entry]  # max 180 items
```

## 7. Constraints

| Constraint | Implementation |
|---|---|
| Unique soal | Exact string match saat cek duplicate |
| Max 180 entries | Auto-purge oldest saat append baru |
| jawaban ∈ pilihan | Validasi dalam kode setelah Gemini response |
| topik ∈ allowed_topics | Validasi dalam kode |

## 8. Index Strategy

N/A — Linear scan pada array <200 items. Tidak perlu index.

## 9. Unique Constraints

**Natural key:** `soal` (full text uniqueness).

Duplikasi dicegah di application layer:
1. Gemini diberikan context 20 history terakhir untuk hindari generate duplicate
2. Response divalidasi dengan string match terhadap seluruh history
3. Jika duplicate detected → retry generate

## 10. Audit Strategy

| Aspect | Implementation |
|---|---|
| Create timestamps | Field `tanggal` (date-level granularity) |
| Mutation history | Git commit log (setiap push history.json terekam) |
| Read access | GitHub Actions run log |

## 11. RLS Matrix

N/A — Tidak ada multi-user access. Single admin, single writer.

## 12. Reporting Strategy

| Report | Source |
|---|---|
| History posting | Read history.json langsung |
| Error logs | GitHub Actions UI |
| Token status | GitHub Actions log (manual check) |

## 13. Migration Strategy

N/A — Schema melekat pada kode Python. Jika format history berubah, tambah kode migrasi inline di main.py.

## 14. Backup Strategy

| Aspect | Plan |
|---|---|
| history.json | Otomatis tercadang di git setiap commit |
| Recovery | Git checkout ke commit sebelumnya |

## 15. Retention Strategy

| Data | Retention | Mechanism |
|---|---|---|
| history entries | 60 hari (180 entries) | Auto-purge oldest saat nambah baru |
| Git history | Forever | Git repository |
| Temp video files | Satu sesi | Deleted after upload/error |

## 16. Security Design

| Concern | Implementation |
|---|---|
| Data exposure | history.json hanya berisi teks soal, tidak ada PII |
| Integrity | Git-tracked, immutable history |
| Access | Hanya GitHub Actions dan admin yang akses repo |

## 17. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| history.json corrupt | Low | Low | Backup + start fresh, error notif |
| Git conflict | Low | Low | Sequential cron, no concurrent writes |
| Schema change | Low | Low | Migration function in main.py |

## 18. Recommendations

1. File JSON cukup untuk skala project ini (180 entries × ~200 bytes = ~36KB)
2. Jika nantinya perlu multi-user atau query lebih kompleks, migrasi ke SQLite
3. Simpan backup history.json secara periodik jika data dianggap kritis
