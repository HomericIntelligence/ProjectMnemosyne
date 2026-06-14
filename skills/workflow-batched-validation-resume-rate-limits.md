---
name: workflow-batched-validation-resume-rate-limits
description: "Run multi-hour, multi-agent document validation/migration sweeps in Claude Code so they survive session death and API usage-limit resets. Patterns: batch by section instead of per-field (stay under the 1,000-agent workflow cap and avoid re-reading sources), make per-item output JSONs double as a skip-cache for idempotent reruns, resume with Workflow resumeFromRunId so completed agents replay from the journal cache, and persist all scratch state beside the data instead of /tmp. Use when: (1) a validation fan-out may outlive a session or hit usage limits, (2) deciding agent granularity for per-field/per-item sweeps, (3) Workflow-tool orchestration must be resumable/idempotent."
category: tooling
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [workflow, orchestration, batching, resume, rate-limits, skip-cache, subagents]
---

# Workflow: Batched Validation with Resume Across Rate Limits

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-12 |
| Objective | Run a 184-document, per-field validation sweep in Claude Code to completion despite usage-limit resets and session death |
| Outcome | 184/184 items (2,890 fields) validated by 22 agents across 3 resumed runs; zero re-validation of completed items |
| Version | 1.0.0 |

### Verified On

| Context | Result |
|---------|--------|
| FL-142/FL-150 divorce-disclosure validation Pass 3, June 2026 (private repo — no case identifiers in this skill) | 184/184 items completed across two usage-limit resets and one session death |

## When to Use

Apply this skill when:

1. **Multi-hour, multi-agent document validation/migration sweeps** that may outlive a Claude Code session or hit API usage limits — the run must be able to stop and continue without losing completed work.
2. **Deciding agent granularity** for per-field or per-item validation fan-outs — choosing between agent-per-field, agent-per-item, and agent-per-batch designs.
3. **Claude Code Workflow-tool orchestration** that must be resumable and idempotent — any rerun (resume, crash recovery, or a brand-new workflow over the same data) should skip already-completed items for free.

## Verified Workflow

### 1. Batch by section/document-group, not per-field

- A literal agent-per-field design was ~4,500 agents — over the 1,000-agent/workflow cap. An agent-per-item design was 224 agents that re-read the same source PDFs dozens of times.
- Batching whole sections at ~12 items/agent (chunk sections >14 items into chunks of 12) gave 22 agents with identical coverage.
- Each batch agent runs the full per-item procedure sequentially and is explicitly told **"do not get lazier on later items in the batch"** — without this, quality degrades on the tail of the batch.

### 2. Make per-item output files double as a skip-cache

- Each agent writes one JSON per completed item to a persistent scratch dir.
- The prompt's STEP 0 says: *"if `<scratch>/items/<basename>.json` exists and parses with a non-empty `rows` array, load its summary and SKIP the item."*
- Any rerun — resume, crash, or a brand-new workflow — is then idempotent for free.

### 3. Use Workflow `resumeFromRunId` to resume

- Completed `agent()` calls replay from the journal cache instantly; failed/missing ones run live.
- Pattern: same `scriptPath` + `resumeFromRunId=<original run id>`.
- The run survived: session death (background workflows die when the Claude Code session closes), then "session limit" failures at two different reset times. Each resume completed more batches; the third resume finished 184/184 plus the sync phase.

### 4. Compute downstream-phase inputs from structured returns

- The Tier-2 sync phase consumed the structured returns of the batch agents.
- A `parallel()` barrier between the validate and sync phases is justified because sync aggregates all per-section results.

### 5. Persist ALL scratch state beside the data, not in /tmp

- Workflow script, per-item JSONs, and assembly/verify scripts live in a hidden dir next to the data (e.g. `<repo>/.pass3/`), NOT `/tmp` — `/tmp` can be wiped between tool calls.

### Quick Reference

1. Chunk items into batches of ~12 per agent (split sections >14 items); keep total agents well under the 1,000/workflow cap.
2. Prompt STEP 0 = skip-cache check on per-item JSON; agents write one JSON per item to a persistent scratch dir.
3. Tell each batch agent to run the full per-item procedure sequentially and not get lazier on later items.
4. Persist all scratch state in a hidden dir beside the data (e.g. `<repo>/.pass3/`), never `/tmp`.
5. On session death or usage-limit failure, relaunch with `Workflow({scriptPath, resumeFromRunId: "wf_..."})` — cached agents replay, failed agents re-run.
6. Embed data as `const` literals in the persisted script file; do not pass large `args` objects to the Workflow tool.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Large args object passed to Workflow tool | Script crashed instantly: "undefined is not an object (evaluating 'args.sadItems.map')" — args never reached the script | Embed data as const literals in the script file (edit the persisted script, relaunch via scriptPath) |
| 2 | Scratch state in /tmp | /tmp was wiped between tool calls in the sandboxed environment — helper scripts and the skip-cache vanished mid-session | Persist scratch in a hidden dir beside the target repo |
| 3 | Expecting background workflow to survive session close | Workflow died overnight with zero notification artifacts; 0-byte task output file | Keep the session open, or just resume with resumeFromRunId — completed work replays from cache |
| 4 | Assuming a usage-limit failure loses completed work | 9 of 18 batches failed with "You've hit your session limit · resets 10pm" | Failures are not cached; resume after the reset re-runs only the failed agents (91 cached + 30 new on first resume) |

## Results & Parameters

### Batch-prompt skeleton

```text
You are validating a batch of N items. Run the FULL procedure for every item,
in order. Do not get lazier on later items in the batch.

STEP 0 (skip-cache): For each item, if <scratch>/items/<basename>.json exists
and parses with a non-empty "rows" array, load its summary and SKIP the item.

For each remaining item:
  1. <per-item validation steps: open source doc, extract fields, compare,
     classify each field as match/mismatch/missing>
  2. Write <scratch>/items/<basename>.json with the full per-field rows array
     and a summary block.

Return: structured per-item summaries (basename, field counts, mismatch list)
for every item in the batch, including skipped ones (from their cached JSON).
```

### Resume invocation

```javascript
Workflow({
  scriptPath: "<repo>/.pass3/validate_workflow.ts",
  resumeFromRunId: "wf_..."  // run id from the original launch
})
```

### Numbers

| Parameter | Value |
|-----------|-------|
| Items / fields validated | 184 items / 2,890 fields |
| Agents | 22 (18 validate + 3 sync + 1 index) |
| Batch size | ~12 items/agent (sections >14 items chunked into 12s) |
| Runs to completion | 3 (original + 2 resumes across usage-limit resets) |
| First-resume cache behavior | 91 agent calls replayed from cache + 30 ran live |
| Total subagent tokens | ~3.7M |
| Re-validation of completed items | Zero (per-item JSON skip-cache) |
