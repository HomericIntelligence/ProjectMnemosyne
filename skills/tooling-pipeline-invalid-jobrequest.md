---
name: tooling-pipeline-invalid-jobrequest
description: "Use when: (1) encountering TypeErrors or coordinator crashes from JobRequest(None, ...); (2) trying to use JobRequest as a generic callback signal (not for job submission); (3) needing to distinguish timer-park (RETRY disposition) from job submission (JobRequest); (4) fixing legacy code that uses type: ignore to silence JobRequest(None) violations; (5) routing work without actually submitting a job to the queue."
category: tooling
date: 2026-07-05
version: "1.0.0"
user-invocable: false
history: tooling-pipeline-invalid-jobrequest.history
tags:
  - pipeline
  - jobrequest
  - anti-pattern
  - coordinator
  - type-safety
  - job-routing
  - timer-park
---
# tooling-pipeline-invalid-jobrequest

Identify and fix invalid JobRequest(None, ...) patterns in queue-based pipeline stages; use real Job objects or alternative outcome types (RETRY, Continue).

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-07-05 |
| Objective | Eliminate JobRequest(None) pattern; use real GitJob/AgentJob objects or return StageOutcome with RETRY/Continue |
| Outcome | Success — ProjectHephaestus pipeline #1816 fixed multiple JobRequest(None) calls, all tests passing, verified-ci |
| Verification | verified-ci, 479 pipeline unit tests |

## When to Use

- A stage tries to return `JobRequest(None, "some_callback_name")` with `# type: ignore`
- Coordinator crashes with "NoneType has no attribute ..." when processing a stage return value
- Code attempts to use JobRequest as a generic "signal for later callback" (not a job submission)
- Refactoring legacy stages that used placeholder JobRequest(None) to defer decisions
- Distinguishing when you need: (a) a real job submission (JobRequest), (b) a timer-park delay (RETRY disposition), or (c) immediate continuation (Continue)
- Stage logic needs to submit a job conditionally but has no fallback for the "no job" case

## Verified Workflow

### Quick Reference: The Pattern

**WRONG — Don't do this:**

```python
# Coordinator crashes when it tries to serialize/submit None
return JobRequest(None, "on_something_done")  # type: ignore
```

**RIGHT — Use one of these:**

```python
# Option 1: Real job (GitJob, AgentJob, CustomJob)
job = AgentJob(name="my-work", payload={"item": item.id})
return JobRequest(job, on_job_done="on_work_done")

# Option 2: Timer-park (delay before retry)
return StageOutcome(Disposition.RETRY, reason="delay_before_retry")

# Option 3: Continue immediately
return Continue(next_stage="next_stage", reason="no_work_needed")

# Option 4: Finish (early termination)
return StageOutcome(Disposition.FINISH_OK, reason="work_complete")
```

### Detailed Steps

#### 1. Identify JobRequest(None) Calls in Codebase

Search for the anti-pattern:

```bash
# Find all JobRequest(None) calls (with or without type: ignore)
grep -rn "JobRequest(None" hephaestus/automation/pipeline/ --include="*.py"

# Find type: ignore lines near JobRequest to catch hidden violations
grep -rn "type: ignore" hephaestus/automation/pipeline/ --include="*.py" \
  | grep -B2 "JobRequest"
```

**Example findings:**

```python
# File: hephaestus/automation/pipeline/ci_drive_green_stage.py
return JobRequest(None, "on_ci_result")  # type: ignore  ← WRONG
```

#### 2. Understand Why JobRequest(None) Fails

JobRequest is designed to submit a job to the job queue:

```python
class JobRequest:
    """Request the coordinator to submit a job and await its completion."""

    def __init__(self, job: Job, on_job_done: str):
        self.job = job  # ← Expects a real Job object, not None
        self.on_job_done = on_job_done
```

When coordinator processes the return value:

```python
if isinstance(result, JobRequest):
    # Serialize the job to JSON/protocol buffer for submission
    job_payload = result.job.to_dict()  # ← Crashes if job is None
    queue.submit(job_payload)
```

**Error message:**

