---
name: mass-pr-rebase-parallel-agents
description: 'Batch rebase 10-100+ conflicting PRs using parallel sub-agents with
  worktree isolation and semantic conflict resolution. Use when: many PRs are CONFLICTING,
  some have CI failures, and pixi.lock/overlapping files need phased ordering.'
category: ci-cd
date: 2026-03-27
version: 2.0.0
user-invocable: false
verification: verified-local
history: mass-pr-rebase-parallel-agents.history
tags: []
---
# Mass PR Rebase with Parallel Agents

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Batch rebase conflicting PRs and fix CI failures using parallel agents with semantic conflict resolution |
| **Outcome** | Success — verified across two sessions (96 PRs in ProjectOdyssey, 20 PRs in ProjectScylla) |
| **Verification** | verified-local |
| **History** | [changelog](./mass-pr-rebase-parallel-agents.history) |

## When to Use

- A major refactor lands on main causing mass conflicts (10+ PRs CONFLICTING)
- Mix of CONFLICTING PRs and MERGEABLE-but-CI-failing PRs
- PRs touch overlapping files (CLI, config, pixi.lock) requiring phased ordering
- Need semantic conflict resolution (not just `--theirs`) to preserve PR intent
- Auto-generated lockfiles (pixi.lock) need regeneration after rebase

## Verified Workflow

### Quick Reference

```bash
# Classify PRs
gh pr list --state open --limit 200 --json number,headRefName,mergeable,autoMergeRequest \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Launch parallel rebase agent (with worktree isolation)
# Agent tool: isolation: "worktree", prompt includes rebase + pre-commit + push

# Verify after push
gh pr view <number> --json mergeable,state
```

### Phase 0: Fix Systemic CI on Main First

Before rebasing, fix failures that affect ALL PRs:

1. Check CI: `gh pr checks <number>` on a recent MERGEABLE PR
2. Check main: `gh run list --branch main --limit 5`
3. Categorize as systemic vs PR-specific
4. Create a single fix PR for systemic issues

### Phase 1: Classify and Order PRs

```bash
# Group by mergeability
gh pr list --state open --limit 200 --json number,headRefName,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Check which files each PR touches (for ordering)
for pr in <numbers>; do
  branch=$(gh pr view $pr --json headRefName -q .headRefName)
  echo "=== PR #$pr ($branch) ==="
  git diff --name-only origin/main...origin/"$branch" | head -20
done
```

**IMPORTANT**: Always use `--limit 200` or higher. Default limit misses older PRs.

**Order by complexity** (process simple PRs first to avoid compounding conflicts):

| Phase | Criteria | Parallelism |
|-------|----------|-------------|
| Simple (1-2 files) | Single file changes, docs | Fully parallel |
| Moderate (3-15 files, no lockfile) | Feature PRs not touching pixi.lock | Parallel if non-overlapping |
| Lockfile cluster (touches pixi.lock) | PRs modifying pixi.toml/pixi.lock | Parallel OK (each regenerates independently) |
| CI-only fixes (MERGEABLE but failing) | Pre-commit/test failures | Parallel |
| Massive refactors (50+ files) | Layout migrations, renames | DEFER until others merge |

### Phase 2: Batch Rebase with Parallel Agents

Launch sub-agents with **worktree isolation** — each agent gets an isolated repo copy:

```python
# Agent tool configuration
Agent(
    description="Rebase PR #XXXX",
    isolation="worktree",  # CRITICAL: isolates each agent
    prompt="""Rebase PR #XXXX (branch: YYYY) onto origin/main and push.
    1. git fetch origin main && git fetch origin YYYY
    2. git checkout YYYY
    3. git rebase origin/main — resolve conflicts SEMANTICALLY (keep PR intent)
    4. pixi.lock rule: rm pixi.lock && git add pixi.lock && git rebase --continue
       Then: pixi lock after rebase completes
    5. pre-commit run --all-files — fix any issues
    6. git push --force-with-lease origin YYYY
    7. gh pr view XXXX --json mergeable,state"""
)
```

**Conflict resolution — semantic, not blind:**

| File Type | Strategy |
|-----------|----------|
| `pixi.lock` | Delete, continue rebase, regenerate with `pixi lock`. **NEVER** use `--ours`/`--theirs` |
| `pixi.toml` | Merge both sides (keep main's deps + PR's new deps) |
| Feature code (cli, config, models) | Read PR intent, combine both sides semantically |
| Schemas (JSON) | Check for duplicate keys, consolidate into single definition |
| Tests (deleted on main) | Accept deletion if main removed the feature |
| `.pre-commit-config.yaml` | Check for duplicate hook entries after merge |
| Workflows (`.github/`) | Keep main's security patterns (SHA pins, env vars) |

