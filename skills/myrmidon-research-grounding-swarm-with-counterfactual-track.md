---
name: myrmidon-research-grounding-swarm-with-counterfactual-track
description: "Ground a speculative or creative premise (sci-fi story device, invented computing concept) in real, cited science using a Myrmidon Opus swarm: one agent per research dimension writing a tagged, cited, feasibility-graded briefing, PLUS a parallel counterfactual track that re-examines each dimension under the assumption a core physical law is false, all converging in a single synthesis agent. Use when: (1) grounding a creative/speculative premise in rigorous real science (no narrative injected), (2) you need per-claim feasibility tags (established vs frontier vs speculative vs impossible) with real citations, (3) you want to separate what real physics says from what a story's new-physics lever would change via a counterfactual track, (4) one cited briefing per research dimension is the natural deliverable, (5) you want a pure synthesis (recurring-walls + tiered feasibility tables) deferring thematic/narrative integration."
category: architecture
date: 2026-05-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [myrmidon, swarm, parallel-agents, l0-commander, opus, research-grounding, counterfactual-track, evidence-file-per-dimension, feasibility-tagging, citations, synthesis-agent, creative-premise, science-grounding, wave-dispatch]
---

# Myrmidon Research-Grounding Swarm with Counterfactual Track

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-30 |
| **Objective** | Ground a speculative premise ("AI simulating the Planck-constant reaction in real time on a handheld device for ultra-precise measurement of reality", plus follow-on invented computing concepts) in real, cited science using a Myrmidon Opus swarm — pure research, no narrative content injected |
| **Outcome** | Successful: swarm ran end-to-end this session; ~47 single-purpose Opus research briefings + 1 synthesis (`00-SYNTHESIS.md`) produced, all files present on disk under `Story/Research/` |
| **Verification** | verified-local |
| **Concrete example** | Sci-fi premise grounding 2026-05-30: ~47 cited briefings, one Opus agent per research dimension, plus a parallel "assume Heisenberg uncertainty principle is false" counterfactual track, converging in one synthesis agent |

## When to Use

