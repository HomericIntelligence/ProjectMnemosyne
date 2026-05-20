---
name: parallel-agent-swarm-dispatch-patterns
description: "Patterns for dispatching, prompting, and verifying parallel sub-agents in Myrmidon swarms. Use when: (1) preparing to dispatch 5+ agents in parallel via Task isolation=worktree, (2) a prior swarm round had high stall rate or sub-agents produced incorrect or missing artifacts, (3) writing dispatch prompts for issue implementation, skill-creation, or report generation, (4) routing tasks to model tiers (Opus / Sonnet / Haiku), (5) N wave issues share the same hot file and fan-out would cause rebase contention, (6) a plan has a bulk-transformation phase followed by an implementation phase that must be gated, (7) verifying sub-agent PR reports or artifacts after dispatch."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: parallel-agent-swarm-dispatch-patterns.history
tags:
  - myrmidon
  - swarm
  - prompt-design
  - scope-guardrails
  - stall-prevention
  - precommit-stall
  - sub-agent
  - parallel-dispatch
  - file-ownership
  - collision-avoidance
  - trust-but-verify
  - verification
  - subagent-type
  - tool-availability
  - hallucinated-success
  - artifact-verification
  - shared-brief
  - fan-out
  - model-tier
  - haiku
  - sonnet
  - bundle-pr
  - hot-file
  - stop-gate
  - re-grade
  - survivor-queue
  - phase-boundary
  - agent-dispatch
---

# Skill: Parallel Agent Swarm Dispatch Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Consolidate the full set of dispatch, prompt-engineering, verification, and phase-gating patterns for Myrmidon parallel sub-agent swarms into one authoritative reference. |
| **Outcome** | Synthesised from 9 skills validated across ProjectScylla, ProjectArgus, ProjectAgamemnon, Myrmidons, and ProjectMnemosyne sessions (2026-05-06 → 2026-05-19). Key results: stall rate 80% → 0% (7 guardrails), zero file-collision incidents with explicit ownership lines, artifact-confabulation failures caught by post-hoc `stat`/`gh pr view`, hot-file rebase contention eliminated by bundling, and moot implementation work avoided by stop-and-reassess gates. |
| **Verification** | verified-local and verified-ci across multiple projects |

## When to Use

- Preparing to dispatch 5+ Opus/Sonnet agents in parallel against GitHub issues via `Task isolation=worktree`
- A prior swarm round had high stall rate (stream-idle watchdog firing, agents giving up mid-plan)
- Writing a dispatch prompt for issue implementation, skill creation, report generation, or repo audit
- Routing tasks to model tiers: Haiku vs. Sonnet vs. Opus
- A sub-agent reports a PR is "merged" or "auto-armed" and you must verify before chaining dependent work
- A sub-agent goes silent or times out without returning a final message
- Two or more parallel agents target the same output file (skill file, report, config)
- A wave plan shows 3+ issues sharing the same hot file (e.g., `src/store.cpp`, `CMakeLists.txt`)
- A plan has a bulk-transformation phase (mass-close, mass-delete) followed by an implementation phase

## Verified Workflow

### Part 1 — Prompt Guardrails to Eliminate Agent Stalls

Nine guardrails listed in approximate order of impact. Apply ALL when dispatching against hard issues.

#### 1. `Refs #N` instead of `Closes #N` for partial fixes

`Closes #N` puts psychological pressure on the agent to ship the entire issue. On multi-file
refactors this triggers analysis paralysis. `Refs #N` lets the agent ship a slice and move on.
Combine with explicit "this is a partial fix; the rest is tracked in #M and #L" wording.

#### 2. Scope down to one file or one piece

Pick one slice now and file the rest. The "one slice" framing avoids wide-refactor stall mode.

Examples: "JSON logging foundation only; tracing is out of scope." "scaffold only; do NOT touch
existing call sites."

#### 3. Hard LOC budgets per agent

