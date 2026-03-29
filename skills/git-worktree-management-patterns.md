---
name: git-worktree-management-patterns
description: "Use when: (1) creating isolated git worktrees for parallel development on multiple issues, (2) switching between worktrees without stashing, (3) syncing feature branches with main, (4) cleaning up single or multiple stale worktrees after PRs merge, (5) removing all worktrees in bulk after parallel development sessions, (6) fixing file edits that landed in the wrong worktree, (7) parsing git worktree list --porcelain output programmatically, (8) fixing worktree creation failures due to stale origin/HEAD or missing origin/main, (9) fixing branch name collisions in parallel E2E test runs"
category: tooling
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# git-worktree-management-patterns

Consolidated skill for all git worktree patterns: creation, switching, syncing, cleanup (single and mass), correct file edit placement, programmatic path detection from porcelain output, stale origin/HEAD fallback fixes, and branch name collision fixes in parallel automation.

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated skill covering all git worktree creation, use, and cleanup patterns |
| Outcome | Merged from 7 skills: cleanup, collision-fix, edit-placement, mass-cleanup, path-detection, stale-origin-head-fallback, workflow |
| Verification | unverified |

## When to Use

- Starting work on a new issue in parallel with other ongoing work
- Need to work on multiple issues simultaneously without stashing
- After parallel wave execution where agents used worktree isolation
- `git worktree list` shows worktrees for merged PR branches
- Cleaning up nested agent-in-agent worktrees (depth 2 or 3)
- File edits landed in main instead of the intended feature branch
- `git push` rejected on feature branch due to diverged remote
- Parsing `git worktree list --porcelain` output to find paths by branch name
- `git worktree add` fails with exit 128 referencing `origin/main`
- `git symbolic-ref refs/remotes/origin/HEAD --short` returns "not a symbolic ref"
- Branch name collisions in parallel E2E test runs (`fatal: A branch named '...' already exists`)
- After mass parallel auto-implementation sessions leaving 20+ worktrees

## Verified Workflow

### Quick Reference

```bash
# Create worktree for new issue
git worktree add .worktrees/issue-<N> -b <N>-feature-name

# List all worktrees
git worktree list

# Switch to worktree (just cd)
cd <repo>/.worktrees/issue-<N>

# Confirm you're on the right branch
git -C <worktree-path> branch --show-current

# Sync feature branch with main
git fetch origin && git -C <worktree> rebase origin/main

# Remove single worktree
git worktree remove <path>

# Prune stale entries
git worktree prune

# Fix stale origin/HEAD
git fetch origin && git remote set-head origin --auto
```

### Creating Worktrees

```bash
# Create worktree on new branch
git worktree add .worktrees/issue-<N> -b <N>-auto-impl

# Create worktree tracking existing remote branch
git worktree add .worktrees/issue-<N> <branch-name>

# List all worktrees
git worktree list
```

**Best practices:**
- One worktree per issue — do not share branches
- Naming: `.worktrees/issue-<N>` for issue-based work, `.claude/worktrees/agent-<id>` for agent isolation
- Each branch can only be checked out in ONE worktree at a time

**Example directory structure:**
```
repo/
├── (main worktree — main branch)
├── .worktrees/
│   ├── issue-42/    (42-feature branch)
│   └── issue-73/    (73-bugfix branch)
```

### Switching Between Worktrees

```bash
# List all worktrees
git worktree list

# Switch (simple cd — no stash needed)
cd <repo>/.worktrees/issue-<N>

# Verify current branch
git branch --show-current

# Quick navigation with fzf (if installed)
cd $(git worktree list | fzf | awk '{print $1}')
```

Terminal aliases for convenience:
```bash
alias wt='git worktree list'
alias wtcd='cd $(git worktree list | fzf | awk "{print \$1}")'
```

### Syncing Feature Branches with Main

```bash
# Fetch latest (works from any worktree)
git fetch origin

# Rebase feature branch (preferred — linear history)
git -C .worktrees/issue-<N> rebase origin/main

# Force push after rebase (required)
git -C .worktrees/issue-<N> push --force-with-lease origin <branch>

# If conflicts during rebase
git status  # see conflicted files
# ... fix files ...
git add .
git rebase --continue

# Abort if needed
git rebase --abort
```

### Correct File Edit Placement

**Problem**: File edits made to absolute paths land in whichever worktree contains those paths — which may not be the intended feature branch.

