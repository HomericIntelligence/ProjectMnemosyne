---
name: myrmidon-swarm-resume-drain-in-flight-prs-first
description: "When resuming a stalled myrmidon swarm session, drain all in-flight PRs (CI fix loop, rebases, merges) BEFORE dispatching new waves. New work atop unresolved PRs cascades rebase chaos. Use when: (1) starting a session that finds N open PRs from a prior session, (2) prior session ended mid-CI-fix-loop, (3) `gh pr list --state open --author @me` returns 3+ PRs in BLOCKED/DIRTY state."
category: architecture
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [myrmidon, swarm, resume, in-flight-prs, ci-fix-loop, phase-a, drain-queue, rebase-cascade, session-handoff, orchestration]
---

# Myrmidon Swarm Resume — Drain In-Flight PRs First

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-05-17 |
| Objective | Codify the Phase A "drain queue first" rule for resumed swarm sessions |
| Outcome | Verified — drained 6 stale PRs + 1 fix-main PR before dispatching B/C/D waves prevented hours of rebase chaos |
| Verification | verified-ci |

When an L0 commander resumes a myrmidon swarm session that ended mid-flight,
the strongest temptation is to dispatch new waves immediately. **Do not.**
New work atop unresolved PRs inherits broken state, saturates the GitHub
runner pool, and forces cascading rebases across every PR in the fleet.

The verified rule: **Phase A (drain) must complete to 0 in-flight PRs
before Phase B/C/D (new waves) begin.**

## When to Use

- Resuming a swarm session that left N open PRs from a prior run
- Prior session's last act was dispatching agents that haven't been verified
- `gh pr list --state open --author "@me" --limit 50` returns 3+ PRs
- About to dispatch new waves that touch the same files as in-flight PRs

### Do NOT use when

