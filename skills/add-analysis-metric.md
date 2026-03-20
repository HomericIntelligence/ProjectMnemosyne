---
name: add-analysis-metric
description: 'TRIGGER CONDITIONS: Adding new aggregated metrics to build_subtests_df(),
  tier_summary(), or model_comparison() in scylla/analysis/dataframes.py. Use when
  extending the analysis layer with new per-run measurements that need mean/median/std
  at the subtest, tier, or model-comparison level.'
category: evaluation
date: 2026-03-02
version: 1.0.0
user-invocable: false
---
# add-analysis-metric

How to add new aggregated metric columns to `build_subtests_df()`, `tier_summary()`, and `model_comparison()` in ProjectScylla's analysis layer, with correct NaN handling and fixture symmetry.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-27 (updated 2026-03-02) |
| Objective | Extend analysis aggregation functions with process metrics (r_prog, cfp, pr_revert_rate, strategic_drift) |
| Outcome | Success — all pre-commit hooks pass |
| Issues | HomericIntelligence/ProjectScylla#1134, #1189 |
| PRs | HomericIntelligence/ProjectScylla#1183, #1299 |

## When to Use

- Adding mean/median/std aggregations for a new nullable per-run metric to `build_subtests_df()`
- Adding the same aggregations to `tier_summary()` for tier-level analysis
- Adding the same aggregations to `model_comparison()` for cross-model comparison
- Any new column in `build_runs_df()` that needs to be rolled up to subtest, tier, or model granularity
- Updating `conftest.py` fixtures after adding columns to production aggregation functions

## Architecture: 4-Layer Analysis Stack

ProjectScylla analysis follows a strict layer hierarchy — only modify the layer that owns the concern:

```
loader.py         → RunData dataclass (raw fields per run)
    ↓
dataframes.py     → build_runs_df() (one row per run)
                    build_subtests_df() (one row per subtest group, aggregated)
                    tier_summary() (one row per tier group, aggregated)
    ↓
stats.py          → compute_consistency(), compute_cop(), statistical tests
    ↓
tables.py         → formatted output tables (Table_CFP, Table_02, etc.)
```

**Rule**: Aggregation belongs in `dataframes.py` only. Never add it to `stats.py`, `loader.py`, or `tables.py`.

## Verified Workflow

### Step 1: Ensure the column exists in `build_runs_df()`

Confirm the raw column is already present in `build_runs_df()` output (check `dataframes.py` lines ~140–150):

```python
# build_runs_df() rows dict — nullable columns use None (pandas converts to NaN)
"r_prog": run.r_prog,          # float | None
"cfp": run.cfp,                # float | None
"pr_revert_rate": run.pr_revert_rate,  # float | None
"strategic_drift": run.strategic_drift,  # float | None
```

### Step 2: Add aggregations to `compute_subtest_stats()` inside `build_subtests_df()`

Add after the `cop` calculation, before the grade-distribution block:

```python
# Process metrics (nullable — NaN when data not yet collected)
mean_<metric>    = group["<metric>"].mean()
median_<metric>  = group["<metric>"].median()
std_<metric>     = group["<metric>"].std()
```

Add the new keys to the returned `pd.Series` dict after `"cop"`, before `"grade_S"`:

```python
"mean_<metric>":   mean_<metric>,
"median_<metric>": median_<metric>,
"std_<metric>":    std_<metric>,
```

**Do NOT** use `skipna=False` or add explicit NaN guards — pandas `.mean()/.median()/.std()` all default to `skipna=True`, which is correct: aggregate over available data, return NaN only when the entire group is NaN.

### Step 3: Add the same aggregations to `compute_tier_stats()` inside `tier_summary()`

Exact same pattern — add after `cop`, before `return pd.Series(...)`:

```python
# Process metrics (nullable — NaN when data not yet collected)
mean_<metric>    = group["<metric>"].mean()
median_<metric>  = group["<metric>"].median()
std_<metric>     = group["<metric>"].std()
```

Add to the returned dict after `"cop"`.

### Step 3b: Extend `model_comparison()` `.agg()` dict (pandas MultiIndex style)

`model_comparison()` uses a raw `.agg()` dict, not a custom function. Output columns are MultiIndex tuples
like `("r_prog", "mean")`. Add after `"total_tokens"`:

```python
return grouped.agg(
    {
        "passed": "mean",
        "score": ["mean", "median", "std"],
        "cost_usd": ["mean", "sum"],
        "duration_seconds": "mean",
        "total_tokens": ["mean", "sum"],
        "r_prog": ["mean", "median", "std"],         # ← add
        "cfp": ["mean", "median", "std"],            # ← add
        "pr_revert_rate": ["mean", "median", "std"], # ← add
        "strategic_drift": ["mean", "median", "std"],# ← add
    }
).reset_index()
```

**Key difference from `tier_summary()`**: columns are MultiIndex tuples `("r_prog", "mean")`, not flat
strings `"mean_r_prog"`. Tests must check `(metric, agg) in list(result.columns)`.

### Step 4: Update `sample_runs_df` fixture in `tests/unit/analysis/conftest.py`

