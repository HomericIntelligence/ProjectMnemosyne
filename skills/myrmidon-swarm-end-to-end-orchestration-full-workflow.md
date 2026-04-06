---
name: myrmidon-swarm-end-to-end-orchestration-full-workflow
description: "Full end-to-end L0 commander pattern for complex myrmidon orchestration sessions. Use when: (1) task spans 3+ phases (cleanup + rebase + merge + CI + knowledge), (2) 10+ sub-tasks with mixed agent tiers required, (3) cross-repo work requiring /advise and /learn coordination, (4) feedback loops and decision gates are needed before committing to destructive operations, (5) auto-merge assumption cannot be made (CI may fail)."
category: architecture
date: 2026-04-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [myrmidon, orchestration, l0-commander, multi-phase, planning, wave, ci, auto-merge, feedback-loop, end-to-end, knowledge-capture]
---
# Myrmidon Swarm: End-to-End Orchestration Full Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Objective** | L0 commander pattern for complex multi-phase myrmidon sessions: cleanup → rebase → PR creation → CI fix → merge → knowledge capture |
| **Outcome** | Successful — 32→1 worktrees, 6 PRs merged with CI passing, 3 skills created in ProjectMnemosyne |
| **Verification** | verified-ci |

Covers the **orchestration meta-pattern** — how the L0 orchestrator structures a multi-hour session involving heterogeneous sub-tasks, multiple agent tiers, feedback loops, and CI integration. Companion to `myrmidon-waves-worktree-cleanup-rebase-pr-merge` (tactical wave execution) and `batch-pr-rebase-myrmidon-wave-execution` (PR rebase + conflict strategy). This skill is about **session architecture**, not individual wave tactics.

## When to Use

- End-to-end task spans 3+ distinct phases with dependencies between phases
- Mix of destructive operations (worktree removal, force-push) and creative operations (PR creation, knowledge capture)
- Task scope is not fully known at start — requires exploration sub-agents before planning
- CI failures are plausible and require a fix workflow, not just auto-merge and hope
- Session involves cross-repo work (e.g., learn → ProjectMnemosyne skill creation)
- Risk of mid-execution pivots if plan is not explicitly approved before agent deployment

Do NOT use when:
- Task is a single well-defined wave (use `myrmidon-waves-worktree-cleanup-rebase-pr-merge`)
- All sub-tasks are known upfront with no exploration needed
- Session is < 30 minutes estimated

## Verified Workflow

### Quick Reference

```bash
# Phase 1: Exploration — dispatch Sonnet to gather state
# (worktree count, PR state, branch status, CI health)

# Phase 2: Design — L0 creates structured plan with wave assignments
# Present plan to user BEFORE spawning any agents

# Phase 3: User Approval Gate
# Never spawn destructive agents without explicit approval

# Phase 4: Wave Execution
# Wave 1 (Haiku, parallel): mechanical cleanup
# Wave 2a (Sonnet, parallel): analysis + rebase + PR
# Wave 2b (Haiku, parallel with 2a): conflict checks
# Wave 3 (Haiku): prune + verify

# Phase 5: CI Monitoring + Fix Loop
# After PRs created, monitor CI; dispatch Haiku fix agents as needed
gh pr checks <N> --watch
gh run view <run-id> --log-failed
# Fix agent → push → re-enable auto-merge

# Phase 6: Knowledge Capture (parallel sub-agents)
# After all PRs merged, dispatch /learn sub-agents
# One sub-agent per skill being captured
```

### Phase 1: Exploration (Sonnet Sub-Agent)

Dispatch a single Sonnet sub-agent to gather the full state before any planning:

```bash
# Sub-agent gathers:
git worktree list --porcelain               # All worktrees
git branch -v                               # Branch states
gh pr list --state open --json number,title,headRefName,mergeStateStatus
gh pr list --state closed --limit 20 --json number,title,state
# For each open PR:
gh pr checks <N> --json name,status,conclusion
```

Also run `/advise` as a sub-agent call at this phase to pull relevant prior learnings before designing the plan. This prevents re-discovering known failure modes during execution.

