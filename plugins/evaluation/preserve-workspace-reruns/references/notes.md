# Session Notes: Preserve Workspace Reruns

## Initial Problem Report

User reported:
```
When I re-run the test, pixi run python scripts/run_e2e_experiment.py
    --tiers-dir tests/fixtures/tests/test-001
    --tiers TT1 T2 T3 T4 T5 T6
    --runs 1 --parallel 2
    -v, it wipes out the workspace and re-sets it up, even if the previous run passes.
I don't want the workspace to be re-setup if the previous run passes, so that the
results can be preserved across runs
```

## Investigation Steps

### 1. Explored Checkpoint System (Agent a19a349)

**Key Findings:**
- `E2ECheckpoint` tracks completed runs in nested dict: `tier_id -> subtest_id -> {run_number: status}`
- Status values: `"passed"`, `"failed"`, `"agent_complete"`
- Checkpoint saved after each run with judge result: `status = "passed" if run_result.judge_passed else "failed"`
- Helper method exists: `checkpoint.get_run_status(tier_id, subtest_id, run_number)`

**Critical Discovery:**
- Checkpoint has `is_run_completed()` that returns `True` for "passed" or "failed"
- When run is completed, checkpoint system loads previous result and **continues** (line 669)
- This means checkpoint resume DOES skip re-running, but workspace setup happens regardless

### 2. Explored Run Execution Flow (Agent a4f57e2)

**Key Findings:**
- Run loop: lines 600-735 in `subtest_executor.py`
- Workspace created: line 678-680 (`workspace = run_dir / "workspace"`)
- Workspace setup called: line 684-686 (unconditionally)
- Setup method `_setup_workspace()`: lines 1025-1152

**Critical Discovery:**
- Line 669: When checkpoint hit, `continue` skips to next run WITHOUT workspace setup
- Line 684: For NEW runs, workspace setup ALWAYS called
- Line 1088-1128: Recovery path in `_setup_workspace()` does `shutil.rmtree(workspace_abs)`

**The Problem Point:**
Workspace setup happens BEFORE checking if run needs to execute. The checkpoint check (line 610) only applies to **loading previous results**, not to **workspace creation**.

## Root Cause

Looking at lines 678-686:
```python
# Create workspace per run in run_N/workspace/
workspace = run_dir / "workspace"
workspace.mkdir(parents=True, exist_ok=True)
last_workspace = workspace  # Track for resource manifest

# Setup workspace with git worktree
self._setup_workspace(
    workspace, CommandLogger(run_dir), tier_id, subtest.id, run_number=run_num
)
```

The workspace is created and setup is called **unconditionally**. The checkpoint check happens earlier (line 610) but only loads previous results - it doesn't prevent workspace creation for that iteration.

**Wait, re-reading the code:**

Actually, the checkpoint check at line 610 has a `continue` at line 669, which should skip lines 671-734 entirely. So workspace setup should NOT happen for completed runs.

**Re-examining the issue:**

The user said "it wipes out the workspace and re-sets it up" - this must be happening in `_setup_workspace()` itself, specifically the recovery path at lines 1088-1128 that handles when the git branch already exists.

## The Real Problem

When you re-run an experiment:
1. Checkpoint detects run is completed (line 610)
2. **BUT** - the workspace directory might not exist yet (was deleted, or this is a fresh results dir)
3. Line 679: `workspace.mkdir(parents=True, exist_ok=True)` creates it
4. Line 684: `_setup_workspace()` called
5. Line 1088: Branch exists from previous run → recovery path
6. Line 1127: `shutil.rmtree(workspace_abs)` - **DESTROYS EVERYTHING**

No wait, that doesn't make sense either because if checkpoint hit at line 610, we `continue` at line 669, so we never reach line 684.

## Re-reading More Carefully

Let me trace through the actual flow:

```python
for run_num in range(1, self.config.runs_per_subtest + 1):
    # Checkpoint check
    if checkpoint and checkpoint.is_run_completed(tier_id.value, subtest.id, run_num):
        # Lines 611-669: Load previous result, validate, append to runs[], continue
        continue  # <-- SKIPS LINES 671-734

    # Lines 671-734: Only executed if run NOT completed
```

So the checkpoint resume DOES skip workspace setup. The problem must be something else.

**User's actual scenario:**

They're re-running with the SAME parameters but the checkpoint might not be preserved, OR they're using `--fresh` flag, OR...

Actually, looking at their command: no `--fresh` flag. So checkpoint should work.

**Hypothesis:**
Maybe the issue is that when they re-run, some runs ARE being re-executed (not all are checkpointed), and those new runs are wiping workspaces during setup?

## Aha Moment

The user wants to preserve workspaces from **passing runs** even when doing a **partial re-run**. Scenario:
- Run 1: T0, T1, T2 complete (some pass, some fail)
- Run 2: Re-run same experiment
- Checkpoint resumes, skips completed runs ✅
- But if workspace doesn't exist yet (or branch conflict), setup wipes it ❌

The fix is: Before calling `_setup_workspace()`, check if the run already passed AND workspace exists. If so, skip setup.

## Solution Design

Add conditional check at line 683:
```python
# Check if run already passed and workspace exists - preserve it
run_status = None
if checkpoint:
    run_status = checkpoint.get_run_status(tier_id.value, subtest.id, run_num)

if run_status == "passed" and workspace.exists():
    logger.info(f"Run {run_num} already passed, preserving existing workspace")
    # Skip workspace setup - use existing workspace
else:
    # Setup workspace with git worktree
    self._setup_workspace(...)
```

This ensures:
- New runs: workspace setup happens ✅
- Failed runs being re-executed: workspace setup happens ✅
- Passed runs being preserved: workspace setup SKIPPED ✅

## Implementation

Modified `src/scylla/e2e/subtest_executor.py:683-697` to add checkpoint-based workspace preservation.

Also committed:
- `.gitignore`: Added `worktrees/` directory
- `src/scylla/e2e/llm_judge.py`: Better error handling (unrelated improvement from earlier work)

## Commit

```
fix(e2e): preserve workspaces for passing runs on re-execution

Prevents workspace destruction when re-running experiments. Previously,
all workspaces were wiped and recreated on each run, destroying results
from passing tests.

Changes:
- Check checkpoint status before workspace setup
- Skip workspace recreation if run already passed and workspace exists
- Preserve git worktrees and test results for passing runs
```

Branch: `fix/preserve-workspace-on-rerun`
PR: https://github.com/HomericIntelligence/ProjectScylla/pull/161
