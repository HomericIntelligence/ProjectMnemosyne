---
name: multi-branch-rebase-workflow
description: >-
  Parallel multi-branch rebase with semantic conflict resolution and batch PR creation.
  Includes prevention: ALWAYS branch from origin/main to avoid stale bases. Use when:
  (1) creating feature branches (always from origin/main), (2) multiple branches need
  rebasing, (3) semantic conflict resolution needed, (4) batch PR creation after rebase,
  (5) rebase conflicts are purely markdown table separator style differences.
category: tooling
date: 2026-05-02
version: 2.1.0
user-invocable: false
verification: verified-local
history: multi-branch-rebase-workflow.history
---
# Multi-Branch Rebase Workflow

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Objective** | Rebase N branches onto main with semantic conflict resolution |
| **Approach** | Triage by complexity, parallelize simple rebases, delegate complex merges to sub-agents |
| **Outcome** | All 8 branches rebased, 6 PRs created with auto-merge enabled |
| **Duration** | Single session |

## When to Use

- **Before creating any feature branch** -- use Step 0 to branch from `origin/main` and avoid stale bases entirely
- **Especially in submodules** -- submodule checkouts are often on detached HEAD at old pins, not on `main`
- Multiple feature branches have fallen behind main and need rebasing
- Some branches have conflicts that require semantic understanding (not just accept-theirs/ours)
- Batch PR creation is needed after rebase
- Branches have varying complexity: some empty (already on main), some trivial, some with 20+ conflicts
- Rebase conflicts are purely markdown table separator style — `main` uses `:---` (markdownlint-compliant) and branches use `-------` (plain dashes)

## Verified Workflow

### Step 0: Prevention -- Always Branch from origin/main (CRITICAL)

**Most rebase conflicts are avoidable.** The single biggest cause of batch rebase pain is
creating branches from stale starting points instead of from `origin/main`.

```bash
# CORRECT -- Always do this before creating a feature branch:
git fetch origin main
git checkout -b my-feature-branch origin/main   # Branch FROM origin/main, not HEAD

# For submodules specifically (often on detached HEAD at old pins):
cd submodule/
git fetch origin main
git checkout -b chore/my-fix origin/main   # NOT from detached HEAD
```

**NEVER do this:**
```bash
git checkout -b my-feature-branch           # Branches from HEAD which may be stale
git checkout -b my-feature-branch origin    # Ambiguous, may resolve to old ref
```

**Why this matters for submodules:**
In a meta-repo like Odysseus, submodule checkouts are pinned to specific SHAs (often
weeks or months behind main). If you `cd` into a submodule and create a branch from
the current HEAD, your branch starts from the old pin -- not from current main. Every
commit that landed on main since that pin becomes a potential conflict.

**Observed failure rate (2026-04-03):** 5 out of 5 PRs created from stale submodule
HEADs had merge conflicts. All were fixable by rebasing onto origin/main, but the
entire rebase wave was avoidable if branches had been created from origin/main initially.

### Quick Reference

```bash
# 0. ALWAYS start from origin/main
git fetch origin main
git checkout -b my-feature origin/main

# 1. Triage branches by complexity
for branch in $BRANCHES; do
  git log --oneline main..$branch | wc -l  # commits ahead
  git merge-tree $(git merge-base main $branch) main $branch | grep -c '<<<<'  # conflict count
done

# 2. Simple rebase (skip-only or trivial)
git worktree add /tmp/rebase-NAME BRANCH
cd /tmp/rebase-NAME && git rebase main
git rebase --skip  # if commit already on main
git push --force-with-lease origin BRANCH

# 3. Complex rebase (delegate to sub-agent for 20+ conflicts)
# 4. Batch PR creation
for branch in $BRANCHES; do
  gh pr create --head $branch --title "..." --body "..."
  gh pr merge $PR_NUM --auto --rebase
done
```

### Step 1: Analyze and Triage

Before rebasing, categorize each branch:

| Category | Description | Strategy |
| ---------- | ------------- | ---------- |
| **Empty** | All commits already on main | Rebase + skip, no PR needed |
| **Trivial** | 1-2 small conflicts (docstrings, imports) | Resolve inline with Edit tool |
| **Complex** | 20+ conflicts requiring semantic understanding | Delegate to sub-agent |

### Step 2: Parallel Worktree Setup

Use git worktrees to rebase multiple branches simultaneously:

```bash
# Current branch can be rebased in-place
git rebase main

# Other branches use worktrees
git worktree add /tmp/rebase-NAME BRANCH
cd /tmp/rebase-NAME && git rebase main
```

Key constraints:
- Cannot create worktree for the currently checked-out branch
- Worktrees share the same git objects, so branch operations are visible across worktrees
- Clean up worktrees after each rebase: `git worktree remove /tmp/rebase-NAME`

### Step 3: Conflict Resolution Strategies

**Skip-only (empty branches)**: When main already has the same fix:
```bash
git rebase main  # conflicts appear
git rebase --skip  # commit becomes empty, skip it
```

**Trivial conflicts**: Use Edit tool to resolve conflict markers directly.

**Markdown table separator conflicts** (`:---` vs `-------`): When main enforces markdownlint-compliant `:---` separators and branches use plain `-------` dashes, the conflict is purely formatting. Resolution rule:
- **Always keep main's `:---` style** (it is markdownlint-compliant; `-------` fails CI)
- This can appear multiple times across separate rebase commits — resolve identically each time
- For **content+formatting conflicts** (branch changed real content AND separator style): keep the branch's content data, but use main's `:---` separator style

