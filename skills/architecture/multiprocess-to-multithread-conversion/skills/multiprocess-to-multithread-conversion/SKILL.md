---
name: multiprocess-to-multithread-conversion
description: "Converting ProcessPoolExecutor to ThreadPoolExecutor for Python 3.14t compatibility. Use when: multiprocessing hangs on free-threaded Python, or workers run external subprocesses making threads sufficient."
category: architecture
date: 2026-03-18
user-invocable: false
---

# MultiProcess to MultiThread Conversion

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `ProcessPoolExecutor` hangs on Python 3.14t (free-threaded) |
| **Root Cause** | `forkserver` serializes arguments; `Manager().Semaphore()` proxies contain `AuthenticationString` that refuses serialization |
| **Solution** | Convert to `ThreadPoolExecutor` with `threading.Semaphore`/`Event`/`dict` |
| **Scope** | 10 source files, 4 test files, ~600 lines of dead code removed |
| **Risk Level** | Medium — requires careful identification of all cross-process patterns |

## When to Use

- Python 3.14t (free-threaded) `ProcessPoolExecutor` hangs silently on `pool.submit()`
- Workers primarily run external CLI subprocesses via `subprocess.run()`/`Popen()` (GIL released during I/O)
- `multiprocessing.Manager()` proxies fail serialization with `forkserver` start method
- Checkpoint disk-merge logic exists solely to handle forked process state divergence

## Verified Workflow

### Quick Reference

1. **Core conversion**: `ProcessPoolExecutor` -> `ThreadPoolExecutor`, `Manager().Semaphore/Event/dict` -> `threading.Semaphore/Event/dict`
2. **Dead code removal**: Delete process-reconstruction code (`from_existing()`, `_retry_with_new_pool`, disk-merge in `save_checkpoint`)
3. **Parameter simplification**: Remove `Manager` param from schedulers/coordinators, pass parent objects directly instead of primitives
4. **Test cleanup**: Remove `Manager()` fixtures, update mock targets for renamed functions
5. **Comment cleanup**: "child process" -> "worker thread", "cross-process" -> "cross-thread"

### Step 1: Identify the Conversion Boundary

Map all files that reference `ProcessPoolExecutor`, `Manager()`, `BrokenProcessPool`, or `SyncManager`:

```bash
grep -rn "ProcessPoolExecutor\|from multiprocessing import Manager\|BrokenProcessPool\|SyncManager" src/
```

### Step 2: Core Conversion (Imports + Primitives)

Replace in each file:
- `from concurrent.futures import ProcessPoolExecutor` -> `ThreadPoolExecutor`
- `from concurrent.futures.process import BrokenProcessPool` -> remove
- `from multiprocessing import Manager` -> `import threading`
- `manager.Event()` -> `threading.Event()`
- `manager.Semaphore(n)` -> `threading.Semaphore(n)`
- `manager.dict()` -> `{}` (threads share memory)

### Step 3: Remove Process-Reconstruction Code

With threads, workers share the parent's objects directly. Remove:
- `from_existing()` classmethods that recreated managers in child processes
- Primitive parameter decomposition (passing `tiers_dir`, `base_repo`, `repo_url` instead of parent objects)
- `BrokenProcessPool` exception handling and retry-with-new-pool logic

### Step 4: Remove Disk-Merge Logic

Forked processes had stale checkpoint copies, requiring read-modify-write merges. With threads sharing one checkpoint object:
- Remove `save_checkpoint()` disk-merge (read existing -> deep-merge -> write)
- Remove `checkpoint_merge_lock` from action builders
- Remove disk-reload in `mark_checkpoint_completed()`
- Keep atomic write pattern (temp file + rename) for crash safety

### Step 5: Update Tests

- Remove `multiprocessing.Manager()` fixtures
- Update function references (`_run_subtest_in_process_safe` -> `_run_subtest_safe`)
- Update mock targets (`parallel_executor._run_subtest_in_process` -> `_run_subtest`)
- Delete tests for removed functions (`TestWorkspaceManagerFromExisting`, disk-merge tests)
- Update call signatures in test helpers (pass `tier_manager`/`workspace_manager` instead of primitives)

### Step 6: Semantic Rebase Strategy

When the final commit subsumes earlier incremental fixes:
1. Resolve the current conflict by merging both sides
2. Edit `.git/rebase-merge/git-rebase-todo` to `drop` superseded intermediate commits
3. Keep only the defense-in-depth commit + final conversion commit
4. Resolve any remaining conflicts from the final commit

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Incremental lock fixes | Added `filelock.FileLock` for pipeline serialization, then removed it | Each fix addressed a symptom, not the root cause (processes themselves) | When you are fixing serialization issues in multiprocessing, consider whether threads would eliminate the entire problem class |
| Keeping `_checkpoint_write_lock` | Kept a threading.Lock for checkpoint writes after converting to threads | Unnecessary — threads sharing one checkpoint object don't need merge locks | Identify which synchronization primitives exist solely because of process boundaries |
| Rebase with all intermediate commits | Tried to rebase all 7 commits onto main | Created cascading conflicts since each commit partially undid the previous one | When commits form a superseding chain, drop intermediates and keep only the final result |
| Making scheduler serializable | Made scheduler serializable for `forkserver` | Still failed because `Manager().Semaphore()` proxies in the coordinator could not be serialized | The real fix is switching to threads, not making everything serializable |

## Results & Parameters

### Files Changed (Source)

| File | Change |
|------|--------|
| `parallel_executor.py` | Core conversion + delete 3 functions (~400 lines removed) |
| `scheduler.py` | `Manager.Semaphore` -> `threading.Semaphore` |
| `runner.py` | Remove `Manager`, `BrokenProcessPool`, `checkpoint_merge_lock` |
| `workspace_manager.py` | Delete `from_existing()` classmethod |
| `checkpoint_finalizer.py` | Remove disk-merge from `mark_checkpoint_completed` |
| `tier_action_builder.py` | Remove `checkpoint_merge_lock` + disk-reload block |
| `checkpoint.py` | Remove read-modify-write merge from `save_checkpoint` |
| `subtest_executor.py` | Update lazy import proxy for renamed functions |
| `stages.py` | Update comments: "child process" -> "worker thread" |

### Key Decision: Why Threads Are Sufficient

Workers run external CLI subprocesses (`claude` CLI, `git`, `pytest`) via `subprocess.run()`/`Popen()`. The GIL is released during:
- `subprocess.Popen.communicate()` (waiting for child process I/O)
- `subprocess.run()` (blocking on external process)
- File I/O operations

CPU-bound Python code is minimal — the real work happens in external processes.

### Verification Commands

```bash
pixi run python -m pytest tests/unit/e2e/ -x -q     # E2E unit tests
pixi run python -m pytest tests/unit/ -x -q          # All unit tests
pixi run pre-commit run --all-files                   # Linting + type checks
```
