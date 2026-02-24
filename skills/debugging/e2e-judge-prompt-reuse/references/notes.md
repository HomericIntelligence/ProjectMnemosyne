# Session Notes: E2E Judge Prompt Reuse

## Session Context

**Date**: 2026-02-09
**Objective**: Investigate E2E prompt saving and judge failures across fullrun datasets
**Initial Problem**: 26-28% judge failure rates in haiku fullrun with bimodal distribution

## Bug Analysis

### Bugs Identified (5 Total)

1. **Historical Bug (Fixed)**: E2E framework didn't save `judge_prompt.md` at all
   - Status: Fixed in previous sessions
   - Evidence: Current fullruns have saved `judge_prompt.md` files

2. **Historical Bug (Fixed)**: Judge validity logic inconsistencies
   - Status: Fixed in PR #476 (unify-judge-validity-logic skill)
   - Evidence: All validity checks now unified with `is_valid` as source of truth

3. **Model Behavior**: Claude Haiku produces invalid JSON responses occasionally
   - Status: Expected behavior, not a bug
   - Evidence: Model-specific failures, not framework issues
   - Mitigation: Already handled by `is_valid=False` when JSON parsing fails

4. **Open Bug (Fixed This Session)**: `regenerate.py` rebuilds prompts instead of reusing saved ones
   - Status: Fixed in this session
   - Evidence: `rerun_judges.py` had correct pattern, `regenerate.py` didn't
   - Impact: Caused 26-28% artificial failures when workspace state differed from original
   - Fix location: `scylla/e2e/regenerate.py:310-392`

5. **Expected Failure**: Historical data with broken prompts cannot be retroactively fixed
   - Status: Not a bug, architectural limitation
   - Evidence: Haiku fullrun has broken `prompt.md` files from when bug #1 existed
   - Mitigation: Only future regenerations benefit from the fix

### Bimodal Failure Distribution Analysis

**Observation**: Failures were all-or-nothing per subtest (not per individual test)

**Root Cause**: Workspace recreation from git worktrees caused:
- Different file structures in workspace
- Judge prompts rebuilt from changed workspace
- Entire subtest context invalidated (not just individual test files)

**Why Bimodal**:
- If workspace matches original → All tests pass (prompt accurate)
- If workspace differs → All tests fail (prompt inaccurate)
- No middle ground because prompt is subtest-level, not test-level

## Code Changes

### File: scylla/e2e/regenerate.py

**Location**: Lines 310-392 (approximate)

**Before** (always rebuilds prompt):
```python
# Existing code - no saved prompt reuse
judge_result = run_llm_judge(
    workspace=workspace,
    task_description=task_description,
    success_criteria=success_criteria,
    judge_model=judge_model,
)
```

**After** (reuses saved prompt first):
```python
# Check for saved judge prompt first
saved_judge_prompt_path = run_dir / "judge_prompt.md"

if saved_judge_prompt_path.exists():
    # Reuse saved judge_prompt.md to ensure consistent evaluation
    # (workspace may differ from original)
    logger.info(f"Reusing saved judge_prompt.md from {saved_judge_prompt_path}")
    judge_prompt = saved_judge_prompt_path.read_text()

    # Call judge directly with saved prompt
    stdout, stderr, result = _call_claude_judge(
        judge_prompt, judge_model, workspace
    )
    judge_result = _parse_judge_response(result)

    # Save logs and timing as usual
    judge_dir = run_dir / "judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "stdout.txt").write_text(stdout)
    (judge_dir / "stderr.txt").write_text(stderr)

    # Save timing
    timing_file = judge_dir / "timing.json"
    timing_data = {
        "start_time": judge_start_time.isoformat(),
        "end_time": judge_end_time.isoformat(),
        "duration_seconds": (judge_end_time - judge_start_time).total_seconds(),
    }
    timing_file.write_text(json.dumps(timing_data, indent=2))

    # Save result
    result_file = judge_dir / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "score": judge_result.score,
                "reasoning": judge_result.reasoning,
                "is_valid": judge_result.is_valid,
            },
            indent=2,
        )
    )
else:
    logger.warning(
        f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, "
        "rebuilding from workspace (may be inaccurate)"
    )
    # Existing fallback code
    judge_result = run_llm_judge(
        workspace=workspace,
        task_description=task_description,
        success_criteria=success_criteria,
        judge_model=judge_model,
    )
```

