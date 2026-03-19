---
name: batch-low-difficulty-issue-impl
description: 'Classify, deduplicate, and batch-implement 15-30 low-difficulty GitHub
  issues (doc edits, text fixes, trivial cleanup) in a single session. Use when: (1)
  a large backlog of open issues needs triage, (2) many issues are pure doc/text changes,
  (3) duplicate issues need closing before implementation.'
category: tooling
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Batch Low-Difficulty Issue Implementation

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-06 | Classify 165 open issues, close 9 duplicates, implement 22 LOW issues | 15 PRs merged, 11 issues closed (9 dup + 2 already-done), 0 pre-commit failures |

## When to Use

- (1) Repository has 30+ open issues without PRs and a sprint/cleanup session is planned
- (2) A significant fraction of issues are doc-only changes (README updates, comment fixes, docstring additions)
- (3) You suspect duplicate issues exist that should be closed before work begins
- (4) Issues span many different files with minimal cross-file dependencies
- (5) CI pre-commit hooks are stable (no known broken hooks)

## Verified Workflow

### Phase 1: Classify Issues (30-60 min)

Use an Explore sub-agent to read and classify all open issues:

```bash
# Get full list with labels
gh issue list --state open --limit 200 --json number,title,labels,body | head -300

# For batches, read 20-30 at a time
gh issue list --state open --limit 30 --skip 0 --json number,title,labels
```

**Classification tiers**:

| Tier | Criteria | Action |
|------|----------|--------|
| DUPLICATE | Same change as another open issue | `gh issue close N --comment "Duplicate of #M"` |
| ALREADY-DONE | Change already in codebase | Grep to verify, then close with comment |
| LOW | Single-file doc/text/comment edit, no logic | Implement in batch |
| MEDIUM | Test additions, audits, single-module refactor | Skip this phase |
| HIGH | New features, backward passes, complex bugs | Skip this phase |

**LOW difficulty signals**:
- Title starts with "Update", "Fix typo", "Add note", "Document", "Remove stale"
- Issue body says "change X to Y" or "add one line to docstring"
- Affects only `.md`, `README.md`, or docstring lines (not function logic)
- Expected diff: < 20 lines

### Phase 2: Close Duplicates First

Batch close duplicates before any implementation. This prevents wasted work and keeps
issue count accurate:

```bash
# Close all duplicates in one pass (run in parallel if possible)
gh issue close 3331 --comment "Duplicate of #3321 (both update the historical note in agents/hierarchy.md)"
gh issue close 3256 --comment "Duplicate of #3273 (both add __hash__ tests)"
# ... etc
```

**Duplicate detection pattern**: Look for pairs of issues with nearly identical titles.
Group by target file — issues touching the same file with similar descriptions are usually duplicates.

### Phase 3: Group by Target File

Before branching, group LOW issues by which file they edit. Issues sharing a file
**must go in the same PR** (to avoid merge conflicts):

```
PR 1: agents/hierarchy.md → closes #3321, #3322
PR 2: CLAUDE.md           → closes #3325, #3326, #3367, #3216
PR 3: extensor.mojo       → closes #3290 first, then #3192 in separate PR
```

Issues touching different files can be implemented in parallel.

### Phase 4: Stash-Based Multi-File Workflow

When sub-agents modify the main worktree (not isolated worktrees), use git stash
to separate changes into per-issue branches:

```bash
# 1. Let agents edit all files in main worktree
# 2. Stash all changes together
git stash

# 3. For each issue:
git checkout -b NNNN-auto-impl origin/main
git checkout stash -- path/to/changed/file.mojo
pixi run pre-commit run --all-files
git add path/to/changed/file.mojo
git commit -m "type(scope): description\n\nCloses #NNNN\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin NNNN-auto-impl
gh pr create --title "..." --body "Closes #NNNN"
gh pr merge --auto --rebase
```

### Phase 5: Per-PR Workflow (Standard)

For files not in the stash, create branches directly:

```bash
git fetch origin && git checkout -b NNNN-auto-impl origin/main
# read file BEFORE editing
# make edit
pixi run pre-commit run --all-files  # must pass
git add <file>
git commit -m "type(scope): description

Closes #NNNN

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin NNNN-auto-impl
gh pr create --title "type(scope): description" --body "Closes #NNNN"
gh pr merge --auto --rebase
```

### Phase 6: Verify Already-Done Issues

For issues claiming a change is needed, grep first:

```bash
grep -n "fn main" shared/core/loss_utils.mojo
# If no matches → change already done → close with verification comment
gh issue close NNNN --comment "Verified: already resolved in commit XXXXXXXX. Closing."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sub-agent isolation with `isolation="worktree"` parameter | Launched 5 parallel agents expecting each to work in its own worktree | Agents edited files in the main worktree, not isolated worktrees; all 5 changes landed in the main worktree | The `isolation="worktree"` parameter does not guarantee sub-agents work in separate git worktrees; they share the working directory. Use git stash to separate their changes post-facto. |
| Sub-agents completing full git workflow | Asked sub-agents to create branches, commit, push, and create PRs | Agents completed the file edits but did not execute the git commands (output descriptions instead) | Sub-agents reliably edit files but frequently skip the git+PR workflow. Always execute git operations in the main agent after sub-agents return. |
| Reading files after `git checkout -b` from stash | Assumed `git checkout stash -- file` would have the correct content immediately | The `git checkout stash` command works correctly but the branch check showed "branch already exists" because a previous stash attempt created it | Check for existing branches with `git branch --list` before creating; use `git checkout existing-branch` if it exists. |
| Running `pixi run pre-commit run <specific-file>` | Tried to run hooks on only the changed file | Hook IDs don't match file paths — the command fails with "No hook with id path/to/file" | Always run `pixi run pre-commit run --all-files`, never by file path. |

## Results & Parameters

### Session Statistics (2026-03-06)

| Metric | Value |
|--------|-------|
| Issues triaged | 165 |
| Duplicates closed | 9 |
| Already-done closed | 2 (#3227, #3195) |
| LOW PRs created | 15 |
| PRs failing pre-commit | 0 |
| Issues combined into single PR | 6 (two multi-issue PRs) |
| Total wall-clock time | ~90 minutes |

### Branch Naming Convention

```
NNNN-auto-impl   (where NNNN = primary issue number)
```

### Commit Message Template

```
type(scope): brief description

Closes #NNNN
[Closes #MMMM if combined PR]

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Issue Classification Heuristics

```
LOW if ALL of:
  - Title has: "Update", "Document", "Fix typo", "Remove stale", "Add note"
  - Body has: single file target
  - Expected diff: < 20 lines
  - No logic/behavior change (only text/comments/docs)

DUPLICATE if:
  - Same target file as another open issue
  - Same or nearly same description
  - No unique work required beyond the kept issue

ALREADY-DONE if:
  - Issue says "remove X" → grep for X → not found
  - Issue says "add Y to Z" → grep for Y in Z → already present
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 165-issue backlog cleanup, March 2026 | [notes.md](../references/notes.md) |
