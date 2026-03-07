---
name: batch-retry-errors-checkpoint-reset
description: >
  Fix --retry-errors in batch mode to detect and reset failed/rate-limited runs inside
  checkpoints of tests that are marked 'success' at the batch level. Use when batch
  reruns silently skip tests with internal checkpoint failures, or when rate_limited
  runs are not being retried.
category: testing
date: 2026-03-06
user-invocable: false
tags:
  - batch-mode
  - retry-errors
  - checkpoint
  - run-states
  - rate-limited
  - manage-experiment
---

# Skill: batch-retry-errors-checkpoint-reset

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-06 |
| Project | ProjectScylla |
| Objective | Make `--retry-errors` in batch mode also retry failed/rate-limited runs inside checkpoints of batch-success tests |
| Outcome | 3 new batch tests + 2 updated single-mode tests; PR #1451 merged |
| PR | HomericIntelligence/ProjectScylla#1451 |

## When to Use

Use this skill when:
- Batch `--retry-errors` skips tests marked `success` in `batch_summary.json` even though their checkpoints contain `failed` or `rate_limited` runs
- Single-mode `--retry-errors` is not retrying `rate_limited` runs (only `failed`)
- Extending a batch CLI wrapper to apply the same checkpoint-level reset logic that single mode uses
- Writing tests for batch-skip logic that requires checkpoint state on disk to be verified (not just mock call assertions)

**Trigger symptoms**:
```
test-001 status=success in batch_summary.json
  T5/02/1 = failed   ← silently skipped by old --retry-errors
  T6/01/1 = failed   ← silently skipped by old --retry-errors
```

## Root Cause: Two-Level Success/Failure

Batch mode has two independent success signals:
1. **`batch_summary.json` status** — did `run_experiment()` return truthy? (`"success"` / `"error"`)
2. **Checkpoint `run_states`** — did individual runs within the experiment complete?

A test can be `status=success` at level 1 (partial-failure semantics: experiment ran to completion) while having `failed` or `rate_limited` runs at level 2. Old `--retry-errors` only checked level 1.

Additionally, `reset_runs_for_from_state(status_filter=["failed"])` checked `completed_runs` (not `run_states`). `rate_limited` runs are NOT recorded in `completed_runs`, so they were silently skipped.

## Verified Workflow

### Step 1: Add `_checkpoint_has_retryable_runs()` helper

Fast JSON scan — does NOT load the full `E2ECheckpoint` model:

```python
def _checkpoint_has_retryable_runs(checkpoint_path: Path) -> bool:
    """Return True if checkpoint contains failed or rate-limited runs."""
    import json
    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
        for subtests in data.get("run_states", {}).values():
            for runs in subtests.values():
                for state in runs.values():
                    if state in ("failed", "rate_limited"):
                        return True
    except Exception:
        pass
    return False
```

Place after `_find_checkpoint_path()`.

### Step 2: Add `_reset_terminal_runs()` helper

Directly iterates `run_states` (NOT `completed_runs`) so both `failed` and `rate_limited` are caught:

```python
def _reset_terminal_runs(checkpoint: Any) -> int:
    """Reset all failed/rate-limited runs to pending with tier/subtest cascade."""
    terminal_states = ("failed", "rate_limited")
    reset_count = 0
    affected_tiers: set[str] = set()
    affected_subtests: set[tuple[str, str]] = set()

    for tier_id, subtests in checkpoint.run_states.items():
        for subtest_id, runs in subtests.items():
            for run_num_str, state in list(runs.items()):
                if state in terminal_states:
                    runs[run_num_str] = "pending"
                    checkpoint.unmark_run_completed(tier_id, subtest_id, int(run_num_str))
                    affected_tiers.add(tier_id)
                    affected_subtests.add((tier_id, subtest_id))
                    reset_count += 1

    for tier_id, subtest_id in affected_subtests:
        checkpoint.set_subtest_state(tier_id, subtest_id, "pending")
    for tier_id in affected_tiers:
        checkpoint.set_tier_state(tier_id, "pending")
    if affected_tiers:
        checkpoint.experiment_state = "tiers_running"

    return reset_count
```

**Why `list(runs.items())`**: Avoid mutation-during-iteration error.

### Step 3: Patch batch skip logic (`completed_ids` build loop)

```python
for test_id, r in last_by_test.items():
    if args.retry_errors:
        if r.get("status") == "error":
            continue  # Error tests always re-run
        # Success tests: check checkpoint for internal failures
        cp_path = _find_checkpoint_path(args.results_dir, test_id)
        if cp_path is not None and _checkpoint_has_retryable_runs(cp_path):
            continue  # Has failed/rate-limited runs internally
    # ... existing --max-subtests expansion check ...
    completed_ids.add(test_id)
```

**Key**: Refactor inline loop into `last_by_test` dict first (last-entry-per-test semantics), then iterate. Type annotation: `dict[str, dict[str, Any]]`.

### Step 4: Add reset in `run_one_test()` before `run_experiment()`

