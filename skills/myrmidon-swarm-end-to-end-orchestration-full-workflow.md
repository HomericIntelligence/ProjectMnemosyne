---
name: myrmidon-swarm-end-to-end-orchestration-full-workflow
description: "Full end-to-end L0 commander pattern for complex myrmidon orchestration sessions. Use when: (1) task spans 3+ phases (cleanup + rebase + merge + CI + knowledge), (2) 10+ sub-tasks with mixed agent tiers required, (3) cross-repo work requiring /advise and /learn coordination, (4) feedback loops and decision gates are needed before committing to destructive operations, (5) auto-merge assumption cannot be made (CI may fail)."
category: architecture
date: 2026-04-28
version: "1.6.0"
user-invocable: false
verification: verified-ci
history: myrmidon-swarm-end-to-end-orchestration-full-workflow.history
tags: [myrmidon, orchestration, l0-commander, multi-phase, planning, wave, ci, auto-merge, feedback-loop, end-to-end, knowledge-capture]
---
# Myrmidon Swarm: End-to-End Orchestration Full Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
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
- Running a `repo-analyze-strict` audit across all repos in an ecosystem (meta-repo + all submodules)
- Filing a per-repo Epic + per-finding child issues across 10+ repos simultaneously
- Recovering from GitHub org monthly API usage limit mid-session

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

# Phase 7: Session Record — create tracking issue on target repo
TITLE="chore(triage): $(date +%Y-%m-%d) issue classification pass"
gh issue create --repo <owner>/<repo> --title "$TITLE" \
  --body "$(cat session-summary.md)"
# Discoverable via: gh issue list --search "chore(triage)"

# Identify mega-agent candidates (files with 6+ issues)
# Count file mentions across issue bodies to find contended files
# Files with 6+ → per-file Sonnet mega-agent; branch: bundle-<file>-<issues>
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
- Per-issue file paths (if the issue inventory includes "files-likely-touched")

**Classifier swarm decision rule**: If Explore agents return file-path evidence per issue (e.g. from an issue inventory that includes "files-likely-touched"), skip the Phase 4 classifier swarm — classify LOW/MEDIUM/HIGH deterministically from contention counts instead. Dispatch classifier agents only when issues lack file-mapping evidence.

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

### Phase 7 — Tracking Issue
- Target repo: <owner>/<repo>
- Title: chore(triage): YYYY-MM-DD issue classification pass
- Body: metrics table + closures + PRs + remaining issues + artifact paths + skill PR links

### Go / No-Go Criteria
- Wave 1 irreversible: branches deleted after worktree remove
- Decision gates: present before destructive operations
```

**Per-file mega-agent rule** — when the issue inventory has file-path evidence, apply this during plan design:

```
For each source file touched by 6+ issues → assign one Sonnet mega-agent
  - Branch name: bundle-<file-stem>-<issue-numbers>
  - One PR per mega-agent; PR title may be long (do not abbreviate)
For cross-file mega-agents → run the one touching most files LAST (Wave E), others first (Wave D)
```

This typically collapses many planned waves into 2 (Wave D: parallel per-file agents, Wave E: solo cross-file agent).

**Parallel Plan agent + Explore agents** — the Plan agent (wave design) can run simultaneously with the Explore agents (inventory/already-done/CI checks) if the Plan agent is given the issue list up front and asked to produce a *conditional* plan ("if file X has 6+ issues, use mega-agent"). This saves one full phase compared to running them sequentially.

### Phase 3: User Approval Gate

**Critical**: Present the full plan before dispatching ANY agents. Wait for explicit user approval.

**Pre-launch checks** — run these before presenting the plan and adjust accordingly:

```bash
# Check auto-merge capability
gh repo view --json autoMergeAllowed --jq '.autoMergeAllowed'
# If false: note in plan that PRs require manual merge; remove --auto from agent prompts

# Check pre-commit hooks
ls .pre-commit-config.yaml 2>/dev/null && echo "hooks present" || echo "NO HOOKS — remove pre-commit steps from agent prompts"

# Check lockfiles (affects CI job templates)
ls package-lock.json dagger/package-lock.json pixi.lock 2>/dev/null
# If missing: use npm install not npm ci in any CI jobs added this session
```

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

**Worktree removal — handle __pycache__:**

Agent worktrees that executed Python accumulate `__pycache__/` dirs that block `git worktree remove`:

```bash
# Clean __pycache__ first, then remove normally (no --force needed)
find .claude/worktrees/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
git worktree remove .claude/worktrees/agent-<id>
git worktree prune
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

### Phase 7: Session Record (Tracking Issue)

