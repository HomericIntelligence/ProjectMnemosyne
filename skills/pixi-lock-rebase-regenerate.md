---
name: pixi-lock-rebase-regenerate
description: Correctly resolve pixi.lock conflicts during git rebase without producing
  a stale lock file. Use when git rebase causes pixi.lock conflicts, or CI fails with
  'lock-file not up-to-date with the workspace'.
category: ci-cd
date: 2026-02-22
version: 1.0.0
user-invocable: true
---
# Pixi Lock Rebase Regenerate

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Correctly resolve `pixi.lock` conflicts during `git rebase` without producing a stale lock file |
| **Outcome** | Eliminates `lock-file not up-to-date` CI failures caused by accepting one side of a pixi.lock conflict |

## When to Use This Skill

Use this pattern whenever:
- Running `git rebase` on a branch that includes `pixi.lock`
- A merge conflict occurs in `pixi.lock`
- The branch modifies `pixi.toml` (adds/removes dependencies or tasks)
- CI fails with: `lock-file not up-to-date with the workspace`

**Do NOT use `--ours` or `--theirs`** to resolve a `pixi.lock` conflict — either side may be stale
relative to the rebased branch's actual `pixi.toml`.

## Root Cause

`pixi.lock` encodes the exact resolved dependency graph plus a SHA256 hash of the local
editable package. When you rebase:

1. The branch's `pyproject.toml` or `pixi.toml` may differ from main's
2. Even if `pixi.toml` is identical, the local package hash changes whenever source files change
3. Accepting either `--ours` or `--theirs` produces a lock file whose hash doesn't match the
   rebased branch's actual source tree
4. `pixi install --locked` then fails because the hash is wrong

## Verified Workflow

### During `git rebase origin/main`

When `pixi.lock` shows as conflicted:

```bash
# Step 1: Delete the conflicted file entirely
rm pixi.lock

# Step 2: Stage the deletion to mark conflict resolved
git add pixi.lock

# Step 3: Continue the rebase
git rebase --continue
```

Repeat for each commit that conflicts on `pixi.lock`.

### After rebase completes

```bash
# Regenerate the lock file from scratch
pixi lock

# Verify it installs correctly
pixi install --locked

# Stage the regenerated lock file
git add pixi.lock
```

### If no pixi.lock conflict occurred but pixi.toml was modified

Always regenerate anyway if `pixi.toml` differs between branches:

```bash
git diff origin/main..HEAD -- pixi.toml  # check if modified
pixi lock                                  # regenerate if it was
```

### Full rebase sequence

```bash
git fetch origin
git switch -c <branch> origin/<branch>
git rebase origin/main
# ... resolve conflicts, using delete+add for pixi.lock ...
pixi lock                                   # always regenerate after rebase
pre-commit run --all-files
# Fix any pre-commit failures
git add pixi.lock
git add -u
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| `git checkout --theirs pixi.lock` | Accepted main's lock file; CI failed with `lock-file not up-to-date` | SHA256 hash in lock file is computed from local package source — main's hash doesn't match branch's modified source |
| `git checkout --ours pixi.lock` | Lock file still mismatched | `--ours` is the pre-rebase branch's lock file, which is behind main's dependency changes |
| Skipping `pixi lock` when no pixi.toml conflict | CI still failed with `lock-file not up-to-date` | Local package hash changes even when `pixi.toml` appears unchanged, due to source file modifications |

## Results & Parameters

Key pixi commands:
```bash
pixi lock              # regenerate pixi.lock (reads pixi.toml, resolves all deps)
pixi install --locked  # verify lock file is consistent (what CI runs)
```

## Related Skills

- `parallel-worktree-workflow` — running parallel rebases in isolated worktrees
- `pixi-pip-audit-severity-filter` — configuring pip-audit in the pixi lint environment

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Multiple PRs on 2026-02-22 with pixi.lock conflicts and CI failures | [notes.md](../../references/notes.md) |
