# Session Notes: MultiProcess to MultiThread Conversion

## Date: 2026-03-18

## Context

ProjectScylla's E2E experiment runner used `ProcessPoolExecutor` to run subtests in parallel. When testing on Python 3.14t (free-threaded CPython), the runner hung indefinitely because:

1. Python 3.14t uses `forkserver` as the default multiprocessing start method
2. `forkserver` serializes all arguments passed to `pool.submit()`
3. `ParallelismScheduler` contained `Manager().Semaphore()` proxies
4. These proxies include an `AuthenticationString` that refuses serialization
5. `pool.submit()` silently failed, causing the pool to hang forever

## Approach

### Phase 1: Plan (in plan mode)
- Read all 10 affected source files and 4 test files
- Mapped every reference to `ProcessPoolExecutor`, `Manager()`, `BrokenProcessPool`, `SyncManager`
- Identified dead code that only existed because of process boundaries
- Created a 5-part plan covering core conversion, dead code removal, test cleanup, lazy import proxy updates, and comment cleanup

### Phase 2: Implementation
- Converted all files in a single session
- Started with the 3 core files (parallel_executor, scheduler, runner)
- Then dead code removal (5 files)
- Then test cleanup (4 test files)
- Then comment/docstring updates

### Phase 3: Rebase
- Had to resolve 3 conflicts during rebase onto main
- Dropped 5 intermediate commits that were superseded by the final one
- Used `.git/rebase-merge/git-rebase-todo` to mark commits as `drop`

## Key Metrics

- **Lines removed**: ~600 (net -599 across 14 files)
- **Tests**: 4802 passing after conversion (0 failures)
- **Coverage**: 77.51% (above 75% threshold)
- **Pre-commit**: All hooks pass (ruff, mypy, bandit, etc.)

## Files Modified

### Source (9 files)
1. `scylla/e2e/parallel_executor.py` - Core conversion
2. `scylla/e2e/scheduler.py` - threading.Semaphore
3. `scylla/e2e/runner.py` - Remove Manager/BrokenProcessPool
4. `scylla/e2e/workspace_manager.py` - Delete from_existing()
5. `scylla/e2e/checkpoint_finalizer.py` - Remove disk-merge
6. `scylla/e2e/tier_action_builder.py` - Remove checkpoint_merge_lock
7. `scylla/e2e/checkpoint.py` - Simplify save_checkpoint
8. `scylla/e2e/subtest_executor.py` - Update lazy imports
9. `scylla/e2e/stages.py` - Update comments

### Tests (4 files)
1. `tests/unit/e2e/test_parallel_executor.py`
2. `tests/unit/e2e/test_scheduler.py`
3. `tests/unit/e2e/test_parallel_rate_limit_handling.py`
4. `tests/unit/e2e/test_rate_limit_recovery.py`
5. `tests/unit/e2e/test_checkpoint_finalizer.py`

## Bonus Fix: Trivy CI

Discovered that `docker-build-timing` CI was failing on main due to `trivy-action@0.30.0` defaulting to Trivy v0.60.0 whose install script fails. Fixed by updating to `trivy-action@0.35.0` and pinning `version: v0.69.3`.
