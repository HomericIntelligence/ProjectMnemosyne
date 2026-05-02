# Graceful Signal Handling - Implementation Notes

## Context

ProjectScylla E2E experiments had no signal handling:
- Ctrl+C killed process immediately
- No checkpoint saved
- All work lost
- Couldn't resume from where it stopped

**Issue #130**: "Implement signal handling for graceful interruption (Ctrl+C/Z)"

## Solution

Implemented comprehensive signal handling with:
1. Signal handlers registered in CLI entry point
2. Global shutdown flag in runner module
3. Coordinator extension for cross-process signaling
4. Checkpoint save with "interrupted" status
5. Partial results return

### Code Changes

**File 1**: `scripts/run_e2e_experiment.py`

1. **Import signal module** (line 18):
```python
import signal
```

2. **Import shutdown functions** (line 28):
```python
from scylla.e2e.runner import request_shutdown, run_experiment
```

3. **Register signal handlers** (lines 349-355):
```python
# Register signal handlers for graceful shutdown
def signal_handler(signum: int, frame):
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    request_shutdown()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

**File 2**: `src/scylla/e2e/runner.py`

1. **Global shutdown coordination** (lines 50-71):
```python
# Global shutdown coordination
_shutdown_requested = False

def request_shutdown() -> None:
    """Request graceful shutdown of the experiment."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Graceful shutdown requested")

def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested
```

2. **Check shutdown before each tier** (lines 220-222):
```python
# Check for shutdown before starting tier
if is_shutdown_requested():
    logger.warning(f"Shutdown requested before tier {tier_id.value}, stopping...")
    break
```

3. **Save checkpoint in finally block** (lines 241-248):
```python
finally:
    # Save checkpoint on interrupt
    if is_shutdown_requested() and self.checkpoint:
        self.checkpoint.status = "interrupted"
        self.checkpoint.last_updated_at = datetime.now(UTC).isoformat()
        save_checkpoint(self.checkpoint, checkpoint_path)
        logger.warning("💾 Checkpoint saved after interrupt")
    self._cleanup_pid_file()
```

4. **Return partial results** (lines 251-287):
```python
# If shutdown was requested, return partial results
if is_shutdown_requested():
    logger.warning("Experiment interrupted - returning partial results")
    return ExperimentResult(
        config=self.config,
        tier_results=tier_results,  # Only completed tiers
        # ... (partial results)
    )
```

**File 3**: `src/scylla/e2e/subtest_executor.py`

1. **Extend RateLimitCoordinator** (line 304):
```python
def __init__(self, manager: SyncManager) -> None:
    # ... existing fields
    self._shutdown_event = manager.Event()  # NEW
```

2. **Add shutdown methods** (lines 374-386):
```python
def signal_shutdown(self) -> None:
    """Signal all workers to stop accepting new work."""
    self._shutdown_event.set()
    logger.info("Shutdown signal sent to all workers")

def is_shutdown_requested(self) -> bool:
    """Check if shutdown has been requested."""
    return self._shutdown_event.is_set()
```

3. **Check shutdown before each run** (lines 497-502):
```python
# Check for shutdown before starting run
if coordinator and coordinator.is_shutdown_requested():
    logger.warning(
        f"Shutdown requested before run {run_num}, stopping..."
    )
    break
```

4. **Propagate shutdown in parallel loop** (lines 1212-1215):
```python
# Check for shutdown request
if is_shutdown_requested():
    logger.warning("Shutdown requested, signaling workers to stop...")
    coordinator.signal_shutdown()
    break
```

## Shutdown Flow

```
1. User presses Ctrl+C
   ↓
2. signal_handler() called
   ↓
3. request_shutdown() sets global flag
   ↓
4. Main loop checks is_shutdown_requested()
   ↓
5. If True, break out of tier loop
   ↓
6. coordinator.signal_shutdown() notifies workers
   ↓
7. Workers check coordinator.is_shutdown_requested()
   ↓
8. Workers stop accepting new runs
   ↓
9. finally block executes
   ↓
10. Checkpoint saved with status="interrupted"
   ↓
11. _cleanup_pid_file() removes PID file
   ↓
12. Return partial ExperimentResult
```

## Files Changed

- `scripts/run_e2e_experiment.py`: Signal handler registration
- `src/scylla/e2e/runner.py`: Global flag, shutdown checks, checkpoint save, partial results
- `src/scylla/e2e/subtest_executor.py`: Coordinator extension, worker checks

**Total**: 3 files changed, +136 lines, -21 lines

## Benefits

1. **No Work Lost**: Checkpoint saved with completed work
2. **Clean Shutdown**: Workers stop gracefully
3. **Partial Results**: Return what was completed
4. **Resumable**: Can resume from checkpoint
5. **User-Friendly**: Ctrl+C works as expected

## PR Details

- **Branch**: `130-signal-handling`
- **Files Changed**: 3 modified
- **Lines**: +136, -21
- **Status**: Merged to main

## Testing

Manual test scenarios:
- Interrupt during worktree setup
- Interrupt during agent execution
- Interrupt during judge execution
- Interrupt between tiers
- Verify checkpoint saved with "interrupted" status
- Verify partial results returned
- Verify resume works from interrupted checkpoint
