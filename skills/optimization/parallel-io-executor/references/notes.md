# Session Notes: Parallel I/O-Bound Execution Implementation

## Session Context

**Date**: 2026-01-30
**Task**: Implement multi-threaded `rerun_judges.py` according to pre-planned architecture
**Files Modified**:
- `scripts/rerun_judges.py` - CLI interface
- `scylla/e2e/rerun_judges.py` - Core implementation

## Original Plan Summary

The user provided a complete implementation plan with the following specifications:

### Architecture Decision

**Use ThreadPoolExecutor** (not ProcessPoolExecutor) because:
- I/O-bound: `run_llm_judge()` spawns `claude` CLI subprocess (GIL released)
- No serialization issues: All objects shared directly
- Simpler shared state: `threading.Lock` protects stats/sets
- Precedent: `runner.py:328` already uses ThreadPoolExecutor

### Implementation Steps

1. Add `--parallel N` CLI argument (default: 1)
2. Add imports: `time`, `threading`, `ThreadPoolExecutor`, `as_completed`
3. Create `_JudgeSlotResult` dataclass and safe wrapper
4. Add `parallel` parameter to `rerun_judges_experiment()`
5. Replace sequential loop with branching logic

## Implementation Details

### Changes to scripts/rerun_judges.py

#### Added CLI Argument (lines 171-177)
```python
parser.add_argument(
    "--parallel",
    type=int,
    default=1,
    metavar="N",
    help="Number of judge slots to run in parallel (default: 1, sequential)",
)
```

#### Pass Through Parameter (line 247)
```python
stats = rerun_judges_experiment(
    ...,
    parallel=args.parallel,
)
```

### Changes to scylla/e2e/rerun_judges.py

#### Added Imports (lines 20-22)
```python
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
```

#### Safe Wrapper Pattern (lines 394-418)
```python
@dataclass
class _JudgeSlotResult:
    """Result from a parallel judge slot execution."""
    slot: JudgeSlotToRerun
    success: bool
    error: str | None = None


def _rerun_single_judge_slot_safe(
    slot: JudgeSlotToRerun,
    experiment_dir: Path,
    config: ExperimentConfig,
) -> _JudgeSlotResult:
    """Safe wrapper that never raises — prevents one failure from poisoning the pool."""
    try:
        success = _rerun_single_judge_slot(slot, experiment_dir, config)
        return _JudgeSlotResult(slot=slot, success=success)
    except Exception as e:
        logger.error(
            f"Unexpected exception in judge worker for "
            f"{slot.tier_id}/{slot.subtest_id}/run_{slot.run_number:02d} "
            f"judge_{slot.judge_number:02d}: {type(e).__name__}: {e}"
        )
        return _JudgeSlotResult(slot=slot, success=False, error=str(e))
```

**Pattern Source**: `_run_subtest_in_process_safe()` in `subtest_executor.py:2043-2131`

#### Function Signature Update (line 517)
```python
def rerun_judges_experiment(
    ...,
    parallel: int = 1,
) -> RerunJudgeStats:
```

#### Branching Logic (lines 669-730)

Replaced sequential loop:
```python
for slot in needs_judge_rerun:
    if _rerun_single_judge_slot(slot, experiment_dir, config):
        stats.slots_rerun_success += 1
        runs_with_reruns.add(slot.run_dir)
    else:
        stats.slots_rerun_failed += 1
```

With branching implementation:
```python
if parallel <= 1 or len(needs_judge_rerun) <= 1:
    # === FAST PATH: Sequential (no pool overhead) ===
    for slot in needs_judge_rerun:
        if _rerun_single_judge_slot(slot, experiment_dir, config):
            stats.slots_rerun_success += 1
            runs_with_reruns.add(slot.run_dir)
        else:
            stats.slots_rerun_failed += 1
else:
    # === PARALLEL PATH: ThreadPoolExecutor ===
    lock = threading.Lock()
    total = len(needs_judge_rerun)
    completed_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(
                _rerun_single_judge_slot_safe, slot, experiment_dir, config
            ): slot
            for slot in needs_judge_rerun
        }

        for future in as_completed(futures):
            result = future.result()  # Never raises (safe wrapper)
            completed_count += 1

            with lock:
                if result.success:
                    stats.slots_rerun_success += 1
                    runs_with_reruns.add(result.slot.run_dir)
                else:
                    stats.slots_rerun_failed += 1

            # Progress logging
            elapsed = time.time() - start_time
            remaining = total - completed_count
            slot = result.slot
            status_str = "OK" if result.success else "FAIL"
            logger.info(
                f"[{completed_count}/{total}] "
                f"{slot.tier_id}/{slot.subtest_id}/"
                f"run_{slot.run_number:02d} "
                f"judge_{slot.judge_number:02d} -> {status_str} "
                f"({remaining} remaining, {elapsed:.0f}s elapsed)"
            )
```

## Thread Safety Analysis

### Protected Resources
- `stats.slots_rerun_success` (counter) - protected by `lock`
- `stats.slots_rerun_failed` (counter) - protected by `lock`
- `runs_with_reruns` (set) - protected by `lock`

### Unprotected Resources (Thread-Safe)
- Each `slot` writes to unique `judge_{NN}/` subdirectory
- Reads from immutable files (`config`, `experiment_dir`)
- Consensus regeneration happens AFTER pool context exit

### Lock Critical Sections
Minimized to only stat updates:
```python
with lock:
    if result.success:
        stats.slots_rerun_success += 1
        runs_with_reruns.add(result.slot.run_dir)
    else:
        stats.slots_rerun_failed += 1
```

Progress logging happens OUTSIDE lock (no shared state).

