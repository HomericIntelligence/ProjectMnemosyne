---
name: "Skill: Add Analysis Metric to Pipeline"
description: "Workflow for adding new metrics to ProjectScylla analysis pipeline"
category: evaluation
date: 2026-01-31
user-invocable: false
---
# Skill: Add Analysis Metric to Pipeline

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-31 |
| **Objective** | Implement new metric (Impl-Rate) across entire analysis pipeline |
| **Outcome** | ✅ Success - 119 tests passing, metric integrated end-to-end |
| **Files Modified** | 5 (stats.py, dataframes.py, export_data.py, test_stats.py, conftest.py) |
| **Test Coverage** | +1 metric test, all 119 tests passing |

## When to Use This Skill

**Trigger conditions:**
- Implementing a new metric from `.claude/shared/metrics-definitions.md`
- Adding calculated fields to dataframes (runs_df, judges_df, subtests_df)
- Extending statistical analysis functions
- Exporting new metrics in `summary.json`

**Prerequisites:**
- Metric definition exists in documentation
- Understanding of 4-layer architecture: loader → dataframes → stats → tables
- Access to test fixtures in `tests/unit/analysis/conftest.py`

## Verified Workflow

### Phase 1: Core Function Implementation

**File: `scylla/analysis/stats.py`**

1. Add the metric calculation function after related functions (e.g., `compute_cop`):

```python
def compute_impl_rate(achieved_points: float, max_points: float) -> float:
    """Compute Implementation Rate (Impl-Rate) metric.

    Impl-Rate measures the proportion of semantic requirements satisfied,
    providing more granular feedback than binary pass/fail.

    Args:
        achieved_points: Total points achieved across all criteria
        max_points: Total maximum possible points across all criteria

    Returns:
        Implementation rate in [0, 1], or NaN if max_points is 0

    Examples:
        >>> compute_impl_rate(8.5, 10.0)
        0.85
    """
    if max_points == 0:
        return np.nan
    return achieved_points / max_points
```

**Key decisions:**
- Return `np.nan` (not `0.0`) for edge cases to distinguish missing from zero
- Follow existing function naming pattern (`compute_*`)
- Include docstring with formula, range, and examples

### Phase 2: DataFrame Integration

**File: `scylla/analysis/dataframes.py`**

**2a. Import the function:**

```python
from scylla.analysis.stats import compute_consistency, compute_cop, compute_impl_rate
```

**2b. Add to runs DataFrame (consensus across judges):**

```python
def build_runs_df(experiments: dict[str, list[RunData]]) -> pd.DataFrame:
    # ... existing code ...
    for run in runs:
        # Calculate impl_rate for each judge, then take median (consensus)
        judge_impl_rates = []
        for judge in run.judges:
            total_achieved = sum(
                criterion.achieved for criterion in judge.criteria.values()
            )
            total_max = sum(criterion.max_points for criterion in judge.criteria.values())
            impl_rate = compute_impl_rate(total_achieved, total_max)
            judge_impl_rates.append(impl_rate)

        # Consensus impl_rate: median across judges
        import numpy as np
        consensus_impl_rate = (
            np.median(judge_impl_rates) if judge_impl_rates else np.nan
        )

        rows.append({
            # ... existing fields ...
            "impl_rate": consensus_impl_rate,  # ADD THIS
        })
```

**2c. Add to judges DataFrame (per-judge values):**

```python
def build_judges_df(experiments: dict[str, list[RunData]]) -> pd.DataFrame:
    for judge in run.judges:
        # Calculate impl_rate for this judge
        total_achieved = sum(
            criterion.achieved for criterion in judge.criteria.values()
        )
        total_max = sum(criterion.max_points for criterion in judge.criteria.values())
        judge_impl_rate = compute_impl_rate(total_achieved, total_max)

        rows.append({
            # ... existing fields ...
            "judge_impl_rate": judge_impl_rate,  # ADD THIS
        })
```

**2d. Add to subtests aggregation:**

