# Skill: Backward Compatibility Removal

| Field | Value |
|-------|-------|
| **Date** | 2026-02-13 |
| **Objective** | Remove deprecated `fallback` field compatibility code after migration to `is_valid` field |
| **Outcome** | ✅ Successfully removed 135 lines of deprecated code and tests across 9 files |
| **PRs** | [#577](https://github.com/HomericIntelligence/ProjectScylla/pull/577), [#578](https://github.com/HomericIntelligence/ProjectScylla/pull/578) |

## Overview

This skill documents the systematic removal of deprecated backward compatibility code after a field migration. In this case, the judge system migrated from using a `fallback` field to an `is_valid` field as the sole source of truth for judge validity. After confirming all data was migrated, the old compatibility shims needed removal.

## When to Use This Skill

Use this approach when:

1. **Backward compatibility code exists** for a deprecated field/API
2. **Data migration is complete** - all production data uses the new field
3. **Compatibility shims are scattered** across multiple files
4. **Tests exist specifically** for the deprecated code path
5. **Documentation references** the deprecated approach

This pattern applies to:
- Field renames (e.g., `fallback` → `is_valid`)
- API migrations (e.g., old endpoint → new endpoint)
- Configuration format changes (e.g., YAML v1 → v2)
- Protocol updates (e.g., JSON format changes)

## Verified Workflow

### Phase 1: Identify All Compatibility Code

1. **Search for compatibility shims** using grep:
   ```bash
   grep -rn 'data.get("fallback"' scylla/
   grep -rn 'fallback.*backward' tests/
   ```

2. **Document all locations** before making changes:
   - Production code locations (5 in this case)
   - Test functions exercising deprecated path (5 in this case)
   - Tests with misleading names referencing old field (1 in this case)
   - Documentation/skills referencing the deprecated code

3. **Create a removal plan** with file:line references

### Phase 2: Remove Compatibility Shims

For each location, remove the backward compatibility check while preserving the new logic:

**Before** (with compatibility shim):
```python
# Check is_valid flag (map old fallback=true to is_valid=false)
is_valid = data.get("is_valid", True) is not False
if data.get("fallback", False) is True:
    is_valid = False
return is_valid
```

**After** (clean):
```python
# Check is_valid flag
is_valid = data.get("is_valid", True) is not False
return is_valid
```

**Key principles**:
- Remove ONLY the compatibility code, not the new logic
- Simplify comments to remove references to old field
- Keep the same functionality for the new field

### Phase 3: Remove Deprecated Tests

Delete test functions that ONLY exercised the deprecated code path:

**Criteria for deletion**:
- Test name explicitly mentions deprecated field (e.g., `test_*_with_fallback_true`)
- Test only verifies backward compatibility behavior
- Test has no value once compatibility code is removed

**Example deletions**:
```python
# DELETE - tests deprecated fallback=true behavior
def test_is_valid_judgment_with_fallback_true(tmp_path: Path) -> None:
    ...

# DELETE - tests deprecated fallback=false behavior
def test_is_valid_judgment_with_fallback_false(tmp_path: Path) -> None:
    ...
```

**Do NOT delete**:
- Tests that verify core functionality using the new field
- Tests that happen to use both fields but aren't about compatibility

### Phase 4: Rename Misleading Tests

If a test uses the NEW field but has a name referencing the OLD field:

**Before**:
```python
def test_build_judges_df_fallback_judge_invalid():
    """Test that judges with fallback=true are marked as invalid."""
    # Actually uses is_valid=False, not fallback field
    invalid_judge = JudgeEvaluation(..., is_valid=False)
```

**After**:
```python
def test_build_judges_df_invalid_judge():
    """Test that judges with is_valid=False are marked as invalid."""
    invalid_judge = JudgeEvaluation(..., is_valid=False)
```

**Changes**:
- Rename function to reflect actual behavior
- Update docstring to remove deprecated field references
- Update variable names (e.g., `fallback_judge` → `invalid_judge`)
- Keep test logic unchanged (it's already correct)

### Phase 5: Update Documentation

1. **Skill documentation** - mark related cleanup tasks as completed:
   ```markdown
   ## Related Issues
   - **#475** - Remove fallback compatibility paths ✅ COMPLETED
   ```

2. **Plugin descriptions** - remove references to deprecated features:
   ```json
   - "description": "Fix reruns due to corruption and fallback masking"
   + "description": "Fix reruns due to workspace corruption"
   ```

### Phase 6: Verify and Commit

1. **Run affected tests** to ensure nothing broke:
   ```bash
   pixi run pytest tests/unit/e2e/test_rerun_judges.py \
                   tests/unit/e2e/test_subtest_executor.py \
                   tests/unit/analysis/test_dataframe_builders.py -v
   ```

2. **Run full test suite** to catch integration issues:
   ```bash
   pixi run pytest tests/ -v
   ```

3. **Run pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

4. **Commit with clear message**:
   ```bash
   git commit -m "refactor(judge): Remove deprecated fallback field compatibility

   - Remove data.get(\"fallback\") compatibility shims from 5 locations
   - is_valid is now the sole validity marker
   - Remove 5 fallback-specific test functions
   - Rename misleading test to reflect is_valid usage
   - Update skill documentation

   Closes #475"
   ```

## PR Strategy: Separate Documentation from Code

If you have BOTH documentation cleanup AND code refactoring:

**Best practice**: Create TWO separate PRs

**PR 1: Documentation Cleanup** (low-risk, quick review)
- Delete deprecated docs
- Create documentation indices
- Update references

**PR 2: Code Refactoring** (requires test verification)
- Remove compatibility shims
- Delete deprecated tests
- Update skill docs

**Rationale**:
- Documentation PRs are low-risk and merge quickly
- Code PRs need more careful review and testing
- Keeps PR sizes manageable and focused
- Easier to review and rollback if needed

## Results

### Metrics
- **Files modified**: 9 files
- **Lines removed**: 135 lines (code + tests)
- **Tests removed**: 5 functions
- **Tests renamed**: 1 function
- **Test results**: 65 tests passed in 1.13s

### Files Changed

**Production code** (5 locations):
1. `scylla/e2e/rerun_judges.py:146-148` - `_is_valid_judgment()`
2. `scylla/e2e/rerun_judges.py:525-527` - `_regenerate_consensus()`
3. `scylla/e2e/subtest_executor.py:408-411` - `_has_valid_judge_result()`
4. `scylla/e2e/regenerate.py:506-509` - `_has_valid_judge_result()`
5. `scylla/analysis/loader.py:456-459` - `load_judgment()`

**Tests deleted** (5 functions):
1. `test_is_valid_judgment_with_fallback_true`
2. `test_is_valid_judgment_with_fallback_false`
3. `test_regenerate_consensus_rejects_fallback_judgments`
4. `test_regenerate_consensus_all_fallback_judges`
5. `test_has_valid_judge_result_rejects_fallback`

**Tests renamed** (1 function):
- `test_build_judges_df_fallback_judge_invalid` → `test_build_judges_df_invalid_judge`

## Failed Attempts

### ❌ Attempt: Keep Tests "Just in Case"

**What we tried**: Consider keeping the deprecated tests disabled with `@pytest.mark.skip`

**Why it failed**:
- Tests exercising deprecated code paths have zero value once the code is removed
- Skipped tests create maintenance burden (someone has to remember why they're skipped)
- If the compatibility code is truly gone, the tests can't pass anyway

**Lesson**: Delete tests that only exercise deprecated code. Keep only tests that verify core functionality.

### ❌ Attempt: Update Tests Instead of Deleting

**What we tried**: Modify `test_regenerate_consensus_rejects_fallback_judgments` to test `is_valid=False` instead

**Why it failed**:
- Other tests already cover `is_valid=False` behavior
- The test name explicitly references `fallback`, making it confusing
- Duplication of test coverage with no added value

**Lesson**: If a test's PURPOSE was to verify backward compatibility, delete it. If a test's NAME references the old field but it tests the new field, rename it.

## Common Patterns

### Pattern: Compatibility Shim
```python
# Remove these 2-3 lines everywhere:
if data.get("old_field", False) is True:
    new_field = False
```

### Pattern: Test That Exercises Deprecated Path
```python
# Delete entire function if it only tests deprecated behavior:
def test_function_with_deprecated_field():
    data = {"new_field": True, "old_field": True}  # DELETE
    assert function(data) == expected  # DELETE
```

### Pattern: Misleading Test Name
```python
# Rename function + docstring + variables:
- def test_thing_with_old_field():
-     """Test using old_field."""
-     old_value = Thing(old_field=True)
+ def test_thing_with_new_field():
+     """Test using new_field."""
+     new_value = Thing(new_field=True)
```

## Best Practices

1. **Search exhaustively** - Use grep/ripgrep to find ALL references to the deprecated field
2. **Plan before coding** - Document all locations with file:line numbers
3. **Verify test coverage** - Ensure deleted tests don't remove important coverage
4. **Run tests incrementally** - Test after each file modification
5. **Update documentation** - Mark cleanup tasks as completed in skill docs
6. **Separate concerns** - Use separate PRs for documentation vs code changes

## Anti-Patterns to Avoid

❌ **Don't leave orphaned comments**:
```python
# Check is_valid flag (map old fallback=true to is_valid=false)  # DELETE THIS PART
is_valid = data.get("is_valid", True) is not False
```

❌ **Don't keep disabled tests**:
```python
@pytest.mark.skip("Deprecated - fallback field removed")  # DELETE ENTIRE TEST
def test_old_behavior():
    ...
```

❌ **Don't mix unrelated changes**:
- Keep backward-compat removal separate from new features
- Keep documentation cleanup separate from code refactoring

## Related Skills

- **unify-judge-validity-logic** - Original migration that created the backward compatibility code
- **judge-rerun-workspace-corruption** - Fixed issues that made the migration necessary

## References

- Issue #432 - Research documentation consolidation
- Issue #475 - Remove fallback compatibility paths
- PR #577 - Documentation cleanup
- PR #578 - Fallback compatibility removal
