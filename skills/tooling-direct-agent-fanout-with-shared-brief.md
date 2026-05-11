---
name: tooling-direct-agent-fanout-with-shared-brief
description: "Dispatch N parallel Agent calls for repetitive multi-repo work by writing a single shared classification/instruction brief to ~/.tmp/<topic>.md, then giving each agent a short pointer-prompt with only the per-repo details (path, occurrence count, special handling). Use when: (1) you've already done the planning yourself and want to skip the orchestrator skill's Phase-1 re-plan, (2) the same procedure applies across many repos with minor per-repo variations, (3) you want each agent's context window to stay small so they don't blow through it reading the brief inline, (4) you want post-dispatch feedback from agents to refine the shared brief without re-issuing prompts, (5) deciding between invoking the formal `/hephaestus:myrmidon-swarm` skill vs. direct Agent fan-out."
category: tooling
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - agent-orchestration
  - parallel-dispatch
  - shared-brief
  - multi-repo
  - myrmidon-alternative
  - context-management
  - fan-out
---

# Direct Agent Fan-Out with Shared Brief File

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-10 |
| **Objective** | Dispatch a parallel swarm across 14 submodule repos without re-running the orchestrator's Phase-1 planning (already done by the calling session). |
| **Outcome** | 14 agents launched in a single sweep, 14 PRs opened with auto-merge, ~198 refactors landed; brief file (~10 KB) loaded once by each agent instead of inline-quoted in every prompt. |
| **Verification** | verified-ci |

## When to Use

- You've already completed Mnemosyne consultation and planning yourself (in the parent session) and don't want the orchestrator skill to re-do it
- The same procedure applies to N repos with only minor per-repo deltas (path, occurrence count, special-handling caveats)
- The shared instructions are large (>2 KB) and you don't want to inline them in every Agent prompt
- You want agents to be able to feed observations back to the parent session for follow-up work (e.g., one agent discovers a regex gap that should propagate to a follow-up PR)

## When NOT to Use

- The orchestrator skill's review/integration phases are genuinely needed (cross-agent synthesis, hierarchical Opus/Sonnet/Haiku tiering, etc.)
- The work per repo varies substantially — write per-repo prompts directly
- N is small (≤3) — inline the instructions per prompt

## Verified Workflow

### Step 1: Write the shared brief

In the parent session, write a single markdown file to `~/.tmp/<topic>-brief.md` containing:

- The objective (what the user wants accomplished)
- The classification framework (Bucket A–E or equivalent taxonomy)
- Copy-paste-ready code snippets (YAML hook stanzas, CI job blocks, refactor templates)
- Per-repo workflow (find occurrences, refactor, port lint guard, verify, commit, PR, auto-merge)
- What NOT to do
- Output format the agent should report back

The example file used 2026-05-10: `/home/mvillmow/.tmp/silent-failures-brief.md` (~10 KB, structured with H1/H2 sections).

### Step 2: Dispatch agents with pointer-prompts

Each Agent prompt is just:

- A pointer to the shared brief (`Read /home/mvillmow/.tmp/<topic>-brief.md for the full task spec.`)
- The repo assignment (path + name)
- The expected occurrence count (calibrates the agent's effort)
- Per-repo deltas (special handling, related skills to read, etc.)
- The output format reminder

Prompts stay short (200–500 tokens vs. 2000+ for inline) so spawning 14 in parallel doesn't blow the parent's context.

### Step 3: Agent feedback loop

Agents may surface gaps in the brief (regex missing a control-flow boundary, brief's occurrence count off, brief assumed file existed but it didn't). When you see a pattern repeated across multiple agents, refactor the shared brief and/or write a follow-up PR for the parent repo — don't reissue prompts.

### Quick Reference

```bash
# 1. Write the shared brief (parent session)
mkdir -p ~/.tmp
cat > ~/.tmp/<topic>-brief.md <<'EOF'
# <Topic> Brief

## Objective
...
## Classification framework
...
## Workflow
...
EOF

# 2. Dispatch N agents in parallel (single message, multiple Agent tool calls)
# Each prompt format:
#   "Read ~/.tmp/<topic>-brief.md for the full task spec.
#    Your assigned repo: <name> at <path>.
#    Occurrence count: <N>.
#    Special handling: <...>
#    Output: PR URL + table of refactors + verification status."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | Invoking `/hephaestus:myrmidon-swarm` to fan out across 14 repos | The orchestrator runs Phase-1 (consult Mnemosyne, decompose, plan) — but the parent session had already done all of that. Redundant work and wasted Opus tokens. | When planning is already complete, dispatch Agents directly with the `Agent` tool. Reserve the orchestrator skill for genuinely under-specified work. |
| 2 | Inlining the full classification framework + lint-guard YAML + workflow in each Agent prompt | First two agent prompts were ~3000 tokens each. Dispatching 14 in parallel would have spent significant context on instruction repetition. | Write the brief to `~/.tmp/<topic>-brief.md` (one disk write), then point each agent at it (5-line prompts). Agents read the file once. |
| 3 | Per-repo occurrence counts pre-survey assumed the working tree matched main | One submodule (ProjectHermes) had received 162 commits since the pre-survey — the brief said "0 occurrences, no pre-commit config" but the agent on arrival found 1 occurrence and existing config. | Tell agents to work from current state, not the brief's snapshot. The brief should be hints, not assertions. |
| 4 | Brief used "narrow" regex for the lint hook | One agent (Argus) flagged that the narrow regex missed control-flow boundaries `)`, `;`, `&&` — present in its own repo but not in the meta-repo | Agent feedback is gold — refactor the SHARED BRIEF (and the source-of-truth PR) when multiple agents report the same gap. Don't reissue prompts. |
| 5 | Assumed all 14 agents would finish in a similar wall-clock time | Largest repo (ProjectOdyssey research, 45 refactors) took ~20 minutes; smallest (Mnemosyne, 1 refactor) took ~9 minutes | The longest task sets the critical path. Worth flagging in the brief which repos have known-large surface so the user can plan accordingly. |
| 6 | Each agent independently fetched `gh pr diff 280 --repo HomericIntelligence/Odysseus` as the reference | Worked, but ate identical bytes 14 times. Could have cached the diff to a path in the brief. | For frequently-referenced external artifacts, fetch once in the parent session and store path in the brief (e.g., `gh pr diff 280 --repo ... > /tmp/odysseus-280.diff` then reference `/tmp/odysseus-280.diff` in each prompt). |

## Results & Parameters

```bash
# Example brief structure (full template)
# /home/mvillmow/.tmp/<topic>-brief.md
# ===================================
# # <Topic> Removal Brief (shared across submodule agents)
# ## Reference PR
#   [link + fetch command]
# ## Classification framework (Bucket A–E)
#   [the taxonomy with refactor patterns for each bucket]
# ## Lint guard to port
#   [YAML stanzas — pre-commit hook + CI job]
# ## Per-repo workflow
#   1. cd $REPO; git status (abort if dirty)
#   2. git checkout -b chore/<topic>
#   3. Find occurrences (exact grep command)
#   4. Refactor per bucket
#   5. Port lint guard
#   6. Verify locally (pre-commit, bash -n, shellcheck, repo CI)
#   7. Commit + push + PR + auto-merge --squash
# ## What NOT to do
# ## Output format
```

Token economics (observed 2026-05-10):

- Inline-prompt version (estimate): ~3000 input tokens × 14 agents ≈ 42K input tokens for instructions alone
- Shared-brief version (actual): ~400 input tokens × 14 agents + brief loaded by each agent once ≈ 5.6K + (10K × 14 = 140K read from disk, but disk reads don't count against parent context)
- **Parent-context savings: ~36K tokens** that would have been instruction-replication

## Verified On

| Project | Context | Details |
|---|---|---|
| HomericIntelligence ecosystem | 2026-05-10 silent-failures sweep | 14 parallel agents → 16 PRs → ~198 refactors landed; brief at `/home/mvillmow/.tmp/silent-failures-brief.md`; see Odysseus#280, #281 + 14 submodule PRs |