```python
# Handle --retry-errors: reset failed/rate-limited runs in checkpoint
if args.retry_errors:
    from scylla.e2e.checkpoint import load_checkpoint as _load_cp, save_checkpoint as _save_cp
    _cp_path = _find_checkpoint_path(args.results_dir, experiment_id)
    if _cp_path is not None:
        _cp = _load_cp(_cp_path)
        _reset_count = _reset_terminal_runs(_cp)
        if _reset_count > 0:
            _save_cp(_cp, _cp_path)
            logger.info(f"[{test_id}] --retry-errors: reset {_reset_count} failed/rate-limited run(s)")
```

**Thread safety**: Each test has its own unique `experiment_id` → unique checkpoint file → no cross-test contention in `ThreadPoolExecutor`.

### Step 5: Replace single-mode `--retry-errors` to use `_reset_terminal_runs()`

Old code used `reset_runs_for_from_state(status_filter=["failed"])` which missed `rate_limited`. Replace with:

```python
if args.retry_errors and not (from_run_state or from_tier_state or from_experiment_state):
    from scylla.e2e.checkpoint import load_checkpoint, save_checkpoint
    checkpoint_path = _find_checkpoint_path(args.results_dir, experiment_id)
    if checkpoint_path is not None:
        checkpoint = load_checkpoint(checkpoint_path)
        reset_count = _reset_terminal_runs(checkpoint)
        if reset_count > 0:
            save_checkpoint(checkpoint, checkpoint_path)
            logger.info(f"--retry-errors: reset {reset_count} failed/rate-limited run(s) for retry")
```

## Failed Attempts

| Attempt | What Happened | Fix |
|---------|---------------|-----|
| Used `reset_runs_for_from_state(status_filter=["failed"])` for both modes | Misses `rate_limited` runs — they aren't recorded in `completed_runs` so `get_run_status()` returns `None` | Switch to direct `run_states` iteration via `_reset_terminal_runs()` |
| Test A and B used single `--config` arg | Single config with no `test-*` subdirs triggers single-test mode, not batch mode — `completed_ids` skip logic never runs | Use two `--config` args (`test-001` + `test-002`) to force batch mode dispatch (`len(configs) > 1`) |
| Updated single-mode tests still patched `reset_runs_for_from_state` | After replacing implementation, mock was never called → `assert len(reset_calls) == 1` failed | Drop mock; instead call `load_checkpoint()` after `cmd_run()` and assert `run_states` directly on disk |
| Annotated `_reset_terminal_runs` with `"E2ECheckpoint"` string forward reference | Mypy error: `Missing type parameters for generic type "dict"` at nearby line | Use `Any` type annotation — checkpoint is duck-typed and `Any` is already imported |
| `dict[str, dict]` annotation for `last_by_test` | Mypy: `Missing type parameters for generic type "dict"` | Use `dict[str, dict[str, Any]]` |

## Batch Mode Dispatch Decision Tree

```
cmd_run(args)
├── len(configs) == 1 and configs[0].is_dir():
│   ├── has test-* subdirs → _run_batch(test_dirs, args)  ← batch
│   └── no test-* subdirs → single-test path              ← NOT batch
└── len(configs) > 1 → _run_batch(configs, args)          ← batch
```

**Test implication**: To test batch-mode skip logic, always supply 2+ `--config` args.

## Test Patterns

### Testing batch skip logic (requires 2 configs + checkpoint on disk)

```python
summary = {"results": [{"test_id": "test-001", "status": "success"},
                        {"test_id": "test-002", "status": "success"}]}
(results_dir / "batch_summary.json").write_text(json.dumps(summary))

# test-001: checkpoint with internal failure
exp_dir = results_dir / "2024-01-01T00-00-00-test-001"
exp_dir.mkdir(parents=True)
checkpoint = E2ECheckpoint(..., run_states={"T1": {"01": {"1": "failed"}}}, ...)
save_checkpoint(checkpoint, exp_dir / "checkpoint.json")

args = parser.parse_args(["run", "--config", str(test001), "--config", str(test002),
                          "--retry-errors", "--results-dir", str(results_dir), ...])
# Assert test-001 re-runs, test-002 skipped
```

### Testing `_reset_terminal_runs()` directly

```python
from manage_experiment import _reset_terminal_runs
from scylla.e2e.checkpoint import E2ECheckpoint

checkpoint = E2ECheckpoint(..., run_states={
    "T0": {"00": {"1": "failed", "2": "worktree_cleaned"}},
    "T1": {"01": {"1": "rate_limited"}},
}, completed_runs={})

reset_count = _reset_terminal_runs(checkpoint)

assert reset_count == 2
assert checkpoint.run_states["T0"]["00"]["1"] == "pending"
assert checkpoint.run_states["T1"]["01"]["1"] == "pending"
assert checkpoint.run_states["T0"]["00"]["2"] == "worktree_cleaned"  # untouched
assert checkpoint.get_subtest_state("T0", "00") == "pending"
assert checkpoint.get_tier_state("T1") == "pending"
assert checkpoint.experiment_state == "tiers_running"
```

### Testing single-mode reset (verify disk, not mock)

```python
# After cmd_run(), load checkpoint from disk and assert run_states directly
saved = load_checkpoint(checkpoint_path)
assert saved.run_states["T0"]["00"]["1"] == "pending"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1451 — batch retry-errors per-run checkpoint reset | [notes.md](references/notes.md) |
