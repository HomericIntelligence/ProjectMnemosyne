# Technical Notes: Judge Rerun Workspace Corruption Fix

## Session Context

**Date**: 2026-02-09
**Objective**: Fix judge reruns producing incorrect F-grades due to workspace corruption
**Investigation**: `~/fullruns/test001-nothinking` revealed 64% fallback judge usage masking workspace issues

## Root Cause Analysis

### Problem 1: Workspace Corruption Chain
1. User runs `rerun_agents.py` to retry failed runs
2. Script calls `rerun_single_run()` which moves old `run_dir` to `.failed/`
3. Script recreates workspace with `_setup_workspace()` - fresh git worktree
4. Agent runs successfully (or fails), workspace now has new state
5. User runs `rerun_judges.py` to re-evaluate
6. Judge rerun rebuilds prompt from **current** workspace state, not original
7. If workspace was reset, judge sees empty workspace → correct F-grade for empty workspace
8. But F-grade is incorrect for the **original** agent work that was destroyed

### Problem 2: Fallback Judge Masking
1. LLM judge hits rate limit or timeout
2. Exception caught by try/except in `run_llm_judge()` (lines 886-953)
3. `_fallback_judge()` called, returns blanket 0.7/grade-C
4. In test001-nothinking: 2307/3600 judgments were fallback (64%)
5. These passing grades masked the workspace corruption issue

## Code Structure Discovery

### Judge Prompt Storage Location
```
run_dir/
├── judge_prompt.md          # Saved once during original execution
├── judge/
│   ├── judge_01/
│   │   ├── judgment.json    # Individual judge result
│   │   ├── timing.json      # Execution timing
│   │   ├── response.txt     # LLM response
│   │   └── error.log        # Error details (new)
│   ├── judge_02/
│   └── judge_03/
└── workspace/               # Git worktree (may be reset by rerun scripts)
```

### Function Call Hierarchy

```
run_llm_judge()
├── _get_workspace_state()
├── _get_patchfile()
├── _run_build_pipeline()
├── build_task_prompt()      # Builds judge prompt from current workspace state
├── _call_claude_judge()     # Low-level: calls Claude CLI with prompt string
└── _parse_judge_response()  # Parses JSON response
```

**Key Insight**: `_call_claude_judge()` and `_parse_judge_response()` are low-level functions that can be called directly if you already have a pre-built judge prompt. This is what `rerun_judges.py` now does.

### Run Status State Machine

```
MISSING → PARTIAL → FAILED/RESULTS → COMPLETED
   ↓         ↓          ↓                ↓
  Rerun   Rerun    Rerun/Regen      No action
```

- `MISSING`: No run_dir exists → needs full agent execution
- `PARTIAL`: Agent started but incomplete → needs full agent execution
- `FAILED`: Agent ran but failed (stderr, no output) → needs full agent execution
- `RESULTS`: Agent finished, missing result files → needs regeneration only (no agent rerun)
- `COMPLETED`: All files exist → no action needed (unless re-judging)

**Important**: `rerun_experiment()` never calls `rerun_single_run()` for RESULTS status. RESULTS goes through separate regeneration path.

## Implementation Details

### Change 1: Remove Fallback Judge

**File**: `scylla/e2e/llm_judge.py`

Before (lines 886-953):
```python
try:
    stdout, stderr, result = _call_claude_judge(judge_prompt, model, workspace)
    judge_result = _parse_judge_response(result)
    # ... save logs
    return judge_result
except Exception as e:
    logger.warning(f"LLM judge failed, using fallback: {e}")
    fallback_result = _fallback_judge(agent_output)  # 0.7/C score
    # ... save fallback timing
    return fallback_result
```

After (lines 886-919):
```python
stdout, stderr, result = _call_claude_judge(judge_prompt, model, workspace)
judge_result = _parse_judge_response(result)
# ... save logs
return judge_result
# Exception propagates to caller
```

Also deleted `_fallback_judge()` function (was lines 1123-1169).

