---
name: pr-review-threadless-nogo-verdict-retry-wedge
description: "A queue-based pipeline pr_review stage that returns a NOGO verdict carrying ZERO machine-extractable findings (no review threads, no file:line comments) deterministically wedges the review->implement retry loop until the budget exhausts. Use when: (1) a pipeline pr_review stage returns NOGO but the findings-parser extracts no durable line-level findings so the implementer has nothing concrete to address, (2) the same input re-runs deterministically (2 retries + final = 3 attempts) producing the identical threadless NOGO each time and tripping the artifact-failure cap, (3) an item fails back to implementation whose own fail-back budget (2/2) then also exhausts re-adopting the same PR, reaching a TERMINAL 'manual look needed' stop, (4) a cluster of terminal stops over a long single-repo loop run all trace to the SAME root cause (pr_review.py _nogo_without_durable_artifact) and correlate with a specific issue class (e.g. AUDIT-FINDING issues) rather than a global reviewer breakdown, (5) you are tempted to react to each recurrence as a fresh bug, kill the loop on first wedge, or 'just let it retry' a deterministic input that cannot change between attempts."
category: ci-cd
date: 2026-07-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pr-review
  - nogo-verdict
  - threadless-nogo
  - durable-finding
  - retry-wedge
  - deterministic-retry
  - artifact-failure-cap
  - fail-back-budget
  - review-loop
  - pipeline
  - queue-based-automation
  - poisoned-item-isolation
  - terminal-stop
  - audit-finding-issues
  - escalate-not-retry
  - synthetic-finding
  - root-cause-clustering
  - homericintelligence
---

# PR Review Threadless NOGO Verdict Retry Wedge

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-11 |
| **Objective** | Diagnose why a queue-based automation pipeline's `pr_review` stage deterministically wedged the review->implement retry loop on a specific class of issues, burning the full retry budget while achieving nothing, and land a root-cause fix that stops silently retrying an input that cannot change. |
| **Outcome** | Root-caused to `hephaestus/automation/pipeline/pr_review.py:805` (`_nogo_without_durable_artifact`): a NOGO verdict from which the findings-parser extracts zero durable line-level findings. Filed as bug #2079 with full occurrence data; root-cause fix landed via PR #2105. Blast radius bounded by poisoned-item isolation — the loop stayed net-productive (29 PRs created) despite ~15-21% of pr_review'd issues hitting the wedge. |
| **Verification** | verified-ci — bug #2079 filed with occurrence data from a 4.3h single-repo loop run; the root-cause fix landed via PR #2105. |

## When to Use

- A queue-based pipeline `pr_review` stage returns a NOGO verdict but the findings-parser extracts NO durable line-level findings — no review threads, no `file:line` comments — so the implementer has nothing concrete to address.
- The fail-back path re-runs the review deterministically (2 retries + final = 3 attempts), producing the SAME threadless NOGO each time and tripping the artifact-failure cap, failing the item back to implementation.
- Implementation's own fail-back budget (2/2) then also exhausts re-adopting the same PR, and the item reaches a TERMINAL "manual look needed" stop.
- A cluster of terminal stops over a long single-repo loop run all trace to the SAME root cause and correlate with ONE issue class (here, AUDIT-FINDING issues) rather than a global reviewer breakdown.
- You are tempted to (a) react to each recurrence as a fresh bug, (b) kill the loop on the first wedge, or (c) "just let it retry" — when the input is deterministic and cannot change between attempts.

## Verified Workflow

### Quick Reference

```text
# The wedge condition (distinct case that MUST NOT silently retry):
verdict == NOGO  AND  durable_findings(review_output) == []   # no threads, no file:line

# WRONG: default fail-back retries the identical input
for attempt in (1, 2, final):        # 2 retries + final = 3 attempts
    verdict, findings = run_pr_review(pr)   # deterministic -> same threadless NOGO
    # nothing to address -> artifact-failure cap trips -> fail back to implementation
    # implementation fail-back (2/2) re-adopts same PR -> exhausts -> TERMINAL stop

# RIGHT: treat "NOGO + zero durable findings" as a DISTINCT case
if verdict == NOGO and not durable_findings:
    # (a) surface the raw verdict body as a SYNTHETIC finding, OR
    # (b) classify as a review-ARTIFACT error and ESCALATE to a human
    # Do NOT loop the deterministic fail-back.
```

```text
# Wedge vs normal stop:
normal poisoned-item stop  -> isolated, correct, may spend < full budget
threadless-NOGO wedge      -> DETERMINISTIC: same input -> same NOGO -> ALWAYS burns full budget
```

### Detailed Steps

