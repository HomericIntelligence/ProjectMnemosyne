---
name: batch-pr-rebase-myrmidon-wave-execution
description: "Conflict-aware batch PR update using myrmidon-swarm wave execution. Use when: (1) 10+ open PRs are stale and failing CI, (2) multiple PRs touch the same files and must be sequenced, (3) some PRs are superseded and should be closed, (4) pixi.toml task definitions cause duplicate-path expansion errors in CI."
category: ci-cd
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [git, rebase, pr, parallel, myrmidon, wave, batch, conflict]
---
# Batch PR Rebase: Myrmidon Wave Execution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Conflict-aware batch PR update using myrmidon-swarm wave execution across 30+ open PRs in ProjectHephaestus |
| **Outcome** | Successful — all PRs merged with CI passing; 8 actionable learnings captured |
| **Verification** | verified-ci |

## When to Use

- 10+ open PRs are stale (behind main) with failing CI
- Multiple PRs touch the same files (logging init, config, IO modules) requiring ordered sequencing
- Mix of superseded and valid PRs needing triage before rebasing
- pixi.toml task definitions are causing "Duplicate module" errors in CI (`mypy` invoked with double path)
- pytest `caplog` fixture is failing to capture logs from `ContextLogger` (propagation issue)
- Full-file-rewrite conflicts need manual delta application instead of auto-merge

## Verified Workflow

### Quick Reference

```bash
# Phase 0: Close superseded PRs (always add explanatory comment)
gh pr close <N> --repo <repo> --comment "Superseded by #<M> which is now merged to main."

# Per-PR agent pattern (ALWAYS use fresh worktree — never local checkout)
git worktree add /tmp/worktree-N origin/<branch>
cd /tmp/worktree-N
git rebase origin/main
# Resolve conflicts (see Phase 3)
git push --force-with-lease origin HEAD:<branch>
gh pr merge --auto --rebase <N> --repo <repo>

# Poll for merge completion
for i in $(seq 1 20); do
  STATE=$(gh pr view <N> --repo <repo> --json state --jq '.state')
  [ "$STATE" = "MERGED" ] && break
  sleep 30
done

# Cleanup
cd /home/user/repo && git worktree remove /tmp/worktree-N --force
git worktree prune
```

### Phase 0: Triage and Close Superseded PRs

Before rebasing, identify PRs where the branch diff is empty (changes already on main):

```bash
# Check if branch is already superseded
git worktree add /tmp/check-N origin/<branch>
cd /tmp/check-N
git rebase origin/main
git diff origin/main --stat
# If empty → PR is superseded, close it with explanation
gh pr close <N> --repo <repo> --comment "Superseded by #<M> which is now merged to main."
git worktree remove /tmp/check-N --force
```

Always add an explanatory comment pointing to the superseding PR/commit. Never silently close.

### Phase 1: Pre-flight — Check Required vs Non-Required Checks

Not all failing CI checks block merge. Identify what is actually required:

```bash
# See which checks are branch protection required
gh api repos/{owner}/{repo}/branches/main --jq '.protection.required_status_checks.contexts[]'

# Dependency vulnerability scan (CVEs in third-party deps like pygments/requests)
# are NOT required branch protection checks — do not block merges on them
gh run view <run-id> --log-failed | grep -E "(CVE|vulnerability)"
# If the check name is NOT in required_status_checks, treat as advisory
```

**Key rule**: If a check fails on `main` too and is NOT in required_status_checks, it is advisory only. Enable auto-merge and let GitHub report which checks are actually blocking.

### Phase 2: Wave Ordering for Interdependent PRs

For logging module PRs (or any PRs with init→consumer dependencies):

| Wave | PRs | Wait condition |
|------|-----|---------------|
| Wave 1 | Base init PRs (e.g., ContextLogger.__init__, process methods) | Wait for MERGED |
| Wave 2 | Per-type dedup, lock, propagate=False consumers | Wait for MERGED |
| Wave 3 | setup_logging and top-level entrypoints | Wait for MERGED |