- Open PRs are from a different author (not your swarm's work)
- In-flight PRs are <30 min old (still mid-CI normally — let CI finish)
- Only 1-2 open PRs from prior session AND main is verifiably green
  (a small queue is not a "stalled swarm")

## Verified Workflow

```bash
# Phase A.0 — pre-flight: check main is green
gh run list --branch main --limit 5 --json conclusion,name,status
# If main is broken: fix it FIRST (see ci-cd-broken-main-parallel-fix-wave skill v1.4.0+)

# Phase A.1 — list in-flight PRs (ground truth, not memory)
gh pr list --state open --author "@me" --limit 50 \
  --json number,mergeStateStatus,headRefName,title

# For each PR: classify the failure mode
for PR in $(gh pr list --state open --author "@me" --json number --jq '.[].number'); do
  echo "=== PR #$PR ==="
  gh pr view "$PR" --json statusCheckRollup --jq \
    '.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name'
done

# Phase A.2 — categorize each PR:
#   DIRTY                          -> needs rebase (Haiku rebase agent)
#   BLOCKED + FAILURE checks       -> real CI fix needed (Sonnet fix agent)
#   BLOCKED + 0 FAILURE checks     -> stale; rebase to retrigger
#   UNKNOWN                        -> GitHub computing; wait 30s and re-check

# Phase A.3 — dispatch fix/rebase agents IN PARALLEL
#   subagent_type: general-purpose  (NEVER feature-dev:code-architect)
#   isolation: "worktree"
#   one agent per PR

# Phase A.4 — only after `gh pr list` shows 0 open PRs from @me,
#             dispatch new B/C/D waves.
```

## Detailed Steps — Verified Workflow

1. **Don't trust the prior session's last reported state.** Rerun
   `gh pr list` to get ground truth. PRs may have merged, gone DIRTY, or
   had their CI flip since the session ended.
2. **Re-classify every open PR.** Assume nothing about prior categorization.
3. **Dispatch one rebase/fix agent per PR** with:
   - `subagent_type: general-purpose` (NEVER `feature-dev:code-architect` —
     that subagent is read-only by design and cannot push fixes)
   - `isolation: "worktree"` to prevent file-system collisions
4. **Each agent's prompt MUST include:**
   - Explicit branch name (no "infer from PR title")
   - `git ls-remote --exit-code --heads origin <branch>` collision check
     before any push
   - `gh pr merge --auto --squash` re-enable after force-push (GitHub
     clears auto-merge state on force-push)
5. **After all agents report:** run
   `gh pr list --author "@me" --state all --limit 50` for ground-truth
   PR counts. **Never trust agent-reported PR numbers** — worktree-isolated
   agents racing each other can collide on branch names or report stale
   numbers from their local view.
6. **Only when 0 PRs in flight:** proceed to new waves (B/C/D).

## Failed Attempts (verified-ci)

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Dispatched new MEDIUM Wave 3 + HARD-tier agents in parallel with the in-flight Phase A PRs | 10 agents launched concurrently; 6 in-flight PRs still BLOCKED at the time | The new PRs were rebased onto stale-broken main and inherited the same FAILURE state; runner pool saturated by 14 simultaneous PR CIs ("queued" not "in_progress"); cascade rebase later required for every PR | Drain ALL in-flight PRs to MERGED state BEFORE dispatching new B/C/D agents. The token cost of waiting for green is far less than the cost of rebase chaos. |
| Skipped pre-flight main-is-green check | Assumed prior session left main green | Main was broken via PR #286's clang-tidy violations; all 6 downstream PRs inherited the failure; took 90+ min to detect | Always `gh run list --branch main --limit 3` before any rebase. If main has FAILURE on required checks, fix main FIRST (see [[ci-cd-broken-main-parallel-fix-wave]]). |
| Trusted agent-reported PR numbers | Multiple agents reported "PR #392" but actual PRs from other agents had different numbers | Worktree-isolated agents racing each other can collide on branch names; agent's local view is stale; only `gh pr list` is authoritative | After every wave: `gh pr list --author "@me" --state all --limit 50` for ground truth. Never trust an agent's claim about PR numbers. |

## Results & Parameters

### Pre-flight checklist (run before Phase A.1)

- [ ] `gh run list --branch main --limit 5` — main's last 5 runs are SUCCESS
- [ ] `gh pr list --state open --author "@me" --limit 50` — captured ground truth
- [ ] Worktree directory has space (`df -h` on `/tmp` or worktree root)
- [ ] No prior agent processes still running (`ps -ef | grep -i claude`)
- [ ] Runner pool not already saturated (`gh run list --status in_progress --limit 20`)

### Approximate phase durations (from verified session)

| Phase | Duration | Agents |
|-------|----------|--------|
| Drain 6 PRs | 30-60 min | 1 Sonnet triage + 4-6 Haiku/Sonnet fix/rebase |
| Fix broken main | +30-45 min (if needed) | 1 Sonnet fix-main agent (blocking) |
| Dispatch new B/C/D waves | After 0 in-flight | Per [[batch-low-difficulty-issue-impl]] |

### Runner saturation threshold

- ~10-12 concurrent PR CIs is the practical cap on GitHub free-tier
  ubuntu runners. Beyond that, jobs sit in `queued` state and stall
  every downstream PR. Phase A drain explicitly avoids this saturation.

## Related Skills

- [[ci-cd-broken-main-parallel-fix-wave]] — broken-main detection + fix
- [[myrmidon-swarm-end-to-end-orchestration-full-workflow]] — broader L0 commander pattern
- [[batch-low-difficulty-issue-impl]] — wave structure
- [[batch-pr-rebase-workflow]] — rebase batching mechanics
- [[parallel-issue-wave-execution]] — wave-level parallelism rules
- [[github-branch-protection-strict-false-stale-ci-merge]] — auto-merge re-enable after force-push

## Verified On

- **Project:** ProjectAgamemnon
- **Session:** 2026-05-17 (resumed prior 2026-05-16 swarm)
- **Scale:** 14 PRs drained; 6 prior in-flight + 8 fresh (B/C/D waves)
- **Verification:** verified-ci — all 14 PRs reached MERGED state without
  cascading rebase chaos; runner pool stayed below saturation throughout
