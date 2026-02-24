# Raw Session Notes: Judge Criteria Enhancement

## Session Context

**Date**: 2026-01-04
**Repository**: ProjectScylla
**Branch**: report-cleanup
**PR**: #145

## Initial Problem Statement

User requested analysis of `results.log` and results directory to fix 4 bugs in E2E evaluation implementations:

1. **Penalize agents that create extra files** - Add cleanup instructions to prompts
2. **Fix tier 6 empty results** showing $0.00 cost
3. **Reward high-quality tests** with separate criteria
4. **Penalize useless testing/files/implementation** details

## Detailed Analysis

### T6 Results Bug

**Evidence from results.log**:
```
2026-01-04 14:06:42 [WARNING] scylla.e2e.subtest_executor: Invalid result detected at results/2026-01-04T20-36-11-test-001/T6/01/run_01: exit_code=-1 with zero token stats (incomplete execution)
```

**T6 result.json**:
```json
{
  "exit_code": -1,
  "token_stats": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0
  },
  "cost": 0.00
}
```

**Root Cause**: Agent threw exception but still created files. Output capture failed, resulting in empty token stats and $0.00 cost being recorded.

**Solution**: Mark runs with `exit_code == -1` AND all token_stats == 0 as INVALID to force re-run.

### T6 Over-Engineering Example

**Observation**: T6 agent created 9 extra documentation files (2,900+ lines) for a 1-line task.

**Judge Scores** (before fix):
- `documentation: 0.40` (correctly penalized, but weight only 0.5)
- `following_instructions: 0.50` (penalized for misinterpreting "maximize usage of tools")
- `simplicity: 0.60` (not strict enough)

**Gap**: No explicit criterion for "workspace cleanliness" or "proportionality"

## User Clarifications

### Cleanup Instructions Scope

**User**: "I want the cost bug to be fixed, I don't want the task prompt to change to produce less files, just to specify that agents need to cleanup after themselves for temporary files"

**Interpretation**:
- Cleanup instructions should focus on **temporary files only** (build artifacts, cache files)
- Should NOT restrict documentation or test file creation
- Judge criteria should handle quality assessment, not prompt restrictions

### Test Quality Scoring

**Options Presented**:
1. Bonus-only (no penalty for missing tests)
2. Penalty for unnecessary tests
3. N/A when not applicable

**User Choice**: "Penalize unnecessary tests"

