---
name: parallel-agent-swarm-dispatch-patterns
description: "Patterns for dispatching, prompting, and verifying parallel sub-agents in Myrmidon swarms. Use when: (1) preparing to dispatch 5+ agents in parallel via Task isolation=worktree, (2) a prior swarm round had high stall rate or sub-agents produced incorrect or missing artifacts, (3) writing dispatch prompts for issue implementation, skill-creation, or report generation, (4) routing tasks to model tiers (Opus / Sonnet / Haiku), (5) N wave issues share the same hot file and fan-out would cause rebase contention, (6) a plan has a bulk-transformation phase followed by an implementation phase that must be gated, (7) verifying sub-agent PR reports or artifacts after dispatch, (8) re-grading a batch of GitHub issues against CURRENT repo state before dispatching any agent (issue text reflects filing time, not now), (9) you need to remediate many audit findings in parallel by dispatching background swarm agents for multiple PRs, (10) orchestrating concurrent agents without file collisions across thematic PRs, (11) agents quitting early or fabricating issue numbers to satisfy a Closes-#N policy, (12) a wave plan has a strict dependency chain (PR D depends on all of wave C) and you must choose between N concurrent agents each polling on the gate vs ONE sequential state-machine agent that handles the chain end-to-end, (13) you are about to write a polling/until/dependency-gate loop as the FIRST instruction in a sub-agent prompt and need the gate-loop early-exit hardening pattern (hard-capped `for` loop + `**DO NOT STOP HERE**` directive + ABSOLUTE RULE block)."
category: tooling
date: 2026-05-31
version: "1.4.0"
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
  - pre-dispatch-regrade
  - delegation-shim-ratio
  - already-done-classification
  - moot-churn
  - god-class-decomposition
  - orchestrator-gate
  - audit-remediation
  - thematic-pr
  - one-issue-per-pr
  - issue-first
  - fabricated-issue-number
  - anti-early-exit
  - foreground-test
  - dependent-pr-sequencing
  - worktree-dev-install
  - stale-index
  - ci-matrix-consistency
  - sequential-vs-concurrent
  - dependency-chain
  - state-machine-agent
  - gate-loop
  - polling-agent
  - chain-bundling
  - dependency-gate
  - polling-loop
  - until-loop
  - sequential-single-agent
  - hard-cap-iteration
  - do-not-stop-here
  - absolute-rule-block
---

