---
name: batch-low-difficulty-issue-impl
description: 'Classify, deduplicate, and batch-implement 15-30 low-difficulty GitHub
  issues (doc edits, text fixes, trivial cleanup) in a single session. Use when: (1)
  a large backlog of open issues needs triage, (2) many issues are pure doc/text changes,
  (3) duplicate issues need closing before implementation. Includes worktree-safe grep
  pattern for ALREADY-DONE verification and correct pre-filter order.'
category: tooling
date: 2026-04-23
version: 1.3.0
user-invocable: false
verification: verified-ci
history: batch-low-difficulty-issue-impl.history
---
# Batch Low-Difficulty Issue Implementation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-23 |
| **Objective** | Classify, deduplicate, and batch-implement low-difficulty GitHub issues using worktree-isolated agents |
| **Outcome** | Verified: worktree isolation works correctly; correct pre-filter order; ALREADY-DONE grep must exclude worktrees |
| **Verification** | verified-ci |
| **History** | [changelog](./batch-low-difficulty-issue-impl.history) |

### Session (2026-04-23) — HomericIntelligence/Odysseus 35-Issue Triage

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-04-23 | Classify 35 open Odysseus issues, implement all SIMPLE ones as 1-issue-per-PR using Myrmidon swarm (Haiku agents with isolation=worktree) | 19 issues resolved (17 PRs + 2 ALREADY-DONE closures), 13 merged; remaining auto-merging. Meta-repo with 12 submodule symlinks. |

### Prior session (2026-03-06)

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

**Classification tiers** (apply pre-filters in this order: DUPLICATE → ALREADY-DONE → verify-before-fix → LOW):

| Tier | Criteria | Action |
|------|----------|--------|
| DUPLICATE | Same change as another open issue | `gh issue close N --comment "Duplicate of #M"` |
| ALREADY-DONE | Change already in codebase | Grep (with worktree exclusion) to verify, then close with comment |
| LOW | Single-file doc/text/comment edit, no logic | Implement in batch |
| MEDIUM | Test additions, audits, single-module refactor | Skip this phase |
| HIGH | New features, backward passes, complex bugs | Skip this phase |

**Pre-filter order matters**: Close DUPLICATEs and ALREADY-DONEs first to keep the final LOW count accurate. Run a verify-before-fix pass as a distinct phase — not as part of Haiku classification — before launching fix agents.

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

**CRITICAL — Branch base check before dispatching agents:**

Before spawning any worktree-isolated agents, verify the main conversation is on `main`:
```bash
git branch --show-current  # Must be 'main'; if not, worktrees will inherit wrong base
```

If L0 is on a feature branch, include this as **step 1** in every Haiku agent prompt:
```bash
git fetch origin
git checkout -B <issue-number>-<slug> origin/main  # Explicit base, not inherited
```

This prevents "This branch can't be rebased" errors caused by unrelated commits from the L0's current branch silently appearing in agent branches.

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

For issues claiming a change is needed, grep first — and always exclude worktrees:

```bash
# CORRECT: exclude worktrees and git internals
grep -rn "pattern" /path/to/repo/ \
  --include="*.py" --include="*.toml" --include="*.yml" \
  --exclude-dir=".git" \
  --exclude-dir=".worktrees" \
  --exclude-dir=".claude"

# WRONG: plain grep picks up stale worktree content — gives false "still present" signals
grep -rn "pattern" /path/to/repo/
```

Stale worktrees contain old branch state from prior work. If you grep without excluding them:
- An issue that claims "remove stale `--cov` flag" may appear as still present because the flag exists in a worktree from a prior branch — but is already gone from main.
- A dependency pin done via direct curl (not in a config file) may not appear in `pixi.toml` but the worktree shows an old pinned version string.

