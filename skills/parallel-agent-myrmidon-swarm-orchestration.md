---
name: parallel-agent-myrmidon-swarm-orchestration
description: "Canonical guide to parallel-agent and Myrmidon swarm orchestration: wave-based dispatch, hierarchical tier assignment (Opus L0 → Sonnet L1/L2 → Haiku L4), agent prompt patterns, dispatcher discipline, multi-repo coordination. Use when: (1) dispatching 5+ parallel agents on independent tasks, (2) coordinating a multi-repo swarm operation, (3) designing tier assignments (Opus vs Sonnet vs Haiku), (4) ensuring deterministic dispatch without orchestrator hand-holding."
category: tooling
date: 2026-06-13
version: "1.1.0"
user-invocable: false
verification: verified-local
history: parallel-agent-myrmidon-swarm-orchestration.history
tags: [merged, myrmidon, swarm, parallel-agent, l0-orchestrator, wave-execution]
---

# Parallel-Agent and Myrmidon Swarm Orchestration — Canonical Guide

> **Dependencies (NOT absorbed):** The following meta-skills implement the orchestration
> substrate this skill rests on; they remain standalone:
>
> - `worktree-parallel-agent-execution` (worktree isolation pattern)
> - `myrmidon-swarm-end-to-end-orchestration-full-workflow` (L0 commander pattern)
> - `tooling-myrmidon-swarm-prompt-guardrails-reduce-stall-rate` (anti-stall prompt design)
> - `tooling-sub-agent-pr-trust-but-verify` (PR verification discipline)
> - `tooling-swarm-subagent-needs-write-tools` (Write-tool gotcha)
> - `tooling-gh-pr-merge-admin-parallel-base-branch-race` (parallel-merge hazard)
> - `stop-reassess-gate-bulk-transformation` (gate-pattern discipline)
> - `hephaestus-learn-sub-agent-must-execute` (`/learn` execution contract)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Canonical reference for parallel-agent and Myrmidon swarm patterns across the HomericIntelligence ecosystem |
| **Outcome** | Consolidated from 20 skills covering dispatch, tier assignment, stall recovery, bulk issue triage, audit coverage, submodule cleanup, and corpus correction |
| **Verification** | verified-local |

## When to Use

1. Dispatching 5+ independent tasks in parallel (bulk issue fixes, audit sections, PR remediations)
2. Coordinating a multi-repo swarm across submodules or related repos
3. Designing model tier assignments for a new swarm command
4. Recovering stalled agents from their worktree state without re-burning tokens
5. Resuming a prior session that left in-flight PRs
6. Running a full-coverage strict audit across a large repo
7. Filing 10+ GitHub issues from an audit report
8. Correcting a large document corpus in parallel batches
9. Verifying file disjointness before launching new waves atop an active merge cascade

## Verified Workflow

### Quick Reference

```bash
# Pre-flight: main must be green before any dispatch
gh run list --branch main --limit 5 --json conclusion,name,status

# Enumerate in-flight PRs (ground truth — never trust memory)
gh pr list --state open --author "@me" --limit 50 \
  --json number,mergeStateStatus,headRefName,title

# Launch parallel agents (one message, multiple Agent calls with run_in_background=true)
# ALWAYS use isolation="worktree" for file-modifying agents

# After each wave — verify from gh, not agent output
gh pr list --author "@me" --state all --limit 50

# File disjointness check before new dispatch atop in-flight cascade
gh pr list --state open --author "@me" \
  --json number,files \
  --jq '.[] | "PR#\(.number):" + (.files | map(.path) | join(","))'
```

### 1. Tier Assignment

| Tier | Levels | Model | Role |
|------|--------|-------|------|
| L0 Commander | L0 | `opus` | Strategic decisions, wave sequencing |
| Orchestrators | L1 | `sonnet` | Section coordination, classification |
| Specialists | L2, L3 | `sonnet` | Design, analysis, code review, judgment |
| Executors | L4, L5 | `haiku` | Mechanical fixes, bulk filing, format-only tasks |

**Tier selection heuristics:**

