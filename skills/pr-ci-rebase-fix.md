---
name: pr-ci-rebase-fix
description: 'Diagnose pre-existing CI failures on a PR and fix by rebasing onto current
  main. Use when: PR CI fails with crashes not caused by the PR''s own changes, or
  upstream fixes have landed on main since the branch was created.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Skill: PR CI Rebase Fix

## Overview

| Property | Value |
|----------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Fix CI failures on a PR that are pre-existing on `main` and not introduced by the PR's changes |
| **Outcome** | Rebase branch onto current `main` to pick up upstream fixes; CI passes after push |
| **Context** | PR #3189 (issue #3184) had 4 CI failures — all pre-existing crashes and link-check errors already fixed on `main` after the branch was created |

## When to Use

Use this skill when:

- A PR's CI jobs fail with `execution crashed`, runtime errors, or tool errors
- The PR's own changes are cosmetic or unrelated to the failing test areas
- The latest successful `main` run shows those same tests passing
- CI failures appear in areas the PR did not touch (e.g., gradient tests when PR only changes print strings)

**Key Indicators**:

- `mojo: error: execution crashed` on tests the PR never modified
- `link-check` fails on files the PR didn't change
- The branch was created from an older commit on `main` that predates upstream fixes
- `gh run list --branch main` shows the failing jobs now pass on `main`

## Verified Workflow

### Step 1: Confirm failures are pre-existing, not PR-introduced

```bash
# View current CI failures on the PR
gh pr checks <PR-number>

# View the last successful main run to confirm those jobs now pass on main
gh run list --branch main --limit 5

# Check which files the PR actually changed
gh pr diff <PR-number> --name-only
```

Cross-reference: if failing test files are NOT in the PR's changed files, the failures are pre-existing.

### Step 2: Check how far behind main the branch is

```bash
# Fetch latest main
git fetch origin main

# Show divergence
git log --oneline HEAD..origin/main
git log --oneline origin/main..HEAD
```

### Step 3: Rebase onto current main

```bash
git rebase origin/main
```

If there are no conflicts (common for cosmetic-only PRs), this completes cleanly.

For `pixi.lock` conflicts, take `theirs` and regenerate:

```bash
git checkout --theirs pixi.lock
pixi install
git add pixi.lock
git rebase --continue
```

### Step 4: Push (force-with-lease for safety)

```bash
git push --force-with-lease origin <branch-name>
```

### Step 5: Verify CI re-run

```bash
# Poll until checks complete
gh pr checks <PR-number> --watch

# Or check status after a few minutes
gh pr checks <PR-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Investigate test code for root cause | Considered reading the crashing test files to find a code fix | Tests were crashing due to a Mojo runtime issue already fixed upstream — no code change in the PR could fix it | When failures are in untouched test files and main passes them, always check rebase before investigating code |
| Fixing link-check by editing CLAUDE.md | Considered modifying root-relative paths in CLAUDE.md | The link-check failure was pre-existing on main too; fixing it would be out of scope and likely already fixed upstream | Verify if failure also exists on `main` before attempting a targeted fix |

## Results & Parameters

**Rebase command** (clean, no conflicts):

```bash
git fetch origin main
git rebase origin/main
git push --force-with-lease origin <branch-name>
```

**Confirming pre-existing failures** (key diagnostic):

```bash
# Check last N main runs for the failing workflow
gh run list --branch main --workflow "Comprehensive Tests" --limit 3

# View run result
gh run view <run-id> --json conclusion,jobs | jq '.jobs[] | {name, conclusion}'
```

**When rebase picks up conflicts** (pixi.lock pattern):

```bash
git checkout --theirs pixi.lock
pixi install
git add pixi.lock
git rebase --continue
```
