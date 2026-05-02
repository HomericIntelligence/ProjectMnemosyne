---
name: worktree-lifecycle-create-switch-sync
description: "Use when: (1) creating isolated git worktrees for parallel development, (2) switching between worktrees without stashing context, (3) syncing feature branches with remote/main, (4) editing files in a worktree and getting 'nothing to commit', (5) detecting when a worktree prompt's work is already done."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [worktree, git, parallel, path-awareness, stale-detection]
---
# Worktree Lifecycle: Create, Switch, Sync

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-03-28 | Consolidated worktree lifecycle skills | Merged from worktree-create, worktree-switch, worktree-sync, worktree-path-awareness, worktree-prompt-already-done |

Covers the full lifecycle of a git worktree: creation, navigation, syncing with upstream, path
gotchas when editing files inside nested worktrees, and detecting when a prompt's task is
already complete before doing redundant work.

## When to Use

- Starting work on a new issue that needs isolation from other branches
- Working on multiple issues in parallel without stashing/context switching overhead
- Long-running feature branches that need to stay in sync with main
- After editing a file inside a worktree and `git commit` reports "nothing to commit"
- When invoked with a `.claude-prompt-<N>.md` and you suspect the auto-impl pipeline already ran

## Verified Workflow

### Quick Reference

```bash
# Create worktree for a new branch
git worktree add <path>/<name>-<issue>-<description> -b <branch-name>
# or with create script
<project-root>/scripts/create_worktree.sh <issue-number> <description>

# List all worktrees
git worktree list

# Switch (simple cd — no stashing needed)
cd ../<project-name>-42-feature

# Fetch and sync with main (rebase preferred)
git fetch origin
git rebase origin/main

# Resolve your actual worktree root before editing files
git rev-parse --show-toplevel
```

### Creating a Worktree

```bash
# Basic creation
git worktree add ../<project-name>-42-implement-feature -b 42-implement-feature

# Naming convention: <issue-number>-<kebab-case-description>
# Place under parent directory:
# parent/
# ├── <project>/            # main worktree (main branch)
# ├── <project>-42-feature/ # issue worktree
# └── <project>-99-exp/     # experimental worktree

# Verify
git worktree list
```

**Phase-based pattern for related issues:**

```bash
# Phase 1: Plan (sequential — must complete first)
git worktree add ../<project>-62-plan -b 62-plan

# Phase 2: Parallel (after plan merges)
git worktree add ../<project>-63-tests -b 63-tests
git worktree add ../<project>-64-impl -b 64-impl

# Phase 3: Cleanup (after parallel phases merge)
git worktree add ../<project>-66-cleanup -b 66-cleanup
```

### Switching Between Worktrees

```bash
# List available worktrees
git worktree list

# Switch — just cd
cd ../<project-name>-42-feature

# Verify branch
git branch

# Optional aliases for convenience
alias wt='git worktree list'
alias wtcd='cd $(git worktree list | fzf | awk "{print \$1}")'

# Tmux sessions (persistent per worktree)
tmux new -s issue-42 -c ../<project-name>-42-feature
tmux attach -t issue-42
```

### Syncing a Worktree with Main

```bash
# Fetch from remote (works from any worktree)
git fetch origin

# Update main worktree
cd ../<project> && git pull origin main

# Rebase feature branch onto main (preferred — linear history)
cd ../<project>-42-feature && git rebase origin/main

# If conflicts occur during rebase
git status           # identify conflicted files
# edit files to resolve
git add <file>
git rebase --continue
# or abort
git rebase --abort

# Merge approach (when preserving branch history)
git merge origin/main
```

| Approach | Use When |
| ---------- | ---------- |
| Rebase | Linear history preferred (default for most projects) |
| Merge | Preserving branch topology / public branches |

### Path Awareness: Editing the Right Files

**Critical gotcha**: if you edit a file using the main-repo absolute path while your working
directory is a worktree, git will report "nothing to commit" because the edit landed in a
different copy of the repo.

