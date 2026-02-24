---
name: graceful-signal-handling
description: Implement graceful shutdown for SIGINT/SIGTERM with checkpoint save and partial results
category: tooling
date: 2026-01-04
tags: [signals, shutdown, checkpoint, ctrl-c, graceful-exit]
---

# Graceful Signal Handling

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Enable graceful shutdown on Ctrl+C (SIGINT) and SIGTERM without losing completed work |
| **Outcome** | ✅ Processes save checkpoints on interrupt and return partial results |
| **Project** | ProjectScylla |
| **PR** | [#141](https://github.com/HomericIntelligence/ProjectScylla/pull/141) |

## When to Use

Use this pattern when:
- Long-running processes need to handle Ctrl+C gracefully
- Work should be saved on interruption (checkpoints)
- Partial results are valuable even if process doesn't complete
- Multi-process/multi-threaded execution needs coordinated shutdown
- Users need ability to stop and resume work

## Problem

**Abrupt Termination**:
```
[INFO] Starting tier T0...
^C
Process terminated with signal SIGINT
```

**Issues**:
1. Ctrl+C kills process immediately
2. No checkpoint saved
3. All work lost
4. Can't resume from where it stopped
5. Workers left in inconsistent state

## Verified Workflow

### 1. Define Global Shutdown Flag

```python
# In main runner module
_shutdown_requested = False

def request_shutdown() -> None:
    """Request graceful shutdown (called by signal handlers)."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Graceful shutdown requested")

def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested
```

### 2. Register Signal Handlers

```python
# In CLI entry point
import signal

def signal_handler(signum: int, frame):
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    request_shutdown()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

### 3. Check for Shutdown in Main Loop

```python
try:
    for tier_id in config.tiers_to_run:
        # Check for shutdown before starting tier
        if is_shutdown_requested():
            logger.warning(f"Shutdown requested before tier {tier_id}, stopping...")
            break

        tier_result = run_tier(tier_id, baseline)
        tier_results[tier_id] = tier_result

finally:
    # Save checkpoint on interrupt
    if is_shutdown_requested() and checkpoint:
        checkpoint.status = "interrupted"
        checkpoint.last_updated_at = datetime.now(UTC).isoformat()
        save_checkpoint(checkpoint, checkpoint_path)
        logger.warning("💾 Checkpoint saved after interrupt")
```

### 4. Extend Coordinator for Cross-Process Shutdown

```python
class RateLimitCoordinator:
    def __init__(self, manager: SyncManager) -> None:
        self._shutdown_event = manager.Event()  # Add shutdown event

    def signal_shutdown(self) -> None:
        """Signal all workers to stop accepting new work."""
        self._shutdown_event.set()
        logger.info("Shutdown signal sent to all workers")

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_event.is_set()
```

### 5. Check Shutdown in Worker Processes

```python
for run_num in range(1, runs_per_subtest + 1):
    # Check for shutdown before starting run
    if coordinator and coordinator.is_shutdown_requested():
        logger.warning(f"Shutdown requested before run {run_num}, stopping...")
        break

    # Execute run...
```

### 6. Return Partial Results

```python
# If shutdown was requested, return partial results
if is_shutdown_requested():
    logger.warning("Experiment interrupted - returning partial results")
    return ExperimentResult(
        config=config,
        tier_results=tier_results,  # Only completed tiers
        # ... other fields
    )
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Using KeyboardInterrupt exception | Doesn't work well with ProcessPoolExecutor, can leave workers in bad state |
| Only checking shutdown at tier boundaries | Workers can run for 30+ seconds, too coarse-grained |
| Polling shutdown flag every N seconds | Race conditions and complexity, hard to get right |
| Not using finally block | Checkpoint not saved if exception occurs |

## Results & Parameters

### Signal Handling Pattern

```python
# 1. Global shutdown flag (module level)
_shutdown_requested = False

def request_shutdown() -> None:
    global _shutdown_requested
    _shutdown_requested = True

# 2. Register handlers in main()
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 3. Check in loops
if is_shutdown_requested():
    break

# 4. Save checkpoint in finally
finally:
    if is_shutdown_requested() and checkpoint:
        checkpoint.status = "interrupted"
        save_checkpoint(checkpoint, checkpoint_path)
```

### Checkpoint Status Values

```python
"running"                 # Normal execution
"paused_rate_limit"      # Paused for rate limit
"interrupted"            # User interrupted (Ctrl+C)
"completed"              # Finished normally
"failed"                 # Error occurred
```

### Shutdown Flow

1. **Signal Received** → Set global shutdown flag
2. **Main Loop** → Check flag before next tier/task
3. **Coordinator** → Signal all workers via shared Event
4. **Workers** → Check coordinator.is_shutdown_requested()
5. **Current Work** → Complete gracefully or timeout
6. **Checkpoint** → Save with "interrupted" status
7. **Return** → Partial results for completed work

## Key Learnings

1. **Global Flag First**: Simple global flag + signal handlers is sufficient
2. **Coordinator for Workers**: Use multiprocessing.Manager.Event for cross-process coordination
3. **Check at Boundaries**: Check shutdown before starting new work, not mid-task
4. **Always Use Finally**: Checkpoint save must be in finally block
5. **Partial Results OK**: Returning partial results is valuable

## Use Cases

1. **Long-Running Experiments**: ML training, benchmarking, testing
2. **Batch Processing**: ETL pipelines, data migrations
3. **Parallel Execution**: Multiple workers coordinating shutdown
4. **Resumable Tasks**: Save checkpoint and resume later

## Related Skills

- `optimization/checkpoint-result-validation` - Validating checkpoints on resume
- `tooling/execution-stage-logging` - Tracking which stage was interrupted
- `testing/resume-tests` - Testing interrupt/resume scenarios

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #141 - Graceful signal handling for E2E experiments | [notes.md](../../references/notes.md) |
