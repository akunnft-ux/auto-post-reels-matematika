# PRD Expansion — Multi-Category Content (v0.5)

## Document Control

### Version History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.5 | 2026-07-03 | Tech Lead | Added multi-category rotation (Olimpiade SD/SMP/SMA, Ujian SD/SMP/SMA) alongside existing CPNS |

### Change Request Log

| CR ID | Date | Description | Owner | Status |
|---|---|---|---|---|
| CR-001 | 2026-07-03 | Add Olimpiade SD/SMP/SMA + Ujian SD/SMP/SMA content categories | Tech Lead | Draft |

### Change Origin

This document is a **delta** to PRD v0.4. Only sections that change are listed. All sections from v0.4 not mentioned here remain valid and unchanged.

---

## 1. Executive Summary (Updated)

**Project Name:** Auto Post Reels Matematika — Multi-Category Expansion

**Change Overview:** Bot awalnya hanya menarget konten CPNS/TKA/SNBT. Sekarang diperluas ke 7 kategori:

| Kategori | Deskripsi |
|---|---|
| CPNS (existing) | Soal CPNS/TKA/SNBT |
| Olimpiade SD | Soal olimpiade matematika tingkat SD |
| Olimpiade SMP | Soal olimpiade matematika tingkat SMP |
| Olimpiade SMA | Soal olimpiade matematika tingkat SMA |
| Ujian SD | Soal ujian matematika tingkat SD (US/USBN) |
| Ujian SMP | Soal ujian matematika tingkat SMP (US/USBN) |
| Ujian SMA | Soal ujian matematika tingkat SMA (US/USBN) |

**Rotation:** Equal weight 1/7 — giliran harian. Setiap hari bot memilih satu kategori secara acak.

**Topics:** Topik matematika (deret_angka, aritmatika_aljabar, dll) tetap sama untuk semua kategori — yang membedakan adalah tingkat kesulitan dan konteks soal.

**Success Definition Addition:** Semua 7 kategori menghasilkan konten secara merata tanpa dominasi kategori tertentu, audiens dari berbagai jenjang pendidikan terlayani.

---

## 2. Business Objectives (Updated)

| ID | Objective | Type | Success Metric |
|---|---|---|---|
| BO-001 | (unchanged) | Primary | 90-150 video/bulan |
| BO-002 | (unchanged) | Operational | 100% jadwal |
| BO-003 | (unchanged) | Operational | No duplicate in 60 days |
| BO-004 | (unchanged) | Strategic | Semua gratis/open source |
| BO-005 | (unchanged) | Secondary | Notifikasi error real-time |
| BO-006 | (unchanged) | Primary | 5.000 followers in 30 days |
| BO-007 | (unchanged) | Strategic | Analytics-driven optimization |
| BO-008 | (unchanged) | Operational | Zero violation |
| **BO-009** | Distribusi konten merata ke 7 kategori | **Operational** | Setiap kategori muncul ≥10% dari total post dalam sebulan |
| **BO-010** | Caption dan hashtag sesuai tiap kategori | **Operational** | Tidak ada hashtag CPNS di konten Olimpiade SD (100% akurat) |

---

## 3. Project Scope (Updated)

### In Scope (Additions)

- Rotasi kategori harian (CPNS, Olimpiade SD/SMP/SMA, Ujian SD/SMP/SMA) — 7 kategori, equal weight
- Prompt Gemini yang menyesuaikan kategori (tingkat kesulitan, konteks, terminologi)
- 7 kumpulan hashtag terpisah, masing-masing relevan per kategori
- Category ID disimpan di history.json untuk tracking dan analytics
- Category field ditambahkan ke history entry
- Video header/frame menampilkan nama kategori (misal: "OLIMPIADE SD" bukan "CPNS")

### Out of Scope (Additions)

- Pembuatan konten spesifik per jenjang yang membutuhkan kurikulum berbeda (topik tetap 5 yang sama)
- Sub-topik per kategori (misal: Kombinatorik khusus Olimpiade)

### Future Scope (Additions)

- Weight rotasi bisa diubah via self-learning
- Sub-topik spesifik per kategori (misal: Teori Bilangan untuk Olimpiade)
- Konten spesifik berdasarkan kurikulum (Kurikulum Merdeka, Cambridge, dll.)

---

## 6. Assumption Log (Updated)