State the cap explicitly: `Scope ≤ ~400 LOC of net change`. Round-2 budgets that worked: 250–600
LOC depending on the slice. Agents that exceeded the budget on round 1 stalled while planning
maximalist solutions.

#### 4. Gated verification with explicit STOP path

Build a Step 1 verification gate into the prompt with an explicit STOP condition.

Example: "Step 1 must be: verify which entry points actually exist. If FEWER than 5 of 9 entry
points exist, STOP and comment on the issue without opening a PR."

#### 5. Explicit scope-out boundaries for foundation/scaffold PRs

Write the *don'ts* into the prompt: `Do NOT modify production code in <area>`, `Do NOT touch
existing call sites`. Without these, the agent expands scope mid-task and stalls.

#### 6. Real-evidence requirement for documentation tasks

For any "produce a doc / table / report" issue, require:
- Real `path/to/file.py:LINE` citations for every claim
- An explicit `TBD` marker for every numeric cell that lacks a citation

This kills the stall mode where the agent invents data, doubts itself, and freezes mid-table.

#### 7. PR protocol block, copy-paste ready, with the repo's actual merge method

Embed a literal PR protocol block so the agent does not rediscover repo policy:

```text
git push -u origin <N>-<slug>
gh pr create --title "..." --body "...Refs #<N>."
gh pr merge --auto --squash    # repo only allows squash, not rebase
```

#### 8. PRECOMMIT_STALL abort condition

pre-commit hook env installs can hang indefinitely on the first run in an isolated worktree
(cold pixi/python env). Every dispatch prompt for any agent that will run `git commit` MUST
include:

```text
PRECOMMIT_STALL: If `git commit` or `pre-commit run` hangs >60s on hook env
install ("Installing environment for ..." with no further output), ABORT immediately.
Do NOT wait. Skip local pre-commit and let CI validate:
  SKIP=audit-doc-policy-violations,gitleaks,yamllint git commit -m "..."
Or use `git commit --no-verify`. Report `PRECOMMIT_STALL` in your final summary.
```

#### 9. Don't run pre-commit locally for low-risk wave changes

For doc-only / config-only / single-line wave changes, explicitly tell the agent NOT to run
pre-commit locally. CI runs all hooks in a clean environment.

```text
NOTE: Do NOT run `pre-commit run --all-files` locally for this change. If you
need a check, run targeted-files only:
  SKIP=audit-doc-policy-violations,gitleaks,yamllint pre-commit run --files <files>
```

### Part 2 — Explicit File Ownership in Parallel Agent Prompts

Lead every parallel sub-agent prompt with an explicit file-ownership line BEFORE any background:

```text
**The file you own is: `<exact-relative-path>`.** Do NOT touch any other file.
```

For amendments to existing files:

```text
**The file you own is: `skills/existing-skill-name.md`.** AMEND it from v<old> to v<new>.
Do NOT create a new skill file under a different name.
```

**Detailed steps:**

1. Enumerate every file touched collectively. One file per agent.
2. Put the file-ownership line at the TOP (first paragraph, before background).
3. If two agents could reasonably read the instructions as pointing to the same file, fix them.
4. After completion, verify each agent produced its intended PR by checking the PR's file list.
   If two PRs touch the same file, close the loser DIRTY and reclaim the intent in a follow-up.

**Do NOT bother when:** only one sub-agent (no collision), sub-agents work on entirely unrelated
repos/trees, or sub-agents are pure-research (read-only, no file writes).

### Part 3 — Subagent Type Selection: Write-Capable vs. Read-Only

Use `subagent_type: "general-purpose"` for ANY agent that commits, pushes, opens PRs, edits files,
or writes any output file (JSON, markdown, log). Read-only types (`feature-dev:code-architect`,
`feature-dev:code-explorer`, `feature-dev:code-reviewer`, `Explore`, `Plan`) have NO `Write` tool
and will either silently no-op OR hallucinate "Wrote /tmp/output.json" in their summary while
leaving disk untouched.

```text
For implementation / artifact-producing work:
  subagent_type: "general-purpose"   ✓ has Bash, Write, Edit, full toolset

