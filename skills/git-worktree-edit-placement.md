---
name: git-worktree-edit-placement
description: 'Correct workflow for editing files in the right git worktree when multiple
  worktrees share the same monorepo. Use when: editing files that may land in the
  wrong branch, changes appear in main instead of a feature worktree, or a push is
  rejected due to a diverged remote.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | In a monorepo with many git worktrees, file edits made to absolute paths land in whichever worktree contains those paths — which may not be the intended feature branch |
| **Risk** | Edits intended for a feature branch silently modify `main`; remote push is rejected because the feature branch has diverged |
| **Resolution** | Always check `git branch --show-current` for the directory you are editing; copy files to the correct worktree if needed, then revert the wrong location |

## When to Use

- Starting implementation in a worktree (e.g. `.worktrees/issue-N/`) when absolute paths map to the main repo root
- After making edits and discovering `git status` in the worktree shows no changes
- When `git push` is rejected with "fetch first" on the feature branch
- When pre-commit hooks or CI run from the wrong directory

## Verified Workflow

1. **Confirm your worktree** — before any edit, verify which branch holds the target files:

   ```bash
   git -C /path/to/worktree branch --show-current
   # Should print the feature branch name, e.g. 3086-auto-impl
   ```

2. **Edit files inside the worktree path**, e.g. `/repo/.worktrees/issue-N/shared/core/file.mojo`
   — not the main repo path `/repo/shared/core/file.mojo`

3. **Verify changes landed correctly**:

   ```bash
   git -C /path/to/worktree diff --stat
   ```

4. **If edits went to the wrong location** (main repo instead of worktree):

   ```bash
   # Copy edited files to the correct worktree
   cp /repo/shared/core/file.mojo /repo/.worktrees/issue-N/shared/core/file.mojo

   # Revert the accidental changes in main
   git -C /repo checkout -- shared/core/file.mojo
   ```

5. **Commit from inside the worktree** (or using `-C`):

   ```bash
   git -C /path/to/worktree add shared/core/file.mojo
   git -C /path/to/worktree commit -m "type(scope): message"
   ```

6. **If push is rejected** due to diverged remote, fetch and rebase — do NOT force-push:

   ```bash
   git -C /path/to/worktree fetch origin <branch>
   git -C /path/to/worktree log --oneline HEAD..origin/<branch>  # inspect remote commits
   git -C /path/to/worktree reset --hard HEAD~1  # drop local duplicate
   git -C /path/to/worktree pull --rebase origin <branch>
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit files via absolute path in main repo | Used `Read`/`Edit` on `/repo/shared/core/extensor.mojo` from a session rooted in `.worktrees/issue-N/` | Changes landed on `main` branch, not the feature branch | Always resolve absolute paths relative to the worktree root, or verify CWD branch first |
| Push feature branch after editing wrong location | Ran `git push` on feature branch without copying changes over | Push rejected: remote had commits the local branch lacked | Check `git diff --stat` in the worktree before pushing |
| Force-push to fix diverged branch | Considered `git push --force` | Would overwrite legitimate remote commits (prior automation run) | Fetch remote, inspect, then `reset --hard` + `pull --rebase` |

## Results & Parameters

**Key diagnostics** — run these before and after editing to catch placement errors early:

```bash
# Which branch is each worktree on?
git worktree list

# Is the worktree clean or does main have our changes?
git -C /repo diff --stat HEAD                        # main repo
git -C /repo/.worktrees/issue-N diff --stat          # feature worktree

# Check remote state of feature branch
git -C /repo/.worktrees/issue-N log --oneline HEAD..origin/<branch>
```

**Recovery snippet** (copy-paste when changes landed in wrong location):

```bash
WORKTREE="/repo/.worktrees/issue-N"
FILES="shared/core/extensor.mojo tests/shared/core/test_extensor_slicing.mojo"

# Copy to correct worktree
for f in $FILES; do cp "/repo/$f" "$WORKTREE/$f"; done

# Revert main
git -C /repo checkout -- $FILES

# Verify
git -C "$WORKTREE" diff --stat
```
