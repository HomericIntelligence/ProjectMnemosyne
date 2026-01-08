# Global Semaphore Parallelism Control

Debugging and implementing global parallelism control using `multiprocessing.Manager().Semaphore()` to limit concurrent agents across all tiers in a multi-tier parallel execution system.

## Overview

This plugin documents the process of fixing three critical E2E runner errors and implementing a global semaphore-based parallelism control system that:

1. Limits concurrent agents **globally** across all tiers (not per-tier)
2. Preserves parallel tier-start behavior (tiers can start in parallel)
3. Uses `Manager().Semaphore()` for cross-process coordination
4. Implements acquire/release in worker processes (not main process)

## Use Cases

- Implementing global concurrency limits across multiple process pools
- Fixing per-tier parallelism issues in multi-tier execution systems
- Sharing semaphores across process boundaries (ProcessPoolExecutor)
- Controlling total concurrent agents in parallel workflows
- Debugging missing properties/attributes in data classes
- Preventing FileNotFoundError when writing to dynamic directory paths

## Key Problems Solved

### 1. AttributeError: Missing `cost_of_pass`
**Error**: `'TierResult' object has no attribute 'cost_of_pass'`
**Solution**: Add `@property` method to calculate from existing data

### 2. FileNotFoundError on Report Save
**Error**: `No such file or directory: '.../T1/09/report.json'`
**Solution**: `mkdir(parents=True, exist_ok=True)` before write

### 3. Per-Tier vs Global Parallelism
**Problem**: `--parallel 6` with 5 tiers = 30 concurrent agents
**Solution**: Global semaphore limits to 6 agents across ALL tiers

## Architecture

**Before (per-tier)**:
```
ThreadPoolExecutor(5 tiers)
  ├── T0: ProcessPoolExecutor(6) ← 6 agents
  ├── T1: ProcessPoolExecutor(6) ← 6 agents
  └── ... (30 total agents!)
```

**After (global)**:
```
ThreadPoolExecutor(5 tiers)
  └── Global Semaphore(6)
      └── Max 6 agents at any time
```

## Critical Insights

1. **Use `Manager().Semaphore()`** - Direct `multiprocessing.Semaphore()` cannot be serialized for ProcessPoolExecutor
2. **Acquire in worker process** - Acquiring in main process blocks task submission
3. **Try/finally for cleanup** - Guarantees semaphore release even on exceptions
4. **Properties for derived values** - Avoids storing redundant/stale data
5. **mkdir before write** - Always create parent directories for dynamic paths

## Related Skills

- `retry-transient-errors`: Network error handling patterns
- `graceful-signal-handling`: Clean shutdown coordination
- `e2e-checkpoint-resume`: Resume capability for long-running jobs

## Results

- ✅ All 108 unit tests passing
- ✅ Reduced max agents from 30 → 6
- ✅ Fixed AttributeError and FileNotFoundError
- ✅ Preserved tier-parallel-start behavior

## Files

- `skills/global-semaphore-parallelism/SKILL.md` - Complete workflow and failed attempts
- `references/notes.md` - Raw session notes and implementation details
