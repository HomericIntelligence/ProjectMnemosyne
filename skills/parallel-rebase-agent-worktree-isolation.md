---
name: parallel-rebase-agent-worktree-isolation
description: 'Run multiple rebase agents in parallel without working tree collisions
  by assigning each agent a dedicated git worktree. Use when: (1) rebasing 50+ PR
  branches where agents switch branches and interfere with each other, (2) Safety
  Net hooks block git branch -D or git reset --hard in shared working tree, (3) background
  agents need isolated git state to avoid checkout conflicts.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Multiple background agents rebasing branches switch git checkout, colliding with each other and blocking the main conversation's commits |
| **Root cause** | All agents share the same working tree; branch switches by one agent leave another in unexpected state mid-rebase |
| **Fix** | Give each agent a dedicated `git worktree` so they operate on isolated directory copies |
| **Scale** | Tested with 70 PRs rebased via 2 parallel agents + 1 main conversation agent |

## When to Use

- Launching 2+ background agents to mass-rebase branches in parallel
- Agents use `git switch`/`git checkout` and leave rebase-in-progress state behind
- Safety Net blocks `git branch -D` or `git reset --hard` in the shared working tree
- CI failures on all PRs require rebasing 50+ branches quickly
- Main conversation needs to commit while background agents are running

## Verified Workflow

### Quick Reference

| Command | Purpose |
|---------|---------|
| `git worktree add worktrees/<name> <branch>` | Create isolated copy |
| `git worktree remove worktrees/<name>` | Clean up after done |
| `git worktree list` | See all active worktrees |
| `git stash` | Save state when switching to a branch locked by worktree |

### Phase 1: Check current PR state

```bash
gh pr list --state open --json number,mergeStateStatus,headRefName --limit 70 | python3 -c "
import json,sys
prs = json.load(sys.stdin)
by_state = {}
for p in prs:
    by_state.setdefault(p['mergeStateStatus'],[]).append(p['number'])
for s,n in sorted(by_state.items()):
    print(f'{s}: {len(n)} - {sorted(n)[:10]}')
"
```

### Phase 2: Enable auto-merge on all PRs missing it

```bash
gh pr list --state open --json number,autoMergeRequest --limit 70 | python3 -c "
import json,sys
prs = json.load(sys.stdin)
no_auto = [p['number'] for p in prs if not p['autoMergeRequest']]
print('Missing auto-merge:', no_auto)
" | xargs -I{} echo {}
# Then:
for pr in <list>; do gh pr merge "$pr" --auto --rebase; done
```

### Phase 3: Launch agents with worktree isolation

**Key instruction to include in each agent prompt:**

```
CRITICAL: Use a dedicated git worktree to avoid colliding with other agents.

Create your worktree FIRST before doing any rebase work:
  git worktree add worktrees/rebase-batch-N fix-baseline-ci-errors
  cd worktrees/rebase-batch-N

Do ALL rebase work from inside the worktree. When done:
  cd /path/to/repo
  git worktree remove worktrees/rebase-batch-N
```

**Agent batch split (example for 60 PRs):**

```
Batch 1 agent: PRs 4833-4862, worktree: worktrees/rebase-batch1
Batch 2 agent: PRs 4863-4893, worktree: worktrees/rebase-batch2
```

Each agent works from its own directory, never touching the main working tree.

### Phase 4: Handle the "branch already used by worktree" error

When the main conversation tries to switch to a branch that a background agent's
worktree is using:

```bash
# Error: fatal: 'fix-baseline-ci-errors' is already used by worktree at '...'
# Solution: work in the worktree directly, or use a detached HEAD approach

# Option A: Create separate worktree for your own work
git worktree add worktrees/main-work origin/my-branch

# Option B: Stash, do work in the worktree path
git stash
cd worktrees/rebase-batch2  # do your commit here
cd /repo && git stash pop
```

### Phase 5: Rebase each branch inside the worktree

```bash
cd worktrees/rebase-batch-N

for entry in "4833 3937-auto-impl" "4836 3940-auto-impl" ...; do
  pr=$(echo $entry | cut -d' ' -f1)
  branch=$(echo $entry | cut -d' ' -f2)

  git fetch origin $branch -q
  git switch -c tmp-$pr origin/$branch -q

  result=$(git rebase origin/main 2>&1)
  if echo "$result" | grep -q "CONFLICT"; then
    echo "CONFLICT PR#$pr - needs manual resolution"
    git rebase --abort
  else
    git push --force-with-lease origin HEAD:$branch -q && echo "OK PR#$pr"
  fi

  git switch <stable-branch> -q
  git branch -d tmp-$pr 2>/dev/null
done
```

