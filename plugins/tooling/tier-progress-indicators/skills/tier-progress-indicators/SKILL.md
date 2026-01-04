---
name: tier-progress-indicators
description: Add real-time progress tracking for parallel tier execution to prevent 'appears hung' issues
category: tooling
date: 2026-01-04
tags: [progress, observability, parallel-execution, logging, user-experience]
---

# Tier Progress Indicators

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Add real-time progress indicators during parallel tier execution to prevent appearance of hung process |
| **Outcome** | ✅ Progress logging shows completed/total tasks, active workers, and elapsed time |
| **Project** | ProjectScylla |
| **PR** | [#140](https://github.com/HomericIntelligence/ProjectScylla/pull/140) |

## When to Use

Use this pattern when:
- Parallel workers execute long-running tasks
- Users can't tell if the process is stuck or just slow
- Need visibility into overall progress (X of Y complete)
- Want to show active worker count and elapsed time
- Process appears hung due to lack of output during execution

## Problem

**Silent Execution**:
```
[INFO] Starting tier T0
```
...30 seconds of silence...
```
[INFO] Tier T0 complete
```

**Issues**:
1. No indication of progress during execution
2. Users think process has hung
3. Can't tell how many workers are active
4. No timing information for performance analysis
5. Unclear if process is stuck or progressing normally

## Verified Workflow

### 1. Add Progress Tracking Variables

```python
# Before parallel execution starts
total_subtests = len(tier_config.subtests)
start_time = time.time()
completed_count = 0
```

### 2. Log Progress After Each Completion

```python
for future in as_completed(futures):
    subtest_id = futures[future]
    try:
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

### 3. Handle Error Cases

```python
except Exception as e:
    # Create error result
    results[subtest_id] = create_error_result(...)
    completed_count += 1  # Still count as complete

    # Log progress after error
    elapsed = time.time() - start_time
    active_workers = total_subtests - completed_count
    logger.info(
        f"[PROGRESS] Tier {tier_id.value}: "
        f"{completed_count}/{total_subtests} complete, "
        f"{active_workers} active, elapsed: {elapsed:.0f}s"
    )
```

### 4. Example Output

```
[INFO] Starting tier T0
[PROGRESS] Tier T0: 1/24 complete, 23 active, elapsed: 15s
[PROGRESS] Tier T0: 2/24 complete, 22 active, elapsed: 28s
[PROGRESS] Tier T0: 3/24 complete, 21 active, elapsed: 42s
[PROGRESS] Tier T0: 4/24 complete, 20 active, elapsed: 55s
...
[PROGRESS] Tier T0: 24/24 complete, 0 active, elapsed: 320s
[INFO] Tier T0 complete
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Progress bars (tqdm) | Doesn't work well with multiple parallel workers producing output |
| Periodic timer-based updates | Can't show accurate completion count without coordination |
| Only logging start/end | Users still see long gaps with no output during execution |

## Results & Parameters

### Progress Log Format

```
[PROGRESS] Tier {tier_id}: {completed}/{total} complete, {active} active, elapsed: {elapsed}s
```

**Fields**:
- `tier_id`: Tier being executed (e.g., "T0")
- `completed`: Number of subtests completed so far
- `total`: Total number of subtests in tier
- `active`: Number of workers still running (calculated as `total - completed`)
- `elapsed`: Time since tier started (in seconds, no decimals)

### Implementation Locations

```python
# In run_tier_subtests_parallel() function
total_subtests = len(tier_config.subtests)  # Before loop
start_time = time.time()                     # Before loop
completed_count = 0                           # Initialize counter

# In as_completed() loop
completed_count += 1                          # After each completion
elapsed = time.time() - start_time
active_workers = total_subtests - completed_count
logger.info(f"[PROGRESS] Tier {tier_id}: ...")  # Log progress
```

### Benefits Achieved

1. **Visibility**: Users know exactly how many tasks are complete
2. **Active Workers**: Shows parallelism in action
3. **Timing**: Elapsed time helps estimate remaining duration
4. **Confidence**: No more "appears hung" concerns
5. **Debugging**: Easy to spot when workers slow down or stop

## Key Learnings

1. **Log After Every Completion**: Both success and error paths need progress updates
2. **Calculate Active Workers**: `total - completed` gives clear picture of parallelism
3. **Whole Seconds**: Use `elapsed:.0f` to avoid decimal clutter in logs
4. **Consistent Format**: `[PROGRESS]` prefix makes logs parseable
5. **Simple is Better**: Basic counters work better than complex progress bars

## Use Cases

1. **Parallel Test Runners**: Show X of Y tests complete
2. **Batch Processing**: Track items processed across workers
3. **ML Training**: Display epochs or batches completed
4. **API Rate-Limited Operations**: Show progress when workers pause/resume

## Related Skills

- `tooling/execution-stage-logging` - Worker-level stage tracking with timing
- `debugging/hung-process-detection` - Detecting stuck processes
- `optimization/parallel-execution` - Optimizing worker parallelism

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #140 - Progress indicators for E2E tier execution | [notes.md](../../references/notes.md) |
