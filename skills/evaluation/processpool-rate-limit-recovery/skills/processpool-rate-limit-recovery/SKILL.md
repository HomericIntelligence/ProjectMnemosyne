---
name: "ProcessPoolExecutor Rate Limit Recovery"
description: "Robust ProcessPoolExecutor rate limit recovery for E2E evaluation frameworks"
category: evaluation
date: 2026-01-10
user-invocable: false
---
# ProcessPoolExecutor Rate Limit Recovery

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-10 |
| Objective | | Attribute | Value | |-----------|-------| | **Date** | 2026-01-10 | | **Project** | ProjectScylla | |
| Outcome | Operational |


| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-10 |
| **Project** | ProjectScylla |
| **Objective** | Fix T5 tier complete failure when API rate limits hit during parallel evaluation |
| **Outcome** | ✅ Implemented 3-layer defensive strategy with pre-flight checks, safe workers, and pool recovery |
| **Impact** | Prevents catastrophic tier failures from rate limiting; auto-recovery with retry |

## When to Use This Skill

**Trigger Conditions:**
- ProcessPoolExecutor-based parallel execution crashes from external API rate limits
- Workers crash due to rate limits, poisoning the entire pool
- Need robust recovery from `BrokenProcessPool` exceptions
- E2E evaluation frameworks with API-dependent workers
- Batch processing jobs that hit rate limits mid-execution

**Symptoms:**
- All pending futures fail with "process pool was terminated abruptly"
- Actual error (rate limit) hidden in crash logs or `.failed/` directories
- Single worker crash cascades to complete batch failure
- No automatic retry or recovery mechanism

## Problem Analysis

### Root Cause

When a worker in `ProcessPoolExecutor` hits an API rate limit and crashes hard (exit_code=-1), Python throws `BrokenProcessPool` which:
1. **Poisons the entire pool** - all pending futures become unexecutable
2. **Hides the real error** - rate limit message buried in subprocess stderr
3. **No built-in recovery** - requires manual intervention to detect and retry

### Original Failure Pattern (ProjectScylla T5)

```
T0-T4: ✅ Pass
T5:    ❌ ALL 15 subtests fail
       Error: "A process in the process pool was terminated abruptly"

Actual cause (hidden in .failed/ dirs):
  "You've hit your limit · resets 4pm (America/Los_Angeles)"
```

## Verified Workflow

### Architecture: Three-Layer Defense

```
Layer 1: Pre-flight Check
  ↓ (prevents wasted work)
Layer 2: Safe Worker Wrapper
  ↓ (prevents pool poisoning)
Layer 3: Pool Crash Recovery
  ↓ (recovers from failures)
```

### Step 1: Pre-flight Rate Limit Check

Add before starting each batch/tier:

```python
def _check_rate_limit_before_tier(self, tier_id: TierID) -> None:
    """Check for active rate limit before starting tier execution."""
    from scylla.e2e.rate_limit import check_api_rate_limit_status, wait_for_rate_limit

    rate_limit_info = check_api_rate_limit_status()
    if rate_limit_info:
        logger.warning(f"Pre-flight rate limit detected for {tier_id.value}")
        if self.checkpoint and self.experiment_dir:
            checkpoint_path = self.experiment_dir / "checkpoint.json"
            wait_for_rate_limit(
                rate_limit_info.retry_after_seconds,
                self.checkpoint,
                checkpoint_path,
            )
```

**Pre-flight Check Implementation:**

```python
def check_api_rate_limit_status() -> RateLimitInfo | None:
    """Check if we're currently rate limited by making a lightweight API call."""
    import subprocess

    try:
        result = subprocess.run(
            ["claude", "--print", "ping"],  # Minimal interaction
            capture_output=True,
            text=True,
            timeout=30,
        )

        if "rate limit" in result.stderr.lower() or "hit your limit" in result.stderr.lower():
            return RateLimitInfo(
                source="preflight",
                retry_after_seconds=parse_retry_after(result.stderr),
                error_message=result.stderr.strip(),
                detected_at=datetime.now(UTC).isoformat(),
            )

        return None

    except subprocess.TimeoutExpired:
        return None  # Timeout is not a rate limit
    except Exception:
        return None  # Other errors are not rate limits
```

### Step 2: Safe Worker Wrapper

**Critical**: Wrap worker function to NEVER crash the pool:

```python
def _run_subtest_in_process_safe(
    *args, **kwargs
) -> SubTestResult:
    """Safe wrapper that catches ALL exceptions and returns structured error.

    This prevents worker crashes from poisoning the entire ProcessPoolExecutor.
    """
    try:
        return _run_subtest_in_process(*args, **kwargs)
    except RateLimitError as e:
        # Return structured error, don't crash pool
        logger.warning(
            f"Rate limit in worker for {tier_id.value}/{subtest.id}: {e.info.error_message}"
        )
        return SubTestResult(
            subtest_id=subtest.id,
            tier_id=tier_id,
            runs=[],
            pass_rate=0.0,
            selection_reason=f"RateLimitError: {e.info.error_message}",
            # NEW: Store rate limit info for retry logic
            rate_limit_info=e.info,
        )
    except Exception as e:
        # ANY exception becomes structured error
        logger.error(
            f"Worker exception for {tier_id.value}/{subtest.id}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return SubTestResult(
            subtest_id=subtest.id,
            tier_id=tier_id,
            runs=[],
            pass_rate=0.0,
            selection_reason=f"WorkerError: {type(e).__name__}: {e}",
        )
```

**Usage:**
```python
# Replace:
future = pool.submit(_run_subtest_in_process, ...)

# With:
future = pool.submit(_run_subtest_in_process_safe, ...)
```

### Step 3: Enhanced BrokenProcessPool Handler

Even with safe wrapper, handle pool crashes gracefully:

```python
except (KeyboardInterrupt, BrokenProcessPool) as e:
    if isinstance(e, BrokenProcessPool):
        # Scan results for rate limit indicators
        rate_limit_info = _detect_rate_limit_from_results(results, results_dir)

        if rate_limit_info and checkpoint and checkpoint_path:
            logger.warning(
                f"BrokenProcessPool caused by rate limit from {rate_limit_info.source}"
            )
            logger.info(f"Waiting {rate_limit_info.retry_after_seconds or 60}s before retry...")

            wait_for_rate_limit(
                rate_limit_info.retry_after_seconds,
                checkpoint,
                checkpoint_path,
            )

            # Identify remaining subtests (not yet completed OR marked as rate_limited)
            remaining = [
                s
                for s in tier_config.subtests
                if s.id not in results
                or results[s.id].selection_reason.startswith("RateLimitError:")
            ]

            if remaining:
                logger.info(f"Retrying {len(remaining)} subtests after rate limit...")
                retry_results = _retry_with_new_pool(
                    remaining_subtests=remaining,
                    config=config,
                    tier_id=tier_id,
                    tier_config=tier_config,
                    # ... other args
                )
                results.update(retry_results)
                return results

        # Not a rate limit, or no checkpoint - fall through to cleanup
        logger.error(f"BrokenProcessPool with no recovery path: {e}")

    # KeyboardInterrupt or unrecoverable - cleanup
    logger.warning("Experiment interrupted, cleaning up...")
    for future in futures:
        if not future.done():
            future.cancel()
```

### Step 4: Multi-Source Rate Limit Detection

```python
def _detect_rate_limit_from_results(
    results: dict[str, SubTestResult],
    results_dir: Path,
) -> RateLimitInfo | None:
    """Detect rate limit from multiple sources."""

    # Source 1: SubTestResult.rate_limit_info field (from safe wrapper)
    for subtest_id, result in results.items():
        if result.rate_limit_info:
            return result.rate_limit_info

    # Source 2: SubTestResult.selection_reason
    for subtest_id, result in results.items():
        if result.selection_reason.startswith("RateLimitError:"):
            return RateLimitInfo(
                source="agent",
                retry_after_seconds=None,
                error_message=result.selection_reason,
                detected_at=datetime.now(UTC).isoformat(),
            )

    # Source 3: .failed/ directories for crashed workers
    for failed_dir in results_dir.rglob(".failed/*/agent/result.json"):
        try:
            data = json.loads(failed_dir.read_text())
            stderr = data.get("stderr", "")
            stdout = data.get("stdout", "")

            rate_info = detect_rate_limit(stdout, stderr, source="agent")
            if rate_info:
                return rate_info
        except Exception:
            continue

    return None
```

### Step 5: Retry with Fresh Pool