- Use **Haiku** for mechanical tasks: ruff fix, format fix, single-file edits, `gh issue create`, `.gitignore` additions
- Use **Sonnet** for tasks requiring judgment: classification, multi-file analysis, PR review, worktree recovery
- Use **Opus** for L0 only — wave planning, gate decisions, cross-repo coordination
- `subagent_type: general-purpose` is the ONLY type that has the full tool palette (Bash, Read, Edit, Write). Never use `feature-dev:code-reviewer` for audit or fix agents — they are read-only.

### 2. Wave Sizing and Dispatch Rules

- **Max 5 agents per wave** when runner pool may be capped (GitHub free-tier: ~10-12 concurrent CIs saturates the pool)
- **Single parallel batch** (all agents in one message) when harness concurrency is uncapped and tasks are file-disjoint
- Each agent must get its own `isolation="worktree"` — never have two agents share a working tree
- **Never `git add -A`** — stage specific files only
- **Never `--no-verify`** — fix hook failures; pre-commit auto-fixers converge in 2-3 cycles

### 3. Pre-Dispatch Checklist

Before launching any wave:

- [ ] `gh run list --branch main --limit 5` — all required checks SUCCESS
- [ ] `gh pr list --state open --author "@me" --limit 50` — 0 stale PRs in BLOCKED/DIRTY (or drain first — see §5)
- [ ] File disjointness verified against every in-flight PR's diff (see §6)
- [ ] Runner pool not saturated: `gh run list --status in_progress --limit 20`
- [ ] Wave size ≤5 (or confirmed uncapped harness)

### 4. Agent Prompt Pattern (Anti-Stall)

```
IMPORTANT: DO NOT PLAN. EXECUTE IMMEDIATELY.

1. Run: cat path/to/file
2. Run: [exact edit]
3. Run: pre-commit run --files path/to/changed/file
4. Run: git checkout -b NNN-slug
5. Run: git add path/to/changed/file
6. Run: git commit -m "type(scope): description (Closes #NNN)"
7. Run: git push -u origin NNN-slug
8. Run: gh pr create --title "..." --body "Closes #NNN"
9. Run: gh pr merge --auto --squash
```

- Use imperative `Run:` commands, never descriptive "Steps:" or "Plan:" sections
- Use **Haiku** for mechanical tasks — Haiku over-plans far less than Sonnet
- Start every mechanical prompt with `IMPORTANT: DO NOT PLAN. EXECUTE IMMEDIATELY.`
- Include the current API signatures / correct values in every agent prompt — agents without this context waste tokens re-discovering what you already know
- For body strings with apostrophes/single quotes: `--body-file /tmp/issue-body.md` not `--body '...'`

### 5. Session Resume — Drain In-Flight PRs First

When resuming a session that left N open PRs:

```bash
# Phase A.0 — check main is green (fix main FIRST if broken)
gh run list --branch main --limit 5

# Phase A.1 — classify each in-flight PR
for PR in $(gh pr list --state open --author "@me" --json number --jq '.[].number'); do
  echo "=== PR $PR ==="
  gh pr view "$PR" --json mergeStateStatus,statusCheckRollup \
    --jq '.mergeStateStatus + " | failures: " + ([.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name] | join(", "))'
done

# Phase A.2 — categories:
#   DIRTY                   -> rebase (Haiku agent)
#   BLOCKED + FAILURE       -> CI fix needed (Sonnet agent)
#   BLOCKED + 0 failures    -> stale; rebase to retrigger
#   UNKNOWN                 -> wait 30s, re-check

# Phase A.3 — dispatch one agent per PR, isolation=worktree
# Phase A.4 — only after 0 in-flight PRs, dispatch new waves
```

**Rule:** Phase A (drain) must complete to 0 in-flight PRs before Phase B/C/D begins.
New work atop unresolved PRs inherits broken state and saturates the runner pool.

### 6. File Disjointness Gate (Mid-Cascade Dispatch)

Before dispatching new clusters while 5+ PRs are already in the merge cascade:

```bash
# Enumerate files touched by all in-flight PRs
gh pr list --state open --author "@me" \
  --json number,files \
  --jq '.[] | "PR#\(.number):" + (.files | map(.path) | join(","))'

# Compute overlap: any shared path → queue, do not dispatch
```

