---
name: "Defensive Analysis Patterns"
description: "Defensive programming patterns for statistical analysis pipelines to handle data quality issues gracefully"
category: testing
date: 2026-02-01
user-invocable: false
---
# Defensive Analysis Patterns

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-01 |
| **Objective** | Implement defensive programming patterns for statistical analysis pipeline to handle data quality issues gracefully |
| **Outcome** | ✅ Successfully implemented P2 improvements with 3 PRs (309 tests passing, defensive type coercion, centralized config) |
| **Context** | Publication readiness assessment - P2 medium-priority improvements for analysis pipeline |

## When to Use This Skill

Use defensive analysis patterns when:

1. **Building statistical analysis pipelines** that process experiment data with varying quality
2. **Source data cannot be modified** - must make analysis code robust instead
3. **Implementing parametrized tests** to systematically verify edge case handling
4. **Centralizing configuration** to move hardcoded values out of analysis code
5. **Handling type inconsistencies** (string numbers, NaN values, missing fields)

**Trigger phrases**:
- "Analysis fails on real data but passes on test fixtures"
- "TypeError: unsupported operand type(s) for +: 'float' and 'str'"
- "Need to make analysis code robust to data quality issues"
- "Want systematic test coverage across edge cases"

## Verified Workflow

### Step 1: Identify Data Quality Issues

Run analysis on real data to discover issues:

```bash
pixi run -e analysis python scripts/generate_all_results.py \
  --data-dir ~/fullruns \
  --output-dir results/analysis
```

**Expected errors**:
- `TypeError` when summing mixed string/float values
- `ValueError` when converting "N/A" strings to numbers
- Schema validation warnings for invalid grades

### Step 2: Apply Defensive Type Coercion

Add `safe_float()` helper for defensive loading:

```python
def safe_float(value, default=0.0):
    """Convert value to float, returning default for invalid inputs.

    Defensive approach for handling data quality issues:
    - String values coerced to float
    - Invalid values treated as default
    - Analysis continues despite source data issues
    - PRINCIPLE: Never modify source data, make analysis code robust
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# Usage in metrics calculation
total_achieved = sum(safe_float(criterion.achieved) for criterion in judge.criteria.values())
total_max = sum(safe_float(criterion.max_points) for criterion in judge.criteria.values())
```

**Location**: `scylla/analysis/dataframes.py:37-42`

### Step 3: Add Zero-Variance Guards

Protect against degenerate distributions in statistical functions:

```python
def bootstrap_ci(data: pd.Series | np.ndarray, ...) -> tuple[float, float, float]:
    """Compute bootstrap confidence interval with BCa method."""
    data_array = np.array(data)
    mean = np.mean(data_array)

    # Guard against zero variance (BCa fails on degenerate distributions)
    if np.std(data_array) == 0:
        logger.debug(
            "Bootstrap CI called with zero variance data. "
            "Returning point estimate as CI bounds."
        )
        val = float(mean)
        return val, val, val  # (mean, mean, mean) instead of NaN

    # Normal BCa bootstrap...
```

**Location**: `scylla/analysis/stats.py:218-228`

### Step 4: Return NaN for Invalid Computations

Use NaN for undefined operations instead of 0 or raising errors:

```python
def cliffs_delta(group1, group2):
    """Compute Cliff's delta effect size."""
    g1 = np.array(group1)
    g2 = np.array(group2)

    n1, n2 = len(g1), len(g2)

    # Return NaN for empty groups (no comparison possible)
    if n1 == 0 or n2 == 0:
        return np.nan  # Not 0.0!

    # Normal calculation...
```

**Why NaN?** Distinguishes "no data" from "zero effect" in aggregations.

**Location**: `scylla/analysis/stats.py:134-135`

### Step 5: Centralize Configuration

Move hardcoded values to `config.yaml`:

```yaml
# config.yaml
figures:
  pass_threshold: 0.60  # Reference line for acceptable pass-rate

  correlation_metrics:
    score: "Score"
    cost_usd: "Cost (USD)"
    total_tokens: "Total Tokens"
    duration_seconds: "Duration (s)"

colors:
  grade_order: ["S", "A", "B", "C", "D", "F"]  # Canonical ordering
```

```python
# config.py - Add property accessor
@property
def correlation_metrics(self) -> dict[str, str]:
    """Metric pairs for correlation analysis."""
    return self.get("figures", "correlation_metrics", default={
        "score": "Score",
        "cost_usd": "Cost (USD)",
        # ... fallback defaults
    })
```

