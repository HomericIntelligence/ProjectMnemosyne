---
name: stop-reassess-gate-bulk-transformation
description: "Insert an explicit stop-and-reassess gate between a 'bulk transformation' phase and an 'implementation' phase so survivor tasks can be re-graded against the new post-transformation state. Use when: (1) a plan has Phase A (prep) + Phase B (bulk-close/bulk-delete) + Phase C (cleanup PRs) followed by Phase D (implement survivor issues), (2) the bulk transformation will make some survivor tasks moot (e.g., docs about feature X become irrelevant when feature X is deleted), (3) you are about to dispatch a swarm of implementation agents on a survivor queue that was graded against the OLD repo state, (4) a survivor issue was originally graded KEEP-EASY but its subject was deleted by the cleanup phase, (5) the plan author wants to insert a re-grade checkpoint after structural changes land but before implementation begins, (6) implementation work is expensive enough (agent dispatches, CI runs, reviewer time) that re-grading a moot issue out of the queue is cheaper than implementing it."
category: tooling
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [planning, stop-gate, re-grade, survivor-queue, phase-boundary, bulk-transformation, implementation-phase, swarm-dispatch]
---

# Stop-and-Reassess Gate Between Bulk Transformation and Implementation Phases

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-17 |
| **Objective** | Avoid implementing now-irrelevant survivor tasks after a bulk transformation (mass closure / mass deletion / charter cleanup) reshapes the repo. |
| **Outcome** | Successful: in a Myrmidons cleanup session, the user explicitly requested a STOP POINT before dispatching Phase D implementation agents. Several KEEP-EASY survivor issues (e.g., TLS env-var documentation) became moot once the cleanup PRs landed (TLS env vars left with the reconciler). Re-grading after the cleanup avoided wasted swarm dispatches. |
| **Verification** | verified-local — applied successfully in the Myrmidons 2026-05-17 session |

## When to Use

- A plan has a clear "bulk transformation" phase (bulk-close issues, mass-delete files, mass-rename, schema migration) followed by an "implementation" phase that consumes a queue of survivor tasks.
- The survivor queue was graded against the pre-transformation state.
- The bulk transformation will plausibly invalidate some survivor tasks (e.g., issues about feature X are moot when feature X is deleted; docs tasks are moot when their subject file is removed; lint expansions are moot when the offending code is gone).
- You are about to dispatch parallel swarm agents on the survivor queue. Each dispatch costs agent time + CI cycles + reviewer attention — moot issues are pure waste.
- Implementation has not yet started, so there is still time to re-grade.

## Verified Workflow

### Quick Reference

```text
Phase A (prep)          ─┐
Phase B (bulk-close)     ├─ bulk-transformation phases
Phase C (cleanup PRs)   ─┘
        │
        ▼
   ===== STOP-AND-REASSESS GATE =====
   For each survivor task in the queue:
     1. Read the original task description
     2. Check whether the subject still exists post-transformation
     3. Re-grade: KEEP / MOOT-NOW / NEEDS-REWRITE
     4. Remove MOOT-NOW tasks from the queue
     5. Re-write NEEDS-REWRITE tasks against new state
   ===== / GATE =====
        │
        ▼
Phase D (implement survivors) — only the still-relevant tasks
```

### Detailed Steps

1. **Recognise the gate boundary.** Any plan whose phases look like
   `prep → bulk-X → cleanup → implement-survivors` has a latent re-grade gate
   between `cleanup` and `implement-survivors`. Plans that go straight from
   bulk-transformation to dispatch usually waste agent time on moot tasks.

2. **Insert an explicit STOP POINT in the plan.** Do not let the plan run
   uninterrupted from Phase C into Phase D. Write the gate into the plan as
   its own step: "STOP: re-grade survivor queue against post-cleanup state
   before dispatching Phase D." This makes the gate visible to reviewers and
   to future you.

3. **For each survivor task, run a three-way re-grade:**
   - **KEEP** — task subject still exists and is still in-charter; task is
     still valuable. Stays in the queue.
   - **MOOT-NOW** — task subject was deleted, deprecated, or made irrelevant
     by Phase B/C. Close the issue with a comment linking to the cleanup PR
     that obsoleted it. Remove from the queue.
   - **NEEDS-REWRITE** — task subject changed shape (e.g., the file moved,
     the API renamed, the scope shrank). The original wording is wrong but
     the underlying intent still has value. Rewrite the issue against the
     new state, then keep it in the queue.

