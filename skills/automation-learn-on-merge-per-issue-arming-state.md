---
name: automation-learn-on-merge-per-issue-arming-state
description: "When automation that runs `/learn` (or any learnings-capture step) after CI work fires on the optimistic point (auto-merge enabled) instead of on the truth (detected merge), Mnemosyne fills with lessons from PRs that never shipped AND shared-PR groups silently collapse N issues into 1 capture. Fix: a per-issue arming-record state machine driven by detected-merge, fanned out via the shared-PR dedupe map. Use when: (1) building post-CI learnings-capture in `loop_runner.py` / `ci_driver.py`-style pipelines, (2) capturing lessons keyed on `_enable_auto_merge` succeeding, (3) a dedupe step in `_discover_prs` collapses N issues to 1 worker and each issue is a distinct lesson, (4) you need post-merge detection that survives across runs without polling, (5) deciding when to set `learn_captured_at` (success-only vs best-effort)."
category: ci-cd
date: 2026-05-31
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - automation
  - learn-capture
  - drive-green
  - arming-record
  - state-machine
  - shared-pr
  - detected-merge
  - hephaestus-automation-loop
  - homericintelligence
---

# Capture `/learn` On Detected-Merge, Per-Issue, Via Arming Records

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-31 |
| **Objective** | Ensure every issue that lands on a shared PR gets its own `/learn` capture, fired exactly once when the PR actually merges (not when auto-merge is armed), and never duplicated across worker runs. |
| **Outcome** | Successful — drive-green `/learn` capture is now keyed on detected-merge per-issue. A 9-issue shared PR produces 9 distinct captures. Optimistic captures on auto-merge-armed PRs that later get blocked/cancelled no longer pollute Mnemosyne. |
| **Verification** | verified-ci (merged via PR #844 closing issue #840 on `HomericIntelligence/ProjectHephaestus`). Builds on PR #835 (shared-PR dedupe in `_discover_prs`). |
| **History** | N/A (initial version) |

## When to Use

Trigger phrases:

- "`/learn` firing before PR merges"
- "shared PR closes N issues, only 1 learning captured"
- "auto-merge armed != PR merged"
- "drive-green learnings on optimistic point"
- "arming record" / "per-issue arming state"
- "`_arm_drive_green`" / "`_check_arming_on_drive_start`" / "`learn_captured_at`"
- "best-effort /learn idempotency"
- "post-merge cwd fallback worktree gone"

Trigger situations:

- Building or auditing automation that captures lessons after CI work converges (any `drive_prs_green.py` / `loop_runner.py` / `ci_driver.py` analog).
- A dedupe step (e.g., `_discover_prs` collapsing 9 issues to 1 canonical worker because they all share a `Closes #N` to the same PR) means N issues map to 1 PR, and each issue is a distinct lesson that should be captured separately.
- You catch `/learn` (or any captures-step) firing on `_enable_auto_merge` returning True instead of on `gh pr view --json mergedAt` confirming a merge.
- Mnemosyne is filling with "lessons" from PRs that auto-merge-armed but later got blocked by CI flake, branch-protection, or manual cancellation.
- You need a post-merge detector that survives across worker runs without an in-process poll (worker may exit between arming and merge).
- The original worktree for the PR's head branch has been deleted (post-merge cleanup) and the captures-step crashes on a missing `cwd`.

## Verified Workflow

> The shipped fix is a per-issue arming-record state machine driven by
> detected-merge, fanned out via the shared-PR dedupe map already
> produced by `_discover_prs`. The arming step writes one JSON record
> per sibling issue; subsequent runs check each record against
> `gh pr view --json state,headRefOid,mergedAt` and fire `/learn` once
> per issue exactly when the PR is detected MERGED.

### Quick Reference

State file shape — one per issue, at `state_dir/drive-green-armed-<issue>.json`:

```json
{
  "pr_number": 103,
  "pr_head_branch": "12-impl",
  "head_sha_at_arming": "abc12345",
  "armed_at": "2026-05-31T15:30:00Z",
  "learn_captured_at": null
}
```

Per-issue arming after auto-merge is enabled (drop the optimistic `/learn` call here):

```python
# In _drive_issue, AFTER _enable_auto_merge(pr_number) succeeds.
# DO NOT call _run_drive_green_learnings here — that was the bug.
gh_state = self._gh_pr_state(pr_number)  # gh pr view --json state,headRefOid,mergedAt
pr_head_sha = (gh_state or {}).get("headRefOid", "") or ""
pr_head_branch = self._get_pr_branch(pr_number)
self._arm_drive_green(pr_number, pr_head_branch, pr_head_sha)
```

Fan-out across every sibling issue on the shared PR:

```python
def _arm_drive_green(self, pr_number, pr_head_branch, pr_head_sha):
    # self.shared_pr_issues was populated by _discover_prs after dedupe.
    siblings = self.shared_pr_issues.get(pr_number, [])
    armed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for issue_num in siblings:
        existing = self._load_arming_state(issue_num) or {}
        if existing.get("learn_captured_at"):
            continue  # Idempotency: never clobber a captured record.
        self._save_arming_state(issue_num, {
            "pr_number": pr_number,
            "pr_head_branch": pr_head_branch,
            "head_sha_at_arming": pr_head_sha,
            "armed_at": armed_at,
            "learn_captured_at": None,
        })
```

At the top of every subsequent `_drive_issue`, short-circuit on the arming record:

```python
def _drive_issue(self, issue_number, ...):
    armed_result = self._check_arming_on_drive_start(issue_number, pr_number)
    if armed_result is not None:
        return armed_result  # Record handled this issue.
    # ... normal drive logic continues here ...
```

Resolution table inside `_check_arming_on_drive_start` (calls `gh pr view <N> --json state,headRefOid,mergedAt`):

| GH state | `learn_captured_at` | Head SHA | Action |
|----------|--------------------|--------|--------|
| any | not null | any | return success, no `/learn` (already captured) |
| MERGED | null | any | fire `/learn` once, set `learn_captured_at`, return success |
| OPEN | null | same as `head_sha_at_arming` | return success, no `/learn` (still in flight) |
| OPEN | null | different SHA | drop record, return None (PR force-pushed, re-enter drive) |
| CLOSED (not merged) | null | any | drop record, return None (PR abandoned, re-enter drive) |

Best-effort `/learn` — always set `learn_captured_at`, even on failure:

```python
ok = self._run_drive_green_learnings(issue_number, pr_number)
# DO NOT gate the timestamp on `ok` — transient /learn failures must not loop forever.
record["learn_captured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
self._save_arming_state(issue_number, record)
if not ok:
    LOG.warning("drive-green /learn failed for issue #%s; marked captured to avoid re-fire loop",
                issue_number)
```

Post-merge cwd fallback for `_run_drive_green_learnings`:

```python
def _run_drive_green_learnings(self, issue_number, pr_number):
    try:
        cwd = self._get_worktree_path(pr_number)  # may be gone post-merge
    except (FileNotFoundError, RuntimeError):
        cwd = self.repo_root  # fall back; the /learn prompt is self-contained.
    # Use a fresh --session-id; resume-continuity is nice-to-have, not load-bearing.
    return self._invoke_claude_learn(cwd=cwd, issue=issue_number, pr=pr_number)
```

The bridge from `_discover_prs` (dedupe) to `_arm_drive_green` (fan-out):

```python
# In _discover_prs, AFTER grouping issues -> PR via Closes #N:
self.shared_pr_issues = {pr: sorted(issues) for pr, issues in pr_to_issues.items()}
# The canonical-issue dedupe still selects ONE worker per PR for the drive loop,
# but the arming step uses the FULL map to write N records, one per sibling.
```

### Detailed Steps

1. **Audit the existing capture site.** In `loop_runner.py` / `ci_driver.py` analogs, find the call to `_run_drive_green_learnings` (or whatever fires `/learn`). If it sits directly after `_enable_auto_merge(pr_number)` returning True, that is the optimistic-point bug. Move it out.

2. **Populate `self.shared_pr_issues` in `_discover_prs`.** This is the load-bearing link between PR #835's dedupe and the per-issue fan-out. The dedupe step that collapses 9 issues to 1 canonical worker MUST still expose the full PR -> [issues] map; otherwise the 8 deferred siblings never get arming records.

3. **Replace the optimistic call with `_arm_drive_green(pr_number, pr_head_branch, pr_head_sha)`** at the post-`_enable_auto_merge` site. Capture the PR head SHA via `gh pr view --json headRefOid` so the next run can detect force-pushes.

4. **Wire `_check_arming_on_drive_start` at the top of `_drive_issue`.** It must run BEFORE any normal drive logic so a queued sibling does not re-enter implementation. The five-state resolution table (above) is the contract.

5. **In the MERGED branch, fire `/learn` and unconditionally stamp `learn_captured_at`.** Best-effort. Stamping only on success creates an infinite-retry loop on transient `/learn` failures.

6. **Add the post-merge cwd fallback in `_run_drive_green_learnings`.** The PR's head branch is typically deleted after merge; if you `_get_worktree_path` blindly you get FileNotFoundError. Fall back to `self.repo_root`. The `/learn` prompt is self-contained (it carries "you just drove PR #N to green; capture learnings"), so the fresh `--session-id` still captures the lesson — resume-continuity is a nice-to-have.

7. **Drop the record on force-push (OPEN + different SHA) or abandon (CLOSED-not-merged).** In both cases return None so the caller re-enters the normal drive logic. The record is a one-shot armed-for-this-SHA contract.

8. **Tests for the state machine** must cover: the five resolution rows; idempotency (captured record is never clobbered by re-arming); fan-out (a 9-issue shared PR writes 9 records); best-effort (failure path still stamps `learn_captured_at`); cwd fallback (post-merge worktree-gone path uses `self.repo_root`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fire `/learn` on `_enable_auto_merge` returning True | The previous capture-site placed `_run_drive_green_learnings(issue, pr)` directly after the auto-merge enable succeeded, on the assumption that "auto-merge armed" was a close-enough proxy for "PR will merge." | Auto-merge is the optimistic point, not the truth. PRs auto-merge-arm but later get blocked by CI flake, branch-protection failures, or manual cancellation. Mnemosyne filled with lessons from PRs that never shipped, and required-checks audits found "verified-ci" skills referencing PRs that closed unmerged. | Capture only on detected-merge. Move the call out and replace with an arming-record write; the next run resolves the record by polling `gh pr view --json state,mergedAt`. Truth must beat optimism even at the cost of one extra run-cycle of latency. |
| One `/learn` per PR for shared-PR groups | After the `_discover_prs` dedupe in PR #835 collapsed N issues sharing the same `Closes #N -> PR` link into 1 canonical worker, the post-merge capture only fired for the canonical issue. The 8 deferred siblings never got their own `/learn`. | The dedupe is correct for the DRIVE loop (one worker per PR avoids redundant CI launches) but wrong for the LEARN loop (every issue is a distinct lesson). User explicitly required "9 PRs => 9 learning sessions captured." A single capture conflates N independent root-causes into one Mnemosyne entry. | Make `_discover_prs` expose `self.shared_pr_issues = {pr: [sorted issues]}` so the arming step can fan out one record per sibling. Dedupe at the worker layer; fan out at the lesson layer. The map is the bridge between them. |

## Results & Parameters

### State machine resolution (the contract)

`_check_arming_on_drive_start(issue_number, pr_number)` queries
`gh pr view <pr_number> --json state,headRefOid,mergedAt` and returns:

| GH state | `learn_captured_at` | Head SHA vs `head_sha_at_arming` | Returns | Side effect |
|----------|--------------------|---------------------------------|---------|-------------|
| any | not null | n/a | success, no work | none (already captured) |
| MERGED | null | n/a | success | fire `/learn`; set `learn_captured_at` (always, success or fail) |
| OPEN | null | same | success, no `/learn` | none (still in flight) |
| OPEN | null | different | None | drop record (PR force-pushed; re-enter drive) |
| CLOSED, not merged | null | n/a | None | drop record (PR abandoned; re-enter drive) |

Returning None means "this record did not handle the issue; fall through to the
normal drive logic."

### Idempotency invariants

- `_arm_drive_green` walks every sibling issue but SKIPS any whose record already has `learn_captured_at` set. This guarantees that re-running after a partial failure cannot clobber a captured record.
- The MERGED branch sets `learn_captured_at` regardless of `/learn` success. A failed `/learn` is logged and dropped; it does not re-fire on the next run. (Re-firing would loop forever on any transient claude-CLI failure.)
- Force-push (OPEN + SHA mismatch) and abandon (CLOSED non-merged) DROP the record (don't update it) and return None. The next run will re-arm if appropriate.

### Net change shape

| Module | Change |
|--------|--------|
| `_discover_prs` | After issue->PR grouping, set `self.shared_pr_issues = {pr: sorted(issues)}`. |
| `_drive_issue` head | Insert `armed_result = self._check_arming_on_drive_start(...)`; short-circuit if not None. |
| `_drive_issue` body | Replace the post-`_enable_auto_merge` `/learn` call with `_arm_drive_green(...)`. |
| New: `_arm_drive_green` | Fan out one record per sibling; skip captured records. |
| New: `_check_arming_on_drive_start` | Five-row resolution table; queries `gh pr view`. |
| New: `_load_arming_state` / `_save_arming_state` | Read/write `state_dir/drive-green-armed-<issue>.json`. |
| `_run_drive_green_learnings` | Wrap cwd resolution in try/except; fall back to `self.repo_root`. |

### Verified scenario

| Scenario | Setup | Expected captures |
|----------|-------|-------------------|
| Optimistic-armed PR that later gets cancelled | `_enable_auto_merge` returns True, then the PR is closed unmerged before merge | 0 `/learn` captures (record dropped on CLOSED-not-merged; previously: 1 false capture) |
| Shared PR closing 9 issues | One PR has `Closes #1` through `Closes #9` in body; dedupe selects #1 as canonical worker | 9 distinct `/learn` captures, one per issue (previously: 1 capture for #1 only) |
| `/learn` transient failure on merge | PR merges; `_run_drive_green_learnings` raises | `learn_captured_at` set anyway; next run is a no-op (previously: would re-fire forever) |
| PR force-pushed after arming | OPEN + head SHA differs from `head_sha_at_arming` | Record dropped; `_drive_issue` re-enters normal drive logic; arming will re-write on the new SHA |
| Worktree deleted post-merge | PR head branch removed from remote after squash-merge | `_run_drive_green_learnings` falls back to `self.repo_root`; capture still succeeds |

### Trigger-phrase index (for `/advise` discovery)

- `/learn fires before PR merges`
- `drive-green learnings on auto-merge armed`
- `shared PR 9 issues only 1 lesson captured`
- `_arm_drive_green`
- `_check_arming_on_drive_start`
- `learn_captured_at idempotency`
- `arming-record state machine`
- `shared_pr_issues fan-out`
- `post-merge cwd fallback worktree gone`
- `drive-green-armed-<issue>.json`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectHephaestus | Issue #840 - drive-green `/learn` capture fires on optimistic auto-merge-armed and silently collapses shared-PR groups | PR #844 (this fix); builds on PR #835 (shared-PR dedupe in `_discover_prs`); follow-on to PR #834 (shared-PR dedupe). User-facing requirement: "9 PRs => 9 learning sessions captured." |

## References

- [PR #844 - per-issue arming-record state machine for drive-green /learn](https://github.com/HomericIntelligence/ProjectHephaestus/pull/844)
- [Issue #840 - /learn fires on optimistic point instead of detected merge](https://github.com/HomericIntelligence/ProjectHephaestus/issues/840)
- [PR #835 - shared-PR dedupe in `_discover_prs`](https://github.com/HomericIntelligence/ProjectHephaestus/pull/835)
- [tooling-hephaestus-automation-loop-drive-green-broken-design](tooling-hephaestus-automation-loop-drive-green-broken-design.md) - sibling skill covering the drive-green phase-model bugs (#818-#821); orthogonal but cohabits the same `loop_runner.py` / `ci_driver.py` modules.
- [automation-loop-early-exit-zero-work-convergence](automation-loop-early-exit-zero-work-convergence.md) - the early-exit mechanism in the same loop runner.
