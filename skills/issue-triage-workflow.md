---
name: issue-triage-workflow
description: "Use when: (1) large backlog of GitHub issues (10+) needs triage and resolution, (2) many independent low-complexity fixes can be parallelized across worktree-isolated agents, (3) issues may be stale or already implemented and need verification before coding, (4) bulk issue closure with wave-based parallel execution is needed"
category: tooling
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Issue Triage Workflow

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated workflow for bulk GitHub issue triage: verify before implementing, classify by complexity, and execute in parallel waves using worktree-isolated agents |
| Outcome | Merged from 3 skills covering bulk triage+fix, verification before implementation, and wave-based parallel execution |
| Verification | unverified |

## When to Use

- 10+ open GitHub issues that may be simple one-file fixes
- Issues were auto-generated as follow-ups and many may be duplicates or already resolved
- Issue references prior work or sub-issues that may have already been implemented
- Issue says "implement **or document status**" — verify current state before coding
- Large backlog (20+ issues) needs classification and batch resolution to minimize wall-clock time
- Each fix is independent (no cross-issue dependencies)

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Fetch and triage
gh issue list --state open --limit 200 --json number,title,labels,body

# Phase 2: Verify before implementing (for issues referencing prior work)
grep -r "fn <function>" <path>    # Check if already implemented
grep -r "TODO.*#ISSUE_NUM" --include="*.mojo" .  # Find stale references

# Phase 3: Launch parallel agents per wave (max 4-5 per wave, no file conflicts)
# Each agent uses: isolation: "worktree"
# Each agent must: git fetch origin main && git rebase origin/main

# Phase 4: Monitor CI
gh pr checks <PR_NUMBER>
gh run rerun <RUN_ID> --failed  # For transient failures
```

### Step 0: Verify Before Implementing

**Always check current state before writing any code**:

1. **Check if referenced files/functions exist**:
   ```bash
   grep -r "fn <function_name>" <path>
   grep -r "<SymbolName>" <path> --include="*.mojo"
   ```

2. **Check if functions are already exported**:
   ```bash
   grep "<function_name>" shared/core/__init__.mojo
   ```

3. **Run existing tests FIRST** before writing any code:
   ```bash
   NATIVE=1 just test-group "tests/shared/core" "test_shape.mojo"
   ```

4. **Search for stale TODO references** to the issue:
   ```bash
   grep -r "TODO.*#ISSUE_NUM\|Blocked on #ISSUE_NUM\|pending.*#ISSUE_NUM" --include="*.mojo" .
   ```

5. **Check git log for recent related commits**:
   ```bash
   git log --oneline --all | grep -i "<keyword>"
   ```

**Key insight**: If the issue says "already implemented" for some categories or has a detailed plan that may be outdated, verify each item. File paths in issues go stale as code evolves.

### Step 1: Triage All Issues First

Before writing any code, audit all issues:

```bash
gh issue list --repo <org>/<repo> --state open --limit 100 --json number,title,body
```

Identify and close:
- **Duplicates**: `gh issue comment <n> --body "Duplicate of #X"` + `gh issue close <n>`
- **Already fixed**: Verify in code, then close with explanation
- **Already implemented**: Close with comment noting where it was implemented
- **Superseded**: Close referencing the superseding issue

### Step 2: Classify by Complexity

Group remaining issues into tiers:
- **LOW**: Mechanical, single-file, < 30 min (config fixes, docs, version bumps, stale TODOs)
- **MEDIUM**: Multi-file, needs understanding, 30 min - 2 hrs
- **HIGH**: Architectural, core systems, 2+ hrs
- **SKIP**: Meta tracking issues, blocked on upstream

Split into batches of ~25 for parallel classification with Explore-type sub-agents.

### Step 3: Plan Wave Execution

Group LOW complexity issues into waves:

1. **Check for file conflicts**: Issues touching the same file must be in the same agent OR sequential waves
2. **Merge related issues**: 3 issues touching `pyproject.toml` → 1 agent
3. **Wave size**: Max 4-5 agents per wave
4. **Wave ordering**:
   - Wave 1: Simplest single-file changes (config, docs)
   - Wave 2: Slightly more complex, different files
   - Wave 3: CI/config changes
   - Wave 4: Audit/investigate-first issues

### Step 4: Launch Each Wave with Worktree-Isolated Agents

**Agent prompt template** (include ALL instructions upfront — cannot modify after launch):

```text
You are fixing GitHub issue #XXXX for <Project> (repo: <org>/<repo>).
You MUST create a PR. NEVER push directly to main.