**1. Recognize the wedge by its determinism, not its symptom.** The terminal "manual look needed" stop looks like any other poisoned-item stop. What makes THIS one a wedge is that the retry is deterministic: same input -> same threadless NOGO -> same exhaustion. Nothing changes between attempts, so the retry budget is spent achieving nothing. A normal poisoned-item stop is isolated and correct (an item that genuinely can't proceed); the wedge is a specific input class that ALWAYS burns the full budget.

**2. Trace to the single root cause before filing.** In a queue-based pipeline, the `pr_review` stage can return a NOGO whose findings-parser yields no durable line-level findings (`_nogo_without_durable_artifact` at `pr_review.py:805`). The implementer then has nothing concrete to address, so the fail-back path re-runs the review deterministically (2 retries + final = 3 attempts). Each attempt produces the same threadless NOGO, tripping the artifact-failure cap and failing the item back to implementation. If implementation's own fail-back budget (2/2) also exhausts re-adopting the same PR, the item reaches the TERMINAL stop.

**3. Cluster recurrences by root cause; count at run_end, don't file per-occurrence.** Over the observed run, 7 issues / 10 terminal stops all traced to `pr_review.py:805`. File ONE bug (#2079) with the aggregate occurrence data, not one per stop. Note the final count at run_end.

**4. Confirm the blast radius is CLASS-scoped, not a global reviewer breakdown.** The wedge correlated specifically with AUDIT-FINDING issues; other issue classes passed review cleanly. ~15-21% of pr_review'd issues hit it (7 issues / 10 terminal stops over a 4.3h single-repo run). This is a targeted input-class failure, not the reviewer being broken everywhere.

**5. Let the loop finish; the wedge is survivable.** Poisoned-item isolation bounded each wedge — the loop always continued to the next issue and stayed net-productive (29 PRs created). The stuck PRs' underlying implementation work was INTACT: each PR's own CI judged it independently, so only the review infra failed and no work was lost. Do NOT abort the loop on the first wedge — that would abandon good, independently-CI-judged work.

**6. Fix the root cause: treat "NOGO + zero durable findings" as a DISTINCT case.** Either (a) surface the raw verdict body as a synthetic finding so the implementer has something concrete to act on, or (b) classify it as a review-artifact error and escalate to a human — rather than looping the deterministic fail-back. The load-bearing principle: **do NOT silently retry an input that cannot change.** Merged via PR #2105.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Let the loop retry | Default fail-back re-ran the same review 3x (2 retries + final) | Deterministic input -> identical threadless NOGO each attempt -> artifact-failure cap trips -> budget exhausted for nothing | A retry only helps if SOMETHING can change between attempts; a threadless NOGO is invariant. Do not silently retry an input that cannot change. |
| Treat every terminal stop as a new bug | Reacted to each #2079 recurrence as a fresh signal | They were all the SAME root cause (`pr_review.py:805`, `_nogo_without_durable_artifact`) | Cluster by root cause before filing; note the final count at run_end, don't file per-occurrence. |
| Kill the loop on first wedge | Considered aborting the whole run when the wedge first appeared | Would abandon 8 PRs of good, independently-CI-judged work whose implementation was intact | Poisoned-item isolation means a bounded wedge is survivable; let the loop finish and fix the root cause separately. |

## Results & Parameters

### The wedge condition and the two correct dispositions

```text
Condition:  verdict == NOGO  AND  durable_findings == []   (no threads, no file:line comments)
Root cause: hephaestus/automation/pipeline/pr_review.py:805  (_nogo_without_durable_artifact)

WRONG (default): loop the deterministic fail-back
  pr_review fail-back: 2 retries + final = 3 attempts  -> same threadless NOGO each time
  -> trips artifact-failure cap -> fails back to implementation
  implementation fail-back: 2/2 -> re-adopts same PR -> exhausts -> TERMINAL "manual look needed"

RIGHT (fix, PR #2105): treat as a DISTINCT case
  (a) surface raw verdict body as a SYNTHETIC finding (implementer gets something concrete), OR
  (b) classify as a review-ARTIFACT error and ESCALATE to a human
  NEVER silently retry an input that cannot change.
```

### Blast-radius data (4.3h single-repo loop run)

| Metric | Value | Notes |
|--------|-------|-------|
| Terminal stops hitting the wedge | 7 issues / 10 terminal stops | All same root cause (`pr_review.py:805`) |
| Fraction of pr_review'd issues affected | ~15-21% | Class-scoped, NOT a global reviewer breakdown |
| Correlated issue class | AUDIT-FINDING issues | Other issue classes passed review cleanly |
| Net productivity | POSITIVE — 29 PRs created | Poisoned-item isolation bounded each wedge; loop always continued |
| Stuck PRs' underlying work | INTACT | Each PR's own CI judged it independently; only the review infra failed, no work lost |

### Retry budgets involved

| Budget | Value | Behavior on the wedge |
|--------|-------|-----------------------|
| pr_review fail-back | 2 retries + final = 3 attempts | Each attempt deterministically reproduces the threadless NOGO; trips the artifact-failure cap |
| implementation fail-back | 2 / 2 | Re-adopts the same PR; exhausts; reaches TERMINAL "manual look needed" stop |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Queue-based automation pipeline `pr_review` stage; 4.3h single-repo loop run surfaced 7 issues / 10 terminal stops all tracing to `pr_review.py:805` (`_nogo_without_durable_artifact`), correlated with AUDIT-FINDING issues; loop stayed net-productive (29 PRs) via poisoned-item isolation | Bug #2079 (full occurrence data); root-cause fix merged via PR #2105 |