```bash
# Example conflict block — always resolve by keeping HEAD (main) version for separators:
# <<<<<<< HEAD
# | Col A | Col B |
# | :--- | :--- |
# =======
# | Col A | Col B |
# | ------- | ------- |
# >>>>>>> branch-commit
# Resolution: use the :--- version from HEAD
```

**Complex semantic merges (20+ conflicts)**: Delegate to a general-purpose sub-agent with explicit resolution rules per conflict group. Provide:
- The file path and conflict count
- Category of each conflict group (e.g., "arithmetic operators", "save/load methods")
- Explicit resolution rule per group ("keep branch's inlined lambdas", "keep main's tensor_io imports")

### Step 4: Push with --force-with-lease

Always use `--force-with-lease` instead of `--force`:
```bash
git push --force-with-lease origin BRANCH
```

Safety Net (and good practice) blocks `--force` to prevent accidental history destruction.

### Step 5: Batch PR Creation

For branches with commits ahead of main:
```bash
gh pr create --head BRANCH --title "..." --body "Closes #ISSUE ..."
gh pr merge PR_NUM --auto --rebase
```

Skip PRs for empty branches (0 commits ahead of main).

### Step 6: Cleanup

```bash
# Remove the temp worktree for this branch
git worktree remove /tmp/rebase-NAME

# Prune stale worktree refs (no-op if only main worktree remains)
git worktree prune
```

Note: `git worktree prune` is always safe to run. If no stale worktrees exist it exits silently. It does NOT remove existing worktrees or delete branches.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `git push --force` | Force-push after rebase | Safety Net hook blocked it as destructive | Always use `--force-with-lease` for safer force push |
| `git rebase --continue --no-edit` | Skip editor during rebase continue | `--no-edit` is not a valid git rebase flag | Use `GIT_EDITOR=true git rebase --continue` instead |
| Parallel worktree for current branch | `git worktree add /tmp/X CURRENT_BRANCH` | Git error: branch already checked out | Rebase current branch in-place, use worktrees only for other branches |
| All parallel tool calls in one block | Starting 4 worktree creates + rebase together | One failure cancels all parallel calls | Separate worktree creation from rebase, or handle errors gracefully |
| Branched from detached HEAD in submodule | `git checkout -b chore/fix` from detached HEAD at old pin | Branch was based on stale commit, main had 3-10 new commits with governance files and CI fixes | Always `git fetch origin main` then branch from `origin/main` explicitly |
| Branched from current branch without fetch | `git checkout -b feat/x` on submodule's current branch | Current branch was behind main | Specify `origin/main` as the start point |
| Assumed main hadn't moved | Didn't fetch before branching | Main had governance files, CI fixes, coverage improvements merged since submodule pin | Always `git fetch origin main` first, even if you think main is up to date |
| Kept `-------` separator in markdown conflict | Resolved markdown table separator conflict by keeping branch's `-------` style | Fails markdownlint MD055/table rules in CI | Always use main's `:---` separator style — it is the markdownlint-compliant form |
| Treated 0-commits-ahead branch as needing PR | Rebased branch that turned out to be identical to main | Branch's content was already merged; rebase left 0 commits ahead | Check `git log --oneline origin/main..BRANCH` before creating a PR — skip if empty |

## Results & Parameters

### Configuration

```yaml
branches_total: 8
branches_already_done: 3  # by prior sub-agents
branches_empty: 2  # 3680-auto-impl, 3751-auto-impl (already on main)
branches_trivial: 2  # 3742-sequential-mlp (1 docstring), fix/20-dropout-backward (1 skip + 1 clean)
branches_complex: 1  # 4513-auto-impl (26 conflicts in extensor.mojo)
prs_created: 6
auto_merge_enabled: true
push_strategy: --force-with-lease
```

### Conflict Resolution Rules for 4513-auto-impl

```yaml
# 26 conflicts in shared/core/extensor.mojo
arithmetic_operators:  # 14 conflicts
  main: "from .arithmetic import add"  # deferred import
  branch: "@always_inline fn _add[T: DType]..."  # inline lambda
  resolution: keep_branch  # core circular-import fix

reflected_inplace_operators:  # 6 conflicts
  main: "from .arithmetic import subtract; var result = subtract(self, other)"
  branch: "var result = self.__sub__(other)"
  resolution: keep_branch

abs_operator:  # 1 conflict
  resolution: keep_branch  # uses _extensor_abs helper

hash_import:  # 1 conflict
  resolution: keep_main  # deferred import still needed in __hash__

save_load:  # 2 conflicts
  resolution: keep_main  # tensor_io module is proper factoring

split_docstring:  # 1 conflict
  resolution: keep_main  # branch had copy-paste error

final_block:  # 1 large conflict
  resolution: keep_both  # main's split/split_with_indices + branch's helpers
```

### Markdown Separator Conflict Pattern (2026-05-02 Session)

```yaml
# ProjectMnemosyne — 3 branches, all conflicts were markdown table separator style
branches_total: 3
conflict_type: markdown_table_separators  # :--- (main) vs ------- (branch)
branches_with_formatting_only_conflicts: 2
branches_already_on_main: 1  # skill/radiance-sol-dtype-serving-estimates-v1-1 (0 commits ahead)
resolution_rule: always_keep_main_style  # :--- is markdownlint-compliant
worktree_pattern: /tmp/rebase-<slug>  # one per branch, removed after push
push_strategy: --force-with-lease
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 8 branches, 26-conflict semantic merge, 2026-04-03 | Full semantic rebase including submodule detached HEAD fix |
| ProjectMnemosyne | 3 branches, markdown separator conflicts only, 2026-05-02 | All conflicts were `:---` vs `-------` table separator style |