After all skill PRs are merged in ProjectMnemosyne, create a permanent tracking issue on the
**target repo** (the repo the session worked on). This makes the session discoverable in future
work via `gh issue list --search "chore(triage)"`.

**Why this matters**: Without a tracking issue, session results exist only in `results.md`
artifact files and the agent's memory. A tracking issue is indexed by GitHub search, visible
in the issue list, and provides a durable cross-reference from the repo to the session artifacts
and ProjectMnemosyne skill PRs.

**Tracking issue creation:**

```bash
# Title format: chore(triage): YYYY-MM-DD issue classification pass
TITLE="chore(triage): $(date +%Y-%m-%d) issue classification pass"

# Body must include:
# - Session metrics table (issues processed, PRs merged, agents used, duration)
# - Table of closures: ALREADY-DONE issues with numbers
# - Table of batch-fix PRs: issue → PR mapping
# - Lists of remaining MEDIUM and HIGH issues (not yet addressed)
# - Artifact file paths (e.g. analysis/issue-triage/results.md)
# - Links to ProjectMnemosyne skill PRs created this session

gh issue create \
  --repo <owner>/<repo> \
  --title "$TITLE" \
  --body "$(cat session-summary.md)"
```

**Tracking issue body template:**

```markdown
## Session: YYYY-MM-DD Issue Classification Pass

### Metrics

| Metric | Value |
|--------|-------|
| Issues classified | N |
| PRs merged | N |
| Agents used | ... |
| Session duration | ~X hours |

### Closures (ALREADY-DONE)

| Issue | Title | Resolution |
|-------|-------|------------|
| #N | ... | Already implemented |

### Batch Fix PRs

| Issue | Title | PR |
|-------|-------|----|
| #N | ... | #M |

### Remaining MEDIUM Issues

- #N: description

### Remaining HIGH Issues

- #N: description

### Artifacts

- `analysis/issue-triage/results.md`

### ProjectMnemosyne Skills

- PR #N: skill/... (amended/created)
```

**HARD issues — enumerate even if leaving them open**: Even when the user says "leave HARD issues alone", the tracking issue body should still enumerate them with rationale (e.g. "requires architectural decision", "cross-cutting concern"). This gives future sessions a quick reference without reading all open issues.

**PR title length**: Mega-agent PR titles can be long (e.g. `feat(executor): 11 improvements — timeout, teardown, retry, logging, dry-run, hooks, rich progress`). This is fine — do not abbreviate. The PR body's `Closes #N` lines are what matter for issue auto-close; the title is secondary.

**Verification**: Confirm the issue was created by running:

```bash
gh issue list --repo <owner>/<repo> --search "chore(triage)" --limit 5
```

### Full Session Timeline Reference