| ID | Description | Reason | Impact | Status | Linked Risk |
|---|---|---|---|---|---|
| ASM-001 through ASM-009 | (unchanged from v0.4) | | | | |
| **ASM-010** | Gemini bisa menghasilkan konten untuk 7 kategori berbeda dengan kualitas setara | Model cukup general | High | Inferred | RISK-014 |
| **ASM-011** | Audiens dari berbagai jenjang (SD-SMA) ada di akun yang sama | Target user base cukup luas | Medium | Inferred | RISK-015 |
| **ASM-012** | Equal weight 1/7 per kategori tidak mengurangi kualitas total konten | Random distribution cukup fair | Low | Confirmed | |

---

## 7. User Stories (Updated)

| ID | As a | I want | So that | Realized By |
|---|---|---|---|---|
| US-001 through US-008 | (unchanged from v0.4) | | | |
| **US-009** | Admin | Konten berganti kategori setiap hari | Audiens dari SD-SMA semua kebagian konten | FR-019 |
| **US-010** | Admin | Setiap kategori punya hashtag sendiri | Konten relevan ditemukan target audiensnya | FR-020 |
| **US-011** | Audiens | Melihat konten yang sesuai jenjang saya | Belajar sesuai level saya | FR-019 |
| **US-012** | Orang tua/guru | Konten olimpiade untuk anak SD/SMP/SMA | Bahan latihan tambahan | FR-019 |

---

## 8. Functional Requirements (Additions)

### FR-019: Multi-Category Rotation (Core)

| Field | Value |
|---|---|
| Description | Bot memilih satu dari 7 kategori secara acak setiap hari: `cpns`, `olimpiade_sd`, `olimpiade_smp`, `olimpiade_sma`, `ujian_sd`, `ujian_smp`, `ujian_sma`. Semua kategori punya bobot sama (1/7). |
| Business Purpose | Memperluas audiens ke berbagai jenjang pendidikan |
| Traces to | BO-009 |
| Inputs | List kategori (hardcoded 7), history.json (untuk tracking distribusi) |
| Outputs | Selected category ID |
| Validation Rules | Category harus dari daftar 7 yang valid |
| Permissions | None |
| Error Handling | Jika kategori tidak dikenal → fallback ke CPNS |
| Acceptance Criteria | AC-019 |
| Dependencies | None |

Edge cases:
- EC-029: Semua kategori sudah terpakai hari ini → tetap pilih random (tidak ada larangan repeat category per hari — hanya repeat topic dalam 1 hari)
- EC-030: Kategori baru ditambahkan → otomatis terbaca dari list
- EC-031: Bobot tidak equal karena self-learning → bisa diubah via `CATEGORY_WEIGHTS` config

### FR-020: Category-Specific Hashtag Pool (Supporting)

| Field | Value |
|---|---|
| Description | Setiap kategori punya kumpulan hashtag sendiri yang relevan. Bot memilih 4-6 hashtag dari pool kategori yang aktif hari itu. |
| Business Purpose | Konten ditemukan oleh target audiens yang tepat |
| Traces to | BO-010 |
| Inputs | Selected category ID |
| Outputs | String hashtag (4-6 tags) |
| Validation Rules | Hanya hashtag dari pool kategori aktif yang digunakan |
| Permissions | None |
| Error Handling | Jika pool hashtag kategori kosong → fallback ke pool umum |
| Acceptance Criteria | AC-020 |
| Dependencies | FR-019 |

Edge cases:
- EC-032: Pool hashtag kategori tidak ada → fallback ke HASHTAG_POOL umum

### FR-021: Category-Aware Prompts (Core)

| Field | Value |
|---|---|
| Description | Prompt Gemini menyesuaikan konten berdasarkan kategori. CPNS → soal CPNS/TKA/SNBT. Olimpiade SD → soal olimpiade tingkat SD. Ujian SMA → soal ujian nasional/ sekolah SMA. |
| Business Purpose | Konten sesuai jenjang dan konteks yang tepat |
| Traces to | BO-009 |
| Inputs | Category ID, topic ID, content type |
| Outputs | JSON narasi sesuai kategori |
| Validation Rules | Narasi harus sesuai jenjang yang diminta |
| Permissions | GEMINI_API_KEY |
| Error Handling | Jika Gemini hasilkan konten tidak sesuai kategori → retry (3×) |
| Acceptance Criteria | AC-021 |
| Dependencies | FR-001 (generate_narasi), FR-019 |

