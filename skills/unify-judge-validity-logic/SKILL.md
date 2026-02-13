# Unify Judge Validity Logic

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-09 |
| **Objective** | Fix E2E judge data quality bugs by unifying validity checks and ensuring `is_valid` is the single source of truth |
| **Outcome** | ✅ Successfully fixed 4 critical bugs, added comprehensive tests, all 218 tests passing |
| **PR** | #476 |
| **Related Issue** | #475 (future cleanup of fallback compatibility) |

## When to Use This Skill

Use this skill when:

1. **Investigating judge data quality issues** where invalid judgments contaminate consensus scores
2. **Debugging silent failures** in judge evaluation where invalid data appears valid
3. **Unifying validation logic** across multiple code paths that check the same conditions differently
4. **Adding backward compatibility** for deprecated fields while maintaining data integrity
5. **Ensuring filtering consistency** between live execution and regeneration logic

**Trigger Patterns**:
- Judge consensus scores include obviously invalid judgments (e.g., fallback scores)
- Different code paths accept/reject the same judgment inconsistently
- JSON responses with missing required fields get silent defaults
- Validity checks spread across multiple functions with subtle differences

## Core Principle

**`is_valid` is the sole gate for judgment validity.**

- No separate "fallback" logic branches
- For old data: `fallback: true` → `is_valid: false` (compatibility mapping)
- All validation functions must check `is_valid` consistently
- Filter by `is_valid` before computing consensus

## Verified Workflow

### Step 1: Identify All Validation Sites

Find every place that checks judge validity:

```bash
# Find validity checks
rg "is_valid|fallback" scylla/e2e/ --type py

# Find consensus computation
rg "_compute.*consensus|_regenerate.*consensus" scylla/e2e/ --type py

# Find result validation
rg "_has_valid.*result|_is_valid.*judgment" scylla/e2e/ --type py
```

**Key locations found**:
- `scylla/e2e/llm_judge.py` - Judge response parsing
- `scylla/e2e/subtest_executor.py` - Live consensus, result validation
- `scylla/e2e/rerun_judges.py` - Judgment validation, consensus regeneration
- `scylla/e2e/regenerate.py` - Duplicate result validation (!)

### Step 2: Unify Validity Checks (Remove Separate Fallback Logic)

**Pattern**: Replace separate `is_valid` and `fallback` checks with unified logic

**Before** (inconsistent - two separate checks):
```python
return (
    "score" in data
    and data.get("is_valid", True) is not False
    and data.get("fallback", False) is not True  # Separate check!
)
```

**After** (unified - map fallback into is_valid):
```python
is_valid = data.get("is_valid", True) is not False
# Old data has fallback=true with is_valid=true — treat as invalid
if data.get("fallback", False) is True:
    is_valid = False
return "score" in data and is_valid
```

**Apply to**:
- `_is_valid_judgment()` in `rerun_judges.py`
- `_regenerate_consensus()` in `rerun_judges.py`
- `_has_valid_judge_result()` in `subtest_executor.py`
- `_has_valid_judge_result()` in `regenerate.py` (duplicate!)

### Step 3: Validate Required Fields Early

**Problem**: Judge returns `{"status": "ok"}` without `score` → silent default to `score=0.0, is_valid=True`

**Solution**: Validate immediately after JSON parsing

```python
try:
    data = json.loads(response)

    # Add validation BEFORE accessing fields
    if "score" not in data:
        raise ValueError(
            f"Judge response missing required 'score' field. "
            f"Keys found: {list(data.keys())}\nResponse: {response[:500]}"
        )

    score = float(data.get("score", 0.0))  # Safe now
```

**Location**: `scylla/e2e/llm_judge.py:_parse_judge_response()`

### Step 4: Filter Invalid Judges in Consensus

**Problem**: Live consensus includes invalid judges, regeneration excludes them → inconsistency

**Before**:
```python
valid = [j for j in judges if j.score is not None]
```

**After**:
```python
valid = [j for j in judges if j.score is not None and j.is_valid]
```

**Location**: `scylla/e2e/subtest_executor.py:_compute_judge_consensus()`

### Step 5: Add Comprehensive Tests

**Test Coverage Required**:

| Test | What It Verifies |
|------|------------------|
| `test_parse_judge_response_raises_on_missing_score` | ValueError when JSON has no `score` field |
| `test_compute_judge_consensus_excludes_invalid_judges` | Only valid judges in consensus (check average) |
| `test_has_valid_judge_result_rejects_invalid` | `is_valid=False` → False |
| `test_has_valid_judge_result_rejects_fallback` | `fallback=True` → False (even if `is_valid=True`) |
| `test_has_valid_judge_result_accepts_valid` | `is_valid=True` → True |
| `test_has_valid_judge_result_accepts_valid_no_is_valid_field` | Missing `is_valid` defaults to True |

**Critical**: Update existing tests that assume invalid judges are included:
```python
# OLD: test_consensus_with_invalid_judge
# Expected: average of 0.9 and 0.0 = 0.45
assert abs(score - 0.45) < 0.001

# NEW: after filtering invalid judges
# Expected: only valid judge (0.9)
assert abs(score - 0.9) < 0.001
```

### Step 6: Test Directory Structure

