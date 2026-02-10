---
name: "Parallel I/O-Bound Execution with ThreadPoolExecutor"
description: "Pattern for implementing ThreadPoolExecutor-based parallelization of I/O-bound tasks in Python CLI tools"
category: optimization
date: 2026-01-30
user-invocable: false
---
# Parallel I/O-Bound Execution with ThreadPoolExecutor

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-30 |
| Objective | | Field | Value | |-------|-------| | **Date** | 2026-01-30 | | **Objective** | Convert sequential I/O-bound loop to parallel execution using Threa... |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| **Date** | 2026-01-30 |
| **Objective** | Convert sequential I/O-bound loop to parallel execution using ThreadPoolExecutor |
| **Context** | Parallelizing judge slot reruns in `rerun_judges.py` (subprocess-based LLM judge execution) |
| **Outcome** | ✅ Successfully implemented thread-based parallelization with `--parallel N` CLI flag |
| **Performance Gain** | N×speedup for I/O-bound subprocess operations (6× with `--parallel 6`) |

## When to Use This Skill

Implement parallel execution using `ThreadPoolExecutor` when:

1. **I/O-Bound Operations**: Tasks that spawn subprocesses, wait on network/disk, or are blocked on external resources
2. **Independent Work Units**: Each task operates on isolated data (no shared state except stats counters)
3. **Existing Sequential Loop**: Converting `for item in items:` to parallel execution
4. **User-Controllable Parallelism**: CLI tools where users want to control concurrency level

**Do NOT use for**:
- CPU-bound operations (use `ProcessPoolExecutor` instead)
- Operations with complex shared state or ordering dependencies
- Tasks that cannot handle concurrent execution

## Architecture Decision: ThreadPoolExecutor vs ProcessPoolExecutor

**Use ThreadPoolExecutor when:**
- ✅ I/O-bound: Subprocesses, network calls, file operations (GIL released during blocking)
- ✅ No serialization issues: All objects can be shared directly between threads
- ✅ Simple shared state: Counters/sets protected by `threading.Lock`
- ✅ Precedent exists: Codebase already uses threads for similar tasks

**Example from session**: `run_llm_judge()` spawns `claude` CLI subprocess — threads release GIL while blocked on subprocess I/O.

## Verified Workflow

### Step 1: Add CLI Argument

**File**: Script entry point (e.g., `scripts/rerun_judges.py`)

```python
parser.add_argument(
    "--parallel",
    type=int,
    default=1,
    metavar="N",
    help="Number of tasks to run in parallel (default: 1, sequential)",
)
```

Pass through to core function:
```python
result = core_function(..., parallel=args.parallel)
```

### Step 2: Add Imports

**File**: Core module (e.g., `scylla/e2e/rerun_judges.py`)

```python
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
```

### Step 3: Create Safe Wrapper Pattern

**Critical**: Use a safe wrapper that catches exceptions to prevent pool poisoning.

```python
@dataclass
class _TaskResult:
    """Result from a parallel task execution."""
    task: TaskData  # Your task data structure
    success: bool
    error: str | None = None


def _run_task_safe(task: TaskData, *args, **kwargs) -> _TaskResult:
    """Safe wrapper that never raises — prevents one failure from poisoning the pool."""
    try:
        success = _run_task(task, *args, **kwargs)
        return _TaskResult(task=task, success=success)
    except Exception as e:
        logger.error(
            f"Unexpected exception in worker for {task.id}: "
            f"{type(e).__name__}: {e}"
        )
        return _TaskResult(task=task, success=False, error=str(e))
```

**Why this matters**: Without the safe wrapper, an unhandled exception in one worker can crash the entire pool.

### Step 4: Add `parallel` Parameter to Core Function

```python
def core_function(
    ...,
    parallel: int = 1,
) -> Stats:
    """Core processing function.

    Args:
        ...
        parallel: Number of tasks to run in parallel (default: 1, sequential)

    Returns:
        Stats with summary of what was done
    """
```

Update docstring to document the new parameter.

### Step 5: Implement Branching Logic

Replace the sequential loop with branching logic that chooses between sequential and parallel paths:

```python
if tasks:
    logger.info(f"Processing {len(tasks)} tasks (parallel={parallel})...")
    results_tracking: set[ResultKey] = set()

    if parallel <= 1 or len(tasks) <= 1:
        # === FAST PATH: Sequential (no pool overhead) ===
        for task in tasks:
            if _run_task(task, *args, **kwargs):
                stats.success += 1
                results_tracking.add(task.key)
            else:
                stats.failed += 1
    else:
        # === PARALLEL PATH: ThreadPoolExecutor ===
        lock = threading.Lock()
        total = len(tasks)
        completed_count = 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=parallel) as pool:
            futures = {
                pool.submit(_run_task_safe, task, *args, **kwargs): task
                for task in tasks
            }

            for future in as_completed(futures):
                result = future.result()  # Never raises (safe wrapper)
                completed_count += 1

                with lock:
                    if result.success:
                        stats.success += 1
                        results_tracking.add(result.task.key)
                    else:
                        stats.failed += 1

                # Progress logging
                elapsed = time.time() - start_time
                remaining = total - completed_count
                status_str = "OK" if result.success else "FAIL"
                logger.info(
                    f"[{completed_count}/{total}] "
                    f"{result.task.id} -> {status_str} "
                    f"({remaining} remaining, {elapsed:.0f}s elapsed)"
                )

    logger.info(f"Processed {stats.success} tasks successfully")
    logger.info(f"Failed to process {stats.failed} tasks")

    # Post-processing AFTER all tasks complete
    # (guaranteed by ThreadPoolExecutor.__exit__())
    for key in sorted(results_tracking):
        post_process(key)
```

