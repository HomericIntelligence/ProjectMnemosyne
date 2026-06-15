---
name: automation-ci-driver-blocked-poll-early-exit
description: "Use when: (1) a green PR is BLOCKED solely by unresolved review threads under branch protection `required_review_thread_resolution: true` — it gets armed (auto-merge enabled) but is UNMERGEABLE FOREVER and 'Found N unresolved thread(s)' recurs every drive-green loop; (2) the drive-green / ci_driver BLOCKED branch yields WorkerResult(success=True) without ever addressing the review threads; (3) routing the `_arm_and_wait_for_merge` BLOCKED outcome through a `_resolve_blocked_pr` handler that REUSES the address_review.py engine (run_address_fix_session -> _push_ci_fix -> resolve_addressed_threads); (4) _wait_for_pr_terminal spins for the full 30-minute timeout on a BLOCKED PR with unresolved threads or pending required review; (5) diagnosing why the ci_driver polls indefinitely instead of exiting early on mergeStateStatus=BLOCKED; (6) implementing or testing an early-exit guard or a progress-guard / attempt-cap for BLOCKED PRs; (7) adding _pending_required_check_names helper to ci_driver."
category: architecture
date: 2026-06-14
version: "1.1.0"
user-invocable: false
verification: verified-local
history: automation-ci-driver-blocked-poll-early-exit.history
tags: [automation, ci-driver, drive-green, blocked, unresolved-review-threads, required-review-thread-resolution, address-review, resolve-addressed-threads, run-address-fix-session, push-ci-fix, progress-guard, attempt-cap, mergeStateStatus, poll, early-exit, branch-protection, wait-for-pr-terminal, arm-and-wait-for-merge, dry-reuse-engine]
---