Add the 4 nullable columns inside the `data.append({...})` block (after `"exit_code": 0`):

```python
# Process metrics — nullable, ~70% of rows get real values, rest NaN
r_prog = np.random.uniform(0.0, 1.0) if np.random.random() < 0.7 else np.nan
cfp    = np.random.uniform(0.0, 0.3) if np.random.random() < 0.7 else np.nan
pr_revert_rate  = np.random.uniform(0.0, 0.2) if np.random.random() < 0.7 else np.nan
strategic_drift = np.random.uniform(0.0, 0.5) if np.random.random() < 0.7 else np.nan
```

The `np.random.seed(42)` is set at fixture entry, so values are reproducible.

### Step 5: Update `sample_subtests_df` fixture (keep fixture symmetry)

The `sample_subtests_df` fixture contains a local `compute_subtest_stats()` that **must mirror production exactly**. Add the same 12 local variables and return-dict keys.

Use defensive column guards (production doesn't need them, but the fixture is reused across tests that may not supply all columns):

```python
mean_r_prog = group["r_prog"].mean() if "r_prog" in group.columns else np.nan
```

### Step 6: Write tests in focused new file(s)

For `build_subtests_df()` / `tier_summary()` (flat column names), create
`tests/unit/analysis/test_<metric>_aggregation.py` covering:

1. Column presence in `build_subtests_df()` output (`"mean_<metric>" in result.columns`)
2. Correct mean/median/std values (compare to `np.mean(values)`, `np.median(values)`, `pd.Series(values).std()`)
3. All-NaN group → NaN aggregation (`pd.isna(result["mean_<metric>"].iloc[0])`)
4. Mixed NaN → skipna behaviour (`np.isfinite(result["mean_<metric>"].iloc[0])`)
5. Same column presence in `tier_summary()` output
6. Fixture symmetry: `set(sample_subtests_df.columns) == set(build_subtests_df(sample_runs_df).columns)`

For `model_comparison()` (MultiIndex column names), create
`tests/unit/analysis/test_model_comparison_process_metrics.py` covering:

1. Column presence: `(metric, agg) in list(result.columns)` for all 12 combinations
2. Mean correctness per metric (parametrize with `PROCESS_METRICS`): compare against
   `groupby(...)[metric].mean().reset_index()`
3. All-NaN group → NaN for all three aggregations
4. Mixed-NaN group → correct skipna mean
5. Row count unchanged: `len(result) == groupby(...).ngroups`
6. Grouping keys preserved: `"agent_model" in result.columns and "tier" in result.columns`

### Step 7: Verify

```bash
# Analysis unit tests only (fast)
pixi run python -m pytest tests/unit/analysis/ -q --no-cov

# Full suite (required before PR)
pixi run python -m pytest tests/ -q --no-cov

# Pre-commit hooks
pre-commit run --files scylla/analysis/dataframes.py tests/unit/analysis/conftest.py \
  tests/unit/analysis/test_<metric>_aggregation.py \
  tests/unit/analysis/test_model_comparison_process_metrics.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### New columns added (12 per aggregation function)

`build_subtests_df()` / `tier_summary()` — flat column names:
```python
PROCESS_METRIC_COLS = [
    "mean_r_prog",    "median_r_prog",    "std_r_prog",
    "mean_cfp",       "median_cfp",       "std_cfp",
    "mean_pr_revert_rate", "median_pr_revert_rate", "std_pr_revert_rate",
    "mean_strategic_drift", "median_strategic_drift", "std_strategic_drift",
]
```

`model_comparison()` — MultiIndex column tuples:
```python
PROCESS_METRICS = ["r_prog", "cfp", "pr_revert_rate", "strategic_drift"]
AGGREGATIONS = ["mean", "median", "std"]
# columns: (metric, agg) for metric in PROCESS_METRICS for agg in AGGREGATIONS
```

### NaN convention

- Use `None` in `build_runs_df()` row dicts (pandas converts to `NaN` in DataFrame)
- Use `np.nan` in fixture and test helper row dicts
- All aggregations return `NaN` when entire group is NaN, finite float otherwise

### Fixture density (~70% populated)

```python
r_prog = np.random.uniform(0.0, 1.0) if np.random.random() < 0.7 else np.nan
```

This ensures both paths (real value and NaN) are exercised without making tests brittle.

### Type annotation for test helper accepting nullable lists

```python
from collections.abc import Sequence

def _make_runs_df(
    r_prog: Sequence[float | None],
    cfp: Sequence[float | None] | None = None,
    ...
) -> pd.DataFrame:
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1134, PR #1183 | `build_subtests_df()` + `tier_summary()` |
| ProjectScylla | Issue #1189, PR #1299 | `model_comparison()` — MultiIndex agg pattern |

## References

- Related skills: `parallel-metrics-integration`, `defensive-analysis-patterns`, `validation-test-fixture-symmetry`
- Production file: `scylla/analysis/dataframes.py`
- Test files: `tests/unit/analysis/test_process_metrics_aggregation.py`, `tests/unit/analysis/test_model_comparison_process_metrics.py`
- Fixture file: `tests/unit/analysis/conftest.py`
