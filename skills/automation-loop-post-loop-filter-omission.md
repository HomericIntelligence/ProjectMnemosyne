---
name: automation-loop-post-loop-filter-omission
description: "Use when: (1) diagnosing why loops_run reports an inflated loop count after early-exit fires, (2) a caller re-aggregates a raw result list without applying the same filter the inner function already uses, (3) auditing max()/sum() aggregations over mixed per-loop + post-loop result collections."
category: debugging
date: 2026-06-13
version: "1.2.0"
user-invocable: false
verification: verified-ci
history: automation-loop-post-loop-filter-omission.history
tags: [automation, loop-runner, post-loop, filter-omission, early-exit, aggregation, loops-run]
---

# Automation Loop: Post-Loop Filter Omission Bug

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix `loops_run` reporting an inflated count when early-exit fires during a multi-loop run that includes post-loop stages |
| **Outcome** | Successful — one-word inline fix + regression test; PR #1278 merged green |
| **Verification** | verified-ci — ProjectHephaestus PR #1278, all CI gates passed |
| **Source** | ProjectHephaestus issue #1153 |
| **History** | automation-loop-post-loop-filter-omission.history |

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

The inner function `run_loop` itself already applies the correct filter at `loop_runner.py:1525`:

```python
per_loop_results = [r for r in all_results if not r.is_post_loop]
```

The caller (`main`) re-aggregates the same raw `results` list without applying that filter.

## Root Cause Pattern

An internal function correctly filters its result set before aggregating; the caller re-aggregates the same raw list without applying the same filter. The dedicated boolean `is_post_loop: bool = False` (defined at `loop_runner.py:234`) was introduced precisely for this purpose — the dataclass comment at lines 231–233 explains that `post_loop_phases=[]` cannot distinguish post-loop records from crashed or all-skipped per-loop records.

**General pattern to watch for**: When you see `max(x.field for x in collection)` in a caller function, check whether the inner function that produced `collection` applied a filter before its own equivalent aggregation. If so, the caller must apply the same filter using the same discriminator.

## Fix

Add the `if not r.is_post_loop` predicate to mirror the filter already present inside `run_loop`:

```python
# Before (line 1695):
loops_run = max((r.loop_idx for r in results), default=0)

# After:
loops_run = max(
    (r.loop_idx for r in results if not r.is_post_loop),
    default=0,
)
```

This mirrors the canonical filter at `loop_runner.py:1525`. The fix is a **one-word inline change** — adding `if not r.is_post_loop` to the existing generator expression.

## Key Risks

1. **`is_post_loop` is the correct discriminator** — `is_post_loop: bool = False` is defined at `loop_runner.py:234` and set unconditionally to `True` at `loop_runner.py:1395` when `_run_post_loop_stages` constructs a record. Do NOT use `post_loop_phases` non-emptiness as the discriminator — that field is empty for crashed or all-skipped repos, making it ambiguous (see Failed Attempts).

2. **`failures` aggregation is unaffected** — `failures = [r for r in results if r.any_failure]` at line 1697 iterates over ALL records including post-loop. This is **correct behavior** — post-loop stage failures must be counted. The fix only touches `loops_run`.

## Verified Workflow

### Quick Reference

```bash
# Confirm the unfiltered aggregation exists:
grep -n "loops_run" hephaestus/automation/loop_runner.py

# Confirm is_post_loop definition and set site:
grep -n "is_post_loop" hephaestus/automation/loop_runner.py | head -20
# Expect: :234 definition, :1395 set site, :1525 canonical filter
```

### Detailed Steps

1. **Locate the aggregation** — Find `loops_run = max(...)` at `loop_runner.py:1695` in the `main()` function.

2. **Compare to inner filter** — The `run_loop` function at `loop_runner.py:1525` already filters: `per_loop_results = [r for r in all_results if not r.is_post_loop]`. The caller must mirror this using the same boolean flag.

3. **Verify all cited line numbers on disk** — Issue bodies and planning docs are written against a snapshot that may be many commits stale. Always `grep -n` before trusting any `:N` citation. In issue #1153, the body cited `:1337` (a rate-budget sleep, unrelated) and `:1501` as the fix target; the correct post-#818 lines are `:1525` (canonical filter) and `:1695` (fix target).

4. **Apply the fix** — Add `if not r.is_post_loop` to the generator expression inside `max(...)`. Do NOT use `if not r.post_loop_phases` — see Failed Attempts.

5. **Add the mixed-case regression test** — Use `TestMainLoopsRunReporting._run_main_with_results` (`:666`) as the helper pattern for `main()`-layer behavior tests. This helper stubs `run_loop` directly (not `process_repo`) and patches `emit_json_status` to capture kwargs. The post-loop fixture must include BOTH `is_post_loop=True` AND `post_loop_phases=[...]` — setting only one is insufficient.

6. **Run checks**:
   ```bash
   pixi run pytest tests/unit/automation/ -q --no-cov
   pixi run ruff check hephaestus/automation/loop_runner.py
   ```

### Regression Test Pattern

