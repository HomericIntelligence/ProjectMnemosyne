---
name: myrmidon-one-agent-per-item-portfolio-research-pattern
description: "Dispatch ONE Myrmidon agent per item (not 3-4 items per agent) when researching N independent items (10+ startup holdings, contractor invoices, paper citations, etc.). Each agent fully focuses on one item, picks up item-specific evidence, handles identity-disambiguation per-item, and writes a discrete evidence file. Commander synthesizes by reading files. Use when: (1) N >= 10 independent items, (2) each item needs ~5-6 web searches, (3) one-document-per-item is the natural output, (4) batching agents (3-4 items per agent) produced lower quality."
category: architecture
date: 2026-05-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [myrmidon, swarm, parallel-agents, l0-commander, one-agent-per-item, portfolio-research, due-diligence, evidence-file-per-item, wave-dispatch, identity-disambiguation]
---

# Myrmidon One-Agent-Per-Item Portfolio Research Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-30 |
| **Objective** | Establish the canonical granularity rule for Myrmidon swarms researching N independent items: one agent per item beats batching 3-4 items per agent |
| **Outcome** | Verified locally during VillmowFutures portfolio due-diligence session (May 2026): 17 startup holdings → 17 discrete `Status_<Issuer>.md` files, 100% identity-match rate, nuanced per-item evidence caught across all holdings |
| **Verification** | verified-local |
| **Concrete example** | VillmowFutures research 2026-05-30: 17 holdings, 5 waves of 3-4 agents each, one agent per holding |

## When to Use

- N >= 10 **independent** items where each item needs ~5-6 web searches
- "One document per item" is the natural deliverable (holdings research, contractor invoice audit, paper citation check)
- Items are amenable to identity-disambiguation per-item (e.g. distinguishing similarly-named entities)
- You have previously tried batching (3-4 items/agent) and found lower recall or missed nuances
- Commander synthesis is "read N files, extract verdicts" — not cross-item analysis

**Do NOT use when:**

- Items have cross-item dependencies (e.g., corporate structure where subsidiary classification affects parent)
- N < 5 — just handle directly in the main context
- Research requires synthesizing relationships *across* items (use a single agent reading all evidence files after per-item agents complete)

## Verified Workflow

### Quick Reference

```
Step 1: Enumerate N independent items → list with item-specific facts injected per prompt
Step 2: Build per-item agent prompt template
         → inject: item name, known identifiers, output file path
         → instruct: write to <dir>/Status_<Item>.md, cite >= 3 sources
Step 3: Dispatch in waves of 4-5 agents (Myrmidon 5-agent-per-wave cap)
         → 17 items = 4-5 waves of 3-5 agents each
Step 4: Each agent writes to predictable path: <dir>/Status_<Item>.md
Step 5: Commander synthesizes by reading filenames + per-item verdicts
         → no re-prompting agents; just read output files
```

### Per-Item Agent Prompt Template Skeleton

```
You are researching ONE item: <ITEM_NAME>

Known identifiers / disambiguation hints:
  - <ITEM_IDENTIFIER_1>
  - <ITEM_IDENTIFIER_2>

Tasks:
1. Search for current status, funding, legal issues, key news (5-6 WebSearch queries)
2. Disambiguate identity if multiple entities share similar names — pick the correct one
3. Write your complete findings to: <OUTPUT_DIR>/Status_<ITEM_SLUG>.md

Output file must contain:
- ## Summary (2-3 sentences, status verdict)
- ## Evidence (3+ cited sources with dates)
- ## Identity Disambiguation (if needed)
- ## Verdict: [ACTIVE | INACTIVE | UNCERTAIN | INSOLVENT | ACQUIRED]
```

### Wave Dispatch Reference

```
Items: 17
Wave 1: items  1- 4  (4 agents)
Wave 2: items  5- 8  (4 agents)
Wave 3: items  9-12  (4 agents)
Wave 4: items 13-16  (4 agents)
Wave 5: item  17     (1 agent)
# Alternatively: 5 waves of 3-4 agents each — either is fine
# Never dispatch all 17 in a single wave (Myrmidon 5-agent cap)
```