For research / design only:
  subagent_type: "feature-dev:code-architect"    ← read-only
  subagent_type: "feature-dev:code-explorer"     ← read-only
  subagent_type: "feature-dev:code-reviewer"     ← read-only
  subagent_type: "Explore"                       ← read-only
  subagent_type: "Plan"                          ← read-only
```

**Verification is mandatory:** orchestrator must `ls -la` every promised artifact path after
dispatch and treat missing files as failure regardless of what the agent said.

### Part 4 — Model Tier Routing: Haiku for Mechanical Only

```text
ANALYSIS / TRIAGE / CLASSIFICATION  →  model: sonnet  (preferred)
                                       model: opus    (acceptable)
                                       model: haiku   NEVER

MECHANICAL FIX with explicit rules   →  model: haiku   OK
                                       (rebases with explicit conflict rules,
                                        lint fixes ≤50 LOC, bulk renames)

QUOTA EXHAUSTED on Sonnet/Opus       →  Ask the user. Do NOT silently
                                       substitute Haiku for analysis tasks.
```

Haiku conflates *discussion of a thing* with *evidence the thing exists*. In a live session,
4/4 ALREADY-DONE flags from a Haiku triage agent were false positives (Myrmidons 2026-05-07).

**Decision axis:** judgment required vs. mechanical execution — NOT "batch" vs. "interactive".
If the prompt contains *classify*, *decide*, *estimate*, *triage*, *audit*, *review*, *verify
whether*, or *is this already done*, the model is Sonnet or Opus, period.

### Part 5 — Sub-Agent Execute Directive (Not Plan)

When dispatching `/hephaestus:learn` or similar skill-creation agents, the prompt must open with
an EXECUTE directive:

```text
EXECUTE the /hephaestus:learn skill-creation workflow for ProjectMnemosyne.
Do NOT return a plan. Do NOT ask for approval. If a step blocks you, fix
it and continue. Only stop if it is genuinely impossible. If the PR already
exists from a prior run, verify it and report its URL.
```

Always include a pre-flight block requiring the agent to run:

```bash
gh pr list --repo HomericIntelligence/ProjectMnemosyne --state all \
  --head skill/<branch-name> --json number,state,url
```

If the PR exists in any state, the agent reports the URL and skips to cleanup.

### Part 6 — Shared Brief File for Large Fan-Outs

For N-repo fan-outs where the same procedure applies with minor per-repo deltas:

1. Write a single shared brief to `~/.tmp/<topic>-brief.md` (objective, classification framework,
   copy-paste code snippets, per-repo workflow, what NOT to do, output format).
2. Dispatch agents with pointer-prompts (`Read ~/.tmp/<topic>-brief.md for the full task spec.`
   and per-repo assignment).

This keeps each prompt at 200–500 tokens vs. 2000+ for inline-quoted instructions. Parent-context
savings of ~36K tokens observed in a 14-agent fan-out (2026-05-10).

**Do NOT use when:** N ≤ 3 (inline is fine), work per repo varies substantially, or orchestrator
review/integration phases are genuinely needed.

### Part 7 — Hot-File Bundling

When a wave plan shows 3+ issues all targeting the same file, dispatch ONE agent producing N
atomic commits — do NOT dispatch N parallel agents and trust them to serialize via rebase.

```text
ONE general-purpose agent
→ N atomic commits (one per issue, in order)
→ ONE branch (unique name per worktree-parallel-agent-execution pattern)
→ ONE PR with body: "Closes #A. Closes #B. ... Closes #N."
```

PR body must use period-separated `Closes #N.` entries — Markdown tables and comma-lists do NOT
trigger GitHub auto-close.

**Do NOT bundle when:** issues touch genuinely disjoint files (parallel is fine), bundle exceeds
10 issues, or an individual issue is high-risk and needs its own PR for isolated rollback.