```
AttributeError: 'NoneType' object has no attribute 'to_dict'
```

#### 3. Determine What You Actually Need

Ask yourself: "What is the intent of this stage?"

| Intent | Code | Reason |
| -------- | -------- | -------- |
| Submit work and await callback | `JobRequest(real_job, "on_done")` | Coordinator submits job, calls `on_done` on completion |
| Wait and retry the same stage | `StageOutcome(Disposition.RETRY, ...)` | Coordinator parks item, re-invokes stage after timer |
| Move to next stage immediately | `Continue(next_stage="...", ...)` | No job, no wait; state advances |
| Terminate successfully | `StageOutcome(Disposition.FINISH_OK, ...)` | No job, work item complete, no further processing |
| Terminate with failure | `StageOutcome(Disposition.FINISH_FAIL, ...)` | No job, retry from clean state on next cycle |

#### 4. Replace JobRequest(None) with Real Job

**Pattern: Conditional job submission**

```python
# WRONG
async def stage_maybe_do_work(item, ctx):
    if item.needs_work():
        job = AgentJob(name="do-work", payload={"item": item.id})
        return JobRequest(job, "on_work_done")
    else:
        return JobRequest(None, "on_skipped")  # type: ignore  ← WRONG

# RIGHT
async def stage_maybe_do_work(item, ctx):
    if item.needs_work():
        job = AgentJob(name="do-work", payload={"item": item.id})
        return JobRequest(job, "on_work_done")
    else:
        # No job needed; continue to next stage
        return Continue(next_stage="next_stage", reason="no_work_needed")
```

#### 5. Replace JobRequest(None) with RETRY (Timer-Park)

**Pattern: Delay before retry**

```python
# WRONG
async def stage_wait_for_condition(item, ctx):
    if condition_not_met:
        # Want to wait and retry, but using fake JobRequest
        return JobRequest(None, "on_retry")  # type: ignore  ← WRONG

# RIGHT
async def stage_wait_for_condition(item, ctx):
    if condition_not_met:
        # Return RETRY to park with timer
        return StageOutcome(
            Disposition.RETRY,
            reason="condition_not_met_retry_in_30s"
        )
        # Coordinator will: park item, wait 30s, re-invoke this stage
```

#### 6. Replace JobRequest(None) with Continue

**Pattern: Proceed without waiting or work**

```python
# WRONG
async def stage_classify_and_route(item, ctx):
    classification = ctx.classify(item)
    if classification == TERMINAL:
        # Route is decided; no job needed
        return JobRequest(None, "on_classified")  # type: ignore  ← WRONG

# RIGHT
async def stage_classify_and_route(item, ctx):
    classification = ctx.classify(item)
    if classification == TERMINAL:
        # Continue to terminal stage
        return Continue(next_stage="terminal_stage", reason="classification_done")
        # Coordinator will: state advances, next_stage is invoked
```

#### 7. Audit on_job_done Callbacks for Unused Jobless Paths

If a stage has an `on_job_done` callback that was paired with `JobRequest(None)`, the callback may never be invoked:

```python
async def on_work_done(self, item, job_result, ctx):
    # This callback was registered with JobRequest(None, "on_work_done")
    # The coordinator never calls it because no job was submitted!
    # This code is dead.
    pass
```

**Fix:** Remove the dead callback or route the logic into the main stage function:

```python
# BEFORE (with JobRequest(None))
async def stage_foo(item, ctx):
    return JobRequest(None, "on_result")  # type: ignore

async def on_result(self, item, job_result, ctx):
    # Dead code; never invoked
    pass

# AFTER (logic moved to stage)
async def stage_foo(item, ctx):
    # Decision logic that was in on_result callback now here
    decision = make_decision(item, ctx)
    return Continue(next_stage=decision.next_stage)

# Callback removed or used for actual jobs
async def on_result(self, item, job_result, ctx):
    # Only invoked when there's a real JobRequest(real_job, ...)
    pass
```

#### 8. Test the Fix

Use hypothesis to generate stage transitions and verify no JobRequest(None) patterns:

