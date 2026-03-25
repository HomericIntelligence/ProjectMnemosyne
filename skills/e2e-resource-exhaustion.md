---
name: e2e-resource-exhaustion
description: "Diagnose and fix machine crashes from memory/disk exhaustion during parallel E2E experiment runs. Use when: experiment runner hangs, WSL2 VM crashes, or disk fills with uncleaned workspaces."
category: optimization
date: 2026-03-22
version: "1.0.0"
user-invocable: false
---

# E2E Resource Exhaustion: Diagnosis and Fix

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Machine crashes during parallel E2E experiment runs due to memory/disk exhaustion |
| **Root Cause** | Unbounded workspace accumulation + unbounded concurrent `claude` CLI processes |
| **Environment** | WSL2 (16GB RAM), 7 concurrent Mojo tests, 120 subtests x 3-5 runs each |
| **Impact** | 2,737 uncleaned workspaces totaling 187GB; 7+ concurrent 500MB processes |
| **Fix** | Eager workspace cleanup, semaphore-based concurrency limits, resource monitoring |

## When to Use

- Machine hangs or crashes during `manage_experiment.py run --threads N`
- WSL2 VM gets killed silently (no OOM traces in `dmesg`)
- `du -sh` on results directory shows >100GB of workspace directories
- Run log ends with only heartbeat messages (process hung)
- `checkpoint.json` shows `tier_state=complete` but `subtest_states` are `runs_in_progress` (not `aggregated`)

## Verified Workflow

### Quick Reference

```bash
# Check workspace accumulation
find ~/fullruns/<run>/ -name "workspace" -type d -maxdepth 5 | wc -l

# Check disk usage per test
for d in ~/fullruns/<run>/2026-*; do du -sh "$d"; done

# Check memory
free -h

# Check run state breakdown per test
python3 -c "
import json
cp = json.load(open('<test>/checkpoint.json'))
rs = cp.get('run_states', {})
counts = {}
for tier in rs:
    for sub in rs[tier]:
        for run, state in rs[tier][sub].items():
            counts[state] = counts.get(state, 0) + 1
print(counts)
"
```

### Step 1: Diagnose the Resource Consumers

Three things consume resources during E2E runs:

1. **Git worktree workspaces** (~1.2GB each for Mojo repos): Created in `stage_create_worktree`, only cleaned for passing runs in `stage_cleanup_worktree`. Failed runs keep workspaces forever.

2. **`claude` CLI subprocesses** (~200-500MB each): Spawned by `stage_execute_agent` (via `replay.sh`) and `stage_execute_judge` (via `_call_claude_judge`). With `--threads 15`, up to 7 concurrent processes.

3. **Build pipeline processes** (`mojo build`, `bazel`, `pixi`): Run under `_pipeline_lock` (serialized), but each can use 1-2GB.

### Step 2: Check checkpoint.json State

```python
# Understand run pipeline stages
# replay_generated -> agent_complete -> diff_captured -> judge_pipeline_run
# -> judge_prompt_built -> judged -> worktree_cleaned
```

Runs stuck at `diff_captured` = agent work done, workspace still exists, judging not started.
Runs at `worktree_cleaned` = fully complete, workspace removed.

### Step 3: Apply Resource Guards

**Fix 1 - Eager workspace cleanup**: Remove the `run_passed` guard in `stage_cleanup_worktree`. Clean up ALL workspaces after judging. Add `--keep-failed-workspaces` flag for debugging.

**Fix 2 - Workspace semaphore**: `threading.Semaphore` in `stage_create_worktree` / `stage_cleanup_worktree` to limit concurrent live workspaces (default: `cpu_count * 2`).

**Fix 3 - Agent semaphore**: `threading.Semaphore` around `stage_execute_agent` and `stage_execute_judge` to limit concurrent `claude` CLI processes (default: `min(threads, cpu_count)`).

**Fix 4 - Judge optimization**: Remove `--allowedTools Read,Glob,Grep` from judge CLI command. All context is already in the prompt (workspace state, git diff, pipeline results). This eliminates workspace dependency and reduces memory overhead.

**Fix 5 - Resource monitoring**: Log RAM/disk at startup, warn if low. Periodic checks in heartbeat thread.

### Step 4: Update run_tests.sh

```bash
pixi run python scripts/manage_experiment.py run \
  --threads 15 --until agent_complete \
  --max-concurrent-agents 6 "${COMMON_ARGS[@]}"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running with `--threads 15` unguarded | Let all 7 tests run with unbounded concurrency | 7 concurrent `claude` processes + 2700+ workspaces exhausted 16GB RAM and 1TB disk | Always limit concurrent subprocesses to `min(threads, cpu_count)` |
| Checking `dmesg` for OOM killer | Expected Linux OOM traces | WSL2 VM gets killed by Windows host silently - no kernel logs survive | On WSL2, memory exhaustion kills the VM, not individual processes |
| Relying on `_pipeline_lock` alone | Lock serializes build pipeline (`mojo build`) | Lock only covers build pipeline, not `claude` CLI processes which are the main RAM consumers | Need separate semaphores for different resource types |
| Keeping failed workspaces for debugging | `stage_cleanup_worktree` only cleaned passing runs | Failed runs (majority) accumulated 187GB of 1.2GB workspaces | Workspace diff is captured at `DIFF_CAPTURED` stage - workspace is no longer needed after judging |

## Results & Parameters

### Resource Limits (recommended for 16GB machine)

```yaml
# run_tests.sh settings
threads: 15                    # batch thread pool size
max_concurrent_agents: 6       # claude CLI process limit
max_concurrent_workspaces: null # auto: cpu_count * 2

# Per-test resource footprint (Mojo repos)
workspace_size: ~1.2GB         # per git worktree checkout
claude_cli_memory: ~200-500MB  # per process
mojo_build_memory: ~1-2GB      # serialized under _pipeline_lock
```

### Key Files

| File | Role |
|------|------|
| `scylla/e2e/stages.py` | `_workspace_semaphore`, `_agent_semaphore`, `configure_resource_limits()` |
| `scylla/e2e/stage_finalization.py` | `stage_cleanup_worktree()` (eager cleanup), `stage_execute_judge()` (agent semaphore) |
| `scylla/e2e/health.py` | `log_resource_preflight()`, `_log_resource_usage()` |
| `scylla/e2e/llm_judge.py` | `_call_claude_judge()` (no tools, no workspace) |
| `config/judge/system_prompt.md` | "Do NOT run any tests" instruction |
| `scylla/e2e/models.py` | `keep_failed_workspaces`, `max_concurrent_workspaces`, `max_concurrent_agents` |
| `scripts/manage_experiment.py` | CLI flags for resource limits |

### Diagnostic Commands

```bash
# Count live workspaces
find ~/fullruns/<run>/ -name "workspace" -type d -maxdepth 5 | wc -l

# Total disk usage
du -sh ~/fullruns/<run>/

# Check if repo is modular monorepo (uses bazel, very memory-hungry)
test -f <repo>/bazelw && echo "modular monorepo" || echo "standalone"

# Check run completion status
python3 -c "
import json
for tier in ['T0','T1','T2','T3','T4','T5','T6']:
    cp = json.load(open('<test>/checkpoint.json'))
    rs = cp['run_states'].get(tier, {})
    counts = {}
    for sub in rs:
        for run, state in rs[sub].items():
            counts[state] = counts.get(state, 0) + 1
    print(f'{tier}: {counts}')
"
```
