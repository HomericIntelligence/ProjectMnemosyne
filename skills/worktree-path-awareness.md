---
name: worktree-path-awareness
description: 'Identifies and edits files in the correct git worktree path. Use when:
  editing files inside a git worktree, commits show no staged changes after editing,
  or working in .worktrees/ subdirectories.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| Category | documentation |
| Trigger | File edit produces no staged changes on commit |
| Root Cause | Edited main repo path instead of worktree path |
| Fix | Always resolve working directory and edit the absolute worktree path |

## When to Use

- You are working inside a git worktree (e.g., `/repo/.worktrees/issue-NNN/`)
- After editing a file and attempting `git commit`, git reports "nothing to commit"
- The task prompt references a file path under the main repo root (e.g., `/home/user/ProjectOdyssey/tests/...`) but your CWD is the worktree
- Any situation where `git status` shows no changes but you believe you made edits

## Verified Workflow

1. **Determine actual working directory** before any file edit:
   ```bash
   pwd
   # or
   git rev-parse --show-toplevel
   ```

2. **Construct the correct absolute path** using the worktree root, not the main repo root:
   ```
   # WRONG: /home/user/ProjectOdyssey/tests/shared/training/test_training_loop.mojo
   # RIGHT: /home/user/ProjectOdyssey/.worktrees/issue-3094/tests/shared/training/test_training_loop.mojo
   ```

3. **Verify the file exists at the worktree path** before editing:
   ```bash
   ls /path/to/worktree/tests/shared/training/
   ```

4. **Edit the file at the worktree-absolute path** using the Read then Edit tools.

5. **Confirm changes are staged** before committing:
   ```bash
   git diff HEAD <file>
   # or
   git status
   ```

6. **Commit only after confirming staged changes are present.**

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit main repo file | Called Edit on `/home/mvillmow/Odyssey2/tests/shared/training/test_training_loop.mojo` | The worktree at `.worktrees/issue-3094/` has its own copy; the main repo edit was unrelated to the current branch | Always resolve `git rev-parse --show-toplevel` or use `pwd` to determine the worktree root before editing |
| Commit after wrong edit | Ran `git add <file> && git commit` | Git reported "nothing to commit" because the staged file was from the main repo, not the worktree branch | Verify `git diff HEAD <file>` shows changes before committing |

## Results & Parameters

### Correct Pattern

```bash
# Step 1: Find your actual root
WORKTREE_ROOT=$(git rev-parse --show-toplevel)
# e.g., /home/mvillmow/Odyssey2/.worktrees/issue-3094

# Step 2: Construct file path
FILE="$WORKTREE_ROOT/tests/shared/training/test_training_loop.mojo"

# Step 3: Verify file exists
ls "$FILE"

# Step 4: Edit with Read→Edit tools using $FILE as absolute path

# Step 5: Confirm and commit
git diff HEAD "$FILE"
git add "$FILE"
git commit -m "docs: update file"
```

### Key Rule

When a task prompt gives a file path like `/home/user/ProjectOdyssey/tests/...` but you are working in a worktree at `/home/user/ProjectOdyssey/.worktrees/issue-NNN/`, **the correct path is the worktree-prefixed version**, not the main repo path.
