---
name: automation-implementer-dryrun-guard
description: "Guard against dry-run mode leaking into post-implementation steps (PR creation, learn, follow-up). Use when: (1) adding --dry-run to an automation implementer that has distinct Claude-code and PR-creation phases, (2) debugging 'No commits between main and branch' errors in dry-run mode, (3) designing any multi-phase CLI tool where --dry-run should exit early after the simulated phase."
category: debugging
date: 2026-04-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [dry-run, implementer, automation, hephaestus, worktree, pr-creation, early-return]
---

# Automation Implementer Dry-Run Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Objective** | Prevent `--dry-run` mode from leaking past the Claude-code invocation step into worktree PR creation, `/learn`, and follow-up issue filing in `hephaestus.automation.implementer` |
| **Outcome** | SUCCESS — early-return guard added after `_run_claude_code()` in dry-run mode; all 596 tests pass; PR #271 created |
| **Verification** | verified-local — 596 tests pass locally; CI for PR #271 pending |

## When to Use

- Adding `--dry-run` to any multi-phase automation tool where one phase runs code and the next phase creates side effects (PRs, issues, commits)
- Debugging "No commits between main and `<branch>`" or "Nothing to merge" errors that only appear in dry-run mode
- Designing the implementer pattern: Claude-code phase → PR-creation phase — dry-run should skip everything after Claude-code returns
- Reviewing any implementation of `--dry-run` that short-circuits only one internal method but not the full pipeline

## Verified Workflow

### Quick Reference

```python
# After the simulated phase sets session_id, add an early return guard:
session_id = self._run_claude_code(...)   # returns None in dry-run
with self.state_lock:
    state.session_id = session_id
self._save_state(state)

# CRITICAL: exit the worker before any post-implementation side effects
if self.options.dry_run:
    self._log("info", f"[DRY RUN] Skipping PR creation, learn, follow-up for #{issue_number}", thread_id)
    return WorkerResult(
        issue_number=issue_number,
        success=True,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
    )

# Only reached in non-dry-run mode:
self._ensure_pr_created(...)
self._run_learn(...)
self._file_follow_up_issues(...)
```

### Detailed Steps

1. **Identify the dry-run short-circuit point** — Locate where `_run_claude_code()` (or equivalent) returns `None` in dry-run mode. This is typically where the real work is simulated.

2. **Save state before the guard** — Any state that should persist even in dry-run (e.g., `session_id`) must be saved before the early return, so the checkpoint reflects the dry-run attempt.

3. **Add an explicit early return** — Immediately after saving state, check `self.options.dry_run` and return a success `WorkerResult`. Do not rely on downstream methods to check the flag; they may not all be guarded.

4. **Log clearly** — Log a `[DRY RUN]` message listing exactly what was skipped. This makes dry-run behavior auditable without reading code.

5. **Return a proper result object** — Return a `WorkerResult(success=True, ...)` so the caller's aggregation logic counts the dry-run as a "processed" issue without treating it as a failure.

6. **Verify no side effects in dry-run** — After applying the guard, run with `--dry-run` and confirm:
   - No worktree is left behind (or worktree is cleaned up by the guard's finally block)
   - No PR is created
   - No follow-up issues are filed
   - No `/learn` skill is committed

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Short-circuit only `_run_claude_code()` | Returned `None` from `_run_claude_code()` when `dry_run=True` | Execution continued to `_ensure_pr_created()` which called `gh pr create` on an empty branch, producing "No commits between main and `<branch>`" errors | A single method guard is not enough; the entire post-simulation pipeline must be skipped via an early return at the worker level |
| Check `dry_run` inside `_ensure_pr_created()` | Added `if self.options.dry_run: return` inside PR creation | Worked for PR creation but still ran `_run_learn()` and `_file_follow_up_issues()`, creating noise in skill files and issue trackers during testing | Each downstream method would need its own guard — brittle. One early return at the worker level is cleaner and more robust |
| Trust that empty `session_id` would prevent PR creation | Assumed that `session_id = None` from `_run_claude_code()` would be checked before `_ensure_pr_created()` | `_ensure_pr_created()` did not check `session_id` before attempting PR creation | Never rely on implicit sentinel values flowing through to downstream steps; use explicit control flow |

## Results & Parameters

### Bug Signature

```
# Symptom in dry-run mode (before fix)
ERROR: No commits between main and feat/issue-42-some-title
gh: GraphQL error: No commits between main and feat/issue-42-some-title
```

### Fix Location

`hephaestus/automation/implementer.py` — `_process_issue()` worker method, immediately after `_run_claude_code()` call and state save:

```python
# In dry-run mode, skip all post-implementation steps
if self.options.dry_run:
    self._log(
        "info",
        f"[DRY RUN] Skipping PR creation, learn, follow-up for #{issue_number}",
        thread_id,
    )
    return WorkerResult(
        issue_number=issue_number,
        success=True,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
    )
```

### Dry-Run Phases (After Fix)

| Phase | Dry-Run Behavior | Non-Dry-Run Behavior |
|-------|-----------------|----------------------|
| `_run_claude_code()` | Returns `None` immediately | Runs Claude Code session |
| State save | Saves `session_id=None` to checkpoint | Saves real `session_id` |
| Early return guard | Returns `WorkerResult(success=True)` | Continues to next phase |
| `_ensure_pr_created()` | SKIPPED | Creates/updates PR |
| `_run_learn()` | SKIPPED | Commits skill to ProjectMnemosyne |
| `_file_follow_up_issues()` | SKIPPED | Files follow-up GitHub issues |

### Generalizable Pattern for Multi-Phase CLIs

Any tool with a "simulate" phase followed by "side-effect" phases should use this pattern:

```python
result = self._run_simulation_phase(...)
self._persist_state(result)

if self.options.dry_run:
    self._log("info", "[DRY RUN] Skipping side effects")
    return SuccessResult(...)  # No PR, no commits, no issues

# Side-effect phases only reached in real mode:
self._create_pr(...)
self._notify(...)
self._file_issues(...)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #271 — automation module porting + dry-run loop testing | 596 tests pass; dry-run across 14 repos confirmed no PRs created |
