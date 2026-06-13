---
name: automation-loop-post-loop-filter-omission
description: "Use when: (1) diagnosing why loops_run reports an inflated loop count after early-exit fires, (2) a caller re-aggregates a raw result list without applying the same filter the inner function already uses, (3) auditing max()/sum() aggregations over mixed per-loop + post-loop result collections."
category: debugging
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [automation, loop-runner, post-loop, filter-omission, early-exit, aggregation, loops-run]
---

# Automation Loop: Post-Loop Filter Omission Bug

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Fix `loops_run` reporting an inflated count when early-exit fires during a multi-loop run that includes post-loop stages |
| **Outcome** | Plan produced, not yet implemented or CI-confirmed |
| **Verification** | unverified |
| **Source** | ProjectHephaestus issue #1153 |
| **History** | N/A (initial version) |

## When to Use

- `loops_run` (or equivalent) reports a count equal to the configured maximum instead of the actual number of loops executed
- Early-exit fired on loop N < max, yet the loop count metric shows max
- A caller aggregates a flat result list that mixes per-loop `RepoResult` records with post-loop `RepoResult` records
- Reviewing any `max(r.field for r in results)` expression over a result list produced by a loop runner that also runs post-loop stages

## Bug Description

In `hephaestus/automation/loop_runner.py:1695`:

```python
loops_run = max((r.loop_idx for r in results), default=0)
```

`_run_post_loop_stages` appends `RepoResult` records to the same `results` list and **unconditionally sets `loop_idx=cfg.loops`** on each record. When early-exit fires on loop 1 of 5 and the drive-green post-loop stage runs, `loops_run` aggregates over all records including the post-loop ones and reports `5` instead of `1`.

The inner function `run_loop` itself already applies the correct filter at `loop_runner.py:1337`:

```python
loop_results = [r for r in all_results if not r.post_loop_phases]
```

The caller (`main`) re-aggregates the same raw `results` list without applying that filter.

## Root Cause Pattern

An internal function correctly filters its result set before aggregating; the caller re-aggregates the same raw list without applying the same filter. The discriminator field `post_loop_phases` was explicitly designed for this purpose — the comment at lines 230–232 calls out this exact use case.

**General pattern to watch for**: When you see `max(x.field for x in collection)` in a caller function, check whether the inner function that produced `collection` applied a filter before its own equivalent aggregation. If so, the caller must apply the same filter.

## Fix

Add the `if not r.post_loop_phases` predicate to mirror the filter already present inside `run_loop`:

```python
# Before (line 1695):
loops_run = max((r.loop_idx for r in results), default=0)

# After:
loops_run = max(
    (r.loop_idx for r in results if not r.post_loop_phases),
    default=0,
)
```

This mirrors the identical filter at `loop_runner.py:1337`.

## Key Risks

1. **Empty `post_loop_phases` list** — If `_run_post_loop_stages` ever produces a record with `post_loop_phases=[]` (e.g., all stages skipped), the new filter misclassifies it as a per-loop record. The discriminator relies on list **non-emptiness**, not a dedicated boolean flag. Verify that `_run_post_loop_stages` always appends at least one entry to `post_loop_phases` before returning.

2. **`failures` aggregation is unaffected** — `failures = [r for r in results if r.any_failure]` at line 1697 iterates over ALL records including post-loop. This is **correct behavior** — post-loop stage failures must be counted. The fix only touches `loops_run`.

## Existing Test Blind Spot

`test_main_loops_run_early_exit` stubs `run_loop` with a clean per-loop-only result list, so it never exercises the mixed case where post-loop records are present. A new test covering the mixed case is required.

### Minimal Test

```python
def test_loops_run_excludes_post_loop_records(tmp_path, monkeypatch):
    """loops_run must not count post-loop RepoResult records."""
    from hephaestus.automation.loop_runner import LoopConfig, RepoResult

    cfg = LoopConfig(loops=5, projects_dir=tmp_path)

    # Simulate: early-exit fired after loop 1, then post-loop ran
    per_loop_record = RepoResult(repo="r1", loop_idx=1)
    post_loop_record = RepoResult(repo="r1", loop_idx=cfg.loops)
    post_loop_record.post_loop_phases.append("drive-green")

    results = [per_loop_record, post_loop_record]

    loops_run = max(
        (r.loop_idx for r in results if not r.post_loop_phases),
        default=0,
    )
    assert loops_run == 1, f"Expected 1, got {loops_run}"
```

## Verified Workflow

### Quick Reference

```bash
# Confirm the unfiltered aggregation exists:
grep -n "loops_run" hephaestus/automation/loop_runner.py

# Confirm the inner filter for comparison:
grep -n "post_loop_phases" hephaestus/automation/loop_runner.py | head -20
```

### Detailed Steps

1. **Locate the aggregation** — Find `loops_run = max(...)` at `loop_runner.py:1695` in the `main()` function.

2. **Compare to inner filter** — The `run_loop` function at `loop_runner.py:1337` already filters: `loop_results = [r for r in all_results if not r.post_loop_phases]`. The caller must mirror this.

3. **Apply the fix** — Add `if not r.post_loop_phases` to the generator expression inside `max(...)`.

4. **Verify `_run_post_loop_stages`** — Confirm it always appends at least one entry to `post_loop_phases`. If it can produce records with `post_loop_phases=[]`, introduce a dedicated boolean flag instead.

5. **Add the mixed-case test** — `test_main_loops_run_early_exit` must cover the scenario where post-loop records are present alongside per-loop records.

6. **Run checks**:
   ```bash
   pixi run pytest tests/unit/automation/ -q --no-cov
   pixi run ruff check hephaestus/automation/loop_runner.py
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| (None yet — plan only) | This skill documents a planned fix; the section will be populated once implementation is attempted | N/A | N/A |

## Results & Parameters

### Key Behavioral Invariants

| Scenario | `loops_run` before fix | `loops_run` after fix |
|----------|----------------------|-----------------------|
| Early-exit on loop 1/5, post-loop ran | `5` (incorrect) | `1` (correct) |
| No early-exit, all 5 loops ran, post-loop ran | `5` (correct) | `5` (correct) |
| No post-loop stages | `N` (correct) | `N` (correct) |

### Discriminator Field

| Field | Type | Semantics |
|-------|------|-----------|
| `post_loop_phases` | `list[str]` | Non-empty → record is a post-loop record; empty → per-loop record |

### Net Change (Planned)

- `hephaestus/automation/loop_runner.py`: ~3 LOC (add `if not r.post_loop_phases` predicate to `loops_run` generator)
- `tests/unit/automation/test_loop_runner_early_exit.py` (or equivalent): +1 new test method for mixed per-loop + post-loop results

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1153 — loops_run inflated after early-exit + post-loop stages | Plan only; not yet implemented or CI-confirmed |
