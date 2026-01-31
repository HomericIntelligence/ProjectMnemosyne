# Skill: Preserve Workspaces on E2E Experiment Re-runs

| Field | Value |
|-------|-------|
| **Date** | 2026-01-08 |
| **Objective** | Prevent workspace destruction when re-running E2E experiments |
| **Outcome** | ✅ SUCCESS - Workspaces preserved for passing runs |
| **Category** | evaluation |
| **PR** | https://github.com/HomericIntelligence/ProjectScylla/pull/161 |

## Problem Statement

When re-running E2E experiments using the checkpoint resume feature, all workspaces were being wiped out and recreated from scratch, even if:
- The run had already completed successfully (checkpoint marked as "passed")
- The workspace contained valid test results
- No changes were made to the experiment configuration

This caused:
- Loss of previous test results and artifacts
- Unnecessary git worktree recreation overhead
- Inability to inspect workspaces from passing runs

## When to Use This Pattern

Apply this pattern when:
- ✅ You have a checkpoint/resume system that tracks completed work
- ✅ Workspace setup is expensive (git clone, worktree creation, file copying)
- ✅ Completed work produces artifacts that should be preserved
- ✅ Re-runs are common (debugging, iterative development, resuming after rate limits)
- ✅ Workspace state is idempotent based on checkpoint status

Do NOT use this pattern when:
- ❌ Workspaces must always be fresh (no caching allowed)
- ❌ Checkpoint data doesn't reliably track workspace state
- ❌ Workspace mutations can occur outside your control

## Root Cause Analysis

### Code Location
`/home/mvillmow/ProjectScylla/src/scylla/e2e/subtest_executor.py:678-697`

### The Problem Flow

1. **Run loop creates workspace** (line 678-680):
   ```python
   workspace = run_dir / "workspace"
   workspace.mkdir(parents=True, exist_ok=True)
   ```

2. **Workspace setup called unconditionally** (line 684-686):
   ```python
   self._setup_workspace(
       workspace, CommandLogger(run_dir), tier_id, subtest.id, run_number=run_num
   )
   ```

3. **Setup method aggressively cleans up** (line 1088-1128):
   - If git branch exists (from previous run): **deletes entire workspace**
   - Removes worktree, deletes branch, runs `shutil.rmtree(workspace_abs)`
   - Recreates everything from scratch

### Why It Happened

The workspace setup was designed to be **idempotent** - always creating fresh state. However:
- The checkpoint system only tracked **run completion status** (passed/failed)
- No logic existed to check "does this workspace contain valid results?"
- The recovery path assumed "branch exists = stale/corrupted workspace"

## Verified Workflow

### Implementation Pattern

**Location**: `src/scylla/e2e/subtest_executor.py:683-697`

```python
# Check if run already passed and workspace exists - preserve it
run_status = None
if checkpoint:
    run_status = checkpoint.get_run_status(tier_id.value, subtest.id, run_num)

if run_status == "passed" and workspace.exists():
    logger.info(
        f"Run {run_num} already passed (checkpoint), preserving existing workspace"
    )
    # Skip workspace setup - use existing workspace
else:
    # Setup workspace with git worktree
    self._setup_workspace(
        workspace, CommandLogger(run_dir), tier_id, subtest.id, run_number=run_num
    )
```

### Key Decision Points

1. **Check checkpoint BEFORE workspace setup** - Not after
2. **Verify both conditions**:
   - `run_status == "passed"` - Checkpoint confirms success
   - `workspace.exists()` - Physical workspace still present
3. **Skip setup entirely** - Don't partially initialize
4. **Log the preservation** - Makes debugging easier

### Why This Works

- **Checkpoint is source of truth**: If marked "passed", the workspace is valid
- **Existence check catches deletions**: If workspace missing, recreate it
- **Idempotent for new runs**: Failed or new runs still get fresh workspaces
- **Preserves git worktrees**: No branch conflicts or worktree churn

## Failed Attempts

### ❌ Attempt 1: Modify workspace recovery logic only