**What the exploration output must contain:**
- Exact count of worktrees (total, main, stale, active)
- Each branch: commits ahead of main, PR state (open/closed/merged/NONE), CI state
- Any existing open PRs: CI status, merge readiness
- Relevant ProjectMnemosyne skills found via /advise

### Phase 2: Plan Design (L0 Orchestrator)

After exploration, the L0 orchestrator designs a structured multi-wave plan. The plan must include:

```
## Proposed Plan

### Wave 1 — Stale Cleanup (Haiku, parallel)
- Remove N worktrees: <list by path>
- Estimated time: X min

### Wave 2a — Rebase + PR (Sonnet, parallel, concurrent with 2b)
- Branches needing PR: <list>
- Sonnet agents: 1 per branch
- Estimated time: X min

### Wave 2b — Conflict Check (Haiku, parallel, concurrent with 2a)
- Closed-PR branches to check: <list>
- Estimated time: X min

### Wave 3 — Prune + Verify (Haiku, single)
- git worktree prune + git fetch --prune
- Estimated time: X min

### Phase 5 — CI Monitoring + Fix Loop
- Monitor all new PRs for CI failures
- Dispatch Haiku fix agents if pre-commit/lint fails

### Phase 6 — Knowledge Capture
- Skills to create: <list>
- Sub-agents: 1 per skill

### Go / No-Go Criteria
- Wave 1 irreversible: branches deleted after worktree remove
- Decision gates: present before destructive operations
```

### Phase 3: User Approval Gate

**Critical**: Present the full plan before dispatching ANY agents. Wait for explicit user approval.

Approval request format:
```
I have the exploration results. Here is my proposed plan:

[PLAN CONTENT]

This plan will:
- Permanently remove N worktrees (Wave 1 — irreversible)
- Create N PRs from currently-unpublished work (Wave 2a)
- Confirm N closed-PR branches as superseded (Wave 2b)

Shall I proceed?
```

Do not interpret silence or continued conversation as approval. Wait for explicit "yes", "proceed", "approved", or equivalent.

### Phase 4: Wave Execution

Execute waves using the `myrmidon-waves-worktree-cleanup-rebase-pr-merge` skill for tactical details. Key orchestration rules:

1. **Wave 1 must complete before Wave 2**: stale worktrees removed first prevents agent confusion
2. **Wave 2a and 2b run in parallel**: Sonnet rebase+PR work is slow; Haiku conflict checks are fast; do both simultaneously
3. **Wave 3 only after Wave 2**: prune after all changes committed
4. **Check Wave 2a outputs before Phase 5**: count actual PRs created (some branches will be superseded — no PR created)

**Feedback loop at Wave 2 output:**

```
Wave 2a results:
- Branch X: PR #N created, auto-merge enabled
- Branch Y: superseded (all commits already on main), branch deleted
- Branch Z: PR #N created, auto-merge enabled

Decision: 7/10 branches were superseded. Only 3 PRs created.
→ Correct response: proceed with 3 PRs only, do NOT force PRs for superseded work
→ Wrong response: create PRs for superseded branches to "complete the plan"
```

### Phase 5: CI Monitoring and Fix Loop

After PRs are created with auto-merge enabled, monitor CI actively. Do not assume CI will pass.

**Monitoring commands:**

```bash
# Check all new PRs at once
for N in <pr-numbers>; do
  echo "PR #$N:"
  gh pr checks $N --json name,status,conclusion \
    --jq '.[] | select(.conclusion != "SUCCESS" and .conclusion != null) | "\(.name): \(.conclusion)"'
done

# Watch a specific PR
gh pr checks <N> --watch
```

**CI failure response:**

```bash
# Step 1: Identify the failure
gh run view <run-id> --log-failed

# Step 2: Dispatch Haiku fix agent with specific failure context
# Agent task: "Fix pre-commit failure on PR #N. Error: <paste failure>"
# Agent must: fix the code, commit, push to the PR branch

# Step 3: Re-enable auto-merge (GitHub clears it on force-push)
gh pr merge --auto --rebase <N>
gh pr view <N> --json autoMergeRequest
# Confirm: autoMergeRequest.mergeMethod is "rebase", NOT null

# Step 4: Poll for merge
for i in $(seq 1 30); do
  STATE=$(gh pr view <N> --json state --jq '.state')
  [ "$STATE" = "MERGED" ] && echo "PR #$N MERGED" && break
  sleep 30
done
```

