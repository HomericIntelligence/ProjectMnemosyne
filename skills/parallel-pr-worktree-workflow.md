---
name: parallel-pr-worktree-workflow
description: "Use when: (1) launching 2+ parallel rebase agents that need isolated git state to avoid branch collision, (2) implementing 5+ independent fixes in parallel PRs using git worktrees, (3) bulk-merging skill PRs with CI fixes and conflict resolution, (4) batching 10+ PRs across parallel sub-agents for maximum throughput."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---
# Parallel PR Worktree Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Parallel workflow tooling pattern — git worktrees for agent isolation, batching PRs per agent, bulk PR triage and merge |
| **Outcome** | Consolidated from 4 source skills |

## When to Use

- Launching 2+ background agents to mass-rebase branches in parallel (each needs isolated git state)
- Agents use `git switch`/`git checkout` and would leave rebase-in-progress state in shared working tree
- Safety Net blocks `git branch -D` or `git reset --hard` in the shared working tree
- Implementing 5+ independent fixes in parallel, each with its own PR
- Bulk-merging accumulated skill PRs (10+) with a mix of passing/failing CI
- Main conversation needs to commit while background agents are running
- Issues are independent (not interdependent) and benefit from parallel development

**Do NOT use when:**
- Issues are interdependent (use sequential PRs from `batch-pr-rebase-conflict-resolution-workflow`)
- Codebase is unstable (fix stability first)
- Limited CI resources (parallel PRs can overwhelm CI)

## Verified Workflow

### Quick Reference

```bash
# Create worktree for agent isolation
git worktree add worktrees/<name> <branch>

# Agent batch split (example for 13 PRs)
# Batch 1: 4 PRs → agent with worktrees/rebase-batch1
# Batch 2: 4 PRs → agent with worktrees/rebase-batch2
# Batch 3: 3 PRs → agent with worktrees/rebase-batch3

# Cleanup
git worktree remove worktrees/<name>
git worktree prune
```

### Phase 1: Triage PRs into Groups

```bash
# List all open PRs with CI status
gh pr list --state open --json number,title,headRefName,mergeStateStatus --limit 100

# Check individual PR checks
gh pr checks <PR_NUMBER>
```

Identify:
- **Group A (immediate)**: PRs with passing CI → merge immediately
- **Group B (fix needed)**: PRs with failing CI → fix first, then merge
- **Group C (rebase needed)**: PRs with DIRTY/CONFLICTING state → rebase first

Order Group A by PR number (oldest first) to minimize rebase conflicts:
```bash
for pr in <PR_NUMBERS_IN_ORDER>; do
  echo "=== Merging PR #$pr ==="
  gh pr merge $pr --rebase --delete-branch 2>&1
done
```

**Note**: With `strict: false` on branch protection, PRs don't need to be up-to-date with main before merging. Merge all without rebasing between each one.

**Watch for**: `GraphQL: Pull Request is not mergeable` — PR became conflicted during batch. Handle in Phase 4.

### Phase 2: Plan Dependency Groups for Parallel Work

When implementing multiple independent fixes in parallel:

```
Group A (parallel from main — no dependencies):
  - PR1: Independent fix A
  - PR2: Independent fix B
  - PR3: Independent fix C

Group B (after Group A merges — pull updated main first):
  - PR4: Depends on PR1
  - PR5: Depends on PR2
```

**Key decision**: Group issues by dependencies to maximize parallelism while maintaining correctness. Wait for dependencies to merge before creating dependent worktrees.

### Phase 3: Worktree Setup for Parallel Implementation

```bash
# Pull latest main
git checkout main && git pull

# Create worktrees for Group A (all parallel from same main)
git worktree add worktrees/fix-issue-123 -b issue-123-fix-config main
git worktree add worktrees/fix-issue-124 -b issue-124-remove-dead-code main
git worktree add worktrees/fix-issue-125 -b issue-125-update-docs main

# After Group A merges, create Group B worktree from updated main
git checkout main && git pull
git worktree add worktrees/fix-issue-126 -b issue-126-depends-on-pr1 main
```

**Critical:** Always create worktrees from the correct base branch. For dependent PRs, wait for the dependency to merge and pull main first.

**Always place worktrees inside `worktrees/` subdirectory** (per repo convention):
```
worktrees/rebase-batch1/   ← batch 1 agent
worktrees/rebase-batch2/   ← batch 2 agent
worktrees/fix-pr-rebase/   ← main conversation overflow work
```

