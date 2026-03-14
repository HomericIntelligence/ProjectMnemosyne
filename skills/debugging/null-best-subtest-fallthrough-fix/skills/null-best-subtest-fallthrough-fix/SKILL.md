---
name: null-best-subtest-fallthrough-fix
description: "Fix pattern for elif→if fallthrough when a primary JSON file exists with a null key, silently preventing fallback to a secondary file. Use when: T5 subtests fail with 'all required tiers failed' despite tiers completing, or any if/elif chain where primary file exists but has empty/null data."
category: debugging
date: 2026-03-13
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `elif` fallback unreachable when primary file exists but has null/empty key |
| **Symptom** | `Cannot build merged baseline: all required tiers failed (T1)` despite T1 complete |
| **Root Cause** | `if result.exists(): ... elif fallback.exists():` — elif never fires if primary exists |
| **Fix** | Change `elif` to second `if not best_subtest_id` check |
| **File** | `scylla/e2e/tier_manager.py:build_merged_baseline()` |
| **PR** | #1476 |

## When to Use

1. T5 subtests fail with `"Cannot build merged baseline: all required tiers failed (TN)"` even though tier TN is shown as complete in the checkpoint
2. A tier's `result.json` was regenerated (e.g. during retry/re-run) with `best_subtest: null`, but `best_subtest.json` still has `winning_subtest` set correctly
3. Any `if file_A.exists(): ... elif file_B.exists():` pattern where file_A can exist with a null/empty value for the needed key

## Verified Workflow

### Quick Reference

```python
# BROKEN — elif never fires when result.json exists but best_subtest is null
if result_file.exists():
    tier_result = json.load(f)
    best_subtest_id = tier_result.get("best_subtest")  # returns None
elif best_subtest_file.exists():   # ← NEVER REACHED
    selection = json.load(f)
    best_subtest_id = selection.get("winning_subtest")

# FIXED — second if fires whenever best_subtest_id is still None
if result_file.exists():
    with open(result_file) as f:
        tier_result = json.load(f)
    best_subtest_id = tier_result.get("best_subtest")

if not best_subtest_id and best_subtest_file.exists():
    with open(best_subtest_file) as f:
        selection = json.load(f)
    best_subtest_id = selection.get("winning_subtest")
```

### Step 1: Identify the symptom

Look for log lines like:
```
Cannot build merged baseline: all required tiers failed (T1)
```
even though the checkpoint shows `tier_states.T1 = complete`.

### Step 2: Check the tier's result files

```bash
# Check if result.json has null best_subtest
cat ~/dryrun3/<experiment>/T1/result.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('best_subtest'))"
# → None

# Check if best_subtest.json has the winning subtest
cat ~/dryrun3/<experiment>/T1/best_subtest.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('winning_subtest'))"
# → "00"
```

When `result.json` has `null` but `best_subtest.json` has a valid ID, the `elif` bug is confirmed.

### Step 3: Apply the fix

In `scylla/e2e/tier_manager.py`, `build_merged_baseline()`:

Change the `elif` at the `best_subtest_file` fallback to a second `if` guarded by `if not best_subtest_id`:

```python
best_subtest_id = None
if result_file.exists():
    with open(result_file) as f:
        tier_result = json.load(f)
    best_subtest_id = tier_result.get("best_subtest")

if not best_subtest_id and best_subtest_file.exists():
    with open(best_subtest_file) as f:
        selection = json.load(f)
    best_subtest_id = selection.get("winning_subtest")
```

### Step 4: Add a unit test

In `tests/unit/e2e/test_tier_manager.py`, add to `TestBuildMergedBaseline`:

```python
def test_fallback_to_best_subtest_json_when_result_json_has_null_best_subtest(
    self, tmp_path: Path
) -> None:
    """Test that build_merged_baseline falls back to best_subtest.json.

    When result.json exists but best_subtest is null (e.g. tier report was
    regenerated with empty data during a re-run).
    """
    import json

    experiment_dir = tmp_path / "experiment"
    t0_dir = experiment_dir / "T0"
    t0_subtest_dir = t0_dir / "subtest-01"
    t0_subtest_dir.mkdir(parents=True)

    # result.json exists but best_subtest is null
    (t0_dir / "result.json").write_text(
        json.dumps({"best_subtest": None, "scores": {}})
    )

    # best_subtest.json has the winning subtest
    (t0_dir / "best_subtest.json").write_text(
        json.dumps({"winning_subtest": "subtest-01", "rationale": "Best pass rate"})
    )

    manifest = {"resources": {"tools": {"enabled": ["bash", "read"]}}}
    (t0_subtest_dir / "config_manifest.json").write_text(json.dumps(manifest))

    tiers_dir = tmp_path / "tiers"
    tiers_dir.mkdir()
    manager = TierManager(tiers_dir)

    merged = manager.build_merged_baseline([TierID.T0], experiment_dir)
    assert set(merged["tools"]["enabled"]) == {"bash", "read"}
```

### Step 5: Run tests and pre-commit

```bash
pixi run pytest tests/unit/e2e/test_tier_manager.py -v -k "merged_baseline or fallback"
pre-commit run --all-files
pixi run pytest tests/unit/ -q
```

### Step 6: Create PR

```bash
git checkout -b fix-t5-merged-baseline-fallthrough
git add scylla/e2e/tier_manager.py tests/unit/e2e/test_tier_manager.py
git commit -m "fix(tier-manager): fall through to best_subtest.json when result.json has null best_subtest"
git push -u origin fix-t5-merged-baseline-fallthrough
gh pr create --title "fix(tier-manager): ..." --body "..."
gh pr merge --auto --rebase <PR_NUMBER>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Looking for retry/counting bugs only | Initially suspected the `--retry-errors` count fix (commit f77126a0) was sufficient | T5 failures were a separate bug in baseline building, not retry counting | Always check whether multiple independent bugs exist for the same symptom |
| Assuming `elif` was intentional | The `elif` looked correct at first glance (fallback when primary is absent) | The fallback must also fire when primary exists but has null/empty key | `elif` is wrong when the condition "primary file exists" is necessary but not sufficient |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Files changed | 2 (`tier_manager.py`, `test_tier_manager.py`) |
| Lines changed | +41, -1 |
| Tests added | 1 (null best_subtest fallthrough) |
| Unit tests passing | 4681 |
| Coverage | 76.58% (unit) |
| PR | #1476 (ProjectScylla) |

### Key File Locations

```
scylla/e2e/tier_manager.py          # build_merged_baseline() ~line 721
tests/unit/e2e/test_tier_manager.py # TestBuildMergedBaseline class
```

### When This Bug Re-triggers

This bug surfaces specifically when:
- A tier completes and writes `best_subtest.json`
- A subsequent re-run/retry regenerates `result.json` for that tier with `best_subtest: null` (empty report)
- T5 then tries to `build_merged_baseline` using that tier's data

The fix is permanent — the second `if` covers both the "no result.json" and "result.json with null" cases.