### Part 8 — Stop-and-Reassess Gate Between Phases

Any plan whose shape is `prep → bulk-X → cleanup → implement-survivors` has a latent re-grade
gate between cleanup and implementation:

```text
Phase A (prep)         ─┐
Phase B (bulk-close)    ├─ bulk-transformation phases
Phase C (cleanup PRs)  ─┘
        │
        ▼
   ===== STOP-AND-REASSESS GATE =====
   For each survivor task:
     1. Read the original task description
     2. Check whether the subject still exists post-transformation
     3. Re-grade: KEEP / MOOT-NOW / NEEDS-REWRITE
     4. Remove MOOT-NOW tasks from the queue
   ===== / GATE =====
        │
        ▼
Phase D (implement survivors) — only the still-relevant tasks
```

For multi-wave merge operations, run this gate between every wave pair. Use the 25%-threshold
heuristic: `pct_lost < 25%` trim and proceed; `pct_lost >= 25%` flag as MOOT-NOW candidate.

### Part 9 — Trust-But-Verify: PR State and Artifacts

After EVERY sub-agent report, verify via GitHub API before chaining dependent work:

```bash
# STEP 0: Before re-dispatching a silent/stuck sub-agent — check if it already succeeded:
gh pr list --repo <org/repo> --head <branch-name> --state all \
    --json number,state,mergedAt --limit 5
# MERGED → agent succeeded silently — do NOT re-dispatch
# OPEN   → agent is mid-flight — do NOT re-dispatch
# (empty) → no PR exists — safe to re-dispatch

# After every "PR done" report:
gh pr view <#> --repo <org/repo> --json \
    state,mergedAt,baseRefName,mergeable,mergeStateStatus,additions,deletions,files \
  --jq '{state, mergedAt, base: .baseRefName, mergeable,
         mergeState: .mergeStateStatus, additions, deletions,
         files: [.files[].path]}'

# After "rebased and pushed" — verify content matches PR intent:
git diff origin/main..origin/"$BRANCH" --stat

# Validate structured artifacts (JSON/YAML/TOML) with the actual parser:
python3 -c "import json; json.load(open('$f'))"
```

**Three failure shapes to watch for:**
1. **Confabulated completion** — agent claims work it never did (amplified by low token budget).
2. **Hallucinated tool restriction** — agent invents "TEXT ONLY per system constraints" framing.
3. **Tool-capability blindness** — agent claims a Write its profile does not allow.

### Quick Reference

Paste this template into a Task call with `subagent_type="general-purpose"` and `isolation=worktree`:

```text
You are an L4 implementation agent in the Myrmidon swarm. Running in an isolated
git worktree on branch `<N>-<slug>` based on `main` (HEAD `<sha>`).
Implement <full|partial> GitHub issue #<N> in <repo> and open a single PR.

**The file you own is: `<exact-path>`.** Do NOT touch any other file.

## Your task — <one-sentence scope>
<short context>

## Hard constraints (READ FIRST)
- Branch name: `<N>-<slug>`. Do not create any other branch.
- Scope ≤ ~<LOC> LOC of net change.
- Do NOT modify <area-out-of-scope>.
- subagent_type: "general-purpose"  (required if this agent writes files or commits)
- Skip local pre-commit; let CI validate. If you do run it, target-files only:
    `SKIP=audit-doc-policy-violations,gitleaks,yamllint pre-commit run --files <files>`
- PRECOMMIT_STALL: if `git commit` hangs >60s, ABORT and use `git commit --no-verify`.
- Use `Refs #<N>` (NOT `Closes #<N>`) since this is a partial fix.

## PR protocol

    git push -u origin <N>-<slug>
    gh pr create --title "..." --body "...Refs #<N>."
    gh pr merge --auto --squash    # repo only allows squash, not rebase