# Automation CI Driver: BLOCKED PR Poll Early-Exit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-14 |
| **Objective** | (v1.0.0) Make `_wait_for_pr_terminal` exit early on a branch-protection `BLOCKED` rather than spinning 1800s. (v1.1.0) Stop drive-green from yielding `WorkerResult(success=True)` on a PR BLOCKED *solely* by unresolved review threads — under `required_review_thread_resolution: true` that PR is armed but UNMERGEABLE FOREVER. Instead, ADDRESS + RESOLVE the threads by reusing the existing `address_review.py` engine. |
| **Outcome** | Successful — (v1.0.0) early-exit fires only when BOTH failing and pending required checks are empty, returning `"BLOCKED"`. (v1.1.0) the `_arm_and_wait_for_merge` BLOCKED branch now routes to `_resolve_blocked_pr` (run_address_fix_session -> _push_ci_fix -> resolve_addressed_threads -> _recheck_and_arm_after_fix), guarded by a shrink-or-stop progress check and a `_BLOCKED_ADDRESS_MAX_ATTEMPTS = 2` cap. |
| **Verification** | verified-local (v1.1.0: all 177 tests in tests/unit/automation/test_ci_driver.py pass; ruff + mypy (391 files, no issues) + pre-commit all green; PR #1356 / issue #1348, CI pending) |
| **History** | [changelog](./automation-ci-driver-blocked-poll-early-exit.history) |

## When to Use

- A green PR is BLOCKED *solely* by unresolved review threads under branch protection
  `required_review_thread_resolution: true`: it gets armed (auto-merge enabled) but is
  unmergeable forever, and "Found N unresolved thread(s)" recurs every drive-green loop
  (observed on PR #1283).
- The drive-green / `ci_driver` BLOCKED outcome yields `WorkerResult(success=True)` (an
  armed yield) without ever addressing the threads — you want it to actually resolve them.
- Wiring the `_arm_and_wait_for_merge` BLOCKED branch into a `_resolve_blocked_pr` handler
  that REUSES the `address_review.py` engine (do NOT reimplement the address-and-resolve
  loop — it is already wired into the fresh-implementation loop in `_review_phase.py`).
- Adding a progress guard + attempt cap so an unsatisfiable thread can never loop forever.
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

### v1.1.0 — the armed-but-unmergeable-forever follow-on

v1.0.0's early-exit correctly STOPPED the poll, but its caller behavior — "leave armed and
exit, return `WorkerResult(success=True)`" — was a dead end for the most common BLOCKED
cause: **unresolved review threads**. With branch protection `required_review_thread_resolution:
true`, a green PR BLOCKED solely by unresolved threads is armed yet can NEVER merge. The
drive-green loop then re-observed the same "Found N unresolved thread(s)" every pass without
ever acting on them (observed on PR #1283). In `_arm_and_wait_for_merge`, the BLOCKED outcome
branch simply returned an armed yield with NO thread handling.

The v1.1.0 fix routes that BLOCKED branch to a new `_resolve_blocked_pr` handler that
DISPATCHES THE SAME ADDRESS-AND-RESOLVE ENGINE already used by the fresh-implementation loop —
do not reimplement it (DRY). The engine lives in `hephaestus/automation/address_review.py`:
`run_address_fix_session(...)` returns `{"addressed": [...], "replies": {...}}`, and
`resolve_addressed_threads(addressed, replies, presented_thread_ids, *, dry_run)` resolves
only thread ids that were actually presented (hallucination guard).

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

### v1.1.0 — Resolve BLOCKED by addressing review threads (drive-green)

Route the `_arm_and_wait_for_merge` BLOCKED branch to `_resolve_blocked_pr`, which REUSES the
existing engine rather than reimplementing thread handling. Import style mirrors
`_review_phase.py:33`:

```python
from .address_review import (
    _parse_addressed_block,
    resolve_addressed_threads,
    run_address_fix_session,
)

_BLOCKED_ADDRESS_MAX_ATTEMPTS = 2  # cap so unsatisfiable threads can never loop forever
```

```python
def _resolve_blocked_pr(self, *, issue_number, pr_number, threads, ...):
    # Worktree acquisition is ALREADY solved — do not write new worktree logic.
    # _get_worktree_path tries review-state JSON first, then falls back to
    # self.worktree_manager.create_worktree(issue_number, branch).
    worktree_path = self._get_worktree_path(issue_number, pr_number)

    for _attempt in range(_BLOCKED_ADDRESS_MAX_ATTEMPTS):
        # PROGRESS GUARD: snapshot unresolved thread ids BEFORE addressing.
        prior_ids = {t["id"] for t in threads}

        result = run_address_fix_session(
            issue_number=issue_number, pr_number=pr_number,
            worktree_path=worktree_path, threads=threads, agent=...,
            repo_root=..., parse_fn=_parse_addressed_block,
            log_file=..., dry_run=self.options.dry_run,
        )
        # TRUST BOUNDARY: gate "progress" on a REAL pushed commit, not the agent's
        # self-reported `addressed` list. _push_ci_fix advances head + takes a lease.
        self._push_ci_fix(...)
        # resolve_addressed_threads only resolves ids in presented_thread_ids (hallucination guard)
        resolve_addressed_threads(
            result["addressed"], result["replies"], presented_thread_ids=prior_ids,
            dry_run=self.options.dry_run,
        )

        # Re-fetch; if the unresolved set did NOT shrink, STOP (no false promise of progress).
        threads = self._refetch_unresolved_threads(pr_number)
        remaining_ids = {t["id"] for t in threads}
        if not (prior_ids - remaining_ids):
            break  # leave PR armed; do not spin

    return self._recheck_and_arm_after_fix(issue_number=issue_number, pr_number=pr_number, ...)
```

Key points:

- **DRY — reuse, don't reimplement.** The engine was already wired into the fresh-impl loop
  (`_review_phase.py` `_run_address_review_step`, ~line 1189); drive-green just dispatches the
  same functions.
- **Worktree is a solved problem.** Drive-green does not necessarily have a local worktree the
  way a fresh-impl PR does, but `_get_worktree_path(issue_number, pr_number)` already falls
  back to `worktree_manager.create_worktree`. No new worktree logic.
- **Progress guard.** Snapshot `prior_ids` before each attempt; after re-fetch, if
  `not (prior_ids - remaining_ids)` the unresolved set did not shrink — STOP and leave armed.
  This mirrors the `prior_addressed_threads` snapshot in the implementer review loop.
- **Attempt cap.** `_BLOCKED_ADDRESS_MAX_ATTEMPTS = 2` ensures even a thread the agent keeps
  partially-progressing on can never loop forever.
- **Trust boundary.** Gate progress on a real pushed commit via `_push_ci_fix` (head
  advancement + lease), not on the agent's self-reported `addressed` list.

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
| (v1.0.0) Leave the BLOCKED PR armed and return success without addressing threads | The `_arm_and_wait_for_merge` BLOCKED branch returned `WorkerResult(success=True)` with no thread handling | Under `required_review_thread_resolution: true`, a green PR BLOCKED solely by unresolved threads is armed but UNMERGEABLE FOREVER; "Found N unresolved thread(s)" recurred every loop (PR #1283) | Arming is not progress when threads gate the merge. Route BLOCKED to actually address+resolve the threads (`_resolve_blocked_pr` reusing `address_review.py`). |
| Gate "progress" on the agent's self-reported `addressed` list | Trusted `run_address_fix_session`'s returned `addressed`/`replies` as proof of progress | The agent can self-report addressing without a real change landing on the remote; resolving on that basis falsely advances and can hallucinate thread ids | Gate progress on a REAL pushed commit via `_push_ci_fix` (head-advancement + lease); `resolve_addressed_threads` only resolves ids in `presented_thread_ids`. |
| No progress guard / no attempt cap | Re-ran address-and-resolve every BLOCKED loop | An unsatisfiable thread (agent keeps partially-progressing) loops forever | Snapshot `prior_ids` and STOP when `not (prior_ids - remaining_ids)`; cap at `_BLOCKED_ADDRESS_MAX_ATTEMPTS = 2`. |
| `gh pr create --base fix-main-sim102-lint` against a since-merged base branch | Followed an instruction to branch off `origin/fix-main-sim102-lint` | That branch was squash-merged into main (commit #1352) and deleted from the remote, so `gh pr create` failed with "Base ref must be a branch" | When a "base off X" instruction names a branch that has since merged+deleted, `git rebase origin/main` (git auto-drops the already-applied commit) and retarget the PR `--base main`. |

## Results & Parameters

### Key Behavioral Invariants

| Condition | `mergeStateStatus` | `_failing_*` | `_pending_*` | Early-exit fires? |
|-----------|-------------------|--------------|--------------|-------------------|
| CI in-flight | `BLOCKED` | `[]` | `["ci/build"]` | No — keeps polling |
| CI failed | `BLOCKED` | `["ci/build"]` | `[]` | No — returns `"FAILING"` |
| Branch-protection gate | `BLOCKED` | `[]` | `[]` | Yes — returns `"BLOCKED"` |
| Conflict | `CONFLICTING` | any | any | Yes — returns `"CONFLICTING"` (pre-existing) |

### Environment Variables & Constants

| Name | Purpose | Default |
|------|---------|---------|
| `HEPH_PR_MERGE_MAX_WAIT` (env) | Override `max_wait` in seconds for tests | `1800` |
| `_BLOCKED_ADDRESS_MAX_ATTEMPTS` (module const, v1.1.0) | Cap on address-and-resolve attempts per BLOCKED PR so unsatisfiable threads can't loop forever | `2` |

### Reused engine (v1.1.0 — `hephaestus/automation/address_review.py`)

| Function | Signature / behavior |
|----------|----------------------|
| `run_address_fix_session` | `(*, issue_number, pr_number, worktree_path, threads, agent, repo_root, parse_fn, log_file, dry_run=...)` -> `{"addressed": [...], "replies": {...}}` |
| `resolve_addressed_threads` | `(addressed, replies, presented_thread_ids, *, dry_run)` — resolves ONLY ids in `presented_thread_ids` (hallucination guard) |
| `_parse_addressed_block` | parser passed as `parse_fn` |
| `_get_worktree_path` (ci_driver) | review-state JSON first, then falls back to `worktree_manager.create_worktree` |
| `_push_ci_fix` (ci_driver) | head-advancement + lease; the REAL progress signal |
| `_recheck_and_arm_after_fix` (ci_driver) | re-enters check->arm->wait after the fix |

### Net Change (PR #1090, v1.0.0)

- `hephaestus/automation/ci_driver.py`: +~35 LOC (new helper + BLOCKED guard + caller updates)
- `tests/unit/automation/test_ci_driver.py`: +3 new test methods for BLOCKED early-exit scenarios

### Net Change (PR #1356 / issue #1348, v1.1.0)

- `hephaestus/automation/ci_driver.py`: new `_resolve_blocked_pr` handler + `_BLOCKED_ADDRESS_MAX_ATTEMPTS`
  const + import of the `address_review.py` engine; BLOCKED branch routed through it.
- Based on the now-merged SIM102 lint fix #1352.
- Verification: all 177 tests in `tests/unit/automation/test_ci_driver.py` pass; `ruff check`,
  `mypy` (no issues in 391 files), and `pre-commit run --files` all green. NOTE: the ruff-format
  hook reformatted collapsed multi-line calls on the first run — re-stage and re-run pre-commit
  until clean.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | (v1.0.0) `_wait_for_pr_terminal` polls indefinitely on BLOCKED PRs with unresolved review threads | PR #1090; all unit tests pass locally; all pre-commit hooks pass |
| ProjectHephaestus | (v1.1.0) drive-green armed a green PR BLOCKED solely by unresolved review threads but never addressed them — unmergeable forever under `required_review_thread_resolution: true` (observed on PR #1283) | PR #1356 / issue #1348 (based on now-merged SIM102 fix #1352); routed `_arm_and_wait_for_merge` BLOCKED -> `_resolve_blocked_pr` reusing `address_review.py`, with progress guard + `_BLOCKED_ADDRESS_MAX_ATTEMPTS = 2`; all 177 `test_ci_driver.py` tests + ruff + mypy + pre-commit green (verified-local; CI pending) |