**Important**: `_has_valid_judge_result()` takes `run_dir`, not `result_file`!

```python
# WRONG: Passing file directly
result_file = tmp_path / "judge_result.json"
result_file.write_text('{"score": 0.9, ...}')
assert _has_valid_judge_result(result_file)  # FAILS!

# RIGHT: Create proper directory structure
run_dir = tmp_path / "run_01"
judge_dir = run_dir / "judge"
judge_dir.mkdir(parents=True)
result_file = judge_dir / "result.json"  # Must be judge/result.json
result_file.write_text('{"score": 0.9, ...}')
assert _has_valid_judge_result(run_dir)  # WORKS!
```

**Why**: Function calls `get_judge_result_file(run_dir)` which returns `run_dir/judge/result.json`

## Failed Attempts

### ❌ Attempt 1: Initial Test Implementation (Test Failures)

**What We Tried**: Created tests for `_has_valid_judge_result()` passing file paths directly

**Why It Failed**:
```
AssertionError: assert False
 +  where False = _has_valid_judge_result(PosixPath('.../judge_result.json'))
```

**Root Cause**: Function signature is `_has_valid_judge_result(run_dir: Path)`, not `result_file: Path`

**Lesson**: Always check function signatures! The function calls `get_judge_result_file(run_dir)` internally, which expects:
- Input: `run_dir` (e.g., `run_01/`)
- Output: `run_dir/judge/result.json`

**Fix**: Create proper directory structure in tests:
```python
run_dir = tmp_path / "run_01"
judge_dir = run_dir / "judge"
judge_dir.mkdir(parents=True)
result_file = judge_dir / "result.json"  # Proper path
```

### ❌ Attempt 2: Line Length Violations

**What Happened**: Pre-commit hook failed:
```
E501 Line too long (105 > 100)
tests/unit/e2e/test_subtest_executor.py:272:101
```

**Docstring**:
```python
"""Test that _has_valid_judge_result returns True when is_valid is missing (defaults to True)."""
```

**Fix**: Remove redundant "that" to shorten:
```python
"""Test _has_valid_judge_result returns True when is_valid is missing (defaults to True)."""
```

**Lesson**: Docstrings count toward line length limits. Be concise.

## Results & Parameters

### Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `scylla/e2e/llm_judge.py` | Validate `score` field | +6 |
| `scylla/e2e/rerun_judges.py` | Unify validity checks (2 functions) | +11 -6 |
| `scylla/e2e/subtest_executor.py` | Filter invalid + validate results | +13 -2 |
| `scylla/e2e/regenerate.py` | Validate results | +8 -2 |
| `scylla/e2e/models.py` | Remove fallback reference | +1 -1 |
| `tests/unit/e2e/test_subtest_executor.py` | Add 5 tests, update 1 | +52 |
| `tests/unit/e2e/test_rerun_judges.py` | Update docstring | -1 |

**Total**: +309 insertions, -42 deletions

### Test Results

```bash
pixi run python -m pytest tests/unit/e2e/ -x -q
```

**Output**: ✅ 218 passed, 1 skipped in 1.16s

### Pre-commit Hooks

```bash
pre-commit run --all-files
```

**All Passed**:
- Check for shell=True (Security)
- Ruff Format Python
- Ruff Check Python
- Strip Notebook Outputs
- Trim Trailing Whitespace
- Fix End of Files
- Check for Large Files
- Fix Mixed Line Endings

## Key Patterns

### Pattern 1: Mapping Deprecated Fields for Backward Compatibility

When replacing a deprecated field with a new one:

```python
# Step 1: Get new field value (with default)
is_valid = data.get("is_valid", True) is not False

# Step 2: Apply compatibility mapping
if data.get("deprecated_field", False) is True:
    is_valid = False  # Map deprecated → new

# Step 3: Use unified value
return is_valid
```

**Benefits**:
- Single code path for new and old data
- Clear migration story
- Easy to remove later (just delete step 2)

### Pattern 2: Aligning Live and Regeneration Logic

When you have both live execution and regeneration:

1. **Find the filtering logic** in regeneration code
2. **Copy the same logic** to live execution
3. **Verify with tests** that both produce identical results

**Example**:
- `_regenerate_consensus()` filters by `is_valid` → consensus from valid judges only
- `_compute_judge_consensus()` must filter identically → add `and j.is_valid`

### Pattern 3: Fail Fast on Invalid Data

Validate required fields immediately after parsing:

```python
data = json.loads(response)

# Fail fast - don't proceed with invalid data
if "required_field" not in data:
    raise ValueError(f"Missing required field. Keys: {list(data.keys())}")

# Safe to use data now
value = data["required_field"]
```

**Avoid**:
```python
# BAD: Silent default makes invalid data look valid
value = data.get("required_field", default_value)
```

## Related Issues

- **#475** - Remove fallback compatibility paths ✅ COMPLETED
  - All `data.get("fallback")` checks have been removed
  - Simplified to just `data.get("is_valid", True) is not False`

## References

- Investigation: `~/fullruns/test001-nothinking/` and `~/fullruns/test001-nothinking-haiku/`
- Implementation plan: Conversation transcript at `.claude/projects/-home-mvillmow-ProjectScylla/e3f19152-82e8-4da1-9a1e-7e5f547f0511.jsonl`
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/476