## Output (under 150 words)
- <metric 1>
- PR URL
The user does NOT see your tool calls — only this final summary.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Generic "implement #N" with full-issue scope on round 1 | Agent gets lost in analysis when the issue spans 4 files \| cross-cutting work | Scope to one slice; use `Refs` not `Closes` |
| 2 | No LOC budget | Agent attempts a maximalist solution then stalls when it cannot fit it together | Hard LOC ceiling forces decomposition early |
| 3 | `Closes #N` on a partial-fix scope | Agent feels obligated to do the whole issue → analysis paralysis | `Refs #N` + explicit "this is a partial fix" wording in PR body |
| 4 | Telling agent "auto-merge with `--rebase`" without checking repo policy | Repo only allows squash; `gh pr merge --auto --rebase` errors and agent investigates instead of trying squash | Tell the agent the merge method up front |
| 5 | Letting agent invent test cases / numbers | Agent stalls when it cannot find supporting evidence | Require real `file:line` citations for docs; explicit test-name list |
| 6 | Letting agents run `pre-commit run --all-files` on cold worktrees | First-run pre-commit env install hangs 5+ min with no progress output | Add PRECOMMIT_STALL abort condition; trust CI for low-risk changes |
| 7 | Detailed-but-unprefixed parallel prompts | Two of three parallel `/learn` sub-agents amended the SAME existing skill instead of one creating a new file. PRs #1696 and #1697 collided; #1697 closed DIRTY. | Lead every parallel prompt with the file-ownership line before any task description |
| 8 | Trust sub-agent context inference for file routing | Sub-agents read top-down; the "create new skill" intent was buried hundreds of words in | Move ownership statements to the FIRST paragraph |
| 9 | Sequential dispatch instead of fixing prompts | Proposed as "safe" collision avoidance | Wastes wall-clock time; parallel dispatch is fine with explicit ownership |
| 10 | Dispatched `feature-dev:code-architect` agents for C++ issue implementation | All 4 produced blueprints then failed with "I do not have shell execution" — no PRs created | The `feature-dev:*` family is read-only by design; implementation needs `general-purpose` |
| 11 | Dispatched 12 `Explore` Sonnet agents to write per-shard JSON reports | 4 of 12 returned "Wrote /tmp/skill-reports/X.json" but `ls` showed no file; `Explore` has no `Write` tool | Always `ls -la` promised artifact paths; sub-agent summaries lie on read-only toolsets |
| 12 | Trusted "auto-squash armed" report verbatim | PR was actually `CONFLICTING`; auto-merge cannot fire on CONFLICTING state | `gh pr view --json mergeable` is state; sub-agent dialogue is intent — always check |
| 13 | Trusted `gh pr merge --auto --rebase` exit-0 | Repo had rebase-merge disabled; command silently no-op'd. `autoMergeRequest` was `null`. | Check `autoMergeRequest` in API; null means no auto-merge regardless of gh exit code |
| 14 | Trusted "rebased and pushed" from a Haiku rebase agent | Agent's commit contained wrong domain content (sibling PR's changes); GitHub showed CLEAN state | Every post-rebase needs `git diff origin/main..HEAD --stat` vs. PR title's domain |
| 15 | Substituted Haiku for Sonnet on ALREADY-DONE classification when Sonnet quota exhausted | 4/4 ALREADY-DONE flags from Haiku triage agent were false positives — all issues still open | Never substitute Haiku for analysis; ask user: wait, run manually, or authorize with 100% re-verify caveat |
| 16 | Treated Haiku "keyword in codebase" as evidence the feature exists | Haiku saw discussion of gitleaks in `.gitleaks.toml`, concluded test existed. `ls tests/integration/test_gitleaks_*.bats` returned nothing. | ALREADY-DONE detection requires checking EXISTENCE of the artifact, not keyword presence |
| 17 | Assumed `feature-dev:code-reviewer` would commit review-driven fixes | Read-only toolset (`Glob, Grep, LS, Read, NotebookRead, WebFetch`) — same failure class | Any task ending with a write action needs `general-purpose` |
| 18 | Dispatching N parallel agents on N issues all targeting the same hot file | Same-file rebase race — 5 parallel agents on `src/store.cpp` would produce 5-way rebase contention | Bundle the K issues into ONE agent producing K atomic commits on one branch |
| 19 | Relying on "serialize within wave via rebase" instruction in planner output | N agents each must detect that the HEAD moved; N! failure modes; silent conflicts likely | ONE agent, K commits, zero rebase coordination — pre-empts the race by design |
| 20 | Running Phase D (implement survivors) directly after Phase C (cleanup PRs) | Survivor issues graded against OLD repo state; subjects deleted by cleanup became MOOT-NOW | Always insert a stop-and-reassess gate; re-grade survivor queue after every structural transformation |
| 21 | Trusting original KEEP-EASY grading across phases | Classification valid only against the repo state it was performed on | Treat survivor-queue grading as state-dependent; re-grade after every bulk transformation |
| 22 | Bare `/learn` prompt without EXECUTE directive | 3/5 agents wrote a plan file and stopped at "Ready to execute on approval" | Add explicit "EXECUTE NOW. Do NOT return a plan. Do NOT ask for approval." at top of prompt |
| 23 | Skipped pre-flight PR-list check before re-dispatching stuck agent | Agent reported "Task already complete from a prior run" — original dispatch DID create the PR | Always run `gh pr list --head skill/<name>` before re-dispatching; plan-style summary ≠ nothing shipped |
| 24 | Trusted agent summary "all shard reports complete" without checking disk | On-disk `stat /tmp/skill-reports/cicd-shard-01.json` showed file unchanged; agent confabulated completion from sibling-agent notifications in its context | Sibling-task notifications leak into self-reports especially on low token budgets (24k–31k) |
| 25 | Inlined full brief in each of 14 parallel agent prompts | ~3000 tokens × 14 agents spent on instruction repetition | Write brief to `~/.tmp/<topic>-brief.md`, point each agent at it with a 5-line pointer-prompt |
| 26 | Invoked `/hephaestus:myrmidon-swarm` for work already planned | Orchestrator re-ran Phase-1 (consult Mnemosyne, decompose, plan) — redundant when parent already did it | When planning is complete, dispatch Agents directly with the `Agent` tool |
| 27 | Trusted valid JSON existence without parsing | Trailing comma after final `unclustered[]` entry silently broke `json.load`; gate pipeline crashed with `JSONDecodeError` | Always parse structured artifacts with `python3 -c "import json; json.load(open(f))"` — `ls`/`stat` cannot catch trailing commas |

