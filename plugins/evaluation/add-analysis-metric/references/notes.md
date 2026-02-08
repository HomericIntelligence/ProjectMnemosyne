# Implementation Notes: Impl-Rate Metric

## Session Timeline

**Date:** 2026-01-31
**Task:** P1-7 from comprehensive audit report
**Outcome:** Success - PR #285 created and merged

## Conversation Flow

1. **User request:** "lets implement P1-7"
2. **Research phase:** Read metrics-definitions.md to understand Impl-Rate specification
3. **Data exploration:** Examined actual judgment.json to understand criteria structure
4. **Implementation:** 5 phases (stats → dataframes → export → tests → verification)
5. **User feedback:** "make sure that impl-rate is re-used across codebase"
6. **Verification:** Grep search confirmed no duplicate calculations
7. **PR creation:** Created PR #285 with auto-merge enabled

## Key Insights

### Architecture Pattern

The analysis pipeline follows a strict 4-layer architecture:

```
RAW DATA (~/fullruns/)
    ↓
LOADER LAYER (loader.py)
    ↓
TRANSFORM LAYER (dataframes.py)
    ↓
STATISTICS LAYER (stats.py)
    ↓
OUTPUT LAYER (tables.py, figures/, export_data.py)
```

**Critical rule:** Never calculate metrics in loader.py - that's the transform layer's job.

### Data Structure Discovery

**Actual judgment.json structure:**
```json
{
  "score": 0.0,
  "criteria_scores": {
    "functional": {
      "achieved": 0.0,
      "max": 3.5,
      "score": 0.0,
      "items": {
        "F1": {"achieved": 0.0, "max": 1.0, "reason": "..."},
        "F2": {"achieved": 0.0, "max": 1.0, "reason": "..."}
      }
    },
    "code_quality": {
      "achieved": 0.0,
      "max": 2.0,
      "score": 0.0,
      "items": {...}
    }
  }
}
```

This informed the calculation:
```python
total_achieved = sum(criterion.achieved for criterion in judge.criteria.values())
total_max = sum(criterion.max_points for criterion in judge.criteria.values())
```

### Consensus Pattern

**Pattern used throughout codebase:**
- 3 judges evaluate each run independently
- Consensus score = **median** across 3 judges
- Consensus passed = **majority vote** across 3 judges

**Applied to impl_rate:**
```python
judge_impl_rates = [compute_impl_rate(...) for judge in run.judges]
consensus_impl_rate = np.median(judge_impl_rates) if judge_impl_rates else np.nan
```

### Test Fixture Design

**Key principle:** Test data should be **realistic and correlated**

```python
# NOT just random:
impl_rate = np.random.uniform(0.0, 1.0)  # ❌ Unrealistic

# Correlated to score (with variation):
impl_rate = score + np.random.uniform(-0.05, 0.05)  # ✅ Realistic
impl_rate = max(0.0, min(1.0, impl_rate))  # Clamp to valid range
```

This ensures:
- Tests catch missing correlations
- Aggregations produce sensible results
- Edge cases are still exercised

## Code Snippets

### Complete Metric Function

```python
def compute_impl_rate(achieved_points: float, max_points: float) -> float:
    """Compute Implementation Rate (Impl-Rate) metric.

    Impl-Rate measures the proportion of semantic requirements satisfied,
    providing more granular feedback than binary pass/fail. It aggregates
    points achieved across all rubric criteria.

    Args:
        achieved_points: Total points achieved across all criteria
        max_points: Total maximum possible points across all criteria

    Returns:
        Implementation rate in [0, 1], or NaN if max_points is 0

    Examples:
        >>> compute_impl_rate(8.5, 10.0)
        0.85
        >>> compute_impl_rate(0.0, 10.0)
        0.0
        >>> import numpy as np
        >>> np.isnan(compute_impl_rate(0.0, 0.0))
        True

    """
    if max_points == 0:
        return np.nan
    return achieved_points / max_points
```

### Integration in build_runs_df

```python
def build_runs_df(experiments: dict[str, list[RunData]]) -> pd.DataFrame:
    rows = []
    for runs in experiments.values():
        for run in runs:
            # Calculate impl_rate for each judge, then take median (consensus)
            judge_impl_rates = []
            for judge in run.judges:
                total_achieved = sum(
                    criterion.achieved for criterion in judge.criteria.values()
                )
                total_max = sum(
                    criterion.max_points for criterion in judge.criteria.values()
                )
                impl_rate = compute_impl_rate(total_achieved, total_max)
                judge_impl_rates.append(impl_rate)

            # Consensus impl_rate: median across judges (matching consensus score logic)
            import numpy as np
            consensus_impl_rate = (
                np.median(judge_impl_rates) if judge_impl_rates else np.nan
            )

            rows.append({
                "experiment": run.experiment,
                "agent_model": run.agent_model,
                "tier": run.tier,
                "subtest": run.subtest,
                "run_number": run.run_number,
                "score": run.score,
                "impl_rate": consensus_impl_rate,  # NEW FIELD
                "passed": run.passed,
                # ... rest of fields ...
            })

    return pd.DataFrame(rows)
```

