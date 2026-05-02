---
name: resource-manager-pattern
version: 1.0.0
description: "Replace global mutable semaphores with a dependency-injected ResourceManager class using context managers. Use when: concurrent threads share global locks/semaphores, semaphore leaks cause hangs, or shutdown signals bypass finally blocks."
category: architecture
date: 2026-03-22
user-invocable: false
---

# ResourceManager Pattern: Replacing Global Semaphores

## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Global mutable semaphores leak on crash/shutdown, causing permanent capacity reduction and hangs |
| **Pattern** | Dependency-injected ResourceManager with context-manager-based acquire/release |
| **Language** | Python (threading.Semaphore, threading.Lock, contextlib) |
| **Codebase** | ProjectScylla E2E experiment runner |
| **Impact** | Eliminated 5 synchronization bugs that caused machine crashes |

## When to Use

- Module-level `threading.Semaphore` or `threading.Lock` globals with acquire in one function and release in another
- Semaphore acquire/release split across many stages (e.g., acquire in stage 2, release in stage 15)
- `global` keyword needed to initialize semaphores (PLW0603 violations)
- `configure_X()` functions that are "no-op after first call" — state persists between test runs
- Processes hang after Ctrl+C because semaphore was acquired but never released
- Two threads racing to initialize the same global semaphore object

## Verified Workflow

### Quick Reference

```python
# Before (broken): global semaphores with split acquire/release
_workspace_semaphore: threading.Semaphore | None = None

def configure_resource_limits():
    global _workspace_semaphore  # PLW0603!
    if _workspace_semaphore is None:  # Race condition!
        _workspace_semaphore = threading.Semaphore(N)

def stage_create_worktree():
    _workspace_semaphore.acquire()  # No timeout, no finally!

def stage_cleanup_worktree():  # 14 stages later...
    _workspace_semaphore.release()  # Skipped on ShutdownInterruptedError!

# After (fixed): ResourceManager with context managers
class ResourceManager:
    def __init__(self, max_workspaces, max_agents):
        self._workspace_sem = threading.Semaphore(max_workspaces)
        self._agent_sem = threading.Semaphore(max_agents)
        self._pipeline_lock = threading.Lock()

    @contextlib.contextmanager
    def workspace_slot(self, timeout=300):
        if not self._workspace_sem.acquire(timeout=timeout):
            raise TimeoutError("No workspace slots available")
        try:
            yield
        finally:
            self._workspace_sem.release()  # GUARANTEED on any exception
```

### Step 1: Create ResourceManager class

Create a new module (`resource_manager.py`) with:
- Constructor takes limits as parameters (no globals)
- Context managers for each resource type (`workspace_slot`, `agent_slot`, `pipeline_slot`)
- Timeouts on acquire to prevent infinite hangs
- `finally` blocks guarantee release on ANY exception

### Step 2: Add to context/config dataclass

Add `resource_manager: ResourceManager | None = None` to your shared context (e.g., `RunContext`). Use `TYPE_CHECKING` import to avoid circular deps.

### Step 3: Create once, pass to all

Create `ResourceManager` in the entry point (e.g., `_run_batch()` or `runner.run()`), pass it through to all executors via the context. Do NOT use globals.

### Step 4: Wrap stages with context managers

For stages that spawn subprocesses (agent execution, judge execution):
```python
def _agent_with_slot():
    if ctx.resource_manager:
        with ctx.resource_manager.agent_slot():
            stage_execute_agent(ctx)
    else:
        stage_execute_agent(ctx)
```

For long-lived resources (worktrees spanning many stages), wrap the entire run execution:
```python
ws_ctx = (
    resource_manager.workspace_slot()
    if resource_manager
    else contextlib.nullcontext()
)
with ws_ctx:
    sm.advance_to_completion(...)
```

### Step 5: Add checkpoint write lock

If multiple threads save checkpoints, add a module-level `_checkpoint_write_lock = threading.Lock()` around the serialize+write operation to prevent concurrent writes from losing state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Global semaphores with `configure_resource_limits()` | Module-level `_workspace_semaphore` initialized by function | No reset between runs, race in init, no-op after first call, PLW0603 | Never use mutable module-level globals for concurrency primitives |
| Acquire in stage_create_worktree, release in stage_cleanup_worktree | Split acquire/release across 14 stages | ShutdownInterruptedError bypassed release, leaking slot permanently | Always pair acquire/release in the same scope (context manager) |
| `finally` block after try/except in stage_execute_agent | Manual `_agent_sem_acquired` flag + conditional release | ShutdownInterruptedError re-raised before reaching the post-except code | Context managers are more reliable than manual try/finally for semaphore lifecycle |
| `from scylla.e2e.stages import _workspace_semaphore` in stage_finalization.py | Import global from another module to release it | If global was reassigned, the import gets a stale reference | Pass resources via dependency injection (constructor/context), not module imports |
| Atomic checkpoint writes without lock | PID+TID temp files + atomic rename | Two threads serialize simultaneously, last rename wins — first thread's state lost | Atomic rename prevents corruption but doesn't prevent data loss from concurrent serialization |

## Results & Parameters

### ResourceManager Defaults

```python
# For 16GB WSL2 machine with --threads 15
ResourceManager(
    max_workspaces=cpu_count * 2,  # e.g., 16 for 8-core
    max_agents=min(threads, cpu_count),  # e.g., 8 for 8-core, 15 threads
    threads=15,
)
```

### Context Manager Timeouts

```python
workspace_slot(timeout=300)   # 5 min — worktree creation is fast
agent_slot(timeout=600)       # 10 min — agent execution can queue
pipeline_slot()               # No timeout — Lock() blocks until available
```

### Key Files (ProjectScylla)

| File | Purpose |
| ------ | --------- |
| `scylla/e2e/resource_manager.py` | ResourceManager class (new) |
| `scylla/e2e/stages.py` | RunContext.resource_manager field; agent/judge slot wrappers in build_actions_dict() |
| `scylla/e2e/stage_finalization.py` | Removed global semaphore imports |
| `scylla/e2e/subtest_executor.py` | workspace_slot() wraps entire run execution |
| `scylla/e2e/checkpoint.py` | _checkpoint_write_lock for thread-safe saves |
| `scylla/e2e/runner.py` | Creates ResourceManager, passes to TierActionBuilder |

### Anti-Patterns to Avoid

```python
# BAD: Global mutable semaphore
_sem: threading.Semaphore | None = None

# BAD: "Configure once" function with global keyword
def configure():
    global _sem
    if _sem is None:
        _sem = threading.Semaphore(N)

# BAD: Split acquire/release across functions
def start(): _sem.acquire()
def end(): _sem.release()  # What if exception between start() and end()?

# BAD: Import global from another module to release it
from other_module import _sem
_sem.release()  # Stale reference if _sem was reassigned
```