4. **Use cleanup PRs as the evidence.** When closing a MOOT-NOW issue,
   the comment should link to the exact PR that obsoleted it — e.g., "Closed
   as moot: TLS env vars were removed in #732 (reconciler cleanup). The docs
   this issue asked to write no longer have a subject to document." This
   gives the issue author a clear chain of reasoning.

5. **Only dispatch implementation agents after the gate completes.** A swarm
   dispatched against a partially-moot queue will waste resources on tasks
   that get auto-closed (or worse, produce PRs that are immediately rejected
   as out-of-charter).

6. **Generalise: any plan with bulk-X-then-implement-Y has this gate.** The
   pattern is not specific to charter cleanup. It also applies to:
   - Mass schema migration → reimplement queries (some queries now invalid)
   - Mass dependency upgrade → reimplement callers (some callers replaced)
   - Mass rename → update docs (some doc files now empty / merged)
   - Mass deprecation → port consumers (some consumers also being deprecated)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running Phase D directly after Phase C | Initial plan was `prep → bulk-close → cleanup-PRs → implement-survivors` with no gate, assuming the survivor queue was already filtered | Several KEEP-EASY survivor issues were graded against the OLD repo state. Once the cleanup PRs landed, their subjects were gone (e.g., TLS env-var documentation became moot when TLS env vars left with the reconciler in PR #732). Dispatching a swarm would have produced PRs that immediately failed code review as out-of-charter. | Always insert a stop-and-reassess gate between any "bulk transformation" phase and any "implementation" phase. |
| Trusting the original grading | Assumed the upfront classification (KEEP-EASY / KEEP-MEDIUM / KEEP-HARD) was stable across phases | Classification is only valid against the repo state it was performed on. Bulk transformations invalidate the grading basis. A KEEP-EASY task whose subject was just deleted is now MOOT-NOW, regardless of its original grade. | Treat survivor-queue grading as state-dependent. Re-grade after every structural transformation. |
| Catching moot tasks at implementation time | Considered letting the implementation agents discover mootness themselves (e.g., agent opens the file, sees it doesn't exist, reports back) | Wastes the full agent dispatch + CI cycle + reviewer attention. Detection at the gate is O(seconds-per-issue); detection at implementation is O(minutes-per-issue) + tool quota + reviewer time. | Front-load the re-grade. Cheap human/orchestrator inspection beats expensive agent dispatch. |
| Omitting the cleanup-PR link in close comments | Tried closing MOOT-NOW issues with a terse "out of scope now" | Issue authors push back without a clear chain of reasoning. They need to see the exact PR that obsoleted their task. | Always link the closing comment to the specific cleanup PR. The PR is the evidence. |

## Results & Parameters

**Phase-boundary checklist (Myrmidons session, 2026-05-17):**

```text
[x] Phase A (migration prep)               complete
[x] Phase B (bulk-close out-of-charter)    127 issues closed
[x] Phase C (stacked deletion PRs)         #730, #731, #732, #733 opened
[!] STOP POINT — RE-GRADE SURVIVOR QUEUE   <-- gate inserted here at user's request
[ ] Phase D (implement survivors)          pending re-grade
```

**Re-grade outcome buckets (template):**

| Bucket | Action |
|--------|--------|
| KEEP — still relevant | Stays in implementation queue |
| MOOT-NOW — subject deleted | Close issue with link to obsoleting cleanup PR |
| NEEDS-REWRITE — scope changed | Rewrite issue against post-cleanup state, then keep |

**Example MOOT-NOW close comment:**

```text
Closing as moot: the TLS env-var documentation this issue asked to write no
longer has a subject. TLS env vars were removed from this repo in #732 when
the reconciler was ported to ProjectAgamemnon (see ProjectAgamemnon#405).
If TLS docs are still needed, they belong in ProjectAgamemnon's docs tree,
not here.
```

**When to apply the gate (heuristic):**

> If any Phase B or Phase C change could *plausibly* invalidate a survivor
> task — file deletion, API rename, scope reduction, dependency removal —
> insert the gate. The cost of the gate is minutes; the cost of skipping it
> is wasted swarm dispatches.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Myrmidons | 2026-05-17 charter-cleanup session — user explicitly requested a STOP POINT before Phase D after observing that some survivor issues would be mooted by the cleanup PRs | Gate inserted between cleanup PRs (#730-#733) and survivor implementation; several TLS env-var documentation issues identified as MOOT-NOW |