Edge cases:
- EC-033: Gemini menghasilkan soal terlalu sulit/terlalu mudah untuk jenjang → retry
- EC-034: Kategori tidak dikenal oleh prompt → fallback ke prompt CPNS

### FR-022: Category Label in Video (Supporting)

| Field | Value |
|---|---|
| Description | Frame soal menampilkan label kategori (misal: "OLIMPIADE SD" atau "UJIAN NASIONAL SMP") di bagian header, menggantikan sub-label "CPNS • TKA • SNBT" yang saat ini hardcoded. |
| Business Purpose | Audiens langsung tahu jenjang konten |
| Traces to | BO-009 |
| Inputs | Category ID |
| Outputs | Text label yang di-render di header video |
| Validation Rules | Label harus sesuai kategori |
| Permissions | None |
| Error Handling | Jika label tidak ditemukan → fallback ke "SOAL MATEMATIKA" |
| Acceptance Criteria | AC-022 |
| Dependencies | FR-019, FR-010 (render frame) |

Edge cases:
- EC-035: Label kategori terlalu panjang untuk header → auto font-size scaling

### FR-023: Category Field in History (Supporting)

| Field | Value |
|---|---|
| Description | Setiap history entry menyimpan `category` ID (selain `topik`, `content_type`) untuk tracking distribusi dan analytics. |
| Business Purpose | Analytics bisa filter per kategori, distribusi terpantau |
| Traces to | BO-009, BO-010 |
| Inputs | Selected category ID |
| Outputs | history entry dengan field `category` |
| Validation Rules | Category wajib diisi |
| Permissions | Write ke data/history.json |
| Error Handling | Jika category kosong → simpan "unknown" |
| Acceptance Criteria | AC-023 |
| Dependencies | FR-019, FR-005 (anti-dupe must include category context) |

Edge cases:
- EC-036: History entry lama (sebelum update) tidak punya field category → dianggap "cpns" untuk backward compatibility

---

## 9. Non-Functional Requirements (Updated)

| ID | Requirement | Target | Measurement | Traces to |
|---|---|---|---|---|
| NFR-001 through NFR-009 | (unchanged from v0.4) | | | |
| **NFR-010** | Category distribution | Setiap kategori ≥10% dalam 30 hari | history.json category count | BO-009 |
| **NFR-011** | Hashtag accuracy | 0 hashtag mismatch per kategori | Random audit log | BO-010 |

---

## 10. Data Requirements (Updated)

### Entity: History Entry (Updated)

Additional field:

| Field | Type | Required | Description |
|---|---|---|---|
| category | String | Yes | Category ID: `cpns`, `olimpiade_sd`, `olimpiade_smp`, `olimpiade_sma`, `ujian_sd`, `ujian_smp`, `ujian_sma` |

Legacy entries (existing) without category field are treated as category: "cpns".

### Entity: Category Config (NEW)

| Field | Type | Required | Description |
|---|---|---|---|
| id | String | Yes | Category key |
| label | String | Yes | Display label (e.g. "Olimpiade SD") |
| hashtag_pool | String[] | Yes | Array of hashtags for this category |
| prompt_context | String | Yes | Context description for Gemini prompt |
| weight | Float | Yes | Selection weight (default: 1/7 each) |

This is a runtime config, not stored in a file — defined as Python dict in `main.py`.

---

## 12. Category Definitions

