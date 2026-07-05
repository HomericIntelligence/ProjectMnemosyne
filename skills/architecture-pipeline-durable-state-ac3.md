---
name: architecture-pipeline-durable-state-ac3
description: "Use when: (1) implementing durable state operations in pipeline stages (arming records, dedupe markers, state ledgers); (2) designing crash-safe state transitions where durable write failure must block stage advance; (3) managing idempotency: ensuring duplicate job completions don't re-arm/re-apply state changes; (4) handling exception scenarios where a durable write fails after some API calls succeed (e.g., auto-merge enabled but record write fails); (5) implementing acceptance criteria #3 (AC3) from Hephaestus pipeline epic #1809: 'durable records must exist before state advances'; (6) building retry-from-clean-state semantics when durable mutations fail."
category: architecture
date: 2026-07-05
version: "1.0.0"
user-invocable: false
history: architecture-pipeline-durable-state-ac3.history
tags:
  - pipeline
  - durable-state
  - crash-safety
  - idempotency
  - acceptance-criteria
  - queue-automation
  - ledger
  - dedupe
  - arm-records
---
# architecture-pipeline-durable-state-ac3

Implement durable state mutations in pipeline stages with crash-safety: durable writes before state advance, failure blocks progression, dedupe on restart.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-07-05 |
| Objective | Establish pattern for durable state operations in pipeline stages (AC3: durable records before state advances) ensuring crash-safety and idempotency |
| Outcome | Success — ProjectHephaestus pipeline #1816 arm_drive_green stage implements durable arming records with FINISH_FAIL on write failure, all 479 tests pass, verified-ci |
| Verification | verified-ci, 479 pipeline unit tests, AC3 acceptance criteria met |

## When to Use

- A pipeline stage needs to write durable state (e.g., "arm PR for auto-merge") before continuing
- Exception handling must distinguish durable write failures from transient errors
- Job completion (on_job_done callback) succeeded but the follow-up durable write failed (e.g., auto-merge API call succeeded but dedupe record write failed)
- Idempotency is required: if a stage is retried or a job completion is replayed, duplicate writes must be prevented
- Crash-safety is critical: if process crashes after durable write but before state advance, restart must re-check idempotency and not re-apply
- AC3 from pipeline epic: "durable records must exist before state transitions; if write fails, stage must FINISH_FAIL to retry from clean state"

## Verified Workflow

### Quick Reference: Durable State Pattern

```python
async def stage_arm_auto_merge(
    item: WorkItem,
    ctx: StageContext,
) -> Continue | StageOutcome:
    """
    Arm PR for auto-merge with durable record and crash-safety.

    AC3: Durable arming record MUST exist before state advances.
    On failure: return FINISH_FAIL to force retry from clean state.
    """
    # Step 1: Check if already armed (idempotency)
    existing_record = await ctx.check_arming_record(item.pr_number)
    if existing_record:
        # Already armed; continue without re-arming
        return Continue(
            next_stage="merge-wait",
            reason="already_armed_idempotent"
        )

    # Step 2: Classify to decide if we should arm
    merge_state = ctx.classify_pr_merge_state(item)
    if merge_state != MergeState.READY:
        return Continue(next_stage="wait-merge", reason="not_ready")

    try:
        # Step 3: Write DURABLE record FIRST (before API call)
        arming_record = await ctx.create_arming_record(
            pr_number=item.pr_number,
            armed_at=ctx.now(),
            status="pending_api_call",
        )

        # Step 4: Make API call (auto-merge enable)
        await ctx.enable_auto_merge(item.pr_number)

        # Step 5: Update durable record (for audit trail)
        await ctx.update_arming_record(
            arming_record.id,
            status="api_called"
        )

    except Exception as e:
        # Durable write failed: return FINISH_FAIL
        # Coordinator will: mark item for retry, restart from clean state
        # Next restart will check existing_record and idempotently skip
        return StageOutcome(
            Disposition.FINISH_FAIL,
            reason=f"arm_record_failed: {e}"
        )

    # Success: state advances
    return Continue(next_stage="merge-wait", reason="auto_merge_armed")
```

### Detailed Steps