## Results & Parameters

### Stall rate comparison (ProjectScylla, 2026-05-06)

| Metric | Round 1 | Round 2 (all 9 guardrails) |
| ------- | ------- | ------- |
| Agents dispatched | 5 | 7 |
| Model | Opus, isolation=worktree | Opus, isolation=worktree |
| Stall rate | 4/5 (80%) | 0/7 (0%) |
| Avg duration per finished agent | mixed (recovery-heavy) | 305–455s, all under 8 min |
| Token budget per finished agent | unbounded | 60k–83k, mostly under 100k |

### Subagent type quick reference

| Work type | `subagent_type` | Has Write? |
| --------- | --------------- | ---------- |
| Implementation, commit/push/PR, file writes | `general-purpose` | Yes |
| Architecture blueprints (read-only) | `feature-dev:code-architect` | No |
| Code exploration (read-only) | `feature-dev:code-explorer` | No |
| Code review (read-only) | `feature-dev:code-reviewer` | No |
| Open-ended exploration (read-only) | `Explore` | No |
| Planning (read-only) | `Plan` | No |

### Model tier routing

| Task | Model |
| ---- | ----- |
| Classification / triage / ALREADY-DONE detection | Sonnet (preferred) or Opus |
| Repo audit / code review / scope estimation | Sonnet or Opus |
| Root-cause analysis / planning / architecture | Sonnet or Opus |
| Mechanical lint fix ≤50 LOC under documented rules | Haiku OK |
| Rebase fix-up with explicit conflict-resolution policy | Haiku OK |
| Bulk file rename driven by sed-like pattern | Haiku OK |
| Single-issue implementation with explicit file allowlist | Haiku OK |

