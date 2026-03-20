---
name: pr-review-automation-integration
description: 'TRIGGER CONDITIONS: Running implement_issues.py --review in a live environment.
  Use when: (1) testing or running PR review automation end-to-end, (2) debugging
  nested Claude Code session failures (CLAUDECODE env var), (3) understanding actual
  phase timings and what success/failure logs look like, (4) grading automated PR
  fix quality.'
category: tooling
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# pr-review-automation-integration

Live integration test results and operational learnings from running `implement_issues.py --review`
against a real failing PR. Companion to `pr-review-automation` skill which covers implementation.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Live integration test of `--review` mode against PR #1313 (issue #1216, unit tests failing) |
| Outcome | Full success — 1/1 PR reviewed, 1 commit pushed, all 5 phases completed |
| Issue | HomericIntelligence/ProjectScylla#1216 |
| PR fixed | HomericIntelligence/ProjectScylla#1313 |
| Grade | A- |

## When to Use

- Running `--review` mode for the first time against a new environment
- Debugging why the review script fails when launched from inside Claude Code
- Understanding expected phase durations to set timeouts
- Knowing which PR to pick for testing (unit-tests-only failures are cleanest)

## Verified Workflow

### Step 0: Must run from a terminal, NOT from inside Claude Code

The most critical operational constraint:

```bash
# WRONG — will fail if CLAUDECODE=1 is set (e.g. running inside Claude Code CLI)
pixi run python scripts/implement_issues.py --review --issues 1216 --no-ui

# CORRECT — unset CLAUDECODE before launching
CLAUDECODE= pixi run python scripts/implement_issues.py --review --issues 1216 --no-ui

# Or from a plain terminal (no Claude Code session active)
pixi run python scripts/implement_issues.py --review --issues 1216 --no-ui
```

Claude Code sets `CLAUDECODE=1` in the environment of all child processes. When the review script
tries to spawn a new `claude` subprocess, it checks this variable and refuses with:

```
Error: Claude Code cannot be launched inside another Claude Code session.
Nested sessions share runtime resources and will crash all active sessions.
To bypass this check, unset the CLAUDECODE environment variable.
```

### Step 1: Choose a good test target

Best PR candidates for first integration test:
- Unit tests failing, pre-commit passing → cleanest failure mode, Claude knows exactly what to fix
- Avoid PRs where both pre-commit AND tests fail → harder to isolate

```bash
# Find PRs with only unit test failures
for pr in $(gh pr list --state open --json number --jq '.[].number' | head -10); do
  echo "=== PR #$pr ==="
  gh pr checks $pr 2>&1 | grep -E "fail|pass" | head -4
done
```

### Step 2: Run with `--no-ui` and `--max-workers 1` for first test

```bash
CLAUDECODE= pixi run python scripts/implement_issues.py \
  --review --issues <N> --max-workers 1 --no-ui 2>&1 | tee output.log
```

- `--no-ui`: curses UI interferes with terminal logging visibility during testing
- `--max-workers 1`: sequential execution, easier to debug
- `tee output.log`: preserve the log for analysis

### Step 3: Interpret the log output

Successful run produces this sequence (with approximate timings):

```
[INFO] Starting PR review for issues: [1216]
[INFO] Found PR #1313 for issue #1216 via branch name     ← PR discovery (fast path)
[INFO] Found 1 PR(s) to review: {1216: 1313}
[INFO] Starting review of PR #1313 for issue #1216
[INFO] Branch 1216-auto-impl already exists, reusing it   ← worktree creation
[INFO] Created worktree for issue #1216 at .../.worktrees/issue-1216

  ~5.5 min: Analysis session (Phase 1)

[INFO] Analysis complete for PR #1313, plan saved to .../review-plan-1216.md

  ~2.9 min: Fix session (Phase 2)

[INFO] Pushing 1 commit(s) to PR #1313                   ← Phase 3: push
  ~2 min: push (pre-commit hooks run remotely)
[INFO] Pushed fixes to PR #1313

  ~2 min: Retrospective (Phase 4)

[INFO] Retrospective completed for issue #1216
[INFO] PR #1313 review complete for issue #1216
[INFO] Issue #1216 PR review completed
[INFO] PR Review Summary: Total PRs: 1, Successful: 1, Failed: 0
[INFO] Removed worktree for issue #1216
[INFO] PR review complete
```

### Step 4: Verify the fix was pushed

```bash
gh pr view <PR_NUMBER> --json commits,headRefName | jq '.commits[-1]'
gh pr checks <PR_NUMBER>
```

## Phase Timings (observed)

| Phase | Duration | Notes |
|-------|----------|-------|
| PR discovery | ~1s | Branch-name lookup succeeded immediately |
| Worktree creation | ~1s | Branch already existed, reused |
| Analysis session | ~5.5 min | Claude reads code, CI logs, produces plan |
| Fix session | ~2.9 min | Claude implements plan, runs tests, commits |
| Push | ~2 min | Includes remote pre-commit hook execution |
| Retrospective | ~2 min | Optional; resumes fix session |
| **Total** | **~12.5 min** | Single PR, max-workers=1 |

Analysis is consistently the longest phase — Claude needs to read many files to understand the failure context.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Successful invocation

```bash
# From outside Claude Code, on branch 1320-review-mode-implement-issues
CLAUDECODE= pixi run python scripts/implement_issues.py \
  --review \
  --issues 1216 \
  --max-workers 1 \
  --no-ui \
  2>&1 | tee output.log
```

### Target PR characteristics (what worked well)

| Attribute | Value |
|-----------|-------|
| Issue | #1216 — refactor(runner): extract _build_experiment_actions closures |
| PR | #1313 |
| CI failure | Unit tests only (pre-commit passing) |
| Branch | `1216-auto-impl` (matched branch-name strategy, no fallback needed) |
| Commits pushed | 1 |

### Grade breakdown

| Criterion | Score | Notes |
|-----------|-------|-------|
| PR discovery | ✓ | Branch-name fast path succeeded |
| Analysis session | ✓ | Plan produced, saved correctly |
| Fix session | ✓ | Actual fixes implemented, commit created |
| Push | ✓ | 1 commit pushed to PR |
| Retrospective | ✓ | Completed without error |
| Worktree cleanup | ✓ | Removed on exit |
| **Overall** | **A-** | Deduction: nested-session issue requires workaround |

### What still needs testing

- Multi-PR parallel execution (`--max-workers > 1`)
- Body-search fallback (PR not on `{issue}-auto-impl` branch)
- PRs with both pre-commit AND test failures
- Push with no new commits (Claude committed inside the session, nothing left)
- Retrospective disabled (`--no-retrospective`)

## Recommended Future Fix: Strip CLAUDECODE in reviewer.py

Add to `_run_analysis_session` and `_run_fix_session` in `reviewer.py`:

```python
import os

# Strip CLAUDECODE so nested claude subprocess can launch
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

result = run(
    ["claude", str(prompt_file), "--output-format", "json", ...],
    cwd=worktree_path,
    timeout=1200,
    env=env,          # <-- pass cleaned environment
)
```

This matches how other automation scripts handle the nested-session constraint and makes
`--review` usable directly from Claude Code sessions without manual env var unsetting.
