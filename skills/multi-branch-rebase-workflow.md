---
name: multi-branch-rebase-workflow
description: 'Parallel multi-branch rebase with semantic conflict resolution and batch
  PR creation. Use when: (1) multiple branches need rebasing, (2) semantic conflict
  resolution needed, (3) batch PR creation after rebase.'
category: tooling
date: 2026-03-19
version: 1.0.0
user-invocable: false
---
# Multi-Branch Rebase Workflow

## Overview

| Attribute | Value |
|-----------|-------|
| **Objective** | Rebase N branches onto main with semantic conflict resolution |
| **Approach** | Triage by complexity, parallelize simple rebases, delegate complex merges to sub-agents |
| **Outcome** | All 8 branches rebased, 6 PRs created with auto-merge enabled |
| **Duration** | Single session |

## When to Use

- Multiple feature branches have fallen behind main and need rebasing
- Some branches have conflicts that require semantic understanding (not just accept-theirs/ours)
- Batch PR creation is needed after rebase
- Branches have varying complexity: some empty (already on main), some trivial, some with 20+ conflicts

## Verified Workflow

### Quick Reference

```bash
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
|----------|-------------|----------|
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
git worktree remove /tmp/rebase-NAME
git worktree prune
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git push --force` | Force-push after rebase | Safety Net hook blocked it as destructive | Always use `--force-with-lease` for safer force push |
| `git rebase --continue --no-edit` | Skip editor during rebase continue | `--no-edit` is not a valid git rebase flag | Use `GIT_EDITOR=true git rebase --continue` instead |
| Parallel worktree for current branch | `git worktree add /tmp/X CURRENT_BRANCH` | Git error: branch already checked out | Rebase current branch in-place, use worktrees only for other branches |
| All parallel tool calls in one block | Starting 4 worktree creates + rebase together | One failure cancels all parallel calls | Separate worktree creation from rebase, or handle errors gracefully |

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
