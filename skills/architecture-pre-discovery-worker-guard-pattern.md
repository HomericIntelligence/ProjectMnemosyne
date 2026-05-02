---
name: architecture-pre-discovery-worker-guard-pattern
description: "Use when: (1) building parallel workers (ThreadPoolExecutor) that process GitHub issues and need a lookup before doing real work, (2) some subset of items in the work queue may not be actionable (no PR, no matching resource), (3) worker functions receive a resource identifier they need to look up before doing real work, (4) tests for worker methods have stale lookup patches that need updating after adding pre-discovery"
category: architecture
date: 2026-04-24
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: []
---
# Architecture: Pre-Discovery No-PR Worker Guard Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Objective** | Prevent expensive worker slots from being consumed for non-actionable items by pre-discovering resource availability before submitting any workers |
| **Outcome** | Success — 251 unit tests pass, ruff + mypy clean |
| **Verification** | verified-precommit |

## When to Use

Apply this pattern when building parallel worker-based automation (ThreadPoolExecutor) where:

- Workers process GitHub issues/PRs and must look up a resource (e.g., open PR) before doing real work
- Some items in the work queue may not be actionable (no open PR, no matching resource, no relevant state)
- The lookup is cheap (a `gh` CLI call) but the work is expensive (spawning Claude subprocess)
- With N items and M workers, wasted worker slots become a real performance problem (20+ issues, 3 workers = many wasted slots)
- Worker method signature needs to accept a pre-resolved resource identifier, avoiding redundant lookups

**Key triggers:**
- You are writing a worker function that starts with "find the PR for this issue" before doing real work
- Tests for worker methods are patching `_find_pr_for_issue` at the worker level (stale after refactor)
- You see workers that discover "nothing to do" and exit immediately — these are wasted slots

## Verified Workflow

### Quick Reference

```python
# PRE-DISCOVERY PATTERN — correct
def run(self) -> dict[int, WorkerResult]:
    pr_map = self._discover_prs(self.options.issues)  # cheap lookups first
    if not pr_map:
        logger.warning("No open PRs found — nothing to do")
        return {}
    return self._process_all(pr_map)

# Worker receives pr_number directly — no lookup needed inside
def _process_issue(self, issue_number: int, pr_number: int, slot_id: int) -> WorkerResult:
    ...
```

```python
# ANTI-PATTERN — avoid
def _process_issue(self, issue_number: int, slot_id: int) -> WorkerResult:
    pr_number = self._find_pr_for_issue(issue_number)  # lookup INSIDE worker = wasted slot
    if pr_number is None:
        return WorkerResult(success=True)  # wasted worker slot
    ...
```

### Step 1: Add `_discover_prs()` method

Pre-discover all open PRs before submitting any workers. Log skipped issues at INFO level:

```python
def _discover_prs(self, issue_numbers: list[int]) -> dict[int, int]:
    """Pre-discover open PRs for all issues.

    Returns:
        Mapping of issue_number -> pr_number for issues that have an open PR.
        Issues with no open PR are excluded and logged at INFO level.
    """
    pr_map: dict[int, int] = {}
    for issue_num in issue_numbers:
        pr_number = self._find_pr_for_issue(issue_num)
        if pr_number is not None:
            pr_map[issue_num] = pr_number
        else:
            logger.info(f"Issue #{issue_num}: no open PR found, skipping")
    return pr_map
```

### Step 2: Update `run()` to use pre-discovered map

```python
def run(self) -> dict[int, WorkerResult]:
    """Run the phase for all issues."""
    # Pre-discover PRs — only submit workers for issues that have an open PR.
    # This prevents Claude from being launched for issues with no PR at all.
    pr_map = self._discover_prs(self.options.issues)
    if not pr_map:
        logger.warning("No open PRs found for the specified issues — nothing to do")
        return {}

    # Start UI thread, etc.
    try:
        return self._process_all(pr_map)
    finally:
        # cleanup
        ...
```

### Step 3: Update `_process_all()` to pass `pr_number` directly

Workers never call `_find_pr_for_issue` — they receive `pr_number` as a parameter:

```python
def _process_all(self, pr_map: dict[int, int]) -> dict[int, WorkerResult]:
    """Submit workers only for issues with known PRs."""
    with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
        futures: dict[Future, int] = {}
        for idx, (issue_num, pr_num) in enumerate(pr_map.items()):
            slot_id = idx % self.options.max_workers
            # pr_num is passed directly — worker never needs to look it up
            future = executor.submit(self._process_issue, issue_num, pr_num, slot_id)
            futures[future] = issue_num

        results: dict[int, WorkerResult] = {}
        for future in as_completed(futures):
            issue_num = futures[future]
            results[issue_num] = future.result()
    return results
```

### Step 4: Update worker method signature

Add `pr_number` as the second parameter (before `slot_id`):

