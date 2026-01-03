# Session Notes: Industry Grading Scale

## Context

ProjectScylla uses rubrics with grading scales to evaluate AI agent outputs. The original
implementation used academic-style thresholds (A=95%, B=85%, etc.) which didn't translate
well to production readiness semantics.

## User Requirements

1. Replace academic grading with industry-aligned scale
2. Centralize grading definition (avoid duplication across rubric files)
3. Use S/A instead of A/A- for clarity
4. Scores > 1.0 should be an error, not accepted

## Web Search Findings

### SonarQube
- Uses customizable quality gates
- Metrics: coverage, duplication, complexity
- Pass/fail thresholds per metric

### LLM Evaluation Standards
- G-Eval: 1-5 scale
- MT-bench: 1-10 scale
- Likert: 1-4 scale
- No single industry standard for 0-1 normalized scoring

### QA Scorecards (MaestroQA)
- Linear 1-5 scales
- Auto-fail sections
- Bonus sections for exceptional work

### ISO 5055
- CWE-based quality measures
- Pass/fail based on weakness density

## Implementation Details

### Files Changed

1. `.claude/shared/grading-scale.md` (new)
   - Central definition file
   - Grade thresholds and descriptions
   - Assignment logic

2. `schemas/rubric.schema.json`
   - Added S grade property
   - Updated A description from "Amazing" to "Excellent"
   - Changed example values to match new thresholds

3. `docs/design/rubric-schema.md`
   - Version bumped to 1.1
   - Added link to centralized definition
   - Updated examples throughout

4. `src/scylla/judge/rubric.py`
   - Added `s_threshold` to GradeScale
   - Changed `a_threshold` default from 0.95 to 0.80
   - Changed `pass_threshold` default from 0.70 to 0.60
   - Added validation in `assign_grade()` for out-of-range scores
   - Updated parser to read from `grading.grade_scale.S`

5. `tests/unit/judge/test_rubric.py`
   - Added `test_grade_s()` test
   - Added `test_score_over_one_raises()` test
   - Added `test_score_under_zero_raises()` test
   - Updated all existing threshold tests

6. Rubric YAML files (4 files)
   - `tests/fixtures/tests/test-001/expected/rubric.yaml`
   - `tests/fixtures/tests/test-002/expected/rubric.yaml`
   - `tests/001-justfile-to-makefile/expected/rubric.yaml`
   - `tests/002-dtype-native-migration/expected/rubric.yaml`

### Test Results

All 50 unit tests pass after changes.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| S grade at 1.00 | "Super" or "Superior" - reserved for perfect scores |
| A grade at 0.80 | Production ready - the primary goal |
| Pass threshold at 0.60 | "Good" grade - functional with minor improvements |
| Score validation | Prevent invalid states; fail fast on bugs |
| Central file in .claude/shared/ | Consistent with other shared definitions |

## PR Created

- Branch: `refactor/industry-aligned-grading-scale`
- PR: #111
- 9 files changed, 342 insertions, 125 deletions
