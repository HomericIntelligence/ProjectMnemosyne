# Session Notes: auto-discover-parametrize-fixtures

## Session Date
2026-03-06

## Issue
HomericIntelligence/ProjectScylla#1433 — Auto-discover tier fixtures in parametrize instead of hardcoding list

## Problem
`tests/unit/config/test_json_schemas.py:154` hardcoded `["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"]` in a parametrize decorator. Adding a new tier config fixture required a manual code update.

## Fix
Replace the list with `sorted(TIER_FIXTURES_DIR.glob("t*.yaml"))`.

## File Changed
`tests/unit/config/test_json_schemas.py` — `TestTierSchema.test_real_tier_fixture_is_valid`

## Diff Summary
```diff
-    ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"],
+    sorted(TIER_FIXTURES_DIR.glob("t*.yaml")),
+    ids=lambda p: p.name,
 )
-def test_real_tier_fixture_is_valid(self, schema: dict[str, Any], fixture_file: str) -> None:
-    data = load_yaml(TIER_FIXTURES_DIR / fixture_file)
+def test_real_tier_fixture_is_valid(self, schema: dict[str, Any], fixture_file: Path) -> None:
+    data = load_yaml(fixture_file)
```

## Test Results
- 43 tests in `test_json_schemas.py` pass
- Full suite: 4563 passed, 1 skipped (131s)
- Coverage: 75.85% (threshold 9% combined, 75% unit)
- Pre-commit: all hooks pass

## PR
HomericIntelligence/ProjectScylla#1458