- Grounding a **creative or speculative premise** (a story's physics device, an invented computing concept) in **rigorous real science** with **no narrative content injected** — pure research deliverable
- You need **per-claim feasibility tags** separating established science from frontier/speculative/impossible, each backed by real citations with URLs and dates
- You want to cleanly **separate "what real physics says" from "what a story's new-physics lever would change"** — via a parallel counterfactual track that assumes a core physical law is false
- One **cited briefing per research dimension** is the natural deliverable (one agent per dimension, written to a predictable path)
- You want the synthesis to be **pure** (cross-cutting findings, a recurring-walls table, a tiered feasibility table) while **deferring thematic/narrative integration** to a later pass
- The user keeps **adding research directions mid-run** and you want to absorb each as a new wave without re-prompting in-flight agents

**Do NOT use when:**

- The premise needs narrative/thematic integration NOW (this pattern keeps research pure; integration is a separate later pass)
- N < 5 dimensions — just research directly in the main context
- The premise is already well-established science needing no skeptical grounding or feasibility tiering
- You need cross-item synthesis interleaved with research (here synthesis is a single final agent reading all files)

## Verified Workflow

### Quick Reference

```
Step 0: Capture the premise VERBATIM. Note its likely misconceptions
        (e.g. Planck CONSTANT [action, J·s] vs Planck LENGTH).

Step 1: Enumerate research DIMENSIONS (one per agent, never batch topics).
        Assign each a predictable output path: Story/Research/NN-topic.md

Step 2: Build the per-dimension Opus agent prompt (skeleton below):
        - inject premise VERBATIM
        - require per-claim TAGS + real cited sources (URL + date)
        - instruct agent to act as a rigorous skeptic & CORRECT the
          premise's own misconceptions
        - fixed output structure; ~1800-2500 words

Step 3: Dispatch in WAVES of <= 5 agents (Myrmidon cap). Background async;
        agents notify on completion. Large clusters span multiple waves.

Step 4: COUNTERFACTUAL TRACK — for each core dimension, a second Opus agent
        re-examines it under "assume core law X is false" (here: Heisenberg
        uncertainty principle), writing to sibling Story/Research/NN-h0-topic.md
        Surfaces which limits are INDEPENDENT of X (and thus survive).

Step 5: Mid-run additions = new waves of one-agent-per-dimension. Track via
        on-disk inventory (ls Story/Research), NOT by reading transcripts.
        Re-scoped/replacement agents get DISTINCT filenames (06a/06b, NN-h0-*)
        so they never collide with in-flight agents.

Step 6: SYNTHESIS — one Opus agent reads ALL evidence files, writes
        Story/Research/00-SYNTHESIS.md: executive cross-cutting findings +
        recurring-walls table + tiered feasibility table. Cite files like
        (see NN-file.md). Keep PURE — no narrative.
```

### Per-Dimension Agent Prompt Skeleton (copy-paste ready)

```
You are a rigorous physics/engineering research analyst grounding ONE dimension
of a speculative premise in REAL, CITED science. Inject no narrative.

PREMISE (verbatim — do not paraphrase):
<<<PASTE THE USER'S PREMISE VERBATIM HERE>>>

Your dimension: <DIMENSION_NAME>

Rules:
1. Separate established science from frontier/speculative/impossible. TAG EVERY claim:
   [ESTABLISHED] / [FRONTIER] / [SPECULATIVE] / [FRINGE]
   (For engineering dimensions use: [SHIPPING-NOW] / [LAB-PROTOTYPE] / [FAR-FUTURE])
2. Cite REAL sources — paper/title, URL, and date — for every non-trivial claim.
3. Act as a rigorous SKEPTIC: where the premise contains a misconception
   (e.g. conflating the Planck CONSTANT [action, J·s] with the Planck LENGTH;
   "smaller/larger than the Planck constant" as if it were a length), CORRECT it
   explicitly up front.

Write your full findings to: Story/Research/NN-<topic>.md   (~1800-2500 words)
Required structure:
  ## Summary            (what real science says about this dimension)
  <tagged body sections, each claim TAGGED and CITED>
  ## Sources            (numbered list, each with URL + date)
  ## Bottom line        (exactly 3 bullets)
```

### Counterfactual-Track Prompt Skeleton

```
Same dimension as NN-<topic>.md, but RE-EXAMINE it under a COUNTERFACTUAL:
ASSUME <CORE LAW X> IS FALSE  (this session: the Heisenberg uncertainty principle).

Tag every claim:
  [REAL-PHYSICS]                 — true regardless of the counterfactual
  [CONSEQUENCE-IF-PREMISE-TRUE]  — what changes if X is false
  [SPECULATIVE]                  — informed extrapolation

Explicitly flag which limits are INDEPENDENT of X (they survive even if X is false).
Write to a SIBLING file to avoid collisions: Story/Research/NN-h0-<topic>.md
Same ## Summary / tagged body / ## Sources / ## Bottom line structure.
```

### Synthesis-Agent Contract

```
You are the synthesis agent. READ every file in Story/Research/ (the real-physics
NN-*.md briefings AND the counterfactual NN-h0-*.md briefings). Do NOT re-prompt
any research agent. Write Story/Research/00-SYNTHESIS.md containing:

  (a) Executive cross-cutting findings
  (b) RECURRING-WALLS TABLE — each row a hard limit, listing which INDEPENDENT
      files hit that wall (e.g. "Landauer / thermodynamic floor — see 03, 11, 22")
  (c) TIERED FEASIBILITY TABLE — preserve the corpus tags
      ([ESTABLISHED]..[FRINGE] / [SHIPPING-NOW]..[FAR-FUTURE])

Cite every claim by FILE REFERENCE, e.g. (see 06a-decoherence.md).
Keep PURE: NO narrative, NO thematic integration (deferred to a later pass).
```

### Filename Conventions

| Purpose | Pattern | Example |
| ------- | ------- | ------- |
| Real-physics briefing (one per dimension) | `Story/Research/NN-topic.md` | `06-decoherence.md` |
| Counterfactual sibling (law X assumed false) | `Story/Research/NN-h0-topic.md` | `06-h0-decoherence.md` |
| Re-scoped / split replacement agent | distinct suffix `NNa` / `NNb` | `06a-decoherence.md`, `06b-measurement.md` |
| Final synthesis | `Story/Research/00-SYNTHESIS.md` | `00-SYNTHESIS.md` |

Distinct filenames for follow-up/replacement agents guarantee a re-scoped agent
never collides with an in-flight one; the commander synthesizes by reading files,
never by re-prompting.

### Wave Dispatch Reference

```
~47 dimensions  →  respect the Myrmidon <= 5-agents-per-wave cap.
Wave 1: dimensions  1- 5   (5 agents)
Wave 2: dimensions  6-10   (5 agents)
...                         (continue in waves of <= 5)
Counterfactual track: dispatch as its own set of waves (NN-h0-*).
Mid-run user additions: each becomes a new wave of one-agent-per-dimension.
All async/background; agents notify on completion. Track via `ls Story/Research`.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Combining two topics into one agent | Researched dark matter + dark energy in a single agent/file | User explicitly wanted them split; combined output had lower focus/recall per topic | Default to one dimension per agent; split on request immediately via NEW filenames |
| `cd` then bare `ls` for inventory | Ran `cd Story/Research` in one Bash call, then `ls` in a later call | `cd` does not persist across Bash tool calls; the bare `ls` resolved against an unexpected cwd | Use ABSOLUTE paths for inventory checks (or rely on the working dir already being the Research dir) |
| Trusting the premise's wording | Took "smaller than the Planck constant" / "fields slightly larger than the planck constant" at face value | Conflates the Planck CONSTANT (action, J·s) with the Planck LENGTH — a unit/category error | Bake "correct the premise's misconceptions" into EVERY agent prompt; flag unit/category errors up front |
| Reading sub-agent JSONL transcripts via shell | `cat`/`grep` the agent transcript output files to check progress | Context overflow — transcripts are huge | Rely on completion NOTIFICATIONS + on-disk file inventory (`ls Story/Research`); never read transcript JSONL |
| Collision-prone replacement filenames | Re-scoped an agent reusing an in-flight agent's filename | Replacement agent would overwrite / race the in-flight one | Give every follow-up/replacement agent a DISTINCT filename (06 → 06a/06b, NN-h0-*) |
| Mixing narrative into research synthesis | Tempted to weave thematic/story integration into the synthesis | User asked to DEFER thematic integration; mixing pollutes the pure evidence corpus | Keep synthesis PURE (findings + recurring-walls + tiered feasibility); integration is a separate later pass |

## Results & Parameters

### Session (2026-05-30 — speculative premise grounding)

| Metric | Value |
| ------- | ------- |
| Research dimensions | ~46 (one Opus agent each) |
| Counterfactual-track agents | included in total (NN-h0-* siblings for core dimensions) |
| Synthesis agents | 1 (Opus, reads ALL evidence files) |
| Total Opus agents | ~47 research + 1 synthesis |
| Output per agent | one cited briefing, ~1800-2500 words |
| Output path convention | `Story/Research/NN-topic.md`, `Story/Research/NN-h0-topic.md` |
| Synthesis output | `Story/Research/00-SYNTHESIS.md` |
| Dispatch | background async, waves of <= 5 (Myrmidon cap) |
| Narrative injected | none — pure research |

### Tag Schemes (preserve through synthesis)

| Track | Tags |
| ----- | ---- |
| Science feasibility | `[ESTABLISHED]` / `[FRONTIER]` / `[SPECULATIVE]` / `[FRINGE]` |
| Engineering readiness | `[SHIPPING-NOW]` / `[LAB-PROTOTYPE]` / `[FAR-FUTURE]` |
| Counterfactual | `[REAL-PHYSICS]` / `[CONSEQUENCE-IF-PREMISE-TRUE]` / `[SPECULATIVE]` |

### Required Briefing Structure

```
## Summary
<tagged body sections — every claim TAGGED and CITED>
## Sources        (numbered, each with URL + date)
## Bottom line    (exactly 3 bullets)
```

### Synthesis Output Structure

```
# 00-SYNTHESIS
<executive cross-cutting findings>
## Recurring Walls      (table: wall | independent files that hit it, e.g. "see 03, 11, 22")
## Tiered Feasibility   (table preserving corpus tags)
# every claim cited by file reference, e.g. (see 06a-decoherence.md)
```

### Why One Agent Per Dimension (mirrors one-agent-per-item)

This is the one-agent-per-item pattern applied to research DIMENSIONS instead of
portfolio items: each agent has undivided context, picks up dimension-specific
evidence, and writes a discrete cited file. Batching dimensions dilutes context
and lowers recall — split on request immediately.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Story / Research | Speculative sci-fi premise grounding, 2026-05-30 | ~47 cited Opus briefings + 1 synthesis under `Story/Research/`; real-physics + counterfactual (Heisenberg-false) tracks; verified-local (files present on disk; not CI-tested) |

## References

- [myrmidon-one-agent-per-item-portfolio-research-pattern.md](myrmidon-one-agent-per-item-portfolio-research-pattern.md) — Sibling pattern: one agent per item for portfolio/due-diligence research (this skill applies the same granularity rule to research dimensions and adds a counterfactual track + feasibility tagging)
- [parallel-agent-research-and-swarm-orchestration.md](parallel-agent-research-and-swarm-orchestration.md) — General Myrmidon swarm orchestration (wave limits, agent tiers, L0 commander)
- [swarm-agent-status-misread-as-premature-exit.md](swarm-agent-status-misread-as-premature-exit.md) — Handling agent status misreads during wave execution
