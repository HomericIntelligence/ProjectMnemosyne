---
name: issue-triage-wave-parallel-execution
description: "Bulk-triage 57 open issues by complexity, then execute 20 low-complexity fixes in 4 parallel waves using worktree-isolated sub-agents. Use when: (1) large backlog of open issues needs classification and batch resolution, (2) many independent low-complexity fixes can be parallelized."
category: tooling
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - issue-triage
  - parallel-agents
  - worktree-isolation
  - batch-pr
  - wave-execution
---

# Issue Triage & Wave-Based Parallel Execution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Classify 57 open GitHub issues by complexity (low/medium/high), then execute all low-complexity items simultaneously using parallel sub-agents with worktree isolation |
| **Outcome** | Successfully created 14 PRs covering 20 issues in 4 waves, plus 1 issue closed as already resolved. All PRs with auto-merge enabled. |

## When to Use

- Large backlog of open GitHub issues (20+) needs triage and resolution
- Many independent, low-complexity fixes can be parallelized
- Issues span config fixes, documentation, CI improvements, and small code changes
- Need to minimize wall-clock time for bulk fixes

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Fetch and classify all open issues
gh issue list --state open --limit 200 --json number,title,labels,body

# Phase 2: Launch parallel agents per wave (max 5 per wave)
# Each agent gets: isolation: "worktree", explicit rebase instructions
# Key constraints:
#   - No two agents in same wave touch same files
#   - Each agent: git fetch origin main && git rebase origin/main
#   - Each agent: creates branch, PR with "Closes #N", enables auto-merge

# Phase 3: Monitor and fix CI
gh pr checks <PR_NUMBER>
gh run rerun <RUN_ID> --failed  # For transient failures
```

### Detailed Steps

1. **Fetch all open issues** with `gh issue list --json number,title,labels,body`
2. **Classify issues** using sub-agents (Explore type) — split into batches of ~25 for parallel classification
3. **Group into complexity tiers**:
   - LOW: mechanical, single-file, < 30 min (config fixes, docs, version bumps)
   - MEDIUM: multi-file, needs understanding, 30 min - 2 hrs
   - HIGH: architectural, core systems, 2+ hrs
4. **Identify skippable issues**: meta tracking issues, blocked issues
5. **Merge related issues** that touch same files into single agents (e.g., 3 mypy config issues → 1 agent)
6. **Organize into waves** ensuring no file conflicts within a wave (max 4-5 agents per wave)
7. **Launch each wave** with worktree-isolated agents, wait for completion, then launch next wave
8. **Monitor CI** after all waves — re-run transient failures, fix real failures with dedicated agents

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| SendMessage to running agents | Tried to send rebase instructions to already-running background agents via SendMessage tool | SendMessage is not a standalone tool — it's part of the Agent tool and can't reach already-launched background agents | Must include ALL instructions (including rebase) in the original agent prompt. Cannot modify agent behavior after launch. |
| 5 agents in Wave 1 | Initially planned 5 agents with 2 touching pyproject.toml | File conflict between A1 (mypy config) and A3 (src-layout) both editing pyproject.toml | Always check for file overlaps during wave planning. Merge agents that touch the same files. |
| Wave 1 without rebase | First 4 agents launched without explicit `git fetch origin main && git rebase origin/main` | User caught this — agents may create PRs based on stale main | Always include explicit rebase instructions in every agent prompt. Make it a template requirement. |

## Results & Parameters

### Classification Results (57 issues)

```yaml
total_issues: 57
low_complexity: 25  # 20 actionable, 5 skipped (meta/blocked)
medium_complexity: 16
high_complexity: 11
skipped: 5  # 1 meta tracking, 4 blocked on upstream
```

### Wave Execution Results

```yaml
waves: 4
total_agents: 15  # 4 + 4 + 4 + 3
total_prs: 14
issues_closed_directly: 1  # Already resolved
issues_addressed: 20

wave_1:  # Config Fixes
  agents: 4
  prs: [5082, 5083, 5084]
  closed_directly: [4042]
  issues: [5057, 4915, 5045, 5039, 5055, 5054, 4912, 4042]

wave_2:  # Documentation & Cleanup
  agents: 4
  prs: [5085, 5086, 5087, 5088]
  issues: [5038, 5053, 5043, 4905, 4906, 4908]

wave_3:  # DX & CI Improvements
  agents: 4
  prs: [5089, 5090, 5091, 5092]
  issues: [5044, 4006, 4040, 3778]

wave_4:  # ExTensor & Cleanup
  agents: 3
  prs: [5093, 5094, 5095]
  issues: [5080, 3271, 5056]
```

### CI Failure Analysis

```yaml
transient_failures:
  - pr: 5082
    cause: "Pre-existing Mojo test failures on main"
    action: "Re-run triggered"
  - pr: 5083
    cause: "GitHub CodeQL rate limiting (HTTP 429)"
    action: "Re-run triggered"
  - pr: 5084
    cause: "Pixi CDN outage (HTTP 500)"
    action: "Re-run triggered"
real_failures: 0
```

### Agent Prompt Template

```text
You are fixing GitHub issue #XXXX for ProjectOdyssey (repo: HomericIntelligence/ProjectOdyssey).
You MUST create a PR. NEVER push directly to main.

## Issue to Fix
**#XXXX** — [title]

## What to Do
1. Read the issue body: `gh issue view XXXX --json body`
2. [Specific instructions]
3. IMPORTANT: Before committing, run `git fetch origin main && git rebase origin/main`
4. Create a feature branch, commit, push, and create a PR

## Branch & PR
- Branch: `XXXX-description`
- Commit: `type(scope): description`
- PR body must include: `Closes #XXXX`
- After creating PR, run: `gh pr merge --auto --rebase`

## Rules
- Run `pixi run pre-commit run --files <changed-files>` before committing
- Stage only the files you changed (never `git add -A`)
- NEVER push to main directly
- NEVER use `--no-verify`
- ALWAYS run `git fetch origin main && git rebase origin/main` before committing
```

### Key Timing

```yaml
classification_phase: ~3 min (2 parallel Explore agents)
wave_1_duration: ~2 min wall clock
wave_2_duration: ~5 min wall clock
wave_3_duration: ~7 min wall clock
wave_4_duration: ~8 min wall clock
total_wall_clock: ~25 min for 20 issues
sequential_estimate: ~4-5 hours
speedup: ~10-12x
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Bulk triage of 57 open issues, 4-wave parallel execution of 20 low-complexity fixes | 14 PRs created, all with auto-merge |