**Approach**: Add preservation check inside `_setup_workspace()` recovery path (line 1125-1128)

```python
# In _setup_workspace, around line 1125-1128
if workspace_abs.exists():
    should_preserve = self._should_preserve_workspace(workspace_abs, tier_id, subtest_id, run_number)
    if should_preserve:
        logger.info(f"Preserving existing workspace with passing results: {workspace_abs}")
        return  # Skip workspace setup
    else:
        shutil.rmtree(workspace_abs)
```

**Why it failed**:
- Recovery path only executes when git branch already exists
- Requires passing checkpoint context deep into `_setup_workspace()`
- Still creates git worktree command before checking
- More complex - checks happen too late in the flow

**Lesson**: Check conditions BEFORE starting expensive operations, not during recovery.

### ❌ Attempt 2: Add workspace cleanup after run completes

**Approach**: After each run, clean up workspaces for failing runs (after line 723)

```python
if run_result.judge_passed:
    # Preserve workspace for passing run
    pass
else:
    # Clean up workspace for failing run
    self.workspace_manager.cleanup_worktree(workspace, branch_name)
```

**Why it failed**:
- Solves the wrong problem - issue is **re-creation on re-run**, not cleanup
- Doesn't address the core issue: workspace destruction during resume
- Adds cleanup overhead after every run
- Workspaces for failed runs might still be useful for debugging

**Lesson**: Identify the actual problem point - workspace is destroyed during **setup**, not during **cleanup**.

## Results & Parameters

### Test Command
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T1 T2 T3 T4 T5 T6 \
    --runs 1 --parallel 2 -v
```

### Behavior Before Fix
```
Run 1: Creates workspace, runs test, passes ✅
Re-run: Deletes workspace, recreates workspace, runs test again ❌
```

### Behavior After Fix
```
Run 1: Creates workspace, runs test, passes ✅
Re-run: Preserves workspace (checkpoint passed), skips setup ✅
```

### Verification Steps
1. Run experiment once - observe workspace creation
2. Check checkpoint: `cat results/<experiment>/checkpoint.json`
3. Re-run same experiment
4. Verify log message: "Run N already passed (checkpoint), preserving existing workspace"
5. Confirm workspace directory unchanged: `ls -la results/<experiment>/T*/*/run_*/workspace/`

## Related Patterns

### Checkpoint-Driven State Management
- **Pattern**: Use checkpoint as source of truth for what's been completed
- **Key**: Validate physical state (file exists) matches logical state (checkpoint)
- **Apply to**: Resume systems, incremental builds, distributed task queues

### Conditional Expensive Operations
- **Pattern**: Check if operation is needed BEFORE starting it
- **Key**: Fast pre-conditions (checkpoint lookup) before slow operations (git worktree)
- **Apply to**: Network calls, file I/O, subprocess execution

### Idempotent with Caching
- **Pattern**: Operations are idempotent but cached when safe
- **Key**: Clear invalidation rules (checkpoint status + file existence)
- **Apply to**: Build systems, test harnesses, data pipelines

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `src/scylla/e2e/subtest_executor.py` | +12, -4 | Add checkpoint check before workspace setup |
| `.gitignore` | +2 | Ignore worktrees/ directory |
| `src/scylla/e2e/llm_judge.py` | +39, -2 | Better error handling (related improvement) |

## Key Learnings

1. **Checkpoints enable smart caching** - Don't just track completion, use it to skip redundant work
2. **Validate both logical and physical state** - Checkpoint says "passed" AND workspace exists
3. **Pre-conditions beat recovery** - Check before starting, not during cleanup
4. **Log state decisions** - Makes resume behavior visible and debuggable
5. **Idempotent ≠ Always Fresh** - Idempotent operations can cache when safe

## References

- Checkpoint system: `/home/mvillmow/ProjectScylla/src/scylla/e2e/checkpoint.py`
- Workspace manager: `/home/mvillmow/ProjectScylla/src/scylla/e2e/workspace_manager.py`
- Git worktree docs: https://git-scm.com/docs/git-worktree
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/161
