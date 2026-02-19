# Fair Evaluation Baseline - Session Notes

## Session Context

**Date**: 2025-02-15
**Task**: Implement baseline pipeline regression validation for E2E framework
**Outcome**: Successfully implemented with PR #705

## Raw Session Log

### Initial Problem

The E2E framework runs build/lint/test pipeline only AFTER agent execution, with no "before" snapshot. This creates unfair evaluation:

- Agent that breaks a passing build gets same penalty as agent that inherits pre-existing failure
- No way to distinguish regressions from pre-existing issues

### Implementation Plan

Followed the plan from planning phase:

1. Add `baseline_pipeline_summary` field to `E2ERunResult` model
2. Add `baseline_pipeline_str` parameter to `build_task_prompt()`
3. Update judge system prompt with regression instructions
4. Thread `pipeline_baseline` through `run_llm_judge()`
5. Thread `pipeline_baseline` through `_run_judge()`
6. Add baseline persistence helpers
7. Capture baseline in `SubTestExecutor.run_subtest()`
8. Update rubric build_pipeline items
9. Add comprehensive unit tests

### Execution Order

1. Change 6 (models.py) - no dependencies ✅
2. Change 4 (prompts.py) - no dependencies ✅
3. Change 7 (system_prompt.md) - no dependencies ✅
4. Change 3 (llm_judge.py) - depends on #2 ✅
5. Change 2 (judge_runner.py) - depends on #4 ✅
6. Change 5 (subtest_executor helpers) - no dependencies ✅
7. Change 1 (subtest_executor main logic) - depends on #5, #2, #4 ✅
8. Change 8 (rubrics) - independent ✅
9. Tests - after all changes ✅

### Key Import Issues Encountered

**Issue 1**: Wrong module for BuildPipelineResult

- Tried: `from scylla.e2e.pipeline import BuildPipelineResult`
- Error: ModuleNotFoundError
- Fix: `from scylla.e2e.llm_judge import BuildPipelineResult`

**Issue 2**: Circular import in subtest_executor

- Problem: Module-level import caused circular dependency
- Fix: TYPE_CHECKING + string annotations + runtime import in function

**Issue 3**: Invented non-existent PipelineCheckResult class

- Problem: Assumed nested structure based on naming
- Fix: Read actual model definition - BuildPipelineResult has flat structure

**Issue 4**: Wrong field name (lint_passed vs format_passed)

- Problem: Assumed "lint" based on common terminology
- Fix: Checked actual model - field is "format_passed"

### Test Development

Created 9 comprehensive tests in `test_baseline_regression.py`:

1. test_build_task_prompt_with_baseline
2. test_build_task_prompt_without_baseline
3. test_build_task_prompt_baseline_section_before_post_agent
4. test_save_load_pipeline_baseline
5. test_load_pipeline_baseline_missing_file
6. test_load_pipeline_baseline_invalid_json
7. test_run_result_baseline_field
8. test_run_result_baseline_field_none
9. test_baseline_summary_conversion

All tests passing, no regressions in existing test suites.

### Pre-commit Fixes

**Issue**: Line too long in prompts.py

- Line exceeded 100 character limit
- Fix: Split f-string across multiple lines at natural phrase boundary

**Issue**: Undefined BuildPipelineResult in type hints

- Mypy and Ruff couldn't resolve the type
- Fix: Added TYPE_CHECKING import block in subtest_executor.py

### Final Verification

```bash
# All tests passing
✅ tests/unit/e2e/test_baseline_regression.py (9 tests)
✅ tests/unit/judge/test_prompts.py (39 tests)
✅ tests/unit/e2e/ (454 tests)

# Pre-commit hooks passing
✅ ruff-format-python
✅ ruff-check-python
✅ mypy-check-python
✅ markdownlint-cli2
```

### PR Creation

- Branch: `baseline-pipeline-regression-validation`
- Commit: 0871e6b
- PR: #705
- Auto-merge: Enabled with rebase strategy
- Files changed: 8 files, 367 additions, 9 deletions

## Key Learnings

1. **TYPE_CHECKING pattern**: Essential for avoiding circular imports in large codebases

   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from scylla.e2e.llm_judge import BuildPipelineResult

   def func(result: "BuildPipelineResult") -> None:
       from scylla.e2e.llm_judge import BuildPipelineResult  # Runtime import
       # ... use result ...
   ```

2. **Always verify module structure**: Use grep to find actual import paths, don't assume

   ```bash
   grep -r "class BuildPipelineResult" scylla/
   ```

3. **Read model definitions**: Before creating test fixtures, read the actual model structure

   ```python
   # Always check the real model first
   class BuildPipelineResult(BaseModel):
       language: str          # Not nested!
       build_passed: bool     # Flat structure
       format_passed: bool    # Not "lint_passed"
   ```

4. **Checkpoint-aware persistence**: Save immediately, load on resume, skip re-execution

   ```python
   if pipeline_baseline is None:
       pipeline_baseline = _load_pipeline_baseline(results_dir)
       if pipeline_baseline is None:
           pipeline_baseline = _capture_baseline(...)
           _save_pipeline_baseline(results_dir, pipeline_baseline)
   ```

5. **Judge instructions > code enforcement**: Put logic in system prompt for flexibility
   - More maintainable (no code changes needed for iterations)
   - Allows judge to use reasoning
   - Can handle edge cases better

## Architecture Patterns Used

1. **Lazy Initialization**: Baseline captured on first access, cached for subsequent uses
2. **Persistence Layer**: Save/load helpers for checkpoint resume
3. **Parameter Threading**: Optional parameter passed through call stack
4. **Defensive Programming**: Code handles None gracefully even though baseline always present
5. **Separation of Concerns**: Data capture → Formatting → Instruction → Evaluation

## Code Quality Metrics

- **Type Safety**: Full type hints with forward references
- **Test Coverage**: 9 new tests, 100% success rate
- **No Regressions**: 502 existing tests all passing
- **Pre-commit**: All hooks passing (ruff, mypy, markdown-lint)
- **Documentation**: Comprehensive docstrings and comments

## Follow-up Ideas

1. **Multi-level baselines**: Capture at different stages (pre-agent, post-install, post-change)
2. **Baseline diff visualization**: Show side-by-side comparison table in judge prompt
3. **Severity-weighted regressions**: Different penalties for build vs lint failures
4. **Baseline drift detection**: Alert if baseline changes unexpectedly between runs
5. **Historical baseline tracking**: Store baselines over time to detect trends

## Timeline

- Planning: 30 minutes
- Implementation: 90 minutes
  - Models & helpers: 20 minutes
  - Threading & capture: 30 minutes
  - Prompt & instructions: 15 minutes
  - Testing: 25 minutes
- Debugging & fixes: 30 minutes
- PR creation: 10 minutes

**Total**: ~2.5 hours from start to PR merged

## Success Factors

1. ✅ Clear plan with execution order
2. ✅ Incremental implementation (one phase at a time)
3. ✅ Comprehensive testing (unit + integration)
4. ✅ Defensive programming (handle edge cases)
5. ✅ Good error messages (helps debug import issues)
6. ✅ Pre-commit hooks (catch issues early)

## Common Mistakes to Avoid

1. ❌ Assuming module structure based on class names
2. ❌ Module-level imports without checking for circular dependencies
3. ❌ Inventing classes/fields without reading actual definitions
4. ❌ Assuming field names based on common terminology
5. ❌ Relying on auto-formatter for f-string line breaks
6. ❌ Skipping checkpoint resume logic (wastes execution time)
7. ❌ Hardcoding regression logic instead of using judge instructions