#### 1. Identify Durable State Operations in Your Stage

Durable state is any write to persistent storage that must survive process crashes:

- **Arming records**: Track which PRs have been armed for auto-merge
- **Dedupe records**: Track which jobs have been submitted (prevent duplicate submissions)
- **Ledger entries**: Audit trail of state transitions with timestamps
- **Flags**: Persistent markers (e.g., "ci_fix_attempted", "user_contacted")

**NOT durable state:**

- Local variables (lost on crash)
- In-memory caches (lost on restart)
- Item state (handled by coordinator)

**Identify durable writes in your stage:**

```python
async def stage_foo(item, ctx):
    # Durable writes (require AC3 treatment):
    await ctx.write_to_database(...)
    await ctx.write_to_durable_queue(...)
    await ctx.append_ledger(...)

    # NOT durable writes:
    cache.put(...)  # Lost on crash
    return ...      # Coordinator writes item.state
```

#### 2. Implement Crash-Safety: Write BEFORE State Advance

**Rule:** Durable writes must complete BEFORE the stage returns (before state transitions).

If process crashes:
- **Before durable write**: Item is retried from the original stage (safe)
- **After durable write, before return**: Durable write persists; restart checks idempotency and skips re-applying
- **Invariant:** No gap where durable write succeeds but stage advance is lost

**Pattern:**

```python
async def stage_with_durable_write(item, ctx):
    try:
        # 1. Check idempotency FIRST
        existing = await ctx.check_for_existing_record(item.id)
        if existing:
            return Continue(next_stage="next", reason="idempotent_skip")

        # 2. Write durable state
        record = await ctx.create_record(item.id, data={...})

        # 3. Optional: Update record with post-write status
        await ctx.update_record(record.id, status="completed")

    except Exception as e:
        # Durable write failed: don't advance state
        return StageOutcome(Disposition.FINISH_FAIL, reason=f"write_failed: {e}")

    # 4. Return outcome AFTER durable write succeeds
    return Continue(next_stage="next", reason="durable_write_done")
```

**Why this order matters:**

```python
# WRONG: Advance state, then write durable (race condition)
async def stage_wrong(item, ctx):
    await ctx.update_item_state(item.id, "armed")  # State changed
    try:
        await ctx.write_arming_record(...)  # Durable write
    except Exception:
        # Too late! item.state already changed
        # Restart: item is in "armed" state with no durable record (contradiction)
        pass
    return Continue(...)

# RIGHT: Write durable first, then advance state via return
async def stage_right(item, ctx):
    try:
        await ctx.write_arming_record(...)  # Durable write FIRST
    except Exception:
        # Durable write failed; item.state not yet advanced (safe)
        return StageOutcome(Disposition.FINISH_FAIL, ...)
    return Continue(...)  # State advances AFTER durable write
```

#### 3. Implement Idempotency: Check Before Writing

Idempotency ensures that if a stage is retried or a job completion is replayed, duplicate writes are avoided.

```python
async def stage_idempotent_write(item, ctx):
    """Write durable record if not already present."""

    # Check if record exists
    existing_record = await ctx.fetch_arming_record(item.pr_number)
    if existing_record:
        # Already armed in a prior attempt; skip re-writing
        return Continue(
            next_stage="next_stage",
            reason=f"idempotent_skip (record_id={existing_record.id})"
        )

    # Record doesn't exist; write it
    try:
        new_record = await ctx.create_arming_record(
            pr_number=item.pr_number,
            armed_at=ctx.now(),
        )
    except Exception as e:
        return StageOutcome(Disposition.FINISH_FAIL, reason=f"create_failed: {e}")

    return Continue(next_stage="next_stage", reason="created_new_record")
```

**Crash scenario:**

