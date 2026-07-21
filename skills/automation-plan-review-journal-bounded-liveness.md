---
name: automation-plan-review-journal-bounded-liveness
description: "Keep durable plan/review journals useful without making agent prompts unbounded or letting identical amendments exhaust review cycles. Use when: (1) a pipeline archives plan revisions and reviews in GitHub comments, (2) archived history is injected into planner or reviewer prompts, (3) a NOGO amendment can repeat the prior plan, or (4) a state machine promises to block on no progress."
category: architecture
date: 2026-07-21
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - automation-loop
  - plan-review
  - durable-journal
  - bounded-context
  - no-progress
  - liveness
  - state-machine
  - prompt-budget
---

# Automation Plan-Review Journal: Bounded Context and Liveness

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-21 |
| **Objective** | Preserve a complete, auditable plan/review journal while giving agents a bounded actionable view and terminating repeated no-progress amendments as blocked. |
| **Outcome** | A strict review of ProjectHephaestus PR #2357 found that every archived full plan, diff, and review was sent to later planner/reviewer prompts, while identical amendments continued through the full iteration budget. The proposed remediation was not implemented in this session. |
| **Verification** | unverified — source-level review plus focused tests (437 passed) confirmed the current behavior, but the bounded-view/no-progress implementation and its CI evidence do not yet exist. |

## When to Use

- A workflow writes every plan revision and review to an issue or PR comment as a durable audit trail.
- The same workflow feeds comment history back into an LLM planner, reviewer, or amendment prompt.
- A plan review claims that "no improvement" should stop early, but the implementation only recognizes an explicit reviewer `BLOCKED` verdict.
- An amend job can return text identical to an earlier plan, or a cycle can alternate between previously seen plans.
- A long-lived issue risks context-window overflow, prompt-cost growth, or repeated stale guidance.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a design and test plan until the implementation passes CI.

### Quick Reference

```text
GitHub comments are the complete durable journal.
Agent prompts receive a deterministic, bounded projection.

On amendment:
  normalize candidate and prior plan content
  if candidate is unchanged or repeats a known revision:
      publish the reason
      atomically set state:plan-blocked and remove sibling plan-state labels
      stop; submit no further planner/reviewer job
  otherwise:
      archive the superseded full plan/review and continue

For prompt context:
  include current plan + latest review + bounded recent revision pairs
  enforce a byte/token/revision limit with an explicit truncation marker
  retain all older material only in the durable GitHub journal
```

### Detailed Steps

1. Separate the durable store from the agent view. Keep every revision, review, and diff in GitHub comments if that is the audit contract. Do not equate "durably retained" with "must be passed to every agent." Construct a pure `agent_history_view` with an explicit maximum revision count and byte or token budget.

2. Make the bounded view deterministic and useful. Include the current complete plan, the latest complete review, and as many newest prior revision pairs as fit. Prefer an indexed summary or a clear omission marker for older revisions. Do not silently truncate the current plan or latest actionable review. Ensure the same journal produces the same prompt projection on retry.

3. Detect no progress before durable archive/upsert. Normalize content before comparison so generated comment markers and revision metadata cannot make identical plans appear different. Compare the candidate with the immediately prior plan and, where cycle repetition matters, with a stable content digest for prior revisions.

4. Turn no progress into a terminal blocked transition. Preserve or publish the reviewer reason, then atomically add `state:plan-blocked` and remove competing plan-state labels. Return the blocked outcome immediately. Do not archive a meaningless "no textual changes" revision, increment a revision number, or enqueue another planner/reviewer job.

5. Keep explicit reviewer `BLOCKED` separate but equivalent in terminal effect. A reviewer can ask for external information directly; an unchanged/repeated amendment is an independent pipeline-observed signal that further automated work cannot improve the artifact. Both must be visible to an operator and leave the state machine in a durable, restart-safe blocked state.

6. Add behavior-first tests before implementation:
   - an oversized multi-revision journal retains the current plan/latest review, respects the exact bound, and emits the truncation marker;
   - a retry of the same journal produces the identical bounded projection;
   - an identical amendment produces `state:plan-blocked`, does not create a new archive/revision, and submits no further job;
   - a repeated non-adjacent plan follows the same blocked path when repeat detection is enabled;
   - a genuinely changed amendment still archives the prior pair and proceeds to review.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. `Verified Workflow` is retained only for marketplace schema compatibility; follow the proposed workflow above and require new CI evidence before treating it as established practice.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pass every durable comment to every later agent | Rendered all archived full plans, diffs, reviews, and current artifacts into each planner/reviewer prompt. | The journal grows on each revision, so prompt size, token cost, and eventual context-limit failure grow with issue age even though only recent context is actionable. | Preserve the full durable journal, but project a bounded deterministic view for agents. |
| Treat only reviewer-emitted `BLOCKED` as no progress | NOGO/AMBIGUOUS always entered amendment until the fixed budget was exhausted. | An amend job can return the same plan; the system then archived a no-textual-change diff, re-reviewed it, and eventually produced no-go/exhaustion instead of the documented blocked outcome. | Detect unchanged or repeated candidate plans at the state-machine boundary and block before archive/upsert or another job. |
| Compare raw stored comment bodies | Used durable comment text directly as the equality basis. | Revision markers or generated wrappers can make semantically identical plans compare unequal, causing a false impression of progress. | Normalize content or compare a stable semantic digest that excludes generated metadata. |
| Test only explicit reviewer blocking | Covered a reviewer returning `BLOCKED`, but not a planner returning an unchanged amendment. | The test suite could pass while the promised no-improvement behavior remained absent. | Test the observable no-progress transition, labels, absence of new jobs, and absence of a new durable revision. |

## Results & Parameters

| Item | Required contract |
|------|-------------------|
| Durable retention | Keep the complete historical plan/review journal in GitHub comments. |
| Agent context | Current plan + latest review + newest prior pairs within an explicit revision and byte/token bound. |
| Truncation | Deterministic, visible marker or index; never silent loss of the latest actionable artifacts. |
| Equality basis | Normalized plan content or stable digest excluding generated revision/comment metadata. |
| No-progress result | Preserve the reason, atomically transition to `state:plan-blocked`, stop without another agent job. |
| Required regression evidence | Bound/ordering test, deterministic retry test, identical/repeated amendment test, and changed-amendment control test. |
| Observed source evidence | ProjectHephaestus PR #2357: `_plan_history()` returned the complete archive to prompts and amendment persistence did not compare `plan_text` to `old_plan`; focused affected tests passed 437 locally. |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2357 strict review | Source review found the unbounded history and no-progress paths; two MAJOR inline review comments were posted. Focused affected tests passed locally, but no remediation exists yet, so this skill remains unverified. |
