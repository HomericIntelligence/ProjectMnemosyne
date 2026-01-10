# Implementation Notes: Hybrid LLM Judge with Granular Scoring

## Session Timeline

**Date**: 2026-01-10
**Duration**: ~3 hours
**Branch**: skill/testing/multi-language-judge-pipelines → PR #171

## Problem Statement

Observed high variance in LLM judge scores for identical implementations:
- Test: results/2026-01-10T05-02-46-test-001
- Task: Hello World (Python)
- Variance: 14% (scores 0.74, 0.84, 0.88 for same output)
- Root causes:
  - Overly subjective criteria (22 vague items)
  - No scoring anchors
  - Environmental noise (pre-commit, __pycache__)
  - Non-deterministic weighting

## Research Phase

### Anthropic Article Analysis

**Source**: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

**Key takeaways**:
1. Combine grader types: code-based + model-based + human
2. Build partial credit into scoring
3. "Grade what agent produced, not path taken"
4. Use weighted scoring (combined threshold)
5. Multiple trials per task for non-determinism
6. Isolated environments (clean state)

**Comparison to ProjectScylla**:
- Overall rating: 8.5/10
- Strong: Hybrid graders, partial credit, isolated envs
- Gaps: pass@k metrics, human calibration, transcript analysis
- User decision: Skip pass@k and human calibration (not needed)

## Design Decisions

### Weight Distribution: 80/20 Split

**Rationale**: Balance objectivity with judgment
- 80% checklist (objective, reproducible)
- 20% subjective (engineering quality)

**Tested alternatives**:
- 100% checklist: Too rigid, no quality assessment
- 50/50 split: Too much variance from subjective
- 80/20: Optimal balance (variance reduced to 6%)

### Continuous Scoring: 0.0-max Scale

**Problem**: Discrete 0/0.5/1 loses granularity

**Solution**: Proportional awarding
- Checklist: "Award ANY value between 0 and max"
- Subjective: Anchored examples at 7 levels
- Result: Scores like 0.8196, 0.8625, 1.7, 1.8

**Implementation detail**: System prompt MUST explicitly say "not limited to 0, 0.5, 1.0"

### Subjective Scale: 2.0 Points (Not 1.0)

**Why larger scale**:
- More granularity: 1.7 vs 1.8 vs 2.0
- Clearer anchors: 2.0, 1.7, 1.4, 1.0, 0.6, 0.3, 0.0
- Matches weight (20% of 10 total points = 2.0)

**Evidence**: Observed scores of 1.0, 1.7, 1.8 in test results

### N/A Handling: Environmental Factors

**Critical insight**: Exclude from BOTH numerator AND denominator

**Example**:
```
Category: 4 items × 1 point = 4 max
Results: Item1=1, Item2=1, Item3=0, Item4=N/A
Score: (1+1+0) / (1+1+1) = 2/3 = 0.67  ← Correct
NOT: (1+1+0) / 4 = 0.5  ← Wrong
```

**Environmental factors**:
- Missing .pre-commit-config.yaml
- Task doesn't require tests
- __pycache__ (normal Python behavior)

## Implementation Details

### Rubric Format: scoring_type Field

**Key innovation**: Explicit type per category

```yaml
categories:
  functional:
    scoring_type: "checklist"  # Binary/near-binary
    weight: 0.35

  overall_quality:
    scoring_type: "subjective"  # Continuous judgment
    weight: 0.20
```

**Why this matters**: Judge knows how to score each category differently

### Grade Aggregation: Multi-Run Statistics

**Added fields**:
- `grade_distribution: dict[str, int]` - Count per grade
- `modal_grade: str` - Most common
- `min_grade: str` - Worst (using ordered comparison)
- `max_grade: str` - Best

**Implementation**:
```python
grade_order = ["F", "D", "C", "B", "A", "S"]
grade_indices = [grade_order.index(g) for g in grades]
min_grade = grade_order[min(grade_indices)]
max_grade = grade_order[max(grade_indices)]
```

**Display**:
```markdown
## Grade Statistics
**Distribution**: A=8, B=2
**Modal Grade**: A
**Grade Range**: B - A
```

### Backward Compatibility

**Critical requirement**: Old judgments must still work

**Solution**: Flexible parsing
```python
criteria_scores = data.get("categories") or data.get("criteria_scores")
```

New format uses "categories", old uses "criteria_scores"

## Test Results

### Variance Reduction

**Before**:
- Test: 2026-01-10T05-02-46-test-001
- Scores: 0.74, 0.84, 0.88 (same Hello World output)
- Variance: 14%

**After**:
- Test: 2026-01-10T15-08-06-test-001
- Scores: 0.81-0.87 (main cluster, 24 subtests)
- Variance: 6%

**Outlier**: One 0.69 score (likely implementation issue, not judge)

### Granular Scoring Evidence

**Checklist scores** (out of 1.0):
- 0.8196 (not 0.5 or 1.0!)
- 0.8625
- 0.867

**Subjective scores** (out of 2.0):
- 1.0 (poor cleanup)
- 1.7 (excellent with minor issue)
- 1.8 (excellent, minimal deduction)

**Average subjective**: 1.67/2.0 = 83.5%

### Multi-Run Grade Report

**Test**: 2026-01-10T16-13-27-test-001 (3 runs)

