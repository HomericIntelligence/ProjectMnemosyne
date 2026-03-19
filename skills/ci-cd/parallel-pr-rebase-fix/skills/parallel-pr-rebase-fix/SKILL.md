---
name: parallel-pr-rebase-fix
description: "Parallel rebase and CI fix workflow for multiple stale PRs using worktree agents. Use when: many PRs behind main, batch PR maintenance after merge waves, iterative CI diagnosis."
category: ci-cd
date: 2026-03-18
user-invocable: false
---

# Parallel PR Rebase & Fix

## Overview

| Property | Value |
|----------|-------|
| Objective | Rebase and fix CI for 10 stale PRs after 45 test-fix merges to main |
| PRs Processed | 10 (8 simple rebase, 2 with merge conflicts) |
| Rounds Required | 3 (rebase → build fixes → pre-commit/security fixes) |
| Strategy | Parallel worktree agents, one per PR |
| Result | 9/10 fixed, 1 blocked on external dependency |

## When to Use

- Many open PRs are behind main (30-90+ commits) and failing CI
- A batch of PRs merged to main, making remaining PRs stale
- Need to identify and fix per-PR CI failures in parallel
- PRs have mix of simple rebases and merge conflicts requiring semantic resolution

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Parallel rebase (one agent per PR in isolated worktrees)
# Phase 2: Diagnose failures by checking required status checks only
# Phase 3: Fix per-PR issues and push again
# Repeat Phase 2-3 until all required checks pass
```

### Phase 1: Parallel Rebase

Launch one worktree agent per PR. Each agent:

1. `gh pr checkout <number>`
2. `git fetch origin main`
3. `git rebase origin/main`
4. Resolve conflicts if any (semantic merge, not blind picks)
5. `git push --force-with-lease`

**Key decisions**:
- Simple rebases: no conflicts expected, just replay commits
- Conflict PRs: read both versions, merge semantically (keep main's structure + PR's feature additions)
- pixi.lock PRs: run `pixi install` after rebase to regenerate lock file
- Redundant commits: if a PR's commit is already on main, cherry-pick only the unique commits

### Phase 2: Diagnose Failures

After rebase, CI often fails for reasons beyond staleness:

1. **Identify required checks first**: `gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'`
2. **Only fix required checks**: non-required failures (e.g., Docker pull errors) don't block merge
3. **Get failure logs per check**: `gh run view <run-id> --log-failed 2>&1 | grep "error:" | head -10`
4. **Categorize failures**: build errors, pre-commit formatting, security scans, missing trait implementations

### Phase 3: Targeted Fixes

Launch parallel agents for each distinct failure type:

- **Build errors**: Missing trait methods, type mismatches, duplicate functions, docstring format
- **Pre-commit**: Formatting changes (mojo-format trailing lines, Python line length), grandfathered file lists
- **Security scans**: Action config differences (detect vs protect mode, exit-code flags)

### Iteration Pattern

Each round reveals new failures because:
1. Round 1 fixes expose previously-masked errors (e.g., build fix reveals pre-commit formatting issue)
2. CI checks run sequentially — later checks only run after earlier ones pass
3. Some failures are only visible in CI (Docker-based formatting, security scans)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Round 1 rebase-only | Simple rebase and push for all 10 PRs | 9/10 failed CI — rebasing alone didn't fix code issues introduced by PR branches (missing trait methods, type errors, duplicate functions) | Rebase fixes staleness but not code correctness. PRs that modify shared code need compilation verification. |
| Round 2 build-fix agents | Fixed compilation errors (trait methods, type mismatches, docstrings) | 4/10 still failing — pre-commit formatting and security scan issues not caught | Build-validation passing ≠ all required checks passing. Must check each required check independently. |
| Assumed Docker test failures blocked merge | Initially investigated Docker pull errors affecting all PRs | These weren't required checks — #4916 merged despite 20 Docker failures | Always check `required_status_checks` first before investigating failures. |
| gitleaks action with default mode | PR #4836 switched from manual gitleaks binary to `gitleaks-action` | Action defaults to `protect` (git-log) scan mode, finding historical secrets that source-only scan doesn't | When replacing a CI tool with its GitHub Action equivalent, match the scan mode/flags exactly. |
| Grandfathered file list missing entries | PR #4741 added test-count guard hook with allowlist | Missed `DISABLED_test_batchnorm.mojo` which has 14 tests | When adding validation hooks, run against ALL files first to build a complete allowlist. |

## Results & Parameters

### Configuration

```yaml
# Agent parallelism
agents_per_round: 10  # One per PR
agent_type: general-purpose
isolation: worktree  # Each agent gets isolated git worktree

# Required status checks (project-specific)
required_checks:
  - pre-commit
  - security-report
  - Mojo Package Compilation
  - Code Quality Analysis
  - secret-scan

# Diagnosis commands
check_failures: "gh pr checks <number> 2>&1 | grep fail"
check_required: "gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'"
get_failure_log: "gh run view <run-id> --log-failed 2>&1 | grep 'error:' | head -10"
```

### Success Metrics

| Metric | Value |
|--------|-------|
| PRs successfully fixed | 9/10 |
| Total rounds | 3 |
| Total agents launched | 21 (10 + 8 + 3) |
| Blocked PR | #4903 (external dependency not published) |
| Auto-merge enabled | All 10 PRs |

### Key Patterns

1. **Required checks identification**: Always query branch protection rules before investigating failures
2. **Iterative fix loops**: Expect 2-3 rounds — each fix can unmask new failures
3. **Semantic conflict resolution**: For code conflicts, read both versions and merge intent, not just lines
4. **Docker/infra failures**: Often not required checks — verify before spending time fixing
5. **Pre-commit in CI**: Formatting that passes locally may fail in CI (different tool versions, all-files mode)