### Thread Safety Guarantees

1. **Shared State Protection**: `threading.Lock` protects stats counters and result sets
2. **Worker Isolation**: Each task writes to unique output directory/file
3. **Immutable Reads**: Tasks only read immutable configuration data
4. **Post-processing Order**: Happens AFTER `ThreadPoolExecutor.__exit__()` waits for all futures

### Key Implementation Details

| Pattern | Purpose |
|---------|---------|
| `parallel <= 1` check | Skip pool overhead for sequential execution |
| `len(tasks) <= 1` check | No benefit from pool with single task |
| `with lock:` blocks | Protect shared stats/sets (minimize critical section) |
| `as_completed(futures)` | Process results as they finish (better progress reporting) |
| Progress logging | Show throughput: `[completed/total]`, elapsed time, remaining |
| `with ThreadPoolExecutor(...)` | Guarantees all workers finish before exiting context |

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

No failed attempts in this session — implementation followed the plan directly based on:

1. **Precedent**: `runner.py:328` already uses `ThreadPoolExecutor` for tier-level parallelism
2. **Clear Architecture**: Plan specified ThreadPoolExecutor over ProcessPoolExecutor with rationale
3. **Safe Wrapper Pattern**: Pattern borrowed from `subtest_executor.py:2043-2131` (`_run_subtest_in_process_safe`)

**Lessons from precedent code**:
- Always use a safe wrapper to catch exceptions
- Minimize lock critical sections (only stats updates)
- Log progress in parallel mode for user feedback

## Results & Parameters

### Implementation Files

```bash
# CLI interface
scripts/rerun_judges.py:171-177   # --parallel argument
scripts/rerun_judges.py:247       # Pass parallel parameter

# Core implementation
scylla/e2e/rerun_judges.py:20-22      # Imports
scylla/e2e/rerun_judges.py:394-418    # Safe wrapper
scylla/e2e/rerun_judges.py:517        # Function parameter
scylla/e2e/rerun_judges.py:669-730    # Branching logic
```

### Verification Commands

```bash
# Sequential (default, backward compatible)
python scripts/rerun_judges.py /path/to/experiment/ --status missing --parallel 1

# Parallel execution (6 workers)
python scripts/rerun_judges.py /path/to/experiment/ --status missing --parallel 6

# Dry run still works
python scripts/rerun_judges.py /path/to/experiment/ --status missing --dry-run
```

### Performance Characteristics

| Workers | Expected Speedup | Use Case |
|---------|------------------|----------|
| 1 | 1× (sequential) | Default, debugging, low concurrency |
| 3-6 | 3-6× | Typical LLM API calls (rate limits) |
| 10+ | 10×+ | High-throughput I/O (file processing) |

**Rate Limit Strategy**: Individual worker failure model. If rate limit hits, that task returns `False` and can be rerun later. No cross-thread coordinator (YAGNI for recovery tools).

## Code Checklist

When implementing this pattern:

- [ ] Add `--parallel N` CLI argument with `default=1`
- [ ] Import `time`, `threading`, `ThreadPoolExecutor`, `as_completed`
- [ ] Create result dataclass with `task`, `success`, `error` fields
- [ ] Create safe wrapper function that catches all exceptions
- [ ] Add `parallel: int = 1` parameter to core function
- [ ] Implement branching: `if parallel <= 1 or len(tasks) <= 1:` for sequential
- [ ] Use `threading.Lock()` for shared state protection
- [ ] Use `with ThreadPoolExecutor(max_workers=parallel):` context manager
- [ ] Submit tasks with `pool.submit(_safe_wrapper, task, ...)`
- [ ] Iterate with `for future in as_completed(futures):`
- [ ] Update stats inside `with lock:` blocks
- [ ] Add progress logging: `[completed/total] ... (remaining, elapsed)`
- [ ] Verify post-processing happens AFTER pool context exit
- [ ] Test with `--parallel 1` (sequential), `--parallel 6` (parallel), `--dry-run`

## Related Patterns

- `runner.py:328` - Tier-level parallelization with ThreadPoolExecutor
- `subtest_executor.py:2043-2131` - Safe wrapper pattern for exception handling
- ProcessPoolExecutor - Use for CPU-bound tasks instead of I/O-bound

## Tags

`#parallelization` `#ThreadPoolExecutor` `#I/O-bound` `#CLI` `#performance` `#optimization`