```
Phase 1 (Exploration):    1 Sonnet sub-agent + /advise call     ~10-15 min
Phase 2 (Plan Design):    L0 orchestrator designs plan           ~5 min
Phase 3 (Approval):       User review + approval                ~5 min
Phase 4 (Wave Execution): 3 waves, parallel within waves         ~20-45 min
Phase 5 (CI Fix Loop):    Monitor + dispatch fix agents          ~15-30 min
Phase 6 (Learn):          N sub-agents for skill capture         ~20-30 min
Phase 7 (Tracking Issue): gh issue create on target repo         ~2-5 min
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
| Skipping tracking issue creation | Session ended after Phase 6 skill PRs merged; no tracking issue created on target repo | Session results were only in `results.md` artifact file and agent memory — not searchable via `gh issue list` in future sessions | Always create a `chore(triage): YYYY-MM-DD issue classification pass` tracking issue on the target repo as Phase 7 (final step) |
| `git worktree remove <path>` on agent worktrees after session | Ran `git worktree remove` on 5 unlocked worktrees containing only `__pycache__/` as untracked content | Fails with "contains modified or untracked files" — git treats `__pycache__/` as untracked even though it is irrelevant | Clean `__pycache__` first: `find .claude/worktrees/agent-* -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null` then `git worktree remove`. Alternatively ask user to approve `--force` (Safety Net blocks it without explicit permission). |
| Agent-added CI job breaks subsequent PRs | Added a `typecheck` CI job to `ci.yml` in Wave E (issue #31). This job used `npm ci`. All subsequent PRs picked up this new required check. | The new CI job required `package-lock.json` which didn't exist. PRs #60 and #61 (created in later waves) both failed CI on the new typecheck job. Required dispatch of two fix agents to change `npm ci` → `npm install`. | When a wave adds a new CI job, verify it passes on `origin/main` before launching subsequent waves. New required CI checks affect ALL open PRs. If the new job has a dependency (e.g., lockfile), ensure that dependency is met or the job is non-blocking before continuing. |
| Auto-merge disabled blocks wave completion signal | Used `gh pr merge <N> --auto --rebase` as the final step in all agent prompts, per standard pattern | ProjectProteus had `enablePullRequestAutoMerge: false` at the repository level. Agents reported "auto-merge is not enabled" and PRs stayed open. Wave completion was harder to assess — could not use "all PRs MERGED" as the done signal. | Before starting a swarm session, check `gh repo view --json autoMergeAllowed --jq '.autoMergeAllowed'`. If `false`, the completion signal for each wave must be "all PRs pushed with CI passing" rather than "all PRs MERGED". Adjust monitoring accordingly. |
| Two index.ts agents racing to same file (Wave C) | Dispatched C1 (#10), C2 (#14), C3 (#36) as parallel agents since they touched different functions in `dagger/src/index.ts` | Even though they touched different functions, parallel agents on the same file create merge conflicts. Had to run them sequentially (one per wave-step, each rebasing on origin/main after the previous merged). | Same-file edits must always be sequential even if the edits are to different functions/sections. The "no two agents per wave touching the same file" rule applies even to non-overlapping edits within a file. |
| Running Phase 4 classifier swarm when inventory already has file evidence | Dispatching 3 Explore classifier agents after 3 Explore inventory agents already returned file paths per issue | Duplicate work — inventory agents already provided enough signal for deterministic classification from contention counts | Skip classifier swarm if inventory agents returned file-path evidence; classify LOW/MEDIUM/HIGH directly from contention counts |
| Forking implementation branch from wrong base | Created Atlas branch from `feat/issue-22-ci-hardening` instead of `main` (2026-04-27) | Picked up 12 extra CI commits unrelated to Atlas; PR was not rebased to main; MERGEABLE state was wrong | Always verify branch base: `git log --oneline main..HEAD` before creating PR. If wrong base was used, cherry-pick the work onto a clean `main` fork: `git checkout -b <branch> main && git cherry-pick <sha>` |
| Haiku filers for large issue batches | Used Haiku agents to file 40+ issues per repo | Hit GitHub secondary rate limits (403 BCE2) causing incomplete filing across multiple repos | Use Sonnet agents for issue-filing tasks with 40+ issues; add `sleep 3` between creations and `sleep 60` on 403 |
| Concurrent filer agents during org limit | Dispatched retry agents after secondary rate-limit errors | All agents returned "You've hit your org's monthly usage limit" — hard blocker | Test with a single `gh api` POST before dispatching batch; the limit resets daily and the test issue confirms availability |
| `--label "audit-finding"` without `--limit` | Verified child issue counts via `gh issue list --label audit-finding` without specifying `--limit` | GitHub defaults to 30 results, masking true count and causing false MISMATCH alarms | Always pass `--limit 200` when counting issues with `gh issue list` |
| findings.json as nested object | Audit agent returned JSON with top-level keys (`project`, `findings`, `summary`) instead of a flat array | Filer agents expected a flat JSON array, causing KeyError on iteration | Enforce flat array format in agent prompt: "findings.json MUST be a flat JSON array where each element is one finding object"; add a Python extraction fallback if needed |
| Write tool blocked in worktree agents | Audit agents couldn't write `report.md` to their worktree ("Subagents should return findings as text") | L0 received inline content but no file was written; subsequent filer agents had no input file | Instruct audit agents to print the full report as their final message; L0 orchestrator uses Write tool to save it to the scratch dir |
| Parallel filer agents on same repo | Multiple filer agent retries filed against the same repo concurrently | Created exact-title duplicate issues; required a cleanup pass to close ~119 duplicates | Run exactly one filer agent per repo; use idempotency check (label search) before any filing; never retry by spawning a parallel agent |
| Closing duplicate Epics (lower number first) | Assumed the lower-numbered Epic was the canonical one | Child issues referenced the higher-numbered Epic via "Part of #N"; closing lower Epic was correct but required verifying which number the child bodies referenced | Before closing a duplicate Epic, check which issue number the child bodies contain in "Part of #N" — that is the canonical one to keep |

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

### Session Scale Reference (ProjectTelemachy 2026-04-25)

| Metric | Value |
|--------|-------|
| Issues at start | 57 |
| Issues remaining at end | 6 (89% closure rate) |
| PRs created | 17 |
| PRs auto-merged | 17 |
| Issues closed with evidence, no PR | 6 |
| Wave A+B+0 dispatch | Simultaneous — 12 agents in one message |
| Wave D | 3 parallel Sonnet mega-agents (per-file) |
| Wave E | 1 solo Sonnet executor mega-agent (11 issues, 38 tests passing) |
| Waves F+G | 4 agents |
| Total wall clock | ~2.5 hours |
| Classifier swarm dispatched | No — deterministic from file-contention counts |

### Ecosystem-Wide Strict Audit Parameters

| Parameter | Value |
|-----------|-------|
| Repos per batch | 5 (cap from myrmidon-swarm skill) |
| Batches | 3 (for 15 repos) |
| Auditor tier | Sonnet (synthesis + evidence-based grading required) |
| Filer tier | Sonnet preferred over Haiku for 40+ issues (rate-limit resilience) |
| File coverage | Every .py .cpp .h .go .rs .sh .bash .ts source file; every test file; every config (.toml .yaml .yml .json .hcl Dockerfile* justfile) |
| Large corpus sampling | 1-in-10 (every 10th file alphabetically) for doc/data dirs > 100 files |
| findings.json schema | Flat JSON array; fields: section (int), severity (CRITICAL\|MAJOR\|MINOR\|NITPICK), title (<=70 chars), evidence (str), description (str), principle (str\|null) |
| Issue creation sleep | sleep 3 between issues; sleep 60 on 403 |
| Issue count verification | `gh issue list --label audit-finding --state open --limit 200 --jq length` |
| Duplicate detection | `group_by(.title) \| map(select(length > 1))` via jq on full issue list |
| Org limit test | Single `gh api repos/$REPO/issues --method POST` before dispatching batch |
| Scratch dir | ~/.agent-brain/strict-audit-YYYY-MM-DD/ (outside Odysseus working tree) |

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
| Pre-Phase 7 | All skill PRs merged in ProjectMnemosyne | Create tracking issue on target repo |

### L0 Orchestration Checklist

```
[ ] Pre-launch: autoMergeAllowed checked — if false, completion signal is "CI passing" not "MERGED"
[ ] Pre-launch: .pre-commit-config.yaml checked — if absent, pre-commit steps removed from all agent prompts
[ ] Pre-launch: lockfiles checked — if absent, npm install used instead of npm ci in CI job templates
[ ] After any wave that adds new CI jobs: verify new job passes on main before launching next wave
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
[ ] Phase 7: Tracking issue created on target repo (chore(triage): YYYY-MM-DD)
[ ] Phase 7: Tracking issue body includes metrics, closures, PRs, remaining issues, artifacts, skill PR links
[ ] Phase 7: Confirmed via gh issue list --search "chore(triage)"
[ ] Complete: worktree count verified (git worktree list)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 32 worktrees → 1, 6 PRs created and merged, 3 skills captured, 2026-04-05 | Full L0 session: exploration → plan → approval → 3 waves → 2 CI fixes → 3 parallel /learn agents |
| ProjectScylla | 64 issues classified, 12 PRs merged, tracking issue #1786 created, 2026-04-12 | Myrmidon swarm triage: classification + batch-fix waves + Phase 7 tracking issue on target repo |
| ProjectProteus | 43-issue classification + 20 EASY implementations, 2026-04-25 | TypeScript/Bash/YAML repo; auto-merge disabled; no pre-commit hooks; no lockfiles; npm install fix required after typecheck job added |
| ProjectTelemachy | 57 issues → 6 remaining (89% closure), 17 PRs, ~2.5h wall clock, 2026-04-25 | Python/pixi repo; deterministic classification from file-contention counts; per-file Sonnet mega-agents (Wave D+E); Waves 0+A+B dispatched simultaneously (12 agents in one message) |
| HomericIntelligence/Odysseus | Atlas Epic issue #152 scaffold, PR #173, 2026-04-27 | Direct worktree approach (not myrmidon-multi) for precision scaffold; branch forked from wrong base; cherry-pick fix onto clean main fork |
| HomericIntelligence/Odysseus | 2026-04-28 ecosystem-wide strict audit (15 repos, 680 findings, 15 Epics + child issues) | verified-local |

## References

- [myrmidon-waves-worktree-cleanup-rebase-pr-merge](myrmidon-waves-worktree-cleanup-rebase-pr-merge.md) — Tactical wave execution for worktree cleanup (Wave 1-3 details)
- [batch-pr-rebase-myrmidon-wave-execution](batch-pr-rebase-myrmidon-wave-execution.md) — Conflict strategies for rebase + PR workflow
- [multi-repo-pr-orchestration-swarm-pattern](multi-repo-pr-orchestration-swarm-pattern.md) — Multi-repo variant of the swarm pattern
- [haiku-wave-pr-remediation](haiku-wave-pr-remediation.md) — Haiku wave patterns for PR remediation