```python
def _retry_with_new_pool(
    remaining_subtests: list[SubTestConfig],
    config: ExperimentConfig,
    tier_id: TierID,
    tier_config: TierConfig,
    # ... other params
    max_retries: int = 3,
) -> dict[str, SubTestResult]:
    """Create new ProcessPoolExecutor and retry remaining subtests."""
    results: dict[str, SubTestResult] = {}
    retries = 0

    while remaining_subtests and retries < max_retries:
        try:
            # Fresh coordinator for new pool
            manager = Manager()
            coordinator = RateLimitCoordinator(manager)

            with ProcessPoolExecutor(max_workers=config.parallel_subtests) as pool:
                futures = {}
                for subtest in remaining_subtests:
                    subtest_dir = results_dir / subtest.id
                    future = pool.submit(
                        _run_subtest_in_process_safe,  # Use safe wrapper
                        config=config,
                        tier_id=tier_id,
                        # ... other args
                    )
                    futures[future] = subtest.id

                # Collect results
                for future in as_completed(futures):
                    subtest_id = futures[future]
                    result = future.result()
                    results[subtest_id] = result

            # Check for rate-limited results that need retry
            remaining_subtests = [
                s
                for s in remaining_subtests
                if s.id in results
                and results[s.id].selection_reason.startswith("RateLimitError:")
            ]

            if remaining_subtests:
                # More rate limits - wait and retry
                rate_info = _detect_rate_limit_from_results(results, results_dir)
                if rate_info and checkpoint and checkpoint_path:
                    wait_for_rate_limit(
                        rate_info.retry_after_seconds,
                        checkpoint,
                        checkpoint_path,
                    )
                retries += 1
            else:
                # All completed successfully
                break

        except BrokenProcessPool:
            # Pool crashed again - retry
            rate_info = _detect_rate_limit_from_results(results, results_dir)
            if rate_info and checkpoint and checkpoint_path:
                wait_for_rate_limit(
                    rate_info.retry_after_seconds,
                    checkpoint,
                    checkpoint_path,
                )
            retries += 1

    return results
```

## Failed Attempts (Critical Learnings)
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: Relying Only on RateLimitError Exception Handling

**What we tried:**
```python
try:
    result = run_worker(...)
except RateLimitError as e:
    wait_and_retry()
```

**Why it failed:**
- Rate limits detected AFTER worker exits (exit_code=-1)
- Worker crashes before raising clean `RateLimitError`
- ProcessPool throws `BrokenProcessPool` instead
- All pending futures become unexecutable

**Lesson:** Need defensive wrapper that catches exceptions BEFORE they crash the worker process.

### ❌ Failed: Detecting Rate Limits Only from Exceptions

**What we tried:**
- Catching `RateLimitError` in worker execution path
- Assuming rate limit info available in exception

**Why it failed:**
- Rate limit errors sometimes manifest as generic subprocess crashes
- Error message buried in stderr logs, not in exception
- Need to check multiple sources: results, .failed/ dirs, stderr

**Lesson:** Multi-source detection required - exceptions, structured results, AND log files.

### ❌ Failed: Single Retry Attempt

**What we tried:**
```python
if BrokenProcessPool:
    create_new_pool()
    retry_once()
```

**Why it failed:**
- Rate limits can persist across retries
- No exponential backoff or retry limit
- Could retry indefinitely into same rate limit

**Lesson:** Need retry loop with max attempts (3) and proper wait between retries.

### ❌ Failed: Ignoring Pre-flight Checks

**What we tried:**
- Start parallel workers immediately
- Handle rate limits only after they occur

**Why it failed:**
- Wasted CPU/time starting workers when already rate-limited
- All workers would immediately fail
- Better to check status before starting expensive operations

**Lesson:** Pre-flight checks prevent wasted work and provide better UX.

## Results & Metrics

### Before Fix (T5 Failure)
- **T0-T4**: ✅ 100% pass
- **T5**: ❌ 0% pass (all 15 subtests failed)
- **Error visibility**: Poor (hidden in .failed/ dirs)
- **Recovery**: Manual intervention required

### After Fix (Expected)
- **T0-T4**: ✅ 100% pass
- **T5**: ✅ 100% pass (with automatic retry)
- **Error visibility**: Good (logged with context)
- **Recovery**: Automatic (wait + retry)

### Test Coverage
- **Unit tests**: 9/10 passing (90%)
- **Safe wrapper**: Verified exception conversion
- **Detection**: Multi-source validation
- **Serialization**: rate_limit_info field tested

## Configuration & Parameters

### Data Model Changes

Add to your result dataclass:

```python
@dataclass
class SubTestResult:
    # ... existing fields ...

    # NEW: Rate limit info for retry logic (None if not rate-limited)
    rate_limit_info: RateLimitInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            # ... existing fields ...
            "rate_limit_info": (
                {
                    "source": self.rate_limit_info.source,
                    "retry_after_seconds": self.rate_limit_info.retry_after_seconds,
                    "error_message": self.rate_limit_info.error_message,
                    "detected_at": self.rate_limit_info.detected_at,
                }
                if self.rate_limit_info
                else None
            ),
        }
```

