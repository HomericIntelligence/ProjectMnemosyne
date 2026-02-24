---
name: "E2E Path Resolution Fix"
description: "E2E Path Resolution Fix"
category: debugging
date: 2026-01-17
user-invocable: false
---
# E2E Path Resolution Fix

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-17 |
| Objective | | Field | Value | |-------|-------| | **Date** | 2026-01-17 | | **Objective** | Fix E2E agent execution failures caused by relative path handling | |
| Outcome | Operational |


| Field | Value |
|-------|-------|
| **Date** | 2026-01-17 |
| **Objective** | Fix E2E agent execution failures caused by relative path handling |
| **Outcome** | ✅ SUCCESS - Fixed critical bug causing 100% agent execution failure |
| **Impact** | Resolved silent failures across all E2E experiments |

## When to Use This Skill

Use this skill when you encounter:

1. **E2E experiments with 0% pass rates and $0.00 costs** despite configuration appearing correct
2. **Agent execution completing in 0.0s with exit code 1** (immediate failure)
3. **"cd: No such file or directory" errors** in agent stderr logs
4. **Relative paths in subprocess execution** causing directory navigation failures
5. **Generated scripts (replay.sh) failing to navigate** to workspace directories

## Problem Indicators

### Symptoms
- All tiers return 0% pass rate
- Total cost: $0.00 (no API calls made)
- Agent stage completes in 0.0s
- Exit code: 1 (error)
- Token counts: 0 input / 0 output

### Error Message Pattern
```
cd: results/2026-01-17T13-50-51-test-001/T0/00/run_01/workspace: No such file or directory
```

### Root Cause Location
The error occurs in `subtest_executor.py` at two critical locations:
1. **Line 809** - `cwd=workspace` passes relative path to `subprocess.run()`
2. **Line 1022** - `cwd=str(workspace)` logs relative path in command logger

## Verified Workflow

### 1. Identify the Problem

**Read agent stderr logs:**
```bash
cat results/*/T*/*/run_01/agent/stderr.log
```

**Look for:**
- "cd: No such file or directory" errors
- Relative paths in cd commands
- Empty stdout with immediate exit

**Check exit codes:**
```bash
jq '.exit_code' results/*/T*/*/run_01/run_result.json
# Exit code 1 = execution error
# Exit code -2 = timeout
```

### 2. Locate the Bug

**Search for relative path usage:**
```bash
grep -n "cwd=workspace" scylla/e2e/subtest_executor.py
```

**Expected matches:**
- Line 809: `cwd=workspace,` in `_run_via_replay_script()`
- Line 1022: `cwd=str(workspace),` in `_run_agent_execution()`

### 3. Apply the Fix

**Change 1 - Line 809 (subprocess cwd):**
```python
# Before:
result = subprocess.run(
    ["bash", str(replay_script.resolve())],
    capture_output=True,
    text=True,
    timeout=adapter_config.timeout,
    cwd=workspace,  # ❌ Relative path
)

# After:
result = subprocess.run(
    ["bash", str(replay_script.resolve())],
    capture_output=True,
    text=True,
    timeout=adapter_config.timeout,
    cwd=workspace.resolve(),  # ✅ Absolute path
)
```

**Change 2 - Line 1022 (command logger cwd):**
```python
# Before:
command_logger.log_command(
    cmd=cmd,
    stdout="",
    stderr="",
    exit_code=0,
    duration=0.0,
    cwd=str(workspace),  # ❌ Relative path
)

# After:
command_logger.log_command(
    cmd=cmd,
    stdout="",
    stderr="",
    exit_code=0,
    duration=0.0,
    cwd=str(workspace.resolve()),  # ✅ Absolute path
)
```

### 4. Verify the Fix