### Phase 4: Agent Isolation for Parallel Rebase

When launching parallel agents to rebase many PRs, each agent MUST get its own worktree:

**Key instruction to include in each agent prompt:**
```
CRITICAL: Use a dedicated git worktree to avoid colliding with other agents.

Create your worktree FIRST before doing any rebase work:
  git worktree add worktrees/rebase-batch-N <stable-branch>
  cd worktrees/rebase-batch-N

Do ALL rebase work from inside the worktree. When done:
  cd /path/to/repo
  git worktree remove worktrees/rebase-batch-N
```

**Optimal batching strategy**:
```yaml
# Batch 3-4 PRs per agent (sequential within agent, parallel across agents)
# Avoids excessive agent spawn overhead (5-agent-per-wave limit)
agents: 4
prs_per_agent: 3-4
total_prs: 13
waves: 1  # All agents launch simultaneously
```

**Temp branch naming convention** (use unique batch ID to avoid collision):
```
Batch 1 agent: tmp-b1-<issue-number>
Batch 2 agent: tmp-b2-<issue-number>
Main conversation: tmp-<issue-number>
```

### Phase 5: Implementation Pattern (Per Worktree)

For each worktree implementing a fix:

```bash
cd worktrees/fix-issue-123

# 1. Make focused changes (only the issue in this PR — no scope creep)

# 2. Run pre-commit hooks
pre-commit run --all-files
# OR: pixi run pre-commit run --all-files

# 3. Run relevant tests
pixi run pytest tests/unit/path/to/relevant -v

# 4. Stage auto-fixed files if pre-commit made changes
git status --short
git add <changed-files>

# 5. Commit with conventional commits
git commit -m "type(scope): brief description

Fixes #123

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# 6. Push and create PR with auto-merge
git push -u origin issue-123-fix-config
gh pr create \
  --title "type(scope): Brief description" \
  --body "Closes #123

## Summary
Brief explanation

## Changes
- Change 1

## Verification
Tests pass, pre-commit hooks pass"

# 7. Enable auto-merge (CRITICAL for parallel workflow)
gh pr merge --auto --rebase
```

### Phase 6: Rebase Per-PR Inside Worktree (For Rebase Agents)

```bash
cd worktrees/rebase-batch-N

for entry in "4833 3937-auto-impl" "4836 3940-auto-impl"; do
  pr=$(echo $entry | cut -d' ' -f1)
  branch=$(echo $entry | cut -d' ' -f2)

  git fetch origin $branch -q
  git switch -c tmp-b1-$pr origin/$branch -q

  result=$(git rebase origin/main 2>&1)
  if echo "$result" | grep -q "CONFLICT"; then
    echo "CONFLICT PR#$pr - needs manual resolution"
    git rebase --abort
  else
    git push --force-with-lease origin HEAD:$branch -q && echo "OK PR#$pr"
  fi

  git switch <stable-branch> -q
  git branch -d tmp-b1-$pr 2>/dev/null
done
```

Conflict resolution strategies — see `batch-pr-rebase-conflict-resolution-workflow` for full details.

### Phase 7: Fix Group B — Common CI Failures in Skill PRs

#### Common failure: Missing `plugin.json`

```bash
git switch skill/<category>/<name>
```

Create `.claude-plugin/plugin.json` using the SKILL.md frontmatter as source:

```json
{
  "name": "<from SKILL.md frontmatter>",
  "version": "1.0.0",
  "description": "<from SKILL.md frontmatter>",
  "category": "<from directory path>",
  "tags": ["<relevant>", "<tags>"],
  "date": "<from SKILL.md frontmatter>",
  "user-invocable": false
}
```

#### Common failure: Missing `version` field
Add `"version": "1.0.0"` to the existing `plugin.json`.

#### Common failure: Invalid category
Valid categories: `architecture`, `ci-cd`, `debugging`, `documentation`, `evaluation`, `optimization`, `testing`, `tooling`, `training`

```bash
# Edit plugin.json and SKILL.md frontmatter, then:
git add <files>
git commit -m "fix: change invalid category '<wrong>' to '<valid>'"
git push
```

### Phase 8: Identify Required Checks Before Diagnosing Failures

After rebase, CI often fails for reasons beyond staleness:

```bash
# ALWAYS identify required checks first
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'

# Only fix required checks — non-required failures (e.g., Docker pull errors) don't block merge
gh run view <run-id> --log-failed 2>&1 | grep "error:" | head -10
```