| File class | Default risk | Action |
|------------|--------------|--------|
| `src/**`, core C++/Mojo source | High | Serialize if any in-flight PR touches `src/` |
| `.github/workflows/*.yml` | Very high | Always queue |
| `docs/**`, OpenAPI specs | Low | Usually safe to parallelize |
| Client SDK packages | Low | Usually safe |
| Lockfiles (`pixi.lock`, `Cargo.lock`) | High | Serialize |

Re-snapshot in-flight PRs immediately before launching — do not use a stale snapshot.

### 7. Audit Swarm — Full Coverage Methodology

For repos >500 files where per-section swarm is needed:

```bash
# 1. Inventory every file
find . -type f \
  -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/.venv/*' \
  -not -path '*/build/*' -not -path '*/.pixi/*' -not -path '*/__pycache__/*' \
  | sort > /tmp/repo-files.txt

# 2. Bucket into 15 section files (/tmp/audit-section-01.txt ... -15.txt)
#    Every file in exactly one bucket.

# 3. Dispatch — single batch when concurrency allows, else 3 waves of 5
#    subagent_type: general-purpose (NOT feature-dev:code-reviewer — read-only)
#    Each agent gets: section rubric + strict grading + principles list + bucket file

# 4. Assemble: weighted overall grade, GO/NO-GO
```

GO/NO-GO criteria:

| Verdict | Criteria |
|---------|----------|
| **GO** | 0 critical AND ≤2 major AND overall ≥80% |
| **CONDITIONAL GO** | ≤2 critical (scoped fix paths) AND ≥65% |
| **NO-GO** | otherwise |

Weights: Architecture 15%, Source Quality 15%, Testing 12%, Security 12%, Safety 10%, CI/CD 8%, Documentation 7%, AI Tooling 5%, remaining 7 sections ~2.3% each.

### 8. Stall Recovery from Worktree

When a background agent fails with watchdog wording (`status=failed`, "no progress for 600s"):

```bash
# Inspect stalled worktree state
WT=$(ls -dt .claude/worktrees/agent-* | head -1)
cd "$WT"
git branch --show-current
git status --short
git diff --staged --stat
```

| State | `git status` output | Recovery |
|-------|---------------------|----------|
| Empty | (no output) | Restart fresh — cheap |
| Partial-staged | `M  src/...` | Read `git diff --staged`, add missing pieces, commit |
| MM (auto-fixer cycle) | `MM src/...` | Re-stage: `git add -u && git commit -m "..."` (may need 2-3 cycles) |
| Mid-investigation | (empty) but summary captured | Treat like Empty, use insight to drive manual fix |

**NEVER read the agent's transcript file** — it will overflow context.
**NEVER use `--no-verify`** — auto-fixers converge after 2-3 cycles.

Token heuristic: `< 500 tokens` → empty worktree → restart; `> 60k tokens` → recover-and-finish.

### 9. Bulk Issue Filing (No Worktrees Needed)

When filing 10+ `gh issue create` calls (no file modifications):

```bash
# Use plain Agent calls (no isolation=worktree), Haiku model, waves of ≤5
# Multi-line bodies: always write to temp file first
cat > /tmp/issue-body.md << 'EOF'
## Summary
...content with 'single quotes' and apostrophes freely...
EOF
gh issue create \
  --repo ORG/REPO \
  --title "Issue title" \
  --label "bug" \
  --label "priority:high" \
  --body-file /tmp/issue-body.md
```

- Labels: use multiple `--label` flags (NOT comma-separated in one flag)
- Wave limit: ≤5 agents to avoid GitHub API rate limiting
- Verified: 11 issues filed in ~30 seconds (3 waves: 5+5+1 Haiku agents)

### 10. Pre-Classification for Large Backlogs (20+ issues)

Before fix waves, classify all issues using 3 parallel Sonnet agents (~22 issues each):

```
Classify each issue LOW / MEDIUM / HIGH / N/A:
- LOW: single-file change, <50 lines, no architectural impact
- MEDIUM: 2-5 files, module interaction understanding required
- HIGH: 6+ files, architectural decisions, or blocked by other work
- N/A: epic/tracking/blocked issues — skip entirely

Return a markdown table:
| #N | Title | LOW/MEDIUM/HIGH/N/A | one-sentence rationale |
```

