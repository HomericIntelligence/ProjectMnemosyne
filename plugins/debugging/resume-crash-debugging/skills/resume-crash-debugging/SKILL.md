---
name: resume-crash-debugging
description: Pattern for debugging resume crashes in checkpoint-based systems using error tracebacks and file path validation
category: debugging
date: 2026-01-08
tags: [debugging, resume, checkpoint, e2e, file-path-mismatch]
---

# Resume Crash Debugging

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-08 |
| **Project** | ProjectScylla |
| **Objective** | Debug and fix resume crashes in e2e experiment framework |
| **Outcome** | ✅ Found file path mismatch causing FileNotFoundError on 4th resume |
| **Impact** | HIGH - Unblocked overnight experiment runs |

## When to Use

Use this debugging pattern when:

1. **Progressive resume failures**: Experiment works first time, fails on Nth resume
2. **FileNotFoundError on resume**: Resume crashes looking for files that should exist
3. **Checkpoint/filesystem mismatch**: Checkpoint says complete but files are missing or in wrong location
4. **Validation passes but loading fails**: Validation function checks one file, loading reads a different file
5. **Aggregated reports show zeros**: `run_result.json` has correct data but reports show 0.000

**Triggers**:
- Error: `FileNotFoundError: judgment.json` or similar file not found errors
- User reports: "works first run, crashes on 2nd/3rd/4th resume"
- Console output shows 0.000 scores but individual files have data

## Verified Workflow

### Phase 1: Gather Evidence

**Don't assume the hypothesis - get the actual error**:

```bash
# Run the failing scenario and capture FULL traceback
pixi run python scripts/run_e2e_experiment.py --tiers T0 --runs 1 2>&1 | tee error.log

# Resume multiple times to reproduce
# Resume 1: may work
# Resume 2: may work
# Resume 3: may work
# Resume 4: CRASH with traceback
```

**Critical**: Get the exact file path and line number from traceback, don't speculate.

### Phase 2: Ask User Clarifying Questions

Use `AskUserQuestion` to narrow down the issue:

```python
questions = [
    {
        "question": "When you see zero values, which files show zeros?",
        "options": [
            "Console output only",
            "All report files (report.md, report.json)",
            "Some files only"
        ]
    },
    {
        "question": "Do the run_result.json files have correct data?",
        "options": [
            "Yes, correct data",
            "No, empty or zero",
            "Haven't checked"
        ]
    }
]
```

**What this reveals**:
- If `run_result.json` has correct data but reports show 0.000 → aggregation bug or crash before report gen
- If console shows 0.000 but files are correct → console reads stale data
- If all files show 0.000 → checkpoint/loading bug

### Phase 3: Trace File Path Mismatches

**Pattern**: Validation and loading must use the SAME file path.

**How to find mismatches**:

1. Find the validation function:
```python
def _has_valid_judge_result(run_dir: Path) -> bool:
    result_file = get_judge_result_file(run_dir)  # What file does this return?
    if not result_file.exists():
        return False
```

2. Find the loading function:
```python
def _load_judge_result(judge_dir: Path) -> dict:
    # BUG: Hardcoded path might differ from validation!
    with open(judge_dir / "judgment.json") as f:
        data = json.load(f)
```

3. Check if paths match:
```python
# Validation checks: judge/result.json
# Loading reads: judge/judgment.json
# MISMATCH! This causes FileNotFoundError
```

**In this session**:
- Validation: `get_judge_result_file(run_dir)` → `judge/result.json`
- Loading: hardcoded `judge/judgment.json`
- **Different files!** → FileNotFoundError

### Phase 4: Verify the Fix

**Fix pattern**:

```python
def _load_judge_result(judge_dir: Path) -> dict:
    """Load judge evaluation result from judge/result.json."""
    import json

    # FIX: Use SAME file that validation checks
    result_file = judge_dir / RESULT_FILE  # result.json
    with open(result_file) as f:
        data = json.load(f)
    return data
```

**Test the fix**:
1. Run fresh experiment
2. Resume 4+ times (the scenario that previously crashed)
3. Verify NO FileNotFoundError
4. Verify reports show correct values

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| **Hypothesis: Aggregation bug** | Assumed zeros in reports meant aggregation logic was broken | User's actual error was FileNotFoundError, not aggregation | Always get the actual error traceback before diagnosing |
| **Hypothesis: Checkpoint out of sync** | Thought checkpoint was marking complete before files saved | Actual bug was file path mismatch in loading function | File path bugs can look like state sync issues |
| **Exploring aggregation code first** | Launched agents to understand report generation pipeline | Needed error traceback to find root cause, not exploration | For crashes, start with the error, not architecture exploration |

## Results & Parameters

### Bug Found

**File**: `src/scylla/e2e/subtest_executor.py:316`

**Root Cause**: File path mismatch

```python
# Validation (line 385)
result_file = get_judge_result_file(run_dir)  # judge/result.json

# Loading (line 316) - WRONG FILE
with open(judge_dir / "judgment.json") as f:  # Different file!
```

### Fix Applied

```python
def _load_judge_result(judge_dir: Path) -> dict:
    # FIX: Use result.json (same as validation)
    result_file = judge_dir / RESULT_FILE
    with open(result_file) as f:
        data = json.load(f)
    return data
```

### Verification Command

```bash
# Run experiment
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --parallel 6 -v

# Resume multiple times
# Previously crashed on 4th resume with FileNotFoundError
# Now: works indefinitely
```

### Additional Fix: Judge Output Capture

While debugging, also added missing output files to judge directories:

```python
def _save_judge_logs(..., raw_stdout: str = "", raw_stderr: str = ""):
    # Save raw subprocess output (NEW)
    if raw_stdout:
        (judge_dir / "stdout.log").write_text(raw_stdout)
    if raw_stderr:
        (judge_dir / "stderr.log").write_text(raw_stderr)
```

## Key Learnings

1. **Get the actual error first** - Don't hypothesize, get the traceback
2. **Ask user for file-level details** - Which files have correct data? Which show zeros?
3. **Check validation/loading consistency** - They must use the same file path
4. **Progressive failures suggest state mismatch** - Works 1st time, fails Nth time
5. **File path bugs can masquerade as state bugs** - "Checkpoint says complete but file missing" might be path mismatch
6. **Test resume multiple times** - Bug might only appear on 3rd or 4th resume

## Usage Examples

**Scenario 1: FileNotFoundError on resume**

```bash
# User reports:
# "On 4th resume: FileNotFoundError: judgment.json"

# Debug steps:
1. Get full traceback with line numbers
2. Find validation function that checks for this file
3. Find loading function that reads this file
4. Compare file paths - are they the same?
5. Fix: Make loading use same path as validation
```

**Scenario 2: Reports show 0.000 but run_result.json correct**

```bash
# User reports:
# "run_result.json has score=0.88, but report.md shows 0.000"

# Ask user:
- Does the experiment crash before generating reports? (Check logs)
- If crash → fix crash first, reports will regenerate
- If no crash → check aggregation logic
```

## Related Skills

- `e2e-checkpoint-resume` - Checkpoint/resume patterns
- `checkpoint-result-validation` - Validation before loading
- `e2e-resume-refactor` - Directory structure patterns

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | E2E experiment framework resume bugs | [notes.md](../../references/notes.md) |