Failure categories:
- **Build errors**: Missing trait methods, type mismatches, duplicate functions, docstring format
- **Pre-commit**: Formatting changes (trailing lines, line length), grandfathered file lists
- **Security scans**: Action config differences (detect vs protect mode, exit-code flags)

CI checks run sequentially — later checks only run after earlier ones pass. Expect 2-3 fix rounds.

### Phase 9: Handle "Branch Already Used by Worktree" Error

When main conversation tries to switch to a branch locked by a background agent's worktree:

```bash
# Error: fatal: 'fix-baseline-ci-errors' is already used by worktree at '...'

# Option A: Create separate worktree for your own work
git worktree add worktrees/main-work origin/my-branch

# Option B: Work directly in the agent's worktree path
cd worktrees/rebase-batch2  # do your commit here
cd /repo
```

### Phase 10: Monitor CI and Handle Iterative Fix Loops

Each fix round can expose new failures (build fix reveals pre-commit issue; pre-commit fix reveals security issue):

```bash
# Monitor all PRs
gh pr list --author "@me" --state open --json number,title,statusCheckRollup \
  --jq '.[] | {number, title, status: (.statusCheckRollup | map(.conclusion) | unique)}'

# When CI fails — go to failing PR's worktree, fix, push
cd worktrees/fix-issue-123
# ... make changes ...
git add <files>
git commit -m "fix: address CI failure"
git push
# Auto-merge will trigger once CI passes
```

### Phase 11: Cleanup

```bash
# After all PRs merge, remove all worktrees
for wt in worktrees/rebase-batch1 worktrees/rebase-batch2; do
  git worktree remove $wt 2>/dev/null || true
done

# Prune stale references
git worktree prune

# Verify clean state
git worktree list  # Should show only main repo

# Pull all merged changes
git checkout main && git pull
```

Close any orphaned issues:
```bash
gh issue close <issue-number> --comment "Fixed in PR #<number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Launch 2 parallel agents without worktree isolation | Both agents used the same working tree, switching branches with `git switch` | Agents left stale rebase-in-progress state (`.git/rebase-merge/`) from each other's abandoned rebases; commits landed on wrong branches | Always assign each parallel rebase agent a dedicated `git worktree` |
| `git branch -D` to delete temp branches | Safety Net hook blocked force-delete | Safety Net treats `-D` as destructive | Use `git branch -d` (safe delete); verify content is on remote before asking to force-delete |
| `git reset --hard origin/<branch>` to sync | Safety Net blocked the command | `reset --hard` is classified as destructive | Use `git pull --rebase origin/<branch>` instead |
| Commit while batch agent was switching branches | Commit landed on `tmp-rebase-3956` instead of `fix-baseline-ci-errors` | Agent switched branches between our `git add` and `git commit` | When agents are switching branches in shared worktree, do your work in a separate worktree |
| Agent used same temp branch prefix as other agent | Two agents used same temp branch names (`tmp-r2-*`) | First agent created `tmp-r2-4096`, second agent tried to create same name | Include unique batch ID in temp branch prefix: `tmp-b1-<N>`, `tmp-b2-<N>` |
| Spawned agents while parent was in plan mode | Agents completed analysis but couldn't execute any writes | Plan mode is INHERITED by sub-agents — they can only read files | Always exit plan mode BEFORE spawning execution agents |
| Creating all worktrees upfront | Created all 14 worktrees at the start | Some PRs depended on others; had to rebase worktrees later | Create worktrees in dependency groups; wait for dependencies to merge |
| Editing files without reading them first | Edit tool failed: "File has not been read yet" | Edit tool requires reading files first to establish context | Always Read before Edit |
| Not updating test mocks after code changes | PR failed CI because tests expected old behavior | Changed production code but forgot to update corresponding tests | After changing code, grep for related tests and update expectations |
| Pre-commit hook auto-fixes | Committed code; pre-commit auto-fixed formatting causing commit to fail | Hook modified files after staging but before commit | Run `pre-commit run --all-files` manually first, then `git add -A`, then commit |
| Round 1 rebase-only (no code verification) | Simple rebase and push for all 10 PRs | 9/10 failed CI — rebasing alone didn't fix code issues in PR branches | Rebase fixes staleness but not code correctness; verify compilation after rebase |
| Assumed Docker test failures blocked merge | Investigated Docker pull errors affecting all PRs | These weren't required checks — PR merged despite Docker failures | Always check `required_status_checks` first before investigating failures |
| gitleaks action with default mode | PR switched from manual gitleaks binary to `gitleaks-action` | Action defaults to `protect` (git-log) scan mode, finding historical secrets | When replacing a CI tool with its GitHub Action equivalent, match the scan mode/flags exactly |
| Grandfathered file list missing entries | Added test-count guard hook with allowlist | Missed `DISABLED_test_batchnorm.mojo` which has 14 tests | When adding validation hooks, run against ALL files first to build a complete allowlist |
| 1 PR per agent for 13 PRs | Spawned 13 individual agents | Excessive agent spawn overhead; 5-agent-per-wave limit means 3 waves minimum | Batch 3-4 PRs per agent (sequential within agent) — 4 agents handle 13 PRs in 1 wave |
| Sequential PRs instead of parallel | Processed all PRs one at a time | 3-4x slower than parallel worktree approach | Use git worktrees + auto-merge for 5+ independent fixes |

## Results & Parameters

### Key Commands Reference

```bash
# Check current worktrees
git worktree list