```python
CATEGORIES = {
    "cpns": {
        "label": "CPNS",
        "sub_label": "CPNS • TKA • SNBT",
        "hashtag_pool": ["#CPNS2026", "#TIUCPNS", "#SKDCPNS", "#TryoutCPNS", ...],
        "prompt_context": "soal matematika untuk persiapan CPNS/TKA/SNBT, tingkat kesulitan sedang-cukup sulit",
    },
    "olimpiade_sd": {
        "label": "Olimpiade SD",
        "sub_label": "Olimpiade Matematika SD",
        "hashtag_pool": ["#OlimpiadeSD", "#OlimpiadeMatematika", "#MatematikaSD", ...],
        "prompt_context": "soal olimpiade matematika tingkat SD, soal berpola dan logis, sesuai untuk siswa SD kelas 4-6",
    },
    "olimpiade_smp": {
        "label": "Olimpiade SMP",
        "sub_label": "Olimpiade Matematika SMP",
        "hashtag_pool": ["#OlimpiadeSMP", "#OlimpiadeMatematika", "#MatematikaSMP", ...],
        "prompt_context": "soal olimpiade matematika tingkat SMP, soal berpola, logis, dan menantang",
    },
    "olimpiade_sma": {
        "label": "Olimpiade SMA",
        "sub_label": "Olimpiade Matematika SMA",
        "hashtag_pool": ["#OlimpiadeSMA", "#OlimpiadeMatematika", "#MatematikaSMA", ...],
        "prompt_context": "soal olimpiade matematika tingkat SMA, soal berpola kompleks dan menantang",
    },
    "ujian_sd": {
        "label": "Ujian SD",
        "sub_label": "Ujian Sekolah SD",
        "hashtag_pool": ["#UjianSD", "#USSD", "#USBNSD", "#MatematikaSD", ...],
        "prompt_context": "soal ujian sekolah (US/USBN) matematika tingkat SD, sesuai kurikulum SD",
    },
    "ujian_smp": {
        "label": "Ujian SMP",
        "sub_label": "Ujian Sekolah SMP",
        "hashtag_pool": ["#UjianSMP", "#USSMP", "#USBNSMP", "#MatematikaSMP", ...],
        "prompt_context": "soal ujian sekolah (US/USBN) matematika tingkat SMP, sesuai kurikulum SMP",
    },
    "ujian_sma": {
        "label": "Ujian SMA",
        "sub_label": "Ujian Sekolah SMA",
        "hashtag_pool": ["#UjianSMA", "#USSMA", "#USBNSMA", "#MatematikaSMA", ...],
        "prompt_context": "soal ujian sekolah (US/USBN) matematika tingkat SMA, sesuai kurikulum SMA",
    },
}
```

---

## 13. Business Rules (Updated)

Additional rules:

| Rule | Description |
|---|---|
| BR-11 | Satu eksekusi = satu kategori = satu konten (tidak ada multi-kategori dalam 1 video) |
| BR-12 | Kategori dipilih random, equal weight (1/7) setiap hari — tidak ada repeat prevention per kategori |
| BR-13 | Hashtag caption HANYA dari pool kategori aktif hari itu — dilarang campur hashtag dari kategori lain |
| BR-14 | Legacy history entries (tanpa field `category`) dianggap kategori `cpns` |
| BR-15 | Label kategori ditampilkan di header video, sub-label header, dan sub-label prompt |

---

## 14. Workflows (Updated)

### Main Flow: Step 2 — Category Selection (NEW STEP)

```
Start (GitHub Actions trigger)
  ↓
0. Pilih kategori (baru): random dari 7, equal weight
  ↓
1. Load history.json → history list
  ↓
1b. Filter history by category (for anti-dupe context in prompt)
  ↓
2. Pilih topik unik untuk hari ini (tidak repeat dalam 1 hari)
  ↓
3. Call Gemini API → generate narasi soal (JSON) — dengan prompt yang menyesuaikan kategori
  ...
```

### Alternate Flow: Category-Specific Failure

```
Category hashtag pool kosong → fallback ke HASHTAG_POOL umum
Category prompt tidak dikenal → fallback ke prompt "cpns"
```

---

## 18. Reporting Requirements (Updated)

| Report | Description | Trigger | Method |
|---|---|---|---|
| (existing reports unchanged) | | | |
| **Category Distribution Report** | Persentase tiap kategori dalam 30 hari | Setiap bulan | history.json → category count |

---

## 26. Edge Cases (Updated)

| ID | Edge Case | Related FR | Handling |
|---|---|---|---|
| EC-029 through EC-028 | (unchanged from v0.4) | | |
| EC-029 | Semua kategori sudah terpakai hari ini | FR-019 | Tidak dicegah — boleh repeat kategori per hari |
| EC-030 | Kategori baru ditambahkan | FR-019 | Otomatis terbaca dari list |
| EC-031 | Bobot kategori berubah | FR-019 | Config CATEGORY_WEIGHTS bisa diubah |
| EC-032 | Pool hashtag kategori kosong | FR-020 | Fallback ke HASHTAG_POOL umum |
| EC-033 | Gemini hasilkan konten salah jenjang | FR-021 | Retry 3× dengan reminder jenjang |
| EC-034 | Kategori tidak dikenal di prompt | FR-021 | Fallback ke prompt CPNS |
| EC-035 | Label kategori terlalu panjang | FR-022 | Font auto-scaling |
| EC-036 | History entry lama tanpa category | FR-023 | Default ke "cpns" |

---

## 27. Risk Assessment (Updated)

