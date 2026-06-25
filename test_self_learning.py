#!/usr/bin/env python3
"""QA Test: Self-Learning Module — auto-post-reels-matematika

Tests CSV parsing, classification, learning engine, and analytics store
without requiring external API keys (Gemini/Facebook/Telegram).
Uses mock CSV data and mock analytics records.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0
ERROR = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))

def check(name, func):
    global ERROR
    try:
        func()
    except Exception as e:
        ERROR += 1
        print(f"  ✗ {name} — EXCEPTION: {e}")

# ── Fixtures ──

MOCK_CSV_STANDARD = """Post ID,Post Date,Impressions,Likes,Comments,Shares
fb_post_001,2026-06-01,1500,120,45,30
fb_post_002,2026-06-02,200,15,2,1
fb_post_003,2026-06-03,30,1,0,0
fb_post_004,2026-06-04,5000,400,120,80
fb_post_005,2026-06-05,80,3,1,0
"""

MOCK_CSV_BAHASA = """Post ID,Tanggal,Tayangan,Suka,Komentar,Bagikan
fb_post_101,2026-06-01,2000,180,50,25
fb_post_102,2026-06-02,100,5,1,0
fb_post_103,2026-06-03,45,0,0,0
"""

MOCK_CSV_EMPTY = ""
MOCK_CSV_NO_HEADER = "abc,123,def\nghi,456,jkl"
MOCK_CSV_MISSING_COLS = """id,date,random
1,2026-01-01,foo
"""

SAMPLE_RECORDS = [
    {"post_id": "p1", "platform": "facebook", "views": 1500, "likes": 120, "comments": 45, "shares": 30, "engagement_rate": 0.13, "source": "manual", "fetched_at": "2026-06-01T00:00:00Z"},
    {"post_id": "p2", "platform": "facebook", "views": 200, "likes": 15, "comments": 2, "shares": 1, "engagement_rate": 0.09, "source": "manual", "fetched_at": "2026-06-02T00:00:00Z"},
    {"post_id": "p3", "platform": "facebook", "views": 30, "likes": 1, "comments": 0, "shares": 0, "engagement_rate": 0.03, "source": "manual", "fetched_at": "2026-06-03T00:00:00Z"},
    {"post_id": "p4", "platform": "facebook", "views": 5000, "likes": 400, "comments": 120, "shares": 80, "engagement_rate": 0.12, "source": "manual", "fetched_at": "2026-06-04T00:00:00Z"},
    {"post_id": "p5", "platform": "facebook", "views": 80, "likes": 3, "comments": 1, "shares": 0, "engagement_rate": 0.05, "source": "manual", "fetched_at": "2026-06-05T00:00:00Z"},
]


# ══════════════════════════════════════════════
# TEST SUITE 1: CSV PARSER
# ══════════════════════════════════════════════

def test_csv_parser():
    print("\n[SUITE 1] CSV Parser")
    from self_learning.csv_parser import _parse_csv_direct, _map_columns

    # Test 1.1: Standard Facebook Insights CSV
    records = _parse_csv_direct(MOCK_CSV_STANDARD)
    test("Parse standard English CSV", len(records) == 5, f"got {len(records)}")
    if records:
        test("  → post_id extracted", records[0].get("post_id") == "fb_post_001")
        test("  → views parsed", records[0].get("views") == 1500)
        test("  → likes parsed", records[0].get("likes") == 120)
        test("  → engagement_rate computed", records[0].get("engagement_rate") > 0)
        test("  → source = manual", records[0].get("source") == "manual")

    # Test 1.2: Bahasa Indonesia CSV
    records_id = _parse_csv_direct(MOCK_CSV_BAHASA)
    test("Parse Bahasa Indonesia CSV", len(records_id) == 3, f"got {len(records_id)}")
    if records_id:
        test("  → Tayangan mapped to views", records_id[0].get("views") == 2000)
        test("  → Suka mapped to likes", records_id[0].get("likes") == 180)

    # Test 1.3: Empty CSV
    records_empty = _parse_csv_direct(MOCK_CSV_EMPTY)
    test("Parse empty CSV returns empty list", len(records_empty) == 0)

    # Test 1.4: CSV with no recognizable columns
    records_no_cols = _parse_csv_direct(MOCK_CSV_NO_HEADER)
    test("Parse CSV with no matching columns returns empty", len(records_no_cols) == 0)

    # Test 1.5: CSV with missing essential columns
    records_missing = _parse_csv_direct(MOCK_CSV_MISSING_COLS)
    test("Parse CSV missing essential columns returns empty", len(records_missing) == 0)

    # Test 1.6: File not found
    from self_learning.csv_parser import parse_csv
    result = parse_csv("/tmp/nonexistent_file.csv")
    test("Parse non-existent file returns empty", len(result) == 0)


# ══════════════════════════════════════════════
# TEST SUITE 2: ANALYTICS STORE
# ══════════════════════════════════════════════

def test_analytics_store():
    print("\n[SUITE 2] Analytics Store")
    from self_learning.analytics_store import merge_records, load_analytics_records, save_analytics_records

    # Test 2.1: Merge deduplication
    new = [{"post_id": "p1", "views": 999}]  # updated record for same post_id
    merged = merge_records(SAMPLE_RECORDS, new)
    test("Merge deduplicates by post_id", len(merged) == 5, f"got {len(merged)}")
    for r in merged:
        if r["post_id"] == "p1":
            test("  → Latest record wins for same post_id", r["views"] == 999)
            break

    # Test 2.2: Merge with new records
    more = [{"post_id": "p6", "views": 100, "fetched_at": "2026-06-06T00:00:00Z"}]
    merged2 = merge_records(merged, more)
    test("Merge adds new records", len(merged2) == 6, f"got {len(merged2)}")

    # Test 2.3: Merge respects max_records
    many_records = [{"post_id": f"p{i}", "fetched_at": "2026-06-06T00:00:00Z"} for i in range(600)]
    merged3 = merge_records(merged2, many_records, max_records=10)
    test("Merge respects max_records=10", len(merged3) == 10, f"got {len(merged3)}")

    # Test 2.4: Save and load
    tmp = tempfile.mktemp(suffix=".json")
    save_analytics_records(tmp, SAMPLE_RECORDS)
    loaded = load_analytics_records(tmp)
    test("Save and load roundtrip", len(loaded) == 5, f"got {len(loaded)}")
    os.remove(tmp)

    # Test 2.5: Load non-existent file
    loaded2 = load_analytics_records("/tmp/nonexistent_analytics.json")
    test("Load non-existent file returns empty list", len(loaded2) == 0)


# ══════════════════════════════════════════════
# TEST SUITE 3: CLASSIFIER
# ══════════════════════════════════════════════

def test_classifier():
    print("\n[SUITE 3] Classifier")
    from self_learning.classifier import classify_records, _classify_single

    # Test 3.1: Minimum records threshold
    result = classify_records([])
    test("Classify empty list returns empty", len(result) == 0)

    result = classify_records(SAMPLE_RECORDS[:2])
    test("Classify <3 records returns empty", len(result) == 0, f"got {len(result)}")

    # Test 3.2: Classification with follower_count=50 (< 100)
    result = classify_records(SAMPLE_RECORDS, follower_count=50)
    test("Classify with 50 followers produces records", len(result) == 5, f"got {len(result)}")
    if result:
        cls_map = {r["post_id"]: r["classification"] for r in result}
        # p3 has 30 views → bad (views < 50)
        test("  → p3 (30 views) classified as bad", cls_map.get("p3") == "bad")
        # p4 has 5000 views → viral (views > 1000, followers=50 < 100)
        test("  → p4 (5000 views) classified as viral", cls_map.get("p4") == "viral")

    # Test 3.3: Classification with follower_count=500
    result = classify_records(SAMPLE_RECORDS, follower_count=500)
    if result:
        cls_map = {r["post_id"]: r["classification"] for r in result}
        # p4 has 5000 views, threshold = 10 * 500 = 5000 → NOT viral (views not > 5000)
        test("  → p4 (5000 views, 500 followers) not viral (not > 5000)", cls_map.get("p4") != "viral")
        # p1 has 1500 views → not viral (1500 < 5000), engagement 0.13 → good
        test("  → p1 (1500 views, 500 followers) classified as good", cls_map.get("p1") == "good")

    # Test 3.4: _classify_single direct tests
    cls, _ = _classify_single(views=2000, engagement_rate=0.15, follower_count=50, niche_baseline=0.05)
    test("_classify_single: 2000 views, 50 followers = viral", cls == "viral")

    cls, _ = _classify_single(views=40, engagement_rate=0.02, follower_count=100, niche_baseline=0.05)
    test("_classify_single: 40 views = bad (views<50)", cls == "bad")

    cls, _ = _classify_single(views=200, engagement_rate=0.005, follower_count=100, niche_baseline=0.05)
    test("_classify_single: 0.5% engagement = bad (<1%)", cls == "bad")

    cls, _ = _classify_single(views=200, engagement_rate=0.08, follower_count=500, niche_baseline=0.05)
    test("_classify_single: 8% engagement = good", cls == "good")


# ══════════════════════════════════════════════
# TEST SUITE 4: LEARNING ENGINE
# ══════════════════════════════════════════════

def test_learning_engine():
    print("\n[SUITE 4] Learning Engine")
    from self_learning.learning_engine import (
        load_learning_config, save_learning_config,
        compute_learning_config, DEFAULT_CONFIG,
        VARIABLE_ORDER,
    )

    # Test 4.1: Load non-existent config creates default
    tmp = tempfile.mktemp(suffix=".json")
    cfg = load_learning_config(tmp)
    test("Load non-existent config returns defaults", cfg["variable_rotation_index"] == 0)
    test("  → default has content_type_weights", "content_type_weights" in cfg)
    test("  → default has hook_templates", "hook_templates" in cfg)
    test("  → default has cta_pool", "cta_pool" in cfg)
    test("  → default has hashtag_pool", "hashtag_pool" in cfg)
    os.remove(tmp)

    # Test 4.2: Insufficient classifications → no learning
    cfg = dict(DEFAULT_CONFIG)
    classifications = [{"post_id": "p1", "classification": "good", "metric_triggered": "test"}]
    result, iteration = compute_learning_config(cfg, classifications, SAMPLE_RECORDS)
    test("Learning with <3 classifications returns no iteration", iteration is None)

    # Test 4.3: Learning adjusts weights correctly
    cfg = dict(DEFAULT_CONFIG)
    classifications = [
        {"post_id": "p1", "classification": "viral", "metric_triggered": "test"},
        {"post_id": "p2", "classification": "good", "metric_triggered": "test"},
        {"post_id": "p3", "classification": "bad", "metric_triggered": "test"},
        {"post_id": "p4", "classification": "viral", "metric_triggered": "test"},
        {"post_id": "p5", "classification": "good", "metric_triggered": "test"},
    ]
    # Add content_type to analytics records for weight adjustment
    analytics = []
    for r in SAMPLE_RECORDS:
        r2 = dict(r)
        r2["content_type"] = "quiz"
        analytics.append(r2)

    # First iteration should be content_type_weights (rotation_index=0)
    result, iteration = compute_learning_config(cfg, classifications, analytics)
    test("Learning produces iteration", iteration is not None)
    if iteration:
        test("  → variable_changed = content_type_weights",
             iteration["variable_changed"] == "content_type_weights")
        test("  → rotation_index incremented", result["variable_rotation_index"] == 1)
        w = result.get("content_type_weights", {})
        test("  → weights sum to 1.0", abs(sum(w.values()) - 1.0) < 0.02)

    # Test 4.4: Variable rotation cycles
    cfg2 = dict(DEFAULT_CONFIG)
    cfg2["variable_rotation_index"] = 1
    result2, iteration2 = compute_learning_config(cfg2, classifications, analytics)
    if iteration2:
        expected_var = VARIABLE_ORDER[1 % len(VARIABLE_ORDER)]
        test(f"Variable rotation: index 1 → {expected_var}",
             iteration2["variable_changed"] == expected_var)

    # Test 4.5: Config save preserves data
    tmp2 = tempfile.mktemp(suffix=".json")
    save_learning_config(tmp2, result)
    loaded = load_learning_config(tmp2)
    test("Save/load learning_config preserves weights",
         loaded.get("content_type_weights") == result.get("content_type_weights"))
    test("Save/load sets updated_at", loaded.get("updated_at") is not None)
    os.remove(tmp2)


# ══════════════════════════════════════════════
# TEST SUITE 5: FULL PIPELINE (INTEGRATION)
# ══════════════════════════════════════════════

def test_full_pipeline():
    print("\n[SUITE 5] Full Pipeline Integration")
    from self_learning import run_self_learning

    # Write mock CSV to temp file
    tmp_csv = tempfile.mktemp(suffix=".csv")
    with open(tmp_csv, "w") as f:
        f.write(MOCK_CSV_STANDARD)

    result = run_self_learning(tmp_csv)
    test("Pipeline parses 5 records",
         result.get("records_parsed") == 5, f"got {result.get('records_parsed')}")
    test("Pipeline runs without error", result.get("status") == "ok")

    # Verify learning_config.json was written
    config_path = "self_learning/learning_config.json"
    test("learning_config.json exists after pipeline", os.path.exists(config_path))

    # Verify analytics_records.json was written
    analytics_path = "data/analytics_records.json"
    test("analytics_records.json exists after pipeline", os.path.exists(analytics_path))

    # Verify classification.json was written
    classification_path = "data/classification.json"
    test("classification.json exists after pipeline", os.path.exists(classification_path))

    os.remove(tmp_csv)

    # Reset data files for clean state
    for p in [analytics_path, classification_path, "data/learning_iteration.json"]:
        if os.path.exists(p):
            os.remove(p)


# ══════════════════════════════════════════════
# TEST SUITE 6: EDGE CASES
# ══════════════════════════════════════════════

def test_edge_cases():
    print("\n[SUITE 6] Edge Cases")

    # Test 6.1: CSV with duplicate post_ids
    from self_learning.csv_parser import _parse_csv_direct
    dup_csv = """Post ID,Impressions,Likes,Comments,Shares
