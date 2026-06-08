---
name: automation-ci-driver-blocked-poll-early-exit
description: "Use when: (1) _wait_for_pr_terminal spins for the full 30-minute timeout on a BLOCKED PR that has unresolved human review threads or pending required review, (2) diagnosing why the ci_driver polls indefinitely instead of exiting early on mergeStateStatus=BLOCKED, (3) implementing or testing an early-exit guard for BLOCKED PRs, (4) adding _pending_required_check_names helper to ci_driver."
category: debugging
date: 2026-06-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [automation, ci-driver, blocked, mergeStateStatus, poll, early-exit, branch-protection, wait-for-pr-terminal]
---

# Automation CI Driver: BLOCKED PR Poll Early-Exit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Make `_wait_for_pr_terminal` exit early when `mergeStateStatus=BLOCKED` is caused by a branch-protection gate (unresolved conversations, required review) rather than spinning for the full 1800s |
| **Outcome** | Successful — early-exit fires only when BOTH failing and pending required checks are empty; returns `"BLOCKED"` which callers treat as armed success |
| **Verification** | verified-local (all unit tests pass locally; PR #1090 filed, CI pending) |
| **History** | N/A (initial version) |

## When to Use

- `_wait_for_pr_terminal` is polling for 30 minutes on a PR with unresolved human review threads
- Implementing the two-condition BLOCKED guard in `hephaestus/automation/ci_driver.py`
- Adding or reviewing the `_pending_required_check_names` helper method
- Writing tests for the early-exit path (three scenarios: immediate exit, no exit on failing checks, no exit on pending checks)
- Understanding why GitHub reports `BLOCKED` during in-flight CI (not just branch-protection gates)

## Root Cause

`_wait_for_pr_terminal` only exited early for `DIRTY`/`CONFLICTING`. `BLOCKED` was treated as "still pending" and polled for the full `max_wait` (default 1800s). GitHub reports `mergeStateStatus=BLOCKED` for **two distinct situations**:

1. **Branch-protection gate** — unresolved conversations, required review not approved, signed-commit policy, etc. The bot can never satisfy these; polling is futile.
2. **In-flight CI** — required checks are still running. Once they complete the status changes to `CLEAN` or `FAILING`.

The fix requires distinguishing these: only fire the early-exit when ALL required checks have completed (none failing, none pending).

## Verified Workflow

### Quick Reference

```python
# Two helpers needed in CIDriver class:
# 1. _failing_required_check_names (pre-existing)
# 2. _pending_required_check_names (new helper)

def _pending_required_check_names(self, pr_number: int) -> list[str]:
    try:
        checks = gh_pr_checks(pr_number, dry_run=self.options.dry_run)
    except Exception as exc:
        logger.info("PR #%s: failed to fetch CI checks for BLOCKED pending guard (%s)", pr_number, exc)
        return []
    if not checks:
        return []
    required = [c for c in checks if c.get("required")] or checks
    return [c.get("name", "") for c in required if c.get("status") != "completed"]

# In _wait_for_pr_terminal, after the DIRTY/CONFLICTING check:
if merge_status == "BLOCKED" and not failing:
    pending = self._pending_required_check_names(pr_number)
    if not pending:
        logger.warning(
            "Issue #%s: PR #%s is BLOCKED by branch protection "
            "(likely unresolved conversations or pending required review) — "
            "cannot auto-merge; leaving armed and exiting poll early",
            issue_number,
            pr_number,
        )
        return "BLOCKED"
```

### Caller Handling

```python
# In _drive_issue — treat "BLOCKED" as armed success:
terminal_state = self._wait_for_pr_terminal(...)
if terminal_state == "BLOCKED":
    return WorkerResult(success=True, pr_number=pr_number)

# In _check_arming_on_drive_start — treat "BLOCKED" same as "TIMEOUT":
terminal_state = self._wait_for_pr_terminal(...)
if terminal_state in ("TIMEOUT", "BLOCKED"):
    # leave PR armed; fall through
    pass
```

### Test Patterns

```python
# Test 1: No failing, no pending → immediate BLOCKED return
def test_open_blocked_no_failing_no_pending_returns_blocked(self, driver, mock_pr_checks):
    # mock_pr_checks returns [] (no required checks pending)
    mock_pr_checks.return_value = []
    state = driver._wait_for_pr_terminal(issue_number=1, pr_number=100)
    assert state == "BLOCKED"

# Test 2: Failing checks → continues polling, does NOT short-circuit
def test_open_blocked_with_failing_checks_does_not_short_circuit(self, driver, mock_failing_checks):
    mock_failing_checks.return_value = ["ci/build"]
    state = driver._wait_for_pr_terminal(issue_number=1, pr_number=100)
    assert state == "FAILING"  # or "TIMEOUT" depending on mock setup

# Test 3: Pending checks → does NOT fire early exit (uses HEPH_PR_MERGE_MAX_WAIT=0 to force timeout)
def test_open_blocked_with_pending_checks_does_not_short_circuit(self, driver, monkeypatch):
    monkeypatch.setenv("HEPH_PR_MERGE_MAX_WAIT", "0")
    # mock _pending_required_check_names to return in-flight checks
    with patch.object(driver, "_pending_required_check_names", return_value=["ci/build"]):
        state = driver._wait_for_pr_terminal(issue_number=1, pr_number=100)
    assert state == "TIMEOUT"  # early-exit did NOT fire; poll expired
```

### Detailed Steps

1. **Locate the DIRTY/CONFLICTING guard** in `_wait_for_pr_terminal` — the new BLOCKED guard goes right after it.

2. **Add `_pending_required_check_names`** immediately after `_failing_required_check_names` for discoverability. The helper uses `status != "completed"` to identify in-flight checks. If no checks have the `required` flag set, fall back to all checks (conservative).

3. **Two-condition guard** — BOTH must be satisfied before firing early-exit:
   - `not failing` (no required checks are in `failure`/`error` state)
   - `not pending` (no required checks have `status != "completed"`)

4. **Return value** — `"BLOCKED"` (not `None`, not `"TIMEOUT"`). This lets callers distinguish "armed but human action required" from timeout.

5. **Caller updates** — Two callers need updating: `_drive_issue` and `_check_arming_on_drive_start`. In both, map `"BLOCKED"` to the "armed success" path.

6. **Control `max_wait` in tests** via `HEPH_PR_MERGE_MAX_WAIT` env var. Set to `"0"` to force an immediate timeout when testing that the pending-checks guard prevents early exit.

7. **Run checks**:
   ```bash
   pixi run pytest tests/unit/automation/test_ci_driver.py -q --no-cov
   pixi run ruff check hephaestus/automation/ci_driver.py
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single-condition guard | Only checked `not failing` before BLOCKED early-exit | GitHub reports `BLOCKED` while CI checks are still in-flight; would fire early-exit before CI completes, causing premature abandonment of valid PRs | Must check BOTH `not failing` AND `not pending` — two-condition guard required |

## Results & Parameters

### Key Behavioral Invariants

| Condition | `mergeStateStatus` | `_failing_*` | `_pending_*` | Early-exit fires? |
|-----------|-------------------|--------------|--------------|-------------------|
| CI in-flight | `BLOCKED` | `[]` | `["ci/build"]` | No — keeps polling |
| CI failed | `BLOCKED` | `["ci/build"]` | `[]` | No — returns `"FAILING"` |
| Branch-protection gate | `BLOCKED` | `[]` | `[]` | Yes — returns `"BLOCKED"` |
| Conflict | `CONFLICTING` | any | any | Yes — returns `"CONFLICTING"` (pre-existing) |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `HEPH_PR_MERGE_MAX_WAIT` | Override `max_wait` in seconds for tests | `1800` |

### Net Change (PR #1090)

- `hephaestus/automation/ci_driver.py`: +~35 LOC (new helper + BLOCKED guard + caller updates)
- `tests/unit/automation/test_ci_driver.py`: +3 new test methods for BLOCKED early-exit scenarios

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue — `_wait_for_pr_terminal` polls indefinitely on BLOCKED PRs with unresolved review threads | PR #1090; all unit tests pass locally; all pre-commit hooks pass |