# Create worktree
git worktree add worktrees/<name> <branch>

# Remove worktree
git worktree remove worktrees/<name>
git worktree prune

# Check required status checks
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts[]'

# Monitor all open PRs
gh pr list --state open --json number,title,mergeStateStatus --limit 100

# Enable auto-merge
gh pr merge --auto --rebase

# Merge with delete
gh pr merge <number> --rebase --delete-branch

# Verify all target PRs merged
for pr in <SPACE_SEPARATED_PR_NUMBERS>; do
  echo "PR #$pr: $(gh pr view $pr --json state --jq '.state')"
done
```

### Agent Configuration

```yaml
# Optimal for parallel rebase with worktree isolation
subagent_type: general-purpose
isolation: "worktree"  # Each agent gets isolated repo copy (automatic)
# OR manual: agent creates worktrees/rebase-batchN before doing any work

# Batch sizing
agents: 4
prs_per_agent: 3-4  # Sequential within agent
total_prs: 13
waves: 1  # All agents launch simultaneously

# Model tiers (Myrmidon swarm)
orchestrator: opus   # Wave planning, dependency analysis
specialist: sonnet   # Complex conflict resolution
executor: haiku      # Simple rebase, pre-commit fixes
```

### Parallel PR Efficiency Metrics

| Method | PRs | Time | CI Overhead |
|--------|-----|------|-------------|
| Sequential PRs | Any | 3-4x baseline | Minimal |
| Parallel worktrees (independent) | 5-9 | 70% faster | Parallel CI runs |
| 4 parallel agents (3-4 PRs each) | 13 | ~7 minutes | Parallel CI runs |
| 3 parallel agents | 70 | ~45 minutes | Parallel CI runs |

### Skill PR Common Failures

| Error type | Count (reference) | Fix |
|-----------|-------|-----|
| Missing `.claude-plugin/plugin.json` | 4 | Create with name/version/description/category/tags/date |
| Invalid category (e.g., `automation`) | 1 | Change to `tooling` in plugin.json and SKILL.md |
| Missing `version` field | 1 | Add `"version": "1.0.0"` |

### Success Metrics (Reference Sessions)

| Session | PRs | Result |
|---------|-----|--------|
| 13 PRs in 4 batched agents (v1.1) | 13 | ~7 min, 5 conflicts resolved semantically |
| 70 PRs with 3 parallel agents (v1.0) | 70 | ~45 min, 0 DIRTY remaining |
| 9 parallel worktrees (independent fixes) | 9 | All merged, 1,500+ lines removed |
| 30 skill PRs bulk merge | 30 | All merged, 6 CI fixes, 2 rebases |
| 10 stale PRs (3 fix rounds) | 9/10 | 21 agents across 3 rounds |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | 70 PRs rebased with 3 parallel agents, 2026-03-15 | parallel-rebase-agent-worktree-isolation v1.0 |
| ProjectScylla | 13 PRs rebased with 4 batched agents, 2026-03-27 | parallel-rebase-agent-worktree-isolation v1.1 |
| ProjectScylla | 9/10 stale PRs fixed in 3 iterative rounds | parallel-pr-rebase-fix source |
| ProjectScylla | 9 parallel worktrees, 24 fixes, 1,500+ lines removed | parallel-pr-workflow source |
| ProjectMnemosyne | 30 open skill PRs bulk merged, 2026-03-03 | bulk-skill-pr-merge source |