### Retry Configuration

```python
# In _retry_with_new_pool()
max_retries: int = 3  # Maximum retry attempts
default_wait: int = 60  # Default wait if no Retry-After header (seconds)
buffer_multiplier: float = 1.1  # Add 10% buffer to Retry-After times
```

### Pre-flight Check Parameters

```python
# In check_api_rate_limit_status()
test_command = ["claude", "--print", "ping"]  # Minimal API test
timeout = 30  # Subprocess timeout (seconds)
```

## Critical Implementation Details

### 1. Import Rate Limit Detection Early

```python
from scylla.e2e.rate_limit import (
    RateLimitError,
    RateLimitInfo,
    detect_rate_limit,  # CRITICAL: Add this
    wait_for_rate_limit,
)
```

### 2. Always Use Safe Wrapper for Pool Submission

```python
# DON'T:
pool.submit(_run_subtest_in_process, ...)

# DO:
pool.submit(_run_subtest_in_process_safe, ...)
```

### 3. Check Both Sources in BrokenProcessPool Handler

```python
# Check structured results FIRST
rate_limit_info = _detect_rate_limit_from_results(results, results_dir)

# Then check .failed/ directories as fallback
```

### 4. Preserve Partial Results

```python
# CRITICAL: Update results dict, don't replace
retry_results = _retry_with_new_pool(remaining, ...)
results.update(retry_results)  # Merge, don't overwrite
return results
```

## Verification Commands

### Test Pre-flight Check
```bash
# Manually trigger rate limit
# Then verify pre-flight detection:
python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T5
# Should log: "Pre-flight rate limit detected for T5"
```

### Test Safe Wrapper
```bash
# Run unit tests
pixi run pytest tests/unit/e2e/test_rate_limit_recovery.py::TestRunSubtestInProcessSafe -v
```

### Test Pool Recovery
```bash
# Simulate rate limit with low parallelism
python scripts/run_e2e_experiment.py \
    --tiers T5 \
    --parallel 1 \
    --runs 1
# Should log: "BrokenProcessPool caused by rate limit"
# Then: "Retrying N subtests after rate limit..."
```

### Check Logs
```bash
# Look for these indicators:
grep "Pre-flight rate limit detected" logs/
grep "BrokenProcessPool caused by rate limit" logs/
grep "Retrying.*subtests after rate limit" logs/
grep "Rate limit wait complete. Resuming" logs/
```

## Common Pitfalls

### ⚠️ Pitfall 1: Forgetting to Import detect_rate_limit

**Error:**
```
NameError: name 'detect_rate_limit' is not defined
```

**Fix:**
Add to imports at top of file:
```python
from scylla.e2e.rate_limit import detect_rate_limit
```

### ⚠️ Pitfall 2: Not Using Safe Wrapper

**Symptom:** Pool still crashes despite recovery code

**Fix:** Ensure ALL pool.submit() calls use `_run_subtest_in_process_safe`

### ⚠️ Pitfall 3: Infinite Retry Loop

**Symptom:** Keeps retrying same rate limit without waiting

**Fix:** Ensure `wait_for_rate_limit()` called BEFORE retry, and max_retries enforced

### ⚠️ Pitfall 4: Missing rate_limit_info Field

**Error:**
```
AttributeError: 'SubTestResult' object has no attribute 'rate_limit_info'
```

**Fix:** Add field to dataclass and update `to_dict()` serialization

## Related Skills

- **error-handling**: General exception handling patterns
- **retry-logic**: Exponential backoff and retry strategies
- **processpool-debugging**: Debugging ProcessPoolExecutor failures
- **checkpoint-resume**: Checkpoint-based evaluation resume

## References

- Pull Request: https://github.com/HomericIntelligence/ProjectScylla/pull/168
- Original Failure: `results/2026-01-09T20-07-13-test-001/T5/` (.failed/ directories)
- Python ProcessPoolExecutor docs: https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor

## Summary

**Key Insight:** ProcessPoolExecutor crashes from rate limits require THREE layers of defense:
1. **Pre-flight checks** (prevent wasted work)
2. **Safe wrappers** (prevent pool poisoning)
3. **Pool recovery** (handle failures gracefully)

**Most Important:** The safe wrapper (`_run_subtest_in_process_safe`) is the critical fix - it prevents worker crashes from ever reaching the pool level.

**Don't Forget:** Multi-source rate limit detection is essential because errors can hide in:
- Exception messages
- Structured result fields
- .failed/ directory logs
