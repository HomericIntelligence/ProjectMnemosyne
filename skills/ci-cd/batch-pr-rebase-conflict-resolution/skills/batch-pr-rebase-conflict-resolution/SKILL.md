---
name: batch-pr-rebase-conflict-resolution
description: "Batch rebase and resolve conflicts for multiple stale PRs. Use when: multiple PRs are DIRTY and blocking merges."
category: ci-cd
date: 2026-03-17
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| Objective | Fix 25+ PRs with DIRTY merge state (rebase conflicts) plus 3 with pre-commit CI failures |
| Approach | Sequential processing: rebase onto main, semantic conflict resolution, force-with-lease push, auto-merge |
| Result | 27/28 PRs fixed, 13 auto-merged immediately, 1 skipped (too complex) |
| Duration | Single session |

## When to Use

- Multiple open PRs show DIRTY merge state in GitHub
- PRs are blocked from merging due to rebase conflicts
- Pre-commit CI failures need fixing alongside rebases
- Need to batch-process stale branches efficiently

## Verified Workflow

### Quick Reference

```bash
# Per-PR workflow (sequential)
git fetch origin main
git switch -c temp-PRNUM origin/BRANCH
git rebase origin/main
# Resolve conflicts semantically
git add RESOLVED_FILES && git rebase --continue
git push --force-with-lease origin temp-PRNUM:BRANCH
gh pr merge PRNUM --auto --rebase
git switch main && git branch -d temp-PRNUM
```

### Step 1: Assess PR State

```bash
gh pr list --state open --json number,headRefName,mergeStateStatus
```

Group PRs by: DIRTY (need rebase), BLOCKED (CI failures), UNSTABLE (flaky).

### Step 2: Process Each PR Sequentially

1. Create temp branch from remote: `git switch -c temp-N origin/BRANCH`
2. Rebase: `git rebase origin/main`
3. Resolve conflicts semantically (see strategies below)
4. Push: `git push --force-with-lease origin temp-N:BRANCH`
5. Auto-merge: `gh pr merge N --auto --rebase`
6. Cleanup: `git switch main && git branch -d temp-N`

### Step 3: Semantic Conflict Resolution Strategies

| Conflict Type | Strategy |
|---------------|----------|
| Same file, both add tests | Keep both sides' unique tests |
| HEAD richer docs, PR simpler | Keep HEAD's documentation |
| PR adds new function, HEAD empty | Keep PR's addition |
| PR deletes file, HEAD modified | Check if deletion is intentional (file split). If so, accept delete. If not, keep HEAD. |
| Overlapping test functions | Check main's version - if tests already exist, take main's |
| pixi.lock | Delete, continue rebase, regenerate with `pixi lock` |

### Step 4: Handle Pre-commit Failures

- **mypy errors**: Add missing type annotations (e.g., `Set[str]` instead of bare `set()`)
- **ruff format**: Run `pixi run ruff format FILE`
- **ruff check**: Fix lint errors (unused variables, etc.)
- **pixi install**: Usually fixed by rebasing onto latest main

### Step 5: Re-check After Merges

PRs that merge can make other rebased PRs DIRTY again. After a batch of merges:

```bash
git fetch origin main && git pull --ff-only origin main
# Re-check for new DIRTY PRs and re-rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git add .` during rebase | Used `git add .` to stage resolved files | Accidentally committed untracked files (repro_crash, output.sanitize) | Always use `git add SPECIFIC_FILE` during rebase, never `git add .` |
| `git checkout main 2>&1` | Used `2>&1` redirect with git checkout | Safety Net parsed `2>&1` as positional args | Use `git switch` instead of `git checkout` to avoid safety net issues |
| `git branch -D temp-N` | Force-deleted temp branch | Safety Net blocked `-D` flag | Use `git branch -d` (safe delete) instead |
| Rebase PR #4741 (file splits) | Attempted rebase of PR that splits 20+ test files | modify/delete conflicts everywhere, new content from main would be lost | PRs that restructure files (split/rename/delete) after main has diverged significantly need to be re-implemented from scratch, not rebased |
| Parallel processing | Considered processing PRs in parallel | Git state confusion risk with shared working directory | Sequential processing is safer; use worktrees only if truly parallel |
| `&&` chaining grep with git add | `grep -c "<<<" file && git add file && git rebase --continue` | grep exit code 0 (found 0 matches) but the `&&` chain continued; however the file was modified by a linter between edit and add | Check `git status` for UU (unmerged) state; re-add after linter modifies |

## Results & Parameters

### Configuration

```bash
# Safety: always use --force-with-lease, never --force
git push --force-with-lease origin temp-N:BRANCH

# Always enable auto-merge after push
gh pr merge N --auto --rebase

# Check PR merge state
gh pr list --state open --json number,mergeStateStatus
```

### Results

- **27 of 28 PRs** successfully rebased and pushed
- **13 PRs** auto-merged immediately after rebase
- **3 PRs** closed automatically (became empty - all changes already on main)
- **1 PR** skipped (too complex for rebase - needs fresh re-implementation)
- **0 DIRTY PRs** remaining after processing

### Key Metrics

| Metric | Value |
|--------|-------|
| PRs processed | 27 |
| Auto-merged | 13 |
| Closed (empty) | 3 |
| Skipped | 1 |
| Common conflict file | test_hash.mojo (5 PRs) |
| Common conflict file | migrate_odyssey_skills.py (3 PRs) |
| Common conflict file | validate_test_coverage.py (3 PRs) |
