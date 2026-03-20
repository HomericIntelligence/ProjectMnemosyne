---
name: issue-triage-and-fix
description: Bulk triage and fix GitHub issues in parallel using isolated worktrees.
  Use when you have 10+ simple open GitHub issues, many may be duplicates, and each
  fix is independent.
category: evaluation
date: 2026-02-22
version: 1.0.0
user-invocable: true
---
# Skill: Issue Triage and Bulk Fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Bulk-close duplicates and create parallel PRs for simple open GitHub issues |
| Outcome | SUCCESS — 5 issues closed, 16 PRs created, all with auto-merge |

## When to Use

- You have 10+ open GitHub issues that are simple one-file fixes
- Issues were auto-generated as follow-ups and many may be duplicates
- You want to process them efficiently without merge conflicts
- Each fix is independent (no cross-issue dependencies)

## Verified Workflow

### Step 0: Triage First (Always)

Before writing any code, audit all issues:

```bash
gh issue list --repo <org>/<repo> --state open --limit 100 --json number,title,body
```

Identify and close:
- **Duplicates**: Close with `gh issue comment <n> --body "Duplicate of #X"` + `gh issue close <n>`
- **Already fixed**: Verify in code, then close with explanation
- **Superseded**: Close referencing the superseding issue

### Step 1: Pre-Execution Analysis

Group remaining issues by:
1. **File touched** — issues touching the same file must be in the same agent OR sequential waves
2. **Risk level** — "investigate first" issues go in a later wave
3. **Type** — code fixes / docs fixes / config fixes can often run fully in parallel

### Step 2: Wave-Based Parallel Execution

Launch up to 5 agents per wave using `isolation: "worktree"`:

```
Wave 1: Simplest single-file changes (5 agents)
Wave 2: Slightly more complex, different files (5 agents)
Wave 3: Config/CI changes (5 agents)
Wave 4: Audit/investigate-first issues (3 agents)
```

### Step 3: Per-Agent Template

Each agent prompt must include:

1. Create branch: `git switch -c <issue>-<slug>`
2. Read target file(s) before editing
3. Make minimal change
4. Run **targeted** pre-commit (NOT `--all-files`):
   ```bash
   pre-commit run ruff --all-files
   pre-commit run mypy-check-python --all-files
   ```
5. Run unit tests: `<package-manager> run python -m pytest tests/unit/ -q --no-cov 2>&1 | tail -20`
6. Stage **only** changed files: `git add <specific files>`
7. Commit with conventional format
8. Push + create PR: `gh pr create --title "..." --body "Closes #<n>"`
9. Enable auto-merge: `gh pr merge --auto --rebase`

### Step 4: Handle Audit Issues

For "audit and fix" issues:
- Run the grep/search first
- If nothing found → close issue with comment, no PR needed
- If found → fix and create PR

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Configuration

```
Agent type:     Bash with isolation: "worktree"
Wave size:      5 parallel agents max
Auto-merge:     gh pr merge --auto --rebase (always)
Pre-commit:     Targeted only (ruff + mypy-check-python)
Test command:   <package-manager> run python -m pytest tests/unit/ -q --no-cov
Branch naming:  <issue-number>-<short-slug>
```

### Issue Type → Approach Mapping

```
Duplicate issues      → Close with comment, no PR
Already fixed         → Verify in code, close with comment
Simple code fix       → Wave 1-2, single agent
Docs/config fix       → Wave 2-3, single agent
Same-file conflicts   → Merge into single PR
Audit issues          → Wave 4, grep first
Investigate-first     → Wave 4, read + analyze before fixing
```

### PR Template

```bash
gh pr create \
  --title "type(scope): Brief description" \
  --body "One-line explanation of the fix.

Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Related Skills

- `parallel-worktree-workflow` — foundational worktree setup pattern
- `parallel-pr-workflow` — systematic multi-PR creation workflow
- `deduplicate-issues` — focused duplicate-detection approach

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | 5 issues closed, 16 PRs created across 4 waves with auto-merge | [session-notes.md](../../references/session-notes.md) |