Run all 3 classifier agents in a single message; wait for all 3 before proceeding to fix waves.

Fix waves run in order A → B → C → D (docs → config → code → tests). Wave A PRs often merge before Wave D starts, minimizing CI queue contention.

### 11. Multi-Repo / Submodule Swarm

```bash
# Triage submodule dirty state
git submodule foreach --quiet 'echo "$name: $(git status --porcelain | head -3)"'

# Categorize:
# Bucket A: Untracked generated files → gitignore fix (Haiku)
# Bucket B: Real WIP changes          → commit on feature branch, PR (Sonnet)
# Bucket C: Stale checkouts           → fast-forward if on main (Wave 2)

# Wave 1: Independent per-submodule work (parallel)
# Wave 2: Dependent work — worktree cleanup + submodule pin updates
#         Pin ONLY submodules whose main moved forward (never pin to feature branch)
```

Each submodule agent works inside the submodule's own git context — commits inside a submodule
must be made from within the submodule directory, NOT from the parent repo root.

### 12. Corpus Parallel Correction

For correcting 20+ document files after a review pass:

```bash
# Partition files into groups of 5-8 per agent
# Each batch agent:
#   a. Reads the review file for its assigned group
#   b. Makes in-place surgical edits (Edit tool, precise old_string→new_string)
#   c. Adds [corrected: ...] inline markers for auditability
#   d. Never touches review_*.md or verification_*.md (audit trail)

# Inline correction marker format:
# ~8.59 GB [corrected from ~68 GB: formula: 64L × 2 × 8KV × 128hd × 32768tok × 2B]
```

### 13. Strict Review with Audit-Epic Exclusion

When reviewing code that has an existing audit epic with N findings already filed:

```bash
# Step 1 — Build exclusion list FIRST (before reading code)
gh issue list --state open --json number,title,labels,body --limit 200 \
  --repo <owner>/<repo> > /tmp/open_issues.json
gh issue view <epic-number> --repo <owner>/<repo> --json title,body > /tmp/parent_epic.json

# Step 2 — Dispatch parallel Explore agents sliced by PHASE (not by file)
# Step 3 — Spot-verify EVERY concrete claim before writing the plan
grep -n '<symbol>' <claimed-file>
# Step 4 — Categorise: MAJOR (M1..MN) / MINOR (m1..mN) / NITPICK (N1..NN)
# Step 5 — Write plan as deliverable (NOT ExitPlanMode — that's for implementation plans only)
```

Sub-agent claims must be spot-verified — ~3 of 4 agents will have at least one inverted or already-mitigated finding. Budget ~2-5 verifications per agent claim.

### 14. Agent Lifecycle Hooks

To restrict agent capabilities, use hooks in agent frontmatter (Claude Code v2.1.0+):

```yaml
---
name: review-specialist
description: Read-only code review agent
hooks:
  - type: PreToolUse
    matcher: "(Edit|Write|Bash)"
    hooks:
      - type: command
        command: |
          echo '{"decision": "deny", "message": "Review agents are read-only."}'
---
```

Hook types: `PreToolUse` (can allow/deny/modify), `PostToolUse` (read-only logging), `Stop` (cleanup).
Use `once: true` for initialization hooks that should run only once per session.

### 15. Agent-to-Skill Conversion Decision

Convert an agent to a skill when ALL three apply:
- Fixed, predictable, repeatable steps
- Does NOT require exploration or adaptive decision-making
- Acts as automation wrapper, not a reasoning entity