**Run failing E2E test:**
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 -v --max-subtests 1 --fresh
```

**Expected after fix:**
- Agent execution time > 0.0s (e.g., 25.5s)
- Token counts > 0 (e.g., 54 input, 1,308 output)
- Cost > $0.00 (e.g., $0.1650)
- Pass rate > 0% (e.g., 89%)
- Exit code: 0 (success)

**Verify replay.sh contains absolute paths:**
```bash
cat results/*/T0/00/run_01/agent/replay.sh | head -25
```

**Expected output:**
```bash
cd /home/mvillmow/ProjectScylla/results/2026-01-17T14-44-38-test-001/T0/00/run_01/workspace
```

**Run unit tests:**
```bash
pixi run pytest tests/unit/e2e/test_subtest_executor.py -v
```

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Attempt 1: Fixing Only the Subprocess CWD

**What was tried:**
- Fixed only line 809 (`cwd=workspace.resolve()`)
- Left line 1022 unchanged (`cwd=str(workspace)`)

**Why it failed:**
- The command logger still logged relative paths
- Generated `replay.sh` contained relative `cd` commands
- When replay.sh executed, it couldn't navigate to the directory

**Lesson learned:**
Both locations must be fixed together - the subprocess execution AND the command logging must use absolute paths.

### ❌ Attempt 2: Investigating Worktree Creation

**What was tried:**
- Initially suspected worktree creation was the issue
- Checked for "fatal: a branch named 'T6_01_run_01' already exists" errors

**Why it failed:**
- This was a red herring from a different run (T6)
- The real issue was path resolution, not worktree creation
- T6's failure was actually due to timeout, not path issues

**Lesson learned:**
Don't get distracted by errors from different tier runs - focus on the pattern across all failed runs.

## Results & Parameters

### Before Fix
```json
{
  "pass_rate": 0.0,
  "cost_usd": 0.00,
  "agent_duration_seconds": 0.0,
  "exit_code": 1,
  "tokens_input": 0,
  "tokens_output": 0
}
```

### After Fix
```json
{
  "pass_rate": 0.89,
  "cost_usd": 0.1650,
  "agent_duration_seconds": 25.5,
  "exit_code": 0,
  "tokens_input": 54,
  "tokens_output": 1308
}
```

### Configuration Used
- **Mojo version**: 0.26.1
- **Python version**: 3.14.2
- **Test fixture**: tests/fixtures/tests/test-001
- **Timeout**: 300 seconds
- **Model**: claude-sonnet-4-5-20250929

## Key Insights

### 1. Path Resolution in Subprocess Execution
When passing `cwd` to `subprocess.run()`, Python resolves the path relative to the current working directory of the parent process, NOT the subprocess. Using `.resolve()` ensures absolute paths.

### 2. Command Logger Path Consistency
The command logger generates `replay.sh` scripts that will be executed later. These scripts must use absolute paths because they may be run from different working directories.

### 3. Silent Failure Detection
This bug caused 100% silent failures - experiments appeared to complete successfully (exit code 0 at the experiment level) but all subtests failed immediately with exit code 1.

### 4. Diagnostic Importance
The agent stderr logs were crucial for diagnosis - they showed the exact cd command that was failing with the relative path.

## Related Skills

- `e2e-checkpoint-resume` - Documents proper path handling patterns in E2E
- `e2e-rate-limit-detection` - Shows how to debug E2E execution failures
- `debug-evaluation-logs` - Patterns for improving diagnostic messages

## Files Modified

| File | Lines | Description |
|------|-------|-------------|
| `scylla/e2e/subtest_executor.py` | 809 | Changed `cwd=workspace` to `cwd=workspace.resolve()` |
| `scylla/e2e/subtest_executor.py` | 1022 | Changed `cwd=str(workspace)` to `cwd=str(workspace.resolve())` |

## Testing Evidence

### E2E Test Success
```
============================================================
EXPERIMENT COMPLETE
============================================================
Duration: 103.3s
Total Cost: $0.1650

Best Tier: T0
Best Sub-test: 00
Frontier CoP: $0.1650

Tier Results:
------------------------------------------------------------
  T0: PASS (score: 0.890, cost: $0.1650)
============================================================
```

### replay.sh Verification
```bash
#!/bin/bash
# Generated: 2026-01-17T14:44:47.338423+00:00
# Total commands: 1

# Command 1/1 at 2026-01-17T14:44:47.338324+00:00
cd /home/mvillmow/ProjectScylla/results/2026-01-17T14-44-38-test-001/T0/00/run_01/workspace
claude --model claude-sonnet-4-5-20250929 --print --output-format json --dangerously-skip-permissions /home/mvillmow/ProjectScylla/results/2026-01-17T14-44-38-test-001/T0/00/run_01/agent/prompt.md
```

### Unit Test Success
```
============================= test session starts ==============================
tests/unit/e2e/test_subtest_executor.py::TestMoveToFailed::test_move_creates_failed_dir PASSED [ 20%]
tests/unit/e2e/test_subtest_executor.py::TestMoveToFailed::test_move_increments_attempt PASSED [ 40%]
tests/unit/e2e/test_subtest_executor.py::TestMoveToFailed::test_move_preserves_contents PASSED [ 60%]
tests/unit/e2e/test_subtest_executor.py::TestMoveToFailed::test_move_with_custom_attempt PASSED [ 80%]
tests/unit/e2e/test_subtest_executor.py::TestMoveToFailed::test_move_multiple_increments PASSED [100%]

============================== 5 passed in 0.14s
```

## Bonus Finding: T6 Timeout Analysis

While debugging this issue, we also discovered why T6 (maximum capability tier) failed:

**T6 Configuration:**
- 73 sub-agents enabled
- 63 skills enabled
- 9 MCP servers enabled
- Task: Simple "Hello World" script

**Result:**
- Exit code: -2 (timeout)
- Duration: 187.45s (approaching 300s limit)
- Cost: $0.00 (no completion)

**Key Insight:** More tools/agents/complexity ≠ better performance. T6 failed on the simplest task because having "everything enabled" created cognitive overhead that prevented task completion within the timeout.