```python
import ast
import pytest

def test_no_jobrequest_none_in_stages():
    """Fail if any stage uses JobRequest(None)."""
    import hephaestus.automation.pipeline as pipeline_module

    source = inspect.getsource(pipeline_module)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for JobRequest calls
            if isinstance(node.func, ast.Name) and node.func.id == "JobRequest":
                # First arg should not be a Constant with value None
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and first_arg.value is None:
                        raise AssertionError(
                            f"Found JobRequest(None, ...) at line {node.lineno}"
                        )

@pytest.mark.asyncio
async def test_stage_no_job_returns_continue():
    """Stage with no job needed should return Continue, not JobRequest(None)."""
    item = WorkItem(id=1)
    ctx = AsyncMock()
    ctx.classify.return_value = Classification.TERMINAL

    result = await stage_classify_and_route(item, ctx)

    # Verify: not JobRequest(None)
    assert not isinstance(result, JobRequest)
    assert isinstance(result, Continue)
    assert result.next_stage == "terminal_stage"
```

### Common Replacement Patterns

| Original (WRONG) | Replacement (RIGHT) | Use Case |
| -------- | -------- | -------- |
| `JobRequest(None, "on_done")` | `Continue(next_stage="...")` | Immediate proceed; no wait or work |
| `JobRequest(None, "on_retry")` | `StageOutcome(Disposition.RETRY, ...)` | Timer-park; retry same stage after delay |
| `JobRequest(None, "on_finish")` | `StageOutcome(Disposition.FINISH_OK, ...)` | Complete work item; no further processing |
| `JobRequest(None, "on_classify")` | Decision logic in main stage → return Continue | Classification is instant; route immediately |
| `JobRequest(None, ...)` + dead callback | Remove callback; logic moves to stage | Callback was never invoked |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use `type: ignore` to silence the error | `JobRequest(None, "on_done")  # type: ignore` | Hides the underlying contract violation; coordinator still crashes at runtime (type checker says OK, runtime crashes) | Don't silence contract violations with comments; fix the underlying call site |
| Assume coordinator will handle None gracefully | `JobRequest(None)` without error handling | Coordinator serializes to JSON: `None.to_dict()` crashes; no graceful degradation | JobRequest contract requires a real Job object; coordinator doesn't special-case None |
| Use conditional job variable | `job = real_job if x else None; JobRequest(job, ...)` | Same issue: job is None, coordinator crashes | Check the condition BEFORE calling JobRequest; use different return types for different branches |
| Defer decision to on_job_done callback | `JobRequest(None); on_job_done does decision` | Callback never invoked; no job submitted means no callback trigger | Decision logic must be in stage function before JobRequest, not deferred to callback |
| Add special handling in coordinator for None jobs | Modify coordinator to check `if job is None: skip_submission()` | Defeats the purpose of JobRequest (job submission contract); introduces hidden control flow | Don't extend JobRequest semantics; use appropriate return types (Continue, RETRY, etc.) |

## Results & Parameters

**Replacement rules:**

1. JobRequest always takes a real Job object (GitJob, AgentJob, CustomJob)
2. If you don't need a job, use Continue, StageOutcome with RETRY, or FINISH_*
3. If you're conditionally submitting, use an if statement, not JobRequest(None)
4. If you want a timer-park delay, use Disposition.RETRY, not JobRequest(None)
5. If decision logic belongs in on_job_done, move it to the main stage function instead

**Testing strategy:**

- Static analysis: AST scan for JobRequest(None) patterns
- Runtime: type hints (job: Job not job: Optional[Job])
- Unit tests: verify stages never return JobRequest with None

**Verification:**

ProjectHephaestus pipeline #1816:
- 5+ JobRequest(None) calls identified and replaced
- All stages use real JobRequest or Continue/RETRY/FINISH_*
- 479 unit tests (all passing)
- verified-ci (full suite)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Pipeline epic #1809, sub-issue #1816 (ci-drive-green stage), 479 tests | Fixed multiple JobRequest(None) anti-patterns; replaced with real jobs, Continue, or RETRY disposition |
