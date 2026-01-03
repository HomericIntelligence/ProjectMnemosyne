# Industry-Aligned Grading Scale

Replace academic grading scales with production-readiness focused thresholds.

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-02 |
| Objective | Replace academic A=95%/B=85% grading with industry-aligned scale |
| Outcome | Centralized grading definition with S/A/B/C/D/F scale |

## When to Use

- Designing rubric scoring systems for AI/code evaluation
- Replacing academic grading thresholds with production semantics
- Centralizing grading definitions across multiple rubric files
- Adding score validation to prevent invalid scores (>1.0)

**Trigger phrases**: "grading scale", "rubric thresholds", "production ready scoring", "centralize grading"

## The Problem with Academic Scales

Academic grading (A=95%, B=85%, C=75%, D=65%) has issues for software evaluation:

1. **Grade inflation**: 95% for an A is unrealistic for complex tasks
2. **D grade meaningless**: In industry, you pass or fail
3. **No production semantics**: Academic scales don't map to deployment decisions

## Industry-Aligned Grade Scale

| Grade | Threshold | Label | Description |
|-------|-----------|-------|-------------|
| S | 1.00 | Amazing | Exceptional, above and beyond |
| A | 0.80 | Excellent | Production ready, no issues |
| B | 0.60 | Good | Minor improvements possible |
| C | 0.40 | Acceptable | Functional with issues |
| D | 0.20 | Marginal | Significant issues |
| F | 0.00 | Failing | Does not meet requirements |

### Score Interpretation

| Score Range | Action |
|-------------|--------|
| 1.00 | Ship immediately |
| 0.80-0.99 | Ship with confidence |
| 0.60-0.79 | Ship after minor fixes |
| 0.40-0.59 | Rework required |
| 0.20-0.39 | Significant rework |
| 0.00-0.19 | Start over |

## Verified Workflow

### 1. Create Centralized Definition

Create a single source of truth file:

```markdown
# .claude/shared/grading-scale.md

| Grade | Threshold | Label | Description |
|-------|-----------|-------|-------------|
| S | 1.00 | Amazing | Exceptional, above and beyond |
| A | 0.80 | Excellent | Production ready |
| B | 0.60 | Good | Minor improvements possible |
| C | 0.40 | Acceptable | Functional with issues |
| D | 0.20 | Marginal | Significant issues |
| F | 0.00 | Failing | Does not meet requirements |
```

### 2. Update Schema

```json
{
  "grade_scale": {
    "S": { "description": "Amazing - exceptional", "examples": [1.00] },
    "A": { "description": "Excellent - production ready", "examples": [0.80] },
    "B": { "description": "Good - minor improvements", "examples": [0.60] },
    "C": { "description": "Acceptable - functional with issues", "examples": [0.40] },
    "D": { "description": "Marginal - significant issues", "examples": [0.20] },
    "F": { "description": "Failing", "examples": [0.0] }
  }
}
```

### 3. Update Rubric Files

Reference the central definition in each rubric:

```yaml
grading:
  pass_threshold: 0.60
  # Industry-aligned grade scale - see .claude/shared/grading-scale.md
  grade_scale:
    S: 1.00    # Amazing - above and beyond
    A: 0.80    # Excellent - production ready
    B: 0.60    # Good - minor improvements possible
    C: 0.40    # Acceptable - functional with issues
    D: 0.20    # Marginal - significant issues
    F: 0.0     # Failing - does not meet requirements
```

### 4. Add Score Validation

Scores must be in range [0.0, 1.0]. Scores > 1.0 are errors:

```python
def assign_grade(self, weighted_score: float) -> str:
    if weighted_score > 1.0 or weighted_score < 0.0:
        raise RubricValidationError(
            f"Score must be between 0.0 and 1.0, got {weighted_score}"
        )
    if weighted_score >= 1.00: return "S"
    if weighted_score >= 0.80: return "A"
    if weighted_score >= 0.60: return "B"
    if weighted_score >= 0.40: return "C"
    if weighted_score >= 0.20: return "D"
    return "F"
```

## Failed Attempts

| Attempt | Why It Failed |
|---------|---------------|
| Using A/A- grades | Confusing naming; S/A clearer for "super" vs "excellent" |
| Academic 95/85/75/65 thresholds | Too strict; 95% unrealistic for complex tasks |
| Allowing scores > 1.0 | Invalid state; should be an error, not accepted |
| Defining grading in each rubric file | Duplication; changes require updating many files |

## Industry Standards Research

Sources that informed this design:

- **SonarQube**: Quality gates with customizable pass/fail thresholds
- **LLM Evaluation**: 5-point scales (1-5) with clear descriptors
- **QA Scorecards**: Pass thresholds with bonus sections for exceptional work
- **ISO 5055**: Pass/fail based on weakness density thresholds

## Parameters

```yaml
# Default configuration
grading:
  pass_threshold: 0.60  # Good grade = passing
  grade_scale:
    S: 1.00
    A: 0.80
    B: 0.60
    C: 0.40
    D: 0.20
    F: 0.0
```

## Files to Update

When implementing this pattern:

1. `.claude/shared/grading-scale.md` - Central definition (create)
2. `schemas/rubric.schema.json` - Add S grade to schema
3. `docs/design/rubric-schema.md` - Update documentation
4. `src/*/rubric.py` - Update parser with S grade and validation
5. `tests/**/test_rubric.py` - Add tests for S grade and validation
6. `**/rubric.yaml` - Update all rubric files

## Related Skills

- `mojo-test-fixture-creation` - Creating test fixtures with rubrics
- `judge-system-extension` - Extending evaluation systems
