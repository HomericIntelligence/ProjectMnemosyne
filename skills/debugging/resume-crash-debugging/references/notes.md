# Resume Crash Debugging - Session Notes

## Session Context

**Date**: 2026-01-08
**Project**: ProjectScylla
**Session Type**: Debugging and fixing
**Duration**: ~1 hour

## Initial Request

User reported two issues with the e2e experiment framework:

1. **Reports showing 0.000 on resume**: Even though `run_result.json` files contain correct data
2. **Missing judge output**: Agent directories have `stderr.log`, `stdout.log`, etc., but judge directories don't

User also mentioned: "If I re-run again, then the entire report is zero because nothing in the report is reloaded."

## Investigation Process

### Phase 1: Used Skills Registry

Started with `/advise` to search for related patterns:

**Found relevant skills**:
- `e2e-checkpoint-resume` - Core checkpoint/resume patterns
- `checkpoint-result-validation` - Validation before resuming
- `e2e-resume-refactor` - Directory structure with agent/judge separation
- `resume-functionality-tests` - Test patterns
- `token-stats-aggregation` - Hierarchical aggregation

**Key learnings from skills**:
- Must validate filesystem artifacts, not just trust checkpoint
- Use dual persistence: `report.json` + `run_result.json`
- Separate agent/judge directories
- `run_result.json` has full data for resume, `report.json` is simplified

### Phase 2: Exploration

Launched 2 Explore agents in parallel:
1. Report generation flow exploration
2. Agent/judge output storage exploration

**Findings**:
- Reports generated hierarchically: run → subtest → tier → experiment
- Agent has full output capture, judge missing `stderr.log` and raw `stdout.log`
- Resume logic in `subtest_executor.py:606-665` correctly handles missing files

**Initial hypothesis**: Report aggregation bug or checkpoint state mismatch

### Phase 3: User Clarification

Asked user 3 questions:
1. Which files show 0.000? → **All report files**
2. Do run_result.json files have correct data? → **Yes, correct data**
3. What output is missing? → **All: stderr.log, stdout.log, extended thinking**

**This revealed**: The bug is in report regeneration pipeline, not in run execution or checkpoint loading.

### Phase 4: The Error Traceback

User provided the CRITICAL error on 4th resume:

```
FileNotFoundError: [Errno 2] No such file or directory:
'results/2026-01-05T17-46-03-test-001/T6/01/run_01/judge/judgment.json'

  File "subtest_executor.py", line 902, in _execute_single_run
    judgment = _load_judge_result(judge_dir)
  File "subtest_executor.py", line 316, in _load_judge_result
    with open(judge_dir / "judgment.json") as f:
```

**This changed everything!** The issue wasn't report aggregation - the experiment was CRASHING before reports could be generated.

### Phase 5: Root Cause Analysis

Traced the code:

**Validation function** (line 385):
```python
def _has_valid_judge_result(run_dir: Path) -> bool:
    result_file = get_judge_result_file(run_dir)  # Returns judge/result.json
    if not result_file.exists():
        return False
```

**Loading function** (line 316):
```python
def _load_judge_result(judge_dir: Path) -> dict:
    # Load from judgment.json (full result with criteria_scores)
    with open(judge_dir / "judgment.json") as f:  # DIFFERENT FILE!
        data = json.load(f)
```

**The bug**: Validation checks `result.json`, loading reads `judgment.json` - DIFFERENT FILES!

### Phase 6: The Fix

#### Fix 1: File Path Mismatch

Changed `_load_judge_result()` to use the same file:

```python
def _load_judge_result(judge_dir: Path) -> dict:
    # FIX: Use result.json (same file that validation checks)
    result_file = judge_dir / RESULT_FILE
    with open(result_file) as f:
        data = json.load(f)
    return data
```

#### Fix 2: Judge Output Capture

Modified `_call_claude_judge()` to return `(stdout, stderr, response)` tuple instead of just response.

Updated `_save_judge_logs()` to accept and save `raw_stdout` and `raw_stderr`.

## GitHub Issues Created

1. **#152**: FileNotFoundError on resume (HIGH - blocking)
2. **#153**: Reports show 0.000 on resume (HIGH - likely fixed by #152)
3. **#154**: Judge output missing stderr.log (MEDIUM)
4. **#155**: Agent extended thinking capture (LOW)

## Commit

```
fix(e2e): Fix resume bugs - file path mismatch and add judge output logs

Fixes #152, Closes #154
```

Committed as `6df1eef` and pushed to main.

## Lessons Learned

### What Worked

1. **Using `/advise` first** - Found related patterns and anti-patterns
2. **Parallel Explore agents** - Quickly understood codebase structure
3. **Asking user clarifying questions** - Narrowed down the issue
4. **Getting the actual error traceback** - Changed diagnosis completely
5. **Tracing file paths** - Found validation/loading mismatch

### What Didn't Work

1. **Initial hypothesis** - Assumed aggregation bug, was actually simpler (file path)
2. **Exploring aggregation first** - Should have asked for error traceback first
3. **Assuming progressive degradation meant state mismatch** - Was actually file path bug

### Key Insights

- **Progressive failures** (works 1st time, fails Nth) can be file path bugs, not state bugs
- **Always get the error traceback** before diagnosing
- **Validation and loading must use same file path** - easy to miss during refactors
- **File path bugs can look like state sync issues** - "checkpoint says complete but file missing"

## Testing

To verify the fix:

```bash
# Run experiment
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --parallel 6 -v

# Resume 4+ times (previously crashed on 4th)
# Should now work indefinitely
```

## Future Work

- Issue #153 should be resolved by #152 fix (crash was preventing report generation)
- Issue #155 (agent extended thinking) requires investigation into Claude CLI flags
- Consider adding test that validates all validation/loading function pairs use same files