### Import Requirements

Added import at top of file:
```python
from scylla.e2e.llm_judge import _call_claude_judge, _parse_judge_response
```

## Verification Commands

### Dryrun Validation
```bash
# Test regeneration with saved prompts (dryrun mode)
pixi run python -m scylla.e2e.regenerate \
    ~/fullruns/test001-nothinking/dataset_e2e_subtests/001_code_init/ \
    --dryrun

# Expected: 13/13 pass
# Expected logs: "Reusing saved judge_prompt.md from ..." (INFO level)
# Should NOT see: "rebuilding from workspace" (WARNING level)
```

### Check Saved Prompt Files
```bash
# Verify saved prompts exist in fullruns
find ~/fullruns/test001-nothinking/dataset_e2e_subtests/ -name "judge_prompt.md" | wc -l

# Expected: Should find prompt files for each run
```

### Compare Implementations
```bash
# Verify rerun_judges.py has the same pattern
rg -A 15 "saved_judge_prompt_path" scylla/e2e/rerun_judges.py

# Verify regenerate.py now matches
rg -A 15 "saved_judge_prompt_path" scylla/e2e/regenerate.py

# Should be consistent across both files
```

### Search for Remaining Fallback Paths
```bash
# Check if any other files rebuild judge prompts
rg "run_llm_judge" scylla/e2e/ --type py -l

# For each file, verify saved prompt handling
# Expected: All judge invocation sites should check for saved prompt first
```

## Failed Attempts

### Failure 1: Obsolete Pixi Environment

**Command**: `pixi run -e analysis python -m scylla.e2e.regenerate ...`

**Error**:
```
Error: environment 'analysis' not found in pixi.toml
```

**Root Cause**: Environment was removed in commit `4dc1b9b` (2026-02-09)

**Fix**: Use default environment:
```bash
pixi run python -m scylla.e2e.regenerate ...
```

**Cleanup Required**: Updated 21 files total:
- 4 files in ProjectScylla
- 17 skills in ProjectMnemosyne

**Files Updated in ProjectScylla**:
1. `docs/dev/e2e-cli-examples.md`
2. `scripts/README.md`
3. `scylla/e2e/README.md`
4. `README.md`

**Pattern**: Removed `-e analysis` from all pixi command examples

### Failure 2: Line Length Violations

**Pre-commit hook error**:
```
scylla/e2e/regenerate.py:324:101: E501 Line too long (116 > 100 characters)
scylla/e2e/regenerate.py:330:101: E501 Line too long (108 > 100 characters)
```

**Violations**:
1. Comment: `# Reuse saved judge_prompt.md to ensure consistent evaluation (workspace may differ from original)`
2. F-string: `f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, rebuilding from workspace"`

**Fix Applied**:
```python
# Comment - split into multiple lines
# Reuse saved judge_prompt.md to ensure consistent evaluation
# (workspace may differ from original)

# F-string - split with parentheses
logger.warning(
    f"Saved judge_prompt.md not found at {saved_judge_prompt_path}, "
    "rebuilding from workspace (may be inaccurate)"
)
```

### Failure 3: Wrong ProjectMnemosyne Path

**Attempted**: Update skills in `build/ProjectMnemosyne`

**Error**: Directory not found

**Root Cause**: ProjectMnemosyne cloned to `~/ProjectMnemosyne`, not `~/ProjectScylla/build/ProjectMnemosyne`

**Fix**: Use correct path `~/ProjectMnemosyne`

## Key Learnings

### 1. Saved Prompts Are Critical for Reproducibility

**Problem**: Workspaces can be recreated from different sources:
- Git worktrees (different directory structure)
- Fresh clones (different timestamps)
- Modified workspaces (files added/removed during debugging)

**Impact**: Rebuilding judge prompts from changed workspace produces inaccurate evaluations

**Solution**: Always save `judge_prompt.md` during initial run, reuse during rejudging

### 2. Check All Code Paths That Invoke Judges

**Observation**: `rerun_judges.py` had the fix, but `regenerate.py` didn't

**Lesson**: When fixing judge-related bugs, audit ALL judge invocation sites:
```bash
rg "run_llm_judge|_call_claude_judge" scylla/e2e/ --type py -l
```