### Phase 6: Resolve merge conflicts

**Decision tree for common conflict types:**

| File | Resolution |
|------|-----------|
| `shared/core/extensor.mojo` | Keep HEAD's infrastructure (imports, constants), keep branch's new methods |
| `CLAUDE.md`, config files | Take `--ours` always |
| CI workflow YAML | Take `--ours` (main is more up-to-date) unless branch is adding the workflow |
| Deleted file (modify/delete) | Honor the deletion with `git rm <file>` |
| Test files | Keep both sides' additions |
| Python scripts | Merge both features when both add distinct functionality |

**Resolving conflicts programmatically:**

```python
# Take ours (HEAD/main):
def take_ours(content):
    result = []
    in_ours = in_theirs = False
    for line in content.split('\n'):
        if line.startswith('<<<<<<<'):
            in_ours = True
        elif line.startswith('=======') and in_ours:
            in_ours = False; in_theirs = True
        elif line.startswith('>>>>>>>') and in_theirs:
            in_theirs = False
        elif in_ours:
            result.append(line)
        elif not in_theirs:
            result.append(line)
    return '\n'.join(result)
```

### Phase 7: Clean up temp branches

```bash
# Safe delete (merged to remote):
git branch -d tmp-<N>

# If Safety Net blocks -D, verify content is on remote first:
git rev-parse tmp-<N>  # local SHA
git rev-parse origin/<branch>  # remote SHA
# If they match → safe to delete
# If different → content already superseded by force-push, also safe
```

### Phase 8: Final verification

```bash
git fetch --all --quiet
# Check no branches behind main:
for branch in $(git branch -r | grep "auto-impl"); do
  behind=$(git rev-list --count $branch..origin/main 2>/dev/null)
  [ "$behind" != "0" ] && echo "$behind behind: $branch"
done
# Check PR states:
gh pr list --state open --json number,mergeStateStatus --limit 70 | python3 -c "
import json,sys; prs=json.load(sys.stdin)
by_s={}
[by_s.setdefault(p['mergeStateStatus'],[]).append(p['number']) for p in prs]
[print(f'{s}: {len(n)}') for s,n in sorted(by_s.items())]
"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Launch 2 parallel agents without worktree isolation | Both agents used the same working tree, switching branches with `git switch` | Agents left stale rebase-in-progress state (`.git/rebase-merge/`) from each other's abandoned rebases; branch collisions caused commits to land on wrong branches | Always assign each parallel rebase agent a dedicated `git worktree` |
| Use `git branch -D` to delete temp branches | Safety Net hook blocked force-delete | Safety Net treats `-D` as destructive; triggers block | Use `git branch -d` (safe delete); if branch not fully merged, verify the content is already on remote before asking user to force-delete |
| Use `git reset --hard origin/<branch>` to sync diverged local branch | Safety Net blocked the command | `reset --hard` is classified as destructive | Use `git pull --rebase origin/<branch>` instead |
| Commit matrix.mojo fix while batch 1 agent was switching branches | Commit landed on `tmp-rebase-3956` instead of `fix-baseline-ci-errors` | Agent switched branches between our `git add` and `git commit` | When agents are actively switching branches in the same worktree, either wait for them to finish or do your work in a separate worktree |
| Agent used prefix `tmp-r2-*` for temp branches, same as other agent | Two agents used same temp branch names | First agent created `tmp-r2-4096`, second agent tried to create same name | Include unique batch ID in temp branch prefix: `tmp-b1-<N>`, `tmp-b2-<N>` |

## Results & Parameters

### Session outcome

- **70 PRs** rebased from 125 commits behind → 0 behind main
- **0 DIRTY** PRs (was 12+)
- **All PRs** have auto-merge enabled
- **Time**: ~45 minutes with 3 parallel agents

### Temp branch naming convention

```
# Batch 1 agent:
tmp-b1-<issue-number>   # e.g., tmp-b1-4833

# Batch 2 agent:
tmp-b2-<issue-number>   # e.g., tmp-b2-4863

# Main conversation:
tmp-<issue-number>       # e.g., tmp-4889
```

### Worktree placement

```
worktrees/rebase-batch1/   ← batch 1 agent
worktrees/rebase-batch2/   ← batch 2 agent
worktrees/fix-pr-rebase/   ← main conversation overflow work
```

Always place worktrees inside `worktrees/` subdirectory (per CLAUDE.md convention).
