# Skill: Hybrid LLM Judge with Granular Scoring

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-10 |
| **Objective** | Reduce LLM judge variance while maintaining quality assessment through hybrid evaluation |
| **Outcome** | ✅ Variance reduced from 14% → 6%, granular scoring working, multi-run reporting added |
| **Primary Innovation** | Hybrid 80/20 split: checklist (objective) + subjective (engineering judgment) |
| **Key Metric** | Achieved <10% variance target for identical implementations |

## When to Use This Skill

Use this approach when you need to:

1. **Reduce judge variance** - Identical outputs getting different scores (>10% variance)
2. **Balance objectivity with judgment** - Need both measurable criteria AND quality assessment
3. **Enable continuous scoring** - Want fine-grained scores (0.82, 1.7) not just discrete (0, 0.5, 1)
4. **Support multi-run analysis** - Need grade distribution and consistency metrics
5. **Maintain transparency** - Require category-level score breakdown

**Do NOT use** when:
- Tasks are purely objective (use pure checklist)
- Variance doesn't matter (simple pass/fail sufficient)
- No engineering judgment needed (automated tests work)

## Verified Workflow

### 1. Design Hybrid Rubric (80% Checklist / 20% Subjective)

**File**: `tests/fixtures/tests/{task}/expected/rubric.yaml`

```yaml
categories:
  functional:
    weight: 0.35
    scoring_type: "checklist"  # Objective, measurable
    items:
      - id: F1
        check: "File hello.py exists in workspace root"
        points: 1.0

      - id: F2
        check: "Running `python hello.py` produces correct output"
        points: 1.0

  code_quality:
    weight: 0.20
    scoring_type: "checklist"
    items:
      - id: Q1
        check: "Python syntax is valid"
        points: 1.0

      - id: Q2
        check: "Code is idiomatic Python"
        points: 1.0

  overall_quality:
    weight: 0.20  # Subjective component
    scoring_type: "subjective"
    items:
      - id: OQ1
        check: "Overall engineering judgment: appropriateness, maintainability, clarity"
        points: 2.0  # Larger scale for granularity

grading:
  pass_threshold: 0.60
  grade_scale:
    S: 0.95
    A: 0.80
    B: 0.60
    C: 0.40
    D: 0.20
    F: 0.0
```

**Key Principles**:
- Checklist categories: Binary/near-binary (80% total weight)
- Subjective categories: Continuous scale with 2.0+ points (20% total weight)
- N/A conditions for environmental factors

### 2. Update Judge System Prompt

**File**: `config/judge/system_prompt.md`

**Critical sections**:

```markdown
## Evaluation Methodology

### Two Scoring Types

1. **Checklist Categories** (`scoring_type: "checklist"`)
   - Award ANY value between 0 and max
   - Proportional to satisfaction: 0.3, 0.7, 0.85, etc.
   - NOT limited to 0, 0.5, 1.0

2. **Subjective Categories** (`scoring_type: "subjective"`)
   - Continuous scale (e.g., 0.0 to 2.0)
   - Anchored examples at multiple levels
   - Engineering judgment

### Anchored Examples (max = 2.0)

- **2.0**: Exceptional - perfectly appropriate
- **1.7**: Excellent - minor improvements possible
- **1.4**: Good - solid with some complexity
- **1.0**: Acceptable - functional with concerns
- **0.6**: Marginal - significant issues
- **0.3**: Poor - barely functional
- **0.0**: Unacceptable - broken
```

**Why anchors matter**: Without them, judges default to 0/0.5/1 discrete scoring.

### 3. Implement Grade Aggregation (Multi-Run)

**File**: `src/scylla/e2e/models.py`

Add to `SubTestResult`:
```python
@dataclass
class SubTestResult:
    # ... existing fields ...
    grade_distribution: dict[str, int] | None = None  # {"A": 8, "B": 2}
    modal_grade: str | None = None
    min_grade: str | None = None
    max_grade: str | None = None
```

**File**: `src/scylla/e2e/subtest_executor.py`

In `_aggregate_results()`:
```python
# Aggregate grades
grades = [r.judge_grade for r in runs if r.judge_grade]
if grades:
    # Distribution
    grade_distribution = {}
    for g in grades:
        grade_distribution[g] = grade_distribution.get(g, 0) + 1

    # Modal (most common)
    modal_grade = max(grade_distribution, key=grade_distribution.get)

    # Range (F=worst, S=best)
    grade_order = ["F", "D", "C", "B", "A", "S"]
    grade_indices = [grade_order.index(g) for g in grades if g in grade_order]
    if grade_indices:
        min_grade = grade_order[min(grade_indices)]
        max_grade = grade_order[max(grade_indices)]
```

### 4. Update Reports

**File**: `src/scylla/e2e/run_report.py`

Add after runs table:
```python
if result.grade_distribution:
    grade_order = ["S", "A", "B", "C", "D", "F"]
    sorted_dist = sorted(
        result.grade_distribution.items(),
        key=lambda x: grade_order.index(x[0]) if x[0] in grade_order else 99,
    )
    dist_str = ", ".join(f"{g}={c}" for g, c in sorted_dist)
    md_lines.append(f"**Distribution**: {dist_str}")
    md_lines.append(f"**Modal Grade**: {result.modal_grade}")
    md_lines.append(f"**Grade Range**: {result.min_grade} - {result.max_grade}")
```

### 5. Test and Calibrate

```bash
# Run with multiple attempts to test variance
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 \
  --runs 3 \
  --parallel 3

# Check variance
jq '.summary | {mean: .mean_score, median: .median_score, std_dev: .std_dev, distribution: .grade_distribution}' \
  results/latest/T0/*/report.json

# Target: std_dev < 0.03 (3% variance)
```

