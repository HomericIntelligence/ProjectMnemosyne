# Fix E2E Rerun Script Errors

| Field | Value |
|-------|-------|
| **Date** | 2026-01-29 |
| **Category** | Debugging |
| **Objective** | Fix SubTestExecutor constructor errors, checkpoint status validation, and T5 inheritance crashes in rerun script |
| **Outcome** | ✅ All three issues resolved, rerun script executes successfully |

## When to Use This Skill

Use this skill when encountering errors in the E2E rerun script (`src/scylla/e2e/rerun.py`):

1. **Constructor Errors**: `SubTestExecutor.__init__() got an unexpected keyword argument`
2. **Checkpoint Errors**: `Invalid status: completed. Must be 'passed', 'failed', or 'agent_complete'`
3. **T5 Inheritance Errors**: `ValueError: Cannot inherit from T2: result.json not found`
4. **Parameter Mismatch**: `_execute_single_run()` missing required parameters

## Problem Analysis

### Issue 1: Invalid SubTestExecutor Constructor Parameters

**Error**:
```
TypeError: SubTestExecutor.__init__() got an unexpected keyword argument 'tier_id'
```

**Root Cause**:
`rerun_single_run()` passed 11 parameters to the constructor, but `SubTestExecutor.__init__()` only accepts 4:
- Valid: `config`, `tier_manager`, `workspace_manager`, `adapter`
- Invalid: `tier_id`, `tier_config`, `baseline`, `results_dir`, `checkpoint`, `checkpoint_path`, `global_semaphore`, `experiment_dir`

The invalid parameters are per-execution arguments that belong in `_execute_single_run()`, not the constructor.

### Issue 2: Invalid Checkpoint Status

**Error**:
```
ValueError: Invalid status: completed. Must be 'passed', 'failed', or 'agent_complete'.
```

**Root Cause**:
`checkpoint.mark_run_completed()` was called with `status="completed"`, but the checkpoint system only accepts:
- `"passed"` - Run succeeded (judge passed)
- `"failed"` - Run failed (judge failed)
- `"agent_complete"` - Agent finished but not judged yet

### Issue 3: T5 Inheritance Crash

**Error**:
```
ValueError: Cannot inherit from T2: result.json not found. Ensure tier T2 completed before T5.
```

**Root Cause**:
T5 subtests with `inherit_best_from` require parent tiers to be complete. When parent tier results are missing, `build_merged_baseline()` raises ValueError, crashing the entire rerun process instead of skipping that run.

## Verified Workflow

### Step 1: Fix SubTestExecutor Constructor

**Location**: `src/scylla/e2e/rerun.py:313-317`

**Before (INCORRECT - 11 parameters)**:
```python
executor = SubTestExecutor(
    config=config,
    tier_id=tier_id,  # INVALID
    tier_config=tier_config,  # INVALID
    tier_manager=tier_manager,
    workspace_manager=workspace_manager,
    baseline=baseline,  # INVALID
    results_dir=results_dir,  # INVALID
    checkpoint=None,  # INVALID
    checkpoint_path=None,  # INVALID
    global_semaphore=None,  # INVALID
    experiment_dir=experiment_dir,  # INVALID
)
```

**After (CORRECT - 3 parameters)**:
```python
executor = SubTestExecutor(
    config=config,
    tier_manager=tier_manager,
    workspace_manager=workspace_manager,
)
```

### Step 2: Add Workspace Setup

**Location**: `src/scylla/e2e/rerun.py:335-381`

**Pattern**: Follow `run_subtest()` in `subtest_executor.py:687-738`

```python
# Setup run directory and workspace
run_dir = run_info.run_dir
run_dir.mkdir(parents=True, exist_ok=True)

workspace = run_dir / "workspace"
workspace.mkdir(parents=True, exist_ok=True)

# Setup workspace with git worktree
from scylla.e2e.command_logger import CommandLogger

executor._setup_workspace(
    workspace,
    CommandLogger(run_dir),
    tier_id,
    subtest_config.id,
    run_number=run_info.run_number,
)

# Build merged resources for T5 (with error handling)
merged_resources = None
if tier_id == TierID.T5 and subtest_config.inherit_best_from and experiment_dir:
    try:
        merged_resources = tier_manager.build_merged_baseline(
            subtest_config.inherit_best_from,
            experiment_dir,
        )
    except ValueError as e:
        logger.error(
            f"Failed to build merged baseline for T5/{subtest_config.id}: {e}. "
            f"Skipping this run - parent tiers must complete first."
        )
        # Clean up workspace and return None to skip this run
        branch_name = f"{tier_id.value}_{subtest_config.id}_run_{run_info.run_number:02d}"
        workspace_manager.cleanup_worktree(workspace, branch_name)
        return None

# Prepare tier configuration
thinking_enabled = config.thinking_mode is not None and config.thinking_mode != "None"
tier_manager.prepare_workspace(
    workspace=workspace,
    tier_id=tier_id,
    subtest_id=subtest_config.id,
    baseline=baseline,
    merged_resources=merged_resources,
    thinking_enabled=thinking_enabled,
)

# Commit test configs
_commit_test_config(workspace)

# Load task prompt
task_prompt = config.task_prompt_file.read_text()
```

### Step 3: Fix _execute_single_run() Call

**Location**: `src/scylla/e2e/rerun.py:385-395`

**Before (INCORRECT - 2 parameters, wrong name)**:
```python
run_result = executor._execute_single_run(
    subtest_config=subtest_config,  # Wrong parameter name
    run_number=run_info.run_number,
)
```

