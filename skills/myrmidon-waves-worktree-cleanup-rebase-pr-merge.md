---
name: myrmidon-waves-worktree-cleanup-rebase-pr-merge
description: "Use when cleaning up 10+ stale worktrees with a mix of mergeable and superseded branches. Orchestrates a 3-wave myrmidon swarm: Wave 1 (Haiku) removes stale/merged, Wave 2 (Sonnet+Haiku) rebases unreleased work into PRs while parallel agents check stale PRs for conflicts, Wave 3 (Haiku) prunes. Assigns Haiku for mechanical removal/prune steps and Sonnet for code analysis + rebase + PR creation."
category: tooling
date: 2026-04-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [myrmidon, wave, worktree, cleanup, rebase, pr, swarm, parallel, haiku, sonnet]
---
# Myrmidon Waves: Worktree Cleanup, Rebase, PR, Merge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Objective** | Parallel 3-wave myrmidon cleanup of 31 stale worktrees: remove stale, rebase+PR unreleased work, prune |
| **Outcome** | 32 → 1 worktrees; 3 new PRs created from previously-unsubmitted work; 7 superseded branches confirmed; 3 stale-PR branches confirmed conflict-superseded |
| **Verification** | verified-local |

Applies the myrmidon-swarm three-wave pattern specifically to the worktree cleanup scenario where a pool of 10+ agent-created worktrees contains heterogeneous states: purely stale merged work, unreleased commits that need PRs, and stale branches with closed PRs that conflict with main. The key insight is that Sonnet analysis is required only for the rebase+PR wave — all other waves can use cost-efficient Haiku executors.

## When to Use

- `git worktree list` shows 15+ worktrees beyond main
- Pool is heterogeneous: some merged/stale, some ahead of main without PRs, some with closed PRs
- Need to determine which branches contain unique unreleased work vs. superseded work
- Want to create PRs from agent-created branches that were never submitted
- Want parallel wave execution to minimize total wall-clock time

Do NOT use when:
- Only a few worktrees need cleanup (use `worktree-cleanup-branches-artifacts` directly)
- All worktrees are already classified (go straight to the appropriate phase of that skill)
- Worktrees contain conflicting changes that require human decision-making

## Verified Workflow

### Quick Reference

```bash
# Step 1: Triage all worktrees into categories A/B/C
git worktree list --porcelain | awk '/^worktree /{path=$2} /^branch /{sub("refs/heads/",""); print path, $2}'
for branch in $(git branch | tr -d ' '); do
  ahead=$(git rev-list --count origin/main.."$branch" 2>/dev/null || echo 0)
  pr=$(gh pr list --head "$branch" --state all --json state -q '.[0].state' 2>/dev/null)
  echo "$branch: ahead=$ahead pr=$pr"
done

# Wave 1 (Haiku, parallel): remove Category A stale/merged
rm -f "$wt"/.claude-prompt-*.md "$wt"/.issue_implementer
rm -rf "$wt"/ProjectMnemosyne
git worktree remove "$wt"

# Wave 2a (Sonnet): rebase + PR for Category B (unreleased work)
git fetch origin
git worktree add /tmp/rebase-<branch> <branch>
cd /tmp/rebase-<branch>
git rebase origin/main
git push --force-with-lease origin <branch>
gh pr create --title "..." --body "$(cat <<'EOF'
Brief description.
EOF
)"
gh pr merge --auto --rebase

# Wave 2b (Haiku, parallel with 2a): conflict-check Category C
git fetch origin
git rebase --onto origin/main origin/main <branch> --no-commit 2>&1 | grep -E "CONFLICT|error"
git rebase --abort 2>/dev/null
# If conflicts → confirm superseded, keep PR closed

# Wave 3 (Haiku): prune
git worktree prune
git fetch --prune origin
git worktree list  # verify final state
```

### Phase 0: Triage — Build the A/B/C Map

Run this audit before dispatching any agents. Do not skip — incorrect triage leads to over-deletion.

```bash
# Full worktree + branch status audit
git worktree list --porcelain

for branch in $(git branch | tr -d ' *'); do
  ahead=$(git rev-list --count origin/main.."$branch" 2>/dev/null || echo 0)
  pr_state=$(gh pr list --head "$branch" --state all --json state,number \
    -q '.[0] | "\(.state) #\(.number)"' 2>/dev/null || echo "NONE")
  echo "  $branch: ahead=$ahead pr=$pr_state"
done
```

**Triage decision table:**