```python
def compute_subtest_stats(group: pd.DataFrame) -> pd.Series:
    # ... existing stats ...
    mean_impl_rate = group["impl_rate"].mean()
    median_impl_rate = group["impl_rate"].median()
    std_impl_rate = group["impl_rate"].std()

    return pd.Series({
        # ... existing fields ...
        "mean_impl_rate": mean_impl_rate,
        "median_impl_rate": median_impl_rate,
        "std_impl_rate": std_impl_rate,
    })
```

**2e. Add to tier aggregation:**

```python
def compute_tier_stats(group: pd.DataFrame) -> pd.Series:
    # ... existing stats ...
    mean_impl_rate = group["impl_rate"].mean()
    median_impl_rate = group["impl_rate"].median()
    std_impl_rate = group["impl_rate"].std()

    return pd.Series({
        # ... existing fields ...
        "mean_impl_rate": mean_impl_rate,
        "median_impl_rate": median_impl_rate,
        "std_impl_rate": std_impl_rate,
    })
```

### Phase 3: Export Integration

**File: `scripts/export_data.py`**

**3a. Overall statistics:**

```python
"overall_stats": {
    # ... existing fields ...
    "mean_impl_rate": float(runs_df["impl_rate"].mean()),
    "median_impl_rate": float(runs_df["impl_rate"].median()),
}
```

**3b. By-model statistics:**

```python
for model in runs_df["agent_model"].unique():
    model_df = runs_df[runs_df["agent_model"] == model]
    impl_rates = model_df["impl_rate"].dropna()

    summary["by_model"][model] = {
        # ... existing fields ...
        "mean_impl_rate": float(impl_rates.mean()),
        "median_impl_rate": float(impl_rates.median()),
        "std_impl_rate": float(impl_rates.std()),
        "min_impl_rate": float(impl_rates.min()),
        "max_impl_rate": float(impl_rates.max()),
    }
```

**3c. By-tier statistics:**

```python
for tier in tier_order:
    tier_df = runs_df[runs_df["tier"] == tier]
    impl_rates = tier_df["impl_rate"].dropna()

    summary["by_tier"][tier] = {
        # ... existing fields ...
        "mean_impl_rate": float(impl_rates.mean()),
        "median_impl_rate": float(impl_rates.median()),
        "std_impl_rate": float(impl_rates.std()),
    }
```

### Phase 4: Test Implementation

**File: `tests/unit/analysis/test_stats.py`**

**4a. Add metric test:**

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

**File: `tests/unit/analysis/conftest.py`**

**4b. Update fixtures:**

```python
@pytest.fixture
def sample_runs_df():
    for run in range(1, 6):
        # ... existing fields ...
        score = np.random.uniform(0.5, 1.0) if passed else np.random.uniform(0.0, 0.5)

        # impl_rate: usually close to score, but not identical
        impl_rate = score + np.random.uniform(-0.05, 0.05)
        impl_rate = max(0.0, min(1.0, impl_rate))  # Clamp to [0, 1]

        data.append({
            # ... existing fields ...
            "impl_rate": impl_rate,  # ADD THIS
        })

@pytest.fixture
def sample_judges_df(sample_runs_df):
    for judge_idx, judge_model in enumerate(judge_models, start=1):
        # ... existing fields ...
        judge_impl_rate = np.clip(row["impl_rate"] + np.random.uniform(-0.1, 0.1), 0.0, 1.0)

        data.append({
            # ... existing fields ...
            "judge_impl_rate": judge_impl_rate,  # ADD THIS
        })
```

### Phase 5: Verification

**Run tests:**

```bash
# Test the new metric function
pixi run -e analysis pytest tests/unit/analysis/test_stats.py::test_compute_impl_rate -xvs

# Test dataframes integration
pixi run -e analysis pytest tests/unit/analysis/test_dataframes.py -xvs

# Run all analysis tests
pixi run -e analysis pytest tests/unit/analysis/ -q
```

**Expected outcome:**
- All existing tests continue to pass
- New metric test passes
- No warnings about missing columns

## Failed Attempts & Lessons Learned

### ❌ Attempt 1: Using 0.0 instead of NaN for edge cases

**What we tried:**
```python
if max_points == 0:
    return 0.0  # WRONG
```