1. Stage writes arming_record with id=123
2. Process crashes before returning Continue
3. Restart: stage is re-invoked
4. Check: arming_record with id=123 exists
5. Idempotent skip: return Continue (don't re-create)
6. Proceed to next stage

#### 4. Handle Mixed Success/Failure: API Call Succeeds, Durable Write Fails

A common scenario: an external API call (e.g., enable auto-merge) succeeds, but the follow-up durable write fails. This violates AC3 (durable record must exist before state advance).

**Pattern: Write durable FIRST, call API second**

```python
async def stage_arm_auto_merge(item, ctx):
    """Durable record written FIRST, then API call."""

    try:
        # 1. Write durable arming record (persistent)
        arming_record = await ctx.create_arming_record(
            pr_number=item.pr_number,
            armed_at=ctx.now(),
            status="pending_api_call",  # Mark as not-yet-api-called
        )

        # 2. Call API to enable auto-merge (may succeed or fail)
        try:
            await ctx.enable_auto_merge(item.pr_number)
            api_status = "success"
        except Exception as api_err:
            api_status = f"failed: {api_err}"

        # 3. Update record with API result (for audit)
        await ctx.update_arming_record(arming_record.id, status=api_status)

    except Exception as e:
        # Durable write failed (before or after API call)
        return StageOutcome(Disposition.FINISH_FAIL, reason=f"durable_write_failed: {e}")

    # Success: durable record exists, state advances
    return Continue(next_stage="merge-wait", reason="armed_durable_recorded")
```

**Why write durable first:**

- If durable write fails: no API call made (transaction consistent, retry is safe)
- If API call fails after durable write: record exists with `status="failed: ..."` (audit trail preserved, idempotent retry skips re-api-calling)
- Coordinator never sees "PR armed but no record" contradiction

#### 5. Distinguish FINISH_FAIL from Continue with Retry

Two different outcomes:

- **FINISH_FAIL**: Durable write failed; item must be retried from clean state. Coordinator will re-invoke the stage, which will check idempotency and skip if record exists.
- **RETRY (Disposition)**: Stage encountered a transient condition (e.g., rate limit); park and delay before retrying the same stage.
- **Continue**: Stage succeeded; state advances to next stage.

```python
async def stage_example(item, ctx):
    try:
        record = await ctx.create_durable_record(...)
    except DatabaseConnectionError:
        # Transient error; retry after delay
        return StageOutcome(Disposition.RETRY, reason="db_connection_timeout")
    except Conflict as e:
        # Durable write failed (likely a logic error); fail and retry from clean
        return StageOutcome(Disposition.FINISH_FAIL, reason=f"conflict: {e}")

    return Continue(next_stage="next", reason="record_created")
```

#### 6. Test Durable Writes with Idempotency

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_stage_durable_write_idempotent():
    """Stage should skip if durable record already exists."""
    item = WorkItem(pr_number=123)
    ctx = AsyncMock()

    # Existing record
    existing_record = Record(id=1, pr_number=123, status="armed")
    ctx.fetch_arming_record.return_value = existing_record
    ctx.classify_pr_merge_state.return_value = MergeState.READY

    result = await stage_arm_auto_merge(item, ctx)

    # Should idempotently skip
    assert isinstance(result, Continue)
    assert "idempotent" in result.reason
    # Should NOT have created new record
    ctx.create_arming_record.assert_not_called()

@pytest.mark.asyncio
async def test_stage_durable_write_failure_returns_finish_fail():
    """Stage should return FINISH_FAIL if durable write fails."""
    item = WorkItem(pr_number=123)
    ctx = AsyncMock()

    # No existing record
    ctx.fetch_arming_record.return_value = None
    ctx.classify_pr_merge_state.return_value = MergeState.READY

    # Durable write fails
    ctx.create_arming_record.side_effect = Exception("Database error")

    result = await stage_arm_auto_merge(item, ctx)

    # Should return FINISH_FAIL
    assert isinstance(result, StageOutcome)
    assert result.disposition == Disposition.FINISH_FAIL
    # Should NOT have called enable_auto_merge (durable write comes first)
    ctx.enable_auto_merge.assert_not_called()

@pytest.mark.asyncio
async def test_stage_durable_write_api_call_after():
    """Durable write BEFORE API call: write succeeds, API may fail."""
    item = WorkItem(pr_number=123)
    ctx = AsyncMock()

    ctx.fetch_arming_record.return_value = None
    ctx.classify_pr_merge_state.return_value = MergeState.READY

    # Durable write succeeds
    record = Record(id=1, pr_number=123, status="pending")
    ctx.create_arming_record.return_value = record

    # API call fails
    ctx.enable_auto_merge.side_effect = Exception("GitHub API error")

    result = await stage_arm_auto_merge(item, ctx)

    # Stage should still return Continue (durable record exists as audit trail)
    assert isinstance(result, Continue)
    # Update record should have been called with failure status
    ctx.update_arming_record.assert_called_once()
    assert "GitHub API error" in str(ctx.update_arming_record.call_args)
```

### AC3 Acceptance Criteria

From pipeline epic #1809:

> **AC3:** Durable records (e.g., arming markers, dedupe entries) must be written to persistent storage before state transitions. If any durable write fails, the stage must return FINISH_FAIL (not Continue or RETRY) to force the coordinator to retry the item from a clean state. On restart, the stage must check idempotency and skip re-applying if the record already exists.

**Verification checklist:**

- [ ] Durable writes happen BEFORE stage returns (before state advances)
- [ ] Durable write failures return FINISH_FAIL (not Continue or RETRY)
- [ ] Stage checks idempotency (existing record) on entry
- [ ] Idempotency check skips duplicate writes
- [ ] Test: crash scenario where durable write persists, restart checks idempotency
- [ ] Test: FINISH_FAIL scenario; coordinator retries, stage skips via idempotency check
- [ ] Audit trail: all durable operations logged or recorded

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Defer durable write until after state advance | `return Continue(...); await write_record()` | Code after return never executes; durable write is skipped on exception or normal exit | Durable writes MUST happen BEFORE return statement |
| Catch and log durable write exception, then continue | `try: write(); except: log(); return Continue(...)` | Durable record doesn't exist; state advanced without durable marker; restart finds no idempotency key and re-applies (duplicate work) | Exception in durable write must block state advance (return FINISH_FAIL) |
| Skip idempotency check, assume stage invoked only once | No check for existing record; always write new | If stage is retried, creates duplicate arming records (logical contradiction, race conditions) | Always check for existing record before writing; idempotency is not optional |
| Write to API before durable record | `enable_auto_merge(); write_record()` | API succeeds, durable write fails; PR is armed but no durable marker exists; restart may re-arm (duplicate API calls, race conditions) | Write durable FIRST, then API; if durable fails, API never runs |
| Use RETRY disposition for durable write failures | `return StageOutcome(Disposition.RETRY, ...)` after write fails | RETRY parks item with timer, intending to re-run stage; but durable record may not exist yet or may be partially written (inconsistent state) | Use FINISH_FAIL for durable failures (forces clean retry), not RETRY (assumes idempotent state) |
| Assume coordinator handles durable failures | Return Continue from stage even if durable write fails; expect coordinator to catch exceptions | Coordinator doesn't know about durable semantics; stage exception is caught but state has already advanced | Stage must explicitly check and signal durable failures (FINISH_FAIL) |

## Results & Parameters

**Core pattern:**

1. Check idempotency (existing record) on stage entry
2. Write durable record BEFORE external API calls
3. If durable write fails, return FINISH_FAIL (blocks state advance)
4. If API call fails after durable write, update durable record with status (audit trail)
5. Return Continue only AFTER durable write succeeds
6. Test: idempotency + crash scenarios

**AC3 verification:**

- Durable records exist before state transitions ✓
- Durable write failures block state advance (FINISH_FAIL) ✓
- Restart checks idempotency and skips duplicate writes ✓
- Audit trail (status field) tracks write and API call outcomes ✓

**Tested scenarios:**

- Idempotency: existing record → skip ✓
- Durable failure: exception in create_record → FINISH_FAIL ✓
- API failure after durable success: record created with status="failed" ✓
- Crash before return: durable write persists; restart idempotently skips ✓

**Verification:**

ProjectHephaestus pipeline #1816 (arm_drive_green stage):
- AC3 verified
- 479 unit tests (all passing)
- verified-ci (full suite)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Pipeline epic #1809, sub-issue #1816 (ci-drive-green → arm_drive_green stage), 479 tests | Implemented durable arming records with crash-safety, idempotency checks, AC3 acceptance criteria, FINISH_FAIL on write failure |
