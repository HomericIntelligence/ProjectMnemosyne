---
name: mass-pr-rebase-parallel-agents
description: 'Batch rebase 100+ conflicting PRs using parallel sub-agents with worktree
  isolation. Use when: many PRs are CONFLICTING after main changes, systemic CI needs
  fixing first.'
category: ci-cd
date: 2026-03-17
version: 1.0.0
user-invocable: false
---
# Mass PR Rebase with Parallel Agents

## Overview

| Attribute | Value |
|-----------|-------|
| **Scope** | Repository-wide PR maintenance |
| **Scale** | 138 open PRs, 80+ conflicting |
| **Duration** | ~20 minutes for all rebases |
| **Parallelism** | 5-9 sub-agents simultaneously |
| **Success Rate** | 100% (0 failures across 96 rebases) |

## When to Use

- A major refactor lands on main (e.g., import style change) causing mass conflicts
- 10+ PRs show CONFLICTING status simultaneously
- CI has systemic failures blocking all PRs (fix main first, then rebase)
- Need to rebase PRs that touch overlapping files (e.g., shared/__init__.mojo)

## Verified Workflow

### Phase 0: Fix Systemic CI on Main First

Before rebasing any PRs, identify and fix failures that affect ALL PRs:

1. Check CI on a recent MERGEABLE PR: `gh pr checks <number>`
2. Check CI on main: `gh run list --branch main --limit 5`
3. Categorize failures as systemic vs PR-specific
4. Create a single fix PR for all systemic issues

**Common systemic failures found:**

| Failure | Root Cause | Fix |
|---------|-----------|-----|
| pre-commit hook uses `just` | `just` not installed in pre-commit CI env | Inline the bash command directly |
| mypy on wrapper scripts | `sys.path` manipulation invisible to static analysis | Add `# type: ignore[attr-defined]` |
| markdownlint on `*_backward` in tables | Unescaped `*` interpreted as emphasis | Escape with `\*\_backward` |
| Docker `mkdir: Permission denied` | `build/` dir created inside container on bind mount | Create dir on host before entering Docker |
| Template .mojo files fail build | Placeholder code doesn't compile | Exclude `papers/_template/` from build find |

### Phase 1: Classify PRs

```bash
# Get all PRs grouped by mergeability
gh pr list --state open --limit 200 --json number,headRefName,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# List all CONFLICTING PRs with branch names
gh pr list --state open --limit 200 --json number,headRefName,mergeable \
  --jq '.[] | select(.mergeable == "CONFLICTING") | "\(.number) \(.headRefName)"'
```

**IMPORTANT**: `gh pr list --limit 100` is the default and may miss older PRs. Always use `--limit 200` or higher.

### Phase 2: Batch Rebase with Parallel Agents

Split PRs into batches of 10-12 and launch sub-agents in parallel:

```
Agent prompt template for each batch:
- Fetch branch, create worktree under worktrees/<pr-number>
- Rebase onto origin/main
- Resolve conflicts with --theirs strategy
- Force push with --force-with-lease
- Enable auto-merge: gh pr merge <number> --auto --rebase
- Clean up worktree
```

**Key conflict resolution strategies:**

| File Pattern | Strategy |
|-------------|----------|
| `.github/workflows/*.yml` | `--theirs` (keep PR's version) |
| `scripts/*.py` | `--theirs` (keep PR's version) |
| `shared/**/*.mojo` | `--theirs` (keep PR's version) |
| `tests/**/*.mojo` | `--theirs` (keep PR's version) |
| `.pre-commit-config.yaml` | `--theirs` (keep PR's version) |
| Rename/rename conflicts | Use `git show REBASE_HEAD:<path>` to extract content |
| Modify/delete conflicts | `git rm` if PR intended deletion |

**Conflict resolution command pattern:**

```bash
# Standard --theirs resolution
git -C worktrees/<pr> checkout --theirs <file>
git -C worktrees/<pr> add <file>
GIT_EDITOR=true git -C worktrees/<pr> rebase --continue

# For rename conflicts where --theirs doesn't work
git -C worktrees/<pr> show REBASE_HEAD:<original-path> > worktrees/<pr>/<new-path>
git -C worktrees/<pr> add <new-path>
GIT_EDITOR=true git -C worktrees/<pr> rebase --continue
```

### Phase 3: Monitor and Clean Up

```bash
# Verify all PRs are MERGEABLE
gh pr list --state open --limit 200 --json number,mergeable \
  --jq '[group_by(.mergeable)[] | {status: .[0].mergeable, count: length}]'

# Clean up worktrees
git worktree prune

# Check CI queue status
gh run list --branch <branch> --limit 5 --json status,conclusion
```

### Quick Reference

| Step | Command | Notes |
|------|---------|-------|
| List conflicting | `gh pr list --limit 200 --json number,mergeable --jq '...'` | Use limit 200+ |
| Create worktree | `git worktree add worktrees/<pr> origin/<branch>` | Use worktrees/ dir |
| Rebase | `git -C worktrees/<pr> rebase origin/main` | In worktree |
| Resolve conflicts | `git checkout --theirs <file> && git add <file>` | --theirs for most |
| Continue rebase | `GIT_EDITOR=true git rebase --continue` | Avoid editor |
| Force push | `git push --force-with-lease origin <branch>` | Never --force |
| Auto-merge | `gh pr merge <pr> --auto --rebase` | Enable immediately |
| Cleanup | `git worktree remove worktrees/<pr>` | Per worktree |
| Prune | `git worktree prune` | After all done |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Native builds in CI | Changed `just build` to `just native build` in workflows | User wants Docker builds, not native | Fix Docker permissions instead of bypassing Docker |
| Fix only alexnet download_cifar10.py | Added type:ignore to one wrapper | Same file exists in resnet18/ and vgg16/ | Always search for all copies of a file pattern |
| Using `--limit 100` for PR listing | Default gh pr list limit | Missed 34 older conflicting PRs | Always use `--limit 200` or higher |
| Single agent for all rebases | Considered processing sequentially | Would take hours for 80+ PRs | Parallel agents (5-9) complete in ~20 minutes |

## Results & Parameters

### Session Results

- **138 total open PRs** processed
- **96 PRs rebased** and force-pushed (0 failures)
- **17 PRs** were already closed (commits on main)
- **All conflicts** resolved with `--theirs` strategy
- **Auto-merge** enabled on all open PRs

### Optimal Batch Size

```
PRs per agent: 10-12 (sweet spot)
Parallel agents: 5-9 (limited by git lock contention)
Total time: ~20 min for 80+ PRs
```

### Agent Configuration

```yaml
subagent_type: general-purpose
run_in_background: true
# No isolation: "worktree" needed - agents create their own worktrees
```

### CI Impact

Mass force-pushing overwhelms CI runners. All PR runs queue simultaneously.
Plan for 30-60 min CI queue drain after batch rebases.
