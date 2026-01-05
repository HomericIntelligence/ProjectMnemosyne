# Judge Criteria Enhancement: Proportionality & Scope Discipline

## Overview

| Attribute | Value |
|-----------|-------|
| **Session Date** | 2026-01-04 |
| **Objective** | Fix E2E evaluation bugs: add judge criteria to penalize over-engineering, fix T6 cost tracking bug, reward proportionate solutions |
| **Outcome** | ✅ Successfully added 3 new criteria (workspace_cleanliness, test_quality, scope_discipline), fixed invalid result detection, updated unit tests |
| **PR** | [#145](https://github.com/HomericIntelligence/ProjectScylla/pull/145) |

## When to Use This Skill

Use this skill when you need to:

1. **Add new evaluation criteria** to an LLM judge system to assess quality dimensions not currently covered
2. **Penalize over-engineering** in agent outputs (excessive files, documentation bloat, unnecessary tests)
3. **Fix result validation bugs** where incomplete runs are incorrectly marked as completed
4. **Update unit tests** after adding new evaluation categories or criteria
5. **Ensure proportionality** between task complexity and solution scope

### Trigger Conditions

- Judge is giving high scores to solutions with excessive files/documentation
- Simple tasks (e.g., 1-line code) receive 9+ extra documentation files without penalty
- Cost tracking shows $0.00 for runs with `exit_code=-1` and zero token stats
- Tests required: penalize agents that don't create tests OR create unnecessary tests for trivial tasks

## Verified Workflow

### Phase 1: Analyze the Problem

1. **Review evaluation results** to identify patterns:
   ```bash
   # Check results.log for anomalies
   grep -A 5 "exit_code.*-1" results.log

   # Look for runs with zero cost
   grep "cost.*0.00" results/*/T*/*/result.json
   ```

2. **Identify missing criteria** by examining judge output:
   - Are over-engineered solutions scoring too high?
   - Are proportionate solutions being penalized?
   - Are there quality dimensions not being measured?

3. **Document specific examples**:
   - T6 created 9 extra documentation files (2,900+ lines) for 1-line task
   - T6 got `documentation: 0.40` (correctly penalized) but weight was only 0.5
   - T6 got `following_instructions: 0.50` for misinterpreting "maximize usage of tools"

### Phase 2: Design New Criteria

**Key Principle**: Add criteria under a unified conceptual category (e.g., "Proportionality & Scope")

1. **Define the new criteria** with clear scoring guidance:

   ```markdown
   ### Proportionality & Scope Criteria (Weight: 30%)

   11. **Workspace Cleanliness** (1.0): Are files proportionate to task complexity?
       - Files should meaningfully contribute to the solution
       - Penalize files that don't improve results
       - Simple tasks (1-line code) warrant minimal supporting files (1-3 max)
       - Complex tasks can justify more supporting files

   12. **Test Quality** (1.0): Are tests appropriate and valuable?
       - IF tests required: comprehensive coverage, edge cases, meaningful assertions
       - IF tests NOT required: penalize unnecessary test files for trivial tasks
       - Tests should be proportionate to task complexity

   13. **Scope Discipline** (1.0): Is the solution appropriately scoped?
       - No over-engineering for simple tasks
       - Documentation matches task complexity
       - No unused code or dead ends
   ```

2. **Choose appropriate weights**:
   - Use 1.0 for criteria that are as important as Code Quality
   - Use 0.5 for criteria that are nice-to-have but not critical
   - Total weight increased from 9.5 to 12.5 (added 3 × 1.0)

3. **Update existing criteria descriptions** to be explicit:
   - Add "Penalize excessive file creation" to SIMPLICITY
   - Add "Penalize documentation bloat" to DOCUMENTATION

### Phase 3: Update Code

**File: `config/judge/system_prompt.md`**

Add the new criteria sections under a clear heading:

```markdown
### Proportionality & Scope Criteria (Weight: 30%)

[Insert criteria definitions from Phase 2]
```

**File: `src/scylla/judge/prompts.py`**

1. Add enum values:
   ```python
   class EvaluationCategory(Enum):
       # ... existing 10 categories ...
       WORKSPACE_CLEANLINESS = "workspace_cleanliness"
       TEST_QUALITY = "test_quality"
       SCOPE_DISCIPLINE = "scope_discipline"
   ```

2. Update weights dictionary:
   ```python
   CATEGORY_WEIGHTS: dict[EvaluationCategory, float] = {
       # ... existing weights ...
       EvaluationCategory.WORKSPACE_CLEANLINESS: 1.0,
       EvaluationCategory.TEST_QUALITY: 1.0,
       EvaluationCategory.SCOPE_DISCIPLINE: 1.0,
   }
   ```

3. Update `JSON_OUTPUT_SCHEMA` string:
   ```python
   JSON_OUTPUT_SCHEMA: str = """{
       "categories": {
           # ... existing categories ...
           "workspace_cleanliness": { "score": 0.0-1.0, "confidence": 0.0-1.0, "notes": "" },
           "test_quality": { "score": 0.0-1.0, "confidence": 0.0-1.0, "notes": "" },
           "scope_discipline": { "score": 0.0-1.0, "confidence": 0.0-1.0, "notes": "" }
       }
   }"""
   ```

4. Update `JUDGE_PROMPT_TEMPLATE` to include new categories in the table (if hardcoded)

**File: `src/scylla/e2e/subtest_executor.py`**

Fix invalid result detection:

```python
def _has_valid_agent_result(run_dir: Path) -> bool:
    """Check if a valid agent result exists for the run."""
    result_file = run_dir / "result.json"
    if not result_file.exists():
        return False

    try:
        with open(result_file) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False

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

### Phase 4: Update Unit Tests

**Pattern**: When adding N new categories, update test expectations systematically.

**File: `tests/unit/judge/test_prompts.py`**

1. Update category count:
   ```python
   def test_all_categories_present(self) -> None:
       """Test all 13 categories are defined."""
       assert len(EvaluationCategory) == 13  # Changed from 10
   ```

2. Add assertions for new category values:
   ```python
   def test_category_values(self) -> None:
       # ... existing assertions ...
       assert EvaluationCategory.WORKSPACE_CLEANLINESS.value == "workspace_cleanliness"
       assert EvaluationCategory.TEST_QUALITY.value == "test_quality"
       assert EvaluationCategory.SCOPE_DISCIPLINE.value == "scope_discipline"
   ```

3. Update total weight expectation:
   ```python
   def test_total_weight(self) -> None:
       """Test total weight matches expected value."""
       assert TOTAL_CATEGORY_WEIGHT == pytest.approx(12.5)  # Changed from 9.5
   ```

**File: `tests/unit/e2e/test_tier_manager.py`** (if cleanup instructions added)

1. Add constant matching production code:
   ```python
   CLEANUP_INSTRUCTIONS = (
       "\n\n## Cleanup Requirements\n"
       "- Remove any temporary files created during task completion "
       "(build artifacts, cache files, etc.)\n"
       "- Clean up after yourself - the workspace should contain only final deliverables"
   )
   ```

2. Update all assertions to append cleanup:
   ```python
   def test_tools_enabled_all(self) -> None:
       # ... setup ...
       expected = (
           "Maximize usage of all available tools to complete this task."
           + CLEANUP_INSTRUCTIONS
       )
       assert result == expected
   ```

### Phase 5: Verify and Commit

1. **Run tests locally**:
   ```bash
   pixi run pytest tests/unit/judge/test_prompts.py -v
   pixi run pytest tests/unit/e2e/test_tier_manager.py -v
   ```

2. **Run pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

3. **Commit changes**:
   ```bash
   git add tests/unit/judge/test_prompts.py tests/unit/e2e/test_tier_manager.py
   git commit -m "test: update unit tests for new judge criteria and cleanup instructions"
   git push
   ```

4. **Monitor CI** to ensure all checks pass

## Failed Attempts

### ❌ Attempt 1: Restricting Agent File Creation

**What We Tried**: Initial plan included changing task prompts to say "Don't create extra files unless necessary"

**Why It Failed**:
- User clarified: "I don't want the task prompt to change to produce less files, just to specify that agents need to cleanup after themselves for temporary files"
- This would restrict legitimate documentation and test creation
- The problem is over-engineering, not file creation itself

**Lesson**:
- Judge criteria should handle quality assessment, not prompt restrictions
- Cleanup instructions should focus on temporary files only (build artifacts, cache)
- Don't prevent agents from creating documentation/tests when appropriate

### ❌ Attempt 2: Using Bonus-Only Scoring for Test Quality

**What We Considered**: Making test_quality only give bonus points (no penalty for missing tests)

**Why It Failed**:
- User chose "penalize unnecessary tests" approach
- A 1-line task with 200-line test suite should score low on test_quality
- Need to penalize both missing tests (when required) AND unnecessary tests (for trivial tasks)

**Lesson**: Proportionality criteria should penalize deviations in BOTH directions (too little AND too much)

### ❌ Attempt 3: Line Length Violations in Test Assertions

**What Happened**: First commit attempt failed pre-commit hooks with E501 (line too long)

**Error**:
```
tests/unit/e2e/test_tier_manager.py:34:101: E501 Line too long (104 > 100)
expected = "Maximize usage of all available tools..." + CLEANUP_INSTRUCTIONS
```

**Fix**: Break into multi-line string concatenation:
```python
expected = (
    "Maximize usage of all available tools to complete this task."
    + CLEANUP_INSTRUCTIONS
)
```

**Lesson**: When adding constants to test assertions, watch for line length limits (100 chars). Use parenthesized multi-line strings.

## Results & Parameters

### Judge Criteria Configuration

**Before** (10 categories, weight 9.5):
```python
CATEGORY_WEIGHTS = {
    EvaluationCategory.FUNCTIONAL_CORRECTNESS: 2.0,
    EvaluationCategory.COMPLETENESS: 1.5,
    EvaluationCategory.CODE_QUALITY: 1.0,
    EvaluationCategory.SIMPLICITY: 1.0,
    EvaluationCategory.LACK_OF_DUPLICATION: 0.5,
    EvaluationCategory.CLARITY: 1.0,
    EvaluationCategory.DOCUMENTATION: 0.5,
    EvaluationCategory.ARCHITECTURAL_CLEANLINESS: 0.5,
    EvaluationCategory.EFFICIENCY: 0.5,
    EvaluationCategory.CLEANUP_SCRIPT_QUALITY: 1.0,
}
TOTAL_CATEGORY_WEIGHT = 9.5
```

**After** (13 categories, weight 12.5):
```python
CATEGORY_WEIGHTS = {
    # ... existing 10 categories (9.5 total) ...
    EvaluationCategory.WORKSPACE_CLEANLINESS: 1.0,
    EvaluationCategory.TEST_QUALITY: 1.0,
    EvaluationCategory.SCOPE_DISCIPLINE: 1.0,
}
TOTAL_CATEGORY_WEIGHT = 12.5
```

### Invalid Result Detection

**Pattern to Detect**:
```python
exit_code == -1 AND (
    input_tokens == 0 AND
    output_tokens == 0 AND
    cache_creation_tokens == 0 AND
    cache_read_tokens == 0
)
```

**Action**: Return `False` from `_has_valid_agent_result()` to force re-run

### Cleanup Instructions Template

```markdown
## Cleanup Requirements
- Remove any temporary files created during task completion (build artifacts, cache files, etc.)
- Clean up after yourself - the workspace should contain only final deliverables
```

**Where Applied**: Appended to all task prompts via `TierManager.build_resource_suffix()`

## Key Takeaways

1. **Proportionality is a distinct quality dimension**: Separate from simplicity, it measures whether the solution matches task complexity
2. **Judge criteria beat prompt restrictions**: Better to score quality post-hoc than restrict agent behavior upfront
3. **Bi-directional penalties**: Proportionality criteria should penalize BOTH over-engineering AND under-engineering
4. **Test updates are systematic**: When adding N categories, update N+2 tests (category count, category values, total weight)
5. **Invalid result detection**: Check for `exit_code=-1 + zero tokens` pattern to catch incomplete executions
6. **User intent matters**: Clarify whether goal is to restrict behavior (prompts) or assess quality (judge)

## Related Skills

- `evaluation/judge-prompt-design` - Designing effective judge prompts
- `testing/unit-test-patterns` - Patterns for updating tests after enum/constant changes
- `debugging/cost-tracking-validation` - Validating cost/token tracking in evaluation systems