```python
# OLD — lookup inside worker (anti-pattern)
def _process_issue(self, issue_number: int, slot_id: int) -> WorkerResult:
    pr_number = self._find_pr_for_issue(issue_number)
    if pr_number is None:
        return WorkerResult(success=True)
    ...

# NEW — pr_number provided by caller (pre-discovery pattern)
def _process_issue(self, issue_number: int, pr_number: int, slot_id: int) -> WorkerResult:
    # pr_number is already known — proceed directly to work
    ...
```

### Step 5: Update tests — remove stale patches, update call sites

The method signature change is a **breaking change** for tests. Update all call sites:

```python
# OLD test call (no longer valid):
result = driver._process_issue(123, 0)

# NEW test call:
result = driver._process_issue(123, 456, 0)
```

Remove stale `_find_pr_for_issue` patches from worker-level tests — the method is no longer called inside `_process_issue`:

```python
# STALE — remove this patch from worker-level tests:
with patch.object(driver, "_find_pr_for_issue", return_value=42):  # dead code
    result = driver._process_issue(123, 456, 0)

# CLEAN — no patch needed:
result = driver._process_issue(123, 456, 0)
```

### Step 6: Update "no PR" tests to use `run()` level

Tests for the "no PR found → skip" path must now be tested via `run()`, not inside the worker:

```python
# OLD pattern — no longer works (_find_pr_for_issue not called inside worker):
def test_no_pr_skips(driver):
    with patch.object(driver, "_find_pr_for_issue", return_value=None):
        result = driver._process_issue(123, 0)
    assert result.success is True

# NEW pattern — test via run():
def test_no_pr_skips(driver):
    with patch.object(driver, "_find_pr_for_issue", return_value=None):
        results = driver.run()  # pre-discovery finds nothing
    assert results == {}  # empty dict — no workers submitted
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Lookup inside worker | Original design called `_find_pr_for_issue` inside `_process_issue` | Wasted a worker slot per non-actionable issue; caught in code review | Always pre-discover before submitting workers when the lookup is cheap |
| Forgetting to update test assertions | After adding `pr_number` param, some `assert_called_once_with(42)` asserted old value | Tests failed because PR number was now passed as 456 but asserted as 42 | Update ALL assertions in tests when changing a method signature |
| Leaving stale patches in worker tests | `patch.object(driver, "_find_pr_for_issue", return_value=42)` left in direct worker test | Dead code causing confusion; may hide bugs during future refactors | Remove stale patches immediately when they become unreachable |

## Results & Parameters

### Architecture Diagram

```
run()
  └── _discover_prs(issues)           ← cheap: gh CLI calls only
       ├── issue #1 → PR #101 ✓
       ├── issue #2 → no PR  ✗ (logged + skipped)
       └── issue #3 → PR #305 ✓
  └── _process_all({1: 101, 3: 305})  ← only actionable issues
       ├── ThreadPoolExecutor
       │    ├── worker: _process_issue(1, 101, 0)  ← pr_number pre-resolved
       │    └── worker: _process_issue(3, 305, 1)  ← pr_number pre-resolved
       └── returns {1: result, 3: result}
```

### Resource Savings

| Scenario | Without Pre-Discovery | With Pre-Discovery |
| ---------- | ----------------------- | -------------------- |
| 20 issues, 5 have PRs, 3 workers | 20 worker slots consumed | 5 worker slots consumed |
| Wasted Claude launches | Up to 15 (issues without PRs) | 0 |
| Worker slot utilization | ~25% effective | 100% effective |

### Method Signature Contract

The pre-discovery pattern establishes a clear contract:

- `_discover_prs(issue_numbers)` → `dict[int, int]` — maps issue→PR, excludes non-actionable
- `_process_all(pr_map)` — submits workers only for items in the map
- `_process_issue(issue_number, pr_number, slot_id)` — receives fully resolved identifiers

### Test Checklist After Refactor

- [ ] Update all `_process_issue(issue, slot)` calls to `_process_issue(issue, pr_num, slot)`
- [ ] Remove `patch.object(driver, "_find_pr_for_issue", ...)` from worker-level tests
- [ ] Add/move "no PR → skip" test to use `run()` with `_find_pr_for_issue` returning `None`
- [ ] Verify `assert_called_once_with(...)` assertions use the correct PR number
- [ ] Run full test suite to confirm no remaining stale call sites

## Related Skills

- `pr-review-automation-workflow` — PRReviewer class that uses the two-tier PR discovery strategy (`_find_pr_for_issue` via branch-name lookup then body-search fallback)
- `parallel-io-bound-execution-with-threadpoolexecutor` — general ThreadPoolExecutor pattern for I/O-bound tasks
- `global-semaphore-parallelism` — rate limiting across parallel workers

## Tags

`#architecture` `#ThreadPoolExecutor` `#parallel` `#pre-discovery` `#worker-guard` `#GitHub` `#automation` `#no-PR`