**Common CI failure patterns in ProjectHephaestus:**

| Failure | Symptom | Fix |
|---------|---------|-----|
| pre-commit hook | "Files were modified by this hook" | Run `pre-commit run --all-files`, commit changes |
| ruff S101 | "Use of assert detected" | Replace `assert x is not None` with `if x is None: raise` |
| mypy union-attr | "Item of None has no attribute" | Use if/raise guard to narrow type before use |
| pixi task path | "Missing target module" or "Duplicate module" | Ensure task bakes in path; CI step must NOT re-pass path |
| caplog empty | pytest `caplog` shows no records | Set `logger.propagate = True` in try/finally around caplog section |

### Phase 6: Knowledge Capture

After all PRs are merged, capture learnings in ProjectMnemosyne using `/learn` sub-agents.

**Sub-agent delegation pattern for knowledge capture:**

Dispatch one sub-agent per skill being captured. This keeps the main conversation clean and allows parallel skill creation:

```
Sub-agent task:
"You are a Sonnet specialist agent creating a skill in ProjectMnemosyne.
Topic: <skill topic>
Learnings: <paste learnings>
Instructions:
1. Search for existing skills to amend (search: <keywords>)
2. If amending: update the existing skill file
3. If new: create skill/mnemosyne-skill-<name> worktree, create file, validate, commit, PR, auto-merge
4. Validate with python3 scripts/validate_plugins.py
5. Enable auto-merge on PR
6. Clean up worktree"
```

**Required validation before commit:**

```bash
cd /tmp/mnemosyne-skill-<name>
python3 scripts/validate_plugins.py 2>&1 | tail -20
# Must show: Valid: N/N  with no errors before committing
```

### Full Session Timeline Reference

