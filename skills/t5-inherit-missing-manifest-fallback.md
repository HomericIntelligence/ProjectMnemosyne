---
name: t5-inherit-missing-manifest-fallback
description: "Skill: T5 Inheritance Fallback for Missing config_manifest.json"
category: uncategorized
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: T5 Inheritance Fallback for Missing config_manifest.json

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-05 |
| Project | ProjectScylla |
| Objective | Fix T5 crash when parent tier's best subtest has no `config_manifest.json` |
| Outcome | Success — PR #1426 merged, 4437 tests pass, 75.26% unit coverage |
| PR | HomericIntelligence/ProjectScylla#1426 |

## When to Use

Use this skill when:
- `build_merged_baseline()` raises `ValueError: Cannot inherit from <tier>/<subtest>: config_manifest.json not found`
- A T5 run with `--retry-errors` crashes on inheritance from a tier where all subtests scored 0.0
- Diagnosing failures where tiebreaker selection picks a subtest whose runs failed early (before manifest was written)

## Root Cause

`build_merged_baseline()` in `scylla/e2e/tier_manager.py` assumed the best subtest always had `config_manifest.json`. When all subtests score 0.0, the tiebreaker (alphabetical) picks the first subtest. If that subtest's run failed before `_save_resource_manifest()` executed, no manifest exists — and the old code raised `ValueError` unconditionally.

## Verified Workflow

### Fix in `build_merged_baseline()` (~line 738)

Replace the hard `raise ValueError` with a two-stage fallback:

```python
manifest_file = (
    experiment_dir / tier_id.value / best_subtest_id / "config_manifest.json"
)
if not manifest_file.exists():
    # Best subtest failed before manifest was written — find an alternative
    tier_dir = experiment_dir / tier_id.value
    alternative = None
    for subdir in sorted(tier_dir.iterdir()):
        candidate = subdir / "config_manifest.json"
        if subdir.is_dir() and candidate.exists():
            alternative = candidate
            logger.warning(
                f"Best subtest {tier_id.value}/{best_subtest_id} has no "
                f"config_manifest.json; falling back to "
                f"{tier_id.value}/{subdir.name}"
            )
            break
    if alternative is None:
        logger.warning(
            f"No subtest in {tier_id.value} has config_manifest.json; "
            f"skipping inheritance from {tier_id.value}"
        )
        continue
    manifest_file = alternative
```

### Logger Setup

`tier_manager.py` had no logger. Add at module level:

```python
import logging
# ... other imports ...
logger = logging.getLogger(__name__)
```

### Unit Tests

Add to `tests/unit/e2e/test_tier_manager.py` in `TestBuildMergedBaseline`:

1. **Fallback to sibling** — `best_subtest.json` points to `02` (no manifest); `00` has one → merged from `00`
2. **Skip entire tier** — no subtest has a manifest → returns `{}`
3. **Skip only failing tier** — T1 has no manifests, T0 does → T0 resources present, T1 skipped

## Key Implementation Details

- `sorted(tier_dir.iterdir())` ensures deterministic fallback (lowest-numbered subtest wins)
- Use `continue` (not `return`) so other tiers in `inherit_from_tiers` still contribute
- The fallback is silent from the caller's perspective — only warnings logged, no exception

## Failed Attempts

None in this session — the plan was clear from diagnosis. The only gotcha was that `tier_manager.py` lacked `import logging` / `logger`, requiring both to be added before the fix compiled.

## Parameters

| Item | Value |
|------|-------|
| File modified | `scylla/e2e/tier_manager.py` — `build_merged_baseline()` |
| Test file | `tests/unit/e2e/test_tier_manager.py` — `TestBuildMergedBaseline` |
| New tests | 4 (3 fallback scenarios + pre-existing passing tests) |
| Total tests | 4437 passed, 1 skipped |
| Unit coverage | 75.26% |