Keep as an agent when: tasks require exploration, cross-module judgment, escalation paths, or
dynamic branching based on discovered state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Dispatched new waves while 6 PRs still BLOCKED | New PRs inherited broken state; runner pool saturated at 14 concurrent CIs; cascade rebase required for every PR | Drain ALL in-flight PRs to MERGED before launching new waves. Token cost of waiting < cost of rebase chaos. |
| 2 | Skipped pre-flight main-is-green check | Main was broken; all 6 downstream PRs inherited the failure; 90+ min to detect | Always `gh run list --branch main --limit 3` before any rebase or new wave. |
| 3 | Trusted agent-reported PR numbers | Two parallel agents both reported "PR \#120"; actual PRs had different numbers | After every wave: `gh pr list --author "@me" --state all --limit 50` for ground truth. |
| 4 | Read stalled agent's JSONL transcript | System reminder forbids it: would overflow context | Inspect stalled agent state via `git status --short` and `git diff --staged`, never via transcript |
| 5 | `rm -rf` cleanup in stalled worktree | Safety Net blocked: "rm -rf outside cwd is blocked" | Use `git rm` or trust `.gitignore` — `__pycache__` is gitignored anyway |
| 6 | Spawned fresh agent for stalled task with 60k+ tokens | Wasted tokens for work the worktree already had ~50% done | Inspect worktree first; recover-and-finish usually cheaper than restart |
| 7 | Used `feature-dev:code-reviewer` for audit agents | Read-only subagent; lacks Bash tool; cannot run `find`, `gh issue list`, `git log` | Always use `subagent_type: general-purpose` for audit agents — full tool palette is non-negotiable |
| 8 | Launched all 15 audit agents at once on a capped harness | Extras queued or failed on harnesses capping at 5 concurrent agents | Check harness limits first; fall back to 3 waves of 5 if needed |
| 9 | Dispatching same-file remediations in parallel | Second PR required two manual rebases before merge | Same-file = serialize. File-level disjointness is the only reliable signal — line ranges don't matter. |
| 10 | Re-snapshot skipped before dispatch | Two in-flight PRs merged in the interim; new cluster claimed a file now in-flight | Re-snapshot in-flight PRs IMMEDIATELY before dispatch, not from a 30-min-old snapshot |
| 11 | Used Sonnet agents with descriptive "Steps:" prompts | Agents paused to present plans instead of executing | Rewrite prompts as explicit `Run: <shell command>` lines with `IMPORTANT: DO NOT PLAN.` header; use Haiku for mechanical tasks |
| 12 | Bulk `gh issue create` with commas in a single `--label` | Labels silently not applied or rejected | Pass one `--label` flag per label; use `--body-file` for apostrophe-containing bodies |
| 13 | Committing submodule changes from parent repo root | "Pathspec is in submodule" error | Submodule commits must happen inside the submodule's own git context |
| 14 | Letting audit agents pick their own files (no bucket list) | Overlap (same file audited twice) and gaps (files audited zero times) | Pre-bucket every file into exactly one section list before dispatch |
| 15 | Single-agent full audit on >500-file repo | Context overflow; quality drops sharply mid-audit | Per-section swarm with bucketing keeps each agent's context tight |
| 16 | Trusting plan-level constants without live verification | Wrong port (8082 vs 8085), wrong NATS URL (WSL2 IP vs service DNS) | Always grep live config files before accepting any constant from a plan doc |
| 17 | Making `ExitPlanMode` call after producing review document | Plan-mode tooling expects an implementation plan; reviewers confused | `ExitPlanMode` is for IMPLEMENTATION plans only. Present review findings as regular markdown. |
| 18 | Anonymous agent IDs on relaunch after dirty recovery | Old planner IDs reused; workspace showed one planner assigned to multiple tasks | After dirty recovery, always relaunch with explicit `--agent-id` values |
| 19 | Recovering stale Liza task claims without cleaning Git state | Liza still showed tasks assigned; git worktrees/branches remained | Recover tasks first (`liza recover-task`), then verify `git worktree list` is clean before relaunch |
| 20 | Gave Haiku agent a canonical SHA map but it looked up its own SHAs | Haiku agents sometimes ignore provided canonical maps and query GitHub APIs for SHAs — got upload-artifact v4.7.1 instead of v7.0.1, setup-python v5.7.0 instead of v6.2.0 | Add explicit instruction: `"DO NOT look up SHAs — use ONLY the values from the canonical SHA map in this prompt. Never query GitHub APIs for SHAs."` as first line after `IMPORTANT: DO NOT PLAN` |
| 21 | Treated BLOCKED mergeStateStatus as PR failure | BLOCKED means CI checks are pending/running, not that the PR failed — caused unnecessary re-investigation | BLOCKED = waiting on CI; FAILURE = actual check failed; only act on FAILURE |