## Failed Attempts & Lessons Learned

### ❌ Pure Checklist Approach
**What we tried**: 100% checklist with discrete 0/0.5/1 scoring

**Why it failed**:
- Too rigid - couldn't capture overall code quality
- Environmental noise penalized agents (pre-commit hooks, __pycache__)
- No engineering judgment capability

**Lesson**: Need subjective component for holistic quality assessment

### ❌ Pure Subjective Grading
**What we tried**: Vague criteria like "code quality: 0-1 score"

**Why it failed**:
- High variance (14% for identical outputs)
- Non-deterministic weights per criterion
- No reference points for scores

**Lesson**: Need objective anchors to reduce variance

### ❌ Discrete Scoring Only (0, 0.5, 1)
**What we tried**: Limited judges to three score values

**Why it failed**:
- Lost granularity - "good but not perfect" collapsed to 0.5
- Couldn't distinguish quality levels
- Partial credit impossible

**Lesson**: Continuous scoring with anchored examples essential

### ⚠️ Initial Weight Distribution
**What we tried**: 50/50 checklist/subjective split

**Why suboptimal**:
- Too much subjective weight increased variance
- 80/20 split found to be optimal balance

**Lesson**: Majority checklist (objective) with minority subjective (judgment)

## Results & Key Parameters

### Variance Reduction

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Variance (identical outputs) | 14% | 6% | <10% |
| Score range | 0.74-0.88 | 0.81-0.87 | ±0.05 |
| Scoring resolution | 3 values | Continuous | >10 distinct |

### Test Results (test-001, 24 subtests)

**Fractional scores observed**:
- Checklist: 0.8196, 0.8625, 0.867
- Subjective: 1.0, 1.7, 1.8 (on 2.0 scale)

**Grade distribution** (3 runs):
```
Distribution: A=3
Modal Grade: A
Grade Range: A - A
```

### Critical Configuration Values

**Weight Distribution**:
```yaml
functional: 0.35        # Core functionality
code_quality: 0.20      # Objective quality
proportionality: 0.15   # Scope appropriateness
build_pipeline: 0.10    # CI/CD compliance
overall_quality: 0.20   # Subjective judgment ← KEY
```

**Subjective Scale**:
- Use 2.0+ points (not 1.0)
- Provides granularity: 1.7 ≠ 1.8 ≠ 2.0

**Grade Ordering**:
```python
["F", "D", "C", "B", "A", "S"]  # For min/max calculation
```

## Implementation Checklist

When implementing this system:

- [ ] Create hybrid rubric (80% checklist, 20% subjective)
- [ ] Add `scoring_type` field to all categories
- [ ] Update judge system prompt with anchored examples
- [ ] Implement N/A handling for environmental factors
- [ ] Add grade aggregation fields to data models
- [ ] Update report generation (markdown + JSON)
- [ ] Test with multiple runs (min 3)
- [ ] Verify variance < 10%
- [ ] Check for fractional scores in output
- [ ] Validate backward compatibility

## Files Modified

**Core Evaluation**:
- `config/judge/system_prompt.md` - Judge instructions
- `tests/fixtures/tests/*/expected/rubric.yaml` - Task-specific rubrics

**Models & Logic**:
- `src/scylla/e2e/models.py` - Added grade fields to SubTestResult
- `src/scylla/e2e/subtest_executor.py` - Grade aggregation logic
- `src/scylla/e2e/llm_judge.py` - Rubric path parameter, parsing

**Reporting**:
- `src/scylla/e2e/run_report.py` - Grade statistics display

## References

- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- Anthropic recommendation: Combine multiple grader types (code-based + model-based)
- ProjectScylla implementation: `docs/eval_hybrid_approach.md`
- Test results: `results/2026-01-10T15-08-06-test-001/` (24 subtests, 6% variance)

## Quick Start

```bash
# 1. Design rubric with scoring_type fields
vim tests/fixtures/tests/my-task/expected/rubric.yaml

# 2. Update system prompt if needed (already done in this implementation)
# No action required - config/judge/system_prompt.md already updated

# 3. Run evaluation with multiple attempts
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/my-task \
  --runs 5 \
  --tiers T0

# 4. Check grade statistics
cat results/latest/T0/*/report.md | grep -A 5 "Grade Statistics"

# 5. Verify variance
jq '.summary | {std_dev, distribution: .grade_distribution}' \
  results/latest/T0/*/report.json
```

## Troubleshooting

**Problem**: Still seeing only 0/0.5/1 scores

**Solution**: Check system prompt includes "Award ANY value between 0 and max"

---

**Problem**: High variance still present (>10%)

**Solutions**:
1. Increase checklist weight (reduce subjective %)
2. Add more anchored examples
3. Make checklist criteria more objective
4. Check for environmental factors not marked N/A

---

**Problem**: Grade distribution not showing

**Solution**: Ensure `grade_distribution` field added to SubTestResult and passed from _aggregate_results()

---

**Problem**: Judges still using discrete 0/0.5/1

**Solution**: Add explicit instruction: "Do not limit yourself to 0, 0.5, or 1.0" in system prompt

## Success Indicators

✅ Variance < 10% for identical outputs
✅ Fractional scores appearing (0.82, 1.7, not just 0.5/1.0)
✅ Grade distribution showing counts
✅ Subjective category uses 2.0 scale with values like 1.7, 1.8
✅ N/A items excluded from scoring
✅ Backward compatible (old judgments still parse)

## Related Skills

- `evaluation/llm-judge-calibration` - Calibrating judges against human experts
- `evaluation/variance-analysis` - Analyzing and debugging score variance
- `evaluation/rubric-design` - Designing effective evaluation rubrics
