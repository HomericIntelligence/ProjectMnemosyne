# References: PR Rebase Pipeline

## Session Context

- **Project**: ProjectScylla
- **Date**: 2026-02-23
- **Root Cause**: `pip-audit --min-severity high` is not a valid flag — all Security CI checks failed
- **Scale**: 71 open issues, 8 open PRs all blocked, 13 issues resolved in one session

## Key Commands Used

```bash
# Inspect failing CI log
gh run view <run-id> --log-failed | head -50

# Rebase a branch in its worktree
git -C <worktree-path> fetch origin
git -C <worktree-path> rebase origin/main

# Handle pixi.lock conflict during rebase
git -C <worktree-path> checkout --theirs pixi.lock
git -C <worktree-path> add pixi.lock
GIT_EDITOR=true git -C <worktree-path> rebase --continue
cd <worktree-path> && pixi install
git -C <worktree-path> add pixi.lock
git -C <worktree-path> commit -m "fix(deps): regenerate pixi.lock after rebase on main"

# Enable auto-merge immediately after PR creation
gh pr merge --auto --rebase

# Clean up merged worktrees
git worktree remove <path>
git worktree prune
```

## PR Series

- #1029: Fix pip-audit flag (blocker)
- #1030–#1040: 13 issue fixes in 5 waves

## pixi.lock Notes

Every branch that changes `pyproject.toml` or that rebases over a commit that did must regenerate `pixi.lock`. The safe pattern:
1. Take `--theirs` during conflict (main's lock is valid)
2. Run `pixi install` to update for your branch's deps
3. Commit the regenerated lock separately