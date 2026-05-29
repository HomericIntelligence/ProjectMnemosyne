---
name: clear-open-issue-backlog-myrmidon-swarm
description: "End-to-end orchestrator recipe for clearing an entire open GitHub issue backlog with a single myrmidon-swarm session: preflight the whole backlog, re-grade each issue against current code, map file ownership, dispatch wave-based parallel agents, trust-but-verify each PR, and close out. Use when: (1) an open-issue backlog has 5+ issues to triage and implement in one session, (2) planning a myrmidon swarm to close out accumulated issues, (3) managing file-ownership collisions across parallel agents, (4) deciding which issues to flag to the user vs dispatch to agents."
category: tooling
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - myrmidon
  - swarm
  - issue-backlog
  - orchestration
  - file-ownership
  - wave-dispatch
  - trust-but-verify
  - issue-triage
  - re-grade
  - squash-merge
---

# Clear Open Issue Backlog with Myrmidon Swarm — End-to-End Orchestrator Recipe

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Close an entire open-issue backlog in one myrmidon-swarm session: triage, re-grade, dispatch, verify, close out |
| **Outcome** | 9 open issues → 5 PRs merged, 1 verified-closed with no PR, 1 re-graded and left open with evidence, 2 flagged to user. Zero file collisions across 5 parallel Wave-1 agents. main green, ruff/mypy clean (286 files), 762 automation tests pass |
| **Verification** | verified-local — all 6 PRs merged, main green, 762 automation tests pass; orchestration-process learning observed end-to-end locally in one session (2026-05-28, ProjectHephaestus) |

## When to Use

- An open-issue backlog has 5+ issues to triage and implement in one session
- Planning a myrmidon swarm to close out accumulated GitHub issues
- Need to detect and manage file-ownership collisions before dispatching parallel agents
- Deciding which issues to flag to the user vs safely dispatch to agents
- Recovering from a partial backlog-clearing attempt (re-run from Step 3)
- Validating that issues are still relevant before implementing them (re-grading)

## Verified Workflow

### Quick Reference

```bash
# Step 0 — preflight
gh issue list --state open --json number,title,body | jq -r '.[] | "\(.number)\t\(.title)"'

# Step 0 — check repo merge settings (CRITICAL — determines --squash vs --rebase)
gh api repos/ORG/REPO --jq '{rebase:.allow_rebase_merge,squash:.allow_squash_merge,merge:.allow_merge_commit}'

# Step 0 — check CI health on main
gh run list --branch main --limit 5 --json status,conclusion,name

# Step 1 — for each issue, check if prior PRs already reference it
gh pr list --search "#N" --state all --json number,title,state,mergedAt | jq .

# Step 2 — re-grade: check CURRENT file state vs issue text
grep -rn "function_name\|class_name" hephaestus/ --include="*.py" | wc -l

# Step 4 — dispatch agents (squash-only org example)
# (see Detailed Steps)

# Step 6 — trust-but-verify each PR
gh pr view <#> --json state,autoMergeRequest,additions,deletions,files,body \
  | jq '{state:.state,autoMerge:.autoMergeRequest,files:[.files[].path],closes:(
      .body | scan("Closes #[0-9]+")
    )}'

# Step 7 — close-out
pixi run pytest tests/unit -v
pixi run ruff check hephaestus/ tests/
pixi run mypy
```

### Detailed Steps

**Step 1 — PREFLIGHT THE WHOLE BACKLOG**

Before any dispatch:

1. Run `gh issue list --state open` to enumerate all open issues.
2. For each issue, check whether prior PRs already reference or closed it:
   `gh pr list --search "<issue-number>" --state all --json number,title,state,mergedAt`
3. Check repo CI is green on main: `gh run list --branch main --limit 5`
4. Check repo merge settings — this determines which `gh pr merge` flag to use:
   ```bash
   gh api repos/ORG/REPO --jq '{rebase:.allow_rebase_merge,squash:.allow_squash_merge}'
   ```
   If `squash: true` and `rebase: false`, ALWAYS use `--squash` not `--rebase`. Using `--rebase` in a squash-only repo causes `gh pr merge --auto --rebase` to silently never arm auto-merge.

**Step 2 — RE-GRADE EACH ISSUE AGAINST CURRENT CODE**

Issue text reflects filing-time state, not current repo state. Before dispatching any agent:

- Read the relevant source files referenced by each issue.
- Classify each issue as one of:
  - **DONE-ALREADY**: The issue's goal is fully achieved in current `main`. Action: verify with evidence, then close with `gh issue close <N> --comment "Verified done: <evidence>"` — no PR needed.
  - **PARTIAL**: Scaffolding is present; full implementation is not. Action: note what remains, scope a targeted agent task.
  - **KEEP**: Issue is still valid and unaddressed. Action: dispatch agent.
  - **MOOT**: The issue describes work that is no longer relevant (e.g., a refactor the codebase already outgrew). Action: post evidence, let human close — do NOT dispatch.

Real examples from 2026-05-28 session:
- A "revert OS matrix" issue was already done in main → DONE-ALREADY, closed with no PR
- A "decompose 1912-line God Class" issue: file was now 872 lines with 21/40 methods being delegation shims → MOOT, posted evidence, did not dispatch
- An "early-exit loop" issue already had its scaffolding present → PARTIAL, dispatched targeted agent

**Step 3 — MAP FILE OWNERSHIP**

Before dispatch, list every file each KEEP/PARTIAL issue touches. Detect collisions:

```bash
# For each issue, note the files changed. Collisions = same file in 2+ issues.
# Example collision map:
# Issue A → review_state.py, utils.py
# Issue B → review_state.py, CONTRIBUTING.md   ← collision on review_state.py
# Issue C → CONTRIBUTING.md, README.md          ← collision on CONTRIBUTING.md
```