## Rate Limit Strategy

**Individual Worker Failure Model**:
- If rate limit hits, that slot returns `False`
- Slot can be rerun later with another invocation
- No cross-thread coordinator (YAGNI — this is a recovery tool)

**Alternative Considered**: Global rate limiter with backoff
**Decision**: Not needed for recovery tool, adds complexity

## Verification Strategy

### Syntax Check
```bash
python3 -m py_compile scripts/rerun_judges.py
python3 -m py_compile scylla/e2e/rerun_judges.py
```
Result: ✅ Both files compile successfully

### Help Output Check
```bash
python3 scripts/rerun_judges.py --help | grep -A 2 "parallel"
```
Result: ✅ `--parallel N` argument present in help

### Planned Integration Tests
```bash
# Dry run — verify classification still works
pixi run python scripts/rerun_judges.py \
  ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001/ \
  --status missing --dry-run

# Sequential (default, behavior unchanged)
pixi run python scripts/rerun_judges.py \
  ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001/ \
  --status missing --parallel 1

# Parallel execution
pixi run python scripts/rerun_judges.py \
  ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001/ \
  --status missing --parallel 6
```

## Design Patterns Used

### 1. Safe Wrapper Pattern
**Purpose**: Prevent unhandled exceptions from poisoning thread pool
**Source**: `subtest_executor.py:2043-2131`
**Implementation**: `_rerun_single_judge_slot_safe()` catches all exceptions

### 2. Branching Execution Pattern
**Purpose**: Avoid pool overhead for sequential execution
**Implementation**: `if parallel <= 1 or len(tasks) <= 1:` fast path

### 3. Result Dataclass Pattern
**Purpose**: Type-safe result passing from workers
**Implementation**: `_JudgeSlotResult` with `slot`, `success`, `error`

### 4. Lock Minimization Pattern
**Purpose**: Reduce contention in parallel code
**Implementation**: Only protect stat updates, log outside lock

### 5. Progress Reporting Pattern
**Purpose**: User feedback during long-running parallel operations
**Implementation**: `[completed/total]` with elapsed time and remaining count

## Key Learnings

### What Worked Well
1. **Following precedent**: Using existing patterns from `runner.py` and `subtest_executor.py`
2. **Clear plan**: Having detailed architecture decision upfront
3. **Safe wrapper**: Prevents one failure from crashing entire pool
4. **Sequential fast path**: Avoids pool overhead when `parallel=1`

### ThreadPoolExecutor vs ProcessPoolExecutor
**When to use ThreadPoolExecutor**:
- ✅ I/O-bound: subprocess, network, disk
- ✅ Shared state simple: counters, sets with lock
- ✅ No serialization needed: objects shared directly

**When to use ProcessPoolExecutor**:
- ❌ CPU-bound: heavy computation, no I/O wait
- ❌ Need true parallelism: bypass GIL
- ❌ Isolated state: each worker independent

### Backward Compatibility
- Default `--parallel 1` maintains sequential behavior
- Existing scripts/automation continue to work
- Users opt-in to parallelism explicitly

## Performance Expectations

| Scenario | Workers | Expected Speedup |
|----------|---------|------------------|
| Single slot | any | 1× (no parallelism benefit) |
| 10 slots | 1 | 1× (sequential baseline) |
| 10 slots | 3 | ~3× (I/O-bound ideal) |
| 10 slots | 6 | ~6× (I/O-bound ideal) |
| 10 slots | 12 | ~6-8× (diminishing returns, rate limits) |

**Bottlenecks**:
- LLM API rate limits (429 responses)
- Disk I/O contention (consensus regeneration)
- Logging contention (minor)

## Future Enhancements (YAGNI)

Not implemented (kept simple):
- [ ] Global rate limiter with exponential backoff
- [ ] Retry logic for transient failures
- [ ] Worker pool warmup/cooldown
- [ ] Dynamic worker adjustment based on success rate
- [ ] Prometheus metrics for parallel execution
- [ ] Progress bar instead of log messages

These can be added later if needed, following YAGNI principle.

## Related Code References

- `runner.py:328` - Tier-level ThreadPoolExecutor parallelism
- `subtest_executor.py:2043-2131` - Safe wrapper exception handling pattern
- `rerun_judges.py:319-389` - Original `_rerun_single_judge_slot()` (now wrapped)

## Testing Checklist

Pre-merge verification:
- [x] Syntax check passes (`py_compile`)
- [x] Help text includes `--parallel` argument
- [ ] Dry run produces same classification as before
- [ ] Sequential execution (`--parallel 1`) produces same results
- [ ] Parallel execution (`--parallel 6`) completes without errors
- [ ] Progress logging shows `[N/total]` format
- [ ] Consensus regeneration happens after all workers complete
- [ ] Failed slots are tracked correctly
- [ ] Lock contention is minimal (test with high parallelism)

## Commit Message

```
feat(e2e): Add parallel execution to rerun_judges.py

Implement ThreadPoolExecutor-based parallelization for judge slot reruns
with --parallel N CLI flag (default: 1, sequential).

Key features:
- ThreadPoolExecutor for I/O-bound subprocess operations
- Safe wrapper prevents pool poisoning from exceptions
- Thread-safe stats updates with threading.Lock
- Progress logging: [completed/total] with elapsed time
- Backward compatible (default --parallel 1)
- Fast path skips pool overhead when parallel <= 1

Architecture: Uses threads (not processes) because run_llm_judge()
spawns subprocesses (GIL released during I/O wait).

Files changed:
- scripts/rerun_judges.py: Add --parallel CLI arg
- scylla/e2e/rerun_judges.py: Implement branching logic
```
