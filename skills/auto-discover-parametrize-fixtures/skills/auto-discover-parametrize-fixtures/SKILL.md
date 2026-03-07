---
name: auto-discover-parametrize-fixtures
description: "TRIGGER CONDITIONS: A pytest.mark.parametrize list hardcodes fixture filenames that must be manually updated when new fixtures are added. Use when replacing a hardcoded list with glob-based auto-discovery so new fixtures are picked up automatically."
user-invocable: false
category: testing
date: 2026-03-06
---

# auto-discover-parametrize-fixtures

Replace a hardcoded `pytest.mark.parametrize` filename list with glob-based auto-discovery so new fixture files are picked up automatically without code changes.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-06 |
| Objective | Replace `["t0.yaml", ..., "t6.yaml"]` hardcoded list with `TIER_FIXTURES_DIR.glob("t*.yaml")` |
| Outcome | Success — 43 tests pass; new tier fixtures auto-discovered at collection time |
| Issue | HomericIntelligence/ProjectScylla#1433 |
| PR | HomericIntelligence/ProjectScylla#1458 |

## When to Use

- A `pytest.mark.parametrize` list enumerates fixture filenames by hand
- The test should run against all files matching a pattern in a known directory
- New fixture files may be added in the future and the test should cover them without code changes
- The fixture files follow a naming convention (e.g. `t*.yaml`, `case_*.json`, `*.toml`)

## Verified Workflow

### Before (hardcoded list)

```python
TIER_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config" / "tiers"

@pytest.mark.parametrize(
    "fixture_file",
    ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"],
)
def test_real_tier_fixture_is_valid(self, schema: dict[str, Any], fixture_file: str) -> None:
    data = load_yaml(TIER_FIXTURES_DIR / fixture_file)
    check_schema(data, schema)
```

### After (auto-discovery)

```python
from pathlib import Path

TIER_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config" / "tiers"

@pytest.mark.parametrize(
    "fixture_file",
    sorted(TIER_FIXTURES_DIR.glob("t*.yaml")),
    ids=lambda p: p.name,
)
def test_real_tier_fixture_is_valid(self, schema: dict[str, Any], fixture_file: Path) -> None:
    data = load_yaml(fixture_file)
    check_schema(data, schema)
```

### Key changes

1. **Parameter type**: `str` → `Path` (pass full paths from glob, no joining needed)
2. **`sorted()`**: stabilizes test order across platforms (glob order is not guaranteed)
3. **`ids=lambda p: p.name`**: keeps test IDs readable (`t0.yaml`, `t1.yaml`) instead of showing full paths
4. **No path joining**: `load_yaml(fixture_file)` directly — no `TIER_FIXTURES_DIR / fixture_file`

### Why `sorted()` matters

`Path.glob()` order is filesystem-dependent. Without `sorted()`, test order may differ between Linux and macOS or between CI runs, making failures hard to reproduce. Always wrap glob results in `sorted()` for parametrize.

### Why `ids=` matters

Without `ids=`, pytest uses the full absolute path as the test ID, making output hard to read:

```
FAILED tests/unit/config/test_json_schemas.py::TestTierSchema::test_real_tier_fixture_is_valid[/home/user/project/tests/fixtures/config/tiers/t0.yaml]
```

With `ids=lambda p: p.name`:

```
FAILED tests/unit/config/test_json_schemas.py::TestTierSchema::test_real_tier_fixture_is_valid[t0.yaml]
```

## Results & Parameters

- **Pattern**: `sorted(FIXTURES_DIR.glob("<pattern>"))`
- **IDs**: `ids=lambda p: p.name`
- **Type hint**: `fixture_file: Path`
- **Test count before**: 7 parametrized cases (hardcoded)
- **Test count after**: 7 parametrized cases (auto-discovered, same fixtures)
- **All 43 tests pass**; pre-commit hooks pass

## Failed Attempts

None — the change was straightforward. The only non-obvious aspect is remembering to:
- Change the parameter type from `str` to `Path`
- Remove the path join (`FIXTURES_DIR / fixture_file`) since glob already returns full paths
- Add `ids=` to keep readable test output