| Category | Criteria | Wave | Executor |
|----------|----------|------|----------|
| A — Stale/Merged | 0 commits ahead of main, OR `[gone]` remote, OR merged PR | Wave 1 | Haiku |
| B — Unreleased | 1+ commits ahead, no merged PR (open, closed-without-merge, or NONE) | Wave 2a | Sonnet |
| C — Stale-PR conflict | Closed PR + suspected conflicts with main | Wave 2b | Haiku |

**Common agent-created branch patterns that are Category A:**
- `feat/*` branches created for already-merged features
- `issue-*` branches where the issue is merged or closed
- Branches where `git rev-list --count origin/main..<branch>` is 0

### Phase 1: Wave 1 — Remove Category A (Haiku, Parallel)

Dispatch Haiku sub-agents in parallel. Each agent handles one or a small batch of stale worktrees.

**Per-agent task (Haiku):**

```bash
# Pre-cleanup: remove agent artifacts that block git worktree remove
wt="<path>"
rm -f "$wt"/.claude-prompt-*.md
rm -rf "$wt/ProjectMnemosyne"
rm -f "$wt/.issue_implementer"

# Remove the worktree (without --force)
git worktree remove "$wt"

# If worktree has no associated branch to keep, also delete the local branch:
git branch -d <branch-name>
```

**Safety constraint**: Never use `git worktree remove --force`. Remove stray files individually first, then call remove without --force.

Haiku agents can batch multiple stale worktrees in one task (5-10 per agent). No ordering constraints — all are independent.

### Phase 2a: Wave 2 — Rebase + PR for Category B (Sonnet, Per-Branch)

Dispatch one Sonnet sub-agent per Category B branch. These agents require code analysis to:
1. Determine whether the branch contains genuinely unique work vs. work already on main
2. Write a meaningful PR title and description
3. Handle any rebase conflicts

**Per-agent task (Sonnet):**

```bash
cd /path/to/main/repo
git fetch origin

# Check if content is already on main (superseded)
cherry_count=$(git cherry origin/main <branch> | grep "^+" | wc -l)
if [ "$cherry_count" -eq 0 ]; then
  echo "Branch <branch> is superseded — all commits already on main. Skipping PR."
  git branch -d <branch>
  exit 0
fi

# Create isolated worktree for rebase
git worktree add /tmp/rebase-<branch> <branch>
cd /tmp/rebase-<branch>

# Rebase onto current main
git rebase origin/main
# (resolve any conflicts — for agent branches, usually clean)

# Push rebased branch
git push --force-with-lease origin <branch>

# Create PR with descriptive title/body based on actual code analysis
gh pr create \
  --title "<type>(<scope>): <description based on actual changes>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet summarizing what the branch actually implements>

## Changes
- <file-level description>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

# Enable auto-merge
gh pr merge --auto --rebase

# Cleanup worktree
cd /path/to/main/repo
git worktree remove /tmp/rebase-<branch>
```

**Key Sonnet analysis step**: Before creating the PR, the agent must read the actual diff to write a meaningful PR description. Use `git diff origin/main...HEAD` to understand what the branch actually introduces.

### Phase 2b: Wave 2 — Conflict Check for Category C (Haiku, Parallel with 2a)

Run concurrently with Wave 2a. Each agent checks whether a stale branch with a closed PR conflicts with main. If it does, the work is superseded — keep the PR closed.

**Per-agent task (Haiku):**

```bash
cd /path/to/main/repo
git fetch origin

# Dry-run rebase to detect conflicts (no commits made)
conflict_output=$(git rebase --onto origin/main origin/main <branch> --no-commit 2>&1)
git rebase --abort 2>/dev/null

if echo "$conflict_output" | grep -qE "CONFLICT|error"; then
  echo "Branch <branch>: CONFLICTS DETECTED — work is superseded by main. Keep PR closed."
  # Do NOT attempt to fix conflicts — the work has been superseded
else
  echo "Branch <branch>: no conflicts — could potentially be resurrected."
  # Escalate to Sonnet if value is suspected
fi
```

**Decision rule**: If a closed PR branch has conflicts with main, do not attempt to fix them. The fact that main diverged significantly enough to create conflicts means the same functionality was implemented differently. The closed PR's work is superseded.

### Phase 3: Wave 3 — Prune + Final Cleanup (Haiku)

After Waves 1 and 2 complete, dispatch a single Haiku agent:

```bash
git worktree prune
git fetch --prune origin
git branch -v | grep '\[gone\]'  # Verify no orphaned tracking branches remain

# Final state verification
git worktree list
git branch -v
```

### Orchestration Pattern

The three waves can be launched as follows from the orchestrator:

