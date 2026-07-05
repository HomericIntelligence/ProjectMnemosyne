---
name: architecture-pipeline-stage-implementation
description: "Use when: (1) implementing queue-based pipeline stages with state machine semantics (Continue/JobRequest/StageOutcome); (2) delegating pure classifiers to pipeline stages via context accessors; (3) routing jobs via on_job_done payload flags while avoiding state mutations; (4) distinguishing timer-park (RETRY disposition) from job submission (JobRequest); (5) managing job completion routing that doesn't mutate item.state (coordinator clobber risk); (6) implementing durable mutations (e.g., arming records, dedupe markers) that must occur before state advances."
category: architecture
date: 2026-07-05
version: "1.0.0"
user-invocable: false
history: architecture-pipeline-stage-implementation.history
tags:
  - pipeline
  - stage
  - state-machine
  - coordinator
  - job-routing
  - durable-mutations
  - timer-park
  - queue-automation
  - classifiers
---
# architecture-pipeline-stage-implementation

Implement queue-based pipeline stages with state machine semantics, pure classifiers, job routing avoiding state mutation, and durable pre-advance mutations.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-07-05 |
| Objective | Establish patterns for pipeline stage implementation using Continue/JobRequest/StageOutcome, delegated pure classifiers, job routing via payload flags, and durable state before advance |
| Outcome | Success — ProjectHephaestus pipeline stages (ci-drive-green, merge-wait) implemented with 479 unit tests passing, verified-ci |
| Verification | verified-ci, 479 pipeline unit tests |

## When to Use

- Implementing a pipeline stage that must classify work items and route them to different jobs or outcomes
- Extracting pure classifiers from legacy code (not coupled to item.state mutations) for use in pipeline stages
- Routing completed jobs back to the pipeline (on_job_done) using payload flags instead of direct state writes
- Implementing timer-park semantics where a stage should delay before retrying (RETRY disposition, not JobRequest)
- Managing durable state (arming records, dedupe markers) that must be written before state advances
- Ensuring crash-safety: if a job completes but the arming record write fails, the stage must retry, not continue with a dangling armed state
- Distinguishing when to return Continue (no job needed), JobRequest (submit a new job), or StageOutcome with RETRY (park and delay)

## Verified Workflow

### Quick Reference: Stage Structure

A pipeline stage is a callable that:
1. **Receives** a WorkItem and a context (state accessor, classifier accessors, durable mutations)
2. **Decides** (via classifiers) which job to submit, if any, or whether to continue/retry
3. **Mutates durably** before state change (arming records, dedupe markers)
4. **Returns** Continue, JobRequest, or StageOutcome with one of: Disposition.FINISH_OK, Disposition.FINISH_FAIL, Disposition.RETRY

```python
async def stage_ci_drive_green(
    item: WorkItem,
    ctx: StageContext,
) -> Continue | JobRequest | StageOutcome:
    # 1. Classify using pure classifier from context
    ci_state = ctx.classify_ci_state(item)

    # 2. Route based on classification
    if ci_state == CIState.GREEN:
        # Durable mutation BEFORE state change
        await ctx.arm_auto_merge(item.pr_number)
        return Continue(next_stage="merge-wait", reason="ci_green_armed")

    if ci_state == CIState.RED:
        # Durable mutation if needed
        await ctx.record_ci_failure(item.pr_number, ci_state)
        return StageOutcome(Disposition.RETRY, reason="ci_red_retry")

    # 3. Submit job if work needed
    job = AgentJob(
        name="drive-green",
        payload={"pr_number": item.pr_number},
    )
    return JobRequest(job, on_job_done="on_drive_green_done")
```

### Detailed Steps

#### 1. Extract Pure Classifiers from Legacy Code

Pure classifiers are functions that:
- Take a WorkItem and return a classification (enum, bool, or structured result)
- Do NOT mutate item.state or any global state
- Are deterministic (same input → same output)

**Example: Extract from legacy code**

```python
# Legacy code (DO NOT USE in stages — couples state mutation to classification)
def legacy_classify_and_advance(item):
    state = fetch_external_state(item.pr_number)
    if state.ci_passed:
        item.state = "merge_ready"  # BAD: direct state mutation
        return True
    item.state = "ci_fixing"  # BAD: direct state mutation
    return False

# Pure classifier extraction
def classify_ci_state(item: WorkItem) -> CIState:
    """Pure classifier: no side effects, no item.state writes."""
    state = fetch_external_state(item.pr_number)
    if state.ci_passed and state.all_checks_green:
        return CIState.GREEN
    if state.ci_passed and state.has_warnings:
        return CIState.GREEN_WITH_WARNINGS
    return CIState.RED

# Make it accessible via context
class StageContext:
    def classify_ci_state(self, item: WorkItem) -> CIState:
        return classify_ci_state(item)
```

**Benefit:** The classifier is testable in isolation, reusable across stages, and doesn't require mocking item.state mutations.

#### 2. Implement Job Routing via on_job_done Callback

