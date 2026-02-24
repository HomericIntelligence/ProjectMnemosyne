# Global Semaphore Parallelism - Session Notes

## Session Context

**Date**: 2026-01-08
**Project**: ProjectScylla
**Branch**: `fix-e2e-errors-and-global-parallelism`
**PR**: [#151](https://github.com/HomericIntelligence/ProjectScylla/pull/151)

## Initial Problem Report

User reported three errors after implementing retry logic for git clone:

### Error 1: AttributeError
```
Traceback (most recent call last):
  File "runner.py", line 332
    tier_results[tier_id].cost_of_pass
AttributeError: 'TierResult' object has no attribute 'cost_of_pass'
```

### Error 2: FileNotFoundError
```
FileNotFoundError: [Errno 2] No such file or directory:
'results/.../T1/09/report.json'
```

### Error 3: Parallelism Behavior
User: "Also, when I run with multiple `--parallel`, I don't want to run different tiers in parallel and then have N parallel agents per tier, I want N parallel agents globally irrespective of tier"

**Current**: `--parallel 6` with 5 tiers = 30 concurrent agents (6 per tier)
**Desired**: `--parallel 6` = 6 agents globally

## Exploration Phase

Used Task tool with 3 parallel Explore agents to understand:
1. TierResult structure and cost_of_pass usage
2. Subtest report saving logic
3. Current parallelism architecture

**Key findings**:
- TierResult class missing cost_of_pass property
- save_subtest_report doesn't create directory before write
- Current architecture: ThreadPoolExecutor for tiers, ProcessPoolExecutor per tier for subtests

## Planning Phase

Entered plan mode and presented user with parallelism approach options:

**Option A**: Sequential tier execution (rejected - loses tier parallelism)
**Option B**: Shared semaphore ✅ (selected - preserves tier parallelism, limits agents)
**Option C**: Dynamic pool sizing (rejected - too complex)

User selected **Option B: Shared semaphore**

## Implementation Details

### Fix 1: cost_of_pass Property

Added to `TierResult` class at line 464-479:
```python
@property
def cost_of_pass(self) -> float:
    """Calculate cost-of-pass for this tier's best subtest."""
    if not self.best_subtest or self.best_subtest not in self.subtest_results:
        return float("inf")

    best = self.subtest_results[self.best_subtest]
    if best.pass_rate <= 0:
        return float("inf")

    return best.mean_cost / best.pass_rate
```

Updated `to_dict()` at line 493 to include `cost_of_pass`.

### Fix 2: mkdir Before Write

Added at `run_report.py:492-494`:
```python
# Ensure directory exists before writing
subtest_dir.mkdir(parents=True, exist_ok=True)
(subtest_dir / "report.json").write_text(json.dumps(json_report, indent=2))
```

### Fix 3: Global Semaphore Implementation

#### runner.py Changes

**Line 265-272**: Create Manager and global semaphore
```python
from multiprocessing import Manager

manager = Manager()
global_semaphore = manager.Semaphore(self.config.parallel_subtests)
logger.info(
    f"Created global semaphore with {self.config.parallel_subtests} concurrent agent limit"
)
```

**Line 542**: Update `_run_tier` signature
```python
def _run_tier(
    self,
    tier_id: TierID,
    baseline: TierBaseline | None,
    global_semaphore=None,
) -> TierResult:
```

**Line 290, 314-316**: Pass semaphore to tier execution calls
```python
# Sequential
tier_result = self._run_tier(tier_id, previous_baseline, global_semaphore)

# Parallel
futures = {
    executor.submit(self._run_tier, tier_id, previous_baseline, global_semaphore): tier_id
    for tier_id in group
}
```

**Line 589**: Pass to subtest executor
```python
results = run_tier_subtests_parallel(
    # ... params ...
    global_semaphore=global_semaphore,
)
```

#### subtest_executor.py Changes

**Line 1258**: Update `run_tier_subtests_parallel` signature
```python
def run_tier_subtests_parallel(
    # ... existing params ...
    global_semaphore=None,
) -> dict[str, SubTestResult]:
```

**Line 1347**: Pass to worker via pool.submit()
```python
future = pool.submit(
    _run_subtest_in_process,
    # ... params ...
    global_semaphore=global_semaphore,
)
```

**Line 1464**: Update `_run_subtest_in_process` signature
```python
def _run_subtest_in_process(
    # ... existing params ...
    global_semaphore=None,
) -> SubTestResult:
```

**Line 1490-1519**: Implement acquire/release in worker
```python
# Acquire global semaphore to limit concurrent agents across all tiers
if global_semaphore:
    global_semaphore.acquire()

try:
    tier_manager = TierManager(tiers_dir)
    workspace_manager = WorkspaceManager(...)

    executor = SubTestExecutor(config, tier_manager, workspace_manager)
    return executor.run_subtest(...)
finally:
    # Always release semaphore, even if exception occurred
    if global_semaphore:
        global_semaphore.release()
```

## Testing

Ran unit tests:
```bash
pixi run pytest tests/unit/e2e/ -v
============================= 108 passed in 0.32s ==============================
```

All tests passing ✅

## Commit & PR

**Branch**: `fix-e2e-errors-and-global-parallelism`

**Commit message**:
```
fix(e2e): add cost_of_pass property, fix FileNotFoundError, implement global parallelism

This commit fixes three critical issues in the E2E experiment runner:

1. Added cost_of_pass property to TierResult class (models.py:464-479)
   - Calculates mean_cost / pass_rate for best subtest
   - Returns infinity if no passes or no best subtest
   - Fixes AttributeError at runner.py:332

2. Fixed FileNotFoundError when saving subtest reports (run_report.py:492-494)
   - Added mkdir before writing report.json
   - Ensures directory exists even if runs moved to .failed/

3. Implemented global semaphore for parallelism control
   - Changed --parallel N from per-tier to global limit
   - Before: --parallel 6 with 5 tiers = 30 concurrent agents
   - After: --parallel 6 = max 6 agents globally across all tiers
   - Uses Manager().Semaphore() for cross-process sharing
   - Modified runner.py (265-272, 542, 589) and subtest_executor.py (1258, 1347, 1464, 1490-1519)

All 108 unit tests pass.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/151

Auto-merge enabled ✅

## Key Technical Decisions

### Why Manager().Semaphore()?

Initially considered `multiprocessing.Semaphore()` but it cannot be serialized for passing to ProcessPoolExecutor workers. `Manager().Semaphore()` creates a server process that hosts the semaphore, allowing it to be shared across process boundaries.

### Why Acquire in Worker Process?

Acquiring in main process before pool.submit() would block the main thread and prevent submitting remaining tasks. Acquiring in worker process allows all tasks to be queued, then throttles execution at the right place.

### Why try/finally?

Ensures semaphore is released even if worker crashes or raises exception. Critical for preventing semaphore slot leaks in long-running systems.

### Why Property Instead of Field?

`cost_of_pass` is derived from existing subtest results. Using a property:
- Guarantees consistency with source data
- Avoids state management complexity
- Eliminates risk of stale data

## Files Modified

1. `src/scylla/e2e/models.py` (+18 lines)
2. `src/scylla/e2e/run_report.py` (+2 lines)
3. `src/scylla/e2e/runner.py` (+12 lines)
4. `src/scylla/e2e/subtest_executor.py` (+17 lines)

**Total**: 4 files, +49 lines

## Related Work

This session built on previous work:
- **PR #146**: Implemented retry logic for transient git clone errors
- **Retrospective PR #66**: Documented retry patterns in ProjectMnemosyne

## Performance Impact

**Before**:
- Max agents: 30 (6 per tier × 5 tiers)
- High memory usage
- Frequent API rate limits

**After**:
- Max agents: 6 (global limit)
- Controlled memory usage
- Manageable rate limits

## Lessons Learned

1. **Manager for cross-process sharing**: Use Manager() for objects that need to work across ProcessPoolExecutor boundaries
2. **Acquire location matters**: Worker process, not main process
3. **Try/finally for cleanup**: Always guarantee resource release
4. **Properties for derived data**: Avoid storing calculated values
5. **mkdir before write**: Always create parent directories for dynamic paths