**Critical**: `git fetch origin` before each wave to pick up new main after previous wave merges.

```bash
# After each wave completes:
git -C /home/user/repo fetch origin main
# Then create fresh worktrees from updated origin/<branch> for next wave
```

### Phase 3: Conflict Resolution Strategies

#### Full-file-rewrite conflicts (most common with logging/config overhauls)

When a PR rewrites an entire file and main also has substantial changes:

```bash
# Take the PR's version as the base, then manually apply the small delta from main
git checkout --theirs <file>  # Take PR's version
git add <file>
# Manually read what main added and apply the small delta
# Do NOT use auto-merge or mergetool — produces incoherent hybrid content
```

#### pixi.lock conflicts

```bash
git checkout --theirs pixi.lock
pixi install
git add pixi.lock
git rebase --continue
```

#### CI/workflow file conflicts

```bash
# Take main's version for CI files unless the PR is adding the workflow
git checkout --ours .github/workflows/<file>
git add .github/workflows/<file>
```

### Phase 4: Fix pixi Task Definition Double-Path Expansion

**Symptom**: CI fails with `mypy: error: Duplicate module named 'hephaestus'` or similar.

**Root cause**: pixi.toml defines a task with the path embedded in the task definition, and CI passes the path again as an argument.

```toml
# WRONG — causes double-path expansion:
# pixi run mypy hephaestus/ → expands to: mypy hephaestus/ hephaestus/
[tasks]
mypy = "mypy hephaestus/"

# CORRECT — task is the binary only; CI step passes the path:
[tasks]
mypy = "mypy"
# CI: pixi run mypy hephaestus/  → expands to: mypy hephaestus/  ✓
```

Always define pixi tasks as the bare binary name when the CI step passes path arguments separately.

### Phase 5: Fix pytest caplog with ContextLogger

**Symptom**: `pytest caplog` fixture shows empty records even though ContextLogger emits logs.

**Root cause**: `ContextLogger` sets `self.propagate = False` to prevent log duplication. But `caplog` installs handlers on the root logger — so logs never reach it.

**Fix pattern** (in test files):

```python
import logging

def test_something_with_caplog(caplog):
    logger = get_logger("my_module")
    # Re-enable propagation for caplog to work
    logger.propagate = True
    try:
        with caplog.at_level(logging.DEBUG):
            # ... code under test ...
            pass
    finally:
        logger.propagate = False  # Always restore
```

**Alternative**: Use a dedicated `LogCapture` fixture that installs a handler directly on the specific logger, bypassing root logger dependency.

### Phase 6: Push and Enable Auto-Merge

```bash
git push --force-with-lease origin HEAD:<branch>
# CRITICAL: Always re-enable auto-merge after force-push
# GitHub silently clears auto-merge on force-push
gh pr merge --auto --rebase <N> --repo <repo>

# Verify auto-merge is active
gh pr view <N> --repo <repo> --json autoMergeRequest
# Should show mergeMethod: "rebase", NOT null
```

### Phase 7: Worktree Cleanup