When a job completes, the coordinator calls the stage's `on_job_done` handler. Use this to route the completed job's result WITHOUT mutating item.state directly (the coordinator will clobber it).

**Pattern:**

```python
async def stage_ci_drive_green(
    item: WorkItem,
    ctx: StageContext,
) -> Continue | JobRequest | StageOutcome:
    job = AgentJob(
        name="drive-green-agent",
        payload={"pr_number": item.pr_number, "branch": item.branch},
    )
    return JobRequest(
        job,
        on_job_done="on_drive_green_done",  # ← Callback name
    )

# In the stage class:
async def on_drive_green_done(
    self,
    item: WorkItem,
    job_result: JobResult,
    ctx: StageContext,
) -> Continue | JobRequest | StageOutcome:
    """Invoked by coordinator when job completes."""
    if job_result.success:
        # Job succeeded: drive-green completed
        # Durable mutation BEFORE state advance
        await ctx.arm_auto_merge(item.pr_number)
        return Continue(next_stage="merge-wait")
    else:
        # Job failed: retry with timer-park
        return StageOutcome(Disposition.RETRY, reason="drive_green_failed")
```

**Why not item.state = "armed"?** The coordinator is the sole writer of item.state; a stage writing directly causes race conditions and lost updates. Use `on_job_done` to signal the next stage or outcome to the coordinator.

#### 3. Distinguish RETRY Disposition from JobRequest

Two different patterns for different semantics:

- **RETRY disposition**: Park the item, wait before retrying the SAME stage (timer-park semantics)
- **JobRequest**: Submit a NEW job immediately, await its completion

```python
# Pattern 1: Timer-park (use RETRY)
async def stage_with_delay(item, ctx):
    """Wait before retrying the stage."""
    # No new job needed; just delay and retry.
    return StageOutcome(Disposition.RETRY, reason="delay_before_retry")

# Pattern 2: Submit job (use JobRequest)
async def stage_with_agent_work(item, ctx):
    """Have an agent do work, then call on_job_done."""
    job = AgentJob(name="my-agent", payload={"item": item.id})
    return JobRequest(job, on_job_done="on_agent_done")
```

**In coordinator logic:**
- RETRY: Coordinator parks item in a retry queue with a timer; after timeout, re-invokes the same stage
- JobRequest: Coordinator submits the job, awaits completion, calls `on_job_done` in the same stage

#### 4. Implement Durable Mutations BEFORE State Change

A durable mutation is any write to persistent state (database, durable queue, file system) that must NOT be lost if the process crashes.

**Rule:** Write durable state BEFORE returning Continue/JobRequest/StageOutcome. If the write fails, return FINISH_FAIL to force retry from a clean state.

```python
async def stage_arm_auto_merge(item, ctx) -> Continue | StageOutcome:
    """Arm the PR for auto-merge. Durable arming record must be written before continue."""

    # Classify to decide if we should arm
    merge_state = ctx.classify_pr_merge_state(item)
    if merge_state != MergeState.READY:
        return Continue(next_stage="wait-merge", reason="not_ready")

    try:
        # Step 1: Write durable arming record to database
        arming_record = await ctx.create_arming_record(
            pr_number=item.pr_number,
            armed_at=ctx.now(),
            auto_merge_enabled=True,
        )

        # Step 2: Enable auto-merge on the PR (API call)
        await ctx.enable_auto_merge(item.pr_number)

        # Step 3: Update arming record (optional, for audit trail)
        await ctx.update_arming_record(arming_record.id, status="api_called")

    except Exception as e:
        # Durable write failed: return FINISH_FAIL to force retry
        # The PR is NOT armed (no arming record), so the retry is safe
        return StageOutcome(Disposition.FINISH_FAIL, reason=f"arm_record_failed: {e}")

    # Success: state advances to next stage
    return Continue(next_stage="merge-wait", reason="auto_merge_armed")
```

**Why this matters:** If the process crashes between "enable_auto_merge" (step 2) and "create_arming_record" (step 1), the PR is armed but no dedupe record exists. On restart, the stage might re-arm the PR (duplicate API calls, race conditions). By doing durable writes FIRST, a crash leaves the state consistent.

#### 5. Avoid JobRequest(None) — Use Real Jobs or RETRY Disposition

**WRONG:** Trying to use `JobRequest(None, ...)` as a way to signal "no job but want a callback":

```python
# WRONG — coordinator crashes on None
return JobRequest(None, "on_something_done")  # type: ignore
```

**RIGHT:** Use one of:

```python
# Option 1: Return Continue if no job and no delay needed
return Continue(next_stage="next_stage")

# Option 2: Return RETRY if you want timer-park (delay then retry)
return StageOutcome(Disposition.RETRY, reason="delay_before_retry")

# Option 3: Submit a real job (GitJob, AgentJob, or custom)
job = AgentJob(name="work", payload={...})
return JobRequest(job, on_job_done="on_done")
```

**Reason:** JobRequest's job parameter is always instantiated and submitted to the job queue. If you pass None, the coordinator receives a None job and crashes when trying to serialize/queue it.

#### 6. Test Stage Classification and Routing