### Change 2: Reuse Saved Judge Prompt

**File**: `scylla/e2e/rerun_judges.py`

Added logic at line 342:
```python
saved_judge_prompt_path = run_dir / "judge_prompt.md"

if saved_judge_prompt_path.exists():
    judge_prompt = saved_judge_prompt_path.read_text()

    # Bypass run_llm_judge() which would rebuild prompt
    from scylla.e2e.llm_judge import _call_claude_judge, _parse_judge_response, _save_judge_logs

    stdout, stderr, result = _call_claude_judge(judge_prompt, model, workspace)
    judge_result = _parse_judge_response(result)

    # Save logs with rerun flag
    _save_judge_logs(actual_judge_dir, judge_prompt, result, ...)
else:
    logger.warning("Rebuilding from workspace (may be inaccurate)")
    judge_result = run_llm_judge(...)  # Old behavior as fallback
```

### Change 3: Block Workspace Recreation for Completed Runs

**File**: `scylla/e2e/rerun.py`

Added at line 320 (before workspace operations):
```python
if run_info.status in (RunStatus.COMPLETED, RunStatus.RESULTS):
    logger.error(
        f"Refusing to rerun: status is {run_info.status.value}. "
        f"Use regenerate.py for RESULTS or rerun_judges.py for COMPLETED."
    )
    return None
```

**Note**: This is a safety check. Normal operation already filters these out in `rerun_experiment()`.

### Change 4: Exception Handling at Caller Sites

**Files**: `scylla/e2e/subtest_executor.py:1487`, `scylla/e2e/regenerate.py:310`

Both now wrap `run_llm_judge()` in try/except that:
1. Logs error with full context
2. Saves error artifacts (timing.json with `failed: true`, error.log)
3. Either re-raises (subtest_executor) or continues to next (regenerate)

## Testing Results

```bash
$ pixi run python -m pytest tests/unit/e2e/ -x -q
188 passed, 1 skipped in 1.43s

$ grep -r "_fallback_judge" scylla/e2e/
scylla/e2e/__pycache__/llm_judge.cpython-312.pyc: binary file matches  # OK - will regenerate

$ grep -n "fallback" scylla/e2e/llm_judge.py
# No output - all fallback judge code removed

$ grep -n "fallback" scylla/e2e/*.py | wc -l
7  # All unrelated (rate limit fallback, legacy compatibility, etc.)
```

## Coordination Between Scripts

### Correct Usage Pattern

For a run with failed judge:
```bash
# 1. If agent also failed, rerun agent first
pixi run python scripts/rerun_agents.py ~/experiment/ --status failed

# 2. Then rerun judges (will use saved judge_prompt.md)
pixi run python scripts/rerun_judges.py ~/experiment/
```

For a run with missing result files:
```bash
# Use regenerate, not rerun_agents (no need to re-execute agent)
pixi run python scripts/regenerate.py ~/experiment/ --status results
```

### Why This Matters

Before this fix:
1. Running `rerun_agents.py` would destroy workspace
2. Running `rerun_judges.py` would judge the empty workspace
3. Fallback judge would give passing grades, masking the issue

After this fix:
1. `rerun_judges.py` uses saved `judge_prompt.md` (original workspace state)
2. No fallback judge - failures are visible
3. Safety check prevents accidental workspace destruction

## Performance Impact

- **No performance change** for normal execution path
- **Slightly faster** judge reruns (skips workspace state collection and prompt rebuilding)
- **Better debuggability** due to saved error artifacts

## Related Issues Prevented

This fix also prevents:
- Judges evaluating against partial/incomplete agent work if agent was interrupted
- Judges evaluating against wrong git branch if workspace was reset
- Silently passing broken runs due to fallback judge
- Lost debugging information when judges fail

---

**Session Transcript**: `/home/mvillmow/.claude/projects/-home-mvillmow-ProjectScylla/9bfdc6b7-e7ea-4558-a17e-188ded1a7188.jsonl`