### Complete Test Function

```python
def test_compute_impl_rate():
    """Test Implementation Rate (Impl-Rate) metric."""
    import numpy as np
    from scylla.analysis.stats import compute_impl_rate

    # Perfect implementation (all requirements satisfied)
    impl_rate = compute_impl_rate(10.0, 10.0)
    assert abs(impl_rate - 1.0) < 1e-6

    # Partial implementation
    impl_rate = compute_impl_rate(8.5, 10.0)
    assert abs(impl_rate - 0.85) < 1e-6

    # Zero implementation (complete failure)
    impl_rate = compute_impl_rate(0.0, 10.0)
    assert abs(impl_rate - 0.0) < 1e-6

    # Edge case: zero max_points (no rubric defined)
    impl_rate = compute_impl_rate(0.0, 0.0)
    assert np.isnan(impl_rate)

    # Edge case: float precision
    impl_rate = compute_impl_rate(7.3, 12.5)
    assert abs(impl_rate - 0.584) < 1e-6
```

## Metric Definition Reference

**From `.claude/shared/metrics-definitions.md`:**

```
### Implementation Rate (Impl-Rate)

**Definition**: Proportion of semantic requirements satisfied by the solution.

**Formula**:
Impl-Rate = satisfied_requirements / total_requirements

**Range**: [0, 1]

**Interpretation**:
- Measures partial credit for incomplete solutions
- More granular than binary Pass-Rate

**Notes**:
- Requires predefined requirement checklist
- Each requirement should be independently verifiable
```

**From `docs/design/metrics-formulas.md`:**

```
### Implementation Rate (impl_rate)

Semantic requirement satisfaction from the judge's weighted score.

impl_rate = judgment.summary.weighted_score

Value range: [0.0, 1.0]
```

**Implementation decision:**
We calculated impl_rate from criteria rather than using `weighted_score` directly because:
1. More transparent (shows calculation from first principles)
2. Matches the formula in metrics-definitions.md
3. Allows per-criterion analysis in future

## Commands Used

```bash
# Initial exploration
grep -r "impl.?rate" --include="*.py" --include="*.md"
find ~/fullruns -name "judgment.json" | head -1 | xargs cat | jq '.'

# Test new function
pixi run -e analysis pytest tests/unit/analysis/test_stats.py::test_compute_impl_rate -xvs

# Test dataframes integration
pixi run -e analysis pytest tests/unit/analysis/test_dataframes.py -xvs

# Test tables integration
pixi run -e analysis pytest tests/unit/analysis/test_tables.py -xvs

# Run all analysis tests
pixi run -e analysis pytest tests/unit/analysis/ -q

# Git workflow
git checkout -b implement-impl-rate
git add scylla/ tests/ scripts/
git commit -m "feat(metrics): Implement Impl-Rate metric (P1-7)"
git push -u origin implement-impl-rate
gh pr create --title "..." --body "..."
gh pr merge --auto --rebase 285
```

## Test Output

```
============================= test session starts ==============================
119 passed, 2 skipped, 6 warnings in 3.15s
```

**Breakdown:**
- test_stats.py: 33 tests (including new test_compute_impl_rate)
- test_dataframes.py: 11 tests
- test_tables.py: 23 tests
- test_figures.py: 24 tests
- test_loader.py: 28 tests

## Remaining Metrics to Implement

From audit report, 8 more metrics not yet implemented:

1. **R_Prog** (Fine-Grained Progress Rate) - P3 priority
2. **Ablation Score** - P2 priority
3. **CFP** (Change Fail Percentage) - P3 priority
4. **Strategic Drift** - P3 priority
5. **Tool Success Rate** - P3 priority
6. **Delegation Overhead** - P3 priority
7. **Correction Frequency** - P3 priority
8. Tier-specific metrics - P3 priority

**This skill can be used for implementing any of the above.**

## Related PRs

- PR #281: P0-1, P1-1, P1-2, P1-3, P1-6 (first batch)
- PR #282: P0-2 (table tests)
- PR #283: P1-5 (BibTeX references)
- PR #284: P1-4 (loader tests)
- **PR #285: P1-7 (this implementation)** ← YOU ARE HERE

## Success Metrics

- ✅ Zero code duplication (single `compute_impl_rate()` function)
- ✅ Reused across all layers (dataframes, export)
- ✅ Comprehensive test coverage (5 test cases)
- ✅ All 119 tests passing
- ✅ No performance regression
- ✅ Proper NaN handling for edge cases
- ✅ Export to all JSON outputs (overall, by_model, by_tier)

## Lessons for Next Metric

1. **Start with definition** - Read metrics-definitions.md first
2. **Understand data structure** - Check actual JSON files in ~/fullruns
3. **Follow the layers** - stats.py → dataframes.py → export_data.py → tests
4. **Update ALL aggregations** - Don't forget subtests AND tiers
5. **Use NaN consistently** - For edge cases, not 0.0
6. **Test fixtures matter** - Update conftest.py with realistic correlated data
7. **Verify integration** - Grep for manual calculations to ensure reuse
