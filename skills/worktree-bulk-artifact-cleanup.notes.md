# Session Notes: Worktree Bulk Artifact Cleanup

## Date: 2026-03-10

## Context

23 worktrees in ProjectOdyssey had "uncommitted changes" flagged during a worktree audit.
Analysis revealed 22 of 23 only had `__pycache__/*.pyc` and/or `ProjectMnemosyne/` directories
— generated artifacts, not real source code.

One worktree (issue-3203) had actual uncommitted changes to `README.md` and
`docs/dev/release-process.md`, but these were destructive (replacing real content with
placeholder text like "Description here.").

## Steps Taken

1. **First attempt**: Used `find + rm -rf` to delete `__pycache__` dirs from all worktrees.
   This caused tracked `.pyc` files to appear as "D" (deleted) in `git status`.

2. **Fix**: Ran `git checkout -- .` in each worktree to restore tracked files, then
   `git clean -fd` to remove only untracked artifacts.

3. **Issue 3203**: Discarded destructive placeholder changes with targeted
   `git checkout -- README.md docs/dev/release-process.md`.

4. **Missing PRs**: Pushed 6 branches and created PRs with `gh pr create` + auto-merge.

5. **Empty worktree**: Removed issue-3252 (no changes from main) with `git worktree remove`.

## Issues Encountered

### Tracked vs Untracked __pycache__

The `.pyc` files were tracked in git (committed at some point). When deleted from disk with
`rm -rf`, git reported them as deleted files. The fix was:

```bash
# Pass 1: Restore tracked files
git checkout -- .

# Pass 2: Remove untracked artifacts
git clean -fd --quiet
```

### Worktrees outside scope

After cleaning the 23 target worktrees, 4 other worktrees (3349, 3392, 3430, 3511) still had
`ProjectMnemosyne/` directories. These were outside the scope of this task.

## PRs Created

| Issue | PR | Title |
|-------|----|-------|
| 3198 | #4475 | feat(scripts): add PNG/JPEG to IDX conversion script |
| 3228 | #4476 | fix(migrate): copy auxiliary subdirectories |
| 3229 | #4477 | feat(scripts): add --audit flag for migration coverage |
| 3230 | #4478 | fix(skills): handle Quick Reference section transformation |
| 3307 | #4479 | feat(ci): automate test count badge |
| 3309 | #4480 | test(scripts): add unit tests for migrate_odyssey_skills |

## Worktree Removed

- issue-3252: No changes from main, branch `3252-auto-impl` deleted