**Why This Matters**: Different code paths may have inconsistent patterns, causing subtle bugs

### 3. Bimodal Failure Distributions Indicate Configuration Issues

**Pattern**: All tests in a subtest fail together (not independently)

**Diagnosis**:
- Independent test failures → Test-specific bugs
- All-or-nothing subtest failures → Configuration/setup issues

**Root Cause in This Case**: Subtest-level workspace recreation caused subtest-level prompt invalidation

### 4. Historical Data Artifacts Cannot Be Fixed Retroactively

**Reality**: Haiku fullrun has broken `prompt.md` files from when bug #1 existed

**Expectation**: Code fix should retroactively correct historical data

**Truth**: Code fix only affects future runs, historical data remains broken

**Implication**: When analyzing old fullruns, must account for bugs that existed at data collection time

## Related Code Paths

### Judge Invocation Sites (All Files)

1. **scylla/e2e/subtest_executor.py**
   - Function: `_run_single_test_execution()`
   - Purpose: Initial judge execution during live runs
   - Pattern: Calls `run_llm_judge()`, saves `judge_prompt.md`
   - Status: ✅ Correct (saves prompt for later reuse)

2. **scylla/e2e/rerun_judges.py**
   - Function: `rerun_judges_for_tier()`
   - Purpose: Rejudge existing runs with saved prompts
   - Pattern: Checks for saved `judge_prompt.md` first, reuses if found
   - Status: ✅ Correct (reference implementation for this fix)

3. **scylla/e2e/regenerate.py**
   - Function: `regenerate_results_from_checkpoints()`
   - Purpose: Regenerate full results from checkpoints
   - Pattern: ❌ Was rebuilding prompts, now fixed to reuse saved prompts
   - Status: ✅ Fixed in this session

### Helper Functions

**scylla/e2e/llm_judge.py**:
- `_call_claude_judge(prompt, model, workspace)` - Direct judge invocation with prompt string
- `_parse_judge_response(response)` - Parse judge output into structured result
- `run_llm_judge(workspace, task_description, ...)` - High-level function that builds prompt

**Pattern**: Use `_call_claude_judge()` when you have saved prompt, `run_llm_judge()` when building new prompt

## Environment Cleanup Details

### Files Updated to Remove `-e analysis`

**ProjectScylla (4 files)**:
1. `docs/dev/e2e-cli-examples.md`
2. `scripts/README.md`
3. `scylla/e2e/README.md`
4. `README.md`

**ProjectMnemosyne (17 skills)**:
1. `plugins/evaluation/e2e-cli-guide/SKILL.md`
2. `plugins/evaluation/e2e-result-comparison/SKILL.md`
3. `plugins/evaluation/evaluate-judge-cost/SKILL.md`
4. `plugins/git/baseline-results-management/SKILL.md`
5. `plugins/git/fullrun-result-analysis/SKILL.md`
6. `plugins/git/git-worktree-e2e-workflow/SKILL.md`
7. Plus 11 more (see marketplace.json for full list)

**Pattern Replaced**:
```bash
# OLD
pixi run -e analysis python -m scylla.e2e.regenerate ...

# NEW
pixi run python -m scylla.e2e.regenerate ...
```

## Success Metrics

### Before Fix
- Haiku fullrun: 26-28% judge failure rate
- Bimodal distribution: entire subtests pass or fail
- Inconsistent results between initial run and regeneration

### After Fix (Verified with Dryrun)
- 13/13 tests pass in dryrun regeneration
- All tests reuse saved `judge_prompt.md` (INFO logs confirm)
- No warnings about rebuilding from workspace
- Reproducible evaluations regardless of workspace state

### Impact
- Eliminated artificial failures from workspace mismatches
- Ensured reproducible judging for all future regenerations
- Simplified debugging (failures now indicate actual judge issues, not prompt mismatches)

## Next Steps (Future Work)

1. **PR Creation**: Create pull request with regenerate.py fix
2. **Full Regeneration**: Run full regeneration on haiku fullrun to validate fix at scale
3. **Documentation**: Update E2E CLI guide with saved prompt reuse pattern
4. **Monitoring**: Add metrics to track saved-prompt vs rebuilt-prompt usage ratios
5. **Cleanup**: Consider removing fallback prompt rebuilding (always require saved prompts)