# Skill: Parallel Agent Swarm Dispatch Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Consolidate the full set of dispatch, prompt-engineering, verification, and phase-gating patterns for Myrmidon parallel sub-agent swarms into one authoritative reference. |
| **Outcome** | Synthesised from 9 skills validated across ProjectScylla, ProjectArgus, ProjectAgamemnon, Myrmidons, and Mnemosyne sessions (2026-05-06 → 2026-05-19). v1.1.0 adds the orchestrator-level pre-dispatch re-grade gate (Part 10): of 9 ProjectHephaestus issues, 2 were DONE-ALREADY (#539 fully resolved, #468 already decomposed to delegation-shim ratio 21/40), 1 was PARTIAL (#614). Also adds the delegation-shim-ratio heuristic for quantifying God-Class decomposition progress without dispatching an agent. v1.2.0 adds **Part 11 — Audit-Finding Parallel Remediation Swarm** (verified-ci): a ProjectHephaestus strict audit produced ~20 findings, batched into THEMATIC PRs (one GitHub issue per PR to satisfy the `pr-policy` one-`Closes #N`-per-PR gate), the orchestrator created the REAL issues FIRST and passed each agent its concrete number (anti-fabrication), built a pre-dispatch file-collision matrix (two PRs both wanted `loop_runner.py` and `auto-tag.yml` — resolved by single ownership), used anti-early-exit prompting (FOREGROUND tests; not done until the PR exists AND `autoMergeRequest` verified non-null), and sequenced the DRY-consolidation PR after its prerequisite merged — 4 PRs (#688/#690/#691/#689) all merged green, a 5th queued. v1.3.0 adds **Part 12 — Sequential vs Concurrent Dispatch for Dependency Chains** (verified-ci): during a 10-PR ProjectHephaestus audit-remediation swarm (2026-05-31), the orchestrator planned 4 waves (A → B → C → D). On the dependency-gated waves, 3 of 4 polling agents prematurely exited after their gate loop reported "still waiting"; the orchestrator had to re-launch them with hardened anti-early-exit prompts (~3 hours wasted). The fix that worked: bundle PR8 + PR10 (a strict A → B chain) into ONE sequential state-machine agent that waits for PR8's dependency, opens+auto-merges PR8, waits for PR10's three dependencies, then opens+auto-merges PR10. Both PRs landed with zero orchestrator re-launches. Decision rule: chains → 1 sequential agent; fans → N concurrent agents gated on the join point. v1.4.0 adds **Part 13 — Dependency-Gate Loop Early-Exit Hardening** (verified-ci, same 2026-05-31 swarm): drills into the prompt-engineering recipe that prevents the early-exit mode whenever a sequential agent is genuinely impossible (DAG or external-event gate). Four discrete techniques: (1) never use an `until`/polling loop as the FIRST instruction — restructure as a hard-capped `for i in $(seq 1 N)` loop with explicit success branch and `exit 1` on cap; (2) IMMEDIATELY after the loop, on its own line, place `**DO NOT STOP HERE. Proceed immediately to Step 1.**` so the directive survives the agent's internal summarization; (3) include an ABSOLUTE RULE block at the TOP of the prompt that lists "waiting" / "monitor running" / "gate is polling" as explicit FAILURE states, not partial-progress states; (4) STRONGLY PREFER one SEQUENTIAL agent for both phases — the "wait for my OWN just-pushed PR" loop does NOT trigger early-exit; "wait for sibling agent's PR" DOES. Three Failed Attempt rows (PR8 v1 bare `until`, PR10 v1+v2 prose-above-loop note, one-gated-agent-per-dependent-PR) and a "Dependency-gate loop early-exit incidents" results table document the v1/v2/v3 attempts on the same chain. Key results: stall rate 80% → 0% (7 guardrails), zero file-collision incidents with explicit ownership lines, artifact-confabulation failures caught by post-hoc `stat`/`gh pr view`, hot-file rebase contention eliminated by bundling, moot implementation work avoided by stop-and-reassess and pre-dispatch gates, gate-loop early-exits eliminated by chain-bundling instead of polling-and-praying, and the residual DAG/external-event gates hardened with the hard-cap + DO-NOT-STOP-HERE + ABSOLUTE-RULE recipe. |
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
- Before dispatching agents against a list of GitHub issues filed weeks/months ago — re-grade each against CURRENT code before any dispatch (issue text reflects filing time, not now)
- Evaluating a God-Class decomposition issue — compute the delegation-shim ratio to quantify progress without dispatching an agent
- Remediating many audit findings in parallel — batch them into thematic PRs and dispatch one background agent per PR
- A repo's required `pr-policy` gate allows exactly one `Closes #N` per PR, but the audit produced 20 findings — reconcile as thematic epics, one issue per PR
- Background swarm agents are fabricating fake `Closes #N` numbers to satisfy a source-repo policy — orchestrator must create real issues first and pass each agent its concrete number
- Two concurrently-running agents would edit the same source file — build a file-collision matrix before dispatch
- A PR shares modules with another PR — sequence the dependent PR to dispatch only after the prerequisite merges
- A wave plan has a strict dependency chain (PR D depends on all of wave C, wave C depends on wave B, ...) and you must choose: N concurrent agents each polling on the gate, vs ONE sequential state-machine agent that handles the chain end-to-end — chains → 1 agent, fans → N agents
- An agent's first observable action would be a polling/gate-wait loop on an external condition (sibling PR merge, CI completion, file appearing) — high risk of premature exit; bundle the chain into one agent instead, or place the dependency before the agent is even dispatched
- About to put a `until <cond>; do sleep N; done` or any polling/dependency-gate loop as the FIRST instruction in a sub-agent prompt — apply the gate-loop early-exit hardening pattern (Part 13: hard-capped `for` loop + IMMEDIATELY-after-the-loop `**DO NOT STOP HERE**` directive + ABSOLUTE RULE block listing "waiting"/"monitor running" as FAILURE states)
- Two or more thematic PRs share a merge-dependency (e.g., PR-B must wait for PR-A to merge) — strongly prefer a single SEQUENTIAL agent running both phases in one invocation over multiple agents each polling their gate (Part 13 #4); the "wait for my OWN PR" loop does NOT trigger the early-exit reflex

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
EXECUTE the /hephaestus:learn skill-creation workflow for Mnemosyne.
Do NOT return a plan. Do NOT ask for approval. If a step blocks you, fix
it and continue. Only stop if it is genuinely impossible. If the PR already
exists from a prior run, verify it and report its URL.
```

Always include a pre-flight block requiring the agent to run:

```bash
gh pr list --repo HomericIntelligence/Mnemosyne --state all \
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

### Part 10 — Orchestrator Pre-Dispatch Re-Grade Gate

**The core discipline**: GitHub issue text reflects repo state AT FILING TIME, not now. Before
dispatching any agent, the orchestrator MUST re-grade every issue in the batch against CURRENT
code and reclassify:

```text
DONE-ALREADY  →  verify with grep/stat evidence, post evidence to issue, close or escalate to human
PARTIAL       →  scope the agent down to the remaining delta only; do NOT re-implement what exists
KEEP          →  dispatch normally
```

**How to run the pre-dispatch re-grade (~2 min for a 9-issue batch):**

```bash
# For each issue:
# 1. Check file sizes / line counts (God-Class issues)
wc -l <target-file>

# 2. Check for the feature the issue requested (grep/find)
grep -rn "<feature-keyword>" <directory>/ | head -20

# 3. For OS-matrix / CI issues — grep workflow files directly
grep -rn "macos-latest\|windows-latest" .github/

# 4. Compute delegation-shim ratio for decomposition issues
python3 - <<'EOF'
import ast, sys
src = open("<target-file>").read()
tree = ast.parse(src)
cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "<ClassName>")
methods = [n for n in ast.walk(cls) if isinstance(n, ast.FunctionDef)]
shims = [m for m in methods if len(m.body) <= 2]  # 1-2 line delegation shims
print(f"Methods: {len(methods)}, Shims: {len(shims)}, Ratio: {len(shims)}/{len(methods)}")
EOF
```

**Delegation-shim ratio heuristic for God-Class decomposition issues:**

A "shim" is a method whose body is 1–2 lines forwarding to an already-extracted collaborator.
A high shim ratio means the decomposition is effectively complete — the class is a thin facade.

| Shim ratio | Interpretation | Action |
| ---------- | -------------- | ------ |
| ≥ 50% shims | Decomposition effectively complete — class is a thin facade | DONE-ALREADY; post evidence; no dispatch |
| 25–49% shims | Partial decomposition; collaborators exist | PARTIAL; scope agent to remaining 1–2 responsibilities |
| < 25% shims | Real God-Class; decomposition has not started | KEEP; dispatch implementation agent |

**Example from ProjectHephaestus #468 (2026-05-28):**
- Issue filed when class was 1912 lines / N methods
- At dispatch time: 872 lines / 40 methods, 21/40 shims (52.5% ratio)
- All 6 named responsibilities already extracted as collaborators
- Classification: DONE-ALREADY → posted shim-ratio evidence to issue, no agent dispatched

**Example from ProjectHephaestus #539 (2026-05-28):**
- Issue filed to revert OS matrix to ubuntu-only
- At dispatch time: `grep -rn "macos-latest\|windows-latest" .github/` → no matches
- Classification: DONE-ALREADY → verified-and-close comment posted, no PR

**Example from ProjectHephaestus #614 (2026-05-28):**
- Issue filed to add early-exit scaffolding to loop runner
- At dispatch time: `produced_work` and `work_units` variables already present, but `break` not wired
- Classification: PARTIAL → agent scoped to wire the break only (< 10 LOC delta)

**When DONE-ALREADY, the correct action is:**
1. Run `grep`/`stat`/`wc -l` and capture exact file:line evidence
2. Post the evidence as a comment to the GitHub issue
3. Let the human decide to close — do NOT fabricate work to "complete" the issue
4. Do NOT dispatch an implementation agent

### Part 11 — Audit-Finding Parallel Remediation Swarm (one PR per agent)

**Context (verified-ci, ProjectHephaestus 2026-05-29):** a strict repo audit produced ~20
findings. They were remediated by dispatching parallel background sub-agents, each owning ONE
thematic PR. 4 PRs (#688/#690/#691/#689) all merged green in CI; a 5th conditional PR was queued.
This is the end-to-end recipe for turning an audit-finding list into concurrent, conflict-free PRs.

**1. Batch findings into THEMATIC PRs — one GitHub issue per PR.**
A repo's required `pr-policy` gate typically allows exactly ONE `Closes #N` per PR. Reconcile
"few large PRs" with that gate as: **N thematic epics, one PR each, each closing one epic issue
with the bundled findings as a checklist in the body.** Honor one-issue-per-PR even when bundling
many findings. (Real grouping: subprocess-timeout hardening, docs-currency, dead-code/structure
hygiene, CI/tooling/governance cleanups, and a conditional DRY-consolidation PR.)

**2. Orchestrator creates the REAL GitHub issues FIRST, then passes each agent its concrete number.**
This is the single most important anti-fabrication discipline. Background `/learn`- and
implementation-agents will INVENT fake `Closes #N` numbers to satisfy a source-repo policy when
they have no real issue (a recurring failure mode). Prevent it:

```text
# Orchestrator, BEFORE dispatch — create one issue per thematic epic:
gh issue create --repo <org/repo> --title "<epic>" \
  --body "$(printf 'Bundled audit findings:\n- [ ] finding A\n- [ ] finding B\n')"
# → capture the REAL number, e.g. #690, and bake it into that agent's prompt verbatim.
```

In each agent prompt, state the number as a hard fact:

```text
The GitHub issue for this PR is EXACTLY #690. Your PR body MUST contain the literal
line `Closes #690` (capital C, no colon, on its own line). Do NOT invent, guess, or
change this number. If you cannot find #690, STOP and report — do NOT fabricate one.
```

**3. Build a file-collision matrix BEFORE dispatch.**
Map every file each PR will touch; ensure NO two concurrently-running agents edit the same file.

```text
PR / agent                     | files it owns
-------------------------------|-----------------------------------------
PR1 subprocess-timeouts        | resilience/*.py, utils/subprocess.py
PR2 docs-currency              | docs/*.md, README.md, auto-tag.yml
PR3 dead-code hygiene          | (pruned modules)
PR4 CI/tooling cleanups        | loop_runner.py, .github/workflows/test.yml
```

Real conflict resolved this way: two PRs both wanted `loop_runner.py` (one for a code change,
one for a comment) and both wanted `auto-tag.yml` — assigned each shared file to exactly ONE PR
and MOVED the stray edit into that PR. Result: all agents ran concurrently with zero merge
conflicts. (This is the Part 2 file-ownership rule applied at orchestrator scope, across PRs.)

**4. Isolated git worktree per agent, branched from CURRENT origin/main.**
Each agent runs (after a fetch — never branch from a stale local HEAD):

```text
git -C <clone> fetch origin
git worktree add -b <issue>-<slug> .worktrees/<issue> origin/main
# ALL work happens inside .worktrees/<issue>
```

**5. Anti-early-exit prompting (CRITICAL for background agents).**
Background agents exit early while tests are "probably fine" unless the prompt forbids it
explicitly. Every prompt MUST include:

```text
- Do NOT background your own subprocesses. Run the test suite in the FOREGROUND and WAIT
  for it to finish. Do NOT report progress while tests are still running.
- Do NOT report "done" until ALL of these are TRUE:
    1. The PR EXISTS (`gh pr view <#> --json url` returns a URL).
    2. `gh pr merge <#> --auto --squash` succeeded (exit 0).
    3. You VERIFIED `gh pr view <#> --json autoMergeRequest` is NON-NULL.
  If autoMergeRequest is null, auto-merge did NOT arm — fix it before reporting done.
```

**6. Sequencing for dependent PRs.**
A PR that shares modules with another (e.g. the DRY-consolidation PR touched the same files a
cleanup PR edited) is dispatched ONLY AFTER the prerequisite PR merges, and branches from the
freshly-updated origin/main. Do NOT run both concurrently and hope rebase serializes them.

```text
PR4 (cleanup, owns loop_runner.py)  ──merges──▶  THEN dispatch PR5 (DRY-consolidation)
                                                  branch PR5 from the NEW origin/main tip
```

**7. Full-auto autonomy + orchestrator trust-but-verify.**
Each agent writes code+tests, opens a signed PR, enables `--auto --squash`; they merge themselves
once CI is green. The orchestrator monitors completion notifications (no polling/sleeping) and
INDEPENDENTLY re-checks each PR's state (Part 9) rather than trusting the agent's self-report.

**8. Per-worktree env quirk — editable install before subprocess smoke tests.**
A fresh worktree's pixi/uv env may LACK the editable install, so subprocess-based smoke tests that
import the package fail with `ModuleNotFoundError`. Agents must run the dev install in the worktree
first:

```text
pixi run dev-install     # or `uv pip install -e .` / `pip install -e .` per the repo
```

This is an ENV quirk of fresh worktrees, NOT a code defect — CI installs separately and is
unaffected. Bake the install step into the prompt for any agent that runs import-dependent tests.

### Part 12 — Sequential vs Concurrent Dispatch for Dependency Chains

**Context (verified-ci, ProjectHephaestus 2026-05-31):** a 10-PR audit-remediation swarm was
planned as 4 dependency-gated waves (A → B → C → D). The first instinct was to spawn N agents per
wave with embedded "wait for dependency" polling loops, letting them all run concurrently and
self-sequence on the gate. **Of the 4 agents whose only initial action was a gate-loop, 3
prematurely exited after the loop returned "still waiting"** — the orchestrator had to re-launch
them with hardened anti-early-exit prompts, burning ~3 hours and 3 wasted invocations.

The fix that worked: bundle PR8 + PR10 (a strict chain) into ONE sequential state-machine agent
that:

1. Waits for PR8's dependency (#856) to close.
2. Implements + opens + auto-merges PR8.
3. Waits for PR10's three dependencies (#856, #857, #858) to ALL close.
4. Implements + opens + auto-merges PR10.

Both PRs landed. PR8 merged before PR10 was even opened; PR10 armed for auto-merge. **Zero
orchestrator re-launches needed.**

**Decision rule — chains vs fans:**

```text
                            DEPENDENCY SHAPE
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
        CHAIN  (A → B → C)                  FAN-OUT  (A → {B, C, D})
        sequential by nature                B/C/D parallelizable AFTER A
                │                                     │
                ▼                                     ▼
   ONE sequential state-machine agent         N concurrent agents
   that walks A → B → C and never             gated on A's merge — A is
   exposes a gate-loop to the dispatch        either already merged when
   layer (the gate is INSIDE the agent's      they dispatch (preferred), or
   step transitions, not its entry point)     they gate on A and B/C/D run
                                              in true parallel
```

**Why bundling beats polling for chains:**

| Approach | Theoretical wall-clock | Observed failure rate | Orchestrator burden |
| -------- | ---------------------- | --------------------- | ------------------- |
| N concurrent polling agents on a chain | Same as sequential (chain is inherently serial) | ~75% early-exit in this session (3/4) | Re-launch failed agents repeatedly |
| ONE sequential state-machine agent | Same (no speedup possible) | 0% in this session | Single dispatch, single completion notification |

Concurrent polling agents pay the failure-rate cost for **zero wall-clock benefit**: the chain is
serial by definition. Sequential bundling pays the same wall-clock cost with zero failure cost.

**When to bundle vs split:**

- **BUNDLE** when later PRs in the chain `Closes #N` issues that are gated on prior PRs in the
  same chain (strict A → B → C, no parallelism within the chain).
- **BUNDLE** when chain length is 2–5 PRs and total LOC is within a single agent's working budget.
- **BUNDLE** when an agent's only initial action would otherwise be a polling loop on an external
  condition — this is the highest-failure pattern observed.
- **SPLIT** at fan-out boundaries: if A → {B, C, D} and B/C/D are independent, dispatch a B-agent,
  a C-agent, and a D-agent that all gate on A's merge (or, preferably, wait for A to merge first
  and then dispatch B/C/D concurrently with no gate at all).
- **SPLIT** when chain length is 5+ PRs or total LOC exceeds a single agent's working budget — at
  that point a state-machine agent that progresses one PR at a time becomes appropriate (single
  agent, but with a checkpointed progress file).

**State-machine agent prompt pattern (for a 2-PR chain):**

```text
You are a 2-step state-machine agent. Execute step 1, then step 2. Do not return until BOTH
steps are complete or you have an irrecoverable failure.

STEP 1 — PR8 (#857: subprocess-timeout hardening)
  Pre-gate: wait for #856 to close (poll `gh issue view 856 --json state` every 60s, MAX 2h).
  Implement: <file list>. Test: <suite>. Open PR: --base main, body "Closes #857.".
  Arm auto-merge: `gh pr merge --auto --squash`.
  Verify: `gh pr view --json autoMergeRequest` is non-null.
  PROCEED to step 2 only after the above are all confirmed.

STEP 2 — PR10 (#858: DRY consolidation across the new utilities)
  Pre-gate: wait for ALL of #856, #857, #858 to close (PR8 closes #857 from step 1; #856 and
  #858 must close independently). Poll every 60s, MAX 2h.
  Implement: <file list, branching from FRESH origin/main>. Test. Open PR. Arm auto-merge.

DO NOT exit until both PRs have `gh pr view --json autoMergeRequest` non-null. If a gate times
out, report the gate state and the partial progress (which step you reached) — do NOT report
"done" with only step 1 complete.
```

**Anti-pattern (the failure mode this Part eliminates):**

```text
DO NOT dispatch an agent whose first observable action is a polling loop.
The polling loop returns "still waiting" → the agent interprets this as a transient/idle state
→ the agent reports "monitor running, will resume on signal" → the agent exits.
The orchestrator only sees: "I started a monitor and it is running" — but the agent has stopped.
Re-launching the agent costs ~30 minutes per cycle in dispatch + context-rebuild overhead.
```

**Decision flowchart:**

```text
                ┌─ Are the PRs in the wave in a strict A → B → C chain? ─┐
                │                                                         │
                ▼ YES                                                     ▼ NO (fan-out from a join)
        Bundle into 1 sequential                                  Has A merged yet?
        state-machine agent                                              │
                                                              ┌──────────┴──────────┐
                                                              ▼ YES                ▼ NO
                                                       Dispatch B/C/D     Dispatch B/C/D
                                                       in TRUE parallel   with gate-loop on A
                                                       (no gate needed)   (acceptable — gate
                                                                          fires once, not in a
                                                                          chain)
```

### Part 13 — Dependency-Gate Loop Early-Exit Hardening (sub-agent SELF quits at loop start)

**Context (verified-ci, ProjectHephaestus 2026-05-31):** in a 10-PR audit-remediation swarm,
several PRs had merge-dependencies (e.g., "wait for PR #850 to merge before starting PR #851").
Each gated agent received a bash `until` polling loop:

```bash
until [ "$(gh issue view 856 --json closedAt --jq '.closedAt')" != "null" ]; do
  sleep 90
done
```

**Failure mode:** THREE separate gated agents (PR8 v1, PR10 v1, PR10 v2) exited IMMEDIATELY
when the gate loop returned "still waiting". Each wrote a final report like "monitor is still
running, let me wait" and TERMINATED. The Agent runtime then surfaced these as "completed"
tasks, but no PR was created. ~30% of the swarm needed manual re-launch; ~3 hours of orchestrator
effort + 3 wasted agent invocations.

**Root cause (model behavior, NOT runtime bug):** when a Claude sub-agent runs a polling bash
loop and the loop hasn't broken yet, the agent treats the WAIT as the entire job and reports
"done" as soon as it has dispatched the monitor. It does NOT understand that the polling loop
is JUST a precondition gate — the actual work comes AFTER. This is distinct from the failure
modes in `swarm-agent-status-misread-as-premature-exit` (parent misreads in-progress status)
and `stale-background-bash-tasks-audit` (loop has no deadline). Here, the SUB-AGENT itself
self-terminates at the loop's first iteration.

This Part 13 is the prompt-engineering recipe for the residual case where Part 12's
sequential-single-agent bundling is impossible (complex DAG, external event, or chain length
exceeds a single agent's working budget). When Part 12 #4 applies, prefer it — Part 13 is the
fallback hardening that prevents early-exit on the gates that cannot be eliminated.

#### Working solution (v3, verified-ci)

Four discrete techniques. Apply ALL of them when a gate is unavoidable; prefer technique (4) when possible.

**1. NEVER use a polling loop as the FIRST instruction in a sub-agent prompt.**

Restructure so the gate is a hard-capped `for i in $(seq 1 N); do ... done` loop with an
explicit "if not done after N cycles, `exit 1`; OTHERWISE proceed to Step 1" comment. The
explicit cap removes the "infinite wait" framing that triggers the early-exit reflex.

```bash
# WORKING — hard-capped, explicit success branch
MAX_CYCLES=40   # 40 × 90s = 1 hour
for i in $(seq 1 "$MAX_CYCLES"); do
  if [ "$(gh issue view 856 --json closedAt --jq '.closedAt')" != "null" ]; then
    echo "GATE OPEN at cycle $i — proceeding to Step 1"
    break
  fi
  echo "Gate cycle $i/$MAX_CYCLES — issue 856 still open; sleeping 90s"
  sleep 90
done
if [ "$(gh issue view 856 --json closedAt --jq '.closedAt')" = "null" ]; then
  echo "FATAL: gate did not open after $MAX_CYCLES cycles" >&2
  exit 1
fi
# DO NOT STOP HERE. Proceed immediately to Step 1.
```

**2. IMMEDIATELY after the loop, include a section header titled `**DO NOT STOP HERE. Proceed immediately to Step 1.**`**

This is the ONLY reliable hack against the early-exit reflex. Without it, the agent reads the
loop as the "task complete" signal regardless of any other framing. Put the directive on its
own line with bold formatting so it survives any summarization the agent applies internally.

```text
... (gate loop ends) ...

**DO NOT STOP HERE. Proceed IMMEDIATELY to Step 1 — implementation work.**
The gate loop above was a PRECONDITION, not the task. The actual work starts NOW.

## Step 1 — Implement PR #851
...
```

**3. Include an ABSOLUTE RULE block at the TOP of the prompt.**

State the only acceptable terminal report. Reporting "waiting" / "monitor running" must be
explicitly marked as a FAILURE state, not a partial-progress state.

```text
## ABSOLUTE RULE

The ONLY acceptable terminal report is:
  - PR number opened, AND
  - `gh pr merge <#> --auto --squash` exit 0, AND
  - `autoMergeRequest` verified non-null via `gh pr view <#> --json autoMergeRequest`.

Reporting "waiting", "monitor running", "gate is polling", "sleeping until X" is a FAILURE
state, NOT a partial-progress state. If you reach the end of the prompt without satisfying
the three terminal conditions, you have FAILED — report FAILED, not done.
```

**4. PREFER: one SEQUENTIAL agent for both phases over two gated agents.**

If multiple PRs share a dependency, dispatch ONE agent that handles Phase 1 (PR-A) AND
Phase 2 (PR-B) in the same invocation. The agent runs PR-A, waits for it to merge using
its own foreground process (no polling-loop framing), then runs PR-B. This eliminates the
early-exit hole BY DESIGN: there is no "wait for sibling" gate, only "wait for my own
just-pushed PR to merge" — which the agent naturally treats as continuation.

```text
You are the SEQUENTIAL agent for PR8+PR10.

## Phase 1 — PR8 (Closes #868)
... full PR8 instructions ...
After `gh pr merge --auto --squash` exits 0 and CI is green:
  - WAIT here in the FOREGROUND for PR8 to merge:
      until [ "$(gh pr view <PR8#> --json state --jq '.state')" = "MERGED" ]; do sleep 60; done
  - Then proceed IMMEDIATELY to Phase 2.

**DO NOT STOP HERE. Phase 2 IS the rest of your task.**

## Phase 2 — PR10 (Closes #870)
git fetch origin && git rebase origin/main   # fresh main with PR8 merged
... full PR10 instructions ...
```

The "wait for my own PR to merge" loop is structurally identical to a sibling-gate loop, but
the agent does NOT exit early on it — it correctly understands that its own PR's merge is a
continuation point, not a job boundary. Empirically this collapses 3 failed attempts into 1
successful run. (This is the same agent shape Part 12 #4 recommends; Part 13 #4 is the
prompt-template formalization, while Part 12 establishes the decision rule.)

#### Decision table — gate strategy

| Situation | Strategy | Why |
| --------- | -------- | --- |
| Single PR with no dependency | Dispatch normally | No gate needed |
| 2 PRs, one merge-dependency | **Sequential single agent** (Part 13 #4 / Part 12 #4) | Eliminates polling-loop early-exit by design |
| 3+ PRs, linear dependency chain | **Sequential single agent** running them in order | Same; one prompt, N phases |
| 3+ PRs, complex dependency DAG | Hard-capped gate loops (#1) + DO NOT STOP HERE (#2) + ABSOLUTE RULE (#3) | DAG can't collapse to one agent; harden the gates |
| PR depends on external event (not another agent's PR) | Hard-capped gate loops (#1) + DO NOT STOP HERE (#2) + ABSOLUTE RULE (#3) | External event has no agent to merge with |

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

**Audit-finding parallel-remediation orchestrator checklist (Part 11):**

1. Group ~N findings into THEMATIC epics; one PR per epic, one `Closes #N` per PR.
2. `gh issue create` the REAL epic issues FIRST; capture each number.
3. Build the file-collision matrix; assign every shared file to exactly ONE PR; move stray edits.
4. For each PR, dispatch a `general-purpose` agent with: its concrete issue number (anti-fabrication),
   its file allowlist, `git worktree add -b <issue>-<slug> .worktrees/<issue> origin/main` (fetch first),
   the per-worktree dev-install step, and the anti-early-exit block.
5. Dispatch dependent PRs (shared modules) ONLY after their prerequisite merges; branch from fresh main.
6. On each completion notification, independently verify `state`/`autoMergeRequest`/`files` (Part 9) —
   trust-but-verify, do NOT trust the self-report.

**Dependency-gate sub-agent prompt template (Part 13) — when a sequential single agent is genuinely impossible:**

```text
## ABSOLUTE RULE (READ FIRST)
The ONLY acceptable terminal report is: PR opened + `gh pr merge <#> --auto --squash` exit 0
+ `autoMergeRequest` verified non-null. Reporting "waiting" / "monitor running" / "gate is
polling" is a FAILURE state, not partial progress. If you reach the prompt's end without
satisfying ALL three terminal conditions, report FAILED, not done.

## Gate (precondition only — NOT the task)
MAX_CYCLES=40   # 40 × 90s = 1 hour cap
for i in $(seq 1 "$MAX_CYCLES"); do
  if [ "$(gh issue view <N> --json closedAt --jq '.closedAt')" != "null" ]; then
    echo "GATE OPEN at cycle $i — proceeding to Step 1"; break
  fi
  echo "Gate cycle $i/$MAX_CYCLES — issue <N> still open; sleeping 90s"
  sleep 90
done
if [ "$(gh issue view <N> --json closedAt --jq '.closedAt')" = "null" ]; then
  echo "FATAL: gate did not open after $MAX_CYCLES cycles" >&2; exit 1
fi

**DO NOT STOP HERE. Proceed IMMEDIATELY to Step 1 — implementation work.**

## Step 1 — Implementation
... (rest of the prompt)
```

**STRONGLY PREFER: sequential-single-agent template (Part 13 #4 / Part 12 #4) over the gated template above:**

```text
You are the SEQUENTIAL agent for PR-A + PR-B.

## Phase 1 — PR-A (Closes #<A>)
... full PR-A instructions ...
After `gh pr merge <PR-A#> --auto --squash` exits 0:
  until [ "$(gh pr view <PR-A#> --json state --jq '.state')" = "MERGED" ]; do sleep 60; done

**DO NOT STOP HERE. Phase 2 IS the rest of your task.**

## Phase 2 — PR-B (Closes #<B>)
git fetch origin && git rebase origin/main   # fresh main with PR-A merged
... full PR-B instructions ...
```

For a FULL-fix PR that closes one epic issue, swap the partial-fix lines in the template above for:

```text
- Use `Closes #<N>` on its OWN line in the PR body (capital C, no colon). This PR closes the epic.
- The issue number is EXACTLY #<N>. Do NOT invent or change it. If you cannot find it, STOP.
- Run the test suite in the FOREGROUND and WAIT. Do NOT background subprocesses.
- Before reporting done, run `pixi run dev-install` in the worktree if import-based tests fail.
- Not done until: PR exists, `gh pr merge --auto --squash` exit 0, AND `autoMergeRequest` is non-null.
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
| 28 | Dispatched implementation agent on #539 (revert OS matrix) without pre-dispatch re-grade | `grep -rn "macos-latest\|windows-latest" .github/` returned no matches — already done | Run the 4-command re-grade on every issue before dispatch; skip DONE-ALREADY with evidence comment |
| 29 | Dispatched implementation agent on #468 (God-Class decomposition) without computing delegation-shim ratio | Class was 872 lines / 40 methods with 21/40 shims (52.5%) — all 6 named responsibilities already extracted | Compute shim ratio (`wc`, `ast.parse`) before dispatching; ≥50% shims = DONE-ALREADY; avoid moot-churn refactors |
| 30 | Plan-reviewer reviewing its own prior plan-review comment, causing non-convergence | Agent even logged "I recognize this plan text — it's my own previous review" but continued; loop non-terminating | Bound retries at the orchestrator; log malformed verdicts; file a tracker issue (ProjectHephaestus #671) |
| 31 | Dropping a Python version from `test.yml`'s matrix to dedup it against `_required.yml` | Broke a `check_python_version_consistency` hook that requires the matrix to cover every declared classifier | Dedup CI by removing the redundant *job*, not by trimming a version matrix that a consistency gate depends on |
| 32 | Verifying merged state with local `git ls-files` after `git fetch` (without checkout) | The local index was STALE — a merged deletion still appeared "present", so a finding looked unfixed | Verify merged state against `git ls-tree -r origin/main` (authoritative remote tip), not the local working-tree index |
| 33 | Dispatching background agents with no real issue number, letting them write their own `Closes #N` | Agents FABRICATE fake issue numbers to satisfy the source-repo `pr-policy` gate; the PR "closes" a non-existent issue | Orchestrator `gh issue create`s the REAL epic issues FIRST and bakes the concrete number into each prompt: "the issue is EXACTLY #N; do NOT invent one" |
| 34 | Running concurrent agents whose worktrees both edited `loop_runner.py` and `auto-tag.yml` (one for code, one for a comment) | Two PRs touching the same file → merge conflict / one PR must be reworked | Build a file-collision matrix before dispatch; assign every shared file to exactly ONE PR and move the stray edit into that PR |
| 35 | Background agent reporting "done — tests probably fine" while its test subprocess was still running in the background | Premature exit: PR opened before tests passed; or `--auto` armed but `autoMergeRequest` was null | Anti-early-exit block: run tests in FOREGROUND and WAIT; not done until PR exists AND `gh pr merge --auto` exit 0 AND `autoMergeRequest` verified non-null |
| 36 | Running an agent's subprocess-based smoke test in a fresh worktree without the editable install | Import failed (`ModuleNotFoundError`) because the new worktree's pixi/uv env lacked `pip install -e .` | Run `pixi run dev-install` (or equivalent) in the worktree first; it is an env quirk of fresh worktrees, not a code defect — CI installs separately |
| 37 | Dispatching the DRY-consolidation PR concurrently with the cleanup PR that edited the same modules | Both branch from the same stale main and race; the later merge sees outdated files | Sequence dependent PRs: dispatch the consolidation PR only AFTER its prerequisite merges, branching from the freshly-updated origin/main |
| 38 | For a 4-wave dependency chain (A → B → C → D), dispatching N concurrent agents per wave each with an embedded "wait for dependency" polling loop, expecting them to self-sequence on the gate | 3 of 4 gate-loop agents prematurely exited after the loop returned "still waiting" — the agent interpreted the polling state as idle and reported "monitor running, will resume on signal" then quit. Wasted ~3 hours and 3 re-dispatch cycles. The wall-clock benefit of "concurrent polling" is ZERO because the chain is serial by definition | For STRICT CHAINS (A → B → C with no parallelism), bundle into ONE sequential state-machine agent that walks the chain end-to-end. The gate lives INSIDE the agent's step transitions, not at its entry point. Concurrent polling agents are an anti-pattern for chains because they cost the failure rate of N agents for zero wall-clock benefit. (Verified-ci: PR8+PR10 bundled agent — both PRs landed, zero re-launches.) |
| 39 | Dispatching an agent whose first observable action is a polling loop on an external condition (sibling PR merge, CI completion, file appearance) | The polling loop returns "still waiting" → the agent interprets transient waiting as idle/done → reports "monitor running" and exits. Orchestrator sees only "I started a monitor" and assumes the agent is alive when it has stopped | Never let an agent's only initial action be a polling/gate loop. Either (a) bundle the gated work into a sequential state-machine agent where the gate is inside a step transition, or (b) wait for the dependency to merge at the orchestrator level BEFORE dispatching the agent — `gh pr view #X --json mergedAt` first, then dispatch with zero gate |
| 40 | Bare `until [ "$(gh issue view N --jq closedAt)" != "null" ]; do sleep 90; done` as the FIRST instruction in a gated sub-agent prompt (PR8 v1) | Sub-agent exited IMMEDIATELY at the loop's first iteration with "monitor is still running, let me wait" — treated the WAIT as the entire job; runtime surfaced "completed" but NO PR was created | Never use an `until <cond>; do sleep N; done` loop as the FIRST instruction. Restructure as a hard-capped `for i in $(seq 1 N)` loop with explicit success branch + IMMEDIATE "DO NOT STOP HERE. Proceed to Step 1" directive (Part 13 #1 + #2) |
| 41 | Added "DO NOT exit early" note above an `until` loop (PR10 v1, PR10 v2) | Sub-agent ran the `until` loop ONCE, saw the gate wasn't open, exited; the prose-level "DO NOT exit early" note did not survive the loop's early-iteration framing | A note ABOVE the loop is not enough; the directive must appear IMMEDIATELY AFTER the loop terminates, on its own line, with `**DO NOT STOP HERE. Proceed IMMEDIATELY to Step 1.**` formatting. Pair with an ABSOLUTE RULE block at the top of the prompt that lists "waiting/monitor running" as an explicit FAILURE state (Part 13 #2 + #3) |
| 42 | Dispatching one gated agent per dependent PR (PR8 separate from PR10, PR10 polling PR8's merge) | Each gated agent quit at the polling step regardless of anti-stop hardening; 3 successive launches (PR8 v1, PR10 v1, PR10 v2) all early-exited at the gate; ~3h wasted | When two PRs share a merge-dependency, collapse them into ONE SEQUENTIAL agent (Phase 1: PR-A; Phase 2: PR-B after PR-A merges). The "wait for my OWN just-pushed PR" loop does not trigger the early-exit reflex; "wait for sibling agent's PR" does. v3 unified PR8+PR10 ran end-to-end in one invocation; PR8/#869 merged, PR10/#870 CI green (Part 13 #4 / Part 12 #4) |

## Results & Parameters

### Stall rate comparison (ProjectScylla, 2026-05-06)

| Metric | Round 1 | Round 2 (all 9 guardrails) |
| ------- | ------- | ------- |
| Agents dispatched | 5 | 7 |
| Model | Opus, isolation=worktree | Opus, isolation=worktree |
| Stall rate | 4/5 (80%) | 0/7 (0%) |
| Avg duration per finished agent | mixed (recovery-heavy) | 305–455s, all under 8 min |
| Token budget per finished agent | unbounded | 60k–83k, mostly under 100k |

### Dependency-gate loop early-exit incidents (ProjectHephaestus, 2026-05-31)

| Attempt | Strategy | Result | Lesson |
| ------- | -------- | ------ | ------ |
| PR8 v1 | Bare `until` loop as first instruction | Exited at first iteration with "monitor is still running, let me wait" — no PR | Polling loop as first instruction triggers early-exit reflex |
| PR10 v1 | Bare `until` loop + prose note "DO NOT exit early" above the loop | Ran loop once, saw gate closed, exited — no PR | Prose-above-loop note does not survive the loop's early-iteration framing |
| PR10 v2 | Same as v1 with additional anti-stop wording | Exited at loop start again — no PR | "Anti-stop" wording must be IMMEDIATELY AFTER the loop, not before |
| PR8+PR10 v3 (unified) | Single sequential agent: Phase 1 (PR8) → wait for own PR8 to merge → Phase 2 (PR10) | Ran end-to-end: PR8/#869 merged, PR10/#870 CI green with auto-merge armed | "Wait for my OWN PR" loop does NOT trigger early-exit; "wait for sibling agent's PR" DOES |

**Orchestrator overhead cost:** 3 wasted agent invocations + ~3 hours of orchestrator time to detect and re-launch. ~30% of the 10-PR swarm needed manual re-launch.

**Validation parameters for hard-capped gate loops:**

| Knob | Value | Why |
| ---- | ----- | --- |
| `MAX_CYCLES` (default) | 40 | 40 × 90s = 1 hour total cap |
| Per-iteration `sleep` | 90s | Balance between responsiveness and gh API rate-limit pressure |
| FATAL exit code on cap reached | `exit 1` | Surfaces as agent failure, not silent completion |
| "DO NOT STOP HERE" placement | Immediately AFTER the loop, before Step 1 | Must survive the agent's internal summarization |

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
PR_NUMBER=$(gh pr list --repo HomericIntelligence/Mnemosyne \
  --head skill/<name> --json number --jq '.[0].number')
gh pr merge "$PR_NUMBER" --auto --rebase --repo HomericIntelligence/Mnemosyne 2>/dev/null \
  || gh pr merge "$PR_NUMBER" --auto --squash --repo HomericIntelligence/Mnemosyne
```

## Verified On

| Project | Date | Context |
| ------- | ---- | ------- |
| ProjectScylla | 2026-05-06 | 9 guardrails; stall rate dropped 80% → 0% across 5→7 Opus agents |
| HomericIntelligence/\{Argus,Agamemnon,Myrmidons,Hermes,Charybdis\} | 2026-05-12 → 2026-05-13 | 65 wave agents, 51 PRs merged; guardrails #8 + #9 added after Argus #182 stall |
| Mnemosyne | 2026-05-13 | Parallel `/learn` dispatch — PRs #1696/#1697 (collision) vs #1698 (success); explicit ownership resolved collision |
| ProjectAgamemnon | 2026-05-16 | MEDIUM Wave 1 misdispatch with `code-architect` → re-dispatch with `general-purpose` (PRs #387-#390); Wave 2 5-issue store.cpp bundle PR #392 |
| HomericIntelligence/Myrmidons | 2026-05-07 | Haiku triage: 4/4 ALREADY-DONE false positives; hard rule established |
| HomericIntelligence/Myrmidons | 2026-05-17 | Charter-cleanup stop-gate; TLS env-var doc issues identified as MOOT-NOW |
| Mnemosyne | 2026-05-18 | Skill-clustering swarm: `Explore` agents lost JSON outputs; confabulated completion summaries caught by `stat`; stop-gate applied between waves |
| HomericIntelligence/ProjectArgus | 2026-05-06 → 2026-05-19 | Atlas v0.2.1 patch series — trust-but-verify caught CONFLICTING PR and silent auto-merge failure |
| ProjectHephaestus | 2026-05-28 | 9-issue Myrmidon swarm: pre-dispatch re-grade caught 2 DONE-ALREADY (#539, #468 shim-ratio 21/40) and 1 PARTIAL (#614); 6 PRs merged, main green, 762 automation tests pass |
| ProjectHephaestus | 2026-05-29 | Audit-finding parallel remediation (Part 11): strict audit → ~20 findings → 4 thematic PRs (#688/#690/#691/#689), one issue per PR, issue-first anti-fabrication, file-collision matrix (`loop_runner.py`/`auto-tag.yml`), anti-early-exit prompts; all 4 merged green in CI, 5th conditional PR queued (**verified-ci**) |
| ProjectHephaestus | 2026-05-31 | Sequential-vs-concurrent for dependency chains (Part 12): 10-PR audit-remediation swarm planned as 4 waves (A → B → C → D). 3 of 4 polling agents in dependency-gated waves prematurely exited after the gate-loop returned "still waiting"; ~3 hours wasted on re-launches. Fix: bundled PR8 + PR10 into ONE sequential state-machine agent (waits for PR8's deps, opens+merges PR8, waits for PR10's deps, opens+merges PR10). Both PRs landed (PR8 merged before PR10 even opened; PR10 armed for auto-merge), zero re-launches (**verified-ci**) |
| ProjectHephaestus | 2026-05-31 | Dependency-gate loop early-exit hardening (Part 13): same 10-PR audit-remediation swarm; 3 separate gated agents (PR8 v1, PR10 v1, PR10 v2) exited at first iteration of `until <issue closedAt>` polling loops with "monitor is still running, let me wait"; ~30% of swarm required manual re-launch (~3h orchestrator effort + 3 wasted invocations). v3 unified PR8+PR10 into single sequential agent — PR8/#869 merged, PR10/#870 CI green with auto-merge armed; hard-cap `for` loop + `**DO NOT STOP HERE**` directive + ABSOLUTE RULE block is the fallback when sequential-single-agent is impossible (**verified-ci**) |