**When 2+ issues touch the SAME file: BUNDLE into ONE sub-agent**, producing 2+ atomic commits and one PR with one `Closes #N` line per issue. Do NOT run colliding issues as parallel agents — this causes rebase races / merge conflicts.

**Disjoint-file issues run as parallel agents in the same wave.**

**Step 4 — DISPATCH WAVES**

Agent dispatch parameters:
- Model: `sonnet` (never Haiku for judgment work — Haiku for bulk mechanical transforms only)
- Isolation: `worktree`
- Max agents per wave: 5
- File-ownership line FIRST in each prompt (prevents scope creep)
- Include hard LOC budget if refactoring (e.g., "do not increase file beyond N lines")
- Include signed commits requirement: `git commit -S`
- PRECOMMIT_STALL abort clause: "if pre-commit hooks hang >60s, skip them, commit, push, let CI validate"
- EXECUTE directive: "Do NOT return a plan, do NOT ask for approval. Execute immediately."
- Each agent runs `/advise` before work and `/learn` after

Auto-merge command (squash-only org):
```bash
gh pr merge "$PR_NUMBER" --auto --squash --repo ORG/REPO
```
NOT `--rebase` even if CLAUDE.md documents `--rebase` — always check actual repo merge settings first.

Flag to user (do NOT dispatch) any issue that is:
- Admin/security config (branch ruleset edits, org settings — needs repo-admin)
- Environment-bound (e.g., lockfile regen requiring running `pixi update`)
- High-regression-risk refactors the user should scope/approve first

The user may resolve some flagged issues in parallel during the run (e.g., closed a branch ruleset issue mid-run).

**Step 5 — TRUST-BUT-VERIFY EACH PR**

Never trust the agent's self-report alone. After each wave, for every PR:

```bash
gh pr view <#> --json state,autoMergeRequest,additions,deletions,files,body
```

Verify:
1. `autoMergeRequest` is non-null and method is `SQUASH` (not null / not REBASE)
2. The literal `Closes #N` line(s) are present in `.body` (capital C, no colon, on its own line)
3. The `.files` list matches the agent's declared file ownership (catches scope creep or collision)
4. `state` is `OPEN` (not DRAFT, not already merged by accident)

**Step 6 — CLOSE-OUT**

After all waves' PRs have merged:

```bash
# Run full test suite on merged main
pixi run pytest tests/unit -v
pixi run ruff check hephaestus/ tests/
pixi run mypy

# Capture orchestration learnings
# /learn (this skill)

# Report remaining user-owned items to user
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Taking issue text at face value | Queued implementation for "revert OS matrix" and "decompose God Class" issues | Issue text reflected filing-time state; code had already changed | Re-grade every issue against CURRENT code before dispatching any agent |
| Running two same-file issues as parallel agents | Dispatched two agents that both touched `review_state.py` | Rebase race: second agent's PR could not rebase cleanly onto first agent's merged commit | Map file ownership first; bundle colliding issues into one agent with atomic commits |
| Using CLAUDE.md-documented `--rebase` for auto-merge | Ran `gh pr merge --auto --rebase` per CLAUDE.md instructions | Repo is squash-only; `--rebase` silently never arms auto-merge, leaving PRs stuck | Always `gh api repos/ORG/REPO` to check merge settings; use `--squash` for squash-only repos |
| Dispatching a worktree agent for branch-ruleset edit | Tried to have an agent fix a branch protection ruleset | Agent lacked repo-admin permission; operation requires GitHub org admin | Flag admin/env/high-risk items to the user; only dispatch what a worktree agent can safely do |
| Dispatching a "moot" refactor because issue was open | Was about to dispatch a God-Class decomposition agent | File had already been restructured (1912 → 872 lines, 21/40 methods delegation shims); agent would have created churn on top of completed work | Re-grade confirms DONE-ALREADY/MOOT before dispatch, even if the issue is legitimately filed |

## Results & Parameters

**Session results (2026-05-28, ProjectHephaestus):**

```
Backlog: 9 open issues
─────────────────────────────────────────────
DONE-ALREADY (1):   #539 — OS matrix revert → verified in main, closed with no PR
MOOT (1):           #468 — God Class decomposition → evidence posted, left open for human close
FLAGGED-TO-USER (2): #N — branch ruleset (admin); #N — pixi lockfile regen (environment-bound)
DISPATCHED (5):     5 PRs merged → #667 #668 #669 #670 + CLAUDE.md fix PR
─────────────────────────────────────────────
Wave-1: 5 parallel agents (disjoint file sets)
Wave collisions: 0
File-ownership violations: 0
Auto-merge armed correctly: 5/5 (squash)
─────────────────────────────────────────────
Post-merge: main green, ruff clean (286 files), mypy clean, 762 automation tests pass
```

**Merge setting check command:**
```bash
gh api repos/ORG/REPO --jq '{rebase:.allow_rebase_merge,squash:.allow_squash_merge,merge:.allow_merge_commit}'
# HomericIntelligence repos: {"rebase": false, "squash": true, "merge": false}
# → Always use: gh pr merge --auto --squash
```

**Agent prompt template (file-ownership line first):**
```
FILE OWNERSHIP: You own ONLY these files: <list>. Do not modify any other files.
EXECUTE: Do NOT return a plan, do NOT ask for approval. Implement immediately.
PRECOMMIT_STALL: If pre-commit hooks hang >60s, abort them, commit, push, let CI validate.
Signed commits: git commit -S
Auto-merge: gh pr merge --auto --squash (NOT --rebase)
PR body must contain on its own line: Closes #<N>
Run /advise before starting. Run /learn after completing.
<task description>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-28 backlog-clearing session | 9 issues → 5 PRs merged, 762 tests pass |