## Results & Parameters

### Verified Swarm Configurations

| Session | Scale | Topology | Outcome |
|---------|-------|----------|---------|
| ProjectScylla audit 2026-05-07 | 1821 files, 15 sections | 3 waves × 5 Sonnet agents | B- (82%), CONDITIONAL GO, issues \#1934-\#1959 |
| ProjectAgamemnon audit 2026-05-17 | 500+ files, 15 sections | 1 batch × 15 Sonnet agents | B- (78%), CONDITIONAL GO, ~10-15 min wall-clock |
| ProjectOdyssey bulk issues 2026-04-11 | 66 issues classified, 28 fixed | 3 classifier + 4 fix-wave | 28 PRs, ~3h wall-clock |
| ProjectScylla stall recovery 2026-05-06 | 5 agents dispatched, 4 stalled | Manual worktree recovery | 4 of 4 recovered, 5/5 PRs shipped |
| Haiku PR remediation 2026-03-15 | 46/49 PRs fixed | Wave-0 diagnosis + fix waves of 5 | 43 fixed, 3 deferred (pre-existing) |
| Meta-repo submodule cleanup 2026-04-03 | 15 submodules, 8 agents | Wave 1 (6) + Wave 2 (2) | 5 PRs, 2 pins updated, 2 worktrees removed |
| ProjectTelemachy bulk triage 2026-04-25 | 9 Haiku agents | Wave A+B + Phase 0 simultaneous | 9 PRs, 0 stall, ~2h wall-clock |
| Corpus correction 2026-04-13 | 66 files, 8 batches | All batches parallel | 100% correction rate with inline audit markers |
| ProjectAgamemnon drain 2026-05-17 | 14 PRs | Phase A drain + B/C/D waves | All 14 merged, no rebase chaos |
| 13-repo SHA-pin swarm 2026-06-13 | 13 repos, 13 agents | 1 single-wave (file-disjoint repos) | All 13 PRs created; Haiku SHA override pitfall discovered |

### Stall Recovery Heuristics

| `total_tokens` in failure notification | Worktree state | Action |
|----------------------------------------|----------------|--------|
| < 500 | Empty/almost-empty | Restart from scratch |
| 500 – 60k | Partial staged or mid-investigation | Read `git diff --staged`, recover if meaningful |
| > 60k | Substantial partial work | Recover-and-finish (saves tokens) |

Pre-commit MM cycle (staged + unstaged after auto-fixer) is normal — re-stage and retry up to 3 times.

### Runner Pool Saturation Thresholds

| Tier | Cap | Action |
|------|-----|--------|
| GitHub free-tier ubuntu runners | ~10-12 concurrent CIs | Stay below; beyond this, jobs sit in `queued` |
| Wave size (safe) | ≤5 agents | Default for all swarm operations |
| Wave size (uncapped harness) | 15 agents | Verified on ProjectAgamemnon 2026-05-17 |

### Auto-Merge Flags by Repo Policy

- `--squash` (default for most HomericIntelligence repos — rebase auto-merge is disabled)
- `--rebase` only when repo explicitly allows it
- Re-enable auto-merge after force-push: `gh pr merge <N> --auto --squash` (GitHub clears state on force-push)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Audit 2026-05-07, stall recovery 2026-05-06 | Verified all patterns |
| ProjectAgamemnon | Audit + drain 2026-05-17, PR remediation | 14 PRs drained, zero rebase chaos |
| ProjectOdyssey | 66-issue classification + 28-issue fix 2026-04-11 | Haiku PR remediation 2026-03-15 |
| HomericIntelligence/Odysseus | Atlas Epic \#151, submodule cleanup 2026-04-03, 35-issue triage 2026-04-23 | Meta-repo patterns verified |
| ProjectTelemachy | Wave A+B 2026-04-25 | .gitignore bundle, silent already-done absorption |
| ProjectHephaestus | Strict review PR \#367 | Audit-epic exclusion pattern |
| ArchIdeas corpus | 2026-04-13 correction pass | 66-file parallel batch correction |