```
Phase 1 (Exploration):    1 Sonnet sub-agent + /advise call     ~10-15 min
Phase 2 (Plan Design):    L0 orchestrator designs plan           ~5 min
Phase 3 (Approval):       User review + approval                ~5 min
Phase 4 (Wave Execution): 3 waves, parallel within waves         ~20-45 min
Phase 5 (CI Fix Loop):    Monitor + dispatch fix agents          ~15-30 min
Phase 6 (Learn):          N sub-agents for skill capture         ~20-30 min
─────────────────────────────────────────────────────────────────────────
Total session (typical):                                         ~1.5-3 hours
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Over-broad Wave 1 agent scope | Agent prompt said "remove stale worktrees" without explicit list | Agent removed too many worktrees before rebase analysis, discarding branches that had unreleased work | Be extremely specific in agent prompts: provide the exact list of worktree paths to remove, not a general instruction |
| Auto-merge assumption | Enabled auto-merge on all 6 PRs and moved on to Phase 6 | 2 PRs failed pre-commit hooks; auto-merge was blocked and they stayed open | Always monitor CI after PR creation; never assume auto-merge will complete; have Phase 5 fix workflow ready |
| Forcing PRs for superseded branches | When Wave 2a reported 7/10 branches superseded, considered creating "stub" PRs anyway to match the plan | Would create unnecessary noise PRs that add no value to main | When agents report superseded work, accept the decision and do NOT create PRs; update plan in real time |
| Skipping /advise before planning | Jumped from exploration to plan design without consulting ProjectMnemosyne | Re-discovered known failure modes (pixi.lock conflict strategy, caplog propagation issue) mid-execution | Always run /advise as a sub-agent call after exploration, before designing the plan |
| Parallel skill capture in main conversation | Tried to create all 3 skills in the main L0 conversation thread | Each skill creation involves worktree creation, file writing, validation, commit, push — sequential in main thread takes 45+ minutes | Delegate skill capture to parallel sub-agents: one per skill, run concurrently |
| Not re-enabling auto-merge after CI fix | Fix agent pushed commit to fix pre-commit failure, declared "done" | GitHub silently cleared auto-merge on the force-push; PR sat open indefinitely | After every push to a PR branch, explicitly re-run `gh pr merge --auto --rebase <N>` and verify the response |

## Results & Parameters

### Session Scale Reference (ProjectHephaestus 2026-04-05)

| Metric | Value |
|--------|-------|
| Starting worktrees | 32 |
| Ending worktrees | 1 (main only) |
| PRs created | 6 (Wave 2a) |
| PRs merged with CI passing | 6 |
| Skills created in ProjectMnemosyne | 3 |
| Total session time | ~3 hours |
| Agents used | 1 Sonnet (exploration), 2 Haiku (Wave 1 + Wave 3), 1 Sonnet (conflict resolution), 1 Haiku (CI fix), 3 Sonnet (skill capture) |
| Data loss incidents | 0 |
| Force-push disasters | 0 |

### Agent Tier Assignment

| Task | Tier | Reason |
|------|------|--------|
| Exploration + state gathering | Sonnet | Requires structured output synthesis across many data sources |
| /advise query | Sonnet | Knowledge retrieval requires semantic matching |
| Remove stale worktrees | Haiku | Mechanical: rm artifacts + git worktree remove |
| Conflict pre-check (closed PRs) | Haiku | Binary output: conflicts or no conflicts |
| Rebase + analyze unique work + create PR | Sonnet | Requires diff reading, meaningful PR description |
| Pre-commit/lint CI fix | Haiku | Pattern-based fix: run pre-commit, commit, push |
| Complex CI fix (logic errors) | Sonnet | Requires understanding of code to fix meaningfully |
| Final prune + verify | Haiku | Mechanical: git worktree prune + git fetch --prune |
| Skill creation in ProjectMnemosyne | Sonnet | Requires synthesis of learnings into structured documentation |
| L0 orchestration | Sonnet/Opus | Session architecture, wave sequencing, user interaction |

### Decision Gates

| Gate | Condition | Action |
|------|-----------|--------|
| Wave 1 pre-flight | Branch list confirmed by exploration | Proceed with exact list |
| Wave 2a output | Some branches superseded | Do NOT create PRs for them; update PR count expectation |
| CI post-creation | Any PR has failing required checks | Dispatch Haiku fix agent before proceeding to Phase 6 |
| Pre-Phase 6 | All PRs in MERGED state | Proceed to knowledge capture |

### L0 Orchestration Checklist

```
[ ] Phase 1: Exploration sub-agent dispatched and completed
[ ] Phase 1: /advise called and prior learnings reviewed
[ ] Phase 2: Plan drafted with explicit wave assignments, agent tiers, time estimates
[ ] Phase 3: User explicitly approved plan before agent deployment
[ ] Phase 4: Wave 1 completed; stale worktrees removed
[ ] Phase 4: Wave 2a (Sonnet) and 2b (Haiku) run in parallel
[ ] Phase 4: Wave 3 (Haiku prune) completed after Wave 2
[ ] Phase 4: Actual PR count confirmed (may differ from plan if branches superseded)
[ ] Phase 5: All new PRs monitored for CI failures
[ ] Phase 5: Any failing PRs fixed; auto-merge re-enabled after fix push
[ ] Phase 5: All PRs confirmed MERGED
[ ] Phase 6: /learn sub-agents dispatched (one per skill)
[ ] Phase 6: All skill PRs merged in ProjectMnemosyne
[ ] Complete: worktree count verified (git worktree list)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 32 worktrees → 1, 6 PRs created and merged, 3 skills captured, 2026-04-05 | Full L0 session: exploration → plan → approval → 3 waves → 2 CI fixes → 3 parallel /learn agents |

## References

- [myrmidon-waves-worktree-cleanup-rebase-pr-merge](myrmidon-waves-worktree-cleanup-rebase-pr-merge.md) — Tactical wave execution for worktree cleanup (Wave 1-3 details)
- [batch-pr-rebase-myrmidon-wave-execution](batch-pr-rebase-myrmidon-wave-execution.md) — Conflict strategies for rebase + PR workflow
- [multi-repo-pr-orchestration-swarm-pattern](multi-repo-pr-orchestration-swarm-pattern.md) — Multi-repo variant of the swarm pattern
- [haiku-wave-pr-remediation](haiku-wave-pr-remediation.md) — Haiku wave patterns for PR remediation