```python
def test_loops_run_excludes_post_loop_records(tmp_path, monkeypatch):
    """loops_run must not count post-loop RepoResult records."""
    from hephaestus.automation.loop_runner import LoopConfig, PhaseResult, RepoResult

    cfg = LoopConfig(loops=5, projects_dir=tmp_path)

    # Simulate: early-exit fired after loop 1, then post-loop ran.
    # is_post_loop=True is REQUIRED — post_loop_phases alone is ambiguous
    # for crashed/all-skipped repos where post_loop_phases=[] too.
    # BOTH fields must be set on the fixture for correct classification.
    per_loop_record = RepoResult(repo="r1", loop_idx=1)
    post_loop_record = RepoResult(
        repo="r1",
        loop_idx=cfg.loops,
        is_post_loop=True,                                    # required boolean
        post_loop_phases=[PhaseResult(phase="drive-green")],  # also required
    )

    results = [per_loop_record, post_loop_record]

    loops_run = max(
        (r.loop_idx for r in results if not r.is_post_loop),
        default=0,
    )
    assert loops_run == 1, f"Expected 1, got {loops_run}"
```

**Note**: For `main()`-layer behavior tests that exercise the full reporting path, use `TestMainLoopsRunReporting._run_main_with_results` (`:666`) which stubs `run_loop` directly and patches `emit_json_status`. This is distinct from `run_loop` behavior tests which patch `process_repo`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| v1.0.0 planning pass | Used `not r.post_loop_phases` as the discriminator, claiming it "mirrored `loop_runner.py:1337`" (a rate-budget sleep — unrelated line). Fix was `if not r.post_loop_phases` in the generator. | (1) `post_loop_phases=[]` is ambiguous — crashed and all-skipped repos produce per-loop records with empty `post_loop_phases`, so the filter would misclassify them as post-loop. (2) The cited line 1337 was wrong; the real filter is at 1525. (3) The regression test fixture only set `post_loop_phases=[...]` without `is_post_loop=True`, so it would not guard the real bug under the correct fix. The reviewer caught all three issues. | Always use the dedicated `is_post_loop` boolean. Never rely on list-emptiness when a boolean flag exists for the same purpose. Verify cited line numbers before documenting. |
| `post_loop_phases` emptiness as discriminator | Used `not r.post_loop_phases` to detect post-loop records in `main()` | A crashed/uncloned repo leaves BOTH phase lists empty — emptiness cannot distinguish post-loop from per-loop records | Use `is_post_loop=True` (the dedicated boolean flag defined at `:234`, set at `:1395`) |
| Stale issue-body line citations | Trusted `:1337` (filter) and `:1501` (fix target) from the issue description | Issue body was written against pre-#818 code; post-#818 correct lines are `:1525` (canonical filter in `run_loop`) and `:1695` (fix target in `main()`) | Verify all `file:line` citations on disk with `grep -n` before acting |
| Regression fixture with only `post_loop_phases` set | Constructed post-loop fixture with `post_loop_phases=[...]` but without `is_post_loop=True` | The fixture was not classified as post-loop under the correct predicate (`not r.is_post_loop`), so the test did not guard the actual bug | Post-loop regression fixture needs BOTH `is_post_loop=True` AND `post_loop_phases=[...]` |

## Results & Parameters

### Key Behavioral Invariants

| Scenario | `loops_run` before fix | `loops_run` after fix |
|----------|----------------------|-----------------------|
| Early-exit on loop 1/5, post-loop ran | `5` (incorrect) | `1` (correct) |
| No early-exit, all 5 loops ran, post-loop ran | `5` (correct) | `5` (correct) |
| No post-loop stages | `N` (correct) | `N` (correct) |

### Discriminator Fields

| Field | Type | Semantics |
|-------|------|-----------|
| `is_post_loop` | `bool` | **Correct discriminator.** `True` iff this record was produced by `_run_post_loop_stages`. Defined at `loop_runner.py:234`, set at `loop_runner.py:1395`. |
| `post_loop_phases` | `list` | **Wrong discriminator.** Non-empty only when stages ran — ambiguous for crashed/all-skipped records that also have `post_loop_phases=[]`. |

### Key Line References (post-#818)

| Line | Symbol | Role |
|------|--------|------|
| `:234` | `is_post_loop: bool = False` | Dataclass field definition |
| `:1395` | `result.is_post_loop = True` | Set site in `_run_post_loop_stages` |
| `:1525` | `per_loop_results = [r for r in all_results if not r.is_post_loop]` | Canonical filter inside `run_loop` |
| `:1695` | `loops_run = max(...)` | Fix target in `main()` |
| `:666` | `TestMainLoopsRunReporting._run_main_with_results` | Helper for `main()`-layer behavior tests |

### Net Change

- `hephaestus/automation/loop_runner.py`: 3 LOC (add `if not r.is_post_loop` to `loops_run` generator in `main()`)
- `tests/unit/automation/test_loop_runner_early_exit.py` (or equivalent): +1 new test method for mixed per-loop + post-loop results (fixture must include BOTH `is_post_loop=True` AND `post_loop_phases=[...]`)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1153 — loops_run inflated after early-exit + post-loop stages | PR #1278 merged; all CI gates passed (verified-ci) |