## Issue to Fix
**#XXXX** — [title]

## What to Do
1. Read the issue body: `gh issue view XXXX --json body`
2. IMPORTANT: Before committing, run `git fetch origin main && git rebase origin/main`
3. [Specific fix instructions]

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

**Per-agent steps**:
1. Create branch: `git switch -c <issue>-<slug>`
2. Read target file(s) before editing
3. Make minimal change
4. Run targeted pre-commit (NOT `--all-files`):
   ```bash
   pre-commit run ruff --all-files
   pre-commit run mypy-check-python --all-files
   ```
5. Stage **only** changed files: `git add <specific files>`
6. Commit with conventional format
7. Push + create PR: `gh pr create --title "..." --body "Closes #<n>"`
8. Enable auto-merge: `gh pr merge --auto --rebase`

### Step 5: Handle Audit Issues

For "audit and fix" issues:
- Run the grep/search first
- If nothing found → close issue with comment, no PR needed
- If found → fix and create PR

### Step 6: Monitor CI After All Waves

```bash
gh pr checks <PR_NUMBER>
gh run rerun <RUN_ID> --failed  # For transient failures (CodeQL rate limiting, CDN outages)
```

Distinguish transient CI failures (pre-existing on main, network issues) from real failures caused by the PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Starting to implement without verifying | Read issue plan suggesting operations needed implementation | All functions already existed with full test coverage | Always verify current state before coding; issues filed weeks/months ago may describe problems already solved |
| Looking for files by stale path | Issue referenced `shared/core/extensor.mojo:23-28` | File didn't exist — was renamed or never created | File paths in issues go stale; always glob/grep to find current locations |
| Searching for old issue number refs | Expected `#2717-#2721` TODO references in code | A previous commit had already cleaned these up | Check git log for recent related commits before starting work |
| SendMessage to running agents | Tried to send rebase instructions to already-running background agents | SendMessage is not a standalone tool — can't reach already-launched agents | Include ALL instructions (including rebase) in the original agent prompt |
| 5 agents with file conflict in Wave 1 | Planned 5 agents with 2 touching pyproject.toml | File conflict between agents both editing pyproject.toml | Always check for file overlaps during wave planning; merge conflicting agents |
| Wave 1 without rebase instruction | First 4 agents launched without explicit rebase | Agents created PRs based on stale main | Always include explicit rebase instructions in every agent prompt |

## Results & Parameters

### Configuration

```yaml
agent_type: "Bash with isolation: worktree"
wave_size: "4-5 parallel agents max"
auto_merge: "gh pr merge --auto --rebase"
pre_commit: "Targeted only (ruff + mypy-check-python)"
test_command: "<package-manager> run python -m pytest tests/unit/ -q --no-cov"
branch_naming: "<issue-number>-<short-slug>"
```

### Issue Type → Approach Mapping

```
Duplicate issues       → Close with comment, no PR
Already fixed          → Verify in code, close with comment
Stale TODOs only       → Update comment/docstring, create PR
Simple code fix        → Wave 1-2, single agent
Docs/config fix        → Wave 2-3, single agent
Same-file conflicts    → Merge into single agent/PR
Audit issues           → Wave 4, grep first
Investigate-first      → Wave 4, read + analyze before fixing
```

### PR Template

```bash
gh pr create \
  --title "type(scope): Brief description" \
  --body "One-line explanation of the fix.

Closes #<issue-number>"
gh pr merge --auto --rebase
```

### Timing Benchmarks (57-issue triage session)

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

### Stale TODO Update Pattern

```
# Before: TODO pointing to consolidated/closed issue
# TODO(#3013): implement when from_array() ships

# After: TODO pointing to specific tracking issue
# TODO(#4127): implement when from_array() ships
```

**Verify cleanup is complete**:
```bash
grep -r "TODO.*#OLD_ISSUE_NUM" --include="*.mojo" .  # Should return empty
```