```bash
# Per-PR cleanup (do immediately after push, before starting next PR)
cd /home/user/repo
git worktree remove /tmp/worktree-N --force

# End-of-session cleanup
git worktree prune
git branch -d $(git branch | grep tmp- | tr -d ' ') 2>/dev/null || true
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Local branch checkout | `git checkout <branch>` on local repo | Safety Net blocks `git reset --hard` when local branch diverges from remote | Always use fresh worktree from `origin/<branch>` — never local checkout for rebase work |
| `mypy = "mypy hephaestus/"` in pixi.toml | Defined task with path embedded | pixi expands to `mypy hephaestus/ hephaestus/` causing "Duplicate module named 'hephaestus'" error | Define tasks as bare binaries; let CI steps pass path arguments |
| auto-merge on full-file-rewrite conflicts | Used `git mergetool` or accepted auto-merged result | Produced incoherent hybrid of two complete rewrites — corrupted module logic | Use `git checkout --theirs <file>` then manually apply the small delta from the other side |
| caplog without propagation fix | Ran pytest with `caplog.at_level(logging.DEBUG)` on ContextLogger output | `propagate=False` on logger prevents records reaching root logger where caplog installs handlers | Add `logger.propagate = True` in try/finally block around caplog test section |
| Treating CVE scan failures as blockers | Investigated pygments/requests CVE failures before checking required checks | CVE scan (dependency vulnerability) is not a required branch protection check — does not block merge | Always query `required_status_checks` first; advisory failures should be deferred |
| Parallel rebase without wave ordering | Attempted to rebase logging init and setup_logging PRs simultaneously | setup_logging depends on ContextLogger init — rebasing out of order caused import errors in CI | Establish explicit wave ordering for interdependent module PRs |
| `git add -A` during rebase | Staged all files after conflict resolution | Accidentally picked up untracked test artifacts and build outputs | Always stage specific files by name: `git add <specific-file>` |
| Not re-enabling auto-merge after force-push | Force-pushed rebased branch, assumed auto-merge persisted | GitHub silently clears auto-merge setting on every force-push | After every `--force-with-lease` push: immediately run `gh pr merge --auto --rebase` |

## Results & Parameters

### Wave Ordering for Logging PRs (Reference)

For ProjectHephaestus logging module batch (2026-03-29):

```
Wave 1: ContextLogger init + process methods  (base class, no dependencies)
Wave 2: get_logger per-type dedup + lock + propagate=False  (uses Wave 1)
Wave 3: setup_logging  (uses Wave 1+2)
```

### caplog Propagation Fix Pattern

```python
# Canonical pattern for testing ContextLogger output with pytest caplog
def test_logger_output(caplog):
    logger = get_logger(__name__)
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger=__name__):
            # trigger code that logs
            result = my_function()
        assert "expected message" in caplog.text
    finally:
        logger.propagate = False
```

### pixi Task Definition Fix

```toml
# Pattern: bare binary in task definition, path in CI invocation
[tasks]
mypy = "mypy"
ruff = "ruff"
pytest = "pytest"

# CI step:
# pixi run mypy hephaestus/ tests/
# pixi run ruff check hephaestus/ tests/
# pixi run pytest tests/unit -v
```

### Worktree Per-PR Time Budget

| PR Type | Estimated Time |
|---------|----------------|
| Clean rebase (no conflicts) | ~2 min |
| pixi.lock conflict only | ~3 min |
| Full-file-rewrite conflict | ~10-15 min |
| Superseded (empty diff) | ~1 min (close PR) |
| caplog/propagation fix | ~5 min |

### Session Scale Reference

| Scale | Method | Time |
|-------|--------|------|
| 5-10 PRs | Sequential fresh worktrees | ~20-30 min |
| 15-30 PRs | Myrmidon 2-3 waves, 5 agents/wave | ~45-90 min |
| 30+ PRs | Myrmidon swarm + wave ordering | 2-3 hours |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 30+ open PRs, myrmidon-swarm wave execution, 2026-03-29 | pixi task expansion fix, caplog propagation fix, logging PR wave ordering |

## References

- [batch-pr-rebase-conflict-resolution-workflow](batch-pr-rebase-conflict-resolution-workflow.md) — General rebase/conflict patterns
- [batch-pr-ci-fix-workflow](batch-pr-ci-fix-workflow.md) — CI failure triage and required vs non-required checks
- [parallel-pr-worktree-workflow](parallel-pr-worktree-workflow.md) — Agent isolation with worktrees
- [haiku-wave-pr-remediation](haiku-wave-pr-remediation.md) — Myrmidon haiku wave agent patterns