dup_1,100,10,1,0
dup_1,200,20,2,1
"""
    records = _parse_csv_direct(dup_csv)
    test("CSV with duplicates parsed (both rows)", len(records) == 2)

    # After merge, only last should remain
    from self_learning.analytics_store import merge_records
    merged = merge_records([], records)
    test("Merge deduplicates: only 1 of dup_1", len(merged) == 1)
    test("  → keeps last value", merged[0]["views"] == 200)

    # Test 6.2: Zero views record
    zero_csv = """Post ID,Impressions,Likes,Comments,Shares
zero_1,0,0,0,0
"""
    recs = _parse_csv_direct(zero_csv)
    if recs:
        test("Zero views record: engagement_rate = 0.0", recs[0].get("engagement_rate") == 0.0)

    # Test 6.3: Very large numbers
    large_csv = """Post ID,Impressions,Likes,Comments,Shares
big_1,9999999,500000,100000,50000
"""
    recs = _parse_csv_direct(large_csv)
    if recs:
        test("Large numbers parsed correctly", recs[0].get("views") == 9999999)

    # Test 6.4: Classification with zero engagement rate
    from self_learning.classifier import _classify_single
    cls, _ = _classify_single(views=100, engagement_rate=0.0, follower_count=500, niche_baseline=0.05)
    test("Zero engagement rate classified as bad", cls == "bad")

    # Test 6.5: main.py fallback when learning_config.json missing
    from self_learning.learning_engine import load_learning_config
    cfg = load_learning_config("/tmp/definitely_not_exists.json")
    test("Fallback config has content_type_weights", "content_type_weights" in cfg)
    test("  → fallback weights sum to 1.0",
         abs(sum(cfg.get("content_type_weights", {}).values()) - 1.0) < 0.01)


# ══════════════════════════════════════════════
# TEST SUITE 7: MAIN.PY INTEGRATION (STATIC ANALYSIS)
# ══════════════════════════════════════════════

def test_main_integration():
    print("\n[SUITE 7] main.py Integration (Static Analysis)")

    with open("main.py") as f:
        content = f.read()

    test("main.py imports run_self_learning via lazy import",
         "from self_learning import run_self_learning" in content)
    test("main.py calls load_and_apply_learning_config()",
         "load_and_apply_learning_config()" in content)
    test("main.py calls process_telegram_csv()",
         "process_telegram_csv()" in content)
    test("main.py has LEARNING_CONFIG_FILE constant",
         "LEARNING_CONFIG_FILE" in content)

    # Check format_caption uses hook and cta
    test("build_caption gets hook from config",
         "get_hook" in content or "HOOK_TEMPLATES" in content)
    test("build_caption gets cta from config",
         "get_cta" in content or "CTA_POOL" in content)


# ══════════════════════════════════════════════
# RUN ALL TESTS
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("QA TEST: Self-Learning Module")
    print("=" * 60)

    check("Suite 1: CSV Parser", test_csv_parser)
    check("Suite 2: Analytics Store", test_analytics_store)
    check("Suite 3: Classifier", test_classifier)
    check("Suite 4: Learning Engine", test_learning_engine)
    check("Suite 5: Full Pipeline Integration", test_full_pipeline)
    check("Suite 6: Edge Cases", test_edge_cases)
    check("Suite 7: main.py Integration", test_main_integration)

    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} passed, {FAIL} failed, {ERROR} errors")
    print("=" * 60)

    if FAIL > 0 or ERROR > 0:
        sys.exit(1)