**Implication**: test_quality should score low for both:
- Missing tests when required
- Unnecessary tests for trivial tasks (e.g., hello.py doesn't need 200-line suite)

### Workspace Cleanliness Threshold

**Options Presented**:
1. Fixed threshold (e.g., max 5 files)
2. Task-proportionate
3. Only penalize temp files

**User Choice**: "Task-proportionate"

**Implication**: Simple tasks (1-line code) warrant minimal supporting files (1-3 max). Complex tasks can justify more.

## Implementation Details

### Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `config/judge/system_prompt.md` | +60 | Added 3 new criteria sections |
| `src/scylla/judge/prompts.py` | +20 | Added enum values, weights, schema |
| `src/scylla/e2e/subtest_executor.py` | +18 | Enhanced `_has_valid_agent_result()` |
| `src/scylla/e2e/tier_manager.py` | +8 | Appended cleanup instructions |
| `tests/unit/judge/test_prompts.py` | +14 | Updated test expectations |
| `tests/unit/e2e/test_tier_manager.py` | +16 | Updated assertions with cleanup |

### Code Changes

**prompts.py - New Categories**:
```python
class EvaluationCategory(Enum):
    # ... 10 existing ...
    WORKSPACE_CLEANLINESS = "workspace_cleanliness"
    TEST_QUALITY = "test_quality"
    SCOPE_DISCIPLINE = "scope_discipline"

CATEGORY_WEIGHTS: dict[EvaluationCategory, float] = {
    # ... existing 9.5 total ...
    EvaluationCategory.WORKSPACE_CLEANLINESS: 1.0,
    EvaluationCategory.TEST_QUALITY: 1.0,
    EvaluationCategory.SCOPE_DISCIPLINE: 1.0,
}
# New TOTAL_CATEGORY_WEIGHT = 12.5
```

**subtest_executor.py - Invalid Result Detection**:
```python
def _has_valid_agent_result(run_dir: Path) -> bool:
    # ... existing validation ...

    # Check for incomplete execution: exit_code=-1 AND all token stats are 0
    if data["exit_code"] == -1:
        token_stats = data["token_stats"]
        all_tokens_zero = (
            token_stats.get("input_tokens", 0) == 0
            and token_stats.get("output_tokens", 0) == 0
            and token_stats.get("cache_creation_tokens", 0) == 0
            and token_stats.get("cache_read_tokens", 0) == 0
        )
        if all_tokens_zero:
            logger.warning(
                f"Invalid result detected at {run_dir}: "
                f"exit_code=-1 with zero token stats (incomplete execution)"
            )
            return False
    return True
```

**tier_manager.py - Cleanup Instructions**:
```python
def build_resource_suffix(self, subtest: SubTestConfig) -> str:
    # ... existing logic to build base_message ...

    # Always add cleanup instructions (temporary files only)
    cleanup_instructions = (
        "\n\n## Cleanup Requirements\n"
        "- Remove any temporary files created during task completion "
        "(build artifacts, cache files, etc.)\n"
        "- Clean up after yourself - the workspace should contain only final deliverables"
    )

    return base_message + cleanup_instructions
```

## CI/CD Test Failures

### First Failure

**test_tier_manager.py** (6 tests):
```
AssertionError: assert 'Maximize usa... deliverables' == 'Maximize usa...te this task.'
```

**Cause**: Cleanup instructions now appended to all prompts, but test expectations didn't include them.

**Fix**: Added `CLEANUP_INSTRUCTIONS` constant to test file and updated all 6 assertions.

### Second Failure

**test_prompts.py** (3 tests):
```
AssertionError: assert 13 == 10  # test_all_categories_present
AssertionError: assert 12.5 == pytest.approx(9.5)  # test_total_weight
```

**Cause**: Added 3 new categories but didn't update test expectations.

**Fix**:
- Updated category count: 10 → 13
- Added assertions for 3 new category values
- Updated total weight: 9.5 → 12.5

### Third Failure

**Pre-commit hook** (ruff):
```
E501 Line too long (104 > 100)
expected = "Maximize usage of all available tools..." + CLEANUP_INSTRUCTIONS
```

**Fix**: Break into multi-line string:
```python
expected = (
    "Maximize usage of all available tools to complete this task."
    + CLEANUP_INSTRUCTIONS
)
```

## Commits

1. **9002a3d**: "feat(e2e): enhance judge criteria and fix T6 cost tracking bug"
   - Added 3 new judge criteria
   - Fixed invalid result detection
   - Added cleanup instructions

2. **4062361**: "test: update unit tests for new judge criteria and cleanup instructions"
   - Updated test_prompts.py (category count, values, weight)
   - Updated test_tier_manager.py (cleanup instructions in assertions)
   - Fixed line length violations

## Verification

**Invalid result detection working**:
```
2026-01-04 14:06:42 [WARNING] scylla.e2e.subtest_executor: Invalid result detected at results/2026-01-04T20-36-11-test-001/T6/01/run_01: exit_code=-1 with zero token stats (incomplete execution)
```

**CI Status**: Tests passing after commit 4062361

## Judge Criteria Rationale

### Workspace Cleanliness (1.0)

**Purpose**: Penalize files that don't meaningfully contribute to the solution

**Scoring Guidance**:
- Simple tasks (1-line code): 1-3 supporting files max
- Complex tasks: More files justified
- Penalize: README.md, ARCHITECTURE.md, CONTRIBUTING.md for hello.py

### Test Quality (1.0)

**Purpose**: Reward comprehensive tests when needed, penalize unnecessary tests for trivial tasks

**Scoring Guidance**:
- IF tests required: comprehensive coverage, edge cases, meaningful assertions → high score
- IF tests NOT required: penalize unnecessary test files for trivial tasks → low score
- Tests should be proportionate to task complexity

### Scope Discipline (1.0)

**Purpose**: Penalize over-engineering and ensure documentation matches task complexity

**Scoring Guidance**:
- No over-engineering for simple tasks
- Documentation matches code complexity
- No unused code or dead ends
- Files created directly serve the deliverable

## Weight Distribution Analysis

**Before** (Total: 9.5):
- Functional Correctness: 2.0 (21%)
- Completeness: 1.5 (16%)
- Code Quality: 1.0 (11%)
- Other criteria: 5.0 (52%)

**After** (Total: 12.5):
- Functional Correctness: 2.0 (16%)
- Completeness: 1.5 (12%)
- Proportionality & Scope: 3.0 (24%) ← NEW
- Code Quality: 1.0 (8%)
- Other criteria: 5.0 (40%)

**Impact**: Proportionality criteria now account for 24% of total score, ensuring task-appropriate solutions are rewarded.

## Lessons Learned

1. **User intent clarification is critical**: Initial plan included restricting file creation via prompts, but user wanted cleanup instructions only for temp files.

2. **Judge criteria vs. prompt restrictions**: Better to assess quality post-hoc (judge) than restrict behavior upfront (prompts).

3. **Bi-directional penalties**: Proportionality criteria should penalize BOTH over-engineering AND under-engineering.

4. **Systematic test updates**: When adding N categories, expect to update N+2 tests (count, values, total weight).

5. **Invalid result patterns**: `exit_code=-1 + zero tokens` indicates incomplete execution requiring re-run.

6. **Line length discipline**: Multi-line string concatenation prevents E501 violations in test assertions.

## Future Considerations

1. **Adaptive weights**: Could adjust category weights based on task complexity (more weight on test_quality for complex tasks).

2. **Automated proportionality detection**: Could parse task description for complexity indicators (e.g., "implement X" vs. "write hello world").

3. **Category correlation analysis**: Track whether workspace_cleanliness, test_quality, and scope_discipline correlate with overall pass rate.

4. **Threshold tuning**: May need to adjust 1-3 file threshold for simple tasks based on empirical data.

## Commands Used

```bash
# Analysis
grep -A 5 "exit_code.*-1" results.log
gh issue view <number> --comments

# Development
git checkout -b report-cleanup
pre-commit run --all-files
pixi run pytest tests/unit/judge/test_prompts.py -v

# Commits
git add <files>
git commit -m "..."
git push

# PR
gh pr create --title "..." --body "Closes #<number>"
gh pr checks 145
```