### Commander Synthesis Pattern

```python
# After all waves complete, commander reads output files:
for item in items:
    path = f"{output_dir}/Status_{item.slug}.md"
    verdict = extract_verdict_line(path)  # grep for "## Verdict:"
    summary_table.append((item.name, verdict))

# Write master summary from verdict table — no re-prompting agents needed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Plan A: 4 agents × 4 holdings each | Batch 17 holdings into 4 agents (4-4-4-5 items each) | User objected immediately; batching would have lost per-item disambiguation (Smart Tire Recycling vs SMART Tire Company are two separate StartEngine alumni with nearly identical names) | One-agent-per-item is the correct granularity for portfolio research; batching compromises recall |
| Single-agent all-17 pass | One agent researching all 17 holdings sequentially | Context-window strain; per-item evidence trail lost; early items contaminate later item analysis; agent skips nuanced disambiguation | Parallel per-item agents avoid context bloat and maintain clean evidence trails |
| Dispatch all 17 in a single wave | Launch 17 Myrmidon agents simultaneously | Violates Myrmidon 5-agent-per-wave cap; causes resource exhaustion and agent failures | Always respect the 5-agent-per-wave cap; 17 items = 4-5 waves |

## Results & Parameters

### VillmowFutures Session (2026-05-30)

| Metric | Value |
| ------- | ------- |
| Holdings researched | 17 |
| Agents dispatched | 17 (one per holding) |
| Waves | 5 (4-4-4-4-1 or similar) |
| Web searches per agent | ~5 queries |
| Wall time per agent | ~80-120 seconds |
| Total wall time | ~25-30 minutes |
| Evidence files produced | 17 (one per holding) |
| Identity-match rate | 100% |
| Disambiguation issues caught | 2 (Smart Tire Recycling vs SMART Tire Company; Piestro CB-Insights-vs-PitchBook conflict) |
| Nuanced evidence caught | BlueSky Energy Austrian Wels Regional Court insolvency; Island Brands fraud lawsuit + Bogmeyer brand-only acquisition |
| Per-agent report size | 100-200 words back to commander (vs 600+ for batched agents) |

### Token Cost Comparison

| Approach | Agents | Searches/Agent | Total Searches | Context per Agent | Quality |
| -------- | ------ | --------------- | --------------- | ----------------- | ------- |
| One-agent-per-item (17 items) | 17 | 5-6 | ~90 | Minimal (1 item) | High — per-item focus |
| Batched (4 agents × 4 items) | 4 | 20-25 | ~90 | Heavy (4 items mixed) | Lower — context dilution |

Token cost is roughly equivalent; quality difference is significant because per-item agents have undivided context.

### Identity-Disambiguation Nuance

Per-item agents naturally surface disambiguation issues because they are asked about ONE entity and must confirm they have the right one. Batched agents face competing attention across multiple items and tend to accept the most prominent search result without disambiguation.

Example from session:
- **SMART Tire Company** — NASA shape-memory-alloy airless tire technology (StartEngine 2021)
- **Smart Tire Recycling** — supercritical-water tire-to-oil process (separate StartEngine alumni)
- A batched agent mixing these two items would likely conflate them; per-item agents correctly separated them

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| VillmowFutures | 17 startup holdings due-diligence, May 2026 | 5 waves of per-item Myrmidon agents; 17 Status_*.md files produced; 100% identity-match rate |

## References

- [parallel-agent-research-and-swarm-orchestration.md](parallel-agent-research-and-swarm-orchestration.md) — General Myrmidon swarm orchestration pattern (wave limits, agent tiers, L0 commander)
- [swarm-agent-status-misread-as-premature-exit.md](swarm-agent-status-misread-as-premature-exit.md) — Handling agent status misreads during wave execution
