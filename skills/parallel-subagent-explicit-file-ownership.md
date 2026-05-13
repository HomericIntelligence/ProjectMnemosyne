---
name: parallel-subagent-explicit-file-ownership
description: "Lead every parallel sub-agent prompt with an explicit '**The file you own is: <path>**' line BEFORE any background context. Use when: (1) dispatching >=2 sub-agents in a single message that produce related-but-distinct output files (e.g., one amends skill X, another creates new skill Y in the same family), (2) sub-agents collectively touch a shared file tree where misidentification would cause silent duplicate work, (3) you observe two parallel sub-agents producing PRs that amend the same file when one was supposed to create a new file, (4) /learn or similar workflows are dispatched in parallel across related skill topics. Skip when: a single sub-agent (no collision risk), or sub-agents working on entirely unrelated repos/trees."
category: tooling
date: 2026-05-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - sub-agent
  - parallel-dispatch
  - prompt-engineering
  - file-ownership
  - collision-avoidance
  - orchestration
  - learn-workflow
---

# Skill: Explicit File Ownership in Parallel Sub-Agent Prompts

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-13 |
| **Objective** | Prevent parallel sub-agents from independently converging on the same target file by stating each agent's owned file as the FIRST line of its prompt, before any task description. |
| **Outcome** | One of three parallel sub-agents whose prompt led with explicit filename ownership produced the intended unique PR (#1698). The two whose prompts buried the filename in a long task description collided on the same existing skill file, producing duplicate PRs #1696 and #1697 — #1697 had to be closed DIRTY. |
| **Verification** | verified-ci — direct evidence from ProjectMnemosyne PR set #1696/#1697/#1698 (2026-05-13). The single difference between the collision and the success was the leading file-ownership line. |

## When to Use

- Launching >=2 parallel sub-agents in a single message
- Sub-agents operate on related/overlapping topics (same skill family, same module, same file tree)
- Any pattern where misidentification of the target file would cause silent duplicate work
- `/learn` workflows dispatched in parallel across related skill topics
- Mixed create/amend batches — one agent creates a new file, another amends a sibling file

**Do NOT bother when:**

- Only one sub-agent is being dispatched (no collision possible)
- Sub-agents work on entirely unrelated repos or file trees
- Sub-agents are pure-research (read-only, no file writes)

## Verified Workflow

### Quick Reference

The fix is one line at the top of every parallel sub-agent's prompt:

```text
**The file you own is: `<exact-relative-path>`.** Do NOT touch any other file.
```

For amendments to existing files, be just as explicit:

```text
**The file you own is: `skills/existing-skill-name.md`.** AMEND it from v<old> to v<new>.
Do NOT create a new skill file under a different name. Do NOT touch any other skill file.
```

Place this line in the first paragraph of the prompt — sub-agent attention is finite, and early
instructions dominate the rest.

### Detailed Steps

1. Before launching parallel sub-agents, enumerate every file they will collectively touch. One file per agent.
2. For each agent prompt, put the file-ownership line at the top (first paragraph, before background).
3. If two agents could reasonably read the instructions as pointing to the same file, the instructions are
   ambiguous — fix them, don't hope.
4. After sub-agents complete, verify each produced its intended PR by checking that the PR's file list
   matches the assigned ownership. If two PRs touch the same file, one is duplicate work; close the loser
   as DIRTY and reclaim the agent's intent in a follow-up.

### Template

```text
[First paragraph]
**The file you own is: `<exact-path>`.** [If amending:] AMEND it from v<old> to v<new>.
Do NOT touch any other file [list any files you specifically must avoid].

[Then: full task description, background, context]
```

### Worked Example — Right vs Wrong

```python
# WRONG — prompt buries the filename in the task description
Agent(prompt="""Execute /learn for ProjectMnemosyne to capture a session learning.
...long context about the incident, the methodology, the verification steps...
Create a new skill describing the X-Y-Z methodology.""")

# RIGHT — prompt LEADS with the filename
Agent(prompt="""Execute /learn for ProjectMnemosyne.

**The file you own is: `skills/x-y-z-methodology.md`** (plus its .history and .notes.md
companions). Do NOT touch any other skill file.

...long context about the incident, the methodology, the verification steps...""")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Detailed-but-unprefixed prompts | Three parallel `/learn` sub-agents got long prompts describing each distinct skill topic, but no leading filename | Two of the three independently amended the same existing skill (`mojo-jit-emits-avx512-on-non-avx512-cpu.md`) instead of one creating a new file. PRs #1696 and #1697 collided; #1697 closed DIRTY. | Lead with the filename, not the topic. The task description was clear about WHAT but not about WHICH FILE. |
| Trust sub-agent context inference | Assumed each agent would pick the right file from the surrounding context | Sub-agents read prompts top-down; the "create new skill" intent was buried hundreds of words in | Move ownership statements to the FIRST paragraph. Sub-agent attention is finite and weighted early. |
| Rely on `/learn`'s "search existing skills first" step | Both colliding sub-agents ran the search step, found the existing skill, and independently concluded "amend it" — for the same skill | The search step is necessary but not sufficient. Two parallel agents will independently converge on the same "amend X" conclusion if their prompts both touch X. | The dispatcher must commit each sub-agent to a unique target file BEFORE the search step runs. |
| Switch to sequential dispatch as the "safe" alternative | Proposed as a way to avoid collisions without prompt changes | Wastes wall-clock time; parallel dispatch is fine with explicit ownership | Don't sacrifice parallelism to compensate for vague prompts. Fix the prompts. |

## Results & Parameters

Reference incident: ProjectMnemosyne PRs #1696, #1697, #1698 on 2026-05-13.

- **PR #1696** — `mojo-jit-emits-avx512-on-non-avx512-cpu` v3.0.0 amendment (intended target of
  sub-agent A) — MERGED.
- **PR #1697** — same file, same amendment from sub-agent B whose *intended* target was a NEW file —
  CLOSED DIRTY (conflicts with main).
- **PR #1698** — `multi-layer-cpu-feature-detection-mismatch-probe` (sub-agent C, prompt led with
  explicit ownership line) — MERGED successfully on first try.

Cost of the collision: ~3 minutes of manual cleanup and a wasted sub-agent dispatch
(tens of thousands of tokens). The single observable difference between the colliding agents
(A, B) and the successful one (C) was C's prompt starting with
`**The file you own is: skills/multi-layer-cpu-feature-detection-mismatch-probe.md**`.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectMnemosyne | 2026-05-13 parallel `/learn` dispatch from ProjectOdyssey session | PRs #1696/#1697 (collision) vs PR #1698 (success). Direct evidence that explicit-ownership prompts succeeded where unprefixed prompts collided. |

## Companion Skills

- `parallel-pr-worktree-workflow` — covers worktree isolation for write safety; this skill is the
  complementary *prompt-level* discipline.
- `tooling-sub-agent-pr-trust-but-verify` — after dispatch, verify each PR's file list matches the
  assigned ownership; if two PRs touch the same file, one is duplicate work.
- `hephaestus-learn-sub-agent-must-execute` — the `/learn` workflow already recommends sub-agent
  worktree isolation; this skill adds the missing prompt-construction discipline.
