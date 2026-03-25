---
name: tooling-pr-auto-merge-worktree-command-migration
description: "Batch auto-merge + rebase open PRs and migrate command workflows from clone-to-.agent-brain to git worktrees. Use when: (1) many open PRs need auto-merge enabled and rebasing, (2) command files reference rm -rf on shared directories, (3) migrating clone-based workflows to git worktree isolation."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [auto-merge, rebase, worktree, retrospective, advise, agent-brain, pr-management]
---

# Batch PR Auto-Merge + Worktree Command Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Enable auto-merge on 14 open PRs, rebase all against main, and migrate /retrospective and /advise commands from clone+rm-rf pattern to git worktree isolation |
| **Outcome** | 13/14 PRs merged (1 auto-merging), worktree migration PR merged |
| **Verification** | verified-ci |

## When to Use

- Multiple open PRs need auto-merge enabled and rebasing against main
- Command files (advise.md, retrospective.md) reference `rm -rf` on shared directories like `$HOME/.agent-brain/`
- Migrating any clone-based workflow to git worktree isolation
- Need to replace "Never delete X" guardrails with proper worktree lifecycle management

## Verified Workflow

### Quick Reference

```bash
# Enable auto-merge on all open PRs
gh pr list --state open --json number --jq '.[].number' --limit 1000 | \
  while read pr; do gh pr merge "$pr" --auto --rebase; done

# Rebase PR branch using worktree
git worktree add /tmp/rebase-pr-<number> origin/<branch>
git -C /tmp/rebase-pr-<number> rebase origin/main
git -C /tmp/rebase-pr-<number> push --force-with-lease origin <branch>
git worktree remove /tmp/rebase-pr-<number>

# Worktree pattern for /retrospective
MNEMOSYNE_BASE="$(git rev-parse --show-toplevel)"
git -C "$MNEMOSYNE_BASE" worktree add /tmp/mnemosyne-skill-<name> -b skill/<name> origin/main
cd /tmp/mnemosyne-skill-<name>
# ... do work ...
git -C "$MNEMOSYNE_BASE" worktree remove /tmp/mnemosyne-skill-<name>
git -C "$MNEMOSYNE_BASE" worktree prune
```

### Detailed Steps

**Phase 1: Auto-merge all PRs**

1. Run `gh pr merge <pr> --auto --rebase` for each open PR
2. Handle "clean status" errors — these mean the PR was already eligible for immediate merge, retry once
3. Verify with `gh pr list --state open --json number,autoMergeRequest`

**Phase 2: Parallel rebase with worktree agents**

1. Split PRs into batches of ~5
2. Launch parallel agents with `isolation: "worktree"` — each agent rebases its batch
3. Each agent: fetch, checkout branch, rebase onto origin/main, force-push with `--force-with-lease`
4. Clean up worktrees after agents complete: `git worktree remove` + `git worktree prune`

**Phase 3: Migrate commands to worktree pattern**

1. Replace `**Clone location**` headers with `**Work isolation**: Git worktrees`
2. Replace clone+checkout setup with: detect base repo, `git worktree add`, work in worktree
3. Replace `rm -rf` cleanup with `git worktree remove` + `git worktree prune`
4. Remove "Never delete ~/.agent-brain/" notes (the worktree pattern makes deletion irrelevant)
5. Add stale worktree troubleshooting to Common Issues section
6. For read-only commands (advise): keep persistent cache, just remove deletion references

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh pr merge --auto --rebase` on "clean status" PRs | First attempt returned "Pull request is in clean status" error | PR was already eligible for immediate merge — GitHub attempted to merge instead of enabling auto-merge | Retry once; the PR either merged or needs a second `gh pr merge --auto` call |
| Enable auto-merge on "unstable" PR | `gh pr merge 987 --auto --rebase` returned "unstable status" | CI was still running after rebase push | Wait for CI to complete, then retry — or just let auto-merge handle it after checks pass |
| Single rebase approach for 14 PRs | Considered sequential processing | Too slow for batch operations | Use 3 parallel worktree-isolated agents (batches of 4-5 PRs each) |
| Full worktree migration for /advise | Considered replacing .agent-brain cache with worktrees for advise too | Advise is read-only — worktree isolation adds complexity with no benefit | Apply KISS: keep persistent cache for read-only operations, use worktrees only for write operations |

## Results & Parameters

### Auto-Merge Results

```yaml
total_prs: 14
auto_merge_enabled: 14/14
merged_during_session: 13/14
remaining: 1 (auto-merging, transient UNKNOWN state)
conflicts: 0
```

### Parallel Rebase Configuration

```yaml
agents: 3
prs_per_agent: 4-5
isolation: worktree
total_time: ~2 minutes
success_rate: 100%
```

### Files Modified for Worktree Migration

```
plugins/tooling/skills-registry-commands/commands/retrospective.md  # Primary: new worktree setup + cleanup
plugins/tooling/skills-registry-commands/commands/advise.md          # Minor: remove "Never delete" note
CLAUDE.md                                                            # Update workflow description
ADVISE_RETROSPECTIVE_UPDATED.md                                      # Update workflow comparison
```

### Key gh pr merge Error Codes

| Error | Meaning | Action |
|-------|---------|--------|
| "clean status" | PR already eligible for merge | Retry — may have merged immediately |
| "unstable status" | CI still running | Wait and retry, or let auto-merge handle |
| "Protected branch rules not configured" | PR targets non-main branch | `gh pr edit <pr> --base main` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | 14 PRs auto-merged + worktree migration PR #991 | 2026-03-25 session |