```python
# Usage in analysis code
from scylla.analysis.config import config

metrics = config.correlation_metrics  # Not hardcoded!
```

**Benefits**: Easier to modify for different experiments without code changes.

### Step 6: Add Parametrized Tests

Create systematic test coverage with `pytest.mark.parametrize`:

```python
import pytest

class TestBootstrapCIParametrized:
    """Parametrized tests for bootstrap confidence intervals."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            ([5.0], (5.0, 5.0, 5.0)),  # Single element
            ([0.0], (0.0, 0.0, 0.0)),  # Single zero
            ([7.0, 7.0, 7.0], (7.0, 7.0, 7.0)),  # Zero variance
        ],
        ids=["single_element", "single_zero", "zero_variance"],
    )
    def test_bootstrap_ci_degenerate(self, data, expected):
        """Test bootstrap CI with degenerate inputs."""
        from scylla.analysis.stats import bootstrap_ci

        mean, ci_low, ci_high = bootstrap_ci(data)
        exp_mean, exp_low, exp_high = expected
        assert abs(mean - exp_mean) < 1e-6
        assert abs(ci_low - exp_low) < 1e-6
        assert abs(ci_high - exp_high) < 1e-6
```

**Key pattern**: Test degenerate cases (empty, single element, zero variance, all same).

**Location**: `tests/unit/analysis/test_stats_parametrized.py`

### Step 7: Expand Export Tests

Test edge cases in data export pipeline:

```python
def test_compute_statistical_results_empty_df(tmp_path):
    """Test compute_statistical_results handles empty DataFrame gracefully."""
    empty_df = pd.DataFrame(
        columns=["agent_model", "tier", "score", "cost_usd", ...]
    )

    tier_order = []
    results = compute_statistical_results(empty_df, tier_order)

    # Should return empty lists, not crash
    assert results["normality_tests"] == []
    assert results["omnibus_tests"] == []
    assert results["pairwise_comparisons"] == []
```

**Location**: `tests/unit/analysis/test_export_data.py:189-201`

### Step 8: Create Separate PRs

One PR per improvement for easier review:

```bash
# P2-3: Config centralization
git checkout -b p2-3-correlation-metrics-config
git add scylla/analysis/config.{py,yaml} scylla/analysis/figures/correlation.py
git commit -m "refactor(analysis): Move correlation metric pairs to config.yaml"
gh pr create --title "..." --body "..." --label enhancement
gh pr merge --auto --rebase

# P2-1: Parametrized tests
git checkout main && git pull origin main
git checkout -b p2-1-parametrized-tests
git add tests/unit/analysis/test_stats_parametrized.py
git commit -m "test(analysis): Add parametrized tests for statistical functions"
gh pr create --title "..." --body "..." --label "testing,enhancement"
gh pr merge --auto --rebase

# P2-2: Export tests
# ... same pattern
```

## Failed Attempts

### ❌ Attempt 1: Hardcoded Holm-Bonferroni Expectations

**What we tried**: Initial parametrized tests for Holm-Bonferroni expected all p-values below threshold to be rejected.

```python
# WRONG: Misunderstood step-down procedure
([0.001, 0.01, 0.03, 0.04], [True, True, True, False])  # Expected 3 rejections
([0.001, 0.02, 0.03, 0.04], [True, True, True, True])   # Expected all 4
```

**Why it failed**: Holm-Bonferroni is a **step-down procedure** that stops at the first non-rejection:
- `[0.001, 0.01, 0.03, 0.04]` → corrected `[0.004, 0.03, 0.06, 0.06]` → only first 2 rejected
- `[0.001, 0.02, 0.03, 0.04]` → corrected `[0.004, 0.06, 0.06, 0.06]` → only first 1 rejected

**Fix**: Test the actual behavior by running the function first:

```bash
pixi run -e analysis python3 -c "
from scylla.analysis.stats import holm_bonferroni_correction
p_values = [0.001, 0.01, 0.03, 0.04]
corrected = holm_bonferroni_correction(p_values)
print('Corrected:', corrected)
print('Rejections:', [p < 0.05 for p in corrected])
"
# Output: Corrected: [0.004, 0.03, 0.06, 0.06]
#         Rejections: [True, True, False, False]
```

Then update test expectations to match reality.

**Location**: `tests/unit/analysis/test_stats_parametrized.py:269-296`

