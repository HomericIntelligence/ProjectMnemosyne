# Session Notes: Resource Manager Pattern

## Date: 2026-03-22

## Context

ProjectScylla E2E experiment runner was crashing the machine during parallel batch runs.
Root cause: 2,737 uncleaned workspace directories (187GB) + unbounded concurrent claude CLI processes.

## Phase 1: Diagnosis

- haiku-2 run: 7 tests, 120 subtests x 3-5 runs each, --threads 15
- Workspaces: ~1.2GB each (Mojo/ProjectOdyssey repo)
- stage_cleanup_worktree only cleaned PASSING runs
- No OOM in dmesg (WSL2 VM killed by Windows host)

## Phase 2: Initial Fix (Global Semaphores)

Added to stages.py:
- `_workspace_semaphore: threading.Semaphore | None = None`
- `_agent_semaphore: threading.Semaphore | None = None`
- `_pipeline_lock = threading.Lock()`
- `configure_resource_limits()` function

Problems identified:
1. No reset between runs (no-op after first call)
2. Race condition in configure_resource_limits()
3. Workspace semaphore acquired in stage 2, released in stage 15
4. ShutdownInterruptedError bypassed finally block
5. No timeout on acquire — infinite hang on leaked slot
6. Import of global from another module gets stale reference

## Phase 3: Proper Fix (ResourceManager)

Created scylla/e2e/resource_manager.py:
- ResourceManager class with context managers
- workspace_slot(timeout=300) — guaranteed release
- agent_slot(timeout=600) — guaranteed release
- pipeline_slot() — Lock-based serialization

Wired through:
- RunContext.resource_manager field
- build_actions_dict() wraps agent/judge with agent_slot()
- SubtestExecutor wraps run execution with workspace_slot()
- TierActionBuilder passes to run_tier_subtests_parallel()
- runner.py creates ResourceManager, passes to E2ERunner
- manage_experiment.py creates shared ResourceManager for batch

Added checkpoint write lock:
- _checkpoint_write_lock = threading.Lock() in checkpoint.py
- Wraps save_checkpoint() to prevent concurrent write data loss

## Test Results

- 4788 tests pass
- All pre-commit hooks pass (29 hooks)
- No regressions