```bash
# If no matches in main tree → change already done → close with verification comment
gh issue close NNNN --comment "Verified: already resolved. [pattern] not found in main tree. Closing."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sub-agent isolation with `isolation="worktree"` parameter (2026-03-06) | Launched 5 parallel agents expecting each to work in its own worktree | Agents edited files in the main worktree, not isolated worktrees; all 5 changes landed in the main worktree | The `isolation="worktree"` parameter does not guarantee sub-agents work in separate git worktrees; they share the working directory. Use git stash to separate their changes post-facto. (Note: this failure did NOT occur in the 2026-04-12 session — may be environment-specific; see Results.) |
| Sub-agents completing full git workflow (2026-03-06) | Asked sub-agents to create branches, commit, push, and create PRs | Agents completed the file edits but did not execute the git commands (output descriptions instead) | Sub-agents reliably edit files but frequently skip the git+PR workflow. Always execute git operations in the main agent after sub-agents return. (Note: NOT observed in 2026-04-12 session with worktree isolation — all 12 agents completed full git workflow.) |
| Reading files after `git checkout -b` from stash | Assumed `git checkout stash -- file` would have the correct content immediately | The `git checkout stash` command works correctly but the branch check showed "branch already exists" because a previous stash attempt created it | Check for existing branches with `git branch --list` before creating; use `git checkout existing-branch` if it exists. |
| Running `pixi run pre-commit run <specific-file>` | Tried to run hooks on only the changed file | Hook IDs don't match file paths — the command fails with "No hook with id path/to/file" | Always run `pixi run pre-commit run --all-files`, never by file path. |
| Grepping for ALREADY-DONE without worktree exclusion (2026-04-12) | Plain `grep -rn pattern /repo/` to detect whether issue content still exists | Worktrees contain stale branch state — gave false "still present" for #1655 (nats-server) and #1671 (--cov refs) | Always pass `--exclude-dir=.worktrees --exclude-dir=.claude --exclude-dir=.git` when grepping for ALREADY-DONE verification |
| Running verify-before-fix as part of Haiku classification (2026-04-12) | Expected Haiku to catch all ALREADY-DONE issues during the classification pass | Haiku missed 2 ALREADY-DONE issues (4.7% miss rate) where implementation was in a different location than the issue title implied | Always run verify-before-fix as a distinct separate phase after Haiku classification, not as part of it |
| Haiku agents with `isolation: "worktree"` dispatched while L0 was on a non-main branch (`15-exporter-port-9101`) | Agents created worktrees and checked out branches, which inherited the L0's current branch as base | Worktrees start from the current HEAD of the base repo — not from `origin/main` — so each branch silently included 4-5 unrelated commits. GitHub refused rebase merge: "This branch can't be rebased." | Always verify L0 is on `main` before dispatching worktree agents, OR explicitly include `git fetch origin && git checkout -B <branch> origin/main` as step 1 in every agent prompt instead of relying on worktree inheritance |
| PR number collision from parallel agents (2026-04-23) | Two parallel agents working in HomericIntelligence/Odysseus simultaneously both reported "PR #120" in their output | Agents report their own in-flight view of PR numbers, which can be stale when two agents race to create PRs in the same repo; both PRs existed but with different numbers | Always run `gh pr list --author "@me" --state all` after each wave to get ground-truth PR numbers — never trust agent-reported PR numbers |
| Worktree creation failure on symlink-heavy repo (2026-04-23) | Agent for issue #58 failed during worktree creation with "Updating files: X%" timeout error | HomericIntelligence/Odysseus has 12 submodule symlinks; worktree checkout can time out on repos with many symlinks when many files must be resolved | Fallback: `git checkout -b <branch> origin/main` in main worktree directly, push the branch, then `git checkout <original-branch>` to return afterward |
| Agent branch naming drift (2026-04-23) | Agent for issue #18 used branch `18-fix-runbook` instead of the specified `18-auto-impl` convention | Haiku agents sometimes derive branch names from the issue title rather than following the `<N>-auto-impl` convention when the convention is only mentioned as a note rather than an explicit command | Explicitly spell out the exact branch name in every agent prompt as an imperative: "Run: git checkout -b 18-auto-impl origin/main" — never rely on the agent interpreting a naming convention |
| Two agents merging into same PR branch (2026-04-23) | Agents for #50 and #53 (both in Wave A1 parallel) both committed to branch `50-auto-impl` | Parallel worktree agents targeting similar branch names in the same repo; the worktrees may have been assigned the same directory, causing both agents to commit to the same branch | Use distinct, non-overlapping branch names per agent; verify each agent's branch with `gh pr list` after the wave; both issues still closed correctly but PR was messy |

## Results & Parameters

### Session Statistics (2026-03-06) — ProjectOdyssey

| Metric | Value |
|--------|-------|
| Issues triaged | 165 |
| Duplicates closed | 9 |
| Already-done closed | 2 (#3227, #3195) |
| LOW PRs created | 15 |
| PRs failing pre-commit | 0 |
| Issues combined into single PR | 6 (two multi-issue PRs) |
| Total wall-clock time | ~90 minutes |

### Session Statistics (2026-04-12) — ProjectScylla 64-Issue Pass

| Metric | Value |
|--------|-------|
| Issues classified by Haiku | 64 |
| Haiku ALREADY-DONE miss rate | 4.7% (3 false negatives) |
| ALREADY-DONE caught by verify-before-fix pass | 3 (including #1655, #1671 caught by worktree-excluded grep) |
| Waves | 4 |
| PRs created | 12 |
| PRs merged CI-green | 11 |
| Agent git-op failures | 0 — all 12 Sonnet agents completed full branch/commit/push/PR/auto-merge |
| Worktree isolation failures | 0 — agents worked in isolated worktrees, not main tree |

**Note on `isolation="worktree"` reliability**: In this session on ProjectScylla (Python/pixi repo), `Task(isolation="worktree")` worked correctly — agents created branches and PRs in isolated worktrees without polluting the main worktree. The failure mode documented in the 2026-03-06 session (agents editing main worktree) did NOT occur. Hypothesis: the failure may be environment-specific. Always verify that each PR was created from the correct branch, not from main.

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
| ProjectScylla | 64-issue myrmidon swarm pass, 4 waves, 12 PRs (2026-04-12) | 11/12 PRs merged CI-green; worktree isolation worked correctly; verify-before-fix caught 3 ALREADY-DONE issues |
| HomericIntelligence/Odysseus | 35-issue triage, 19 resolved (17 PRs + 2 ALREADY-DONE), meta-repo with 12 submodule symlinks (2026-04-23) | 0 git-op failures; worktree creation timeout on symlink-heavy repo (fallback to main worktree); parallel agents reported colliding PR numbers; Haiku branch naming drift to title-slug form |