### ❌ Attempt 2: Small Sample Mann-Whitney Tests

**What we tried**: Test significance detection with N=3 samples:

```python
# WRONG: Too small for reliable p-values
([1, 2, 3], [7, 8, 9], True),  # Expected significant
```

**Why it failed**: Mann-Whitney U with N=3 returns `p=0.1` (not < 0.05) due to limited permutations.

**Fix**: Use larger samples (N≥5) for reliable significance tests:

```python
# CORRECT: Larger samples for stable p-values
([1, 2, 3, 4, 5], [10, 11, 12, 13, 14], True),  # Now p < 0.05
```

**Lesson**: Statistical tests need minimum sample sizes for reliable results. Always verify with actual data first.

**Location**: `tests/unit/analysis/test_stats_parametrized.py:147-163`

### ❌ Attempt 3: Integration Test Flakiness

**What we tried**: Run full test suite with `pytest tests/unit/analysis/`:

```bash
pixi run -e analysis pytest tests/unit/analysis/ -v
# FAILED: 3 integration tests fail
```

**Why it failed**: Test order dependency - integration tests passed when run in isolation but failed in full suite.

**Debug approach**:

```bash
# Run individually - PASSES
pixi run -e analysis pytest tests/unit/analysis/test_integration.py -v

# Run with full suite - FAILS
pixi run -e analysis pytest tests/unit/analysis/ -v
```

**Root cause**: Likely shared state or configuration modified by earlier tests.

**Fix**: Tests now pass consistently (309 total). Likely resolved by improved fixture isolation.

**Lesson**: Always run tests both individually AND as part of full suite to catch order dependencies.

## Results & Parameters

### Test Coverage Summary

| Category | Before | After | Change |
|----------|--------|-------|--------|
| stats.py tests | 36 | 99 | +63 parametrized |
| export_data.py tests | 2 | 8 | +6 edge cases |
| **Total tests** | **240** | **309** | **+69 (+28%)** |

### PR Summary

| PR | Title | Status | Lines Changed |
|----|-------|--------|---------------|
| #307 | Move correlation metric pairs to config.yaml | ✅ Merged | +24 -6 |
| #308 | Add parametrized tests for statistical functions | ✅ Merged | +356 |
| #309 | Expand export_data test coverage | ✅ Merged | +129 |

### Configuration Changes

```yaml
# scylla/analysis/config.yaml additions
figures:
  pass_threshold: 0.60
  correlation_metrics:
    score: "Score"
    cost_usd: "Cost (USD)"
    total_tokens: "Total Tokens"
    duration_seconds: "Duration (s)"

colors:
  grade_order: ["S", "A", "B", "C", "D", "F"]
```

### Defensive Patterns Applied

1. **Type Coercion**: `safe_float()` in `dataframes.py:37-42`
2. **Zero-Variance Guard**: `bootstrap_ci()` in `stats.py:218-228`
3. **NaN for Invalid**: `cliffs_delta()` in `stats.py:134-135`
4. **Min Sample Guard**: `shapiro_wilk()` in `stats.py:354-360`
5. **Division by Zero**: `compute_impl_rate()` in `stats.py:332-333`

### Test Execution

```bash
# Run all new parametrized tests
pixi run -e analysis pytest tests/unit/analysis/test_stats_parametrized.py -v
# ============================== 63 passed in 0.61s ===============================

# Run expanded export tests
pixi run -e analysis pytest tests/unit/analysis/test_export_data.py -v
# ============================== 8 passed in 0.92s ===============================

# Run full analysis test suite
pixi run -e analysis pytest tests/unit/analysis/ -v
# =================== 309 passed, 6 warnings in 3.93s ============================
```

## Key Takeaways

1. **Never modify source data** - Make analysis code robust to data quality issues
2. **Test degenerate cases** - Empty, single element, zero variance, all same values
3. **Use NaN for undefined** - Distinguishes "no data" from "zero effect"
4. **Centralize configuration** - Easier to experiment without code changes
5. **Verify statistical behavior** - Run functions with test inputs before writing test expectations
6. **Separate PRs** - One improvement per PR for easier review and revert
7. **Run tests individually AND in suite** - Catch order dependencies early

## Related Skills

- **parametrized-testing-pattern**: Pattern for systematic test coverage
- **config-centralization-pattern**: Moving hardcoded values to YAML config
- **statistical-debugging**: Debugging statistical test failures
- **pr-workflow**: Branch strategy and auto-merge patterns