Use pure classifiers to make stages testable without mocking external state:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_stage_ci_green_routes_to_merge_wait():
    """Test that CI-green classification routes to merge-wait stage."""
    item = WorkItem(pr_number=123, state="drive_green")

    # Mock the context classifier
    ctx = AsyncMock()
    ctx.classify_ci_state.return_value = CIState.GREEN
    ctx.arm_auto_merge = AsyncMock()

    # Invoke stage
    result = await stage_ci_drive_green(item, ctx)

    # Assert: Continue to merge-wait
    assert isinstance(result, Continue)
    assert result.next_stage == "merge-wait"
    assert result.reason == "ci_green_armed"

    # Assert: Durable mutation was called
    ctx.arm_auto_merge.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_stage_ci_red_retries_with_delay():
    """Test that CI-red returns RETRY disposition."""
    item = WorkItem(pr_number=123, state="drive_green")

    ctx = AsyncMock()
    ctx.classify_ci_state.return_value = CIState.RED

    result = await stage_ci_drive_green(item, ctx)

    assert isinstance(result, StageOutcome)
    assert result.disposition == Disposition.RETRY
    assert result.reason == "ci_red_retry"
```

### Architecture Diagram

```
Pipeline Coordinator (sole state writer)
    │
    ├── Invokes Stage (e.g., stage_ci_drive_green)
    │   ├── Classifier (pure, no side effects)
    │   │   └── Returns CIState (GREEN, RED, etc.)
    │   └── Router (decision logic)
    │       ├── If GREEN → Durable mutation (arm_auto_merge) → Continue
    │       ├── If RED → Return RETRY (timer-park)
    │       └── If UNKNOWN → Submit JobRequest → await on_job_done
    │
    ├── Receives stage return value
    │   ├── Continue → State advances to next stage
    │   ├── RETRY → Item parked in retry queue, timer set
    │   ├── FINISH_OK → Work item completes
    │   ├── FINISH_FAIL → Work item retried from clean state
    │   └── JobRequest → Job submitted, on_job_done callback registered
    │
    └── On job completion → Invokes on_job_done callback → Return outcome → Update state
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Mutate item.state directly in stage | `item.state = "armed"` after enabling auto-merge | Coordinator is the sole state writer; if stage and coordinator both write, coordinator's write clobbers the stage's mutation (lost update) | Delegate state changes to coordinator via return value (Continue with next_stage) or on_job_done callback |
| Use JobRequest(None) for "no job but want callback" | `JobRequest(None, "on_done")` with type ignore | Coordinator crashes when trying to serialize/queue a None job (violates constructor contract) | Use real Job objects or return RETRY/Continue; never pass None to JobRequest |
| Defer durable writes until after state change | `return Continue(...); await write_arming_record()` | Crash between return and write leaves PR armed but no dedupe record; restart re-arms the PR (duplicate work) | Write durable state BEFORE returning; if write fails, return FINISH_FAIL to force clean retry |
| Exception handling swallows durable write failures | `try: await create_arming_record() except: pass; return Continue()` | Exception logged but stage continues with armed PR and no dedupe record (violates AC3 requirement for durable dedupe) | Propagate durable write failures as FINISH_FAIL; force the coordinator to retry the stage from scratch |
| Use same stage function for initial and on_job_done paths | Single function handles both "first call" and "job done" cases without branching | Logic branching became unclear; hard to test "did job get submitted?" vs "does callback know result?" | Use separate functions: stage_foo (initial) and on_job_done handler (callback); or use a clear if-job-exists branch |
| Extract classifier as a method on item | `item.classify_ci_state()` | Couples classifier to item schema; harder to test; classifier can't access external context (e.g., GH API state) | Classifier as a free function taking item + context; context provides accessors (fetch GH state, etc.) |

## Results & Parameters

**Core patterns:**

1. Pure classifiers (enum returns, no side effects) extracted from legacy code
2. Job routing via on_job_done callback (not direct item.state mutation)
3. Timer-park: RETRY disposition for delay-before-retry
4. Durable mutations BEFORE state advances (arming records, dedupe markers)
5. Exception handling: propagate durable-write failures as FINISH_FAIL
6. JobRequest: always with a real Job object, never None

**Testing approach:**

- Unit test classifier in isolation (pure function)
- Unit test stage routing with mocked classifier
- Integration test end-to-end pipeline with durable store (in-memory or test DB)
- Property-based tests for state machine transitions (Continue→next_stage, RETRY timing, etc.)

**Verification:**

ProjectHephaestus pipeline stages (ci-drive-green, merge-wait):
- 479 unit tests (all passing)
- Stage logic verified with classified inputs (GREEN, RED, UNKNOWN)
- Durable arming records tested for crash-safety
- on_job_done callbacks tested for job completion routing
- verified-ci (full CI suite passing)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Pipeline epic #1809, stages ci-drive-green (issue #1816) and merge-wait (issue #1817), 479 tests passing | Implemented pure classifiers, job routing via on_job_done, timer-park (RETRY) semantics, durable arming records with crash-safety |