```bash
# Step 1: Determine the ACTUAL worktree root
WORKTREE_ROOT=$(git rev-parse --show-toplevel)
# e.g., /home/user/ProjectOdyssey/.worktrees/issue-3094

# Step 2: Construct file path from the worktree root
FILE="$WORKTREE_ROOT/tests/shared/training/test_training_loop.mojo"
# WRONG: /home/user/ProjectOdyssey/tests/shared/training/test_training_loop.mojo
# RIGHT: /home/user/ProjectOdyssey/.worktrees/issue-3094/tests/shared/training/test_training_loop.mojo

# Step 3: Verify file exists at worktree path
ls "$FILE"

# Step 4: After editing, confirm changes are staged
git diff HEAD "$FILE"
git status
# => File should show as modified, not "nothing to commit"
```

**Rule**: When a task prompt gives a path like `/home/user/Project/tests/...` but your CWD
is inside `.worktrees/issue-NNN/`, always prepend the worktree root — not the main repo root.

### Detecting Already-Done Work (Stale Prompts)

When invoked via a `.claude-prompt-<N>.md` file, always verify the work is not already done:

```bash
# 1. Read the prompt to get issue number, branch, task description
cat .claude-prompt-<N>.md

# 2. Check recent git history FIRST (< 1 second)
git log --oneline -5
# If HEAD commit message matches the task description → work already done

# 3. Verify the expected target state
ls <expected-directory>          # for deletion tasks: file should be absent
# or spot-check relevant files for other tasks

# 4. Check for an existing PR
gh pr list --head <branch-name>
# If OPEN PR exists → done, awaiting review

# 5. Report clearly
# - Commit hash that completed the work
# - PR number and status
# - No further action needed
```

| git log result | PR exists | Action |
| ---------------- | ----------- | -------- |
| HEAD matches task | Yes (OPEN) | Report complete, no action |
| HEAD matches task | No | Check if merged; may need to create PR |
| HEAD does NOT match | No | Proceed with implementation |
| HEAD does NOT match | Yes (OPEN) | Check PR diff; may be partial |

**Time saved**: Without verification ~10 tool calls; with verification ~4 tool calls (~10 sec).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Edit main repo file while in worktree | Called Edit on `/home/user/Project/tests/file.mojo` | Worktree has its own copy; the main repo edit was unrelated to current branch | Always run `git rev-parse --show-toplevel` before editing to get the worktree root |
| Commit after wrong-path edit | Ran `git add <file> && git commit` | "Nothing to commit" — staged file was from main repo, not worktree branch | Verify `git diff HEAD <file>` shows changes before committing |
| Start implementation without checking git log | Read prompt, planned to search for imports | File was already deleted in HEAD commit | Always run `git log --oneline -3` before any planning |
| Check only directory listing for completion | Confirmed file was absent | Correct but incomplete — needed to also confirm PR exists | Combine directory check with `gh pr list --head <branch>` |
| N/A (worktree create/switch/sync) | Direct approach worked | N/A | Solution was straightforward |

## Results & Parameters

### Worktree Directory Structure

```
parent-directory/
├── <project>/                         # Main worktree (main branch)
├── <project>-42-tensor-ops/           # Issue #42 worktree
├── <project>-73-bugfix/               # Issue #73 worktree
└── <project>-99-experiment/           # Experimental worktree
```

### Error Reference

| Error | Solution |
| ------- | ---------- |
| Branch already exists | Use different branch name or delete old branch |
| Directory already exists | Choose different location or remove directory |
| Each branch checked out in ONE worktree | Cannot use same branch in two worktrees |
| "nothing to commit" after edit | Path confusion — resolve root with `git rev-parse --show-toplevel` |

### Best Practices

- One worktree per issue (don't share branches)
- Use descriptive names: `<issue-number>-<description>`
- All worktrees share the same `.git` directory
- Clean up after PR merge (see `worktree-cleanup-branches-artifacts` skill)
- Fetch regularly to catch conflicts early
- Keep feature branches short-lived (2-3 days max)
- Resolve conflicts immediately, don't let them accumulate

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3060, branch `3060-auto-impl`, stale prompt detection | Path awareness and prompt detection patterns |
| ProjectScylla | Multiple parallel issue workflows | Create/switch/sync workflow |