**Batch sizing:**

| Scale | Agents | PRs/Agent |
|-------|--------|-----------|
| 10-20 PRs | 3-4 | 3-5 |
| 20-50 PRs | 4-6 | 5-10 |
| 50-100+ PRs | 5-9 | 10-12 |

### Phase 3: Fix CI-Only Failures (MERGEABLE PRs)

For PRs that are MERGEABLE but failing CI, launch parallel fix agents:

| Failure Type | Diagnosis | Fix Pattern |
|-------------|-----------|-------------|
| Schema validation | Duplicate keys in JSON, field mismatch | Remove duplicates, align with schema |
| Forbidden phrases in docs | Test enforces terminology rules | Replace terms (e.g., "failure injection" → "fault injection") |
| Version consistency hooks | Aspirational version refs > canonical | Add smart exclusions (fenced code, inline code, URLs) |
| Pre-commit formatting | ruff-format, markdownlint | `pre-commit run --all-files` auto-fixes |

### Phase 4: Handle Closed/Superseded PRs

Expect 15-25% of PRs to be already closed or superseded:

- **Rebase produces empty commit** → PR's changes are already on main
- **PR shows CLOSED state** → Check if a newer PR delivered the same work
- **Cannot reopen after force-push** → Create new PR if changes are still needed
- **Log these** — don't waste time investigating, just skip and note

### Phase 5: Monitor and Clean Up

```bash
# Verify final state
gh pr list --state open --limit 200 --json number,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Clean up worktrees
git worktree prune
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `--theirs` for all conflicts | Blind conflict resolution | Loses PR-specific work when main has diverged significantly | Use semantic resolution — read PR intent and combine both sides |
| `--ours`/`--theirs` for pixi.lock | Standard git conflict resolution on lockfiles | pixi.lock encodes SHA256 of local editable package; merged version is always invalid | Always delete pixi.lock, continue rebase, regenerate with `pixi lock` |
| Using `--limit 100` for PR listing | Default gh pr list limit | Missed older conflicting PRs | Always use `--limit 200` or higher |
| Single agent for all rebases | Considered processing sequentially | Would take hours for 20+ PRs | Parallel agents with worktree isolation complete in minutes |
| No phased ordering | Rebase all PRs at once regardless of complexity | Compounding conflicts when interdependent PRs land in wrong order | Process simple PRs first, defer massive refactors |
| Rebasing closed/superseded PRs | Spent time resolving conflicts on PRs already delivered by other work | Empty commits after rebase — wasted effort | Check PR state before investing in conflict resolution |
| Not running pre-commit before push | Pushed rebased branches without local validation | Primary cause of CI failures on auto-impl branches | Always run `pre-commit run --all-files` before every push |

## Results & Parameters

### Session Results (v2.0.0 — ProjectScylla, 2026-03-27)

- **21 open PRs** processed (17 CONFLICTING + 3 CI-failing + 1 already merged)
- **16 PRs** rebased and pushed to MERGEABLE state
- **4 PRs** found already closed/superseded (skipped)
- **1 PR** deferred (202-file src-layout migration)
- **Semantic conflict resolution** across CLI, config, schema, maestro module files
- **pixi.lock** regenerated on 7 PRs

### Session Results (v1.0.0 — ProjectOdyssey, 2026-03-17)

- **138 total open PRs** processed
- **96 PRs rebased** and force-pushed (0 failures)
- **17 PRs** were already closed
- **All conflicts** resolved with `--theirs` strategy

### Agent Configuration

```yaml
# v2.0.0: Use built-in worktree isolation
subagent_type: general-purpose
isolation: "worktree"  # Each agent gets isolated repo copy
# No need for manual worktree management

# v1.0.0: Manual worktree management
subagent_type: general-purpose
run_in_background: true
```

### CI Impact

Mass force-pushing overwhelms CI runners. All PR runs queue simultaneously.
Plan for 30-60 min CI queue drain after batch rebases.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | 21 PRs (17 conflicting + 3 CI-failing), semantic resolution, pixi.lock regen | 2026-03-27 |
| ProjectOdyssey | 138 PRs, 80+ conflicting, `--theirs` strategy | 2026-03-17 |