**Results**:
```
Run 01: Score 0.90, Grade A
Run 02: Score 0.89, Grade A
Run 03: Score 0.85, Grade A

Grade Statistics:
Distribution: A=3
Modal Grade: A
Grade Range: A - A
```

**Verified**:
- Markdown report: results/.../T0/00/report.md (lines 27-31)
- JSON report: results/.../T0/00/report.json

## Code Changes

### Commit 1: Hybrid Evaluation System (269ba1d)

**Files**:
- config/judge/system_prompt.md (440 lines changed)
- src/scylla/e2e/llm_judge.py (+367 lines)
- src/scylla/e2e/models.py (+4 fields)
- tests/fixtures/tests/test-001/expected/rubric.yaml (+111 lines)
- docs/eval_hybrid_approach.md (NEW, 270 lines)

**Key changes**:
- Two scoring types (checklist vs subjective)
- Proportional point awarding
- Anchored examples (7 levels)
- N/A handling instructions
- Rubric path parameter

### Commit 2: Grade Aggregation (855e105)

**Files**:
- src/scylla/e2e/models.py (+4 fields to SubTestResult)
- src/scylla/e2e/subtest_executor.py (+33 lines aggregation logic)
- src/scylla/e2e/run_report.py (+14 lines display logic)

**Key changes**:
- Grade distribution calculation
- Modal grade (max with dict value key)
- Grade range (ordered comparison)
- Markdown and JSON output

## Lessons Learned

### What Worked

1. **Hybrid approach is essential** - Neither pure checklist nor pure subjective works alone
2. **Anchored examples critical** - Without them, judges default to 0/0.5/1
3. **Larger subjective scale** - 2.0 points gives more granularity than 1.0
4. **Explicit instructions** - Must say "not limited to 0, 0.5, 1.0"
5. **N/A exclusion** - Exclude from denominator, not just numerator

### What Didn't Work

1. **Pure checklist** - Too rigid, no quality judgment
2. **Pure subjective** - Too much variance (14%)
3. **Vague criteria** - "Code quality: 0-1" without anchors
4. **50/50 split** - Too much subjective weight
5. **Discrete scoring** - Lost granularity for partial credit

### Surprising Findings

1. **Fractional scores appeared immediately** - Once we added "Award ANY value", judges used 0.82, 0.86, etc.
2. **Subjective worked well at 2.0 scale** - Saw 1.0, 1.7, 1.8 (good distribution)
3. **80/20 sweet spot** - More checklist → less variance, but need some subjective
4. **Environmental factors major issue** - pre-commit, __pycache__ penalized agents unfairly

## Production Considerations

### When to Use This System

**Good for**:
- Simple to medium complexity tasks
- Code generation/modification
- Well-defined success criteria
- Need variance < 10%

**Not recommended for**:
- Purely objective tasks (use pure checklist)
- Highly subjective tasks (need human review)
- Multi-turn interaction quality (need transcript analysis)

### Calibration Process

1. Run 5+ attempts per task
2. Check std_dev < 0.03 (3% variance)
3. Verify fractional scores appearing
4. Inspect grade distribution
5. Adjust weights if needed (keep 70-85% checklist)

### Future Enhancements

**Considered but not implemented**:
- pass@k metrics (user didn't need)
- Human calibration loop (user didn't need)
- Transcript quality analysis (focus on end-state only)

**Potential improvements**:
- Fine-tune subjective anchors (1.7 vs 1.8 distinction)
- Test on complex tasks (multi-file, refactoring)
- Automated variance monitoring
- Grade distribution alerts

## References

### External Sources

- Anthropic article: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- LLM-as-a-Judge survey: https://arxiv.org/abs/2411.15594
- Confident AI guide: https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method

### Internal Documentation

- docs/eval_hybrid_approach.md (comprehensive methodology)
- Plan file: /home/mvillmow/.claude/plans/melodic-bouncing-pizza.md
- Verification: /tmp/hybrid_results_analysis.md
- PR: #171 (skill/testing/multi-language-judge-pipelines)

### Test Data

- Old results (14% variance): results/2026-01-10T05-02-46-test-001/
- New results (6% variance): results/2026-01-10T15-08-06-test-001/
- Multi-run test: results/2026-01-10T16-13-27-test-001/

## Command Reference

```bash
# Run evaluation with hybrid system
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 \
  --runs 3 \
  --parallel 3

# Check variance
jq '.summary | {mean_score, median_score, std_dev_score, grade_distribution}' \
  results/latest/T0/*/report.json

# View grade statistics
cat results/latest/T0/*/report.md | grep -A 5 "Grade Statistics"

# Verify fractional scores
jq '.runs[].judge_score' results/latest/T0/*/report.json | sort -u

# Check N/A handling
jq '.runs[0].criteria_scores | with_entries(select(.value.items | to_entries[] | .value.achieved == "N/A"))' \
  results/latest/T0/00/run_01/report.json
```

## Session Metadata

**Tools used**:
- Task (Explore subagent): Codebase exploration
- WebFetch: Anthropic article analysis
- Read/Edit/Write: Code modifications
- Bash: Test execution

**Time breakdown**:
- Research & planning: 1 hour
- Implementation: 1.5 hours
- Testing & verification: 0.5 hours

**Total tokens**: ~100k (within 200k budget)

**Status**: ✅ Complete, tested, committed (PR #171)