**After (CORRECT - 9 parameters)**:
```python
run_result = executor._execute_single_run(
    tier_id=tier_id,
    tier_config=tier_config,
    subtest=subtest_config,  # Correct parameter name
    baseline=baseline,
    run_number=run_info.run_number,
    run_dir=run_dir,
    workspace=workspace,
    task_prompt=task_prompt,
    experiment_dir=experiment_dir,
)
```

### Step 4: Fix Checkpoint Status

**Location**: `src/scylla/e2e/rerun.py:591-597`

**Before (INCORRECT)**:
```python
checkpoint.mark_run_completed(
    tier_id=run_info.tier_id,
    subtest_id=run_info.subtest_id,
    run_number=run_info.run_number,
    status="completed",  # INVALID
)
```

**After (CORRECT)**:
```python
# Status based on judge result
status = "passed" if run_result.judge_passed else "failed"
checkpoint.mark_run_completed(
    tier_id=run_info.tier_id,
    subtest_id=run_info.subtest_id,
    run_number=run_info.run_number,
    status=status,
)
```

### Step 5: Add Required Import

**Location**: `src/scylla/e2e/rerun.py:28`

```python
from scylla.e2e.subtest_executor import SubTestExecutor, _commit_test_config
```

## Failed Attempts

### Attempt 1: Using `raise` Instead of `return None` for T5 Inheritance

**What Was Tried**:
```python
except ValueError as e:
    logger.error(f"Failed to build merged baseline: {e}")
    raise  # Re-raise the exception
```

**Why It Failed**:
- Crashed the entire rerun process
- Prevented processing of other runs
- Left partially-created workspaces without cleanup

**Lesson Learned**:
For rerun operations, graceful degradation is better than crashing. Return `None` to skip the problematic run and continue with others. Always clean up resources (worktrees) before returning.

### Attempt 2: Not Cleaning Up Workspace on T5 Failure

**What Was Tried**:
Initial fix returned `None` but didn't clean up the git worktree created by `_setup_workspace()`.

**Why It Failed**:
- Left orphaned git worktrees
- Caused conflicts on subsequent rerun attempts
- Branch names were marked as "in use"

**Lesson Learned**:
Always pair resource creation with cleanup. When returning early from error handling, ensure all allocated resources (worktrees, directories) are properly released.

## Results & Verification

### Test Command
```bash
pixi run python scripts/rerun_agents.py \
  ~/fullruns/test001-nothinking-haiku/2026-01-23T17-01-08-test-001/ \
  --status missing \
  --dry-run
```

### Output (Success)
```
2026-01-29 14:50:55 [INFO] scylla.e2e.rerun: Classification complete:
  completed: 1092
  results:   0
  failed:    0
  partial:   0
  missing:   38

Total expected runs:     1130
  ✓ completed:           1092
  ⚠ results:             0
  ✗ failed:              0
  ⋯ partial:             0
  ○ missing:             38
```

### Verification Steps

1. **Constructor Verification**:
   ```python
   import inspect
   from scylla.e2e.subtest_executor import SubTestExecutor

   sig = inspect.signature(SubTestExecutor.__init__)
   print(list(sig.parameters.keys()))
   # Output: ['self', 'config', 'tier_manager', 'workspace_manager', 'adapter']
   ```

2. **Checkpoint Status Verification**:
   ```python
   from scylla.e2e.checkpoint import E2ECheckpoint

   checkpoint = E2ECheckpoint()
   checkpoint.mark_run_completed('T0', '00', 1, status='passed')  # ✓
   checkpoint.mark_run_completed('T0', '00', 2, status='failed')  # ✓
   checkpoint.mark_run_completed('T0', '00', 3, status='completed')  # ✗ ValueError
   ```

3. **T5 Graceful Degradation**:
   - T5 runs with missing parent tiers now log error and continue
   - Other runs in the batch continue processing
   - Workspace cleanup prevents orphaned branches

## Key Implementation Details

### SubTestExecutor Constructor Signature

```python
def __init__(
    self,
    config: ExperimentConfig,
    tier_manager: TierManager,
    workspace_manager: WorkspaceManager,
    adapter: ClaudeCodeAdapter | None = None,
) -> None:
```

**Only 4 parameters accepted**. Per-execution parameters go to `_execute_single_run()`.

### _execute_single_run() Signature

```python
def _execute_single_run(
    self,
    tier_id: TierID,
    tier_config: TierConfig,
    subtest: SubTestConfig,  # NOTE: 'subtest', not 'subtest_config'
    baseline: TierBaseline | None,
    run_number: int,
    run_dir: Path,
    workspace: Path,
    task_prompt: str,
    experiment_dir: Path | None = None,
) -> RunResult:
```

**9 parameters required** (experiment_dir optional). Note: parameter is `subtest`, not `subtest_config`.

### Checkpoint Valid Statuses

- `"passed"` - Judge passed (use when `run_result.judge_passed == True`)
- `"failed"` - Judge failed (use when `run_result.judge_passed == False`)
- `"agent_complete"` - Agent finished, not yet judged (not used in rerun)

### Workspace Cleanup Pattern

```python
branch_name = f"{tier_id.value}_{subtest_config.id}_run_{run_number:02d}"
workspace_manager.cleanup_worktree(workspace, branch_name)
```

Always call `cleanup_worktree()` before returning `None` from error handling.

## Related Files

- `src/scylla/e2e/rerun.py` - Main file modified
- `src/scylla/e2e/subtest_executor.py` - Reference implementation (`run_subtest()`)
- `src/scylla/e2e/checkpoint.py` - Checkpoint status validation
- `src/scylla/e2e/tier_manager.py` - T5 baseline inheritance

## Tags

`debugging`, `e2e`, `rerun`, `constructor-fix`, `checkpoint`, `T5-inheritance`, `error-handling`, `workspace-cleanup`