| ID | Risk | Likelihood | Impact | Mitigation | Linked Assumption |
|---|---|---|---|---|---|
| RISK-001 through RISK-012 | (unchanged from v0.4) | | | | |
| **RISK-014** | Gemini tidak konsisten hasilkan konten untuk 7 kategori | Medium | Medium | Prompt engineering per kategori, retry 3× | ASM-010 |
| **RISK-015** | Audiens SD-SMA tidak cocok di 1 akun | Medium | Medium | Analisis engagement per kategori setelah 14 hari; jika ada kategori 0 engagement → pindahkan ke platform terpisah | ASM-011 |
| **RISK-016** | Kompleksitas kode bertambah signifikan | Low | Low | Refactor terstruktur: kategori sebagai module terpisah |

---

## 28. Acceptance Criteria (Updated)

| ID | Related FR | Given | When | Then |
|---|---|---|---|---|
| AC-001 through AC-017 | (unchanged from v0.4) | | | |
| **AC-019** | FR-019 | Bot jalan | Setiap eksekusi | Kategori terpilih salah satu dari 7 dengan distribusi mendekati equal dalam 70 run |
| **AC-020** | FR-020 | Kategori terpilih | Bot generate caption | Hanya hashtag dari pool kategori itu yang muncul (cek sampling 10 post) |
| **AC-021** | FR-021 | Kategori "Olimpiade SD" terpilih | Gemini generate konten | Soal sesuai tingkat SD (cek kata-kata, tidak ada konsep SMA) |
| **AC-022** | FR-022 | Video di-render | Cek header frame | Label kategori muncul di header, bukan "CPNS • TKA • SNBT" |
| **AC-023** | FR-023 | History entry disimpan | Cek history.json | Field `category` ada dan terisi |

---

## 28a. Traceability Matrix (Updated)

| BO | FR/NFR | AC | Risk |
|---|---|---|---|
| BO-001 | FR-001, FR-002, FR-003, FR-007, FR-009, FR-010, FR-011, FR-016, FR-017 | AC-001, AC-002, AC-003, AC-007, AC-009, AC-010, AC-011, AC-016, AC-017 | RISK-001, RISK-002, RISK-011, RISK-013 |
| BO-002 | FR-004, FR-008 | AC-004, AC-008 | |
| BO-003 | FR-005 | AC-005 | |
| BO-004 | NFR-005 | — | |
| BO-005 | FR-006 | AC-006 | |
| BO-006 | FR-011, FR-012, FR-013, FR-014, NFR-007 | AC-011, AC-012, AC-013, AC-014 | RISK-007 |
| BO-007 | FR-011, FR-012, FR-014, NFR-008 | AC-011, AC-012, AC-014 | |
| BO-008 | FR-015, NFR-009 | AC-015 | RISK-008, RISK-009 |
| **BO-009** | **FR-019, FR-021, FR-022, FR-023, NFR-010** | **AC-019, AC-021, AC-022, AC-023** | **RISK-014, RISK-015** |
| **BO-010** | **FR-020, FR-023, NFR-011** | **AC-020** | |
| | NFR-001, NFR-002, NFR-003, NFR-004, NFR-006 | — | |

---

## 32. Effort & Resource Estimation (Updated)

| Feature Group | Estimated Effort | Roles Required | Critical Path |
|---|---|---|---|
| Existing features | (already completed) | | |
| **Category system (FR-019, FR-022, FR-023)** | **0.5 day** | 1 engineer | FR-019 → FR-022 → FR-023 |
| **Category prompts (FR-021)** | **0.25 day** | 1 engineer | FR-021 (modify generate_narasi) |
| **Hashtag pools (FR-020)** | **0.25 day** | 1 engineer | FR-020 (add CATEGORIES dict) |
| **Testing** | **0.25 day** | 1 engineer | All new FRs |
| **Total Expansion** | **~1.25 days** | 1 engineer | |

---

## 34. Final Validation (Expansion)

| Checklist Item | Status |
|---|---|
| Category rotation defined (7 categories, equal weight) | ✓ |
| Category-specific prompts defined | ✓ |
| Category-specific hashtags defined | ✓ |
| Category label in video defined | ✓ |
| Category field in history defined | ✓ |
| Edge cases documented | ✓ |
| Assumptions documented | ✓ |
| Risks documented | ✓ |
| Acceptance criteria defined | ✓ |
| Traceability matrix updated | ✓ |

**Outstanding Gaps:** None