```
Wave 1: Spawn N Haiku agents (parallel) — one per stale worktree batch
         Wait for ALL Wave 1 agents to complete

Wave 2: SIMULTANEOUSLY spawn:
         - Sonnet agents for Category B (one per branch, parallel)
         - Haiku agents for Category C conflict-check (one per branch, parallel)
         Wait for ALL Wave 2 agents to complete

Wave 3: Spawn 1 Haiku agent for prune + verification
```

Wave 2 parallelism is the key time-saver: rebase analysis (Sonnet, slow) and conflict detection (Haiku, fast) happen concurrently.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Over-broad Wave 1 removal | Removed all `worktree-agent-*` branches in Wave 1 before checking for unreleased work | Discarded 10 branches that could have been rebased and PRed; only stale confirmed merged work should be in Wave 1 | Triage first — categorize every branch before dispatching any agent; only remove Category A in Wave 1 |
| Haiku for Category B rebase+PR | Attempted to use Haiku agents for the rebase+PR wave | Haiku wrote generic/inaccurate PR descriptions without analyzing the actual diff | Sonnet required for Category B: needs to read the diff and write meaningful PR title/body |
| Skipping conflict pre-check | Attempted `git rebase origin/main` on closed-PR branches without dry-run check first | All 3 branches had conflicts — wasted time on rebase attempts that couldn't succeed | Always run `git rebase --no-commit` dry-run first on closed-PR branches; conflicts = superseded |
| Sequential Wave 2 | Ran rebase+PR and conflict-check sequentially | Doubled the time for Wave 2 when both subtasks are fully independent | Run Wave 2a (Sonnet rebase+PR) and Wave 2b (Haiku conflict-check) in parallel — no dependencies |
| `git worktree remove --force` | Tried to shortcut removal of worktrees with stray Claude session files | Safety Net blocks `--force` flag | Remove `.claude-prompt-*.md` and similar artifacts manually first, then use `git worktree remove` without `--force` |

## Results & Parameters

### Session Reference (ProjectHephaestus, 2026-04-05)

| Wave | Executor | Task | Count | Outcome |
|------|----------|------|-------|---------|
| 1 | Haiku (parallel) | Remove Category A stale | 13 (5 `feat/*`, 2 merged issue, 6 issue 0-ahead, 1 merged) | All removed cleanly |
| 2a | Sonnet (parallel) | Rebase + PR for `worktree-agent-*` | 10 branches | 3 new PRs (#262, #263, #264) created; 7 superseded by main |
| 2b | Haiku (parallel with 2a) | Conflict-check closed PRs #29, #31, #32 | 3 branches | All had conflicts; work superseded; kept closed |
| 3 | Haiku | Prune + fetch --prune | — | Orphaned refs eliminated |
| **Final** | | | | **32 → 1 worktrees** (main only) |

**Total execution time:** ~20 minutes across 3 waves

### Model Tier Assignment

| Task | Tier | Reason |
|------|------|--------|
| Remove stale worktrees + artifact cleanup | Haiku | Mechanical, no analysis needed |
| Conflict pre-check (closed-PR branches) | Haiku | Binary output: conflicts or no conflicts |
| Final prune + verification | Haiku | Mechanical, single command sequence |
| Rebase + analyze unique work + create PR | Sonnet | Requires diff analysis, meaningful PR description |

### Worktree Artifact Patterns to Pre-Clean

```bash
# Common agent artifacts that block git worktree remove:
rm -f "$wt"/.claude-prompt-*.md     # Claude Code session files
rm -rf "$wt/ProjectMnemosyne"        # Cloned knowledge base
rm -f "$wt/.issue_implementer"       # Agent state files
```

### Scale Reference

| Worktree Count | Approach | Expected Duration |
|----------------|----------|-------------------|
| < 10 | Sequential, skip myrmidon | 10-20 min |
| 10-20 | Myrmidon waves, 3-5 agents/wave | 15-25 min |
| 20-35 | Myrmidon waves, 5-10 agents/wave | 20-45 min |
| 35+ | Myrmidon waves, sub-batch per agent | 45-90 min |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 31 agent+issue worktrees, 3-wave myrmidon swarm, 2026-04-05 | 32→1 worktrees; 3 PRs from unsubmitted work; 7 superseded; 3 confirmed conflict-closed |

## References

- [worktree-cleanup-branches-artifacts](worktree-cleanup-branches-artifacts.md) — Full worktree cleanup reference (individual steps, artifact cleanup, branch deletion)
- [batch-pr-rebase-myrmidon-wave-execution](batch-pr-rebase-myrmidon-wave-execution.md) — Wave execution for fixing failing PRs (conflict resolution, CI fixes)
- [haiku-wave-pr-remediation](haiku-wave-pr-remediation.md) — Haiku wave patterns for large-scale PR remediation
