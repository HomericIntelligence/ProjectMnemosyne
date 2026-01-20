# Grading Consolidation - Detailed Notes

## Session Context

**Date:** 2026-01-19
**Project:** ProjectScylla E2E Evaluation Framework
**Duration:** Extended session covering infrastructure fixes and grading consolidation

## Problem Statement

User discovered that a score of 0.97 was receiving an S grade instead of an A grade. This revealed deeper infrastructure issues with duplicate grading logic across the codebase.

## User's Explicit Requirements

1. "S grade is ONLY for a 1.0 and not anything else"
2. "I want to throw an assertion if there is a score > 1.0"
3. "also assert that a score < 0 is an error also!"
4. "I also want the consensus_score to use the same scoring function as in grading.py and not have its own logic"
5. "There should only be one function and one definition in the documentation"
6. "If there is not a test making them in sync, write a test that validates them"
7. "I also want to reduce duplication of the grading infrastructure if possible"

## Discovery Process

### Initial Bug Location

Found in `src/scylla/e2e/subtest_executor.py:1437-1440`:
```python
# BEFORE (duplicate logic with wrong threshold)
if consensus_score >= 0.95:
    grade = "S"
elif consensus_score >= 0.80:
    grade = "A"
# ... etc
```

Also found in `src/scylla/metrics/grading.py:151`:
```python
# BEFORE (>= allows 1.0+ to get S)
if score >= 1.0:
    return "S"
```

### Comprehensive Search Results

**Duplicate GradeScale Classes Found:**
1. `src/scylla/config/models.py:92-112` - GradeScale class
2. `src/scylla/judge/rubric.py:65-91` - GradeScale class (duplicate)

**Duplicate Grade Assignment Methods:**
1. `src/scylla/metrics/grading.py:128-163` - assign_letter_grade() (canonical)
2. `src/scylla/judge/rubric.py:124-152` - Rubric.assign_letter_grade() (duplicate)
3. `src/scylla/e2e/subtest_executor.py:1437-1450` - Inline grade assignment (duplicate)

**Pass Threshold Defaults Found:**
- `src/scylla/config/models.py:102` - default=0.60
- `src/scylla/judge/rubric.py:87` - default=0.60
- `src/scylla/judge/rubric.py:266` - fallback 0.60
- Tests using hardcoded 0.60 values

## Changes Made

### Commit 1: Fix S Grade Threshold

**File:** `src/scylla/metrics/grading.py`

Changed line 151:
```python
# BEFORE
if score >= 1.0:
    return "S"

# AFTER
if score == 1.0:
    return "S"
```

Added assertions at line 149:
```python
# Scores outside [0.0, 1.0] are errors - should never occur
assert 0.0 <= score <= 1.0, f"Score {score} is outside valid range [0.0, 1.0]"
```

### Commit 2: Remove Duplicate Grading Infrastructure

**Deleted Classes:**
1. `src/scylla/config/models.py:92-112` - GradeScale (30 lines)
2. `src/scylla/judge/rubric.py:65-91` - GradeScale (27 lines)

**Deleted Methods:**
- `src/scylla/judge/rubric.py:124-152` - Rubric.assign_letter_grade() (29 lines)

**Updated Consensus Grading:**
`src/scylla/e2e/subtest_executor.py:1437-1440`:
```python
# AFTER (uses centralized function)
from scylla.metrics.grading import assign_letter_grade
grade = assign_letter_grade(consensus_score)
```

**Removed grade_scale Fields:**
- Removed from GradingConfig class
- Removed from Rubric model
- Removed from RubricParser.parse_yaml()
- Updated all imports and exports

**Total Lines Removed:** 241 lines of duplicate code

### Commit 3: Consolidate Pass Threshold

**Added Constant:**
`src/scylla/metrics/grading.py:16`:
```python
# Default pass threshold (Good grade - B)
# See docs/design/grading-scale.md for specification
DEFAULT_PASS_THRESHOLD = 0.60
```

**Updated Usage:**
- `src/scylla/config/models.py:103` - Uses DEFAULT_PASS_THRESHOLD
- `src/scylla/judge/rubric.py:87` - Uses DEFAULT_PASS_THRESHOLD
- `src/scylla/judge/rubric.py:266` - Uses DEFAULT_PASS_THRESHOLD
- Exported from `src/scylla/metrics/__init__.py`

**Updated Tests:**
- `tests/unit/judge/test_rubric.py` - Uses DEFAULT_PASS_THRESHOLD
- `tests/unit/test_config_loader.py` - Uses DEFAULT_PASS_THRESHOLD

## Tests Created

**New File:** `tests/unit/test_grading_consistency.py`

Six comprehensive tests:
1. `test_grade_thresholds_match_documentation` - Validates all threshold boundaries
2. `test_s_grade_requires_perfect_score` - S grade only for exactly 1.0
3. `test_grade_assignment_boundaries` - Edge cases at boundaries
4. `test_metrics_grading_validates_range` - Assertions catch invalid scores
5. `test_grade_assignment_exhaustive` - All percentages 0-100
6. `test_s_grade_exclusively_for_perfect` - S never for < 1.0

## Documentation Updates

**File:** `docs/design/grading-scale.md`

