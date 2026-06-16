---
name: automation-ci-driver-blocked-poll-early-exit
description: "Use when: (1) _wait_for_pr_terminal spins for the full 30-minute timeout on a BLOCKED PR that has unresolved human review threads or pending required review, (2) diagnosing why the ci_driver polls indefinitely instead of exiting early on mergeStateStatus=BLOCKED, (3) implementing or testing an early-exit guard for BLOCKED PRs, (4) adding _pending_required_check_names helper to ci_driver, (5) a CI-green auto-merge-armed PR is stuck in mergeStateStatus=BLOCKED and you need to determine whether the blocker is unresolved review threads (not a human approval gate), (6) triaging github-code-quality bot false-positive threads (unused-import on re-export shims, unnecessary-lambda on DIP injection wrappers)."
category: debugging
date: 2026-06-15
version: "1.1.0"
history: "skills/automation-ci-driver-blocked-poll-early-exit.history"
user-invocable: false
verification: verified-ci
tags: [automation, ci-driver, blocked, mergeStateStatus, poll, early-exit, branch-protection, wait-for-pr-terminal, review-threads, thread-resolution, false-positive, github-code-quality, dip-lambda, re-export-shim]
---

# Automation CI Driver: BLOCKED PR Poll Early-Exit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | (1) Make `_wait_for_pr_terminal` exit early when `mergeStateStatus=BLOCKED` is caused by a branch-protection gate rather than spinning for the full 1800s. (2) Diagnose and resolve BLOCKED state on green+armed PRs by identifying and clearing unresolved review threads rather than waiting for a non-existent human approval gate. |
| **Outcome** | Successful — early-exit fires only when BOTH failing and pending required checks are empty; returns `"BLOCKED"` which callers treat as armed success. Confirmed: green+armed PRs blocked by `required_review_thread_resolution` unblock and auto-merge fires within seconds of thread clearance. |
| **Verification** | verified-ci (PRs #1283 and #1358, ProjectHephaestus, merged once threads cleared) |
| **History** | See `skills/automation-ci-driver-blocked-poll-early-exit.history` |

## When to Use

- `_wait_for_pr_terminal` is polling for 30 minutes on a PR with unresolved human review threads
- Implementing the two-condition BLOCKED guard in `hephaestus/automation/ci_driver.py`
- Adding or reviewing the `_pending_required_check_names` helper method
- Writing tests for the early-exit path (three scenarios: immediate exit, no exit on failing checks, no exit on pending checks)
- Understanding why GitHub reports `BLOCKED` during in-flight CI (not just branch-protection gates)
- A CI-green, auto-merge-armed PR is stuck in `mergeStateStatus: BLOCKED` and you suspect it needs human approval — **verify the branch-protection config first** (see Diagnostic Runbook below)
- A `github-code-quality` SAST bot has opened threads about "unused import" or "unnecessary lambda" that appear to be false positives

## Root Cause

`_wait_for_pr_terminal` only exited early for `DIRTY`/`CONFLICTING`. `BLOCKED` was treated as "still pending" and polled for the full `max_wait` (default 1800s). GitHub reports `mergeStateStatus=BLOCKED` for **two distinct situations**:

1. **Branch-protection gate** — unresolved conversations, required review not approved, signed-commit policy, etc. The bot can never satisfy these; polling is futile.
2. **In-flight CI** — required checks are still running. Once they complete the status changes to `CLEAN` or `FAILING`.

The fix requires distinguishing these: only fire the early-exit when ALL required checks have completed (none failing, none pending).

**Agent diagnostic note (v1.1.0):** A green+armed PR can sit in `BLOCKED` with `required_approving_review_count: null` (no human approval required) when `required_review_thread_resolution: true` is set. In this case the blocker is **unresolved review threads**, not a missing human approval. Threads opened by the `github-code-quality` SAST bot are often false positives (see Diagnostic Runbook).

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

### Diagnostic Runbook: Green+Armed PR Stuck BLOCKED

When a PR shows all CI checks green and auto-merge is armed but `mergeStateStatus` is `BLOCKED`:

**Step 1 — Check branch-protection config (takes 10 seconds):**

```bash
gh api repos/<owner>/<repo>/branches/main/protection \
  --jq '{approving_count: .required_pull_request_reviews.required_approving_review_count, thread_resolution: .required_conversation_resolution.enabled}'
```

If `approving_count` is `null` and `thread_resolution` is `true`, the blocker is **unresolved review threads** — NOT a human approval gate.

**Step 2 — Enumerate unresolved threads:**

```bash
gh api graphql -F owner=<owner> -F repo=<repo> -F pr=<number> -f query='
query($owner:String! $repo:String! $pr:Int!) {
  repository(owner:$owner name:$repo) {
    pullRequest(number:$pr) {
      reviewThreads(first:20) {
        nodes {
          id
          isResolved
          comments(first:1) {
            nodes { author { login } path line body }
          }
        }
      }
    }
  }
}' | python3 -c "
import json,sys
data=json.load(sys.stdin)
threads=data['data']['repository']['pullRequest']['reviewThreads']['nodes']
for t in threads:
    if not t['isResolved']:
        c=t['comments']['nodes'][0]
        print(f\"Thread {t['id']}: {c['author']['login']} @ {c['path']}:{c['line']}\")
        print(f\"  {c['body'][:120]}\")
"
```

**Step 3 — Triage each unresolved thread:**

- **`github-code-quality` bot, "Unused import" on a re-export shim** — This fires on `import X as X` in a backward-compat shim. `ruff`/real-CI lint passes because `import X as X` IS a recognized re-export idiom. Bot doesn't recognize it.
  - FIX: Add an `__all__` listing the re-exported names (makes intent explicit and silences the bot at source). Note: adding `__all__` can make a prior `# noqa: F401` redundant → triggers `RUF100` — remove the `noqa` comment if ruff reports it.
  - Then reply to the thread: "Fixed: added `__all__` to make the re-export intent explicit." and resolve.

- **`github-code-quality` bot, "Unnecessary lambda" on a DIP injection wrapper** — e.g., `lambda: self._foo()`. These are INTENTIONAL: they defer method lookup to call time so `patch.object(driver, '_foo')` works in tests. A bare method ref (`self._foo`) captures the original function at `__init__` time and bypasses the mock.
  - FIX: Do NOT change the code. Reply: "Intentional by design — defers `self._method` lookup to call time so `patch.object(driver, '_method')` intercepts correctly in tests; inlining would capture the original and break the test suite." Then resolve.

- **Other threads** — Apply the genuine fix if the concern is valid, then reply with what was done and resolve.

**Step 4 — Resolve threads via GraphQL:**

```bash
gh api graphql -f query='
mutation($id:ID!) {
  resolveReviewThread(input:{threadId:$id}) {
    thread { isResolved }
  }
}' -F id=<thread-id>
```

**Step 5 — Verify unblock:** Once all threads are resolved, GitHub re-evaluates within seconds. Auto-merge fires automatically if conditions are met. Check with:

```bash
gh pr view <number> --json mergeStateStatus,autoMergeRequest
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single-condition guard | Only checked `not failing` before BLOCKED early-exit | GitHub reports `BLOCKED` while CI checks are still in-flight; would fire early-exit before CI completes, causing premature abandonment of valid PRs | Must check BOTH `not failing` AND `not pending` — two-condition guard required |
| Diagnosed green+armed BLOCKED PR as "waiting on human approval" | Concluded BLOCKED status meant a human reviewer was needed before merge could proceed | Branch protection had `required_approving_review_count: null` (no approval required) and `required_review_thread_resolution: true`; the real blocker was unresolved bot review threads, not a human gate | Always check `gh api repos/.../branches/main/protection` first; if approving count is null and thread-resolution is true, the blocker is threads — resolvable by an agent |
| "Fixed" a github-code-quality "unnecessary lambda" thread by inlining the DIP lambda | Changed `lambda: self._foo()` to `self._foo` to satisfy the bot's complaint | `self._foo` captures the method at `__init__` time, bypassing `patch.object` mocks; would have broken the entire test suite for ci_driver | DIP injection lambdas are intentional — reply with rationale ("defers lookup to call time so patch.object works") and resolve without code change |

## Results & Parameters

### Key Behavioral Invariants

| Condition | `mergeStateStatus` | `_failing_*` | `_pending_*` | Early-exit fires? |
|-----------|-------------------|--------------|--------------|-------------------|
| CI in-flight | `BLOCKED` | `[]` | `["ci/build"]` | No — keeps polling |
| CI failed | `BLOCKED` | `["ci/build"]` | `[]` | No — returns `"FAILING"` |
| Branch-protection gate | `BLOCKED` | `[]` | `[]` | Yes — returns `"BLOCKED"` |
| Conflict | `CONFLICTING` | any | any | Yes — returns `"CONFLICTING"` (pre-existing) |

### Branch-Protection BLOCKED Sub-Types

| Sub-type | `required_approving_review_count` | `required_review_thread_resolution` | Resolution |
|----------|-----------------------------------|--------------------------------------|------------|
| Missing human approval | non-null integer | any | Wait for human reviewer |
| Unresolved review threads | null | true | Triage and resolve each thread |
| Signed-commit policy | N/A | any | Ensure commits are GPG-signed |

### False-Positive Thread Patterns (github-code-quality bot)

| Bot complaint | Actual situation | Correct action |
|---------------|-----------------|----------------|
| "Unused import" on `import X as X` | Backward-compat re-export shim; ruff passes | Add `__all__` listing re-exports; remove now-redundant `# noqa: F401` if RUF100 fires; reply+resolve |
| "Unnecessary lambda" on `lambda: self._method()` | DIP injection wrapper; defers lookup for `patch.object` testability | Reply "intentional by design" + resolve; do NOT inline |

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
| ProjectHephaestus | PR queue session 2026-06-15 — multiple green+armed PRs stuck BLOCKED; diagnosed as unresolved review threads (not human approval gate); `github-code-quality` false-positive threads cleared via reply+resolve | PRs #1283 and #1358 merged within seconds of thread clearance; branch protection confirmed `required_approving_review_count: null`, `required_review_thread_resolution: true` |