**Why it failed:**
- Cannot distinguish between "no rubric defined" (edge case) vs "zero requirements satisfied" (actual failure)
- Inconsistent with loader.py convention of using `np.nan` for missing values (P1-6)

**Correct approach:**
```python
if max_points == 0:
    return np.nan  # Consistent with codebase conventions
```

### ❌ Attempt 2: Calculating impl_rate in loader.py

**What we tried:**
- Adding `impl_rate` field to `RunData` dataclass
- Calculating during `load_run()` function

**Why it failed:**
- Loader should be pure data loading (no calculations)
- Violates separation of concerns: loader → dataframes → stats
- Would require importing `compute_impl_rate` in loader (wrong layer)

**Correct approach:**
- Calculate in `build_runs_df()` (transformation layer)
- Use `compute_impl_rate()` from stats.py (calculation layer)

### ❌ Attempt 3: Not updating test fixtures

**What we tried:**
- Adding metric to dataframes without updating fixtures
- Expected tests to still pass

**Why it failed:**
```
KeyError: 'impl_rate'
```
- Fixtures in conftest.py didn't have the new column
- Tests that build dataframes or access columns failed

**Correct approach:**
- Always update fixtures when adding new columns
- Add realistic correlated data (impl_rate ≈ score ± 0.05)

### ⚠️ Important: Import placement in dataframes.py

**Issue:**
```python
# Consensus impl_rate: median across judges
import numpy as np  # Inside function - not ideal but works
```

**Why it's inside the function:**
- Ruff formatter moved it there during auto-formatting
- Works but not optimal placement

**Better approach for future:**
- Add `import numpy as np` at module level (top of file)
- Prevents redundant imports inside loops

## Results & Parameters

### Metric Specification

```
Impl-Rate = Σ(achieved_points) / Σ(max_points)
```

**Range:** [0, 1] where higher = more requirements satisfied
**Granularity:** More detailed than Pass-Rate (provides partial credit)
**Calculation:** Per-judge values aggregated via median (consensus)

### Files Modified

1. `scylla/analysis/stats.py` - Added `compute_impl_rate()` (+29 lines)
2. `scylla/analysis/dataframes.py` - Integration in 4 places (+40 lines)
3. `scripts/export_data.py` - Export to JSON (+15 lines)
4. `tests/unit/analysis/test_stats.py` - Test function (+20 lines)
5. `tests/unit/analysis/conftest.py` - Fixture updates (+11 lines)

**Total:** 115 lines added across 5 files

### Test Results

```
119 passed, 2 skipped, 6 warnings in 3.15s
```

**Breakdown:**
- ✅ 33 stats tests (including new `test_compute_impl_rate`)
- ✅ 11 dataframes tests (integration verified)
- ✅ 23 table tests (backward compatibility)
- ✅ 52 other analysis tests

### Performance Impact

**No performance degradation:**
- Metric calculated during DataFrame construction (already iterating)
- Simple arithmetic operation (achieved / max)
- Test suite runtime: ~3.15 seconds (unchanged)

## Common Pitfalls

1. **Forgetting aggregation layers:** Must add metric to both subtests AND tier aggregations
2. **Missing judge-level calculation:** Both consensus (runs_df) and per-judge (judges_df) needed
3. **Export incomplete:** Add to overall, by_model, AND by_tier sections
4. **Test fixtures out of sync:** Always update conftest.py when adding columns
5. **Using 0.0 instead of NaN:** Follow codebase convention for missing values

## Related Skills

- `data-integrity-best-practices` - NaN vs 0.0 conventions
- `test-fixture-management` - Updating conftest.py
- `analysis-pipeline-architecture` - Understanding 4 layers

## Success Criteria

- ✅ Core function in `stats.py` with proper edge case handling
- ✅ Integration in `dataframes.py` (runs, judges, subtests, tiers)
- ✅ Export in `export_data.py` (overall, by_model, by_tier)
- ✅ Test coverage with 5+ test cases
- ✅ Fixtures updated in `conftest.py`
- ✅ All 119 tests passing
- ✅ No performance degradation
