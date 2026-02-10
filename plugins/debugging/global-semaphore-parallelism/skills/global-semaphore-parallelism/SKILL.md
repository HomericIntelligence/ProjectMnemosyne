---
name: global-semaphore-parallelism
description: "Implement global parallelism control using shared semaphores. Use when limiting concurrent workers across multiple process pools or fixing per-tier parallelism issues."
user-invocable: false
---

# Global Semaphore Parallelism Control

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-08 |
| **Project** | ProjectScylla |
| **Objective** | Fix E2E runner errors and implement global parallelism control using shared semaphores |
| **Outcome** | ✅ Successfully fixed 3 critical errors: AttributeError, FileNotFoundError, and per-tier parallelism |
| **PR** | [#151](https://github.com/HomericIntelligence/ProjectScylla/pull/151) |
| **Tests** | 108/108 unit tests passing |

## When to Use This Skill

Use this approach when you need to:

1. **Limit concurrent workers across multiple process pools** - When you have parallel tiers/groups that each spawn their own process pools, but you want a global limit on total concurrent workers
2. **Share concurrency limits across process boundaries** - When ProcessPoolExecutor workers need to coordinate on a shared resource limit
3. **Fix per-tier to global parallelism** - When `--parallel N` creates N workers per tier instead of N workers globally
4. **Preserve parallel-start behavior** - When you want tiers to start in parallel but limit total concurrent execution within them
5. **Debug missing properties/attributes** - When encountering `AttributeError: 'Object' has no attribute 'property'`

## Context: The Three Problems

### Problem 1: Missing `cost_of_pass` Attribute
**Error**: `AttributeError: 'TierResult' object has no attribute 'cost_of_pass'` at `runner.py:332`

**Root cause**: Code tried to access `tier_results[tier_id].cost_of_pass` but TierResult class didn't have this property.

### Problem 2: FileNotFoundError on Report Save
**Error**: `FileNotFoundError: .../T1/09/report.json` when saving subtest reports

**Root cause**: `save_subtest_report` tried to write to a directory that didn't exist (runs may have been moved to `.failed/` directory).

### Problem 3: Per-Tier Parallelism Instead of Global
**Current behavior**: With `--parallel 6` and 5 tiers running in parallel:
- Each tier creates ProcessPoolExecutor with 6 workers
- Total: 6 workers × 5 tiers = **30 concurrent agents**

**Desired behavior**: `--parallel 6` = maximum **6 agents globally** across ALL tiers

## Verified Workflow

### Fix 1: Add Missing Property to Data Class

**File**: `src/scylla/e2e/models.py`

Add a `@property` method that calculates the value from existing data:

```python
@property
def cost_of_pass(self) -> float:
    """Calculate cost-of-pass for this tier's best subtest.

    Returns:
        Cost per successful pass (mean_cost / pass_rate), or infinity if no passes.

    """
    if not self.best_subtest or self.best_subtest not in self.subtest_results:
        return float("inf")

    best = self.subtest_results[self.best_subtest]
    if best.pass_rate <= 0:
        return float("inf")

    return best.mean_cost / best.pass_rate
```

Update `to_dict()` to include the property:

```python
def to_dict(self) -> dict[str, Any]:
    return {
        # ... existing fields ...
        "cost_of_pass": self.cost_of_pass,  # Add this line
        # ... more fields ...
    }
```

### Fix 2: Ensure Directory Exists Before Writing

**File**: `src/scylla/e2e/run_report.py`

Add `mkdir` before file write operations:

```python
# Ensure directory exists before writing
subtest_dir.mkdir(parents=True, exist_ok=True)
(subtest_dir / "report.json").write_text(json.dumps(json_report, indent=2))
```

**Key insight**: Always create parent directories when writing files that might be in dynamically created locations (like `.failed/` subdirectories).

### Fix 3: Global Semaphore for Cross-Process Concurrency Control

**Architecture change**: From per-tier limits to global limits

**Before**:
```
ThreadPoolExecutor(5 tiers) - parallel tier start
  ├── T0: ProcessPoolExecutor(6 workers) ← 6 agents
  ├── T1: ProcessPoolExecutor(6 workers) ← 6 agents
  ├── T2: ProcessPoolExecutor(6 workers) ← 6 agents
  ├── T3: ProcessPoolExecutor(6 workers) ← 6 agents
  └── T4: ProcessPoolExecutor(6 workers) ← 6 agents
  Total: 30 concurrent agents!
```

**After**:
```
ThreadPoolExecutor(5 tiers) - parallel tier start (preserved)
  └── Global Semaphore(6) - shared across ALL process pools
      └── Max 6 agents at any time across ALL tiers
```

#### Step 1: Create Manager and Global Semaphore

**File**: `src/scylla/e2e/runner.py` (in `run()` method)

```python
# Create global semaphore for limiting concurrent agents across ALL tiers
from multiprocessing import Manager

manager = Manager()
global_semaphore = manager.Semaphore(self.config.parallel_subtests)
logger.info(
    f"Created global semaphore with {self.config.parallel_subtests} concurrent agent limit"
)
```

**Critical**: Use `Manager().Semaphore()` NOT `multiprocessing.Semaphore()` because Manager creates a server process that hosts the semaphore, allowing it to be shared across process boundaries when ProcessPoolExecutor spawns new processes.

#### Step 2: Thread Call Chain - Pass Semaphore Through Layers

**File**: `src/scylla/e2e/runner.py`

Update function signature:
```python
def _run_tier(
    self,
    tier_id: TierID,
    baseline: TierBaseline | None,
    global_semaphore=None,  # Add parameter
) -> TierResult:
```

Pass to all tier execution calls:
```python
# Sequential execution
tier_result = self._run_tier(tier_id, previous_baseline, global_semaphore)

# Parallel execution
futures = {
    executor.submit(self._run_tier, tier_id, previous_baseline, global_semaphore): tier_id
    for tier_id in group
}
```

Pass to subtest executor:
```python
results = run_tier_subtests_parallel(
    # ... other params ...
    global_semaphore=global_semaphore,  # Add parameter
)
```

#### Step 3: Process Pool Submission - Pass to Workers

**File**: `src/scylla/e2e/subtest_executor.py`

Update function signature:
```python
def run_tier_subtests_parallel(
    # ... existing params ...
    global_semaphore=None,  # Add parameter
) -> dict[str, SubTestResult]:
```

Pass to worker function via pool.submit():
```python
future = pool.submit(
    _run_subtest_in_process,
    # ... other params ...
    global_semaphore=global_semaphore,  # eksternal parameter
)
```

#### Step 4: Worker Process - Implement Acquire/Release

**File**: `src/scylla/e2e/subtest_executor.py`

Update worker function signature:
```python
def _run_subtest_in_process(
    # ... existing params ...
    global_semaphore=None,  # Add parameter
) -> SubTestResult:
```

Wrap agent execution with semaphore:
```python
# Acquire global semaphore to limit concurrent agents across all tiers
if global_semaphore:
    global_semaphore.acquire()

try:
    # Create managers and executor
    tier_manager = TierManager(tiers_dir)
    workspace_manager = WorkspaceManager(...)

    # Run agent (this is the expensive operation we want to limit)
    executor = SubTestExecutor(config, tier_manager, workspace_manager)
    return executor.run_subtest(
        # ... params ...
    )
finally:
    # Always release semaphore, even if exception occurred
    if global_semaphore:
        global_semaphore.release()
```

**Critical patterns**:
- ✅ Acquire in worker process (not main process)
- ✅ Use try/finally to guarantee release
- ✅ Check if semaphore exists (backward compatibility)
- ✅ Acquire blocks until slot available

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Attempt 1: Using `multiprocessing.Semaphore()` Directly

**What we tried**: Creating semaphore without Manager
```python
from multiprocessing import Semaphore
global_semaphore = Semaphore(6)
```

**Why it failed**:
- `multiprocessing.Semaphore` cannot be serialized for inter-process communication
- ProcessPoolExecutor needs to serialize arguments to send to worker processes
- Error encountered during serialization

**Solution**: Use `Manager().Semaphore()` instead - Manager creates a server process that hosts shareable objects.

### ❌ Attempt 2: Acquiring Semaphore in Main Process Before Submission

**What we tried**: Acquire semaphore before submitting to pool
```python
for subtest in tier_config.subtests:
    global_semaphore.acquire()  # ❌ Wrong place
    future = pool.submit(_run_subtest_in_process, ...)
```

**Why it failed**:
- Main process blocks waiting for semaphore
- Can't submit remaining tasks to pool
- Defeats purpose of parallel execution
- Deadlock risk: main process holds all semaphore slots

**Solution**: Acquire semaphore IN the worker process, just before expensive operation.

### ❌ Attempt 3: Storing `cost_of_pass` as a Field

**What we tried**: Adding `cost_of_pass` as a dataclass field
```python
@dataclass
class TierResult:
    cost_of_pass: float = 0.0  # ❌ Wrong approach
```

**Why it failed**:
- `cost_of_pass` is derived from `best_subtest` results
- Would require updating whenever subtest results change
- Risk of stale/inconsistent data
- Adds unnecessary state management

**Solution**: Use `@property` to calculate on-demand from existing data.

### ❌ Attempt 4: Limiting ProcessPoolExecutor max_workers

**What we tried**: Reduce pool size to prevent over-subscription
```python
with ProcessPoolExecutor(max_workers=1) as pool:  # ❌ Too restrictive
```

**Why it failed**:
- Limits parallelism WITHIN each tier
- Multiple tiers still create multiple pools
- Doesn't solve the global limit problem
- Reduces concurrency unnecessarily when few tiers active

**Solution**: Keep per-tier pools at full size, use semaphore for global coordination.

## Results & Parameters

### Configuration Used

**Experiment parameters**:
- `--parallel 6`: Global concurrent agent limit
- Multiple tiers (T0-T4): 5 tiers with parallel execution
- Each tier: 10-24 subtests per tier

### Performance Characteristics

**Before (per-tier parallelism)**:
- Max concurrent agents: `parallel_subtests × active_tiers`
- With `--parallel 6` and 5 tiers: **30 agents**
- Memory usage: Very high
- API rate limits: Frequently hit

**After (global parallelism)**:
- Max concurrent agents: `parallel_subtests` (6)
- With `--parallel 6` and 5 tiers: **6 agents**
- Memory usage: Controlled
- API rate limits: Manageable

### Test Results

All 108 unit tests passing:
```bash
pixi run pytest tests/unit/e2e/ -v
============================= 108 passed in 0.32s ==============================
```

### Code Changes Summary

| File | Lines Changed | Change Type |
|------|--------------|-------------|
| `models.py` | +18 | Add cost_of_pass property |
| `run_report.py` | +2 | Add mkdir before write |
| `runner.py` | +12 | Create and pass semaphore |
| `subtest_executor.py` | +17 | Acquire/release in worker |
| **Total** | **+49** | **4 files modified** |

## Key Insights

### 1. Manager() vs Direct Semaphore Creation

**Always use `Manager().Semaphore()` for cross-process sharing**:
- Manager creates a server process hosting the semaphore
- Server process allows sharing across process boundaries
- Direct semaphore creation fails with serialization errors

### 2. Acquire Location Matters

**Acquire in worker process, not main process**:
- Main process acquires → blocks submission of remaining tasks
- Worker process acquires → allows pool to queue all tasks
- Worker blocking is the desired behavior (throttles execution)

### 3. Try/Finally for Resource Cleanup

**Always wrap semaphore acquire/release in try/finally**:
- Guarantees release even on exceptions
- Prevents semaphore slot leaks
- Critical for long-running processes

### 4. Properties for Derived Values

**Use `@property` for calculated values**:
- Avoids storing redundant data
- Guarantees consistency with source data
- Simplifies state management

### 5. Directory Creation Before Writes

**Always create parent directories for dynamic paths**:
- Use `path.mkdir(parents=True, exist_ok=True)`
- Especially important for failure/retry paths (`.failed/` directories)
- Prevents FileNotFoundError on first write

## Related Skills

- **retry-transient-errors**: Network error handling with exponential backoff
- **graceful-signal-handling**: Clean shutdown with signal handlers
- **e2e-checkpoint-resume**: Resume capability for long-running experiments

## References

- Python multiprocessing.Manager documentation: https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Manager
- ProcessPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
- Semaphore synchronization: https://docs.python.org/3/library/threading.html#semaphore-objects