### Hot-file bundle dispatch pattern

```python
# ONE agent for K issues sharing the same file
Agent(
    description="MEDIUM Wave 2 — store.cpp 5 issues",
    subagent_type="general-purpose",
    model="sonnet",
    isolation="worktree",
    prompt="""Implement these 5 issues in ONE PR with one signed commit each.
Issue order: #155 → #161 → #209 → #222 → #340 (all touch src/store.cpp).
For each: implement, test, git commit -S -m '<scope>: <summary> (#N)', then
gh pr create with 'Closes #155. Closes #161. Closes #209. Closes #222. Closes #340.'
Enable auto-merge --squash."""
)
```

### Multi-wave re-grade threshold

- `pct_lost < 25%` — trim the manifest and proceed; cluster is still viable.
- `pct_lost >= 25%` — flag as MOOT-NOW candidate; human review before dispatch.

### Trust-but-verify field reference

| Field | Meaning |
| ----- | ------- |
| `state` | `OPEN` / `MERGED` / `CLOSED` |
| `mergeable` | `MERGEABLE` / `CONFLICTING` / `UNKNOWN` |
| `mergeStateStatus` | `CLEAN` / `UNSTABLE` / `BEHIND` / `BLOCKED` / `DIRTY` |
| `autoMergeRequest` | object = armed; `null` = NOT armed (regardless of `gh pr merge --auto` exit code) |
| `files` | scope check |
| `statusCheckRollup` | live CI status |

### Execute-directive template for skill-creation agents

```bash
PR_NUMBER=$(gh pr list --repo HomericIntelligence/ProjectMnemosyne \
  --head skill/<name> --json number --jq '.[0].number')
gh pr merge "$PR_NUMBER" --auto --rebase --repo HomericIntelligence/ProjectMnemosyne 2>/dev/null \
  || gh pr merge "$PR_NUMBER" --auto --squash --repo HomericIntelligence/ProjectMnemosyne
```

## Verified On

| Project | Date | Context |
| ------- | ---- | ------- |
| ProjectScylla | 2026-05-06 | 9 guardrails; stall rate dropped 80% → 0% across 5→7 Opus agents |
| HomericIntelligence/\{Argus,Agamemnon,Myrmidons,Hermes,Charybdis\} | 2026-05-12 → 2026-05-13 | 65 wave agents, 51 PRs merged; guardrails #8 + #9 added after Argus #182 stall |
| ProjectMnemosyne | 2026-05-13 | Parallel `/learn` dispatch — PRs #1696/#1697 (collision) vs #1698 (success); explicit ownership resolved collision |
| ProjectAgamemnon | 2026-05-16 | MEDIUM Wave 1 misdispatch with `code-architect` → re-dispatch with `general-purpose` (PRs #387-#390); Wave 2 5-issue store.cpp bundle PR #392 |
| HomericIntelligence/Myrmidons | 2026-05-07 | Haiku triage: 4/4 ALREADY-DONE false positives; hard rule established |
| HomericIntelligence/Myrmidons | 2026-05-17 | Charter-cleanup stop-gate; TLS env-var doc issues identified as MOOT-NOW |
| ProjectMnemosyne | 2026-05-18 | Skill-clustering swarm: `Explore` agents lost JSON outputs; confabulated completion summaries caught by `stat`; stop-gate applied between waves |
| HomericIntelligence/ProjectArgus | 2026-05-06 → 2026-05-19 | Atlas v0.2.1 patch series — trust-but-verify caught CONFLICTING PR and silent auto-merge failure |