Changes:
1. Removed `grade_scale:` YAML field from examples (lines 32-38)
2. Added note that grade scale is centralized in code (lines 27-35)
3. Updated "Usage in Rubric Files" section (lines 91-103)
4. Clarified that only pass_threshold is configurable per rubric

Before example:
```yaml
grading:
  pass_threshold: 0.60
  grade_scale:
    S: 1.00
    A: 0.80
    # ... etc
```

After example:
```yaml
grading:
  pass_threshold: 0.60
  # Note: Grade scale is centralized in scylla.metrics.grading
```

## Validation Results

### Test Suite Results
```
============================= test session starts ==============================
collected 76 items

tests/unit/test_grading_consistency.py::TestGradingConsistency::test_grade_thresholds_match_documentation PASSED
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_s_grade_requires_perfect_score PASSED
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_grade_assignment_boundaries PASSED
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_metrics_grading_validates_range PASSED
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_grade_assignment_exhaustive PASSED
tests/unit/test_grading_consistency.py::TestGradingConsistency::test_s_grade_exclusively_for_perfect PASSED
tests/unit/judge/test_rubric.py ... (44 tests PASSED)
tests/unit/test_config_loader.py ... (26 tests PASSED)

======================== 75 passed, 1 skipped in 0.34s ==============================
```

### Pre-commit Hooks
- ✅ ruff - Passed
- ✅ ruff-format - Passed

## Grade-Related Patterns That Remain (Validated as Non-Duplicates)

### 1. Grade Order Arrays
**Purpose:** Sorting grades for display

`src/scylla/e2e/run_report.py:617`:
```python
grade_order = ["S", "A", "B", "C", "D", "F"]
```

`src/scylla/e2e/subtest_executor.py:1583`:
```python
grade_order = ["F", "D", "C", "B", "A", "S"]
```

**Rationale:** These are for sorting/ordering, not grade assignment. Different orderings serve different purposes (ascending vs descending).

### 2. Grade Validation
**Purpose:** Pydantic field validation

`src/scylla/judge/prompts.py:97-98`:
```python
@field_validator("grade")
def validate_grade(cls, v: str) -> str:
    if v not in {"S", "A", "B", "C", "D", "F"}:
        raise ValueError(f"Invalid grade: {v}")
```

**Rationale:** This validates that grade strings are in the valid set. It's input validation, not grade assignment logic.

### 3. Grade-to-Points Conversion
**Purpose:** Converting letter grades to numeric points for averaging

`src/scylla/reporting/scorecard.py:106`:
```python
base_points = {"S": 5.0, "A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
```

**Rationale:** This is for calculating GPA-style averages across multiple graded items. It's a reverse mapping (grade→points) rather than score→grade assignment.

## Key Lessons Learned

### 1. Explicit User Requirements
When user says "ONLY for a 1.0", they mean:
- Change `>=` to `==`
- Not just documentation
- Actual behavior change required

### 2. Holistic Audit Pattern
After fixing initial bug:
1. Search comprehensively for related patterns
2. Categorize findings (duplicates vs legitimate different uses)
3. Remove duplicates systematically
4. Verify with tests
5. Update documentation

### 3. Failed Configuration Removal
Attempted to remove GradingConfig entirely, but:
- `pass_threshold` was still actively used
- Different tests legitimately need different thresholds (0.60, 0.80)
- Lesson: Only remove truly unused code

### 4. Test-Driven Consistency
Created tests that validate:
- Code matches documentation
- S grade exclusively for 1.0
- Assertions catch invalid scores
- All boundaries work correctly

This prevents future regression.

## Search Commands Reference

```bash
# Find grade assignment patterns
grep -r "def.*grade" src/
grep -r "assign.*grade" src/
grep -r "class.*Grade" src/

# Find specific thresholds
grep -r "0\.95" src/
grep -r ">= 1\.0" src/
grep -r "== 1\.0" src/

# Find grade literals
grep -r '"S"' src/ | grep -i grade
grep -r "'S'.*'A'.*'B'" src/

# Find pass threshold usage
grep -r "pass_threshold.*=.*0\.60" src/ tests/
grep -r "pass_threshold.*Field" src/

# Find grade scale references
grep -r "grade_scale" src/ tests/ docs/
grep -r "GradeScale" src/ tests/
```

## Final Architecture

### Single Source of Truth

**Grade Assignment:**
- Function: `scylla.metrics.grading.assign_letter_grade()`
- Location: `src/scylla/metrics/grading.py:128-163`
- Documentation: `docs/design/grading-scale.md:42-61`
- Tests: `tests/unit/test_grading_consistency.py`

**Pass Threshold:**
- Constant: `scylla.metrics.grading.DEFAULT_PASS_THRESHOLD`
- Value: `0.60`
- Usage: All Pydantic model defaults reference this constant

**Grade Scale:**
- No longer configurable
- Hardcoded in assign_letter_grade() function
- Based on industry-aligned standards (SonarQube, LLM evaluation frameworks)

## Related Issues

This work was part of PR #199 which also fixed four E2E infrastructure issues:
1. FileExistsError on symlink during resume
2. Git status path parsing bug (ojo/ vs mojo/)
3. Strengthen fn main() requirement
4. Save pipeline command outputs

The grading consolidation was discovered during the infrastructure fixes when examining grade assignment in the consensus scoring logic.
