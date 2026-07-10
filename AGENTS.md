# Agent Memory — auto-post-reels-matematika

## Fixes Applied (2026-07-10)

### Fix #2: CSV Parser `_extract_record()`
- `csv_parser.py`: `_extract_record()` sekarang membaca `account_type`, `format`, `theme` dari CSV column mapping, bukan hardcoded None
- Menggunakan `row.get(COL_MAPPING.get("account_type", ""), "").strip()` dll

### Fix #3: Duplikasi `parse_csv_with_gemini()`
- `main.py`: Hapus duplikasi `parse_csv_with_gemini()` dan dead code `classify_performance()`
- Ganti call pakai `self_learning.csv_parser._parse_csv_via_gemini()`

### Fix #6: Import json
- `csv_parser.py`: Pindahkan `import json` ke atas file (posisi standar)

### Fix #7: STAGGER_MIN_HOURS
- `main.py`: Tambah `STAGGER_MIN_HOURS = 3` konsisten
- Pastikan `load_and_apply_learning_config()` return `cfg`