**Before editing, always verify the target branch:**
```bash
git -C <worktree-path> branch --show-current
# Must print the feature branch name, e.g. 3086-auto-impl
```

**Edit files inside the worktree path:**
```bash
# WRONG (lands on main if main repo is at /repo)
/repo/shared/core/file.mojo

# CORRECT
/repo/.worktrees/issue-N/shared/core/file.mojo
```

**If edits went to the wrong location:**
```bash
WORKTREE="/repo/.worktrees/issue-N"
FILES="shared/core/file.mojo tests/shared/core/test_file.mojo"

# Copy to correct worktree
for f in $FILES; do cp "/repo/$f" "$WORKTREE/$f"; done

# Revert main
git -C /repo checkout -- $FILES

# Verify
git -C "$WORKTREE" diff --stat
```

**If push is rejected due to diverged remote:**
```bash
git -C <worktree> fetch origin <branch>
git -C <worktree> log --oneline HEAD..origin/<branch>  # inspect remote commits
git -C <worktree> reset --hard HEAD~1  # drop local duplicate
git -C <worktree> pull --rebase origin <branch>
```

Do NOT force-push — fetch and rebase instead.

### Single Worktree Cleanup

Remove deepest-nested first (depth 3 → 2 → 1):

```bash
# For nested agent worktrees: remove children before parents
git worktree remove ".claude/worktrees/agent-A/.claude/worktrees/agent-B/.claude/worktrees/agent-C"
git worktree remove ".claude/worktrees/agent-A/.claude/worktrees/agent-B"
git worktree remove ".claude/worktrees/agent-A"

# For issue worktrees with untracked ProjectMnemosyne dirs
rm -rf ".worktrees/issue-N/ProjectMnemosyne"  # clean first, avoids --force
git worktree remove ".worktrees/issue-N"

# Prune stale metadata
git worktree prune

# Delete local branch (try safe delete first)
git branch -d <branch>        # safe: refuses unmerged
git branch -D <branch>        # force: needed for rebase-merged PRs

# Verify
git worktree list
git branch
```

**Safety Net interaction**: `git worktree remove --force` is blocked when untracked files are present. Delete untracked directories first, then remove without `--force`.

### Mass Cleanup (20+ worktrees)

```bash
# Phase 1: Audit
git worktree list
git branch -v  # [gone] = remote deleted = merged

# Phase 2: Remove stale worktrees (merged PRs)
STALE="3033 3061 3062 3063"
for issue in $STALE; do
  rm -rf ".worktrees/issue-$issue/ProjectMnemosyne" \
         ".worktrees/issue-$issue/.issue_implementer"
  git worktree remove ".worktrees/issue-$issue" 2>/dev/null || true
  git branch -D "${issue}-auto-impl" 2>/dev/null || true
done

# Phase 3: Check active worktrees for uncommitted changes
ACTIVE="3071 3077 3083"
for issue in $ACTIVE; do
  wt=".worktrees/issue-$issue"
  status=$(git -C "$wt" status --short 2>&1)
  if [ -n "$status" ]; then
    echo "=== $issue has changes ==="
    echo "$status"
  fi
done

# Phase 4: Remove active worktrees
for issue in $ACTIVE; do
  wt=".worktrees/issue-$issue"
  rm -rf "$wt/ProjectMnemosyne"
  git worktree remove "$wt" 2>/dev/null || \
    git worktree remove --force "$wt"
done

# Phase 5: Final cleanup
git worktree prune
git fetch --prune
git branch -v | grep '\[gone\]' | awk '{print $1}' | xargs git branch -D
git checkout main && git pull origin main

# Verify
git worktree list    # only main repo
git branch -v        # main + open PR branches only
git status           # clean
ls .worktrees/       # empty
```

**Key insight**: Use `git branch -D` (not `-d`) for rebase-merged PRs — rebase leaves no merge commit, so `-d` refuses with "not fully merged".

### Programmatic Path Detection from Porcelain Output

`git worktree list --porcelain` outputs multi-line blocks:
```text
worktree /home/user/repo/.worktrees/issue-3198
HEAD 38f3c196...
branch refs/heads/3198-auto-impl
```

**Wrong** — extracts the ref, not the path:
```bash
WORKTREE_PATH=$(git worktree list --porcelain | grep "branch.*/$BRANCH$" | awk '{print $2}')
# Returns: refs/heads/3198-auto-impl  ← WRONG
```

