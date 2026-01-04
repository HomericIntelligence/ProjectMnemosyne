# Tier Progress Indicators - Implementation Notes

## Context

ProjectScylla E2E experiments showed long periods of silence during tier execution:
- Users thought process had hung
- No visibility into which subtests were running vs complete
- No timing data to estimate remaining duration

**Evidence from Issue #129**:
- Desired: Live progress updates showing X of Y sub-tests complete
- Desired: Active worker thread count
- Desired: Elapsed time

## Solution

Added real-time progress logging after each subtest completion in the parallel execution loop.

### Code Changes

**File**: `src/scylla/e2e/subtest_executor.py`

**In `run_tier_subtests_parallel()` function**:

1. **Track tier-level timing** (lines 1157-1158):
```python
total_subtests = len(tier_config.subtests)
start_time = time.time()
```

2. **Initialize completion counter** (line 1184):
```python
completed_count = 0
```

3. **Log progress after each successful completion** (lines 1189-1198):
```python
results[subtest_id] = future.result()
completed_count += 1

# Log progress after each completion
elapsed = time.time() - start_time
active_workers = total_subtests - completed_count
logger.info(
    f"[PROGRESS] Tier {tier_id.value}: "
    f"{completed_count}/{total_subtests} complete, "
    f"{active_workers} active, elapsed: {elapsed:.0f}s"
)
```

4. **Log progress after rate limit errors** (lines 1234-1243):
```python
results[subtest_id] = SubTestResult(...)  # Error result
completed_count += 1

# Log progress after error
elapsed = time.time() - start_time
active_workers = total_subtests - completed_count
logger.info(f"[PROGRESS] Tier {tier_id.value}: ...")
```

5. **Log progress after general exceptions** (lines 1260-1269):
```python
results[subtest_id] = SubTestResult(...)  # Error result
completed_count += 1

# Log progress after error
elapsed = time.time() - start_time
active_workers = total_subtests - completed_count
logger.info(f"[PROGRESS] Tier {tier_id.value}: ...")
```

## Example Output

```
[INFO] Starting tier T0
[INFO] Tier T0: 24 sub-tests, mode: empty
[PROGRESS] Tier T0: 1/24 complete, 23 active, elapsed: 15s
[PROGRESS] Tier T0: 2/24 complete, 22 active, elapsed: 28s
[PROGRESS] Tier T0: 3/24 complete, 21 active, elapsed: 42s
[PROGRESS] Tier T0: 4/24 complete, 20 active, elapsed: 55s
[PROGRESS] Tier T0: 5/24 complete, 19 active, elapsed: 68s
...
[PROGRESS] Tier T0: 23/24 complete, 1 active, elapsed: 305s
[PROGRESS] Tier T0: 24/24 complete, 0 active, elapsed: 320s
[INFO] Tier T0 complete
```

## Files Changed

- `src/scylla/e2e/subtest_executor.py`:
  - Added `total_subtests` tracking
  - Added `start_time` tracking
  - Added `completed_count` counter
  - Added progress logging in 3 locations (success, rate limit error, general error)
  - Total: +34 lines

## Benefits

1. **User Confidence**: No more "appears hung" concerns - progress is visible
2. **Performance Analysis**: Elapsed time helps identify slow tiers
3. **Debugging**: Active worker count shows parallelism in action
4. **Estimation**: Users can estimate remaining time
5. **Simple**: Minimal overhead, just counters and logs

## PR Details

- **Branch**: `129-progress-indicators`
- **Files Changed**: 1 modified (`subtest_executor.py`)
- **Lines**: +34
- **Status**: Merged to main

## Related Issues

- Issue #131: Worker stage reporting (shows which stage each worker is in)
- Issue #129: Progress indicators (this skill - overall tier progress)