**Correct** — tracks preceding worktree line:
```bash
WORKTREE_PATH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v branch="$BRANCH" '/^worktree /{path=$2} /^branch / && $2 ~ "/" branch "$" {print path}')
# Returns: /home/user/repo/.worktrees/issue-3198  ← CORRECT
```

Extracting branch name from worktree path:
```bash
WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
```

### Automated Stale Worktree Cleanup Pattern

Safe cleanup loop (checks dirty state and open PRs before removing):

```bash
while IFS= read -r WT_PATH; do
    [ -z "$WT_PATH" ] && continue
    [ "$WT_PATH" = "$MAIN_REPO_ROOT" ] && continue

    WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
      awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
    [ -z "$WT_BRANCH" ] && continue

    # Skip if dirty
    [ -n "$(git -C "$WT_PATH" status --porcelain 2>/dev/null)" ] && continue

    # Skip if has open PR
    OPEN_PRS=$(gh pr list --head "$WT_BRANCH" --state open --json number 2>/dev/null)
    [ -n "$OPEN_PRS" ] && [ "$OPEN_PRS" != "[]" ] && continue

    # Safe to remove
    git worktree remove "$WT_PATH" 2>/dev/null
    git branch -d "$WT_BRANCH" 2>/dev/null  # -d (safe), NOT -D
done < <(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')

git worktree prune 2>/dev/null
```

### Fixing Stale origin/HEAD and Missing origin/main

**Symptoms**: `git worktree add -b <name> <path> origin/main` fails with exit 128; `WorktreeManager` logs "Could not auto-detect base branch"; repos renamed from `master` to `main` on GitHub but local clone only tracks `origin/master`.

```bash
# Fix single repo
git -C "$HOME/<repo>" fetch origin
git -C "$HOME/<repo>" remote set-head origin --auto
git -C "$HOME/<repo>" symbolic-ref refs/remotes/origin/HEAD --short  # verify: "origin/main"
git -C "$HOME/<repo>" checkout main

# Bulk fix for multiple repos
for repo in Repo1 Repo2 Repo3; do
    git -C "$HOME/$repo" fetch origin
    git -C "$HOME/$repo" remote set-head origin --auto
    git -C "$HOME/$repo" checkout main
    git -C "$HOME/$repo" branch -d master 2>/dev/null || true
done
```

**Diagnostic commands:**
```bash
# Check if origin/HEAD is set
git symbolic-ref refs/remotes/origin/HEAD --short 2>&1
# Success: "origin/main"
# Failure: "fatal: ref refs/remotes/origin/HEAD is not a symbolic ref"

# Check what remote branches exist locally
git branch -r

# Check GitHub's actual default branch
gh api repos/<OWNER>/<REPO> --jq '.default_branch'
```

**WorktreeManager hardening** — replace hardcoded `"origin/main"` fallback with branch probing:
```python
if base_branch is None:
    try:
        result = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"], ...)
        base_branch = result.stdout.strip()
    except Exception:
        for candidate in ("origin/main", "origin/master"):
            try:
                run(["git", "rev-parse", "--verify", candidate], ...)
                base_branch = candidate
                break
            except Exception:
                continue
        if base_branch is None:
            base_branch = "origin/main"
```

### Fixing Branch Name Collisions in Parallel E2E Runs

**Symptom**: `fatal: A branch named 'T0_00_run_01' already exists` — branch names are not experiment-scoped; parallel runs collide.

**Fix**: Prefix branch names with experiment ID:

```python
# workspace_setup.py
def _setup_workspace(..., experiment_id: str = "") -> None:
    exp_prefix = experiment_id[:8] if experiment_id else ""
    if exp_prefix:
        branch_name = f"{exp_prefix}_{tier_id.value}_{subtest_id}_run_{run_number:02d}"
    else:
        branch_name = f"{tier_id.value}_{subtest_id}_run_{run_number:02d}"

# subtest_executor.py — pass experiment_id at call site
_setup_workspace(..., experiment_id=self.config.experiment_id)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit files via absolute path in main repo | Used Read/Edit on main repo path from session rooted in worktree | Changes landed on main branch, not feature branch | Always verify CWD branch with `git -C <dir> branch --show-current` before editing |
| Push feature branch after editing wrong location | Ran `git push` without copying changes to correct worktree | Push rejected: remote had commits the local branch lacked | Check `git diff --stat` in worktree before pushing |
| Force-push to fix diverged branch | Considered `git push --force` | Would overwrite legitimate remote commits | Fetch remote, inspect, then `reset --hard` + `pull --rebase` |
| `git branch -d` on rebase-merged branches | Used safe delete flag | "not fully merged" error — rebase leaves no merge commit | Always use `git branch -D` when remote branch is confirmed deleted |
| `git worktree remove` without cleaning untracked dirs | Tried removing worktrees containing `ProjectMnemosyne/` | "contains modified or untracked files" error | Pre-clean `rm -rf $wt/ProjectMnemosyne` before `git worktree remove` |
| grep + awk on branch line of porcelain output | `grep "branch.*/$BRANCH$" \| awk '{print $2}'` | Extracts the git ref, not the filesystem path | Path is on the preceding `worktree` line; use awk to track it |
| `git branch -D` in stale cleanup automation | Force-delete in cleanup script | Too aggressive — deletes unmerged branches silently | Use `git branch -d` (safe delete) in automation to preserve unmerged branches |
| merge-base without `-C` repo context | `git merge-base --is-ancestor main "$BRANCH"` without `-C` | Runs in wrong repo context when CWD is a worktree | Always use `git -C "$WORK_DIR"` for explicit context |
| `git -C path` piped to `head` | Used `head` to limit output of `git -C` subcommand | `head` doesn't accept `-C` as git does | Don't pipe `git -C` subcommands to `head`; use separate commands |
| Direct worktree creation without fetching | `git worktree add -b name path origin/main` on stale clone | `origin/main` did not exist locally (only `origin/master`) | Always fetch origin before referencing remote refs in worktree commands |
| Auto-detect via symbolic-ref on fresh clone | `git symbolic-ref refs/remotes/origin/HEAD --short` | `origin/HEAD` is never set automatically on clone | Requires explicit `git remote set-head origin --auto` |
| Remove parent nested worktree before children | Removed depth-1 worktree that contained depth-2 entries | Left orphaned entries in git tracking | Remove deepest-nested first (depth 3 → 2 → 1) |

## Results & Parameters

### Worktree nesting patterns from agent waves

| Pattern | Path depth | Occurs when |
|---------|-----------|-------------|
| Simple wave | `.claude/worktrees/agent-XXXXXXXX` | Agent spawned from main session |
| Nested depth-2 | `.claude/worktrees/agent-A/.claude/worktrees/agent-B` | Wave-2 agent spawned another agent |
| Nested depth-3 | `agent-A/.../agent-B/.../agent-C` | Wave-2 agent's agent spawned yet another agent |

### Safety Net interaction

| Operation | Blocked? | Workaround |
|-----------|----------|------------|
| `git worktree remove --force` (untracked files) | Yes | Delete untracked files first, then remove without `--force` |
| `git branch -D` | No | Allowed |
| `git reset --hard` | Yes | N/A — use `pull --rebase` instead |

### Scale reference for mass cleanup

| Worktrees | Time | Notes |
|-----------|------|-------|
| 33 worktrees | ~3 min | All removed successfully |
| 20 stale (merged) | ~1 min | No --force needed after cleaning untracked dirs |
| 13 active | ~1 min | 2 needed --force for modified tracked files |

### Identifying [gone] branches

```bash
# List all branches with gone remotes
git branch -v | grep '\[gone\]'

# Delete them all at once
git branch -v | grep '\[gone\]' | awk '{print $1}' | xargs git branch -D
```

### Key porcelain verification

```bash
# Verify worktree path extraction
git worktree list --porcelain | awk '/^worktree /{path=$2} /^branch / {print path, $2}'
```

### Branch delete flag reference

| Flag | Use when |
|------|----------|
| `-d` (safe) | Remote branch still exists OR automation scripts (safety net) |
| `-D` (force) | Remote branch confirmed deleted (PR merged, `[gone]` in `git branch -v`) |

### Repo rename affected repos (as of 2026-03-24)

| Repo | Had origin/main locally? | Had origin/HEAD? |
|------|--------------------------|-------------------|
| Odysseus | No (only master) | No |
| ProjectHermes | No (only master) | No |
| ProjectKeystone | No (only master) | No |
| AchaeanFleet | Yes | No |
| ProjectHephaestus | Yes | Yes |
| ProjectMnemosyne | Yes | Yes |
| ProjectOdyssey | Yes | Yes |
| ProjectScylla | Yes | Yes |
